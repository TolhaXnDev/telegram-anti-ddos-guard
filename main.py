"""
Telegram Anti-DDoS Sentinel Guard - Dual Engine Controller
পাবলিক বট (@LiveShieldXBot) এবং অ্যাসিস্ট্যান্ট ডিফেন্স ইঞ্জিন (Local & Cloud Ready)
"""
import asyncio
import os
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession
from colorama import Fore, Style, init

import config
from core.database import init_db, get_stats
from core.shield_engine import MultiShieldEngine
from core.telegram_ui import register_bot_handlers

init(autoreset=True)

def print_banner():
    banner = f"""
{Fore.RED + Style.BRIGHT}╔══════════════════════════════════════════════════════════════════════╗
║  {Fore.WHITE + Style.BRIGHT}🛡️  TELEGRAM ANTI-DDOS SENTINEL (LIVE SHIELD PRO v1.0)             {Fore.RED}║
║  {Fore.YELLOW}পাবলিক বট: @LiveShieldXBot | সার্বক্ষণিক লাইভ স্ট্রিম সুরক্ষা        {Fore.RED}║
╚══════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
    print(banner)

async def main():
    print_banner()

    # ১. ডাটাবেজ তৈরি ও লোড
    init_db()
    stats = get_stats()
    print(Fore.CYAN + f"[*] ডাটাবেজ সচল: {stats['total_protected_channels']} টি চ্যানেল সুরক্ষায় আছে।")

    # সেশন পাথ
    base_dir = os.path.dirname(os.path.abspath(__file__))
    bot_session = os.path.join(base_dir, "bot_session")

    # ২. পাবলিক চ্যাটবট ক্লায়েন্ট চালু করা (@LiveShieldXBot)
    print(Fore.CYAN + "[*] পাবলিক টেলিগ্রাম বট কানেক্ট করা হচ্ছে...")
    bot_client = TelegramClient(bot_session, config.API_ID, config.API_HASH)
    await bot_client.start(bot_token=config.BOT_TOKEN)
    bot_me = await bot_client.get_me()
    print(Fore.GREEN + Style.BRIGHT + f"[✓] পাবলিক বট সফলভাবে সক্রিয়: {bot_me.first_name} (@{bot_me.username})")

    # ৩. অ্যাসিস্ট্যান্ট ক্লায়েন্ট চালু করা (StringSession অথবা লোকাল ফাইল)
    print(Fore.CYAN + "[*] অ্যাসিস্ট্যান্ট ডিফেন্স ক্লায়েন্ট কানেক্ট করা হচ্ছে...")
    if config.SESSION_STRING:
        print(Fore.GREEN + "[*] ক্লাউড সেশন স্ট্রিং ডিটেক্ট হয়েছে (Headless Mode)")
        assistant_client = TelegramClient(StringSession(config.SESSION_STRING), config.API_ID, config.API_HASH)
        await assistant_client.start()
    else:
        assistant_session = os.path.join(base_dir, "assistant_session")
        assistant_client = TelegramClient(assistant_session, config.API_ID, config.API_HASH)
        await assistant_client.start(phone=config.PHONE_NUMBER)

    asst_me = await assistant_client.get_me()
    print(Fore.GREEN + Style.BRIGHT + f"[✓] অ্যাসিস্ট্যান্ট ক্লায়েন্ট সক্রিয়: {asst_me.first_name} (@{asst_me.username or asst_me.phone})")

    # ৪. ইঞ্জিন ও হ্যান্ডলার ইনিশিয়ালাইজ
    engine = MultiShieldEngine(
        assistant_client=assistant_client,
        bot_client=bot_client,
        scan_interval=config.SCAN_INTERVAL_SECONDS
    )
    register_bot_handlers(bot_client, engine)
    print(Fore.GREEN + "[✓] চ্যাটবট কমান্ড হ্যান্ডলার ও বাটন সক্রিয় হয়েছে।")

    # ৫. সার্বক্ষণিক ডিফেন্স লুপ চালু
    print(Fore.WHITE + Style.BRIGHT + f"\n[🔥 সাকসেস!] @LiveShieldXBot এখন পুরোপুরি লাইভ ও সক্রিয়!")
    print(Fore.WHITE + f"[*] যে কোনো ইউজার বা বন্ধু বটে গিয়ে /start দিয়ে চ্যানেল সুরক্ষিত করতে পারবে।\n")

    try:
        await asyncio.gather(
            engine.start(),
            bot_client.run_until_disconnected(),
            assistant_client.run_until_disconnected()
        )
    except KeyboardInterrupt:
        print(Fore.YELLOW + "\n[!] সিস্টেম বন্ধ করা হচ্ছে...")
    finally:
        await engine.stop()
        await bot_client.disconnect()
        await assistant_client.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
