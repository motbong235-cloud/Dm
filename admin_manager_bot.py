"""
Kairozen Admin Manager Bot
--------------------------
គ្រប់គ្រង Admin + អនុវត្តច្បាប់ Channel
តម្លៃធ្វើ Admin: $3
Contact: @kairozen_support
"""

import os
import json
import time
import re
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
import telebot
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)

load_dotenv()

# ========================
# Config
# ========================
BOT_TOKEN   = os.getenv("BOT_TOKEN", "")
OWNER_ID    = int(os.getenv("OWNER_ID", "0"))          # ម្ចាស់ Bot
CHANNEL_ID  = os.getenv("CHANNEL_ID", "")              # Channel ដែលត្រូវគ្រប់គ្រង
SUPPORT     = "@kairozen_support"
ADMIN_FEE   = 3.00                                     # $3 ធ្វើ Admin

DATA_DIR = os.getenv("DATA_DIR", ".")
os.makedirs(DATA_DIR, exist_ok=True)

ADMINS_FILE   = os.path.join(DATA_DIR, "admins.json")
POSTS_FILE    = os.path.join(DATA_DIR, "admin_posts.json")
VIOLATIONS_FILE = os.path.join(DATA_DIR, "violations.json")
SHOP_STATUS_FILE = os.path.join(DATA_DIR, "shop_status.json")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# ========================
# Data
# ========================
def _load(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def _save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

admins     = _load(ADMINS_FILE, {})       # uid -> {name, username, since, paid, active}
posts      = _load(POSTS_FILE, {})        # uid -> {date: count}
violations = _load(VIOLATIONS_FILE, [])   # list of violations
shop       = _load(SHOP_STATUS_FILE, {"closed": False})

def is_owner(uid):
    return uid == OWNER_ID

def is_admin(uid):
    return str(uid) in admins and admins[str(uid)].get("active", False)

def get_today():
    return datetime.now().strftime("%Y-%m-%d")

def get_post_count(uid):
    return posts.get(str(uid), {}).get(get_today(), 0)

def add_post(uid):
    uid = str(uid)
    day = get_today()
    if uid not in posts:
        posts[uid] = {}
    posts[uid][day] = posts[uid].get(day, 0) + 1
    _save(POSTS_FILE, posts)
    return posts[uid][day]

def demote_admin(uid, name, reason):
    """ដក Admin ដោយស្វ័យប្រវត្តិ"""
    uid = str(uid)

    # 1. ដកពីបញ្ជី Bot
    if uid in admins:
        admins[uid]["active"] = False
        admins[uid]["demoted_reason"] = reason
        admins[uid]["demoted_at"] = int(time.time())
        _save(ADMINS_FILE, admins)

    # 2. ដកសិទ្ធិ Admin ក្នុង Channel (បើ Bot មានសិទ្ធិ)
    try:
        bot.promote_chat_member(
            CHANNEL_ID,
            int(uid),
            can_change_info=False,
            can_post_messages=False,
            can_edit_messages=False,
            can_delete_messages=False,
            can_invite_users=False,
            can_restrict_members=False,
            can_pin_messages=False,
            can_promote_members=False,
            can_manage_chat=False,
            can_manage_video_chats=False,
            is_anonymous=False
        )
    except Exception as e:
        logger.error(f"promote demote failed: {e}")

    # 3. ជូនដំណឹង User
    try:
        bot.send_message(
            int(uid),
            f"🚫 <b>អ្នកត្រូវបានដក Admin (DM)</b>\n\n"
            f"📌 មូលហេតុ: {reason}\n\n"
            f"ទាក់ទង: {SUPPORT}"
        )
    except:
        pass

    # 4. ជូនដំណឹង Owner
    try:
        bot.send_message(
            OWNER_ID,
            f"🚫 <b>Auto DM Admin</b>\n"
            f"👤 {name} (<code>{uid}</code>)\n"
            f"📌 {reason}\n"
            f"⏰ {datetime.now().strftime('%H:%M %d/%m')}"
        )
    except:
        pass


def add_violation(uid, name, reason, auto_dm=True):
    entry = {
        "uid": str(uid),
        "name": name,
        "reason": reason,
        "ts": int(time.time()),
        "dm": auto_dm
    }
    violations.append(entry)
    if len(violations) > 300:
        violations[:] = violations[-300:]
    _save(VIOLATIONS_FILE, violations)

    # ជូនដំណឹង Owner
    try:
        bot.send_message(
            OWNER_ID,
            f"⚠️ <b>Violation</b>\n"
            f"👤 {name} (<code>{uid}</code>)\n"
            f"📌 {reason}\n"
            f"⏰ {datetime.now().strftime('%H:%M %d/%m')}"
        )
    except:
        pass

    # Auto Demote
    if auto_dm and is_admin(uid):
        demote_admin(uid, name, reason)

# ========================
# ច្បាប់ Admin
# ========================
RULES_TEXT = f"""
📢 <b>ច្បាប់ Admin ទាំងអស់</b>

➡️ <b>ហាម Forward</b>
បើឃើញ FW = DM

✔️ <b>ក្នុងមួយអាទិត្យ</b>
ត្រូវលេងចែកលុយឲ្យបាន ១ ដង

❌ <b>ពេលបិទហាង</b>
មិនឲ្យឆាត ឬ FW
បើនៅ FW = DM

🚫 <b>មិនអនុញ្ញាត</b>
• ដាក់ Logo Channel = DM
• ដាក់ Link (Bot នឹងព្រមាន)
• ប្រម៉ូត Channel គេ ឬខ្លួនឯង = DM
• Spam Channel = DM
• បោកអតិថិជន = DM
• ប្រើ Bot ផ្សេងដោយមិនបានអនុញ្ញាត = DM
• លុបសារ Owner = DM

📌 <b>ផុសក្នុង 1 ថ្ងៃ = 3 ផុស</b>
បើលើស = DM

✅ <b>ត្រូវធ្វើ</b>
• ជួយ Forward សារ Owner
• ឆ្លើយតបអតិថិជនដោយស្មោះ
• រក្សាការសម្ងាត់ព័ត៌មាន
• ប្រើភាសាសមរម្យ
• រាយការណ៍បញ្ហាទៅ Owner ភ្លាម

💰 <b>ធ្វើ Admin = ${ADMIN_FEE:.0f}</b>

━━━━━━━━━━━━━━
បើបំពានច្បាប់ = ដក Admin (DM)
ទាក់ទង: {SUPPORT}
"""

# ========================
# Keyboards
# ========================
def owner_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton("👥 បញ្ជី Admin"), KeyboardButton("➕ បន្ថែម Admin"))
    kb.row(KeyboardButton("🗑 ដក Admin"), KeyboardButton("📋 ច្បាប់"))
    kb.row(KeyboardButton("🏪 បិទ/បើក ហាង"), KeyboardButton("⚠️ Violations"))
    kb.row(KeyboardButton("📊 ស្ថិតិ"))
    return kb

# Bot ប្រើបានតែ Owner — គ្មាន admin_kb

# ========================
# /start
# ========================
@bot.message_handler(commands=["start"])
def cmd_start(message):
    uid = message.from_user.id
    name = message.from_user.first_name or ""

    if is_owner(uid):
        bot.send_message(uid, f"👑 សួស្តី Owner!\nនេះជា <b>Kairozen Admin Manager</b>", reply_markup=owner_kb())
        return

    # Bot ប្រើបានតែ Owner
    bot.send_message(
        uid,
        f"🔒 <b>Bot នេះសម្រាប់ Owner តែប៉ុណ្ណោះ</b>\n\n"
        f"ទាក់ទង: {SUPPORT}"
    )

# ========================
# Owner Commands
# ========================
@bot.message_handler(func=lambda m: m.text == "📋 ច្បាប់" and is_owner(m.from_user.id))
def show_rules(message):
    bot.send_message(message.chat.id, RULES_TEXT, reply_markup=owner_kb())

@bot.message_handler(func=lambda m: m.text == "👥 បញ្ជី Admin" and is_owner(m.from_user.id))
def list_admins(message):
    if not admins:
        bot.send_message(message.chat.id, "គ្មាន Admin ទេ។", reply_markup=owner_kb())
        return

    active = sum(1 for a in admins.values() if a.get("active"))
    total = len(admins)

    lines = [f"👥 <b>បញ្ជី Admin</b> ({active}/{total} សកម្ម)\n"]
    for uid, a in admins.items():
        status = "🟢" if a.get("active") else "🔴"
        since = datetime.fromtimestamp(a.get("since", 0)).strftime("%d/%m/%Y")
        paid = "✅" if a.get("paid") else "❌"
        lines.append(f"{status} <code>{uid}</code> | {a.get('name','?')} | បង់:{paid} | {since}")

    bot.send_message(message.chat.id, "\n".join(lines), reply_markup=owner_kb())

@bot.message_handler(func=lambda m: m.text == "➕ បន្ថែម Admin" and is_owner(m.from_user.id))
def add_admin_start(message):
    msg = bot.send_message(message.chat.id, "វាយ User ID របស់ Admin ថ្មី:")
    bot.register_next_step_handler(msg, add_admin_process)

def add_admin_process(message):
    if not is_owner(message.from_user.id):
        return
    text = (message.text or "").strip()
    if not text.isdigit():
        bot.send_message(message.chat.id, "User ID ត្រូវជាលេខ", reply_markup=owner_kb())
        return

    uid = text
    try:
        chat = bot.get_chat(int(uid))
        name = chat.first_name or ""
        username = chat.username or ""
    except:
        name = "Unknown"
        username = ""

    admins[uid] = {
        "name": name,
        "username": username,
        "since": int(time.time()),
        "paid": False,
        "active": True
    }
    _save(ADMINS_FILE, admins)

    bot.send_message(message.chat.id, f"✅ បានបន្ថែម Admin <code>{uid}</code> ({name})", reply_markup=owner_kb())
    try:
        bot.send_message(int(uid), f"🎉 អ្នកត្រូវបានបន្ថែមជា Admin!\n\n{RULES_TEXT}")
    except:
        pass

@bot.message_handler(func=lambda m: m.text == "🗑 ដក Admin" and is_owner(m.from_user.id))
def remove_admin_start(message):
    msg = bot.send_message(message.chat.id, "វាយ User ID ដែលចង់ដក:")
    bot.register_next_step_handler(msg, remove_admin_process)

def remove_admin_process(message):
    if not is_owner(message.from_user.id):
        return
    text = (message.text or "").strip()
    if text not in admins:
        bot.send_message(message.chat.id, "រកមិនឃើញ Admin នេះ", reply_markup=owner_kb())
        return

    name = admins[text].get("name", "")
    del admins[text]
    _save(ADMINS_FILE, admins)

    bot.send_message(message.chat.id, f"🗑 បានដក Admin <code>{text}</code> ({name})", reply_markup=owner_kb())
    try:
        bot.send_message(int(text), "⚠️ អ្នកត្រូវបានដកចេញពី Admin។")
    except:
        pass

@bot.message_handler(func=lambda m: m.text == "🏪 បិទ/បើក ហាង" and is_owner(m.from_user.id))
def toggle_shop(message):
    shop["closed"] = not shop.get("closed", False)
    _save(SHOP_STATUS_FILE, shop)

    status = "🔴 បិទហាង" if shop["closed"] else "🟢 បើកហាង"
    bot.send_message(message.chat.id, f"ស្ថានភាព: <b>{status}</b>", reply_markup=owner_kb())

    # ជូនដំណឹង Admin ទាំងអស់
    for uid in admins:
        if admins[uid].get("active"):
            try:
                if shop["closed"]:
                    bot.send_message(int(uid), "🔴 <b>ហាងបិទហើយ!</b>\nហាមឆាត និង Forward។ បើនៅ FW = DM")
                else:
                    bot.send_message(int(uid), "🟢 <b>ហាងបើកហើយ!</b>\nអាចដំណើរការធម្មតា។")
            except:
                pass

@bot.message_handler(func=lambda m: m.text == "⚠️ Violations" and is_owner(m.from_user.id))
def show_violations(message):
    recent = violations[-15:][::-1]
    if not recent:
        bot.send_message(message.chat.id, "គ្មាន Violation ទេ។", reply_markup=owner_kb())
        return

    lines = ["⚠️ <b>Violations (15 ចុងក្រោយ)</b>\n"]
    for v in recent:
        t = datetime.fromtimestamp(v["ts"]).strftime("%d/%m %H:%M")
        lines.append(f"• {t} | {v.get('name','?')} (<code>{v['uid']}</code>)\n  → {v['reason']}")

    bot.send_message(message.chat.id, "\n".join(lines), reply_markup=owner_kb())

@bot.message_handler(func=lambda m: m.text == "📊 ស្ថិតិ" and is_owner(m.from_user.id))
def owner_stats(message):
    total = len(admins)
    active = sum(1 for a in admins.values() if a.get("active"))
    demoted = sum(1 for a in admins.values() if not a.get("active"))
    paid = sum(1 for a in admins.values() if a.get("paid"))
    unpaid = active - sum(1 for a in admins.values() if a.get("active") and a.get("paid"))
    total_v = len(violations)
    closed = "🔴 បិទ" if shop.get("closed") else "🟢 បើក"

    bot.send_message(
        message.chat.id,
        f"📊 <b>ស្ថិតិ Admin</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"👥 Admin សរុប: <b>{total}</b>\n"
        f"🟢 សកម្ម: <b>{active}</b>\n"
        f"🔴 ត្រូវបាន DM: <b>{demoted}</b>\n"
        f"💰 បង់ហើយ: <b>{paid}</b>\n"
        f"⏳ មិនទាន់បង់: <b>{unpaid}</b>\n"
        f"⚠️ Violations: <b>{total_v}</b>\n"
        f"🏪 ហាង: <b>{closed}</b>",
        reply_markup=owner_kb()
    )

# Admin មិនអាចប្រើ Bot នេះ (Owner only)

# ========================
# Channel Message Monitor
# ========================
@bot.channel_post_handler(content_types=["text", "photo", "video", "document", "animation", "sticker"])
@bot.message_handler(content_types=["text", "photo", "video", "document", "animation", "sticker"],
                     func=lambda m: m.chat.type in ("channel", "supergroup") and str(m.chat.id) == str(CHANNEL_ID))
def monitor_channel(message):
    """តាមដានសារក្នុង Channel / Group"""
    try:
        # បើជា Owner → រួច
        if message.from_user and message.from_user.id == OWNER_ID:
            return

        uid = message.from_user.id if message.from_user else None
        if not uid:
            return

        name = message.from_user.first_name or ""
        text = (message.text or message.caption or "")

        # មានតែ Admin ទេដែលត្រូវពិនិត្យ
        if not is_admin(uid):
            return

        # 1. ហាម Forward
        if message.forward_date or message.forward_from or message.forward_from_chat:
            add_violation(uid, name, "Forward (FW)")
            try:
                bot.send_message(uid, "⚠️ <b>អ្នកបាន Forward!</b>\nតាមច្បាប់ = DM\nសូមកុំធ្វើម្ដងទៀត។")
            except:
                pass
            return

        # 2. ពេលបិទហាង → ហាម FW និងឆាត
        if shop.get("closed"):
            add_violation(uid, name, "ផុសពេលបិទហាង")
            try:
                bot.send_message(uid, "🔴 ហាងបិទហើយ! ហាមផុស។ បើនៅបន្ត = DM")
            except:
                pass
            return

        # 3. ដាក់ Link → ផ្ញើសារផ្ទាល់ (មិនដក Admin ភ្លាម)
        if re.search(r'(https?://|t\.me/|telegram\.me/)', text, re.IGNORECASE):
            add_violation(uid, name, "ដាក់ Link", auto_dm=False)
            try:
                bot.send_message(
                    uid,
                    "⚠️ <b>អ្នកបានដាក់ Link ក្នុង Channel</b>\n\n"
                    "តាមច្បាប់ ហាមដាក់ Link។\n"
                    "សូមលុបចេញ បើមិនដូច្នេះ Admin អាចត្រូវបានដក។\n\n"
                    f"ទាក់ទង: {SUPPORT}"
                )
            except:
                pass
            return

        # 4. ហាមប្រម៉ូត Channel (ពាក្យគន្លឹះ)
        promo_words = ["subscribe", "join", "channel", "ចូល", "subscribe", "ប្រម៉ូត", "promo"]
        if any(w in text.lower() for w in promo_words) and ("t.me/" in text.lower() or "@" in text):
            add_violation(uid, name, "ប្រម៉ូត Channel")
            try:
                bot.send_message(uid, "⚠️ ហាមប្រម៉ូត Channel!\nបើបន្ត = DM")
            except:
                pass
            return

        # 5. ដែនកំណត់ 3 ផុស / ថ្ងៃ
        count = add_post(uid)
        if count > 3:
            add_violation(uid, name, f"ផុសលើស 3 ដង ({count})")
            try:
                bot.send_message(uid, f"⚠️ អ្នកផុសលើស 3 ដងហើយថ្ងៃនេះ ({count})!\nតាមច្បាប់ = DM")
            except:
                pass

    except Exception as e:
        logger.error(f"monitor error: {e}")

# ========================
# Mark paid
# ========================
@bot.message_handler(commands=["paid"])
def cmd_paid(message):
    """Owner: /paid <user_id>"""
    if not is_owner(message.from_user.id):
        return
    parts = (message.text or "").split()
    if len(parts) < 2 or not parts[1].isdigit():
        bot.send_message(message.chat.id, "ប្រើ: /paid <user_id>")
        return

    uid = parts[1]
    if uid not in admins:
        bot.send_message(message.chat.id, "រកមិនឃើញ Admin")
        return

    admins[uid]["paid"] = True
    _save(ADMINS_FILE, admins)
    bot.send_message(message.chat.id, f"✅ បានកត់ថា <code>{uid}</code> បង់ ${ADMIN_FEE:.0f} រួច")
    try:
        bot.send_message(int(uid), f"✅ ការបង់ប្រាក់ ${ADMIN_FEE:.0f} ត្រូវបានបញ្ជាក់!")
    except:
        pass

# ========================
# Fallback
# ========================
@bot.message_handler(func=lambda m: True)
def fallback(message):
    if is_owner(message.from_user.id):
        bot.send_message(message.chat.id, "សូមប្រើប៊ូតុងខាងក្រោម។", reply_markup=owner_kb())
    else:
        bot.send_message(
            message.chat.id,
            f"🔒 <b>Bot នេះសម្រាប់ Owner តែប៉ុណ្ណោះ</b>\n\nទាក់ទង: {SUPPORT}"
        )

# ========================
# Main
# ========================
if __name__ == "__main__":
    if not BOT_TOKEN or not OWNER_ID:
        print("❌ សូមកំណត់ BOT_TOKEN និង OWNER_ID")
        exit(1)

    print("🤖 Kairozen Admin Manager is running...")
    bot.infinity_polling(allowed_updates=["message", "channel_post", "callback_query"])
