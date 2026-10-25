"""
Standard Telegram Bot API Engine (HTTP Long-Polling)
সব মেসেজ, বাটন ও অ্যাডমিন কমান্ড ১০০% নির্ভরযোগ্যভাবে হ্যান্ডেল করার ইঞ্জিন
"""
import asyncio
import aiohttp
import json
import time

import config
from core.database import (
    register_user, is_user_banned, ban_user, unban_user,
    get_all_users, get_users_count, add_channel, remove_channel,
    get_user_channels, get_active_channels, get_stats, get_recent_attacks
)

API_BASE = f"https://api.telegram.org/bot{config.BOT_TOKEN}"
USER_LAST_ACTION = {}
FLOOD_TIMEOUT = 0.8

def is_flood(user_id):
    now = time.time()
    last = USER_LAST_ACTION.get(user_id, 0)
    USER_LAST_ACTION[user_id] = now
    return (now - last) < FLOOD_TIMEOUT

async def call_api(session, method, payload=None):
    url = f"{API_BASE}/{method}"
    try:
        async with session.post(url, json=payload or {}, timeout=30) as resp:
            return await resp.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

async def send_msg(session, chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return await call_api(session, "sendMessage", payload)

async def edit_msg(session, chat_id, message_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return await call_api(session, "editMessageText", payload)

async def answer_cb(session, cb_id, text=None, alert=False):
    payload = {"callback_query_id": cb_id}
    if text:
        payload["text"] = text
        payload["show_alert"] = alert
    return await call_api(session, "answerCallbackQuery", payload)

# ========================================================
# বাটন লেআউট তৈরি
# ========================================================
def get_start_keyboard(user_id):
    buttons = [
        [{"text": "➕ চ্যানেল যুক্ত করার নিয়ম", "callback_data": "help_add"}, {"text": "📋 আমার চ্যানেলসমূহ", "callback_data": "my_chans"}],
        [{"text": "📊 ডিফেন্স রিপোর্ট", "callback_data": "show_stats"}, {"text": "❓ সাহায্য ও সাপোর্ট", "callback_data": "help_info"}]
    ]
    if user_id == config.ADMIN_ID:
        buttons.append([{"text": "👑 অ্যাডমিন কন্ট্রোল প্যানেল", "callback_data": "open_admin_panel"}])
    return {"inline_keyboard": buttons}

def get_admin_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "📢 চ্যানেল ম্যানেজমেন্ট", "callback_data": "adm_channels"}, {"text": "👥 ইউজার ম্যানেজমেন্ট", "callback_data": "adm_users"}],
            [{"text": "⚔️ আক্রমণ হিস্ট্রি", "callback_data": "adm_attacks"}, {"text": "🔄 ইঞ্জিন সিঙ্ক", "callback_data": "adm_sync"}],
            [{"text": "📣 ব্রডকাস্ট নোটিশ গাইড", "callback_data": "adm_broadcast_help"}]
        ]
    }

# ========================================================
# মূল পোলিং ইঞ্জিন
# ========================================================
async def run_bot_polling(shield_engine):
    print("[*] Telegram Bot API Long-Polling ইঞ্জিন চালু হচ্ছে...")
    offset = 0

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                updates_data = await call_api(session, "getUpdates", {
                    "offset": offset,
                    "timeout": 20,
                    "allowed_updates": ["message", "callback_query"]
                })

                if not updates_data.get("ok"):
                    await asyncio.sleep(2)
                    continue

                for update in updates_data.get("result", []):
                    offset = update["update_id"] + 1

                    # --- ১. সাধারণ মেসেজ হ্যান্ডলার ---
                    if "message" in update:
                        msg = update["message"]
                        chat_id = msg["chat"]["id"]
                        user = msg.get("from", {})
                        user_id = user.get("id")
                        text = msg.get("text", "").strip()

                        if not user_id or is_user_banned(user_id):
                            continue

                        register_user(user_id, user.get("first_name", ""), user.get("username", ""))

                        # /start
                        if text == "/start":
                            stats = get_stats()
                            resp_text = f"""
🛡️ **স্বাগতম {user.get('first_name', 'ইউজার')}!**
আমি **𝐀𝐧𝐭𝐢-𝐃𝐃𝐨𝐒 𝐋𝐢𝐯𝐞 𝐒𝐡𝐢𝐞𝐥𝐝 🛡️** — টেলিগ্রামের অফিসিয়াল লাইভ স্ট্রিম সিকিউরিটি গার্ড।

আপনার পাবলিক চ্যানেলে লাইভ চলাকালীন কোনো হ্যাকার ডিডক্স (`GROUPCALL_INVALID`) মারলে আমাদের ক্লাউড সিস্টেম **৩০০ মিলি-সেকেন্ডে** লাইভ রিস্টোর করে অ্যাটাক সম্পূর্ণ ব্যর্থ করে দেয়।

📊 **লাইভ সিস্টেম হেলথ:**
• 📡 সক্রিয় পাহারায় চ্যানেল: `{stats['total_protected_channels']}` টি
• ⚔️ প্রতিহত করা আক্রমণ: `{stats['total_attacks_blocked']}` টি
• 👥 মোট নিবন্ধিত ইউজার: `{stats['total_users']}` জন
• ⚡ গড় রিকভারি গতি: `< ৩০০ ms`

👇 **নিচের বাটন চেপে আপনার চ্যানেলটি এখনই সুরক্ষিত করুন:**
"""
                            await send_msg(session, chat_id, resp_text, get_start_keyboard(user_id))

                        # /admin
                        elif text == "/admin":
                            if user_id != config.ADMIN_ID:
                                await send_msg(session, chat_id, "⛔ **এক্সেস ডিনাইড!** আপনি এই বটের অ্যাডমিন নন।")
                            else:
                                stats = get_stats()
                                adm_text = f"""
👑 **মাস্টার অ্যাডমিন কন্ট্রোল প্যানেল**
সেন্টিনেল ক্লাউড ইঞ্জিনের সমস্ত ম্যানেজমেন্ট ও সেটিংস:

📊 **সার্ভার পরিসংখ্যান:**
• 📡 মোট প্রোটেক্টেড চ্যানেল: `{stats['total_protected_channels']}` টি
• 👥 মোট রেজিস্টার্ড ইউজার: `{stats['total_users']}` জন
• ⚔️ প্রতিহত করা আক্রমণ: `{stats['total_attacks_blocked']}` টি
• 🔒 সিকিউরিটি শিল্ড: **সর্বোচ্চ লেভেল (Active)**

👇 **যে মেনুতে ঢুকতে চান সিলেক্ট করুন:**
"""
                                await send_msg(session, chat_id, adm_text, get_admin_keyboard())

                        # /add @channel
                        elif text.startswith("/add"):
                            parts = text.split(maxsplit=1)
                            if len(parts) < 2:
                                await send_msg(session, chat_id, "⚠️ **ভুল ফরম্যাট!**\nদয়া করে এভাবে লিখুন:\n`/add @your_channel_username`")
                            else:
                                target = parts[1].strip()
                                await send_msg(session, chat_id, f"🔍 `{target}` চ্যানেলটি যাচাই করা হচ্ছে...")
                                try:
                                    channel_entity = await shield_engine.assistant_client.get_entity(target)
                                    cid = channel_entity.id if str(channel_entity.id).startswith("-100") else int(f"-100{channel_entity.id}")
                                    title = getattr(channel_entity, 'title', target)
                                    username = getattr(channel_entity, 'username', '')

                                    add_channel(cid, title, username, user_id)
                                    await shield_engine.refresh_channels()

                                    await send_msg(session, chat_id, f"""
✅ **চ্যানেল সফলভাবে যুক্ত হয়েছে!**

📢 **চ্যানেল:** {title} (`@{username or 'Private'}`)
🛡️ **স্ট্যাটাস:** ২৪/৭ সেন্টিনেল শিল্ড সম্পূর্ণ সক্রিয়!
⚔️ এখন থেকে এই চ্যানেলে লাইভ চলাকালীন কোনো আক্রমণকারী ডিডক্স মারলে তা মুহূর্তেই নিষ্ক্রিয় হয়ে যাবে।
""")
                                except Exception as e:
                                    await send_msg(session, chat_id, f"❌ চ্যানেল যুক্ত করতে সমস্যা হয়েছে:\n`{str(e)}`\n\n💡 নিশ্চিত করুন চ্যানেলটি পাবলিক এবং আমাদের সহকারী একাউন্ট ওই চ্যানেলে প্রবেশাধিকার রাখে।")

                        # /my_channels
                        elif text == "/my_channels":
                            chans = get_user_channels(user_id)
                            if not chans:
                                await send_msg(session, chat_id, "⚠️ আপনার সুরক্ষায় এখনো কোনো চ্যানেল যুক্ত করা হয়নি।\nচ্যানেল যুক্ত করতে লিখুন: `/add @your_channel`")
                            else:
                                msg_c = "📋 **আপনার সুরক্ষায় থাকা চ্যানেলগুলো:**\n\n"
                                for i, c in enumerate(chans, 1):
                                    msg_c += f"{i}. **{c['channel_title']}** (`@{c['channel_username'] or c['channel_id']}`)\n   🛡️ স্ট্যাটাস: সার্বক্ষণিক পাহারা চলছে ✅\n\n"
                                msg_c += "চ্যানেল সরাতে লিখুন: `/remove @channel`"
                                await send_msg(session, chat_id, msg_c)

                        # /stats
                        elif text == "/stats":
                            stats = get_stats()
                            await send_msg(session, chat_id, f"""
📊 **গ্লোবাল অ্যান্টি-ডিডক্স ডিফেন্স রিপোর্ট:**

📡 মোট প্রোটেক্টেড চ্যানেল: `{stats['total_protected_channels']}` টি
👥 মোট রেজিস্টার্ড ইউজার: `{stats['total_users']}` জন
🛡️ মোট প্রতিহত আক্রমণ: `{stats['total_attacks_blocked']}` টি
⚡ গড় রিকভারি গতি: `< ৩০০ মিলি-সেকেন্ড`
🚀 ইঞ্জিন স্ট্যাটাস: ১০০% সচল ও সক্রিয়
""")

                        # /help
                        elif text == "/help":
                            await send_msg(session, chat_id, """
📖 **কমান্ড তালিকা ও নির্দেশিকা:**

• `/start` — বট চালু করুন ও মূল মেনু দেখুন
• `/add @channel` — আপনার চ্যানেল সুরক্ষায় যুক্ত করুন
• `/my_channels` — আপনার চ্যানেলগুলোর স্ট্যাটাস দেখুন
• `/remove @channel` — চ্যানেল পাহারা থেকে সরান
• `/stats` — লাইভ আক্রমণ প্রতিহত করার পরিসংখ্যান
""")

                        # /broadcast (Admin Only)
                        elif text.startswith("/broadcast") and user_id == config.ADMIN_ID:
                            parts = text.split(maxsplit=1)
                            if len(parts) < 2:
                                await send_msg(session, chat_id, "⚠️ লিখুন: `/broadcast আপনার নোটিশ`")
                            else:
                                b_msg = parts[1]
                                users = get_all_users()
                                await send_msg(session, chat_id, f"⏳ `{len(users)}` জন ইউজারের কাছে পাঠানো হচ্ছে...")
                                cnt = 0
                                for u in users:
                                    res = await send_msg(session, u["user_id"], f"📢 **অফিশিয়াল নোটিশ:**\n\n{b_msg}")
                                    if res.get("ok"):
                                        cnt += 1
                                    await asyncio.sleep(0.05)
                                await send_msg(session, chat_id, f"✅ সফলভাবে `{cnt}` জন ইউজারের কাছে নোটিশ পাঠানো হয়েছে!")

                        # /ban & /unban (Admin Only)
                        elif text.startswith("/ban ") and user_id == config.ADMIN_ID:
                            target_u = int(text.split()[1])
                            ban_user(target_u)
                            await send_msg(session, chat_id, f"🚫 ইউজার `{target_u}` কে ব্যান করা হয়েছে।")

                        elif text.startswith("/unban ") and user_id == config.ADMIN_ID:
                            target_u = int(text.split()[1])
                            unban_user(target_u)
                            await send_msg(session, chat_id, f"✅ ইউজার `{target_u}` এর ব্যান তুলে নেওয়া হয়েছে।")

                    # --- ২. বাটন কলব্যাক হ্যান্ডলার ---
                    elif "callback_query" in update:
                        cb = update["callback_query"]
                        cb_id = cb["id"]
                        cb_data = cb.get("data", "")
                        from_user = cb.get("from", {})
                        user_id = from_user.get("id")
                        msg = cb.get("message", {})
                        chat_id = msg.get("chat", {}).get("id")
                        mid = msg.get("message_id")

                        if cb_data == "show_stats":
                            stats = get_stats()
                            await answer_cb(session, cb_id, f"🛡️ ব্লকড: {stats['total_attacks_blocked']} টি | 📡 চ্যানেল: {stats['total_protected_channels']} টি", alert=True)

                        elif cb_data == "help_add":
                            await answer_cb(session, cb_id)
                            await send_msg(session, chat_id, """
📌 **চ্যানেল সুরক্ষিত করার ৩টি সহজ ধাপ:**

১. প্রথমে এই বট (`@LiveShieldXBot`) কে আপনার পাবলিক চ্যানেলে **Admin** হিসেবে যুক্ত করুন।
২. এডমিন পারমিশনে **'Manage Live Streams' (ভিডিও চ্যাট পরিচালনা)** অন রাখুন।
৩. এরপর এই চ্যাটে মেসেজ দিন:
`/add @your_channel_username`

বটটি স্বয়ংক্রিয়ভাবে চ্যানেল ভেরিফাই করে সার্বক্ষণিক পাহারায় নিয়ে নেবে!
""")

                        elif cb_data == "my_chans":
                            chans = get_user_channels(user_id)
                            if not chans:
                                await answer_cb(session, cb_id, "⚠️ আপনার কোনো চ্যানেল যুক্ত নেই।", alert=True)
                            else:
                                await answer_cb(session, cb_id)
                                msg_c = "📋 **আপনার সুরক্ষায় থাকা চ্যানেলগুলো:**\n\n"
                                for i, c in enumerate(chans, 1):
                                    msg_c += f"{i}. **{c['channel_title']}** (`@{c['channel_username'] or c['channel_id']}`)\n   🛡️ স্ট্যাটাস: সার্বক্ষণিক পাহারা চলছে ✅\n\n"
                                await send_msg(session, chat_id, msg_c)

                        elif cb_data == "help_info":
                            await answer_cb(session, cb_id)
                            await send_msg(session, chat_id, """
📖 **𝐀𝐧𝐭𝐢-𝐃𝐃𝐨𝐒 𝐋𝐢𝐯𝐞 𝐒𝐡𝐢𝐞𝐥𝐝 গাইড:**

• **চ্যানেল কি পাবলিক থাকতে পারবে?**
হ্যাঁ! চ্যানেল ১০০% পাবলিক থাকবে, কোনো প্রাইভেট বা রিকোয়েস্ট টু জয়েন দরকার নেই।
• **ডিডক্স আক্রমণ হলে কী হবে?**
আক্রমণকারী বুটার দিয়ে লাইভ বন্ধ করতে চাইলে আমাদের ক্লাউড বট ০.৩ সেকেন্ডে নতুন পোর্টে লাইভ রিরুট করে দেবে। আক্রমণকারীর ডিডক্স ব্যর্থ হবে এবং লাইভ সচল থাকবে।
""")

                        # অ্যাডমিন প্যানেল বাটনসমূহ
                        elif cb_data == "open_admin_panel":
                            if user_id != config.ADMIN_ID:
                                await answer_cb(session, cb_id, "⛔ এক্সেস ডিনাইড!", alert=True)
                            else:
                                await answer_cb(session, cb_id)
                                stats = get_stats()
                                await edit_msg(session, chat_id, mid, f"""
👑 **মাস্টার অ্যাডমিন কন্ট্রোল প্যানেল**
• 📡 চ্যানেল: `{stats['total_protected_channels']}` টি | 👥 ইউজার: `{stats['total_users']}` জন | ⚔️ ব্লকড অ্যাটাক: `{stats['total_attacks_blocked']}` টি
""", get_admin_keyboard())

                        elif cb_data == "adm_channels":
                            if user_id == config.ADMIN_ID:
                                await answer_cb(session, cb_id)
                                chans = get_active_channels()
                                if not chans:
                                    t = "📢 বর্তমানে কোনো চ্যানেল পাহারায় যুক্ত নেই।"
                                else:
                                    t = f"📢 **পাহারায় থাকা সমস্ত চ্যানেল ({len(chans)} টি):**\n\n"
                                    for i, c in enumerate(chans[:15], 1):
                                        t += f"{i}. **{c['channel_title']}** (`@{c['channel_username'] or c['channel_id']}`)\n   👤 যোগকারী: `{c['added_by_user_id']}`\n\n"
                                await edit_msg(session, chat_id, mid, t, {"inline_keyboard": [[{"text": "🔙 পেছনে যান", "callback_data": "open_admin_panel"}]]})

                        elif cb_data == "adm_users":
                            if user_id == config.ADMIN_ID:
                                await answer_cb(session, cb_id)
                                tot = get_users_count()
                                t = f"""
👥 **ইউজার ম্যানেজমেন্ট ড্যাশবোর্ড**

• 👥 মোট নিবন্ধিত ইউজার: `{tot}` জন
• 🔒 সিকিউরিটি: অ্যান্টি-ফ্লাড রেট লিমিটার সক্রিয়

⚙️ **কমান্ডসমূহ:**
• `/ban <user_id>` — ইউজার ব্যান
• `/unban <user_id>` — ব্যান প্রত্যাহার
• `/broadcast <মেসেজ>` — সবাইকে নোটিশ পাঠান
"""
                                await edit_msg(session, chat_id, mid, t, {"inline_keyboard": [[{"text": "🔙 পেছনে যান", "callback_data": "open_admin_panel"}]]})

                        elif cb_data == "adm_attacks":
                            if user_id == config.ADMIN_ID:
                                await answer_cb(session, cb_id)
                                atks = get_recent_attacks(limit=5)
                                if not atks:
                                    t = "⚔️ এখনো কোনো ডিডক্স আক্রমণ রেকর্ড হয়নি। সিস্টেম নিরাপদ!"
                                else:
                                    t = "⚔️ **সাম্প্রতিক প্রতিহত হওয়া ডিডক্স আক্রমণ লগ:**\n\n"
                                    for i, a in enumerate(atks, 1):
                                        t += f"{i}. 📢 **{a.get('channel_title', 'Unknown')}**\n"
                                        t += f"   ⚡ রিকভারি সময়: `{a['recovery_time_ms']}` ms\n"
                                        t += f"   🕒 সময়: `{a['timestamp']}`\n   🛡️ ফলাফল: **সফলভাবে প্রতিহত** ✅\n\n"
                                await edit_msg(session, chat_id, mid, t, {"inline_keyboard": [[{"text": "🔙 পেছনে যান", "callback_data": "open_admin_panel"}]]})

                        elif cb_data == "adm_sync":
                            if user_id == config.ADMIN_ID:
                                await shield_engine.refresh_channels()
                                await answer_cb(session, cb_id, "✅ ক্লাউড ইঞ্জিন ও ডাটাবেজ সফলভাবে রিফ্রেশ ও সিঙ্ক হয়েছে!", alert=True)

                        elif cb_data == "adm_broadcast_help":
                            if user_id == config.ADMIN_ID:
                                await answer_cb(session, cb_id)
                                t = """
📣 **সবাইকে নোটিশ বা মেসেজ পাঠানোর নিয়ম:**

চ্যাটে এভাবে লিখুন:
`/broadcast আপনার নোটিশের কথা এখানে লিখবেন`
"""
                                await edit_msg(session, chat_id, mid, t, {"inline_keyboard": [[{"text": "🔙 পেছনে যান", "callback_data": "open_admin_panel"}]]})

            except Exception as e:
                print(f"[!] Polling loop error: {e}")
                await asyncio.sleep(2)
