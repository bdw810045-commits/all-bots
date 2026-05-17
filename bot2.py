import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import datetime
import sqlite3

TOKEN = "7972029946:AAHh7FxpxnZsTSpERi8mawUUv_GxJ2XOS2A" 
ADMIN_ID = 8306879296  
CHANNEL_ID = -1003937917667  # قناة التخزين

bot = telebot.TeleBot(TOKEN)
bot.remove_webhook()

# ========== VARIABLES ==========
bot_active = True
cash_number = "01000000000"

user_states = {}
user_data = {}
auto_replies = {}

#========== DATABASE ==========

conn = sqlite3.connect("bot.db", check_same_thread=False)

# 🔥 مهم جدًا لمنع مشاكل الكراش والتداخل
conn.execute("PRAGMA journal_mode=WAL;")

cursor = conn.cursor()

# جدول العروض
cursor.execute("""
CREATE TABLE IF NOT EXISTS offers (
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT,
code TEXT,
bonus TEXT,
min_deposit TEXT
)
""")

# جدول المستخدمين
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
user_id INTEGER PRIMARY KEY
)
""")

# جدول الموافقة على الشروط
cursor.execute("""
CREATE TABLE IF NOT EXISTS accepted (
user_id INTEGER PRIMARY KEY
)
""")

# احصائيات العروض
cursor.execute("""
CREATE TABLE IF NOT EXISTS stats (
offer_name TEXT PRIMARY KEY,
count INTEGER DEFAULT 0
)
""")

# جدول المحظورين
cursor.execute("""
CREATE TABLE IF NOT EXISTS banned (
user_id INTEGER PRIMARY KEY
)
""")

# جدول الطلبات
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

import sqlite3

def db(query, params=(), fetchone=False):
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()

    cursor.execute(query, params)

    result = cursor.fetchone() if fetchone else cursor.fetchall()

    conn.commit()
    conn.close()

    return result

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


def optimize_db():
    pass
  
# ========== START ==========
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id

    # ✅ تحقق من الحظر
    cursor.execute("SELECT user_id FROM banned WHERE user_id=?", (user_id,))
    if cursor.fetchone():
        return

    if not bot_active:
        bot.send_message(
            message.chat.id,
            """⛔ خدمات IbrahimBet متوقفة حالياً

⏳ برجاء المحاولة مرة أخرى لاحقاً"""
        )
        return

    # 🔥 شرط الموافقة على الشروط
    cursor.execute("SELECT user_id FROM accepted WHERE user_id=?", (user_id,))
    if not cursor.fetchone():
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("📜 عرض الشروط والأحكام", callback_data="show_terms_first"),
            InlineKeyboardButton("✅ موافق على الشروط", callback_data="accept_terms")
        )

        bot.send_message(
            message.chat.id,
            """📜 قبل استخدام خدمات IbrahimBet

يرجى قراءة والموافقة على الشروط والأحكام أولاً 👇""",
            reply_markup=markup
        )
        return

    # ✅ تحقق هل المستخدم جديد
    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    is_new = cursor.fetchone() is None

    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()

    user_states.pop(user_id, None)

    # 🔔 إشعار الأدمن
    if is_new:
        full_name = message.from_user.first_name or "لا يوجد"
        username = f"@{message.from_user.username}" if message.from_user.username else "لا يوجد"

        from datetime import datetime
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        kb_admin = InlineKeyboardMarkup()
        kb_admin.add(
            InlineKeyboardButton("👤 فتح حساب العضو", url=f"tg://user?id={user_id}")
        )

        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        bot.send_message(
            ADMIN_ID,
            f"""🚀 عضو جديد انضم إلى IbrahimBet

━━━━━━━━━━━━━━━
👤 الاسم: {full_name}
💬 اليوزر: {username}
🆔 الايدي: {user_id}
🕒 وقت الدخول: {now_str}
━━━━━━━━━━━━━━━

📊 إجمالي المستخدمين: {total_users}
""",
            reply_markup=kb_admin
        )

    # ✅ القائمة الرئيسية
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🎁 عروض وبونص اليوم", callback_data="bonus"),
        InlineKeyboardButton("📊 حالة طلبي", callback_data="my_request")
    )
    markup.add(
        InlineKeyboardButton("💰 سحب الأرباح", callback_data="withdraw"),
        InlineKeyboardButton("📜 الشروط والأحكام", callback_data="terms")
    )

    bot.send_message(
        message.chat.id,
        """👋 أهلاً بيك في IbrahimBet VIP

💸 سجل واستلم أفضل عروض البونص
⚡ تنفيذ سريع وآمن لجميع الطلبات
🎁 عروض حصرية يومية للمستخدمين

اختر الخدمة المطلوبة من القائمة 👇""",
        reply_markup=markup
    )


# ========== ACCEPT TERMS ==========
@bot.callback_query_handler(func=lambda call: call.data == "accept_terms")
def accept_terms(call):
    user_id = call.from_user.id

    # ✅ حفظ في الداتا بيز بدل set
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

    # ✅ لو مفيش عروض
    if not rows:
        bot.answer_callback_query(call.id, "❌ لا توجد عروض متاحة حالياً")
        return

    for row in rows:
        offer_id = row[0]
        name = row[1]

        markup.add(
            InlineKeyboardButton(
                f"🎯 {name}",
                callback_data=f"offer_{offer_id}"
            )
        )

    markup.add(
        InlineKeyboardButton(
            "🔙 القائمة الرئيسية",
            callback_data="back_home"
        )
    )

    bot.edit_message_text(
        "🎁 اختر عرض التسجيل المناسب ليك من القائمة 👇",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )


# ========== BACK HOME ==========
@bot.callback_query_handler(func=lambda call: call.data == "back_home")
def back_home(call):
    if not bot_active:
        return

    markup = InlineKeyboardMarkup(row_width=2)

    markup.add(
        InlineKeyboardButton("🎁 عروض وبونص اليوم", callback_data="bonus"),
        InlineKeyboardButton("📊 حالة طلبي", callback_data="my_request")
    )
    markup.add(
        InlineKeyboardButton("💰 سحب الأرباح", callback_data="withdraw"),
        InlineKeyboardButton("📜 الشروط والأحكام", callback_data="terms")
    )

    bot.edit_message_text(
        """👋 أهلاً بيك في IbrahimBet VIP

💸 سجل واستلم أفضل عروض البونص
⚡ تنفيذ سريع وآمن لجميع الطلبات
🎁 عروض حصرية يومية للمستخدمين

اختر الخدمة المطلوبة من القائمة 👇""",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data == "my_request")
def my_request(call):
    if not bot_active:
        return

    user_id = call.from_user.id

    row = db("""
    SELECT offer, amount, phone, status 
    FROM requests 
    WHERE user_id=? 
    ORDER BY id DESC 
    LIMIT 1
    """, (user_id,), fetchone=True)

    if not row:
        bot.answer_callback_query(call.id, "❌ لا يوجد لديك أي طلب حالياً")
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
    markup.add(
        InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_home")
    )

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

# ========== TERMS ==========
@bot.callback_query_handler(func=lambda call: call.data == "terms")
def terms(call):
    if not bot_active:
        return

    text = """📜 الشروط والأحكام | IbrahimBet VIP

━━━━━━━━━━━━━━━

🎁 للاستفادة من عروض التسجيل والبونص:

1️⃣ يجب إرسال صورة تسجيل واضحة
📸 ويظهر بها البروموكود بشكل كامل وواضح

❌ أي صورة غير واضحة أو ناقصة
سيتم رفض الطلب مباشرة

━━━━━━━━━━━━━━━

💰 سحب الأرباح متاح بعد تفعيل الحساب:

⏱ الحد الأدنى للسحب:
3 ساعات

⏱ الحد الأقصى:
6 ساعات

⚡ لضمان تأكيد وتفعيل الحساب بشكل صحيح

━━━━━━━━━━━━━━━

📌 باستخدامك للبوت فأنت موافق على جميع الشروط المذكورة"""

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_home")
    )

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

# ========== SHOW OFFER ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith("offer_"))
def show_offer(call):
    if not bot_active:
        return

    offer_id = call.data.replace("offer_", "")

    # ✅ جلب البيانات من الداتا بيز باستخدام ID
    cursor.execute(
        "SELECT name, code, bonus, min_deposit FROM offers WHERE id=?",
        (offer_id,)
    )

    row = cursor.fetchone()

    if not row:
        bot.answer_callback_query(call.id, "❌ العرض غير متاح حالياً")
        return

    name, code, bonus, min_deposit = row

    # ✅ تحديث الإحصائيات
    cursor.execute("""
    INSERT INTO stats (offer_name, count)
    VALUES (?, 1)
    ON CONFLICT(offer_name) DO UPDATE SET count = count + 1
    """, (name,))
    conn.commit()

    text = f"""🎁 عرض تسجيل متاح الآن

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

⚡ قم باستخدام البروموكود أثناء التسجيل
ثم اضغط على الزر بالأسفل للمتابعة"""

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton(
            "🚀 متابعة الطلب",
            callback_data=f"start_{offer_id}"
        ),
        InlineKeyboardButton(
            "🔙 رجوع للعروض",
            callback_data="bonus"
        )
    )

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )


# ========== WITHDRAW ==========
@bot.callback_query_handler(func=lambda call: call.data == "withdraw")
def withdraw(call):
    if not bot_active:
        return

    text = """💰 سحب الأرباح | IbrahimBet VIP

لسحب أرباحك بشكل سريع وآمن 👇

🤖 قم بالدخول إلى بوت السحب الرسمي:
@ibrahim0_bot

⚡ يتم تنفيذ جميع عمليات السحب بأسرع وقت ممكن"""

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🚀 الدخول إلى بوت السحب", url="https://t.me/ibrahim0_bot"),
        InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_home")
    )

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

# ========== START PROCESS ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith("start_"))
def start_process(call):
    if not bot_active:
        return

    user_id = call.from_user.id

    # ✅ جلب ID العرض
    offer_id = call.data.replace("start_", "")

    # ✅ جلب اسم العرض من الداتا بيز
    cursor.execute(
        "SELECT name FROM offers WHERE id=?",
        (offer_id,)
    )

    row = cursor.fetchone()

    if not row:
        bot.answer_callback_query(call.id, "❌ العرض غير متوفر")
        return

    offer_name = row[0]

    # 🔥 منع طلب جديد لو فيه طلب شغال أو تحت المراجعة أو مقفول
    if user_id in user_data and (
        user_data[user_id].get("status") in ["جاري التنفيذ ⏳", "قيد المراجعة 🔍"]
        or user_data[user_id].get("locked")
    ):
        bot.answer_callback_query(call.id, "⚠️ لديك طلب جاري بالفعل، انتظر حتى يتم مراجعته")
        return

    # 🔥 منع بدء طلب جديد لو المستخدم لسه مكملش الخطوات
    if user_states.get(user_id):
        bot.answer_callback_query(call.id, "⚠️ يرجى استكمال الطلب الحالي أولاً")
        return

    user_states[user_id] = "waiting_register_screen"

    user_data[user_id] = {
        "offer": offer_name,
        "status": "جاري التنفيذ ⏳"
    }

    bot.send_message(
        call.message.chat.id,
        """📸 أرسل صورة تسجيل الحساب

⚠️ يجب أن يظهر البروموكود بوضوح داخل الصورة
❌ أي صورة غير واضحة قد تؤدي إلى رفض الطلب"""
    )


# ========== HANDLE PHOTOS ==========
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    if not bot_active:
        return

    user_id = message.from_user.id

    # 🔥 تجاهل أي صورة لو المستخدم مش في خطوة مطلوبة
    if user_id not in user_states:
        return

    # ✅ صورة التسجيل الأولى
    if user_states.get(user_id) == "waiting_register_screen":

        user_data[user_id]["register_photo"] = message.photo[-1].file_id

        # 🔥 نطلب الصورة الثانية
        user_states[user_id] = "waiting_account_info_photo"

        bot.send_message(
            message.chat.id,
"""⚠️ لازم الحساب يكون متسجل برقم التليفون والجيميل

📩 ابعت سكرينة واضحة يظهر فيها:
• رقم التليفون
• الجيميل
• الـ ID الخاص بالحساب"""
        )

    # ✅ الصورة الثانية (التليفون + الجيميل + ID)
    elif user_states.get(user_id) == "waiting_account_info_photo":

        user_data[user_id]["account_info_photo"] = message.photo[-1].file_id

        user_states[user_id] = "waiting_confirm_transfer"

        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ قمت بالتحويل", callback_data="confirm_transfer")
        )

        bot.send_message(
            message.chat.id,
f"""💳 بيانات التحويل | IbrahimBet VIP

━━━━━━━━━━━━━━━
📱 رقم الكاش:
{cash_number}
━━━━━━━━━━━━━━━

⚡ قم بتحويل المبلغ المطلوب
ثم اضغط على الزر بالأسفل للمتابعة""",
            reply_markup=markup
        )

    # ✅ صورة التحويل
    elif user_states.get(user_id) == "waiting_transfer_screen":

        user_data[user_id]["transfer_photo"] = message.photo[-1].file_id

        user_states[user_id] = "waiting_user_id"

        bot.send_message(
            message.chat.id,
            "🆔 أرسل ID الحساب الذي ترغب بالشحن عليه"
        )


# ========== CONFIRM ==========
@bot.callback_query_handler(func=lambda call: call.data == "confirm_transfer")
def confirm_transfer(call):
    user_states[call.from_user.id] = "waiting_amount"

    bot.send_message(
        call.message.chat.id,
        "💰 أرسل قيمة المبلغ الذي قمت بتحويله"
    )


# ========== GET AMOUNT ==========
@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "waiting_amount")
def get_amount(message):
    if message.from_user.id not in user_states:
        return

    if not message.text.isdigit():
        bot.send_message(message.chat.id, "❌ يرجى إرسال رقم صحيح")
        return

    user_data[message.from_user.id]["amount"] = message.text
    user_states[message.from_user.id] = "waiting_phone"

    bot.send_message(
        message.chat.id,
        "📱 أرسل رقم الهاتف الذي تم التحويل منه"
    )


# ========== GET PHONE ==========
@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "waiting_phone")
def get_phone(message):
    if message.from_user.id not in user_states:
        return

    if len(message.text) != 11 or not message.text.isdigit():
        bot.send_message(
            message.chat.id,
            "❌ رقم الهاتف غير صحيح\n\n📱 يجب أن يكون الرقم مكوّن من 11 رقم"
        )
        return

    user_data[message.from_user.id]["phone"] = message.text
    user_states[message.from_user.id] = "waiting_transfer_screen"

    bot.send_message(
        message.chat.id,
        """📸 أرسل صورة التحويل الآن

⚠️ يجب أن تكون الصورة واضحة بالكامل
✅ ويظهر بها المبلغ ووقت التحويل"""
    )


# ========== FINAL REQUEST ==========
@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "waiting_user_id")
def get_deposit_user_id(message):
    user_id = message.from_user.id

    if user_id not in user_states:
        return

    if user_id not in user_data:
        bot.send_message(
            message.chat.id,
            "❌ حدث خطأ أثناء تنفيذ الطلب\n\n🔄 ابدأ من جديد باستخدام /start"
        )
        return

    data = user_data[user_id]

    required = [
        "register_photo",
        "account_info_photo",
        "transfer_photo",
        "amount",
        "phone"
    ]

    for r in required:
        if r not in data:
            bot.send_message(
                message.chat.id,
                "⚠️ البيانات المطلوبة غير مكتملة\n\n🔄 يرجى إعادة المحاولة من البداية /start"
            )

            user_states.pop(user_id, None)
            return

    data["account_id"] = message.text
    data["status"] = "قيد المراجعة 🔍"

    row = db(
        "SELECT bonus, min_deposit FROM offers WHERE name=?",
        (data["offer"],),
        fetchone=True
    )

    bonus = row[0] if row else "-"
    min_dep = row[1] if row else "-"

    text = f"""📥 طلب إيداع جديد | IbrahimBet VIP

━━━━━━━━━━━━━━━
👤 بيانات العميل
━━━━━━━━━━━━━━━
👤 المستخدم:
@{message.from_user.username or 'لا يوجد'}

🆔 ID:
<code>{user_id}</code>

━━━━━━━━━━━━━━━
🎁 تفاصيل العرض
━━━━━━━━━━━━━━━
🏷️ المنصة:
{data['offer']}

🎁 البونص:
{bonus} جنيه

📉 أقل إيداع:
{min_dep} جنيه

━━━━━━━━━━━━━━━
💳 بيانات التحويل
━━━━━━━━━━━━━━━
💰 المبلغ:
{data['amount']} جنيه

📱 رقم التحويل:
<code>{data['phone']}</code>

🆔 ID الحساب:
<code>{data['account_id']}</code>

━━━━━━━━━━━━━━━
📊 الحالة الحالية:
⏳ قيد المراجعة"""

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ قبول", callback_data=f"accept_{user_id}"),
        InlineKeyboardButton("❌ رفض", callback_data=f"reject_{user_id}")
    )

    # 🔥 أهم حاجة: طمّن المستخدم الأول
    bot.send_message(
        message.chat.id,
        "⏳ جاري إرسال طلبك إلى فريق المراجعة..."
    )

    media = [
        telebot.types.InputMediaPhoto(data["register_photo"]),
        telebot.types.InputMediaPhoto(data["account_info_photo"]),
        telebot.types.InputMediaPhoto(data["transfer_photo"])
    ]

    try:
        # ✅ إرسال للأدمن
        album = bot.send_media_group(ADMIN_ID, media)

        msg_admin = bot.send_message(
            ADMIN_ID,
            text,
            reply_markup=markup,
            reply_to_message_id=album[0].message_id,
            parse_mode="HTML"
        )

        data["admin_msg_id"] = msg_admin.message_id

        # ✅ إرسال للقناة
        try:
            album_ch = bot.send_media_group(CHANNEL_ID, media)

            msg_channel = bot.send_message(
                CHANNEL_ID,
                text,
                reply_to_message_id=album_ch[0].message_id,
                parse_mode="HTML"
            )

            data["channel_msg_id"] = msg_channel.message_id

        except Exception as e:
            print("Channel Error:", e)

    except Exception as e:
        print("Admin Error:", e)

        bot.send_message(
            message.chat.id,
            "❌ حدث خطأ أثناء إرسال الطلب\n\n🔄 حاول مرة أخرى بعد قليل"
        )
        return

    # ✅ حفظ في الداتا بيز
    db("""
    INSERT INTO requests (user_id, offer, status, amount, phone, account_id)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        data['offer'],
        data['status'],
        data['amount'],
        data['phone'],
        data['account_id']
    ))

    clean_old_requests(50)
    optimize_db()

    # ✅ رسالة التأكيد
    bot.send_message(
        message.chat.id,
        """✅ تم إرسال طلبك بنجاح

📨 الطلب الآن قيد المراجعة بواسطة فريق IbrahimBet VIP
⚡ سيتم مراجعة الطلب في أقرب وقت ممكن"""
    )

    user_states.pop(user_id, None)

    # 🔥 قفل الطلب
    user_data[user_id]["locked"] = True


# ========== ACCEPT ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith("accept_"))
def accept(call):
    user_id = int(call.data.split("_")[1])
    data = user_data.get(user_id)

    if not data:
        return

    data["status"] = "تم القبول ✅"

    if call.message.caption:
        new_text = call.message.caption.replace("قيد المراجعة", "تم القبول ✅")

        bot.edit_message_caption(
            caption=new_text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )

    else:
        bot.edit_message_text(
            f"""✅ تم قبول الطلب بنجاح

🆔 ID العميل:
{user_id}

⚡ تمت مراجعة الطلب واعتماده""",
            call.message.chat.id,
            call.message.message_id
        )

    try:
        if data.get("channel_msg_id"):
            bot.edit_message_caption(
                caption=new_text,
                chat_id=CHANNEL_ID,
                message_id=data["channel_msg_id"]
            )
    except:
        pass

    bot.send_message(
        user_id,
        """✅ تم تنفيذ طلب الإيداع بنجاح

💸 تم إضافة الرصيد إلى حسابك
⚡ شكراً لاستخدامك IbrahimBet VIP

🎉 نتمنى لك تجربة موفقة"""
    )

    # 🔥 فك قفل الطلب
    if user_id in user_data:
        user_data[user_id]["locked"] = False

    # ✅ تنظيف الطلبات القديمة
    clean_old_requests(50)


# ========== REJECT ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith("reject_"))
def reject(call):
    user_id = int(call.data.split("_")[1])
    data = user_data.get(user_id)

    if not data:
        return

    data["status"] = "مرفوض ❌"

    if call.message.caption:
        new_text = call.message.caption.replace("قيد المراجعة", "مرفوض ❌")

        bot.edit_message_caption(
            caption=new_text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )

    else:
        bot.edit_message_text(
            f"""❌ تم رفض الطلب

🆔 ID العميل:
{user_id}

⚠️ يرجى مراجعة البيانات المرسلة""",
            call.message.chat.id,
            call.message.message_id
        )

    try:
        if data.get("channel_msg_id"):
            bot.edit_message_caption(
                caption=new_text,
                chat_id=CHANNEL_ID,
                message_id=data["channel_msg_id"]
            )
    except:
        pass

    bot.send_message(
        user_id,
        """❌ تم رفض الطلب

⚠️ يرجى التأكد من:
• وضوح صور التحويل
• صحة البيانات المرسلة
• تطابق معلومات الحساب

🔄 يمكنك إعادة المحاولة مرة أخرى

#IbrahimBet"""
    )

    # 🔥 فك قفل الطلب
    if user_id in user_data:
        user_data[user_id]["locked"] = False

    # ✅ تنظيف الطلبات القديمة
    clean_old_requests(50)


@bot.message_handler(commands=['admin'])
def admin_panel(message):

    # ✅ السماح للأدمن فقط
    if message.from_user.id != ADMIN_ID:
        return

    # ✅ لو البوت متوقف الأدمن يقدر يدخل عادي
    markup = InlineKeyboardMarkup(row_width=2)

    markup.add(
        InlineKeyboardButton("➕ إضافة عرض", callback_data="add_offer"),
        InlineKeyboardButton("➖ حذف عرض", callback_data="delete_offer"),
        InlineKeyboardButton("📊 الإحصائيات", callback_data="stats"),
        InlineKeyboardButton("📈 الأكثر استخدام", callback_data="top_offers"),
        InlineKeyboardButton("🧾 الطلبات", callback_data="all_requests"),
        InlineKeyboardButton("🔍 بحث عن مستخدم", callback_data="search_user"),
        InlineKeyboardButton("💬 رد تلقائي", callback_data="auto_reply"),
        InlineKeyboardButton("📢 رسالة جماعية", callback_data="broadcast"),
        InlineKeyboardButton("👤 مراسلة عضو", callback_data="msg_user"),
        InlineKeyboardButton("🚫 حظر عضو", callback_data="ban_user"),
        InlineKeyboardButton("🔓 فك الحظر", callback_data="unban_user"),
        InlineKeyboardButton("♻️ فك حظر الجميع", callback_data="unban_all"),
        InlineKeyboardButton("📋 قائمة المحظورين", callback_data="list_banned"),
        InlineKeyboardButton("💳 تغيير رقم الكاش", callback_data="change_cash"),
        InlineKeyboardButton("⛔ إيقاف البوت", callback_data="stop_bot"),
        InlineKeyboardButton("✅ تشغيل البوت", callback_data="on_bot")
    )

    status = "🟢 يعمل" if bot_active else "🔴 متوقف"

    bot.send_message(
        message.chat.id,
f"""⚙️ لوحة تحكم IbrahimBet VIP

━━━━━━━━━━━━━━━
🤖 حالة البوت:
{status}

📊 إدارة كاملة للبوت
👥 التحكم بالمستخدمين
📈 متابعة الطلبات والإحصائيات
━━━━━━━━━━━━━━━

اختر القسم المطلوب 👇""",
        reply_markup=markup
    )


# ========== ADD OFFER ==========
@bot.callback_query_handler(func=lambda call: call.data == "add_offer")
def add_offer(call):
    if not bot_active:
        return

    if call.from_user.id != ADMIN_ID:
        return

    user_states[call.from_user.id] = "add_name"

    bot.send_message(
        call.message.chat.id,
        "📌 أرسل اسم المنصة أو التطبيق"
    )


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "add_name")
def get_offer_name(message):
    if not message.text.strip():
        bot.send_message(
            message.chat.id,
            "❌ يرجى إرسال اسم منصة صحيح"
        )
        return

    user_data[message.from_user.id] = {"name": message.text}
    user_states[message.from_user.id] = "add_code"

    bot.send_message(
        message.chat.id,
        "🎟️ أرسل البروموكود الخاص بالعرض"
    )


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "add_code")
def get_code(message):
    if not message.text.strip():
        bot.send_message(
            message.chat.id,
            "❌ يرجى إرسال بروموكود صحيح"
        )
        return

    user_data[message.from_user.id]["code"] = message.text
    user_states[message.from_user.id] = "add_bonus"

    bot.send_message(
        message.chat.id,
        "🎁 أرسل قيمة البونص الخاصة بالعرض"
    )


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "add_bonus")
def get_bonus(message):
    if not message.text.strip():
        bot.send_message(
            message.chat.id,
            "❌ يرجى إرسال قيمة البونص بشكل صحيح"
        )
        return

    user_data[message.from_user.id]["bonus"] = message.text

    user_states[message.from_user.id] = "add_min_deposit"

    bot.send_message(
        message.chat.id,
        "💳 أرسل الحد الأدنى للإيداع"
    )


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "add_min_deposit")
def get_min_deposit(message):

    # تأكد إن البيانات موجودة
    if message.from_user.id not in user_data:
        bot.send_message(
            message.chat.id,
            "❌ حدث خطأ أثناء إضافة العرض\n\n🔄 ابدأ من جديد"
        )
        return

    data = user_data[message.from_user.id]
    data["min_deposit"] = message.text

    try:
        # ✅ حفظ في الداتا بيز
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
🏷️ المنصة:
{data['name']}

🎟️ البروموكود:
{data['code']}

🎁 البونص:
{data['bonus']}

💳 أقل إيداع:
{data['min_deposit']}
━━━━━━━━━━━━━━━"""
        )

    except Exception as e:
        bot.send_message(
            message.chat.id,
            "❌ حدث خطأ أثناء حفظ العرض"
        )

        log(f"❌ خطأ إضافة عرض: {e}")

    user_states.pop(message.from_user.id)
    user_data.pop(message.from_user.id)


@bot.callback_query_handler(func=lambda call: call.data == "delete_offer")
def delete_offer(call):
    if not bot_active:
        return

    markup = InlineKeyboardMarkup(row_width=1)

    cursor.execute("SELECT id, name FROM offers")
    rows = cursor.fetchall()

    if not rows:
        markup.add(
            InlineKeyboardButton("🔙 رجوع", callback_data="back_admin")
        )

        bot.edit_message_text(
            "❌ لا توجد عروض متاحة للحذف حالياً",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )

        return

    for row in rows:
        offer_id = row[0]
        name = row[1]

        markup.add(
            InlineKeyboardButton(
                f"🗑️ {name}",
                callback_data=f"del_{offer_id}"
            )
        )

    markup.add(
        InlineKeyboardButton("🔙 رجوع", callback_data="back_admin")
    )

    bot.edit_message_text(
        "🗑️ اختر العرض الذي تريد حذفه من القائمة 👇",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("del_"))
def ask_delete(call):
    if not bot_active:
        return

    offer_id = call.data.replace("del_", "")

    cursor.execute(
        "SELECT name FROM offers WHERE id=?",
        (offer_id,)
    )

    row = cursor.fetchone()

    if not row:
        return

    name = row[0]

    markup = InlineKeyboardMarkup()

    markup.add(
        InlineKeyboardButton(
            "✅ تأكيد الحذف",
            callback_data=f"confirm_del_{offer_id}"
        ),

        InlineKeyboardButton(
            "❌ إلغاء",
            callback_data="delete_offer"
        )
    )

    bot.send_message(
        call.message.chat.id,
f"""⚠️ تأكيد حذف العرض

━━━━━━━━━━━━━━━
🏷️ اسم العرض:
{name}
━━━━━━━━━━━━━━━

هل أنت متأكد من حذف هذا العرض؟""",
        reply_markup=markup
    )



@bot.callback_query_handler(func=lambda call: call.data == "change_cash")
def change_cash(call):
    if not bot_active:
        return

    user_states[call.from_user.id] = "cash"

    bot.send_message(
        call.message.chat.id,
        "💳 أرسل رقم الكاش الجديد لتحديث بيانات التحويل"
    )


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "cash")
def set_cash(message):
    global cash_number

    if not message.text.isdigit():
        bot.send_message(
            message.chat.id,
            "❌ الرقم غير صحيح\n\n📱 يرجى إرسال رقم كاش صالح"
        )
        return

    old = cash_number
    new = message.text

    cash_number = new

    user_states.pop(message.from_user.id)

    log(f"💳 تغيير الكاش: {new}")

    bot.send_message(
        message.chat.id,
f"""✅ تم تحديث رقم الكاش بنجاح

━━━━━━━━━━━━━━━
📱 الرقم القديم:
{old}

📱 الرقم الجديد:
{new}
━━━━━━━━━━━━━━━"""
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_del_"))
def confirm_delete(call):
    if not bot_active:
        return

    offer_id = call.data.replace("confirm_del_", "")

    cursor.execute(
        "SELECT name FROM offers WHERE id=?",
        (offer_id,)
    )

    row = cursor.fetchone()

    if not row:
        bot.send_message(
            call.message.chat.id,
            "❌ العرض المطلوب غير موجود"
        )
        return

    name = row[0]

    cursor.execute(
        "DELETE FROM offers WHERE id=?",
        (offer_id,)
    )

    conn.commit()

    log(f"🗑 تم حذف عرض: {name}")

    bot.send_message(
        call.message.chat.id,
f"""✅ تم حذف العرض بنجاح

━━━━━━━━━━━━━━━
🏷️ اسم العرض:
{name}
━━━━━━━━━━━━━━━"""
    )


@bot.callback_query_handler(func=lambda call: call.data == "search_user")
def search_user(call):
    if not bot_active:
        return

    user_states[call.from_user.id] = "search"

    bot.send_message(
        call.message.chat.id,
        "🔍 أرسل ID المستخدم المطلوب البحث عنه"
    )


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "search")
def do_search(message):
    if not message.text.isdigit():
        bot.send_message(
            message.chat.id,
            "❌ يرجى إرسال ID صحيح"
        )
        return

    uid = int(message.text)

    # ✅ تحقق من المستخدم من الداتا بيز
    cursor.execute(
        "SELECT user_id FROM users WHERE user_id=?",
        (uid,)
    )

    if not cursor.fetchone():
        bot.send_message(
            message.chat.id,
            "❌ المستخدم غير موجود داخل قاعدة البيانات"
        )
        return

    # ✅ جلب حالة الطلب من الداتا بيز
    cursor.execute(
        "SELECT status FROM requests WHERE user_id=?",
        (uid,)
    )

    row = cursor.fetchone()

    status = row[0] if row else "لا يوجد طلب"

    bot.send_message(
        message.chat.id,
f"""👤 بيانات المستخدم

━━━━━━━━━━━━━━━
🆔 ID:
{uid}

📊 حالة الطلب:
{status}
━━━━━━━━━━━━━━━"""
    )

    user_states.pop(message.from_user.id)


@bot.callback_query_handler(func=lambda call: call.data == "auto_reply")
def auto_reply(call):
    if not bot_active:
        return

    user_states[call.from_user.id] = "auto_q"

    bot.send_message(
        call.message.chat.id,
        "💬 أرسل الكلمة المفتاحية الخاصة بالرد التلقائي"
    )


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "auto_q")
def set_auto_q(message):
    user_data[message.from_user.id] = {"q": message.text}

    user_states[message.from_user.id] = "auto_a"

    bot.send_message(
        message.chat.id,
        "✉️ أرسل الرد الذي سيتم إرساله تلقائياً"
    )


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "auto_a")
def set_auto_a(message):
    q = user_data[message.from_user.id]["q"]

    auto_replies[q] = message.text

    user_states.pop(message.from_user.id)
    user_data.pop(message.from_user.id)

    bot.send_message(
        message.chat.id,
        "✅ تم حفظ الرد التلقائي بنجاح"
    )


@bot.message_handler(func=lambda message: message.text in auto_replies and message.from_user.id not in user_states)
def auto_reply_handler(message):
    bot.send_message(
        message.chat.id,
        auto_replies[message.text]
    )


@bot.callback_query_handler(func=lambda call: call.data == "msg_user")
def msg_user(call):
    if not bot_active:
        return

    user_states[call.from_user.id] = "msg_id"

    bot.send_message(
        call.message.chat.id,
        "👤 أرسل ID العضو الذي تريد مراسلته"
    )


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "msg_id")
def get_msg_user_id(message):
    if not message.text.isdigit():
        bot.send_message(
            message.chat.id,
            "❌ الـ ID غير صحيح"
        )
        return

    user_data[message.from_user.id] = {
        "id": int(message.text)
    }

    user_states[message.from_user.id] = "msg_text"

    bot.send_message(
        message.chat.id,
        "✉️ أرسل الرسالة التي تريد إرسالها للعضو"
    )


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "msg_text")
def send_private(message):
    uid = user_data[message.from_user.id]["id"]

    try:
        bot.send_message(uid, message.text)

        bot.send_message(
            message.chat.id,
            "✅ تم إرسال الرسالة للعضو بنجاح"
        )

    except:
        bot.send_message(
            message.chat.id,
            "❌ تعذر إرسال الرسالة للعضو"
        )

    user_states.pop(message.from_user.id)
    user_data.pop(message.from_user.id)


# ========== BAN ==========
@bot.callback_query_handler(func=lambda call: call.data == "ban_user")
def ban_user(call):
    if not bot_active:
        return

    user_states[call.from_user.id] = "ban"

    bot.send_message(
        call.message.chat.id,
        "🚫 أرسل ID العضو الذي تريد حظره"
    )


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "ban")
def do_ban(message):
    if not message.text.isdigit():
        bot.send_message(
            message.chat.id,
            "❌ يرجى إرسال ID صحيح"
        )
        return

    uid = int(message.text)

    # ✅ حفظ في الداتا بيز
    cursor.execute(
        "INSERT OR IGNORE INTO banned (user_id) VALUES (?)",
        (uid,)
    )

    conn.commit()

    log(f"🚫 حظر {uid}")

    try:
        bot.send_message(
            uid,
"""🚫 تم تقييد وصولك إلى IbrahimBet VIP

📩 إذا كنت تعتقد أن هذا بالخطأ يرجى التواصل مع الإدارة"""
        )
    except:
        pass

    bot.send_message(
        message.chat.id,
        "✅ تم حظر العضو بنجاح"
    )

    user_states.pop(message.from_user.id)


# ========== UNBAN ==========
@bot.callback_query_handler(func=lambda call: call.data == "unban_user")
def unban_user(call):
    if not bot_active:
        return

    user_states[call.from_user.id] = "unban"

    bot.send_message(
        call.message.chat.id,
        "🔓 أرسل ID العضو الذي تريد فك الحظر عنه"
    )


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "unban")
def do_unban(message):
    if not message.text.isdigit():
        bot.send_message(
            message.chat.id,
            "❌ يرجى إرسال ID صحيح"
        )
        return

    uid = int(message.text)

    # ✅ حذف من الداتا بيز
    cursor.execute(
        "DELETE FROM banned WHERE user_id=?",
        (uid,)
    )

    conn.commit()

    log(f"🔓 فك حظر {uid}")

    try:
        bot.send_message(
            uid,
"""✅ تم فك الحظر عن حسابك

🎉 يمكنك الآن استخدام جميع خدمات IbrahimBet VIP من جديد"""
        )
    except:
        pass

    bot.send_message(
        message.chat.id,
        "✅ تم فك حظر العضو بنجاح"
    )

    user_states.pop(message.from_user.id)


# ========== UNBAN ALL ==========
@bot.callback_query_handler(func=lambda call: call.data == "unban_all")
def unban_all(call):
    if not bot_active:
        return

    # ✅ حذف الكل من الداتا بيز
    cursor.execute("DELETE FROM banned")

    conn.commit()

    log("♻️ فك حظر الكل")

    bot.send_message(
        call.message.chat.id,
        "♻️ تم فك الحظر عن جميع الأعضاء بنجاح"
    )


# ========== LIST BANNED ==========
@bot.callback_query_handler(func=lambda call: call.data == "list_banned")
def list_banned(call):
    if not bot_active:
        return

    cursor.execute("SELECT user_id FROM banned")
    rows = cursor.fetchall()

    if not rows:
        bot.send_message(
            call.message.chat.id,
            "📋 لا يوجد أعضاء محظورين حالياً"
        )
        return

    text = "🚫 قائمة الأعضاء المحظورين\n\n"

    for r in rows:
        text += f"🆔 {r[0]}\n"

    bot.send_message(
        call.message.chat.id,
        text
    )


# ========== STOP BOT ==========
@bot.callback_query_handler(func=lambda call: call.data == "stop_bot")
def stop_bot(call):
    global bot_active

    # ✅ السماح للأدمن فقط
    if call.from_user.id != ADMIN_ID:
        return

    bot_active = False

    bot.answer_callback_query(call.id, "⛔ تم إيقاف البوت")

    bot.send_message(
        call.message.chat.id,
        "⛔ تم إيقاف خدمات IbrahimBet VIP"
    )


@bot.callback_query_handler(func=lambda call: call.data == "on_bot")
def start_bot(call):
    global bot_active

    if call.from_user.id != ADMIN_ID:
        return

    bot_active = True

    bot.answer_callback_query(call.id, "✅ تم تشغيل البوت")

    bot.send_message(
        call.message.chat.id,
        "✅ تم تشغيل خدمات IbrahimBet VIP بنجاح"
    )


@bot.callback_query_handler(func=lambda call: call.data == "top_offers")
def top_offers(call):
    if not bot_active:
        return

    # ✅ جلب البيانات من الداتا بيز
    cursor.execute("""
    SELECT offer_name, count 
    FROM stats 
    ORDER BY count DESC 
    LIMIT 5
    """)

    rows = cursor.fetchall()

    if not rows:
        bot.edit_message_text(
            "❌ لا توجد بيانات متاحة حالياً",
            call.message.chat.id,
            call.message.message_id
        )

        return

    text = "📈 أكثر العروض استخداماً داخل البوت\n\n"

    for name, count in rows:
        text += f"""🎯 {name}
📊 عدد الاستخدام: {count}

"""

    markup = InlineKeyboardMarkup()

    markup.add(
        InlineKeyboardButton("🔙 رجوع", callback_data="back_admin")
    )

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data == "all_requests")
def all_requests(call):
    if not bot_active:
        return

    # ✅ جلب الطلبات من الداتا بيز
    cursor.execute(
        "SELECT user_id, offer, status FROM requests"
    )

    rows = cursor.fetchall()

    if not rows:
        bot.send_message(
            call.message.chat.id,
            "❌ لا توجد طلبات حالياً"
        )

        return

    text = "🧾 جميع الطلبات الحالية\n\n"

    for uid, offer, status in rows:
        text += f"""👤 المستخدم:
{uid}

🎯 العرض:
{offer}

📊 الحالة:
{status}

━━━━━━━━━━━━━━━

"""

    bot.send_message(
        call.message.chat.id,
        text
    )


@bot.callback_query_handler(func=lambda call: call.data == "broadcast")
def broadcast(call):
    if not bot_active:
        return

    user_states[call.from_user.id] = "broadcast"

    bot.send_message(
        call.message.chat.id,
        "📢 أرسل الرسالة التي تريد إرسالها لجميع المستخدمين"
    )


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "broadcast")
def send_broadcast(message):
    success = 0
    fail = 0

    # ✅ نجيب المستخدمين من الداتا بيز
    cursor.execute("SELECT user_id FROM users")

    rows = cursor.fetchall()

    for row in rows:
        user_id = row[0]

        try:
            bot.send_message(user_id, message.text)
            success += 1

        except:
            fail += 1

    log(f"📢 إذاعة | نجح: {success} | فشل: {fail}")

    user_states.pop(message.from_user.id, None)

    bot.send_message(
        message.chat.id,
f"""✅ تم إرسال الرسالة الجماعية بنجاح

━━━━━━━━━━━━━━━
📤 تم الإرسال إلى:
{success} مستخدم

❌ فشل الإرسال إلى:
{fail} مستخدم
━━━━━━━━━━━━━━━"""
    )


@bot.callback_query_handler(func=lambda call: call.data == "stats")
def stats(call):
    if not bot_active:
        return

    send_stats(call, edit=True)


@bot.callback_query_handler(func=lambda call: call.data == "refresh_stats")
def refresh_stats(call):
    if not bot_active:
        return

    send_stats(call, edit=True)


def send_stats(call, edit=False):

    # ✅ من الداتا بيز
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM offers")
    total_offers = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM banned")
    total_banned = cursor.fetchone()[0]

    # ✅ الطلبات
    cursor.execute("SELECT status, amount FROM requests")
    rows = cursor.fetchall()

    total_requests = len(rows)

    pending = 0
    accepted = 0
    rejected = 0
    total_amount = 0

    for status, amount in rows:

        if status == "قيد المراجعة 🔍":
            pending += 1

        elif status == "تم القبول ✅":
            accepted += 1

            if str(amount).isdigit():
                total_amount += int(amount)

        elif status == "مرفوض ❌":
            rejected += 1

    # ✅ أفضل عرض
    cursor.execute(
        "SELECT offer_name FROM stats ORDER BY count DESC LIMIT 1"
    )

    row = cursor.fetchone()

    top_offer = row[0] if row else "لا يوجد"

    import datetime

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    text = f"""📊 إحصائيات IbrahimBet VIP

━━━━━━━━━━━━━━━
👥 إجمالي المستخدمين:
{total_users}

🚫 المحظورين:
{total_banned}

🎁 العروض المتاحة:
{total_offers}
━━━━━━━━━━━━━━━

📥 إجمالي الطلبات:
{total_requests}

⏳ قيد المراجعة:
{pending}

✅ الطلبات المقبولة:
{accepted}

❌ الطلبات المرفوضة:
{rejected}
━━━━━━━━━━━━━━━

💰 إجمالي الأرباح:
{total_amount} جنيه

📈 أكثر عرض استخداماً:
{top_offer}
━━━━━━━━━━━━━━━

🕒 آخر تحديث:
{now}
"""

    markup = InlineKeyboardMarkup()

    markup.add(
        InlineKeyboardButton("🔄 تحديث", callback_data="refresh_stats"),
        InlineKeyboardButton("🔙 رجوع", callback_data="back_admin")
    )

    if edit:
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )

    else:
        bot.send_message(
            call.message.chat.id,
            text,
            reply_markup=markup
        )


@bot.callback_query_handler(func=lambda call: call.data == "back_admin")
def back_admin(call):
    if not bot_active:
        return

    markup = InlineKeyboardMarkup(row_width=2)

    markup.add(
        InlineKeyboardButton("➕ إضافة عرض", callback_data="add_offer"),
        InlineKeyboardButton("➖ حذف عرض", callback_data="delete_offer"),
        InlineKeyboardButton("📊 الإحصائيات", callback_data="stats"),
        InlineKeyboardButton("📈 الأكثر استخدام", callback_data="top_offers"),
        InlineKeyboardButton("🧾 الطلبات", callback_data="all_requests"),
        InlineKeyboardButton("🔍 بحث عن مستخدم", callback_data="search_user"),
        InlineKeyboardButton("💬 رد تلقائي", callback_data="auto_reply"),
        InlineKeyboardButton("📢 رسالة جماعية", callback_data="broadcast"),
        InlineKeyboardButton("👤 مراسلة عضو", callback_data="msg_user"),
        InlineKeyboardButton("🚫 حظر عضو", callback_data="ban_user"),
        InlineKeyboardButton("🔓 فك الحظر", callback_data="unban_user"),
        InlineKeyboardButton("♻️ فك حظر الجميع", callback_data="unban_all"),
        InlineKeyboardButton("📋 قائمة المحظورين", callback_data="list_banned"),
        InlineKeyboardButton("💳 تغيير رقم الكاش", callback_data="change_cash"),
        InlineKeyboardButton("⛔ إيقاف البوت", callback_data="stop_bot"),
        InlineKeyboardButton("✅ تشغيل البوت", callback_data="start_bot")
    )

    bot.edit_message_text(
"""⚙️ لوحة تحكم IbrahimBet VIP

━━━━━━━━━━━━━━━
📊 إدارة كاملة للبوت
📈 متابعة الطلبات والإحصائيات
👥 التحكم في المستخدمين
━━━━━━━━━━━━━━━

اختر القسم المطلوب من القائمة 👇""",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )


@bot.message_handler(func=lambda message: message.text in auto_replies and message.from_user.id not in user_states)
def auto_reply_handler(message):

    bot.send_message(
        message.chat.id,
        auto_replies[message.text]
    )


@bot.message_handler(func=lambda m: True)
def fallback(message):
    user_id = message.from_user.id

    # لو المستخدم في نص عملية
    if user_states.get(user_id):

        bot.send_message(
            message.chat.id,
            "⚠️ يرجى إكمال الخطوة المطلوبة أولاً\n\n🔄 أو استخدم /start للبدء من جديد"
        )

        return

    else:
        bot.send_message(
            message.chat.id,
            "❌ الأمر غير معروف\n\n🚀 استخدم /start لفتح القائمة الرئيسية"
        )

# ========== RUN ==========
print("Bot Running...")
bot.infinity_polling(
    skip_pending=True,
    timeout=30,
    long_polling_timeout=30
)