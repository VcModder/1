#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import telebot
from telebot import types
import subprocess
import threading
import queue
import time
import os
import signal
import sys
import json
import random
import string
import pexpect
import requests
from datetime import datetime, timedelta
from collections import defaultdict
import shutil
import re

# ============================================
# BOT CONFIGURATION
# ============================================
BOT_TOKEN = "8904905040:AAGGTt6jaoNfFvEBzFH7vfgEWL6pw24xK8g"  # ← APNA TOKEN YAHAN
ADMIN_IDS = [8170807285]  # ← APNI TELEGRAM ID

# Bot Info
BOT_NAME = "MONX BOT"
BOT_USERNAME = "@MONX_BOT"
OWNER_USERNAME = "@QTowner"
BOT_VERSION = "3.0.0"

# Data Directory
DATA_DIR = "MONX_DATA"
USER_LOGS_DIR = f"{DATA_DIR}/user_logs"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(USER_LOGS_DIR, exist_ok=True)

# Auto-create JSON files
DEFAULT_FILES = {
    f"{DATA_DIR}/users.json": {},
    f"{DATA_DIR}/logs.json": [],
    f"{DATA_DIR}/referrals.json": {},
    f"{DATA_DIR}/transactions.json": [],
    f"{DATA_DIR}/subscriptions.json": {},
    f"{DATA_DIR}/wallets.json": {},
    f"{DATA_DIR}/banned.json": {},
    f"{DATA_DIR}/clones.json": {},
    f"{DATA_DIR}/channels.json": [],
    f"{DATA_DIR}/gc_settings.json": {},
    f"{DATA_DIR}/stickers.json": {},
    f"{DATA_DIR}/ads.json": {}
}

for filepath, default_data in DEFAULT_FILES.items():
    if not os.path.exists(filepath):
        with open(filepath, 'w') as f:
            json.dump(default_data, f, indent=2)

# Load channels from file
CHANNELS_FILE = f"{DATA_DIR}/channels.json"
FORCE_JOIN_CHANNELS = load_json(CHANNELS_FILE, []) if os.path.exists(CHANNELS_FILE) else []

# Token System
TOKEN_DAILY_BONUS = 2
TOKEN_REFERRAL_BONUS = 2
TOKEN_COSTS = {"1min": 2, "3min": 5, "10min": 10}
FREE_DAILY_LIMIT = 5
TOKEN_TO_INR = 0.5  # 100 token = 50₹

# Subscription Plans
SUBSCRIPTION_PLANS = {
    "1hour": {"price_usd": 0.3, "price_inr": 28, "hours": 1, "bonus": 0, "icon": "🕐"},
    "1day": {"price_usd": 1, "price_inr": 95, "hours": 24, "bonus": 0, "icon": "📅"},
    "1week": {"price_usd": 3, "price_inr": 284, "hours": 168, "bonus": 25, "icon": "🍺"},
    "1month": {"price_usd": 5, "price_inr": 473, "hours": 720, "bonus": 50, "icon": "🌙", "own_bot": True},
    "1year": {"price_usd": 30, "price_inr": 2836, "hours": 8760, "bonus": 10, "icon": "🎄", "daily_bonus": True},
    "lifetime": {"price_usd": 100, "price_inr": 9455, "hours": 87600, "bonus": 0, "icon": "🔥", "lifetime": True}
}

# Language Options
LANGUAGES = {
    "EN": "English",
    "HI": "Hindi",
    "RU": "Russian",
    "HING": "Hinglish"
}

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')

# Helper functions
def load_json(filename, default=None):
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        return default if default is not None else {}
    except:
        return default if default is not None else {}

def save_json(filename, data):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except:
        return False

# Data Manager Class
class DataManager:
    def __init__(self):
        self.users = load_json(f"{DATA_DIR}/users.json", {})
        self.logs = load_json(f"{DATA_DIR}/logs.json", [])
        self.referrals = load_json(f"{DATA_DIR}/referrals.json", {})
        self.transactions = load_json(f"{DATA_DIR}/transactions.json", [])
        self.subscriptions = load_json(f"{DATA_DIR}/subscriptions.json", {})
        self.wallets = load_json(f"{DATA_DIR}/wallets.json", {})
        self.banned = load_json(f"{DATA_DIR}/banned.json", {})
        self.clones = load_json(f"{DATA_DIR}/clones.json", {})
        self.gc_settings = load_json(f"{DATA_DIR}/gc_settings.json", {})
        self.stickers = load_json(f"{DATA_DIR}/stickers.json", {})
        self.ads = load_json(f"{DATA_DIR}/ads.json", {})
    
    def get_user(self, user_id):
        user_id = str(user_id)
        if user_id not in self.users:
            self.users[user_id] = {
                'user_id': user_id,
                'username': '',
                'first_name': '',
                'tokens': 10,  # Welcome bonus
                'total_tokens_earned': 10,
                'total_tokens_used': 0,
                'balance_usd': 0,
                'balance_inr': 0,
                'currency': 'INR',
                'language': 'EN',
                'subscription': None,
                'subscription_expiry': None,
                'subscription_history': [],
                'total_checks': 0,
                'daily_checks': 0,
                'last_check_date': None,
                'total_referrals': 0,
                'referral_code': self.generate_code(),
                'referred_by': None,
                'last_daily_bonus': None,
                'created_at': datetime.now().isoformat(),
                'is_banned': False,
                'is_premium': False,
                'free_checks_left': FREE_DAILY_LIMIT,
                'invitation_links': [],
                'clone_bots': [],
                'last_activity': datetime.now().isoformat(),
                'spam_count': 0,
                'last_spam_time': None
            }
            self.save_users()
        return self.users[user_id]
    
    def generate_code(self):
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            if not any(u.get('referral_code') == code for u in self.users.values()):
                return code
    
    def save_users(self):
        save_json(f"{DATA_DIR}/users.json", self.users)
    
    def add_tokens(self, user_id, amount, reason="admin"):
        user = self.get_user(user_id)
        user['tokens'] += amount
        user['total_tokens_earned'] += amount
        self.transactions.append({
            'user_id': str(user_id),
            'type': 'token',
            'amount': amount,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        })
        self.save_users()
        save_json(f"{DATA_DIR}/transactions.json", self.transactions)
        return user['tokens']
    
    def remove_tokens(self, user_id, amount, reason="check"):
        user = self.get_user(user_id)
        if user['tokens'] >= amount:
            user['tokens'] -= amount
            user['total_tokens_used'] += amount
            self.transactions.append({
                'user_id': str(user_id),
                'type': 'token',
                'amount': -amount,
                'reason': reason,
                'timestamp': datetime.now().isoformat()
            })
            self.save_users()
            save_json(f"{DATA_DIR}/transactions.json", self.transactions)
            return True
        return False
    
    def add_balance(self, user_id, amount_usd, amount_inr, reason="referral"):
        user = self.get_user(user_id)
        user['balance_usd'] += amount_usd
        user['balance_inr'] += amount_inr
        self.save_users()
        return True
    
    def log_activity(self, user_id, action, details=""):
        user = self.get_user(user_id)
        log_entry = {
            'user_id': str(user_id),
            'username': user.get('username', ''),
            'first_name': user.get('first_name', ''),
            'action': action,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        self.logs.append(log_entry)
        save_json(f"{DATA_DIR}/logs.json", self.logs)
        
        user_log_file = f"{USER_LOGS_DIR}/{user_id}.json"
        user_logs = load_json(user_log_file, [])
        user_logs.append(log_entry)
        save_json(user_log_file, user_logs)
    
    def log_command(self, message, command, argument=""):
        user = self.get_user(message.from_user.id)
        log_data = {
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'timezone': 'IND',
            'user_id': message.from_user.id,
            'username': message.from_user.username or 'N/A',
            'chat_id': message.chat.id,
            'chat_type': message.chat.type,
            'gc_link': '',
            'message_id': message.message_id,
            'command': command,
            'argument': argument,
            'first_name': message.from_user.first_name or 'N/A'
        }
        
        if message.chat.type in ['group', 'supergroup']:
            try:
                invite = bot.export_chat_invite_link(message.chat.id)
                log_data['gc_link'] = invite
            except:
                pass
        
        self.logs.append(log_data)
        save_json(f"{DATA_DIR}/logs.json", self.logs)
        
        user_log_file = f"{USER_LOGS_DIR}/{message.from_user.id}.json"
        user_logs = load_json(user_log_file, [])
        user_logs.append(log_data)
        save_json(user_log_file, user_logs)
    
    def is_banned(self, user_id):
        return str(user_id) in self.banned
    
    def ban_user(self, user_id, reason=""):
        self.banned[str(user_id)] = {'reason': reason, 'banned_at': datetime.now().isoformat()}
        save_json(f"{DATA_DIR}/banned.json", self.banned)
    
    def unban_user(self, user_id):
        if str(user_id) in self.banned:
            del self.banned[str(user_id)]
            save_json(f"{DATA_DIR}/banned.json", self.banned)
            return True
        return False
    
    def get_subscription(self, user_id):
        user = self.get_user(user_id)
        if user.get('subscription'):
            try:
                expiry = datetime.fromisoformat(user['subscription_expiry'])
                if expiry > datetime.now():
                    return user['subscription'], expiry
            except:
                pass
        return None, None
    
    def set_subscription(self, user_id, plan_name):
        user = self.get_user(user_id)
        plan = SUBSCRIPTION_PLANS.get(plan_name)
        if not plan:
            return None
        
        expiry = datetime.now() + timedelta(hours=plan['hours'])
        user['subscription'] = plan_name
        user['subscription_expiry'] = expiry.isoformat()
        user['is_premium'] = True
        
        if 'subscription_history' not in user:
            user['subscription_history'] = []
        user['subscription_history'].append({
            'plan': plan_name,
            'activated_at': datetime.now().isoformat(),
            'expiry': expiry.isoformat()
        })
        
        if plan.get('bonus', 0) > 0:
            self.add_tokens(user_id, plan['bonus'], f"subscription_bonus_{plan_name}")
        
        self.save_users()
        self.subscriptions[str(user_id)] = {
            'plan': plan_name,
            'activated_at': datetime.now().isoformat(),
            'expiry': expiry.isoformat()
        }
        save_json(f"{DATA_DIR}/subscriptions.json", self.subscriptions)
        return expiry

data_manager = DataManager()

# User Sessions
user_sessions = {}

class UserSession:
    def __init__(self, user_id):
        self.user_id = user_id
        self.process = None
        self.is_logged_in = False
        self.is_checking = False
        self.output_queue = queue.Queue()
        self.current_url = None
        self.current_method = None
        self.current_threads = None
        self.output_history = []
        self.max_output_lines = 100
        self.check_start_time = None
        self.check_duration = None
        self.current_message_id = None
        self.last_message_id = None

# Message deletion helper
def delete_previous_message(chat_id, session):
    """Delete previous message"""
    try:
        if session.last_message_id:
            bot.delete_message(chat_id, session.last_message_id)
    except:
        pass

# Force Join Functions
def check_force_join(user_id):
    try:
        for channel in FORCE_JOIN_CHANNELS:
            username = channel.get('username', '')
            if username.startswith('@'):
                chat_member = bot.get_chat_member(username, user_id)
                if chat_member.status in ['left', 'kicked', 'banned']:
                    return False, channel
        return True, None
    except:
        return True, None

def create_force_join_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, channel in enumerate(FORCE_JOIN_CHANNELS):
        btn = types.InlineKeyboardButton(f"📢 JOIN CHANNEL {i+1}", url=channel.get('invite_link', ''))
        markup.add(btn)
    btn_joined = types.InlineKeyboardButton("✅ I'VE JOINED ALL", callback_data="check_join")
    markup.add(btn_joined)
    return markup

def create_main_menu(user_id):
    user = data_manager.get_user(user_id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn_login = types.InlineKeyboardButton("🔐 LOGIN", callback_data="btn_login")
    btn_check = types.InlineKeyboardButton("🚀 CHECK", callback_data="btn_check")
    markup.add(btn_login, btn_check)
    
    btn_profile = types.InlineKeyboardButton("👤 PROFILE", callback_data="btn_profile")
    btn_balance = types.InlineKeyboardButton("💰 BALANCE", callback_data="btn_balance")
    markup.add(btn_profile, btn_balance)
    
    btn_shop = types.InlineKeyboardButton("🛍️ SHOP", callback_data="btn_shop")
    btn_daily = types.InlineKeyboardButton("🎁 DAILY", callback_data="btn_daily")
    markup.add(btn_shop, btn_daily)
    
    btn_referral = types.InlineKeyboardButton("👥 REFERRAL", callback_data="btn_referral")
    btn_subscription = types.InlineKeyboardButton("💎 SUBSCRIPTION", callback_data="btn_subscription")
    markup.add(btn_referral, btn_subscription)
    
    btn_wallet = types.InlineKeyboardButton("👛 WALLET", callback_data="btn_wallet")
    btn_status = types.InlineKeyboardButton("📈 STATUS", callback_data="btn_status")
    markup.add(btn_wallet, btn_status)
    
    btn_clone = types.InlineKeyboardButton("🤖 CREATE BOT", callback_data="btn_clone")
    btn_help = types.InlineKeyboardButton("ℹ️ HELP", callback_data="btn_help")
    markup.add(btn_clone, btn_help)
    
    return markup

# ============================================
# BOT COMMANDS
# ============================================

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    data_manager.log_command(message, '/start')
    
    if data_manager.is_banned(user_id):
        bot.reply_to(message, "🚫 YOU'RE BANNED BY ADMIN. CONTACT FOR USED.")
        return
    
    has_joined, channel = check_force_join(user_id)
    
    if not has_joined:
        first_name = message.from_user.first_name or "User"
        restricted_text = f"""
🔒 <b>Aᴄᴄᴇss Rᴇsᴛʀɪᴄᴛᴇᴅ</b>
━━━━━━━━━━━━━━━━━━━
𝐇𝐞𝐲 <b>{first_name}</b> 💀!
🛡 ʏᴏᴜ ᴍᴜsᴛ ᴊᴏɪɴ ᴏᴜʀ ᴄʜᴀɴɴᴇʟ(s)
ʙᴇꜰᴏʀᴇ ᴜsɪɴɢ ᴛʜɪs ʙᴏᴛ.

📢 Cʟɪᴄᴋ ᴛʜᴇ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ ᴛᴏ ᴊᴏɪɴ,
ᴛʜᴇɴ ᴘʀᴇss I'ᴠᴇ Jᴏɪɴᴇᴅ Aʟʟ ✅
"""
        msg = bot.send_message(message.chat.id, restricted_text, reply_markup=create_force_join_keyboard())
        threading.Thread(target=delete_later, args=(message.chat.id, msg.message_id, 60)).start()
        return
    
    user = data_manager.get_user(user_id)
    user['username'] = message.from_user.username or ''
    user['first_name'] = message.from_user.first_name or ''
    user['last_activity'] = datetime.now().isoformat()
    data_manager.save_users()
    
    # Referral check
    try:
        if len(message.text.split()) > 1:
            referral_code = message.text.split()[1]
            for uid, udata in data_manager.users.items():
                if udata.get('referral_code') == referral_code and uid != str(user_id):
                    data_manager.add_tokens(uid, TOKEN_REFERRAL_BONUS, "referral_bonus")
                    data_manager.add_tokens(user_id, 1, "referral_join")
                    user['referred_by'] = uid
                    data_manager.save_users()
                    try:
                        bot.send_message(int(uid), f"🎉 New Referral! +{TOKEN_REFERRAL_BONUS} tokens")
                    except:
                        pass
                    break
    except:
        pass
    
    welcome_text = f"""
🤖 <b>{BOT_NAME}</b>
Version: {BOT_VERSION}

𝐇𝐞𝐲 <b>{user['first_name']}</b> 💀!

💰 <b>Tokens:</b> {user['tokens']}
💎 <b>Subscription:</b> {user.get('subscription') or 'None'}

<b>📋 Quick Start:</b>
1️⃣ Click <b>🔐 LOGIN</b>
2️⃣ Click <b>🚀 CHECK</b>
3️⃣ Send: <code>URL METHOD DURATION</code>

<b>💡 Example:</b>
<code>https://example.com GET 1min</code>

<b>Token Costs:</b>
• 2 tokens = 1 minute
• 5 tokens = 3 minutes
• 10 tokens = 10 minutes
"""
    msg = bot.send_message(message.chat.id, welcome_text, reply_markup=create_main_menu(user_id))
    
    if user_id in user_sessions:
        user_sessions[user_id].last_message_id = msg.message_id

def delete_later(chat_id, message_id, delay):
    time.sleep(delay)
    try:
        bot.delete_message(chat_id, message_id)
    except:
        pass

@bot.message_handler(commands=['help'])
def help_command(message):
    user_id = message.from_user.id
    data_manager.log_command(message, '/help')
    
    help_text = f"""
📚 <b>Help - {BOT_NAME}</b>

🔐 <b>Login:</b>
Auto-login with {BOT_NAME} credentials (Anonymous)

🚀 <b>Check Process:</b>
1. Login karo (Auto Login)
2. Check start karo
3. Format: <code>URL METHOD DURATION</code>

💰 <b>Token System:</b>
• Daily Bonus: {TOKEN_DAILY_BONUS} tokens
• Referral Bonus: {TOKEN_REFERRAL_BONUS} tokens
• 2 tokens = 1 minute
• 5 tokens = 3 minutes
• 10 tokens = 10 minutes

💎 <b>Subscription Plans:</b>
• 0.3$ (28₹) = 1 hour
• 1$ (95₹) = 1 day
• 3$ (284₹) = 1 week +25 tokens
• 5$ (473₹) = 1 month +50 tokens + Own Bot
• 30$ (2836₹) = 1 year +Daily 10 tokens
• 100$ (9455₹) = Lifetime +Join Friends

👛 <b>Withdrawal:</b>
• Minimum: 5$
• Commission: 20%

📌 <b>Commands:</b>
/start - Start bot
/help - Help
/login - Login (Auto)
/check - Check website
/stop - Stop checking
/output - View output
/profile - Your profile
/balance - Check balance
/daily - Daily bonus
/referral - Referral info
/status - Status
/subscription - Buy subscription

⚠️ <b>Warning:</b>
Only test your own websites
"""
    msg = bot.reply_to(message, help_text)
    if user_id in user_sessions:
        delete_previous_message(message.chat.id, user_sessions[user_id])
        user_sessions[user_id].last_message_id = msg.message_id

@bot.message_handler(commands=['login'])
def login_command(message):
    user_id = message.from_user.id
    data_manager.log_command(message, '/login')
    
    if data_manager.is_banned(user_id):
        bot.reply_to(message, "🚫 YOU'RE BANNED.")
        return
    
    if user_id not in user_sessions:
        user_sessions[user_id] = UserSession(user_id)
    
    session = user_sessions[user_id]
    
    if session.is_logged_in:
        bot.reply_to(message, "✅ Already logged in!")
        return
    
    msg = bot.reply_to(message, "🔄 <b>Auto-login process...</b>")
    
    def do_auto_login():
        try:
            script_file = None
            for f in ['c2.py', 'c.py', 'v.py']:
                if os.path.exists(f) and f != 'v.py':
                    script_file = f
                    break
            
            if not script_file:
                bot.edit_message_text("❌ No script found!", message.chat.id, msg.message_id)
                return
            
            session.process = pexpect.spawn(f'python3 {script_file}', encoding='utf-8', timeout=30)
            
            try:
                session.process.expect(['[Uu]sername', 'login', 'user'], timeout=5)
                session.process.sendline('v')
                time.sleep(1)
            except:
                pass
            
            try:
                session.process.expect(['[Pp]assword', 'pass'], timeout=5)
                session.process.sendline('v')
                time.sleep(3)
            except:
                pass
            
            if session.process.isalive():
                session.is_logged_in = True
                bot.edit_message_text("✅ <b>Login Successful!</b>\n\nAnonymous session started.", message.chat.id, msg.message_id)
                start_output_monitor(session)
                data_manager.log_activity(user_id, "login_success", "Auto login")
            else:
                bot.edit_message_text("❌ Login Failed!", message.chat.id, msg.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ Error: {str(e)}", message.chat.id, msg.message_id)
    
    threading.Thread(target=do_auto_login, daemon=True).start()

def start_output_monitor(session):
    def monitor():
        while session.process and session.process.isalive():
            try:
                output = session.process.read_nonblocking(size=4096, timeout=0.1)
                if output:
                    session.output_queue.put(output.strip())
                    session.output_history.append(output.strip())
                    if len(session.output_history) > session.max_output_lines:
                        session.output_history = session.output_history[-session.max_output_lines:]
            except pexpect.TIMEOUT:
                continue
            except pexpect.EOF:
                break
            except Exception:
                break
        session.is_checking = False
    
    threading.Thread(target=monitor, daemon=True).start()

@bot.message_handler(commands=['check'])
def check_command(message):
    user_id = message.from_user.id
    try:
        argument = message.text.split(' ', 1)[1] if len(message.text.split()) > 1 else ""
    except:
        argument = ""
    data_manager.log_command(message, '/check', argument)
    
    if data_manager.is_banned(user_id):
        bot.reply_to(message, "🚫 YOU'RE BANNED.")
        return
    
    user = data_manager.get_user(user_id)
    
    if user_id not in user_sessions:
        user_sessions[user_id] = UserSession(user_id)
    
    session = user_sessions[user_id]
    
    if not session.is_logged_in:
        msg = bot.reply_to(message, "❌ Pehle login karo!\nClick: 🔐 LOGIN")
        return
    
    if session.is_checking:
        bot.reply_to(message, "⚠️ Already checking!")
        return
    
    sub_plan, sub_expiry = data_manager.get_subscription(user_id)
    
    if not sub_plan:
        today = datetime.now().date().isoformat()
        if user.get('last_check_date') != today:
            user['daily_checks'] = 0
            user['last_check_date'] = today
            data_manager.save_users()
        
        if user['daily_checks'] >= FREE_DAILY_LIMIT:
            markup = types.InlineKeyboardMarkup()
            btn_sub = types.InlineKeyboardButton("💎 BUY SUBSCRIPTION", callback_data="btn_subscription")
            markup.add(btn_sub)
            bot.reply_to(message, f"❌ Daily limit reached!\nFree: {FREE_DAILY_LIMIT} checks/day", reply_markup=markup)
            return
    
    msg = bot.reply_to(
        message,
        "📝 <b>Check Format:</b>\n\n"
        "<code>URL METHOD DURATION</code>\n\n"
        "<b>Example:</b>\n"
        "<code>https://example.com GET 1min</code>\n\n"
        "<b>Durations:</b>\n"
        "• 1min = 2 tokens\n"
        "• 3min = 5 tokens\n"
        "• 10min = 10 tokens"
    )
    bot.register_next_step_handler(msg, process_check_command)

def process_check_command(message):
    user_id = message.from_user.id
    session = user_sessions.get(user_id)
    user = data_manager.get_user(user_id)
    
    if not session:
        bot.reply_to(message, "❌ Session expired. /start karo")
        return
    
    try:
        parts = message.text.strip().split()
        if len(parts) < 3:
            bot.reply_to(message, "❌ Format: URL METHOD DURATION")
            return
        
        url = parts[0]
        method = parts[1].upper()
        duration = parts[2].lower()
        
        duration_map = {"1min": (1, 2), "3min": (3, 5), "10min": (10, 10)}
        
        if duration not in duration_map:
            bot.reply_to(message, "❌ Invalid duration! Use: 1min, 3min, 10min")
            return
        
        minutes, token_cost = duration_map[duration]
        
        sub_plan, sub_expiry = data_manager.get_subscription(user_id)
        
        if not sub_plan:
            if user['tokens'] < token_cost:
                bot.reply_to(message, f"❌ Insufficient tokens!\nNeed: {token_cost}\nYour: {user['tokens']}")
                return
            if not data_manager.remove_tokens(user_id, token_cost, "check_cost"):
                bot.reply_to(message, "❌ Token deduction failed!")
                return
        
        session.current_url = url
        session.current_method = method
        session.check_duration = minutes
        session.check_start_time = datetime.now()
        
        user['total_checks'] += 1
        user['daily_checks'] += 1
        user['last_check_date'] = datetime.now().date().isoformat()
        data_manager.save_users()
        
        data_manager.log_activity(user_id, "check_start", f"URL: {url}, Method: {method}, Duration: {minutes}min")
        
        msg = bot.reply_to(
            message,
            f"🚀 <b>Check Started!</b>\n\n"
            f"URL: {url}\nMethod: {method}\nDuration: {minutes} min\n"
            f"Cost: {token_cost} tokens\n\n"
            f"⏱️ Auto-stop after {minutes} minute(s)"
        )
        
        session.current_message_id = msg.message_id
        session.last_message_id = msg.message_id
        
        def do_check():
            try:
                session.is_checking = True
                command = f"CHEAK {url} {method} 100"
                session.process.sendline(command)
                
                def auto_stop():
                    time.sleep(minutes * 60)
                    if session.is_checking:
                        try:
                            if session.process and session.process.isalive():
                                session.process.sendintr()
                                time.sleep(1)
                                if session.process.isalive():
                                    session.process.terminate()
                            session.is_checking = False
                            markup = types.InlineKeyboardMarkup()
                            btn_sub = types.InlineKeyboardButton("💎 BUY SUBSCRIPTION", callback_data="btn_subscription")
                            markup.add(btn_sub)
                            bot.send_message(message.chat.id, f"⏱️ Time Complete! ({minutes} min)\n\n💎 Buy subscription for longer checks!", reply_markup=markup)
                        except:
                            pass
                
                threading.Thread(target=auto_stop, daemon=True).start()
            except Exception as e:
                session.is_checking = False
                bot.send_message(message.chat.id, f"❌ Error: {str(e)}")
        
        threading.Thread(target=do_check, daemon=True).start()
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['profile'])
def profile_command(message):
    user_id = message.from_user.id
    data_manager.log_command(message, '/profile')
    
    user = data_manager.get_user(user_id)
    sub_plan, sub_expiry = data_manager.get_subscription(user_id)
    
    currency = user.get('currency', 'INR')
    balance = f"₹{user['balance_inr']}" if currency == 'INR' else f"${user['balance_usd']}"
    token_value = user['tokens'] * TOKEN_TO_INR
    
    profile_text = f"""
👤 <b>Your Profile</b>

Name: {user['first_name']}
Username: @{user.get('username', 'N/A')}
ID: <code>{user_id}</code>

🪙 Tokens: {user['tokens']}
💰 Wallet: {balance} (~₹{token_value})
💎 Subscription: {sub_plan or 'None'}
{'⏰ Expiry: ' + sub_expiry.strftime('%Y-%m-%d %H:%M') if sub_expiry else ''}

🚧 Total Checks: {user['total_checks']}
📊 Checks Today: {user['daily_checks']}/{FREE_DAILY_LIMIT}

🌐 Language: {LANGUAGES.get(user.get('language', 'EN'), 'English')}
🕐 Timezone: IND

📅 Member Since: {user['created_at'][:10]}
"""
    msg = bot.reply_to(message, profile_text)

@bot.message_handler(commands=['balance'])
def balance_command(message):
    user_id = message.from_user.id
    data_manager.log_command(message, '/balance')
    
    user = data_manager.get_user(user_id)
    sub_plan, sub_expiry = data_manager.get_subscription(user_id)
    
    balance_text = f"""
💰 <b>Your Balance</b>

🪙 Tokens: {user['tokens']}
💎 Subscription: {sub_plan or 'None'}

📊 Usage:
• Total Checks: {user['total_checks']}
• Tokens Used: {user['total_tokens_used']}
• Tokens Earned: {user['total_tokens_earned']}

Earn:
• Daily: /daily (+{TOKEN_DAILY_BONUS})
• Referral: /referral (+{TOKEN_REFERRAL_BONUS})
"""
    msg = bot.reply_to(message, balance_text)

@bot.message_handler(commands=['daily'])
def daily_command(message):
    user_id = message.from_user.id
    data_manager.log_command(message, '/daily')
    
    user = data_manager.get_user(user_id)
    today = datetime.now().date().isoformat()
    
    if user.get('last_daily_bonus') == today:
        bot.reply_to(message, "❌ Already claimed today!")
        return
    
    user['last_daily_bonus'] = today
    data_manager.add_tokens(user_id, TOKEN_DAILY_BONUS, "daily_bonus")
    
    bot.reply_to(message, f"🎁 +{TOKEN_DAILY_BONUS} tokens!\nBalance: {user['tokens']} tokens")

@bot.message_handler(commands=['referral'])
def referral_command(message):
    user_id = message.from_user.id
    data_manager.log_command(message, '/referral')
    
    user = data_manager.get_user(user_id)
    ref_code = user.get('referral_code', 'N/A')
    bot_username = bot.get_me().username
    ref_link = f"https://t.me/{bot_username}?start={ref_code}"
    
    ref_text = f"""
👥 <b>Referral System</b>

Code: <code>{ref_code}</code>
Link: {ref_link}

Stats:
• Referrals: {user.get('total_referrals', 0)}
• Earned: {user.get('total_referrals', 0) * TOKEN_REFERRAL_BONUS} tokens

Share and earn {TOKEN_REFERRAL_BONUS} tokens per referral!
"""
    bot.reply_to(message, ref_text)

@bot.message_handler(commands=['subscription'])
def subscription_command(message):
    user_id = message.from_user.id
    data_manager.log_command(message, '/subscription')
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for plan_name, plan in SUBSCRIPTION_PLANS.items():
        btn = types.InlineKeyboardButton(
            f"{plan['icon']} {plan['duration']} - ${plan['price_usd']} (₹{plan['price_inr']})",
            callback_data=f"sub_{plan_name}"
        )
        markup.add(btn)
    
    sub_text = f"""
💎 <b>Subscription Plans</b>

🕐 1 Hour: 0.3$ (28₹)
📅 1 Day: 1$ (95₹)
🍺 1 Week: 3$ (284₹) +25 tokens
🌙 1 Month: 5$ (473₹) +50 tokens + Own Bot
🎄 1 Year: 30$ (2836₹) +Daily 10 tokens
🔥 Lifetime: 100$ (9455₹) +Join Friends

Payment: Telegram Stars ⭐
"""
    msg = bot.reply_to(message, sub_text, reply_markup=markup)

@bot.message_handler(commands=['status'])
def status_command(message):
    user_id = message.from_user.id
    data_manager.log_command(message, '/status')
    
    user = data_manager.get_user(user_id)
    sub_plan, sub_expiry = data_manager.get_subscription(user_id)
    
    status_text = f"""
📈 <b>Status</b>

User: {user['first_name']}
Tokens: {user['tokens']}
Subscription: {sub_plan or 'None'}

Session:
{'✅ Logged in' if user_id in user_sessions and user_sessions[user_id].is_logged_in else '❌ Not logged in'}
{'🔄 Checking' if user_id in user_sessions and user_sessions[user_id].is_checking else '⏹️ Idle'}
"""
    bot.reply_to(message, status_text)

@bot.message_handler(commands=['output'])
def output_command(message):
    user_id = message.from_user.id
    data_manager.log_command(message, '/output')
    
    if user_id in user_sessions:
        session = user_sessions[user_id]
        if session.output_history:
            # Last 5 lines in message
            output_text = '\n'.join(session.output_history[-5:])
            
            # Full output to file
            output_file = f"MONX-{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(output_file, 'w') as f:
                f.write('\n'.join(session.output_history))
                f.write(f"\n\nCredit: {BOT_USERNAME}")
            
            bot.send_message(message.chat.id, f"📊 <b>Output by {BOT_NAME}:</b>\n\n<code>{output_text}</code>\n\nFull output:")
            with open(output_file, 'rb') as f:
                bot.send_document(message.chat.id, f)
            os.remove(output_file)
        else:
            bot.reply_to(message, "📊 No output available")
    else:
        bot.reply_to(message, "❌ Session not found")

@bot.message_handler(commands=['stop'])
def stop_command(message):
    user_id = message.from_user.id
    data_manager.log_command(message, '/stop')
    
    if user_id in user_sessions:
        session = user_sessions[user_id]
        if session.is_checking:
            try:
                if session.process and session.process.isalive():
                    session.process.sendintr()
                    time.sleep(1)
                    if session.process.isalive():
                        session.process.terminate()
                session.is_checking = False
                bot.reply_to(message, "✅ Check stopped!")
            except Exception as e:
                bot.reply_to(message, f"❌ Error: {str(e)}")
        else:
            bot.reply_to(message, "❌ No check in progress")
    else:
        bot.reply_to(message, "❌ Session not found")

# ============================================
# CALLBACK HANDLERS
# ============================================

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    data = call.data
    
    try:
        if data == "check_join":
            has_joined, channel = check_force_join(user_id)
            if has_joined:
                bot.answer_callback_query(call.id, "✅ Thanks!")
                try:
                    bot.delete_message(call.message.chat.id, call.message.message_id)
                except:
                    pass
                
                user = data_manager.get_user(user_id)
                welcome_msg = bot.send_message(call.message.chat.id, "✅ <b>Thanks For Joining!</b>\n\n⏱️ Loading... 5")
                
                def countdown():
                    for i in range(4, 0, -1):
                        time.sleep(1)
                        try:
                            bot.edit_message_text(f"✅ <b>Thanks For Joining!</b>\n\n⏱️ Loading... {i}", call.message.chat.id, welcome_msg.message_id)
                        except:
                            pass
                    time.sleep(1)
                    try:
                        bot.delete_message(call.message.chat.id, welcome_msg.message_id)
                    except:
                        pass
                    start_command(call.message)
                
                threading.Thread(target=countdown, daemon=True).start()
            else:
                bot.answer_callback_query(call.id, "❌ Join all channels first!", show_alert=True)
        
        elif data == "btn_login":
            login_command(call.message)
        elif data == "btn_check":
            check_command(call.message)
        elif data == "btn_profile":
            profile_command(call.message)
        elif data == "btn_balance":
            balance_command(call.message)
        elif data == "btn_shop":
            subscription_command(call.message)
        elif data == "btn_daily":
            daily_command(call.message)
        elif data == "btn_referral":
            referral_command(call.message)
        elif data == "btn_subscription":
            subscription_command(call.message)
        elif data == "btn_wallet":
            wallet_command(call.message)
        elif data == "btn_status":
            status_command(call.message)
        elif data == "btn_clone":
            clone_bot_command(call.message)
        elif data == "btn_help":
            help_command(call.message)
        elif data.startswith("sub_"):
            plan_name = data.split("_")[1]
            process_subscription(call, plan_name)
        
    except Exception as e:
        print(f"Callback error: {e}")
        try:
            bot.answer_callback_query(call.id, f"❌ Error")
        except:
            pass

def wallet_command(message):
    user_id = message.from_user.id
    user = data_manager.get_user(user_id)
    
    wallet_text = f"""
👛 <b>Wallet</b>

Balance (INR): ₹{user['balance_inr']}
Balance (USD): ${user['balance_usd']}
Tokens: {user['tokens']}

<b>Withdrawal:</b>
Minimum: $5
Commission: 20%
Methods: INR/USDT
"""
    bot.reply_to(message, wallet_text)

def clone_bot_command(message):
    user_id = message.from_user.id
    user = data_manager.get_user(user_id)
    sub_plan, sub_expiry = data_manager.get_subscription(user_id)
    
    if not sub_plan or sub_plan not in ['1month', '1year', 'lifetime']:
        bot.reply_to(message, "❌ Clone bot requires 5$+ subscription!")
        return
    
    msg = bot.reply_to(message, "🤖 <b>Create Your Own Bot</b>\n\nBot Token bhejo (@BotFather se):")
    bot.register_next_step_handler(msg, process_clone_token)

def process_clone_token(message):
    user_id = message.from_user.id
    token = message.text.strip()
    
    try:
        # Test token
        test_bot = telebot.TeleBot(token)
        bot_info = test_bot.get_me()
        
        data_manager.clones[str(user_id)] = {
            'bot_token': token,
            'bot_username': bot_info.username,
            'bot_name': bot_info.first_name,
            'created_at': datetime.now().isoformat(),
            'owner_id': user_id,
            'bot_name_custom': f"MONX-{bot_info.first_name}"
        }
        save_json(f"{DATA_DIR}/clones.json", data_manager.clones)
        
        data_manager.log_activity(user_id, "clone_bot_created", f"Created bot: @{bot_info.username}")
        
        bot.reply_to(message, f"✅ <b>Bot Created!</b>\n\nName: {bot_info.first_name}\nUsername: @{bot_info.username}\n\nAapka bot ready hai!")
    except Exception as e:
        bot.reply_to(message, f"❌ Invalid token!\nError: {str(e)}")

def process_subscription(call, plan_name):
    if plan_name not in SUBSCRIPTION_PLANS:
        bot.answer_callback_query(call.id, "❌ Invalid plan!")
        return
    
    plan = SUBSCRIPTION_PLANS[plan_name]
    
    # Get sticker/image from data
    stickers = data_manager.stickers
    if stickers:
        # Send sticker first
        sticker_id = random.choice(list(stickers.values()))
        try:
            bot.send_sticker(call.message.chat.id, sticker_id)
        except:
            pass
    
    prices = [types.LabeledPrice(label=f"{plan['duration']} Subscription", amount=int(plan['price_usd'] * 100))]
    
    try:
        bot.send_invoice(
            call.message.chat.id,
            title=f"{BOT_NAME} - {plan['duration']}",
            description=f"Subscription: {plan['duration']}\nBonus: {plan['bonus']} tokens",
            invoice_payload=f"sub_{plan_name}_{call.from_user.id}",
            provider_token="",
            currency="XTR",
            prices=prices
        )
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Error: {str(e)}")

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout_handler(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def successful_payment_handler(message):
    user_id = message.from_user.id
    payload = message.successful_payment.invoice_payload
    parts = payload.split('_')
    plan_name = parts[1]
    
    if plan_name in SUBSCRIPTION_PLANS:
        plan = SUBSCRIPTION_PLANS[plan_name]
        expiry = data_manager.set_subscription(user_id, plan_name)
        
        # Send sticker/image as confirmation
        stickers = data_manager.stickers
        if stickers:
            sticker_id = random.choice(list(stickers.values()))
            try:
                bot.send_sticker(message.chat.id, sticker_id)
            except:
                pass
        
        data_manager.log_activity(user_id, "subscription_purchase", f"Purchased {plan_name} via Stars")
        
        bot.reply_to(
            message,
            f"✅ <b>Subscription Activated!</b>\n\n"
            f"Plan: {plan['icon']} {plan['duration']}\n"
            f"Expiry: {expiry.strftime('%Y-%m-%d %H:%M')}\n"
            f"Bonus: +{plan['bonus']} tokens\n\n"
            f"Thank you for supporting {BOT_NAME}!"
        )

# ============================================
# ADMIN COMMANDS
# ============================================

@bot.message_handler(commands=['admin'])
def admin_command(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return
    
    stats = {
        'total_users': len(data_manager.users),
        'total_premium': sum(1 for u in data_manager.users.values() if u.get('is_premium')),
        'total_banned': len(data_manager.banned),
        'total_clones': len(data_manager.clones)
    }
    
    admin_text = f"""
👑 <b>Admin Panel</b>

Users: {stats['total_users']}
Premium: {stats['total_premium']}
Banned: {stats['total_banned']}
Clones: {stats['total_clones']}

<b>Commands:</b>
/addc &lt;channel_link&gt; - Add force join channel
/rmvc &lt;channel_link&gt; - Remove channel
/give &lt;user_id&gt; &lt;tokens&gt; - Give tokens
/addb &lt;user_id&gt; &lt;amount&gt; - Add balance
/ban &lt;user_id&gt; - Ban user
/unban &lt;user_id&gt; - Unban user
/log [user_id] - View logs
/broadcast &lt;msg&gt; - Broadcast
/adds - Add sticker (reply to sticker)
/addi - Add image (reply to image)
/subunlock &lt;user_id&gt; &lt;plan&gt; - Give subscription
/sunlock &lt;user_id&gt; - Remove subscription
"""
    bot.reply_to(message, admin_text)

@bot.message_handler(commands=['addc'])
def add_channel_command(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Usage: /addc <channel_link>")
            return
        
        channel_link = parts[1]
        channel_username = f"@channel_{len(FORCE_JOIN_CHANNELS)+1}"
        
        FORCE_JOIN_CHANNELS.append({
            "username": channel_username,
            "invite_link": channel_link
        })
        save_json(CHANNELS_FILE, FORCE_JOIN_CHANNELS)
        
        bot.reply_to(message, f"✅ Channel added!\nLink: {channel_link}")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['rmvc'])
def remove_channel_command(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Usage: /rmvc <channel_link>")
            return
        
        channel_link = parts[1]
        for i, ch in enumerate(FORCE_JOIN_CHANNELS):
            if ch.get('invite_link') == channel_link:
                FORCE_JOIN_CHANNELS.pop(i)
                save_json(CHANNELS_FILE, FORCE_JOIN_CHANNELS)
                bot.reply_to(message, "✅ Channel removed!")
                return
        
        bot.reply_to(message, "❌ Channel not found!")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['give'])
def give_command(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return
    
    try:
        parts = message.text.split()
        target_id = int(parts[1])
        amount = int(parts[2])
        
        new_balance = data_manager.add_tokens(target_id, amount, "admin_give")
        bot.reply_to(message, f"✅ {amount} tokens given to {target_id}")
        try:
            bot.send_message(target_id, f"💰 +{amount} tokens from admin!")
        except:
            pass
    except:
        bot.reply_to(message, "❌ Usage: /give <user_id> <amount>")

@bot.message_handler(commands=['addb'])
def addb_command(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return
    
    try:
        parts = message.text.split()
        target_id = int(parts[1])
        amount = float(parts[2])
        
        data_manager.add_balance(target_id, amount, amount * 95, "admin_balance")
        bot.reply_to(message, f"✅ ${amount} added to {target_id}")
    except:
        bot.reply_to(message, "❌ Usage: /addb <user_id> <amount_usd>")

@bot.message_handler(commands=['ban'])
def ban_command(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return
    
    try:
        target_id = int(message.text.split()[1])
        data_manager.ban_user(target_id)
        bot.reply_to(message, f"✅ User {target_id} banned!")
        try:
            bot.send_message(target_id, "🚫 YOU'RE BANNED BY ADMIN. CONTACT FOR USED.")
        except:
            pass
    except:
        bot.reply_to(message, "❌ Usage: /ban <user_id>")

@bot.message_handler(commands=['unban'])
def unban_command(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return
    
    try:
        target_id = int(message.text.split()[1])
        if data_manager.unban_user(target_id):
            bot.reply_to(message, f"✅ User {target_id} unbanned!")
        else:
            bot.reply_to(message, "❌ Not banned")
    except:
        bot.reply_to(message, "❌ Usage: /unban <user_id>")

@bot.message_handler(commands=['log'])
def log_command(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return
    
    try:
        parts = message.text.split()
        if len(parts) > 1:
            target_id = parts[1]
            user_log_file = f"{USER_LOGS_DIR}/{target_id}.json"
            logs = load_json(user_log_file, [])
            if logs:
                with open(f"log_{target_id}.json", 'w') as f:
                    json.dump(logs, f, indent=2)
                bot.send_document(message.chat.id, open(f"log_{target_id}.json", 'rb'))
                os.remove(f"log_{target_id}.json")
            else:
                bot.reply_to(message, "No logs found")
        else:
            with open(f"{DATA_DIR}/logs.json", 'w') as f:
                json.dump(data_manager.logs[-100:], f, indent=2)
            bot.send_document(message.chat.id, open(f"{DATA_DIR}/logs.json", 'rb'))
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['broadcast'])
def broadcast_command(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return
    
    try:
        broadcast_text = message.text.split(' ', 1)[1]
        sent = 0
        failed = 0
        for uid in data_manager.users:
            try:
                bot.send_message(int(uid), broadcast_text)
                sent += 1
                time.sleep(0.3)
            except:
                failed += 1
        bot.reply_to(message, f"📢 Sent: {sent}, Failed: {failed}")
    except:
        bot.reply_to(message, "❌ Usage: /broadcast <message>")

@bot.message_handler(commands=['adds'])
def add_sticker_command(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return
    
    if message.reply_to_message and message.reply_to_message.sticker:
        sticker_id = message.reply_to_message.sticker.file_id
        data_manager.stickers[str(len(data_manager.stickers)+1)] = sticker_id
        save_json(f"{DATA_DIR}/stickers.json", data_manager.stickers)
        bot.reply_to(message, "✅ Sticker added!")
    else:
        bot.reply_to(message, "❌ Reply to a sticker!")

@bot.message_handler(commands=['addi'])
def add_image_command(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return
    
    if message.reply_to_message and message.reply_to_message.photo:
        photo_id = message.reply_to_message.photo[-1].file_id
        data_manager.stickers[str(len(data_manager.stickers)+1)] = photo_id
        save_json(f"{DATA_DIR}/stickers.json", data_manager.stickers)
        bot.reply_to(message, "✅ Image added!")
    else:
        bot.reply_to(message, "❌ Reply to an image!")

@bot.message_handler(commands=['subunlock'])
def subunlock_command(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return
    
    try:
        parts = message.text.split()
        target_id = int(parts[1])
        plan_name = parts[2]
        
        if plan_name in SUBSCRIPTION_PLANS:
            expiry = data_manager.set_subscription(target_id, plan_name)
            bot.reply_to(message, f"✅ Subscription {plan_name} given to {target_id}")
            try:
                bot.send_message(target_id, f"🎉 Subscription activated: {plan_name}")
            except:
                pass
        else:
            bot.reply_to(message, "❌ Invalid plan!")
    except:
        bot.reply_to(message, "❌ Usage: /subunlock <user_id> <plan_name>")

@bot.message_handler(commands=['sunlock'])
def sunlock_command(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return
    
    try:
        target_id = int(message.text.split()[1])
        user = data_manager.get_user(target_id)
        user['subscription'] = None
        user['subscription_expiry'] = None
        user['is_premium'] = False
        data_manager.save_users()
        bot.reply_to(message, f"✅ Subscription removed from {target_id}")
    except:
        bot.reply_to(message, "❌ Usage: /sunlock <user_id>")

# ============================================
# MESSAGE HANDLER
# ============================================

@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    user_id = message.from_user.id
    
    if data_manager.is_banned(user_id):
        bot.reply_to(message, "🚫 YOU'RE BANNED BY ADMIN. CONTACT FOR USED.")
        return
    
    if message.text and message.text.startswith('/'):
        data_manager.log_command(message, message.text.split()[0], ' '.join(message.text.split()[1:]))
    
    if message.text and message.text.startswith(('http://', 'https://')):
        if user_id in user_sessions and user_sessions[user_id].is_logged_in:
            check_input = f"{message.text} GET 1min"
            message.text = check_input
            process_check_command(message)
        else:
            bot.reply_to(message, "❌ Pehle login karo!")

# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print(f"🤖 {BOT_NAME} Starting...")
    print(f"Version: {BOT_VERSION}")
    print(f"Owner: {OWNER_USERNAME}")
    print("=" * 60)
    
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Bot token not set!")
        sys.exit(1)
    
    print("✅ Bot token configured")
    print("🚀 Bot is running...")
    
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"❌ Crash: {e}")
            print("🔄 Restarting...")
            time.sleep(0.6)
