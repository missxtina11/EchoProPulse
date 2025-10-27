#!/usr/bin/env python3
# ============================================================
# 📡 Discord Notification Helper — EchoProPulse Edition
# Posts structured messages to MAIN, LOGS, and VPS channels.
# ============================================================
import os
import requests
from dotenv import load_dotenv
from datetime import datetime

# --- Load environment
load_dotenv(dotenv_path="/root/EchoProPulse/discord_bot/.env")

BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
MAIN_CHANNEL = os.getenv("DISCORD_CHANNEL_ID")
LOG_CHANNEL = os.getenv("DISCORD_LOG_CHANNEL_ID")
VPS_CHANNEL = os.getenv("DISCORD_VPS_CHANNEL_ID")

# --- Shared request headers
HEADERS = {
    "Authorization": f"Bot {BOT_TOKEN}",
    "Content-Type": "application/json"
}

# ============================================================
# 🔗 Universal Helper
# ============================================================
def post_message(channel_id: str, content: str):
    """Send a message to a specific Discord channel."""
    if not channel_id or not content:
        print("[WARN] Missing channel ID or content.")
        return False

    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    payload = {"content": content}

    try:
        response = requests.post(url, headers=HEADERS, json=payload)
        if response.status_code not in (200, 204):
            print(f"⚠️ Discord API returned {response.status_code}: {response.text}")
        else:
            print(f"✅ Sent message to {channel_id}: {content[:80]}...")
        return response.ok
    except Exception as e:
        print(f"❌ Failed to post to Discord: {e}")
        return False

# ============================================================
# 📢 Channel-Specific Helpers
# ============================================================

def notify_main(message: str):
    """Send general bot updates or alerts."""
    post_message(MAIN_CHANNEL, f"🚀 {message}")

def notify_logs(message: str):
    """Send system, backup, or watchdog updates."""
    post_message(LOG_CHANNEL, f"🪵 {message}")

def notify_vps(message: str):
    """Send VPS or cron job notifications."""
    post_message(VPS_CHANNEL, f"🖥️ {message}")

# ============================================================
# 🧩 Optional Debug Helper (for testing)
# ============================================================
def notify_debug(message: str):
    now = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    post_message(LOG_CHANNEL, f"🧠 [DEBUG {now}] {message}")
