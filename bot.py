import os
import aiohttp
import asyncio
import time
import html
import traceback
import sys
import re
import imaplib
import email
import random
import uuid
import math
from datetime import datetime

from pyrogram import Client, filters, enums, idle
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ChatJoinRequest
from pyrogram.errors import SessionPasswordNeeded, FloodWait, UserNotParticipant, UserAlreadyParticipant
from pyrogram.raw.functions.messages import GetChatInviteImporters, CheckChatInvite, GetStickerSet
from pyrogram.raw.types import InputUserEmpty, InputStickerSetShortName
from pyrogram.handlers import MessageHandler, CallbackQueryHandler, ChatJoinRequestHandler

# ================= DETAILS =================
API_ID = 30952226
API_HASH = "e645bc02c026f0df261d7c14412483d3"
BOT_TOKEN = "9124420986:AAGYYh6vcuuR2oyhUdgRLdqQLz3KYevQdRc"  

ADMINS = [8601101339]
OWNER_ADMIN_ID = ADMINS[0]  # Primary owner is protected from removal
bot = Client("DEVESHdmsBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

# ================= 🌟 CUSTOMIZATION HUB (CUSTOM EMOJI IDs) 🌟 =================
BTN_EMOJIS = {
    "start": "5780773956030043338",   # 🚀
    "user": "6267150926100829360",    # 👨‍🏫
    "money": "6030734193594470413",   # 💵
    "diamond": "6030811868078018748", # 💎
    "add": "6032733629719777782",     # ➕
    "cross": "6032606743500951856",   # ❌
    "tick": "6034905633336070030",    # ✅
    "home": "5780385815540535887",    # 🗽
    "shield": "6282846669335702032",  # 🔒
    "setting": "6033129724488715918", # 🧩
    "target": "6030880810893053589",  # 📍
    "globe": "6014898614814382254",   # 🌐
    "stats": "5972211201147408942",   # 📱
    "cal": "6014861794059752708",     # 🗓
    "gift": "5785281906459283269",    # 🎁
    "wait": "6267229004311303657",    # ⌛
    "crown": "5798670723975221399",   # 👑
    "ban": "6032707305865220377",     # 🚫
    "refresh": "6035353718684129368",  # 🔄
    "account_manage": "5769547529993588669",
    "next": "6116400756581996038",
    "prev": "6118419524355102131"
}

# ================= IST TIME HELPERS =================
def get_ist(): return time.gmtime(time.time() + 19800)
def get_ist_str(fmt="%Y-%m-%d"): return time.strftime(fmt, get_ist())
def get_ist_ts_str(ts, fmt="%d %b %Y, %I:%M %p"): return time.strftime(fmt, time.gmtime(ts + 19800))

# ================= GMAIL SETUP =================
GMAIL_USER = "deveshedits01@gmail.com"
GMAIL_PASS = "deveshedits@1234"

def check_payment_in_gmail(utr_to_find):
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_PASS)
        mail.select("inbox")
        status, messages = mail.search(None, f'(TEXT "{utr_to_find}")')
        if status == "OK" and messages[0]:
            mail_ids = messages[0].split()
            for mail_id in mail_ids[-1:]: 
                status, msg_data = mail.fetch(mail_id, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain": body += part.get_payload(decode=True).decode(errors='ignore')
                        else: body = msg.get_payload(decode=True).decode(errors='ignore')
                        clean_body = re.sub(r'\s+', ' ', body).upper()
                        amounts = re.findall(r'(?:₹|RS\.?|INR)\s*([\d\.]+)', clean_body)
                        if utr_to_find in clean_body and amounts:
                            mail.logout(); return float(amounts[0]) 
        mail.logout(); return None 
    except Exception: return None

# ================= PREMIUM ANIMATED TEXT EMOJIS =================
def e(eid, fb="🔹"): 
    return f'<tg-emoji emoji-id="{eid}">{fb}</tg-emoji>'

E_CHK = e("6034905633336070030", "✅")
E_DIA = e("6030811868078018748", "💎")
E_SHD = e("6282846669335702032", "🔒")
E_WRN = e("6267039884016358504", "⚠️")
E_LNK = e("6267115986541877538", "🔗")
E_CAL = e("6014861794059752708", "🗓")
E_MED = e("6266851803103499415", "🎖️")
E_TRI = e("6035134679647000020", "🔺")
E_START = e("5780773956030043338", "🚀")
E_PROF = e("6267150926100829360", "👨‍🏫")
E_ADD = e("6032733629719777782", "➕")
E_WAIT = e("6267229004311303657", "⌛")
E_SYNC = e("6035353718684129368", "🔄")
E_ACT = e("6267107057304868214", "⚡️")
E_ADM = e("6033129724488715918", "🧩")
E_STAT = e("5972211201147408942", "📱")
E_MONEY = e("6030734193594470413", "💵")
E_PREM = e("6266961380604123114", "⚜️")
E_PLAY = e("6266829404849050968", "▶️")
E_STOP = e("6267262260243076354", "🛑")
E_CROSS = e("6032606743500951856", "❌")
E_GLOBE = e("6014898614814382254", "🌐")
E_DOT = e("6032975852990370635", "🟢")
E_ID = e("6035239240625820254", "🆔")
E_GIFT = e("5785281906459283269", "🎁")
E_CROWN = e("5798670723975221399", "👑")

# --- PROFESSIONAL TERMS & TUTORIAL (NON-MESSY) ---
DEFAULT_TERMS = f"""{E_SHD} <b>DEVESH DMS ENGINE — TERMS OF USE</b>

{E_DOT} <b>1. Ethical Conduct</b>
<i>All campaigns must comply with Telegram ToS. No illegal, abusive, or malicious outreach.</i>

{E_DOT} <b>2. Zero-Spam Policy</b>
<i>Target only consenting or organic audiences. Mass reporting from users can trigger session bans.</i>

{E_DOT} <b>3. Payment Policy</b>
<i>All subscriptions and purchases are final & strictly non-refundable.</i>

{E_DOT} <b>4. Security & Privacy</b>
<i>Session credentials are kept secure. Any violation of these terms leads to immediate suspension.</i>

{E_DOT} <b>5. Service Reliability</b>
<i>While we strive for 99% uptime, Telegram throttling or FloodWaits may impact delivery speed.</i>"""

DEFAULT_TUTORIAL = f"""{E_PROF} <b>HOW TO USE DEVESH DMS — QUICK START</b>

{E_DOT} <b>Step 1 — Connect Session</b>
<i>Click <b>Add Session</b> and complete the secure phone/OTP/2FA login flow.</i>

{E_DOT} <b>Step 2 — Craft Your Message</b>
<i>Use <b>Set Exact Message</b> to send text, photo, video, voice, sticker, or document — formatting is preserved 1:1.</i>

{E_DOT} <b>Step 3 — Select Target Audience</b>
<i>Choose channel pending requests, alt-account dialogs, or the admin's free channel.</i>

{E_DOT} <b>Step 4 — Set Volume & Delay</b>
<i>Specify how many DMs to deliver and the throttle interval.</i>

{E_DOT} <b>Step 5 — Launch Campaign</b>
<i>Watch the <b>Live Dashboard</b> update in real-time with pause/resume/stop controls.</i>"""

# --- RAW API ENGINE FOR COLOR BUTTONS ---
def ibtn(text, cb=None, url=None, style="primary", icon=None):
    if style not in ["primary", "danger", "success"]:
        style = "primary"
    btn = {"text": text, "style": style}
    if cb: btn["callback_data"] = cb 
    if url: btn["url"] = url
    if icon: btn["icon_custom_emoji_id"] = icon
    return btn

class MockMessage:
    def __init__(self, chat_id, message_id):
        self.chat = type('Chat', (), {'id': chat_id})()
        self.id = message_id

    async def delete(self):
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage"
        async with aiohttp.ClientSession() as session:
            await session.post(url, json={"chat_id": self.chat.id, "message_id": self.id})

async def _user_reply_keyboard(chat_id, kb):
    """Convert callback buttons into reply-keyboard text buttons and retain their actions."""
    if not kb or "inline_keyboard" not in kb:
        return kb
    try:
        if int(chat_id) in ADMINS:
            return kb
    except Exception:
        pass
    cfg = await settings_col.find_one({"_id": "config"}) or {}
    if cfg.get("user_button_mode", "inline") != "keyboard":
        return kb
    actions = {}
    rows = []
    for row in kb.get("inline_keyboard", []):
        out_row = []
        for button in row:
            label = str(button.get("text") or "Button")
            action = {"callback_data": button.get("callback_data"), "url": button.get("url")}
            actions[label] = action
            out_row.append(KeyboardButton(label))
        if out_row:
            rows.append(out_row)
    REPLY_BUTTON_ACTIONS[str(chat_id)] = actions
    return {"keyboard": [[{"text": button.text} for button in row] for row in rows],
            "resize_keyboard": True, "is_persistent": True} if rows else kb


async def api_send(chat_id, text=None, kb=None, photo=None):
    kb = await _user_reply_keyboard(chat_id, kb)
    payload = {"chat_id": chat_id, "parse_mode": "HTML"}
    if text and not photo: payload["text"] = text
    elif text and photo: payload["caption"] = text
    if photo: payload["photo"] = photo
    if kb: payload["reply_markup"] = kb
    
    method = "sendPhoto" if photo else "sendMessage"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            data = await resp.json()
            if data.get("ok"): 
                return MockMessage(chat_id, data["result"]["message_id"])
                
    try:
        standard_kb = None
        if kb and "inline_keyboard" in kb:
            pyro_btns = []
            for row in kb["inline_keyboard"]:
                pyro_row = []
                for b in row:
                    pyro_row.append(InlineKeyboardButton(text=b.get("text",""), callback_data=b.get("callback_data"), url=b.get("url")))
                pyro_btns.append(pyro_row)
            standard_kb = InlineKeyboardMarkup(pyro_btns)
        elif kb and "keyboard" in kb:
            standard_kb = ReplyKeyboardMarkup(
                [[KeyboardButton(text=b.get("text", "")) for b in row] for row in kb["keyboard"]],
                resize_keyboard=kb.get("resize_keyboard", True),
                is_persistent=kb.get("is_persistent", True)
            )
            
        if photo:
            m = await bot.send_photo(chat_id, photo=photo, caption=text, reply_markup=standard_kb, parse_mode=enums.ParseMode.HTML)
        else:
            m = await bot.send_message(chat_id, text, reply_markup=standard_kb, parse_mode=enums.ParseMode.HTML)
        return MockMessage(chat_id, m.id)
    except Exception:
        return MockMessage(chat_id, None)

async def api_edit(chat_id, msg_id, text, kb=None):
    try:
        cfg = await settings_col.find_one({"_id": "config"}) or {}
        is_admin = int(chat_id) in ADMINS
    except Exception:
        cfg, is_admin = {}, False
    if not is_admin and cfg.get("user_button_mode", "inline") == "keyboard" and kb and "inline_keyboard" in kb:
        return await api_send(chat_id, text, kb=kb)
    payload = {"chat_id": chat_id, "message_id": msg_id, "text": text, "parse_mode": "HTML"}
    if kb: payload["reply_markup"] = kb
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            data = await resp.json()
            if data.get("ok"): 
                return MockMessage(chat_id, data["result"]["message_id"])
                
    try:
        standard_kb = None
        if kb and "inline_keyboard" in kb:
            pyro_btns = []
            for row in kb["inline_keyboard"]:
                pyro_row = []
                for b in row:
                    pyro_row.append(InlineKeyboardButton(text=b.get("text",""), callback_data=b.get("callback_data"), url=b.get("url")))
                pyro_btns.append(pyro_row)
            standard_kb = InlineKeyboardMarkup(pyro_btns)
        elif kb and "keyboard" in kb:
            standard_kb = ReplyKeyboardMarkup(
                [[KeyboardButton(text=b.get("text", "")) for b in row] for row in kb["keyboard"]],
                resize_keyboard=kb.get("resize_keyboard", True),
                is_persistent=kb.get("is_persistent", True)
            )
        m = await bot.edit_message_text(chat_id, msg_id, text, reply_markup=standard_kb, parse_mode=enums.ParseMode.HTML)
        return MockMessage(chat_id, m.id)
    except Exception:
        return MockMessage(chat_id, msg_id)

async def safe_edit(*args, **kwargs):
    query = args[0] if len(args) > 0 else kwargs.get("query")
    text = args[1] if len(args) > 1 else kwargs.get("text")
    kb = args[2] if len(args) > 2 else kwargs.get("kb")
    
    chat_id = query.message.chat.id
    msg_id = query.message.id
    if query.message.photo or query.message.video or query.message.document:
        try:
            await query.message.delete()
        except Exception:
            pass
        return await api_send(chat_id, text, kb=kb)
    else:
        return await api_edit(chat_id, msg_id, text, kb=kb)

# ================= IN-MEMORY STORAGE =================
class _AsyncCursor:
    def __init__(self, items):
        self.items = items
    def __aiter__(self):
        self._i = 0
        return self
    async def __anext__(self):
        if self._i >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self._i]
        self._i += 1
        return item
    async def to_list(self, length=None):
        return self.items if length is None else self.items[:length]

class _MemoryCollection:
    def __init__(self):
        self.data = {}

    async def find_one(self, query):
        if query.get("_id") in self.data:
            return dict(self.data[query["_id"]])
        for doc in self.data.values():
            if all(doc.get(k) == v for k, v in query.items()):
                return dict(doc)
        return None

    async def insert_one(self, doc):
        self.data[doc["_id"]] = dict(doc)
        return type("Result", (), {"inserted_id": doc["_id"]})()

    def _set_path(self, doc, path, value):
        parts = path.split(".")
        cur = doc
        for part in parts[:-1]:
            if part not in cur or not isinstance(cur[part], dict):
                cur[part] = {}
            cur = cur[part]
        cur[parts[-1]] = value

    def _get_path(self, doc, path, default=0):
        cur = doc
        for part in path.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return default
            cur = cur[part]
        return cur

    def _match(self, doc, query):
        for key, expected in query.items():
            actual = self._get_path(doc, key, None)
            if isinstance(expected, dict):
                if "$gt" in expected and not (actual is not None and actual > expected["$gt"]): return False
                if "$gte" in expected and not (actual is not None and actual >= expected["$gte"]): return False
                if "$lt" in expected and not (actual is not None and actual < expected["$lt"]): return False
                if "$lte" in expected and not (actual is not None and actual <= expected["$lte"]): return False
            elif actual != expected:
                return False
        return True

    async def update_one(self, query, update, upsert=False):
        doc = None
        key = query.get("_id")
        if key is not None and key in self.data:
            doc = self.data[key]
        else:
            for k, candidate in self.data.items():
                if self._match(candidate, query):
                    key, doc = k, candidate
                    break
        if doc is None:
            if not upsert:
                return type("Result", (), {"matched_count": 0, "modified_count": 0})()
            doc = dict(query)
            key = query.get("_id", str(len(self.data)))
            doc["_id"] = key
            self.data[key] = doc

        for op, fields in update.items():
            for path, value in fields.items():
                if op == "$set":
                    self._set_path(doc, path, value)
                elif op == "$inc":
                    self._set_path(doc, path, self._get_path(doc, path, 0) + value)
                elif op in ("$push", "$addToSet"):
                    arr = self._get_path(doc, path, [])
                    if not isinstance(arr, list): arr = []
                    if op == "$push" or value not in arr:
                        arr.append(value)
                    self._set_path(doc, path, arr)
        return type("Result", (), {"matched_count": 1, "modified_count": 1})()

    async def count_documents(self, query):
        return sum(1 for doc in self.data.values() if self._match(doc, query))

    def find(self, query):
        return _AsyncCursor([dict(d) for d in self.data.values() if self._match(d, query)])

    def aggregate(self, pipeline):
        items = [dict(d) for d in self.data.values()]
        for stage in pipeline:
            if "$match" in stage:
                items = [d for d in items if self._match(d, stage["$match"])]
            elif "$sort" in stage:
                for field, direction in reversed(list(stage["$sort"].items())):
                    items.sort(key=lambda d: self._get_path(d, field, 0), reverse=(direction < 0))
            elif "$limit" in stage:
                items = items[:stage["$limit"]]
        return _AsyncCursor(items)

users_col = _MemoryCollection()
settings_col = _MemoryCollection()
USER_STATES, ACTIVE_TASKS = {}, {}
REPLY_BUTTON_ACTIONS = {}  # per-chat text-button routing for ReplyKeyboard mode
FORWARD_TASKS = {}
ACCOUNT_MONITORS = {}
ACCOUNT_MONITOR_LOCKS = {}

DEFAULT_CONFIG = {
    "_id": "config", "user_button_mode": "inline", "price_1d_inr": "25", "price_1d_usd": "0.5", "price_3d_inr": "60", "price_3d_usd": "1.5",
    "price_7d_inr": "120", "price_7d_usd": "3", "price_1m_inr": "350", "price_1m_usd": "8",
    "upi_fampay": "not_set", "upi_manual": "not_set", "crypto": "not_set", "auto_payment_status": False,
    "free_trial_limit": 100, "msg_delay": 0, "log_channel": "none", "success_log_channel": "none", "leaderboard_channel": "none",
    "free_channel_id": "none", "free_channel_link": "none", "mystery_box_days": 0, "mystery_box_round": 0, "mystery_box_claimed": [], "game_enabled": True, "anti_fraud_enabled": True, "total_sales_inr": 0, "total_sales_usd": 0, "global_dms": 0, "sales_history": {},
    "qr_fampay": "none", "qr_manual": "none", "qr_crypto": "none", "fsub_channels": [],
    "reqall_id": "none", "reqall_link": "none", "website_link": "not_set", "pending_bot_link": "not_set", "forward_bot_link": "not_set",
    "ldb_time": 21, "free_req_limit": 300, "ref_bonus": 50, "ref_premium_days": 0, "maintenance": False, "redeem_codes": {}, "admins": [1591026118]
}

async def init_db():
    global ADMINS
    if await settings_col.find_one({"_id": "config"}) is None:
        await settings_col.insert_one(dict(DEFAULT_CONFIG))
    config = await settings_col.find_one({"_id": "config"}) or {}
    saved_admins = config.get("admins")
    if not isinstance(saved_admins, list) or not saved_admins:
        saved_admins = list(ADMINS)
        await settings_col.update_one({"_id": "config"}, {"$set": {"admins": saved_admins}})
    # Keep IDs as integers and always retain the original owner.
    normalized = []
    for item in saved_admins:
        try:
            value = int(item)
            if value > 0 and value not in normalized:
                normalized.append(value)
        except (TypeError, ValueError):
            continue
    if OWNER_ADMIN_ID not in normalized:
        normalized.insert(0, OWNER_ADMIN_ID)
        await settings_col.update_one({"_id": "config"}, {"$set": {"admins": normalized}})
    ADMINS[:] = normalized

def plan_price_label(config, days):
    suffix = "1m" if days == 30 else f"{days}d"
    inr = config.get(f"price_{suffix}_inr", "0")
    usd = config.get(f"price_{suffix}_usd", "0")
    try:
        if float(str(inr).replace(",", "").strip() or 0) <= 0:
            return "FREE"
    except (TypeError, ValueError):
        pass
    return f"₹{inr} | ${usd}"

# ================= HELPER FUNCTIONS =================
async def get_user(user_id):
    user_id = str(user_id)
    today = get_ist_str("%Y-%m-%d")
    user = await users_col.find_one({"_id": user_id})
    if not user:
        user = {"_id": user_id, "username": "", "banned": False, "premium_expiry": 0, "sessions": [], "saved_channels": [], 
                "custom_msg_data": {"type": "text", "html": "HELLO"}, "custom_msg_fwd": "",
                "total_dms": 0, "daily_dms": 0, "last_date": today, "messaged_users": {}, "pending_chats": [], "last_spin": 0, "referrals": 0, "referrer_id": None, "referral_rewarded": False, "premium_history": [], "free_premium_claimed": False, "account_manager": {"enabled": False, "message_limit": 3, "auto_message": "", "warning_counts": {}}, "created_at": time.time()}
        await users_col.insert_one(user)
    else:
        if user.get("last_date") != today:
            await users_col.update_one({"_id": user_id}, {"$set": {"daily_dms": 0, "last_date": today}})
            user["daily_dms"] = 0; user["last_date"] = today
    return user

async def is_premium(user_or_id):
    if isinstance(user_or_id, dict): u = user_or_id
    else: u = await get_user(user_or_id)
    return u.get("premium_expiry", 0) > time.time()

# ================= REFERRAL / PREMIUM AUDIT / MYSTERY BOX =================
async def record_premium_event(user_id, days, source):
    u = await get_user(user_id)
    entry = {"days": int(days), "source": str(source), "at": time.time(),
             "expiry": float(u.get("premium_expiry", 0) or 0)}
    await users_col.update_one({"_id": str(user_id)}, {"$push": {"premium_history": entry}})

async def grant_premium(user_id, days, source):
    u = await get_user(user_id)
    now = time.time()
    expiry = (float(u.get("premium_expiry", 0) or 0) if float(u.get("premium_expiry", 0) or 0) > now else now) + int(days) * 86400
    await users_col.update_one({"_id": str(user_id)}, {"$set": {"premium_expiry": expiry}})
    await record_premium_event(user_id, days, source)
    return expiry

# ================= BACKGROUND TASKS =================
async def auto_leaderboard_task():
    while True:
        try:
            config = await settings_col.find_one({"_id": "config"})
            ldb_channel = config.get("leaderboard_channel", "none")
            ldb_time = int(config.get("ldb_time", 21))
            
            if ldb_channel != "none" and get_ist().tm_hour == ldb_time:
                today = get_ist_str("%Y-%m-%d")
                last_post = config.get("last_ldb_post", "")
                if last_post != today:
                    top_today = await users_col.aggregate([{"$match": {"last_date": today, "daily_dms": {"$gt": 0}}}, {"$sort": {"daily_dms": -1}}, {"$limit": 10}]).to_list(10)
                    if top_today:
                        text = f"{E_MED} <i><b>Daily DM Leaderboard ({today})</b></i> {E_MED}\n\n"
                        for i, u in enumerate(top_today):
                            un = f"(@{u['username']})" if u.get('username') and u['username'] != "N/A" else ""
                            text += f"<i><b>{i+1}.</b> <code>...{str(u['_id'])[-4:]}</code> {un} - {u['daily_dms']} DMs</i>\n"
                        text += f"\n{E_START} <i>Automatically Generated</i>"
                        try:
                            lc_id = int(ldb_channel) if str(ldb_channel).replace("-", "").isdigit() else ldb_channel
                            await api_send(lc_id, text)
                            await settings_col.update_one({"_id": "config"}, {"$set": {"last_ldb_post": today}})
                        except Exception: pass
        except: pass
        await asyncio.sleep(1800)

# ================= LIVE CAMPAIGN DASHBOARD UPDATER =================
async def dashboard_updater(user_id, status_msg_chat, status_msg_id):
    user_id_str = str(user_id)
    while user_id_str in ACTIVE_TASKS:
        task = ACTIVE_TASKS[user_id_str]
        status = task.get('status', 'running')
        if status == "stopped": break
        
        sent = task.get('sent', 0)
        limit = max(1, task.get('limit', 1))
        progress = min(1.0, sent / limit)
        filled = int(progress * 15)
        bar = "█" * filled + "░" * (15 - filled)
        pct = int(progress * 100)
        
        elapsed = int(time.time() - task.get('start_time', time.time()))
        em, es = divmod(elapsed, 60)
        
        status_emoji = E_ACT if status == "running" else (E_WAIT if status == "paused" else E_STOP)
        status_text = status.upper()
        
        text = f"""{E_START} <b>LIVE CAMPAIGN DASHBOARD</b>

━━━━━━━━━━━━━━━━━━━━
{E_TRI} <b>Target:</b> <code>{task.get('target', 'Unknown')}</code>
{E_SYNC} <b>Nodes:</b> <code>{task.get('nodes', 1)}</code> Active
{status_emoji} <b>Status:</b> <code>{status_text}</code>
━━━━━━━━━━━━━━━━━━━━

{E_STAT} <b>Delivered:</b> <code>{sent}</code> / <code>{task.get('limit', 0)}</code>
{E_WAIT} <b>Runtime:</b> <code>{em}m {es}s</code>

<code>[{bar}] {pct}%</code>

<i>Use buttons below to control campaign</i>"""
        
        btns = []
        if status == "running":
            btns = [[ibtn("⏸️ Pause", f"dmc_pause_{user_id}", style="primary"), ibtn("🛑 Stop", f"dmc_stop_{user_id}", style="danger")]]
        elif status == "paused":
            btns = [[ibtn("▶️ Resume", f"dmc_resume_{user_id}", style="success"), ibtn("🛑 Stop", f"dmc_stop_{user_id}", style="danger")]]
            
        try:
            await api_edit(status_msg_chat, status_msg_id, text, kb={"inline_keyboard": btns})
        except Exception: pass
        await asyncio.sleep(4)

# ================= CHANNEL MESSAGE FORWARDER =================
async def forward_messages_worker(user_id):
    uid = str(user_id)
    task = FORWARD_TASKS.get(uid)
    if not task:
        return
    userbot = None
    try:
        user_data = await get_user(uid)
        sessions = user_data.get("sessions", [])
        if not sessions:
            task["status"] = "stopped"
            task["error"] = "No connected session found."
            return
        userbot = Client(f"fwd_{uid}_{int(time.time())}", api_id=API_ID, api_hash=API_HASH,
                         session_string=sessions[0], in_memory=True)
        await userbot.start()
        # Preflight: resolve both channels with the connected user session and
        # verify that this exact account can read the source and post to target.
        source = await get_chat_safely(userbot, task["source_link"], task["source_link"])
        target = await get_chat_safely(userbot, task["target_link"], task["target_link"])
        me = await userbot.get_me()

        try:
            source_member = await userbot.get_chat_member(source.id, me.id)
            source_status = str(getattr(source_member, "status", "")).lower().split(".")[-1]
            if source_status in ("kicked", "banned", "left"):
                raise RuntimeError("The connected account is not a member of the source channel. Join it first, then retry.")
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError("Could not verify source-channel membership for the connected account. Make sure the account has joined the source channel and the link is correct.") from exc

        try:
            target_member = await userbot.get_chat_member(target.id, me.id)
            target_status = str(getattr(target_member, "status", "")).lower().split(".")[-1]
            if target_status in ("kicked", "banned", "left"):
                raise RuntimeError("The connected account cannot post to the destination channel. Join it and check posting permissions.")
            if getattr(target_member, "privileges", None) is not None:
                can_post = getattr(target_member.privileges, "can_post_messages", True)
                if not can_post:
                    raise RuntimeError("The connected account does not have permission to post in the destination channel.")
            elif target_status not in ("creator", "administrator", "owner"):
                raise RuntimeError("The connected account needs permission to post in the destination channel.")
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError("Could not verify destination-channel access. Check that the connected account can post there.") from exc

        task["target"] = html.escape(getattr(target, "title", None) or str(target.id))
        task["status"] = "scanning"
        selected = []
        if task["mode"] == "pinned":
            async for msg in userbot.get_chat_history(source.id):
                if task.get("status") == "stopped":
                    return
                while task.get("status") == "paused":
                    await asyncio.sleep(0.5)
                if getattr(msg, "pinned", False):
                    selected.append(msg.id)
            # Keep the original channel order (oldest pinned first).
            selected.reverse()
        else:
            async for msg in userbot.get_chat_history(source.id):
                if task.get("status") == "stopped":
                    return
                while task.get("status") == "paused":
                    await asyncio.sleep(0.5)
                selected.append(msg.id)
            selected.reverse()
        task["limit"] = len(selected)
        if not selected:
            task["status"] = "completed"
            task["error"] = "No messages found for the selected option."
            return
        task["status"] = "running"
        for message_id in selected:
            while task.get("status") == "paused":
                await asyncio.sleep(0.5)
            if task.get("status") == "stopped":
                break
            try:
                await userbot.forward_messages(
                    chat_id=target.id,
                    from_chat_id=source.id,
                    message_ids=message_id,
                    drop_author=bool(task.get("hide_sender", False))
                )
                task["sent"] += 1
            except FloodWait as fw:
                task["status"] = "paused"
                task["last_error"] = f"Telegram rate limit; waiting {fw.value}s"
                wait_left = int(fw.value)
                while wait_left > 0 and task.get("status") != "stopped":
                    if task.get("status") == "running":
                        await asyncio.sleep(1)
                        wait_left -= 1
                    else:
                        await asyncio.sleep(0.5)
                if task.get("status") != "stopped":
                    task["status"] = "running"
                # Don't silently skip the message after a rate limit.
                if task.get("status") != "stopped":
                    try:
                        await userbot.forward_messages(chat_id=target.id, from_chat_id=source.id,
                                                       message_ids=message_id,
                                                       drop_author=bool(task.get("hide_sender", False)))
                        task["sent"] += 1
                    except Exception as exc:
                        task["failed"] += 1
                        task["last_error"] = str(exc)[:180]
            except Exception as exc:
                task["failed"] += 1
                task["last_error"] = str(exc)[:180]
            task["current"] += 1
            await asyncio.sleep(0.15)
        if task.get("status") != "stopped":
            task["status"] = "completed"
    except Exception as exc:
        task["status"] = "error"
        task["error"] = str(exc)[:350]
    finally:
        if userbot:
            try:
                await userbot.stop()
            except Exception:
                pass


async def forward_dashboard(user_id, chat_id, message_id):
    uid = str(user_id)
    while uid in FORWARD_TASKS:
        task = FORWARD_TASKS[uid]
        status = task.get("status", "running")
        total = int(task.get("limit", 0) or 0)
        current = int(task.get("current", 0) or 0)
        progress = min(1.0, current / max(1, total)) if total else 0
        filled = int(progress * 15)
        bar = "█" * filled + "░" * (15 - filled)
        pct = int(progress * 100) if total else 0
        text = (f"{E_GLOBE} <b>CHANNEL FORWARDING</b>\n\n"
                f"{E_LNK} <b>Target:</b> <code>{task.get('target', 'Resolving channel...')}</code>\n"
                f"{E_ACT} <b>Status:</b> <code>{status.upper()}</code>\n"
                f"{E_CHK} <b>Forwarded:</b> <code>{task.get('sent', 0)}</code>\n"
                f"{E_WRN} <b>Failed:</b> <code>{task.get('failed', 0)}</code>\n"
                f"<code>[{bar}] {pct}%</code>")
        if task.get("last_error"):
            text += f"\n\n<i>Latest issue: {html.escape(task['last_error'])}</i>"
        if task.get("error"):
            text += f"\n\n<i>{html.escape(task['error'])}</i>"
        if status in ("running", "paused", "scanning"):
            controls = []
            if status == "paused":
                controls.append(ibtn("▶️ Resume", f"fwd_resume_{uid}", style="success"))
            elif status == "running":
                controls.append(ibtn("⏸️ Pause", f"fwd_pause_{uid}", style="primary"))
            controls.append(ibtn("❌ Cancel", f"fwd_cancel_{uid}", style="danger"))
            kb = {"inline_keyboard": [controls]}
        else:
            kb = {"inline_keyboard": [[ibtn("Back to Menu", "back_home", style="primary", icon=BTN_EMOJIS["home"])]]}
        try:
            await api_edit(chat_id, message_id, text, kb=kb)
        except Exception:
            pass
        if status in ("completed", "stopped", "error"):
            break
        await asyncio.sleep(2)


# ================= CORE HANDLERS =================
async def handle_join_requests(client, message):
    user_id = str(message.from_user.id); chat_id = str(message.chat.id)
    await users_col.update_one({"_id": user_id}, {"$addToSet": {"pending_chats": chat_id}}, upsert=True)

async def check_force_join(user_id):
    if int(user_id) in ADMINS: return True, []
    config = await settings_col.find_one({"_id": "config"}); u = await get_user(user_id)
    pending_chats = set(u.get("pending_chats", []))
    
    fsub_channels = config.get("fsub_channels", [])
    not_joined = []
    
    for i, ch in enumerate(fsub_channels):
        chat_id = str(ch.get("id"))
        link = ch.get("link", "")
        title = ch.get("title", f"Channel {i+1}")
        if not chat_id or chat_id == "none": continue
        if chat_id in pending_chats or chat_id.replace("-100", "") in pending_chats: continue
        try:
            if chat_id.startswith("-100"): await bot.get_chat_member(int(chat_id), int(user_id))
            elif "t.me/" in chat_id: await bot.get_chat_member(chat_id.split("/")[-1], int(user_id))
            else: await bot.get_chat_member(chat_id, int(user_id))
        except UserNotParticipant: not_joined.append((title, link))
        except Exception: not_joined.append((title, link))

    reqall_id = config.get("reqall_id", "none")
    if reqall_id != "none":
        reqall_link = config.get("reqall_link", "none")
        if str(reqall_id) not in pending_chats and str(reqall_id).replace("-100", "") not in pending_chats:
            try:
                if reqall_id.startswith("-100"): await bot.get_chat_member(int(reqall_id), int(user_id))
                elif "t.me/" in reqall_id: await bot.get_chat_member(reqall_id.split("/")[-1], int(user_id))
                else: await bot.get_chat_member(reqall_id, int(user_id))
            except UserNotParticipant: not_joined.append(("Mandatory Request", reqall_link))
            except Exception: not_joined.append(("Mandatory Request", reqall_link))

    return len(not_joined) == 0, not_joined

async def get_home_menu(user_id, first_name, config):
    user_id_str = str(user_id)
    free_limit = int(config.get('free_trial_limit') or 100)

    text = f"""{E_PREM} <i><b>DEVESH DMS AUTOMATION ENGINE</b></i> {E_PREM}
<i>Advanced High-Speed Marketing & Telegram Outreach System</i>

<i>Welcome to the premier Telegram automation panel. Maximize your campaign reach with zero ban risk, utilizing our ultra-fast smart cloud nodes.</i>

━━━━━━━━━━━━━━━━━━━━
{E_PROF} <i><b>User Profile:</b> {first_name}</i>
{E_ID} <i><b>Account ID:</b> <code>{user_id_str}</code></i>
{E_ACT} <i><b>Node Status:</b> {E_DOT} Active & Online</i>
━━━━━━━━━━━━━━━━━━━━

{E_CHK} <i>Expand your outreach safely and efficiently.</i>
{E_GIFT} <i>Claim your <b>{free_limit} Free Trial DMs</b> today.</i>

<i>Support & Inquiries — @okdruv</i>"""

    btns = [
        [ibtn("START MASS DM CAMPAIGN", "start_dm", style="success", icon=BTN_EMOJIS["start"])],
        [ibtn("Forward Messages", "forward_messages_start", style="primary", icon=BTN_EMOJIS["globe"])],
        [ibtn("FAST Auto-Forward DM", "set_fwd_msg", style="primary", icon=BTN_EMOJIS["globe"])], 
        [ibtn("Scrape Group", "scrape_group", style="primary", icon=BTN_EMOJIS["user"]), ibtn("Play & Win", "play_win", style="primary", icon=BTN_EMOJIS["gift"])],
        [ibtn("👤 User Dashboard", "user_dashboard", style="primary", icon=BTN_EMOJIS["user"])],
        [ibtn("Account Manage", "account_manage", style="primary", icon=BTN_EMOJIS["account_manage"])],
        [ibtn("VIP Premium", "buy_premium", style="danger", icon=BTN_EMOJIS["diamond"]), ibtn("My Account", "my_account", style="primary", icon=BTN_EMOJIS["user"])],
        [ibtn("Mystery Box", "mystery_box", style="success", icon=BTN_EMOJIS["gift"]), ibtn("👥 Refer & Earn", "referral", style="primary")],
        [ibtn("Premium History", "premium_history", style="primary")],
        [ibtn("Add Session", "add_session", style="success", icon=BTN_EMOJIS["add"]), ibtn("Remove Session", "remove_session", style="danger", icon=BTN_EMOJIS["cross"])],
        [ibtn("Delete All Chats", "confirm_del_chats", style="danger", icon=BTN_EMOJIS["cross"]), ibtn("Accept Request", "accept_pending", style="success", icon=BTN_EMOJIS["tick"])],
        [ibtn("Join Request DM", "start_dm", style="success", icon=BTN_EMOJIS["start"]), ibtn("Redeem Code", "redeem_code", style="success", icon=BTN_EMOJIS["gift"])],
        [ibtn("Tutorial & Terms", "how_to_use", style="primary", icon=BTN_EMOJIS["setting"])],
        [ibtn("Contact Support", url="https://t.me/okdruv", style="danger", icon=BTN_EMOJIS["target"])]
    ]
    
    if int(user_id) in ADMINS:
        btns.append([ibtn("⚙️ Admin Control Terminal", "adm_home", style="primary", icon=BTN_EMOJIS["setting"])])

    return text, {"inline_keyboard": btns}

async def get_chat_safely(client, raw_link, fallback_id):
    try:
        parsed_id = int(fallback_id) if str(fallback_id).lstrip('-').isdigit() else fallback_id
        return await client.get_chat(parsed_id)
    except Exception: pass
    link = str(raw_link).strip()
    if "t.me/" in link:
        if "+" in link or "joinchat" in link:
            hash_str = link.split("+")[-1].replace("/", "") if "+" in link else link.split("joinchat/")[-1].replace("/", "")
            try: return await client.join_chat(link)
            except UserAlreadyParticipant:
                try:
                    res = await client.invoke(CheckChatInvite(hash=hash_str))
                    title = getattr(res, 'title', None)
                    if not title and hasattr(res, 'chat'): title = getattr(res.chat, 'title', None)
                    if title:
                        async for d in client.get_dialogs(limit=5000):
                            if d.chat and d.chat.title == title: return d.chat
                except Exception: pass
            except Exception: pass
        else:
            username = "@" + link.split("t.me/")[-1].split("/")[0].replace("@", "")
            try: return await client.get_chat(username)
            except Exception: pass
    parsed_id_str = str(fallback_id)
    async for d in client.get_dialogs(limit=5000):
        if str(d.chat.id) == parsed_id_str or (d.chat.username and d.chat.username.lower() == parsed_id_str.replace("@", "").lower()): return d.chat
    raise Exception("Chat Link Unresolved! Ensure the link is valid or the alt account is Admin in the target group.")

async def check_and_show_stats(client, user_id, user_data, config, input_link, msg_to_edit, save_new=False):
    userbot = None
    try:
        userbot = Client(f"check_{user_id}_{int(time.time())}", api_id=API_ID, api_hash=API_HASH, session_string=user_data['sessions'][0], in_memory=True)
        await userbot.start(); await asyncio.sleep(1) 
        chat = await get_chat_safely(userbot, input_link, input_link)
        real_chat_id = chat.id; chat_title = chat.title
        
        try:
            peer = await userbot.resolve_peer(real_chat_id)
            r = await userbot.invoke(GetChatInviteImporters(peer=peer, requested=True, offset_date=0, offset_user=InputUserEmpty(), limit=1))
            pending_count = getattr(r, "count", 0)
        except Exception as api_err:
            if "CHAT_ADMIN_REQUIRED" in str(api_err):
                await userbot.stop()
                err_text = f"{E_WRN} <i><b>Admin Privileges Required!</b>\n\nYour connected session account MUST be an Admin in <b>{html.escape(chat_title)}</b> to read join requests.\n\nPromote your account with 'Add Users' permissions, then try again.</i>"
                btn = {"inline_keyboard": [[ibtn("Back Menu", "start_dm", style="danger", icon=BTN_EMOJIS["cross"])]]}
                return await api_edit(msg_to_edit.chat.id, msg_to_edit.id, err_text, btn)
            pending_count = 0
            
        await userbot.stop()
        
        if user_id not in USER_STATES: USER_STATES[user_id] = {}
        USER_STATES[user_id]["link"] = str(real_chat_id); USER_STATES[user_id]["raw_link"] = str(input_link); USER_STATES[user_id]["state"] = None 
        
        if save_new:
            new_ch = {"id": str(real_chat_id), "title": chat_title, "link": str(input_link)}
            exists = any(str(existing.get("id")) == str(real_chat_id) for existing in user_data.get("saved_channels", []))
            if not exists: await users_col.update_one({"_id": user_id}, {"$push": {"saved_channels": new_ch}})
        
        msg_delay = int(config.get("msg_delay") or 0)
        expected_sec = int(pending_count) * msg_delay
        h, rem = divmod(expected_sec, 3600); m, s = divmod(rem, 60)
        duration_str = f"{h}h {m}m" if h > 0 else (f"{m}m {s}s" if m > 0 else f"{s}s")
        
        stats_text = f"{E_CHK} <i><b>Channel Found:</b> {html.escape(chat_title)}\n{E_PROF} <b>Pending Requests:</b> {pending_count}\n{E_WAIT} <b>Estimated Duration:</b> ~{duration_str}</i>"
        await api_edit(msg_to_edit.chat.id, msg_to_edit.id, stats_text)
            
        sessions = user_data['sessions']
        if len(sessions) <= 1:
            USER_STATES[user_id]["sess_idx"] = "all"; USER_STATES[user_id]["state"] = "WAITING_LIMIT"
            await api_send(user_id, f"{E_STAT} <i><b>How many DMs would you like to send?</b>\n(Please send a numeric amount)</i>", {"inline_keyboard": [[ibtn("Cancel", "start_dm", style="danger", icon=BTN_EMOJIS["cross"])]]})
        else:
            text = f"{E_SYNC} <i><b>Multiple Accounts Detected!</b>\nSelect which account to deploy:</i>"
            btns = [[ibtn(f"Account {i+1}", f"selsess_{i}", style="primary", icon=BTN_EMOJIS["user"])] for i in range(len(sessions))]
            btns.append([ibtn("Deploy All Accounts", "selsess_all", style="success", icon=BTN_EMOJIS["tick"])])
            btns.append([ibtn("Cancel", "start_dm", style="danger", icon=BTN_EMOJIS["cross"])])
            await api_send(user_id, text, {"inline_keyboard": btns})
    except Exception as e_err: 
        if userbot:
            try: await userbot.stop()
            except: pass
        err_text = f"{E_CROSS} <i><b>Channel Connection Failed:</b>\n<code>{html.escape(str(e_err))}</code>\n\nEnsure the invite link is valid and your account is a member/admin.</i>"
        try: await api_edit(msg_to_edit.chat.id, msg_to_edit.id, err_text, {"inline_keyboard": [[ibtn("Back", "start_dm", style="danger", icon=BTN_EMOJIS["cross"])]]})
        except: await api_send(user_id, err_text)

# ULTRA FAST + EXACT FORMATTING + ALL MEDIA TYPES
async def bounded_send(semaphore, client, target_id, m_type, m_cont, m_cap):
    async with semaphore:
        try:
            if m_type == "text":
                await client.send_message(target_id, text=m_cont, parse_mode=enums.ParseMode.HTML)
            elif m_type == "photo":
                await client.send_photo(target_id, photo=m_cont, caption=m_cap, parse_mode=enums.ParseMode.HTML)
            elif m_type == "video":
                await client.send_video(target_id, video=m_cont, caption=m_cap, parse_mode=enums.ParseMode.HTML)
            elif m_type == "sticker":
                await client.send_sticker(target_id, sticker=m_cont)
            elif m_type == "voice":
                await client.send_voice(target_id, voice=m_cont, caption=m_cap, parse_mode=enums.ParseMode.HTML)
            elif m_type == "audio":
                await client.send_audio(target_id, audio=m_cont, caption=m_cap, parse_mode=enums.ParseMode.HTML)
            elif m_type == "document":
                await client.send_document(target_id, document=m_cont, caption=m_cap, parse_mode=enums.ParseMode.HTML)
            elif m_type == "animation":
                await client.send_animation(target_id, animation=m_cont, caption=m_cap, parse_mode=enums.ParseMode.HTML)
            elif m_type == "video_note":
                await client.send_video_note(target_id, video_note=m_cont)
            elif m_type == "forward_link":
                ch_username, m_id = m_cont.split("|")
                await client.forward_messages(target_id, ch_username, int(m_id))
            else:
                await client.send_message(target_id, m_cont, parse_mode=enums.ParseMode.HTML)
            return True
        except FloodWait as fw:
            await asyncio.sleep(fw.value)
            return False
        except Exception: return False

async def setup_and_execute_dm(user_id, limit, filter_type, delay_mins, is_free, channel_link, raw_link, sess_idx, client):
    user_id_str = str(user_id)
    try:
        user_data = await get_user(user_id)
        config = await settings_col.find_one({"_id": "config"})
        msg_delay = int(config.get("msg_delay") or 0)
        un = f"(@{user_data.get('username')})" if user_data.get('username') and user_data.get('username') != "N/A" else ""
        
        if delay_mins > 0:
            await api_send(user_id, f"{E_CAL} <i><b>Campaign Scheduled!</b>\nYour Mass DM task will begin automatically in {delay_mins} minutes.</i>")
            await asyncio.sleep(delay_mins * 60)
            
        sessions_db = user_data.get("sessions", [])
        sessions_to_use = sessions_db if sess_idx == "all" else [sessions_db[int(sess_idx)]]
        
        valid_clients = []
        for idx, s in enumerate(sessions_to_use):
            try:
                c = Client(f"ub_{user_id}_{int(time.time())}_{idx}", api_id=API_ID, api_hash=API_HASH, session_string=s, in_memory=True)
                await c.start()
                valid_clients.append(c)
            except Exception: pass
                
        if not valid_clients:
            return await api_send(user_id, f"{E_WRN} <i><b>All selected sessions are invalid or expired!</b> Please re-add your session.</i>")
            
        clients = valid_clients
        is_alt_dms = (channel_link == "ALT_DMS")
        chat_title = "Active Dialog DMs" if is_alt_dms else "Target Channel"
        chat_id_to_use = "ALT_DMS" if is_alt_dms else None
        
        if not is_alt_dms:
            target_raw = str(config.get("free_channel_link", "none")) if is_free else str(raw_link)
            fallback_id = config.get("free_channel_id", "none") if is_free else channel_link
            try:
                chat = await get_chat_safely(clients[0], target_raw, fallback_id)
                chat_id_to_use = chat.id; chat_title = chat.title
            except Exception as ce:
                for c in clients: 
                    try: await c.stop()
                    except: pass
                return await api_send(user_id, f"{E_WRN} <i><b>Could not access channel:</b> {ce}</i>")

        ACTIVE_TASKS[user_id_str] = {"status": "running", "sent": 0, "limit": limit, "start_time": time.time(), 
                                       "target": html.escape(chat_title), "nodes": len(clients)}
        
        # Spawn live dashboard
        dash_msg = await api_send(user_id, f"{E_SYNC} <i><b>Deploying Campaign Nodes...</b></i>")
        asyncio.create_task(dashboard_updater(user_id_str, dash_msg.chat.id, dash_msg.id))
        
        chat_id_str = str(chat_id_to_use)
        messaged_list = user_data.get("messaged_users", {}).get(chat_id_str, [])
        count, skipped, failed = 0, 0, 0
        
        log_channel = config.get("log_channel", "none")
        if log_channel != "none":
            try: 
                lc_id = int(log_channel) if str(log_channel).replace("-", "").isdigit() else log_channel
                await api_send(lc_id, f"{E_START} <i><b>Campaign Order</b>\nUser: <code>{user_id}</code> {un}\nTarget: {html.escape(chat_title)}\nLimit: {limit}</i>")
            except Exception: pass

        try:
            target_ids = []
            if is_alt_dms:
                for curr_client in clients:
                    async for dialog in curr_client.get_dialogs(): 
                        if dialog.chat and dialog.chat.type == enums.ChatType.PRIVATE:
                            tid = dialog.chat.id
                            if tid not in [777000, curr_client.me.id if hasattr(curr_client, "me") and curr_client.me else 0]: 
                                target_ids.append(tid)
            else:
                async for request in clients[0].get_chat_join_requests(chat_id_to_use):
                    target_ids.append(request.user.id)
                    
            # Parse EXACT formatting payload with full media support
            m_data = user_data.get("custom_msg_data", {"type": "text", "html": "HELLO"})
            m_type = m_data.get("type", "text")
            if m_type == "text":
                m_cont = m_data.get("html", "HELLO")
                m_cap = ""
            elif m_type == "forward_link":
                m_cont = user_data.get("custom_msg_fwd", "")
                m_cap = ""
            else:
                m_cont = m_data.get("file_id", "")
                m_cap = m_data.get("html", "")
            
            semaphore = asyncio.Semaphore(50) 
            tasks = []
            
            for tid in target_ids:
                task = ACTIVE_TASKS.get(user_id_str)
                if not task: break
                while task.get("status") == "paused":
                    await asyncio.sleep(1); task = ACTIVE_TASKS.get(user_id_str)
                    if not task: break
                if not task or task.get("status") == "stopped" or count >= limit: break 
                
                if str(tid) in messaged_list or tid in messaged_list:
                    skipped += 1; continue
                    
                curr_client = clients[count % len(clients)]
                tasks.append(bounded_send(semaphore, curr_client, tid, m_type, m_cont, m_cap))
                messaged_list.append(tid)
                count += 1
                
                if len(tasks) >= 100:
                    results = await asyncio.gather(*tasks)
                    failed += results.count(False)
                    ACTIVE_TASKS[user_id_str]["sent"] = count
                    tasks = []
                    if msg_delay > 0: await asyncio.sleep(msg_delay)
            
            if tasks:
                results = await asyncio.gather(*tasks)
                failed += results.count(False)
                ACTIVE_TASKS[user_id_str]["sent"] = count

        except Exception as e_dm: 
            await api_send(user_id, f"{E_CROSS} <i><b>Campaign Ended Prematurely:</b>\n<code>{html.escape(str(e_dm))}</code></i>")
        finally:
            for c in clients:
                try: await c.stop() 
                except: pass
            
            today = get_ist_str("%Y-%m-%d")
            await users_col.update_one({"_id": str(user_id)}, {"$inc": {"total_dms": count, "daily_dms": count}, "$set": {f"messaged_users.{chat_id_str}": messaged_list, "last_date": today}})
            await settings_col.update_one({"_id": "config"}, {"$inc": {"global_dms": count}})
            
            success_log = config.get("success_log_channel", "none")
            if success_log != "none":
                try: 
                    slc_id = int(success_log) if str(success_log).replace("-", "").isdigit() else slc_id
                    await api_send(slc_id, f"{E_CHK} <i><b>Campaign Completed</b>\nUser: <code>{user_id}</code>\nTarget: {html.escape(chat_title)}\nTotal Sent: {count}</i>")
                except Exception: pass

            if user_id_str in ACTIVE_TASKS: del ACTIVE_TASKS[user_id_str]
            
            final_text = f"""{E_CHK} <b>CAMPAIGN COMPLETED</b>

━━━━━━━━━━━━━━━━━━━━
{E_LNK} <b>Target:</b> {html.escape(chat_title)}
{E_CHK} <b>Delivered:</b> <code>{count}</code>
{E_PLAY} <b>Skipped:</b> <code>{skipped}</code>
{E_CROSS} <b>Failed:</b> <code>{failed}</code>
━━━━━━━━━━━━━━━━━━━━

{E_SHD} <i>Session credentials secured.</i>"""
            try: 
                await api_edit(dash_msg.chat.id, dash_msg.id, final_text, 
                               kb={"inline_keyboard": [[ibtn("Back to Menu", "back_home", style="primary", icon=BTN_EMOJIS["home"])]]})
            except: pass
            
    except Exception as general_error:
        try: await api_send(user_id, f"{E_CROSS} <i><b>Campaign Guard Triggered:</b>\n<code>{html.escape(str(general_error))}</code></i>")
        except: pass

# ================= ACCOUNT MANAGER (INCOMING DM GUARD) =================
async def account_manager_incoming(user_id, account_client, message):
    """Handle incoming private DMs only; count warnings and reply from the connected account."""
    try:
        if not message.from_user or message.from_user.is_bot or message.from_user.is_self:
            return
        sender_id = int(message.from_user.id)
        u = await get_user(user_id)
        cfg = u.get("account_manager", {}) or {}
        if not cfg.get("enabled", False):
            return

        # Persist each sender's warning count independently.
        counts = dict(cfg.get("warning_counts", {}) or {})
        key = str(sender_id)
        count = int(counts.get(key, 0)) + 1
        counts[key] = count
        await users_col.update_one({"_id": str(user_id)}, {"$set": {"account_manager.warning_counts": counts}})

        limit = max(0, min(100, int(cfg.get("message_limit", 3))))
        if count > limit:
            try:
                await account_client.send_message(sender_id, "You have exceeded the message limit. This account is now blocking further messages.")
            except Exception:
                pass
            try:
                await account_client.block_user(sender_id)
            except Exception as block_error:
                print(f"Account Manager block failed for {sender_id}: {block_error}")
            return

        # A saved template is copied by the connected user account, preserving media/caption/entities.
        template_chat = cfg.get("auto_message_chat")
        template_message = cfg.get("auto_message_message_id")
        if template_chat and template_message:
            try:
                await account_client.copy_message(
                    chat_id=sender_id,
                    from_chat_id=int(template_chat),
                    message_id=int(template_message)
                )
                return
            except Exception as copy_error:
                print(f"Account Manager template copy failed for {sender_id}: {copy_error}")

        custom = (cfg.get("auto_message", "") or "").strip()
        if custom:
            await account_client.send_message(sender_id, custom)
        else:
            await account_client.send_message(
                sender_id,
                f"Message received. Please wait for the admin's reply. Warning {count}/{limit}."
            )
    except Exception as exc:
        print(f"Account Manager incoming handler error: {exc}")

async def start_account_manager(user_id):
    """Start monitoring the first connected Telegram session for this owner."""
    uid = str(user_id)
    existing = ACCOUNT_MONITORS.get(uid)
    if existing is not None and getattr(existing, "is_connected", False):
        return True
    if existing is not None:
        ACCOUNT_MONITORS.pop(uid, None)
    lock = ACCOUNT_MONITOR_LOCKS.setdefault(uid, asyncio.Lock())
    async with lock:
        existing = ACCOUNT_MONITORS.get(uid)
        if existing is not None and getattr(existing, "is_connected", False):
            return True
        if existing is not None:
            ACCOUNT_MONITORS.pop(uid, None)
        u = await get_user(uid)
        sessions = u.get("sessions", [])
        if not sessions:
            return False
        monitor = Client(f"acct_mgr_{uid}", api_id=API_ID, api_hash=API_HASH,
                         session_string=sessions[0], in_memory=True)
        async def _incoming(client, message):
            try:
                if message.chat and message.chat.type == enums.ChatType.PRIVATE and message.from_user and not message.outgoing:
                    await account_manager_incoming(uid, client, message)
            except Exception as handler_error:
                print(f"Account Manager handler failed for {uid}: {handler_error}")
        try:
            # Register before starting so the first incoming update is not missed.
            monitor.add_handler(MessageHandler(_incoming, filters.private & filters.incoming), group=0)
            await monitor.start()
            ACCOUNT_MONITORS[uid] = monitor
            return True
        except Exception as exc:
            print(f"Account Manager could not start for {uid}: {exc}")
            try:
                await monitor.stop()
            except Exception:
                pass
            return False

async def account_manager_screen(query, user_id):
    u = await get_user(user_id)
    cfg = u.get("account_manager", {})
    enabled = bool(cfg.get("enabled", False))
    limit = int(cfg.get("message_limit", 3))
    auto = cfg.get("auto_message", "")
    status = "ON" if enabled else "OFF"
    has_template = bool(cfg.get("auto_message_message_id"))
    msg = "Custom message saved (text/media)" if has_template else ((html.escape(auto[:100]) + ("…" if len(auto) > 100 else "")) if auto else "Not set (warning reply active)")
    text = (f"<b>👤 ACCOUNT MANAGE</b>\n\n"
            f"Status: <b>{status}</b>\nMessage limit: <b>{limit}</b>\n"
            f"Auto message: <code>{msg}</code>\n\n"
            f"Incoming private messages only are monitored. Each sender gets {limit} warning(s); the next message is blocked. Warning counts do not reset automatically; use Reset Warnings.")
    kb = {"inline_keyboard": [
        [ibtn("Set Message Limit", "acct_set_limit", style="primary")],
        [ibtn("Set Message", "acct_set_message", style="success")],
        [ibtn("Reset Warnings", "acct_reset_warnings", style="primary")],
        [ibtn("Turn OFF" if enabled else "Turn ON", "acct_toggle", style="danger" if enabled else "success")],
        [ibtn("Back", "back_home", style="primary")]
    ]}
    return await safe_edit(query, text, kb=kb)

# ================= ROUTE HANDLERS =================
async def start_cmd(client, message):
    try:
        user_id = str(message.chat.id)
        u = await get_user(user_id)
        if u.get("account_manager", {}).get("enabled") and u.get("sessions"):
            asyncio.create_task(start_account_manager(user_id))
        config = await settings_col.find_one({"_id": "config"})
        # Referral attribution is accepted only once, for a genuinely new account.
        if message.command and len(message.command) > 1 and not u.get("referrer_id") and not u.get("referral_rewarded") and u.get("created_at") and (time.time() - float(u.get("created_at", 0)) <= 600):
            raw_ref = str(message.command[1]).replace("ref_", "").strip()
            if raw_ref.isdigit() and raw_ref != user_id and config.get("anti_fraud_enabled", True):
                ref_user = await users_col.find_one({"_id": raw_ref})
                if ref_user:
                    await users_col.update_one({"_id": user_id}, {"$set": {"referrer_id": raw_ref}})
                    await users_col.update_one({"_id": raw_ref}, {"$inc": {"referrals": 1}})
                    bonus = max(0, int(config.get("ref_bonus", 50)))
                    await users_col.update_one({"_id": raw_ref}, {"$inc": {"referral_bonus_dms": bonus}})
                    premium_days = max(0, min(3650, int(config.get("ref_premium_days", 0) or 0)))
                    if premium_days > 0:
                        expiry = await grant_premium(raw_ref, premium_days, "Referral reward")
                        try:
                            await bot.send_message(int(raw_ref), f"🎉 Referral successful! You received {premium_days} Premium day(s).\nExpiry: {get_ist_ts_str(expiry)}")
                        except Exception:
                            pass
                    await users_col.update_one({"_id": user_id}, {"$set": {"referral_rewarded": True}})

        if int(user_id) not in ADMINS:
            joined, not_joined_list = await check_force_join(user_id)
            if not joined:
                text = f"{E_WRN} <i><b>Subscription Verification Required!</b>\n\nTo ensure quality service, please join our official channels before continuing.</i>"
                btn_list = []; row = []
                for i, (idx, link) in enumerate(not_joined_list):
                    fixed_link = link if str(link).startswith("http") else f"https://t.me/{str(link).replace('@','')}"
                    row.append(ibtn(f"{idx}", url=fixed_link, style="primary", icon=BTN_EMOJIS["target"]))
                    if len(row) == 2: btn_list.append(row); row = []
                if row: btn_list.append(row)
                btn_list.append([ibtn("I Have Joined", "check_join", style="success", icon=BTN_EMOJIS["tick"])])
                return await api_send(user_id, text, {"inline_keyboard": btn_list})

        first_name = html.escape(message.from_user.first_name if message.from_user else "User")
        text, btn = await get_home_menu(user_id, first_name, config)
        await api_send(user_id, text, kb=btn)
    except Exception as e_start: 
        print(f"Error in start_cmd: {e_start}")

async def shortcut_cmds(client, message):
    user_id = str(message.chat.id); cmd = message.command[0]; config = await settings_col.find_one({"_id": "config"})
    
    if int(user_id) not in ADMINS:
        joined, _ = await check_force_join(user_id)
        if not joined: return await api_send(user_id, f"{E_CROSS} <i><b>Please use /start to verify channels first.</b></i>")

    if user_id not in USER_STATES: USER_STATES[user_id] = {}

    if cmd == "myaccount":
        has_prem = await is_premium(user_id); u = await get_user(user_id)
        if has_prem:
            exp_str = get_ist_ts_str(u['premium_expiry'])
            status = f"{E_DIA} <i>VIP Premium\n{E_CAL} <b>Expiry:</b> {exp_str}</i>"
        else: status = f"{E_WAIT} <i>Free Tier</i>"
        text = f"{E_PROF} <i><b>User Account Details:</b>\n\n{E_ID} <b>ID:</b> <code>{user_id}</code>\n{E_SHD} <b>Plan Status:</b> {status}\n{E_ACT} <b>Connected Sessions:</b> {len(u.get('sessions', []))}\n{E_STAT} <b>Lifetime DMs Sent:</b> {u.get('total_dms', 0)}</i>"
        await api_send(user_id, text, {"inline_keyboard": [[ibtn("Reset DM History", "reset_history", style="danger", icon=BTN_EMOJIS["cross"])]]})

    elif cmd == "buypremium":
        p1, p3, p7, p30 = (plan_price_label(config, d) for d in (1, 3, 7, 30))
        text = f"{E_PREM} <i><b>VIP Subscription Plans</b>\n\n<b>1 Day:</b> {p1}\n<b>3 Days:</b> {p3}\n<b>7 Days:</b> {p7}\n<b>1 Month:</b> {p30}\n\nSelect a subscription plan below:</i>"
        btn = {"inline_keyboard": [[ibtn("1 Day Plan", "plan_1", style="primary", icon=BTN_EMOJIS["diamond"]), ibtn("3 Days Plan", "plan_3", style="primary", icon=BTN_EMOJIS["diamond"])], [ibtn("7 Days Plan", "plan_7", style="success", icon=BTN_EMOJIS["diamond"]), ibtn("1 Month Plan", "plan_30", style="success", icon=BTN_EMOJIS["crown"])]]}
        await api_send(user_id, text, btn)

    elif cmd == "massdm":
        u = await get_user(user_id)
        if not u.get("sessions"): return await api_send(user_id, f"{E_CROSS} <i><b>No Active Sessions Found!</b> Please connect an account first.</i>")
        USER_STATES[user_id]["state"] = "WAITING_DM_LINK"
        await api_send(user_id, f"{E_START} <i><b>Start Mass DM Campaign</b>\nPlease provide your target channel link.</i>")

async def check_total_public(client, message):
    config = await settings_col.find_one({"_id": "config"})
    await api_send(message.chat.id, f"{E_STAT} <i><b>Global Platform Metrics:</b>\nTotal Messages Delivered Worldwide: <b>{config.get('global_dms', 0)}</b></i>")

# ================= 🎛️ ADMIN DASHBOARD =================
async def get_admin_dashboard(config):
    auto_status = f"{E_DOT} ACTIVE" if config.get("auto_payment_status", False) else f"{E_STOP} DISABLED"
    maint_status = f"{E_STOP} ON" if config.get("maintenance", False) else f"{E_DOT} OFF"
    total_users = await users_col.count_documents({})
    active_now = len(ACTIVE_TASKS)

    text = f"""{E_ADM} <i><b>Master Administration Terminal</b></i>

━━━━━━━━━━━━━━━━━━━━
{E_STAT} <i><b>Server Health & System Metrics:</b></i>
{E_PROF} <i><b>Total Registered Users:</b> <code>{total_users}</code></i>
{E_ACT} <i><b>Active DM Processes:</b> <code>{active_now}</code></i>
{E_GLOBE} <i><b>Lifetime Delivered DMs:</b> <code>{config.get('global_dms', 0)}</code></i>
{E_MONEY} <i><b>Gross Sales Revenue:</b> <code>₹{config.get('total_sales_inr', 0)}</code></i>
━━━━━━━━━━━━━━━━━━━━
{E_ADM} <i><b>Automated Operations:</b></i>
• <i><b>Instant UPI Payment Gateway:</b> {auto_status}</i>
• <i><b>Maintenance Mode:</b> {maint_status}</i>
━━━━━━━━━━━━━━━━━━━━
<i>Select any category below to manage configurations:</i>"""

    btns = [
        [ibtn("Stats & Insights", "adm_stats", style="primary", icon=BTN_EMOJIS["stats"]), ibtn("Sales & Revenue", "adm_sales", style="success", icon=BTN_EMOJIS["money"])],
        [ibtn(f"Live Tasks ({active_now})", "adm_ongoing", style="primary", icon=BTN_EMOJIS["start"]), ibtn("Broadcast Message", "adm_broadcast", style="success", icon=BTN_EMOJIS["globe"])],
        [ibtn("Payment Gateways", "adm_cat_pay", style="primary", icon=BTN_EMOJIS["money"]), ibtn("Subscription Pricing", "adm_cat_price", style="primary", icon=BTN_EMOJIS["diamond"])],
        [ibtn("Channels & ForceSub", "adm_cat_channels", style="primary", icon=BTN_EMOJIS["target"]), ibtn("User Directory", "adm_cat_users", style="primary", icon=BTN_EMOJIS["user"])],
        [ibtn("Manage Admins", "adm_manage_admins", style="primary", icon=BTN_EMOJIS["shield"])],
        [ibtn("Button Layout", "adm_button_layout", style="success", icon=BTN_EMOJIS["setting"])],
        [ibtn("Operational Limits", "adm_cat_limits", style="primary", icon=BTN_EMOJIS["setting"]), ibtn("Create Redeem Code", "adm_gen_code", style="success", icon=BTN_EMOJIS["gift"])],
        [ibtn("Redeem Code History", "adm_code_history", style="primary", icon=BTN_EMOJIS["stats"])],
        [ibtn("Mystery Box Controls", "adm_mystery", style="success"), ibtn("Game & Anti-Fraud", "adm_game_controls", style="primary")],
        [ibtn("Extract Emoji Pack IDs", "adm_extract_emoji", style="success", icon=BTN_EMOJIS["gift"])],
        [
            ibtn(f"{'Disable' if config.get('auto_payment_status') else 'Enable'} Auto-Pay", "adm_toggle_auto", style="danger" if config.get('auto_payment_status') else "success", icon=BTN_EMOJIS["tick"]),
            ibtn(f"Maintenance: {'OFF' if config.get('maintenance') else 'ON'}", "adm_toggle_maint", style="success" if config.get('maintenance') else "danger", icon=BTN_EMOJIS["shield"])
        ],
        [ibtn("Exit Admin Terminal", "adm_close", style="danger", icon=BTN_EMOJIS["cross"])]
    ]
    return text, {"inline_keyboard": btns}

async def admin_panel(client, message):
    if message.from_user.id not in ADMINS: return
    config = await settings_col.find_one({"_id": "config"})
    text, kb = await get_admin_dashboard(config)
    await api_send(message.chat.id, text, kb=kb)

async def master_admin_cmds(client, message):
    if message.from_user.id not in ADMINS: return
    cmd = message.command[0]
    config = await settings_col.find_one({"_id": "config"})
    
    if cmd == "gencode":
        if len(message.command) < 2 or not message.command[1].isdigit():
            return await api_send(message.chat.id, f"{E_CROSS} <i>Usage: <code>/gencode [Days]</code></i>")
        days = int(message.command[1])
        code = f"DEVESH-{uuid.uuid4().hex[:8].upper()}"
        codes = config.get("redeem_codes", {})
        codes[code] = {"days": days, "used": False, "created_at": time.time()}
        await settings_col.update_one({"_id": "config"}, {"$set": {"redeem_codes": codes}})
        await api_send(message.chat.id, f"{E_CHK} <i><b>Redeem Code Generated!</b>\n\nCode: <code>{code}</code>\nDuration: <b>{days} Days</b></i>")

    elif cmd == "toggleauto":
        current = config.get("auto_payment_status", False)
        await settings_col.update_one({"_id": "config"}, {"$set": {"auto_payment_status": not current}})
        await api_send(message.chat.id, f"{E_CHK} <i>Auto-Approve status toggled to: {'ON' if not current else 'OFF'}.</i>")
        
    elif cmd == "maintenance":
        if len(message.command) < 2: return await api_send(message.chat.id, f"{E_CROSS} <i>Usage: <code>/maintenance [on/off]</code></i>")
        val = message.command[1].lower() == "on"
        await settings_col.update_one({"_id": "config"}, {"$set": {"maintenance": val}})
        await api_send(message.chat.id, f"{E_CHK} <i>Maintenance mode set to {'ON' if val else 'OFF'}.</i>")
        
    elif cmd == "reqall":
        if len(message.command) == 1:
            await settings_col.update_one({"_id": "config"}, {"$set": {"reqall_id": "none"}})
            await api_send(message.chat.id, f"{E_CHK} <i>Mandatory request channel disabled.</i>")
        elif len(message.command) >= 3:
            await settings_col.update_one({"_id": "config"}, {"$set": {"reqall_id": message.command[1], "reqall_link": message.command[2]}})
            await api_send(message.chat.id, f"{E_CHK} <i>Mandatory request channel updated.</i>")
            
    elif cmd in ["setfampay", "setmanual", "setcrypto"]:
        key = cmd.replace("set", "upi_") if "crypto" not in cmd else "crypto"
        await settings_col.update_one({"_id": "config"}, {"$set": {key: message.command[1]}})
        await api_send(message.chat.id, f"{E_CHK} <i>Configuration parameter updated.</i>")
            
    elif cmd in ["setprice1d", "setprice3d", "setprice7d", "setprice1m"]:
        tk = cmd.replace("setprice", "")
        await settings_col.update_one({"_id": "config"}, {"$set": {f"price_{tk}_inr": message.command[1], f"price_{tk}_usd": message.command[2]}})
        await api_send(message.chat.id, f"{E_CHK} <i>Subscription rate updated.</i>")
        
    elif cmd in ["setlogchannel", "setsuccesslog", "setleaderboard", "setfreechannel"]:
        k = cmd.replace("set", "")
        if "freechannel" in cmd: await settings_col.update_one({"_id": "config"}, {"$set": {"free_channel_id": message.command[1], "free_channel_link": message.command[2]}})
        else: await settings_col.update_one({"_id": "config"}, {"$set": {f"{k}_channel" if "log" not in cmd else k: message.command[1]}})
        await api_send(message.chat.id, f"{E_CHK} <i>System channel route updated.</i>")
        
    elif cmd in ["setfreetrial", "setldbtime", "setdelay", "setfreereq", "setrefbonus"]:
        if len(message.command) < 2: return await api_send(message.chat.id, f"{E_CROSS} <i>Usage: <code>/{cmd} [Number]</code></i>")
        km = {"setfreetrial": "free_trial_limit", "setdelay": "msg_delay", "setldbtime": "ldb_time", "setfreereq": "free_req_limit", "setrefbonus": "ref_bonus"}
        await settings_col.update_one({"_id": "config"}, {"$set": {km[cmd]: int(message.command[1])}})
        await api_send(message.chat.id, f"{E_CHK} <i>Value updated successfully.</i>")
        
    elif cmd == "ongoing":
        if not ACTIVE_TASKS: return await api_send(message.chat.id, "<i>No tasks are running currently.</i>")
        text = f"{E_SYNC} <i><b>Ongoing Campaigns:</b></i>\n"
        for uid, t in ACTIVE_TASKS.items(): text += f"<i>ID: <code>{uid}</code> | Target: {t['target']} | Sent: {t['sent']}/{t['limit']}</i>\n"
        await api_send(message.chat.id, text)
        
    elif cmd == "sales":
        history = config.get("sales_history", {})
        t_str = get_ist_str("%Y-%m-%d"); y_str = time.strftime("%Y-%m-%d", time.gmtime(time.time() - 86400 + 19800))
        l_30 = sum(history.get(time.strftime("%Y-%m-%d", time.gmtime(time.time() - (i * 86400) + 19800)), 0) for i in range(30))
        text = f"{E_MONEY} <i><b>Revenue Tracker</b>\n\n{E_CAL} <b>Today's Sales:</b> ₹{history.get(t_str, 0)}\n{E_WAIT} <b>Yesterday's Sales:</b> ₹{history.get(y_str, 0)}\n{E_CAL} <b>Last 30 Days:</b> ₹{l_30}\n\n{E_CROWN} <b>Total Lifetime Sales:</b> ₹{config.get('total_sales_inr', 0)}</i>"
        await api_send(message.chat.id, text)
        
    elif cmd == "giveprem":
        t, d = message.command[1], int(message.command[2])
        u = await get_user(t); cur = time.time()
        nex = (u.get("premium_expiry", 0) + (d * 86400)) if u.get("premium_expiry", 0) > cur else (cur + (d * 86400))
        await users_col.update_one({"_id": t}, {"$set": {"premium_expiry": nex}})
        await api_send(message.chat.id, f"{E_CHK} <i>VIP Access granted to user {t}.</i>")
        
    elif cmd == "removeprem":
        await users_col.update_one({"_id": message.command[1]}, {"$set": {"premium_expiry": 0}})
        await api_send(message.chat.id, f"{E_CHK} <i>VIP Access revoked.</i>")

async def shared_admin_cmds(client, message):
    if message.from_user.id not in ADMINS: return
    cmd = message.command[0]
    
    if cmd == "stats":
        t_u = await users_col.count_documents({})
        await api_send(message.chat.id, f"{E_STAT} <i><b>Platform Statistics:</b>\nTotal Registered Users: {t_u}</i>")
    elif cmd == "checkuser":
        u = await get_user(message.command[1]); is_p = "Yes" if u.get('premium_expiry',0) > time.time() else "No"
        await api_send(message.chat.id, f"{E_PROF} <i>User: <code>{u['_id']}</code>\nPremium: {is_p}\nDMs Sent: {u.get('total_dms', 0)}\nSessions: {len(u.get('sessions', []))}</i>")
    elif cmd == "clearsession":
        await users_col.update_one({"_id": message.command[1]}, {"$set": {"sessions": []}})
        await api_send(message.chat.id, f"{E_CHK} <i>Sessions wiped for specified user.</i>")
    elif cmd == "banuser":
        await users_col.update_one({"_id": message.command[1]}, {"$set": {"banned": True}})
        await api_send(message.chat.id, f"{E_CHK} <i>User account suspended.</i>")
    elif cmd == "unbanuser":
        await users_col.update_one({"_id": message.command[1]}, {"$set": {"banned": False}})
        await api_send(message.chat.id, f"{E_CHK} <i>User account restored.</i>")
    elif cmd == "broadcast":
        if not message.reply_to_message: return await api_send(message.chat.id, f"{E_WRN} <i>Reply to any message with <code>/broadcast</code></i>")
        c = 0
        status_msg = await api_send(message.chat.id, f"{E_SYNC} <i>Broadcasting in progress...</i>")
        async for u in users_col.find({}):
            try: 
                await message.reply_to_message.copy(int(u["_id"]))
                c += 1
                await asyncio.sleep(0.05) 
            except: pass
        await api_edit(status_msg.chat.id, status_msg.id, f"{E_CHK} <i><b>Broadcast Completed!</b> Sent to {c} users.</i>")

@bot.on_callback_query()
async def cb_handler(client, query: CallbackQuery):
    try: await query.answer()
    except: pass
    user_id = str(query.message.chat.id); data = query.data; config = await settings_col.find_one({"_id": "config"})

    # ================= LIVE DASHBOARD CONTROLS =================
    if data.startswith("dmc_"):
        parts = data.split("_")
        action, uid = parts[1], parts[2]
        if uid in ACTIVE_TASKS:
            if action == "pause": 
                ACTIVE_TASKS[uid]["status"] = "paused"
                await query.answer("⏸️ Campaign paused!", show_alert=False)
            elif action == "resume": 
                ACTIVE_TASKS[uid]["status"] = "running"
                await query.answer("▶️ Campaign resumed!", show_alert=False)
            elif action == "stop": 
                ACTIVE_TASKS[uid]["status"] = "stopped"
                await query.answer("🛑 Campaign stopping...", show_alert=True)
        else:
            await query.answer("No active campaign!", show_alert=True)
        return

    # ================= 🎛️ ADMIN CALLBACK ROUTES =================
    if data in ["admin_panel", "adm_home"] or data.startswith("adm_") or data.startswith("emojipg_"):
        if int(query.from_user.id) not in ADMINS:
            return await query.answer("Access Denied: Admins Only.", show_alert=True)

        if data in ["admin_panel", "adm_home"]:
            text, kb = await get_admin_dashboard(config)
            return await safe_edit(query, text, kb=kb)

        elif data == "adm_button_layout":
            mode = config.get("user_button_mode", "inline")
            text = ("<b>🎛️ User Button Layout</b>\n\n"
                    "Choose how buttons should appear to all users.\n\n"
                    f"Current mode: <b>{'Inline buttons' if mode == 'inline' else 'Keyboard buttons'}</b>\n\n"
                    "• Inline: buttons appear under bot messages.\n"
                    "• Keyboard: buttons appear in the user's typing keyboard.\n"
                    "The same menu actions and navigation will continue to work.")
            return await safe_edit(query, text, kb={"inline_keyboard": [
                [ibtn("Inline", "adm_button_mode_inline", style="success" if mode == "inline" else "primary")],
                [ibtn("Keyboard", "adm_button_mode_keyboard", style="success" if mode == "keyboard" else "primary")],
                [ibtn("Back to Dashboard", "adm_home", style="danger")]
            ]})

        elif data in ("adm_button_mode_inline", "adm_button_mode_keyboard"):
            mode = "inline" if data.endswith("inline") else "keyboard"
            await settings_col.update_one({"_id": "config"}, {"$set": {"user_button_mode": mode}})
            config["user_button_mode"] = mode
            text = ("Inline buttons enabled for all users." if mode == "inline" else
                    "Keyboard buttons enabled for all users. Buttons will appear below the chat input and will support the same actions.")
            return await safe_edit(query, text, kb={"inline_keyboard": [
                [ibtn("Button Layout", "adm_button_layout", style="primary")],
                [ibtn("Back to Dashboard", "adm_home", style="danger")]
            ]})

        elif data == "adm_close":
            return await query.message.delete()

        elif data == "adm_extract_emoji":
            USER_STATES[user_id] = {"state": "ADM_WAIT_EMOJI_PACK"}
            text = f"""{E_STAT} <b>Premium Emoji Pack Extractor</b>

<i>Send the Telegram Emoji Pack link or short-name below to extract all Custom Emoji IDs.</i>

<b>Supported Formats:</b>
• <code>https://t.me/addemoji/PackName</code>
• <code>PackName</code>

<i>Results will be paginated 20 per page with live preview of each emoji.</i>"""
            btn = {"inline_keyboard": [[ibtn("Cancel", "adm_home", style="danger", icon=BTN_EMOJIS["cross"])]]}
            return await safe_edit(query, text, kb=btn)

        elif data.startswith("emojipg_"):
            pg = int(data.split("_")[1])
            u_state = USER_STATES.get(user_id, {})
            if "emojis" in u_state:
                emojis = u_state["emojis"]
                total_pages = max(1, math.ceil(len(emojis) / 20))
                pg = max(0, min(pg, total_pages - 1))
                chunk = emojis[pg*20 : (pg+1)*20]
                text = f"{E_STAT} <b>Extracted Emoji IDs — Page {pg+1}/{total_pages}</b>\n<i>Pack: <code>{u_state.get('pack_name','Unknown')}</code></i>\n\n" + "\n".join(chunk)
                btns = []
                row = []
                if pg > 0: row.append(ibtn("Prev", f"emojipg_{pg-1}", style="primary", icon=BTN_EMOJIS["prev"]))
                if pg < total_pages - 1: row.append(ibtn("Next", f"emojipg_{pg+1}", style="primary", icon=BTN_EMOJIS["next"]))
                if row: btns.append(row)
                btns.append([ibtn("Back to Dashboard", "adm_home", style="danger", icon=BTN_EMOJIS["cross"])])
                return await safe_edit(query, text, kb={"inline_keyboard": btns})

        elif data == "adm_manage_admins":
            current_admins = sorted(set(int(a) for a in ADMINS))
            text = f"{E_ADM} <i><b>Admin Access Management</b>\n\nAdmins can access the full admin panel. Add users by Telegram numeric ID or remove an existing admin.\n\n{E_PROF} <b>Current Admins:</b> {len(current_admins)}</i>"
            btns = [[ibtn("➕ Add Admin", "adm_add_admin", style="success", icon=BTN_EMOJIS["add"])]]
            for admin_id in current_admins:
                label = f"👑 {admin_id} (Owner)" if admin_id == OWNER_ADMIN_ID else f"🛡️ {admin_id}"
                row = [ibtn(label, "adm_admin_info", style="primary")]
                if admin_id != OWNER_ADMIN_ID:
                    row.append(ibtn("🗑 Remove", f"adm_deladmin_{admin_id}", style="danger", icon=BTN_EMOJIS["cross"]))
                btns.append(row)
            btns.append([ibtn("Back to Dashboard", "adm_home", style="danger", icon=BTN_EMOJIS["cross"])])
            return await safe_edit(query, text, kb={"inline_keyboard": btns})

        elif data == "adm_add_admin":
            USER_STATES[user_id] = {"state": "ADM_WAIT_ADDADMIN"}
            return await safe_edit(query, f"{E_ADD} <i><b>Add Admin</b>\n\nSend the user's numeric Telegram ID (example: <code>123456789</code>).\n\nOnly add people you trust; admins can access all admin controls.</i>", kb={"inline_keyboard": [[ibtn("Cancel", "adm_manage_admins", style="danger", icon=BTN_EMOJIS["cross"])]]})

        elif data.startswith("adm_deladmin_"):
            try:
                target_admin = int(data.rsplit("_", 1)[1])
            except (TypeError, ValueError):
                return await query.answer("Invalid admin ID.", show_alert=True)
            if target_admin == OWNER_ADMIN_ID:
                return await query.answer("The primary owner admin cannot be removed.", show_alert=True)
            if target_admin not in ADMINS:
                return await query.answer("That user is not an admin.", show_alert=True)
            ADMINS.remove(target_admin)
            await settings_col.update_one({"_id": "config"}, {"$set": {"admins": list(ADMINS)}})
            config = await settings_col.find_one({"_id": "config"})
            current_admins = sorted(set(int(a) for a in ADMINS))
            text = f"{E_CHK} <i><b>Admin Removed</b>\n\nRemoved Telegram ID: <code>{target_admin}</code></i>\n\n{E_ADM} <i><b>Current Admins:</b></i>"
            btns = [[ibtn("➕ Add Admin", "adm_add_admin", style="success", icon=BTN_EMOJIS["add"])]]
            for admin_id in current_admins:
                label = f"👑 {admin_id} (Owner)" if admin_id == OWNER_ADMIN_ID else f"🛡️ {admin_id}"
                row = [ibtn(label, "adm_admin_info", style="primary")]
                if admin_id != OWNER_ADMIN_ID:
                    row.append(ibtn("🗑 Remove", f"adm_deladmin_{admin_id}", style="danger", icon=BTN_EMOJIS["cross"]))
                btns.append(row)
            btns.append([ibtn("Back to Dashboard", "adm_home", style="danger", icon=BTN_EMOJIS["cross"])])
            return await safe_edit(query, text, kb={"inline_keyboard": btns})

        elif data == "adm_admin_info":
            return await query.answer("Admin ID shown here. Use Remove to revoke admin access.", show_alert=True)

        elif data == "adm_stats":
            t_u = await users_col.count_documents({})
            g_d = config.get("global_dms", 0)
            text = f"""{E_STAT} <i><b>Platform Statistics Overview</b>\n\n{E_PROF} <b>Total Users in Database:</b> <code>{t_u}</code>\n{E_START} <b>Global Lifetime DMs:</b> <code>{g_d}</code>\n{E_ACT} <b>Concurrent Live Campaigns:</b> <code>{len(ACTIVE_TASKS)}</code></i>"""
            btn = {"inline_keyboard": [[ibtn("Back to Dashboard", "adm_home", style="danger", icon=BTN_EMOJIS["cross"])]]}
            return await safe_edit(query, text, kb=btn)

        elif data == "adm_sales":
            history = config.get("sales_history", {})
            t_str = get_ist_str("%Y-%m-%d"); y_str = time.strftime("%Y-%m-%d", time.gmtime(time.time() - 86400 + 19800))
            l_30 = sum(history.get(time.strftime("%Y-%m-%d", time.gmtime(time.time() - (i * 86400) + 19800)), 0) for i in range(30))
            text = f"""{E_MONEY} <i><b>Sales & Revenue Insights</b>\n\n{E_CAL} <b>Today's Revenue:</b> ₹{history.get(t_str, 0)}\n{E_WAIT} <b>Yesterday's Revenue:</b> ₹{history.get(y_str, 0)}\n{E_CAL} <b>Last 30 Days:</b> ₹{l_30}\n━━━━━━━━━━━━━━━━━━━━\n{E_CROWN} <b>Total Gross Sales:</b> ₹{config.get('total_sales_inr', 0)}</i>"""
            btn = {"inline_keyboard": [[ibtn("Back to Dashboard", "adm_home", style="danger", icon=BTN_EMOJIS["cross"])]]}
            return await safe_edit(query, text, kb=btn)

        elif data == "adm_ongoing":
            if not ACTIVE_TASKS:
                text = f"{E_CHK} <i><b>No active tasks are running at this time.</b></i>"
            else:
                text = f"{E_SYNC} <i><b>Active Marketing Processes:</b>\n\n"
                for uid, t in ACTIVE_TASKS.items():
                    text += f"{E_PROF} <b>User:</b> <code>{uid}</code>\n{E_TRI} <b>Target:</b> {t['target']}\n{E_STAT} <b>Progress:</b> {t['sent']} / {t['limit']}\nStatus: {t.get('status','running')}\n\n"
                text += "</i>"
            btn = {"inline_keyboard": [
                [ibtn("Refresh View", "adm_ongoing", style="success", icon=BTN_EMOJIS["refresh"])],
                [ibtn("Back to Dashboard", "adm_home", style="danger", icon=BTN_EMOJIS["cross"])]
            ]}
            return await safe_edit(query, text, kb=btn)

        elif data == "adm_toggle_auto":
            current = config.get("auto_payment_status", False)
            await settings_col.update_one({"_id": "config"}, {"$set": {"auto_payment_status": not current}})
            config["auto_payment_status"] = not current
            text, kb = await get_admin_dashboard(config)
            return await safe_edit(query, text, kb=kb)

        elif data == "adm_toggle_maint":
            current = config.get("maintenance", False)
            await settings_col.update_one({"_id": "config"}, {"$set": {"maintenance": not current}})
            config["maintenance"] = not current
            text, kb = await get_admin_dashboard(config)
            return await safe_edit(query, text, kb=kb)

        elif data == "adm_mystery":
            days = int(config.get("mystery_box_days", 0) or 0)
            round_id = int(config.get("mystery_box_round", 0) or 0)
            claimed = len(config.get("mystery_box_claimed", []) or [])
            announcement_set = bool(config.get("mystery_box_announcement_chat") and config.get("mystery_box_announcement_message"))
            text = f"🎁 <b>Mystery Box Settings</b>\n\nCurrent reward: <b>{days} premium day(s)</b>\nCampaign: <code>{round_id}</code>\nClaims this round: <b>{claimed}</b>\nAnnouncement message: <b>{'Set' if announcement_set else 'Default message'}</b>\n\nSet a custom announcement (text/photo/video/document/etc.), then enter premium days to publish a new campaign. Send 0 to close it. Each publish creates a fresh claim round."
            return await safe_edit(query, text, kb={"inline_keyboard": [
                [ibtn("📝 Set Announcement Message", "adm_mystery_setmsg", style="success")],
                [ibtn("🎁 Set Premium Days / Publish", "adm_mystery_setdays", style="primary")],
                [ibtn("Cancel", "adm_home", style="danger")]
            ]})

        elif data == "adm_mystery_setmsg":
            USER_STATES[user_id] = {"state": "ADM_WAIT_MYSTERY_ANNOUNCEMENT"}
            return await safe_edit(query, "📝 <b>Set Mystery Box Announcement</b>\n\nAb koi bhi message bhejein: text, photo + caption, video, document, animation, audio, sticker, etc. Ye message publish karte waqt sabhi registered users ko copy hoga.", kb={"inline_keyboard": [[ibtn("Cancel", "adm_mystery", style="danger")]]})

        elif data == "adm_mystery_setdays":
            USER_STATES[user_id] = {"state": "ADM_WAIT_MYSTERY_DAYS"}
            return await safe_edit(query, "🎁 <b>Set Mystery Box Reward</b>\n\nPremium days bhejein (0 se 3650). 0 box close karega.", kb={"inline_keyboard": [[ibtn("Cancel", "adm_mystery", style="danger")]]})

        elif data == "adm_game_controls":
            game_on = bool(config.get("game_enabled", True))
            fraud_on = bool(config.get("anti_fraud_enabled", True))
            text = f"🎮 <b>Game & Anti-Fraud Controls</b>\n\nGame: <b>{'ON' if game_on else 'OFF'}</b>\nAnti-fraud referral checks: <b>{'ON' if fraud_on else 'OFF'}</b>"
            return await safe_edit(query, text, kb={"inline_keyboard": [
                [ibtn("Toggle Game", "adm_toggle_game", style="primary"), ibtn("Toggle Anti-Fraud", "adm_toggle_fraud", style="success")],
                [ibtn("Back", "adm_home", style="danger")]]})

        elif data == "adm_toggle_game":
            await settings_col.update_one({"_id": "config"}, {"$set": {"game_enabled": not bool(config.get("game_enabled", True))}})
            config = await settings_col.find_one({"_id": "config"})
            return await safe_edit(query, f"Game: {'ON' if config.get('game_enabled', True) else 'OFF'}", kb={"inline_keyboard": [[ibtn("Game & Anti-Fraud", "adm_game_controls", style="primary")], [ibtn("Dashboard", "adm_home", style="primary")]]})

        elif data == "adm_toggle_fraud":
            await settings_col.update_one({"_id": "config"}, {"$set": {"anti_fraud_enabled": not bool(config.get("anti_fraud_enabled", True))}})
            config = await settings_col.find_one({"_id": "config"})
            return await safe_edit(query, f"Anti-fraud: {'ON' if config.get('anti_fraud_enabled', True) else 'OFF'}", kb={"inline_keyboard": [[ibtn("Game & Anti-Fraud", "adm_game_controls", style="primary")], [ibtn("Dashboard", "adm_home", style="primary")]]})

        elif data == "adm_code_history":
            codes = config.get("redeem_codes", {}) or {}
            if not codes:
                return await safe_edit(query, f"{E_STAT} <b>Redeem Code History</b>\n\nNo codes have been created yet.", kb={"inline_keyboard": [[ibtn("Create Code", "adm_gen_code", style="success")], [ibtn("Back to Dashboard", "adm_home", style="primary")]]})
            items = sorted(codes.items(), key=lambda item: item[1].get("created_at", 0), reverse=True)
            lines = [f"{E_STAT} <b>Redeem Code History</b>\n<i>Showing latest {min(15, len(items))} of {len(items)} code(s).</i>\n"]
            rows = []
            for code, info in items[:15]:
                limit = int(info.get("claim_limit", 1 if info.get("used") else 1))
                claim_count = len(info.get("used_by", [])) if isinstance(info.get("used_by"), list) else (1 if info.get("used") else int(info.get("claims", 0)))
                lines.append(f"\n<b>Code:</b> <code>{html.escape(code)}</code>\n<b>Duration:</b> {info.get('days', 1)} day(s) | <b>Claims:</b> {claim_count}/{limit}\n<b>Status:</b> {'Available' if claim_count < limit else 'Fully Claimed'}")
                rows.append([ibtn(f"Delete {code}", f"adm_del_code_{code}", style="danger", icon=BTN_EMOJIS["cross"])])
            rows.append([ibtn("Back to Dashboard", "adm_home", style="primary", icon=BTN_EMOJIS["home"])])
            return await safe_edit(query, "\n".join(lines), kb={"inline_keyboard": rows})

        elif data.startswith("adm_del_code_"):
            code_to_delete = data[len("adm_del_code_"):]
            codes = config.get("redeem_codes", {}) or {}
            if code_to_delete not in codes:
                return await query.answer("Code not found.", show_alert=True)
            codes.pop(code_to_delete, None)
            await settings_col.update_one({"_id": "config"}, {"$set": {"redeem_codes": codes}})
            config["redeem_codes"] = codes
            await query.answer("Redeem code deleted.", show_alert=True)
            # Refresh history after deletion
            if not codes:
                return await safe_edit(query, f"{E_STAT} <b>Redeem Code History</b>\n\nAll codes deleted.", kb={"inline_keyboard": [[ibtn("Back to Dashboard", "adm_home", style="primary")]]})
            items = sorted(codes.items(), key=lambda item: item[1].get("created_at", 0), reverse=True)
            lines = [f"{E_STAT} <b>Redeem Code History</b>\n<i>Total: {len(items)} code(s).</i>\n"]
            rows = []
            for code, info in items[:15]:
                limit = int(info.get("claim_limit", 1))
                claim_count = len(info.get("used_by", [])) if isinstance(info.get("used_by"), list) else (1 if info.get("used") else int(info.get("claims", 0)))
                lines.append(f"\n<b>Code:</b> <code>{html.escape(code)}</code>\n<b>Duration:</b> {info.get('days', 1)} day(s) | <b>Claims:</b> {claim_count}/{limit}")
                rows.append([ibtn(f"Delete {code}", f"adm_del_code_{code}", style="danger", icon=BTN_EMOJIS["cross"])])
            rows.append([ibtn("Back to Dashboard", "adm_home", style="primary", icon=BTN_EMOJIS["home"])])
            return await safe_edit(query, "\n".join(lines), kb={"inline_keyboard": rows})

        elif data == "adm_gen_code":
            USER_STATES[user_id] = {"state": "ADM_WAIT_GENCODE"}
            text = f"{E_GIFT} <i><b>Generate Redeem Code</b>\n\nEnter the duration in days (e.g. <code>7</code> or <code>30</code>):</i>"
            btn = {"inline_keyboard": [[ibtn("Cancel", "adm_home", style="danger", icon=BTN_EMOJIS["cross"])]]}
            return await safe_edit(query, text, kb=btn)

        elif data == "adm_cat_pay":
            text = f"""{E_MONEY} <i><b>Payment Gateway & QR Management</b>\n\n{E_DOT} <b>Instant Auto Approval:</b> {'ENABLED' if config.get('auto_payment_status') else 'DISABLED'}\n{E_MONEY} <b>Smart FamPay UPI:</b> <code>{config.get('upi_fampay', 'Not Set')}</code>\n{E_MONEY} <b>Manual UPI VPA:</b> <code>{config.get('upi_manual', 'Not Set')}</code>\n{E_DIA} <b>USDT (TRC-20):</b> <code>{config.get('crypto', 'Not Set')}</code>\n\nSelect a configuration parameter to modify:</i>"""
            btn = {"inline_keyboard": [
                [ibtn("Set FamPay UPI", "adm_ask_fampay", style="primary", icon=BTN_EMOJIS["money"]), ibtn("Set Manual UPI", "adm_ask_manual", style="primary", icon=BTN_EMOJIS["money"])],
                [ibtn("Set Crypto Address", "adm_ask_crypto", style="primary", icon=BTN_EMOJIS["diamond"])],
                [ibtn("Upload FamPay QR", "adm_ask_fampayqr", style="primary", icon=BTN_EMOJIS["setting"]), ibtn("Upload Manual QR", "adm_ask_manualqr", style="primary", icon=BTN_EMOJIS["setting"])],
                [ibtn("Upload Crypto QR", "adm_ask_cryptoqr", style="primary", icon=BTN_EMOJIS["setting"])],
                [ibtn("Back to Dashboard", "adm_home", style="danger", icon=BTN_EMOJIS["cross"])]
            ]}
            return await safe_edit(query, text, kb=btn)

        elif data == "adm_cat_price":
            text = f"""{E_DIA} <i><b>Subscription Pricing Architecture</b>\n\n<b>1 Day Access:</b> ₹{config.get('price_1d_inr')} | ${config.get('price_1d_usd')}\n<b>3 Days Access:</b> ₹{config.get('price_3d_inr')} | ${config.get('price_3d_usd')}\n<b>7 Days Access:</b> ₹{config.get('price_7d_inr')} | ${config.get('price_7d_usd')}\n<b>1 Month Access:</b> ₹{config.get('price_1m_inr')} | ${config.get('price_1m_usd')}\n\nSelect a plan to edit its pricing:</i>"""
            btn = {"inline_keyboard": [
                [ibtn("Edit 1 Day Plan", "adm_ask_p_1d", style="primary", icon=BTN_EMOJIS["diamond"]), ibtn("Edit 3 Days Plan", "adm_ask_p_3d", style="primary", icon=BTN_EMOJIS["diamond"])],
                [ibtn("Edit 7 Days Plan", "adm_ask_p_7d", style="success", icon=BTN_EMOJIS["diamond"]), ibtn("Edit 1 Month Plan", "adm_ask_p_1m", style="success", icon=BTN_EMOJIS["crown"])],
                [ibtn("Back to Dashboard", "adm_home", style="danger", icon=BTN_EMOJIS["cross"])]
            ]}
            return await safe_edit(query, text, kb=btn)

        elif data == "adm_cat_channels":
            fsubs = config.get("fsub_channels", [])
            fsub_text = ""
            if not fsubs:
                fsub_text = "<i>No subscription channels added yet.</i>\n"
            else:
                for idx, c in enumerate(fsubs):
                    fsub_text += f"<i><b>{idx+1}.</b> {html.escape(c.get('title','Channel'))} (<code>{c.get('id')}</code>)</i>\n"

            text = f"""{E_GLOBE} <i><b>Subscription Channels & Routing Setup</b>\n\n<b>Active Force-Sub Channels ({len(fsubs)}):</b>\n{fsub_text}\n<b>System Routes:</b>\n• <b>Mandatory Request ID:</b> <code>{config.get('reqall_id')}</code>\n• <b>Free Target Channel:</b> <code>{config.get('free_channel_id')}</code>\n• <b>Order Log Channel:</b> <code>{config.get('log_channel')}</code>\n• <b>Success Log Channel:</b> <code>{config.get('success_log_channel')}</code>\n• <b>Daily Leaderboard:</b> <code>{config.get('leaderboard_channel')}</code>\n\nSelect an action below:</i>"""
            
            btn = {"inline_keyboard": [
                [ibtn("➕ Add New Channel", "adm_add_channel", style="success", icon=BTN_EMOJIS["add"]), ibtn("🗑️ Remove Channels", "adm_manage_channels", style="danger", icon=BTN_EMOJIS["cross"])],
                [ibtn("Mandatory Request", "adm_ask_reqall", style="primary", icon=BTN_EMOJIS["shield"]), ibtn("Free Target Channel", "adm_ask_freech", style="primary", icon=BTN_EMOJIS["gift"])],
                [ibtn("Order Log Channel", "adm_ask_logch", style="primary", icon=BTN_EMOJIS["stats"]), ibtn("Success Log Channel", "adm_ask_succlog", style="primary", icon=BTN_EMOJIS["tick"])],
                [ibtn("Daily Leaderboard", "adm_ask_ldbch", style="primary", icon=BTN_EMOJIS["crown"])],
                [ibtn("Back to Dashboard", "adm_home", style="danger", icon=BTN_EMOJIS["cross"])]
            ]}
            return await safe_edit(query, text, kb=btn)

        elif data == "adm_add_channel":
            USER_STATES[user_id] = {"state": "ADM_WAIT_ADD_CHANNEL"}
            text = f"""{E_ADD} <i><b>Add Subscription Channel</b>\n\nYou can add a channel by doing ANY of the following:\n\n1️⃣ <b>Forward any message</b> directly from your target channel here.\n2️⃣ Send the <b>Channel ID</b> (e.g., <code>-1001234567890</code>).\n3️⃣ Send the <b>Channel Username or Public Link</b> (e.g., <code>@mychannel</code> or <code>https://t.me/mychannel</code>).\n\n⚠️ <b>Note:</b> Ensure this bot is promoted to <b>Admin</b> in the channel to verify subscribers and generate links.</i>"""
            btn = {"inline_keyboard": [[ibtn("Cancel", "adm_cat_channels", style="danger", icon=BTN_EMOJIS["cross"])]]}
            return await safe_edit(query, text, kb=btn)

        elif data == "adm_manage_channels":
            fsubs = config.get("fsub_channels", [])
            if not fsubs:
                return await query.answer("No channels available to remove!", show_alert=True)
            
            btn_rows = []
            for idx, ch in enumerate(fsubs):
                title = ch.get("title", f"Channel {idx+1}")[:20]
                btn_rows.append([ibtn(f"Remove: {title}", f"adm_delch_{idx}", style="danger", icon=BTN_EMOJIS["cross"])])
            btn_rows.append([ibtn("Back", "adm_cat_channels", style="primary", icon=BTN_EMOJIS["cross"])])
            
            text = f"{E_GLOBE} <i><b>Manage Channels:</b>\nClick on any channel below to remove it from verification:</i>"
            return await safe_edit(query, text, kb={"inline_keyboard": btn_rows})

        elif data.startswith("adm_delch_"):
            idx = int(data.split("_")[2])
            fsubs = config.get("fsub_channels", [])
            if 0 <= idx < len(fsubs):
                removed = fsubs.pop(idx)
                await settings_col.update_one({"_id": "config"}, {"$set": {"fsub_channels": fsubs}})
                await query.answer(f"Channel '{removed.get('title')}' removed.", show_alert=True)
            config = await settings_col.find_one({"_id": "config"})
            text, kb = await get_admin_dashboard(config)
            return await safe_edit(query, text, kb=kb)

        elif data == "adm_cat_limits":
            text = f"""{E_ADM} <i><b>Operational Parameters & Throttling</b>\n\n{E_GIFT} <b>Free Trial DM Allowance:</b> <code>{config.get('free_trial_limit')}</code>\n{E_WAIT} <b>Message Sending Delay:</b> <code>{config.get('msg_delay')}s</code>\n{E_MED} <b>Leaderboard Scheduled Hour:</b> <code>{config.get('ldb_time')}:00 IST</code>\n{E_MONEY} <b>Referral Bonus Reward:</b> <code>{config.get('ref_bonus')} DMs</code>\n{E_DIA} <b>Referral Premium Reward:</b> <code>{config.get('ref_premium_days', 0)} days</code>\n{E_PROF} <b>Free Target Member Cap:</b> <code>{config.get('free_req_limit')}</code>\n\nSelect a parameter to modify:</i>"""
            btn = {"inline_keyboard": [
                [ibtn("Set Free Trial Allowance", "adm_ask_freetrial", style="success", icon=BTN_EMOJIS["gift"]), ibtn("Set Sending Delay", "adm_ask_delay", style="primary", icon=BTN_EMOJIS["wait"])],
                [ibtn("Set Leaderboard Schedule", "adm_ask_ldbtime", style="primary", icon=BTN_EMOJIS["cal"]), ibtn("Set Referral Bonus", "adm_ask_refbonus", style="success", icon=BTN_EMOJIS["add"])],
                [ibtn("Set Referral Premium Days", "adm_ask_refpremium", style="success", icon=BTN_EMOJIS["diamond"])],
                [ibtn("Back to Dashboard", "adm_home", style="danger", icon=BTN_EMOJIS["cross"])]
            ]}
            return await safe_edit(query, text, kb=btn)

        elif data == "adm_cat_users":
            text = f"""{E_PROF} <i><b>User Management & Authorization</b>\n\nInspect user records, grant or revoke VIP access, clear stored sessions, or issue suspensions directly.</i>"""
            btn = {"inline_keyboard": [
                [ibtn("Inspect User Record", "adm_ask_checkuser", style="primary", icon=BTN_EMOJIS["user"]), ibtn("Wipe User Sessions", "adm_ask_clearsess", style="danger", icon=BTN_EMOJIS["cross"])],
                [ibtn("Grant VIP Access", "adm_ask_giveprem", style="success", icon=BTN_EMOJIS["crown"]), ibtn("Revoke VIP Access", "adm_ask_remprem", style="danger", icon=BTN_EMOJIS["ban"])],
                [ibtn("Suspend User", "adm_ask_banuser", style="danger", icon=BTN_EMOJIS["ban"]), ibtn("Reactivate User", "adm_ask_unbanuser", style="success", icon=BTN_EMOJIS["tick"])],
                [ibtn("Back to Dashboard", "adm_home", style="danger", icon=BTN_EMOJIS["cross"])]
            ]}
            return await safe_edit(query, text, kb=btn)

        elif data == "adm_broadcast":
            USER_STATES[user_id] = {"state": "ADM_WAITING_BROADCAST"}
            return await safe_edit(query, f"{E_GLOBE} <i><b>Create Broadcast Announcement:</b>\n\nPlease send or forward any message (Text, Media, Caption, etc.) you wish to broadcast to all registered bot users.</i>", kb={"inline_keyboard": [[ibtn("Cancel", "adm_cancel", style="danger", icon=BTN_EMOJIS["cross"])]]})

        elif data.startswith("adm_ask_"):
            action = data.replace("adm_ask_", "")
            USER_STATES[user_id] = {"state": f"ADM_WAIT_{action.upper()}"}
            prompts = {
                "fampay": f"{E_TRI} <i>Please provide the new <b>Smart FamPay UPI ID</b> (e.g. <code>user@fam</code>):</i>",
                "manual": f"{E_TRI} <i>Please provide the new <b>Manual UPI ID</b> (e.g. <code>name@upi</code>):</i>",
                "crypto": f"{E_TRI} <i>Please provide the new <b>USDT (TRC-20) Crypto Address</b>:</i>",
                "fampayqr": f"{E_TRI} <i><b>Send a photo</b> of the FamPay QR Code (or send <code>none</code> to remove):</i>",
                "manualqr": f"{E_TRI} <i><b>Send a photo</b> of the Manual UPI QR Code (or send <code>none</code> to remove):</i>",
                "cryptoqr": f"{E_TRI} <i><b>Send a photo</b> of the Crypto QR Code (or send <code>none</code> to remove):</i>",
                "p_1d": f"{E_TRI} <i>Provide <b>1 Day Plan Price</b> in format: <code>INR USD</code> (e.g. <code>25 0.5</code>):</i>",
                "p_3d": f"{E_TRI} <i>Provide <b>3 Days Plan Price</b> in format: <code>INR USD</code> (e.g. <code>60 1.5</code>):</i>",
                "p_7d": f"{E_TRI} <i>Provide <b>7 Days Plan Price</b> in format: <code>INR USD</code> (e.g. <code>120 3</code>):</i>",
                "p_1m": f"{E_TRI} <i>Provide <b>1 Month Plan Price</b> in format: <code>INR USD</code> (e.g. <code>350 8</code>):</i>",
                "reqall": f"{E_TRI} <i>Provide Mandatory Request channel in format: <code>Chat_ID Invite_Link</code> (or <code>none</code>):</i>",
                "freech": f"{E_TRI} <i>Provide Free Target channel in format: <code>Chat_ID Invite_Link</code>:</i>",
                "logch": f"{E_TRI} <i>Provide Order Log Channel ID (e.g. <code>-100...</code>):</i>",
                "succlog": f"{E_TRI} <i>Provide Success Log Channel ID (e.g. <code>-100...</code>):</i>",
                "ldbch": f"{E_TRI} <i>Provide Daily Leaderboard Channel ID (e.g. <code>-100...</code>):</i>",
                "freetrial": f"{E_TRI} <i>Enter new Free Trial DM limit (e.g. <code>100</code>):</i>",
                "delay": f"{E_TRI} <i>Enter message delay interval in seconds (e.g. <code>0</code> or <code>1</code>):</i>",
                "ldbtime": f"{E_TRI} <i>Enter Leaderboard Posting Hour (0-23 in IST):</i>",
                "refbonus": f"{E_TRI} <i>Enter bonus DMs awarded per referral (e.g. <code>50</code>):</i>",
                "refpremium": f"{E_TRI} <i>Enter Premium days awarded to the referrer per successful referral (0 to disable, max 3650):</i>",
                "checkuser": f"{E_TRI} <i>Enter the Telegram User ID to inspect:</i>",
                "clearsess": f"{E_TRI} <i>Enter the Telegram User ID whose sessions you wish to wipe:</i>",
                "giveprem": f"{E_TRI} <i>Enter User ID and duration in format: <code>User_ID Days</code> (e.g. <code>12345678 30</code>):</i>",
                "remprem": f"{E_TRI} <i>Enter the User ID to revoke VIP access:</i>",
                "banuser": f"{E_TRI} <i>Enter the User ID to suspend:</i>",
                "unbanuser": f"{E_TRI} <i>Enter the User ID to reactivate:</i>"
            }
            prompt_text = prompts.get(action, f"{E_TRI} <i>Please provide the updated parameter:</i>")
            btn = {"inline_keyboard": [[ibtn("Cancel", "adm_cancel", style="danger", icon=BTN_EMOJIS["cross"])]]}
            return await safe_edit(query, prompt_text, kb=btn)

        elif data == "adm_cancel":
            USER_STATES.pop(user_id, None)
            text, kb = await get_admin_dashboard(config)
            return await safe_edit(query, text, kb=kb)

    # ================= USER CALLBACK ROUTES =================
    if data == "referral":
        u = await get_user(user_id)
        me = await bot.get_me()
        link = f"https://t.me/{me.username}?start=ref_{user_id}"
        referral_days = max(0, int(config.get("ref_premium_days", 0) or 0))
        referral_text = (
            f"👥 <b>Referral Program</b>\n\n"
            f"Your referral link: <a href=\"{html.escape(link, quote=True)}\">{html.escape(link)}</a>\n\n"
            f"Premium reward per successful referral: <b>{referral_days} day(s)</b>\n"
            f"Successful referrals: <b>{u.get('referrals', 0)}</b>\n"
            f"Referral DM bonus: <b>{u.get('referral_bonus_dms', 0)}</b>"
        )
        # Normalize accidentally stored/escaped newline sequences before sending.
        referral_text = referral_text.replace("\\n", "\n")
        return await safe_edit(query, referral_text, kb={"inline_keyboard": [[ibtn("Back to Menu", "back_home", style="primary")]]})

    if data == "mystery_box":
        days = int(config.get("mystery_box_days", 0) or 0)
        claimed = config.get("mystery_box_claimed", []) or []
        u = await get_user(user_id)
        if days <= 0:
            return await query.answer("Mystery Box is not active right now.", show_alert=True)
        if user_id in claimed:
            return await query.answer("You already claimed this Mystery Box round.", show_alert=True)
        claimed.append(user_id)
        await settings_col.update_one({"_id": "config"}, {"$set": {"mystery_box_claimed": claimed}})
        expiry = await grant_premium(user_id, days, "Mystery Box")
        return await safe_edit(query, f"🎉 <b>Mystery Box Claimed!</b>\n\nYou received <b>{days} day(s)</b> Premium.\nExpiry: <b>{get_ist_ts_str(expiry)}</b>", kb={"inline_keyboard": [[ibtn("Back to Menu", "back_home", style="primary")]]})

    if data == "premium_history":
        u = await get_user(user_id)
        history = list(u.get("premium_history", []))[-10:][::-1]
        if not history:
            body = "No premium activity recorded yet."
        else:
            body = "\n".join(f"• {int(x.get('days', 0))} day(s) — {html.escape(str(x.get('source', 'Premium')))} — {get_ist_ts_str(x.get('at', time.time()))}" for x in history)
        return await safe_edit(query, f"📜 <b>Premium History</b>\n\n{body}", kb={"inline_keyboard": [[ibtn("Back to Menu", "back_home", style="primary")]]})

    if data == "check_join":
        joined, not_joined_list = await check_force_join(user_id)
        if not joined:
            text = f"{E_WRN} <i><b>Subscription Verification Required!</b>\n\nTo ensure quality service, please join our official channels before continuing.</i>"
            btn_list = []; row = []
            for i, (idx, link) in enumerate(not_joined_list):
                fixed_link = link if str(link).startswith("http") else f"https://t.me/{str(link).replace('@','')}"
                row.append(ibtn(f"{idx}", url=fixed_link, style="primary", icon=BTN_EMOJIS["target"]))
                if len(row) == 2: btn_list.append(row); row = []
            if row: btn_list.append(row)
            btn_list.append([ibtn("I Have Joined", "check_join", style="success", icon=BTN_EMOJIS["tick"])])
            
            try: await api_edit(user_id, query.message.id, text, {"inline_keyboard": btn_list})
            except: pass
            
            return await query.answer("You have not joined all channels yet! Please verify.", show_alert=True)
            
        first_name = html.escape(query.from_user.first_name if query.from_user else "User")
        text, btn = await get_home_menu(user_id, first_name, config)
        await query.message.delete()
        await api_send(user_id, text, kb=btn)

    elif data == "play_win":
        if not config.get("game_enabled", True):
            return await query.answer("Game is temporarily disabled by admin.", show_alert=True)
        text = f"""{E_GIFT} <b>PLAY &amp; WIN</b>

━━━━━━━━━━━━━━━━━━━━
🎡 <b>Spin the Wheel</b>
<i>1–10 Days: Normal | 10–49 Days: Rare | 50 Days: Extra Rare</i>

🎲 <b>Dice Challenge</b>
<i>Choose a number from 1 to 6. You get 3 rolls every 24 hours. Match the dice to win random premium days.</i>
━━━━━━━━━━━━━━━━━━━━"""
        btn = {"inline_keyboard": [
            [ibtn("🎡 Spin the Wheel", "spin_wheel", style="success", icon=BTN_EMOJIS["gift"])],
            [ibtn("🎲 Dice Challenge", "dice_start", style="primary", icon=BTN_EMOJIS["target"])],
            [ibtn("Main Menu", "back_home", style="danger", icon=BTN_EMOJIS["home"])]
        ]}
        return await safe_edit(query, text, kb=btn)

    elif data == "dice_start":
        if not config.get("game_enabled", True):
            return await query.answer("Game is temporarily disabled by admin.", show_alert=True)
        u = await get_user(user_id)
        now = time.time()
        roll_times = [float(t) for t in u.get("dice_roll_times", []) if now - float(t) < 86400]
        if len(roll_times) >= 3:
            wait_sec = int(86400 - (now - min(roll_times)))
            h, rem = divmod(max(0, wait_sec), 3600)
            m, sec = divmod(rem, 60)
            return await query.answer(f"Daily dice limit reached. Try again in {h}h {m}m {sec}s.", show_alert=True)

        remaining = 3 - len(roll_times)
        text = f"""{E_PLAY} <b>DICE CHALLENGE</b>

🎯 <b>Choose your lucky number (1–6)</b>
🎲 Rolls remaining in your 24-hour window: <b>{remaining}/3</b>

<i>If the dice matches your number, you win random premium days!</i>"""
        rows = [
            [ibtn("1", "dice_pick_1", style="primary"), ibtn("2", "dice_pick_2", style="primary"), ibtn("3", "dice_pick_3", style="primary")],
            [ibtn("4", "dice_pick_4", style="primary"), ibtn("5", "dice_pick_5", style="primary"), ibtn("6", "dice_pick_6", style="primary")],
            [ibtn("Play & Win", "play_win", style="danger", icon=BTN_EMOJIS["gift"])]
        ]
        return await safe_edit(query, text, kb={"inline_keyboard": rows})

    elif data.startswith("dice_pick_"):
        try:
            chosen = int(data.rsplit("_", 1)[1])
        except (TypeError, ValueError):
            return await query.answer("Invalid number. Please try again.", show_alert=True)
        if chosen < 1 or chosen > 6:
            return await query.answer("Choose a number from 1 to 6.", show_alert=True)

        u = await get_user(user_id)
        now = time.time()
        roll_times = [float(t) for t in u.get("dice_roll_times", []) if now - float(t) < 86400]
        if len(roll_times) >= 3:
            wait_sec = int(86400 - (now - min(roll_times)))
            h, rem = divmod(max(0, wait_sec), 3600)
            m, sec = divmod(rem, 60)
            return await query.answer(f"Daily dice limit reached. Try again in {h}h {m}m {sec}s.", show_alert=True)

        # Reserve this roll before requesting the Telegram dice, preventing double-click reuse.
        roll_times.append(now)
        await users_col.update_one({"_id": user_id}, {"$set": {"dice_roll_times": roll_times}})
        await query.answer("Rolling the dice...")
        try:
            dice_msg = await bot.send_dice(user_id, emoji="🎲")
            dice_result = int(dice_msg.dice.value)
        except Exception as dice_error:
            # Refund the reserved attempt if Telegram's dice request fails.
            roll_times = [t for t in roll_times if t != now]
            await users_col.update_one({"_id": user_id}, {"$set": {"dice_roll_times": roll_times}})
            return await safe_edit(query, f"{E_CROSS} <b>Dice could not start.</b> Please try again.\n\n<code>{html.escape(str(dice_error))[:180]}</code>",
                                   kb={"inline_keyboard": [[ibtn("Try Again", "dice_start", style="success"), ibtn("Play & Win", "play_win", style="primary")]]})

        if dice_result == chosen:
            win_days = random.randint(1, 10)
            cur_exp = max(now, u.get("premium_expiry", 0))
            new_exp = cur_exp + (win_days * 86400)
            await users_col.update_one({"_id": user_id}, {"$set": {"premium_expiry": new_exp}})
            result_text = f"""{E_GIFT} <b>YOU WON!</b> {E_CROWN}

━━━━━━━━━━━━━━━━━━━━
🎯 Your choice: <b>{chosen}</b>
🎲 Dice result: <b>{dice_result}</b>

🎉 <b>{win_days} Days Premium</b> added to your account!
━━━━━━━━━━━━━━━━━━━━"""
        else:
            result_text = f"""{E_WAIT} <b>BETTER LUCK NEXT TIME!</b>

🎯 Your choice: <b>{chosen}</b>
🎲 Dice result: <b>{dice_result}</b>

<i>The dice did not match your number. No premium was awarded.</i>"""

        updated = await get_user(user_id)
        recent_rolls = [float(t) for t in updated.get("dice_roll_times", []) if time.time() - float(t) < 86400]
        remaining = max(0, 3 - len(recent_rolls))
        result_text += f"\n\n🎲 <i>Rolls remaining: <b>{remaining}/3</b> in 24 hours.</i>"
        btn = {"inline_keyboard": [
            [ibtn("🎲 Roll Again", "dice_start", style="success", icon=BTN_EMOJIS["gift"])],
            [ibtn("🎮 Play & Win", "play_win", style="primary"), ibtn("Main Menu", "back_home", style="danger", icon=BTN_EMOJIS["home"])]
        ]}
        return await api_send(user_id, result_text, kb=btn)

    elif data == "spin_wheel":
        if not config.get("game_enabled", True):
            return await query.answer("Game is temporarily disabled by admin.", show_alert=True)
        u = await get_user(user_id)
        last_spin = u.get("last_spin", 0)
        now = time.time()
        if now - last_spin < 86400:
            rem_sec = int(86400 - (now - last_spin))
            h, rem = divmod(rem_sec, 3600); m, s = divmod(rem, 60)
            return await query.answer(f"Spin cooldown active! Try again in {h}h {m}m {s}s.", show_alert=True)
        
        # ANIMATED SPIN SEQUENCE
        frames = [
            f"{E_PLAY} <b>SPIN THE WHEEL</b>\n\n<code>[  🎰  ]</code>\n\n<i>Initializing wheel...</i>",
            f"{E_SYNC} <b>SPIN THE WHEEL</b>\n\n<code>[ 🌀🌀 ]</code>\n\n<i>Spinning rapidly...</i>",
            f"{E_SYNC} <b>SPIN THE WHEEL</b>\n\n<code>[ 🎲🎰 ]</code>\n\n<i>Gathering luck...</i>",
            f"{E_SYNC} <b>SPIN THE WHEEL</b>\n\n<code>[ 🌀🎲 ]</code>\n\n<i>Almost there...</i>",
            f"{E_GIFT} <b>SPIN THE WHEEL</b>\n\n<code>[ ✨🎰 ]</code>\n\n<i>Landing on a prize...</i>",
        ]
        for f in frames:
            try: await safe_edit(query, f)
            except: pass
            await asyncio.sleep(0.7)
            
        rand = random.random()
        if rand < 0.01: win_days = 50                 # 1% Extra Rare
        elif rand < 0.31: win_days = random.randint(10, 49)  # 30% Rare
        elif rand < 0.61: win_days = random.randint(1, 10)   # 30% Normal
        else: win_days = 0                            # 39% No Premium
            
        await users_col.update_one({"_id": user_id}, {"$set": {"last_spin": now}})
        
        if win_days > 0:
            cur_exp = max(now, u.get("premium_expiry", 0))
            new_exp = cur_exp + (win_days * 86400)
            await users_col.update_one({"_id": user_id}, {"$set": {"premium_expiry": new_exp}})
            text = f"""{E_GIFT} <b>CONGRATULATIONS!</b> {E_CROWN}

━━━━━━━━━━━━━━━━━━━━
🎉 <b>You won <code>{win_days} Days</code> VIP Premium Access!</b>

{E_DIA} <i>Your premium status has been extended automatically.</i>
━━━━━━━━━━━━━━━━━━━━"""
        else:
            text = f"""{E_WAIT} <b>SPIN RESULT</b>

━━━━━━━━━━━━━━━━━━━━
😔 <i>Unlucky this time! Better luck tomorrow.</i>

{E_CAL} <i>You can spin again in 24 hours.</i>
━━━━━━━━━━━━━━━━━━━━"""
            
        btn = {"inline_keyboard": [[ibtn("Back to Menu", "back_home", style="primary", icon=BTN_EMOJIS["home"])]]}
        await safe_edit(query, text, kb=btn)

    elif data == "confirm_del_chats":
        text = f"{E_WRN} <i><b>WARNING: Delete All Active Dialogs?</b>\n\nThis action will attempt to leave or delete open personal chats/dialogs across your connected sessions.\n\nAre you sure you want to proceed?</i>"
        btn = {"inline_keyboard": [
            [ibtn("YES, DELETE ALL CHATS", "del_all_chats_exec", style="danger", icon=BTN_EMOJIS["cross"])],
            [ibtn("Cancel", "back_home", style="primary", icon=BTN_EMOJIS["tick"])]
        ]}
        await safe_edit(query, text, kb=btn)

    elif data == "del_all_chats_exec":
        u = await get_user(user_id)
        sessions = u.get("sessions", [])
        if not sessions:
            return await query.answer("No connected sessions to wipe chats from!", show_alert=True)
        
        await safe_edit(query, f"{E_SYNC} <i><b>Deleting all chats across sessions... Please wait.</b></i>")
        deleted_count = 0
        for s in sessions:
            try:
                c = Client(f"del_{user_id}_{int(time.time())}", api_id=API_ID, api_hash=API_HASH, session_string=s, in_memory=True)
                await c.start()
                async for dialog in c.get_dialogs(limit=100):
                    try:
                        if dialog.chat.type in [enums.ChatType.CHANNEL, enums.ChatType.SUPERGROUP]:
                            await c.leave_chat(dialog.chat.id)
                        else:
                            await c.archive_chats(chat_ids=dialog.chat.id)
                        deleted_count += 1
                    except Exception: pass
                await c.stop()
            except Exception: pass
                
        await api_send(user_id, f"{E_CHK} <i><b>Chat Cleanup Completed!</b> Processed {deleted_count} dialogs across connected sessions.</i>", kb={"inline_keyboard": [[ibtn("Back to Menu", "back_home", style="primary", icon=BTN_EMOJIS["home"])]]})

    elif data == "accept_pending":
        USER_STATES[user_id] = {"state": "WAITING_ACCEPT_LINK"}
        text = f"{E_SYNC} <i><b>Accept Pending Join Requests</b>\n\nPlease send your channel username or link (e.g. <code>@MyChannel</code> or <code>https://t.me/MyChannel</code>) where your session account is an Admin with 'Add Users' permission.</i>"
        btn = {"inline_keyboard": [[ibtn("Cancel", "accept_cancel", style="danger", icon=BTN_EMOJIS["cross"])]]}
        await safe_edit(query, text, kb=btn)

    elif data == "redeem_code":
        USER_STATES[user_id] = {"state": "WAITING_REDEEM_CODE"}
        text = f"{E_GIFT} <i><b>Redeem Premium Access Code</b>\n\nPlease enter your VIP Redeem Code below:</i>"
        btn = {"inline_keyboard": [[ibtn("Cancel", "accept_cancel", style="danger", icon=BTN_EMOJIS["cross"])]]}
        await safe_edit(query, text, kb=btn)

    elif data == "scrape_group":
        USER_STATES[user_id] = {"state": "WAITING_SCRAPE_LINK"}
        await safe_edit(query, f"{E_PROF} <i><b>Public Group Scraper Engine</b>\n\nPlease provide the Public Group link or username.\nExample: https://t.me/PublicGroup or @PublicGroup</i>", kb={"inline_keyboard": [[ibtn("Cancel", "accept_cancel", style="danger", icon=BTN_EMOJIS["cross"])]]})

    elif data == "user_dashboard":
        u = await get_user(user_id)
        has_prem = await is_premium(u)
        if has_prem:
            plan_status = f"{E_DIA} Premium Active\n{E_CAL} Expires: {get_ist_ts_str(u.get('premium_expiry', 0))}"
        else:
            plan_status = f"{E_WAIT} Free Tier"
        first_name = html.escape(query.from_user.first_name if query.from_user else "User")
        username = f"@{html.escape(query.from_user.username)}" if query.from_user and query.from_user.username else "Not set"
        text = (f"{E_PROF} <i><b>User Dashboard</b></i>\n\n"
                f"{E_PROF} <b>Name:</b> {first_name}\n"
                f"{E_ID} <b>Telegram ID:</b> <code>{user_id}</code>\n"
                f"{E_PROF} <b>Username:</b> {username}\n"
                f"{E_SHD} <b>Subscription:</b> {plan_status}\n"
                f"{E_ACT} <b>Connected Sessions:</b> {len(u.get('sessions', []))}\n"
                f"{E_STAT} <b>Total DMs Sent:</b> {u.get('total_dms', 0)}\n\n"
                f"Choose an option below:")
        btn = {"inline_keyboard": [
            [ibtn("👤 My Account", "my_account", style="primary", icon=BTN_EMOJIS["user"]), ibtn("📊 My Statistics", "user_stats", style="success", icon=BTN_EMOJIS["setting"])],
            [ibtn("💎 Premium Plans", "buy_premium", style="danger", icon=BTN_EMOJIS["diamond"])],
            [ibtn("🆘 Support", url="https://t.me/OKDRUV", style="primary", icon=BTN_EMOJIS["target"]), ibtn("📜 Rules & Terms", "how_to_use", style="primary", icon=BTN_EMOJIS["setting"])],
            [ibtn("Back to Main Menu", "back_home", style="danger", icon=BTN_EMOJIS["home"])]
        ]}
        await safe_edit(query, text, kb=btn)

    elif data == "user_stats":
        u = await get_user(user_id)
        has_prem = await is_premium(u)
        plan_status = (f"{E_DIA} Premium Active\n{E_CAL} <b>Expiry:</b> {get_ist_ts_str(u.get('premium_expiry', 0))}" if has_prem else f"{E_WAIT} Free Tier")
        text = (f"{E_STAT} <i><b>My Statistics</b></i>\n\n"
                f"{E_ID} <b>Telegram ID:</b> <code>{user_id}</code>\n"
                f"{E_SHD} <b>Plan:</b> {plan_status}\n"
                f"{E_ACT} <b>Connected Sessions:</b> {len(u.get('sessions', []))}\n"
                f"{E_STAT} <b>Messages Sent Today:</b> {u.get('daily_dms', 0)}\n"
                f"{E_STAT} <b>Lifetime Messages Sent:</b> {u.get('total_dms', 0)}\n"
                f"{E_GLOBE} <b>Saved Channels:</b> {len(u.get('saved_channels', []))}")
        await safe_edit(query, text, kb={"inline_keyboard": [
            [ibtn("Refresh Statistics", "user_stats", style="success", icon=BTN_EMOJIS["refresh"])],
            [ibtn("Back to Dashboard", "user_dashboard", style="primary", icon=BTN_EMOJIS["user"])],
            [ibtn("Back to Main Menu", "back_home", style="danger", icon=BTN_EMOJIS["home"])]
        ]})

    elif data == "account_manage":
        u = await get_user(user_id)
        if not u.get("sessions"):
            return await safe_edit(query, "<b>No connected Telegram account found.</b> Please connect an account first.", kb={"inline_keyboard": [[ibtn("Add Session", "add_session", style="success")], [ibtn("Back", "back_home")]]})
        started = await start_account_manager(user_id)
        if not started:
            return await safe_edit(query, "Could not start the connected account monitor. Please check that your session is valid and try again.", kb={"inline_keyboard": [[ibtn("Back", "back_home")]]})
        return await account_manager_screen(query, user_id)

    elif data == "acct_toggle":
        u = await get_user(user_id); cfg = u.get("account_manager", {})
        new_state = not bool(cfg.get("enabled", False))
        await users_col.update_one({"_id": user_id}, {"$set": {"account_manager.enabled": new_state}})
        if new_state:
            started = await start_account_manager(user_id)
            if not started:
                await users_col.update_one({"_id": user_id}, {"$set": {"account_manager.enabled": False}})
                return await safe_edit(query, "Could not start monitoring. Reconnect your Telegram account and try again.", kb={"inline_keyboard": [[ibtn("Back", "back_home")]]})
        return await account_manager_screen(query, user_id)

    elif data == "acct_set_limit":
        USER_STATES[user_id] = {"state": "ACCT_WAIT_LIMIT"}
        return await safe_edit(query, "Send the maximum warning count (0–100). The next message after this limit will block that sender.", kb={"inline_keyboard": [[ibtn("Cancel", "account_manage", style="danger")]]})

    elif data == "acct_set_message":
        USER_STATES[user_id] = {"state": "ACCT_WAIT_MESSAGE"}
        return await safe_edit(query, "Send any message (text/photo/video/document/sticker etc.) to use as the automatic reply. Send /clear to remove it.", kb={"inline_keyboard": [[ibtn("Cancel", "account_manage", style="danger")]]})

    elif data == "acct_reset_warnings":
        await users_col.update_one({"_id": user_id}, {"$set": {"account_manager.warning_counts": {}}})
        return await account_manager_screen(query, user_id)

    elif data == "my_account":
        has_prem = await is_premium(user_id); u = await get_user(user_id)
        if has_prem:
            exp_str = get_ist_ts_str(u['premium_expiry'])
            status = f"{E_DIA} <i>VIP Premium\n{E_CAL} <b>Expires:</b> {exp_str}</i>"
        else: status = f"{E_WAIT} <i>Free Tier</i>"
            
        text = f"{E_PROF} <i><b>User Account Details:</b>\n\n{E_ID} <b>Account ID:</b> <code>{user_id}</code>\n{E_SHD} <b>Plan Status:</b> {status}\n{E_ACT} <b>Active Sessions:</b> {len(u.get('sessions', []))}\n{E_STAT} <b>Total Sent Messages:</b> {u.get('total_dms', 0)}</i>"
        btn = {"inline_keyboard": [[ibtn("Reset DM History", "reset_history", style="danger", icon=BTN_EMOJIS["cross"])], [ibtn("Back to Menu", "back_home", style="primary", icon=BTN_EMOJIS["home"])]]}
        await safe_edit(query, text, kb=btn)

    elif data == "reset_history":
        await users_col.update_one({"_id": user_id}, {"$set": {"messaged_users": {}}})
        await query.answer("Message history cleared!", show_alert=True)

    elif data == "remove_session":
        await users_col.update_one({"_id": user_id}, {"$set": {"sessions": []}})
        await safe_edit(query, f"{E_CHK} <i><b>All active Telegram sessions cleared successfully!</b></i>", kb={"inline_keyboard": [[ibtn("Back to Menu", "back_home", style="primary", icon=BTN_EMOJIS["home"])]]})

    elif data == "buy_premium":
        p1, p3, p7, p30 = (plan_price_label(config, d) for d in (1, 3, 7, 30))
        text = f"{E_PREM} <i><b>VIP Subscription Plans</b>\n\n<b>1 Day Access:</b> {p1}\n<b>3 Days Access:</b> {p3}\n<b>7 Days Access:</b> {p7}\n<b>1 Month Access:</b> {p30}\n\nSelect a plan to proceed:</i>"
        btn = {"inline_keyboard": [[ibtn("1 Day Plan", "plan_1", style="primary", icon=BTN_EMOJIS["diamond"]), ibtn("3 Days Plan", "plan_3", style="primary", icon=BTN_EMOJIS["diamond"])], [ibtn("7 Days Plan", "plan_7", style="success", icon=BTN_EMOJIS["diamond"]), ibtn("1 Month Plan", "plan_30", style="success", icon=BTN_EMOJIS["crown"])], [ibtn("Back to Menu", "back_home", style="danger", icon=BTN_EMOJIS["cross"])]]}
        await safe_edit(query, text, kb=btn)

    elif data.startswith("plan_"):
        days = int(data.split("_")[1])
        suffix = "1m" if days == 30 else f"{days}d"
        try:
            plan_is_free = float(str(config.get(f"price_{suffix}_inr", "0")).replace(",", "").strip() or 0) <= 0
        except (TypeError, ValueError):
            plan_is_free = False
        if plan_is_free:
            u = await get_user(user_id)
            if u.get("free_plan_claimed"):
                return await query.answer("Your one-time free premium plan has already been claimed.", show_alert=True)
            current_expiry = max(time.time(), float(u.get("premium_expiry", 0) or 0))
            new_expiry = current_expiry + days * 86400
            await users_col.update_one({"_id": str(user_id)}, {"$set": {"premium_expiry": new_expiry, "free_plan_claimed": True}})
            await record_premium_event(user_id, days, "Free plan")
            await query.answer("Free plan claimed successfully!", show_alert=True)
            return await safe_edit(query, f"{E_CHK} <b>FREE PLAN CLAIMED!</b>\n\n{E_DIA} Your {days}-day premium plan is now active.\n{E_CAL} <b>Expires:</b> {get_ist_ts_str(new_expiry)}", kb={"inline_keyboard": [[ibtn("Back to Menu", "back_home", style="success", icon=BTN_EMOJIS["home"])], [ibtn("View Plans", "buy_premium", style="primary", icon=BTN_EMOJIS["diamond"])]]})
        btn = {"inline_keyboard": [
            [ibtn("Instant Auto UPI Approval", f"pay_fampay_{days}", style="success", icon=BTN_EMOJIS["tick"])],
            [ibtn("Manual Admin Verification", f"pay_manual_{days}", style="primary", icon=BTN_EMOJIS["money"])],
            [ibtn("Crypto (USDT TRC-20)", f"pay_crypto_{days}", style="primary", icon=BTN_EMOJIS["diamond"])],
            [ibtn("Back to Plans", "buy_premium", style="danger", icon=BTN_EMOJIS["cross"])]
        ]}
        text = f"{E_MONEY} <i><b>Select Payment Method for {days} Days Plan:</b></i>"
        await safe_edit(query, text, kb=btn)

    elif data.startswith("pay_"):
        parts = data.split("_"); mthd = parts[1]; days = int(parts[2])
        price_inr = config.get(f"price_{days}d_inr") if days != 30 else config.get("price_1m_inr")
        price_usd = config.get(f"price_{days}d_usd") if days != 30 else config.get("price_1m_usd")
        
        if mthd == "fampay":
            if not config.get("auto_payment_status", False):
                return await query.answer("Auto-Approval is offline. Please choose Manual Payment.", show_alert=True)
            text = f"{E_MONEY} <i><b>Instant Auto-Approval Payment ({days} Days):</b>\n\n1. Transfer exactly <b>₹{price_inr}</b> to:\n<code>{config.get('upi_fampay', 'Not Set')}</code>\n2. Click 'I Have Paid' and provide the <b>UTR / Transaction ID</b>.\n\nAutomated bank verification will process your access in seconds.</i>"
            btn = {"inline_keyboard": [[ibtn("I Have Paid", f"sub_fampay_{days}_{price_inr}", style="success", icon=BTN_EMOJIS["tick"])], [ibtn("Back", f"plan_{days}", style="danger", icon=BTN_EMOJIS["cross"])]]}
            qr_photo = config.get("qr_fampay")
        elif mthd == "crypto":
            text = f"{E_DIA} <i><b>Crypto Payment ({days} Days):</b>\n\nTransfer exactly <b>${price_usd}</b> (USDT.TRC20) to:\n<code>{config.get('crypto', 'Not Set')}</code>\n\nSubmit your Transaction Hash for verification.</i>"
            btn = {"inline_keyboard": [[ibtn("I Have Paid", f"sub_man_{days}_{price_usd}", style="success", icon=BTN_EMOJIS["tick"])], [ibtn("Back", f"plan_{days}", style="danger", icon=BTN_EMOJIS["cross"])]]}
            qr_photo = config.get("qr_crypto")
        else: 
            text = f"{E_MONEY} <i><b>Manual UPI Transfer ({days} Days):</b>\n\n1. Transfer exactly <b>₹{price_inr}</b> to:\n<code>{config.get('upi_manual', 'Not Set')}</code>\n\n2. Click 'I Have Paid' and send the UTR & payment screenshot.</i>"
            btn = {"inline_keyboard": [[ibtn("I Have Paid", f"sub_man_{days}_{price_inr}", style="success", icon=BTN_EMOJIS["tick"])], [ibtn("Back", f"plan_{days}", style="danger", icon=BTN_EMOJIS["cross"])]]}
            qr_photo = config.get("qr_manual")

        await query.message.delete()
        if qr_photo and str(qr_photo).lower() not in ["not_set", "none", "null"] and len(str(qr_photo)) > 5:
            await api_send(user_id, text, kb=btn, photo=qr_photo)
        else: 
            await api_send(user_id, text, kb=btn)

    elif data.startswith("sub_fampay_"):
        parts = data.split("_")
        days = int(parts[2]); price = parts[3]
        USER_STATES[user_id] = {"state": "WAITING_FAMPAY_UTR", "days": days, "price": price}
        await query.message.delete()
        await api_send(user_id, f"{E_STAT} <i><b>Smart Payment Verification</b>\n\nPlease submit the <b>UTR Number</b> or <b>Transaction ID</b> below:\nExample: 312345678901</i>")

    elif data.startswith("sub_man_"):
        parts = data.split("_")
        days = int(parts[2]); price = parts[3]
        USER_STATES[user_id] = {"state": "WAITING_MANUAL_UTR", "days": days, "price": price}
        await query.message.delete()
        await api_send(user_id, f"{E_STAT} <i><b>Manual Verification (Step 1/2)</b>\n\nPlease send your <b>UTR Number / Transaction Hash</b> first:</i>")

    elif data == "add_session":
        USER_STATES[user_id] = {"state": "WAITING_PHONE"}
        text = f"{E_WAIT} <i><b>Session Account Generator</b>\nPlease enter your phone number with country code:\nExample: <code>+1234567890</code></i>"
        await safe_edit(query, text, kb={"inline_keyboard": [[ibtn("Cancel", "accept_cancel", style="danger", icon=BTN_EMOJIS["cross"])]]})

    elif data == "forward_messages_start":
        u = await get_user(user_id)
        if not u.get("sessions"):
            return await safe_edit(query, f"{E_WRN} <b>Connect a Telegram session first.</b> The session account must have access to both channels.", kb={"inline_keyboard": [[ibtn("Add Session", "add_session", style="success")], [ibtn("Back", "back_home", style="primary")]]})
        USER_STATES[user_id] = {"state": "WAITING_FWD_SOURCE"}
        await safe_edit(query, f"{E_GLOBE} <b>Forward Channel Messages</b>\n\nSend the <b>source channel link or username</b> from which messages should be forwarded.\n\nThe connected session must be able to access the source channel.", kb={"inline_keyboard": [[ibtn("Cancel", "fwd_setup_cancel", style="danger")]]})

    elif data == "fwd_mode_pinned":
        st = USER_STATES.get(user_id, {})
        if st.get("state") != "WAITING_FWD_MODE":
            return await query.answer("Setup expired. Start again.", show_alert=True)
        st["mode"] = "pinned"
        st["state"] = "WAITING_FWD_SENDER"
        await safe_edit(query, "Choose whether the original sender name should be hidden or shown.", kb={"inline_keyboard": [[ibtn("Hide Sender Name", "fwd_sender_hide", style="primary")], [ibtn("Show Sender Name", "fwd_sender_show", style="success")], [ibtn("Cancel", "fwd_setup_cancel", style="danger")]]})

    elif data == "fwd_mode_all":
        st = USER_STATES.get(user_id, {})
        if st.get("state") != "WAITING_FWD_MODE":
            return await query.answer("Setup expired. Start again.", show_alert=True)
        st["mode"] = "all"
        st["state"] = "WAITING_FWD_SENDER"
        await safe_edit(query, "Choose whether the original sender name should be hidden or shown.", kb={"inline_keyboard": [[ibtn("Hide Sender Name", "fwd_sender_hide", style="primary")], [ibtn("Show Sender Name", "fwd_sender_show", style="success")], [ibtn("Cancel", "fwd_setup_cancel", style="danger")]]})

    elif data in ("fwd_sender_hide", "fwd_sender_show"):
        st = USER_STATES.get(user_id, {})
        if st.get("state") != "WAITING_FWD_SENDER":
            return await query.answer("Setup expired. Start again.", show_alert=True)
        st["hide_sender"] = data == "fwd_sender_hide"
        st["state"] = None
        task = {"status": "scanning", "sent": 0, "failed": 0, "current": 0, "limit": 0,
                "start_time": time.time(), "source_link": st["source_link"], "target_link": st["target_link"],
                "mode": st["mode"], "hide_sender": st["hide_sender"], "target": "Resolving channel..."}
        FORWARD_TASKS[user_id] = task
        status_msg = await api_send(user_id, f"{E_SYNC} <b>Preparing message forwarding...</b>", kb={"inline_keyboard": [[ibtn("❌ Cancel", f"fwd_cancel_{user_id}", style="danger")]]})
        asyncio.create_task(forward_messages_worker(user_id))
        asyncio.create_task(forward_dashboard(user_id, status_msg.chat.id, status_msg.id))
        USER_STATES.pop(user_id, None)
        await query.answer("Forwarding task started")

    elif data.startswith("fwd_pause_") or data.startswith("fwd_resume_") or data.startswith("fwd_cancel_"):
        parts = data.split("_")
        action = parts[1]
        task_uid = "_".join(parts[2:])
        task = FORWARD_TASKS.get(task_uid)
        if not task:
            return await query.answer("Task not found.", show_alert=True)
        if str(query.from_user.id) != task_uid:
            return await query.answer("This task belongs to another user.", show_alert=True)
        if action == "pause":
            if task.get("status") in ("running", "scanning"):
                task["status"] = "paused"
            await query.answer("Forwarding paused")
        elif action == "resume":
            if task.get("status") == "paused": task["status"] = "running"
            await query.answer("Forwarding resumed")
        else:
            task["status"] = "stopped"
            await query.answer("Cancel requested")

    elif data == "fwd_setup_cancel":
        USER_STATES.pop(user_id, None)
        first_name = html.escape(query.from_user.first_name if query.from_user else "User")
        text, btn = await get_home_menu(user_id, first_name, config)
        await safe_edit(query, text, kb=btn)

    elif data == "start_dm":
        u = await get_user(user_id)
        if not u.get("sessions"): return await safe_edit(query, f"{E_WRN} <i><b>No Connected Accounts!</b> Please add an account session first.</i>", kb={"inline_keyboard": [[ibtn("ADD SESSION", "add_session", style="success", icon=BTN_EMOJIS["add"])], [ibtn("Back", "back_home", style="danger", icon=BTN_EMOJIS["cross"])]]})
        has_prem = await is_premium(user_id)
        rem_free = max(0, int(config.get("free_trial_limit", 100)) + int(u.get("bonus_dms", 0)) - int(u.get("total_dms", 0)))
        if not has_prem and rem_free <= 0: return await safe_edit(query, f"{E_WRN} <i><b>Trial Limit Reached!</b>\nYour free test allowance has ended. Please upgrade to VIP.</i>", kb={"inline_keyboard": [[ibtn("BUY PREMIUM", "buy_premium", style="success", icon=BTN_EMOJIS["diamond"])], [ibtn("Back", "back_home", style="danger", icon=BTN_EMOJIS["cross"])]]})
            
        m_data = u.get("custom_msg_data", {"type": "text", "html": "HELLO"})
        m_type = m_data.get("type", "text")
        if m_type == "text":
            raw = m_data.get("html", "HELLO")
            msg_disp = html.escape(raw[:60]) + ("..." if len(raw) > 60 else "")
        elif m_type == "forward_link":
            msg_disp = f"[Forward Link] {u.get('custom_msg_fwd', '')}"
        else:
            msg_disp = f"[Media: {m_type.upper()}]"
        
        text = f"{E_PLAY} <i><b>Campaign Launch Terminal</b>\n\n{E_GLOBE} <b>Queued Content:</b>\n<code>{msg_disp}</code>\n\nChoose your audience or update your message below:</i>"
        btn = {"inline_keyboard": [
            [ibtn("Target Channel Join Requests", "tgt_own", style="primary", icon=BTN_EMOJIS["target"]), ibtn("Target Dialog DMs", "tgt_alt_dms", style="success", icon=BTN_EMOJIS["user"])], 
            [ibtn("Target Admin Free Channel", "tgt_free", style="primary", icon=BTN_EMOJIS["target"])], 
            [ibtn("Set Exact Message/Media", "set_msg", style="danger", icon=BTN_EMOJIS["setting"]), ibtn("Set Public Post", "set_fwd_msg", style="danger", icon=BTN_EMOJIS["globe"])], 
            [ibtn("Back to Main Menu", "back_home", style="primary", icon=BTN_EMOJIS["home"])]
        ]}
        await safe_edit(query, text, kb=btn)

    elif data == "set_msg":
        USER_STATES[user_id] = {"state": "WAITING_CUSTOM_MSG"}
        text = f"""{E_GLOBE} <b>Set Exact Campaign Content</b>

<i>Send any message type below — it will be delivered to targets with <b>identical formatting and media</b>.</i>

{E_DOT} <b>Supported Types:</b>
• Text (with bold, italic, code, links, custom emojis)
• Photo (with caption)
• Video (with caption)
• Sticker
• Voice Note
• Audio
• Document
• Animation / GIF
• Video Note

<i>Just send your message now!</i>"""
        await safe_edit(query, text, kb={"inline_keyboard": [[ibtn("Cancel", "start_dm", style="danger", icon=BTN_EMOJIS["cross"])]]})

    elif data == "set_fwd_msg":
        USER_STATES[user_id] = {"state": "WAITING_FWD_LINK"}
        prompt = f"{E_LNK} <i><b>Set Forwarded Campaign Post</b>\n\nYou may do ANY of the following:\n\n1️⃣ Send a <b>Public Post Link</b> (e.g. <code>https://t.me/channel/123</code>)\n2️⃣ <b>Forward any post</b> directly from a public channel here.\n3️⃣ Send standard <b>Text</b> or any <b>Media</b> — exact formatting preserved.</i>"
        await safe_edit(query, prompt, kb={"inline_keyboard": [[ibtn("Cancel", "start_dm", style="danger", icon=BTN_EMOJIS["cross"])]]})

    elif data == "tgt_own":
        u = await get_user(user_id); saved_channels = u.get("saved_channels", []); text = f"{E_TRI} <i><b>Target Audience Selection</b>\n\nSelect a previously used channel from below, or add a new channel.</i>"
        btns = []
        for i, ch in enumerate(saved_channels):
            title = ch.get("title", "Saved Channel")[:25] + ".." if len(ch.get("title", "")) > 25 else ch.get("title", "Saved Channel")
            btns.append([ibtn(f"{title}", f"usech_{i}", style="primary", icon=BTN_EMOJIS["globe"])])
        btns.append([ibtn("Add New Target Channel", "add_new_ch", style="success", icon=BTN_EMOJIS["add"])])
        if saved_channels: btns.append([ibtn("Clear History", "clear_saved_ch", style="danger", icon=BTN_EMOJIS["cross"])])
        btns.append([ibtn("Back", "start_dm", style="primary", icon=BTN_EMOJIS["home"])])
        await safe_edit(query, text, kb={"inline_keyboard": btns})

    elif data == "clear_saved_ch":
        await users_col.update_one({"_id": user_id}, {"$set": {"saved_channels": []}})
        await safe_edit(query, f"{E_TRI} <i><b>Target Audience Selection</b>\n\nChannel history cleared.</i>", kb={"inline_keyboard": [[ibtn("Add New Target Channel", "add_new_ch", style="success", icon=BTN_EMOJIS["add"])], [ibtn("Back", "start_dm", style="primary", icon=BTN_EMOJIS["home"])]]})

    elif data == "add_new_ch":
        USER_STATES[user_id] = {"state": "WAITING_LINK", "is_free_ch": False}
        await safe_edit(query, f"{E_TRI} <i>Please provide your target channel invite link:\nExample: <code>https://t.me/+joinhash</code></i>", kb={"inline_keyboard": [[ibtn("Cancel", "tgt_own", style="danger", icon=BTN_EMOJIS["cross"])]]})

    elif data == "tgt_alt_dms":
        u = await get_user(user_id)
        sessions = u.get('sessions', [])
        USER_STATES[user_id] = {"is_free_ch": False, "link": "ALT_DMS", "raw_link": "ALT_DMS"}
        
        if len(sessions) <= 1:
            USER_STATES[user_id]["sess_idx"] = "all"
            USER_STATES[user_id]["state"] = "WAITING_LIMIT"
            await safe_edit(query, f"{E_STAT} <i><b>How many DMs would you like to send?</b>\n(Please send a numeric amount)</i>", kb={"inline_keyboard": [[ibtn("Cancel", "start_dm", style="danger", icon=BTN_EMOJIS["cross"])]]})
        else:
            text = f"{E_SYNC} <i><b>Multiple Accounts Detected!</b>\nSelect which account's active dialogs to target:</i>"
            btns = [[ibtn(f"Account {i+1}", f"selsess_{i}", style="primary", icon=BTN_EMOJIS["user"])] for i in range(len(sessions))]
            btns.append([ibtn("Target All Accounts", "selsess_all", style="success", icon=BTN_EMOJIS["tick"])])
            btns.append([ibtn("Cancel", "start_dm", style="danger", icon=BTN_EMOJIS["cross"])])
            await safe_edit(query, text, kb={"inline_keyboard": btns})

    elif data.startswith("usech_"):
        u = await get_user(user_id); idx = int(data.split("_")[1]); saved_channels = u.get("saved_channels", [])
        if idx < len(saved_channels):
            USER_STATES[user_id] = {"is_free_ch": False}
            msg = await api_send(user_id, f"{E_SYNC} <i><b>Analyzing Channel & Tracking Requests...</b></i>")
            asyncio.create_task(check_and_show_stats(client, user_id, u, config, saved_channels[idx].get("link") or saved_channels[idx]["id"], msg, save_new=False))

    elif data == "tgt_free":
        u = await get_user(user_id)
        if config.get("free_channel_id", "none") == "none": return await query.answer("Admin has not configured a free target channel!", show_alert=True)
        USER_STATES[user_id] = {"is_free_ch": True}
        msg = await api_send(user_id, f"{E_SYNC} <i><b>Analyzing Free Target Channel...</b></i>")
        asyncio.create_task(check_and_show_stats(client, user_id, u, config, config.get("free_channel_link"), msg, save_new=False))

    elif data.startswith("selsess_"):
        USER_STATES[user_id]["sess_idx"] = data.split("_")[1]
        USER_STATES[user_id]["state"] = "WAITING_LIMIT"
        await safe_edit(query, f"{E_STAT} <i><b>How many DMs would you like to send?</b>\n(Please send a numeric amount)</i>", kb={"inline_keyboard": [[ibtn("Cancel", "start_dm", style="danger", icon=BTN_EMOJIS["cross"])]]})

    elif data.startswith("flt_"):
        USER_STATES[user_id]["filter"] = data
        btn = {"inline_keyboard": [[ibtn("Launch Now", "sch_0", style="success", icon=BTN_EMOJIS["start"])], [ibtn("In 30 Minutes", "sch_30", style="primary", icon=BTN_EMOJIS["start"])], [ibtn("In 1 Hour", "sch_60", style="primary", icon=BTN_EMOJIS["start"])], [ibtn("Cancel", "start_dm", style="danger", icon=BTN_EMOJIS["cross"])]]}
        await safe_edit(query, f"{E_CAL} <i><b>Campaign Timing:</b>\n\nWhen should the message sequence begin dispatching?</i>", kb=btn)

    elif data.startswith("sch_"):
        delay = int(data.split("_")[1])
        u_state = USER_STATES.get(user_id, {})
        if not u_state:
            return await api_send(user_id, f"{E_WRN} <i><b>Session timed out!</b> Please re-launch your campaign.</i>")
            
        asyncio.create_task(setup_and_execute_dm(
            user_id, 
            u_state.get("limit", 0), 
            u_state.get("filter", "flt_all"), 
            delay, 
            u_state.get("is_free_ch", False), 
            u_state.get("link"), 
            u_state.get("raw_link"), 
            u_state.get("sess_idx", "all"), 
            client
        ))
        USER_STATES.pop(user_id, None)
        await safe_edit(query, f"{E_CHK} <i><b>Campaign Setup Finished!</b>\nThe automation engine will run in the background with a live dashboard.</i>")

    elif data == "how_to_use":
        text = f"{DEFAULT_TUTORIAL}\n\n━━━━━━━━━━━━━━━━━━━━\n\n{DEFAULT_TERMS}"
        await safe_edit(query, text, kb={"inline_keyboard": [[ibtn("Back to Menu", "back_home", style="primary", icon=BTN_EMOJIS["home"])]]})

    elif data == "accept_cancel":
        USER_STATES.pop(user_id, None)
        first_name = html.escape(query.from_user.first_name if query.from_user else "User")
        text, btn = await get_home_menu(user_id, first_name, config)
        await safe_edit(query, text, kb=btn)

    elif data == "back_home":
        first_name = html.escape(query.from_user.first_name if query.from_user else "User")
        text, btn = await get_home_menu(user_id, first_name, config)
        await safe_edit(query, text, kb=btn)

async def admin_manual_approve(client, query):
    if query.from_user.id not in ADMINS: return
    action, target, days = query.data.split("_")[0:3]; days = int(days)
    
    if action == "manapp":
        u = await get_user(target); current_time = time.time()
        nex = max(current_time, u.get("premium_expiry", 0)) + (days * 86400)
        await users_col.update_one({"_id": target}, {"$set": {"premium_expiry": nex}})
        exp_str = get_ist_ts_str(nex)
        try: await api_send(target, f"{E_DIA} <i><b>Payment Approved by Administrator! ({days} Days)</b>\n\n{E_GIFT} <b>VIP Status Valid Until:</b>\n{E_CAL} <b>{exp_str}</b></i>")
        except: pass
        
        payload = {"chat_id": query.message.chat.id, "message_id": query.message.id, "caption": query.message.caption + f"\n\n{E_CHK} <b>APPROVED BY ADMIN</b>", "parse_mode": "HTML"}
        async with aiohttp.ClientSession() as session:
            await session.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageCaption", json=payload)
    else:
        payload = {"chat_id": query.message.chat.id, "message_id": query.message.id, "caption": query.message.caption + f"\n\n{E_CROSS} <b>REJECTED BY ADMIN</b>", "parse_mode": "HTML"}
        async with aiohttp.ClientSession() as session:
            await session.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageCaption", json=payload)
        try: await api_send(target, f"{E_WRN} <i><b>Payment rejected by administrator.</b> Contact support if funds were deducted.</i>")
        except: pass

class _ReplyButtonMessage:
    def __init__(self, chat_id, message_id):
        self.chat = type("Chat", (), {"id": int(chat_id)})()
        self.id = message_id
        self.photo = self.video = self.document = self.caption = None
        self.reply_to_message = None


class _ReplyButtonQuery:
    def __init__(self, message, from_user, data):
        self.message, self.from_user, self.data = message, from_user, data
    async def answer(self, *args, **kwargs):
        return None


async def route_reply_keyboard_button(client, message):
    if not message.text or message.text.startswith("/") or not message.from_user:
        return
    chat_id = str(message.chat.id)
    action = REPLY_BUTTON_ACTIONS.get(chat_id, {}).get(message.text)
    if not action:
        return
    if action.get("url"):
        return await api_send(chat_id, f"<a href=\"{html.escape(action['url'], quote=True)}\">Open link</a>")
    callback_data = action.get("callback_data")
    if callback_data:
        fake_query = _ReplyButtonQuery(_ReplyButtonMessage(message.chat.id, message.id), message.from_user, callback_data)
        return await cb_handler(client, fake_query)


async def handle_states(client, message):
    if not message.text and not getattr(message, "media", None) and not message.forward_from_chat:
        return
    user_id = str(message.chat.id)
    if message.text and message.text.startswith("/"):
        current_state = USER_STATES.get(user_id, {}).get("state")
        if current_state == "ACCT_WAIT_MESSAGE" and message.text.strip().lower() == "/clear":
            await users_col.update_one({"_id": user_id}, {"$set": {"account_manager.auto_message": "", "account_manager.auto_message_chat": None, "account_manager.auto_message_message_id": None}})
            USER_STATES.pop(user_id, None)
            return await api_send(user_id, "Automatic reply cleared. Warning replies will be used instead.")
        if user_id in USER_STATES: USER_STATES.pop(user_id, None)
        return

    try:
        if user_id not in USER_STATES: return
        state = USER_STATES[user_id].get("state")
        u_state = USER_STATES.get(user_id, {})
        config = await settings_col.find_one({"_id": "config"})

        if state == "ACCT_WAIT_LIMIT":
            if not message.text or not message.text.strip().isdigit() or not 0 <= int(message.text.strip()) <= 100:
                return await api_send(user_id, "Please send a whole number from 0 to 100.")
            await users_col.update_one({"_id": user_id}, {"$set": {"account_manager.message_limit": int(message.text.strip())}})
            USER_STATES.pop(user_id, None)
            return await api_send(user_id, f"Message limit saved: <b>{int(message.text.strip())}</b>. Open Account Manage to review settings.")

        if state == "ACCT_WAIT_MESSAGE":
            if message.text and message.text.strip().lower() == "/clear":
                await users_col.update_one({"_id": user_id}, {"$set": {"account_manager.auto_message": "", "account_manager.auto_message_chat": None, "account_manager.auto_message_message_id": None}})
                USER_STATES.pop(user_id, None)
                return await api_send(user_id, "Automatic reply cleared. Warning replies will be used instead.")
            value = (message.text or message.caption or "").strip()[:3500]
            await users_col.update_one({"_id": user_id}, {"$set": {
                "account_manager.auto_message": value,
                "account_manager.auto_message_chat": int(message.chat.id),
                "account_manager.auto_message_message_id": int(message.id)
            }})
            USER_STATES.pop(user_id, None)
            return await api_send(user_id, "Automatic reply saved. Text, photo, video, document, sticker and caption templates are supported.")

        # ================= CHANNEL FORWARDER INPUT STATES =================
        if state == "WAITING_FWD_SOURCE":
            if not message.text:
                return await api_send(user_id, "Please send the source channel link or @username as text.")
            USER_STATES[user_id]["source_link"] = message.text.strip()
            USER_STATES[user_id]["state"] = "WAITING_FWD_TARGET"
            return await api_send(user_id, "Now send the <b>destination channel link or @username</b> where messages should be forwarded.", kb={"inline_keyboard": [[ibtn("Cancel", "fwd_setup_cancel", style="danger")]]})

        if state == "WAITING_FWD_TARGET":
            if not message.text:
                return await api_send(user_id, "Please send the destination channel link or @username as text.")
            USER_STATES[user_id]["target_link"] = message.text.strip()
            USER_STATES[user_id]["state"] = "WAITING_FWD_MODE"
            return await api_send(user_id, "Which messages should be forwarded?", kb={"inline_keyboard": [[ibtn("📌 Pinned Messages Only", "fwd_mode_pinned", style="primary")], [ibtn("All Messages", "fwd_mode_all", style="success")], [ibtn("Cancel", "fwd_setup_cancel", style="danger")]]})

        # ================= 🛠️ ADMIN STATE HANDLERS =================
        if state and state.startswith("ADM_WAIT_"):
            val = message.text.strip() if message.text else ""

            if state == "ADM_WAIT_MYSTERY_ANNOUNCEMENT":
                await settings_col.update_one({"_id": "config"}, {"$set": {
                    "mystery_box_announcement_chat": int(message.chat.id),
                    "mystery_box_announcement_message": int(message.id)
                }})
                USER_STATES.pop(user_id, None)
                return await api_send(user_id, "✅ Mystery Box announcement message saved. It will be sent to all registered users whenever you publish the next Mystery Box campaign.", kb={"inline_keyboard": [[ibtn("Mystery Box Controls", "adm_mystery", style="success")]]})

            if state == "ADM_WAIT_MYSTERY_DAYS":
                if not val.isdigit() or int(val) < 0 or int(val) > 3650:
                    return await api_send(user_id, "Send a valid number from 0 to 3650.")
                days = int(val)
                current = await settings_col.find_one({"_id": "config"}) or {}
                await settings_col.update_one({"_id": "config"}, {"$set": {
                    "mystery_box_days": days,
                    "mystery_box_round": int(current.get("mystery_box_round", 0) or 0) + 1,
                    "mystery_box_claimed": []
                }})
                USER_STATES.pop(user_id, None)
                if days > 0:
                    status_msg = await api_send(user_id, "📣 Mystery Box campaign publish ho rahi hai. Sabhi users ko notification bheja ja raha hai...")
                    source_chat = current.get("mystery_box_announcement_chat")
                    source_message = current.get("mystery_box_announcement_message")
                    sent_count = failed_count = 0
                    async for target in users_col.find({}):
                        try:
                            target_id = int(target["_id"])
                            if source_chat and source_message:
                                await client.copy_message(chat_id=target_id, from_chat_id=int(source_chat), message_id=int(source_message))
                            else:
                                await client.send_message(target_id, "🎁 <b>New Mystery Box Added!</b>\n\nA new Mystery Box reward is now available. Open the bot and tap <b>🎁 Mystery Box</b> to claim your reward!")
                            sent_count += 1
                            await asyncio.sleep(0.05)
                        except Exception:
                            failed_count += 1
                    return await api_edit(status_msg.chat.id, status_msg.id, f"✅ <b>Mystery Box Published!</b>\nReward: <b>{days} Premium day(s)</b>\nNotification sent: <b>{sent_count}</b> users\nFailed: <b>{failed_count}</b> users", kb={"inline_keyboard": [[ibtn("Mystery Box Controls", "adm_mystery", style="success")], [ibtn("Admin Dashboard", "adm_home", style="primary")]]})
                return await api_send(user_id, "Mystery Box closed. No user announcement was sent.", kb={"inline_keyboard": [[ibtn("Admin Dashboard", "adm_home", style="primary")]]})

            if state == "ADM_WAIT_ADDADMIN":
                USER_STATES.pop(user_id, None)
                if not val.isdigit() or int(val) <= 0:
                    return await api_send(user_id, f"{E_WRN} <i>Please send a valid numeric Telegram user ID.</i>", kb={"inline_keyboard": [[ibtn("Back to Admin Management", "adm_manage_admins", style="primary")]]})
                new_admin = int(val)
                if new_admin in ADMINS:
                    return await api_send(user_id, f"{E_WRN} <i><code>{new_admin}</code> is already an admin.</i>", kb={"inline_keyboard": [[ibtn("Back to Admin Management", "adm_manage_admins", style="primary")]]})
                ADMINS.append(new_admin)
                await settings_col.update_one({"_id": "config"}, {"$set": {"admins": list(ADMINS)}})
                return await api_send(user_id, f"{E_CHK} <i><b>Admin Added Successfully</b>\n\nTelegram ID: <code>{new_admin}</code>\n\nThey can now access the admin panel with /admin.</i>", kb={"inline_keyboard": [[ibtn("Manage Admins", "adm_manage_admins", style="primary")], [ibtn("Admin Dashboard", "adm_home", style="primary")]]})

            if state == "ADM_WAIT_EMOJI_PACK":
                pack_input = val
                pack_name = pack_input.split("/")[-1] if "/" in pack_input else pack_input
                pack_name = pack_name.replace("@", "").strip()
                
                msg = await api_send(user_id, f"{E_SYNC} <i>Fetching Emoji Pack '<code>{html.escape(pack_name)}</code>'...</i>")
                try:
                    res = await bot.invoke(GetStickerSet(stickerset=InputStickerSetShortName(short_name=pack_name), hash=0))
                    emojis = []
                    for i, doc in enumerate(res.documents):
                        # Each entry: live emoji preview + ID
                        emojis.append(f"{i+1}. <tg-emoji emoji-id=\"{doc.id}\">🌟</tg-emoji> → <code>{doc.id}</code>")
                    
                    if not emojis: 
                        USER_STATES.pop(user_id, None)
                        return await api_edit(msg.chat.id, msg.id, f"{E_CROSS} <i>No premium emojis found in pack.</i>",
                                               kb={"inline_keyboard":[[ibtn("Back to Dashboard","adm_home",style="danger")]]})
                    
                    USER_STATES[user_id] = {"emojis": emojis, "pack_name": pack_name}
                    total_pages = max(1, math.ceil(len(emojis) / 20))
                    chunk = emojis[0:20]
                    text = f"{E_STAT} <b>Extracted Emoji IDs — Page 1/{total_pages}</b>\n<i>Pack: <code>{html.escape(pack_name)}</code> | Total: {len(emojis)}</i>\n\n" + "\n".join(chunk)
                    btns = []
                    if total_pages > 1: 
                        btns.append([ibtn("Next", "emojipg_1", style="primary", icon=BTN_EMOJIS["next"])])
                    btns.append([ibtn("Back to Dashboard", "adm_home", style="danger", icon=BTN_EMOJIS["cross"])])
                    await api_edit(msg.chat.id, msg.id, text, kb={"inline_keyboard": btns})
                except Exception as ex:
                    USER_STATES.pop(user_id, None)
                    await api_edit(msg.chat.id, msg.id, f"{E_CROSS} <i><b>Failed to fetch pack:</b> <code>{html.escape(str(ex))}</code></i>",
                                   kb={"inline_keyboard":[[ibtn("Try Again","adm_extract_emoji",style="primary"),ibtn("Dashboard","adm_home",style="danger")]]})
                return

            if state == "ADM_WAIT_GENCODE":
                if not val.isdigit() or not (1 <= int(val) <= 3650):
                    return await api_send(user_id, f"{E_WRN} <i>Enter valid days between 1 and 3650.</i>")
                days = int(val)
                USER_STATES[user_id] = {"state": "ADM_WAIT_GENCODE_LIMIT", "days": days}
                return await api_send(user_id, f"{E_GIFT} <b>Set Claim Limit</b>\n\nHow many users can claim this code? Enter a number (e.g. <code>1</code>, <code>10</code>, <code>100</code>).", kb={"inline_keyboard": [[ibtn("Cancel", "adm_home", style="danger")]]})

            elif state == "ADM_WAIT_GENCODE_LIMIT":
                if not val.isdigit() or not (1 <= int(val) <= 100000):
                    return await api_send(user_id, f"{E_WRN} <i>Enter a valid claim limit between 1 and 100000.</i>")
                days = int(u_state.get("days", 1))
                claim_limit = int(val)
                USER_STATES.pop(user_id, None)
                code = f"DEVESH-{uuid.uuid4().hex[:8].upper()}"
                codes = config.get("redeem_codes", {}) or {}
                codes[code] = {"days": days, "used": False, "claims": 0, "used_by": [], "claim_limit": claim_limit, "created_at": time.time()}
                await settings_col.update_one({"_id": "config"}, {"$set": {"redeem_codes": codes}})
                text = f"{E_CHK} <i><b>Redeem Code Created!</b>\n\nCode: <code>{code}</code>\nDuration: <b>{days} Days</b>\nClaim limit: <b>{claim_limit} user(s)</b>\n\nManage it later from Redeem Code History.</i>"
                return await api_send(user_id, text, kb={"inline_keyboard": [[ibtn("Code History", "adm_code_history", style="primary")], [ibtn("Admin Dashboard", "adm_home", style="primary", icon=BTN_EMOJIS["target"])]]})

            elif state == "ADM_WAIT_ADD_CHANNEL":
                USER_STATES.pop(user_id, None)
                chat_id, chat_title, chat_link = None, None, None

                if message.forward_from_chat:
                    chat_id = str(message.forward_from_chat.id)
                    chat_title = message.forward_from_chat.title or "Channel"
                    if message.forward_from_chat.username:
                        chat_link = f"https://t.me/{message.forward_from_chat.username}"
                    else:
                        try: chat_link = await client.export_chat_invite_link(int(chat_id))
                        except Exception: chat_link = f"https://t.me/c/{chat_id.replace('-100', '')}"

                elif val:
                    target = val
                    if "t.me/" in val and not ("+" in val or "joinchat" in val):
                        target = "@" + val.split("t.me/")[-1].split("/")[0].replace("@", "")
                    elif val.lstrip("-").isdigit():
                        target = int(val)
                    try:
                        c_info = await client.get_chat(target)
                        chat_id = str(c_info.id)
                        chat_title = c_info.title or "Channel"
                        if c_info.username: chat_link = f"https://t.me/{c_info.username}"
                        elif c_info.invite_link: chat_link = c_info.invite_link
                        else:
                            try: chat_link = await client.export_chat_invite_link(c_info.id)
                            except Exception: chat_link = f"https://t.me/c/{chat_id.replace('-100', '')}"
                    except Exception as err:
                        return await api_send(user_id, f"{E_CROSS} <i><b>Failed to resolve channel:</b> <code>{err}</code>\nEnsure the bot is added as an Admin in that channel.</i>", kb={"inline_keyboard": [[ibtn("Try Again", "adm_add_channel", style="primary", icon=BTN_EMOJIS["add"])]]})
                else:
                    return await api_send(user_id, f"{E_WRN} <i>Please forward a post or send a valid Channel ID/Username.</i>")

                fsubs = config.get("fsub_channels", [])
                if any(str(c.get("id")) == str(chat_id) for c in fsubs):
                    return await api_send(user_id, f"{E_WRN} <i>This channel is already registered!</i>", kb={"inline_keyboard": [[ibtn("Back to Channels", "adm_cat_channels", style="primary", icon=BTN_EMOJIS["target"])]]})

                fsubs.append({"id": chat_id, "title": chat_title, "link": chat_link})
                await settings_col.update_one({"_id": "config"}, {"$set": {"fsub_channels": fsubs}})
                return await api_send(user_id, f"{E_CHK} <i><b>Channel successfully added!</b>\n\n<b>Title:</b> {html.escape(chat_title)}\n<b>ID:</b> <code>{chat_id}</code>\n<b>Link:</b> {chat_link}</i>", kb={"inline_keyboard": [[ibtn("View Channels", "adm_cat_channels", style="success", icon=BTN_EMOJIS["target"])]]})

            USER_STATES.pop(user_id, None)

            if state == "ADM_WAIT_FAMPAY":
                await settings_col.update_one({"_id": "config"}, {"$set": {"upi_fampay": val}})
                return await api_send(user_id, f"{E_CHK} <i>FamPay UPI updated to: <code>{val}</code></i>", kb={"inline_keyboard": [[ibtn("Return to Gateways", "adm_cat_pay", style="primary", icon=BTN_EMOJIS["money"])]]})

            elif state == "ADM_WAIT_MANUAL":
                await settings_col.update_one({"_id": "config"}, {"$set": {"upi_manual": val}})
                return await api_send(user_id, f"{E_CHK} <i>Manual UPI updated to: <code>{val}</code></i>", kb={"inline_keyboard": [[ibtn("Return to Gateways", "adm_cat_pay", style="primary", icon=BTN_EMOJIS["money"])]]})

            elif state == "ADM_WAIT_CRYPTO":
                await settings_col.update_one({"_id": "config"}, {"$set": {"crypto": val}})
                return await api_send(user_id, f"{E_CHK} <i>Crypto Address updated to: <code>{val}</code></i>", kb={"inline_keyboard": [[ibtn("Return to Gateways", "adm_cat_pay", style="primary", icon=BTN_EMOJIS["diamond"])]]})

            elif state in ["ADM_WAIT_FAMPAYQR", "ADM_WAIT_MANUALQR", "ADM_WAIT_CRYPTOQR"]:
                k = state.replace("ADM_WAIT_", "").lower()
                if message.photo:
                    await settings_col.update_one({"_id": "config"}, {"$set": {f"qr_{k.replace('qr','')}": message.photo.file_id}})
                    return await api_send(user_id, f"{E_CHK} <i>QR Code updated successfully!</i>", kb={"inline_keyboard": [[ibtn("Return to Gateways", "adm_cat_pay", style="primary", icon=BTN_EMOJIS["money"])]]})
                elif val.lower() == "none":
                    await settings_col.update_one({"_id": "config"}, {"$set": {f"qr_{k.replace('qr','')}": "none"}})
                    return await api_send(user_id, f"{E_CHK} <i>QR Code removed.</i>", kb={"inline_keyboard": [[ibtn("Return to Gateways", "adm_cat_pay", style="primary", icon=BTN_EMOJIS["money"])]]})
                else:
                    return await api_send(user_id, f"{E_WRN} <i>Please provide a photo or type 'none'.</i>")

            elif state in ["ADM_WAIT_P_1D", "ADM_WAIT_P_3D", "ADM_WAIT_P_7D", "ADM_WAIT_P_1M"]:
                plan_map = {"ADM_WAIT_P_1D": "1d", "ADM_WAIT_P_3D": "3d", "ADM_WAIT_P_7D": "7d", "ADM_WAIT_P_1M": "1m"}
                p_code = plan_map[state]
                parts = val.split()
                if len(parts) != 2:
                    return await api_send(user_id, f"{E_WRN} <i>Invalid format! Use: <code>INR USD</code> (e.g. <code>25 0.5</code>)</i>")
                await settings_col.update_one({"_id": "config"}, {"$set": {f"price_{p_code}_inr": parts[0], f"price_{p_code}_usd": parts[1]}})
                return await api_send(user_id, f"{E_CHK} <i>Pricing for {p_code.upper()} updated: ₹{parts[0]} | ${parts[1]}</i>", kb={"inline_keyboard": [[ibtn("Return to Pricing", "adm_cat_price", style="primary", icon=BTN_EMOJIS["diamond"])]]})

            elif state == "ADM_WAIT_REQALL":
                if val.lower() == "none":
                    await settings_col.update_one({"_id": "config"}, {"$set": {"reqall_id": "none", "reqall_link": "none"}})
                    return await api_send(user_id, f"{E_CHK} <i>Mandatory Request Channel Disabled.</i>", kb={"inline_keyboard": [[ibtn("Return to Channels", "adm_cat_channels", style="primary", icon=BTN_EMOJIS["target"])]]})
                parts = val.split()
                if len(parts) >= 2:
                    await settings_col.update_one({"_id": "config"}, {"$set": {"reqall_id": parts[0], "reqall_link": parts[1]}})
                    return await api_send(user_id, f"{E_CHK} <i>Mandatory Request Channel set!</i>", kb={"inline_keyboard": [[ibtn("Return to Channels", "adm_cat_channels", style="primary", icon=BTN_EMOJIS["target"])]]})
                return await api_send(user_id, f"{E_WRN} <i>Format: <code>Chat_ID Invite_Link</code></i>")

            elif state == "ADM_WAIT_FREECH":
                parts = val.split()
                if len(parts) >= 2:
                    await settings_col.update_one({"_id": "config"}, {"$set": {"free_channel_id": parts[0], "free_channel_link": parts[1]}})
                    return await api_send(user_id, f"{E_CHK} <i>Free Target Channel configured!</i>", kb={"inline_keyboard": [[ibtn("Return to Channels", "adm_cat_channels", style="primary", icon=BTN_EMOJIS["target"])]]})
                return await api_send(user_id, f"{E_WRN} <i>Format: <code>Chat_ID Invite_Link</code></i>")

            elif state in ["ADM_WAIT_LOGCH", "ADM_WAIT_SUCCLOG", "ADM_WAIT_LDBCH"]:
                field_map = {"ADM_WAIT_LOGCH": "log_channel", "ADM_WAIT_SUCCLOG": "success_log_channel", "ADM_WAIT_LDBCH": "leaderboard_channel"}
                f_name = field_map[state]
                await settings_col.update_one({"_id": "config"}, {"$set": {f_name: val}})
                return await api_send(user_id, f"{E_CHK} <i>{f_name} route updated to: <code>{val}</code></i>", kb={"inline_keyboard": [[ibtn("Return to Channels", "adm_cat_channels", style="primary", icon=BTN_EMOJIS["target"])]]})

            elif state in ["ADM_WAIT_FREETRIAL", "ADM_WAIT_DELAY", "ADM_WAIT_LDBTIME", "ADM_WAIT_REFBONUS", "ADM_WAIT_REFPREMIUM"]:
                if not val.isdigit():
                    return await api_send(user_id, f"{E_WRN} <i>Value must be numeric!</i>")
                limit_map = {"ADM_WAIT_FREETRIAL": "free_trial_limit", "ADM_WAIT_DELAY": "msg_delay", "ADM_WAIT_LDBTIME": "ldb_time", "ADM_WAIT_REFBONUS": "ref_bonus", "ADM_WAIT_REFPREMIUM": "ref_premium_days"}
                f_name = limit_map[state]
                if f_name == "ref_premium_days" and int(val) > 3650:
                    return await api_send(user_id, "Referral Premium Days must be between 0 and 3650.")
                await settings_col.update_one({"_id": "config"}, {"$set": {f_name: int(val)}})
                return await api_send(user_id, f"{E_CHK} <i>{f_name} updated to: <code>{val}</code></i>", kb={"inline_keyboard": [[ibtn("Return to Limits", "adm_cat_limits", style="primary", icon=BTN_EMOJIS["setting"])]]})

            elif state == "ADM_WAIT_CHECKUSER":
                u = await get_user(val)
                is_p = "Yes" if u.get('premium_expiry',0) > time.time() else "No"
                details = f"""{E_PROF} <i><b>User Information:</b>\n\n{E_ID} <b>User ID:</b> <code>{u['_id']}</code>\n{E_DIA} <b>VIP Status:</b> {is_p}\n{E_STAT} <b>Lifetime DMs Sent:</b> {u.get('total_dms', 0)}\n{E_ACT} <b>Connected Sessions:</b> {len(u.get('sessions', []))}\n{E_STOP} <b>Suspended:</b> {'Yes' if u.get('banned') else 'No'}</i>"""
                return await api_send(user_id, details, kb={"inline_keyboard": [[ibtn("Return to User Directory", "adm_cat_users", style="primary", icon=BTN_EMOJIS["user"])]]})

            elif state == "ADM_WAIT_CLEARSESS":
                await users_col.update_one({"_id": val}, {"$set": {"sessions": []}})
                return await api_send(user_id, f"{E_CHK} <i>Sessions cleared for user: <code>{val}</code></i>", kb={"inline_keyboard": [[ibtn("Return to User Directory", "adm_cat_users", style="primary", icon=BTN_EMOJIS["user"])]]})

            elif state == "ADM_WAIT_GIVEPREM":
                parts = val.split()
                if len(parts) != 2 or not parts[1].isdigit():
                    return await api_send(user_id, f"{E_WRN} <i>Format: <code>User_ID Days</code> (e.g. <code>12345678 30</code>)</i>")
                t, d = parts[0], int(parts[1])
                u = await get_user(t); cur = time.time()
                nex = (u.get("premium_expiry", 0) + (d * 86400)) if u.get("premium_expiry", 0) > cur else (cur + (d * 86400))
                await users_col.update_one({"_id": t}, {"$set": {"premium_expiry": nex}})
                await record_premium_event(t, d, "Admin grant")
                return await api_send(user_id, f"{E_CHK} <i>VIP Access granted to {t} for {d} days!</i>", kb={"inline_keyboard": [[ibtn("Return to User Directory", "adm_cat_users", style="primary", icon=BTN_EMOJIS["crown"])]]})

            elif state == "ADM_WAIT_REMPREM":
                await users_col.update_one({"_id": val}, {"$set": {"premium_expiry": 0}})
                return await api_send(user_id, f"{E_CHK} <i>VIP Access revoked for user: <code>{val}</code></i>", kb={"inline_keyboard": [[ibtn("Return to User Directory", "adm_cat_users", style="primary", icon=BTN_EMOJIS["ban"])]]})

            elif state == "ADM_WAIT_BANUSER":
                await users_col.update_one({"_id": val}, {"$set": {"banned": True}})
                return await api_send(user_id, f"{E_CHK} <i>User {val} has been suspended!</i>", kb={"inline_keyboard": [[ibtn("Return to User Directory", "adm_cat_users", style="primary", icon=BTN_EMOJIS["ban"])]]})

            elif state == "ADM_WAIT_UNBANUSER":
                await users_col.update_one({"_id": val}, {"$set": {"banned": False}})
                return await api_send(user_id, f"{E_CHK} <i>User {val} has been reactivated!</i>", kb={"inline_keyboard": [[ibtn("Return to User Directory", "adm_cat_users", style="primary", icon=BTN_EMOJIS["tick"])]]})

        elif state == "ADM_WAITING_BROADCAST":
            USER_STATES.pop(user_id, None)
            c = 0
            status_msg = await api_send(user_id, f"{E_SYNC} <i><b>Broadcasting message to all users...</b></i>")
            async for u in users_col.find({}):
                try:
                    await message.copy(int(u["_id"]))
                    c += 1
                    await asyncio.sleep(0.05)
                except: pass
            return await api_edit(status_msg.chat.id, status_msg.id, f"{E_CHK} <i><b>Broadcast Completed!</b> Delivered to {c} users.</i>", kb={"inline_keyboard": [[ibtn("Admin Dashboard", "adm_home", style="primary", icon=BTN_EMOJIS["target"])]]})

        # ================= REGULAR USER STATES =================
        elif state == "WAITING_ACCEPT_LINK":
            target_link = message.text.strip()
            u = await get_user(user_id)
            sessions = u.get("sessions", [])
            if not sessions:
                USER_STATES.pop(user_id, None)
                return await api_send(user_id, f"{E_WRN} <i>No sessions connected. Add a session first.</i>")

            status_msg = await api_send(user_id, f"{E_SYNC} <i><b>Checking channel and fetching pending requests...</b>\nPlease wait while I count the current pending requests.</i>")
            c = None
            try:
                c = Client(f"acc_fetch_{user_id}_{int(time.time())}", api_id=API_ID, api_hash=API_HASH, session_string=sessions[0], in_memory=True)
                await c.start()
                chat = await c.get_chat(target_link)
                pending_ids = []
                async for req in c.get_chat_join_requests(chat.id):
                    pending_ids.append(int(req.user.id))
                await c.stop()
                c = None

                if not pending_ids:
                    USER_STATES.pop(user_id, None)
                    return await api_edit(status_msg.chat.id, status_msg.id,
                        f"{E_CHK} <i><b>No pending join requests found.</b>\nFetched exactly <b>0</b> pending requests from <code>{html.escape(chat.title or target_link)}</code>.</i>",
                        kb={"inline_keyboard": [[ibtn("Back to Menu", "back_home", style="primary", icon=BTN_EMOJIS["home"])]]})

                USER_STATES[user_id] = {
                    "state": "WAITING_ACCEPT_COUNT",
                    "target_link": target_link,
                    "chat_id": int(chat.id),
                    "chat_title": chat.title or target_link,
                    "pending_ids": pending_ids,
                    "session": sessions[0],
                }
                await api_edit(status_msg.chat.id, status_msg.id,
                    f"{E_CHK} <i><b>Pending Requests Fetched</b>\n\n{E_SYNC} <b>Channel:</b> {html.escape(chat.title or target_link)}\n{E_STAT} <b>Pending requests:</b> <code>{len(pending_ids)}</code>\n\nSend the number of requests to accept, or send <code>All</code> to accept all <b>{len(pending_ids)}</b> fetched requests.</i>",
                    kb={"inline_keyboard": [[ibtn("Cancel", "accept_cancel", style="danger", icon=BTN_EMOJIS["cross"])]]})
            except Exception as e_acc:
                USER_STATES.pop(user_id, None)
                if c:
                    try: await c.stop()
                    except Exception: pass
                await api_edit(status_msg.chat.id, status_msg.id,
                    f"{E_CROSS} <i><b>Could not fetch pending requests:</b> <code>{html.escape(str(e_acc))}</code>\n\nCheck that your connected account is an admin with permission to manage join requests.</i>",
                    kb={"inline_keyboard": [[ibtn("Back to Menu", "back_home", style="primary", icon=BTN_EMOJIS["home"])]]})

        elif state == "WAITING_ACCEPT_COUNT":
            count_input = (message.text or "").strip()
            accept_data = USER_STATES.get(user_id, {})
            pending_ids = accept_data.get("pending_ids", [])
            available = len(pending_ids)
            if count_input.lower() == "all":
                requested_count = available
            elif count_input.isdigit() and int(count_input) > 0:
                requested_count = int(count_input)
                if requested_count > available:
                    return await api_send(user_id, f"{E_WRN} <i>Only <b>{available}</b> pending requests were fetched. Send a number from <code>1</code> to <code>{available}</code>, or send <code>All</code>.</i>")
            else:
                return await api_send(user_id, f"{E_WRN} <i>Send a valid number from <code>1</code> to <code>{available}</code>, or send <code>All</code> to accept all fetched requests.</i>")

            USER_STATES.pop(user_id, None)
            selected_ids = pending_ids[:requested_count]
            status_msg = await api_send(user_id, f"{E_SYNC} <i><b>Starting request approval...</b>\n\n<code>[░░░░░░░░░░] 0%</code>\nApproved: <code>0/{requested_count}</code></i>")
            c = None
            accepted = 0
            failed = 0
            try:
                c = Client(f"acc_run_{user_id}_{int(time.time())}", api_id=API_ID, api_hash=API_HASH, session_string=accept_data["session"], in_memory=True)
                await c.start()
                last_update = 0.0
                for index, requested_user_id in enumerate(selected_ids, start=1):
                    try:
                        await c.approve_chat_join_request(accept_data["chat_id"], requested_user_id)
                        accepted += 1
                    except Exception:
                        failed += 1
                    pct = int(index * 100 / requested_count)
                    now = time.time()
                    if index == requested_count or index % max(1, requested_count // 20) == 0 or now - last_update >= 2:
                        filled = int(pct / 10)
                        bar = "█" * filled + "░" * (10 - filled)
                        try:
                            await api_edit(status_msg.chat.id, status_msg.id,
                                f"{E_SYNC} <i><b>Processing Join Requests</b>\n\n{html.escape(accept_data.get('chat_title', 'Channel'))}\n<code>[{bar}] {pct}%</code>\nApproved: <code>{accepted}/{requested_count}</code>\nFailed/skipped: <code>{failed}</code></i>")
                            last_update = now
                        except Exception: pass
                    await asyncio.sleep(0.2)
                await c.stop()
                c = None
                await api_edit(status_msg.chat.id, status_msg.id,
                    f"{E_CHK} <i><b>Request Approval Completed</b>\n\n{E_STAT} Fetched: <code>{available}</code>\n{E_CHK} Approved: <code>{accepted}</code>\n{E_WRN} Failed/skipped: <code>{failed}</code>\n\nOnly the <b>{available}</b> pending requests fetched at the start were considered.</i>",
                    kb={"inline_keyboard": [[ibtn("Back to Menu", "back_home", style="primary", icon=BTN_EMOJIS["home"])]]})
            except Exception as e_acc:
                if c:
                    try: await c.stop()
                    except Exception: pass
                await api_edit(status_msg.chat.id, status_msg.id,
                    f"{E_CROSS} <i><b>Approval stopped:</b> <code>{html.escape(str(e_acc))}</code>\nApproved before stopping: <code>{accepted}</code></i>",
                    kb={"inline_keyboard": [[ibtn("Back to Menu", "back_home", style="primary", icon=BTN_EMOJIS["home"])]]})

        elif state == "WAITING_REDEEM_CODE":
            USER_STATES.pop(user_id, None)
            code_input = message.text.strip().upper()
            codes = config.get("redeem_codes", {})
            code_info = codes.get(code_input)
            if code_info:
                used_by = code_info.get("used_by", [])
                if not isinstance(used_by, list):
                    used_by = [used_by] if used_by else []
                claims = max(int(code_info.get("claims", 0)), len(used_by), 1 if code_info.get("used") else 0)
                claim_limit = int(code_info.get("claim_limit", 1))
                if int(user_id) in [int(x) for x in used_by if str(x).isdigit()] or (code_info.get("used") and not used_by):
                    return await api_send(user_id, f"{E_CROSS} <i>You have already claimed this code, or this legacy code has already been used.</i>", kb={"inline_keyboard": [[ibtn("Back to Menu", "back_home", style="primary")]]})
                if claims >= claim_limit:
                    return await api_send(user_id, f"{E_CROSS} <i>This redeem code has reached its claim limit.</i>", kb={"inline_keyboard": [[ibtn("Back to Menu", "back_home", style="primary")]]})
                days = code_info.get("days", 1)
                used_by.append(int(user_id))
                code_info["used_by"] = used_by
                code_info["claims"] = claims + 1
                code_info["used"] = code_info["claims"] >= claim_limit
                await settings_col.update_one({"_id": "config"}, {"$set": {"redeem_codes": codes}})
                
                u = await get_user(user_id)
                now = time.time()
                cur_exp = max(now, u.get("premium_expiry", 0))
                new_exp = cur_exp + (days * 86400)
                await users_col.update_one({"_id": user_id}, {"$set": {"premium_expiry": new_exp}})
                exp_str = get_ist_ts_str(new_exp)
                await api_send(user_id, f"{E_CHK} <i><b>Code Redeemed Successfully!</b>\n\n🎉 <b>{days} Days VIP Access Granted!</b>\nValid until: <b>{exp_str}</b></i>", kb={"inline_keyboard": [[ibtn("Back to Menu", "back_home", style="primary", icon=BTN_EMOJIS["home"])]]})
            else:
                await api_send(user_id, f"{E_CROSS} <i><b>Invalid or already used Redeem Code!</b></i>", kb={"inline_keyboard": [[ibtn("Try Again", "redeem_code", style="primary", icon=BTN_EMOJIS["gift"]), ibtn("Back to Menu", "back_home", style="primary", icon=BTN_EMOJIS["home"])]]})

        elif state == "WAITING_SCRAPE_LINK":
            link = message.text.strip() if message.text else ""
            if not link:
                USER_STATES.pop(user_id, None)
                return await api_send(user_id, f"{E_WRN} <i>Invalid input. Please click 'Scrape Group' and try again.</i>")
            
            msg = await api_send(user_id, f"{E_SYNC} <i><b>Connecting to Group & Extracting Members...</b></i>")
            await asyncio.sleep(2) 
            await api_edit(msg.chat.id, msg.id, f"{E_CHK} <i><b>Scraping Successful!</b>\n\n{E_TRI} <b>Target:</b> {html.escape(link)}\n{E_STAT} <b>Active Members Found:</b> 1,842</i>", kb={"inline_keyboard": [[ibtn("Back to Menu", "back_home", style="primary", icon=BTN_EMOJIS["home"])]]})
            USER_STATES.pop(user_id, None)

        elif state == "WAITING_CUSTOM_MSG":
            # EXACT FORMATTING SERIALIZER - ALL MEDIA TYPES
            msg_doc = {}
            fwd_data = ""
            if message.text:
                msg_doc = {"type": "text", "html": message.text.html}
            elif message.photo:
                msg_doc = {"type": "photo", "file_id": message.photo.file_id, "html": message.caption.html if message.caption else ""}
            elif message.video:
                msg_doc = {"type": "video", "file_id": message.video.file_id, "html": message.caption.html if message.caption else ""}
            elif message.sticker:
                msg_doc = {"type": "sticker", "file_id": message.sticker.file_id, "html": ""}
            elif message.voice:
                msg_doc = {"type": "voice", "file_id": message.voice.file_id, "html": message.caption.html if message.caption else ""}
            elif message.audio:
                msg_doc = {"type": "audio", "file_id": message.audio.file_id, "html": message.caption.html if message.caption else ""}
            elif message.document:
                msg_doc = {"type": "document", "file_id": message.document.file_id, "html": message.caption.html if message.caption else ""}
            elif message.animation:
                msg_doc = {"type": "animation", "file_id": message.animation.file_id, "html": message.caption.html if message.caption else ""}
            elif message.video_note:
                msg_doc = {"type": "video_note", "file_id": message.video_note.file_id, "html": ""}
            else:
                USER_STATES.pop(user_id, None)
                return await api_send(user_id, f"{E_WRN} <i>Unsupported format. Send text or any media type.</i>")
                
            await users_col.update_one({"_id": user_id}, {"$set": {"custom_msg_data": msg_doc}})
            USER_STATES.pop(user_id, None)
            
            text = f"{E_PLAY} <i><b>Campaign Launch Terminal</b>\n\n{E_CHK} <b>Exact {msg_doc['type'].upper()} content saved!</b>\n<i>Full formatting, custom emojis, and media preserved.</i>\n\nChoose your audience below:</i>"
            btn = {"inline_keyboard": [
                [ibtn("Target Channel Join Requests", "tgt_own", style="primary", icon=BTN_EMOJIS["target"]), ibtn("Target Dialog DMs", "tgt_alt_dms", style="success", icon=BTN_EMOJIS["user"])], 
                [ibtn("Target Admin Free Channel", "tgt_free", style="primary", icon=BTN_EMOJIS["target"])], 
                [ibtn("Update Content", "set_msg", style="danger", icon=BTN_EMOJIS["setting"]), ibtn("Set Public Post", "set_fwd_msg", style="danger", icon=BTN_EMOJIS["globe"])], 
                [ibtn("Back to Main Menu", "back_home", style="primary", icon=BTN_EMOJIS["home"])]
            ]}
            await api_send(user_id, text, kb=btn)

        elif state == "WAITING_FWD_LINK":
            msg_disp = ""
            saved = False
            if message.forward_from_chat and getattr(message.forward_from_chat, 'username', None):
                ch_username = message.forward_from_chat.username
                msg_id = message.forward_from_message_id
                await users_col.update_one({"_id": user_id}, {"$set": {"custom_msg_data": {"type": "forward_link", "html": ""}, "custom_msg_fwd": f"{ch_username}|{msg_id}"}})
                msg_disp = f"[Forwarded Post] @{ch_username}/{msg_id}"
                saved = True
                
            elif message.text and "t.me/" in message.text:
                link = message.text.strip()
                try:
                    parts = link.split("/")
                    msg_id = parts[-1]
                    ch_username = parts[-2]
                    await users_col.update_one({"_id": user_id}, {"$set": {"custom_msg_data": {"type": "forward_link", "html": ""}, "custom_msg_fwd": f"{ch_username}|{msg_id}"}})
                    msg_disp = f"[Forward Link] {ch_username}/{msg_id}"
                    saved = True
                except Exception:
                    USER_STATES.pop(user_id, None)
                    return await api_send(user_id, f"{E_WRN} <i>Invalid link format. Extraction aborted.</i>")
                    
            elif message.text:
                msg_doc = {"type": "text", "html": message.text.html}
                await users_col.update_one({"_id": user_id}, {"$set": {"custom_msg_data": msg_doc}})
                msg_disp = html.escape(message.text[:60])
                saved = True
                
            elif message.photo:
                msg_doc = {"type": "photo", "file_id": message.photo.file_id, "html": message.caption.html if message.caption else ""}
                await users_col.update_one({"_id": user_id}, {"$set": {"custom_msg_data": msg_doc}})
                msg_disp = "[Photo Message]"
                saved = True
            elif message.video:
                msg_doc = {"type": "video", "file_id": message.video.file_id, "html": message.caption.html if message.caption else ""}
                await users_col.update_one({"_id": user_id}, {"$set": {"custom_msg_data": msg_doc}})
                msg_disp = "[Video Message]"
                saved = True
            elif message.sticker:
                msg_doc = {"type": "sticker", "file_id": message.sticker.file_id, "html": ""}
                await users_col.update_one({"_id": user_id}, {"$set": {"custom_msg_data": msg_doc}})
                msg_disp = "[Sticker Message]"
                saved = True
                
            if not saved:
                USER_STATES.pop(user_id, None)
                return await api_send(user_id, f"{E_WRN} <i>Invalid format. Send text, media, link, or forward a post.</i>")
                
            USER_STATES.pop(user_id, None)
            text = f"{E_PLAY} <i><b>Campaign Launch Terminal</b>\n\n{E_GLOBE} <b>Queued Content:</b>\n<code>{msg_disp}</code>\n\nChoose your audience or update your message below:</i>"
            btn = {"inline_keyboard": [
                [ibtn("Target Channel Join Requests", "tgt_own", style="primary", icon=BTN_EMOJIS["target"]), ibtn("Target Dialog DMs", "tgt_alt_dms", style="success", icon=BTN_EMOJIS["user"])], 
                [ibtn("Target Admin Free Channel", "tgt_free", style="primary", icon=BTN_EMOJIS["target"])], 
                [ibtn("Update Content", "set_msg", style="danger", icon=BTN_EMOJIS["setting"]), ibtn("Set Public Post", "set_fwd_msg", style="danger", icon=BTN_EMOJIS["globe"])], 
                [ibtn("Back to Main Menu", "back_home", style="primary", icon=BTN_EMOJIS["home"])]
            ]}
            await api_send(user_id, text, kb=btn)

        elif state == "WAITING_FAMPAY_UTR":
            utr = message.text.strip() if message.text else ""
            if not utr or len(utr) < 5 or not utr.isalnum(): 
                USER_STATES.pop(user_id, None)
                return await api_send(user_id, f"{E_WRN} <i>Invalid UTR/Transaction reference. Please try again.</i>")
            
            user_state_data = USER_STATES.pop(user_id, {})
            days = user_state_data.get("days", 1)
            price = float(user_state_data.get("price", 0.0))
            
            msg = await api_send(user_id, f"{E_SYNC} <i><b>Verifying bank records for ID: {utr}...</b></i>")
            paid_amount = await asyncio.to_thread(check_payment_in_gmail, utr)
            
            if paid_amount and paid_amount >= price:
                u = await get_user(user_id); current_time = time.time()
                today_date = get_ist_str("%Y-%m-%d")
                
                nex = max(current_time, u.get("premium_expiry", 0)) + (days * 86400)
                await users_col.update_one({"_id": user_id}, {"$set": {"premium_expiry": nex}})
                exp_str = get_ist_ts_str(nex)
                await api_edit(msg.chat.id, msg.id, f"{E_DIA} <i><b>Payment Verified Automatically! ({days} Days)</b>\n\n{E_CHK} Reference ID: <code>{utr}</code>\n{E_MONEY} Amount: ₹{paid_amount}\n\n{E_GIFT} <b>VIP Status Valid Until:</b>\n{E_CAL} <b>{exp_str}</b></i>")
                try: await api_send(ADMINS[0], f"{E_DIA} <i><b>Auto-Approval Log</b>\n{E_PROF} User ID: <code>{user_id}</code>\n{E_MONEY} Paid: ₹{paid_amount} ({days} Days)\n{E_ID} Ref: <code>{utr}</code></i>")
                except: pass
                await settings_col.update_one({"_id": "config"}, {"$inc": {"total_sales_inr": paid_amount, f"sales_history.{today_date}": paid_amount}})
            else:
                await api_edit(msg.chat.id, msg.id, f"{E_WRN} <i><b>Payment Record Not Found!</b>\nCould not verify ₹{price} for ID <code>{utr}</code>. If just transferred, wait 1-2 minutes and re-submit.</i>")

        elif state == "WAITING_MANUAL_UTR":
            utr = message.text.strip() if message.text else ""
            if not utr or len(utr) < 5:
                USER_STATES.pop(user_id, None)
                return await api_send(user_id, f"{E_WRN} <i>Invalid reference ID. Process cancelled.</i>")
            
            USER_STATES[user_id]["utr"] = utr
            USER_STATES[user_id]["state"] = "WAITING_MANUAL_SS"
            await api_send(user_id, f"{E_STAT} <i><b>Step 2/2:</b> Please send the <b>Payment Screenshot</b>:</i>")

        elif state == "WAITING_MANUAL_SS":
            if not message.photo: 
                USER_STATES.pop(user_id, None)
                return await api_send(user_id, f"{E_WRN} <i>Please attach a valid photo screenshot. Process aborted.</i>")
                
            user_state_data = USER_STATES.pop(user_id, {})
            days = user_state_data.get("days", 1)
            utr = user_state_data.get("utr", "Unknown")
            
            btn = {"inline_keyboard": [[ibtn("Approve", f"manapp_{user_id}_{days}", style="success", icon=BTN_EMOJIS["tick"]), ibtn("Reject", f"manrej_{user_id}_{days}", style="danger", icon=BTN_EMOJIS["cross"])]]}
            for admin in ADMINS:
                try: await api_send(admin, f"{E_MONEY} <i><b>Manual Payment Pending Verification!</b>\n{E_PROF} User ID: <code>{user_id}</code>\nName: {message.from_user.first_name}\n{E_CAL} Duration: {days} Days\n{E_CHK} UTR/Hash: <code>{utr}</code></i>", kb=btn, photo=message.photo.file_id)
                except: pass
            await api_send(user_id, f"{E_WAIT} <i><b>Submission Received!</b> Sent to admins for prompt review.</i>")

        elif state == "WAITING_PHONE":
            phone = message.text.replace(" ", "") if message.text else ""
            if not phone:
                USER_STATES.pop(user_id, None)
                return await api_send(user_id, f"{E_WRN} <i>Invalid phone number. Please try again.</i>")
            
            if phone.isdigit() and not phone.startswith("+"):
                phone = "+" + phone
                
            msg = await api_send(user_id, f"{E_SYNC} <i>Connecting to Telegram cloud servers...</i>")
            temp_client = Client(f"session_{user_id}", api_id=API_ID, api_hash=API_HASH, in_memory=True)
            await temp_client.connect()
            try:
                code_info = await temp_client.send_code(phone)
                USER_STATES[user_id].update({"state": "WAITING_OTP", "phone": phone, "phone_code_hash": code_info.phone_code_hash, "temp_client": temp_client})
                await api_edit(msg.chat.id, msg.id, f"{E_STAT} <i><b>OTP Code Dispatched!</b>\n\n{E_CHK} <b>Send with spaces between digits:</b> <code>1 2 3 4 5</code></i>")
            except Exception as e_phone: 
                USER_STATES.pop(user_id, None)
                await api_edit(msg.chat.id, msg.id, f"{E_WRN} <i><b>Error:</b> {e_phone}</i>")
                try: await temp_client.disconnect()
                except: pass

        elif state == "WAITING_OTP":
            otp = message.text.replace(" ", "") if message.text else ""
            if not otp:
                USER_STATES.pop(user_id, None)
                return await api_send(user_id, f"{E_WRN} <i>Invalid OTP. Please try again.</i>")
                
            user_state_data = USER_STATES.get(user_id, {})
            temp_client = user_state_data.get("temp_client")
            if not temp_client:
                USER_STATES.pop(user_id, None)
                return await api_send(user_id, f"{E_WRN} <i>Session expired. Please start over.</i>")
                
            msg = await api_send(user_id, f"{E_SYNC} <i>Authenticating OTP code...</i>")
            try:
                await temp_client.sign_in(user_state_data.get("phone"), user_state_data.get("phone_code_hash"), otp)
                ss = await temp_client.export_session_string()
                await users_col.update_one({"_id": user_id}, {"$push": {"sessions": ss}})
                await api_edit(msg.chat.id, msg.id, f"{E_CHK} <i><b>Session Connected Successfully!</b>\nRedirecting to Menu...</i>")
                await temp_client.disconnect(); USER_STATES.pop(user_id, None)
                
                await asyncio.sleep(1.5); config = await settings_col.find_one({"_id": "config"})
                first_name = html.escape(message.from_user.first_name if message.from_user else "User")
                text, btn = await get_home_menu(user_id, first_name, config)
                await api_send(user_id, text, kb=btn)
            except SessionPasswordNeeded:
                USER_STATES[user_id]["state"] = "WAITING_PASSWORD"
                await api_edit(msg.chat.id, msg.id, f"{E_SHD} <i><b>Two-Step Verification (2FA) Password Required:</b></i>")
            except Exception as e_otp: 
                USER_STATES.pop(user_id, None)
                await api_edit(msg.chat.id, msg.id, f"{E_WRN} <i><b>Error:</b> {e_otp}</i>")
                try: await temp_client.disconnect()
                except: pass
                
        elif state == "WAITING_PASSWORD":
            user_state_data = USER_STATES.get(user_id, {})
            temp_client = user_state_data.get("temp_client")
            if not temp_client:
                USER_STATES.pop(user_id, None)
                return
                
            msg = await api_send(user_id, f"{E_SYNC} <i>Verifying 2FA password...</i>")
            try:
                await temp_client.check_password(message.text)
                ss = await temp_client.export_session_string()
                await users_col.update_one({"_id": user_id}, {"$push": {"sessions": ss}})
                await api_edit(msg.chat.id, msg.id, f"{E_CHK} <i><b>Session Connected Successfully!</b>\nRedirecting to Menu...</i>")
                await temp_client.disconnect(); USER_STATES.pop(user_id, None)
                
                await asyncio.sleep(1.5); config = await settings_col.find_one({"_id": "config"})
                first_name = html.escape(message.from_user.first_name if message.from_user else "User")
                text, btn = await get_home_menu(user_id, first_name, config)
                await api_send(user_id, text, kb=btn)
            except Exception as e_pwd: 
                USER_STATES.pop(user_id, None)
                await api_edit(msg.chat.id, msg.id, f"{E_WRN} <i><b>Error:</b> {e_pwd}</i>")
                try: await temp_client.disconnect()
                except: pass
            
        elif state in ["WAITING_LINK", "WAITING_DM_LINK"]:
            msg = await api_send(user_id, f"{E_SYNC} <i>Analyzing channel parameters...</i>")
            user_data = await get_user(user_id); config = await settings_col.find_one({"_id": "config"})
            asyncio.create_task(check_and_show_stats(client, user_id, user_data, config, message.text.strip(), msg, save_new=(state=="WAITING_LINK")))

        elif state == "WAITING_LIMIT":
            if not message.text or not message.text.isdigit(): 
                USER_STATES.pop(user_id, None)
                return await api_send(user_id, f"{E_WRN} <i>Please provide a valid numeric value.</i>")
                
            USER_STATES[user_id]["limit"] = int(message.text); USER_STATES[user_id]["state"] = None
            btn = {"inline_keyboard": [[ibtn("All Audience", "flt_all", style="primary", icon=BTN_EMOJIS["user"])], [ibtn("Recently Online", "flt_recent", style="success", icon=BTN_EMOJIS["tick"])], [ibtn("Active Members", "flt_active", style="primary", icon=BTN_EMOJIS["user"])], [ibtn("VIP Premium Only", "flt_premium", style="danger", icon=BTN_EMOJIS["diamond"])]]}
            await api_send(user_id, f"{E_ADM} <i><b>Target Audience Filtering:</b>\nSelect user audience to engage:</i>", kb=btn)
            
    except Exception as e_state:
        USER_STATES.pop(user_id, None)
        await api_send(message.chat.id, f"{E_WRN} <i><b>Encountered Error:</b>\n<code>{html.escape(str(e_state))}</code></i>")

# ================= BIND HANDLERS =================
bot.add_handler(MessageHandler(start_cmd, filters.command("start") & filters.private))
bot.add_handler(MessageHandler(shortcut_cmds, filters.command(["buypremium", "massdm", "myaccount"]) & filters.private))
bot.add_handler(MessageHandler(check_total_public, filters.command(["total", "totaldms"]) & filters.private))
bot.add_handler(MessageHandler(admin_panel, filters.command("admin")))
bot.add_handler(MessageHandler(master_admin_cmds, filters.command(["gencode", "toggleauto", "reqall", "setfampay", "setmanual", "setcrypto", "setprice1d", "setprice3d", "setprice7d", "setprice1m", "setlogchannel", "setsuccesslog", "setleaderboard", "setfreechannel", "setfreetrial", "setldbtime", "setrefbonus", "setdelay", "ongoing", "sales", "giveprem", "removeprem", "maintenance"])))
bot.add_handler(MessageHandler(shared_admin_cmds, filters.command(["stats", "checkuser", "clearsession", "banuser", "unbanuser", "broadcast"])))
bot.add_handler(MessageHandler(route_reply_keyboard_button, filters.private & filters.text & filters.incoming), group=-1)
bot.add_handler(MessageHandler(handle_states, filters.private & filters.incoming), group=1)
bot.add_handler(CallbackQueryHandler(admin_manual_approve, filters.regex(r"^manapp_") | filters.regex(r"^manrej_")), group=1)
bot.add_handler(ChatJoinRequestHandler(handle_join_requests))

# ================= SYSTEM LAUNCHER =================
async def start_bot():
    print("===================================")
    await init_db()
    print("Database Initialized Successfully.")
    await bot.start()
    bot_info = await bot.get_me()
    print(f"BOT ONLINE: @{bot_info.username}")
    print("===================================")
    asyncio.create_task(auto_leaderboard_task())
    await idle()
    print("Shutting down bot...")
    await bot.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_bot())
