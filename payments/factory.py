"""Payment provider selection."""
from __future__ import annotations

from config import PAYMENT_PROVIDER
from payments.base import PaymentProvider
from payments.rollypay import RollyPayProvider


def get_payment_provider(provider_name: str | None = None) -> PaymentProvider:
    """Return the configured adapter; unsupported providers fail explicitly."""
    selected = (provider_name or PAYMENT_PROVIDER).strip().lower()
    if selected == "rollypay":
        return RollyPayProvider()
    raise ValueError(
        f"unsupported payment provider: {selected!r}; "
        "implement its adapter before selecting it"
    )
