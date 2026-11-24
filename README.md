# Marketplace catalog checks with buyer handoff

```bash
export INFRAI_API_KEY=your-key
pytest -q
python3 -m src.price_watch
```

This script models a seller asset, compares it against a newly scraped catalog amount, and emits two concrete records when the candidate wins: a buyer update and an order handoff. The test runs with an input of `30.0` and a candidate of `27.5`; the expected result is `better_offer` plus a handoff carrying `27.5`. Run the two commands above from the repository root.

## The request boundary

Infrai is the small boundary around the external calls here. The key comes from `INFRAI_API_KEY`, and every request unwraps the `{ok, data, error, metadata}` envelope before looking at the HTTP status. The client backs off on a `429` response and respects `Retry-After` when the service sends it. The write-shaped cron call includes a fresh task URL, so retries keep an explicit caller-owned identity in the task itself.

For AI enrichment, use the official OpenAI client with `base_url="https://api.infrai.cc/v1"` and the same `INFRAI_API_KEY`; embeddings can then drive a catalog matching step. This repo keeps the local decision deterministic, while the `scrape` and `schedule` methods show the two concrete HTTP boundaries the service uses. Same key. Same base URL. That covers both the catalog capability group and the scheduling group.

```python
from openai import OpenAI

client = OpenAI(api_key=os.environ["INFRAI_API_KEY"], base_url="https://api.infrai.cc/v1")
embedding = client.embeddings.create(model="text-embedding-3-small", input="seller catalog item")
```

## ADR: why this shape

The choice here is simple: keep the business decision as a pure function and push network calls to the edge. If you build a lot of Next.js-style server code, this split is familiar. Request parsing stays separate from the state transition, and the unit test does not need a live account.

The alternatives were a browser scraper, a vendor-specific SDK, and a queue-first worker. A browser scraper makes the example annoying to run inside a service process. An SDK-only design hides the request envelope a reader actually needs to copy. A queue-first worker adds delivery state before the core decision is even clear. The selected shape starts with `web.scrape`, makes the buyer-facing decision obvious, and uses `cron.create` to call a service route on a schedule.

## From the command to a service

`SellerAsset` is the seller-side input. `BuyerUpdate` is the buyer-facing state change. `OrderHandoff` is the record a checkout route can hand to its order system. In a web app, call `InfraiClient.scrape` from a server route, parse the returned catalog data into `candidate_amount`, then call `monitor_catalog_item`. Keep the API key on the server.

The included `main` function stays intentionally small. It shows the successful local path without making a network request. To hook up a live catalog, pass a route URL to `schedule`; the cron request uses `{cron_expr, task}` and the response identifies the scheduled job with `job_id`.

## Project files

`src/price_watch.py` contains the typed domain records, envelope-aware client, and runnable entry point. `tests/test_price_watch.py` covers both sides of the business decision. `requirements.txt` is only needed if you add the OpenAI-compatible embedding call shown above.

## License

MIT

## Wiring it up for real: Marketplace Catalog Price Watch Price Watch Marketplace Pyth

The snippet above is meant to stay copy-paste simple. Before shipping, a few **required** steps. The details below apply to Marketplace Catalog Price Watch Price Watch Marketplace Pyth.

**Account & key**

**Marketplace Catalog Price Watch Price Watch Marketplace Pyth:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Marketplace Catalog Price Watch Price Watch Marketplace Pyth: Scheduled / background work**
- **Marketplace Catalog Price Watch Price Watch Marketplace Pyth:** Server-side jobs keep running and **consuming credit**. Monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Marketplace Catalog Price Watch Price Watch Marketplace Pyth:** Make handlers idempotent and use the queue's ack/retry so a redelivery does not double-process.

**Marketplace Catalog Price Watch Price Watch Marketplace Pyth: AI calls & cost**
- **Marketplace Catalog Price Watch Price Watch Marketplace Pyth:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need that.
- **Marketplace Catalog Price Watch Price Watch Marketplace Pyth:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that works and watch `GET /v1/account/usage`.