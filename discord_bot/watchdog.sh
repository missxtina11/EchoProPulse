#!/bin/bash
# ==========================================================
# 🛡️ EchoProPulse v10 Watchdog
# Monitors the Discord bot and restarts it if it stops.
# Sends alerts via discord_notify.py
# ==========================================================

BASE_DIR="/root/EchoProPulse"
BOT_PATH="$BASE_DIR/echopropulse_v10.py"
VENV_PATH="$BASE_DIR/venv/bin/python3"
SERVICE_NAME="echopropulse.service"
LOG_FILE="$BASE_DIR/discord_bot/watchdog.log"
ENV_FILE="$BASE_DIR/discord_bot/.env"

DATE=$(date '+%Y-%m-%d %H:%M:%S')
echo "[$DATE] [WATCHDOG] Check cycle running..." >> "$LOG_FILE"

# --- Load env vars
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
else
    echo "[$DATE] ⚠️ .env missing. Cannot send Discord notifications." >> "$LOG_FILE"
fi

# --- Check if the bot process is running
if ! pgrep -f "$BOT_PATH" > /dev/null; then
    echo "[$DATE] ❌ Bot not found — restarting..." >> "$LOG_FILE"

    # Restart the systemd service
    systemctl restart "$SERVICE_NAME"

    # --- Send restart alert to Discord using discord_notify.py
    "$VENV_PATH" - <<'PY'
from discord_notify import notify_logs
notify_logs("⚠️ **EchoProPulse Watchdog Alert:** Bot was unresponsive and has been restarted automatically.")
PY

    echo "[$DATE] 🚨 Restart alert sent via discord_notify.py" >> "$LOG_FILE"
else
    echo "[$DATE] ✅ Bot running normally." >> "$LOG_FILE"

    # --- Optional: Send periodic heartbeat confirmation
    "$VENV_PATH" - <<'PY'
from discord_notify import notify_vps
notify_vps("🟢 EchoProPulse Watchdog check: bot heartbeat OK.")
PY
fi

exit 0
