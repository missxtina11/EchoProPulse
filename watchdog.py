#!/usr/bin/env python3
import os
import time
import requests
import subprocess
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# ==========================================================
# CONFIGURATION
# ==========================================================
HEARTBEAT_FILE = "/root/EchoProPulse/discord_bot/heartbeat.log"
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://discord.com/api/webhooks/1431637669393338542/zsl56oNcZ2ZLDqkM50afBrKZxZxFCz7huu2dIXbHZGOWZ15n2rGX6Gir22-vxOsqo5yA")
SERVICE_NAME = "echopropulse.service"

TIMEZONE = ZoneInfo("America/New_York")
CHECK_INTERVAL = 3600        # check every 60 minutes
MAX_IDLE_MINUTES = 150       # if no heartbeat in >150 mins, restart
COOLDOWN_LIMIT = 3           # max restarts allowed in COOLDOWN_WINDOW
COOLDOWN_WINDOW = timedelta(hours=6)

restart_history = []

# ==========================================================
# DISCORD ALERTS
# ==========================================================
def send_discord_alert(message, title="⚠️ EchoProPulse Watchdog"):
    """Send an alert to Discord via webhook."""
    if not WEBHOOK_URL:
        print("⚠️ No WEBHOOK_URL set. Cannot send alerts.")
        return
    timestamp = datetime.now(TIMEZONE).strftime("[%Y-%m-%d %I:%M %p EST]")
    data = {"username": title, "content": f"{timestamp} {message}"}
    try:
        response = requests.post(WEBHOOK_URL, json=data, timeout=10)
        if response.status_code not in (200, 204):
            print(f"❌ Discord alert failed: {response.status_code} {response.text}")
    except Exception as e:
        print(f"❌ Failed to send Discord alert: {e}")

# ==========================================================
# HEARTBEAT CHECKER
# ==========================================================
def check_heartbeat():
    """Check if the bot heartbeat is up to date."""
    if not os.path.exists(HEARTBEAT_FILE):
        send_discord_alert("🚨 Heartbeat file missing — possible crash detected.")
        restart_bot()
        return

    last_modified = datetime.fromtimestamp(os.path.getmtime(HEARTBEAT_FILE), tz=TIMEZONE)
    now = datetime.now(TIMEZONE)
    idle_minutes = (now - last_modified).total_seconds() / 60
    print(f"[{now:%Y-%m-%d %I:%M %p EST}] Last heartbeat: {last_modified:%I:%M %p EST}, Idle: {idle_minutes:.1f} min")

    if idle_minutes > MAX_IDLE_MINUTES:
        send_discord_alert(f"🚨 No heartbeat detected in {int(idle_minutes)} minutes. Restarting service.")
        restart_bot()

# ==========================================================
# RESTART HANDLER WITH COOLDOWN
# ==========================================================
def restart_bot():
    """Restart the bot service safely with cooldown limits."""
    global restart_history
    now = datetime.now(TIMEZONE)

    # prune old restart timestamps
    restart_history = [t for t in restart_history if now - t < COOLDOWN_WINDOW]

    if len(restart_history) >= COOLDOWN_LIMIT:
        msg = f"🚫 Cooldown active: {len(restart_history)} restarts within {COOLDOWN_WINDOW}. Restart skipped."
        print(msg)
        send_discord_alert(msg)
        return

    try:
        print("🔁 Restarting EchoProPulse service...")
        result = subprocess.run(
            ["systemctl", "restart", SERVICE_NAME],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0:
            restart_history.append(now)
            send_discord_alert("🔁 EchoProPulse service restarted successfully.")
            print("✅ Restart successful.")
        else:
            msg = f"⚠️ Restart failed (code {result.returncode}): {result.stderr.strip()}"
            print(msg)
            send_discord_alert(msg)
    except Exception as e:
        print(f"❌ Restart exception: {e}")
        send_discord_alert(f"❌ Watchdog restart exception: {e}")

# ==========================================================
# MAIN LOOP
# ==========================================================
def main():
    print("🐾 EchoProPulse Watchdog initialized.")
    send_discord_alert("🟢 Watchdog service started. Monitoring EchoProPulse...")
    while True:
        try:
            check_heartbeat()
        except Exception as e:
            print(f"⚠️ Heartbeat check failed: {e}")
            send_discord_alert(f"⚠️ Heartbeat check exception: {e}")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("👋 Watchdog stopped manually.")
        send_discord_alert("🔴 Watchdog service stopped manually.")
    except Exception as e:
        print(f"❌ Watchdog crashed: {e}")
        send_discord_alert(f"💥 Watchdog crashed: {e}")
