#!/bin/bash
# ============================================================
# 🧠 EchoProPulse Git Auto-Backup Script
# Runs every 6 hours via cron to back up changes to GitHub
# ============================================================

cd /root/EchoProPulse || exit
LOG_FILE="/root/EchoProPulse/discord_bot/git_auto_push.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$DATE] 🚀 Starting auto-backup..." >> "$LOG_FILE"

# --- Ensure correct remote and branch tracking
git remote set-url origin https://github.com/missxtina11/EchoProPulse.git
git branch --set-upstream-to=origin/main main >/dev/null 2>&1

# --- Pull latest from GitHub first (safe rebase)
git fetch origin main >> "$LOG_FILE" 2>&1
git pull --rebase origin main >> "$LOG_FILE" 2>&1

# --- Stage and commit any local changes
git add -A >> "$LOG_FILE" 2>&1
git commit -m "Auto-backup $DATE" >> "$LOG_FILE" 2>&1

# --- Push to GitHub (uses stored credentials)
git push origin main >> "$LOG_FILE" 2>&1

# --- Record commit hash and time
git rev-parse HEAD > /root/EchoProPulse/last_commit.txt
echo "[$DATE] ✅ Backup complete. Commit: $(cat /root/EchoProPulse/last_commit.txt)" >> "$LOG_FILE"

# --- Clean up old logs (7 days)
find /root/EchoProPulse/discord_bot -type f -name "*.log" -mtime +7 -exec rm -f {} \; >> "$LOG_FILE" 2>&1
echo "[$DATE] 🧹 Cleaned logs older than 7 days." >> "$LOG_FILE"

exit 0
