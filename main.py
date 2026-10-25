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
import aiohttp
from core.database import init_db, get_stats, get_recent_forensics, add_channel
from core.shield_engine import MultiShieldEngine

init(autoreset=True)

# গ্লোবাল স্ট্যাটাস ট্র্যাকার ও ইঞ্জিন রেফারেন্স
engine_ref = None
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
║  {Fore.YELLOW}ক্লাউডফায়ার এজ + রেন্ডার ডুয়াল ব্যাকএন্ড | সার্বক্ষণিক লাইভ সুরক্ষা  {Fore.RED}║
╚══════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
    print(banner)

async def handle_health(request):
    """Render হেলথচেক পোর্ট (২৪/৭ সজাগ রাখার জন্য ও লাইভ স্ট্যাটাস মনিটরিং)"""
    stats = get_stats()
    return web.json_response({
        "status": "online",
        "shield": "active",
        "platform": "Render MTProto Sentinel + Cloudflare Workers Edge",
        "assistant_connected": service_status["assistant_connected"],
        "assistant_name": service_status["assistant_name"],
        "assistant_id": service_status["assistant_id"],
        "assistant_error": service_status["assistant_error"],
        "bot": "@LiveShieldXBot",
        "protected_channels": stats["total_protected_channels"],
        "attacks_blocked": stats["total_attacks_blocked"]
    })

async def handle_forensics(request):
    """ব্ল্যাকবক্স ফরেনসিক অডিট এন্ডপয়েন্ট (আক্রমণ ও সন্দেহভাজনদের ইতিহাস)"""
    logs = get_recent_forensics(limit=25)
    return web.json_response({
        "status": "ok",
        "total_forensic_records": len(logs),
        "forensics": logs
    })

async def handle_register_channel(request):
    """ক্লাউডফায়ার এজ ওয়ার্কার থেকে ইনস্ট্যান্ট চ্যানেল রেজিস্ট্রেশন হ্যান্ডলার"""
    try:
        data = await request.json()
        cid = data.get("channel_id")
        title = data.get("title", "")
        username = data.get("username", "")
        added_by = data.get("added_by", config.ADMIN_ID)
        if cid:
            add_channel(cid, title, username, added_by)
            if engine_ref:
                await engine_ref.refresh_channels()
            print(Fore.GREEN + f"[+] ক্লাউডফায়ার থেকে চ্যানেল সিঙ্ক: {title} ({cid})")
        return web.json_response({"ok": True, "registered": cid})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=400)

async def start_keepalive_server():
    """রেন্ডারের ফ্রি সার্ভারকে ঘুম থেকে বিরত রাখার ওয়েব পোর্ট"""
    port = int(os.getenv("PORT", "10000"))
    app = web.Application()
    app.router.add_get("/", handle_health)
    app.router.add_get("/health", handle_health)
    app.router.add_get("/forensics", handle_forensics)
    app.router.add_post("/api/register_channel", handle_register_channel)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(Fore.GREEN + f"[✓] ক্লাউড কিপ-অ্যালাইভ ওয়েব পোর্ট সক্রিয়: পোর্ট {port}")

async def sync_cloudflare_channels(engine):
    """ক্লাউডফায়ার ডি১ ডাটাবেজ থেকে স্বয়ংক্রিয় চ্যানেল সিঙ্ক লুপ"""
    cf_url = "https://liveshield-bot.dktolha.workers.dev/api/channels"
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(cf_url, timeout=10) as resp:
                    if resp.status == 200:
                        chans = await resp.json()
                        for c in chans:
                            add_channel(
                                c["channel_id"],
                                c.get("channel_title", ""),
                                c.get("channel_username", ""),
                                c.get("added_by_user_id", config.ADMIN_ID)
                            )
                        await engine.refresh_channels()
            except Exception:
                pass
            await asyncio.sleep(20)

async def main():
    global engine_ref
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
    engine_ref = engine

    print(Fore.WHITE + Style.BRIGHT + f"\n[🔥 সাকসেস!] @LiveShieldXBot ক্লাউডফায়ার এজ + রেন্ডার ডুয়াল আর্কিটেকচারে সম্পূর্ণ সক্রিয়!")
    print(Fore.WHITE + f"[*] সমস্ত বট মেসেজ ও কমান্ড ক্লাউডফায়ার এজ থেকে আগুনের গতিতে (<10ms) চলছে।\n")

    # ৫. সেন্টিনেল ডিফেন্স ইঞ্জিন এবং ক্লাউডফায়ার সিঙ্ক লুপ চালানো
    tasks = [sync_cloudflare_channels(engine)]
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
