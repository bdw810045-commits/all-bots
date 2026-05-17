# -*- coding: utf-8 -*-
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot.types import InputMediaPhoto
import sqlite3
import json

TOKEN = "8985256764:AAG-Op8Ro4sttVuH5WxLliJR_oRmEvcenUY"
ADMIN_ID = 5990930430  # الأدمن الأساسي (لازم يكون ضمن ADMIN_IDS)
CHANNEL_ID = -1003773315482

# كل الأدمنز
ADMIN_IDS = [8306879296]

# الأدمن اللي يستقبل الطلبات حالياً
ACTIVE_ADMIN = ADMIN_IDS[0]  # دايماً أول أدمن في الليست

bot_active = True
blocked_users = set()

bot = telebot.TeleBot(TOKEN)

users = set()
user_last_status = {}
user_state = {}
pending_requests = {}

user_total_requests = {}
user_deposit_count = {}
user_withdraw_count = {}

from datetime import datetime

transactions = []  # هنخزن كل العمليات هنا

deposit_stats = []
withdraw_stats = []

BONUS_PERCENT = 5      # نسبة البونص
BONUS_MIN = 200       # أقل إيداع
BONUS_MAX = None      # سيبها None = مفيش حد أقصى

import sqlite3

conn = sqlite3.connect("bot.db", check_same_thread=False)

# ❌ تم حذف users / requests / transactions

# settings
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")
conn.commit()

def db_execute(query, params=(), fetchone=False, fetchall=False):
    cursor = conn.cursor()
    cursor.execute(query, params)

    if fetchone:
        return cursor.fetchone()

    if fetchall:
        return cursor.fetchall()

    conn.commit()


# 🔥 تحميل المدينة
row_city = db_execute(
    "SELECT value FROM settings WHERE key='withdraw_city_1xbet'",
    fetchone=True
)

if row_city:
    WITHDRAW_CITY_1XBET = row_city[0]
else:
    WITHDRAW_CITY_1XBET = "Cairo"


# 🔥 تحميل الشارع
row_street = db_execute(
    "SELECT value FROM settings WHERE key='withdraw_street_1xbet'",
    fetchone=True
)

if row_street:
    WITHDRAW_STREET_1XBET = row_street[0]
else:
    WITHDRAW_STREET_1XBET = "Gold cash3"
# ================= START =================
def safe_send_message(chat_id, text):
    try:
        bot.send_message(chat_id, text)
    except:
        pass

@bot.message_handler(commands=['start'])
def start(msg):
    user_id = msg.from_user.id

    # 🧹 إلغاء أي عملية شغالة
    user_state.pop(user_id, None)
    pending_requests.pop(user_id, None)

    if user_id in blocked_users:
        return

    if not bot_active and user_id not in ADMIN_IDS:
        bot.send_message(msg.chat.id, "⛔ خدمات IbrahimBet متوقفة حالياً")
        return

    # ✅ تحقق هل المستخدم جديد
    is_new = user_id not in users
    users.add(user_id)

    # 🔥 إشعار الأدمن
    if is_new:
        full_name = msg.from_user.first_name or "لا يوجد"
        username = f"@{msg.from_user.username}" if msg.from_user.username else "لا يوجد"

        from datetime import datetime
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        kb_admin = InlineKeyboardMarkup()
        kb_admin.add(
            InlineKeyboardButton(
                "👤 فتح حساب العميل",
                url=f"tg://user?id={user_id}"
            )
        )

        bot.send_message(
            ADMIN_ID,
            f"""🚀 عميل جديد انضم إلى البوت

━━━━━━━━━━━━━━━
👤 الاسم: {full_name}
💬 اليوزر: {username}
🆔 الايدي: {user_id}
🕒 وقت الدخول: {now_str}
━━━━━━━━━━━━━━━

📊 إجمالي العملاء: {len(users)}
""",
            reply_markup=kb_admin
        )

    # 📌 كيبورد المستخدم
    kb = InlineKeyboardMarkup()

    kb.add(
        InlineKeyboardButton("📥 شحن حساب", callback_data="deposit"),
        InlineKeyboardButton("📤 سحب أرباح", callback_data="withdraw")
    )

    kb.add(
        InlineKeyboardButton("📊 حالة الطلب", callback_data="status")
    )

    kb.add(
        InlineKeyboardButton("👤 حسابي", callback_data="profile"),
        InlineKeyboardButton("🎟 Promo Codes", callback_data="promo")
    )

    kb.add(
        InlineKeyboardButton("📢 قناة IbrahimBet", url="https://t.me/+7X48pwS1V38yY2U0")
    )

    bot.send_message(
        msg.chat.id,
        """👋 أهلاً بيك في IbrahimBet VIP

💳 خدمات شحن وسحب 
1xebt

⚡ تنفيذ سريع وآمن للطلبات

🎁 عروض وبونصات يومية حصرية

اختر الخدمة المطلوبة من القائمة بالأسفل 👇""",
        reply_markup=kb
    )

# ================= WITHDRAW BUTTON =================
@bot.callback_query_handler(func=lambda c: c.data == "withdraw")
def withdraw(c):

    if c.from_user.id in pending_requests:
        bot.answer_callback_query(
            c.id,
            "⏳ لديك طلب قيد المراجعة حالياً"
        )
        return

    kb = InlineKeyboardMarkup()

    kb.add(
        InlineKeyboardButton(
            "1XBET 🎯",
            callback_data="w_1XBET"
        )
    )

    # زر الرجوع
    kb.add(
        InlineKeyboardButton(
            "🔙 القائمة الرئيسية",
            callback_data="home"
        )
    )

    try:
        bot.edit_message_text(
            "🏧 اختر المنصة المطلوبة لإتمام عملية السحب 👇",
            c.message.chat.id,
            c.message.message_id,
            reply_markup=kb
        )

    except:
        bot.send_message(
            c.message.chat.id,
            "🏧 اختر المنصة المطلوبة لإتمام عملية السحب 👇",
            reply_markup=kb
        )


# ================= CHOOSE APP =================
@bot.callback_query_handler(func=lambda c: c.data == "w_1XBET")
def choose_withdraw_app(c):

    if c.from_user.id in pending_requests:
        bot.answer_callback_query(
            c.id,
            "⏳ لديك طلب قيد المراجعة حالياً"
        )
        return

    # حفظ حالة المستخدم
    user_state[c.from_user.id] = {
        "type": "withdraw",
        "step": "start",
        "app": "1XBET"
    }

    kb = InlineKeyboardMarkup()

    kb.add(
        InlineKeyboardButton(
            "✅ متابعة الطلب",
            callback_data="w_complete"
        )
    )

    # زر الرجوع
    kb.add(
        InlineKeyboardButton(
            "🔙 القائمة الرئيسية",
            callback_data="home"
        )
    )

    text = f"""🏧 تم تحديد نقطة السحب بنجاح

━━━━━━━━━━━━━━━
🏙️ المدينة :
{WITHDRAW_CITY_1XBET}

📍 الشارع :
{WITHDRAW_STREET_1XBET}
━━━━━━━━━━━━━━━

اضغط متابعة لإكمال الطلب 👇"""

    try:
        bot.edit_message_text(
            text,
            c.message.chat.id,
            c.message.message_id,
            reply_markup=kb
        )

    except:
        bot.send_message(
            c.message.chat.id,
            text,
            reply_markup=kb
        )


# ================= COMPLETE =================
@bot.callback_query_handler(func=lambda c: c.data == "w_complete")
def withdraw_complete(c):
    user_id = c.from_user.id

    if user_id not in user_state:
        return

    if user_state[user_id].get("type") != "withdraw":
        return

    user_state[user_id]["step"] = "code"

    bot.edit_message_text(
        "🔐 أرسل كود السحب الذي تم إنشاؤه من التطبيق",
        c.message.chat.id,
        c.message.message_id
    )


# ================= WITHDRAW TEXT =================
@bot.message_handler(func=lambda m: m.from_user.id in user_state and user_state[m.from_user.id].get("type") == "withdraw")
def withdraw_steps(m):
    user_id = m.from_user.id
    data = user_state[user_id]

    step = data["step"]

    # ================= CODE =================
    if step == "code":
        if not m.text:
            bot.send_message(m.chat.id, "❌ يرجى إرسال كود السحب بشكل صحيح")
            return

        data["code"] = m.text.strip()
        data["step"] = "amount"

        bot.send_message(m.chat.id, "💵 أرسل قيمة المبلغ المطلوب سحبه")

    # ================= AMOUNT =================
    elif step == "amount":
        try:
            amount = int(m.text)
            if amount < 30:
                bot.send_message(m.chat.id, "❌ الحد الأدنى للسحب هو 30 جنيه")
                return

            data["amount"] = amount
            data["step"] = "account"

            bot.send_message(m.chat.id, "🆔 أرسل ID الحساب")
        except:
            bot.send_message(m.chat.id, "❌ يرجى إرسال رقم صحيح")

   # ================= ACCOUNT =================
    elif step == "account":
        if not m.text:
            bot.send_message(m.chat.id, "❌ يرجى إرسال ID الحساب بشكل صحيح")
            return

        data["account_id"] = m.text.strip()
        data["step"] = "phone"

        bot.send_message(m.chat.id, "📱 أرسل رقم الكاش الذي ترغب باستلام السحب عليه")

    # ================= PHONE =================
    elif step == "phone":
        if not (m.text and m.text.isdigit() and len(m.text) == 11):
            bot.send_message(m.chat.id, "❌ رقم الكاش غير صحيح")
            return

        data["phone"] = m.text

        pending_requests[user_id] = data

        # 📊 تسجيل العملية
        transactions.append({
            "type": "withdraw",
            "amount": data["amount"],
            "status": "pending",
            "time": datetime.now()
        })

        user_last_status[user_id] = "⏳ قيد المراجعة"
        user_total_requests[user_id] = user_total_requests.get(user_id, 0) + 1
        user_withdraw_count[user_id] = user_withdraw_count.get(user_id, 0) + 1

        bot.send_message(
            m.chat.id,
            """⏳ تم استلام طلب السحب بنجاح

📨 الطلب الآن قيد المراجعة من فريق IbrahimBet VIP
⚡ سيتم تنفيذ العملية في أقرب وقت ممكن"""
        )

        username = f"@{m.from_user.username}" if m.from_user.username else "لا يوجد"

        caption = f"""📤 <b>طلب سحب جديد | IbrahimBet VIP</b>

━━━━━━━━━━━━━━━━━━━━
👤 <b>بيانات العميل</b>
━━━━━━━━━━━━━━━━━━━━
🆔 ID:
<code>{user_id}</code>

📛 Username:
{username}

━━━━━━━━━━━━━━━━━━━━
💸 <b>تفاصيل العملية</b>
━━━━━━━━━━━━━━━━━━━━
🎯 التطبيق:
{data['app']}

🔐 كود السحب:
<code>{data['code']}</code>

💵 المبلغ:
<b>{data['amount']} جنيه</b>

🆔 ID الحساب:
<code>{data['account_id']}</code>

📱 رقم الكاش:
<code>{data['phone']}</code>
"""

        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton("✅ قبول", callback_data=f"w_accept_{user_id}"),
            InlineKeyboardButton("❌ رفض", callback_data=f"w_reject_{user_id}")
        )

        admin_msg = bot.send_message(
            ACTIVE_ADMIN,
            caption,
            reply_markup=kb,
            parse_mode="HTML"
        )
        data["admin_msg_id"] = admin_msg.message_id

        ch_msg = bot.send_message(
            CHANNEL_ID,
            caption + "\n━━━━━━━━━━━━━━━━━━━━\n📊 الحالة الحالية: ⏳ قيد المراجعة",
            parse_mode="HTML"
        )
        data["channel_msg_id"] = ch_msg.message_id

        del user_state[user_id]


# ================= ACCEPT =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("w_accept_"))
def w_accept(c):
    user_id = int(c.data.split("_")[2])

    if user_id not in pending_requests:
        return

    data = pending_requests[user_id]
    admin_name = c.from_user.first_name

    # تحديث الإحصائيات
    for t in reversed(transactions):
        if t["status"] == "pending":
            t["status"] = "accepted"
            break

    user_last_status[user_id] = "✅ تم القبول"

    bot.send_message(
        user_id,
        """✅ تم تنفيذ طلب السحب بنجاح

💸 تم تحويل المبلغ الخاص بك بنجاح
⚡ شكراً لاستخدامك خدمات IbrahimBet VIP

#IbrahimBet"""
    )

    bot.edit_message_text(
        f"""✅ تم قبول الطلب

🆔 ID: {user_id}

👑 بواسطة الأدمن:
{admin_name}""",
        ACTIVE_ADMIN,
        data["admin_msg_id"]
    )

    caption = f"""📤 طلب سحب | IbrahimBet VIP

━━━━━━━━━━━━━━━━━━━━
👤 بيانات العميل
━━━━━━━━━━━━━━━━━━━━
🆔 ID: {user_id}

━━━━━━━━━━━━━━━━━━━━
💸 تفاصيل العملية
━━━━━━━━━━━━━━━━━━━━
🎯 التطبيق: {data['app']}

🔐 كود السحب:
{data['code']}

💵 المبلغ:
{data['amount']} جنيه

🆔 ID الحساب:
{data['account_id']}

📱 رقم الكاش:
{data['phone']}

━━━━━━━━━━━━━━━━━━━━
📊 الحالة: ✅ تم القبول
"""

    bot.edit_message_text(caption, CHANNEL_ID, data["channel_msg_id"])

    del pending_requests[user_id]


# ================= REJECT =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("w_reject_"))
def w_reject(c):
    user_id = int(c.data.split("_")[2])

    if user_id not in pending_requests:
        return

    data = pending_requests[user_id]
    admin_name = c.from_user.first_name

    # تحديث الإحصائيات
    for t in reversed(transactions):
        if t["status"] == "pending":
            t["status"] = "rejected"
            break

    user_last_status[user_id] = "❌ تم الرفض"

    bot.send_message(
        user_id,
        """❌ تعذر تنفيذ طلب السحب

⚠️ يرجى التأكد من صحة البيانات المرسلة
📩 في حالة وجود مشكلة تواصل مع الدعم

#IbrahimBet"""
    )

    bot.edit_message_text(
        f"""❌ تم رفض الطلب

🆔 ID: {user_id}

👑 بواسطة الأدمن:
{admin_name}""",
        ACTIVE_ADMIN,
        data["admin_msg_id"]
    )

    bot.edit_message_text(
        "📊 الحالة الحالية: ❌ تم رفض الطلب",
        CHANNEL_ID,
        data["channel_msg_id"]
    )

    del pending_requests[user_id]


# ================= DEPOSIT =================
@bot.callback_query_handler(func=lambda c: c.data == "deposit")
def deposit(c):
    if c.from_user.id in pending_requests:
        bot.answer_callback_query(c.id, "⏳ لديك طلب قيد المراجعة حالياً")
        return

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("1XBET 🎯", callback_data="app_1XBET"))

    # ✅ زر الرجوع
    kb.add(InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="home"))

    try:
        bot.edit_message_text(
            "💳 اختر المنصة المطلوبة لإتمام عملية الشحن 👇",
            c.message.chat.id,
            c.message.message_id,
            reply_markup=kb
        )
    except:
        bot.send_message(
            c.message.chat.id,
            "💳 اختر المنصة المطلوبة لإتمام عملية الشحن 👇",
            reply_markup=kb
        )

# ================= CHOOSE DEPOSIT APP =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("app_"))
def choose_deposit_app(c):
    if c.from_user.id in pending_requests:
        bot.answer_callback_query(c.id, "⏳ لديك طلب قيد المراجعة حالياً")
        return

    app = c.data.split("_")[1]

    user_state[c.from_user.id] = {
        "type": "deposit",
        "step": "start",
        "app": app
    }

    text = f"""💳 بيانات التحويل | IbrahimBet VIP

━━━━━━━━━━━━━━━━━━
📱 رقم الكاش:
{CASH_NUMBER}
━━━━━━━━━━━━━━━━━━

📌 قم بتحويل المبلغ المطلوب
ثم اضغط على متابعة العملية 👇"""

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✅ متابعة العملية", callback_data="complete"))
    kb.add(InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="home"))

    try:
        bot.edit_message_text(
            text,
            c.message.chat.id,
            c.message.message_id,
            reply_markup=kb
        )
    except:
        bot.send_message(
            c.message.chat.id,
            text,
            reply_markup=kb
        )

# ================= COMPLETE =================
@bot.callback_query_handler(func=lambda c: c.data == "complete")
def complete(c):
    user_state[c.from_user.id]["step"] = "amount"

    bot.edit_message_text(
        "💵 أرسل المبلغ الذي قمت بتحويله\n\n🔻 الحد الأدنى للإيداع: 10 جنيه",
        c.message.chat.id,
        c.message.message_id
    )


# ================= TEXT =================
@bot.message_handler(func=lambda m: m.text and not m.text.startswith("/") and (m.from_user.id not in user_state or not user_state[m.from_user.id].get("admin")))
def handle_text(m):
    user_id = m.from_user.id

    if user_id in user_state and user_state[user_id].get("admin"):
        return

    if user_id in user_state and user_state[user_id].get("type") == "withdraw":
        return

    if user_id not in user_state:
        return

    step = user_state[user_id]["step"]

    if step == "amount":
        try:
            amount = int(m.text)
            if amount < 10:
                bot.send_message(m.chat.id, "❌ الحد الأدنى للإيداع هو 10 جنيه")
                return

            user_state[user_id]["amount"] = amount
            user_state[user_id]["step"] = "phone"

            bot.send_message(m.chat.id, "📱 أرسل رقم الكاش الذي قمت بالتحويل منه")
        except:
            bot.send_message(m.chat.id, "❌ يرجى إرسال رقم صحيح")

    elif step == "phone":
        if not (m.text.isdigit() and len(m.text) == 11):
            bot.send_message(m.chat.id, "❌ رقم الهاتف يجب أن يكون 11 رقم")
            return

        user_state[user_id]["phone"] = m.text
        user_state[user_id]["step"] = "photo"

        bot.send_message(m.chat.id, "📸 أرسل صورة أو لقطة شاشة للتحويل")

    elif step == "photo":
        bot.send_message(m.chat.id, "❌ يرجى إرسال صورة التحويل وليس رسالة نصية")

    elif step == "account":
        data = user_state[user_id]

        if "photo" not in data:
            bot.send_message(m.chat.id, "❌ يجب إرسال صورة التحويل أولاً")
            data["step"] = "photo"
            return

        data["account_id"] = m.text

        pending_requests[user_id] = data

        transactions.append({
            "type": "deposit",
            "amount": data["amount"],
            "status": "pending",
            "time": datetime.now()
        })

        user_last_status[user_id] = "⏳ قيد المراجعة"
        user_total_requests[user_id] = user_total_requests.get(user_id, 0) + 1
        user_deposit_count[user_id] = user_deposit_count.get(user_id, 0) + 1

        bot.send_message(
            m.chat.id,
            """⏳ تم استلام طلب الإيداع بنجاح

📨 طلبك الآن قيد المراجعة بواسطة فريق IbrahimBet VIP
⚡ متوسط وقت التنفيذ من 1 إلى 10 دقائق"""
        )

        username = "@" + m.from_user.username if m.from_user.username else "لا يوجد"

        caption = f"""📥 <b>طلب إيداع جديد | IbrahimBet VIP</b>

━━━━━━━━━━━━━━━━━━━━
👤 <b>بيانات العميل</b>
━━━━━━━━━━━━━━━━━━━━
🆔 ID:
<code>{user_id}</code>

📛 Username:
{username}

━━━━━━━━━━━━━━━━━━━━
💳 <b>تفاصيل العملية</b>
━━━━━━━━━━━━━━━━━━━━
🎯 التطبيق:
{data['app']}

🆔 ID الحساب:
<code>{data['account_id']}</code>

📱 رقم الكاش:
<code>{data['phone']}</code>

💵 المبلغ:
<b>{data['amount']} جنيه</b>
"""

        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton("✅ قبول", callback_data=f"accept_{user_id}"),
            InlineKeyboardButton("❌ رفض", callback_data=f"reject_{user_id}")
        )

        admin_msg = bot.send_photo(
            ACTIVE_ADMIN,
            data["photo"],
            caption=caption,
            reply_markup=kb,
            parse_mode="HTML"
        )
        data["admin_msg_id"] = admin_msg.message_id

        ch_msg = bot.send_photo(
            CHANNEL_ID,
            data["photo"],
            caption=caption + "\n━━━━━━━━━━━━━━━━━━━━\n📊 الحالة الحالية: ⏳ قيد المراجعة",
            parse_mode="HTML"
        )
        data["channel_msg_id"] = ch_msg.message_id

        del user_state[user_id]


@bot.message_handler(content_types=['photo'])
def handle_photo(m):
    user_id = m.from_user.id

    if user_id not in user_state:
        return

    data = user_state[user_id]

    if data.get("admin"):
        return

    if data.get("step") != "photo":
        return

    data["photo"] = m.photo[-1].file_id
    data["step"] = "account"

    bot.send_message(m.chat.id, "🆔 أرسل ID الحساب الذي ترغب بالشحن عليه")


# ================= ACCEPT =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("accept_"))
def accept(c):
    user_id = int(c.data.split("_")[1])

    if user_id not in pending_requests:
        return

    data = pending_requests[user_id]
    admin_name = c.from_user.first_name

    # تحديث الإحصائيات
    for t in reversed(transactions):
        if t["status"] == "pending":
            t["status"] = "accepted"
            break

    user_last_status[user_id] = "✅ تم القبول"

    bot.send_message(
        user_id,
        """✅ تم تنفيذ عملية الإيداع بنجاح

💳 تم شحن الحساب الخاص بك
⚡ شكراً لاستخدامك خدمات IbrahimBet VIP

#IbrahimBet"""
    )

    bot.edit_message_caption(
        chat_id=ACTIVE_ADMIN,
        message_id=data["admin_msg_id"],
        caption=f"""✅ تم قبول الطلب

🆔 ID: {user_id}

👑 بواسطة الأدمن:
{admin_name}"""
    )

    caption = f"""📥 طلب إيداع | IbrahimBet VIP

━━━━━━━━━━━━━━━━━━━━
👤 بيانات العميل
━━━━━━━━━━━━━━━━━━━━
🆔 ID: {user_id}

━━━━━━━━━━━━━━━━━━━━
💳 تفاصيل العملية
━━━━━━━━━━━━━━━━━━━━
🎯 التطبيق: {data['app']}

🆔 ID الحساب:
{data['account_id']}

📱 رقم الكاش:
{data['phone']}

💵 المبلغ:
{data['amount']} جنيه

━━━━━━━━━━━━━━━━━━━━
📊 الحالة: ✅ تم القبول
"""

    bot.edit_message_caption(
        chat_id=CHANNEL_ID,
        message_id=data["channel_msg_id"],
        caption=caption
    )

    del pending_requests[user_id]


# ================= REJECT =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("reject_"))
def reject(c):
    user_id = int(c.data.split("_")[1])

    if user_id not in pending_requests:
        return

    data = pending_requests[user_id]
    admin_name = c.from_user.first_name

    # تحديث الإحصائيات
    for t in reversed(transactions):
        if t["status"] == "pending":
            t["status"] = "rejected"
            break

    user_last_status[user_id] = "❌ تم الرفض"

    bot.send_message(
        user_id,
        """❌ تم رفض عملية الإيداع

⚠️ يرجى مراجعة بيانات التحويل المرسلة
📩 في حالة وجود أي مشكلة تواصل مع الدعم

#IbrahimBet"""
    )

    bot.edit_message_caption(
        chat_id=ACTIVE_ADMIN,
        message_id=data["admin_msg_id"],
        caption=f"""❌ تم رفض الطلب

🆔 ID: {user_id}

👑 بواسطة الأدمن:
{admin_name}"""
    )

    caption = f"""📥 طلب إيداع | IbrahimBet VIP

━━━━━━━━━━━━━━━━━━━━
👤 بيانات العميل
━━━━━━━━━━━━━━━━━━━━
🆔 ID: {user_id}

━━━━━━━━━━━━━━━━━━━━
💳 تفاصيل العملية
━━━━━━━━━━━━━━━━━━━━
🎯 التطبيق: {data['app']}

🆔 ID الحساب:
{data['account_id']}

📱 رقم الكاش:
{data['phone']}

💵 المبلغ:
{data['amount']} جنيه

━━━━━━━━━━━━━━━━━━━━
📊 الحالة: ❌ تم الرفض
"""

    bot.edit_message_caption(
        chat_id=CHANNEL_ID,
        message_id=data["channel_msg_id"],
        caption=caption
    )

    del pending_requests[user_id]


# ================= BONUS =================

BONUS_PERCENT = 5
BONUS_MIN = 200
BONUS_MAX = None  # لو عايز تضيف حد أقصى حط رقم بدل None

@bot.callback_query_handler(func=lambda c: c.data == "bonus")
def bonus(c):
    text = f"""🎁 عروض وبونص IbrahimBet VIP

━━━━━━━━━━━━━━━━━━
💸 نسبة البونص الحالية:
{BONUS_PERCENT}%

📥 الحد الأدنى للحصول على البونص:
{BONUS_MIN} جنيه"""

    if BONUS_MAX:
        text += f"\n📤 الحد الأقصى للبونص:\n{BONUS_MAX} جنيه"

    text += "\n━━━━━━━━━━━━━━━━━━\n🔥 استمتع بعروض يومية حصرية"

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="home"))

    bot.edit_message_text(
        text,
        c.message.chat.id,
        c.message.message_id,
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda c: c.data == "status")
def status(c):
    user_id = c.from_user.id

    if user_id not in user_last_status:
        text = """📊 حالة الطلبات

❌ لا يوجد لديك أي طلبات حالياً"""
    else:
        text = f"""📊 حالة طلبك الحالي

━━━━━━━━━━━━━━━━━━
{user_last_status[user_id]}
━━━━━━━━━━━━━━━━━━"""

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="home"))

    bot.edit_message_text(
        text,
        c.message.chat.id,
        c.message.message_id,
        reply_markup=kb
    )


# ================= BACK TO HOME =================
@bot.callback_query_handler(func=lambda c: c.data == "home")
def back_home(c):
    kb = InlineKeyboardMarkup()

    kb.add(
        InlineKeyboardButton("📥 شحن حساب", callback_data="deposit"),
        InlineKeyboardButton("📤 سحب أرباح", callback_data="withdraw")
    )

    kb.add(
        InlineKeyboardButton("📊 حالة الطلب", callback_data="status")
    )

    kb.add(
        InlineKeyboardButton("👤 حسابي", callback_data="profile"),
        InlineKeyboardButton("🎟 Promo Codes", callback_data="promo")
    )

    kb.add(
        InlineKeyboardButton("📢 قناة IbrahimBet", url="https://t.me/+7X48pwS1V38yY2U0")
    )

    text = """👋 أهلاً بيك في IbrahimBet VIP

💳 خدمات شحن وسحب 
1xebt

⚡ تنفيذ سريع وآمن للطلبات

🎁 عروض وبونصات يومية حصرية

اختر الخدمة المطلوبة من القائمة بالأسفل 👇"""

    try:
        if c.message.content_type == "text":
            bot.edit_message_text(
                text,
                c.message.chat.id,
                c.message.message_id,
                reply_markup=kb
            )
        else:
            bot.edit_message_caption(
                chat_id=c.message.chat.id,
                message_id=c.message.message_id,
                caption=text,
                reply_markup=kb
            )
    except:
        bot.send_message(c.message.chat.id, text, reply_markup=kb)


@bot.callback_query_handler(func=lambda c: c.data == "profile")
def profile(c):
    user_id = c.from_user.id

    total = user_total_requests.get(user_id, 0)
    dep = user_deposit_count.get(user_id, 0)
    wit = user_withdraw_count.get(user_id, 0)

    text = f"""👤 الملف الشخصي | IbrahimBet VIP

━━━━━━━━━━━━━━━━━━
🆔 ID:
{user_id}

📊 إجمالي الطلبات:
{total}

📥 عدد الإيداعات:
{dep}

📤 عدد السحوبات:
{wit}
━━━━━━━━━━━━━━━━━━"""

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="home"))

    try:
        photos = bot.get_user_profile_photos(user_id)

        if photos.total_count > 0:
            photo = photos.photos[0][-1].file_id

            media = InputMediaPhoto(media=photo, caption=text)

            bot.edit_message_media(
                media=media,
                chat_id=c.message.chat.id,
                message_id=c.message.message_id,
                reply_markup=kb
            )
        else:
            raise Exception()

    except:
        bot.edit_message_text(
            text,
            c.message.chat.id,
            c.message.message_id,
            reply_markup=kb
        )   


@bot.callback_query_handler(func=lambda c: c.data == "admin_home")
def admin_home(c):
    if c.from_user.id not in ADMIN_IDS:
        return

    kb = InlineKeyboardMarkup()

    kb.add(
        InlineKeyboardButton("💳 تغيير رقم الكاش", callback_data="admin_cash"),
        InlineKeyboardButton("🏧 تغيير نقطة السحب", callback_data="change_withdraw")
    )

    kb.add(InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats"))

    kb.add(
        InlineKeyboardButton("⛔ إيقاف البوت", callback_data="admin_stop"),
        InlineKeyboardButton("✅ تشغيل البوت", callback_data="admin_start")
    )

    kb.add(
        InlineKeyboardButton("📢 رسالة جماعية", callback_data="admin_broadcast"),
        InlineKeyboardButton("📩 مراسلة عميل", callback_data="admin_msg")
    )

    kb.add(
        InlineKeyboardButton("➕ إضافة أدمن", callback_data="admin_add"),
        InlineKeyboardButton("➖ حذف أدمن", callback_data="admin_remove")
    )

    kb.add(
        InlineKeyboardButton("📋 قائمة الأدمن", callback_data="admin_list")
    )

    kb.add(
        InlineKeyboardButton("🚫 حظر عضو", callback_data="admin_ban"),
        InlineKeyboardButton("♻️ فك الحظر", callback_data="admin_unban")
    )

    kb.add(
        InlineKeyboardButton("👤 تحويل الطلبات", callback_data="set_admin_2"),
        InlineKeyboardButton("👑 استلام الطلبات", callback_data="set_admin_1")
    )

    kb.add(
        InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="home")
    )

    try:
        bot.edit_message_text(
            "⚙️ لوحة تحكم IbrahimBet VIP",
            c.message.chat.id,
            c.message.message_id,
            reply_markup=kb
        )
    except:
        bot.send_message(
            c.message.chat.id,
            "⚙️ لوحة تحكم IbrahimBet VIP",
            reply_markup=kb
        )


# ================= ADMIN PANEL =================

@bot.message_handler(commands=['admin'])
def admin_panel(m):
    if m.from_user.id not in ADMIN_IDS:
        return

    kb = InlineKeyboardMarkup()

    kb.add(
        InlineKeyboardButton("💳 تغيير رقم الكاش", callback_data="admin_cash"),
        InlineKeyboardButton("🏧 تغيير نقطة السحب", callback_data="change_withdraw")
    )

    kb.add(InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats"))

    kb.add(
        InlineKeyboardButton("⛔ إيقاف البوت", callback_data="admin_stop"),
        InlineKeyboardButton("✅ تشغيل البوت", callback_data="admin_start")
    )

    kb.add(
        InlineKeyboardButton("📢 رسالة جماعية", callback_data="admin_broadcast"),
        InlineKeyboardButton("📩 مراسلة عميل", callback_data="admin_msg")
    )

    kb.add(
        InlineKeyboardButton("➕ إضافة أدمن", callback_data="admin_add"),
        InlineKeyboardButton("➖ حذف أدمن", callback_data="admin_remove")
    )

    kb.add(
        InlineKeyboardButton("📋 قائمة الأدمن", callback_data="admin_list")
    )

    kb.add(
        InlineKeyboardButton("🚫 حظر عضو", callback_data="admin_ban"),
        InlineKeyboardButton("♻️ فك الحظر", callback_data="admin_unban")
    )

    kb.add(
        InlineKeyboardButton("👤 تحويل الطلبات", callback_data="set_admin_2"),
        InlineKeyboardButton("👑 استلام الطلبات", callback_data="set_admin_1")
    )

    kb.add(
        InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="home")
    )

    bot.send_message(
        m.chat.id,
        "⚙️ لوحة تحكم IbrahimBet VIP",
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda c: c.data == "set_admin_2")
def set_admin2(c):
    global ACTIVE_ADMIN

    if c.from_user.id not in ADMIN_IDS:
        return

    ACTIVE_ADMIN = 6569294790  # حط ايدي الأدمن التاني هنا

    bot.send_message(
        c.message.chat.id,
        "✅ تم تحويل جميع الطلبات إلى الأدمن الآخر بنجاح"
    )


@bot.callback_query_handler(func=lambda c: c.data == "set_admin_1")
def set_admin1(c):
    global ACTIVE_ADMIN

    if c.from_user.id not in ADMIN_IDS:
        return

    ACTIVE_ADMIN = ADMIN_ID

    bot.send_message(
        c.message.chat.id,
        "👑 تم استلام الطلبات مرة أخرى بنجاح"
    )


# ================= CHANGE WITHDRAW =================
@bot.callback_query_handler(func=lambda c: c.data == "change_withdraw")
def change_withdraw(c):

    if c.from_user.id not in ADMIN_IDS:
        return

    user_state[c.from_user.id] = {
        "admin": True,
        "step": "withdraw_city"
    }

    bot.send_message(
        c.message.chat.id,
        "🏙️ أرسل المدينة الجديدة الخاصة بـ 1XBET"
    )


# ================= SET CITY =================
@bot.message_handler(func=lambda m:
    m.from_user.id in user_state
    and user_state[m.from_user.id].get("admin")
    and user_state[m.from_user.id].get("step") == "withdraw_city"
)
def set_withdraw_city(m):

    user_state[m.from_user.id]["city"] = m.text
    user_state[m.from_user.id]["step"] = "withdraw_street"

    bot.send_message(
        m.chat.id,
        "📍 أرسل الشارع الجديد الخاص بـ 1XBET"
    )


# ================= SET STREET =================
@bot.message_handler(func=lambda m:
    m.from_user.id in user_state
    and user_state[m.from_user.id].get("admin")
    and user_state[m.from_user.id].get("step") == "withdraw_street"
)
def set_withdraw_street(m):

    global WITHDRAW_CITY_1XBET
    global WITHDRAW_STREET_1XBET

    city = user_state[m.from_user.id]["city"]
    street = m.text

    WITHDRAW_CITY_1XBET = city
    WITHDRAW_STREET_1XBET = street

    # حفظ المدينة
    db_execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        ("withdraw_city_1xbet", city)
    )

    # حفظ الشارع
    db_execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        ("withdraw_street_1xbet", street)
    )

    bot.send_message(
        m.chat.id,
        f"""✅ تم تحديث نقطة السحب بنجاح

🏙️ المدينة:
{city}

📍 الشارع:
{street}"""
    )

    del user_state[m.from_user.id]

# ================= CASH =================
@bot.callback_query_handler(func=lambda c: c.data == "admin_cash")
def change_cash(c):
    if c.from_user.id not in ADMIN_IDS:
        return

    user_state[c.from_user.id] = {"admin": True, "step": "cash"}

    bot.send_message(
        c.message.chat.id,
        "📱 أرسل رقم الكاش الجديد\n\n⚠️ يجب أن يكون الرقم مكوّن من 11 رقم"
    )


# 🔥 تحميل الكاش من DB
row = db_execute(
    "SELECT value FROM settings WHERE key='cash'",
    fetchone=True
)

if row:
    CASH_NUMBER = row[0]
else:
    CASH_NUMBER = "01000000000"


@bot.message_handler(func=lambda m: m.from_user.id in user_state 
                    and user_state[m.from_user.id].get("admin") 
                    and user_state[m.from_user.id].get("step") == "cash")
def set_cash(m):
    global CASH_NUMBER

    if not (m.text and m.text.isdigit() and len(m.text) == 11):
        bot.send_message(m.chat.id, "❌ الرقم يجب أن يكون 11 رقم بشكل صحيح")
        return

    old = CASH_NUMBER
    CASH_NUMBER = m.text

    # 🔥 حفظ في الداتا بيز
    db_execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        ("cash", CASH_NUMBER)
    )

    bot.send_message(
        m.chat.id,
        f"""✅ تم تحديث رقم الكاش بنجاح

━━━━━━━━━━━━━━━━━━
📱 الرقم القديم:
{old}

📱 الرقم الجديد:
{CASH_NUMBER}
━━━━━━━━━━━━━━━━━━"""
    )

    del user_state[m.from_user.id]


# ================= STOP / START =================
@bot.callback_query_handler(func=lambda c: c.data == "admin_stop")
def stop_bot(c):
    global bot_active

    if c.from_user.id not in ADMIN_IDS:
        return

    bot_active = False

    bot.send_message(
        c.message.chat.id,
        "⛔ تم إيقاف خدمات IbrahimBet VIP مؤقتاً"
    )


@bot.callback_query_handler(func=lambda c: c.data == "admin_start")
def start_bot(c):
    global bot_active

    if c.from_user.id not in ADMIN_IDS:
        return

    bot_active = True

    bot.send_message(
        c.message.chat.id,
        "✅ تم تشغيل خدمات IbrahimBet VIP بنجاح"
    )


# ================= BAN =================
@bot.callback_query_handler(func=lambda c: c.data == "admin_ban")
def ban_user(c):
    if c.from_user.id not in ADMIN_IDS:
        return

    user_state[c.from_user.id] = {"admin": True, "step": "ban"}

    bot.send_message(
        c.message.chat.id,
        "🚫 أرسل ID العضو الذي تريد حظره"
    )


@bot.message_handler(func=lambda m: m.from_user.id in user_state and user_state[m.from_user.id].get("admin") and user_state[m.from_user.id].get("step") == "ban")
def do_ban(m):
    try:
        uid = int(m.text)
    except:
        bot.send_message(m.chat.id, "❌ يرجى إرسال ID صحيح")
        return

    blocked_users.add(uid)

    bot.send_message(
        m.chat.id,
        "✅ تم حظر العضو بنجاح"
    )

    try:
        bot.send_message(
            uid,
            """🚫 تم تقييد وصولك إلى IbrahimBet VIP

📩 إذا كنت تعتقد أن هذا بالخطأ يرجى التواصل مع الإدارة"""
        )
    except:
        pass

    del user_state[m.from_user.id]


# ================= UNBAN =================
@bot.callback_query_handler(func=lambda c: c.data == "admin_unban")
def unban_user(c):
    if c.from_user.id not in ADMIN_IDS:
        return

    user_state[c.from_user.id] = {"admin": True, "step": "unban"}

    bot.send_message(
        c.message.chat.id,
        "♻️ أرسل ID العضو لفك الحظر عنه"
    )


@bot.message_handler(func=lambda m: m.from_user.id in user_state and user_state[m.from_user.id].get("admin") and user_state[m.from_user.id].get("step") == "unban")
def do_unban(m):
    try:
        uid = int(m.text)
    except:
        bot.send_message(m.chat.id, "❌ يرجى إرسال ID صحيح")
        return

    blocked_users.discard(uid)

    bot.send_message(
        m.chat.id,
        "✅ تم فك الحظر عن العضو بنجاح"
    )

    try:
        bot.send_message(
            uid,
            """✅ تم استعادة إمكانية الوصول إلى IbrahimBet VIP

🎉 يمكنك الآن استخدام جميع خدمات البوت مرة أخرى"""
        )
    except:
        pass

    del user_state[m.from_user.id]


# ================= BROADCAST =================
@bot.callback_query_handler(func=lambda c: c.data == "admin_broadcast")
def broadcast(c):
    if c.from_user.id not in ADMIN_IDS:
        return

    user_state[c.from_user.id] = {"admin": True, "step": "broadcast"}

    bot.send_message(
        c.message.chat.id,
        "📢 أرسل الرسالة التي تريد إرسالها لجميع المستخدمين"
    )


@bot.message_handler(func=lambda m: m.from_user.id in user_state and user_state[m.from_user.id].get("admin") and user_state[m.from_user.id].get("step") == "broadcast")
def send_broadcast(m):
    success = 0
    fail = 0

    for u in users:
        try:
            bot.send_message(u, m.text)
            success += 1
        except:
            fail += 1

    bot.send_message(
        m.chat.id,
        f"""✅ تم إرسال الرسالة الجماعية بنجاح

📤 تم الإرسال إلى:
{success} مستخدم

❌ فشل الإرسال إلى:
{fail} مستخدم"""
    )

    del user_state[m.from_user.id]


# ================= SEND TO USER =================
@bot.callback_query_handler(func=lambda c: c.data == "admin_msg")
def admin_msg(c):
    if c.from_user.id not in ADMIN_IDS:
        return

    user_state[c.from_user.id] = {"admin": True, "step": "msg_id"}

    bot.send_message(
        c.message.chat.id,
        "📩 أرسل ID العميل الذي تريد مراسلته"
    )


@bot.message_handler(func=lambda m: m.from_user.id in user_state and user_state[m.from_user.id].get("admin") and user_state[m.from_user.id].get("step") == "msg_id")
def get_msg_id(m):
    try:
        user_state[m.from_user.id]["target"] = int(m.text)
    except:
        bot.send_message(m.chat.id, "❌ يرجى إرسال ID صحيح")
        return

    user_state[m.from_user.id]["step"] = "msg_text"

    bot.send_message(
        m.chat.id,
        "✉️ أرسل الرسالة التي تريد إرسالها"
    )


@bot.message_handler(func=lambda m: m.from_user.id in user_state and user_state[m.from_user.id].get("admin") and user_state[m.from_user.id].get("step") == "msg_text")
def send_to_user(m):
    uid = user_state[m.from_user.id]["target"]

    try:
        bot.send_message(uid, m.text)

        bot.send_message(
            m.chat.id,
            "✅ تم إرسال الرسالة للعميل بنجاح"
        )

    except Exception as e:
        bot.send_message(
            m.chat.id,
            f"❌ فشل إرسال الرسالة\n\n{e}"
        )

    del user_state[m.from_user.id]


# ================= ADD ADMIN =================
@bot.callback_query_handler(func=lambda c: c.data == "admin_add")
def add_admin(c):
    if c.from_user.id not in ADMIN_IDS:
        return

    user_state[c.from_user.id] = {"admin": True, "step": "add_admin"}

    bot.send_message(
        c.message.chat.id,
        "➕ أرسل ID الشخص لإضافته كأدمن"
    )


@bot.message_handler(func=lambda m: m.from_user.id in user_state and user_state[m.from_user.id].get("admin") and user_state[m.from_user.id].get("step") == "add_admin")
def do_add_admin(m):
    try:
        uid = int(m.text)
    except:
        bot.send_message(m.chat.id, "❌ يرجى إرسال ID صحيح")
        return

    if uid not in ADMIN_IDS:
        ADMIN_IDS.append(uid)

        # 🔥 رسالة للعضو الجديد
        try:
            bot.send_message(uid, """👑 تم منحك صلاحيات الأدمن في IbrahimBet VIP

━━━━━━━━━━━━━━━━━━
⚙️ الصلاحيات المتاحة لك:
• إدارة المستخدمين
• مراجعة الطلبات
• إرسال رسائل جماعية
• التحكم الكامل في البوت
• متابعة الإحصائيات
━━━━━━━━━━━━━━━━━━

🚀 للدخول إلى لوحة التحكم استخدم:
/admin
""")
        except:
            pass

    bot.send_message(
        m.chat.id,
        "✅ تم إضافة الأدمن الجديد بنجاح"
    )

    del user_state[m.from_user.id]


@bot.callback_query_handler(func=lambda c: c.data == "admin_remove")
def remove_admin_btn(c):
    if c.from_user.id not in ADMIN_IDS:
        return

    user_state[c.from_user.id] = {"admin": True, "step": "remove_admin"}

    bot.send_message(
        c.message.chat.id,
        "➖ أرسل ID الأدمن الذي تريد حذفه"
    )

# ================= REMOVE ADMIN =================
@bot.message_handler(func=lambda m: m.from_user.id in user_state and user_state[m.from_user.id].get("admin") and user_state[m.from_user.id].get("step") == "remove_admin")
def do_remove_admin(m):
    try:
        uid = int(m.text)
    except:
        bot.send_message(m.chat.id, "❌ يرجى إرسال ID صحيح")
        return

    # ❗ منع الأدمن إنه يحذف نفسه
    if uid == m.from_user.id:
        bot.send_message(m.chat.id, "❌ لا يمكنك حذف نفسك من قائمة الأدمن")
        return

    if uid in ADMIN_IDS:
        ADMIN_IDS.remove(uid)

        # 🔥 رسالة للعضو بعد إزالة الأدمن
        try:
            bot.send_message(uid, """🚫 تم سحب صلاحيات الأدمن الخاصة بك

⚠️ لم يعد لديك صلاحية الوصول إلى لوحة التحكم
📩 إذا كان هناك خطأ يرجى التواصل مع الإدارة
""")
        except:
            pass

        bot.send_message(
            m.chat.id,
            "✅ تم حذف الأدمن بنجاح"
        )

    else:
        bot.send_message(m.chat.id, "❌ هذا المستخدم ليس ضمن قائمة الأدمن")

    del user_state[m.from_user.id]


@bot.callback_query_handler(func=lambda c: c.data == "admin_list")
def list_admins(c):
    if c.from_user.id not in ADMIN_IDS:
        return

    text = "👑 قائمة أدمن IbrahimBet VIP\n\n"

    for a in ADMIN_IDS:
        text += f"🆔 {a}\n"

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 رجوع", callback_data="admin_home"))

    try:
        bot.edit_message_text(
            text,
            c.message.chat.id,
            c.message.message_id,
            reply_markup=kb
        )
    except Exception as e:
        # لو الرسالة مش قابلة للتعديل
        bot.send_message(
            c.message.chat.id,
            text,
            reply_markup=kb
        )


@bot.callback_query_handler(func=lambda c: c.data == "admin_bonus")
def admin_bonus(c):
    if c.from_user.id not in ADMIN_IDS:
        return

    user_state[c.from_user.id] = {"admin": True, "step": "bonus_percent"}

    bot.send_message(
        c.message.chat.id,
        "🎁 أرسل نسبة البونص الحالية\n\nمثال: 5"
    )


@bot.message_handler(func=lambda m: m.from_user.id in user_state and user_state[m.from_user.id].get("admin") and user_state[m.from_user.id].get("step") == "bonus_percent")
def set_bonus_percent(m):
    global BONUS_PERCENT

    try:
        BONUS_PERCENT = int(m.text)
    except:
        bot.send_message(m.chat.id, "❌ يرجى إرسال رقم صحيح")
        return

    user_state[m.from_user.id]["step"] = "bonus_min"

    bot.send_message(
        m.chat.id,
        "💰 أرسل الحد الأدنى للإيداع للحصول على البونص"
    )


@bot.message_handler(func=lambda m: m.from_user.id in user_state and user_state[m.from_user.id].get("admin") and user_state[m.from_user.id].get("step") == "bonus_min")
def set_bonus_min(m):
    global BONUS_MIN

    try:
        BONUS_MIN = int(m.text)
    except:
        bot.send_message(m.chat.id, "❌ يرجى إرسال رقم صحيح")
        return

    user_state[m.from_user.id]["step"] = "bonus_max"

    bot.send_message(
        m.chat.id,
        "📤 أرسل الحد الأقصى للبونص\n\nأرسل 0 إذا كنت لا تريد حد أقصى"
    )


@bot.message_handler(func=lambda m: m.from_user.id in user_state and user_state[m.from_user.id].get("admin") and user_state[m.from_user.id].get("step") == "bonus_max")
def set_bonus_max(m):
    global BONUS_MAX

    try:
        val = int(m.text)
        BONUS_MAX = None if val == 0 else val
    except:
        bot.send_message(m.chat.id, "❌ يرجى إرسال رقم صحيح")
        return

    bot.send_message(
        m.chat.id,
        f"""✅ تم تحديث إعدادات البونص بنجاح

━━━━━━━━━━━━━━━━━━
🎁 نسبة البونص:
{BONUS_PERCENT}%

💰 الحد الأدنى:
{BONUS_MIN} جنيه

📤 الحد الأقصى:
{BONUS_MAX if BONUS_MAX else "غير محدود"}
━━━━━━━━━━━━━━━━━━"""
    )

    del user_state[m.from_user.id]


def filter_by_days(days):
    now = datetime.now()
    return [t for t in transactions if (now - t["time"]).days < days]


@bot.callback_query_handler(func=lambda c: c.data == "admin_stats")
def stats(c):
    if c.from_user.id not in ADMIN_IDS:
        return

    today = filter_by_days(1)
    week = filter_by_days(7)
    month = filter_by_days(30)

    def calc(data, ttype):
        ops = [x for x in data if x["type"] == ttype]
        total = len(ops)
        amount = sum(x["amount"] for x in ops)
        accepted = len([x for x in ops if x["status"] == "accepted"])
        rejected = len([x for x in ops if x["status"] == "rejected"])
        return total, amount, accepted, rejected

    d = calc(today, "deposit")
    w = calc(week, "deposit")
    m = calc(month, "deposit")

    wd = calc(today, "withdraw")
    ww = calc(week, "withdraw")
    wm = calc(month, "withdraw")

    def fmt(x):
        return f"{x:,}"

    def rate(acc, total):
        return f"{(acc/total*100):.0f}%" if total else "0%"

    total_deposit = sum(x["amount"] for x in transactions if x["type"] == "deposit")
    total_withdraw = sum(x["amount"] for x in transactions if x["type"] == "withdraw")

    text = f"""📊 لوحة إحصائيات IbrahimBet VIP

━━━━━━━━━━━━━━━━━━
📥 الإيداعات اليوم:
{fmt(d[0])} عملية

💰 المبلغ:
{fmt(d[1])} جنيه

✅ نسبة النجاح:
{rate(d[2], d[0])}

━━━━━━━━━━━━━━━━━━
📤 السحوبات اليوم:
{fmt(wd[0])} عملية

💸 المبلغ:
{fmt(wd[1])} جنيه

✅ نسبة النجاح:
{rate(wd[2], wd[0])}

━━━━━━━━━━━━━━━━━━
👥 إجمالي المستخدمين:
{fmt(len(users))}

📦 إجمالي العمليات:
{fmt(len(transactions))}

💰 إجمالي الداخل:
{fmt(total_deposit)} جنيه

💸 إجمالي الخارج:
{fmt(total_withdraw)} جنيه

━━━━━━━━━━━━━━━━━━
⏱ آخر تحديث:
{datetime.now().strftime('%H:%M:%S')}
"""

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("🔄 تحديث", callback_data="admin_stats"),
        InlineKeyboardButton("🔙 رجوع", callback_data="admin_home")
    )

    try:
        bot.edit_message_text(
            text,
            c.message.chat.id,
            c.message.message_id,
            reply_markup=kb
        )
    except:
        bot.send_message(
            c.message.chat.id,
            text,
            reply_markup=kb
        )


# ================= PROMO =================

PROMO_CODES = {
    "1XBET": "IBRAHIM100",
    "LINBET": "LinIbrahim",
    "GOOBET": "VipGooo",
    "SPINBETR": "MOSPIN",
}


@bot.callback_query_handler(func=lambda c: c.data == "promo")
def promo_menu(c):

    kb = InlineKeyboardMarkup()

    # ✅ إظهار الأزرار اللي ليها بروموكود فقط
    if "1XBET" in PROMO_CODES:
        kb.add(
            InlineKeyboardButton(
                "1XBET 🎯",
                callback_data="promo_1XBET"
            )
        )

    if "LINBET" in PROMO_CODES:
        kb.add(
            InlineKeyboardButton(
                "LINBET 🎮",
                callback_data="promo_LINBET"
            )
        )

    if "GOOBET" in PROMO_CODES:
        kb.add(
            InlineKeyboardButton(
                "GOO BET 🔥",
                callback_data="promo_GOOBET"
            )
        )

    if "SPINBETR" in PROMO_CODES:
        kb.add(
            InlineKeyboardButton(
                "SPIN BETR ⚡",
                callback_data="promo_SPINBETR"
            )
        )

    kb.add(
        InlineKeyboardButton(
            "🔙 القائمة الرئيسية",
            callback_data="home"
        )
    )

    bot.edit_message_text(
        """🎟 Promo Codes | IbrahimBet VIP

━━━━━━━━━━━━━━━━━━
اختر المنصة المطلوبة للحصول على البروموكود 👇""",
        c.message.chat.id,
        c.message.message_id,
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("promo_"))
def show_promo(c):
    app = c.data.split("_")[1]

    code = PROMO_CODES.get(app, "❌ لا يوجد بروموكود متاح حالياً")

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 رجوع", callback_data="promo"))

    bot.edit_message_text(
        f"""🎟 Promo Code | {app}

━━━━━━━━━━━━━━━━━━
💎 البروموكود الخاص بك:

{code}

━━━━━━━━━━━━━━━━━━
🔥 عروض حصرية مقدمة من IbrahimBet VIP""",
        c.message.chat.id,
        c.message.message_id,
        reply_markup=kb
    )

# ================= RUN =================
import time

while True:
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=30)
    except Exception as e:
        print("ERROR:", e)
        time.sleep(5)