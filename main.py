import os
import logging
import asyncio
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TOKEN", "8789453928:AAGlimSktG-zLypM6rMsMwec27_N7wNzDKs")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أهلاً بك! أرسل رابط الفيديو واختر الجودة التي تناسبك.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http"):
        await update.message.reply_text("⚠️ الرجاء إرسال رابط صحيح.")
        return

    msg = await update.message.reply_text("⏳ جاري تحليل الرابط واستخراج الجودات المتاحة...")

    # حفظ الرابط في جلسة المستخدم
    context.user_data['url'] = url

    try:
        ydl_opts = {'quiet': True, 'no_warnings': True}
        loop = asyncio.get_running_loop()
        
        def extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)

        info = await loop.run_in_executor(None, extract)
        title = info.get('title', 'فيديو')[:30]

        # خيارات الجودة المتاحة
        keyboard = [
            [InlineKeyboardButton("🎬 أعلى جودة متاحة (Best)", callback_data="f_best")],
            [InlineKeyboardButton("📺 1080p HD", callback_data="f_1080"), InlineKeyboardButton("📺 720p HD", callback_data="f_720")],
            [InlineKeyboardButton("📱 480p SD", callback_data="f_480"), InlineKeyboardButton("📱 360p SD", callback_data="f_360")],
            [InlineKeyboardButton("🎵 تحميل صوت فقط (Audio)", callback_data="f_audio")]
        ]

        await msg.edit_text(
            f"📹 **{title}**\n\nاختر الجودة المطلوبة للتحميل:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error: {e}")
        await msg.edit_text(f"❌ حدث خطأ أثناء فحص الرابط:\n`{str(e)[:100]}`", parse_mode="Markdown")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    choice = query.data
    url = context.user_data.get('url')

    if not url:
        await query.edit_message_text("❌ انتهت الجلسة، أرسل الرابط مجدداً.")
        return

    await query.edit_message_text("🚀 جاري التحميل فوراً... انتظر لحظات.")
    user_id = query.from_user.id

    # تحديد معايير التنزيل حسب الجودة
    if choice == "f_best":
        fmt = "best[ext=mp4]/best"
        ext = "mp4"
    elif choice == "f_1080":
        fmt = "bestvideo[height<=1080][ext=mp4]+bestaudio/best[height<=1080]"
        ext = "mp4"
    elif choice == "f_720":
        fmt = "bestvideo[height<=720][ext=mp4]+bestaudio/best[height<=720]"
        ext = "mp4"
    elif choice == "f_480":
        fmt = "bestvideo[height<=480][ext=mp4]+bestaudio/best[height<=480]"
        ext = "mp4"
    elif choice == "f_360":
        fmt = "bestvideo[height<=360][ext=mp4]+bestaudio/best[height<=360]"
        ext = "mp4"
    elif choice == "f_audio":
        fmt = "bestaudio/best"
        ext = "m4a"  # صيغة تعمل مباشرة دون الحاجة لـ ffmpeg

    out_file = f"dl_{user_id}.{ext}"

    ydl_opts = {
        'format': fmt,
        'outtmpl': out_file,
        'quiet': True,
        'no_warnings': True,
    }

    try:
        loop = asyncio.get_running_loop()
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        await loop.run_in_executor(None, download)

        # البحث عن الملف الناتج في حال تغيير الامتداد تلقائياً
        actual_file = out_file
        if not os.path.exists(actual_file):
            for file in os.listdir('.'):
                if file.startswith(f"dl_{user_id}"):
                    actual_file = file
                    break

        with open(actual_file, 'rb') as f:
            if choice == "f_audio":
                await context.bot.send_audio(chat_id=query.message.chat_id, audio=f)
            else:
                await context.bot.send_video(chat_id=query.message.chat_id, video=f, supports_streaming=True)

        await query.message.delete()

    except Exception as e:
        logger.error(f"Download Error: {e}")
        await query.edit_message_text(f"❌ حدث خطأ أثناء التحميل:\n`{str(e)[:100]}`", parse_mode="Markdown")

    finally:
        # تنظيف أي ملفات مؤقتة
        for file in os.listdir('.'):
            if file.startswith(f"dl_{user_id}"):
                try:
                    os.remove(file)
                except Exception:
                    pass

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("Bot Started...")
    app.run_polling()

if __name__ == "__main__":
    main()
