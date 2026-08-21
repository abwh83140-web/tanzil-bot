import os
import logging
import asyncio
import re
import yt_dlp
from google_play_scraper import app as play_app
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TOKEN", "8789453928:AAGlimSktG-zLypM6rMsMwec27_N7wNzDKs")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 **أهلاً بك في البوت الشامل!**\n\n"
        "أرسل لي أي رابط وسأقوم بمعالجته فوراً:\n"
        "🎬 فيديوهات (يوتيوب، فيسبوك، تيك توك)\n"
        "🖼 صور وصور متحركة (إنستغرام، تويتر/X)\n"
        "🎵 مقاطع صوتية MP3/M4A\n"
        "📱 تطبيقات Android من Google Play"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not ("http://" in text or "https://" in text):
        await update.message.reply_text("⚠️ يرجى إرسال رابط صحيح يبدأ بـ http أو https.")
        return

    url = [word for word in text.split() if word.startswith("http")][0]
    context.user_data['url'] = url

    # 1. كشف رابط Google Play للتطبيقات
    if "play.google.com/store/apps/details" in url:
        await process_app(update, url)
        return

    # 2. كشف روابط التواصل الاجتماعي والوسائط
    msg = await update.message.reply_text("⏳ جاري فحص الرابط وتحديد النوع...")
    
    is_social = any(p in url for p in ["facebook.com", "tiktok.com", "fb.watch", "instagram.com", "twitter.com", "x.com"])

    if is_social:
        keyboard = [
            [InlineKeyboardButton("🎬 تحميل فيديو / صورة", callback_data="f_best")],
            [InlineKeyboardButton("🎵 تحميل صوت فقط", callback_data="f_audio")]
        ]
        await msg.edit_text("📱 **روابط منصات التواصل الاجتماعي**\nاختر صيغة التحميل المطلوب:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        # خيارات يوتيوب وبقية المواقع
        keyboard = [
            [InlineKeyboardButton("🎬 أعلى جودة", callback_data="f_best")],
            [InlineKeyboardButton("📺 720p", callback_data="f_720"), InlineKeyboardButton("📱 480p", callback_data="f_480")],
            [InlineKeyboardButton("🎵 تحميل صوت فقط", callback_data="f_audio")]
        ]
        await msg.edit_text("📺 **يوتيوب والوسائط العامة**\nاختر الجودة المطلوب تحميلها:", reply_markup=InlineKeyboardMarkup(keyboard))

# --- معالجة روابط التطبيقات ---
async def process_app(update: Update, url: str):
    msg = await update.message.reply_text("📱 جاري البحث عن بيانات التطبيق في متجر Play...")
    try:
        app_id_search = re.search(r'id=([a-zA-Z0-9_.]+)', url)
        if not app_id_search:
            await msg.edit_text("❌ تعذر تحديد معرف التطبيق من الرابط.")
            return
            
        app_id = app_id_search.group(1)
        result = play_app(app_id, lang='ar', country='us')

        title = result.get('title', 'تطبيق Android')
        developer = result.get('developer', 'غير معروف')
        score = round(result.get('score', 0) or 0, 1)
        summary = result.get('summary', '')[:150]
        icon = result.get('icon')

        text_response = (
            f"📱 **{title}**\n"
            f"👨‍💻 المطور: {developer}\n"
            f"⭐ التقييم: {score}\n\n"
            f"📝 **الوصف:**\n{summary}...\n\n"
            f"🔗 [رابط متجر Google Play]({url})"
        )

        if icon:
            await update.message.reply_photo(photo=icon, caption=text_response, parse_mode="Markdown")
            await msg.delete()
        else:
            await msg.edit_text(text_response, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"App error: {e}")
        await msg.edit_text("❌ تعذر استخراج بيانات التطبيق من Google Play.")

# --- معالجة الأزرار للوسائط ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    url = context.user_data.get('url')
    
    if not url:
        await query.edit_message_text("❌ انتهت الجلسة، أرسل الرابط مجدداً.")
        return
    
    await query.edit_message_text("🚀 جاري التنزيل والمعالجة بأعلى سرعة... انتظر لحظات.")
    user_id = query.from_user.id
    choice = query.data
    
    formats = {
        "f_best": ("b/best", "mp4"),
        "f_720": ("bv*[height<=720]+ba/b[height<=720]/b", "mp4"),
        "f_480": ("bv*[height<=480]+ba/b[height<=480]/b", "mp4"),
        "f_audio": ("ba/b", "m4a")
    }
    
    fmt, ext = formats.get(choice, ("b/best", "mp4"))
    out_file = f"dl_{user_id}.{ext}"
    
    ydl_opts = {
        'format': fmt,
        'outtmpl': out_file,
        'quiet': True,
        'no_warnings': True,
        'writethumbnail': False
    }

    try:
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        await asyncio.to_thread(download)
        
        # كشف الملف الفعلي المنسوخ
        actual_file = out_file
        for f in os.listdir('.'):
            if f.startswith(f"dl_{user_id}"):
                actual_file = f
                break

        # إرسال حسب النوع (صورة، صوت، فيديو)
        if actual_file.endswith(('.jpg', '.jpeg', '.png', '.webp')):
            with open(actual_file, 'rb') as f:
                await context.bot.send_photo(chat_id=query.message.chat_id, photo=f)
        elif choice == "f_audio" or actual_file.endswith(('.m4a', '.mp3', '.ogg')):
            with open(actual_file, 'rb') as f:
                await context.bot.send_audio(chat_id=query.message.chat_id, audio=f)
        else:
            with open(actual_file, 'rb') as f:
                await context.bot.send_video(chat_id=query.message.chat_id, video=f, supports_streaming=True)

        await query.message.delete()

    except Exception as e:
        logger.error(f"Media download error: {e}")
        await query.edit_message_text(f"❌ حدث خطأ أثناء التحميل: `{str(e)[:60]}`", parse_mode="Markdown")

    finally:
        for f in os.listdir('.'):
            if f.startswith(f"dl_{user_id}"):
                try:
                    os.remove(f)
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
