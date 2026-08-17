import os
import json
import uuid
import subprocess
import telebot
from telebot import types
import yt_dlp
from flask import Flask, request

BOT_TOKEN = "8861680634:AAFOUC0LVP3FevhFV3mUNv3qGmghM8NECIA"
ADMIN_ID = 6518487331

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

USERS_FILE = "users.json"
DOWNLOAD_DIR = "downloads"
MAX_SIZE = 50 * 1024 * 1024

pending_urls = {}

WELCOME_MSG = """لتحميل فديو وصور من انستا فقط ارسل رابط المنشور او يوزر الحساب📲 .

- لتحميل فديو من تيك توك فقط ارسل رابط المنشور👁🗨 .
- لتحميل من يوتيوب فقط ارسل اسم الاغنيه او الرابط🎙 .

🤖 عجبك البوت؟ ابعتلي و اعملك واحد.
@N9s_y"""

MAINTENANCE_MODE = False


def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)


def register_user(message):
    users = load_users()
    uid = str(message.from_user.id)
    is_new = uid not in users
    users[uid] = {
        "name": message.from_user.first_name or "",
        "username": message.from_user.username or "",
        "downloads": users.get(uid, {}).get("downloads", 0)
    }
    save_users(users)
    if is_new and message.from_user.id != ADMIN_ID:
        try:
            bot.send_message(
                ADMIN_ID,
                f"👤 مستخدم جديد بدأ البوت:\nالاسم: {message.from_user.first_name}\nاليوزر: @{message.from_user.username}\nID: {message.from_user.id}"
            )
        except Exception:
            pass


def increment_downloads(user_id):
    users = load_users()
    uid = str(user_id)
    if uid in users:
        users[uid]["downloads"] = users[uid].get("downloads", 0) + 1
        save_users(users)


def is_admin(user_id):
    return user_id == ADMIN_ID


def compress_video(input_path):
    output_path = input_path.rsplit(".", 1)[0] + "_compressed.mp4"
    try:
        subprocess.run(
            ["ffmpeg", "-i", input_path, "-vcodec", "libx264", "-crf", "32",
             "-preset", "fast", "-acodec", "aac", "-b:a", "96k", "-y", output_path],
            check=True, capture_output=True, timeout=900
        )
        if os.path.exists(output_path) and os.path.getsize(output_path) < MAX_SIZE:
            return output_path
        return None
    except Exception:
        return None


def download_media(url, mode="video"):
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    uid = uuid.uuid4().hex[:8]
    outtmpl = f"{DOWNLOAD_DIR}/{uid}_%(playlist_index)s.%(ext)s"

    common_opts = {
        'outtmpl': outtmpl,
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'noplaylist': False,
    }

    if mode == "audio":
        ydl_opts = dict(common_opts, **{
            'format': 'bestaudio/best',
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
        })
    else:
        ydl_opts = dict(common_opts, **{
            'format': 'bestvideo*+bestaudio/best',
            'merge_output_format': 'mp4',
        })

    files = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if info is None:
            return []
        entries = info.get('entries') if info.get('_type') == 'playlist' else [info]
        for entry in entries:
            if entry is None:
                continue
            fn = ydl.prepare_filename(entry)
            if mode == "audio":
                base, _ = os.path.splitext(fn)
                fn = base + ".mp3"
            elif not os.path.exists(fn):
                base, _ = os.path.splitext(fn)
                alt = base + ".mp4"
                if os.path.exists(alt):
                    fn = alt
            if os.path.exists(fn):
                files.append(fn)
    return files


def cleanup_files(files):
    for f in files:
        try:
            if os.path.exists(f):
                os.remove(f)
        except Exception:
            pass


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    register_user(message)
    bot.reply_to(message, WELCOME_MSG)


@bot.message_handler(func=lambda message: True)
def handle_link(message):
    global MAINTENANCE_MODE
    if MAINTENANCE_MODE and not is_admin(message.from_user.id):
        bot.reply_to(message, "🔧 البوت تحت الصيانة حاليًا، حاول تاني بعد شوية.")
        return

    text = message.text.strip()

    if is_admin(message.from_user.id):
        if text.startswith("/stats"):
            users = load_users()
            total_downloads = sum(u.get("downloads", 0) for u in users.values())
            bot.reply_to(message, f"📊 عدد المستخدمين: {len(users)}\nإجمالي التحميلات: {total_downloads}")
            return
        if text.startswith("/broadcast "):
            msg_text = text.replace("/broadcast ", "", 1)
            users = load_users()
            sent, failed = 0, 0
            for uid in users:
                try:
                    bot.send_message(int(uid), f"📢 رسالة من الإدارة:\n\n{msg_text}")
                    sent += 1
                except Exception:
                    failed += 1
            bot.reply_to(message, f"تم الإرسال لـ {sent}، فشل {failed}.")
            return
        if text.startswith("/maintenance_on"):
            MAINTENANCE_MODE = True
            bot.reply_to(message, "🔧 تم تفعيل الصيانة.")
            return
        if text.startswith("/maintenance_off"):
            MAINTENANCE_MODE = False
            bot.reply_to(message, "✅ تم إلغاء الصيانة.")
            return
        if text.startswith("/users"):
            users = load_users()
            lines = [f"{u.get('name','')} (@{u.get('username','')}) - {u.get('downloads',0)}" for u in users.values()]
            bot.reply_to(message, ("👥 المستخدمين:\n\n" + "\n".join(lines[:50]))[:4000] if lines else "لا يوجد مستخدمين.")
            return

    register_user(message)

    if not text.startswith("http"):
        bot.reply_to(message, "ابعتلي لينك صحيح يبدأ بـ http أو https.")
        return

    process_download(message, text, mode="video")


def process_download(message, url, mode):
    status_msg = bot.reply_to(message, "⏳ بحمل، استنى شوية...")
    files = []
    try:
        files = download_media(url, mode=mode)
        if not files:
            bot.edit_message_text("مقدرتش ألاقي محتوى في اللينك ده. جرب لينك تاني.", message.chat.id, status_msg.message_id)
            return

        sent_any = False
        for f in files:
            size = os.path.getsize(f)
            if size > MAX_SIZE and f.lower().endswith(".mp4"):
                compressed = compress_video(f)
                if compressed:
                    os.remove(f)
                    f = compressed
                else:
                    bot.send_message(message.chat.id, "⚠️ الملف كبير جدًا (أكبر من 50 ميجا) ومقدرناش نضغطه.")
                    continue
            elif size > MAX_SIZE:
                bot.send_message(message.chat.id, "⚠️ الملف كبير جدًا عن حد تليجرام (50 ميجا).")
                continue

            with open(f, 'rb') as media:
                lower = f.lower()
                if lower.endswith(".mp3"):
                    bot.send_audio(message.chat.id, media)
                elif lower.endswith((".jpg", ".jpeg", ".png", ".webp")):
                    bot.send_photo(message.chat.id, media)
                else:
                    sent = bot.send_video(message.chat.id, media, caption="اتفضل الفيديو")
                    if mode == "video":
                        short_id = uuid.uuid4().hex[:10]
                        pending_urls[short_id] = url
                        markup = types.InlineKeyboardMarkup()
                        markup.row(
                            types.InlineKeyboardButton("🎵 نسخة صوتية", callback_data=f"audio:{short_id}")
                        )
                        bot.send_message(sent.chat.id, "عايز نسخة صوتية من نفس الفيديو؟", reply_markup=markup)
            sent_any = True

        bot.delete_message(message.chat.id, status_msg.message_id)
        if sent_any:
            increment_downloads(message.from_user.id)
    except Exception as e:
        try:
            bot.edit_message_text(f"حصل خطأ: {e}", message.chat.id, status_msg.message_id)
        except Exception:
            bot.send_message(message.chat.id, f"حصل خطأ: {e}")
    finally:
        cleanup_files(files)


@bot.callback_query_handler(func=lambda call: call.data.startswith("audio:"))
def handle_callback(call):
    _, short_id = call.data.split(":", 1)
    url = pending_urls.get(short_id)
    if not url:
        bot.answer_callback_query(call.id, "انتهت صلاحية الرابط، ابعت الرابط تاني.")
        return
    bot.answer_callback_query(call.id, "جاري التحميل...")
    process_download(call.message, url, mode="audio")



@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200


@app.route('/')
def home():
    return "البوت شغال"
    
