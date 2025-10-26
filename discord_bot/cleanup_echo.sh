#!/bin/bash
# ============================================================
# 🧹 EchoProPulse Smart Cleanup Script
# Automatically removes old logs and notifies Discord via bot token.
# ============================================================

BASE_DIR="/root/EchoProPulse"
BOT_DIR="$BASE_DIR/discord_bot"
ENV_FILE="$BOT_DIR/.env"
LOG_FILE="$BOT_DIR/cleanup_echo.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$DATE] 🧹 Starting weekly cleanup..." >> "$LOG_FILE"

# Load Discord token and log channel ID from .env
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
else
    echo "[$DATE] ❌ .env not found. Cannot send Discord notifications." >> "$LOG_FILE"
fi

LOG_CHANNEL_ID="${DISCORD_LOG_CHANNEL_ID:-1431773496848945302}"

# Default channel if not defined
LOG_CHANNEL_ID="${DISCORD_LOG_CHANNEL_ID:-1431773496848945302}"

# --- Remove common log/cache/temp files (older than 3 days)
find "$BASE_DIR" -type f -name "*.log" -mtime +3 -exec rm -f {} \; 2>/dev/null
find "$BASE_DIR" -type f -name "*.gz"  -mtime +3 -exec rm -f {} \; 2>/dev/null
find "$BASE_DIR" -type f -name "*.tmp" -mtime +3 -exec rm -f {} \; 2>/dev/null

# --- Remove redundant generated files
rm -f "$BASE_DIR/cron.log" "$BASE_DIR/last_commit.txt"

# --- Optionally remove old bot versions
# rm -f "$BASE_DIR/main_discord_v7.py"

# --- Clean Python cache folders
find "$BASE_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

echo "[$DATE] ✅ Cleanup complete." >> "$LOG_FILE"

# --- Prepare Discord message
MESSAGE_CONTENT="🧹 **EchoProPulse Cleanup Completed**
🕓 Time: $DATE
📦 Server: $(hostname)
📁 Folder: $BASE_DIR
✅ Old logs, temp files, and caches removed."

# --- Post to Discord logs channel using bot token
if [ -n "$DISCORD_BOT_TOKEN" ]; then
    curl -H "Authorization: Bot $DISCORD_BOT_TOKEN" \
         -H "Content-Type: application/json" \
         -X POST \
         -d "{\"content\": \"$MESSAGE_CONTENT\"}" \
         "https://discord.com/api/v10/channels/$LOG_CHANNEL_ID/messages" >/dev/null 2>&1
    echo "[$DATE] ✅ Discord notification sent to channel $LOG_CHANNEL_ID." >> "$LOG_FILE"
else
    echo "[$DATE] ⚠️ Discord bot token missing, no message sent." >> "$LOG_FILE"
fi

exit 0
