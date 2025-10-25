#!/bin/bash
HEARTBEAT="/root/EchoProPulse/discord_bot/heartbeat.log"
LOG="/root/EchoProPulse/discord_bot/watchdog.log"
SERVICE="echopropulse.service"
MAX_AGE_MINUTES=10
DISCORD_WEBHOOK="https://discord.com/api/webhooks/1431086202407995402/your_private_error_webhook"

send_discord_alert () {
  local msg="$1"
  local cpu=$(top -bn1 | grep "Cpu(s)" | awk '{print $2 + $4"%"}')
  local ram=$(free -m | awk 'NR==2{printf "%.1f%%", $3*100/$2 }')
  local host=$(hostname)
  curl -s -H "Content-Type: application/json" \
    -X POST -d "{\"content\": \"$msg\n🧠 **System Load:** CPU $cpu | RAM $ram | Host $host\"}" "$DISCORD_WEBHOOK" >/dev/null 2>&1
}

echo "[`date '+%Y-%m-%d %H:%M:%S'`] [watchdog] START" >> "$LOG"
send_discord_alert "🧩 **EchoProPulse Watchdog** started monitoring heartbeat."

while true; do
  if [ -f "$HEARTBEAT" ]; then
    LAST=$(stat -c %Y "$HEARTBEAT")
    NOW=$(date +%s)
    AGE=$(( (NOW - LAST) / 60 ))
    if [ "$AGE" -gt "$MAX_AGE_MINUTES" ]; then
      echo "[`date '+%Y-%m-%d %H:%M:%S'`] [watchdog] Heartbeat stale ($AGE min) — restarting." >> "$LOG"
      send_discord_alert "🚨 **EchoProPulse Watchdog:** Heartbeat stale (${AGE} min). Restarting service..."
      systemctl restart "$SERVICE"
      sleep 20
      STATUS=$(systemctl is-active "$SERVICE")
      if [ "$STATUS" = "active" ]; then
        send_discord_alert "✅ **EchoProPulse Restarted Successfully** at $(date '+%I:%M %p EST')."
      else
        send_discord_alert "❌ **Restart FAILED** — manual check required."
      fi
    else
      echo "[`date '+%Y-%m-%d %H:%M:%S'`] [watchdog] OK (heartbeat $AGE min old)" >> "$LOG"
    fi
  else
    echo "[`date '+%Y-%m-%d %H:%M:%S'`] [watchdog] No heartbeat file found — restarting service." >> "$LOG"
    send_discord_alert "⚠️ **EchoProPulse Watchdog:** No heartbeat file found. Restarting service..."
    systemctl restart "$SERVICE"
  fi
  sleep 300
done
