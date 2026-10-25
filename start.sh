#!/usr/bin/env bash
# ========================================================
# Telegram Anti-DDoS Sentinel Guard Launcher
# ========================================================

cd "$(dirname "$0")"

echo "=========================================================="
echo "🛡️  Telegram Anti-DDoS Sentinel Guard - স্টার্টার স্ক্রিপ্ট"
echo "=========================================================="

# ভার্চুয়াল এনভায়রনমেন্ট চেক
if [ ! -d ".venv" ]; then
    echo "[*] ভার্চুয়াল এনভায়রনমেন্ট তৈরি করা হচ্ছে (.venv)..."
    python3 -m venv .venv
fi

# এনভায়রনমেন্ট সোর্স করা
source .venv/bin/activate

# ডিপেনডেন্সি চেক ও ইনস্টল
echo "[*] প্রয়োজনীয় লাইব্রেরি ইনস্টল/যাচাই করা হচ্ছে..."
pip install --quiet -r requirements.txt

# .env চেক
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "[!] .env ফাইল পাওয়া যায়নি। .env.example থেকে কপি তৈরি করা হচ্ছে..."
        cp .env.example .env
        echo "[*] .env তৈরি হয়েছে! দয়া করে ফাইলটিতে আপনার API তথ্য বসান।"
    fi
fi

# মূল ডিফেন্স ইঞ্জিন চালু করা
echo "[*] ডিফেন্স সেন্টিনেল ইঞ্জিন চালু করা হচ্ছে..."
python3 main.py
