"""RollyPay implementation of the provider-neutral contract."""
from __future__ import annotations

import hashlib
import hmac
import json
from typing import Mapping

from config import PAYMENT_SIGNING_SECRET
from payments.base import PaymentWebhookEvent
from rollypay import create_payment as create_rollypay_payment
from payments.base import PaymentResult


class RollyPayProvider:
    """Adapter that keeps RollyPay-specific API details out of handlers."""

    async def create_payment(
        self,
        *,
        api_key: str,
        amount: float,
        tg_id: int,
        days: int,
        test: bool,
        devices: int,
        months: int,
    ) -> PaymentResult:
        result = await create_rollypay_payment(
            api_key=api_key,
            amount=amount,
            tg_id=tg_id,
            days=days,
            test=test,
            devices=devices,
            months=months,
        )
        return {
            "payment_id": str(result["payment_id"]),
            "order_id": str(result["order_id"]),
            "pay_url": str(result["pay_url"]),
        }

    def verify_webhook(
        self, raw_body: bytes, headers: Mapping[str, str]
    ) -> bool:
        """Verify the current RollyPay timestamp + HMAC-SHA256 signature."""
        timestamp = headers.get("X-Timestamp", "")
        signature = headers.get("X-Signature", "")
        if not timestamp or not signature or not PAYMENT_SIGNING_SECRET:
            return False
        expected = hmac.new(
            PAYMENT_SIGNING_SECRET.encode(),
            timestamp.encode() + b"." + raw_body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def parse_webhook(self, raw_body: bytes) -> PaymentWebhookEvent:
        """Translate RollyPay's payload into the shared event structure."""
        try:
            payload = json.loads(raw_body)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError("invalid json") from exc
        if not isinstance(payload, dict):
            raise ValueError("invalid webhook payload")
        payment_id = payload.get("payment_id")
        status = payload.get("status")
        if not payment_id or not status:
            raise ValueError("missing payment fields")
        test_value = bool(payload["test"]) if "test" in payload else None
        return PaymentWebhookEvent(
            payment_id=str(payment_id),
            status=str(status),
            amount=str(payload.get("amount", 0)),
            currency=str(payload.get("currency", "")),
            test=test_value,
            event_type=str(payload.get("event_type", "—")),
        )
