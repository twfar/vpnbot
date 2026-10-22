"""Provider-neutral payment contracts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol, TypedDict


class PaymentResult(TypedDict):
    """Minimum normalized fields required by the bot checkout flow."""

    payment_id: str
    order_id: str
    pay_url: str


class PaymentProvider(Protocol):
    """Contract every payment integration must implement."""

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
        """Create a payment and return normalized checkout details."""
        ...

    def verify_webhook(
        self, raw_body: bytes, headers: Mapping[str, str]
    ) -> bool:
        """Verify the provider-specific webhook signature."""
        ...

    def parse_webhook(self, raw_body: bytes) -> PaymentWebhookEvent:
        """Normalize a provider-specific webhook payload."""
        ...

@dataclass(frozen=True, slots=True)
class PaymentWebhookEvent:
    """Provider-neutral representation of a verified payment webhook."""

    payment_id: str
    status: str
    amount: str
    currency: str
    test: bool | None
    event_type: str


