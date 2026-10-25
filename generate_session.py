"""
Telegram String Session Generator for Cloud (Heroku, Koyeb, Render, VPS)
ক্লাউডে বট চালানোর জন্য স্থায়ী স্ট্রিং সেশন জেনারেটর
"""
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = 34336082
API_HASH = "5eed427426d9f7b8e952e18bfcc42ace"

async def main():
    print("=" * 60)
    print("🔑 TELEGRAM STRING SESSION GENERATOR (HEROKU & CLOUD READY)")
    print("=" * 60)
    print("টেলিগ্রাম থেকে পাঠানো ওটিপি কোডটি দিলে এটি একটি সেশন স্ট্রিং তৈরি করে দেবে।")
    print("এই স্ট্রিংটি ক্লাউড এনভায়রনমেন্টে বসিয়ে দিলে আর কখনো ওটিপি চাবে না।\n")

    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.start()
    
    session_str = client.session.save()
    print("\n" + "=" * 60)
    print("🎉 আপনার ক্লাউড স্ট্রিং সেশন সফলভাবে তৈরি হয়েছে:")
    print("=" * 60)
    print(session_str)
    print("=" * 60)
    print("\n💡 এই লম্বা কোডটি কপি করে হিরোকু বা ক্লাউডের 'SESSION_STRING' এ বসিয়ে দিন।\n")
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
