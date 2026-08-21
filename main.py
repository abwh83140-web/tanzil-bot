import os
import logging
import asyncio
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# إعداد السجلات (Logging)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# جلب التوكن من المتغيرات أو التوكن المباشر
TOKEN = os.environ.get("TOKEN", "8789453928:AAGlimSktG-zLypM6rMsMwec27_N7wNzDKs")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أهلاً بك! أرسل لي أي رابط فيديو (تيك توك، يوتيوب، فيسبوك...) وسأقوم بتحميله لك بأعلى سرعة.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http"):
        await update.message.reply_text("⚠️ الرجاء إرسال رابط صحيح يبدأ بـ http أو https.")
        return

    msg = await update.message.reply_text("⏳ جاري فحص الرابط وجلب البيانات...")

    # حفظ الرابط في ذاكرة المستخدم لمنع خطأ Button_data_invalid
    context.user_data['url'] = url

    try:
        ydl_opts = {'quiet': True, 'no_warnings': True}
        loop = asyncio.get_running_loop()
        
        def extract_info():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)

        info = await loop.run_in_executor(None, extract_info)
        title = info.get('title', 'فيديو')[:35]  # اختصار العنوان

        # خيارات التحميل بأكواد قصيرة جداً لا تتجاوز حد تليجرام
        keyboard = [
            [InlineKeyboardButton("🎬 أعلى جودة فيديو (Best Quality)", callback_data="dl_best")],
            [InlineKeyboardButton("🎵 تحميل صوت فقط (MP3)", callback_data="dl_audio")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await msg.edit_text(f"📹 **العنوان:** {title}\n\nاختر الخيار المطلوب للتحميل:", reply_markup=reply_markup, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error extracting info: {e}")
        await msg.edit_text(f"❌ حدث خطأ أثناء فحص الرابط:\n`{str(e)[:100]}`", parse_mode="Markdown")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    url = context.user_data.get('url')

    if not url:
        await query.edit_message_text("❌ انتهت الجلسة، يرجى إرسال الرابط من جديد.")
        return

    await query.edit_message_text("🚀 جاري التحميل والمعالجة فوراً... انتظر لحظات.")

    user_id = query.from_user.id
    out_file = f"dl_{user_id}.mp4"

    try:
        if data == "dl_best":
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'outtmpl': out_file,
                'quiet': True,
                'merge_output_format': 'mp4'
            }
        elif data == "dl_audio":
            out_file = f"dl_{user_id}.mp3"
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': out_file,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'quiet': True
            }

        loop = asyncio.get_running_loop()
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        await loop.run_in_executor(None, download)

        # إرسال الملف للمستخدم
        with open(out_file, 'rb') as f:
            if data == "dl_audio":
                await context.bot.send_audio(chat_id=query.message.chat_id, audio=f)
            else:
                await context.bot.send_video(chat_id=query.message.chat_id, video=f, supports_streaming=True)

        await query.message.delete()

    except Exception as e:
        logger.error(f"Download error: {e}")
        await query.edit_message_text(f"❌ حدث خطأ أثناء التحميل:\n`{str(e)[:100]}`", parse_mode="Markdown")

    finally:
        # حذف الملف الفعلي فوراً للحفاظ على مساحة السيرفر
        if os.path.exists(out_file):
            os.remove(out_file)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("Starting Bot...")
    app.run_polling()

if __name__ == "__main__":
    main()
