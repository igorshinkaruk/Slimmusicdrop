import os
import yt_dlp
import json
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if TELEGRAM_TOKEN is None:
    raise ValueError("Змінна TELEGRAM_TOKEN не встановлена! Додайте її у Railway Environment Variables.")

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

USAGE_FILE = "usage.json"
SUBSCRIPTION_URL = "https://your-subscription-link.com"  # заміни на своє посилання

def load_usage():
    if os.path.exists(USAGE_FILE):
        with open(USAGE_FILE, "r") as f:
            return json.load(f)
    return {"plays": 0}

def save_usage(data):
    with open(USAGE_FILE, "w") as f:
        json.dump(data, f)

def check_subscription():
    usage = load_usage()
    return usage["plays"] < 5

def increase_usage():
    usage = load_usage()
    usage["plays"] += 1
    save_usage(usage)

# --- Команда /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Купити підписку 💳", url=SUBSCRIPTION_URL)]]

    if not check_subscription():
        await update.message.reply_text(
            "❌ Ліміт 5 прослуховувань вичерпано. Купіть підписку.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    try:
        with open("images/background.jpg", "rb") as photo:
            await update.message.reply_photo(
                photo=photo,
                caption="🎵 Привіт! Напиши назву треку або посилання з YouTube Music, щоб отримати аудіо.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    except FileNotFoundError:
        await update.message.reply_text(
            "🎵 Привіт! Напиши назву треку або посилання з YouTube Music, щоб отримати аудіо.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# --- Логіка пошуку та завантаження ---
async def search_youtube_music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Купити підписку 💳", url=SUBSCRIPTION_URL)]]

    if not check_subscription():
        await update.message.reply_text(
            "❌ Ліміт 5 прослуховувань вичерпано. Купіть підписку.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    increase_usage()

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
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    try:
        if not query.startswith("http"):
            query = f"ytsearch1:{query}"

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(query, download=True)
            entries = info_dict["entries"] if "entries" in info_dict and info_dict["entries"] else [info_dict]

            for entry in entries:
                file_path = None
                if "requested_downloads" in entry:
                    file_path = entry["requested_downloads"][0]["filepath"]
                elif "filepath" in entry:
                    file_path = entry["filepath"]
                elif "_filename" in entry:
                    file_path = str(Path(entry["_filename"]).with_suffix(".mp3"))

                if file_path and Path(file_path).exists():
                    if Path(file_path).stat().st_size > 50 * 1024 * 1024:
                        yt_url = entry.get("webpage_url", "")
                        await update.message.reply_text(
                            f"❌ Файл занадто великий для Telegram (>50 МБ).\n"
                            f"🔗 [Відкрити на YouTube]({yt_url})" if yt_url else "🔗 Скачайте напряму з YouTube.",
                            parse_mode="Markdown",
                            disable_web_page_preview=True
                        )
                        Path(file_path).unlink(missing_ok=True)
                        continue

                    thumbnail_url = entry.get("thumbnail")
                    if thumbnail_url:
                        try:
                            await update.message.reply_photo(
                                photo=thumbnail_url,
                                caption=f"{entry.get('title', 'Audio')}\nВиконавець: {entry.get('uploader', '')}"
                            )
                        except Exception:
                            pass

                    with open(file_path, "rb") as audio_file:
                        await update.message.reply_audio(
                            audio=audio_file,
                            title=entry.get("title", "Audio"),
                            performer=entry.get("uploader", None)
                        )
                    Path(file_path).unlink(missing_ok=True)
                else:
                    await update.message.reply_text("❌ Не вдалося знайти аудіофайл.")

                info_text = (
                    f"🎵 <b>{entry.get('title', 'Audio')}</b>\n"
                    f"👤 Виконавець: {entry.get('uploader', '')}\n"
                    f"⏱️ Тривалість: {entry.get('duration', '')} сек\n"
                    f"👁️ Переглядів: {entry.get('view_count', '')}\n"
                    f"👍 Лайків: {entry.get('like_count', '')}\n"
                    f"🎶 Жанр: {entry.get('genre', '')}\n"
                    f"📀 Альбом: {entry.get('album', '')}\n"
                    f"📅 Рік випуску: {entry.get('release_year', '')}\n"
                    f"📝 Опис: {entry.get('description', '')[:200]}..."
                )
                await update.message.reply_text(info_text, parse_mode="HTML")

                yt_url = entry.get("webpage_url", "")
                if yt_url:
                    keyboard_video = [[InlineKeyboardButton("Відкрити на YouTube ▶️", url=yt_url)]]
                    await update.message.reply_text("🔗 Перейти до відео:", reply_markup=InlineKeyboardMarkup(keyboard_video))

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