#!/usr/bin/env python3
"""
EchoProPulse Token & System Watchdog v3.5
- Token verification + restart on failure
- Disk usage threshold alerts + auto-clean
- Daily All-Systems-Green report (8 AM ET)
- Bot inactive/failed restart logic
- Reduced heartbeat spam (once per cron)
"""

import os
import json
import shutil
import socket
import random
import time
import requests
import subprocess
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from discord_notify import notify_logs, notify_vps

# -------------------------------------------------------------------
# CONFIG / ENV
# -------------------------------------------------------------------
load_dotenv(dotenv_path="/root/EchoProPulse/discord_bot/.env")

BOT_TOKEN     = os.getenv("DISCORD_BOT_TOKEN")
SERVICE_NAME  = "echopropulse.service"
CHECK_URL     = "https://discord.com/api/v10/users/@me"
TZ_NY         = ZoneInfo("America/New_York")
WATCHDOG_LOG  = "/root/EchoProPulse/discord_bot/watchdog.log"
CLEAN_SCRIPT  = "/root/EchoProPulse/discord_bot/cleanup_echo.sh"
DISK_ALERT_THRESHOLD = int(os.getenv("DISK_ALERT_THRESHOLD", "85"))

# -------------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------------
def ny_now():
    return datetime.now(tz=TZ_NY)

def restart_service(reason="Unknown"):
    try:
        subprocess.run(["systemctl", "restart", SERVICE_NAME], check=False)
        notify_logs(f"🔁 **Auto-Restart Triggered** — Reason: {reason}")
    except Exception as e:
        notify_logs(f"❌ **Restart Failed:** {e}")

def get_service_state():
    try:
        out = subprocess.check_output(["systemctl", "is-active", SERVICE_NAME], text=True).strip()
        return out
    except Exception:
        return "unknown"

def read_disk():
    try:
        total, used, free = shutil.disk_usage("/")
        pct = int(used * 100 / total) if total else 0
        def human(bytes_):
            for unit in ("B","KB","MB","GB","TB"):
                if bytes_ < 1024:
                    return f"{bytes_:.1f}{unit}"
                bytes_ /= 1024
        return f"{human(used)}/{human(total)} ({pct}%)", pct
    except Exception:
        return "Unknown", 0

def auto_clean_if_needed():
    """Run cleanup script when disk usage > threshold."""
    disk_str, disk_pct = read_disk()
    if disk_pct < DISK_ALERT_THRESHOLD:
        return

    notify_logs(f"🚨 Disk at **{disk_pct}%**, initiating auto-clean via cleanup_echo.sh…")
    before = disk_str
    try:
        if os.path.exists(CLEAN_SCRIPT):
            subprocess.run(["bash", CLEAN_SCRIPT], check=False)
            time.sleep(5)
        after, after_pct = read_disk()
        notify_logs(
            f"🧹 **Auto-Clean Complete**\nBefore: `{before}`\nAfter: `{after}`\n"
            f"Freeed: ~{max(0, disk_pct - after_pct)}%"
        )
    except Exception as e:
        notify_logs(f"❌ Auto-clean failed: {e}")

def check_token():
    headers = {"Authorization": f"Bot {BOT_TOKEN}"}
    try:
        r = requests.get(CHECK_URL, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            notify_vps(
                f"🟢 Token OK • Connected as **{data.get('username')}#{data.get('discriminator')}** "
                f"at {ny_now():%I:%M %p %Z}"
            )
            return True
        else:
            restart_service(f"Invalid token ({r.status_code})")
            return False
    except Exception as e:
        restart_service(f"Token check error: {e}")
        return False

def post_daily_summary():
    now = ny_now()
    load1, load5, load15 = os.getloadavg()
    disk_str, _ = read_disk()
    msg = (
        f"🟢 **All Systems Green — Daily Status**\n"
        f"📅 {now:%A, %B %d, %Y}\n"
        f"🕗 {now:%I:%M %p %Z}\n"
        f"📊 CPU Load: `{load1:.2f} {load5:.2f} {load15:.2f}`\n"
        f"💽 Disk: `{disk_str}`\n"
        f"🤖 Service State: `{get_service_state()}`\n"
        f"✅ Token verified\n"
        f"🪵 Log: `{WATCHDOG_LOG}`\n"
        f"— EchoProPulse Watchdog v3.5"
    )
    notify_logs(msg)

# -------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------
if __name__ == "__main__":
    # Stagger to avoid same-second floods
    time.sleep(random.randint(0, 60))

    state = get_service_state()
    if state not in ("active", "activating"):
        restart_service(f"Service state {state}")

    check_token()
    auto_clean_if_needed()

    now_ny = ny_now()
    if now_ny.hour == 8 and now_ny.minute < 10:
        post_daily_summary()
