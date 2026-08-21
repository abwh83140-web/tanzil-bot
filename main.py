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
    await update.message.reply_text("👋 أهلاً بك! أرسل رابط الفيديو وسأقوم بتحميله لك.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.startswith("http"):
        await update.message.reply_text("⚠️ أرسل رابطاً صحيحاً.")
        return

    msg = await update.message.reply_text("⏳ جاري فحص الرابط...")
    context.user_data['url'] = text
    
    # تحديد المنصة
    is_social = any(p in text for p in ["facebook.com", "tiktok.com", "fb.watch", "vm.tiktok.com"])
    
    if is_social:
        keyboard = [
            [InlineKeyboardButton("🎬 تحميل فيديو", callback_data="f_best")],
            [InlineKeyboardButton("🎵 تحميل صوت فقط", callback_data="f_audio")]
        ]
        await msg.edit_text("📱 **فيسبوك / تيك توك**\nاختر الصيغة المطلوبة:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        # خيارات يوتيوب
        keyboard = [
            [InlineKeyboardButton("🎬 أعلى جودة", callback_data="f_best")],
            [InlineKeyboardButton("📺 720p", callback_data="f_720"), InlineKeyboardButton("📱 480p", callback_data="f_480")],
            [InlineKeyboardButton("🎵 صوت فقط", callback_data="f_audio")]
        ]
        await msg.edit_text("📺 **يوتيوب**\nاختر الجودة المطلوبة:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    url = context.user_data.get('url')
    if not url: return
    
    await query.edit_message_text("🚀 جارٍ التحميل... انتظر لحظات.")
    user_id = query.from_user.id
    choice = query.data
    
    # تعريف التنسيقات
    formats = {
        "f_best": ("b/best", "mp4"),
        "f_720": ("bv*[height<=720]+ba/b[height<=720]/b", "mp4"),
        "f_480": ("bv*[height<=480]+ba/b[height<=480]/b", "mp4"),
        "f_audio": ("ba/b", "m4a")
    }
    
    fmt, ext = formats.get(choice, ("b/best", "mp4"))
    out_file = f"dl_{user_id}.{ext}"
    
    try:
        def download():
            with yt_dlp.YoutubeDL({'format': fmt, 'outtmpl': out_file, 'quiet': True}) as ydl:
                ydl.download([url])
        await asyncio.to_thread(download)
        
        # التأكد من اسم الملف
        actual_file = out_file
        for f in os.listdir('.'):
            if f.startswith(f"dl_{user_id}"): actual_file = f
            
        with open(actual_file, 'rb') as f:
            if ext == "m4a": await context.bot.send_audio(query.message.chat_id, audio=f)
            else: await context.bot.send_video(query.message.chat_id, video=f, supports_streaming=True)
        await query.message.delete()
    except Exception as e:
        await query.edit_message_text(f"❌ حدث خطأ أثناء التحميل: {str(e)[:50]}")
    finally:
        for f in os.listdir('.'):
            if f.startswith(f"dl_{user_id}"): os.remove(f)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.run_polling()

if __name__ == "__main__":
    main()
