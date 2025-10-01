import logging
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ContextTypes

# --- Конфіг ---
TELEGRAM_TOKEN = "YOUR_TOKEN_HERE"
ADMIN_ID = 5759462723  # заміни на свій Telegram ID
USAGE_FILE = "usage.json"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Робота з лімітом ---
def load_usage():
    if not os.path.exists(USAGE_FILE):
        return {"plays": 0}
    with open(USAGE_FILE, "r") as f:
        return json.load(f)

def save_usage(usage):
    with open(USAGE_FILE, "w") as f:
        json.dump(usage, f)

def increase_usage():
    usage = load_usage()
    usage["plays"] += 1
    save_usage(usage)
    return usage["plays"]

def get_remaining():
    usage = load_usage()
    return max(0, 5 - usage["plays"])

# --- Хендлери ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    remaining = get_remaining()
    if remaining > 0:
        await update.message.reply_text(
            f"👋 Вітаю! У вас залишилось {remaining} з 5 безкоштовних прослуховувань.\n"
            "Введіть назву треку, щоб знайти його."
        )
    else:
        keyboard = [[InlineKeyboardButton("Купити підписку 💳", url="https://example.com/payment")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🚫 Ліміт у 5 прослуховувань вичерпано. Купіть підписку, щоб слухати далі.",
            reply_markup=reply_markup
        )

async def search_youtube_music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usage = load_usage()
    if usage["plays"] >= 5:
        keyboard = [[InlineKeyboardButton("Купити підписку 💳", url="https://example.com/payment")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🚫 Ви використали всі 5 безкоштовних прослуховувань. Купіть підписку для доступу.",
            reply_markup=reply_markup
        )
        return

    # тут вставляєш логіку пошуку/завантаження музики
    # поки що просто текст:
    query = update.message.text
    await update.message.reply_text(f"🎵 Знаходжу трек: {query} ...")

    # Збільшуємо лічильник
    increase_usage()
    remaining = get_remaining()
    await update.message.reply_text(f"✅ Запит прийнято. Залишилось {remaining} з 5 прослуховувань.")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ У вас немає доступу до цієї команди.")
        return

    usage = {"plays": 0}
    save_usage(usage)
    remaining = get_remaining()
    await update.message.reply_text(
        f"✅ Лічильник скинуто. У вас тепер {remaining} з 5 безкоштовних прослуховувань."
    )

# --- Запуск ---
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_youtube_music))

    app.run_polling()

if __name__ == "__main__":
    main()