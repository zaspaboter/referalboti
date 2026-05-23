import asyncio
import aiosqlite

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder

# =====================
# CONFIG
# =====================
TOKEN = "8720538642:AAEm4Pz4_4IvLEqOol-B1h8Fcu9WLqVJCVo"
ADMIN_ID = 7747726585

CHANNEL_LINK = "https://t.me/+j-9uREtQcsUxZmJi"
CHANNEL_ID = -1003979305317

bot = Bot(token=TOKEN)
dp = Dispatcher()

COIN = "🪙"

# =====================
# SHOP
# =====================
SHOP = {
    "Мишка": 2,
    "Сердце": 2,
    "Роза": 4,
    "Подарок": 4,
    "Тортик": 7,
    "Букет": 7,
    "Ракета": 7,
    "Кубок": 14,
    "Бриллиант": 14,
    "NFT": 27
}

# =====================
# DB
# =====================
async def init_db():
    async with aiosqlite.connect("db.sqlite3") as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            coins INTEGER DEFAULT 0,
            referrals INTEGER DEFAULT 0,
            ref_by INTEGER
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            item TEXT,
            price INTEGER
        )
        """)

        await db.commit()

# =====================
# USERS
# =====================
async def get_user(uid):
    async with aiosqlite.connect("db.sqlite3") as db:
        cur = await db.execute("SELECT * FROM users WHERE user_id=?", (uid,))
        return await cur.fetchone()

async def create_user(uid, username, ref=None):
    async with aiosqlite.connect("db.sqlite3") as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, ref_by) VALUES (?,?,?)",
            (uid, username, ref)
        )

        if ref and ref != uid:
            await db.execute(
                "UPDATE users SET coins = coins + 1, referrals = referrals + 1 WHERE user_id=?",
                (ref,)
            )

        await db.commit()

async def get_profile(uid):
    async with aiosqlite.connect("db.sqlite3") as db:
        cur = await db.execute(
            "SELECT coins, referrals FROM users WHERE user_id=?",
            (uid,)
        )
        return await cur.fetchone()

async def update_coins(uid, amount):
    async with aiosqlite.connect("db.sqlite3") as db:
        await db.execute(
            "UPDATE users SET coins = coins + ? WHERE user_id=?",
            (amount, uid)
        )
        await db.commit()

# =====================
# LOG PURCHASE
# =====================
async def log_purchase(uid, username, item, price):
    async with aiosqlite.connect("db.sqlite3") as db:
        await db.execute(
            "INSERT INTO purchases (user_id, username, item, price) VALUES (?,?,?,?)",
            (uid, username, item, price)
        )
        await db.commit()

# =====================
# TOP
# =====================
async def top_users():
    async with aiosqlite.connect("db.sqlite3") as db:
        cur = await db.execute(
            "SELECT username, referrals FROM users ORDER BY referrals DESC"
        )
        return await cur.fetchall()

# =====================
# SUB CHECK
# =====================
async def check_sub(uid):
    try:
        m = await bot.get_chat_member(CHANNEL_ID, uid)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False

# =====================
# MENU
# =====================
def menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="👤 Профиль", callback_data="profile")
    kb.button(text="👥 Рефералы", callback_data="refs")
    kb.button(text="🎁 Магазин", callback_data="shop")
    kb.button(text="🏆 Топ", callback_data="top")
    kb.button(text="👑 Админ", callback_data="admin")
    kb.button(text="📢 Канал", url=CHANNEL_LINK)
    kb.adjust(2)
    return kb.as_markup()

# =====================
# START + SUB
# =====================
@dp.message(CommandStart())
async def start(m: Message):
    args = m.text.split()
    ref = int(args[1]) if len(args) > 1 and args[1].isdigit() else None

    if not await get_user(m.from_user.id):
        await create_user(m.from_user.id, m.from_user.username, ref)

    if not await check_sub(m.from_user.id):
        kb = InlineKeyboardBuilder()
        kb.button(text="📢 Подписаться", url=CHANNEL_LINK)
        kb.button(text="✅ Проверить подписку", callback_data="check_sub")
        kb.adjust(1)

        await m.answer("❗ Подпишись на канал", reply_markup=kb.as_markup())
        return

    await m.answer("🏠 Меню", reply_markup=menu())

# =====================
# CHECK SUB
# =====================
@dp.callback_query(F.data == "check_sub")
async def check_sub_btn(c: CallbackQuery):
    if await check_sub(c.from_user.id):
        await c.message.edit_text("✅ Подписка подтверждена", reply_markup=menu())
    else:
        await c.answer("❌ Ты не подписан", show_alert=True)

# =====================
# PROFILE
# =====================
@dp.callback_query(F.data == "profile")
async def profile(c: CallbackQuery):
    coins, refs = await get_profile(c.from_user.id)

    await c.message.edit_text(
        f"👤 ПРОФИЛЬ\n\n💰 Монеты: {coins} {COIN}\n👥 Рефералы: {refs}",
        reply_markup=menu()
    )

# =====================
# REFS
# =====================
@dp.callback_query(F.data == "refs")
async def refs(c: CallbackQuery):
    username = (await bot.get_me()).username
    link = f"https://t.me/{username}?start={c.from_user.id}"

    await c.message.edit_text(
        f"👥 РЕФЕРАЛКА\n\n🔗 {link}\n💰 +1 {COIN}",
        reply_markup=menu()
    )

# =====================
# SHOP
# =====================
@dp.callback_query(F.data == "shop")
async def shop(c: CallbackQuery):
    kb = InlineKeyboardBuilder()
    text = "🎁 МАГАЗИН\n\n"

    for name, price in SHOP.items():
        text += f"{name} — {price} {COIN}\n"
        kb.button(text=f"Купить {name} — {price}🪙", callback_data=f"buy|{name}")

    kb.button(text="⬅️ Назад", callback_data="back")
    kb.adjust(1)

    await c.message.edit_text(text, reply_markup=kb.as_markup())

# =====================
# BUY + NOTIFY USER + ADMIN
# =====================
@dp.callback_query(F.data.startswith("buy|"))
async def buy(c: CallbackQuery):
    name = c.data.split("|")[1]
    price = SHOP[name]

    async with aiosqlite.connect("db.sqlite3") as db:
        cur = await db.execute("SELECT coins FROM users WHERE user_id=?", (c.from_user.id,))
        coins = (await cur.fetchone())[0]

        if coins < price:
            await c.answer("❌ Нет монет", show_alert=True)
            return

        await db.execute(
            "UPDATE users SET coins = coins - ? WHERE user_id=?",
            (price, c.from_user.id)
        )
        await db.commit()

    # лог покупки
    await log_purchase(c.from_user.id, c.from_user.username, name, price)

    # пользователю
    await c.message.edit_text("⏳ Ваш заказ взят в обработку", reply_markup=menu())

    # админу
    await bot.send_message(
        ADMIN_ID,
        f"🛒 НОВЫЙ ЗАКАЗ\n\n"
        f"👤 Юзер: @{c.from_user.username}\n"
        f"🆔 ID: {c.from_user.id}\n"
        f"📦 Товар: {name}\n"
        f"💰 Цена: {price} {COIN}"
    )

# =====================
# TOP
# =====================
@dp.callback_query(F.data == "top")
async def top(c: CallbackQuery):
    users = await top_users()

    text = "🏆 ТОП\n\n"

    for i, u in enumerate(users[:25], 1):
        text += f"{i}. @{u[0]} — {u[1]}\n"

    await c.message.edit_text(text, reply_markup=menu())

# =====================
# ADMIN PANEL
# =====================
@dp.callback_query(F.data == "admin")
async def admin(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return

    kb = InlineKeyboardBuilder()
    kb.button(text="👥 Пользователи", callback_data="a_users")
    kb.button(text="🛒 Покупки", callback_data="a_purchases")
    kb.button(text="➕ Выдать монеты", callback_data="a_give")
    kb.adjust(1)

    await c.message.edit_text("👑 АДМИН ПАНЕЛЬ", reply_markup=kb.as_markup())

# =====================
# USERS
# =====================
@dp.callback_query(F.data == "a_users")
async def users(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return

    async with aiosqlite.connect("db.sqlite3") as db:
        cur = await db.execute("SELECT user_id, username, coins FROM users")
        data = await cur.fetchall()

    text = "👥 USERS\n\n"
    for u in data:
        text += f"{u[0]} | @{u[1]} | {u[2]}🪙\n"

    await c.message.edit_text(text)

# =====================
# PURCHASES
# =====================
@dp.callback_query(F.data == "a_purchases")
async def purchases(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return

    async with aiosqlite.connect("db.sqlite3") as db:
        cur = await db.execute("SELECT username,item,price FROM purchases ORDER BY id DESC LIMIT 20")
        data = await cur.fetchall()

    text = "🛒 ПОКУПКИ\n\n"
    for p in data:
        text += f"@{p[0]} купил {p[1]} за {p[2]}🪙\n"

    await c.message.edit_text(text)

# =====================
# GIVE COINS
# =====================
@dp.callback_query(F.data == "a_give")
async def give_hint(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return

    await c.message.answer("Напиши: /give USER_ID SUM")

@dp.message(lambda m: m.text.startswith("/give"))
async def give(m: Message):
    if m.from_user.id != ADMIN_ID:
        return

    _, uid, amount = m.text.split()
    await update_coins(int(uid), int(amount))

    await m.answer("✅ Выдано")

# =====================
# BACK
# =====================
@dp.callback_query(F.data == "back")
async def back(c: CallbackQuery):
    await c.message.edit_text("🏠 МЕНЮ", reply_markup=menu())

# =====================
# RUN
# =====================
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
