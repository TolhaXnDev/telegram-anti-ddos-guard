# MASTER PROMPT: TELEGRAM LIVE ANTI-DDOS SENTINEL SYSTEM

## Mission Objective
Defend Telegram Public Channel Live Streams from automated WebRTC UDP Port Flooding / Group Call termination attacks (`GROUPCALL_INVALID` RPC Error 400 triggered by DDoS Booters like `Kaal ☠️` targeting `DC_IP:PORT` for 60s).

## Core Defense Logic
1. **No Compromise on Public Accessibility:**
   - Channel stays 100% public.
   - No Join Requests or private group restrictions required.
2. **Sub-300ms Dynamic Port Rotation (Auto-Respawn):**
   - Booter attacks lock onto a single UDP port for a fixed duration (typically 60s).
   - High-frequency watchdog catches session drop within milliseconds.
   - Instantly issues `phone.CreateGroupCallRequest` with a new random entropy ID.
   - Telegram assigns a brand-new WebRTC SFU port and IP.
   - Attack packets land harmlessly on the dead port while the audience resumes playback immediately.
3. **Sniffer & Scraper Neutralization:**
   - Scans incoming Group Call participants.
   - Enforces `can_self_unmute = False` and strict listener restrictions to block unauthorized RTC packet injection.
4. **Resilience & Metric Logging:**
   - Records every deflection in JSON format for forensics and transparency.
