import os
import re
import logging
import tempfile

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import yt_dlp

BOT_TOKEN = os.environ.get("BOT_TOKEN", "PUT_YOUR_TOKEN_HERE")
MAX_FILE_SIZE_MB = 50

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

URL_REGEX = re.compile(r"https?://\S+")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "أهلاً! أرسل لي رابط فيديو من تيك توك أو يوتيوب أو تويتر/X "
        "وسأقوم بتحميله وإرساله لك.\n\n"
        "⚠️ تنويه: أنت مسؤول عن استخدام المحتوى وفق حقوق صاحبه. "
        "هذا البوت لأغراض شخصية فقط."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "فقط أرسل رابط الفيديو مباشرة، ولا تحتاج أي أمر إضافي."
    )


def download_video(url: str, out_dir: str) -> str:
    output_template = os.path.join(out_dir, "%(id)s.%(ext)s")

    ydl_opts = {
        "outtmpl": output_template,
        "format": "mp4/best[ext=mp4]/best",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "max_filesize": MAX_FILE_SIZE_MB * 1024 * 1024,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        return filename


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    match = URL_REGEX.search(text)

    if not match:
        await update.message.reply_text("من فضلك أرسل رابط فيديو صالح.")
        return

    url = match.group(0)
    status_msg = await update.message.reply_text("⏳ جاري تحميل الفيديو...")

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = download_video(url, tmp_dir)

            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if file_size_mb > MAX_FILE_SIZE_MB:
                await status_msg.edit_text(
                    f"⚠️ حجم الفيديو ({file_size_mb:.1f} MB) أكبر من الحد "
                    f"المسموح ({MAX_FILE_SIZE_MB} MB)."
                )
                return

            with open(file_path, "rb") as video_file:
                await update.message.reply_video(video=video_file)

            await status_msg.delete()

    except yt_dlp.utils.DownloadError as e:
        logger.error(f"Download error: {e}")
        await status_msg.edit_text(
            "❌ تعذر تحميل الفيديو. تأكد أن الرابط صحيح والمنصة مدعومة."
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        await status_msg.edit_text("❌ حدث خطأ غير متوقع، حاول مرة أخرى.")


def main():
    if BOT_TOKEN == "PUT_YOUR_TOKEN_HERE":
        raise SystemExit(
            "يجب ضبط متغير البيئة BOT_TOKEN بتوكن البوت الذي حصلت عليه من BotFather."
        )

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    logger.info("Bot started.")
    application.run_polling()


if __name__ == "__main__":
    main()
