"""Unit tests for subscription URL construction."""
import unittest

from subscription_urls import build_subscription_url


class SubscriptionUrlTests(unittest.TestCase):
    def test_regular_subscription_uses_configured_base(self) -> None:
        self.assertEqual(
            build_subscription_url(
                "https://vpn.example:2096/",
                "abc123",
                "/s/",
            ),
            "https://vpn.example:2096/s/abc123",
        )

    def test_json_subscription_uses_same_base(self) -> None:
        self.assertEqual(
            build_subscription_url(
                "https://vpn.example:2096",
                "abc123",
                "/jsnn/",
            ),
            "https://vpn.example:2096/jsnn/abc123",
        )

    def test_subscription_id_is_url_encoded(self) -> None:
        self.assertEqual(
            build_subscription_url("https://vpn.example", "id /1", "s"),
            "https://vpn.example/s/id%20%2F1",
        )

    def test_missing_base_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_subscription_url("", "abc123", "/s/")


if __name__ == "__main__":
    unittest.main()
