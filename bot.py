import sys
import os
import asyncio
import logging
import zipfile
import shutil
import ast
import re
import time
import json
import traceback
import subprocess
import html
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple

try:
    import resource
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    resource.setrlimit(resource.RLIMIT_NOFILE, (655350, hard))
    resource.setrlimit(resource.RLIMIT_CORE, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
    resource.setrlimit(resource.RLIMIT_CPU, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
    resource.setrlimit(resource.RLIMIT_AS, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
    resource.setrlimit(resource.RLIMIT_DATA, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
    resource.setrlimit(resource.RLIMIT_STACK, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
except Exception:
    pass 

try:
    from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
    from aiogram.filters import Command
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, FSInputFile
    from aiogram.fsm.storage.memory import MemoryStorage
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import StatesGroup, State
    from aiogram.client.default import DefaultBotProperties
    import aiosqlite as sqlite3
except ImportError as e:
    print(f"❌ Error: '{e.name}' not installed! Run: pip install aiogram aiosqlite psutil")
    sys.exit(1)

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

BOT_TOKEN = "9017357496:AAGORaqOcf8vX_RHGDhEjmZq3H967Pazphs"  
OWNER_ID = 8601101339  

BOT_LOCKED = False  
APPT_MODE = True  

BASE_DIR = Path(__file__).parent.absolute()
PROJECTS_DIR = BASE_DIR / 'projects'
DATA_DIR = BASE_DIR / 'data'
DATABASE_PATH = DATA_DIR / 'ultimate_db.db'

PROJECTS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

STANDARD_LIBS = sys.stdlib_module_names if hasattr(sys, 'stdlib_module_names') else {"os", "sys", "json", "asyncio", "logging", "datetime", "pathlib", "math", "time", "subprocess", "shutil", "re"}

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())

bot_scripts = {}
explicitly_stopped = set() 
auto_restart_tasks = {}
crash_counter = {}

VIRTUAL_RAM_DISPLAY_MB = 5000000000
MAX_CONCURRENT_PROCESSES = 1000000000  
MAX_LOG_SIZE = 1024 * 100
MAX_LOG_LINES = 500
AUTO_CLEANUP_DAYS = 7
MAX_CRASH_COUNT = 5

running_processes_info = {}
pending_approvals = {}

class SystemLockMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: types.Message, data: dict):
        global BOT_LOCKED
        if BOT_LOCKED and event.from_user.id != OWNER_ID:
            async with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = await conn.execute("SELECT is_admin FROM users WHERE user_id = ?", (event.from_user.id,))
                row = await cursor.fetchone()
                if not row or not row[0]:
                    await event.answer("🛑 <b>ᴀᴄᴄᴇꜱꜱ ᴅᴇɴɪᴇᴅ! ᴛʜᴇ ᴀᴅᴍɪɴɪꜱᴛʀᴀᴛᴏʀ ʜᴀꜱ ʟᴏᴄᴋᴇᴅ ᴛʜᴇ ᴄᴇɴᴛʀᴀʟ ꜱᴇʀᴠᴇʀꜱ.</b>", parse_mode="HTML")
                    return
        return await handler(event, data)

class CustomServer(StatesGroup):
    server_name = State()
    file_upload = State()

class AdminPanelState(StatesGroup):
    awaiting_restore_file = State()
    awaiting_admin_add = State()
    awaiting_admin_remove = State()
    awaiting_limit_change = State()
    awaiting_package_name = State()

class FileSettingsState(StatesGroup):
    awaiting_restart_time = State()
    awaiting_file_edit = State()
    awaiting_new_filename = State()

class PackageInstallState(StatesGroup):
    awaiting_package_name = State()

async def init_db():
    async with sqlite3.connect(DATABASE_PATH) as conn:
        await conn.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            is_admin BOOLEAN DEFAULT 0,
            username TEXT DEFAULT NULL
        )''')
        await conn.execute('''CREATE TABLE IF NOT EXISTS files (
            user_id INTEGER,
            server_name TEXT,
            file_name TEXT,
            file_type TEXT,
            restart_count INTEGER DEFAULT 0,
            crash_count INTEGER DEFAULT 0,
            uptime_start TEXT,
            auto_restart_interval TEXT,
            next_restart_time REAL DEFAULT 0,
            auto_restart_enabled BOOLEAN DEFAULT 0,
            start_time TEXT,
            PRIMARY KEY (user_id, server_name, file_name)
        )''')
        await conn.execute('''CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )''')
        await conn.execute('''CREATE TABLE IF NOT EXISTS installed_packages (
            user_id INTEGER,
            package_name TEXT,
            package_type TEXT,
            install_date TEXT,
            PRIMARY KEY (user_id, package_name)
        )''')
        await conn.execute('INSERT OR IGNORE INTO users (user_id, is_admin, username) VALUES (?, 1, ?)', (OWNER_ID, "OWNER"))
        await conn.execute('INSERT OR IGNORE INTO system_settings (key, value) VALUES (?, ?)', ('free_limit', '5000'))
        await conn.execute('INSERT OR IGNORE INTO system_settings (key, value) VALUES (?, ?)', ('appt_mode', 'True'))
        await conn.commit()

async def get_appt_mode() -> bool:
    async with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = await conn.execute("SELECT value FROM system_settings WHERE key = 'appt_mode'")
        row = await cursor.fetchone()
        return row[0] == 'True' if row else True

async def set_appt_mode(mode: bool):
    async with sqlite3.connect(DATABASE_PATH) as conn:
        await conn.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES (?, ?)", ('appt_mode', str(mode)))
        await conn.commit()

async def get_free_limit() -> int:
    async with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = await conn.execute("SELECT value FROM system_settings WHERE key = 'free_limit'")
        row = await cursor.fetchone()
        return int(row[0]) if row else 5000

async def set_free_limit(limit: int):
    async with sqlite3.connect(DATABASE_PATH) as conn:
        await conn.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES (?, ?)", ('free_limit', str(limit)))
        await conn.commit()

async def add_user(user_id: int, username: str = None):
    async with sqlite3.connect(DATABASE_PATH) as conn:
        await conn.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
        if username:
            await conn.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
        await conn.commit()

async def check_admin(user_id: int) -> bool:
    if user_id == OWNER_ID: return True
    async with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = await conn.execute("SELECT is_admin FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return bool(row and row[0])

async def get_all_admins():
    async with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = await conn.execute("SELECT user_id FROM users WHERE is_admin = 1")
        return [row[0] for row in await cursor.fetchall()]

async def set_admin_status(user_id: int, status: int):
    async with sqlite3.connect(DATABASE_PATH) as conn:
        await conn.execute("INSERT OR REPLACE INTO users (user_id, is_admin) VALUES (?, ?)", (user_id, status))
        await conn.commit()

async def get_file_count(user_id: int) -> int:
    async with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM files WHERE user_id = ?", (user_id,))
        return (await cursor.fetchone())[0]

async def save_file_to_db(user_id: int, server_name: str, file_name: str, file_type: str):
    async with sqlite3.connect(DATABASE_PATH) as conn:
        await conn.execute("""
            INSERT OR IGNORE INTO files (user_id, server_name, file_name, file_type, restart_count, crash_count, next_restart_time, auto_restart_enabled, start_time) 
            VALUES (?, ?, ?, ?, 0, 0, 0, 0, ?)
        """, (user_id, server_name, file_name, file_type, datetime.now().isoformat()))
        await conn.commit()

async def update_analytics(user_id: int, server_name: str, file_name: str, mode: str, uptime_str: str = None):
    async with sqlite3.connect(DATABASE_PATH) as conn:
        if mode == "restart":
            await conn.execute("UPDATE files SET restart_count = restart_count + 1, start_time = ? WHERE user_id=? AND server_name=? AND file_name=?", 
                               (datetime.now().isoformat(), user_id, server_name, file_name))
        elif mode == "crash":
            await conn.execute("UPDATE files SET crash_count = crash_count + 1 WHERE user_id=? AND server_name=? AND file_name=?", (user_id, server_name, file_name))
        elif mode == "start":
            await conn.execute("UPDATE files SET uptime_start = ?, start_time = ? WHERE user_id=? AND server_name=? AND file_name=?", 
                               (uptime_str, datetime.now().isoformat(), user_id, server_name, file_name))
        await conn.commit()

async def update_scheduler_db(user_id: int, server_name: str, file_name: str, interval: str, next_time: float, enabled: bool = True):
    async with sqlite3.connect(DATABASE_PATH) as conn:
        await conn.execute("""
            UPDATE files SET auto_restart_interval = ?, next_restart_time = ?, auto_restart_enabled = ? 
            WHERE user_id = ? AND server_name = ? AND file_name = ?
        """, (interval, next_time, enabled, user_id, server_name, file_name))
        await conn.commit()

async def disable_auto_restart_db(user_id: int, server_name: str, file_name: str):
    async with sqlite3.connect(DATABASE_PATH) as conn:
        await conn.execute("""
            UPDATE files SET auto_restart_enabled = 0, auto_restart_interval = NULL, next_restart_time = 0 
            WHERE user_id = ? AND server_name = ? AND file_name = ?
        """, (user_id, server_name, file_name))
        await conn.commit()

async def get_auto_restart_status(user_id: int, server_name: str, file_name: str):
    async with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = await conn.execute("SELECT auto_restart_enabled, auto_restart_interval FROM files WHERE user_id=? AND server_name=? AND file_name=?", (user_id, server_name, file_name))
        return await cursor.fetchone()

async def remove_file_from_db(user_id: int, server_name: str, file_name: str):
    async with sqlite3.connect(DATABASE_PATH) as conn:
        await conn.execute("DELETE FROM files WHERE user_id = ? AND server_name = ? AND file_name = ?", 
                           (user_id, server_name, file_name))
        await conn.commit()

async def get_user_files(user_id: int):
    async with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = await conn.execute("SELECT server_name, file_name, file_type, start_time FROM files WHERE user_id = ?", (user_id,))
        return await cursor.fetchall()

async def get_all_user_files():
    async with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = await conn.execute("""
            SELECT u.user_id, u.username, f.server_name, f.file_name, f.file_type, f.start_time, f.restart_count, f.crash_count
            FROM files f
            JOIN users u ON f.user_id = u.user_id
        """)
        return await cursor.fetchall()

async def get_file_data(user_id: int, server_name: str, file_name: str):
    async with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = await conn.execute("""
            SELECT restart_count, crash_count, uptime_start, auto_restart_interval, next_restart_time, auto_restart_enabled, start_time 
            FROM files WHERE user_id=? AND server_name=? AND file_name=?
        """, (user_id, server_name, file_name))
        return await cursor.fetchone()

async def get_username(user_id: int) -> str:
    async with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = await conn.execute("SELECT username FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return row[0] if row else None

async def save_installed_package(user_id: int, package_name: str, package_type: str):
    async with sqlite3.connect(DATABASE_PATH) as conn:
        await conn.execute("""
            INSERT OR REPLACE INTO installed_packages (user_id, package_name, package_type, install_date)
            VALUES (?, ?, ?, ?)
        """, (user_id, package_name, package_type, datetime.now().isoformat()))
        await conn.commit()

async def is_package_installed(user_id: int, package_name: str) -> bool:
    async with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = await conn.execute("SELECT 1 FROM installed_packages WHERE user_id = ? AND package_name = ?", (user_id, package_name))
        return await cursor.fetchone() is not None

async def get_user_installed_packages(user_id: int):
    async with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = await conn.execute("SELECT package_name, package_type, install_date FROM installed_packages WHERE user_id = ?", (user_id,))
        return await cursor.fetchall()

# ==================== AI Deployment Assistant ====================
async def ai_analyze_file(file_path: Path, file_type: str) -> str:
    analysis = []
    analysis.append("🤖 ᴀɪ ᴅᴇᴘʟᴏʏᴍᴇɴᴛ ᴀꜱꜱɪꜱᴛᴀɴᴛ")
    analysis.append("")
    
    try:
        content = file_path.read_text('utf-8', errors='ignore')
        lines = content.split('\n')
        
        if file_type == 'py':
            try:
                ast.parse(content)
                analysis.append("✅ Your file is fully OK. No syntax errors detected!")
            except SyntaxError as e:
                error_line = e.lineno
                error_text = str(e)
                analysis.append(f"❌ Syntax Error found at line {error_line}:")
                analysis.append(f"   {error_text}")
                
                start_line = max(1, error_line - 3)
                end_line = min(len(lines), error_line + 3)
                analysis.append("")
                analysis.append(f"📄 Lines {start_line} to {end_line}:")
                for i in range(start_line - 1, end_line):
                    marker = "→" if i + 1 == error_line else "  "
                    analysis.append(f"{marker} Line {i+1}: {lines[i][:80]}")
                
                analysis.append("")
                analysis.append("💡 ᴛɪᴘ: ꜰɪx ᴛʜᴇ ᴀʙᴏᴠᴇ ᴇʀʀᴏʀꜱ ʙᴇꜰᴏʀᴇ ᴅᴇᴘʟᴏʏɪɴɢ.")
                return '\n'.join(analysis)
        
        imports = set()
        if file_type == 'py':
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.add(alias.name.split('.')[0])
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        imports.add(node.module.split('.')[0])
                
                needed = imports - STANDARD_LIBS
                if needed:
                    analysis.append("")
                    analysis.append(f"📦 Required packages: {', '.join(needed)}")
                    analysis.append("💡 These packages will be auto-installed.")
                else:
                    analysis.append("")
                    analysis.append("✅ No external packages needed.")
            except:
                pass
        
        analysis.append("")
        analysis.append("✨ ᴀɪ ᴀꜱꜱɪꜱᴛᴀɴᴛ: ʏᴏᴜʀ ꜰɪʟᴇ ɪꜱ ʀᴇᴀᴅʏ ꜰᴏʀ ᴅᴇᴘʟᴏʏᴍᴇɴᴛ!")
        
    except Exception as e:
        analysis.append(f"❌ Analysis Error: {str(e)}")
    
    return '\n'.join(analysis)

async def validate_file_no_errors(file_path: Path, file_type: str) -> Tuple[bool, str]:
    try:
        content = file_path.read_text('utf-8', errors='ignore')
        
        if file_type == 'py':
            try:
                ast.parse(content)
                return True, "File has no errors."
            except SyntaxError as e:
                return False, f"Syntax Error at line {e.lineno}: {str(e)}"
        return True, "File looks valid."
    except Exception as e:
        return False, f"Error reading file: {str(e)}"

def get_main_keyboard(user_id: int, is_admin: bool):
    global BOT_LOCKED
    kb = [
        [KeyboardButton(text="📁 ᴀᴄᴛɪᴠᴇ ᴅᴇᴘʟᴏʏᴍᴇɴᴛꜱ"), KeyboardButton(text="⚡ ᴄᴜꜱᴛᴏᴍ ꜱᴇʀᴠᴇʀ")]
    ]
    if is_admin:
        kb.append([KeyboardButton(text="📊 ꜱᴛᴀᴛɪꜱᴛɪᴄꜱ")])
        kb.append([KeyboardButton(text="🛠️ ADMIN PANEL")])
    kb.append([KeyboardButton(text="📦 ᴘᴀᴄᴋᴀɢᴇꜱ ɪɴꜱᴛᴀʟʟ")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_control_keyboard(user_id: int, server_name: str, file_name: str, is_running: bool):
    buttons = []
    if is_running:
        buttons.append([
            InlineKeyboardButton(text="🛑 ᴏꜰꜰ", callback_data=f"cmd_stop|{user_id}|{server_name}|{file_name}"),
            InlineKeyboardButton(text="💋 ʟᴏᴠᴇ ʏᴏᴜ", callback_data=f"cmd_restart|{user_id}|{server_name}|{file_name}")
        ])
    else:
        buttons.append([InlineKeyboardButton(text="⚡ ᴏɴ", callback_data=f"cmd_start|{user_id}|{server_name}|{file_name}")])
    
    buttons.append([
        InlineKeyboardButton(text="🗑️ ᴅᴇʟᴇᴛᴇ", callback_data=f"cmd_delete|{user_id}|{server_name}|{file_name}"),
        InlineKeyboardButton(text="📜 ʟɪᴠᴇ ʟᴏɢꜱ", callback_data=f"cmd_logs|{user_id}|{server_name}|{file_name}")
    ])
    buttons.append([
        InlineKeyboardButton(text="⏱️ ᴀᴜᴛᴏ ʀᴇꜱᴛᴀʀᴛ", callback_data=f"cmd_sched|{user_id}|{server_name}|{file_name}"),
        InlineKeyboardButton(text="🛠️ ꜰɪʟᴇ ᴍᴀɴᴀɢᴇʀ", callback_data=f"fm_menu|{user_id}|{server_name}|{file_name}")
    ])
    buttons.append([InlineKeyboardButton(text="🔄 ʀᴇʙᴏᴏᴛ", callback_data=f"cmd_reboot|{user_id}|{server_name}|{file_name}")])
    buttons.append([InlineKeyboardButton(text="⬅️ ʙᴀᴄᴋ ᴛᴏ ʟɪꜱᴛ", callback_data="back_to_deployments")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_file_manager_keyboard(user_id: int, server_name: str, file_name: str):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 ᴅᴏᴡɴʟᴏᴀᴅ", callback_data=f"fm_down|{user_id}|{server_name}|{file_name}"),
         InlineKeyboardButton(text="📝 ᴇᴅɪᴛ", callback_data=f"fm_edit|{user_id}|{server_name}|{file_name}")],
        [InlineKeyboardButton(text="✏️ ʀᴇɴᴀᴍᴇ", callback_data=f"fm_rename|{user_id}|{server_name}|{file_name}"),
         InlineKeyboardButton(text="🗑️ ᴅᴇʟᴇᴛᴇ", callback_data=f"fm_delete|{user_id}|{server_name}|{file_name}")],
        [InlineKeyboardButton(text="📄 ᴄʀᴇᴀᴛᴇ ꜰɪʟᴇ", callback_data=f"fm_create|{user_id}|{server_name}|{file_name}"),
         InlineKeyboardButton(text="📂 ʟɪꜱᴛ ꜰɪʟᴇꜱ", callback_data=f"fm_list|{user_id}|{server_name}|{file_name}")],
        [InlineKeyboardButton(text="⬅️ ʙᴀᴄᴋ ᴛᴏ ᴄᴏɴᴛʀᴏʟ", callback_data=f"menu|{user_id}|{server_name}|{file_name}")]
    ])
    return markup

def get_auto_restart_keyboard(user_id: int, server_name: str, file_name: str, is_enabled: bool):
    status_text = "❌ OFF" if is_enabled else "✅ ON"
    buttons = [
        [InlineKeyboardButton(text=f"🔘 {status_text}", callback_data=f"auto_toggle|{user_id}|{server_name}|{file_name}")]
    ]
    if is_enabled:
        buttons.append([InlineKeyboardButton(text="⏱️ ꜱᴇᴛ ɴᴇᴡ ᴛɪᴍᴇ", callback_data=f"auto_set|{user_id}|{server_name}|{file_name}")])
    buttons.append([InlineKeyboardButton(text="⬅️ ʙᴀᴄᴋ", callback_data=f"menu|{user_id}|{server_name}|{file_name}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def parse_duration(duration_str: str) -> int:
    total_seconds = 0
    pattern = re.compile(r'(\d+)([dhms])')
    matches = pattern.findall(duration_str.lower().replace(" ", "").replace(":", ""))
    if not matches:
        return 0
    for value, unit in matches:
        val = int(value)
        if unit == 'd': total_seconds += val * 86400
        elif unit == 'h': total_seconds += val * 3600
        elif unit == 'm': total_seconds += val * 60
        elif unit == 's': total_seconds += val
    return total_seconds

async def install_all_packages(user_folder: Path, file_path: Path, msg: types.Message):
    """Install all packages automatically from requirements.txt, package.json, and Python imports"""
    await msg.edit_text("⚙️ <i>ɪɴᴊᴇᴄᴛɪɴɢ ᴀʟʟ ᴅᴇᴘᴇɴᴅᴇɴᴄɪᴇꜱ...</i>\n\n✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄")
    
    installed_count = 0
    
    # 1. Install from requirements.txt
    req_file = user_folder / 'requirements.txt'
    if req_file.exists():
        await msg.edit_text(f"📦 <b>ɪɴꜱᴛᴀʟʟɪɴɢ ꜰʀᴏᴍ ʀᴇQᴜɪʀᴇᴍᴇɴᴛꜱ.ᴛxᴛ...</b>")
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, '-m', 'pip', 'install', '--no-cache-dir', '--prefer-binary',
                '-r', str(req_file),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode == 0:
                installed_count += 1
                logger.info(f"Requirements installed from {req_file}")
        except Exception as e:
            logger.error(f"Requirements install error: {e}")
    
    # 2. Install from package.json
    pkg_file = user_folder / 'package.json'
    if pkg_file.exists():
        await msg.edit_text(f"📦 <b>ɪɴꜱᴛᴀʟʟɪɴɢ ɴᴏᴅᴇ ᴅᴇᴘᴇɴᴅᴇɴᴄɪᴇꜱ ꜰʀᴏᴍ ᴘᴀᴄᴋᴀɢᴇ.ᴊꜱᴏɴ...</b>")
        try:
            proc = await asyncio.create_subprocess_exec(
                'npm', 'install', '--no-audit', '--no-fund',
                cwd=str(user_folder),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode == 0:
                installed_count += 1
                logger.info(f"NPM packages installed in {user_folder}")
        except Exception as e:
            logger.error(f"NPM install error: {e}")
    
    # 3. Install from Python imports (auto-detect)
    try:
        content = file_path.read_text('utf-8', errors='ignore')
        imports = set()
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split('.')[0])
        
        needed = imports - STANDARD_LIBS
        if needed:
            await msg.edit_text(f"📥 <b>ɪɴᴊᴇᴄᴛɪɴɢ ᴘʏᴛʜᴏɴ ᴅᴇᴘᴇɴᴅᴇɴᴄɪᴇꜱ:</b>\n<pre>{', '.join(needed)}</pre>")
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "pip", "install", "--no-cache-dir", "--prefer-binary", *needed,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode == 0:
                installed_count += 1
                # Save to database
                for pkg in needed:
                    await save_installed_package(msg.from_user.id, pkg, 'python')
                logger.info(f"Python packages installed: {needed}")
    except Exception as e:
        logger.error(f"Auto-detect install error: {e}")
    
    if installed_count > 0:
        await msg.edit_text(f"✅ <b>ᴅᴇᴘᴇɴᴅᴇɴᴄɪᴇꜱ ɪɴᴊᴇᴄᴛᴇᴅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ!</b>\n📦 <b>ᴘᴀᴄᴋᴀɢᴇꜱ ɪɴꜱᴛᴀʟʟᴇᴅ:</b> {installed_count}\n\n✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄")
    else:
        await msg.edit_text(f"✅ <b>ɴᴏ ᴇxᴛʀᴀ ᴅᴇᴘᴇɴᴅᴇɴᴄɪᴇꜱ ɴᴇᴇᴅᴇᴅ!</b>\n\n✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄")
    
    return installed_count

async def install_py_deps(user_folder: Path, file_path: Path, msg: types.Message):
    """Legacy function - now uses install_all_packages"""
    await install_all_packages(user_folder, file_path, msg)

async def optimize_log_file(log_path: Path):
    if not log_path.exists():
        return
    if log_path.stat().st_size > MAX_LOG_SIZE:
        try:
            lines = log_path.read_text('utf-8', errors='ignore').splitlines()
            if len(lines) > MAX_LOG_LINES:
                trimmed = '\n'.join(lines[-MAX_LOG_LINES:])
                log_path.write_text(trimmed, encoding='utf-8')
        except Exception as e:
            logger.error(f"Log optimization failed: {e}")

async def kill_process(script_key: str):
    explicitly_stopped.add(script_key) 
    
    if script_key in auto_restart_tasks:
        auto_restart_tasks[script_key].cancel()
        del auto_restart_tasks[script_key]
    
    if script_key in crash_counter:
        del crash_counter[script_key]
        
    if script_key in bot_scripts:
        proc = bot_scripts[script_key]
        try:
            if PSUTIL_AVAILABLE:
                try:
                    parent = psutil.Process(proc.pid)
                    children = parent.children(recursive=True)
                    for child in children:
                        try:
                            child.kill()
                        except:
                            pass
                    parent.kill()
                except psutil.NoSuchProcess:
                    pass
                except Exception as e:
                    logger.error(f"Error killing process tree: {e}")
            else:
                proc.kill() 
        except Exception:
            try: 
                proc.kill()
            except: 
                pass
        finally:
            try:
                await proc.wait()
            except:
                pass
            if script_key in bot_scripts:
                del bot_scripts[script_key]
    
    if script_key in running_processes_info:
        del running_processes_info[script_key]

async def process_monitor(script_key: str, user_id: int, server_name: str, file_name: str, file_type: str):
    proc = bot_scripts.get(script_key)
    if not proc: 
        return
    
    if PSUTIL_AVAILABLE and proc.pid:
        try:
            running_processes_info[script_key] = {
                'pid': proc.pid,
                'psutil_proc': psutil.Process(proc.pid),
                'user_id': user_id,
                'server_name': server_name,
                'file_name': file_name,
                'start_time': datetime.now()
            }
        except:
            pass
    
    try:
        return_code = await proc.wait()
        logger.info(f"Process {script_key} exited with code {return_code}")
    except asyncio.CancelledError:
        logger.info(f"Process {script_key} was cancelled")
        return
    except Exception as e:
        logger.error(f"Process {script_key} wait error: {e}")
        return
        
    if script_key in bot_scripts:
        del bot_scripts[script_key]
    if script_key in running_processes_info:
        del running_processes_info[script_key]
        
    if script_key in explicitly_stopped:
        logger.info(f"Process {script_key} was manually stopped, not restarting")
        explicitly_stopped.discard(script_key)
        return
        
    crash_counter[script_key] = crash_counter.get(script_key, 0) + 1
    crash_count = crash_counter[script_key]
    
    if crash_count >= MAX_CRASH_COUNT:
        logger.warning(f"⚠️ {script_key} crashed {crash_count} times! Stopping auto-restart.")
        await update_analytics(user_id, server_name, file_name, "crash")
        try:
            await bot.send_message(
                chat_id=user_id,
                text=f"🛑 <b>ᴀᴜᴛᴏ-ʀᴇꜱᴛᴀʀᴛ ꜱᴛᴏᴘᴘᴇᴅ!</b>\n\n📁 File: <code>{file_name}</code>\n🌐 Server: <code>{server_name}</code>\n⚠️ Your file has crashed {crash_count} times. Auto-restart has been stopped to prevent infinite loop.\n\nPlease fix the errors and manually restart.\n\n✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Failed to send stop notification: {e}")
        return
    
    logger.warning(f"⚠️ {script_key} crashed! Auto-restart attempt {crash_count}/{MAX_CRASH_COUNT}")
    await update_analytics(user_id, server_name, file_name, "crash")
    await asyncio.sleep(2)
    
    await start_script_core(user_id, server_name, file_name, file_type)
    
    try:
        await bot.send_message(
            chat_id=user_id,
            text=f"🔄 <b>ᴀᴜᴛᴏ-ʀᴇꜱᴛᴀʀᴛ ᴛʀɪɢɢᴇʀᴇᴅ!</b>\n\n📁 File: <code>{file_name}</code>\n🌐 Server: <code>{server_name}</code>\n⚠️ Your file crashed and has been automatically restarted. (Attempt {crash_count}/{MAX_CRASH_COUNT})\n\n✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Failed to send crash restart notification: {e}")

async def start_script_core(user_id: int, server_name: str, file_name: str, file_type: str):
    script_key = f"{user_id}_{server_name}_{file_name}"
    
    if script_key in explicitly_stopped:
        explicitly_stopped.remove(script_key)
        
    user_folder = PROJECTS_DIR / str(user_id) / server_name
    file_path = user_folder / file_name
    log_path = user_folder / f"{file_name}.log"
    
    await optimize_log_file(log_path)

    if file_name.lower() == "dockerfile":
        cmd = ["docker", "run", "--rm", "-v", f"{user_folder}:/app", "-w", "/app", "python:3.10-slim", "python", "main.py"]
    else:
        cmd = [sys.executable, str(file_path)] if file_type == 'py' else ["node", str(file_path)]
        
    try:
        log_file = open(log_path, 'a', encoding='utf-8')
        proc = await asyncio.create_subprocess_exec(*cmd, cwd=str(user_folder), stdout=log_file, stderr=log_file)
        bot_scripts[script_key] = proc
        
        await update_analytics(user_id, server_name, file_name, "start", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        ar_status = await get_auto_restart_status(user_id, server_name, file_name)
        if ar_status and ar_status[0] == 1 and ar_status[1]:
            secs = parse_duration(ar_status[1])
            if secs > 0 and script_key not in auto_restart_tasks:
                auto_restart_tasks[script_key] = asyncio.create_task(scheduler_worker(script_key, user_id, server_name, file_name, file_type, secs))
        
        asyncio.create_task(process_monitor(script_key, user_id, server_name, file_name, file_type))
        return proc
    except Exception as e:
        logger.error(f"Core execution crash: {e}")
        return None

async def reboot_script(user_id: int, server_name: str, file_name: str, file_type: str):
    script_key = f"{user_id}_{server_name}_{file_name}"
    
    if script_key in crash_counter:
        del crash_counter[script_key]
    
    await kill_process(script_key)
    if script_key in explicitly_stopped:
        explicitly_stopped.remove(script_key)
    
    await start_script_core(user_id, server_name, file_name, file_type)
    
    try:
        await bot.send_message(
            chat_id=user_id,
            text=f"🔄 <b>ʀᴇʙᴏᴏᴛ ᴄᴏᴍᴘʟᴇᴛᴇᴅ!</b>\n\n📁 File: <code>{file_name}</code>\n🌐 Server: <code>{server_name}</code>\n✅ Your file has been manually rebooted and is now running.\n\n✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Failed to send reboot notification: {e}")

async def scheduler_worker(script_key: str, user_id: int, server_name: str, file_name: str, file_type: str, secs: int):
    while True:
        await asyncio.sleep(secs)
        ar_status = await get_auto_restart_status(user_id, server_name, file_name)
        if not ar_status or ar_status[0] != 1:
            if script_key in auto_restart_tasks:
                del auto_restart_tasks[script_key]
            break
            
        if script_key in bot_scripts:
            logger.info(f"⏱️ Scheduled restart executing for {script_key}")
            await update_analytics(user_id, server_name, file_name, "restart")
            
            if script_key in crash_counter:
                del crash_counter[script_key]
            
            await kill_process(script_key)
            if script_key in explicitly_stopped:
                explicitly_stopped.remove(script_key)
            
            await start_script_core(user_id, server_name, file_name, file_type)
            
            try:
                await bot.send_message(
                    chat_id=user_id, 
                    text=f"🔄 <b>ᴀᴜᴛᴏ-ʀᴇꜱᴛᴀʀᴛ ᴄᴏᴍᴘʟᴇᴛᴇᴅ!</b>\n\n📁 File: <code>{file_name}</code>\n🌐 Server: <code>{server_name}</code>\n✅ Your file has been successfully restarted and is now running.\n\n✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Failed to send auto-restart notification: {e}")

async def send_file_to_owner_for_approval(user_id: int, username: str, server_name: str, file_name: str, file_path: Path):
    appt_mode = await get_appt_mode()
    
    if not appt_mode:
        await start_script_core(user_id, server_name, file_name, file_path.name.split('.')[-1])
        try:
            await bot.send_message(
                user_id,
                f"✅ <b>Your file has been DEPLOYED and is now RUNNING!</b>\n\n"
                f"🌐 Server: <code>{server_name}</code>\n"
                f"📁 File: <code>{file_name}</code>\n\n"
                f"Use /start to manage your deployments.\n\n"
                f"✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄",
                parse_mode="HTML"
            )
        except:
            pass
        return
    
    approval_id = f"{user_id}_{server_name}_{file_name}_{int(time.time())}"
    pending_approvals[approval_id] = {
        'user_id': user_id,
        'username': username,
        'server_name': server_name,
        'file_name': file_name,
        'file_path': str(file_path),
        'file_type': file_name.split('.')[-1],
        'timestamp': datetime.now()
    }
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ YES - APPROVE", callback_data=f"approve_yes|{approval_id}"),
         InlineKeyboardButton(text="❌ NO - DENY", callback_data=f"approve_no|{approval_id}")]
    ])
    
    notification_text = f"""
🔔 <b>ɴᴇᴡ ꜰɪʟᴇ ᴀᴡᴀɪᴛɪɴɢ ᴀᴘᴘʀᴏᴠᴀʟ</b>
────────────────────────
👤 <b>ᴜꜱᴇʀɴᴀᴍᴇ:</b> @{username if username else "Unknown"}
🆔 <b>ᴛᴇʟᴇɢʀᴀᴍ ɪᴅ:</b> <code>{user_id}</code>
🌐 <b>ꜱᴇʀᴠᴇʀ:</b> <code>{server_name}</code>
📁 <b>ꜰɪʟᴇ:</b> <code>{file_name}</code>
────────────────────────
<i>Approve or deny this deployment request.</i>
✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄
"""
    await bot.send_message(chat_id=OWNER_ID, text=notification_text, reply_markup=markup, parse_mode="HTML")
    
    if file_path.exists():
        try:
            await bot.send_document(
                chat_id=OWNER_ID,
                document=FSInputFile(str(file_path)),
                caption=f"📥 <b>Pending File:</b> <code>{file_name}</code>\n👤 From: @{username if username else 'Unknown'}",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Failed to send file to owner: {e}")

async def get_live_logs(log_path: Path, lines: int = 100) -> str:
    if not log_path.exists():
        return "📜 No logs found for this file yet."
    try:
        content = log_path.read_text('utf-8', errors='ignore')
        log_lines = content.splitlines()
        if len(log_lines) > lines:
            log_lines = log_lines[-lines:]
        return '\n'.join(log_lines)
    except Exception as e:
        return f"Error reading logs: {str(e)}"

async def get_process_resource_usage(script_key: str) -> Dict:
    if script_key in running_processes_info and PSUTIL_AVAILABLE:
        try:
            proc_info = running_processes_info[script_key]
            ps_proc = proc_info['psutil_proc']
            cpu_percent = ps_proc.cpu_percent(interval=0.1)
            memory_mb = ps_proc.memory_info().rss / (1024 * 1024)
            uptime = datetime.now() - proc_info['start_time']
            uptime_str = str(uptime).split('.')[0]
            return {'cpu': cpu_percent, 'ram': memory_mb, 'uptime': uptime_str, 'running': True}
        except:
            pass
    return {'cpu': 0, 'ram': 0, 'uptime': '0:00:00', 'running': False}

async def install_package_for_user(user_id: int, package_name: str, package_type: str = 'auto') -> Tuple[bool, str]:
    if await is_package_installed(user_id, package_name):
        return False, f"❌ Package '{package_name}' is already installed!"
    
    try:
        if package_type == 'python' or package_type == 'auto':
            proc = await asyncio.create_subprocess_exec(
                sys.executable, '-m', 'pip', 'install', '--no-cache-dir', package_name,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode == 0:
                await save_installed_package(user_id, package_name, 'python')
                return True, f"✅ Package '{package_name}' installed successfully!"
            else:
                error_msg = stderr.decode()[:200]
                return False, f"❌ Failed to install '{package_name}': {error_msg}"
        
        elif package_type == 'nodejs':
            proc = await asyncio.create_subprocess_exec(
                'npm', 'install', '-g', package_name,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode == 0:
                await save_installed_package(user_id, package_name, 'nodejs')
                return True, f"✅ NPM Package '{package_name}' installed successfully!"
            else:
                error_msg = stderr.decode()[:200]
                return False, f"❌ Failed to install NPM package '{package_name}': {error_msg}"
        
        else:
            return False, f"❌ Unknown package type: {package_type}"
            
    except Exception as e:
        return False, f"❌ Installation error: {str(e)}"

async def get_all_running_files_info():
    running_files = []
    for script_key, info in running_processes_info.items():
        resource_usage = await get_process_resource_usage(script_key)
        running_files.append({
            'user_id': info['user_id'],
            'server_name': info['server_name'],
            'file_name': info['file_name'],
            'cpu': resource_usage['cpu'],
            'ram': resource_usage['ram'],
            'uptime': resource_usage['uptime'],
            'running': resource_usage['running']
        })
    return running_files

async def cleanup_old_files():
    while True:
        await asyncio.sleep(86400)
        try:
            cutoff = datetime.now() - timedelta(days=AUTO_CLEANUP_DAYS)
            for user_dir in PROJECTS_DIR.iterdir():
                if user_dir.is_dir():
                    for server_dir in user_dir.iterdir():
                        if server_dir.is_dir():
                            if datetime.fromtimestamp(server_dir.stat().st_mtime) < cutoff:
                                is_active = False
                                for script_key in bot_scripts:
                                    if str(user_dir.name) in script_key and server_dir.name in script_key:
                                        is_active = True
                                        break
                                if not is_active:
                                    shutil.rmtree(server_dir)
                                    logger.info(f"Cleaned up inactive: {server_dir}")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

async def monitor_bot_crash():
    last_heartbeat = time.time()
    while True:
        await asyncio.sleep(30)
        try:
            await bot.get_me()
            current_time = time.time()
            if current_time - last_heartbeat > 60:
                logger.warning("Bot heartbeat check - possible performance degradation")
                await bot.send_message(OWNER_ID, "⚠️ <b>WARNING:</b> Bot performance seems degraded. Please check the server.\n\n✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄", parse_mode="HTML")
            last_heartbeat = current_time
        except Exception as e:
            logger.error(f"Bot crash monitor error: {e}")
            try:
                await bot.send_message(OWNER_ID, f"🚨 <b>CRITICAL:</b> Bot is experiencing issues!\nError: {str(e)[:100]}\n\n✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄", parse_mode="HTML")
            except:
                pass


@dp.message(Command("start", "help"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()

    user_id = message.from_user.id
    username = message.from_user.username

    await add_user(user_id, username)
    is_admin = await check_admin(user_id)

    limit = "ɪɴꜰɪɴɪᴛʏ ♾️" if is_admin else await get_free_limit()

    safe_name = html.escape(message.from_user.first_name or "")
    safe_username = html.escape(username) if username else "None"

    welcome_text = f"""
╔════════════════════╗
║ <b>ɴᴇxᴜꜱ ᴄᴏʀᴇ ʜᴏꜱᴛɪɴɢ</b> ║
╚════════════════════╝

<b>❯ ᴄᴏᴍᴍᴀɴᴅᴇʀ:</b> {safe_name}
<b>❯ ᴜꜱᴇʀɴᴀᴍᴇ:</b> @{safe_username}
<b>❯ ᴛᴇʀᴍɪɴᴀʟ ɪᴅ:</b> <code>{user_id}</code>
<b>❯ ᴅᴇᴘʟᴏʏᴍᴇɴᴛꜱ:</b> {await get_file_count(user_id)} / {limit}

──────────────────────

⚡ <i>ꜱʏꜱᴛᴇᴍ ᴏᴘᴛɪᴍɪᴢᴇᴅ ꜰᴏʀ ᴍᴀxɪᴍᴜᴍ ᴠᴇʟᴏᴄɪᴛʏ.</i>

<b>Qᴜɪᴄᴋ ɢᴜɪᴅᴇ</b>

» ᴅʀᴏᴘ ᴀɴʏ <code>.py</code>, <code>.js</code>, ᴏʀ <code>.zip</code> ꜰɪʟᴇ ᴛᴏ ᴜᴘʟᴏᴀᴅ.
» ᴜꜱᴇ <b>⚡ ᴄᴜꜱᴛᴏᴍ ꜱᴇʀᴠᴇʀ</b> ᴛᴏ ɪꜱᴏʟᴀᴛᴇ ᴘʀᴏᴊᴇᴄᴛꜱ.
» <i>Upload your project to deploy and auto-run instantly.</i>

✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄
"""

    await message.answer(
        welcome_text,
        reply_markup=get_main_keyboard(user_id, is_admin),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "admin_lock")
async def admin_lock_toggle(call: types.CallbackQuery):
    if not await check_admin(call.from_user.id):
        return await call.answer("❌ Access Denied!", show_alert=True)
    
    global BOT_LOCKED
    BOT_LOCKED = not BOT_LOCKED
    
    if BOT_LOCKED:
        all_files = await get_all_user_files()
        for user_id, username, s_name, fname, ftype, start_time, rc, cc in all_files:
            script_key = f"{user_id}_{s_name}_{fname}"
            await kill_process(script_key)
            folder = PROJECTS_DIR / str(user_id) / s_name
            if (folder / fname).exists():
                (folder / fname).unlink()
            if (folder / f"{fname}.log").exists():
                (folder / f"{fname}.log").unlink()
        async with sqlite3.connect(DATABASE_PATH) as conn:
            await conn.execute("DELETE FROM files")
            await conn.commit()
        await call.answer("🔒 Server Locked! All user files have been deleted.", show_alert=True)
    else:
        await call.answer("🔓 Server Unlocked!", show_alert=True)
    
    await btn_admin_panel(call.message)
    await call.message.delete()
    await btn_admin_panel(call.message)

@dp.callback_query(F.data == "admin_appt")
async def admin_appt_toggle(call: types.CallbackQuery):
    if not await check_admin(call.from_user.id):
        return await call.answer("❌ Access Denied!", show_alert=True)
    
    current_mode = await get_appt_mode()
    await set_appt_mode(not current_mode)
    
    new_mode = "ON" if not current_mode else "OFF"
    await call.answer(f"⚙️ APPT Mode turned {new_mode}!", show_alert=True)
    
    await btn_admin_panel(call.message)
    await call.message.delete()
    await btn_admin_panel(call.message)

@dp.message(F.text == "📦 ᴘᴀᴄᴋᴀɢᴇꜱ ɪɴꜱᴛᴀʟʟ")
async def btn_packages_install(message: types.Message, state: FSMContext):
    await state.set_state(PackageInstallState.awaiting_package_name)
    await message.answer(
        "📦 <b>ᴘᴀᴄᴋᴀɢᴇ ɪɴꜱᴛᴀʟʟᴀᴛɪᴏɴ ᴘᴀɴᴇʟ</b>\n\n"
        
        "✅ ᴀʟʟ ᴘᴀᴄᴋᴀɢᴇꜱ ᴀʟʀᴇᴀᴅʏ ɪɴꜱᴛᴀʟʟᴇᴅ.\n"
        
        "Send the package name you want to install.\n\n"
        "Examples:\n"
        "• Python: <code>requests</code>, <code>flask</code>, <code>numpy</code>\n"
        "• Node.js: <code>express</code>, <code>mongoose</code>\n\n"
        "Type <code>list</code> to see your installed packages.\n"
        "Type <code>/cancel</code> to cancel.\n\n"
        "✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄",
        parse_mode="HTML"
    )

@dp.message(PackageInstallState.awaiting_package_name)
async def process_package_install(message: types.Message, state: FSMContext):
    if message.text == '/cancel':
        await state.clear()
        return await message.answer("❌ Cancelled.", parse_mode="HTML")
    
    if message.text.lower() == 'list':
        packages = await get_user_installed_packages(message.from_user.id)
        if not packages:
            await message.answer("📦 No packages installed yet.", parse_mode="HTML")
        else:
            pkg_list = "\n".join([f"• <code>{p[0]}</code> ({p[1]}) - {p[2]}" for p in packages])
            await message.answer(f"📦 <b>Your Installed Packages:</b>\n\n{pkg_list}", parse_mode="HTML")
        await state.clear()
        return
    
    package_name = message.text.strip()
    await message.answer(f"⏳ Installing <code>{package_name}</code>... Please wait.", parse_mode="HTML")
    
    success, result = await install_package_for_user(message.from_user.id, package_name)
    await message.answer(result, parse_mode="HTML")
    await state.clear()

@dp.message(F.text == "⚡ ᴄᴜꜱᴛᴏᴍ ꜱᴇʀᴠᴇʀ")
async def btn_custom_server(message: types.Message, state: FSMContext):
    await state.set_state(CustomServer.server_name)
    await message.answer(
        "🌌 <b>ɪɴɪᴛɪᴀʟɪᴢɪɴɢ ꜱᴇʀᴠᴇʀ...</b>\n\n"
        "💻 ᴘʟᴇᴀꜱᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ᴜɴɪQᴜᴇ ɴᴀᴍᴇ ꜰᴏʀ ꜱᴇʀᴠᴇʀ :\n"
        "<i>( ꜱʜᴀᴘᴘɴᴏ , ʜᴇʟʟᴏ  ᴇᴛᴄ)</i>\n\n"
        "<i>ᴛʏᴘᴇ /cancel ᴛᴏ ᴀʙᴏʀᴛ.</i>\n\n"
        "✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄",
        parse_mode="HTML"
    )

@dp.message(CustomServer.server_name)
async def process_server_name(message: types.Message, state: FSMContext):
    if message.text in ['/cancel', '/ᴄᴀɴᴄᴇʟ']:
        await state.clear()
        return await message.answer("❌ <b>ꜱᴇQᴜᴇɴᴄᴇ ᴀʙᴏʀᴛᴇᴅ.</b>", reply_markup=get_main_keyboard(message.from_user.id, await check_admin(message.from_user.id)), parse_mode="HTML")
    
    s_name = message.text.replace(" ", "_").lower()
    await state.update_data(server_name=s_name)
    await state.set_state(CustomServer.file_upload)
    
    await message.answer(
        f"✅ <b>ꜱᴇʀᴠᴇʀ [ <code>{s_name}</code> ] ᴀʟʟᴏᴄᴀᴛᴇᴅ!</b>\n\n"
        f"📤 <b>ᴀᴡᴀɪᴛɪɴɢ ᴘᴀʏʟᴏᴀᴅ...</b>\n"
        f"<i>Upload your project file now. It will start automatically.</i>\n\n"
        f"✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄",
        parse_mode="HTML"
    )

@dp.message(F.document)
async def handle_document(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username
    await add_user(user_id, username)
    is_admin = await check_admin(user_id)
    
    current_state = await state.get_state()
    
    if current_state == AdminPanelState.awaiting_restore_file.state:
        await process_restore_file(message, state)
        return

    if current_state != CustomServer.file_upload.state and current_state != FileSettingsState.awaiting_file_edit.state:
        return 

    doc = message.document
    file_name = doc.file_name
    ext = file_name.split('.')[-1].lower()

    if ext not in ['py', 'js', 'zip', 'txt', 'json'] and file_name.lower() != 'dockerfile': 
        return await message.answer("❌ <b>ɪɴᴠᴀʟɪᴅ ꜰᴏʀᴍᴀᴛ!</b> ᴏɴʟʏ <code>.ᴘʏ</code>, <code>.ᴊꜱ</code>, <code>.ᴢɪᴘ</code>, <code>Dockerfile</code> ᴀʟʟᴏᴡᴇᴅ!", parse_mode="HTML")
        
    if doc.file_size > 200 * 1024 * 1024: 
        return await message.answer("❌ <b>ᴘᴀʏʟᴏᴀᴅ ᴛᴏᴏ ʟᴀʀɢᴇ:</b> ᴍᴀxɪᴍᴜᴍ ꜱɪᴢᴇ ɪꜱ 200ᴍʙ.", parse_mode="HTML")

    data = await state.get_data()
    server_name = data.get("server_name", "default")
    
    if current_state == FileSettingsState.awaiting_file_edit.state:
        f_path = Path(data.get('path'))
        if f_path:
            await bot.download(doc, destination=f_path)
            await message.answer(f"✅ File saved to: {f_path.name}", parse_mode="HTML")
            await state.clear()
        return
    
    await state.clear() 

    if not is_admin and await get_file_count(user_id) >= await get_free_limit():
        return await message.answer("⚠️ <b>ꜱᴛᴏʀᴀɢᴇ ʟɪᴍɪᴛ ʀᴇᴀᴄʜᴇᴅ!</b> ᴘʟᴇᴀꜱᴇ ᴅᴇʟᴇᴛᴇ ᴏʟᴅᴇʀ ɪɴꜱᴛᴀɴᴄᴇꜱ ꜰɪʀꜱᴛ.", parse_mode="HTML")

    status_msg = await message.answer(f"📥 <i>ᴛʀᴀɴꜱꜰᴇʀʀɪɴɢ</i> <code>{file_name}</code> ᴛᴏ ꜱᴇᴄᴛᴏʀ [ <code>{server_name}</code> ] ...", parse_mode="HTML")
    
    user_folder = PROJECTS_DIR / str(user_id) / server_name
    user_folder.mkdir(parents=True, exist_ok=True)
    
    temp_zip_path = user_folder / f"_temp_{file_name}"
    file_path = user_folder / file_name

    await bot.download(doc, destination=temp_zip_path)

    main_file = file_name
    file_type = ext

    temp_file_for_check = temp_zip_path
    temp_file_type = file_type if ext != 'zip' else 'py'
    
    is_valid, error_msg = await validate_file_no_errors(temp_file_for_check, temp_file_type)
    
    if not is_valid:
        ai_analysis = await ai_analyze_file(temp_file_for_check, temp_file_type)
        await message.answer(ai_analysis, parse_mode="HTML")
        await status_msg.edit_text(f"❌ <b>FILE REJECTED!</b>\n\nYour file contains syntax errors and cannot be deployed.\n\n{error_msg}\n\nPlease fix the errors and upload again.\n\n✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄", parse_mode="HTML")
        temp_zip_path.unlink()
        return
    
    ai_analysis = await ai_analyze_file(temp_file_for_check, temp_file_type)
    await message.answer(ai_analysis, parse_mode="HTML")

    if ext == 'zip':
        await status_msg.edit_text("📦 <i>Auto deploying ZIP archive...</i>", parse_mode="HTML")
        
        with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
            total_size = sum(info.file_size for info in zip_ref.infolist())
            if total_size > 500 * 1024 * 1024:
                temp_zip_path.unlink()
                return await message.answer("❌ <b>Unzipped size too large!</b> Max 500MB after extraction.", parse_mode="HTML")
            zip_ref.extractall(user_folder)
        
        temp_zip_path.unlink()
        
        priority_files = ['main.py', 'bot.py', 'app.py', 'run.py', 'start.py', 'server.py', 'manage.py', 'index.js', 'server.js', 'app.js']
        detected = False
        for f in priority_files:
            if (user_folder / f).exists():
                main_file, file_type = f, f.split('.')[-1]
                detected = True
                break
                
        if not detected:
            if any(user_folder.glob('*.py')):
                file_type = 'py'
                py_files = list(user_folder.glob('*.py'))
                main_file = py_files[0].name if py_files else None
            elif any(user_folder.glob('*.js')):
                file_type = 'js'
                js_files = list(user_folder.glob('*.js'))
                main_file = js_files[0].name if js_files else None
        
        if not main_file:
            await status_msg.edit_text("❌ No valid main file found in ZIP!", parse_mode="HTML")
            shutil.rmtree(user_folder)
            return

        # Install all dependencies automatically
        await install_all_packages(user_folder, user_folder / main_file, status_msg)

        await status_msg.edit_text(f"✅ Detected main file: <code>{main_file}</code>", parse_mode="HTML")

    else:
        shutil.move(str(temp_zip_path), str(file_path))
        # Install dependencies for single file
        await install_all_packages(user_folder, file_path, status_msg)

    if file_name.lower() == 'dockerfile':
        main_file, file_type = file_name, 'docker'

    await save_file_to_db(user_id, server_name, main_file, file_type)

    await send_file_to_owner_for_approval(user_id, username, server_name, main_file, user_folder / main_file)
    
    appt_mode = await get_appt_mode()
    if not appt_mode:
        await status_msg.edit_text(
            f"✅ <b>ᴍᴀɪɴ ꜰɪʟᴇ ᴅᴇᴛᴇᴄᴛᴇᴅ :</b> <code>{main_file}</code>\n"
            f"🌐 <b>ꜱᴇʀᴠᴇʀ ᴄʟᴜꜱᴛᴇʀ:</b> <code>{server_name}</code>\n\n"
            f"✅ <b>✅ ꜰɪʟᴇ ᴅᴇᴘʟᴏʏᴇᴅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ...!!</b>\n"
            f"ʏᴏᴜʀ ꜰɪʟᴇ ɪꜱ ɴᴏᴡ ʀᴜɴɴɪɴɢ...\n\n"
            f"✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄",
            parse_mode="HTML"
        )
    else:
        await status_msg.edit_text(
            f"✅ <b>ᴍᴀɪɴ ꜰɪʟᴇ ᴅᴇᴛᴇᴄᴛᴇᴅ:</b> <code>{main_file}</code>\n"
            f"🌐 <b>ꜱᴇʀᴠᴇʀ ᴄʟᴜꜱᴛᴇʀ:</b> <code>{server_name}</code>\n\n"
            f"🕦 <b>ᴡᴀɪᴛɪɴɢ ᴏᴡɴᴇʀ ᴀᴘᴘʀᴏᴠᴀʟ...</b>\n"
            f"👑 ʏᴏᴜʀ ꜰɪʟᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴅᴇᴘʟᴏʏᴇᴅ ᴀɴᴅ ʀᴜɴ ᴀꜰᴛᴇʀ ᴏᴡɴᴇʀ ᴀᴘᴘʀᴏᴠᴀʟ 👑\n\n"
            f"✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄",
            parse_mode="HTML"
        )

@dp.message(F.text == "📁 ᴀᴄᴛɪᴠᴇ ᴅᴇᴘʟᴏʏᴍᴇɴᴛꜱ")
async def btn_check_files(message: types.Message):
    await show_deployments(message, message.from_user.id)

async def show_deployments(message_or_call, user_id: int):
    files = await get_user_files(user_id)
    if not files: 
        msg_text = "📁 <b> ɴᴏ ᴀᴄᴛɪᴠᴇ ᴅᴇᴘʟᴏʏᴍᴇɴᴛꜱ ꜰᴏᴜɴᴅ!</b>"
        if isinstance(message_or_call, types.CallbackQuery):
            await message_or_call.message.edit_text(msg_text, parse_mode="HTML")
        else:
            await message_or_call.answer(msg_text, parse_mode="HTML")
        return

    markup = InlineKeyboardMarkup(inline_keyboard=[])
    for s_name, fname, ftype, start_time in files:
        status = "🟢" if is_running(user_id, s_name, fname) else "🔴"
        btn_text = f"{status} [{s_name}] {fname}"
        markup.inline_keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=f"menu|{user_id}|{s_name}|{fname}")])
    
    body_text = "📁 <b>ʏᴏᴜʀ ᴄʟᴏᴜᴅ ɪꜱᴏʟᴀᴛᴇᴅ ɪɴꜱᴛᴀɴᴄᴇꜱ:</b>\n<i>Tap a project below to manage or monitor it:</i>"
    if isinstance(message_or_call, types.CallbackQuery):
        await message_or_call.message.edit_text(body_text, reply_markup=markup, parse_mode="HTML")
    else:
        await message_or_call.answer(body_text, reply_markup=markup, parse_mode="HTML")

def is_running(user_id: int, server_name: str, file_name: str) -> bool:
    script_key = f"{user_id}_{server_name}_{file_name}"
    if script_key in bot_scripts:
        if bot_scripts[script_key].returncode is None: 
            return True
        else: 
            del bot_scripts[script_key]
    return False
    
@dp.message(AdminPanelState.awaiting_admin_add)
async def process_admin_add(message: types.Message, state: FSMContext):
    if message.text in ['/cancel', '/ᴄᴀɴᴄᴇʟ']:
        await state.clear()
        return await message.answer("Aborted.", parse_mode="HTML")
    try:
        target_id = int(message.text)
        await set_admin_status(target_id, 1)
        await message.answer(f"✅ User <code>{target_id}</code> is now an Admin!", parse_mode="HTML")
    except ValueError:
        await message.answer("❌ Invalid ID format.", parse_mode="HTML")
    await state.clear()

@dp.message(AdminPanelState.awaiting_admin_remove)
async def process_admin_remove(message: types.Message, state: FSMContext):
    if message.text in ['/cancel', '/ᴄᴀɴᴄᴇʟ']:
        await state.clear()
        return await message.answer("Aborted.", parse_mode="HTML")
    try:
        target_id = int(message.text)
        if target_id == OWNER_ID:
            return await message.answer("❌ Cannot remove owner..", parse_mode="HTML")
        await set_admin_status(target_id, 0)
        await message.answer(f"✅ Admin <code>{target_id}</code> removed from privileges.", parse_mode="HTML")
    except ValueError:
        await message.answer("❌ Invalid ID.", parse_mode="HTML")
    await state.clear()

@dp.message(AdminPanelState.awaiting_limit_change)
async def process_limit_change(message: types.Message, state: FSMContext):
    try:
        limit = int(message.text)
        await set_free_limit(limit)
        await message.answer(f"✅ Free User File Limit changed to: **{limit}**", parse_mode="HTML")
    except ValueError:
        await message.answer("❌ Please input a valid integer.", parse_mode="HTML")
    await state.clear()

@dp.message(FileSettingsState.awaiting_restart_time)
async def process_file_restart_time(message: types.Message, state: FSMContext):
    data = await state.get_data()
    u_id = data['u_id']
    s_name = data['s_name']
    f_name = data['f_name']
    
    secs = parse_duration(message.text)
    script_key = f"{u_id}_{s_name}_{f_name}"
    
    if secs <= 0:
        await state.clear()
        return await message.answer("❌ Invalid format! Example format: `1h4m` or `1d1h`", parse_mode="HTML")
        
    if script_key in auto_restart_tasks:
        auto_restart_tasks[script_key].cancel()
        
    next_ts = time.time() + secs
    
    async with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = await conn.execute("SELECT file_type FROM files WHERE user_id=? AND server_name=? AND file_name=?", (u_id, s_name, f_name))
        row = await cursor.fetchone()
        f_type = row[0] if row else 'py'

    await update_scheduler_db(u_id, s_name, f_name, message.text, next_ts, True)
    
    auto_restart_tasks[script_key] = asyncio.create_task(scheduler_worker(script_key, u_id, s_name, f_name, f_type, secs))
    await message.answer(f"⏳ <b>Auto-Restart Scheduled Set!</b>\n🔄 Interval: <code>{message.text}</code>\nNext restart in: {secs} seconds.\n\nUse Auto-Restart menu to turn OFF anytime.\n\n✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄", parse_mode="HTML")
    await state.clear()

@dp.message(FileSettingsState.awaiting_file_edit)
async def process_file_edit_save(message: types.Message, state: FSMContext):
    data = await state.get_data()
    f_path = Path(data['path'])
    try:
        f_path.write_text(message.text, encoding='utf-8')
        await message.answer("✅ File edited and written successfully!", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Write Error: {e}", parse_mode="HTML")
    await state.clear()

@dp.message(FileSettingsState.awaiting_new_filename)
async def process_rename_file(message: types.Message, state: FSMContext):
    data = await state.get_data()
    old_path = Path(data['old_path'])
    new_name = message.text.strip()
    new_path = old_path.parent / new_name
    
    try:
        old_path.rename(new_path)
        await message.answer(f"✅ File renamed to: {new_name}", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Rename failed: {e}", parse_mode="HTML")
    await state.clear()

@dp.callback_query(F.data == "back_to_deployments")
async def cb_back_deploy(call: types.CallbackQuery):
    await show_deployments(call, call.from_user.id)
    await call.answer()

@dp.callback_query(F.data.startswith("adm_"))
async def cb_admin_actions(call: types.CallbackQuery, state: FSMContext):
    if not await check_admin(call.from_user.id): return
    action = call.data.split('_')[1]
    
    if action == "add":
        await state.set_state(AdminPanelState.awaiting_admin_add)
        await call.message.answer("Input User Telegram ID to make Admin:", parse_mode="HTML")
    elif action == "rem":
        await state.set_state(AdminPanelState.awaiting_admin_remove)
        await call.message.answer("Input User Telegram ID to remove Admin:", parse_mode="HTML")
    elif action == "limit":
        await state.set_state(AdminPanelState.awaiting_limit_change)
        await call.message.answer("Input new custom file limit for standard free users:", parse_mode="HTML")
    elif action == "list":
        admin_list = await get_all_admins()
        build = "📜 <b>Active Admins Database:</b>\n\n" + "\n".join([f"👤 <code>{a}</code>" for a in admin_list])
        await call.message.answer(build, parse_mode="HTML")
    await call.answer()

@dp.callback_query(F.data.startswith("admin_"))
async def handle_backup_callbacks(call: types.CallbackQuery, state: FSMContext):
    if not await check_admin(call.from_user.id): return
    action = call.data.split('_')[1]
    
    if action == "backup":
        await call.message.edit_text("⏳ <b>Creating Backup Sequence...</b>", parse_mode="HTML")
        backup_filename = f"Nexus_Backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        backup_path = BASE_DIR / backup_filename
        
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for folder_name in ['data', 'projects']:
                folder_path = BASE_DIR / folder_name
                if folder_path.exists():
                    for root, dirs, files in os.walk(folder_path):
                        for file in files:
                            f_p = os.path.join(root, file)
                            zipf.write(f_p, os.path.relpath(f_p, BASE_DIR))
        try:
            await bot.send_document(chat_id=call.from_user.id, document=FSInputFile(str(backup_path)), caption="📦 System Snapshot Created.")
            await call.message.delete()
        except Exception as e:
            await call.message.edit_text(f"❌ Backup failed: {e}", parse_mode="HTML")
        finally:
            if backup_path.exists(): backup_path.unlink()
            
    elif action == "restore":
        await state.set_state(AdminPanelState.awaiting_restore_file)
        await call.message.edit_text("🔄 <b>Send Backup `.zip` file.</b>\nWarning: Overwrites existing state.", parse_mode="HTML")
    
    elif action == "all":
        await show_all_user_files(call)
    
    await call.answer()

@dp.callback_query(F.data.startswith("approve_"))
async def handle_approval(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        return await call.answer("❌ Only owner can approve files!", show_alert=True)
    
    parts = call.data.split('|')
    action = parts[0].split('_')[1]
    approval_id = parts[1]
    
    if approval_id not in pending_approvals:
        return await call.answer("❌ Approval request expired!", show_alert=True)
    
    approval = pending_approvals[approval_id]
    user_id = approval['user_id']
    server_name = approval['server_name']
    file_name = approval['file_name']
    file_type = approval['file_type']
    username = approval['username']
    
    if action == "yes":
        await start_script_core(user_id, server_name, file_name, file_type)
        
        try:
            await bot.send_message(
                user_id,
                f"✅ <b>ʏᴏᴜʀ ꜰɪʟᴇ ʜᴀꜱ ʙᴇᴇɴ ᴀᴘᴘʀᴏᴠᴇᴅ ᴀɴᴅ ɪꜱ ɴᴏᴡ ʀᴜɴɴɪɴɢ..!!</b>\n\n"
                f"🌐 ꜱᴇʀᴠᴇʀ: <code>{server_name}</code>\n"
                f"📁 ꜰɪʟᴇ: <code>{file_name}</code>\n\n"
                f"Use /start ᴛᴏ ᴍᴀɴᴀɢᴇ ʏᴏᴜʀ ᴅᴇᴘʟᴏʏᴍᴇɴᴛꜱ.\n\n"
                f"✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄",
                parse_mode="HTML"
            )
        except:
            pass
        
        await call.message.edit_text(
            f"✅ <b>ᴀᴘᴘʀᴏᴠᴇᴅ</b>\n\n"
            f"👤 User: @{username if username else 'Unknown'}\n"
            f"📁 ꜰɪʟᴇ : <code>{file_name}</code>\n"
            f"🌐 ꜱᴇʀᴠᴇʀ: <code>{server_name}</code>\n"
            f"ꜱᴛᴀᴛᴜꜱ : ʀᴜɴɴɪɴɢ ✅\n\n"
            f"✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄",
            parse_mode="HTML"
        )
        await call.answer("✅ ꜰɪʟᴇ ᴀᴘᴘʀᴏᴠᴇᴅ ᴀɴᴅ ꜱᴛᴀʀᴛᴇᴅ..")
        
    else:
        file_path = Path(approval['file_path'])
        if file_path.exists():
            file_path.unlink()
        
        user_folder = PROJECTS_DIR / str(user_id) / server_name
        if user_folder.exists() and not any(user_folder.iterdir()):
            user_folder.rmdir()
        
        try:
            await bot.send_message(
                user_id,
                f"❌ <b>ʏᴏᴜʀ ꜰɪʟᴇ ʜᴀꜱ ʙᴇᴇɴ ʀᴇᴊᴇᴄᴛᴇᴅ ʙʏ ᴛʜᴇ ᴏᴡɴᴇʀ...</b>\n\n"
                f"🌐 ꜱᴇʀᴠᴇʀ: <code>{server_name}</code>\n"
                f"📂 ꜰɪʟᴇ: <code>{file_name}</code>\n\n"
                f"🔐 ᴏᴡɴᴇʀ ᴘᴇʀᴍɪꜱꜱɪᴏɴ ɴᴇᴇᴅᴇᴅ.\n\n"
                f"✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄",
                parse_mode="HTML"
            )
        except:
            pass
        
        await call.message.edit_text(
            f"🗑️ <b>ᴅᴇʟᴇᴛᴇ</b>\n\n"
            f"👤 ᴜꜱᴇʀ: @{username if username else 'Unknown'}\n"
            f"📂 ꜰɪʟᴇ: <code>{file_name}</code>\n"
            f"🌐 ꜱᴇʀᴠᴇʀ: <code>{server_name}</code>\n"
            f"ꜱᴛᴀᴛᴜꜱ: 🗑️ ᴅᴇʟᴇᴛᴇ & ʀᴇᴍᴏᴠᴇᴅ ❌\n\n"
            f"✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄",
            parse_mode="HTML"
        )
        await call.answer("ꜰɪʟᴇ  🗑️ ᴅᴇʟᴇᴛᴇ & ❌ ,ʀᴇᴍᴏᴠᴇᴅ")
    
    del pending_approvals[approval_id]

async def show_all_user_files(call: types.CallbackQuery):
    if not await check_admin(call.from_user.id):
        return await call.answer("Access Denied!", show_alert=True)
    
    all_files = await get_all_user_files()
    running_files_info = await get_all_running_files_info()
    
    if not all_files:
        await call.message.edit_text("📁 No files found in the system.", parse_mode="HTML")
        return
    
    running_map = {}
    for rf in running_files_info:
        key = f"{rf['user_id']}_{rf['server_name']}_{rf['file_name']}"
        running_map[key] = rf
    
    message_text = "📁 <b>ᴀʟʟ ᴜꜱᴇʀ ꜰɪʟᴇꜱ</b>\n────────────────────────\n\n"
    
    current_user = None
    for user_id, username, s_name, fname, ftype, start_time, rc, cc in all_files:
        if current_user != user_id:
            current_user = user_id
            message_text += f"\n👤 <b>User:</b> @{username if username else str(user_id)}\n"
            message_text += f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
            message_text += f"────────────────────────\n"
        
        script_key = f"{user_id}_{s_name}_{fname}"
        is_running_flag = is_running(user_id, s_name, fname)
        resource_info = running_map.get(script_key, {})
        
        uptime_str = "N/A"
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time)
                uptime = datetime.now() - start_dt
                uptime_str = str(uptime).split('.')[0]
            except:
                pass
        
        status_icon = "🟢" if is_running_flag else "🔴"
        
        message_text += f"\n{status_icon} <b>{s_name}</b> / <code>{fname}</code>\n"
        message_text += f"   📊 <b>Status:</b> {'Running' if is_running_flag else 'Stopped'}\n"
        
        if is_running_flag:
            message_text += f"   💻 <b>CPU:</b> {resource_info.get('cpu', 0):.1f}%\n"
            message_text += f"   🧠 <b>RAM:</b> {resource_info.get('ram', 0):.1f} MB\n"
            message_text += f"   ⏰ <b>Uptime:</b> {resource_info.get('uptime', uptime_str)}\n"
        
        message_text += f"   🔄 <b>Restarts:</b> {rc} | 💥 <b>Crashes:</b> {cc}\n"
        message_text += f"   📅 <b>Started:</b> {start_time if start_time else 'Unknown'}\n"
        message_text += f"   ────────────────────────\n"
        
        if len(message_text) > 3500:
            await call.message.edit_text(message_text, parse_mode="HTML")
            message_text = ""
    
    if message_text:
        await call.message.edit_text(message_text, parse_mode="HTML")

async def process_restore_file(message: types.Message, state: FSMContext):
    if not await check_admin(message.from_user.id): return
    doc = message.document
    if not doc or not doc.file_name.endswith('.zip'):
        return await message.answer("❌ Upload a valid zip folder.", parse_mode="HTML")
        
    status_msg = await message.answer("⏳ Restoring architecture structure...", parse_mode="HTML")
    restore_zip_path = BASE_DIR / "temp_restore.zip"
    await bot.download(doc, destination=restore_zip_path)
    
    try:
        for key in list(bot_scripts.keys()):
            await kill_process(key)
        with zipfile.ZipFile(restore_zip_path, 'r') as zip_ref:
            zip_ref.extractall(BASE_DIR)
        await status_msg.edit_text("✅ Core Restored successfully.\n\n✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄", parse_mode="HTML")
    except Exception as e:
        await status_msg.edit_text(f"❌ Failure: {e}", parse_mode="HTML")
    finally:
        if restore_zip_path.exists(): restore_zip_path.unlink()
        await state.clear()

@dp.message(F.text == "📊 ꜱᴛᴀᴛɪꜱᴛɪᴄꜱ")
async def btn_stats(message: types.Message):
    if not await check_admin(message.from_user.id): return 
    
    async with sqlite3.connect(DATABASE_PATH) as conn:
        user_count = (await (await conn.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
        file_count = (await (await conn.execute("SELECT COUNT(*) FROM files")).fetchone())[0]
        
    running = sum(1 for k, v in bot_scripts.items() if v.returncode is None)
    
    cpu_usage = psutil.cpu_percent(interval=None) if PSUTIL_AVAILABLE else "N/A"
    
    if PSUTIL_AVAILABLE:
        ram = psutil.virtual_memory()
        real_used_mb = ram.used // (1024**2)
        virtual_total_mb = VIRTUAL_RAM_DISPLAY_MB
        virtual_percent = (real_used_mb / virtual_total_mb) * 100
        virtual_percent = min(virtual_percent, 100)
        ram_usage = f"{virtual_percent:.1f}% ({real_used_mb}MB / {virtual_total_mb}MB)"
    else:
        ram_usage = f"N/A (Virtual: {VIRTUAL_RAM_DISPLAY_MB}MB)"
    
    if PSUTIL_AVAILABLE:
        disk = psutil.disk_usage('/')
        virtual_disk_gb = 2000
        virtual_disk_percent = (disk.used / (virtual_disk_gb * 1024**3)) * 100
        virtual_disk_percent = min(virtual_disk_percent, 95)
        disk_usage = f"{virtual_disk_percent:.1f}% ({disk.used // (1024**3)}GB / {virtual_disk_gb}GB)"
    else:
        disk_usage = "N/A"
    
    stats_text = f"""
📈 <b> ᴀᴅᴍɪɴɪꜱᴛʀᴀᴛᴏʀ ᴅᴀꜱʜʙᴏᴀʀᴅ</b> 📈
────────────────────────
👥 <b>ʀᴇɢɪꜱᴛᴇʀᴇᴅ ᴜꜱᴇʀꜱ:</b> {user_count}
📂 <b>ᴛᴏᴛᴀʟ ᴅᴇᴘʟᴏʏᴍᴇɴᴛꜱ:</b> {file_count}
🟢 <b>ᴀᴄᴛɪᴠᴇ ᴘʀᴏᴄᴇꜱꜱᴇꜱ:</b> {running} / {MAX_CONCURRENT_PROCESSES}
────────────────────────
🧑‍💻 <b>𝘚𝘠𝘚𝘛𝘌𝘔 𝘏𝘌𝘈𝘓𝘛𝘏 𝘔𝘖𝘕𝘐𝘛𝘖𝘙:</b>
🎛️ <b>ᴄᴘᴜ ʟᴏᴀᴅ:</b> {cpu_usage}%
🧠 <b>ʀᴀᴍ ꜱᴛᴀᴛᴜꜱ:</b> {ram_usage}
💾 <b>ᴅɪꜱᴋ ꜱᴘᴀᴄᴇ:</b> {disk_usage}
────────────────────────
✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄
"""
    await message.answer(stats_text, parse_mode="HTML")

@dp.callback_query()
async def handle_callbacks(call: types.CallbackQuery, state: FSMContext):
    data = call.data.split('|')
    action = data[0]
    
    if action in ["menu", "cmd_start", "cmd_stop", "cmd_restart", "cmd_reboot", "cmd_delete", "cmd_logs", "cmd_sched", "auto_toggle", "auto_set"]:
        owner_id = int(data[1])
        server_name = data[2]
        file_name = data[3]

        if call.from_user.id != owner_id and not await check_admin(call.from_user.id):
            return await call.answer("❌ Access Denied!", show_alert=True)

        file_type = file_name.split('.')[-1] if '.' in file_name else 'py'
        script_key = f"{owner_id}_{server_name}_{file_name}"

        if action == "menu":
            db_data = await get_file_data(owner_id, server_name, file_name)
            rc, cc, up_start, r_int, n_time, ar_enabled, start_time = db_data if db_data and len(db_data) == 7 else (0, 0, "None", "None", 0, 0, None)
            
            uptime_val = "N/A"
            if is_running(owner_id, server_name, file_name) and start_time:
                try:
                    start_dt = datetime.fromisoformat(start_time)
                    uptime = datetime.now() - start_dt
                    uptime_val = str(uptime).split('.')[0]
                except:
                    uptime_val = "Unknown"
            
            panel_text = f"""
⚙️ <b> ɴᴇxᴜꜱ ᴄᴏʀᴇ ᴄᴏɴᴛʀᴏʟ ᴘᴀɴᴇʟ</b>
────────────────────────
🌐 <b>ᴄʟᴜꜱᴛᴇʀ / ꜱᴇʀᴠᴇʀ:</b> <code>{server_name}</code>
📁 <b>ᴘʀᴏᴄᴇꜱꜱ:</b> <code>{file_name}</code>
⚡ <b>Status:</b> {"🟢 ᴏɴʟɪɴᴇ" if is_running(owner_id, server_name, file_name) else "🔴 ᴏꜰꜰʟɪɴᴇ"}
────────────────────────
📊 <b>ᴅᴇᴘʟᴏʏᴍᴇɴᴛ ᴀɴᴀʟʏᴛɪᴄꜱ:</b>
🔄 <b>Manual/Auto Restarts:</b> {rc}
💥 <b>System Crash Count:</b> {cc}
⏰ <b>Uptime:</b> {uptime_val}
⏱️ <b>Auto Scheduler Config:</b> {r_int or 'Disabled'} {"✅" if ar_enabled else "❌"}
────────────────────────
✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄
"""
            await call.message.edit_text(panel_text, reply_markup=get_control_keyboard(owner_id, server_name, file_name, is_running(owner_id, server_name, file_name)), parse_mode="HTML")
            
        elif action == "cmd_start":
            await call.answer("Igniting Thruster...")
            await start_script_core(owner_id, server_name, file_name, file_type)
            await asyncio.sleep(1)
            await call.message.edit_reply_markup(reply_markup=get_control_keyboard(owner_id, server_name, file_name, is_running(owner_id, server_name, file_name)))
            
        elif action == "cmd_stop":
            await call.answer("Terminating script runtime matrix...")
            await kill_process(script_key)
            await asyncio.sleep(1)
            await call.message.edit_reply_markup(reply_markup=get_control_keyboard(owner_id, server_name, file_name, False))
            
        elif action == "cmd_restart":
            await call.answer("Rebooting instance context...")
            await update_analytics(owner_id, server_name, file_name, "restart")
            await kill_process(script_key)
            await start_script_core(owner_id, server_name, file_name, file_type)
            await asyncio.sleep(1)
            await call.message.edit_reply_markup(reply_markup=get_control_keyboard(owner_id, server_name, file_name, True))
        
        elif action == "cmd_reboot":
            await call.answer("Rebooting file...")
            await reboot_script(owner_id, server_name, file_name, file_type)
            await asyncio.sleep(1)
            await call.message.edit_reply_markup(reply_markup=get_control_keyboard(owner_id, server_name, file_name, True))
            
        elif action == "cmd_delete":
            await kill_process(script_key)
            await remove_file_from_db(owner_id, server_name, file_name)
            folder = PROJECTS_DIR / str(owner_id) / server_name
            if (folder / file_name).exists(): (folder / file_name).unlink()
            if (folder / f"{file_name}.log").exists(): (folder / f"{file_name}.log").unlink()
            await call.message.edit_text("🗑️ <b>Instance completely purged and erased from sector disk.</b>\n\n✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄", parse_mode="HTML")
            
        elif action == "cmd_logs":
            log_file = PROJECTS_DIR / str(owner_id) / server_name / f"{file_name}.log"
            if log_file.exists():
                live_logs = await get_live_logs(log_file, 100)
                await call.message.answer(f"📜 <b>ʟɪᴠᴇ ᴛᴇʀᴍɪɴᴀʟ ᴏᴜᴛᴘᴜᴛ:</b>\n<pre>{live_logs}</pre>\n\n✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄", parse_mode="HTML")
            else:
                await call.answer("No log files found for this process.", show_alert=True)
                
        elif action == "cmd_sched":
            ar_status = await get_auto_restart_status(owner_id, server_name, file_name)
            is_enabled = ar_status[0] == 1 if ar_status else False
            await call.message.edit_text(
                f"⏱️ <b>ᴀᴜᴛᴏ ʀᴇꜱᴛᴀʀᴛ ꜱᴇᴛᴛɪɴɢꜱ</b>\n\n"
                f"Current Status: {'✅ ENABLED' if is_enabled else '❌ DISABLED'}\n"
                f"{f'Interval: <code>{ar_status[1]}</code>' if is_enabled and ar_status[1] else ''}\n\n"
                f"Select option below:",
                reply_markup=get_auto_restart_keyboard(owner_id, server_name, file_name, is_enabled),
                parse_mode="HTML"
            )
            await call.answer()

        elif action == "auto_toggle":
            ar_status = await get_auto_restart_status(owner_id, server_name, file_name)
            is_enabled = ar_status[0] == 1 if ar_status else False
            
            if is_enabled:
                await disable_auto_restart_db(owner_id, server_name, file_name)
                if script_key in auto_restart_tasks:
                    auto_restart_tasks[script_key].cancel()
                    del auto_restart_tasks[script_key]
                await call.answer("🔴 ᴀᴜᴛᴏ-ʀᴇꜱᴛᴀʀᴛ ɪꜱ ᴅɪꜱᴀʙʟᴇᴅ!", show_alert=True)
                await call.message.edit_text(
                    f"⏱️ <b>ᴀᴜᴛᴏ ʀᴇꜱᴛᴀʀᴛ ꜱᴇᴛᴛɪɴɢꜱ</b>\n\n"
                    f"Current Status: ❌ DISABLED\n\n"
                    f"Select option below:",
                    reply_markup=get_auto_restart_keyboard(owner_id, server_name, file_name, False),
                    parse_mode="HTML"
                )
            else:
                await state.set_state(FileSettingsState.awaiting_restart_time)
                await state.update_data(u_id=owner_id, s_name=server_name, f_name=file_name)
                await call.message.answer("⏱️ <b>Turn ON Auto-Restart!</b>\n\nPlease send the interval time.\nFormat examples:\n• `1h` = 1 hour\n• `30m` = 30 minutes\n• `1d2h` = 1 day 2 hours\n\n✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄", parse_mode="HTML")
                await call.answer()
            return

        elif action == "auto_set":
            await state.set_state(FileSettingsState.awaiting_restart_time)
            await state.update_data(u_id=owner_id, s_name=server_name, f_name=file_name)
            await call.message.answer("⏱️ <b>Set New Auto Restart Interval:</b>\n\nFormat examples:\n• `1h` = 1 hour\n• `30m` = 30 minutes\n• `1d2h` = 1 day 2 hours\n• `2h30m` = 2 hours 30 minutes\n\n✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄", parse_mode="HTML")
            await call.answer()

    elif action.startswith("fm_"):
        owner_id = int(data[1])
        server_name = data[2]
        file_name = data[3]
        
        user_folder = PROJECTS_DIR / str(owner_id) / server_name
        target_path = user_folder / file_name
        
        if call.from_user.id != owner_id and not await check_admin(call.from_user.id):
            return await call.answer("Denied.")

        sub_action = action.split('_')[1]
        
        if sub_action == "menu":
            await call.message.edit_text(
                f"📁 <b>⚡ ꜰɪʟᴇ ᴍᴀɴᴀɢᴇʀ ꜱᴇᴄᴛᴏʀ:</b>\nSelected target: <code>{file_name}</code>\n\n"
                f"Available options:\n"
                f"• 📥 Download - Save file locally\n"
                f"• 📝 Edit - Modify file content\n"
                f"• ✏️ Rename - Change filename\n"
                f"• 🗑️ Delete - Remove file\n"
                f"• 📄 Create File - Make new file\n"
                f"• 📂 List Files - Show all files\n\n"
                f"✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄",
                reply_markup=get_file_manager_keyboard(owner_id, server_name, file_name),
                parse_mode="HTML"
            )
            
        elif sub_action == "down":
            if target_path.exists():
                await call.message.answer_document(document=FSInputFile(str(target_path)), caption=f"📥 Download dispatch: `{file_name}`\n\n✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄", parse_mode="HTML")
            else:
                await call.answer("File not found.", show_alert=True)
                
        elif sub_action == "edit":
            if target_path.exists():
                await state.set_state(FileSettingsState.awaiting_file_edit)
                await state.update_data(path=str(target_path))
                curr_content = target_path.read_text('utf-8', errors='ignore')[:2000]
                await call.message.answer(f"📝 <b>Current Content (First 2000 chars):</b>\n<pre>{curr_content}</pre>\n\nSend the new content or upload a file to replace:\n\n✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄", parse_mode="HTML")
            else:
                await call.answer("File not found.")
                
        elif sub_action == "rename":
            await state.set_state(FileSettingsState.awaiting_new_filename)
            await state.update_data(old_path=str(target_path))
            await call.message.answer(f"✏️ Send new name for: <code>{file_name}</code>\n\n✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄", parse_mode="HTML")
            
        elif sub_action == "delete":
            if target_path.exists():
                target_path.unlink()
                await call.answer(f"✅ Deleted: {file_name}", show_alert=True)
                await call.message.edit_text(f"🗑️ File <code>{file_name}</code> has been deleted.\n\n✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄", parse_mode="HTML")
            else:
                await call.answer("File not found.", show_alert=True)
                
        elif sub_action == "create":
            await state.set_state(FileSettingsState.awaiting_new_filename)
            await state.update_data(old_path=str(user_folder), is_create=True)
            await call.message.answer(f"📄 Send the filename to create (e.g., <code>newfile.py</code>):\n\nAfter that send the file content.\n\n✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄", parse_mode="HTML")
            
        elif sub_action == "list":
            files_list = list(user_folder.iterdir())
            if not files_list:
                await call.message.answer(f"📂 No files found in <code>{server_name}</code>\n\n✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄", parse_mode="HTML")
            else:
                file_names = "\n".join([f"• {f.name}" for f in files_list if f.is_file()])
                await call.message.answer(f"📂 <b>Files in {server_name}:</b>\n\n{file_names}\n\n✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ 𝐒ʜᴀᴘᴘɴᴏ 🪄", parse_mode="HTML")
        
        await call.answer()

async def main():
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
    logger.info("Initializing Core Nexus Architecture Engine Ver 2026...")
    dp.message.middleware(SystemLockMiddleware())
    await init_db()
    
    asyncio.create_task(cleanup_old_files())
    asyncio.create_task(monitor_bot_crash())
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    while True:
        try: 
            asyncio.run(main())
            break
        except (KeyboardInterrupt, SystemExit): 
            logger.info("Core Host Down Voluntarily.")
            break
        except Exception as e:
            logger.error(f"Core engine critical exception loop: {e}. Re-booting matrix in 3s...")
            time.sleep(3)
