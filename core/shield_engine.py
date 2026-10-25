"""
Multi-Channel Shield Engine - Active Anti-DDoS Watchdog & Auto-Respawn
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
        alert_text = f"""
🚨 <b>𝐀𝐓𝐓𝐀𝐂𝐊 𝐃𝐄𝐅𝐋𝐄𝐂𝐓𝐄𝐃 | আক্রমণ প্রতিহত হয়েছে!</b> 🛡️

📢 <b>চ্যানেল:</b> {channel_data['title']} (<code>@{channel_data['username'] or 'ID: ' + str(channel_data['peer'].channel_id)}</code>)
⚔️ <b>আক্রমণের ধরন:</b> UDP WebRTC Port Flood (GROUPCALL_INVALID)
⚡ <b>রিকভারি গতি:</b> <code>{recovery_ms}</code> মিলি-সেকেন্ড
🔒 <b>নতুন সেশন আইডি:</b> <code>{new_call_id}</code>

💡 <b>ডিফেন্স অ্যাকশন:</b> 
আক্রমণকারীর ৬০ সেকেন্ডের ডিডক্স বুটার পুরোনো ডেড পোর্টে আবর্জনা ফেলতে গিয়ে সম্পূর্ণ ব্যর্থ হয়েছে! নতুন সুরক্ষিত পোর্টে লাইভ নিরবচ্ছিন্নভাবে চালু আছে।

— 𝐀𝐧𝐭𝐢-𝐃𝐃𝐨𝐒 𝐋𝐢𝐯𝐞 𝐒𝐡𝐢𝐞𝐥𝐝 🛡️
"""
        recipients = set()
        if channel_data.get("owner_id"):
            recipients.add(channel_data["owner_id"])
        if config.ADMIN_ID:
            recipients.add(config.ADMIN_ID)

        notifier = self.bot_client or self.assistant_client
        if notifier:
            for uid in recipients:
                try:
                    await notifier.send_message(uid, alert_text)
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

        start_t = time.time()
        random_id = int(time.time() * 1000) & 0x7fffffff

        try:
            await self.assistant_client(functions.phone.CreateGroupCallRequest(
                peer=channel_data["peer"],
                random_id=random_id,
                title="🔴 লাইভ স্ট্রিম (সুরক্ষিত ও সচল)"
            ))

            new_call = await self.get_channel_call(channel_data["peer"])
            recovery_ms = int((time.time() - start_t) * 1000)
            new_call_id = new_call.id if new_call else "ACTIVE_NEW"

            record_attack(cid, recovery_ms)
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
                        if data["last_known_call_id"] != call.id:
                            data["last_known_call_id"] = call.id
                            data["active_call_input"] = types.InputGroupCall(id=call.id, access_hash=call.access_hash)
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
