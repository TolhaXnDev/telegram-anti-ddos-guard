"""
Sniffer & Userbot Hunter Module
পাবলিক লাইভ থেকে আক্রমণকারীদের স্নিফার স্ক্রিপ্ট ও ইউজারবট চিহ্নিতকরণ ও দমন
"""
import asyncio
import time
from telethon import functions, types
import config

class SnifferHunter:
    def __init__(self, client, channel_peer):
        self.client = client
        self.channel_peer = channel_peer
        self.known_safe_users = {config.ADMIN_ID}
        self.banned_scrapers = set()
        self.recent_speakers = [] # [(user_id, timestamp, details)]
        self.last_participants = []

    async def secure_call_permissions(self, call_input):
        """
        লাইভ চ্যাটের স্পিকার পারমিশন হার্ড-লক করা।
        সাধারণ কোনো ইউজার বা আক্রমণকারীর স্ক্রিপ্ট যাতে নিজেকে আনমিউট বা আইপি স্নিফিং করতে না পারে।
        """
        try:
            # শুধুমাত্র অ্যাডমিনরা কথা বলতে পারবে - সাধারণ কেউ সরাসরি আনমিউট হতে পারবে না
            await self.client(functions.phone.ToggleGroupCallSettingsRequest(
                call=call_input,
                reset_invite_hash=False,
                join_muted=True # যোগদানকারী সবাই স্বয়ংক্রিয়ভাবে মিউট থাকবে
            ))
            return True
        except Exception:
            return False

    async def scan_and_neutralize_participants(self, call_input):
        """
        লাইভের পার্টিসিপেন্ট তালিকা স্ক্যান করে কোনো আক্রমণকারী বা স্নিফার আনমিউট হয়েছে কিনা চেক করা।
        যদি কোনো আন-অথোরাইজড ইউজার নিজেকে আনমিউট করার চেষ্টা করে, তাকে সাথে সাথে ফোর্স-মিউট করা হবে
        এবং ফরেনসিক রেকর্ডের জন্য তার আইডি ব্ল্যাকবক্সে সেভ করা হবে।
        """
        suspicious_found = []
        try:
            result = await self.client(functions.phone.GetGroupCallParticipantsRequest(
                call=call_input,
                ids=[],
                sources=[],
                offset="",
                limit=100
            ))

            current_time = time.time()
            self.last_participants = []

            for p in result.participants:
                user_id = getattr(p.peer, "user_id", None)
                if not user_id:
                    continue

                can_speak = getattr(p, "can_self_unmute", False)
                is_unmuted = not getattr(p, "muted", True)
                
                self.last_participants.append({
                    "user_id": user_id,
                    "muted": getattr(p, "muted", True),
                    "can_speak": can_speak
                })

                if user_id in self.known_safe_users:
                    continue

                # যদি কোনো আন-অথোরাইজড ইউজার কথা বলা বা আনমিউট অবস্থায় থাকে
                if can_speak or is_unmuted:
                    try:
                        # সাথে সাথে তার স্পিক পারমিশন বাতিল ও ফোর্স মিউট করা
                        await self.client(functions.phone.EditGroupCallParticipantRequest(
                            call=call_input,
                            participant=p.peer,
                            muted=True
                        ))
                    except Exception:
                        pass

                    # ফরেনসিক ব্ল্যাকবক্সে সন্দেহভাজন হিসেবে রেকর্ড রাখা
                    suspect_entry = {
                        "user_id": user_id,
                        "time": current_time,
                        "action": "unmuted_speaker" if is_unmuted else "speaker_permission_attempt"
                    }
                    suspicious_found.append(user_id)
                    self.recent_speakers.append(suspect_entry)

            # পুরোনো রেকর্ড পরিষ্কার (শেষ ৩ মিনিটের ডাটা রাখা)
            self.recent_speakers = [s for s in self.recent_speakers if current_time - s["time"] < 180]

        except Exception:
            pass

        return suspicious_found

    def get_forensic_suspects(self):
        """ক্র্যাশের ঠিক আগের সন্দেহভাজনদের তালিকা রিটার্ন করা"""
        current_time = time.time()
        # শেষ ২ মিনিটের মধ্যে যারা আনমিউট ছিল
        suspects = [s for s in self.recent_speakers if current_time - s["time"] < 120]
        # ইউনিক ইউজার আইডি বের করা
        seen = set()
        unique_suspects = []
        for s in reversed(suspects):
            if s["user_id"] not in seen:
                seen.add(s["user_id"])
                unique_suspects.append(s)
        return unique_suspects
