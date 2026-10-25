"""
Telegram Anti-DDoS Sentinel Guard - Dual Engine Controller
পাবলিক বট (@LiveShieldXBot) এবং অ্যাসিস্ট্যান্ট ডিফেন্স ইঞ্জিন (Render, Heroku & Cloud 24/7 Ready)
"""
import asyncio
import os
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession
from aiohttp import web
from colorama import Fore, Style, init

import config
from core.database import init_db, get_stats
from core.shield_engine import MultiShieldEngine
from core.bot_api_engine import run_bot_polling

init(autoreset=True)

def print_banner():
    banner = f"""
{Fore.RED + Style.BRIGHT}╔══════════════════════════════════════════════════════════════════════╗
║  {Fore.WHITE + Style.BRIGHT}🛡️  TELEGRAM ANTI-DDOS SENTINEL (LIVE SHIELD PRO v1.0)             {Fore.RED}║
║  {Fore.YELLOW}পাবলিক বট: @LiveShieldXBot | সার্বক্ষণিক লাইভ স্ট্রিম সুরক্ষা        {Fore.RED}║
╚══════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
    print(banner)

async def handle_health(request):
    """Render বা যেকোনো ক্লাউডের জন্য হেলথচেক পোর্ট (২৪/৭ সজাগ রাখার জন্য)"""
    stats = get_stats()
    return web.json_response({
        "status": "online",
        "shield": "active",
        "bot": "@LiveShieldXBot",
        "protected_channels": stats["total_protected_channels"],
        "attacks_blocked": stats["total_attacks_blocked"]
    })

async def start_keepalive_server():
    """রেন্ডারের ফ্রি সার্ভারকে ঘুম থেকে বিরত রাখার ওয়েব পোর্ট"""
    port = int(os.getenv("PORT", "10000"))
    app = web.Application()
    app.router.add_get("/", handle_health)
    app.router.add_get("/health", handle_health)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(Fore.GREEN + f"[✓] ক্লাউড কিপ-অ্যালাইভ ওয়েব পোর্ট সক্রিয়: পোর্ট {port}")

async def main():
    print_banner()

    # ১. ডাটাবেজ তৈরি ও লোড
    init_db()
    stats = get_stats()
    print(Fore.CYAN + f"[*] ডাটাবেজ সচল: {stats['total_protected_channels']} টি চ্যানেল সুরক্ষায় আছে।")

    # ২. দ্রুত ক্লাউড ওয়েব পোর্ট চালু করা (Render Healthcheck পাস করার জন্য)
    await start_keepalive_server()

    # ৩. অ্যাসিস্ট্যান্ট ক্লায়েন্ট চালু করা (Telethon MTProto Engine)
    print(Fore.CYAN + "[*] অ্যাসিস্ট্যান্ট ডিফেন্স ক্লায়েন্ট কানেক্ট করা হচ্ছে...")
    if config.SESSION_STRING:
        print(Fore.GREEN + "[*] ক্লাউড সেশন স্ট্রিং ডিটেক্ট হয়েছে (Headless Mode)")
        assistant_client = TelegramClient(StringSession(config.SESSION_STRING), config.API_ID, config.API_HASH)
        await assistant_client.start()
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        assistant_session = os.path.join(base_dir, "assistant_session")
        assistant_client = TelegramClient(assistant_session, config.API_ID, config.API_HASH)
        await assistant_client.start(phone=config.PHONE_NUMBER)

    asst_me = await assistant_client.get_me()
    print(Fore.GREEN + Style.BRIGHT + f"[✓] অ্যাসিস্ট্যান্ট ক্লায়েন্ট সক্রিয়: {asst_me.first_name} (@{asst_me.username or asst_me.phone})")

    # ৪. ইঞ্জিন ইনিশিয়ালাইজ
    engine = MultiShieldEngine(
        assistant_client=assistant_client,
        scan_interval=config.SCAN_INTERVAL_SECONDS
    )

    print(Fore.WHITE + Style.BRIGHT + f"\n[🔥 সাকসেস!] @LiveShieldXBot এখন পুরোপুরি লাইভ ও সক্রিয়!")
    print(Fore.WHITE + f"[*] যে কোনো ইউজার বা বন্ধু বটে গিয়ে /start দিয়ে চ্যানেল সুরক্ষিত করতে পারবে।\n")

    # ৫. প্যারালালি ডিফেন্স ইঞ্জিন এবং Bot API পোলিং চালানো
    try:
        await asyncio.gather(
            engine.start(),
            run_bot_polling(engine),
            assistant_client.run_until_disconnected()
        )
    except KeyboardInterrupt:
        print(Fore.YELLOW + "\n[!] সিস্টেম বন্ধ করা হচ্ছে...")
    finally:
        await engine.stop()
        await assistant_client.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
