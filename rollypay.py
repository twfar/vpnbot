import uuid
import aiohttp

from config import PAYMENT_API_BASE_URL, PAYMENT_CURRENCY, PAYMENT_ORDER_PREFIX, SERVICE_NAME

BASE_URL = PAYMENT_API_BASE_URL


async def create_payment(api_key, amount, tg_id, days, test, devices=3, months=1):
    order_id = f"{PAYMENT_ORDER_PREFIX}_{tg_id}_{uuid.uuid4().hex[:12]}"
    payload = {
        "amount": f"{amount:.2f}",
        "payment_currency": PAYMENT_CURRENCY,
        "order_id": order_id,
        "description": f"{SERVICE_NAME} — {days} дней",
        "metadata": {
            "tg_id": str(tg_id),
            "days": str(days),
            "devices": str(devices),
            "months": str(months),
        },
        "test": test,
    }
    headers = {
        "X-API-Key": api_key,
        "X-Nonce": str(uuid.uuid4()),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    timeout = aiohttp.ClientTimeout(total=15)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(
            f"{BASE_URL}/api/v1/payments",
            json=payload,
            headers=headers,
        ) as response:
            data = await response.json(content_type=None)
            if response.status >= 400 or not data.get("payment_id") or not data.get("pay_url"):
                raise RuntimeError(f"rollypay api error: {data}")
            return data
