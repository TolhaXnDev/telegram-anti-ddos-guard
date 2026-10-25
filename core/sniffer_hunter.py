"""
Sniffer & Userbot Hunter Module
পাবলিক লাইভ থেকে আক্রমণকারীদের স্নিফার স্ক্রিপ্ট ও ইউজারবট চিহ্নিতকরণ ও দমন
"""
import asyncio
from telethon import functions, types
import config

class SnifferHunter:
    def __init__(self, client, channel_peer):
        self.client = client
        self.channel_peer = channel_peer
        self.known_safe_users = {config.ADMIN_ID}
        self.banned_scrapers = set()

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
        যদি কোনো আন-অথোরাইজড ইউজার নিজেকে আনমিউট করার চেষ্টা করে, তাকে সাথে সাথে ফোর্স-মিউট করা হবে।
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

            for p in result.participants:
                user_id = getattr(p.peer, "user_id", None)
                if not user_id or user_id in self.known_safe_users:
                    continue

                # চেক করা: কোনো আন-অথোরাইজড ইউজার কথা বলা বা আনমিউট অবস্থায় আছে কিনা
                can_speak = getattr(p, "can_self_unmute", False)
                is_unmuted = not getattr(p, "muted", True)

                if can_speak or is_unmuted:
                    try:
                        # সাথে সাথে তার স্পিক পারমিশন বাতিল ও ফোর্স মিউট করা
                        await self.client(functions.phone.EditGroupCallParticipantRequest(
                            call=call_input,
                            participant=p.peer,
                            muted=True
                        ))
                        suspicious_found.append(user_id)
                    except Exception:
                        pass

        except Exception:
            pass

        return suspicious_found
