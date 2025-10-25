#!/bin/bash
# ============================================
# 🧩 EchoProPulse Git Auto-Backup Script
# ============================================

REPO_DIR="/root/EchoProPulse/discord_bot"
LOG_FILE="/root/EchoProPulse/discord_bot/git_auto_push.log"

cd "$REPO_DIR" || exit

# Configure Git identity (used for auto commits)
git config user.name "AutoBot"
git config user.email "autobot@localhost"

# Stage and check for changes
git add .
CHANGES=$(git status --porcelain)

if [ -n "$CHANGES" ]; then
    COMMIT_MSG="Auto-backup $(date '+%Y-%m-%d %H:%M:%S')"
    echo "[`date '+%Y-%m-%d %H:%M:%S'`] Backing up changes..." >> "$LOG_FILE"
    git commit -m "$COMMIT_MSG" >> "$LOG_FILE" 2>&1
    git push origin main >> "$LOG_FILE" 2>&1
    echo "[`date '+%Y-%m-%d %H:%M:%S'`] ✅ Backup complete." >> "$LOG_FILE"
else
    echo "[`date '+%Y-%m-%d %H:%M:%S'`] No changes detected." >> "$LOG_FILE"
fi
