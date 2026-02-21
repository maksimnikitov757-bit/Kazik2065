import os
import random
import sqlite3
import threading
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

TOKEN = os.getenv("TOKEN")
CHANNEL_USERNAME = "@Kazik2065"

# ---------- БАЗА ----------
conn = sqlite3.connect("kazik.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    balance INTEGER DEFAULT 0,
    verified INTEGER DEFAULT 0
)
""")
conn.commit()

# ---------- КАРТЫ ----------
cards = [
    ("Владимир колесников", "обычный", 50, 50),
    ("Соня бум", "редкий", 100, 25),
    ("гор и марго", "эпический", 300, 15),
    ("соц педагог", "легендарный", 1000, 9),
    ("урсегов", "мифический", 5000, 1),
]

# ---------- МЕНЮ ----------
def main_menu():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🎴 Открыть")],
            [KeyboardButton("👤 Профиль"), KeyboardButton("🏆 Топ")]
        ],
        resize_keyboard=True
    )

def verify_menu():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📢 Подписаться")],
            [KeyboardButton("✅ Проверить подписку")]
        ],
        resize_keyboard=True
    )

# ---------- ПРОВЕРКА ПОДПИСКИ ----------
async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user.id)
        if member.status in ["member", "administrator", "creator"]:
            cursor.execute("UPDATE users SET verified=1 WHERE user_id=?", (user.id,))
            conn.commit()
            await update.message.reply_text(
                "✅ Верификация пройдена!\n\nДобро пожаловать в Казик 2065!",
                reply_markup=main_menu()
            )
        else:
            await update.message.reply_text("❌ Ты не подписан на канал.")
    except:
        await update.message.reply_text("Ошибка проверки. Попробуй позже.")

# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?,?)",
                   (user.id, user.username))
    conn.commit()

    cursor.execute("SELECT verified FROM users WHERE user_id=?", (user.id,))
    verified = cursor.fetchone()[0]

    if verified == 1:
        await update.message.reply_text(
            "Добро пожаловать в Казик 2065 👑",
            reply_markup=main_menu()
        )
    else:
        await update.message.reply_text(
            "Чтобы пользоваться ботом, подпишись на канал.",
            reply_markup=verify_menu()
        )

# ---------- ОТКРЫТИЕ ----------
async def open_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    cursor.execute("SELECT verified FROM users WHERE user_id=?", (user.id,))
    verified = cursor.fetchone()[0]

    if verified == 0:
        await update.message.reply_text("Сначала подпишись.", reply_markup=verify_menu())
        return

    weights = [c[3] for c in cards]
    chosen = random.choices(cards, weights=weights)[0]
    name, rarity, value, _ = chosen

    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?",
                   (value, user.id))
    conn.commit()

    await update.message.reply_text(
        f"🎴 Ты выбил:\n\n{name}\nРедкость: {rarity}\nСтоимость: {value}₽",
        reply_markup=main_menu()
    )

# ---------- ПРОФИЛЬ ----------
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user.id,))
    balance = cursor.fetchone()[0]

    await update.message.reply_text(
        f"👤 @{user.username}\nБаланс: {balance}₽",
        reply_markup=main_menu()
    )

# ---------- ТОП ----------
async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("SELECT username, balance FROM users ORDER BY balance DESC LIMIT 10")
    rows = cursor.fetchall()

    text = "🏆 Топ игроков:\n\n"
    for i, row in enumerate(rows, 1):
        username, balance = row
        text += f"{i}. @{username} — {balance}₽\n"

    await update.message.reply_text(text, reply_markup=main_menu())

# ---------- ОБРАБОТКА ----------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🎴 Открыть":
        await open_card(update, context)
    elif text == "👤 Профиль":
        await profile(update, context)
    elif text == "🏆 Топ":
        await top(update, context)
    elif text == "📢 Подписаться":
        await update.message.reply_text(f"Подпишись на {CHANNEL_USERNAME}")
    elif text == "✅ Проверить подписку":
        await check_subscription(update, context)

# ---------- FLASK ДЛЯ RENDER ----------
app = Flask(__name__)

@app.route("/")
def home():
    return "Kazik 2065 работает!"

def run_bot():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
