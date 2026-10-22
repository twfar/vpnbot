"""Central configuration for the reusable VPN Telegram bot.

All deployment-specific values are read from environment variables or .env.
Keep secrets out of version control.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings loaded from the process environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    service_name: str = "my vpn"
    bot_token: str = ""
    admin_id: int = 0
    admin_command: str = "admin"
    test_user_tg_id: int = 0

    subscription_base_url: str = "https://example.com:2096"

    xui_host: str = "https://127.0.0.1:2053"
    xui_api_token: str = ""
    xui_inbound_ids: str = "1"
    trial_hwid_limit: int = 1
    paid_hwid_limit: int = 3

    trial_hours: int = 12
    trial_duration_hours: int = 24
    trial_limit: int = 4
    subscription_delete_after_days: int = 3

    min_paid_devices: int = 3
    max_paid_devices: int = 10
    base_monthly_price: int = 80
    extra_device_monthly_price: int = 30
    currency_code: str = "RUB"
    currency_symbol: str = "₽"

    payment_provider: str = "rollypay"
    payment_api_base_url: str = "https://rollypay.io"
    payment_api_key: str = ""
    payment_signing_secret: str = ""
    payment_callback_url: str = ""
    payment_webhook_path: str = "/payment/webhook"
    payment_test: bool = True
    payment_default_price: int = 80
    payment_default_days: int = 30
    payment_order_prefix: str = "vpn"

    channel_url: str = ""
    channel_username: str = ""
    admin_url: str = ""
    support_url: str = ""
    privacy_url: str = ""
    offer_url: str = ""

    main_menu_photo: str = ""
    trial_menu_photo: str = ""
    menu_photos: str = ""
    premium_emoji_id: str = ""

    database_path: str = "bot.db"
    webhook_host: str = "127.0.0.1"
    webhook_port: int = 8443
    webhook_ssl_cert_path: str = ""
    webhook_ssl_key_path: str = ""

    @property
    def parsed_inbound_ids(self) -> list[int]:
        """Parse a comma-separated list of 3x-ui inbound IDs."""
        values = [part.strip() for part in self.xui_inbound_ids.split(",") if part.strip()]
        ids = [int(value) for value in values]
        if not ids or any(value <= 0 for value in ids) or len(ids) != len(set(ids)):
            raise ValueError("XUI_INBOUND_IDS must contain unique positive integers")
        return ids

    @property
    def parsed_menu_photos(self) -> list[str]:
        """Parse optional comma-separated Telegram photo file IDs."""
        values = [value.strip() for value in self.menu_photos.split(",") if value.strip()]
        return values or [value for value in (self.main_menu_photo, self.trial_menu_photo) if value]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()


settings = get_settings()

# Backwards-compatible names used by the current legacy modules.
BOT_TOKEN = settings.BOT_TOKEN
ADMIN_ID = settings.ADMIN_ID
ADMIN_COMMAND = settings.ADMIN_COMMAND
TEST_USER_TG_ID = settings.TEST_USER_TG_ID

SERVICE_NAME = settings.SERVICE_NAME
SUBSCRIPTION_BASE_URL = settings.SUBSCRIPTION_BASE_URL.rstrip("/")
XUI_HOST = settings.XUI_HOST.rstrip("/")
XUI_API_TOKEN = settings.XUI_API_TOKEN
XUI_INBOUND_IDS = settings.parsed_inbound_ids
TRIAL_HOURS = settings.TRIAL_HOURS
TRIAL_DURATION_HOURS = settings.TRIAL_DURATION_HOURS
TRIAL_LIMIT = settings.TRIAL_LIMIT
TRIAL_HWID_LIMIT = settings.TRIAL_HWID_LIMIT
PAID_HWID_LIMIT = settings.PAID_HWID_LIMIT
SUBSCRIPTION_DELETE_AFTER_DAYS = settings.SUBSCRIPTION_DELETE_AFTER_DAYS
MIN_PAID_DEVICES = settings.MIN_PAID_DEVICES
MAX_PAID_DEVICES = settings.MAX_PAID_DEVICES
BASE_MONTHLY_PRICE = settings.BASE_MONTHLY_PRICE
EXTRA_DEVICE_MONTHLY_PRICE = settings.EXTRA_DEVICE_MONTHLY_PRICE
PAYMENT_CURRENCY = settings.CURRENCY_CODE
CURRENCY_SYMBOL = settings.CURRENCY_SYMBOL
PAYMENT_PROVIDER = settings.PAYMENT_PROVIDER
PAYMENT_API_BASE_URL = settings.PAYMENT_API_BASE_URL.rstrip("/")
PAYMENT_API_KEY = settings.PAYMENT_API_KEY
PAYMENT_SIGNING_SECRET = settings.PAYMENT_SIGNING_SECRET
PAYMENT_CALLBACK_URL = settings.PAYMENT_CALLBACK_URL
PAYMENT_WEBHOOK_PATH = settings.PAYMENT_WEBHOOK_PATH
PAYMENT_TEST = settings.PAYMENT_TEST
PAYMENT_DEFAULT_PRICE = settings.PAYMENT_DEFAULT_PRICE
PAYMENT_DEFAULT_DAYS = settings.PAYMENT_DEFAULT_DAYS
PAYMENT_ORDER_PREFIX = settings.PAYMENT_ORDER_PREFIX
CHANNEL_URL = settings.CHANNEL_URL
CHANNEL_USERNAME = settings.CHANNEL_USERNAME or settings.CHANNEL_URL
ADMIN_URL = settings.ADMIN_URL
SUPPORT_URL = settings.SUPPORT_URL
PRIVACY_URL = settings.PRIVACY_URL
OFFER_URL = settings.OFFER_URL
MAIN_MENU_PHOTO = settings.MAIN_MENU_PHOTO
TRIAL_MENU_PHOTO = settings.TRIAL_MENU_PHOTO
MENU_PHOTOS = settings.parsed_menu_photos
PREMIUM_EMOJI_ID = settings.PREMIUM_EMOJI_ID
DATABASE_PATH = str(Path(settings.DATABASE_PATH))
WEBHOOK_HOST = settings.WEBHOOK_HOST
WEBHOOK_PORT = settings.WEBHOOK_PORT
WEBHOOK_SSL_CERT_PATH = settings.WEBHOOK_SSL_CERT_PATH
WEBHOOK_SSL_KEY_PATH = settings.WEBHOOK_SSL_KEY_PATH

# Compatibility aliases for the existing RollyPay adapter and webhook.
ROLLYPAY_API_KEY = PAYMENT_API_KEY
ROLLYPAY_SIGNING_SECRET = PAYMENT_SIGNING_SECRET
ROLLYPAY_CALLBACK_URL = PAYMENT_CALLBACK_URL
ROLLYPAY_TEST = PAYMENT_TEST
ROLLYPAY_DEFAULT_PRICE = PAYMENT_DEFAULT_PRICE
ROLLYPAY_DEFAULT_DAYS = PAYMENT_DEFAULT_DAYS

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")
if not ADMIN_ID:
    raise RuntimeError("ADMIN_ID is not set")
if not XUI_API_TOKEN:
    raise RuntimeError("XUI_API_TOKEN is not set")
