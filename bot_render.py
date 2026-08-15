import os
import telebot
import yt_dlp
from flask import Flask
from threading import Thread

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8861680634:AAFOUC0LVP3FevhFV3mUNv3qGmghM8NECIA")

bot = telebot.TeleBot(BOT_TOKEN)

WELCOME_MSG = """لتحميل فديو وصور من انستا فقط ارسل رابط المنشور او يوزر الحساب📲 .

- لتحميل فديو من تيك توك فقط ارسل رابط المنشور👁🗨 .
- لتحميل من يوتيوب فقط ارسل اسم الاغنيه او الرابط🎙 .بوت تيك توك

🤖 عجبك البوت؟ ابعتلي و اعملك واحد.
@N9s_y"""


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, WELCOME_MSG)


@bot.message_handler(func=lambda message: True)
def handle_link(message):
    url = message.text.strip()
    if not url.startswith("http"):
        bot.reply_to(message, "ابعتلي لينك صحيح يبدأ بـ http أو https.")
        return
    status_msg = bot.reply_to(message, "بحمل الفيديو، استنى شوية...")
    filename = None
    try:
        os.makedirs('downloads', exist_ok=True)
        ydl_opts = {'outtmpl': 'downloads/%(id)s.%(ext)s', 'format': 'mp4/best', 'max_filesize': 50 * 1024 * 1024, 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        if not os.path.exists(filename):
            base, _ = os.path.splitext(filename)
            filename = base + ".mp4"
        with open(filename, 'rb') as video:
            bot.send_video(message.chat.id, video, caption="اتفضل الفيديو")
        bot.delete_message(message.chat.id, status_msg.message_id)
    except yt_dlp.utils.DownloadError:
        bot.edit_message_text("مقدرتش أحمل الفيديو ده. اتأكد إن اللينك صحيح أو إن الفيديو مش أكبر من 50 ميجا.", message.chat.id, status_msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"حصل خطأ: {e}", message.chat.id, status_msg.message_id)
    finally:
        if filename and os.path.exists(filename):
            os.remove(filename)


# ============================================
# خادم ويب صغير عشان UptimeRobot يقدر يزوره
# ============================================
app = Flask(__name__)

@app.route('/')
def home():
    return "البوت شغال"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)


if __name__ == "__main__":
    # شغل الخادم الصغير في خيط منفصل
    web_thread = Thread(target=run_web)
    web_thread.start()

    # شغل البوت نفسه
    print("البوت شغال دلوقتي")
    bot.polling(none_stop=True)
