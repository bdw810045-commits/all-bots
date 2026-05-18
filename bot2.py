import telebot
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    CopyTextButton
)
import datetime
import sqlite3


# ========== COLORED BUTTONS HELPER (Bot API 9.4) ==========
# style: "primary" = أزرق | "success" = أخضر | "danger" = أحمر
def btn(text, callback_data=None, url=None, style=None, copy_text=None):
    """
    Wrapper عشان نضيف style للأزرار من Bot API 9.4
    style options: "primary" (أزرق), "success" (أخضر), "danger" (أحمر)
    """
    if copy_text is not None:
        b = InlineKeyboardButton(text, copy_text=copy_text)
    elif url:
        b = InlineKeyboardButton(text, url=url)
    else:
        b = InlineKeyboardButton(text, callback_data=callback_data)

    if style:
        b.style = style  # Bot API 9.4 - pyTelegramBotAPI بيبعته في الـ JSON تلقائي

    return b

TOKEN = "7972029946:AAG9yBuLwC508HKQxsVOrQnvAOtoVzv1AbU"
ADMIN_ID = 8306879296
CHANNEL_ID = -1003939414009

bot = telebot.TeleBot(TOKEN)
bot.remove_webhook()

# ========== VARIABLES ==========
bot_active = True
cash_number = "01000000000"

user_states = {}
user_data = {}
auto_replies = {}

# ========== DATABASE ==========
conn = sqlite3.connect("bot.db", check_same_thread=False)
conn.execute("PRAGMA journal_mode=WAL;")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS offers (
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT,
code TEXT,
bonus TEXT,
min_deposit TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
user_id INTEGER PRIMARY KEY
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS accepted (
user_id INTEGER PRIMARY KEY
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS stats (
offer_name TEXT PRIMARY KEY,
count INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS banned (
user_id INTEGER PRIMARY KEY
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS requests (
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
offer TEXT,
status TEXT,
amount TEXT,
phone TEXT,
account_id TEXT
)
""")

conn.commit()


def db(query, params=(), fetchone=False):
    try:
        cursor.execute(query, params)
        result = cursor.fetchone() if fetchone else cursor.fetchall()
        conn.commit()
        return result
    except Exception as e:
        print(f"DB Error: {e}")
        return None


# ========== LOG ==========
def log(text):
    try:
        bot.send_message(ADMIN_ID, f"📜 {text}")
    except:
        pass


def clean_old_requests(limit=50):
    try:
        cursor.execute("""
        DELETE FROM requests
        WHERE rowid NOT IN (
            SELECT rowid FROM requests
            ORDER BY rowid DESC
            LIMIT ?
        )
        """, (limit,))
        conn.commit()
    except Exception as e:
        print("Error cleaning requests:", e)


# ========== MAIN MENU MARKUP ==========
def main_menu_markup():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        btn("🎁 عروض وبونص اليوم", callback_data="bonus", style="success"),
        btn("📊 حالة طلبي", callback_data="my_request", style="primary")
    )
    markup.add(
        btn("💰 سحب الأرباح", callback_data="withdraw", style="success"),
        btn("📜 الشروط والأحكام", callback_data="terms", style="primary")
    )
    markup.add(
        btn("❓ شرح البوت", callback_data="help_bot", style="primary")
    )
    return markup


MAIN_MENU_TEXT = """🌟 أهلاً بيك في IbrahimBet VIP

━━━━━━━━━━━━━━━
💸 سجّل وابدأ تستلم أفضل بونص
🎁 عروض حصرية يومية للأعضاء
⚡ تنفيذ سريع وآمن لكل الطلبات
━━━━━━━━━━━━━━━

اختار الخدمة اللي تحتاجها 👇"""


# ========== START ==========
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id

    cursor.execute("SELECT user_id FROM banned WHERE user_id=?", (user_id,))
    if cursor.fetchone():
        return

    if not bot_active:
        bot.send_message(
            message.chat.id,
            "⛔ خدمات IbrahimBet متوقفة حالياً\n\n⏳ برجاء المحاولة مرة أخرى لاحقاً"
        )
        return

    cursor.execute("SELECT user_id FROM accepted WHERE user_id=?", (user_id,))
    if not cursor.fetchone():
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            btn("📜 عرض الشروط والأحكام", callback_data="show_terms_first", style="primary"),
            btn("✅ موافق على الشروط", callback_data="accept_terms", style="success")
        )
        bot.send_message(
            message.chat.id,
            "📜 قبل ما تبدأ تستخدم IbrahimBet VIP\n\nلازم تقرأ وتوافق على الشروط والأحكام الأول 👇",
            reply_markup=markup
        )
        return

    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    is_new = cursor.fetchone() is None

    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()

    user_states.pop(user_id, None)

    if is_new:
        full_name = message.from_user.first_name or "بدون اسم"
        username = f"@{message.from_user.username}" if message.from_user.username else "بدون يوزر"
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        kb_admin = InlineKeyboardMarkup()
        kb_admin.add(btn("👤 فتح حساب العضو", url=f"tg://user?id={user_id}", style="primary"))

        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        bot.send_message(
            ADMIN_ID,
            f"""🚀 عضو جديد انضم إلى IbrahimBet VIP

━━━━━━━━━━━━━━━
👤 الاسم: {full_name}
💬 اليوزر: {username}
🆔 الـ ID: {user_id}
🕒 وقت الدخول: {now_str}
━━━━━━━━━━━━━━━
📊 إجمالي المستخدمين: {total_users}""",
            reply_markup=kb_admin
        )

    first_name = message.from_user.first_name or "عزيزي"
    bot.send_message(
        message.chat.id,
        f"👋 أهلاً {first_name}!\n\n{MAIN_MENU_TEXT}",
        reply_markup=main_menu_markup()
    )


# ========== HELP ==========
@bot.message_handler(commands=['help'])
def help_command(message):
    user_id = message.from_user.id
    cursor.execute("SELECT user_id FROM banned WHERE user_id=?", (user_id,))
    if cursor.fetchone():
        return
    send_help(message.chat.id, use_send=True)


def send_help(chat_id, use_send=False, call=None):
    text = """❓ شرح البوت | IbrahimBet VIP

━━━━━━━━━━━━━━━
🤖 إيه اللي البوت بيعملو؟
━━━━━━━━━━━━━━━

🎁 عروض وبونص اليوم
← اختار عرض تسجيل وابدأ تستلم بونصك

📸 خطوات تقديم الطلب:
1️⃣ ابعت صورة تسجيل الحساب مع البروموكود
2️⃣ ابعت صورة بيانات الحساب (رقم، إيميل، ID)
3️⃣ حوّل المبلغ على رقم الكاش وابعت صورة التحويل
4️⃣ أدخل ID الحساب اللي هتشحن عليه

📊 حالة طلبي
← تقدر تشوف آخر حالة لطلبك في أي وقت

💰 سحب الأرباح
← بيوديك على بوت السحب الرسمي

━━━━━━━━━━━━━━━
⏱ مواعيد تنفيذ الطلبات:
من 3 إلى 6 ساعات بعد تفعيل الحساب

━━━━━━━━━━━━━━━
📌 الأوامر المتاحة:
/start ← القائمة الرئيسية
/help ← شرح البوت
/status ← حالة طلبك الحالي
/cancel ← إلغاء الطلب الجاري"""

    markup = InlineKeyboardMarkup()
    markup.add(btn("🔙 القائمة الرئيسية", callback_data="back_home", style="primary"))

    if use_send:
        bot.send_message(chat_id, text, reply_markup=markup)
    elif call:
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
        except:
            bot.send_message(chat_id, text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "help_bot")
def help_bot_callback(call):
    send_help(call.message.chat.id, call=call)


# ========== STATUS COMMAND ==========
@bot.message_handler(commands=['status'])
def status_command(message):
    user_id = message.from_user.id
    cursor.execute("SELECT user_id FROM banned WHERE user_id=?", (user_id,))
    if cursor.fetchone():
        return

    row = db("""
    SELECT offer, amount, phone, status
    FROM requests
    WHERE user_id=?
    ORDER BY id DESC
    LIMIT 1
    """, (user_id,), fetchone=True)

    if not row:
        bot.send_message(message.chat.id, "📭 مفيش طلبات مسجلة باسمك لحد دلوقتي.\n\n💡 استخدم /start لتقديم طلب جديد")
        return

    offer, amount, phone, status = row
    bot.send_message(
        message.chat.id,
        f"""📊 حالة طلبك الحالي

━━━━━━━━━━━━━━━
🏷️ العرض: {offer}
💰 المبلغ: {amount} جنيه
📱 رقم التحويل: {phone}
📌 الحالة: {status}
━━━━━━━━━━━━━━━"""
    )


# ========== CANCEL COMMAND ==========
@bot.message_handler(commands=['cancel'])
def cancel_command(message):
    user_id = message.from_user.id
    if user_states.get(user_id):
        user_states.pop(user_id, None)
        user_data.pop(user_id, None)
        bot.send_message(
            message.chat.id,
            "🚫 تم إلغاء العملية الحالية\n\n💡 استخدم /start للرجوع للقائمة الرئيسية"
        )
    else:
        bot.send_message(
            message.chat.id,
            "ℹ️ مفيش عملية جارية دلوقتي\n\n💡 استخدم /start للقائمة الرئيسية"
        )


# ========== SHOW TERMS FIRST ==========
@bot.callback_query_handler(func=lambda call: call.data == "show_terms_first")
def show_terms_first(call):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        btn("✅ موافق على الشروط", callback_data="accept_terms", style="success")
    )
    text = """📜 الشروط والأحكام | IbrahimBet VIP

━━━━━━━━━━━━━━━

🎁 للاستفادة من عروض التسجيل والبونص:

1️⃣ لازم ترسل صورة تسجيل واضحة
📸 البروموكود يظهر فيها بشكل كامل وواضح

❌ أي صورة مش واضحة أو ناقصة
هيتم رفض الطلب على طول

━━━━━━━━━━━━━━━

💰 سحب الأرباح متاح بعد تفعيل الحساب:

⏱ الحد الأدنى للسحب: 3 ساعات
⏱ الحد الأقصى: 6 ساعات

⚡ عشان نتأكد من تفعيل الحساب صح

━━━━━━━━━━━━━━━

📌 باستخدامك للبوت إنت موافق على كل الشروط دي"""

    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except:
        bot.send_message(call.message.chat.id, text, reply_markup=markup)


# ========== ACCEPT TERMS ==========
@bot.callback_query_handler(func=lambda call: call.data == "accept_terms")
def accept_terms(call):
    user_id = call.from_user.id
    cursor.execute("INSERT OR IGNORE INTO accepted (user_id) VALUES (?)", (user_id,))
    conn.commit()
    bot.answer_callback_query(call.id, "✅ تم قبول الشروط بنجاح")
    back_home(call)


# ========== BONUS MENU ==========
@bot.callback_query_handler(func=lambda call: call.data == "bonus")
def bonus_menu(call):
    if not bot_active:
        return

    markup = InlineKeyboardMarkup(row_width=1)
    cursor.execute("SELECT id, name FROM offers")
    rows = cursor.fetchall()

    if not rows:
        bot.answer_callback_query(call.id, "❌ مفيش عروض متاحة دلوقتي")
        return

    for row in rows:
        offer_id, name = row
        markup.add(btn(f"🟢 {name}", callback_data=f"offer_{offer_id}", style="success"))

    markup.add(btn("🔙 القائمة الرئيسية", callback_data="back_home", style="primary"))

    try:
        bot.edit_message_text(
            "🎁 اختار عرض التسجيل المناسب ليك من القائمة 👇",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    except:
        bot.send_message(call.message.chat.id, "🎁 اختار عرض التسجيل المناسب ليك من القائمة 👇", reply_markup=markup)


# ========== BACK HOME ==========
@bot.callback_query_handler(func=lambda call: call.data == "back_home")
def back_home(call):
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text(
            MAIN_MENU_TEXT,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=main_menu_markup()
        )
    except:
        bot.send_message(call.message.chat.id, MAIN_MENU_TEXT, reply_markup=main_menu_markup())


# ========== MY REQUEST ==========
@bot.callback_query_handler(func=lambda call: call.data == "my_request")
def my_request(call):
    if not bot_active:
        return
    bot.answer_callback_query(call.id)

    user_id = call.from_user.id

    row = db("""
    SELECT offer, amount, phone, status
    FROM requests
    WHERE user_id=?
    ORDER BY id DESC
    LIMIT 1
    """, (user_id,), fetchone=True)

    if not row:
        bot.answer_callback_query(call.id, "📭 مفيش طلبات مسجلة باسمك لحد دلوقتي")
        return

    offer, amount, phone, status = row

    text = f"""📊 حالة طلبك الحالي

━━━━━━━━━━━━━━━
🏷️ العرض:
{offer}

💰 مبلغ الإيداع:
{amount} جنيه

📱 رقم التحويل:
{phone}

📌 الحالة الحالية:
{status}
━━━━━━━━━━━━━━━"""

    markup = InlineKeyboardMarkup()
    markup.add(btn("🔙 القائمة الرئيسية", callback_data="back_home", style="primary"))

    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except:
        bot.send_message(call.message.chat.id, text, reply_markup=markup)


# ========== TERMS ==========
@bot.callback_query_handler(func=lambda call: call.data == "terms")
def terms(call):
    if not bot_active:
        return
    bot.answer_callback_query(call.id)

    text = """📜 الشروط والأحكام | IbrahimBet VIP

━━━━━━━━━━━━━━━

🎁 للاستفادة من عروض التسجيل والبونص:

1️⃣ لازم ترسل صورة تسجيل واضحة
📸 البروموكود يظهر فيها بشكل كامل وواضح

❌ أي صورة مش واضحة أو ناقصة
هيتم رفض الطلب على طول

━━━━━━━━━━━━━━━

💰 سحب الأرباح متاح بعد تفعيل الحساب:

⏱ الحد الأدنى للسحب: 3 ساعات
⏱ الحد الأقصى: 6 ساعات

⚡ عشان نتأكد من تفعيل الحساب صح

━━━━━━━━━━━━━━━

📌 باستخدامك للبوت إنت موافق على كل الشروط دي"""

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(btn("🔙 القائمة الرئيسية", callback_data="back_home", style="primary"))

    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except:
        bot.send_message(call.message.chat.id, text, reply_markup=markup)


# ========== SHOW OFFER ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith("offer_"))
def show_offer(call):
    if not bot_active:
        return

    offer_id = call.data.replace("offer_", "")

    cursor.execute("SELECT name, code, bonus, min_deposit FROM offers WHERE id=?", (offer_id,))
    row = cursor.fetchone()

    if not row:
        bot.answer_callback_query(call.id, "❌ العرض مش متاح دلوقتي")
        return

    name, code, bonus, min_deposit = row

    cursor.execute("""
    INSERT INTO stats (offer_name, count) VALUES (?, 1)
    ON CONFLICT(offer_name) DO UPDATE SET count = count + 1
    """, (name,))
    conn.commit()

    text = f"""🎁 عرض تسجيل متاح دلوقتي

━━━━━━━━━━━━━━━
🏷️ المنصة:
{name}

🎟️ البروموكود:
{code}

💰 قيمة البونص:
{bonus}

📉 أقل إيداع:
{min_deposit} جنيه
━━━━━━━━━━━━━━━

⚡ استخدم البروموكود وانت بتسجل
ثم اضغط على الزر تحت للمتابعة 👇"""

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        btn("🚀 ابدأ الطلب", callback_data=f"start_{offer_id}", style="success"),
        btn("🔙 رجوع للعروض", callback_data="bonus", style="primary")
    )

    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except:
        bot.send_message(call.message.chat.id, text, reply_markup=markup)


# ========== WITHDRAW ==========
@bot.callback_query_handler(func=lambda call: call.data == "withdraw")
def withdraw(call):
    if not bot_active:
        return

    text = """💰 سحب الأرباح | IbrahimBet VIP

━━━━━━━━━━━━━━━
عشان تسحب أرباحك بسرعة وأمان 👇

🤖 ادخل على بوت السحب الرسمي:
@ibrahim0_bot

⚡ كل عمليات السحب بتتنفذ بأسرع وقت
━━━━━━━━━━━━━━━"""

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        btn("🟡 الدخول لبوت السحب", url="https://t.me/ibrahim0_bot", style="success"),
        btn("🔙 القائمة الرئيسية", callback_data="back_home", style="primary")
    )

    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except:
        bot.send_message(call.message.chat.id, text, reply_markup=markup)


# ========== START PROCESS ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith("start_"))
def start_process(call):
    if not bot_active:
        return

    user_id = call.from_user.id
    offer_id = call.data.replace("start_", "")

    cursor.execute("SELECT name FROM offers WHERE id=?", (offer_id,))
    row = cursor.fetchone()

    if not row:
        bot.answer_callback_query(call.id, "❌ العرض مش موجود")
        return

    offer_name = row[0]

    if user_id in user_data and (
        user_data[user_id].get("status") in ["جاري التنفيذ ⏳", "قيد المراجعة 🔍"]
        or user_data[user_id].get("locked")
    ):
        bot.answer_callback_query(call.id, "⚠️ عندك طلب جاري بالفعل، استنى لحد ما يتراجع")
        return

    if user_states.get(user_id):
        bot.answer_callback_query(call.id, "⚠️ لازم تكمل الطلب الحالي الأول")
        return

    user_states[user_id] = "waiting_register_screen"
    user_data[user_id] = {"offer": offer_name, "status": "جاري التنفيذ ⏳"}

    cancel_markup = InlineKeyboardMarkup()
    cancel_markup.add(btn("🚫 إلغاء الطلب", callback_data="cancel_request", style="danger"))

    bot.send_message(
        call.message.chat.id,
        """📸 ابعت صورة تسجيل الحساب

⚠️ لازم يظهر فيها البروموكود بوضوح تام
❌ أي صورة مش واضحة هيتم رفض الطلب بيها""",
        reply_markup=cancel_markup
    )


# ========== HANDLE PHOTOS ==========
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    if not bot_active:
        return

    user_id = message.from_user.id

    if user_id not in user_states:
        return

    if user_states.get(user_id) == "waiting_register_screen":
        user_data[user_id]["register_photo"] = message.photo[-1].file_id
        user_states[user_id] = "waiting_account_info_photo"

        cancel_mk = InlineKeyboardMarkup()
        cancel_mk.add(btn("🚫 إلغاء الطلب", callback_data="cancel_request", style="danger"))

        bot.send_message(
            message.chat.id,
            """⚠️ لازم الحساب يكون مسجل برقم التليفون والإيميل

📩 ابعت صورة واضحة يظهر فيها:
• رقم التليفون
• الإيميل
• الـ ID الخاص بالحساب""",
            reply_markup=cancel_mk
        )

    elif user_states.get(user_id) == "waiting_account_info_photo":
        user_data[user_id]["account_info_photo"] = message.photo[-1].file_id
        user_states[user_id] = "waiting_confirm_transfer"

        markup = InlineKeyboardMarkup()
        markup.add(btn(
            "📋 انسخ رقم الكاش",
            copy_text=CopyTextButton(text=cash_number),
            style="primary"
        ))
        markup.add(btn("✅ حوّلت المبلغ، كمّل", callback_data="confirm_transfer", style="success"))
        markup.add(btn("🚫 إلغاء الطلب", callback_data="cancel_request", style="danger"))

        bot.send_message(
            message.chat.id,
            f"💳 رقم الكاش: {cash_number}\n\nانسخ الرقم ← حوّل المبلغ ← اضغط كمّل 👇",
            reply_markup=markup
        )

    elif user_states.get(user_id) == "waiting_transfer_screen":
        user_data[user_id]["transfer_photo"] = message.photo[-1].file_id
        user_states[user_id] = "waiting_user_id"

        cancel_mk = InlineKeyboardMarkup()
        cancel_mk.add(btn("🚫 إلغاء الطلب", callback_data="cancel_request", style="danger"))
        bot.send_message(
            message.chat.id,
            "🆔 ابعت ID الحساب اللي عايز تشحن عليه",
            reply_markup=cancel_mk
        )


# ========== CONFIRM TRANSFER ==========
@bot.callback_query_handler(func=lambda call: call.data == "confirm_transfer")
def confirm_transfer(call):
    user_states[call.from_user.id] = "waiting_amount"
    cancel_mk = InlineKeyboardMarkup()
    cancel_mk.add(btn("🚫 إلغاء الطلب", callback_data="cancel_request", style="danger"))
    bot.send_message(call.message.chat.id, "💰 ابعت قيمة المبلغ اللي حوّلته", reply_markup=cancel_mk)


# ========== GET AMOUNT ==========
@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "waiting_amount")
def get_amount(message):
    if not message.text.isdigit():
        bot.send_message(message.chat.id, "❌ لازم ترسل رقم صحيح بس")
        return

    user_data[message.from_user.id]["amount"] = message.text
    user_states[message.from_user.id] = "waiting_phone"

    cancel_mk = InlineKeyboardMarkup()
    cancel_mk.add(btn("🚫 إلغاء الطلب", callback_data="cancel_request", style="danger"))
    bot.send_message(message.chat.id, "📱 ابعت رقم التليفون اللي حوّلت منه", reply_markup=cancel_mk)


# ========== GET PHONE ==========
@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "waiting_phone")
def get_phone(message):
    if len(message.text) != 11 or not message.text.isdigit():
        bot.send_message(
            message.chat.id,
            "❌ رقم التليفون غلط\n\n📱 لازم يكون 11 رقم بالظبط"
        )
        return

    user_data[message.from_user.id]["phone"] = message.text
    user_states[message.from_user.id] = "waiting_transfer_screen"

    cancel_mk = InlineKeyboardMarkup()
    cancel_mk.add(btn("🚫 إلغاء الطلب", callback_data="cancel_request", style="danger"))
    bot.send_message(
        message.chat.id,
        """📸 ابعت صورة إيصال التحويل دلوقتي

⚠️ لازم الصورة تكون واضحة بالكامل
✅ يظهر فيها المبلغ ووقت التحويل""",
        reply_markup=cancel_mk
    )


# ========== FINAL REQUEST ==========
@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "waiting_user_id")
def get_deposit_user_id(message):
    user_id = message.from_user.id

    if user_id not in user_data:
        bot.send_message(
            message.chat.id,
            "❌ حصل خطأ أثناء تنفيذ الطلب\n\n🔄 ابدأ من أول وجديد من /start"
        )
        user_states.pop(user_id, None)
        return

    data = user_data[user_id]
    required = ["register_photo", "account_info_photo", "transfer_photo", "amount", "phone"]

    for r in required:
        if r not in data:
            bot.send_message(
                message.chat.id,
                "⚠️ البيانات مش مكتملة\n\n🔄 ابدأ من أول وجديد من /start"
            )
            user_states.pop(user_id, None)
            return

    data["account_id"] = message.text
    data["status"] = "قيد المراجعة 🔍"

    # ===== تأكيد البيانات قبل الإرسال =====
    user_states[user_id] = "waiting_final_confirm"

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        btn("✅ أيوه، بياناتي صح", callback_data="confirm_request", style="success"),
        btn("❌ لأ، إلغاء الطلب", callback_data="cancel_request", style="danger")
    )

    row = db("SELECT bonus, min_deposit FROM offers WHERE name=?", (data["offer"],), fetchone=True)
    bonus = row[0] if row else "-"
    min_dep = row[1] if row else "-"

    bot.send_message(
        message.chat.id,
        f"""🔍 مراجعة بيانات الطلب

━━━━━━━━━━━━━━━
🏷️ المنصة: {data['offer']}
🎁 البونص: {bonus} جنيه
📉 أقل إيداع: {min_dep} جنيه
━━━━━━━━━━━━━━━
💰 المبلغ المحوّل: {data['amount']} جنيه
📱 رقم التحويل: {data['phone']}
🆔 ID الحساب: {data['account_id']}
━━━━━━━━━━━━━━━

❓ إنت متأكد من البيانات دي وعايز تكمل الطلب؟""",
        reply_markup=markup
    )


# ========== CONFIRM REQUEST ==========
@bot.callback_query_handler(func=lambda call: call.data == "confirm_request")
def confirm_request(call):
    user_id = call.from_user.id

    if user_states.get(user_id) != "waiting_final_confirm":
        return

    if user_id not in user_data:
        bot.answer_callback_query(call.id, "❌ انتهت صلاحية الطلب، ابدأ من جديد")
        user_states.pop(user_id, None)
        return

    data = user_data[user_id]

    bot.edit_message_text(
        "⏳ جاري إرسال طلبك لفريق المراجعة...",
        call.message.chat.id,
        call.message.message_id
    )

    row = db("SELECT bonus, min_deposit FROM offers WHERE name=?", (data["offer"],), fetchone=True)
    bonus = row[0] if row else "-"
    min_dep = row[1] if row else "-"

    text = f"""📥 طلب إيداع جديد | IbrahimBet VIP

━━━━━━━━━━━━━━━
👤 بيانات العميل
━━━━━━━━━━━━━━━
👤 المستخدم: @{call.from_user.username or 'بدون يوزر'}
🆔 ID: <code>{user_id}</code>

━━━━━━━━━━━━━━━
🎁 تفاصيل العرض
━━━━━━━━━━━━━━━
🏷️ المنصة: {data['offer']}
🎁 البونص: {bonus} جنيه
📉 أقل إيداع: {min_dep} جنيه

━━━━━━━━━━━━━━━
💳 بيانات التحويل
━━━━━━━━━━━━━━━
💰 المبلغ: {data['amount']} جنيه
📱 رقم التحويل: <code>{data['phone']}</code>
🆔 ID الحساب: <code>{data['account_id']}</code>

━━━━━━━━━━━━━━━
📊 الحالة: ⏳ قيد المراجعة"""

    markup = InlineKeyboardMarkup()
    markup.add(
        btn("✅ قبول", callback_data=f"accept_{user_id}", style="success"),
        btn("❌ رفض", callback_data=f"reject_{user_id}", style="danger")
    )

    media = [
        telebot.types.InputMediaPhoto(data["register_photo"]),
        telebot.types.InputMediaPhoto(data["account_info_photo"]),
        telebot.types.InputMediaPhoto(data["transfer_photo"])
    ]

    try:
        album = bot.send_media_group(ADMIN_ID, media)
        msg_admin = bot.send_message(
            ADMIN_ID, text,
            reply_markup=markup,
            reply_to_message_id=album[0].message_id,
            parse_mode="HTML"
        )
        data["admin_msg_id"] = msg_admin.message_id

        try:
            album_ch = bot.send_media_group(CHANNEL_ID, media)
            msg_channel = bot.send_message(
                CHANNEL_ID, text,
                reply_to_message_id=album_ch[0].message_id,
                parse_mode="HTML"
            )
            data["channel_msg_id"] = msg_channel.message_id
        except Exception as e:
            print("Channel Error:", e)

    except Exception as e:
        print("Admin Error:", e)
        bot.send_message(
            call.message.chat.id,
            "❌ حصل خطأ أثناء إرسال الطلب\n\n🔄 حاول تاني بعد شوية"
        )
        user_states.pop(user_id, None)
        return

    db("""
    INSERT INTO requests (user_id, offer, status, amount, phone, account_id)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, data['offer'], data['status'], data['amount'], data['phone'], data['account_id']))

    clean_old_requests(50)

    bot.send_message(
        call.message.chat.id,
        """✅ تم إرسال طلبك بنجاح!

📨 طلبك دلوقتي قيد المراجعة عند فريق IbrahimBet VIP
⚡ هيتم مراجعته في أقرب وقت ممكن

💡 تقدر تتابع حالة طلبك من القائمة الرئيسية 👇""",
        reply_markup=main_menu_markup()
    )

    user_states.pop(user_id, None)
    data["locked"] = True


# ========== CANCEL REQUEST ==========
@bot.callback_query_handler(func=lambda call: call.data == "cancel_request")
def cancel_request(call):
    user_id = call.from_user.id

    user_states.pop(user_id, None)
    user_data.pop(user_id, None)

    markup = InlineKeyboardMarkup()
    markup.add(btn("🏠 القائمة الرئيسية", callback_data="back_home", style="primary"))

    try:
        bot.edit_message_text(
            """🚫 تم إلغاء طلبك بنجاح

━━━━━━━━━━━━━━━
لو حابب تعمل طلب جديد، اضغط على
القائمة الرئيسية واختار عرض جديد 👇""",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    except:
        bot.send_message(
            call.message.chat.id,
            "🚫 تم إلغاء طلبك بنجاح\n\nلو حابب تعمل طلب جديد اضغط /start",
            reply_markup=markup
        )


# ========== ACCEPT ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith("accept_"))
def accept(call):
    user_id = int(call.data.split("_")[1])
    data = user_data.get(user_id)

    if not data:
        return

    data["status"] = "تم القبول ✅"

    try:
        if call.message.caption:
            new_text = call.message.caption.replace("قيد المراجعة", "تم القبول ✅")
            bot.edit_message_caption(caption=new_text, chat_id=call.message.chat.id, message_id=call.message.message_id)
        else:
            new_text = f"✅ تم قبول الطلب\n\n🆔 ID العميل: {user_id}\n\n⚡ تمت المراجعة والاعتماد"
            bot.edit_message_text(new_text, call.message.chat.id, call.message.message_id)
    except:
        pass

    try:
        if data.get("channel_msg_id"):
            ch_text = f"✅ تم القبول\n🆔 {user_id}"
            bot.edit_message_caption(caption=ch_text, chat_id=CHANNEL_ID, message_id=data["channel_msg_id"])
    except:
        pass

    try:
        bot.send_message(
            user_id,
            """🎉 تم تنفيذ طلب الإيداع بنجاح!

💸 الرصيد اتضاف على حسابك
⚡ شكراً لاستخدامك IbrahimBet VIP

نتمنالك تجربة موفقة دايماً 🌟""",
            reply_markup=main_menu_markup()
        )
    except:
        pass

    if user_id in user_data:
        user_data[user_id]["locked"] = False

    clean_old_requests(50)


# ========== REJECT ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith("reject_"))
def reject(call):
    user_id = int(call.data.split("_")[1])
    data = user_data.get(user_id)

    if not data:
        return

    data["status"] = "مرفوض ❌"

    try:
        if call.message.caption:
            new_text = call.message.caption.replace("قيد المراجعة", "مرفوض ❌")
            bot.edit_message_caption(caption=new_text, chat_id=call.message.chat.id, message_id=call.message.message_id)
        else:
            new_text = f"❌ تم رفض الطلب\n\n🆔 ID العميل: {user_id}\n\n⚠️ راجع البيانات المرسلة"
            bot.edit_message_text(new_text, call.message.chat.id, call.message.message_id)
    except:
        pass

    try:
        if data.get("channel_msg_id"):
            ch_text = f"❌ مرفوض\n🆔 {user_id}"
            bot.edit_message_caption(caption=ch_text, chat_id=CHANNEL_ID, message_id=data["channel_msg_id"])
    except:
        pass

    try:
        bot.send_message(
            user_id,
            """❌ للأسف تم رفض طلبك

━━━━━━━━━━━━━━━
⚠️ تأكد من:
• وضوح صور التحويل
• صحة البيانات المرسلة
• تطابق معلومات الحساب
━━━━━━━━━━━━━━━

🔄 تقدر تعمل طلب جديد من القائمة دلوقتي 👇""",
            reply_markup=main_menu_markup()
        )
    except:
        pass

    if user_id in user_data:
        user_data[user_id]["locked"] = False

    clean_old_requests(50)


# ========== ADMIN PANEL ==========
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        return

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        btn("➕ إضافة عرض", callback_data="add_offer", style="success"),
        btn("➖ حذف عرض", callback_data="delete_offer", style="danger"),
        btn("📊 الإحصائيات", callback_data="stats", style="primary"),
        btn("📈 الأكثر استخداماً", callback_data="top_offers", style="primary"),
        btn("🧾 الطلبات", callback_data="all_requests", style="primary"),
        btn("🔍 بحث مستخدم", callback_data="search_user", style="primary"),
        btn("💬 رد تلقائي", callback_data="auto_reply", style="primary"),
        btn("📢 رسالة جماعية", callback_data="broadcast", style="primary"),
        btn("👤 مراسلة عضو", callback_data="msg_user", style="primary"),
        btn("🚫 حظر عضو", callback_data="ban_user", style="danger"),
        btn("🔓 فك الحظر", callback_data="unban_user", style="success"),
        btn("♻️ فك حظر الكل", callback_data="unban_all", style="success"),
        btn("📋 المحظورين", callback_data="list_banned", style="primary"),
        btn("💳 تغيير رقم الكاش", callback_data="change_cash", style="primary"),
        btn("⛔ إيقاف البوت", callback_data="stop_bot", style="danger"),
        btn("✅ تشغيل البوت", callback_data="start_bot", style="success")
    )

    status = "🟢 يعمل" if bot_active else "🔴 متوقف"

    bot.send_message(
        message.chat.id,
        f"""⚙️ لوحة تحكم IbrahimBet VIP

━━━━━━━━━━━━━━━
🤖 حالة البوت: {status}

📊 إدارة كاملة للبوت
👥 التحكم بالمستخدمين
📈 متابعة الطلبات والإحصائيات
━━━━━━━━━━━━━━━

اختار القسم المطلوب 👇""",
        reply_markup=markup
    )


# ========== BACK ADMIN ==========
@bot.callback_query_handler(func=lambda call: call.data == "back_admin")
def back_admin(call):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        btn("➕ إضافة عرض", callback_data="add_offer", style="success"),
        btn("➖ حذف عرض", callback_data="delete_offer", style="danger"),
        btn("📊 الإحصائيات", callback_data="stats", style="primary"),
        btn("📈 الأكثر استخداماً", callback_data="top_offers", style="primary"),
        btn("🧾 الطلبات", callback_data="all_requests", style="primary"),
        btn("🔍 بحث مستخدم", callback_data="search_user", style="primary"),
        btn("💬 رد تلقائي", callback_data="auto_reply", style="primary"),
        btn("📢 رسالة جماعية", callback_data="broadcast", style="primary"),
        btn("👤 مراسلة عضو", callback_data="msg_user", style="primary"),
        btn("🚫 حظر عضو", callback_data="ban_user", style="danger"),
        btn("🔓 فك الحظر", callback_data="unban_user", style="success"),
        btn("♻️ فك حظر الكل", callback_data="unban_all", style="success"),
        btn("📋 المحظورين", callback_data="list_banned", style="primary"),
        btn("💳 تغيير رقم الكاش", callback_data="change_cash", style="primary"),
        btn("⛔ إيقاف البوت", callback_data="stop_bot", style="danger"),
        btn("✅ تشغيل البوت", callback_data="start_bot", style="success")
    )

    try:
        bot.edit_message_text(
            """⚙️ لوحة تحكم IbrahimBet VIP

━━━━━━━━━━━━━━━
📊 إدارة كاملة للبوت
📈 متابعة الطلبات والإحصائيات
👥 التحكم في المستخدمين
━━━━━━━━━━━━━━━

اختار القسم المطلوب 👇""",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    except:
        pass


# ========== ADD OFFER ==========
@bot.callback_query_handler(func=lambda call: call.data == "add_offer")
def add_offer(call):
    if call.from_user.id != ADMIN_ID:
        return

    user_states[call.from_user.id] = "add_name"
    bot.send_message(call.message.chat.id, "📌 ابعت اسم المنصة أو التطبيق")


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "add_name")
def get_offer_name(message):
    if not message.text.strip():
        bot.send_message(message.chat.id, "❌ ابعت اسم منصة صحيح")
        return
    user_data[message.from_user.id] = {"name": message.text}
    user_states[message.from_user.id] = "add_code"
    bot.send_message(message.chat.id, "🎟️ ابعت البروموكود الخاص بالعرض")


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "add_code")
def get_code(message):
    if not message.text.strip():
        bot.send_message(message.chat.id, "❌ ابعت بروموكود صحيح")
        return
    user_data[message.from_user.id]["code"] = message.text
    user_states[message.from_user.id] = "add_bonus"
    bot.send_message(message.chat.id, "🎁 ابعت قيمة البونص للعرض ده")


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "add_bonus")
def get_bonus(message):
    if not message.text.strip():
        bot.send_message(message.chat.id, "❌ ابعت قيمة البونص صح")
        return
    user_data[message.from_user.id]["bonus"] = message.text
    user_states[message.from_user.id] = "add_min_deposit"
    bot.send_message(message.chat.id, "💳 ابعت الحد الأدنى للإيداع")


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "add_min_deposit")
def get_min_deposit(message):
    if message.from_user.id not in user_data:
        bot.send_message(message.chat.id, "❌ حصل خطأ\n\n🔄 ابدأ من جديد")
        return

    data = user_data[message.from_user.id]
    data["min_deposit"] = message.text

    try:
        cursor.execute(
            "INSERT OR REPLACE INTO offers (name, code, bonus, min_deposit) VALUES (?, ?, ?, ?)",
            (data["name"], data["code"], data["bonus"], data["min_deposit"])
        )
        conn.commit()
        log(f"➕ إضافة عرض: {data['name']}")

        bot.send_message(
            message.chat.id,
            f"""✅ تم إضافة العرض بنجاح

━━━━━━━━━━━━━━━
🏷️ المنصة: {data['name']}
🎟️ البروموكود: {data['code']}
🎁 البونص: {data['bonus']}
💳 أقل إيداع: {data['min_deposit']}
━━━━━━━━━━━━━━━"""
        )
    except Exception as e:
        bot.send_message(message.chat.id, "❌ حصل خطأ أثناء حفظ العرض")
        log(f"❌ خطأ إضافة عرض: {e}")

    user_states.pop(message.from_user.id, None)
    user_data.pop(message.from_user.id, None)


# ========== DELETE OFFER ==========
@bot.callback_query_handler(func=lambda call: call.data == "delete_offer")
def delete_offer(call):
    markup = InlineKeyboardMarkup(row_width=1)
    cursor.execute("SELECT id, name FROM offers")
    rows = cursor.fetchall()

    if not rows:
        markup.add(btn("🔙 رجوع", callback_data="back_admin", style="primary"))
        try:
            bot.edit_message_text("❌ مفيش عروض متاحة للحذف دلوقتي", call.message.chat.id, call.message.message_id, reply_markup=markup)
        except:
            bot.send_message(call.message.chat.id, "❌ مفيش عروض متاحة للحذف دلوقتي", reply_markup=markup)
        return

    for row in rows:
        markup.add(btn(f"🗑️ {row[1]}", callback_data=f"del_{row[0]}", style="danger"))
    markup.add(btn("🔙 رجوع", callback_data="back_admin", style="primary"))

    try:
        bot.edit_message_text("🗑️ اختار العرض اللي عايز تحذفه 👇", call.message.chat.id, call.message.message_id, reply_markup=markup)
    except:
        bot.send_message(call.message.chat.id, "🗑️ اختار العرض اللي عايز تحذفه 👇", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("del_"))
def ask_delete(call):
    offer_id = call.data.replace("del_", "")
    cursor.execute("SELECT name FROM offers WHERE id=?", (offer_id,))
    row = cursor.fetchone()

    if not row:
        return

    markup = InlineKeyboardMarkup()
    markup.add(
        btn("✅ تأكيد الحذف", callback_data=f"confirm_del_{offer_id}", style="danger"),
        btn("❌ إلغاء", callback_data="delete_offer", style="primary")
    )

    bot.send_message(
        call.message.chat.id,
        f"""⚠️ تأكيد حذف العرض

━━━━━━━━━━━━━━━
🏷️ اسم العرض: {row[0]}
━━━━━━━━━━━━━━━

إنت متأكد إنك عايز تحذف العرض ده؟""",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_del_"))
def confirm_delete(call):
    offer_id = call.data.replace("confirm_del_", "")
    cursor.execute("SELECT name FROM offers WHERE id=?", (offer_id,))
    row = cursor.fetchone()

    if not row:
        bot.send_message(call.message.chat.id, "❌ العرض مش موجود")
        return

    name = row[0]
    cursor.execute("DELETE FROM offers WHERE id=?", (offer_id,))
    conn.commit()
    log(f"🗑 تم حذف عرض: {name}")

    bot.send_message(
        call.message.chat.id,
        f"✅ تم حذف عرض {name} بنجاح"
    )


# ========== CHANGE CASH ==========
@bot.callback_query_handler(func=lambda call: call.data == "change_cash")
def change_cash(call):
    user_states[call.from_user.id] = "cash"
    bot.send_message(call.message.chat.id, "💳 ابعت رقم الكاش الجديد")


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "cash")
def set_cash(message):
    global cash_number

    if not message.text.isdigit():
        bot.send_message(message.chat.id, "❌ الرقم مش صحيح\n\n📱 ابعت رقم كاش صالح")
        return

    old = cash_number
    cash_number = message.text
    user_states.pop(message.from_user.id, None)
    log(f"💳 تغيير الكاش: {cash_number}")

    bot.send_message(
        message.chat.id,
        f"""✅ تم تحديث رقم الكاش بنجاح

━━━━━━━━━━━━━━━
📱 الرقم القديم: {old}
📱 الرقم الجديد: {cash_number}
━━━━━━━━━━━━━━━"""
    )


# ========== SEARCH USER ==========
@bot.callback_query_handler(func=lambda call: call.data == "search_user")
def search_user(call):
    user_states[call.from_user.id] = "search"
    bot.send_message(call.message.chat.id, "🔍 ابعت ID المستخدم اللي عايز تبحث عنه")


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "search")
def do_search(message):
    if not message.text.isdigit():
        bot.send_message(message.chat.id, "❌ ابعت ID صحيح")
        return

    uid = int(message.text)
    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (uid,))

    if not cursor.fetchone():
        bot.send_message(message.chat.id, "❌ المستخدم ده مش موجود في قاعدة البيانات")
        return

    cursor.execute("SELECT status FROM requests WHERE user_id=?", (uid,))
    row = cursor.fetchone()
    status = row[0] if row else "لا يوجد طلب"

    markup = InlineKeyboardMarkup()
    markup.add(btn("👤 فتح حساب العضو", url=f"tg://user?id={uid}", style="primary"))

    bot.send_message(
        message.chat.id,
        f"""👤 بيانات المستخدم

━━━━━━━━━━━━━━━
🆔 ID: {uid}
📊 حالة الطلب: {status}
━━━━━━━━━━━━━━━""",
        reply_markup=markup
    )

    user_states.pop(message.from_user.id, None)


# ========== AUTO REPLY ==========
@bot.callback_query_handler(func=lambda call: call.data == "auto_reply")
def auto_reply(call):
    user_states[call.from_user.id] = "auto_q"
    bot.send_message(call.message.chat.id, "💬 ابعت الكلمة المفتاحية للرد التلقائي")


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "auto_q")
def set_auto_q(message):
    user_data[message.from_user.id] = {"q": message.text}
    user_states[message.from_user.id] = "auto_a"
    bot.send_message(message.chat.id, "✉️ ابعت الرد اللي هيتبعت تلقائياً")


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "auto_a")
def set_auto_a(message):
    q = user_data[message.from_user.id]["q"]
    auto_replies[q] = message.text
    user_states.pop(message.from_user.id, None)
    user_data.pop(message.from_user.id, None)
    bot.send_message(message.chat.id, "✅ تم حفظ الرد التلقائي بنجاح")


# ========== MSG USER ==========
@bot.callback_query_handler(func=lambda call: call.data == "msg_user")
def msg_user(call):
    user_states[call.from_user.id] = "msg_id"
    bot.send_message(call.message.chat.id, "👤 ابعت ID العضو اللي عايز تراسله")


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "msg_id")
def get_msg_user_id(message):
    if not message.text.isdigit():
        bot.send_message(message.chat.id, "❌ الـ ID غلط")
        return
    user_data[message.from_user.id] = {"id": int(message.text)}
    user_states[message.from_user.id] = "msg_text"
    bot.send_message(message.chat.id, "✉️ ابعت الرسالة اللي عايز ترسلها للعضو")


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "msg_text")
def send_private(message):
    uid = user_data[message.from_user.id]["id"]
    try:
        bot.send_message(uid, message.text)
        bot.send_message(message.chat.id, "✅ تم إرسال الرسالة للعضو بنجاح")
    except:
        bot.send_message(message.chat.id, "❌ تعذر الإرسال للعضو ده")

    user_states.pop(message.from_user.id, None)
    user_data.pop(message.from_user.id, None)


# ========== BAN ==========
@bot.callback_query_handler(func=lambda call: call.data == "ban_user")
def ban_user(call):
    user_states[call.from_user.id] = "ban"
    bot.send_message(call.message.chat.id, "🚫 ابعت ID العضو اللي عايز تحظره")


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "ban")
def do_ban(message):
    if not message.text.isdigit():
        bot.send_message(message.chat.id, "❌ ابعت ID صحيح")
        return

    uid = int(message.text)
    cursor.execute("INSERT OR IGNORE INTO banned (user_id) VALUES (?)", (uid,))
    conn.commit()
    log(f"🚫 حظر {uid}")

    try:
        bot.send_message(uid, "🚫 تم تقييد وصولك لـ IbrahimBet VIP\n\n📩 لو في خطأ تواصل مع الإدارة")
    except:
        pass

    bot.send_message(message.chat.id, f"✅ تم حظر العضو {uid} بنجاح")
    user_states.pop(message.from_user.id, None)


# ========== UNBAN ==========
@bot.callback_query_handler(func=lambda call: call.data == "unban_user")
def unban_user(call):
    user_states[call.from_user.id] = "unban"
    bot.send_message(call.message.chat.id, "🔓 ابعت ID العضو اللي عايز تفك حظره")


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "unban")
def do_unban(message):
    if not message.text.isdigit():
        bot.send_message(message.chat.id, "❌ ابعت ID صحيح")
        return

    uid = int(message.text)
    cursor.execute("DELETE FROM banned WHERE user_id=?", (uid,))
    conn.commit()
    log(f"🔓 فك حظر {uid}")

    try:
        bot.send_message(uid, "✅ تم فك الحظر عن حسابك\n\n🎉 تقدر تستخدم كل خدمات IbrahimBet VIP تاني", reply_markup=main_menu_markup())
    except:
        pass

    bot.send_message(message.chat.id, f"✅ تم فك حظر العضو {uid} بنجاح")
    user_states.pop(message.from_user.id, None)


# ========== UNBAN ALL ==========
@bot.callback_query_handler(func=lambda call: call.data == "unban_all")
def unban_all(call):
    cursor.execute("DELETE FROM banned")
    conn.commit()
    log("♻️ فك حظر الكل")
    bot.send_message(call.message.chat.id, "♻️ تم فك الحظر عن كل الأعضاء بنجاح")


# ========== LIST BANNED ==========
@bot.callback_query_handler(func=lambda call: call.data == "list_banned")
def list_banned(call):
    cursor.execute("SELECT user_id FROM banned")
    rows = cursor.fetchall()

    if not rows:
        bot.send_message(call.message.chat.id, "📋 مفيش أعضاء محظورين دلوقتي")
        return

    text = "🚫 قائمة الأعضاء المحظورين\n\n"
    for r in rows:
        text += f"🆔 {r[0]}\n"

    bot.send_message(call.message.chat.id, text)


# ========== BROADCAST ==========
@bot.callback_query_handler(func=lambda call: call.data == "broadcast")
def broadcast(call):
    user_states[call.from_user.id] = "broadcast"
    bot.send_message(call.message.chat.id, "📢 ابعت الرسالة اللي عايز ترسلها لكل المستخدمين")


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "broadcast")
def send_broadcast(message):
    success = 0
    fail = 0

    cursor.execute("SELECT user_id FROM users")
    rows = cursor.fetchall()

    for row in rows:
        try:
            bot.send_message(row[0], message.text)
            success += 1
        except:
            fail += 1

    log(f"📢 إذاعة | نجح: {success} | فشل: {fail}")
    user_states.pop(message.from_user.id, None)

    bot.send_message(
        message.chat.id,
        f"""✅ تم إرسال الرسالة الجماعية بنجاح

━━━━━━━━━━━━━━━
📤 تم الإرسال لـ: {success} مستخدم
❌ فشل الإرسال لـ: {fail} مستخدم
━━━━━━━━━━━━━━━"""
    )


# ========== STATS ==========
@bot.callback_query_handler(func=lambda call: call.data in ["stats", "refresh_stats"])
def stats(call):
    send_stats(call, edit=True)


def send_stats(call, edit=False):
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM offers")
    total_offers = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM banned")
    total_banned = cursor.fetchone()[0]

    cursor.execute("SELECT status, amount FROM requests")
    rows = cursor.fetchall()

    total_requests = len(rows)
    pending = accepted_count = rejected = total_amount = 0

    for status, amount in rows:
        if status == "قيد المراجعة 🔍":
            pending += 1
        elif status == "تم القبول ✅":
            accepted_count += 1
            if str(amount).isdigit():
                total_amount += int(amount)
        elif status == "مرفوض ❌":
            rejected += 1

    cursor.execute("SELECT offer_name FROM stats ORDER BY count DESC LIMIT 1")
    row = cursor.fetchone()
    top_offer = row[0] if row else "لا يوجد"

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    text = f"""📊 إحصائيات IbrahimBet VIP

━━━━━━━━━━━━━━━
👥 إجمالي المستخدمين: {total_users}
🚫 المحظورين: {total_banned}
🎁 العروض المتاحة: {total_offers}
━━━━━━━━━━━━━━━
📥 إجمالي الطلبات: {total_requests}
⏳ قيد المراجعة: {pending}
✅ مقبولة: {accepted_count}
❌ مرفوضة: {rejected}
━━━━━━━━━━━━━━━
💰 إجمالي الأرباح: {total_amount} جنيه
📈 أكثر عرض استخداماً: {top_offer}
━━━━━━━━━━━━━━━
🕒 آخر تحديث: {now}"""

    markup = InlineKeyboardMarkup()
    markup.add(
        btn("🔄 تحديث", callback_data="refresh_stats", style="success"),
        btn("🔙 رجوع", callback_data="back_admin", style="primary")
    )

    try:
        if edit:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, text, reply_markup=markup)
    except:
        bot.send_message(call.message.chat.id, text, reply_markup=markup)


# ========== TOP OFFERS ==========
@bot.callback_query_handler(func=lambda call: call.data == "top_offers")
def top_offers(call):
    cursor.execute("SELECT offer_name, count FROM stats ORDER BY count DESC LIMIT 5")
    rows = cursor.fetchall()

    if not rows:
        try:
            bot.edit_message_text("❌ مفيش بيانات متاحة دلوقتي", call.message.chat.id, call.message.message_id)
        except:
            pass
        return

    text = "📈 أكثر العروض استخداماً\n\n"
    for name, count in rows:
        text += f"🎯 {name}\n📊 عدد الاستخدام: {count}\n\n"

    markup = InlineKeyboardMarkup()
    markup.add(btn("🔙 رجوع", callback_data="back_admin", style="primary"))

    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except:
        bot.send_message(call.message.chat.id, text, reply_markup=markup)


# ========== ALL REQUESTS ==========
@bot.callback_query_handler(func=lambda call: call.data == "all_requests")
def all_requests(call):
    cursor.execute("SELECT user_id, offer, status FROM requests")
    rows = cursor.fetchall()

    if not rows:
        bot.send_message(call.message.chat.id, "❌ مفيش طلبات دلوقتي")
        return

    text = "🧾 جميع الطلبات الحالية\n\n"
    for uid, offer, status in rows:
        text += f"👤 {uid}\n🎯 {offer}\n📊 {status}\n━━━━━━━━━━━━━━━\n\n"

    # تقسيم الرسالة لو كانت كبيرة
    if len(text) > 4000:
        parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for part in parts:
            bot.send_message(call.message.chat.id, part)
    else:
        bot.send_message(call.message.chat.id, text)


# ========== STOP / START BOT ==========
@bot.callback_query_handler(func=lambda call: call.data == "stop_bot")
def stop_bot(call):
    global bot_active
    if call.from_user.id != ADMIN_ID:
        return
    bot_active = False
    bot.answer_callback_query(call.id, "⛔ تم إيقاف البوت")
    bot.send_message(call.message.chat.id, "⛔ تم إيقاف خدمات IbrahimBet VIP")


@bot.callback_query_handler(func=lambda call: call.data == "start_bot")
def start_bot(call):
    global bot_active
    if call.from_user.id != ADMIN_ID:
        return
    bot_active = True
    bot.answer_callback_query(call.id, "✅ تم تشغيل البوت")
    bot.send_message(call.message.chat.id, "✅ تم تشغيل خدمات IbrahimBet VIP بنجاح")


# ========== AUTO REPLY HANDLER ==========
@bot.message_handler(func=lambda message: message.text in auto_replies and message.from_user.id not in user_states)
def auto_reply_handler(message):
    bot.send_message(message.chat.id, auto_replies[message.text])


# ========== FALLBACK ==========
@bot.message_handler(func=lambda m: True)
def fallback(message):
    user_id = message.from_user.id

    if user_states.get(user_id):
        bot.send_message(
            message.chat.id,
            "⚠️ لازم تكمل الخطوة الحالية الأول\n\n🔄 أو استخدم /cancel لإلغاء العملية"
        )
    else:
        bot.send_message(
            message.chat.id,
            "❓ الأمر ده مش معروف\n\n🚀 استخدم /start لفتح القائمة الرئيسية"
        )


# ========== RUN ==========
print("✅ IbrahimBet Bot Running...")
bot.infinity_polling(
    skip_pending=True,
    timeout=30,
    long_polling_timeout=30,
    interval=0
)
