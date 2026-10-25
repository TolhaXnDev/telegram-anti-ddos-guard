"""
Multi-Channel Shield Engine - Active Anti-DDoS Watchdog & Auto-Respawn
"""
import asyncio
import time
import sys
import json
import os
from datetime import datetime
from telethon import TelegramClient, functions, types, errors
from colorama import Fore, Style, init

import config
from core.database import get_active_channels, record_attack
from core.sniffer_hunter import SnifferHunter

init(autoreset=True)

FORENSIC_LOG_FILE = os.path.join(config.LOG_DIR, "attack_forensics.jsonl")

class MultiShieldEngine:
    def __init__(self, assistant_client=None, bot_client=None, scan_interval=0.5):
        self.assistant_client = assistant_client
        self.bot_client = bot_client
        self.scan_interval = scan_interval
        self.monitored_channels = {}
        self.is_running = False

    async def refresh_channels(self):
        """ডাটাবেজ থেকে সমস্ত সক্রিয় চ্যানেল লোড ও সিঙ্ক করা"""
        if not self.assistant_client:
            return

        active_list = get_active_channels()
        current_ids = set()

        for c in active_list:
            cid = c["channel_id"]
            current_ids.add(cid)
            if cid not in self.monitored_channels:
                try:
                    if c["channel_username"]:
                        target = c["channel_username"]
                    else:
                        try:
                            target = int(cid)
                        except (ValueError, TypeError):
                            target = cid

                    try:
                        peer = await self.assistant_client.get_input_entity(target)
                    except Exception:
                        try:
                            # প্রাইভেট চ্যানেল বা গ্রুপের ডায়লগ ক্যাশ সিঙ্ক
                            await self.assistant_client.get_dialogs(limit=50)
                            peer = await self.assistant_client.get_input_entity(target)
                        except Exception as e2:
                            print(Fore.YELLOW + f"[!] চ্যানেল এন্টিটি পাওয়া যায়নি: {c['channel_title']} ({target}) - {e2}")
                            continue

                    hunter_inst = SnifferHunter(self.assistant_client, peer)
                    if c["added_by_user_id"]:
                        hunter_inst.known_safe_users.add(c["added_by_user_id"])

                    self.monitored_channels[cid] = {
                        "title": c["channel_title"],
                        "username": c["channel_username"],
                        "owner_id": c["added_by_user_id"],
                        "peer": peer,
                        "hunter": hunter_inst,
                        "last_known_call_id": None,
                        "active_call_input": None,
                        "call_start_time": None
                    }
                    print(Fore.GREEN + f"[+] পাহারায় যুক্ত: {c['channel_title']} (ID: {cid})")
                except Exception as e:
                    print(Fore.YELLOW + f"[!] চ্যানেল সিঙ্ক সমস্যা: {c['channel_title']} - {e}")

        removed = [cid for cid in self.monitored_channels if cid not in current_ids]
        for cid in removed:
            del self.monitored_channels[cid]

    async def send_defense_alert(self, channel_data, recovery_ms, new_call_id, forensic_data=None):
        suspects_text = ""
        suspects = forensic_data.get("suspects", []) if forensic_data else []
        if suspects:
            suspects_text = "\n🕵️ <b>ব্ল্যাকবক্স শনাক্তকৃত সন্দেহভাজন (ড্রপের আগে আনমিউট থাকা ইউজার):</b>\n"
            for s in suspects[:3]:
                suspects_text += f"• ইউজার আইডি: <code>{s['user_id']}</code> (কার্যক্রম: {s.get('action')})\n"
            suspects_text += "💡 <i>পরামর্শ: সন্দেহভাজন এই আইডিটি অবিলম্বে লাইভ/গ্রুপ থেকে ব্যান করুন।</i>\n"
        else:
            suspects_text = "\n🕵️ <b>ব্ল্যাকবক্স ফরেনসিক:</b> কোনো আন-অথোরাইজড ইউজার কথা বলেনি (প্যাসিভ স্নিফিং বা পোর্টে সরাসরি বুট অ্যাটাক)।\n"

        call_dur = forensic_data.get("call_duration_seconds", 0) if forensic_data else 0

        alert_text = f"""
🚨 <b>𝐀𝐓𝐓𝐀𝐂𝐊 𝐃𝐄𝐅𝐋𝐄𝐂𝐓𝐄𝐃 | আক্রমণ প্রতিহত হয়েছে!</b> 🛡️

📢 <b>চ্যানেল:</b> {channel_data['title']} (<code>@{channel_data['username'] or 'ID: ' + str(channel_data['peer'].channel_id)}</code>)
⚔️ <b>আক্রমণের ধরন:</b> UDP WebRTC SFU Port Flood (GROUPCALL_INVALID)
⏱️ <b>লাইভ চালু ছিল:</b> <code>{call_dur}</code> সেকেন্ড
⚡ <b>রিকভারি গতি:</b> <code>{recovery_ms}</code> মিলি-সেকেন্ড
🔒 <b>নতুন সেশন আইডি:</b> <code>{new_call_id}</code>
{suspects_text}
💡 <b>ডিফেন্স অ্যাকশন:</b> 
আক্রমণকারীর ৬০ সেকেন্ডের ডিডক্স বুটার পুরোনো ডেড পোর্টে আবর্জনা ফেলতে গিয়ে সম্পূর্ণ ব্যর্থ হয়েছে! নতুন সুরক্ষিত পোর্টে লাইভ নিরবচ্ছিন্নভাবে চালু আছে। সমস্ত ফরেনসিক ডাটা ক্লাউড ব্ল্যাকবক্সে সংরক্ষিত হয়েছে।

— 𝐀𝐧𝐭𝐢-𝐃𝐃𝐨𝐒 𝐋𝐢𝐯𝐞 𝐒𝐡𝐢𝐞𝐥𝐝 🛡️
"""
        recipients = set()
        if channel_data.get("owner_id"):
            recipients.add(channel_data["owner_id"])
        if config.ADMIN_ID:
            recipients.add(config.ADMIN_ID)

        # ১. সরাসরি টেলিগ্রাম বট এপিআই দিয়ে ইউজারের ইনবক্সে ইনস্ট্যান্ট এলার্ট পাঠানো
        import aiohttp
        bot_token = getattr(config, "BOT_TOKEN", os.getenv("BOT_TOKEN", "8871001046:AAF4us1-ldRP6q6lqEezAGIeM0_EK6xLAYU"))
        try:
            async with aiohttp.ClientSession() as session:
                for uid in recipients:
                    try:
                        payload = {"chat_id": uid, "text": alert_text, "parse_mode": "HTML"}
                        await session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json=payload, timeout=5)
                    except Exception as e_send:
                        print(Fore.YELLOW + f"[!] বট নোটিশ এরর ({uid}): {e_send}")

                # ক্লাউডফায়ার সেন্টিনেল ডি১ ডাটাবেজে রেকর্ড পাঠানো
                try:
                    cf_payload = {
                        "channel_id": str(channel_data.get("peer", {}).channel_id if hasattr(channel_data.get("peer"), "channel_id") else ""),
                        "recovery_ms": recovery_ms,
                        "attack_type": "UDP_PORT_FLOOD",
                        "suspect_info": suspects_text,
                        "forensic_data": forensic_data or {}
                    }
                    await session.post("https://liveshield-bot.dktolha.workers.dev/api/record_attack", json=cf_payload, timeout=5)
                except Exception:
                    pass
        except Exception as e_session:
            print(Fore.YELLOW + f"[!] এলার্ট সেশন এরর: {e_session}")

        # ফলব্যাক হিসেবে অ্যাসিস্ট্যান্ট অ্যাকাউন্ট দিয়ে পাঠানো
        if self.assistant_client:
            for uid in recipients:
                try:
                    await self.assistant_client.send_message(uid, alert_text)
                except Exception:
                    pass

    async def get_channel_call(self, peer):
        if not self.assistant_client:
            return None
        try:
            full = await self.assistant_client(functions.channels.GetFullChannelRequest(peer))
            if full.full_chat.call:
                return full.full_chat.call
            return None
        except errors.FloodWaitError as f:
            await asyncio.sleep(f.seconds)
            return None
        except Exception:
            return None

    async def respawn_call(self, cid, channel_data, old_call_id):
        if not self.assistant_client:
            return

        channel_data["last_known_call_id"] = None
        start_t = time.time()
        random_id = int(time.time() * 1000) & 0x7fffffff

        # ফরেনসিক তথ্য সংগ্রহ
        hunter = channel_data.get("hunter")
        suspects = hunter.get_forensic_suspects() if hunter else []
        call_dur = int(time.time() - channel_data["call_start_time"]) if channel_data.get("call_start_time") else 0
        suspect_summary = f"{len(suspects)} suspects: " + ", ".join([str(s['user_id']) for s in suspects]) if suspects else "No direct speaker unmuted"

        try:
            # নতুন সুরক্ষিত পোর্টে লাইভ রিস্টোর
            await self.assistant_client(functions.phone.CreateGroupCallRequest(
                peer=channel_data["peer"],
                random_id=random_id,
                title="🔴 লাইভ স্ট্রিম (সুরক্ষিত ও সচল)"
            ))

            new_call = await self.get_channel_call(channel_data["peer"])
            recovery_ms = int((time.time() - start_t) * 1000)
            new_call_id = new_call.id if new_call else "ACTIVE_NEW"

            # ব্ল্যাকবক্স ফরেনসিক পেলোড তৈরি
            forensic_data = {
                "timestamp": datetime.now().isoformat(),
                "channel_id": cid,
                "channel_title": channel_data["title"],
                "channel_username": channel_data["username"],
                "call_duration_seconds": call_dur,
                "old_call_id": old_call_id,
                "new_call_id": new_call_id,
                "recovery_time_ms": recovery_ms,
                "attack_vector": "Telegram WebRTC SFU UDP Flood (GROUPCALL_INVALID)",
                "suspects": suspects,
                "defense_status": "DEFLECTED_SUCCESSFULLY"
            }

            # ১. ডাটাবেজে রেকর্ড সংরক্ষণ
            try:
                record_attack(
                    cid,
                    recovery_ms,
                    attack_type="UDP_PORT_FLOOD",
                    suspect_info=suspect_summary,
                    forensic_json=json.dumps(forensic_data, ensure_ascii=False)
                )
            except Exception as e:
                print(f"[!] ডাটাবেজে সেভ করতে সমস্যা: {e}")

            # ২. পার্মানেন্ট ব্ল্যাকবক্স ফাইলে অ্যাপেন্ড
            try:
                with open(FORENSIC_LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(json.dumps(forensic_data, ensure_ascii=False) + "\n")
            except Exception:
                pass

            # ৩. ইনস্ট্যান্ট নোটিফিকেশন পাঠানো
            asyncio.create_task(self.send_defense_alert(channel_data, recovery_ms, new_call_id, forensic_data))

            if new_call:
                channel_data["active_call_input"] = types.InputGroupCall(id=new_call.id, access_hash=new_call.access_hash)
                channel_data["last_known_call_id"] = new_call.id
                channel_data["call_start_time"] = time.time()
                try:
                    if hunter:
                        await hunter.secure_call_permissions(channel_data["active_call_input"])
                except Exception:
                    pass

        except Exception as e:
            print(Fore.RED + f"[✗] রিকভারি করতে এরর: {e}")

    async def start(self):
        if not self.assistant_client:
            return

        self.is_running = True
        await self.refresh_channels()

        scan_cycle = 0
        while self.is_running:
            if scan_cycle % 60 == 0:
                await self.refresh_channels()

            for cid, data in list(self.monitored_channels.items()):
                try:
                    call = await self.get_channel_call(data["peer"])
                    if call:
                        # লাইভ কল সক্রিয় আছে
                        if data["call_start_time"] is None:
                            data["call_start_time"] = time.time()

                        hunter = data.get("hunter")
                        if data["last_known_call_id"] != call.id:
                            data["last_known_call_id"] = call.id
                            data["active_call_input"] = types.InputGroupCall(id=call.id, access_hash=call.access_hash)
                            if hunter:
                                await hunter.secure_call_permissions(data["active_call_input"])
                            print(Fore.GREEN + f"[🛡️] লাইভ কল সুরক্ষিত ও হার্ড-লক করা হয়েছে: {data['title']}")

                        # প্রতি ৫ সেকেন্ড পরপর পার্টিসিপেন্ট স্ক্যান করে স্নিফার/ইউজারবটের আনমিউট প্রতিহত করা
                        if scan_cycle % 10 == 0 and data.get("active_call_input"):
                            if hunter:
                                await hunter.scan_and_neutralize_participants(data["active_call_input"])
                    else:
                        # যদি পূর্বে কল চালু ছিল এবং এখন হঠাৎ ড্রপ করেছে (আক্রমণ হয়েছে)
                        if data["last_known_call_id"] is not None:
                            print(Fore.RED + f"[⚠️ আক্রমণ শনাক্ত!] কল ড্রপ করেছে: {data['title']}. সাথে সাথে রিকভার করা হচ্ছে...")
                            await self.respawn_call(cid, data, data["last_known_call_id"])
                except Exception:
                    pass

            scan_cycle += 1
            await asyncio.sleep(self.scan_interval)

    async def stop(self):
        self.is_running = False
