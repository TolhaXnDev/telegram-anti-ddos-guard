"""
Telegram Anti-DDoS Sentinel Guard - Configuration
"""
import os
import sys
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(env_path)

# টেলিগ্রাম এপিআই ইনফো (https://my.telegram.org থেকে)
API_ID = int(os.getenv("API_ID", "34336082"))
API_HASH = os.getenv("API_HASH", "5eed427426d9f7b8e952e18bfcc42ace")

# যে অ্যাকাউন্ট দিয়ে চ্যানেলের লাইভ সেশন রিরুট করা হবে
PHONE_NUMBER = os.getenv("PHONE_NUMBER", "+8801403208899")

# ক্লাউড ডিপ্লয়মেন্টের জন্য পার্মানেন্ট স্ট্রিং সেশন (Heroku / Koyeb / Render)
SESSION_STRING = os.getenv("SESSION_STRING", "")

# BotFather থেকে নেওয়া পাবলিক বট টোকেন (UI & নোটিফিকেশন)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8871001046:AAF4us1-ldRP6q6lqEezAGIeM0_EK6xLAYU")

# মাস্টার অ্যাডমিন ইউজার আইডি
ADMIN_ID = int(os.getenv("ADMIN_ID", "6048907312"))

# ডিফেন্স সেনসিটিভিটি ও সেটিংস
AUTO_RESPAWN_DELAY_MS = int(os.getenv("AUTO_RESPAWN_DELAY_MS", "300"))
ENABLE_SNIFFER_HUNTER = os.getenv("ENABLE_SNIFFER_HUNTER", "True").lower() == "true"
SCAN_INTERVAL_SECONDS = float(os.getenv("SCAN_INTERVAL_SECONDS", "0.5"))

# ডাটাবেজ ও লগ
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
ATTACK_LOG_FILE = os.path.join(LOG_DIR, "attack_defense_history.json")
