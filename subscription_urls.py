"""Pure helpers for building public 3x-ui subscription URLs."""
from __future__ import annotations

from urllib.parse import quote


def build_subscription_url(base_url: str, sub_id: str, path: str) -> str:
    """Build a public subscription URL from one base and a configurable path."""
    normalized_base = base_url.strip().rstrip("/")
    normalized_path = "/" + path.strip("/") + "/"
    normalized_sub_id = sub_id.strip()
    if not normalized_base:
        raise ValueError("subscription base URL is required")
    if not normalized_sub_id:
        raise ValueError("subscription ID is required")
    if not normalized_path.strip("/"):
        raise ValueError("subscription path is required")
    return f"{normalized_base}{normalized_path}{quote(normalized_sub_id, safe='')}"
