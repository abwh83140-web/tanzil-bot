import os
import logging
import asyncio
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# إعداد السجلات (Logging)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# جلب التوكن من المتغيرات أو استخدام التوكن المباشر
TOKEN = os.environ.get("TOKEN", "8789453928:AAGlimSktG-zLypM6rMsMwec27_N7wNzDKs")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أهلاً بك في بوت التحميل السريع!\nأرسل لي أي رابط فيديو (فيسبوك، تيك توك، يوتيوب...) وسأقوم بتحميله فوراً.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http"):
        await update.message.reply_text("⚠️ الرجاء إرسال رابط صحيح يبدأ بـ http أو https.")
        return

    msg = await update.message.reply_text("⏳ جاري فحص الرابط وجلب الجودات المتاحة...")

    # حفظ الرابط في جلسة المستخدم لمنع خطأ Button_data_invalid
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
            [InlineKeyboardButton("🎬 أعلى جودة (Best)", callback_data="f_best")],
            [InlineKeyboardButton("📺 1080p", callback_data="f_1080"), InlineKeyboardButton("📺 720p", callback_data="f_720")],
            [InlineKeyboardButton("📱 480p", callback_data="f_480"), InlineKeyboardButton("📱 360p", callback_data="f_360")],
            [InlineKeyboardButton("🎵 تحميل صوت فقط (Audio)", callback_data="f_audio")]
        ]

        await msg.edit_text(
            f"📹 **{title}**\n\nاختر الجودة المطلوبة للتحميل:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error extracting info: {e}")
        await msg.edit_text(f"❌ حدث خطأ أثناء فحص الرابط:\n`{str(e)[:100]}`", parse_mode="Markdown")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    choice = query.data
    url = context.user_data.get('url')

    if not url:
        await query.edit_message_text("❌ انتهت الجلسة، أرسل الرابط مجدداً.")
        return

    await query.edit_message_text("🚀 جاري التحميل والمعالجة فوراً... انتظر لحظات.")
    user_id = query.from_user.id

    # معايير التحميل المرنة لجميع المنصات (Facebook / TikTok / YouTube)
    if choice == "f_best":
        fmt = "b/best"
        ext = "mp4"
    elif choice == "f_1080":
        fmt = "bv*[height<=1080]+ba/b[height<=1080]/b"
        ext = "mp4"
    elif choice == "f_720":
        fmt = "bv*[height<=720]+ba/b[height<=720]/b"
        ext = "mp4"
    elif choice == "f_480":
        fmt = "bv*[height<=480]+ba/b[height<=480]/b"
        ext = "mp4"
    elif choice == "f_360":
        fmt = "bv*[height<=360]+ba/b[height<=360]/b"
        ext = "mp4"
    elif choice == "f_audio":
        fmt = "ba/b"
        ext = "m4a"

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
        # تنظيف أية ملفات مؤقتة فوراً للحفاظ على مساحة السيرفر
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
