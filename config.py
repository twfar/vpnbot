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

    trial_duration_hours: int = 24

    min_paid_devices: int = 3
    max_paid_devices: int = 10
    base_monthly_price: int = 80
    extra_device_monthly_price: int = 30
    three_month_discount_percent: int = 10
    subscription_month_days: int = 30
    currency_code: str = "RUB"
    currency_symbol: str = "₽"

    payment_provider: str = "rollypay"
    payment_api_base_url: str = "https://rollypay.io"
    payment_api_key: str = ""
    payment_signing_secret: str = ""
    payment_callback_url: str = ""
    payment_webhook_path: str = "/payment/webhook"
    payment_test: bool = True
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
BOT_TOKEN = settings.bot_token
ADMIN_ID = settings.admin_id
ADMIN_COMMAND = settings.admin_command
TEST_USER_TG_ID = settings.test_user_tg_id

SERVICE_NAME = settings.service_name
SUBSCRIPTION_BASE_URL = settings.subscription_base_url.rstrip("/")
XUI_HOST = settings.xui_host.rstrip("/")
XUI_API_TOKEN = settings.xui_api_token
XUI_INBOUND_IDS = settings.parsed_inbound_ids
TRIAL_DURATION_HOURS = settings.trial_duration_hours
TRIAL_HWID_LIMIT = settings.trial_hwid_limit
PAID_HWID_LIMIT = settings.paid_hwid_limit
MIN_PAID_DEVICES = settings.min_paid_devices
MAX_PAID_DEVICES = settings.max_paid_devices
BASE_MONTHLY_PRICE = settings.base_monthly_price
EXTRA_DEVICE_MONTHLY_PRICE = settings.extra_device_monthly_price
THREE_MONTH_DISCOUNT_PERCENT = settings.three_month_discount_percent
SUBSCRIPTION_MONTH_DAYS = settings.subscription_month_days
PAYMENT_CURRENCY = settings.currency_code
CURRENCY_SYMBOL = settings.currency_symbol
PAYMENT_PROVIDER = settings.payment_provider
PAYMENT_API_BASE_URL = settings.payment_api_base_url.rstrip("/")
PAYMENT_API_KEY = settings.payment_api_key
PAYMENT_SIGNING_SECRET = settings.payment_signing_secret
PAYMENT_CALLBACK_URL = settings.payment_callback_url
PAYMENT_WEBHOOK_PATH = settings.payment_webhook_path
PAYMENT_TEST = settings.payment_test
PAYMENT_ORDER_PREFIX = settings.payment_order_prefix
CHANNEL_URL = settings.channel_url
CHANNEL_USERNAME = settings.channel_username or settings.channel_url
ADMIN_URL = settings.admin_url
SUPPORT_URL = settings.support_url
PRIVACY_URL = settings.privacy_url
OFFER_URL = settings.offer_url
MAIN_MENU_PHOTO = settings.main_menu_photo
TRIAL_MENU_PHOTO = settings.trial_menu_photo
MENU_PHOTOS = settings.parsed_menu_photos
PREMIUM_EMOJI_ID = settings.premium_emoji_id
DATABASE_PATH = str(Path(settings.database_path))
WEBHOOK_HOST = settings.webhook_host
WEBHOOK_PORT = settings.webhook_port
WEBHOOK_SSL_CERT_PATH = settings.webhook_ssl_cert_path
WEBHOOK_SSL_KEY_PATH = settings.webhook_ssl_key_path

# Compatibility aliases for the existing RollyPay adapter and webhook.
ROLLYPAY_API_KEY = PAYMENT_API_KEY
ROLLYPAY_SIGNING_SECRET = PAYMENT_SIGNING_SECRET
ROLLYPAY_CALLBACK_URL = PAYMENT_CALLBACK_URL
ROLLYPAY_TEST = PAYMENT_TEST

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")
if not ADMIN_ID:
    raise RuntimeError("ADMIN_ID is not set")
if not XUI_API_TOKEN:
    raise RuntimeError("XUI_API_TOKEN is not set")
