# универсальный vpn telegram-бот

изолированная копия для адаптации под отдельный VPN-сервис.

## состояние

- сохранены основные сценарии исходного бота: trial, подписки, HWID, промокоды, рефералы, уведомления, рассылки и админ-панель;
- настройки сервиса вынесены в `config.py`, пример — в `.env.example`;
- платёжная реализация пока использует RollyPay; другой провайдер потребует отдельного адаптера;
- база пока SQLite/aiosqlite, часть логики остаётся в `bot.py`.

## запуск

1. установите Python 3.12+.
2. создайте окружение и установите зависимости: `python -m venv .venv`, затем `pip install -r requirements.txt`.
3. скопируйте `.env.example` в `.env` и заполните собственными значениями.
4. настройте Telegram, 3x-ui, ссылки подписок, тарифы, лимиты устройств и платежи.
5. тестируйте сначала на отдельном Telegram-боте и тестовой панели 3x-ui.

не коммитьте `.env`, базы данных, логи или реальные ключи. см. [реестр зависимостей](DEPENDENCIES.md).

## architecture progress

- `services/subscriptions.py` now owns the paid-renewal operation used by the webhook; trial, promo, referral, broadcast, HWID and notification rules remain in their existing code paths until extracted one at a time.
- `xui.py` remains the 3x-ui adapter. `SUBSCRIPTION_BASE_URL`, `XUI_SUBSCRIPTION_PATH` and `XUI_JSON_SUBSCRIPTION_PATH` generate regular and JSON subscription links from one base URL.
- `payments/` defines a provider contract and a RollyPay adapter. Checkout and webhook parsing go through the contract; a replacement provider must implement payment creation, signature verification and webhook normalization.
- paid webhook handling uses an atomic database claim to prevent simultaneous duplicate deliveries from renewing the same subscription twice. A `processing` payment should be reviewed manually if the process crashes mid-renewal; this avoids blindly retrying an operation that may already have extended 3x-ui.

## isolated test setup

1. Copy `.env.test.example` to `.env.test` and fill it with a separate test bot token, test payment credentials and a dedicated test 3x-ui panel/token.
2. Keep `DATABASE_PATH=test_bot.db`, webhook port `8444`, and a test-only callback URL. Never point this environment at the production panel or database.
3. Run unit tests with `python -m unittest discover -s tests -v` and syntax checks with `python -m compileall -q .`.
4. Then verify the full lifecycle manually in the isolated environment: trial, paid purchase, successful and failed payment, repeated paid webhook, missing 3x-ui client recreation, referral reward, promo redemption, HWID limits, notification deduplication and background cleanup.

The full lifecycle against a real test panel/payment provider has not been run yet; it requires valid test credentials and a reachable test webhook endpoint.
