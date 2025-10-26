#!/bin/bash
# ============================================================
# 🧹 EchoProPulse Auto Cleanup Script
# Logs all deletions, posts summary to Discord via bot, and restarts if space freed.
# ============================================================

BASE_DIR="/root/EchoProPulse"
BOT_DIR="$BASE_DIR/discord_bot"
LOG_FILE="$BOT_DIR/cleanup_echo.log"
ENV_FILE="$BOT_DIR/.env"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$DATE] 🧹 Cleanup cycle started..." >> "$LOG_FILE"

# --- Load environment variables
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
else
    echo "[$DATE] ⚠️ Missing .env file — cannot post to Discord." >> "$LOG_FILE"
fi

# --- Debug environment (optional)
{
  echo "[$DATE] Debug environment check:"
  echo "DISCORD_BOT_TOKEN=${DISCORD_BOT_TOKEN:0:15}..."
  echo "DISCORD_LOG_CHANNEL_ID=$DISCORD_LOG_CHANNEL_ID"
} >> "$LOG_FILE"

# --- Unified Python helper for Discord notifications
function send_discord_message() {
  local MESSAGE="$1"
  /root/EchoProPulse/venv/bin/python3 - <<PY
from discord_notify import notify_logs
notify_logs("$MESSAGE")
PY
}

# --- Check disk usage before cleanup
DISK_BEFORE=$(df -h / | awk 'NR==2 {print $5 " used (" $3 " of " $2 ")"}')

# --- Define cleanup targets
CLEAN_TARGETS=(
    "/var/log/*.log"
    "/var/log/journal/*"
    "$BOT_DIR/*.log.*"
    "$BOT_DIR/*.gz"
    "$BASE_DIR/backups/*.gz"
    "$BASE_DIR/backups/*.log"
    "$BASE_DIR/*.tmp"
)

# --- Delete files and summarize
DELETED_COUNT=0
for TARGET in "${CLEAN_TARGETS[@]}"; do
    if ls $TARGET 1> /dev/null 2>&1; then
        FILES=$(ls -1 $TARGET 2>/dev/null | wc -l)
        DELETED_COUNT=$((DELETED_COUNT + FILES))
        rm -f $TARGET 2>/dev/null
        echo "[$DATE] 🗑️ Deleted $FILES files from $TARGET" >> "$LOG_FILE"
    fi
done

# --- Check disk usage after cleanup
DISK_AFTER=$(df -h / | awk 'NR==2 {print $5 " used (" $3 " of " $2 ")"}')

# --- Prepare summary message
SUMMARY="🧹 **EchoProPulse Auto-Cleanup Complete**
🕒 $DATE
🗑️ Files deleted: $DELETED_COUNT
💽 Disk before: $DISK_BEFORE
💽 Disk after: $DISK_AFTER"

# --- Post summary to Discord log channel
send_discord_message "$SUMMARY"
echo "[$DATE] 📢 Posted summary to Discord log channel." >> "$LOG_FILE"

# --- Auto-restart bot if >10% freed
BEFORE_PCT=$(echo "$DISK_BEFORE" | grep -o '[0-9]\+')
AFTER_PCT=$(echo "$DISK_AFTER" | grep -o '[0-9]\+')

if [ -n "$BEFORE_PCT" ] && [ -n "$AFTER_PCT" ]; then
    FREED=$((BEFORE_PCT - AFTER_PCT))
    if [ "$FREED" -ge 10 ]; then
        echo "[$DATE] 🔁 Freed ${FREED}% — restarting service..." >> "$LOG_FILE"
        systemctl restart echopropulse.service
        send_discord_message "🔁 **EchoProPulse Auto-Restarted** after freeing ${FREED}% disk space during cleanup."
        echo "[$DATE] 📢 Restart alert sent to Discord log channel." >> "$LOG_FILE"
    fi
fi

echo "[$DATE] ✅ Cleanup complete." >> "$LOG_FILE"
exit 0
