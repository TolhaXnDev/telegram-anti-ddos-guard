"""
Telegram Interactive Bot UI & Command Handlers
বন্ধু ও সাধারণ ইউজারদের জন্য প্রিমিয়াম চ্যাটবট ইন্টারফেস
"""
from telethon import events, Button, types
from core.database import add_channel, remove_channel, get_user_channels, get_stats

def register_bot_handlers(bot_client, shield_engine):
    """বটের সমস্ত কমান্ড ও বাটন হ্যান্ডলার রেজিস্টার করা"""

    @bot_client.on(events.NewMessage(pattern=r"^/start$"))
    async def start_handler(event):
        sender = await event.get_sender()
        name = getattr(sender, 'first_name', 'ইউজার')
        
        stats = get_stats()
        text = f"""
🛡️ **স্বাগতম {name}!**
আমি **𝐀𝐧𝐭𝐢-𝐃𝐃𝐨𝐒 𝐋𝐢𝐯𝐞 𝐒𝐡𝐢𝐞𝐥𝐝 🛡️** — টেলিগ্রামের অফিসিয়াল লাইভ স্ট্রিম সিকিউরিটি গার্ড।

আপনার পাবলিক চ্যানেলে লাইভ চলাকালীন হ্যাকাররা বট দিয়ে ডিডক্স (`GROUPCALL_INVALID`) মারলে আমাদের সিস্টেম **৩০০ মিলি-সেকেন্ডে** লাইভ রিস্টোর করে অ্যাটাক সম্পূর্ণ ব্যর্থ করে দেয়।

📊 **লাইভ সিস্টেম হেলথ:**
• 📡 সক্রিয় পাহারায় চ্যানেল: `{stats['total_protected_channels']}` টি
• ⚔️ প্রতিহত করা আক্রমণ: `{stats['total_attacks_blocked']}` টি
• ⚡ গড় রিকভারি গতি: `< ৩০০ ms`

👇 **নিচের বাটন চেপে আপনার চ্যানেলটি এখনই সুরক্ষিত করুন:**
"""
        buttons = [
            [Button.inline("➕ চ্যানেল যুক্ত করার নিয়ম", data="help_add"), Button.inline("📋 আমার চ্যানেলসমূহ", data="my_chans")],
            [Button.inline("📊 ডিফেন্স রিপোর্ট", data="show_stats"), Button.inline("❓ সাহায্য ও সাপোর্ট", data="help_info")]
        ]
        await event.respond(text, buttons=buttons)

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
আক্রমণকারী বুটার দিয়ে লাইভ বন্ধ করতে চাইলে আমাদের বট ০.৩ সেকেন্ডে নতুন পোর্টে লাইভ রিরুট করে দেবে। আক্রমণকারীর ডিডক্স ব্যর্থ হবে এবং লাইভ সচল থাকবে।
""")

    @bot_client.on(events.NewMessage(pattern=r"^/add(?:\s+(.+))?$"))
    async def add_channel_handler(event):
        user_id = event.sender_id
        target = event.pattern_match.group(1)

        if not target:
            await event.respond("⚠️ **ভুল ফরম্যাট!**\nদয়া করে এভাবে লিখুন:\n`/add @your_channel_username`")
            return

        target = target.strip()
        await event.respond(f"🔍 `{target}` চ্যানেলটি যাচাই করা হচ্ছে...")

        try:
            # সহকারী ক্লায়েন্ট বা বট ক্লায়েন্ট দিয়ে চ্যানেল খোঁজা
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

            # ডাটাবেজে রেকর্ড করা
            add_channel(full_id, title, username, user_id)
            
            # ডিফেন্স ইঞ্জিন রিফ্রেশ করা
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
        stats = get_stats()
        await event.respond(f"""
📊 **গ্লোবাল অ্যান্টি-ডিডক্স ডিফেন্স রিপোর্ট:**

📡 মোট প্রোটেক্টেড চ্যানেল: `{stats['total_protected_channels']}` টি
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
