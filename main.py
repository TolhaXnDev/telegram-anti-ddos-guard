"""
Telegram Anti-DDoS Sentinel Guard - Dual Engine Controller
পাবলিক বট (@LiveShieldXBot) এবং অ্যাসিস্ট্যান্ট ডিফেন্স ইঞ্জিন (Bulletproof & Crash-Resistant)
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

# গ্লোবাল স্ট্যাটাস ট্র্যাকার
service_status = {
    "assistant_connected": False,
    "assistant_name": None,
    "assistant_id": None,
    "assistant_error": None
}

def print_banner():
    banner = f"""
{Fore.RED + Style.BRIGHT}╔══════════════════════════════════════════════════════════════════════╗
║  {Fore.WHITE + Style.BRIGHT}🛡️  TELEGRAM ANTI-DDOS SENTINEL (LIVE SHIELD PRO v1.0)             {Fore.RED}║
║  {Fore.YELLOW}পাবলিক বট: @LiveShieldXBot | সার্বক্ষণিক লাইভ স্ট্রিম সুরক্ষা        {Fore.RED}║
╚══════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
    print(banner)

async def handle_health(request):
    """Render হেলথচেক পোর্ট (২৪/৭ সজাগ রাখার জন্য ও লাইভ স্ট্যাটাস মনিটরিং)"""
    stats = get_stats()
    return web.json_response({
        "status": "online",
        "shield": "active",
        "assistant_connected": service_status["assistant_connected"],
        "assistant_name": service_status["assistant_name"],
        "assistant_id": service_status["assistant_id"],
        "assistant_error": service_status["assistant_error"],
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

    # ২. দ্রুত ক্লাউড ওয়েব পোর্ট চালু করা
    await start_keepalive_server()

    # ৩. অ্যাসিস্ট্যান্ট ক্লায়েন্ট সেফ-কানেক্ট
    assistant_client = None
    if config.SESSION_STRING:
        print(Fore.CYAN + "[*] অ্যাসিস্ট্যান্ট ক্লায়েন্ট ইনিশিয়ালাইজ করা হচ্ছে...")
        try:
            assistant_client = TelegramClient(StringSession(config.SESSION_STRING), config.API_ID, config.API_HASH)
            await assistant_client.connect()
            if await assistant_client.is_user_authorized():
                asst_me = await assistant_client.get_me()
                service_status["assistant_connected"] = True
                service_status["assistant_name"] = asst_me.first_name
                service_status["assistant_id"] = asst_me.id
                print(Fore.GREEN + Style.BRIGHT + f"[✓] অ্যাসিস্ট্যান্ট সক্রিয়: {asst_me.first_name} (ID: {asst_me.id})")
            else:
                service_status["assistant_error"] = "Session string exists but user is not authorized"
                print(Fore.YELLOW + "[!] অ্যাসিস্ট্যান্ট সেশন অথোরাইজড নয়, একক বট মোডে চলবে।")
                assistant_client = None
        except Exception as e:
            service_status["assistant_error"] = str(e)
            print(Fore.YELLOW + f"[!] অ্যাসিস্ট্যান্ট ক্লায়েন্ট সতর্কতা: {e}")
            assistant_client = None
    else:
        service_status["assistant_error"] = "SESSION_STRING is empty or not provided"

    # ৪. ইঞ্জিন ইনিশিয়ালাইজ
    engine = MultiShieldEngine(
        assistant_client=assistant_client,
        scan_interval=config.SCAN_INTERVAL_SECONDS
    )

    print(Fore.WHITE + Style.BRIGHT + f"\n[🔥 সাকসেস!] @LiveShieldXBot এখন পুরোপুরি লাইভ ও সক্রিয়!")
    print(Fore.WHITE + f"[*] যে কোনো ইউজার বা বন্ধু বটে গিয়ে /start দিয়ে চ্যানেল সুরক্ষিত করতে পারবে।\n")

    # ৫. প্যারালালি ডিফেন্স ইঞ্জিন এবং Bot API পোলিং চালানো
    tasks = [run_bot_polling(engine)]
    if assistant_client:
        tasks.append(engine.start())
        tasks.append(assistant_client.run_until_disconnected())

    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        print(Fore.YELLOW + "\n[!] সিস্টেম বন্ধ করা হচ্ছে...")
    finally:
        if assistant_client:
            await engine.stop()
            await assistant_client.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
