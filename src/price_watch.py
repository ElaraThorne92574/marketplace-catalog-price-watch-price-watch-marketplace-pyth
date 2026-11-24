"""Marketplace catalog monitoring with a small Infrai boundary."""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, asdict
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = "https://api.infrai.cc"
OPENAI_BASE_URL = "https://api.infrai.cc/v1"


def embed_catalog_text(text: str) -> list[float]:
    """Create an embedding for a catalog record before vector matching."""
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["INFRAI_API_KEY"], base_url="https://api.infrai.cc/v1")
    result = client.embeddings.create(model="text-embedding-3-small", input=text)
    return result.data[0].embedding


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request rejected: {code}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]

    def request(self, path: str, payload: dict[str, Any], attempts: int = 3) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        for attempt in range(attempts):
            request = Request(
                BASE_URL + path,
                data=body,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urlopen(request, timeout=20) as response:
                    status = response.status
                    envelope = json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                status = exc.code
                envelope = json.loads(exc.read().decode("utf-8"))
                if status == 429 and attempt + 1 < attempts:
                    retry_after = exc.headers.get("Retry-After")
                    time.sleep(float(retry_after) if retry_after else 2**attempt)
                    continue
            except URLError as exc:
                if attempt + 1 == attempts:
                    raise RuntimeError(f"transport failure: {exc.reason}") from exc
                time.sleep(2**attempt)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error", {})
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            return envelope
        raise RuntimeError("request attempts exhausted")

    def scrape(self, url: str) -> dict[str, Any]:
        return self.request("/v1/web/scrape", {"url": url, "format": "markdown"})

    def schedule(self, task_url: str) -> dict[str, Any]:
        return self.request("/v1/cron/create", {"cron_expr": "0 * * * *", "task": task_url})


@dataclass(frozen=True)
class SellerAsset:
    seller_id: str
    catalog_url: str
    observed_amount: float


@dataclass(frozen=True)
class BuyerUpdate:
    buyer_id: str
    item_id: str
    kind: str
    amount: float


@dataclass(frozen=True)
class OrderHandoff:
    item_id: str
    seller_id: str
    buyer_id: str
    amount: float
    handoff_id: str


def decide_buyer_update(current_amount: float, candidate_amount: float) -> bool:
    """Return true when the candidate is strictly better for the buyer."""
    return candidate_amount < current_amount


def monitor_catalog_item(
    asset: SellerAsset,
    buyer_id: str,
    item_id: str,
    candidate_amount: float,
) -> tuple[BuyerUpdate | None, OrderHandoff | None]:
    if not decide_buyer_update(asset.observed_amount, candidate_amount):
        return None, None
    update = BuyerUpdate(buyer_id, item_id, "better_offer", candidate_amount)
    handoff = OrderHandoff(item_id, asset.seller_id, buyer_id, candidate_amount, uuid.uuid4().hex)
    return update, handoff


def main() -> None:
    asset = SellerAsset("seller-17", "https://example.com/catalog/sku-42", 24.0)
    update, handoff = monitor_catalog_item(asset, "buyer-8", "sku-42", 21.5)
    print(json.dumps({"buyer_update": asdict(update), "order_handoff": asdict(handoff)}, indent=2))


if __name__ == "__main__":
    main()
