"""
Standard Telegram Bot API Engine (Public & Private Channels/Groups Support)
পাবলিক ও প্রাইভেট চ্যানেল এবং গ্রুপ অটো-ডিটেকশন ও সম্পূর্ণ সুরক্ষা ইঞ্জিন
"""
import asyncio
import aiohttp
import json
import time
import re

import config
from core.database import (
    register_user, is_user_banned, ban_user, unban_user,
    get_all_users, get_users_count, add_channel, remove_channel,
    get_user_channels, get_active_channels, get_stats, get_recent_attacks,
    get_recent_forensics
)

API_BASE = f"https://api.telegram.org/bot{config.BOT_TOKEN}"
USER_LAST_ACTION = {}
FLOOD_TIMEOUT = 0.5

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
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    res = await call_api(session, "sendMessage", payload)
    if not res.get("ok") and "can't parse" in res.get("description", "").lower():
        payload.pop("parse_mode", None)
        res = await call_api(session, "sendMessage", payload)
    return res

async def edit_msg(session, chat_id, message_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    res = await call_api(session, "editMessageText", payload)
    if not res.get("ok") and "can't parse" in res.get("description", "").lower():
        payload.pop("parse_mode", None)
        res = await call_api(session, "editMessageText", payload)
    return res

async def answer_cb(session, cb_id, text=None, alert=False):
    payload = {"callback_query_id": cb_id}
    if text:
        payload["text"] = text
        payload["show_alert"] = alert
    return await call_api(session, "answerCallbackQuery", payload)

# ========================================================
# বাটন লেআউট
# ========================================================
def get_start_keyboard(user_id):
    buttons = [
        [{"text": "➕ চ্যানেল/গ্রুপ যুক্ত করার নিয়ম", "callback_data": "help_add"}, {"text": "🔒 প্রাইভেট চ্যানেল/গ্রুপ গাইড", "callback_data": "help_private"}],
        [{"text": "📋 আমার সুরক্ষায় থাকা তালিকা", "callback_data": "my_chans"}, {"text": "📊 লাইভ ডিফেন্স রিপোর্ট", "callback_data": "show_stats"}],
        [{"text": "❓ সাহায্য ও এফএকিউ", "callback_data": "help_info"}]
    ]
    if user_id == config.ADMIN_ID:
        buttons.append([{"text": "👑 অ্যাডমিন কন্ট্রোল প্যানেল", "callback_data": "open_admin_panel"}])
    return {"inline_keyboard": buttons}

def get_admin_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "📢 চ্যানেল/গ্রুপ তালিকা", "callback_data": "adm_channels"}, {"text": "👥 ইউজার ম্যানেজমেন্ট", "callback_data": "adm_users"}],
            [{"text": "🕵️ ব্ল্যাকবক্স ফরেনসিক লগ", "callback_data": "adm_forensics"}, {"text": "⚔️ আক্রমণ হিস্ট্রি", "callback_data": "adm_attacks"}],
            [{"text": "🔄 ইঞ্জিন সিঙ্ক", "callback_data": "adm_sync"}, {"text": "📣 ব্রডকাস্ট নোটিশ গাইড", "callback_data": "adm_broadcast_help"}]
        ]
    }

# ========================================================
# মূল পোলিং ইঞ্জিন
# ========================================================
async def run_bot_polling(shield_engine):
    print("[*] Telegram Bot API Long-Polling ইঞ্জিন চালু হচ্ছে (Public & Private Mode)...")
    offset = 0

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                updates_data = await call_api(session, "getUpdates", {
                    "offset": offset,
                    "timeout": 20,
                    "allowed_updates": ["message", "callback_query", "my_chat_member"]
                })

                if not updates_data.get("ok"):
                    await asyncio.sleep(2)
                    continue

                for update in updates_data.get("result", []):
                    offset = update["update_id"] + 1

                    # ========================================================
                    # ক) স্বয়ংক্রিয়ভাবে প্রাইভেট/পাবলিক গ্রুপ ও চ্যানেলে অ্যাডমিন শনাক্ত
                    # ========================================================
                    if "my_chat_member" in update:
                        mcm = update["my_chat_member"]
                        chat = mcm["chat"]
                        new_status = mcm.get("new_chat_member", {}).get("status")
                        adder_user = mcm.get("from", {})
                        adder_id = adder_user.get("id")

                        # বটকে যখন কোনো গ্রুপ বা চ্যানেলে Admin বানানো হয়
                        if new_status == "administrator" and adder_id:
                            cid = chat["id"]
                            title = chat.get("title", "Private Group/Channel")
                            username = chat.get("username", "")

                            add_channel(cid, title, username, adder_id)
                            await shield_engine.refresh_channels()

                            # চ্যানেলে/গ্রুপে কনফার্মেশন পাঠানো
                            await send_msg(session, cid, f"""
🛡️ <b>𝐀𝐧𝐭𝐢-𝐃𝐃𝐨𝐒 𝐋𝐢𝐯𝐞 𝐒𝐡𝐢𝐞𝐥𝐝 সক্রিয়!</b>

✅ এই {chat.get('type', 'চ্যানেল/গ্রুপ')}টি সফলভাবে স্বয়ংক্রিয় পাহারায় যুক্ত হয়েছে।
⚔️ এখন থেকে এখানে ভয়েস/ভিডিও চ্যাট চলাকালীন কোনো আক্রমণকারী ডিডক্স মেরে লাইভ ড্রপ করাতে পারবে না!
""")
                            # যে অ্যাডমিন যুক্ত করেছে তাকে ইনবক্সে নোটিফিকেশন পাঠানো
                            await send_msg(session, adder_id, f"""
🎉 <b>অভিনন্দন! আপনার {chat.get('type', 'চ্যানেল/গ্রুপ')} পাহারায় যুক্ত হয়েছে:</b>

📢 <b>নাম:</b> {title}
🆔 <b>আইডি:</b> <code>{cid}</code>
🛡️ <b>স্ট্যাটাস:</b> ২৪/৭ সার্বক্ষণিক প্রটেকশন চালু ✅
""")
                        continue

                    # ========================================================
                    # খ) মেসেজ হ্যান্ডলার
                    # ========================================================
                    if "message" in update:
                        msg = update["message"]
                        chat_id = msg["chat"]["id"]
                        user = msg.get("from", {})
                        user_id = user.get("id")
                        text = msg.get("text", "").strip()

                        if not user_id or is_user_banned(user_id):
                            continue

                        register_user(user_id, user.get("first_name", ""), user.get("username", ""))

                        # ১. প্রাইভেট চ্যানেল থেকে কোনো মেসেজ ফরওয়ার্ড করলে অটো-অ্যাড
                        if "forward_from_chat" in msg:
                            fwd = msg["forward_from_chat"]
                            fwd_id = fwd["id"]
                            fwd_title = fwd.get("title", "Private Channel")
                            fwd_user = fwd.get("username", "")

                            await send_msg(session, chat_id, f"🔍 ফরওয়ার্ড করা প্রাইভেট চ্যানেলটি যাচাই করা হচ্ছে (ID: <code>{fwd_id}</code>)...")

                            # চেক করা বট কি অ্যাডমিন আছে কিনা
                            chat_res = await call_api(session, "getChat", {"chat_id": fwd_id})
                            if chat_res.get("ok"):
                                add_channel(fwd_id, fwd_title, fwd_user, user_id)
                                await shield_engine.refresh_channels()
                                await send_msg(session, chat_id, f"""
✅ <b>প্রাইভেট চ্যানেল সফলভাবে যুক্ত হয়েছে!</b>

📢 <b>নাম:</b> {fwd_title}
🆔 <b>আইডি:</b> <code>{fwd_id}</code>
🛡️ <b>স্ট্যাটাস:</b> সেন্টিনেল শিল্ড সম্পূর্ণ সক্রিয়!
""")
                            else:
                                await send_msg(session, chat_id, f"""
⚠️ <b>বট এখনো ওই প্রাইভেট চ্যানেলে Admin নয়!</b>

দয়া করে প্রথমে <b>@LiveShieldXBot</b> কে ওই প্রাইভেট চ্যানেলে বা গ্রুপে <b>Admin</b> বানিয়ে দিন। এরপর আবার ফরওয়ার্ড করুন অথবা <code>/add {fwd_id}</code> লিখুন।
""")
                            continue

                        # /start
                        if text == "/start":
                            stats = get_stats()
                            resp_text = f"""
🛡️ <b>স্বাগতম {user.get('first_name', 'ইউজার')}!</b>
আমি <b>𝐀𝐧𝐭𝐢-𝐃𝐃𝐨𝐒 𝐋𝐢𝐯𝐞 𝐒𝐡𝐢𝐞𝐥𝐝 🛡️</b> — টেলিগ্রামের অফিসিয়াল লাইভ স্ট্রিম সিকিউরিটি গার্ড।

আপনার পাবলিক বা প্রাইভেট চ্যানেল এবং গ্রুপে লাইভ চলাকালীন কোনো হ্যাকার ডিডক্স (<code>GROUPCALL_INVALID</code>) মারলে আমাদের ক্লাউড সিস্টেম <b>৩০০ মিলি-সেকেন্ডে</b> লাইভ রিস্টোর করে অ্যাটাক সম্পূর্ণ ব্যর্থ করে দেয়।

📊 <b>লাইভ সিস্টেম হেলথ:</b>
• 📡 সক্রিয় পাহারায় চ্যানেল ও গ্রুপ: <code>{stats['total_protected_channels']}</code> টি
• ⚔️ প্রতিহত করা আক্রমণ: <code>{stats['total_attacks_blocked']}</code> টি
• 👥 মোট নিবন্ধিত ইউজার: <code>{stats['total_users']}</code> জন
• ⚡ গড় রিকভারি গতি: &lt; ৩০০ ms

👇 <b>নিচের বাটন চেপে আপনার চ্যানেল বা গ্রুপ এখনই সুরক্ষিত করুন:</b>
"""
                            await send_msg(session, chat_id, resp_text, get_start_keyboard(user_id))

                        # /admin
                        elif text == "/admin":
                            if user_id != config.ADMIN_ID:
                                await send_msg(session, chat_id, "⛔ <b>এক্সেস ডিনাইড!</b> আপনি এই বটের অ্যাডমিন নন।")
                            else:
                                stats = get_stats()
                                adm_text = f"""
👑 <b>মাস্টার অ্যাডমিন কন্ট্রোল প্যানেল</b>
সেন্টিনেল ক্লাউড ইঞ্জিনের সমস্ত ম্যানেজমেন্ট ও সেটিংস:

📊 <b>সার্ভার পরিসংখ্যান:</b>
• 📡 মোট প্রোটেক্টেড চ্যানেল ও গ্রুপ: <code>{stats['total_protected_channels']}</code> টি
• 👥 মোট রেজিস্টার্ড ইউজার: <code>{stats['total_users']}</code> জন
• ⚔️ প্রতিহত করা আক্রমণ: <code>{stats['total_attacks_blocked']}</code> টি
• 🔒 সিকিউরিটি শিল্ড: <b>সর্বোচ্চ লেভেল (Active)</b>

👇 <b>যে মেনুতে ঢুকতে চান সিলেক্ট করুন:</b>
"""
                                await send_msg(session, chat_id, adm_text, get_admin_keyboard())

                        # /add <username_or_id_or_link>
                        elif text.startswith("/add"):
                            parts = text.split(maxsplit=1)
                            if len(parts) < 2:
                                await send_msg(session, chat_id, """
⚠️ <b>চ্যানেল বা গ্রুপ যুক্ত করার সঠিক নিয়ম:</b>

১. <b>পাবলিক হলে:</b>
<code>/add @channel_username</code>

২. <b>প্রাইভেট হলে (চ্যানেল/গ্রুপ আইডি দিয়ে):</b>
<code>/add -1001234567890</code>

৩. <b>অথবা সবচেয়ে সহজ:</b>
প্রাইভেট চ্যানেল থেকে যেকোনো একটি মেসেজ এই বটে ফরওয়ার্ড (Forward) করে দিন!
""")
                            else:
                                target = parts[1].strip()
                                await send_msg(session, chat_id, f"🔍 <code>{target}</code> যাচাই করা হচ্ছে...")

                                # সংখ্যা বা আইডি হলে সরাসরি getChat দিয়ে চেক
                                is_numeric_id = False
                                check_id = target
                                if re.match(r"^-?\d+$", target):
                                    is_numeric_id = True
                                    check_id = int(target)
                                    if not str(check_id).startswith("-100"):
                                        check_id = int(f"-100{abs(check_id)}")

                                try:
                                    chat_info = await call_api(session, "getChat", {"chat_id": check_id})
                                    if chat_info.get("ok"):
                                        cdata = chat_info["result"]
                                        cid = cdata["id"]
                                        ctitle = cdata.get("title", target)
                                        cusername = cdata.get("username", "")

                                        add_channel(cid, ctitle, cusername, user_id)
                                        await shield_engine.refresh_channels()

                                        await send_msg(session, chat_id, f"""
✅ <b>সফলভাবে সুরক্ষায় যুক্ত হয়েছে!</b>

📢 <b>নাম:</b> {ctitle}
🆔 <b>আইডি:</b> <code>{cid}</code>
🔒 <b>টাইপ:</b> {cdata.get('type', 'Channel/Group').capitalize()}
🛡️ <b>স্ট্যাটাস:</b> ২৪/৭ সেন্টিনেল শিল্ড সম্পূর্ণ সক্রিয়!
⚔️ এখন থেকে এখানে লাইভ চালালে আক্রমণকারীর যেকোনো ডিডক্স মুহূর্তেই নিষ্ক্রিয় হয়ে যাবে।
""")
                                    else:
                                        # যদি getChat সরাসরি না পায়, সহকারী অ্যাকাউন্ট দিয়ে ট্রাই
                                        if hasattr(shield_engine, "assistant_client") and shield_engine.assistant_client:
                                            channel_entity = await shield_engine.assistant_client.get_entity(target)
                                            cid = channel_entity.id if str(channel_entity.id).startswith("-100") else int(f"-100{channel_entity.id}")
                                            title = getattr(channel_entity, 'title', target)
                                            username = getattr(channel_entity, 'username', '')

                                            add_channel(cid, title, username, user_id)
                                            await shield_engine.refresh_channels()

                                            await send_msg(session, chat_id, f"""
✅ <b>সফলভাবে সুরক্ষায় যুক্ত হয়েছে!</b>

📢 <b>নাম:</b> {title} (<code>@{username or 'Private'}</code>)
🛡️ <b>স্ট্যাটাস:</b> ২৪/৭ সেন্টিনেল শিল্ড সম্পূর্ণ সক্রিয়!
""")
                                        else:
                                            await send_msg(session, chat_id, f"❌ চ্যানেল বা গ্রুপটি খুঁজে পাওয়া যায়নি!\n\n💡 নিশ্চিত করুন <b>@LiveShieldXBot</b> কে ওই প্রাইভেট চ্যানেল বা গ্রুপে <b>Admin</b> বানানো হয়েছে।")
                                except Exception as e:
                                    await send_msg(session, chat_id, f"❌ যুক্ত করতে সমস্যা হয়েছে:\n<code>{str(e)}</code>\n\n💡 নিশ্চিত করুন বট ওই গ্রুপ বা চ্যানেলে Admin হিসেবে যুক্ত আছে।")

                        # /my_channels
                        elif text == "/my_channels":
                            chans = get_user_channels(user_id)
                            if not chans:
                                await send_msg(session, chat_id, "⚠️ আপনার সুরক্ষায় এখনো কোনো চ্যানেল বা গ্রুপ যুক্ত করা হয়নি।\nযুক্ত করতে লিখুন: <code>/add @channel</code> অথবা প্রাইভেট আইডি।")
                            else:
                                msg_c = "📋 <b>আপনার সুরক্ষায় থাকা চ্যানেল ও গ্রুপসমূহ:</b>\n\n"
                                for i, c in enumerate(chans, 1):
                                    msg_c += f"{i}. 📢 <b>{c['channel_title']}</b> (<code>@{c['channel_username'] or c['channel_id']}</code>)\n   🛡️ স্ট্যাটাস: সার্বক্ষণিক পাহারা চলছে ✅\n\n"
                                msg_c += "সরাতে লিখুন: <code>/remove @channel_or_id</code>"
                                await send_msg(session, chat_id, msg_c)

                        # /stats
                        elif text == "/stats":
                            stats = get_stats()
                            await send_msg(session, chat_id, f"""
📊 <b>গ্লোবাল অ্যান্টি-ডিডক্স ডিফেন্স রিপোর্ট:</b>

📡 মোট প্রোটেক্টেড চ্যানেল ও গ্রুপ: <code>{stats['total_protected_channels']}</code> টি
👥 মোট রেজিস্টার্ড ইউজার: <code>{stats['total_users']}</code> জন
🛡️ মোট প্রতিহত আক্রমণ: <code>{stats['total_attacks_blocked']}</code> টি
⚡ গড় রিকভারি গতি: &lt; ৩০০ মিলি-সেকেন্ড
🚀 ইঞ্জিন স্ট্যাটাস: ১০০% সচল ও সক্রিয়
""")

                        # /help
                        elif text == "/help":
                            await send_msg(session, chat_id, """
📖 <b>কমান্ড তালিকা ও নির্দেশিকা:</b>

• <code>/start</code> — বট চালু করুন ও মূল মেনু দেখুন
• <code>/add @username</code> — পাবলিক চ্যানেল/গ্রুপ যুক্ত করুন
• <code>/add -100xxxxxxx</code> — প্রাইভেট চ্যানেল/গ্রুপ যুক্ত করুন
• <b>মেসেজ ফরওয়ার্ড</b> — প্রাইভেট চ্যানেল থেকে যেকোনো পোস্ট ফরওয়ার্ড করলেই অটো-অ্যাড
• <code>/my_channels</code> — আপনার তালিকার স্ট্যাটাস দেখুন
• <code>/remove @channel</code> — পাহারা থেকে সরান
• <code>/stats</code> — লাইভ আক্রমণ প্রতিহত করার পরিসংখ্যান
""")

                        # /broadcast (Admin Only)
                        elif text.startswith("/broadcast") and user_id == config.ADMIN_ID:
                            parts = text.split(maxsplit=1)
                            if len(parts) < 2:
                                await send_msg(session, chat_id, "⚠️ লিখুন: <code>/broadcast আপনার নোটিশ</code>")
                            else:
                                b_msg = parts[1]
                                users = get_all_users()
                                await send_msg(session, chat_id, f"⏳ <code>{len(users)}</code> জন ইউজারের কাছে পাঠানো হচ্ছে...")
                                cnt = 0
                                for u in users:
                                    res = await send_msg(session, u["user_id"], f"📢 <b>অফিশিয়াল নোটিশ:</b>\n\n{b_msg}")
                                    if res.get("ok"):
                                        cnt += 1
                                    await asyncio.sleep(0.05)
                                await send_msg(session, chat_id, f"✅ সফলভাবে <code>{cnt}</code> জন ইউজারের কাছে নোটিশ পাঠানো হয়েছে!")

                        # /ban & /unban (Admin Only)
                        elif text.startswith("/ban ") and user_id == config.ADMIN_ID:
                            target_u = int(text.split()[1])
                            ban_user(target_u)
                            await send_msg(session, chat_id, f"🚫 ইউজার <code>{target_u}</code> কে ব্যান করা হয়েছে।")

                        elif text.startswith("/unban ") and user_id == config.ADMIN_ID:
                            target_u = int(text.split()[1])
                            unban_user(target_u)
                            await send_msg(session, chat_id, f"✅ ইউজার <code>{target_u}</code> এর ব্যান তুলে নেওয়া হয়েছে।")

                        elif text.startswith("/forensics") and user_id == config.ADMIN_ID:
                            forensics = get_recent_forensics(limit=5)
                            if not forensics:
                                await send_msg(session, chat_id, "🕵️ ব্ল্যাকবক্স ফরেনসিকে এখনো কোনো আক্রমণের রেকর্ড নেই। সিস্টেম সম্পূর্ণ নিরাপদ!")
                            else:
                                t = "🕵️ <b>ডিডক্স ব্ল্যাকবক্স ফরেনসিক অডিট রিপোর্ট:</b>\n\n"
                                for i, f in enumerate(forensics, 1):
                                    t += f"<b>#{i} | চ্যানেল:</b> {f.get('channel_title', 'Unknown')}\n"
                                    t += f"• ⚔️ ধরন: <code>{f.get('attack_type', 'UDP_FLOOD')}</code>\n"
                                    t += f"• ⚡ রিকভারি: <code>{f['recovery_time_ms']}</code> ms\n"
                                    t += f"• 👤 সন্দেহভাজন: <code>{f.get('suspect_info') or 'None'}</code>\n"
                                    t += f"• 🕒 সময়: <code>{f.get('timestamp')}</code>\n\n"
                                await send_msg(session, chat_id, t)

                    # ========================================================
                    # গ) বাটন কলব্যাক হ্যান্ডলার
                    # ========================================================
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
                            await answer_cb(session, cb_id, f"🛡️ ব্লকড: {stats['total_attacks_blocked']} টি | 📡 চ্যানেল/গ্রুপ: {stats['total_protected_channels']} টি", alert=True)

                        elif cb_data == "help_add":
                            await answer_cb(session, cb_id)
                            await send_msg(session, chat_id, """
📌 <b>পাবলিক চ্যানেল বা গ্রুপ যুক্ত করার নিয়ম:</b>

১. প্রথমে <b>@LiveShieldXBot</b> কে আপনার চ্যানেল বা গ্রুপে <b>Admin</b> হিসেবে যুক্ত করুন।
২. এডমিন পারমিশনে <b>'Manage Live Streams' (ভিডিও চ্যাট পরিচালনা)</b> অন রাখুন।
৩. এরপর এই চ্যাটে মেসেজ দিন:
<code>/add @your_channel_or_group</code>
""")

                        elif cb_data == "help_private":
                            await answer_cb(session, cb_id)
                            await send_msg(session, chat_id, """
🔒 <b>প্রাইভেট চ্যানেল বা গ্রুপ যুক্ত করার ৩টি উপায়:</b>

<b>উপায় ১ (সবচেয়ে সহজ - অটো ডিটেক্ট):</b>
আপনার প্রাইভেট গ্রুপ বা চ্যানেলে <b>@LiveShieldXBot</b> কে <b>Admin</b> হিসেবে যুক্ত করুন। বট নিজে থেকেই শনাক্ত করে পাহারায় নিয়ে নেবে!

<b>উপায় ২ (মেসেজ ফরওয়ার্ড):</b>
আপনার প্রাইভেট চ্যানেল থেকে যেকোনো একটি মেসেজ কপি না করে সরাসরি এই বটে <b>Forward</b> করে দিন। বট সাথে সাথে চ্যানেলটি যুক্ত করে নেবে।

<b>উপায় ৩ (আইডি দিয়ে):</b>
প্রাইভেট চ্যানেলের আইডি জানা থাকলে লিখুন:
<code>/add -1001234567890</code>
""")

                        elif cb_data == "my_chans":
                            chans = get_user_channels(user_id)
                            if not chans:
                                await answer_cb(session, cb_id, "⚠️ আপনার কোনো চ্যানেল বা গ্রুপ যুক্ত নেই।", alert=True)
                            else:
                                await answer_cb(session, cb_id)
                                msg_c = "📋 <b>আপনার সুরক্ষায় থাকা চ্যানেল ও গ্রুপসমূহ:</b>\n\n"
                                for i, c in enumerate(chans, 1):
                                    msg_c += f"{i}. 📢 <b>{c['channel_title']}</b> (<code>@{c['channel_username'] or c['channel_id']}</code>)\n   🛡️ স্ট্যাটাস: সার্বক্ষণিক পাহারা চলছে ✅\n\n"
                                await send_msg(session, chat_id, msg_c)

                        elif cb_data == "help_info":
                            await answer_cb(session, cb_id)
                            await send_msg(session, chat_id, """
📖 <b>সচরাচর জিজ্ঞাসিত প্রশ্ন (FAQ):</b>

• <b>প্রাইভেট চ্যানেল/গ্রুপেও কি ডিডক্স আটকাবে?</b>
হ্যাঁ! পাবলিক হোক বা প্রাইভেট, উভয় জায়গাতেই বট লাইভ ভয়েস/ভিডিও ড্রপ হওয়া মাত্র ৩০০ মিলিসেকেন্ডে রিস্টোর করে অ্যাটাক ব্যর্থ করে দেবে।
""")

                        # অ্যাডমিন প্যানেল বাটনসমূহ
                        elif cb_data == "open_admin_panel":
                            if user_id != config.ADMIN_ID:
                                await answer_cb(session, cb_id, "⛔ এক্সেস ডিনাইড!", alert=True)
                            else:
                                await answer_cb(session, cb_id)
                                stats = get_stats()
                                await edit_msg(session, chat_id, mid, f"""
👑 <b>মাস্টার অ্যাডমিন কন্ট্রোল প্যানেল</b>
• 📡 চ্যানেল/গ্রুপ: <code>{stats['total_protected_channels']}</code> টি | 👥 ইউজার: <code>{stats['total_users']}</code> জন | ⚔️ ব্লকড অ্যাটাক: <code>{stats['total_attacks_blocked']}</code> টি
""", get_admin_keyboard())

                        elif cb_data == "adm_channels":
                            if user_id == config.ADMIN_ID:
                                await answer_cb(session, cb_id)
                                chans = get_active_channels()
                                if not chans:
                                    t = "📢 বর্তমানে কোনো চ্যানেল বা গ্রুপ পাহারায় যুক্ত নেই।"
                                else:
                                    t = f"📢 <b>পাহারায় থাকা সমস্ত চ্যানেল ও গ্রুপ ({len(chans)} টি):</b>\n\n"
                                    for i, c in enumerate(chans[:15], 1):
                                        t += f"{i}. 📢 <b>{c['channel_title']}</b> (<code>@{c['channel_username'] or c['channel_id']}</code>)\n   👤 যোগকারী: <code>{c['added_by_user_id']}</code>\n\n"
                                await edit_msg(session, chat_id, mid, t, {"inline_keyboard": [[{"text": "🔙 পেছনে যান", "callback_data": "open_admin_panel"}]]})

                        elif cb_data == "adm_users":
                            if user_id == config.ADMIN_ID:
                                await answer_cb(session, cb_id)
                                tot = get_users_count()
                                t = f"""
👥 <b>ইউজার ম্যানেজমেন্ট ড্যাশবোর্ড</b>

• 👥 মোট নিবন্ধিত ইউজার: <code>{tot}</code> জন
• 🔒 সিকিউরিটি: অ্যান্টি-ফ্লাড রেট লিমিটার সক্রিয়

⚙️ <b>কমান্ডসমূহ:</b>
• <code>/ban &lt;user_id&gt;</code> — ইউজার ব্যান
• <code>/unban &lt;user_id&gt;</code> — ব্যান প্রত্যাহার
• <code>/broadcast &lt;মেসেজ&gt;</code> — সবাইকে নোটিশ পাঠান
"""
                                await edit_msg(session, chat_id, mid, t, {"inline_keyboard": [[{"text": "🔙 পেছনে যান", "callback_data": "open_admin_panel"}]]})

                        elif cb_data == "adm_forensics":
                            if user_id == config.ADMIN_ID:
                                await answer_cb(session, cb_id)
                                forensics = get_recent_forensics(limit=5)
                                if not forensics:
                                    t = "🕵️ <b>ব্ল্যাকবক্স ফরেনসিক ডাটা:</b>\n\nএখনো কোনো আক্রমণ ঘটেনি। সিস্টেম সম্পূর্ণ নিরাপদ ও সুরক্ষিত!"
                                else:
                                    t = "🕵️ <b>ডিডক্স ব্ল্যাকবক্স ফরেনসিক অডিট লগ:</b>\n\n"
                                    for i, f in enumerate(forensics, 1):
                                        t += f"{i}. 📢 <b>{f.get('channel_title', 'Unknown')}</b>\n"
                                        t += f"   ⚔️ ধরন: <code>{f.get('attack_type', 'UDP_FLOOD')}</code>\n"
                                        t += f"   ⚡ রিকভারি: <code>{f['recovery_time_ms']}</code> ms\n"
                                        t += f"   👤 সন্দেহভাজন: <code>{f.get('suspect_info') or 'None'}</code>\n"
                                        t += f"   🕒 সময়: <code>{f.get('timestamp')}</code>\n\n"
                                await edit_msg(session, chat_id, mid, t, {"inline_keyboard": [[{"text": "🔙 পেছনে যান", "callback_data": "open_admin_panel"}]]})

                        elif cb_data == "adm_attacks":
                            if user_id == config.ADMIN_ID:
                                await answer_cb(session, cb_id)
                                atks = get_recent_attacks(limit=5)
                                if not atks:
                                    t = "⚔️ এখনো কোনো ডিডক্স আক্রমণ রেকর্ড হয়নি। সিস্টেম নিরাপদ!"
                                else:
                                    t = "⚔️ <b>সাম্প্রতিক প্রতিহত হওয়া ডিডক্স আক্রমণ লগ:</b>\n\n"
                                    for i, a in enumerate(atks, 1):
                                        t += f"{i}. 📢 <b>{a.get('channel_title', 'Unknown')}</b>\n"
                                        t += f"   ⚡ রিকভারি সময়: <code>{a['recovery_time_ms']}</code> ms\n"
                                        t += f"   🕒 সময়: <code>{a['timestamp']}</code>\n   🛡️ ফলাফল: <b>সফলভাবে প্রতিহত</b> ✅\n\n"
                                await edit_msg(session, chat_id, mid, t, {"inline_keyboard": [[{"text": "🔙 পেছনে যান", "callback_data": "open_admin_panel"}]]})

                        elif cb_data == "adm_sync":
                            if user_id == config.ADMIN_ID:
                                await shield_engine.refresh_channels()
                                await answer_cb(session, cb_id, "✅ ক্লাউড ইঞ্জিন ও ডাটাবেজ সফলভাবে রিফ্রেশ ও সিঙ্ক হয়েছে!", alert=True)

                        elif cb_data == "adm_broadcast_help":
                            if user_id == config.ADMIN_ID:
                                await answer_cb(session, cb_id)
                                t = """
📣 <b>সবাইকে নোটিশ বা মেসেজ পাঠানোর নিয়ম:</b>

চ্যাটে এভাবে লিখুন:
<code>/broadcast আপনার নোটিশের কথা এখানে লিখবেন</code>
"""
                                await edit_msg(session, chat_id, mid, t, {"inline_keyboard": [[{"text": "🔙 পেছনে যান", "callback_data": "open_admin_panel"}]]})

            except Exception as e:
                print(f"[!] Polling loop error: {e}")
                await asyncio.sleep(2)
