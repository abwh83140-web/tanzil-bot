import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from yt_dlp import YoutubeDL

# التوكن الخاص بك
TOKEN = os.environ.get("TOKEN", "8789453928:AAGlimSktG-zLypM6rMsMwec27_N7wNzDKs")

YDL_OPTIONS_INFO = {
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أهلاً بك! أرسل لي رابط الفيديو وسأقوم باستخراج الجودات المتاحة لتحميله بأقصى سرعة.")

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith(("http://", "https://")):
        return

    msg = await update.message.reply_text("⚡ جاري فحص الرابط واستخراج الصيغ المتاحة...")

    try:
        loop = asyncio.get_running_loop()
        with YoutubeDL(YDL_OPTIONS_INFO) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))

        formats = info.get('formats', [])
        title = info.get('title', 'Video')
        
        keyboard = []
        seen_qualities = set()

        for f in formats:
            height = f.get('height')
            ext = f.get('ext')
            format_id = f.get('format_id')
            
            if height and height not in seen_qualities and ext == 'mp4':
                seen_qualities.add(height)
                button_text = f"🎬 {height}p (MP4)"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"{format_id}|{url}")])

        keyboard.append([InlineKeyboardButton("🎵 تحميل صوت فقط (MP3)", callback_data=f"audio|{url}")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await msg.edit_text(f"🎥 **{title}**\n\nاختر الجودة أو الصيغة المطلوبة للتحميل:", reply_markup=reply_markup, parse_mode="Markdown")

    except Exception as e:
        await msg.edit_text(f"❌ حدث خطأ أثناء فحص الرابط:\n`{str(e)}`", parse_mode="Markdown")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    format_id, url = query.data.split("|")
    await query.edit_message_text("⚡ جاري التحميل بأقصى سرعة...")

    os.makedirs("downloads", exist_ok=True)
    file_path = None

    try:
        loop = asyncio.get_running_loop()
        
        if format_id == "audio":
            dl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': 'downloads/%(title)s.%(ext)s',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'concurrent_fragment_downloads': 10,
            }
        else:
            dl_opts = {
                'format': f"{format_id}+bestaudio/best",
                'outtmpl': 'downloads/%(title)s.%(ext)s',
                'merge_output_format': 'mp4',
                'concurrent_fragment_downloads': 10,
            }

        def download():
            with YoutubeDL(dl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)

        file_path = await loop.run_in_executor(None, download)

        if not os.path.exists(file_path):
            base_name = os.path.splitext(file_path)[0]
            if os.path.exists(f"{base_name}.mp4"):
                file_path = f"{base_name}.mp4"

        await query.edit_message_text("🚀 جاري رفع الملف إلى تلجرام...")
        
        with open(file_path, 'rb') as file:
            if format_id == "audio":
                await query.message.reply_audio(audio=file)
            else:
                await query.message.reply_video(video=file)

        await query.delete_message()

    except Exception as e:
        await query.edit_message_text(f"❌ فشل التحميل:\n`{str(e)}`", parse_mode="Markdown")
    
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    print("البوت يعمل الآن...")
    app.run_polling()
