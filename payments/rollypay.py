"""RollyPay implementation of the provider-neutral contract."""
from __future__ import annotations

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
