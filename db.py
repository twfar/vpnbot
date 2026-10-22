import aiosqlite
import time

from config import DATABASE_PATH


async def init_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                tg_id INTEGER PRIMARY KEY,
                username TEXT,
                email TEXT UNIQUE,
                sub_id TEXT,
                subscription_url TEXT,
                status TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                expires_at INTEGER
            )
        """)

        # миграция старой базы
        cursor = await db.execute("PRAGMA table_info(users)")
        columns = {
            row[1]
            for row in await cursor.fetchall()
        }

        if "sub_id" not in columns:
            await db.execute(
                "ALTER TABLE users ADD COLUMN sub_id TEXT"
            )

        if "subscription_class" not in columns:
            await db.execute(
                "ALTER TABLE users ADD COLUMN subscription_class TEXT NOT NULL DEFAULT 'expired'"
            )

        await db.execute("""
            UPDATE users
            SET subscription_class = CASE
                WHEN sub_id IS NOT NULL
                 AND expires_at IS NOT NULL
                 AND expires_at > strftime('%s', 'now')
                THEN 'active'
                ELSE 'expired'
            END
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS trial_claims (
                tg_id INTEGER PRIMARY KEY,
                claimed_at INTEGER NOT NULL
            )
        """)

        # Preserve historical trial records already represented in the users table.
        await db.execute("""
            INSERT OR IGNORE INTO trial_claims (tg_id, claimed_at)
            SELECT tg_id, COALESCE(created_at, strftime('%s', 'now'))
            FROM users
            WHERE status = 'trial'
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS promo_codes (
                code TEXT PRIMARY KEY,
                reward_days INTEGER NOT NULL,
                max_uses INTEGER NOT NULL DEFAULT 0,
                used_count INTEGER NOT NULL DEFAULT 0,
                expires_at INTEGER,
                enabled INTEGER NOT NULL DEFAULT 1
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS promo_uses (
                code TEXT NOT NULL,
                tg_id INTEGER NOT NULL,
                used_at INTEGER NOT NULL,
                PRIMARY KEY (code, tg_id)
            )
        """)

        if "subscription_url" not in columns:
            await db.execute(
                "ALTER TABLE users ADD COLUMN subscription_url TEXT"
            )

        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                payment_id TEXT PRIMARY KEY,
                order_id TEXT UNIQUE NOT NULL,
                tg_id INTEGER NOT NULL,
                amount TEXT NOT NULL,
                currency TEXT NOT NULL,
                days INTEGER NOT NULL,
                test INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER
            )
        """)

        cursor = await db.execute("PRAGMA table_info(payments)")
        payment_columns = {row[1] for row in await cursor.fetchall()}

        if "device_limit" not in payment_columns:
            await db.execute("ALTER TABLE payments ADD COLUMN device_limit INTEGER NOT NULL DEFAULT 3")
        if "months" not in payment_columns:
            await db.execute("ALTER TABLE payments ADD COLUMN months INTEGER NOT NULL DEFAULT 1")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                referred_id INTEGER PRIMARY KEY,
                referrer_id INTEGER NOT NULL,
                created_at INTEGER NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS referral_rewards (
                payment_id TEXT PRIMARY KEY,
                referred_id INTEGER NOT NULL,
                referrer_id INTEGER NOT NULL,
                reward_days INTEGER NOT NULL,
                reward_type TEXT NOT NULL DEFAULT 'payment',
                applied INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL
            )
        """)

        cursor = await db.execute("PRAGMA table_info(referral_rewards)")
        referral_reward_columns = {row[1] for row in await cursor.fetchall()}
        if "reward_type" not in referral_reward_columns:
            await db.execute("ALTER TABLE referral_rewards ADD COLUMN reward_type TEXT NOT NULL DEFAULT 'payment'")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS notification_blocked_users (
                tg_id INTEGER PRIMARY KEY,
                username TEXT,
                blocked_at INTEGER NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS notification_log (
                tg_id INTEGER NOT NULL,
                notification_type TEXT NOT NULL,
                marker TEXT NOT NULL,
                sent_at INTEGER NOT NULL,
                PRIMARY KEY (tg_id, notification_type, marker)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS device_snapshots (
                tg_id INTEGER NOT NULL,
                device_key TEXT NOT NULL,
                device_name TEXT,
                first_seen INTEGER,
                PRIMARY KEY (tg_id, device_key)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS notification_log (
                tg_id INTEGER NOT NULL,
                notification_type TEXT NOT NULL,
                marker TEXT NOT NULL,
                sent_at INTEGER NOT NULL,
                PRIMARY KEY (tg_id, notification_type, marker)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS device_snapshots (
                tg_id INTEGER NOT NULL,
                device_key TEXT NOT NULL,
                device_name TEXT,
                first_seen INTEGER,
                PRIMARY KEY (tg_id, device_key)
            )
        """)

        await db.execute(
            "INSERT OR IGNORE INTO bot_settings (key, value) VALUES (?, ?)",
            ("maintenance_enabled", "0"),
        )
        await db.execute(
            "INSERT OR IGNORE INTO bot_settings (key, value) VALUES (?, ?)",
            (
                "maintenance_message",
                "🔧 технические работы\\n\\nбот временно недоступен. попробуй позже.",
            ),
        )

        await db.commit()


async def get_setting(key: str, default=None):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT value FROM bot_settings WHERE key = ?",
            (key,),
        )
        row = await cursor.fetchone()
        return row[0] if row else default


async def set_setting(key: str, value):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO bot_settings (key, value) VALUES (?, ?)",
            (key, str(value)),
        )
        await db.commit()


async def has_used_trial(tg_id: int) -> bool:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT 1 FROM trial_claims WHERE tg_id = ? LIMIT 1",
            (tg_id,),
        )
        return await cursor.fetchone() is not None


async def mark_trial_claimed(tg_id: int, claimed_at: int) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO trial_claims (tg_id, claimed_at) VALUES (?, ?)",
            (tg_id, claimed_at),
        )
        await db.commit()


async def get_user(tg_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            "SELECT * FROM users WHERE tg_id = ?",
            (tg_id,),
        )

        return await cursor.fetchone()


async def create_user(
    tg_id: int,
    username: str,
    email: str,
    sub_id: str,
    subscription_url: str,
    status: str,
    created_at: int,
    expires_at: int,
):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO users (
                tg_id,
                username,
                email,
                sub_id,
                subscription_url,
                status,
                created_at,
                expires_at,
                subscription_class
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tg_id,
            username,
            email,
            sub_id,
            subscription_url,
            status,
            created_at,
            expires_at,
            "active" if sub_id and expires_at and expires_at > int(time.time()) else "expired",
        ))

        await db.commit()
async def update_user(
    tg_id: int,
    username: str,
    email: str,
    sub_id: str | None,
    subscription_url: str | None,
    status: str,
    created_at: int,
    expires_at: int,
):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            UPDATE users
            SET
                username = ?,
                email = ?,
                sub_id = ?,
                subscription_url = ?,
                status = ?,
                created_at = ?,
                expires_at = ?,
                subscription_class = ?
            WHERE tg_id = ?
        """, (
            username,
            email,
            sub_id,
            subscription_url,
            status,
            created_at,
            expires_at,
            "active" if sub_id and expires_at and expires_at > int(time.time()) else "expired",
            tg_id,
        ))

        await db.commit()


async def get_user_by_username(username: str):
    username = username.lstrip("@").strip()
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE lower(username) = lower(?) LIMIT 1",
            (username,),
        )
        return await cursor.fetchone()


async def get_broadcast_users(group: str = "all"):
    now = int(time.time())
    conditions = {
        "all": "1 = 1",
        "active": "status IN ('trial', 'paid') AND expires_at IS NOT NULL AND expires_at > ?",
        "trial": "status = 'trial' AND expires_at IS NOT NULL AND expires_at > ?",
        "paid": "status = 'paid' AND expires_at IS NOT NULL AND expires_at > ?",
        "expired": "expires_at IS NOT NULL AND expires_at <= ?",
    }
    condition = conditions.get(group, conditions["all"])
    params = () if group == "all" else (now,)

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            f"""
            SELECT tg_id, username, status, expires_at
            FROM users
            WHERE ({condition})
              AND NOT EXISTS (
                  SELECT 1
                  FROM notification_blocked_users b
                  WHERE b.tg_id = users.tg_id
              )
            ORDER BY tg_id
            """,
            params,
        )
        return await cursor.fetchall()


async def get_promos():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM promo_codes ORDER BY code"
        )
        return await cursor.fetchall()


async def delete_promo(code: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM promo_uses WHERE code = ?", (code,))
        cursor = await db.execute(
            "DELETE FROM promo_codes WHERE code = ?",
            (code,),
        )
        await db.commit()
        return cursor.rowcount == 1


async def get_promo(code: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM promo_codes WHERE code = ?",
            (code,),
        )
        return await cursor.fetchone()


async def create_promo(
    code: str,
    reward_days: int,
    max_uses: int = 0,
    expires_at: int | None = None,
):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT INTO promo_codes (
                code,
                reward_days,
                max_uses,
                used_count,
                expires_at,
                enabled
            )
            VALUES (?, ?, ?, 0, ?, 1)
            """,
            (code, reward_days, max_uses, expires_at),
        )
        await db.commit()


async def use_promo(code: str, tg_id: int, used_at: int) -> bool:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            "SELECT * FROM promo_codes WHERE code = ?",
            (code,),
        )
        promo = await cursor.fetchone()

        if not promo:
            return False

        if not promo["enabled"]:
            return False

        if promo["expires_at"] and promo["expires_at"] < used_at:
            return False

        if promo["max_uses"] > 0 and promo["used_count"] >= promo["max_uses"]:
            return False

        cursor = await db.execute(
            """
            SELECT 1
            FROM promo_uses
            WHERE code = ? AND tg_id = ?
            """,
            (code, tg_id),
        )
        if await cursor.fetchone():
            return False

        await db.execute(
            """
            INSERT INTO promo_uses (code, tg_id, used_at)
            VALUES (?, ?, ?)
            """,
            (code, tg_id, used_at),
        )

        await db.execute(
            """
            UPDATE promo_codes
            SET used_count = used_count + 1
            WHERE code = ?
            """,
            (code,),
        )

        await db.commit()
        return True

async def create_payment(
    payment_id,
    order_id,
    tg_id,
    amount,
    currency,
    days,
    test,
    device_limit=3,
    months=1,
):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO payments (
                payment_id, order_id, tg_id, amount, currency,
                days, test, device_limit, months, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'created', strftime('%s', 'now'))
            """,
            (
                payment_id,
                order_id,
                tg_id,
                amount,
                currency,
                days,
                int(test),
                device_limit,
                months,
            ),
        )
        await db.commit()


async def get_payment(payment_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM payments WHERE payment_id = ?",
            (payment_id,),
        )
        return await cursor.fetchone()


async def update_payment_status(payment_id, status):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            UPDATE payments
            SET status = ?, updated_at = strftime('%s', 'now')
            WHERE payment_id = ?
            """,
            (status, payment_id),
        )
        await db.commit()


async def payment_paid_once(payment_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """
            UPDATE payments
            SET status = 'paid', updated_at = strftime('%s', 'now')
            WHERE payment_id = ? AND status != 'paid'
            """,
            (payment_id,),
        )
        await db.commit()
        return cursor.rowcount == 1


async def delete_user_data(tg_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM promo_uses WHERE tg_id = ?", (tg_id,))
        await db.execute("DELETE FROM payments WHERE tg_id = ?", (tg_id,))
        await db.execute("DELETE FROM users WHERE tg_id = ?", (tg_id,))
        await db.commit()


async def create_referral(referrer_id: int, referred_id: int):
    if referrer_id == referred_id:
        return False
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("BEGIN IMMEDIATE")
        cursor = await db.execute("SELECT 1 FROM referrals WHERE referred_id = ?", (referred_id,))
        if await cursor.fetchone():
            await db.commit()
            return False
        await db.execute("INSERT INTO referrals (referred_id, referrer_id, created_at) VALUES (?, ?, strftime('%s','now'))", (referred_id, referrer_id))
        await db.commit()
        return True

async def register_referral_signup_reward(referrer_id: int, referred_id: int):
    if referrer_id == referred_id:
        return False
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("BEGIN IMMEDIATE")
        cursor = await db.execute("SELECT 1 FROM referrals WHERE referred_id = ? AND referrer_id = ?", (referred_id, referrer_id))
        if not await cursor.fetchone():
            await db.commit()
            return False
        cursor = await db.execute(
            "INSERT OR IGNORE INTO referral_rewards (payment_id, referred_id, referrer_id, reward_days, reward_type, applied, created_at) "
            "VALUES (?, ?, ?, 1, 'signup', 0, strftime('%s','now'))",
            (f"signup:{referred_id}", referred_id, referrer_id),
        )
        inserted = cursor.rowcount == 1
        await db.commit()
        return inserted

async def get_referral_stats(tg_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (tg_id,))
        total = (await cursor.fetchone())[0]
        cursor = await db.execute("SELECT COUNT(DISTINCT referred_id) FROM referral_rewards WHERE referrer_id = ? AND reward_type = 'payment'", (tg_id,))
        paid = (await cursor.fetchone())[0]
        cursor = await db.execute("SELECT COALESCE(SUM(reward_days),0) FROM referral_rewards WHERE referrer_id = ?", (tg_id,))
        earned = (await cursor.fetchone())[0]
        cursor = await db.execute("SELECT COALESCE(SUM(reward_days),0) FROM referral_rewards WHERE referrer_id = ? AND applied = 0", (tg_id,))
        pending = (await cursor.fetchone())[0]
        cursor = await db.execute("SELECT 1 FROM referrals WHERE referred_id = ?", (tg_id,))
        return {"total": total, "paid": paid, "earned_days": earned, "pending_days": pending, "is_referred": await cursor.fetchone() is not None}

async def get_pending_referral_rewards(tg_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT payment_id, reward_days FROM referral_rewards WHERE referrer_id = ? AND applied = 0 ORDER BY created_at",
            (tg_id,),
        )
        return await cursor.fetchall()

async def get_referrer_id(referred_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT referrer_id FROM referrals WHERE referred_id = ?",
            (referred_id,),
        )
        row = await cursor.fetchone()
        return row[0] if row else None

async def register_referral_payment(payment_id: str, referred_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("BEGIN IMMEDIATE")
        cursor = await db.execute("SELECT referrer_id FROM referrals WHERE referred_id = ?", (referred_id,))
        referral = await cursor.fetchone()
        if not referral:
            await db.commit()
            return None
        cursor = await db.execute("SELECT months FROM payments WHERE payment_id = ?", (payment_id,))
        payment = await cursor.fetchone()
        if not payment:
            await db.commit()
            return None
        months = max(1, int(payment["months"] or 1))
        reward_days = months * 5
        cursor = await db.execute(
            "INSERT OR IGNORE INTO referral_rewards (payment_id, referred_id, referrer_id, reward_days, reward_type, applied, created_at) "
            "VALUES (?, ?, ?, ?, 'payment', 0, strftime('%s','now'))",
            (payment_id, referred_id, referral["referrer_id"], reward_days),
        )
        inserted = cursor.rowcount == 1
        await db.commit()
        if not inserted:
            return None
        return {"referrer_id": referral["referrer_id"], "reward_days": reward_days, "months": months}

async def mark_referral_rewards_applied(payment_ids):
    if not payment_ids:
        return
    async with aiosqlite.connect(DATABASE_PATH) as db:
        placeholders = ",".join("?" for _ in payment_ids)
        await db.execute(
            f"UPDATE referral_rewards SET applied = 1 WHERE payment_id IN ({placeholders})",
            tuple(payment_ids),
        )
        await db.commit()


# notifications

async def is_notification_blocked(tg_id: int) -> bool:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT 1 FROM notification_blocked_users WHERE tg_id = ?",
            (tg_id,),
        )
        return await cursor.fetchone() is not None


async def block_notification_user(tg_id: int, username=None) -> bool:
    import time
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("BEGIN IMMEDIATE")

        cursor = await db.execute(
            "SELECT 1 FROM notification_blocked_users WHERE tg_id = ?",
            (tg_id,),
        )
        if await cursor.fetchone() is not None:
            await db.commit()
            return False

        await db.execute(
            """
            INSERT INTO notification_blocked_users
            (tg_id, username, blocked_at)
            VALUES (?, ?, ?)
            """,
            (tg_id, username, int(time.time())),
        )
        await db.commit()
        return True


async def unblock_notification_user(tg_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "DELETE FROM notification_blocked_users WHERE tg_id = ?",
            (tg_id,),
        )
        await db.commit()


async def get_active_users():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE sub_id IS NOT NULL AND expires_at IS NOT NULL AND status IN ('trial', 'paid')"
        )
        return await cursor.fetchall()


async def notification_was_sent(tg_id: int, notification_type: str, marker: str) -> bool:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT 1 FROM notification_log WHERE tg_id = ? AND notification_type = ? AND marker = ?",
            (tg_id, notification_type, str(marker)),
        )
        return await cursor.fetchone() is not None


async def mark_notification_sent(tg_id: int, notification_type: str, marker: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO notification_log (tg_id, notification_type, marker, sent_at) VALUES (?, ?, ?, strftime('%s', 'now'))",
            (tg_id, notification_type, str(marker)),
        )
        await db.commit()


async def get_device_snapshots(tg_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT device_key, device_name, first_seen FROM device_snapshots WHERE tg_id = ?",
            (tg_id,),
        )
        return await cursor.fetchall()


async def save_device_snapshot(tg_id: int, device_key: str, device_name: str, first_seen: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO device_snapshots (tg_id, device_key, device_name, first_seen) VALUES (?, ?, ?, ?)",
            (tg_id, device_key, device_name, first_seen),
        )
        await db.commit()
