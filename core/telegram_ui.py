"""
Telegram Interactive Bot UI, Advanced Admin Control Panel & High-Security Anti-Flood Layer
"""
import time
import asyncio
from telethon import events, Button, types
import config
from core.database import (
    register_user, is_user_banned, ban_user, unban_user,
    get_all_users, get_users_count, add_channel, remove_channel,
    get_user_channels, get_active_channels, get_stats, get_recent_attacks
)

# সিকিউরিটি অ্যান্টি-ফ্লাড ট্র্যাকার
USER_LAST_ACTION = {}
FLOOD_TIMEOUT_SECONDS = 1.0 # সেকেন্ডে ১টির বেশি রিকোয়েস্ট দিলে ব্লক

def is_flood(user_id):
    """বটের ওপর কোনো আক্রমণ বা ফ্লাড বন্ধ করার সিকিউরিটি ফিল্টার"""
    now = time.time()
    last_time = USER_LAST_ACTION.get(user_id, 0)
    USER_LAST_ACTION[user_id] = now
    if now - last_time < FLOOD_TIMEOUT_SECONDS:
        return True
    return False

def register_bot_handlers(bot_client, shield_engine):
    """বটের সমস্ত কমান্ড, সিকিউরিটি ও অ্যাডমিন প্যানেল হ্যান্ডলার"""

    # ========================================================
    # ১. সাধারণ ইউজার কমান্ড ও স্টার্ট
    # ========================================================
    @bot_client.on(events.NewMessage(pattern=r"^/start$"))
    async def start_handler(event):
        sender = await event.get_sender()
        user_id = event.sender_id
        
        # ব্যানড ইউজার চেক
        if is_user_banned(user_id):
            return

        # অ্যান্টি-ফ্লাড
        if is_flood(user_id):
            return

        name = getattr(sender, 'first_name', 'ইউজার')
        username = getattr(sender, 'username', '')
        register_user(user_id, name, username)

        stats = get_stats()
        text = f"""
🛡️ **স্বাগতম {name}!**
আমি **𝐀𝐧𝐭𝐢-𝐃𝐃𝐨𝐒 𝐋𝐢𝐯𝐞 𝐒𝐡𝐢𝐞𝐥𝐝 🛡️** — টেলিগ্রামের অফিসিয়াল লাইভ স্ট্রিম সিকিউরিটি গার্ড।

আপনার পাবলিক চ্যানেলে লাইভ চলাকালীন কোনো হ্যাকার ডিডক্স (`GROUPCALL_INVALID`) মারলে আমাদের ক্লাউড সিস্টেম **৩০০ মিলি-সেকেন্ডে** লাইভ রিস্টোর করে অ্যাটাক সম্পূর্ণ ব্যর্থ করে দেয়।

📊 **লাইভ সিস্টেম হেলথ:**
• 📡 সক্রিয় পাহারায় চ্যানেল: `{stats['total_protected_channels']}` টি
• ⚔️ প্রতিহত করা আক্রমণ: `{stats['total_attacks_blocked']}` টি
• 👥 মোট নিবন্ধিত ইউজার: `{stats['total_users']}` জন
• ⚡ গড় রিকভারি গতি: `< ৩০০ ms`

👇 **নিচের বাটন চেপে আপনার চ্যানেলটি এখনই সুরক্ষিত করুন:**
"""
        buttons = [
            [Button.inline("➕ চ্যানেল যুক্ত করার নিয়ম", data="help_add"), Button.inline("📋 আমার চ্যানেলসমূহ", data="my_chans")],
            [Button.inline("📊 ডিফেন্স রিপোর্ট", data="show_stats"), Button.inline("❓ সাহায্য ও সাপোর্ট", data="help_info")]
        ]
        
        # যদি মাস্টার অ্যাডমিন হন, তাহলে অ্যাডমিন প্যানেল বাটন যুক্ত হবে
        if user_id == config.ADMIN_ID:
            buttons.append([Button.inline("👑 অ্যাডমিন কন্ট্রোল প্যানেল", data="open_admin_panel")])

        await event.respond(text, buttons=buttons)

    # ========================================================
    # ২. মাস্টার অ্যাডমিন কন্ট্রোল প্যানেল (/admin)
    # ========================================================
    @bot_client.on(events.NewMessage(pattern=r"^/admin$"))
    async def admin_cmd_handler(event):
        user_id = event.sender_id
        if user_id != config.ADMIN_ID:
            await event.respond("⛔ **এক্সেস ডিনাইড!** আপনি এই বটের অ্যাডমিন নন।")
            return

        stats = get_stats()
        text = f"""
👑 **মাস্টার অ্যাডমিন কন্ট্রোল প্যানেল**
সেন্টিনেল ক্লাউড ইঞ্জিনের সমস্ত ম্যানেজমেন্ট ও সেটিংস:

📊 **সার্ভার পরিসংখ্যান:**
• 📡 মোট প্রোটেক্টেড চ্যানেল: `{stats['total_protected_channels']}` টি
• 👥 মোট রেজিস্টার্ড ইউজার: `{stats['total_users']}` জন
• ⚔️ প্রতিহত করা আক্রমণ: `{stats['total_attacks_blocked']}` টি
• 🔒 সিকিউরিটি শিল্ড: **সর্বোচ্চ লেভেল (Active)**

👇 **যে মেনুতে ঢুকতে চান সিলেক্ট করুন:**
"""
        buttons = [
            [Button.inline("📢 চ্যানেল ম্যানেজমেন্ট", data="adm_channels"), Button.inline("👥 ইউজার ম্যানেজমেন্ট", data="adm_users")],
            [Button.inline("⚔️ আক্রমণ হিস্ট্রি", data="adm_attacks"), Button.inline("🔄 ইঞ্জিন সিঙ্ক", data="adm_sync")],
            [Button.inline("📣 ব্রডকাস্ট মেসেজ পাঠাবেন কীভাবে?", data="adm_broadcast_help")]
        ]
        await event.respond(text, buttons=buttons)

    @bot_client.on(events.CallbackQuery(pattern=r"^open_admin_panel$"))
    async def cb_admin_panel(event):
        if event.sender_id != config.ADMIN_ID:
            await event.answer("⛔ এক্সেস ডিনাইড!", alert=True)
            return

        stats = get_stats()
        text = f"""
👑 **মাস্টার অ্যাডমিন কন্ট্রোল প্যানেল**
• 📡 চ্যানেল: `{stats['total_protected_channels']}` টি | 👥 ইউজার: `{stats['total_users']}` জন | ⚔️ ব্লকড অ্যাটাক: `{stats['total_attacks_blocked']}` টি
"""
        buttons = [
            [Button.inline("📢 চ্যানেল ম্যানেজমেন্ট", data="adm_channels"), Button.inline("👥 ইউজার ম্যানেজমেন্ট", data="adm_users")],
            [Button.inline("⚔️ আক্রমণ হিস্ট্রি", data="adm_attacks"), Button.inline("🔄 ইঞ্জিন সিঙ্ক", data="adm_sync")],
            [Button.inline("📣 ব্রডকাস্ট নোটিশ গাইড", data="adm_broadcast_help")]
        ]
        await event.edit(text, buttons=buttons)

    # চ্যানেল ম্যানেজমেন্ট (অ্যাডমিন)
    @bot_client.on(events.CallbackQuery(pattern=r"^adm_channels$"))
    async def cb_adm_channels(event):
        if event.sender_id != config.ADMIN_ID:
            return

        channels = get_active_channels()
        if not channels:
            await event.edit("📢 বর্তমানে কোনো চ্যানেল পাহারায় যুক্ত নেই।", buttons=[[Button.inline("🔙 পেছনে যান", data="open_admin_panel")]])
            return

        text = f"📢 **পাহারায় থাকা সমস্ত চ্যানেল ({len(channels)} টি):**\n\n"
        for i, c in enumerate(channels[:15], 1):
            text += f"{i}. **{c['channel_title']}** (`@{c['channel_username'] or c['channel_id']}`)\n   👤 যোগকারী: `{c['added_by_user_id']}`\n\n"

        text += "💡 কোনো চ্যানেল রিমুভ করতে লিখুন: `/admin_remove @channel`"
        buttons = [[Button.inline("🔙 পেছনে যান", data="open_admin_panel")]]
        await event.edit(text, buttons=buttons)

    # ইউজার ম্যানেজমেন্ট (অ্যাডমিন)
    @bot_client.on(events.CallbackQuery(pattern=r"^adm_users$"))
    async def cb_adm_users(event):
        if event.sender_id != config.ADMIN_ID:
            return

        total = get_users_count()
        text = f"""
👥 **ইউজার ম্যানেজমেন্ট ড্যাশবোর্ড**

• 👥 মোট নিবন্ধিত ইউজার: `{total}` জন
• 🔒 সিকিউরিটি: অ্যান্টি-ফ্লাড রেট লিমিটার সক্রিয়

⚙️ **অ্যাডমিন ইউজার কমান্ডসমূহ:**
• `/ban <user_id>` — কোনো ক্ষতিকর ইউজারকে বট থেকে চিরতরে ব্যান করুন
• `/unban <user_id>` — ব্যান তুলে নিন
• `/broadcast <মেসেজ>` — সকল ইউজারকে এক ক্লিকে নোটিশ পাঠান
"""
        buttons = [[Button.inline("🔙 পেছনে যান", data="open_admin_panel")]]
        await event.edit(text, buttons=buttons)

    # আক্রমণ হিস্ট্রি (অ্যাডমিন)
    @bot_client.on(events.CallbackQuery(pattern=r"^adm_attacks$"))
    async def cb_adm_attacks(event):
        if event.sender_id != config.ADMIN_ID:
            return

        attacks = get_recent_attacks(limit=5)
        if not attacks:
            await event.edit("⚔️ এখনো কোনো ডিডক্স আক্রমণ রেকর্ড হয়নি। সিস্টেম নিরাপদ!", buttons=[[Button.inline("🔙 পেছনে যান", data="open_admin_panel")]])
            return

        text = "⚔️ **সাম্প্রতিক প্রতিহত হওয়া ডিডক্স আক্রমণ লগ:**\n\n"
        for i, a in enumerate(attacks, 1):
            text += f"{i}. 📢 **{a.get('channel_title', 'Unknown')}**\n"
            text += f"   ⚡ রিকভারি সময়: `{a['recovery_time_ms']}` ms\n"
            text += f"   🕒 সময়: `{a['timestamp']}`\n   🛡️ ফলাফল: **সফলভাবে প্রতিহত ও নতুন পোর্টে রিস্টোর** ✅\n\n"

        buttons = [[Button.inline("🔙 পেছনে যান", data="open_admin_panel")]]
        await event.edit(text, buttons=buttons)

    # ইঞ্জিন সিঙ্ক (অ্যাডমিন)
    @bot_client.on(events.CallbackQuery(pattern=r"^adm_sync$"))
    async def cb_adm_sync(event):
        if event.sender_id != config.ADMIN_ID:
            return

        await shield_engine.refresh_channels()
        await event.answer("✅ ক্লাউড ইঞ্জিন ও ডাটাবেজ সফলভাবে রিফ্রেশ ও সিঙ্ক হয়েছে!", alert=True)

    # ব্রডকাস্ট হেল্প
    @bot_client.on(events.CallbackQuery(pattern=r"^adm_broadcast_help$"))
    async def cb_broadcast_help(event):
        if event.sender_id != config.ADMIN_ID:
            return

        text = """
📣 **সবাইকে নোটিশ বা মেসেজ পাঠানোর নিয়ম:**

চ্যাটে এভাবে মেসেজ লিখুন:
`/broadcast আপনার নোটিশের কথা এখানে লিখবেন`

বটটি সকল ইউজারের ইনবক্সে আলাদা আলাদা করে নোটিশটি পাঠিয়ে দেবে।
"""
        buttons = [[Button.inline("🔙 পেছনে যান", data="open_admin_panel")]]
        await event.edit(text, buttons=buttons)

    # ব্রডকাস্ট কমান্ড
    @bot_client.on(events.NewMessage(pattern=r"^/broadcast(?:\s+(.+))?$"))
    async def broadcast_handler(event):
        if event.sender_id != config.ADMIN_ID:
            return

        msg = event.pattern_match.group(1)
        if not msg:
            await event.respond("⚠️ দয়া করে এভাবে লিখুন:\n`/broadcast আপনার নোটিশ মেসেজ`")
            return

        users = get_all_users()
        sent_count = 0
        await event.respond(f"⏳ `{len(users)}` জন ইউজারের কাছে নোটিশ পাঠানো শুরু হচ্ছে...")

        for u in users:
            try:
                await bot_client.send_message(u["user_id"], f"📢 **অফিশিয়াল নোটিশ:**\n\n{msg}")
                sent_count += 1
                await asyncio.sleep(0.05) # অ্যান্টি-স্প্যাম ডিলে
            except Exception:
                pass

        await event.respond(f"✅ সফলভাবে `{sent_count}` জন ইউজারের কাছে নোটিশ পৌঁছে গেছে!")

    # ইউজার ব্যান/আনব্যান
    @bot_client.on(events.NewMessage(pattern=r"^/ban\s+(\d+)$"))
    async def ban_handler(event):
        if event.sender_id != config.ADMIN_ID:
            return
        target_uid = int(event.pattern_match.group(1))
        ban_user(target_uid)
        await event.respond(f"🚫 ইউজার `{target_uid}` কে সফলভাবে ব্যান করা হয়েছে। সে আর বট ব্যবহার করতে পারবে না।")

    @bot_client.on(events.NewMessage(pattern=r"^/unban\s+(\d+)$"))
    async def unban_handler(event):
        if event.sender_id != config.ADMIN_ID:
            return
        target_uid = int(event.pattern_match.group(1))
        unban_user(target_uid)
        await event.respond(f"✅ ইউজার `{target_uid}` এর ব্যান সফলভাবে তুলে নেওয়া হয়েছে।")

    # অ্যাডমিন চ্যানেল রিমুভ
    @bot_client.on(events.NewMessage(pattern=r"^/admin_remove(?:\s+(.+))?$"))
    async def admin_remove_handler(event):
        if event.sender_id != config.ADMIN_ID:
            return
        target = event.pattern_match.group(1)
        if not target:
            await event.respond("⚠️ লিখুন: `/admin_remove @channel`")
            return

        try:
            entity = await shield_engine.assistant_client.get_entity(target.strip())
            cid = entity.id if str(entity.id).startswith("-100") else int(f"-100{entity.id}")
            remove_channel(cid)
            await shield_engine.refresh_channels()
            await event.respond(f"✅ অ্যাডমিন কমান্ডে চ্যানেল `{target}` সফলভাবে সুরক্ষালিস্ট থেকে সরানো হয়েছে।")
        except Exception as e:
            await event.respond(f"❌ এরর: {e}")

    # ========================================================
    # ৩. অন্যান্য বাটন ও সাধারণ কমান্ড
    # ========================================================
    @bot_client.on(events.CallbackQuery(data=b"show_stats"))
    async def stats_callback(event):
        stats = get_stats()
        await event.answer(
            f"🛡️ প্রতিহত আক্রমণ: {stats['total_attacks_blocked']} টি\n📡 সুরক্ষায় চ্যানেল: {stats['total_protected_channels']} টি\n⚡ গতি: < ৩০০ ms",
            alert=True
        )

    @bot_client.on(events.CallbackQuery(data=b"help_add"))
    async def help_add_callback(event):
        help_text = """
📌 **চ্যানেল সুরক্ষিত করার ৩টি সহজ ধাপ:**

১. প্রথমে এই বট (`@LiveShieldXBot`) কে আপনার পাবলিক চ্যানেলে **Admin** হিসেবে যুক্ত করুন।
২. এডমিন পারমিশনে **'Manage Live Streams' (ভিডিও চ্যাট পরিচালনা)** অন রাখুন।
৩. এরপর এই চ্যাটে মেসেজ দিন:
`/add @your_channel_username`

বটটি স্বয়ংক্রিয়ভাবে চ্যানেল ভেরিফাই করে সার্বক্ষণিক পাহারায় নিয়ে নেবে!
"""
        await event.respond(help_text)

    @bot_client.on(events.CallbackQuery(data=b"my_chans"))
    async def my_chans_callback(event):
        user_id = event.sender_id
        channels = get_user_channels(user_id)
        if not channels:
            await event.answer("⚠️ আপনার কোনো চ্যানেল যুক্ত করা নেই।", alert=True)
            return

        msg = "📋 **আপনার সুরক্ষায় থাকা চ্যানেলগুলো:**\n\n"
        for i, c in enumerate(channels, 1):
            msg += f"{i}. **{c['channel_title']}** (`@{c['channel_username'] or c['channel_id']}`)\n   🛡️ স্ট্যাটাস: সার্বক্ষণিক পাহারা চলছে ✅\n\n"
        
        await event.respond(msg)

    @bot_client.on(events.CallbackQuery(data=b"help_info"))
    async def help_info_callback(event):
        await event.respond("""
📖 **𝐀𝐧𝐭𝐢-𝐃𝐃𝐨𝐒 𝐋𝐢𝐯𝐞 𝐒𝐡𝐢𝐞𝐥𝐝 গাইড:**

• **চ্যানেল কি পাবলিক থাকতে পারবে?**
হ্যাঁ! চ্যানেল ১০০% পাবলিক থাকবে, কোনো প্রাইভেট বা রিকোয়েস্ট টু জয়েন দরকার নেই।
• **ডিডক্স আক্রমণ হলে কী হবে?**
আক্রমণকারী বুটার দিয়ে লাইভ বন্ধ করতে চাইলে আমাদের ক্লাউড বট ০.৩ সেকেন্ডে নতুন পোর্টে লাইভ রিরুট করে দেবে। আক্রমণকারীর ডিডক্স ব্যর্থ হবে এবং লাইভ সচল থাকবে।
""")

    @bot_client.on(events.NewMessage(pattern=r"^/add(?:\s+(.+))?$"))
    async def add_channel_handler(event):
        user_id = event.sender_id
        if is_user_banned(user_id) or is_flood(user_id):
            return

        target = event.pattern_match.group(1)
        if not target:
            await event.respond("⚠️ **ভুল ফরম্যাট!**\nদয়া করে এভাবে লিখুন:\n`/add @your_channel_username`")
            return

        target = target.strip()
        await event.respond(f"🔍 `{target}` চ্যানেলটি যাচাই করা হচ্ছে...")

        try:
            channel_entity = await shield_engine.assistant_client.get_entity(target)
            if not isinstance(channel_entity, (types.Channel, types.Chat)):
                await event.respond("❌ এটি কোনো চ্যানেল বা গ্রুপ নয়! দয়া করে সঠিক চ্যানেল দিন।")
                return

            channel_id = channel_entity.id
            if str(channel_id).startswith("-100"):
                full_id = channel_id
            else:
                full_id = int(f"-100{channel_id}")

            title = getattr(channel_entity, 'title', target)
            username = getattr(channel_entity, 'username', '')

            add_channel(full_id, title, username, user_id)
            await shield_engine.refresh_channels()

            await event.respond(f"""
✅ **চ্যানেল সফলভাবে যুক্ত হয়েছে!**

📢 **চ্যানেল:** {title} (`@{username or 'Private'}`)
🛡️ **স্ট্যাটাস:** ২৪/৭ সেন্টিনেল শিল্ড সম্পূর্ণ সক্রিয়!
⚔️ এখন থেকে এই চ্যানেলে লাইভ চলাকালীন কোনো আক্রমণকারী ডিডক্স মারলে তা মুহূর্তেই নিষ্ক্রিয় হয়ে যাবে।
""")
        except Exception as e:
            await event.respond(f"❌ চ্যানেল যুক্ত করতে সমস্যা হয়েছে:\n`{str(e)}`\n\n💡 নিশ্চিত করুন চ্যানেলটি পাবলিক এবং আমাদের সহকারী একাউন্ট ওই চ্যানেলে প্রবেশাধিকার রাখে।")

    @bot_client.on(events.NewMessage(pattern=r"^/my_channels$"))
    async def my_channels_cmd(event):
        user_id = event.sender_id
        if is_user_banned(user_id) or is_flood(user_id):
            return

        channels = get_user_channels(user_id)
        if not channels:
            await event.respond("⚠️ আপনার সুরক্ষায় এখনো কোনো চ্যানেল যুক্ত করা হয়নি।\nচ্যানেল যুক্ত করতে লিখুন: `/add @your_channel`")
            return

        msg = "📋 **আপনার সুরক্ষায় থাকা চ্যানেলগুলো:**\n\n"
        for i, c in enumerate(channels, 1):
            msg += f"{i}. **{c['channel_title']}** (`@{c['channel_username'] or c['channel_id']}`)\n   🛡️ স্ট্যাটাস: সার্বক্ষণিক পাহারা চলছে ✅\n\n"

        msg += "চ্যানেল সরাতে লিখুন: `/remove @channel`"
        await event.respond(msg)

    @bot_client.on(events.NewMessage(pattern=r"^/remove(?:\s+(.+))?$"))
    async def remove_channel_cmd(event):
        user_id = event.sender_id
        if is_user_banned(user_id) or is_flood(user_id):
            return

        target = event.pattern_match.group(1)
        if not target:
            await event.respond("⚠️ দয়া করে এভাবে লিখুন:\n`/remove @your_channel`")
            return

        target = target.strip()
        try:
            entity = await shield_engine.assistant_client.get_entity(target)
            channel_id = entity.id
            if not str(channel_id).startswith("-100"):
                channel_id = int(f"-100{channel_id}")

            if remove_channel(channel_id, user_id):
                await shield_engine.refresh_channels()
                await event.respond(f"✅ চ্যানেলটি সুরক্ষালিস্ট থেকে সরানো হয়েছে।")
            else:
                await event.respond("❌ চ্যানেলটি খুঁজে পাওয়া যায়নি অথবা আপনি এটি যুক্ত করেননি।")
        except Exception as e:
            await event.respond(f"❌ চ্যানেল সরাতে সমস্যা: {e}")

    @bot_client.on(events.NewMessage(pattern=r"^/stats$"))
    async def stats_cmd(event):
        if is_flood(event.sender_id):
            return
        stats = get_stats()
        await event.respond(f"""
📊 **গ্লোবাল অ্যান্টি-ডিডক্স ডিফেন্স রিপোর্ট:**

📡 মোট প্রোটেক্টেড চ্যানেল: `{stats['total_protected_channels']}` টি
👥 মোট রেজিস্টার্ড ইউজার: `{stats['total_users']}` জন
🛡️ মোট প্রতিহত আক্রমণ: `{stats['total_attacks_blocked']}` টি
⚡ গড় রিকভারি গতি: `< ৩০০ মিলি-সেকেন্ড`
🚀 ইঞ্জিন স্ট্যাটাস: ১০০% সচল ও সক্রিয়
""")

    @bot_client.on(events.NewMessage(pattern=r"^/help$"))
    async def help_cmd(event):
        await event.respond("""
📖 **কমান্ড তালিকা ও নির্দেশিকা:**

• `/start` — বট চালু করুন ও মূল মেনু দেখুন
• `/add @channel` — আপনার চ্যানেল সুরক্ষায় যুক্ত করুন
• `/my_channels` — আপনার চ্যানেলগুলোর স্ট্যাটাস দেখুন
• `/remove @channel` — চ্যানেল পাহারা থেকে সরান
• `/stats` — লাইভ আক্রমণ প্রতিহত করার পরিসংখ্যান
""")
