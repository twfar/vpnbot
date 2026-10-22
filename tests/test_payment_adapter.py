"""Tests for provider-specific webhook verification and normalization."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import unittest

# The legacy config module validates required deployment settings at import time.
# Supply disposable values so these tests never need real credentials.
os.environ["BOT_TOKEN"] = "unit-test-token"
os.environ["ADMIN_ID"] = "1"
os.environ["XUI_API_TOKEN"] = "unit-test-xui-token"
os.environ["PAYMENT_SIGNING_SECRET"] = "unit-test-signing-secret"

from payments.rollypay import RollyPayProvider


class RollyPayAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = RollyPayProvider()

    def test_valid_signature_is_accepted(self) -> None:
        body = b'{"payment_id":"p-1","status":"paid"}'
        timestamp = "1720000000"
        signature = hmac.new(
            b"unit-test-signing-secret",
            timestamp.encode() + b"." + body,
            hashlib.sha256,
        ).hexdigest()
        self.assertTrue(
            self.provider.verify_webhook(
                body,
                {"X-Timestamp": timestamp, "X-Signature": signature},
            )
        )

    def test_invalid_signature_is_rejected(self) -> None:
        self.assertFalse(
            self.provider.verify_webhook(
                b'{"payment_id":"p-1"}',
                {"X-Timestamp": "1720000000", "X-Signature": "bad"},
            )
        )

    def test_payload_is_normalized(self) -> None:
        event = self.provider.parse_webhook(
            json.dumps(
                {
                    "payment_id": "p-1",
                    "status": "paid",
                    "amount": "80.00",
                    "currency": "RUB",
                    "test": True,
                    "event_type": "payment.paid",
                }
            ).encode()
        )
        self.assertEqual(event.payment_id, "p-1")
        self.assertEqual(event.status, "paid")
        self.assertEqual(event.amount, "80.00")
        self.assertEqual(event.currency, "RUB")
        self.assertTrue(event.test)
        self.assertEqual(event.event_type, "payment.paid")

    def test_malformed_payload_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.provider.parse_webhook(b"{not-json")


if __name__ == "__main__":
    unittest.main()
