"""
🔥 PremiumKillerBot - Complete Telegram Session Creator + 2FA Support
📱 Phone → OTP → 2FA → Session Ready!
💎 Owner/Sudo Only - Unlimited Sessions
"""

import os
import asyncio
import time
import json
import logging
from pyrogram import Client, filters, errors
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from pyrogram.errors import SessionPasswordNeeded, PhoneCodeInvalid

# ═══════════════════════════════════════════════════════════════════════════════
# 📋 CONFIG - EDIT THESE
# ═══════════════════════════════════════════════════════════════════════════════

API_ID = 12345678  # Your API ID
API_HASH = "your_api_hash_here"  # Your API Hash
OWNER_ID = 123456789  # Your User ID
SESSION_DIR = "sessions"  # Folder to save sessions

# SUDO USERS (Multiple owners)
SUDOS = [123456789, 987654321]  # Add more IDs

# ═══════════════════════════════════════════════════════════════════════════════
# 🤖 PremiumKillerBot Class
# ═══════════════════════════════════════════════════════════════════════════════

class PremiumKillerBot:
    def __init__(self):
        self.app = None
        self.sessions = {}
        self.pending_sessions = {}  # phone → data
        self.waiting_2fa = {}       # phone → user_id
        
        # Create sessions dir
        os.makedirs(SESSION_DIR, exist_ok=True)
        self.load_sessions()
    
    async def start(self):
        self.app = Client("killer_bot", api_id=API_ID, api_hash=API_HASH)
        
        # Register handlers
        self.app.on_message(filters.command("start") & filters.private)(self.start_handler)
        self.app.on_message(filters.command("sessions") & filters.private)(self.sessions_handler)
        self.app.on_message(filters.command("stats") & filters.private)(self.stats_handler)
        self.app.on_message(filters.command("clear") & filters.private)(self.clear_handler)
        
        # Session creation handlers
        self.app.on_message(filters.private & filters.regex(r'^\+[1-9]\d{1,14}$'))(self.phone_handler)
        self.app.on_message(filters.private & filters.text & filters.regex(r'^\d{5,6}$') & ~filters.command("start"))(self.otp_handler)
        self.app.on_message(filters.private & filters.text & ~filters.regex(r'^\d{5,6}$') & ~filters.regex(r'^\+[1-9]\d{1,14}$') & ~filters.command("start"))(self.password_handler)
        
        await self.app.start()
        print("🚀 PremiumKillerBot Started!")
        await asyncio.Event().wait()  # Keep alive
    
    def load_sessions(self):
        """Load existing sessions"""
        try:
            if os.path.exists("sessions.json"):
                with open("sessions.json", "r") as f:
                    self.sessions = json.load(f)
                print(f"📊 Loaded {len(self.sessions)} sessions")
        except:
            self.sessions = {}
    
    async def save_sessions(self):
        """Save sessions to JSON"""
        try:
            with open("sessions.json", "w") as f:
                json.dump(self.sessions, f, indent=2)
        except Exception as e:
            print(f"❌ Save error: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# 🎯 HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════

bot = PremiumKillerBot()

@bot.app.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in (OWNER_ID, *SUDOS):
        return await message.reply("🔒 **Owner Only!**")
    
    await message.reply(
        "🚀 **PremiumKillerBot Active!**\n\n"
        "📱 **Create Session:**\n"
        "`+919876543210`\n\n"
        "🔑 **Flow:**\n"
        "1. Phone → 2. OTP → 3. 2FA (if enabled)\n\n"
        "📊 **Commands:**\n"
        "`/sessions` - List all\n"
        "`/stats` - Stats\n"
        "`/clear` - Delete all",
        parse_mode=ParseMode.MARKDOWN
    )

@bot.app.on_message(filters.command("sessions") & filters.private)
async def sessions_handler(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in (OWNER_ID, *SUDOS):
        return
    
    if not bot.sessions:
        return await message.reply("📭 **No sessions!**")
    
    text = "📱 **Active Sessions:**\n\n"
    premium_count = 0
    total = len(bot.sessions)
    
    for name, data in bot.sessions.items():
        status = "💎 PREMIUM" if data.get('is_premium') else "📱 Normal"
        if data.get('is_premium'):
            premium_count += 1
        text += f"• `{data['phone']}` - {status}\n"
    
    text += f"\n📊 **{premium_count}/{total} Premium**"
    await message.reply(text, parse_mode=ParseMode.MARKDOWN)

@bot.app.on_message(filters.command("stats") & filters.private)
async def stats_handler(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in (OWNER_ID, *SUDOS):
        return
    
    total = len(bot.sessions)
    premium = sum(1 for s in bot.sessions.values() if s.get('is_premium'))
    normal = total - premium
    
    text = f"""📊 **Bot Stats:**
📱 **Total:** `{total}`
💎 **Premium:** `{premium}`
📱 **Normal:** `{normal}`
"""
    await message.reply(text, parse_mode=ParseMode.MARKDOWN)

@bot.app.on_message(filters.command("clear") & filters.private)
async def clear_handler(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in (OWNER_ID, *SUDOS):
        return
    
    confirm = message.text.split(" ")[1] if len(message.text.split()) > 1 else None
    
    if confirm == "yes":
        # Delete session files
        for session_name in list(bot.sessions.keys()):
            path = bot.sessions[session_name]['path']
            if os.path.exists(path + ".session"):
                os.remove(path + ".session")
        
        bot.sessions.clear()
        await bot.save_sessions()
        await message.reply("🗑️ **All sessions cleared!**")
    else:
        await message.reply("⚠️ **Confirm:** `/clear yes`")

# ═══════════════════════════════════════════════════════════════════════════════
# 🔥 SESSION CREATION - 3 STEP (Phone → OTP → 2FA)
# ═══════════════════════════════════════════════════════════════════════════════

@bot.app.on_message(filters.private & filters.regex(r'^\+[1-9]\d{1,14}$'))
async def phone_handler(client: Client, message: Message):
    phone = message.text.strip()
    user_id = message.from_user.id
    
    if user_id not in (OWNER_ID, *SUDOS):
        return await message.reply("🔒 **Owner/Sudo only!**")
    
    # Cleanup old sessions for this user
    to_delete = []
    for p, data in list(bot.pending_sessions.items()):
        if data['user_id'] == user_id:
            to_delete.append(p)
    for p in to_delete:
        del bot.pending_sessions[p]
    
    session_name = f"session_{int(time.time())}"
    bot.pending_sessions[phone] = {
        'user_id': user_id,
        'session_name': session_name,
        'time': time.time()
    }
    
    await message.reply(
        f"📱 **Phone Registered:** `{phone}`\n\n"
        f"🔑 **Step 1/3 - Send OTP:**\n"
        "`12345` or `123456`\n\n"
        f"🔐 **Step 2/3** - 2FA Password (if enabled)\n"
        f"⏰ **Timeout:** 3 minutes",
        parse_mode=ParseMode.MARKDOWN
    )

@bot.app.on_message(filters.private & filters.text & filters.regex(r'^\d{5,6}$') & ~filters.command("start"))
async def otp_handler(client: Client, message: Message):
    code = message.text.strip()
    user_id = message.from_user.id
    
    # Find pending session
    pending_phone = None
    session_data = None
    for phone, data in list(bot.pending_sessions.items()):
        if data['user_id'] == user_id and (time.time() - data['time']) < 180:
            pending_phone = phone
            session_data = data
            break
    
    if not pending_phone:
        return await message.reply("❌ **No active phone!** Send phone first.")
    
    session_name = session_data['session_name']
    session_path = f"{SESSION_DIR}/{session_name}"
    
    del bot.pending_sessions[pending_phone]
    bot.waiting_2fa[pending_phone] = user_id
    
    try:
        await message.reply(f"🔄 **Verifying `{pending_phone}`...**")
        
        # Create temp client
        temp_client = Client(session_path, api_id=API_ID, api_hash=API_HASH, phone_number=pending_phone)
        await temp_client.connect()
        
        # Send code (real flow)
        sent_code = await temp_client.send_code(pending_phone)
        
        # Sign in
        await temp_client.sign_in(
            phone=pending_phone,
            phone_code_hash=sent_code.phone_code_hash,
            phone_code=code
        )
        
        # Success!
        me = await temp_client.get_me()
        is_premium = getattr(me, 'is_premium', False)
        
        # Store session
        bot.sessions[session_name] = {
            'phone': pending_phone,
            'user_id': me.id,
            'username': getattr(me, 'username', None) or '',
            'first_name': getattr(me, 'first_name', '') or '',
            'is_premium': is_premium,
            'path': session_path,
            'active': True,
            'created': int(time.time())
        }
        
        await bot.save_sessions()
        await temp_client.disconnect()
        
        del bot.waiting_2fa[pending_phone]
        
        status = "💎 PREMIUM" if is_premium else "📱 Normal"
        await message.reply(
            f"✅ **Session Created Successfully!**\n\n"
            f"📱 `{pending_phone}`\n"
            f"👤 `{me.first_name}`\n"
            f"🆔 `{me.id}`\n"
            f"{status}\n\n"
            f"📊 **Total:** `{len(bot.sessions)}`",
            parse_mode=ParseMode.MARKDOWN
        )
        
    except errors.SessionPasswordNeeded:
        await message.reply(
            f"🔐 **2FA Enabled on `{pending_phone}`!**\n\n"
            f"🔑 **Step 2/3 - Send 2FA Password:**\n"
            f"`yourpassword123`\n\n"
            f"⏰ **Timeout:** 2 minutes\n"
            f"💡 **Example:** `mypassword456`",
            parse_mode=ParseMode.MARKDOWN
        )
        
    except errors.PhoneCodeInvalid:
        await message.reply("❌ **Invalid OTP!**\n📱 Send phone number again.")
        if pending_phone in bot.waiting_2fa:
            del bot.waiting_2fa[pending_phone]
            
    except Exception as e:
        await message.reply(f"❌ **Error:** `{str(e)[:100]}`\nTry again!")
        if pending_phone in bot.waiting_2fa:
            del bot.waiting_2fa[pending_phone]

@bot.app.on_message(filters.private & filters.text & ~filters.regex(r'^\d{5,6}$') & ~filters.regex(r'^\+[1-9]\d{1,14}$') & ~filters.command("start"))
async def password_handler(client: Client, message: Message):
    password = message.text.strip()
    user_id = message.from_user.id
    
    # Find pending 2FA
    pending_phone = None
    for phone, waiting_user in list(bot.waiting_2fa.items()):
        if waiting_user == user_id:
            pending_phone = phone
            break
    
    if not pending_phone:
        return  # Ignore non-2FA messages
    
    del bot.waiting_2fa[pending_phone]
    
    session_name = None
    for name, data in bot.pending_sessions.items():
        if data.get('phone') == pending_phone:
            session_name = data['session_name']
            break
    
    if not session_name:
        return await message.reply("❌ **Session expired!** Send phone again.")
    
    session_path = f"{SESSION_DIR}/{session_name}"
    
    try:
        await message.reply(f"🔓 **Unlocking 2FA** `{password[:3]}***` for `{pending_phone}`...")
        
        # Create client for 2FA
        temp_client = Client(session_path, api_id=API_ID, api_hash=API_HASH, phone_number=pending_phone)
        await temp_client.connect()
        
        # Send code again for fresh hash
        sent_code = await temp_client.send_code(pending_phone)
        
        # Sign in with dummy code + password
        await temp_client.sign_in(
            phone=pending_phone,
            phone_code_hash=sent_code.phone_code_hash,
            phone_code="00000",  # Triggers password prompt
            password=password
        )
        
        # Success!
        me = await temp_client.get_me()
        is_premium = getattr(me, 'is_premium', False)
        
        bot.sessions[session_name] = {
            'phone': pending_phone,
            'user_id': me.id,
            'username': getattr(me, 'username', None) or '',
            'first_name': getattr(me, 'first_name', '') or '',
            'is_premium': is_premium,
            'path': session_path,
            'active': True,
            'created': int(time.time())
        }
        
        await bot.save_sessions()
        await temp_client.disconnect()
        
        status = "💎 PREMIUM" if is_premium else "📱 Normal"
        await message.reply(
            f"✅ **2FA Session Created!** 🎉\n\n"
            f"📱 `{pending_phone}`\n"
            f"👤 `{me.first_name}`\n"
            f"🆔 `{me.id}`\n"
            f"{status}\n"
            f"🔐 **Password:** `{password[:3]}***`\n\n"
            f"📊 **Total:** `{len(bot.sessions)}`",
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        await message.reply(f"❌ **2FA Failed:** `{str(e)[:100]}`\n🔐 Try correct password!")
        bot.waiting_2fa[pending_phone] = user_id  # Retry

# ═══════════════════════════════════════════════════════════════════════════════
# 🚀 START BOT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Edit CONFIG above 👆
    asyncio.run(bot.start())
