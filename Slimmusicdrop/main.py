import os
from pathlib import Path
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# --- 🔹 Отримуємо токен з середовища ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TELEGRAM_TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN не знайдено! ➕ Додай змінну в Railway Variables або .env файл.")

# --- 📂 Папка для завантажень ---
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

# --- Команда /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open("images/background.jpg", "rb") as photo:
            await update.message.reply_photo(
                photo=photo,
                caption="🎵 Привіт! Напиши назву треку або посилання з YouTube Music, щоб отримати аудіо."
            )
    except FileNotFoundError:
        await update.message.reply_text("🎵 Привіт! Напиши назву треку або посилання з YouTube Music, щоб отримати аудіо.")

# --- Завантаження треку ---
async def search_youtube_music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    if not query:
        await update.message.reply_text("❌ Вкажи запит або посилання.")
        return

    await update.message.reply_text("⏳ Шукаю і завантажую аудіо з YouTube Music...")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(DOWNLOAD_DIR / "%(id)s.%(ext)s"),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "keepvideo": False,
        "quiet": True,
        "max_filesize": 1000 * 1024 * 1024,
        "user_agent": "Mozilla/5.0"
    }

    try:
        if not query.startswith("http"):
            query = f"ytsearch1:{query}"

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(query, download=True)
            entries = info_dict["entries"] if "entries" in info_dict else [info_dict]

            for entry in entries:
                file_path = Path(ydl.prepare_filename(entry)).with_suffix(".mp3")
                if file_path.exists():
                    with open(file_path, "rb") as audio_file:
                        await update.message.reply_audio(
                            audio=audio_file,
                            title=entry.get("title", "Audio"),
                            performer=entry.get("uploader", None)
                        )
                    file_path.unlink(missing_ok=True)
                else:
                    await update.message.reply_text("❌ Не вдалося знайти аудіофайл.")

    except Exception as e:
        await update.message.reply_text("❌ Сталася помилка при завантаженні.")
        print(f"Error: {e}")

# --- Запуск бота ---
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_youtube_music))
    app.run_polling()

if __name__ == "__main__":
    main()
