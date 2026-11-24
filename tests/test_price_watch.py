import unittest

from src.price_watch import SellerAsset, monitor_catalog_item


class BuyerDecisionTest(unittest.TestCase):
    def test_lower_candidate_creates_update_and_handoff(self):
        asset = SellerAsset("seller-a", "https://example.com/item", 30.0)

        update, handoff = monitor_catalog_item(asset, "buyer-a", "item-1", 27.5)

        self.assertEqual(update.kind, "better_offer")
        self.assertEqual(update.amount, 27.5)
        self.assertEqual(handoff.seller_id, "seller-a")
        self.assertEqual(handoff.buyer_id, "buyer-a")

    def test_equal_candidate_keeps_current_handoff_state(self):
        asset = SellerAsset("seller-a", "https://example.com/item", 30.0)

        update, handoff = monitor_catalog_item(asset, "buyer-a", "item-1", 30.0)

        self.assertIsNone(update)
        self.assertIsNone(handoff)


if __name__ == "__main__":
    unittest.main()
