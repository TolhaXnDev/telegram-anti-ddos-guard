"""
Sniffer & Userbot Hunter Module
পাবলিক লাইভ থেকে আক্রমণকারীদের স্নিফার স্ক্রিপ্ট ও ইউজারবট চিহ্নিতকরণ ও দমন
"""
import asyncio
from telethon import functions, types

class SnifferHunter:
    def __init__(self, client, channel_peer):
        self.client = client
        self.channel_peer = channel_peer
        self.known_safe_users = set()
        self.banned_scrapers = set()

    async def secure_call_permissions(self, call_input):
        """
        লাইভ চ্যাটের স্পিকার পারমিশন হার্ড-লক করা।
        সাধারণ কোনো ইউজার বা আক্রমণকারীর স্ক্রিপ্ট যাতে নিজেকে আনমিউট বা প্যাকেট ইনজেক্ট করতে না পারে।
        """
        try:
            # শুধুমাত্র অ্যাডমিনরা কথা বলতে পারবে - সাধারণ কেউ আনমিউট হতে পারবে না
            await self.client(functions.phone.ToggleGroupCallSettingsRequest(
                call=call_input,
                reset_invite_hash=False,
                join_muted=True # সবাই মিউট অবস্থায় থাকবে
            ))
            return True
        except Exception as e:
            return False

    async def scan_and_neutralize_participants(self, call_input):
        """
        লাইভের পার্টিসিপেন্ট তালিকা স্ক্যান করে কোনো ক্ষতিকর ইউজারবট বা স্নিফার আছে কিনা চেক করা।
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
                user_id = p.peer.user_id if hasattr(p.peer, "user_id") else None
                if not user_id or user_id in self.known_safe_users:
                    continue

                # চেক করা: কোনো আন-অথোরাইজড ইউজার কথা বলার চেষ্টা করছে কিনা
                if p.can_self_unmute:
                    try:
                        # অবিলম্বে স্পিক পারমিশন বাতিল করা
                        await self.client(functions.phone.EditGroupCallParticipantRequest(
                            call=call_input,
                            participant=p.peer,
                            muted=True
                        ))
                    except Exception:
                        pass

        except Exception as e:
            pass

        return suspicious_found
