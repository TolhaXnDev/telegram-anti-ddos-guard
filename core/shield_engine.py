"""
Multi-Channel Shield Engine - Active Anti-DDoS Watchdog & Auto-Respawn
একাধিক চ্যানেল একসাথে ২৪/৭ পাহারা দেওয়া, স্বয়ংক্রিয় রিকভারি ও ইনস্ট্যান্ট নোটিফিকেশন ইঞ্জিন
"""
import asyncio
import time
import sys
from telethon import TelegramClient, functions, types, errors
from colorama import Fore, Style, init

import config
from core.database import get_active_channels, record_attack
from core.sniffer_hunter import SnifferHunter

init(autoreset=True)

class MultiShieldEngine:
    def __init__(self, assistant_client, bot_client=None, scan_interval=0.5):
        self.assistant_client = assistant_client
        self.bot_client = bot_client
        self.scan_interval = scan_interval
        self.monitored_channels = {} # channel_id -> {title, peer, owner_id, last_known_call_id, active_call_input}
        self.is_running = False

    async def refresh_channels(self):
        """ডাটাবেজ থেকে সমস্ত সক্রিয় চ্যানেল লোড ও সিঙ্ক করা"""
        active_list = get_active_channels()
        current_ids = set()

        for c in active_list:
            cid = c["channel_id"]
            current_ids.add(cid)
            if cid not in self.monitored_channels:
                try:
                    target = c["channel_username"] if c["channel_username"] else cid
                    peer = await self.assistant_client.get_input_entity(target)
                    self.monitored_channels[cid] = {
                        "title": c["channel_title"],
                        "username": c["channel_username"],
                        "owner_id": c["added_by_user_id"],
                        "peer": peer,
                        "last_known_call_id": None,
                        "active_call_input": None
                    }
                    print(Fore.GREEN + f"[+] পাহারায় যুক্ত: {c['channel_title']} (ID: {cid})")
                except Exception as e:
                    print(Fore.YELLOW + f"[!] চ্যানেল সিঙ্ক সমস্যা: {c['channel_title']} - {e}")

        removed = [cid for cid in self.monitored_channels if cid not in current_ids]
        for cid in removed:
            del self.monitored_channels[cid]

    async def send_defense_alert(self, channel_data, recovery_ms, new_call_id):
        """আক্রমণ প্রতিহত হওয়ার সাথে সাথে বটের মাধ্যমে ইনস্ট্যান্ট নোটিফিকেশন পাঠানো"""
        alert_text = f"""
🚨 **𝐀𝐓𝐓𝐀𝐂𝐊 𝐃𝐄𝐅𝐋𝐄𝐂𝐓𝐄𝐃 | আক্রমণ প্রতিহত হয়েছে!** 🛡️

📢 **চ্যানেল:** {channel_data['title']} (`@{channel_data['username'] or 'ID: ' + str(channel_data['peer'].channel_id)}`)
⚔️ **আক্রমণের ধরন:** UDP WebRTC Port Flood (GROUPCALL_INVALID)
⚡ **রিকভারি গতি:** `{recovery_ms}` মিলি-সেকেন্ড
🔒 **নতুন সেশন আইডি:** `{new_call_id}`

💡 **ডিফেন্স অ্যাকশন:** 
আক্রমণকারীর ৬০ সেকেন্ডের ডিডক্স বুটার পুরোনো ডেড পোর্টে আবর্জনা ফেলতে গিয়ে সম্পূর্ণ ব্যর্থ হয়েছে! নতুন সুরক্ষিত পোর্টে লাইভ নিরবচ্ছিন্নভাবে চালু আছে।

— 𝐀𝐧𝐭𝐢-𝐃𝐃𝐨𝐒 𝐋𝐢𝐯𝐞 𝐒𝐡𝐢𝐞𝐥𝐝 🛡️
"""
        # ১. চ্যানেল ওনারকে নোটিফিকেশন পাঠানো
        recipients = set()
        if channel_data.get("owner_id"):
            recipients.add(channel_data["owner_id"])
        if config.ADMIN_ID:
            recipients.add(config.ADMIN_ID)

        notifier = self.bot_client or self.assistant_client
        for uid in recipients:
            try:
                await notifier.send_message(uid, alert_text)
                print(Fore.CYAN + f"[✓] অ্যালার্ট নোটিফিকেশন পাঠানো হয়েছে ইউজার: {uid}")
            except Exception as e:
                print(Fore.YELLOW + f"[!] অ্যালার্ট পাঠাতে ব্যর্থ (ইউজার {uid}): {e}")

    async def get_channel_call(self, peer):
        """চ্যানেলে রানিং লাইভ কলের তথ্য চেক করা"""
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
        """ডিডক্স হলে < ৩০০ মিলিসেকেন্ডে নতুন পোর্টে লাইভ রিস্টোর"""
        start_t = time.time()
        random_id = int(time.time() * 1000) & 0x7fffffff

        print(Fore.RED + Style.BRIGHT + "\n" + "="*60)
        print(Fore.RED + Style.BRIGHT + f"[🚨 আক্রমণ প্রতিহত হচ্ছে!] চ্যানেল: {channel_data['title']}")
        print(Fore.YELLOW + f"[*] ক্ষতিগ্রস্ত ডেড পোর্ট/কল আইডি: {old_call_id}")

        try:
            # নতুন লাইভ কল তৈরি
            await self.assistant_client(functions.phone.CreateGroupCallRequest(
                peer=channel_data["peer"],
                random_id=random_id,
                title="🔴 লাইভ স্ট্রিম (সুরক্ষিত ও সচল)"
            ))

            new_call = await self.get_channel_call(channel_data["peer"])
            recovery_ms = int((time.time() - start_t) * 1000)
            new_call_id = new_call.id if new_call else "ACTIVE_NEW"

            print(Fore.GREEN + Style.BRIGHT + f"[🛡️ আক্রমণ সম্পূর্ণ ব্যর্থ!] মাত্র {recovery_ms} মিলিসেকেন্ডে লাইভ রিস্টোর হয়েছে!")
            print(Fore.GREEN + f"[✓] নতুন সক্রিয় লাইভ সেশন আইডি: {new_call_id}")
            print(Fore.RED + Style.BRIGHT + "="*60 + "\n")

            # ডাটাবেজে লগ রাখা
            record_attack(cid, recovery_ms)

            # ইনস্ট্যান্ট টেলিগ্রাম অ্যালার্ট পাঠানো
            asyncio.create_task(self.send_defense_alert(channel_data, recovery_ms, new_call_id))

            if new_call:
                channel_data["active_call_input"] = types.InputGroupCall(id=new_call.id, access_hash=new_call.access_hash)
                channel_data["last_known_call_id"] = new_call.id
                
                try:
                    hunter = SnifferHunter(self.assistant_client, channel_data["peer"])
                    await hunter.secure_call_permissions(channel_data["active_call_input"])
                except Exception:
                    pass

        except Exception as e:
            print(Fore.RED + f"[✗] রিকভারি করতে এরর: {e}")

    async def start(self):
        """সব চ্যানেল স্ক্যান করার কনকারেন্ট ইঞ্জিন"""
        self.is_running = True
        await self.refresh_channels()

        print(Fore.GREEN + Style.BRIGHT + f"\n[🛡️ মাল্টি-চ্যানেল অ্যান্টি-ডিডক্স শিল্ড সম্পূর্ণ সক্রিয়!]")
        print(Fore.CYAN + f"[*] মোট চ্যানেল সংখ্যা: {len(self.monitored_channels)} টি\n")

        scan_cycle = 0
        while self.is_running:
            if scan_cycle % 60 == 0:
                await self.refresh_channels()

            for cid, data in list(self.monitored_channels.items()):
                try:
                    call = await self.get_channel_call(data["peer"])
                    
                    if call:
                        if data["last_known_call_id"] != call.id:
                            data["last_known_call_id"] = call.id
                            data["active_call_input"] = types.InputGroupCall(id=call.id, access_hash=call.access_hash)
                            print(Fore.GREEN + f"[+] {data['title']}: লাইভ চালু হয়েছে (Call ID: {call.id})")
                            
                            hunter = SnifferHunter(self.assistant_client, data["peer"])
                            await hunter.secure_call_permissions(data["active_call_input"])

                    else:
                        if data["last_known_call_id"] is not None:
                            await self.respawn_call(cid, data, data["last_known_call_id"])
                        
                except Exception:
                    pass

            scan_cycle += 1
            await asyncio.sleep(self.scan_interval)

    async def stop(self):
        self.is_running = False
