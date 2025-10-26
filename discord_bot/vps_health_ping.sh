#!/bin/bash
# ============================================================
# 🩵 EchoProPulse Daily VPS Health Ping
# Posts a status heartbeat each morning to #vps-status channel
# ============================================================

BASE_DIR="/root/EchoProPulse"
ENV_FILE="$BASE_DIR/discord_bot/.env"
LOG_FILE="$BASE_DIR/discord_bot/vps_health_ping.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$DATE] [HEALTH] Running daily health check..." >> "$LOG_FILE"

# --- Load environment variables
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
else
    echo "[$DATE] ⚠️ .env not found." >> "$LOG_FILE"
    exit 1
fi

# --- Channel fallback
VPS_CHANNEL_ID="${DISCORD_VPS_CHANNEL_ID:-1430705433861165231}"

# --- Build system summary
UPTIME=$(uptime -p)
LOAD=$(cat /proc/loadavg | awk '{print $1, $2, $3}')
MEM=$(free -m | awk '/Mem:/ {print $3"/"$2" MB"}')
DISK=$(df -h / | awk 'NR==2 {print $3"/"$2" used"}')
IP=$(hostname -I | awk '{print $1}')

MESSAGE="✅ **EchoProPulse VPS Health Report**
🕓 Time: $DATE
💻 Hostname: $(hostname)
🌐 IP: $IP
🕐 Uptime: $UPTIME
💾 Memory: $MEM
📀 Disk: $DISK
📊 Load: $LOAD
🟢 Status: Operational"

# --- Post to Discord
if [ -n "$DISCORD_BOT_TOKEN" ]; then
    curl -H "Authorization: Bot $DISCORD_BOT_TOKEN" \
         -H "Content-Type: application/json" \
         -X POST \
         -d "{\"content\": \"$MESSAGE\"}" \
         "https://discord.com/api/v10/channels/$VPS_CHANNEL_ID/messages" >/dev/null 2>&1
    echo "[$DATE] ✅ Health ping sent to channel $VPS_CHANNEL_ID." >> "$LOG_FILE"
else
    echo "[$DATE] ⚠️ Missing DISCORD_BOT_TOKEN in .env" >> "$LOG_FILE"
fi

exit 0
