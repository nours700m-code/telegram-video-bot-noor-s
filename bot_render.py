import os
import json
import telebot
import yt_dlp
from flask import Flask, request

BOT_TOKEN = "8861680634:AAFOUC0LVP3FevhFV3mUNv3qGmghM8NECIA"
ADMIN_ID = 6518487331

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

USERS_FILE = "users.json"

WELCOME_MSG = """لتحميل فديو وصور من انستا فقط ارسل رابط المنشور او يوزر الحساب📲 .

- لتحميل فديو من تيك توك فقط ارسل رابط المنشور👁🗨 .
- لتحميل من يوتيوب فقط ارسل اسم الاغنيه او الرابط🎙 .بوت تيك توك

🤖 عجبك البوت؟ ابعتلي و اعملك واحد.
@N9s_y"""

MAINTENANCE_MODE = False


# ============================================
# إدارة بيانات المستخدمين
# ============================================
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
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


# ============================================
# أوامر المستخدم العادي
# ============================================
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

    url = message.text.strip()

    # أوامر الأدمن
    if is_admin(message.from_user.id):
        if url.startswith("/stats"):
            users = load_users()
            total_downloads = sum(u.get("downloads", 0) for u in users.values())
            bot.reply_to(message, f"📊 إحصائيات البوت:\nعدد المستخدمين: {len(users)}\nإجمالي التحميلات: {total_downloads}\nحالة الصيانة: {'مفعّلة' if MAINTENANCE_MODE else 'متوقفة'}")
            return
        if url.startswith("/broadcast "):
            msg_text = url.replace("/broadcast ", "", 1)
            users = load_users()
            sent, failed = 0, 0
            for uid in users:
                try:
                    bot.send_message(int(uid), f"📢 رسالة من الإدارة:\n\n{msg_text}")
                    sent += 1
                except Exception:
                    failed += 1
            bot.reply_to(message, f"تم الإرسال لـ {sent} مستخدم، وفشل مع {failed}.")
            return
        if url.startswith("/maintenance_on"):
            MAINTENANCE_MODE = True
            bot.reply_to(message, "🔧 تم تفعيل وضع الصيانة. البوت هيرفض المستخدمين العاديين لحد ما تلغيه.")
            return
        if url.startswith("/maintenance_off"):
            MAINTENANCE_MODE = False
            bot.reply_to(message, "✅ تم إلغاء وضع الصيانة. البوت شغال عادي دلوقتي.")
            return
        if url.startswith("/users"):
            users = load_users()
            lines = [f"{u.get('name','')} (@{u.get('username','')}) - تحميلات: {u.get('downloads',0)}" for u in users.values()]
            text = "👥 قائمة المستخدمين:\n\n" + "\n".join(lines[:50]) if lines else "لا يوجد مستخدمين بعد."
            bot.reply_to(message, text[:4000])
            return
        if url.startswith("/admin_help"):
            bot.reply_to(message, """🛠 أوامر الأدمن المتاحة:
/stats - إحصائيات البوت
/users - قائمة المستخدمين
/broadcast <رسالة> - إرسال رسالة لكل المستخدمين
/maintenance_on - تفعيل وضع الصيانة
/maintenance_off - إلغاء وضع الصيانة
/admin_help - عرض هذه القائمة""")
            return

    register_user(message)

    if not url.startswith("http"):
        bot.reply_to(message, "ابعتلي لينك صحيح يبدأ بـ http أو https.")
        return

    status_msg = bot.reply_to(message, "بحمل الفيديو، استنى شوية...")
    filename = None
    try:
        os.makedirs('/tmp/downloads', exist_ok=True)
        ydl_opts = {'outtmpl': '/tmp/downloads/%(id)s.%(ext)s', 'format': 'mp4/best', 'max_filesize': 50 * 1024 * 1024, 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        if not os.path.exists(filename):
            base, _ = os.path.splitext(filename)
            filename = base + ".mp4"
        with open(filename, 'rb') as video:
            bot.send_video(message.chat.id, video, caption="اتفضل الفيديو")
        bot.delete_message(message.chat.id, status_msg.message_id)
        increment_downloads(message.from_user.id)
    except yt_dlp.utils.DownloadError:
        bot.edit_message_text("مقدرتش أحمل الفيديو ده. اتأكد إن اللينك صحيح أو إن الفيديو مش أكبر من 50 ميجا.", message.chat.id, status_msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"حصل خطأ: {e}", message.chat.id, status_msg.message_id)
    finally:
        if filename and os.path.exists(filename):
            os.remove(filename)


@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200


@app.route('/')
def home():
    return "البوت شغال"
