# -*- coding: utf-8 -*-
"""
Telegram File + Website Hosting Bot  (Termux ready)

Features
- Force channel join (error if not joined, "Joined" verify)
- Reply-keyboard menu (NOT inline) for main navigation
- Upload File  -> host a bot file (.py/.js/.sh) auto run
- Host Website -> upload ANY file; .zip auto-unzipped; site hosted; public link sent
- Check File / Files / Statistics / Bot Speed
- Profile (name, subscription status, usage)
- Buy Subscription (12day 39 / 1month 59 / 1year 99 / lifetime 199) editable by admin
  -> shows QR (set by admin) + UPI -> user sends UTR -> request to channel
  -> admin Accept/Reject -> subscription activated for chosen days
- Limits: normal user = 3 bots + 3 websites ; subscribed = unlimited (till expiry)
- /admin panel: channels, payment channel, prices, QR, folders, files block, stats
- Never sleeps: watchdog auto-restart + infinity polling
"""

import os
import re
import sys
import json
import time
import socket
import signal
import zipfile
import threading
import subprocess
import traceback

try:
    import telebot
    from telebot import types
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "pyTelegramBotAPI"])
    import telebot
    from telebot import types

# ======================= CONFIG =======================
BOT_TOKEN = "9053445412:AAEB-z2-_TrXQA9PQdNSGymWEogn2xGlnP0"
ADMIN_ID = 8601101339
UPI_ID = "Devendra3289@fam"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILES_DIR = os.path.join(BASE_DIR, "hosted_files")
SITES_DIR = os.path.join(BASE_DIR, "hosted_sites")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
USERS_FILE = os.path.join(BASE_DIR, "users.json")

for d in (FILES_DIR, SITES_DIR, LOGS_DIR):
    os.makedirs(d, exist_ok=True)

# ---- speed/connection tuning (safe) ----
from telebot import apihelper
apihelper.READ_TIMEOUT = 25
apihelper.CONNECT_TIMEOUT = 15
# keep-alive connection pool -> faster, without overriding telebot internals
try:
    apihelper.SESSION_TIME_TO_LIVE = 5 * 60
except Exception:
    pass

# process updates concurrently so one slow handler never blocks others
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML", threaded=True, num_threads=6)
START_TIME = time.time()

processes = {}          # bot filename -> Popen
websites = {}           # site name   -> {"server":Popen,"tunnel":Popen,"url":..,"port":..,"folder":..}
user_state = {}         # uid -> dict

FREE_BOTS = 3
FREE_SITES = 3
FREE_MAX_MB = 10        # normal user max file size
VIP_MAX_MB = 100        # subscribed/vip user max file size

PLAN_DAYS = {"12day": 12, "1month": 30, "1year": 365, "lifetime": None}
PLAN_LABEL = {"12day": "12 Days", "1month": "1 Month", "1year": "1 Year", "lifetime": "Lifetime"}

# ======================= FIREBASE (Realtime Database) =======================
try:
    import requests as _rq
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "requests"])
    import requests as _rq

FIREBASE_URL = "https://xhshsjsjs-f5ee7-default-rtdb.firebaseio.com"
FIREBASE_ENABLED = True
# optional DB secret/token for protected rules. Leave "" if rules are public (test mode).
FIREBASE_AUTH = ""

def _fb_url(node):
    u = f"{FIREBASE_URL}/{node}.json"
    if FIREBASE_AUTH:
        u += f"?auth={FIREBASE_AUTH}"
    return u

def fb_get(node):
    """Read a node. Data is stored as a JSON string under {'json': ...} to
    avoid Firebase key restrictions (dots, $, #, etc. in filenames)."""
    if not FIREBASE_ENABLED:
        return None
    try:
        r = _rq.get(_fb_url(node), timeout=15)
        if r.status_code == 200:
            val = r.json()
            if isinstance(val, dict) and "json" in val:
                try:
                    return json.loads(val["json"])
                except Exception:
                    return None
            return val  # legacy/plain
    except Exception as e:
        print("Firebase get error:", e)
    return None

def fb_put(node, data):
    if not FIREBASE_ENABLED:
        return False
    try:
        payload = {"json": json.dumps(data, ensure_ascii=False)}
        r = _rq.put(_fb_url(node), data=json.dumps(payload), timeout=20)
        return r.status_code == 200
    except Exception as e:
        print("Firebase put error:", e)
        return False

# ======================= STORAGE (Firebase + local backup) =======================
def _load(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default

def _save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# --- load: prefer Firebase, fall back to local file ---
def load_config_initial():
    fb = fb_get("config")
    if isinstance(fb, dict):
        return fb
    return _load(CONFIG_FILE, {})

def load_users_initial():
    fb = fb_get("users")
    if isinstance(fb, dict):
        return fb
    return _load(USERS_FILE, {})

config = load_config_initial()
config.setdefault("channels", [])
config.setdefault("folders", [])
config.setdefault("blocked", [])
config.setdefault("payment_channel", "")
config.setdefault("qr_file_id", "")
config.setdefault("prices", {"12day": 39, "1month": 59, "1year": 99, "lifetime": 199})
config.setdefault("welcome", {})   # {"type":"text/photo", "text":..., "file_id":...}
config.setdefault("ratings", {})   # {uid: stars(1-5)}
config.setdefault("env_vars", {})  # {filename: {KEY: VALUE}}
config.setdefault("site_meta", {}) # {sitename: {custom_domain, hits}}

users = load_users_initial()

def _fb_sync(node, data):
    # push to Firebase in background so saving never blocks the bot
    threading.Thread(target=fb_put, args=(node, data), daemon=True).start()

def save_config():
    _save(CONFIG_FILE, config)          # local backup
    _fb_sync("config", config)          # cloud (Firebase)

def save_users():
    _save(USERS_FILE, users)            # local backup
    _fb_sync("users", users)            # cloud (Firebase)

def get_user(uid, name=""):
    u = users.get(str(uid))
    if not u:
        u = {"name": name or "User", "sub_plan": None, "sub_expiry": 0,
             "bots": [], "sites": []}
        users[str(uid)] = u
        save_users()
    if name and u.get("name") != name:
        u["name"] = name
        save_users()
    return u

# ======================= HELPERS =======================
def is_admin(uid):
    return uid == ADMIN_ID

def human_uptime():
    s = int(time.time() - START_TIME)
    d, s = divmod(s, 86400); h, s = divmod(s, 3600); m, s = divmod(s, 60)
    return f"{d}d {h}h {m}m {s}s"

def log_path(fname): return os.path.join(LOGS_DIR, fname + ".log")
def file_path(fname): return os.path.join(FILES_DIR, fname)

def list_files():
    return sorted([f for f in os.listdir(FILES_DIR) if os.path.isfile(file_path(f))]) if os.path.exists(FILES_DIR) else []

def has_active_sub(uid):
    u = get_user(uid)
    if u.get("sub_plan") == "lifetime":
        return True
    exp = u.get("sub_expiry", 0)
    return bool(exp) and exp > time.time()

def sub_text(uid):
    u = get_user(uid)
    if u.get("sub_plan") == "lifetime":
        return "♾ Lifetime (Active)"
    exp = u.get("sub_expiry", 0)
    if exp and exp > time.time():
        days = int((exp - time.time()) / 86400) + 1
        return f"✅ {PLAN_LABEL.get(u.get('sub_plan'),'Premium')} — {days} day left"
    return "❌ No active subscription (Free)"

# ======================= CHANNEL JOIN CHECK (cached) =======================
# Calling Telegram's get_chat_member on every tap is slow. We cache the
# "fully joined" result per-user for a short time so most taps are instant.
_join_cache = {}          # uid -> (expiry_timestamp, True)
JOIN_CACHE_TTL = 600      # seconds a verified user stays cached

def norm_channel(ch):
    """Return dict {name, url, ref}. Supports old string format too."""
    if isinstance(ch, dict):
        return ch
    # old format: plain "@username"
    u = str(ch)
    return {"name": u, "url": f"https://t.me/{u.lstrip('@')}", "ref": u}

def get_channels():
    return [norm_channel(c) for c in config.get("channels", [])]

def parse_channel_input(line):
    """
    Parse a line:  button name || channel link  [|| chat_id]
    - Public channel: link like https://t.me/mychannel  -> ref = @mychannel (auto)
    - Private channel: link like https://t.me/+abc...    -> ref = chat_id (3rd part needed)
    Returns dict or (None, error_message)
    """
    parts = [p.strip() for p in line.split("||")]
    if len(parts) < 2:
        return None, "Format galat. Use:\n<code>Button Name || channel link [|| chat_id]</code>"
    name = parts[0]
    url = parts[1].strip()
    ref = parts[2].strip() if len(parts) >= 3 and parts[2].strip() else None

    # fix unicode minus / spaces in chat_id
    if ref:
        ref = ref.replace("\u2212", "-").replace(" ", "")

    if not ref:
        # public channel? try to auto-derive @username from the link
        m = re.search(r"t\.me/([A-Za-z0-9_]{4,})/?$", url)
        if m and "+" not in url and "joinchat" not in url.lower() and m.group(1).lower() != "c":
            ref = "@" + m.group(1)
        else:
            # private invite link -> need chat_id
            return None, ("🔒 Yeh private channel lag raha hai. Iske liye <b>chat_id</b> bhi dein:\n"
                          "<code>Button Name || invite link || -100xxxxxxxxxx</code>\n\n"
                          "💡 chat_id paane ke liye: bot ko us channel me <b>admin</b> banayein, "
                          "phir us channel se koi message is bot ko <b>forward</b> karein.")

    # normalize numeric id (supports -100..., plain digits)
    cleaned = ref.lstrip("-")
    if cleaned.isdigit():
        ref = int(ref)
        # private channel ids must be like -100xxxxxxxxxx
        if ref > 0:
            ref = int("-100" + str(ref))
    elif not str(ref).startswith("@"):
        ref = "@" + str(ref)

    return {"name": name, "url": url, "ref": ref}, None

def check_joined(uid, force=False):
    chans = get_channels()
    if not chans:
        return []
    if not force:
        c = _join_cache.get(uid)
        if c and c[0] > time.time():
            return []
    not_joined = []
    for ch in chans:
        try:
            member = bot.get_chat_member(ch["ref"], uid)
            if member.status in ("left", "kicked"):
                not_joined.append(ch)
        except Exception:
            not_joined.append(ch)
    if not not_joined:
        _join_cache[uid] = (time.time() + JOIN_CACHE_TTL, True)
    else:
        _join_cache.pop(uid, None)
    return not_joined

def send_join_required(chat_id, channels):
    kb = types.InlineKeyboardMarkup()
    for ch in channels:
        ch = norm_channel(ch)
        kb.add(types.InlineKeyboardButton(f"📢 {ch['name']}", url=ch["url"]))
    kb.add(types.InlineKeyboardButton("✅ Joined", callback_data="joined"))
    bot.send_message(chat_id,
        "❌ <b>Access Denied</b>\n\nBot use karne ke liye pehle neeche diye channel(s) join "
        "karein, phir <b>Joined</b> button dabayein.", reply_markup=kb)

# ======================= REPLY KEYBOARD MENU =======================
BTN_UPLOAD = "📤 Upload File"
BTN_WEBSITE = "🌐 Host Website"
BTN_CHECK = "📂 Check File"
BTN_FILES = "🗂 Files"
BTN_PROFILE = "👤 Profile"
BTN_BUY = "💎 Buy Subscription"
BTN_STATS = "📊 Statistics"
BTN_SPEED = "⚡ Bot Speed"
BTN_RATE = "⭐ Rate Us"

def main_menu_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(BTN_UPLOAD, BTN_WEBSITE)
    kb.row(BTN_CHECK, BTN_FILES)
    kb.row(BTN_PROFILE, BTN_BUY)
    kb.row(BTN_STATS, BTN_SPEED)
    kb.row(BTN_RATE)
    return kb

# ======================= RATING SYSTEM =======================
def rating_summary():
    r = config.get("ratings", {})
    total = len(r)
    if total == 0:
        return 0, 0.0
    avg = sum(int(v) for v in r.values()) / total
    return total, avg

def rate_kb():
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("⭐", callback_data="rate:1"),
        types.InlineKeyboardButton("⭐⭐", callback_data="rate:2"),
        types.InlineKeyboardButton("⭐⭐⭐", callback_data="rate:3"),
    )
    kb.row(
        types.InlineKeyboardButton("⭐⭐⭐⭐", callback_data="rate:4"),
        types.InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data="rate:5"),
    )
    return kb

def send_rating(chat_id, uid):
    total, avg = rating_summary()
    mine = config.get("ratings", {}).get(str(uid))
    stars = "★" * int(round(avg)) + "☆" * (5 - int(round(avg)))
    txt = (f"⭐ <b>Rate Us</b>\n\n"
           f"📊 Average Rating: <b>{avg:.1f} / 5</b>  {stars}\n"
           f"👥 Total Ratings: <b>{total}</b>\n")
    if mine:
        txt += f"\n✅ Aapne diya: {'⭐'*int(mine)} ({mine}/5)\nDobara select karke change kar sakte hain."
    else:
        txt += "\nNeeche se apni rating select karein 👇"
    bot.send_message(chat_id, txt, reply_markup=rate_kb())

def send_main_menu(chat_id):
    bot.send_message(chat_id, "🏠 <b>Main Menu</b>\nNeeche se option chunein 👇",
                     reply_markup=main_menu_kb())

# ======================= PROCESS CONTROL (BOTS) =======================
def run_file(fname):
    path = file_path(fname)
    if not os.path.exists(path):
        return False, "File not found"
    if fname in config.get("blocked", []):
        return False, "File admin ne block ki hai"
    stop_file(fname)
    ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
    if ext == "py":   cmd = [sys.executable, "-u", path]
    elif ext == "js": cmd = ["node", path]
    elif ext == "sh": cmd = ["bash", path]
    else:             cmd = [sys.executable, "-u", path]
    try:
        logf = open(log_path(fname), "w", encoding="utf-8", errors="ignore")
        env = os.environ.copy()
        env.update({str(k): str(v) for k, v in config.get("env_vars", {}).get(fname, {}).items()})
        p = subprocess.Popen(cmd, stdout=logf, stderr=subprocess.STDOUT,
                             cwd=FILES_DIR, start_new_session=True, env=env)
        processes[fname] = p
        return True, "Started (PID %d)" % p.pid
    except Exception as e:
        return False, str(e)

def stop_file(fname):
    p = processes.get(fname)
    if p and p.poll() is None:
        try: os.killpg(os.getpgid(p.pid), signal.SIGTERM)
        except Exception:
            try: p.terminate()
            except Exception: pass
        time.sleep(0.4)
    processes.pop(fname, None)

def is_running(fname):
    p = processes.get(fname)
    return p is not None and p.poll() is None

# ======================= WEBSITE HOSTING =======================
def free_port():
    s = socket.socket(); s.bind(("", 0)); port = s.getsockname()[1]; s.close()
    return port

def find_site_root(folder):
    """Return folder that contains index.html (search 2 levels)."""
    if os.path.exists(os.path.join(folder, "index.html")):
        return folder
    for entry in os.listdir(folder):
        sub = os.path.join(folder, entry)
        if os.path.isdir(sub) and os.path.exists(os.path.join(sub, "index.html")):
            return sub
    return folder

def start_tunnel(port):
    """Try cloudflared quick tunnel, else localtunnel. Return (proc, url)."""
    # cloudflared
    try:
        p = subprocess.Popen(["cloudflared", "tunnel", "--url", f"http://localhost:{port}"],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, start_new_session=True)
        url = _read_url(p, r"https://[-a-z0-9]+\.trycloudflare\.com", 35)
        if url:
            return p, url
        try: os.killpg(os.getpgid(p.pid), signal.SIGTERM)
        except Exception: pass
    except FileNotFoundError:
        pass
    # localtunnel via npx
    try:
        p = subprocess.Popen(["npx", "localtunnel", "--port", str(port)],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, start_new_session=True)
        url = _read_url(p, r"https://[-a-z0-9]+\.loca\.lt", 40)
        if url:
            return p, url
        try: os.killpg(os.getpgid(p.pid), signal.SIGTERM)
        except Exception: pass
    except FileNotFoundError:
        pass
    return None, None

def _read_url(proc, pattern, timeout):
    result = {"url": None}
    def reader():
        for line in proc.stdout:
            m = re.search(pattern, line)
            if m:
                result["url"] = m.group(0); break
    t = threading.Thread(target=reader, daemon=True); t.start()
    t.join(timeout)
    return result["url"]

def start_website(sitename):
    info = websites.get(sitename)
    if not info:
        return False, "Site data missing"
    folder = info["folder"]
    root = find_site_root(folder)
    port = free_port()
    server = subprocess.Popen([sys.executable, "-m", "http.server", str(port),
                              "--directory", root],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
    tunnel, url = start_tunnel(port)
    info.update({"server": server, "tunnel": tunnel, "port": port, "url": url})
    if not url:
        # local fallback url
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            ip = "127.0.0.1"
        info["url"] = f"http://{ip}:{port}"
        return True, info["url"] + "  (local only — cloudflared/localtunnel install karein for public link)"
    return True, url

def stop_website(sitename):
    info = websites.get(sitename)
    if not info: return
    for key in ("server", "tunnel"):
        p = info.get(key)
        if p and p.poll() is None:
            try: os.killpg(os.getpgid(p.pid), signal.SIGTERM)
            except Exception:
                try: p.terminate()
                except Exception: pass
    info["server"] = None; info["tunnel"] = None; info["url"] = None

def site_running(sitename):
    info = websites.get(sitename)
    return bool(info and info.get("server") and info["server"].poll() is None)

# ======================= WATCHDOG =======================
def watchdog():
    while True:
        try:
            for fname in list_files():
                if fname in config.get("blocked", []):
                    continue
                p = processes.get(fname)
                if p is not None and p.poll() is not None:
                    run_file(fname)
            for sn, info in list(websites.items()):
                if info.get("server") and info["server"].poll() is not None:
                    start_website(sn)
        except Exception:
            pass
        time.sleep(15)

# ======================= COMMANDS =======================
@bot.message_handler(commands=["start"])
def cmd_start(m):
    uid = m.from_user.id
    get_user(uid, m.from_user.first_name or "User")
    nj = check_joined(uid)
    if nj:
        send_join_required(m.chat.id, nj); return
    send_welcome(m.chat.id, m.from_user.first_name)
    send_main_menu(m.chat.id)

def send_welcome(chat_id, name=""):
    """Send admin-set welcome (supports premium emoji/photo/text), else default."""
    w = config.get("welcome") or {}
    try:
        if w.get("type") == "copy" and w.get("from_chat") and w.get("msg_id"):
            # copy_message preserves premium emoji, formatting, media, etc.
            bot.copy_message(chat_id, w["from_chat"], w["msg_id"])
            return
        if w.get("type") == "photo" and w.get("file_id"):
            bot.send_photo(chat_id, w["file_id"], caption=(w.get("text") or "").replace("{name}", name or "User"))
            return
        if w.get("type") == "text" and w.get("text"):
            bot.send_message(chat_id, w["text"].replace("{name}", name or "User"))
            return
    except Exception:
        pass
    bot.send_message(chat_id, f"👋 Welcome <b>{name or 'User'}</b>!")

@bot.message_handler(commands=["admin"])
def cmd_admin(m):
    if not is_admin(m.from_user.id):
        bot.reply_to(m, "⛔ Sirf admin hi yeh command use kar sakte hain."); return
    user_state.pop(m.from_user.id, None)  # cancel any pending action
    send_admin_panel(m.chat.id)

# ---- Universal catcher for admin Set-Welcome / Broadcast (any content type) ----
ALL_CONTENT = ["text", "photo", "video", "document", "audio", "voice",
               "video_note", "sticker", "animation"]

@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and
                     user_state.get(m.from_user.id, {}).get("action") in ("set_welcome", "broadcast"),
                     content_types=ALL_CONTENT)
def admin_capture(m):
    uid = m.from_user.id
    act = user_state.get(uid, {}).get("action")
    user_state.pop(uid, None)

    if act == "set_welcome":
        # store as a copyable message -> keeps premium emoji, media, formatting
        config["welcome"] = {"type": "copy", "from_chat": m.chat.id, "msg_id": m.message_id}
        save_config()
        bot.reply_to(m, "✅ Welcome message set ho gaya! Preview:")
        send_welcome(m.chat.id, m.from_user.first_name)
        send_admin_panel(m.chat.id)
        return

    if act == "broadcast":
        do_broadcast(m)
        return

def do_broadcast(m):
    sent = 0; failed = 0
    ids = list(users.keys())
    bot.send_message(m.chat.id, f"📢 Broadcasting to {len(ids)} users...")
    for sid in ids:
        try:
            target = int(sid)
            # copy_message handles ALL types (text/photo/video/forward/etc.) cleanly
            bot.copy_message(target, m.chat.id, m.message_id)
            sent += 1
        except Exception:
            failed += 1
        time.sleep(0.05)  # avoid Telegram flood limits
    bot.send_message(m.chat.id, f"✅ <b>Broadcast complete!</b>\n\n📤 Sent: {sent}\n❌ Failed: {failed}")

def do_install_module(chat_id, mods):
    bot.send_message(chat_id, f"📦 Installing: <code>{telebot.util.escape(' '.join(mods))}</code> ...\nPlease wait ⏳")
    try:
        proc = subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade"] + mods,
                             capture_output=True, text=True, timeout=600)
        out = (proc.stdout or "") + "\n" + (proc.stderr or "")
        out = out.strip()[-3500:] or "—"
        ok = proc.returncode == 0
        head = "✅ <b>Install Successful!</b>" if ok else "❌ <b>Install Failed</b>"
        bot.send_message(chat_id, f"{head}\n\n<pre>{telebot.util.escape(out)}</pre>")
    except subprocess.TimeoutExpired:
        bot.send_message(chat_id, "❌ Timeout — install bahut lamba ho gaya.")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error: {telebot.util.escape(str(e))}")

# ---- Admin forwards a channel message -> bot replies with chat_id (for private channels) ----
def _forwarded_chat(m):
    ch = getattr(m, "forward_from_chat", None)
    if ch is not None:
        return ch
    origin = getattr(m, "forward_origin", None)
    if origin is not None:
        return getattr(origin, "chat", None)
    return None

@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and
                     _forwarded_chat(m) is not None and
                     user_state.get(m.from_user.id, {}).get("action") not in ("set_welcome", "broadcast"),
                     content_types=ALL_CONTENT)
def forward_chatid(m):
    ch = _forwarded_chat(m)
    if ch and getattr(ch, "type", "") in ("channel", "supergroup", "group"):
        title = getattr(ch, "title", None) or "Channel"
        uname = f"@{ch.username}" if getattr(ch, "username", None) else "— private —"
        bot.reply_to(m,
            f"📡 <b>{title}</b>\n\n🆔 chat_id: <code>{ch.id}</code>\n🔗 username: {uname}\n\n"
            f"💡 Private channel add karne ke liye:\n"
            f"<code>Button Name || invite link || {ch.id}</code>")

# ======================= ADMIN PANEL =======================
def admin_kb():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton("➕ Add Channel", callback_data="a_addch"),
           types.InlineKeyboardButton("➖ Remove Channel", callback_data="a_delch"))
    kb.add(types.InlineKeyboardButton("📨 Set Payment Channel", callback_data="a_setpaych"),
           types.InlineKeyboardButton("🖼 Set QR", callback_data="a_setqr"))
    kb.add(types.InlineKeyboardButton("💰 Edit Prices", callback_data="a_prices"),
           types.InlineKeyboardButton("📁 Add Folder", callback_data="a_addfolder"))
    kb.add(types.InlineKeyboardButton("🤖 Bots", callback_data="a_bots"),
           types.InlineKeyboardButton("🌐 Sites List", callback_data="a_sites"))
    kb.add(types.InlineKeyboardButton("🗂 Files List", callback_data="a_files"),
           types.InlineKeyboardButton("📦 Install Module", callback_data="a_module"))
    kb.add(types.InlineKeyboardButton("⛔ Block File", callback_data="a_block"),
           types.InlineKeyboardButton("▶️ Unblock File", callback_data="a_unblock"))
    kb.add(types.InlineKeyboardButton("🎁 Give Subscription", callback_data="a_givesub"),
           types.InlineKeyboardButton("🚫 Remove Subscription", callback_data="a_remsub"))
    kb.add(types.InlineKeyboardButton("👋 Set Welcome", callback_data="a_setwelcome"),
           types.InlineKeyboardButton("📢 Broadcast", callback_data="a_broadcast"))
    kb.add(types.InlineKeyboardButton("📊 Server Stats", callback_data="a_stats"))
    return kb

def send_admin_panel(chat_id, edit=None):
    chs = "\n".join(f"• {c['name']}" for c in get_channels()) or "— none —"
    pr = config["prices"]
    txt = (f"🔧 <b>Admin Panel</b>\n\n"
           f"📢 Force Channels:\n{chs}\n\n"
           f"📨 Payment Channel: {config['payment_channel'] or '— not set —'}\n"
           f"🖼 QR: {'✅ set' if config['qr_file_id'] else '❌ not set'}\n\n"
           f"💰 Prices: 12d ₹{pr['12day']} | 1m ₹{pr['1month']} | "
           f"1y ₹{pr['1year']} | life ₹{pr['lifetime']}\n\n"
           f"🗂 Files: {len(list_files())} | 🌐 Sites: {len(websites)} | "
           f"⛔ Blocked: {len(config['blocked'])}")
    if edit:
        try: bot.edit_message_text(txt, chat_id, edit, reply_markup=admin_kb()); return
        except Exception: pass
    bot.send_message(chat_id, txt, reply_markup=admin_kb())

# ======================= SUBSCRIPTION UI =======================
def buy_kb():
    pr = config["prices"]
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton(f"🗓 12 Days — ₹{pr['12day']}", callback_data="buy:12day"))
    kb.add(types.InlineKeyboardButton(f"🗓 1 Month — ₹{pr['1month']}", callback_data="buy:1month"))
    kb.add(types.InlineKeyboardButton(f"🗓 1 Year — ₹{pr['1year']}", callback_data="buy:1year"))
    kb.add(types.InlineKeyboardButton(f"♾ Lifetime — ₹{pr['lifetime']}", callback_data="buy:lifetime"))
    return kb

def send_buy(chat_id):
    txt = ("💎 <b>Buy Subscription</b>\n\n"
           "Subscription lene par aap <b>unlimited</b> bots & websites host kar sakte hain "
           "(jitne din ka plan, utne din tak).\n\nApna plan chunein 👇")
    bot.send_message(chat_id, txt, reply_markup=buy_kb())

def activate_sub(uid, plan):
    u = get_user(uid)
    days = PLAN_DAYS.get(plan)
    u["sub_plan"] = plan
    if days is None:
        u["sub_expiry"] = 0  # lifetime
    else:
        base = max(u.get("sub_expiry", 0), time.time())
        u["sub_expiry"] = base + days * 86400
    save_users()

# ======================= CALLBACKS =======================
@bot.callback_query_handler(func=lambda c: True)
def callbacks(c):
    uid = c.from_user.id
    data = c.data
    chat_id = c.message.chat.id
    msg_id = c.message.message_id

    # ---- payment approval (works inside channel) ----
    if data.startswith("pay_ok:") or data.startswith("pay_no:"):
        if not is_admin(uid):
            bot.answer_callback_query(c.id, "⛔ Sirf admin approve kar sakta hai", show_alert=True)
            return
        _, target, plan = data.split(":")
        target = int(target)
        if data.startswith("pay_ok:"):
            activate_sub(target, plan)
            bot.answer_callback_query(c.id, "✅ Approved")
            try:
                bot.edit_message_reply_markup(chat_id, msg_id, reply_markup=None)
                bot.edit_message_text(c.message.text + "\n\n✅ <b>APPROVED</b>", chat_id, msg_id)
            except Exception: pass
            try:
                bot.send_message(target, f"🎉 <b>Subscription Active!</b>\n\nPlan: {PLAN_LABEL[plan]}\n"
                                         f"Status: {sub_text(target)}\n\nAb aap unlimited host kar sakte hain.")
            except Exception: pass
        else:
            bot.answer_callback_query(c.id, "❌ Rejected")
            try:
                bot.edit_message_reply_markup(chat_id, msg_id, reply_markup=None)
                bot.edit_message_text(c.message.text + "\n\n❌ <b>REJECTED</b>", chat_id, msg_id)
            except Exception: pass
            try:
                bot.send_message(target, "❌ Aapka payment reject ho gaya. Sahi UTR ke saath dobara try karein ya admin se contact karein.")
            except Exception: pass
        return

    # ---- rating ----
    if data.startswith("rate:"):
        stars = data.split(":", 1)[1]
        config.setdefault("ratings", {})[str(uid)] = int(stars)
        save_config()
        total, avg = rating_summary()
        bot.answer_callback_query(c.id, f"✅ Thanks! Aapne {stars}⭐ diya.", show_alert=True)
        try:
            mine = config["ratings"][str(uid)]
            st = "★" * int(round(avg)) + "☆" * (5 - int(round(avg)))
            txt = (f"⭐ <b>Rate Us</b>\n\n"
                   f"📊 Average Rating: <b>{avg:.1f} / 5</b>  {st}\n"
                   f"👥 Total Ratings: <b>{total}</b>\n\n"
                   f"✅ Aapne diya: {'⭐'*int(mine)} ({mine}/5)\nDobara select karke change kar sakte hain.")
            bot.edit_message_text(txt, chat_id, msg_id, reply_markup=rate_kb())
        except Exception:
            pass
        return

    # ---- joined verify ----
    if data == "joined":
        nj = check_joined(uid, force=True)
        if nj:
            bot.answer_callback_query(c.id, "❌ Aapne abhi tak join nahi kiya!", show_alert=True); return
        bot.answer_callback_query(c.id, "✅ Verified!")
        try: bot.delete_message(chat_id, msg_id)
        except Exception: pass
        send_main_menu(chat_id)
        return

    # everyone else must be joined
    nj = check_joined(uid)
    if nj and not is_admin(uid):
        bot.answer_callback_query(c.id, "Pehle channel join karein!", show_alert=True)
        send_join_required(chat_id, nj); return

    # ---- buy plan selected ----
    if data.startswith("buy:"):
        plan = data.split(":", 1)[1]
        bot.answer_callback_query(c.id)
        price = config["prices"][plan]
        user_state[uid] = {"action": "await_utr", "plan": plan}
        cap = (f"💳 <b>Payment</b>\n\nPlan: <b>{PLAN_LABEL[plan]}</b>\nAmount: <b>₹{price}</b>\n"
               f"UPI: <code>{UPI_ID}</code>\n\n"
               f"👉 Upar diye QR / UPI par payment karein.\n"
               f"👉 Payment ke baad <b>UTR / Transaction ID</b> yahin bhej dein.\n"
               f"Admin verify karne ke baad subscription active ho jayega.")
        if config.get("qr_file_id"):
            bot.send_photo(chat_id, config["qr_file_id"], caption=cap)
        else:
            bot.send_message(chat_id, cap + "\n\n⚠️ QR set nahi hai, UPI ID par pay karein.")
        return

    # ---- file actions ----
    if data.startswith("file:"):
        bot.answer_callback_query(c.id); show_file_detail(chat_id, msg_id, data.split(":",1)[1]); return
    if data.startswith("get:"):
        fname = data.split(":",1)[1]; bot.answer_callback_query(c.id, "Sending...")
        try:
            with open(file_path(fname), "rb") as f: bot.send_document(chat_id, f, caption=f"🗂 {fname}")
        except Exception as e: bot.send_message(chat_id, f"❌ {e}")
        return
    if data.startswith("del:"):
        fname = data.split(":",1)[1]; stop_file(fname)
        for p in (file_path(fname), log_path(fname)):
            try: os.remove(p)
            except Exception: pass
        for u in users.values():
            if fname in u.get("bots", []): u["bots"].remove(fname)
        save_users()
        bot.answer_callback_query(c.id, "🗑 Deleted!"); show_files_list(chat_id, msg_id); return
    if data.startswith(("restart:", "start:")):
        fname = data.split(":",1)[1]; ok, msg = run_file(fname)
        bot.answer_callback_query(c.id, ("🔄 "+msg) if ok else ("❌ "+msg), show_alert=not ok)
        show_file_detail(chat_id, msg_id, fname); return
    if data.startswith("stop:"):
        fname = data.split(":",1)[1]; stop_file(fname)
        bot.answer_callback_query(c.id, "⏹ Stopped!"); show_file_detail(chat_id, msg_id, fname); return
    if data.startswith("log:"):
        fname = data.split(":",1)[1]; bot.answer_callback_query(c.id)
        text = ""
        if os.path.exists(log_path(fname)):
            with open(log_path(fname), "r", encoding="utf-8", errors="ignore") as f: text = f.read()[-3500:]
        bot.send_message(chat_id, f"📜 <b>Log: {fname}</b>\n\n<pre>{telebot.util.escape(text or '— empty —')}</pre>")
        return

    # ---- bot host: environment variables ----
    if data.startswith("env:"):
        fname = data.split(":",1)[1]; bot.answer_callback_query(c.id)
        ev = config.get("env_vars", {}).get(fname, {})
        cur = "\n".join(f"{k}={v}" for k, v in ev.items()) or "— none —"
        user_state[uid] = {"action": "set_env", "fname": fname}
        bot.send_message(chat_id,
            f"⚙️ <b>Environment Variables — {fname}</b>\n\nCurrent:\n<pre>{telebot.util.escape(cur)}</pre>\n\n"
            f"Naye variables bhejein (har line me <code>KEY=VALUE</code>).\n"
            f"Yeh file run hote waqt environment me set honge.\n"
            f"❌ Clear karne ke liye <code>clear</code> bhejein.")
        return

    # ---- bot host: install requirements ----
    if data.startswith("req:"):
        fname = data.split(":",1)[1]; bot.answer_callback_query(c.id, "Checking requirements...")
        threading.Thread(target=do_install_requirements, args=(chat_id, fname), daemon=True).start()
        return

    # ---- edit file ----
    if data.startswith("edit:"):
        fname = data.split(":",1)[1]; bot.answer_callback_query(c.id)
        try:
            with open(file_path(fname), "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            bot.send_message(chat_id, f"❌ {e}"); return
        user_state[uid] = {"action": "edit_file", "fname": fname}
        preview = content[:3000]
        bot.send_message(chat_id,
            f"✏️ <b>Edit File — {fname}</b>\n\nCurrent content:\n<pre>{telebot.util.escape(preview)}</pre>\n\n"
            f"Naya pura content (text) bhejein — file replace ho jayegi aur restart hogi.\n"
            f"❌ Cancel: /admin ya menu button.")
        return

    # ---- file manager actions ----
    if data == "fm_uploadzip":
        bot.answer_callback_query(c.id)
        user_state[uid] = {"action": "fm_uploadzip"}
        bot.send_message(chat_id, "📥 <b>Upload ZIP</b>\n\nApni .zip file bhejein. Woh save hogi (Extract ZIP se kholi ja sakti hai).")
        return
    if data == "fm_extract":
        bot.answer_callback_query(c.id)
        zips = [f for f in fm_user_files(uid) if f.lower().endswith(".zip")]
        if not zips:
            bot.send_message(chat_id, "🗂 Koi .zip file nahi mili. Pehle 📥 Upload ZIP karein."); return
        kb = types.InlineKeyboardMarkup()
        for f in zips:
            kb.add(types.InlineKeyboardButton(f, callback_data=f"fmx:{f}"))
        bot.send_message(chat_id, "📦 Extract karne ke liye ZIP chunein:", reply_markup=kb)
        return
    if data == "fm_download":
        bot.answer_callback_query(c.id)
        fm_file_picker(chat_id, uid, "get", "📤 Download ke liye file chunein:")
        return
    if data == "fm_edit":
        bot.answer_callback_query(c.id)
        fm_file_picker(chat_id, uid, "edit", "✏️ Edit ke liye file chunein:")
        return
    if data == "fm_delete":
        bot.answer_callback_query(c.id)
        fm_file_picker(chat_id, uid, "del", "🗑 Delete ke liye file chunein:")
        return
    if data.startswith("fmx:"):
        fname = data.split(":",1)[1]; bot.answer_callback_query(c.id, "Extracting...")
        try:
            target = os.path.join(FILES_DIR, fname.rsplit(".",1)[0] + "_extracted")
            os.makedirs(target, exist_ok=True)
            with zipfile.ZipFile(file_path(fname)) as z:
                z.extractall(target)
            bot.send_message(chat_id, f"✅ <b>{fname}</b> extract ho gayi:\n<code>{target}</code>")
        except Exception as e:
            bot.send_message(chat_id, f"❌ Extract error: {e}")
        return

    # ---- website actions ----
    if data.startswith("site:"):
        bot.answer_callback_query(c.id); show_site_detail(chat_id, msg_id, data.split(":",1)[1]); return
    if data.startswith("sstart:") or data.startswith("srestart:"):
        sn = data.split(":",1)[1]; bot.answer_callback_query(c.id, "Starting tunnel...")
        ok, msg = start_website(sn)
        bot.send_message(chat_id, f"🌐 <b>{sn}</b>\n🔗 {msg}" if ok else f"❌ {msg}")
        show_site_detail(chat_id, msg_id, sn); return
    if data.startswith("sstop:"):
        sn = data.split(":",1)[1]; stop_website(sn)
        bot.answer_callback_query(c.id, "⏹ Stopped!"); show_site_detail(chat_id, msg_id, sn); return
    if data.startswith("slink:"):
        sn = data.split(":",1)[1]; bot.answer_callback_query(c.id)
        info = websites.get(sn)
        bot.send_message(chat_id, f"🔗 <b>{sn}</b>\n{info.get('url') or 'Not running'}")
        return
    if data.startswith("sdom:"):
        sn = data.split(":",1)[1]; bot.answer_callback_query(c.id)
        info = websites.get(sn) or {}
        user_state[uid] = {"action": "set_domain", "sn": sn}
        bot.send_message(chat_id,
            f"🌍 <b>Custom Domain — {sn}</b>\n\nCurrent: {info.get('custom_domain') or '— none —'}\n\n"
            f"Apna domain bhejein (e.g. <code>mysite.com</code>).\n\n"
            f"📌 <b>Setup:</b> Apne domain DNS me ek CNAME record banayein jo is site ke tunnel URL "
            f"par point kare:\n<code>{info.get('url') or 'site start karein'}</code>\n"
            f"❌ Hatane ke liye <code>remove</code> bhejein.")
        return
    if data.startswith("sssl:"):
        sn = data.split(":",1)[1]; bot.answer_callback_query(c.id)
        info = websites.get(sn) or {}
        url = info.get("url") or ""
        https = url.startswith("https://")
        dom = info.get("custom_domain")
        txt = (f"🔒 <b>SSL Status — {sn}</b>\n\n"
               f"🔗 URL: {url or '—'}\n"
               f"{'✅' if https else '❌'} HTTPS: {'Active (auto SSL via tunnel)' if https else 'Not active'}\n"
               f"🌍 Domain: {dom or '— none —'}\n\n")
        if https:
            txt += "✅ Cloudflare/localtunnel automatically free SSL (HTTPS) provide karta hai."
        else:
            txt += "⚠️ Public HTTPS link ke liye cloudflared install karein."
        bot.send_message(chat_id, txt)
        return
    if data.startswith("sana:"):
        sn = data.split(":",1)[1]; bot.answer_callback_query(c.id)
        info = websites.get(sn) or {}
        meta = config.get("site_meta", {}).get(sn, {})
        txt = (f"📊 <b>Website Analytics — {sn}</b>\n\n"
               f"👁 Total Views: {info.get('hits', 0)}\n"
               f"⚙️ Status: {'🟢 Running' if site_running(sn) else '🔴 Stopped'}\n"
               f"🔗 URL: {info.get('url') or '—'}\n"
               f"🌍 Domain: {info.get('custom_domain') or '— none —'}\n"
               f"📦 Files: {_count_files(info.get('folder'))}\n"
               f"💾 Size: {_folder_size_mb(info.get('folder')):.2f} MB")
        bot.send_message(chat_id, txt)
        return
    if data.startswith("sget:"):
        sn = data.split(":",1)[1]; bot.answer_callback_query(c.id, "Zipping files...")
        info = websites.get(sn)
        if not info:
            bot.send_message(chat_id, "❌ Site not found"); return
        try:
            import shutil
            zip_base = os.path.join(BASE_DIR, sn)
            zpath = shutil.make_archive(zip_base, "zip", info["folder"])
            with open(zpath, "rb") as f:
                bot.send_document(chat_id, f, caption=f"🌐 {sn} (website files)")
            os.remove(zpath)
        except Exception as e:
            bot.send_message(chat_id, f"❌ {e}")
        return
    if data.startswith("sdel:"):
        sn = data.split(":",1)[1]; stop_website(sn)
        info = websites.pop(sn, None)
        if info:
            try:
                import shutil; shutil.rmtree(info["folder"], ignore_errors=True)
            except Exception: pass
        for u in users.values():
            if sn in u.get("sites", []): u["sites"].remove(sn)
        save_users()
        bot.answer_callback_query(c.id, "🗑 Deleted!"); show_sites_list(chat_id, msg_id); return

    # ============ ADMIN ============
    if data.startswith("a_"):
        if not is_admin(uid):
            bot.answer_callback_query(c.id, "⛔ Admin only", show_alert=True); return

        if data == "a_panel":
            bot.answer_callback_query(c.id); send_admin_panel(chat_id, edit=msg_id); return
        if data == "a_addch":
            bot.answer_callback_query(c.id); user_state[uid] = {"action": "addch"}
            bot.send_message(chat_id,
                "➕ <b>Add Force-Join Channel</b>\n\n"
                "Is format me bhejein:\n<code>Button Name || channel link</code>\n\n"
                "📢 <b>Public channel example:</b>\n<code>Join Us || https://t.me/mychannel</code>\n\n"
                "🔒 <b>Private channel example</b> (chat_id zaroori):\n"
                "<code>VIP Group || https://t.me/+AbcXyz123 || -1001234567890</code>\n\n"
                "💡 Private channel ka chat_id paane ke liye us channel se koi message is bot "
                "ko forward karein (bot ko channel me admin banakar).\n\n"
                "➕ Ek se zyada channel: har channel nayi line me likhein.\n"
                "⚠️ Bot ko har channel me <b>admin</b> banana zaroori hai."); return
        if data == "a_delch":
            bot.answer_callback_query(c.id)
            chans = get_channels()
            if not chans:
                bot.send_message(chat_id, "Koi channel nahi."); return
            kb = types.InlineKeyboardMarkup()
            for i, ch in enumerate(chans):
                kb.add(types.InlineKeyboardButton(f"❌ {ch['name']}", callback_data=f"a_rmch:{i}"))
            bot.send_message(chat_id, "Remove channel:", reply_markup=kb); return
        if data.startswith("a_rmch:"):
            try:
                idx = int(data.split(":",1)[1])
                if 0 <= idx < len(config["channels"]):
                    config["channels"].pop(idx); save_config()
            except Exception:
                pass
            _join_cache.clear()
            bot.answer_callback_query(c.id, "Removed!"); send_admin_panel(chat_id); return
        if data == "a_setpaych":
            bot.answer_callback_query(c.id); user_state[uid] = {"action": "setpaych"}
            bot.send_message(chat_id, "📨 Payment request channel username/id bhejein (e.g. <code>@mypaychannel</code>). Bot ko admin banayein."); return
        if data == "a_setqr":
            bot.answer_callback_query(c.id); user_state[uid] = {"action": "setqr"}
            bot.send_message(chat_id, "🖼 Payment QR ki <b>photo</b> bhejein."); return
        if data == "a_prices":
            bot.answer_callback_query(c.id)
            kb = types.InlineKeyboardMarkup()
            for p in ("12day","1month","1year","lifetime"):
                kb.add(types.InlineKeyboardButton(f"{PLAN_LABEL[p]} = ₹{config['prices'][p]}", callback_data=f"a_setp:{p}"))
            bot.send_message(chat_id, "Kis plan ki price change karni hai?", reply_markup=kb); return
        if data.startswith("a_setp:"):
            plan = data.split(":",1)[1]; bot.answer_callback_query(c.id)
            user_state[uid] = {"action": "setprice", "plan": plan}
            bot.send_message(chat_id, f"Nayi price (₹) bhejein for {PLAN_LABEL[plan]}:"); return
        if data == "a_addfolder":
            bot.answer_callback_query(c.id); user_state[uid] = {"action": "addfolder"}
            bot.send_message(chat_id, "📁 Folder ka naam bhejein:"); return
        if data == "a_files":
            bot.answer_callback_query(c.id); show_files_list(chat_id, msg_id); return
        if data == "a_sites":
            bot.answer_callback_query(c.id); show_sites_list(chat_id, msg_id); return
        if data == "a_bots":
            bot.answer_callback_query(c.id); show_admin_bots(chat_id, msg_id); return
        if data == "a_module":
            bot.answer_callback_query(c.id)
            user_state[uid] = {"action": "install_module"}
            bot.send_message(chat_id,
                "📦 <b>Install Module</b>\n\nJo Python module install karna hai uska naam bhejein.\n"
                "Ek se zyada: space se alag karein.\n\n"
                "Example: <code>requests</code>  ya  <code>numpy pillow flask</code>")
            return
        if data == "a_stats":
            bot.answer_callback_query(c.id)
            running = sum(1 for f in list_files() if is_running(f))
            srun = sum(1 for s in websites if site_running(s))
            r_total, r_avg = rating_summary()
            txt = (f"📊 <b>Server Stats</b>\n\n👥 Users: {len(users)}\n"
                   f"🗂 Files: {len(list_files())} (🟢 {running})\n"
                   f"🌐 Sites: {len(websites)} (🟢 {srun})\n"
                   f"⛔ Blocked: {len(config['blocked'])}\n"
                   f"⭐ Rating: {r_avg:.1f}/5 ({r_total} users)\n"
                   f"⏱ Uptime: {human_uptime()}")
            back = types.InlineKeyboardMarkup(); back.add(types.InlineKeyboardButton("🔙 Back", callback_data="a_panel"))
            bot.edit_message_text(txt, chat_id, msg_id, reply_markup=back); return
        if data == "a_block":
            bot.answer_callback_query(c.id)
            kb = types.InlineKeyboardMarkup()
            for f in list_files():
                if f not in config["blocked"]:
                    kb.add(types.InlineKeyboardButton(f"⛔ {f}", callback_data=f"a_bl:{f}"))
            if not kb.keyboard: bot.send_message(chat_id, "Koi file nahi."); return
            bot.send_message(chat_id, "Block/Stop file:", reply_markup=kb); return
        if data.startswith("a_bl:"):
            fname = data.split(":",1)[1]; stop_file(fname)
            if fname not in config["blocked"]: config["blocked"].append(fname); save_config()
            bot.answer_callback_query(c.id, "⛔ Blocked!"); return
        if data == "a_unblock":
            bot.answer_callback_query(c.id)
            kb = types.InlineKeyboardMarkup()
            for f in config["blocked"]:
                kb.add(types.InlineKeyboardButton(f"▶️ {f}", callback_data=f"a_unbl:{f}"))
            if not kb.keyboard: bot.send_message(chat_id, "Koi blocked file nahi."); return
            bot.send_message(chat_id, "Unblock file:", reply_markup=kb); return
        if data.startswith("a_unbl:"):
            fname = data.split(":",1)[1]
            if fname in config["blocked"]: config["blocked"].remove(fname); save_config(); run_file(fname)
            bot.answer_callback_query(c.id, "▶️ Unblocked!"); return

        if data == "a_givesub":
            bot.answer_callback_query(c.id)
            user_state[uid] = {"action": "givesub_id"}
            bot.send_message(chat_id, "🎁 <b>Give Subscription</b>\n\nJis user ko subscription dena hai uska <b>User ID</b> bhejein.\n(User ID 'Profile' me dikhta hai.)")
            return

        if data.startswith("a_gsplan:"):
            _, target, plan = data.split(":")
            target = int(target)
            activate_sub(target, plan)
            bot.answer_callback_query(c.id, "✅ Subscription diya!")
            bot.send_message(chat_id, f"✅ User <code>{target}</code> ko <b>{PLAN_LABEL[plan]}</b> subscription de diya.\nStatus: {sub_text(target)}")
            try:
                bot.send_message(target, f"🎉 <b>Subscription Active!</b>\n\nAdmin ne aapko <b>{PLAN_LABEL[plan]}</b> subscription diya hai.\nStatus: {sub_text(target)}\n\nAb aap unlimited host kar sakte hain.")
            except Exception:
                pass
            return

        if data == "a_remsub":
            bot.answer_callback_query(c.id)
            user_state[uid] = {"action": "remsub_id"}
            bot.send_message(chat_id, "🚫 <b>Remove Subscription</b>\n\nJis user ka subscription hatana hai uska <b>User ID</b> bhejein.")
            return

        if data == "a_setwelcome":
            bot.answer_callback_query(c.id)
            user_state[uid] = {"action": "set_welcome"}
            bot.send_message(chat_id,
                "👋 <b>Set Welcome Message</b>\n\nAb jo bhi message (text / photo / premium emoji / sticker) "
                "bhejenge, wahi naye users ko /start par dikhega.\n\n"
                "💡 Text me <code>{name}</code> likhne par user ka naam aa jayega.\n"
                "❌ Cancel ke liye <code>/admin</code> dobara bhejein.")
            return

        if data == "a_broadcast":
            bot.answer_callback_query(c.id)
            user_state[uid] = {"action": "broadcast"}
            bot.send_message(chat_id,
                "📢 <b>Broadcast</b>\n\nAb jo bhi message bhejenge (text / photo / video / forward / koi bhi), "
                "woh <b>sabhi users</b> ko bhej diya jayega.\n\n"
                f"👥 Total users: {len(users)}\n❌ Cancel: <code>/admin</code>")
            return

# ======================= LISTS / DETAILS =======================
def owner_of_bot(fname):
    for sid, u in users.items():
        if fname in u.get("bots", []):
            return sid, u.get("name", "User")
    return None, None

def show_admin_bots(chat_id, msg_id=None):
    files = list_files()
    if not files:
        _edit_or_send(chat_id, msg_id, "🤖 Abhi tak kisi user ne koi bot host nahi ki."); return
    kb = types.InlineKeyboardMarkup()
    for f in files:
        st = "🟢" if is_running(f) else ("⛔" if f in config["blocked"] else "🔴")
        sid, uname = owner_of_bot(f)
        label = f"{st} {f}" + (f" — {uname}" if uname else "")
        kb.add(types.InlineKeyboardButton(label[:60], callback_data=f"file:{f}"))
    _edit_or_send(chat_id, msg_id,
        f"🤖 <b>All Hosted Bots</b> ({len(files)})\n\nKisi bot par click karke Stop / File le / Log dekh sakte hain:", kb)

def show_files_list(chat_id, msg_id=None, owner=None):
    files = list_files()
    if owner is not None:  # normal user -> only their own hosted bots
        own = get_user(owner).get("bots", [])
        files = [f for f in files if f in own]
    if not files:
        _edit_or_send(chat_id, msg_id, "🗂 Aapne abhi tak koi bot host nahi ki.\n\n📤 Upload File button se host karein."); return
    kb = types.InlineKeyboardMarkup()
    for f in files:
        st = "🟢" if is_running(f) else ("⛔" if f in config["blocked"] else "🔴")
        kb.add(types.InlineKeyboardButton(f"{st} {f}", callback_data=f"file:{f}"))
    _edit_or_send(chat_id, msg_id, "📂 <b>Files</b> — kisi par click karein:", kb)

def show_file_detail(chat_id, msg_id, fname):
    if not os.path.exists(file_path(fname)):
        show_files_list(chat_id, msg_id); return
    running = is_running(fname); blocked = fname in config["blocked"]
    status = "🟢 Running" if running else ("⛔ Blocked" if blocked else "🔴 Stopped")
    txt = f"🗂 <b>{fname}</b>\n📦 {os.path.getsize(file_path(fname))} bytes\n⚙️ {status}"
    kb = types.InlineKeyboardMarkup(row_width=2)
    if running:
        kb.add(types.InlineKeyboardButton("⏹ Stop", callback_data=f"stop:{fname}"),
               types.InlineKeyboardButton("🔄 Restart", callback_data=f"restart:{fname}"))
    else:
        kb.add(types.InlineKeyboardButton("▶️ Start", callback_data=f"start:{fname}"),
               types.InlineKeyboardButton("🔄 Restart", callback_data=f"restart:{fname}"))
    kb.add(types.InlineKeyboardButton("📜 View Logs", callback_data=f"log:{fname}"),
           types.InlineKeyboardButton("📥 Download File", callback_data=f"get:{fname}"))
    kb.add(types.InlineKeyboardButton("⚙️ Environment Vars", callback_data=f"env:{fname}"),
           types.InlineKeyboardButton("📦 Install Requirements", callback_data=f"req:{fname}"))
    kb.add(types.InlineKeyboardButton("✏️ Edit File", callback_data=f"edit:{fname}"),
           types.InlineKeyboardButton("🗑 Delete File", callback_data=f"del:{fname}"))
    _edit_or_send(chat_id, msg_id, txt, kb)

def show_sites_list(chat_id, msg_id=None, owner=None):
    site_names = list(websites.keys())
    if owner is not None:  # normal user -> only their own websites
        site_names = [sn for sn in site_names if websites[sn].get("owner") == owner]
    if not site_names:
        _edit_or_send(chat_id, msg_id, "🌐 Aapne abhi tak koi website host nahi ki.\n\n🌐 Host Website button se host karein."); return
    kb = types.InlineKeyboardMarkup()
    for sn in site_names:
        st = "🟢" if site_running(sn) else "🔴"
        kb.add(types.InlineKeyboardButton(f"{st} {sn}", callback_data=f"site:{sn}"))
    _edit_or_send(chat_id, msg_id, "🌐 <b>Websites</b> — kisi par click karein:", kb)

def show_site_detail(chat_id, msg_id, sn):
    info = websites.get(sn)
    if not info:
        show_sites_list(chat_id, msg_id); return
    running = site_running(sn)
    dom = info.get("custom_domain")
    hits = info.get("hits", 0)
    txt = (f"🌐 <b>{sn}</b>\n⚙️ {'🟢 Running' if running else '🔴 Stopped'}\n"
           f"🔗 {info.get('url') or '—'}\n"
           f"🌍 Domain: {dom or '— not set —'}\n"
           f"👁 Views: {hits}")
    kb = types.InlineKeyboardMarkup(row_width=2)
    if running:
        kb.add(types.InlineKeyboardButton("⏹ Stop", callback_data=f"sstop:{sn}"),
               types.InlineKeyboardButton("🚀 Redeploy Site", callback_data=f"srestart:{sn}"))
    else:
        kb.add(types.InlineKeyboardButton("▶️ Start", callback_data=f"sstart:{sn}"),
               types.InlineKeyboardButton("🚀 Redeploy Site", callback_data=f"srestart:{sn}"))
    kb.add(types.InlineKeyboardButton("🔗 Link", callback_data=f"slink:{sn}"),
           types.InlineKeyboardButton("📥 Get Files", callback_data=f"sget:{sn}"))
    kb.add(types.InlineKeyboardButton("🌍 Custom Domain", callback_data=f"sdom:{sn}"),
           types.InlineKeyboardButton("🔒 SSL Status", callback_data=f"sssl:{sn}"))
    kb.add(types.InlineKeyboardButton("📊 Website Analytics", callback_data=f"sana:{sn}"))
    kb.add(types.InlineKeyboardButton("🗑 Delete Site", callback_data=f"sdel:{sn}"))
    _edit_or_send(chat_id, msg_id, txt, kb)

def _edit_or_send(chat_id, msg_id, text, kb=None):
    if msg_id:
        try: bot.edit_message_text(text, chat_id, msg_id, reply_markup=kb); return
        except Exception: pass
    bot.send_message(chat_id, text, reply_markup=kb)

# ======================= FILE MANAGER =======================
def send_file_manager(chat_id):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton("📥 Upload ZIP", callback_data="fm_uploadzip"),
           types.InlineKeyboardButton("📦 Extract ZIP", callback_data="fm_extract"))
    kb.add(types.InlineKeyboardButton("📤 Download File", callback_data="fm_download"),
           types.InlineKeyboardButton("✏️ Edit File", callback_data="fm_edit"))
    kb.add(types.InlineKeyboardButton("🗑 Delete File", callback_data="fm_delete"))
    bot.send_message(chat_id, "📁 <b>File Manager</b>\nKoi action chunein:", reply_markup=kb)

def fm_user_files(uid):
    """Files belonging to user (bots) + extracted files; admin sees all."""
    if is_admin(uid):
        return list_files()
    return list(get_user(uid).get("bots", []))

def fm_file_picker(chat_id, uid, action_prefix, title):
    files = fm_user_files(uid)
    files = [f for f in files if os.path.exists(file_path(f))]
    if not files:
        bot.send_message(chat_id, "🗂 Koi file nahi mili. Pehle 📤 Upload File se host karein."); return
    kb = types.InlineKeyboardMarkup()
    for f in files:
        kb.add(types.InlineKeyboardButton(f, callback_data=f"{action_prefix}:{f}"))
    bot.send_message(chat_id, title, reply_markup=kb)

def _count_files(folder):
    if not folder or not os.path.isdir(folder):
        return 0
    n = 0
    for _, _, fs in os.walk(folder):
        n += len(fs)
    return n

def _folder_size_mb(folder):
    if not folder or not os.path.isdir(folder):
        return 0.0
    total = 0
    for root, _, fs in os.walk(folder):
        for f in fs:
            try: total += os.path.getsize(os.path.join(root, f))
            except Exception: pass
    return total / (1024 * 1024)

def do_install_requirements(chat_id, fname):
    """pip install -r requirements.txt if present, else detect imports."""
    req = os.path.join(FILES_DIR, "requirements.txt")
    target_req = None
    # look for a requirements file in FILES_DIR
    if os.path.exists(req):
        target_req = req
    if target_req:
        bot.send_message(chat_id, "📦 Installing from requirements.txt ...")
        cmd = [sys.executable, "-m", "pip", "install", "-r", target_req]
    else:
        # try to auto-detect imports from the file
        mods = detect_imports(file_path(fname))
        if not mods:
            bot.send_message(chat_id, "ℹ️ requirements.txt nahi mila aur koi external import detect nahi hua.\n"
                                      "📦 Install Module button se manually install karein."); return
        bot.send_message(chat_id, f"📦 Detected modules install kar rahe hain:\n<code>{', '.join(mods)}</code>")
        cmd = [sys.executable, "-m", "pip", "install"] + mods
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        out = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()[-3500:] or "—"
        head = "✅ <b>Requirements installed!</b>" if proc.returncode == 0 else "❌ <b>Install failed</b>"
        bot.send_message(chat_id, f"{head}\n\n<pre>{telebot.util.escape(out)}</pre>")
    except Exception as e:
        bot.send_message(chat_id, f"❌ {telebot.util.escape(str(e))}")

STDLIB = {"os","sys","re","json","time","math","random","datetime","subprocess",
          "threading","socket","zipfile","shutil","signal","traceback","io","base64",
          "collections","itertools","functools","typing","asyncio","logging","hashlib",
          "urllib","http","sqlite3","string","glob","pathlib","tempfile","struct"}

def detect_imports(path):
    mods = set()
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                m = re.match(r"\s*(?:import|from)\s+([A-Za-z0-9_]+)", line)
                if m:
                    name = m.group(1)
                    if name not in STDLIB:
                        mods.add(name)
    except Exception:
        pass
    # common pip-name fixes
    fix = {"telegram": "python-telegram-bot", "telebot": "pyTelegramBotAPI",
           "cv2": "opencv-python", "PIL": "pillow", "bs4": "beautifulsoup4",
           "yaml": "pyyaml", "dotenv": "python-dotenv"}
    return [fix.get(m, m) for m in mods]

# ======================= PHOTO (QR) =======================
@bot.message_handler(content_types=["photo"])
def photo_handler(m):
    uid = m.from_user.id
    st = user_state.get(uid)
    if st and st.get("action") == "setqr" and is_admin(uid):
        config["qr_file_id"] = m.photo[-1].file_id; save_config()
        user_state.pop(uid, None)
        bot.reply_to(m, "✅ QR set ho gaya!")
        send_admin_panel(m.chat.id)

# ======================= TEXT / MENU ROUTER =======================
@bot.message_handler(content_types=["text"])
def text_handler(m):
    uid = m.from_user.id
    txt = m.text.strip()
    st = user_state.get(uid)

    # ----- admin/multi-step states -----
    if st:
        act = st.get("action")
        if act == "addch" and is_admin(uid):
            added = []; errors = []
            for line in txt.splitlines():
                line = line.strip()
                if not line:
                    continue
                if "||" not in line:
                    # backward-compat: plain @username
                    uname = line if line.startswith("@") else "@" + line
                    obj = {"name": uname, "url": f"https://t.me/{uname.lstrip('@')}", "ref": uname}
                else:
                    obj, err = parse_channel_input(line)
                    if err:
                        errors.append(f"❌ <b>{line}</b>\n{err}")
                        continue
                # verify bot can access this channel (admin?)
                try:
                    chat = bot.get_chat(obj["ref"])
                    me = bot.get_chat_member(obj["ref"], bot.get_me().id)
                    if me.status not in ("administrator", "creator"):
                        errors.append(f"⚠️ <b>{obj['name']}</b>: Bot is channel me <b>admin</b> nahi hai. Pehle admin banayein.")
                        continue
                except Exception as e:
                    errors.append(f"❌ <b>{obj['name']}</b>: Bot is channel ko access nahi kar pa raha.\n"
                                  f"<code>{telebot.util.escape(str(e))}</code>\n"
                                  f"➡️ Sahi chat_id dein aur bot ko admin banayein.")
                    continue
                config["channels"].append(obj); added.append(obj["name"])
            if added:
                save_config(); _join_cache.clear()
            user_state.pop(uid, None)
            msg = ""
            if added:
                msg += "✅ Added: " + ", ".join(added) + "\n\n"
            if errors:
                msg += "\n".join(errors)
            bot.reply_to(m, msg or "Kuch add nahi hua.")
            send_admin_panel(m.chat.id); return
        if act == "setpaych" and is_admin(uid):
            config["payment_channel"] = txt; save_config()
            user_state.pop(uid, None); bot.reply_to(m, f"✅ Payment channel set: {txt}"); send_admin_panel(m.chat.id); return
        if act == "setprice" and is_admin(uid):
            try:
                config["prices"][st["plan"]] = int(re.sub(r"[^0-9]", "", txt))
                save_config(); bot.reply_to(m, "✅ Price updated!")
            except Exception: bot.reply_to(m, "❌ Number bhejein.")
            user_state.pop(uid, None); send_admin_panel(m.chat.id); return
        if act == "addfolder" and is_admin(uid):
            name = txt.replace("/", "_"); os.makedirs(os.path.join(FILES_DIR, name), exist_ok=True)
            if name not in config["folders"]: config["folders"].append(name); save_config()
            user_state.pop(uid, None); bot.reply_to(m, f"✅ Folder: {name}"); send_admin_panel(m.chat.id); return
        if act == "install_module" and is_admin(uid):
            user_state.pop(uid, None)
            mods = txt.split()
            if not mods:
                bot.reply_to(m, "❌ Module naam bhejein."); return
            threading.Thread(target=do_install_module, args=(m.chat.id, mods), daemon=True).start()
            return
        if act == "set_env":
            fname = st["fname"]; user_state.pop(uid, None)
            if txt.lower().strip() == "clear":
                config.get("env_vars", {}).pop(fname, None); save_config()
                bot.reply_to(m, "✅ Environment variables clear ho gaye.")
            else:
                ev = {}
                for line in txt.splitlines():
                    if "=" in line:
                        k, v = line.split("=", 1)
                        ev[k.strip()] = v.strip()
                config.setdefault("env_vars", {})[fname] = ev; save_config()
                bot.reply_to(m, f"✅ {len(ev)} env variable set ho gaye. File restart kar rahe hain...")
            run_file(fname)
            return
        if act == "edit_file":
            fname = st["fname"]; user_state.pop(uid, None)
            try:
                with open(file_path(fname), "w", encoding="utf-8") as f:
                    f.write(m.text)
                bot.reply_to(m, f"✅ <b>{fname}</b> save ho gayi. Restart kar rahe hain...")
                ok, msg = run_file(fname)
                bot.send_message(m.chat.id, f"🟢 {msg}" if ok else f"⚠️ {msg}")
            except Exception as e:
                bot.reply_to(m, f"❌ {e}")
            return
        if act == "set_domain":
            sn = st["sn"]; user_state.pop(uid, None)
            info = websites.get(sn)
            if not info:
                bot.reply_to(m, "❌ Site not found."); return
            if txt.lower().strip() == "remove":
                info["custom_domain"] = None
                config.setdefault("site_meta", {}).setdefault(sn, {})["custom_domain"] = None
                save_config(); bot.reply_to(m, "✅ Custom domain hata diya.")
            else:
                dom = txt.strip().replace("https://", "").replace("http://", "").strip("/")
                info["custom_domain"] = dom
                config.setdefault("site_meta", {}).setdefault(sn, {})["custom_domain"] = dom
                save_config()
                bot.reply_to(m,
                    f"✅ Custom domain set: <b>{dom}</b>\n\n"
                    f"📌 DNS me CNAME record banayein jo is URL par point kare:\n"
                    f"<code>{info.get('url') or 'site start karein'}</code>\n\n"
                    f"DNS propagate hone ke baad <code>https://{dom}</code> par site khulegi.")
            return
        if act == "givesub_id" and is_admin(uid):
            try:
                target = int(re.sub(r"[^0-9]", "", txt))
            except Exception:
                bot.reply_to(m, "❌ Sahi User ID (number) bhejein."); return
            get_user(target)  # ensure user record exists
            user_state.pop(uid, None)
            kb = types.InlineKeyboardMarkup(row_width=1)
            for p in ("12day","1month","1year","lifetime"):
                kb.add(types.InlineKeyboardButton(f"{PLAN_LABEL[p]}", callback_data=f"a_gsplan:{target}:{p}"))
            bot.reply_to(m, f"🎁 User <code>{target}</code> ko kaunsa plan dena hai?", reply_markup=kb)
            return
        if act == "remsub_id" and is_admin(uid):
            try:
                target = int(re.sub(r"[^0-9]", "", txt))
            except Exception:
                bot.reply_to(m, "❌ Sahi User ID (number) bhejein."); return
            u = get_user(target)
            u["sub_plan"] = None; u["sub_expiry"] = 0; save_users()
            user_state.pop(uid, None)
            bot.reply_to(m, f"🚫 User <code>{target}</code> ka subscription hata diya.")
            try:
                bot.send_message(target, "⚠️ Aapka subscription admin ne hata diya hai. Ab aap free limit par hain.")
            except Exception:
                pass
            return
        if act == "await_utr":
            handle_utr(m, st["plan"], txt); user_state.pop(uid, None); return

    # ----- joined gate -----
    nj = check_joined(uid)
    if nj and not is_admin(uid):
        send_join_required(m.chat.id, nj); return

    # any menu button press -> clear stale upload/await states
    if txt in (BTN_UPLOAD, BTN_WEBSITE, BTN_CHECK, BTN_FILES, BTN_PROFILE,
               BTN_BUY, BTN_STATS, BTN_SPEED, BTN_RATE):
        user_state.pop(uid, None)

    # ----- reply keyboard menu -----
    if txt == BTN_UPLOAD:
        if not can_host(uid, "bots"):
            bot.send_message(m.chat.id, limit_msg("bot")); return
        user_state[uid] = {"action": "upload_bot"}
        bot.send_message(m.chat.id, "📤 <b>Host Bot</b>\nApni bot file (.py/.js/.sh) bhejein. Upload hote hi host + run ho jayegi."); return
    if txt == BTN_WEBSITE:
        if not can_host(uid, "sites"):
            bot.send_message(m.chat.id, limit_msg("website")); return
        user_state[uid] = {"action": "upload_site"}
        bot.send_message(m.chat.id, "🌐 <b>Host Website</b>\nApni website file bhejein (.zip / .html / koi bhi).\n"
                                    "ZIP pehle unzip hogi, phir website host hogi aur aapko link milega."); return
    if txt == BTN_CHECK or txt == BTN_FILES:
        viewer = None if is_admin(uid) else uid
        show_files_list(m.chat.id, owner=viewer)
        show_sites_list(m.chat.id, owner=viewer)
        send_file_manager(m.chat.id); return
    if txt == BTN_PROFILE:
        u = get_user(uid, m.from_user.first_name)
        vip = has_active_sub(uid)
        limit = "♾ Unlimited" if vip else f"{FREE_BOTS} bots / {FREE_SITES} sites"
        maxmb = VIP_MAX_MB if vip else FREE_MAX_MB
        bot.send_message(m.chat.id,
            f"👤 <b>Profile</b>\n\n🪪 Name: {u['name']}\n🆔 ID: <code>{uid}</code>\n"
            f"💎 Subscription: {sub_text(uid)}\n📦 Limit: {limit}\n"
            f"📁 Max file size: <b>{maxmb} MB</b>\n"
            f"🗂 Bots hosted: {len(u.get('bots',[]))}\n🌐 Sites hosted: {len(u.get('sites',[]))}"); return
    if txt == BTN_BUY:
        send_buy(m.chat.id); return
    if txt == BTN_STATS:
        running = sum(1 for f in list_files() if is_running(f))
        srun = sum(1 for s in websites if site_running(s))
        bot.send_message(m.chat.id,
            f"📊 <b>Statistics</b>\n\n🗂 Files: {len(list_files())} (🟢 {running})\n"
            f"🌐 Sites: {len(websites)} (🟢 {srun})\n👥 Users: {len(users)}\n⏱ Uptime: {human_uptime()}"); return
    if txt == BTN_SPEED:
        t0 = time.time(); ms = int((time.time()-t0)*1000)
        bot.send_message(m.chat.id, f"⚡ <b>Bot Speed</b>\n🏓 Ping: <code>{ms} ms</code>\n⏱ Uptime: {human_uptime()}\n🟢 Online (never sleeps)"); return
    if txt == BTN_RATE:
        send_rating(m.chat.id, uid); return

# ======================= LIMITS =======================
def can_host(uid, kind):
    if has_active_sub(uid) or is_admin(uid):
        return True
    u = get_user(uid)
    if kind == "bots":
        return len(u.get("bots", [])) < FREE_BOTS
    return len(u.get("sites", [])) < FREE_SITES

def limit_msg(kind):
    n = FREE_BOTS if kind == "bot" else FREE_SITES
    return (f"🚫 <b>Limit Reached!</b>\n\n"
            f"Aapne pehle hi apni free limit <b>{n} {kind}s</b> use kar li hai.\n"
            f"❌ Ab aur {kind} host nahi ho sakta.\n\n"
            f"💎 <b>Unlimited</b> bots & websites host karne ke liye "
            f"<b>{BTN_BUY}</b> button dabakar subscription buy karein.")

# ======================= UTR -> PAYMENT REQUEST =======================
def handle_utr(m, plan, utr):
    uid = m.from_user.id
    price = config["prices"][plan]
    if not config.get("payment_channel"):
        bot.reply_to(m, "⚠️ Payment channel set nahi hai. Admin se contact karein."); return
    bot.reply_to(m, "✅ Aapka payment request bhej diya gaya hai. Admin approve karte hi subscription active ho jayega. ⏳")
    txt = (f"💳 <b>New Payment Request</b>\n\n"
           f"👤 User: {m.from_user.first_name} (<code>{uid}</code>)\n"
           f"📦 Plan: {PLAN_LABEL[plan]}\n💰 Amount: ₹{price}\n"
           f"🧾 UTR/TxnID: <code>{telebot.util.escape(utr)}</code>")
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Accept", callback_data=f"pay_ok:{uid}:{plan}"),
           types.InlineKeyboardButton("❌ Reject", callback_data=f"pay_no:{uid}:{plan}"))
    try:
        bot.send_message(config["payment_channel"], txt, reply_markup=kb)
    except Exception as e:
        bot.send_message(ADMIN_ID, txt + f"\n\n(⚠️ channel send fail: {e})", reply_markup=kb)

# ======================= DOCUMENT UPLOAD =======================
@bot.message_handler(content_types=["document"])
def doc_handler(m):
    uid = m.from_user.id
    nj = check_joined(uid)
    if nj and not is_admin(uid):
        send_join_required(m.chat.id, nj); return
    st = user_state.get(uid) or {}
    mode = st.get("action")
    if mode not in ("upload_bot", "upload_site", "fm_uploadzip"):
        bot.reply_to(m, "Pehle 📤 Upload File ya 🌐 Host Website button dabayein."); return

    fname = m.document.file_name

    # ---- file size limit (10MB normal / 100MB VIP) ----
    size_mb = (m.document.file_size or 0) / (1024 * 1024)
    max_mb = VIP_MAX_MB if (has_active_sub(uid) or is_admin(uid)) else FREE_MAX_MB
    if size_mb > max_mb:
        if max_mb == FREE_MAX_MB:
            bot.reply_to(m,
                f"🚫 <b>File too big!</b>\n\nAapki file <b>{size_mb:.1f} MB</b> hai.\n"
                f"❌ Normal user sirf <b>{FREE_MAX_MB} MB</b> tak file host kar sakta hai.\n\n"
                f"💎 VIP (subscription) lene par <b>{VIP_MAX_MB} MB</b> tak allowed hai.\n"
                f"👉 <b>{BTN_BUY}</b> dabakar subscription buy karein.")
        else:
            bot.reply_to(m,
                f"🚫 <b>File too big!</b>\n\nAapki file <b>{size_mb:.1f} MB</b> hai.\n"
                f"❌ Max limit <b>{VIP_MAX_MB} MB</b> hai.")
        return

    try:
        info = bot.get_file(m.document.file_id)
        data = bot.download_file(info.file_path)
    except Exception as e:
        bot.reply_to(m, f"❌ Download error: {e}\n\n(Note: Telegram bot API se 20MB se badi file download nahi hoti — agar file 20MB+ hai to bot host nahi kar paayega.)"); return

    if mode == "upload_bot":
        if not can_host(uid, "bots"):
            bot.reply_to(m, limit_msg("bot")); return
        with open(file_path(fname), "wb") as f: f.write(data)
        u = get_user(uid)
        if fname not in u["bots"]: u["bots"].append(fname); save_users()
        user_state.pop(uid, None)
        bot.reply_to(m, f"✅ <b>{fname}</b> upload. Host kar rahe hain...")
        ok, msg = run_file(fname)
        bot.send_message(m.chat.id, f"🟢 <b>{fname}</b> live hai!\n{msg}" if ok else
                         f"⚠️ Save hui par run nahi:\n<code>{telebot.util.escape(msg)}</code>")
        send_main_menu(m.chat.id); return

    # ---- website ----
    if not can_host(uid, "sites"):
        bot.reply_to(m, limit_msg("website")); return
    base = re.sub(r"[^a-zA-Z0-9_-]", "", fname.rsplit(".",1)[0]) or "site"
    sitename = f"{base}_{uid}"
    folder = os.path.join(SITES_DIR, sitename)
    import shutil
    shutil.rmtree(folder, ignore_errors=True); os.makedirs(folder, exist_ok=True)

    bot.reply_to(m, f"📥 <b>{fname}</b> received. Processing...")
    if fname.lower().endswith(".zip"):
        zpath = os.path.join(folder, fname)
        with open(zpath, "wb") as f: f.write(data)
        try:
            with zipfile.ZipFile(zpath) as z: z.extractall(folder)
            os.remove(zpath)
            bot.send_message(m.chat.id, "📦 ZIP unzip ho gayi.")
        except Exception as e:
            bot.send_message(m.chat.id, f"❌ Unzip error: {e}"); return
    else:
        with open(os.path.join(folder, fname), "wb") as f: f.write(data)
        # if single html not named index, also copy as index.html
        if fname.lower().endswith((".html", ".htm")) and fname.lower() != "index.html":
            try: shutil.copy(os.path.join(folder, fname), os.path.join(folder, "index.html"))
            except Exception: pass

    websites[sitename] = {"folder": folder, "server": None, "tunnel": None, "url": None, "port": None, "owner": uid}
    u = get_user(uid)
    if sitename not in u["sites"]: u["sites"].append(sitename); save_users()
    user_state.pop(uid, None)

    bot.send_message(m.chat.id, "🚀 Website host kar rahe hain, link bana rahe hain... (15-30 sec)")
    ok, msg = start_website(sitename)
    if ok:
        bot.send_message(m.chat.id, f"✅ <b>Website Live!</b>\n\n🌐 Name: {sitename}\n🔗 Link: {msg}\n\nIs link ko open karke aapki website dekhi ja sakti hai.")
    else:
        bot.send_message(m.chat.id, f"⚠️ Host nahi hui: {msg}")
    send_main_menu(m.chat.id)

# ======================= STARTUP =======================
def autostart():
    for f in list_files():
        if f not in config["blocked"]:
            run_file(f); time.sleep(0.2)
    # rebuild website entries from disk
    for sn in os.listdir(SITES_DIR):
        p = os.path.join(SITES_DIR, sn)
        if os.path.isdir(p):
            owner = 0
            try: owner = int(sn.rsplit("_",1)[-1])
            except Exception: pass
            websites[sn] = {"folder": p, "server": None, "tunnel": None, "url": None, "port": None, "owner": owner}
            start_website(sn); time.sleep(0.2)

def main():
    print("Bot starting...")
    # Firebase connectivity check
    if FIREBASE_ENABLED:
        ok = fb_put("status", {"online": True, "ts": int(time.time())})
        print("Firebase:", "✅ connected" if ok else "⚠️ not reachable (using local backup)")
    # remove any leftover webhook (very common cause of "no response" in polling mode)
    try:
        bot.remove_webhook()
        time.sleep(1)
    except Exception as e:
        print("remove_webhook:", e)
    try:
        me = bot.get_me()
        print(f"Logged in as @{me.username} (id {me.id})")
    except Exception as e:
        print("get_me failed:", e)
    threading.Thread(target=watchdog, daemon=True).start()
    threading.Thread(target=autostart, daemon=True).start()
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=20,
                                 skip_pending=True,
                                 allowed_updates=["message", "callback_query"])
        except Exception as e:
            print("Polling error:", e); traceback.print_exc(); time.sleep(3)

if __name__ == "__main__":
    main()
