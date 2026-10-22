import logging
import ssl

from aiohttp import web
from aiogram import Bot

from config import (BOT_TOKEN, ADMIN_ID, PAYMENT_SIGNING_SECRET, PAYMENT_WEBHOOK_PATH, WEBHOOK_HOST, WEBHOOK_PORT, WEBHOOK_SSL_CERT_PATH, WEBHOOK_SSL_KEY_PATH)
from payments.factory import get_payment_provider
from db import (
    get_payment,
    update_payment_status,
    update_payment_status_if_unclaimed,
    claim_payment_for_processing,
    get_user,
    get_referrer_id,
    update_user,
    register_referral_payment,
    get_pending_referral_rewards,
    mark_referral_rewards_applied,
)
from xui import add_days_to_client_by_sub_id, get_subscription_url
from services.subscriptions import renew_paid_subscription


payment_provider = get_payment_provider()


async def notify_admin(bot, text):
    try:
        await bot.send_message(ADMIN_ID, text)
    except Exception:
        logging.exception("failed to notify admin")


async def webhook(request):
    raw_body = await request.read()

    if not payment_provider.verify_webhook(raw_body, request.headers):
        return web.Response(status=403, text="invalid signature")

    try:
        event = payment_provider.parse_webhook(raw_body)
    except ValueError as exc:
        return web.Response(status=400, text=str(exc))

    payment_id = event.payment_id
    status = event.status

    payment = await get_payment(payment_id)

    if not payment:
        await notify_admin(
            request.app["bot"],
            f"⚠️ неизвестный платёж\n\n🆔 payment id: {payment_id}",
        )
        return web.Response(status=200, text="ignored")

    if event.test is not None and event.test != bool(payment["test"]):
        await notify_admin(
            request.app["bot"],
            f"⚠️ несовпадение test-режима\n\n🆔 payment id: {payment_id}",
        )
        return web.Response(status=400, text="test mode mismatch")

    try:
        event_amount = f"{float(event.amount):.2f}"
        stored_amount = f"{float(payment['amount']):.2f}"
    except (TypeError, ValueError):
        return web.Response(status=400, text="invalid amount")

    if event_amount != stored_amount:
        await notify_admin(
            request.app["bot"],
            f"⚠️ несовпадение суммы\n\n🆔 payment id: {payment_id}",
        )
        return web.Response(status=400, text="amount mismatch")

    if event.currency != payment["currency"]:
        return web.Response(status=400, text="currency mismatch")

    await notify_admin(
        request.app["bot"],
        "📩 платёжный webhook\n\n"
        f"событие: {event.event_type}\n"
        f"статус: {status}\n"
        f"🆔 payment id: {payment_id}\n"
        f"🧪 тест: {'да' if payment['test'] else 'нет'}",
    )

    if status != "paid":
        await update_payment_status_if_unclaimed(payment_id, status)
        if status in ("canceled", "expired"):
            try:
                await request.app["bot"].send_message(payment["tg_id"], "❌ оплата не прошла.\n\nплатёж отменён или истёк. если деньги списались, но подписка не продлилась — напиши в поддержку.")
            except Exception:
                logging.exception("failed to notify user about failed payment")
        return web.Response(status=200, text="ok")

    if not await claim_payment_for_processing(payment_id):
        return web.Response(status=200, text="already processed or processing")

    user = await get_user(payment["tg_id"])

    if not user:
        await notify_admin(
            request.app["bot"],
            "❌ оплата получена, но пользователь не найден в базе\n\n"
            f"🆔 telegram id: {payment['tg_id']}\n"
            f"💳 payment id: {payment_id}",
        )
        await update_payment_status(payment_id, "user_not_found")
        return web.Response(status=200, text="user not found")

    try:
        renewal = await renew_paid_subscription(user, payment)
        sub_id = renewal.sub_id
        expires_at = renewal.expires_at
    except Exception:
        logging.exception("failed to renew after payment")
        await update_payment_status(payment_id, "renewal_review")
        await notify_admin(
            request.app["bot"],
            "❌ оплата получена, но результат продления не подтверждён\n\n"
            "нужна ручная проверка панели перед повторной обработкой.\n"
            f"💳 payment id: {payment_id}\n"
            f"🔗 sub id: {user['sub_id'] or 'не создан'}",
        )
        return web.Response(status=500, text="renewal failed")

    await update_payment_status(payment_id, "paid")

    try:
        reward = await register_referral_payment(
            payment_id,
            payment["tg_id"],
        )
        if reward:
            referrer = await get_user(reward["referrer_id"])
            if referrer and referrer["sub_id"]:
                try:
                    updated_referrer = add_days_to_client_by_sub_id(
                        referrer["sub_id"],
                        reward["reward_days"],
                    )
                    referrer_expiry = (
                        int(updated_referrer.get("expiryTime", 0)) // 1000
                    )
                    await update_user(
                        tg_id=referrer["tg_id"],
                        username=referrer["username"],
                        email=referrer["email"],
                        sub_id=referrer["sub_id"],
                        subscription_url=(
                            get_subscription_url(referrer["sub_id"], json_mode=True)
                        ),
                        status=referrer["status"],
                        created_at=referrer["created_at"],
                        expires_at=referrer_expiry,
                    )
                    await mark_referral_rewards_applied([payment_id])
                except Exception:
                    logging.exception(
                        "failed to apply referral payment reward"
                    )

            await request.app["bot"].send_message(
                reward["referrer_id"],
                "🎉 твой реферал оплатил подписку "
                f"({reward['months']} мес.)!\n"
                f"🎁 тебе начислено +{reward['reward_days']} дней к подписке.",
            )
    except Exception:
        logging.exception("failed to process referral reward")

    await request.app["bot"].send_message(
        payment["tg_id"],
        "✅ оплата прошла!\n\n"
        f"🔗 подписка продлена на {payment['days']} дней.",
    )

    try:
        pending_rewards = await get_pending_referral_rewards(payment["tg_id"])
        if pending_rewards:
            total_pending = sum(int(row["reward_days"]) for row in pending_rewards)
            updated_client = add_days_to_client_by_sub_id(sub_id, total_pending)
            pending_expiry = int(updated_client.get("expiryTime", 0)) // 1000
            await update_user(
                tg_id=user["tg_id"], username=user["username"], email=user["email"],
                sub_id=sub_id, subscription_url=get_subscription_url(sub_id, json_mode=True),
                status="paid", created_at=user["created_at"], expires_at=pending_expiry,
            )
            await mark_referral_rewards_applied([row["payment_id"] for row in pending_rewards])
            await request.app["bot"].send_message(
                user["tg_id"], f"🎁 накопленные реферальные дни добавлены: +{total_pending} дней."
            )
    except Exception:
        logging.exception("failed to apply pending referral rewards")

    referrer_id = await get_referrer_id(payment["tg_id"])

    await notify_admin(
        request.app["bot"],
        "✅ подписка продлена автоматически\n\n"
        f"👤 telegram id: {payment['tg_id']}\n"
        f"💳 payment id: {payment_id}\n"
        f"🎁 добавлено: {payment['days']} дней\n"
        f"📱 устройств: {payment['device_limit']}\n"
        f"⏳ expires: {expires_at}\n"
        f"👥 реферал: {'да — ' + str(referrer_id) if referrer_id else 'нет'}",
    )

    return web.Response(status=200, text="ok")


async def create_app():
    app = web.Application()
    app["bot"] = Bot(token=BOT_TOKEN)
    app.router.add_post(PAYMENT_WEBHOOK_PATH, webhook)
    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    if not PAYMENT_SIGNING_SECRET:
        raise RuntimeError("PAYMENT_SIGNING_SECRET is not set")

    ssl_context = None
    if WEBHOOK_SSL_CERT_PATH and WEBHOOK_SSL_KEY_PATH:
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(WEBHOOK_SSL_CERT_PATH, WEBHOOK_SSL_KEY_PATH)

    web.run_app(
        create_app(),
        host=WEBHOOK_HOST,
        port=WEBHOOK_PORT,
        ssl_context=ssl_context,
    )
