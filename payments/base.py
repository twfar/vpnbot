"""Provider-neutral payment contracts."""
from __future__ import annotations

from typing import Protocol, TypedDict


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
