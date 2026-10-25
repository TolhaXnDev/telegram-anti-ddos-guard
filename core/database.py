"""
Database Module - Multi-User, Channel Management & Admin Storage
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
    """ডাটাবেজ টেবিল তৈরি ও আপডেট করা"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # ইউজার টেবিল
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                username TEXT,
                is_banned INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

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
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

# --- ইউজার ম্যানেজমেন্ট ---
def register_user(user_id, first_name, username):
    """ইউজার রেজিস্টার বা তথ্য আপডেট করা"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (user_id, first_name, username)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                first_name = excluded.first_name,
                username = excluded.username
        """, (user_id, first_name, username))
        conn.commit()

def is_user_banned(user_id):
    """ইউজার ব্যান কিনা যাচাই করা"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return bool(row["is_banned"]) if row else False

def ban_user(user_id):
    """ইউজার ব্যান করা"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0

def unban_user(user_id):
    """ইউজার আনব্যান করা"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0

def get_all_users():
    """সমস্ত বট ইউজারের তালিকা (ব্রডকাস্টের জন্য)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE is_banned = 0")
        return [dict(row) for row in cursor.fetchall()]

def get_users_count():
    """মোট ইউজারের সংখ্যা"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM users")
        return cursor.fetchone()["total"]

# --- চ্যানেল ম্যানেজমেন্ট ---
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
    """চ্যানেল সরানো"""
    with get_connection() as conn:
        cursor = conn.cursor()
        if user_id:
            cursor.execute("DELETE FROM channels WHERE channel_id = ? AND added_by_user_id = ?", (channel_id, user_id))
        else:
            cursor.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id,))
        conn.commit()
        return cursor.rowcount > 0

def get_active_channels():
    """পাহারায় থাকা সমস্ত চ্যানেল"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM channels WHERE is_active = 1")
        return [dict(row) for row in cursor.fetchall()]

def get_user_channels(user_id):
    """নির্দিষ্ট ইউজারের চ্যানেল"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM channels WHERE added_by_user_id = ? AND is_active = 1", (user_id,))
        return [dict(row) for row in cursor.fetchall()]

# --- আক্রমণ ও পরিসংখ্যান ---
def record_attack(channel_id, recovery_ms):
    """ডিডক্স আক্রমণ সফলভাবে প্রতিহত করার তথ্য সংরক্ষণ"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO attack_logs (channel_id, recovery_time_ms)
            VALUES (?, ?)
        """, (channel_id, recovery_ms))
        conn.commit()

def get_recent_attacks(limit=5):
    """সাম্প্রতিক প্রতিহত হওয়া আক্রমণের তালিকা"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.*, c.channel_title, c.channel_username 
            FROM attack_logs a 
            LEFT JOIN channels c ON a.channel_id = c.channel_id 
            ORDER BY a.id DESC LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]

def get_stats():
    """সামগ্রিক পরিসংখ্যান"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total_attacks FROM attack_logs")
        total_attacks = cursor.fetchone()["total_attacks"]
        
        cursor.execute("SELECT COUNT(*) as total_channels FROM channels WHERE is_active = 1")
        total_channels = cursor.fetchone()["total_channels"]
        
        cursor.execute("SELECT COUNT(*) as total_users FROM users")
        total_users = cursor.fetchone()["total_users"]
        
        return {
            "total_attacks_blocked": total_attacks,
            "total_protected_channels": total_channels,
            "total_users": total_users
        }
