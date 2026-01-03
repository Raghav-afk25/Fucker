import asyncio
import json
import os
import random
import time
import re
import aiofiles
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait, UsernameNotOccupied, PeerIdInvalid
from config import BOT_TOKEN, API_ID, API_HASH, OWNER_ID, SESSION_DIR, SESSIONS_FILE, SUDOS_FILE

app = Client("premium_killer", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

class PremiumKillerBot:
    def __init__(self):
        self.sessions = {}
        self.sudos = set()
        self.active_attacks = {}
        os.makedirs(SESSION_DIR, exist_ok=True)
        self.load_data()
    
    async def load_data(self):
        if os.path.exists(SESSIONS_FILE):
            async with aiofiles.open(SESSIONS_FILE, 'r') as f:
                data = json.loads(await f.read())
                self.sessions = data.get('sessions', {})
        
        if os.path.exists(SUDOS_FILE):
            async with aiofiles.open(SUDOS_FILE, 'r') as f:
                data = json.loads(await f.read())
                self.sudos = set(data.get('sudos', []))
    
    async def save_sessions(self):
        async with aiofiles.open(SESSIONS_FILE, 'w') as f:
            await f.write(json.dumps({'sessions': self.sessions}, indent=2))
    
    async def save_sudos(self):
        async with aiofiles.open(SUDOS_FILE, 'w') as f:
            await f.write(json.dumps({'sudos': list(self.sudos)}, indent=2))

bot = PremiumKillerBot()

def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 Add Session", callback_data="add_session")],
        [InlineKeyboardButton("👤 Username Ban", callback_data="ban_username"),
         InlineKeyboardButton("🆔 ID Ban", callback_data="ban_id")],
        [InlineKeyboardButton("📢 Channel Delete", callback_data="delete_channel"),
         InlineKeyboardButton("👥 Group Delete", callback_data="delete_group")],
        [InlineKeyboardButton("💎 Premium Killer", callback_data="premium_kill"),
         InlineKeyboardButton("📊 Stats", callback_data="stats")]
    ])

# 🔥 ENHANCED NOTIFICATION SYSTEM
async def send_notification(chat_id, title, status, details=""):
    emoji = {"start": "🚀", "progress": "⚡", "success": "✅", "premium": "💎", "frozen": "❄️", "banned": "🚫", "deleted": "💥"}
    msg = f"{emoji.get(status, 'ℹ️')} **{title}**\n\n{details}\n\n"
    await app.send_message(chat_id, msg, parse_mode=ParseMode.MARKDOWN)

# 📱 SESSION CREATOR
async def create_session(phone: str, chat_id: int) -> bool:
    session_name = f"session_{int(time.time())}"
    session_path = f"{SESSION_DIR}/{session_name}"
    
    await send_notification(chat_id, f"Session: `{phone}`", "start")
    
    try:
        client = Client(session_path, api_id=API_ID, api_hash=API_HASH, phone_number=phone)
        await client.start()
        me = await client.get_me()
        
        is_premium = getattr(me, 'is_premium', False)
        premium_status = "💎 PREMIUM" if is_premium else "📱 Normal"
        
        bot.sessions[session_name] = {
            'phone': phone, 'user_id': me.id, 'username': me.username or '',
            'first_name': me.first_name, 'is_premium': is_premium,
            'path': session_path, 'active': True
        }
        
        await bot.save_sessions()
        await client.stop()
        
        await send_notification(chat_id, f"✅ `{phone}` Added", "success",
                               f"{premium_status}\nTotal: `{len(bot.sessions)}`")
        return True
    except Exception as e:
        await send_notification(chat_id, f"❌ `{phone}` Failed", "progress", f"Error: {str(e)}")
        return False

# 💥 ENHANCED MASS ATTACK (5-10 sessions = 200-500+ reports!)
async def mass_attack(target_id: int, target_type: str, chat_id: int, session_limit=250):
    attack_id = f"{chat_id}_{int(time.time())}"
    bot.active_attacks[attack_id] = {'progress': 0, 'total': 0}
    
    await send_notification(chat_id, f"🎯 {target_type.upper()} Attack", "start", 
                           f"Target ID: `{target_id}`\n⚡ **Enhanced Multi-Report**")
    
    success_reports = 0
    sessions = list(bot.sessions.values())[:session_limit]
    bot.active_attacks[attack_id]['total'] = len(sessions)
    
    report_variants = [
        ('Violence', 'Violence and dangerous organisations'), ('Child Abuse', 'Child abuse'),
        ('Terrorism', 'Terrorism'), ('Pornography', 'Pornography'), ('Copyright', 'Copyright infringement'),
        ('Spam', 'Spam'), ('Scam', 'Scam'), ('Fake', 'Fake account'), ('Impersonation', 'Impersonation'),
        ('Harassment', 'Harassment'), ('Fake', 'Fake messages'), ('Violence', 'Violent messages'),
        ('Spam', 'Spam messages'), ('Pornography', 'Pornographic content'), ('Copyright', 'Copyright violation'),
    ]
    
    for i, session_info in enumerate(sessions):
        session_path = session_info['path']
        try:
            client = Client(session_path, api_id=API_ID, api_hash=API_HASH)
            await client.start()
            session_reports = 0
            
            # PHASE 1: Peer/Chat Reports
            for reason, _ in report_variants[:10]:
                try:
                    if target_type == 'user':
                        await client.report_peer(target_id, reason)
                    else:
                        await client.report_chat(target_id, reason)
                    session_reports += 1
                    success_reports += 1
                    await asyncio.sleep(random.uniform(0.1, 0.3))
                except FloodWait as e:
                    await asyncio.sleep(e.value + 1)
                except:
                    pass
            
            # PHASE 2: Message Reports
            try:
                async for msg in client.get_chat_history(target_id, limit=20):
                    for reason in ['Violence', 'Spam', 'Fake', 'Pornography']:
                        try:
                            await client.report_message(target_id, msg.id, reason)
                            session_reports += 1
                            success_reports += 1
                            await asyncio.sleep(0.05)
                        except:
                            break
            except:
                pass
            
            await client.stop()
            bot.active_attacks[attack_id]['progress'] = i + 1
            
            progress_pct = f"{(i+1)*100//len(sessions)}%"
            await send_notification(chat_id, f"⚡ Session {i+1}", "progress", 
                                  f"`{session_reports}` reports | `{progress_pct}`")
            
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
        except:
            continue
    
    impact_score = "💀 **CRITICAL**" if success_reports >= 100 else "❄️ **HIGH**" if success_reports >= 50 else "🔥 **MEDIUM**"
    status_msg = f"{impact_score}\n⚡ `{success_reports}` TOTAL reports\n📱 `{len(sessions)}` sessions\n⏱️ `{time.strftime('%H:%M:%S')}`"
    
    await send_notification(chat_id, "🎯 **ATTACK COMPLETED!**", "success", status_msg)
    del bot.active_attacks[attack_id]

# 🎯 HANDLERS
@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    user_id = message.from_user.id
    if user_id not in (OWNER_ID, *bot.sudos):
        await message.reply("🔒 **@Smaugxd Exclusive Bot**")
        return
    
    welcome = """👑 **Premium Killer Bot**
💎 **DEVELOPER: @Smaugxd**

⚡ LIVE notifications (5-10 sessions = 200-500+ reports!)
✅ Username/ID ban  
📢 Channel deletion
❄️ Premium freeze

**Status**: Online"""
    
    await message.reply(welcome, reply_markup=get_main_keyboard(), parse_mode=ParseMode.MARKDOWN)

@app.on_message(filters.command("addsudo") & filters.private)
async def add_sudo(client, message):
    if message.from_user.id != OWNER_ID: return
    try:
        sudo_id = int(message.text.split()[1])
        bot.sudos.add(sudo_id)
        await bot.save_sudos()
        await message.reply(f"✅ **Sudo Added**: `{sudo_id}`")
    except:
        await message.reply("❌ `/addsudo 123456789`")

@app.on_callback_query()
async def callbacks(client, callback):
    user_id = callback.from_user.id
    if user_id not in (OWNER_ID, *bot.sudos):
        await callback.answer("🔒 Owner only!", show_alert=True)
        return
    
    data = callback.data
    if data == "add_session":
        await callback.message.edit_text(f"📱 **Add Session**\n\nSend phone:\n`+1234567890`\n\n`{len(bot.sessions)}` active", parse_mode=ParseMode.MARKDOWN)
    elif data == "ban_username":
        await callback.message.edit_text("👤 **Username Attack**\n\nSend `@username`:")
    elif data == "ban_id":
        await callback.message.edit_text("🆔 **ID Attack**\n\nSend `user_id`:")
    elif data == "delete_channel":
        await callback.message.edit_text("📢 **Channel Delete**\n\nSend `@channel` or `ID`:")
    elif data == "delete_group":
        await callback.message.edit_text("👥 **Group Delete**\n\nSend group ID:")
    elif data == "premium_kill":
        await callback.message.edit_text("💎 **Premium Killer**\n\nSend target username/ID:")
    elif data == "stats":
        premium_count = sum(1 for s in bot.sessions.values() if s.get('is_premium'))
        await callback.message.edit_text(f"📊 **Stats**\n💎 Premium: `{premium_count}`\n📱 Total: `{len(bot.sessions)}`\n⚡ Attacks: `{len(bot.active_attacks)}`", parse_mode=ParseMode.MARKDOWN)
    
    await callback.answer()

@app.on_message(filters.private & filters.regex(r'^\+[1-9]\d{1,14}$'))
async def phone_handler(client, message):
    await create_session(message.text.strip(), message.chat.id)

@app.on_message(filters.private & filters.text & ~filters.regex(r'^\+[1-9]\d{1,14}$'))
async def target_handler(client, message):
    user_id = message.from_user.id
    if user_id not in (OWNER_ID, *bot.sudos): return
    
    target = message.text.strip()
    session_count = min(len(bot.sessions), 250)
    
    await message.reply(f"🚀 **Attack Launched!**\n🎯 `{target}`\n📱 `{session_count}` sessions\n⚡ **50+ reports/session**\n📱 Check notifications!")
    
    # Parse target
    try:
        if target.startswith('@'):
            entity = await app.resolve_peer(target)
            target_id = entity.user.id if hasattr(entity, 'user') else entity.chat.id
            target_type = 'user' if hasattr(entity, 'user') else 'channel'
        else:
            target_id = int(target)
            target_type = 'user'
        
        asyncio.create_task(mass_attack(target_id, target_type, message.chat.id, session_count))
    except Exception as e:
        await message.reply(f"❌ Error: `{str(e)[:50]}`")

if __name__ == "__main__":
    print("🚀 Premium Killer Bot Started | @Smaugxd")
    app.run()
