#!/usr/bin/env python3
import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path="/root/EchoProPulse/discord_bot/.env")

BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
MAIN_CHANNEL = os.getenv("DISCORD_CHANNEL_ID")
LOG_CHANNEL = os.getenv("DISCORD_LOG_CHANNEL_ID")
VPS_CHANNEL = os.getenv("DISCORD_VPS_CHANNEL_ID")

HEADERS = {
    "Authorization": f"Bot {BOT_TOKEN}",
    "Content-Type": "application/json"
}

def post_message(channel_id: str, content: str):
    """Send a message to a specific Discord channel."""
    if not channel_id or not content:
        return False
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    payload = {"content": content}
    try:
        r = requests.post(url, headers=HEADERS, json=payload, timeout=10)
        if r.status_code not in [200, 204]:
            print(f"⚠️ Discord API returned {r.status_code}: {r.text}")
        else:
            print(f"✅ Sent message to {channel_id}: {content}")
        return r.ok
    except Exception as e:
        print(f"❌ Failed to post to Discord: {e}")
        return False


# ====== Channel-Specific Helpers ======

def notify_main(message: str):
    """Send general bot updates or alerts."""
    post_message(MAIN_CHANNEL, f"🚀 {message}")

def notify_logs(message: str):
    """Send system, backup, or watchdog updates."""
    post_message(LOG_CHANNEL, f"🪵 {message}")

def notify_vps(message: str):
    """Send VPS or cron job notifications."""
    post_message(VPS_CHANNEL, f"🖥️ {message}")
