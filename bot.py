import os
import uuid
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

import os
TOKEN = os.environ.get("BOT_TOKEN")
BASE_DOWNLOAD_FOLDER = "downloads"
os.makedirs(BASE_DOWNLOAD_FOLDER, exist_ok=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("دز رابط الفيديو 👇")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    context.user_data["url"] = url

    keyboard = [
        [
            InlineKeyboardButton("🎥 720p", callback_data="720"),
            InlineKeyboardButton("🎥 480p", callback_data="480"),
        ],
        [
            InlineKeyboardButton("🔥 أفضل جودة", callback_data="best"),
        ],
        [
            InlineKeyboardButton("🎵 MP3", callback_data="mp3"),
        ],
    ]

    await update.message.reply_text(
        "اختر النوع:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    choice = query.data
    url = context.user_data.get("url")

    if not url:
        return

    await query.message.delete()
    loading_msg = await query.message.chat.send_message("⏳ جاري التحميل...")

    try:
        # ================= MP3 =================
        if choice == "mp3":
            unique_id = str(uuid.uuid4())
            output_template = os.path.join(
                BASE_DOWNLOAD_FOLDER, f"{unique_id}.%(ext)s"
            )

            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": output_template,
                "noplaylist": False,
                "writethumbnail": True,
                "embedthumbnail": True,
                "addmetadata": True,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    },
                    {"key": "FFmpegMetadata"},
                    {"key": "EmbedThumbnail"},
                ],
                "quiet": True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

                # ================= Playlist =================
                if "entries" in info:
                    playlist_title = info.get("title", "Playlist")
                    safe_folder = os.path.join(
                        BASE_DOWNLOAD_FOLDER,
                        playlist_title.replace("/", "_"),
                    )
                    os.makedirs(safe_folder, exist_ok=True)

                    total = len(info["entries"])
                    count = 1

                    for entry in info["entries"]:
                        if entry is None:
                            continue

                        file_path = os.path.splitext(
                            ydl.prepare_filename(entry)
                        )[0] + ".mp3"

                        # نقل الملف إلى فولدر البلاي ليست
                        new_path = os.path.join(
                            safe_folder,
                            os.path.basename(file_path),
                        )
                        os.rename(file_path, new_path)

                        file_size = os.path.getsize(new_path) / (1024 * 1024)

                        if file_size <= 49:
                            await query.message.chat.send_audio(
                                audio=open(new_path, "rb"),
                                title=entry.get("title"),
                                performer=entry.get("uploader"),
                                caption=f"🎵 {count}/{total}\n📀 {playlist_title}",
                            )

                        os.remove(new_path)
                        count += 1

                    await loading_msg.delete()
                    return

                # ================= ملف واحد =================
                file_path = os.path.splitext(
                    ydl.prepare_filename(info)
                )[0] + ".mp3"

            file_size = os.path.getsize(file_path) / (1024 * 1024)
            await loading_msg.delete()

            if file_size > 49:
                await query.message.chat.send_message("❌ الملف أكبر من 50MB")
                os.remove(file_path)
                return

            await query.message.chat.send_audio(
                audio=open(file_path, "rb"),
                title=info.get("title"),
                performer=info.get("uploader"),
                caption=f"📀 {info.get('uploader')}\n📅 {info.get('upload_date', '')[:4]}",
            )

            os.remove(file_path)
            return

        # ================= فيديو =================
        unique_id = str(uuid.uuid4())
        output_template = os.path.join(
            BASE_DOWNLOAD_FOLDER, f"{unique_id}.%(ext)s"
        )

        if choice == "720":
            format_code = "bestvideo[height<=720]+bestaudio/best[height<=720]"
        elif choice == "480":
            format_code = "bestvideo[height<=480]+bestaudio/best[height<=480]"
        else:
            format_code = "bestvideo+bestaudio/best"

        ydl_opts = {
            "format": format_code,
            "outtmpl": output_template,
            "merge_output_format": "mp4",
            "noplaylist": False,
            "quiet": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            if "entries" in info:
                total = len(info["entries"])
                count = 1

                for entry in info["entries"]:
                    if entry is None:
                        continue

                    file_path = ydl.prepare_filename(entry)

                    if not os.path.exists(file_path):
                        file_path = os.path.splitext(file_path)[0] + ".mp4"

                    file_size = os.path.getsize(file_path) / (1024 * 1024)

                    if file_size <= 49:
                        await query.message.chat.send_video(
                            video=open(file_path, "rb"),
                            caption=f"📂 {count}/{total}",
                        )

                    os.remove(file_path)
                    count += 1

                await loading_msg.delete()
                return

            file_path = ydl.prepare_filename(info)

            if not os.path.exists(file_path):
                file_path = os.path.splitext(file_path)[0] + ".mp4"

        file_size = os.path.getsize(file_path) / (1024 * 1024)
        await loading_msg.delete()

        if file_size > 49:
            await query.message.chat.send_message("❌ الفيديو أكبر من 50MB")
            os.remove(file_path)
            return

        await query.message.chat.send_video(video=open(file_path, "rb"))
        os.remove(file_path)

    except Exception as e:
        await loading_msg.delete()
        await query.message.chat.send_message(f"❌ خطأ:\n{e}")


if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Bot is running...")
    app.run_polling()
