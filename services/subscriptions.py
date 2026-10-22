"""Subscription application service.

This is the first extraction from the legacy Telegram/webhook handlers.
Business rules remain unchanged; database and 3x-ui implementations are
still the existing adapters and can be replaced independently later.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Any

from db import update_user
from xui import create_client, get_subscription_url, renew_client_by_sub_id


@dataclass(frozen=True, slots=True)
class RenewalResult:
    """Result of applying a paid period to a user's 3x-ui subscription."""

    sub_id: str
    expires_at: int


async def renew_paid_subscription(
    user: Mapping[str, Any],
    payment: Mapping[str, Any],
) -> RenewalResult:
    """Apply one paid period and synchronize the local user record.

    The caller remains responsible for validating the payment and marking its
    final status. This function deliberately preserves the legacy behavior:
    recreate a missing 3x-ui client, then apply the paid period and HWID limit.
    """
    raw_sub_id = user["sub_id"]
    sub_id = str(raw_sub_id) if raw_sub_id else ""

    if not sub_id:
        recreated = create_client(
            tg_id=int(user["tg_id"]),
            email=str(user["email"] or f"tg_{user['tg_id']}"),
            expiry_hours=0,
            group="paid",
        )
        sub_id = str(recreated["sub_id"])

    updated = renew_client_by_sub_id(
        sub_id,
        int(payment["days"]),
        device_limit=int(payment["device_limit"]),
    )
    expires_at = int(updated.get("expiryTime", 0)) // 1000

    await update_user(
        tg_id=user["tg_id"],
        username=user["username"],
        email=user["email"],
        sub_id=sub_id,
        subscription_url=get_subscription_url(sub_id, json_mode=True),
        status="paid",
        created_at=user["created_at"],
        expires_at=expires_at,
    )
    return RenewalResult(sub_id=sub_id, expires_at=expires_at)
