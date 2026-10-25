"""
Attack & Defense Statistics Tracker
"""
import json
import os
import time
from datetime import datetime

class StatsTracker:
    def __init__(self, log_file_path):
        self.log_file_path = log_file_path
        self.attacks_blocked = 0
        self.total_scans = 0
        self.last_attack_time = None
        self.start_time = time.time()
        self.history = []
        self._load_history()

    def _load_history(self):
        if os.path.exists(self.log_file_path):
            try:
                with open(self.log_file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.attacks_blocked = data.get("total_attacks_blocked", 0)
                    self.history = data.get("history", [])
            except Exception:
                self.history = []

    def record_attack_neutralized(self, duration_ms, old_call_id, new_call_id):
        self.attacks_blocked += 1
        self.last_attack_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = {
            "timestamp": self.last_attack_time,
            "attack_type": "UDP WebRTC Port Flood (GROUPCALL_INVALID)",
            "recovery_time_ms": duration_ms,
            "old_call_id": str(old_call_id),
            "new_call_id": str(new_call_id),
            "status": "NEUTRALIZED_AND_RESTORED"
        }
        self.history.append(entry)
        self._save()

    def _save(self):
        data = {
            "total_attacks_blocked": self.attacks_blocked,
            "last_attack_time": self.last_attack_time,
            "system_uptime_seconds": int(time.time() - self.start_time),
            "history": self.history[-100:] # শেষ ১০০টি হিস্ট্রি রাখা
        }
        try:
            with open(self.log_file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[!] লগ সেভ করতে সমস্যা: {e}")

    def get_summary(self):
        uptime = int(time.time() - self.start_time)
        hours, rem = divmod(uptime, 3600)
        minutes, seconds = divmod(rem, 60)
        return {
            "attacks_blocked": self.attacks_blocked,
            "uptime_str": f"{hours:02d}h:{minutes:02d}m:{seconds:02d}s",
            "last_attack": self.last_attack_time or "কোনো আক্রমণ রেকর্ড হয়নি"
        }
