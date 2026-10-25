"""
Database Module - Multi-User & Multi-Channel Storage
বটের মাধ্যমে যে কেউ যেকোনো চ্যানেল যুক্ত বা রিমুভ করার ডাটাবেজ
"""
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sentinel_guard.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """ডাটাবেজ টেবিল তৈরি করা"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # চ্যানেল টেবিল
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER UNIQUE NOT NULL,
                channel_title TEXT,
                channel_username TEXT,
                added_by_user_id INTEGER NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # আক্রমণ ও প্রতিরোধ লগ টেবিল
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attack_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER NOT NULL,
                recovery_time_ms INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (channel_id) REFERENCES channels (channel_id)
            )
        """)
        conn.commit()

def add_channel(channel_id, channel_title, channel_username, user_id):
    """নতুন চ্যানেল অ্যাড করা"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO channels (channel_id, channel_title, channel_username, added_by_user_id, is_active)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(channel_id) DO UPDATE SET
                channel_title = excluded.channel_title,
                channel_username = excluded.channel_username,
                is_active = 1
        """, (channel_id, channel_title, channel_username, user_id))
        conn.commit()
        return True

def remove_channel(channel_id, user_id=None):
    """চ্যানেল প্রোটেকশন থেকে সরানো"""
    with get_connection() as conn:
        cursor = conn.cursor()
        if user_id:
            cursor.execute("DELETE FROM channels WHERE channel_id = ? AND added_by_user_id = ?", (channel_id, user_id))
        else:
            cursor.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id,))
        conn.commit()
        return cursor.rowcount > 0

def get_active_channels():
    """পাহারায় থাকা সমস্ত চ্যানেল তালিকা"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM channels WHERE is_active = 1")
        return [dict(row) for row in cursor.fetchall()]

def get_user_channels(user_id):
    """নির্দিষ্ট ইউজারের প্রোটেক্টেড চ্যানেল তালিকা"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM channels WHERE added_by_user_id = ? AND is_active = 1", (user_id,))
        return [dict(row) for row in cursor.fetchall()]

def record_attack(channel_id, recovery_ms):
    """ডিডক্স প্রতিহত করার তথ্য সেভ করা"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO attack_logs (channel_id, recovery_time_ms)
            VALUES (?, ?)
        """, (channel_id, recovery_ms))
        conn.commit()

def get_stats():
    """সামগ্রিক ডিফেন্স পরিসংখ্যান"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total_attacks FROM attack_logs")
        total_attacks = cursor.fetchone()["total_attacks"]
        
        cursor.execute("SELECT COUNT(*) as total_channels FROM channels WHERE is_active = 1")
        total_channels = cursor.fetchone()["total_channels"]
        
        return {
            "total_attacks_blocked": total_attacks,
            "total_protected_channels": total_channels
        }
