#!/usr/bin/env python3
import os
import sys
import asyncio
import discord
import subprocess
import traceback
import requests
import signal
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo

# ==========================================================
# INITIAL SETUP
# ==========================================================
EST = ZoneInfo("America/New_York")
START_TIME = datetime.now(EST)

load_dotenv()

# --- Environment Variables ---
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN")
SOLANA_WALLET = os.getenv("SOLANA_WALLET", "Unknown Wallet")
ADMIN_ID = int(os.getenv("DISCORD_ADMIN_ID", "1166517382064373841"))
ALERT_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))

LOG_FILE = "/root/EchoProPulse/discord_activity.log"
HEARTBEAT_FILE = "/root/EchoProPulse/discord_bot/heartbeat.log"
STATE_FILE = "/root/EchoProPulse/live_state.txt"

# ==========================================================
# Load Persistent Trading State
# ==========================================================
LIVE_TRADING = False
if os.path.exists(STATE_FILE):
    try:
        with open(STATE_FILE, "r") as f:
            state = f.read().strip().lower()
            LIVE_TRADING = (state == "true")
            print(f"🔁 Restored trading state: {'ENABLED' if LIVE_TRADING else 'DISABLED'}")
    except Exception as e:
        print(f"⚠️ Failed to load trading state: {e}")

def save_live_state():
    """Save the trading state persistently."""
    try:
        with open(STATE_FILE, "w") as f:
            f.write(str(LIVE_TRADING).lower())
            print(f"💾 Saved trading state: {'ENABLED' if LIVE_TRADING else 'DISABLED'}")
    except Exception as e:
        print(f"⚠️ Failed to save live state: {e}")

# --- Discord Intents ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree

# ==========================================================
# ERROR & ACTION LOGGING
# ==========================================================
ERROR_WEBHOOK = "https://discord.com/api/webhooks/1431086202491803668/your_error_hook_here"

def log_error_to_discord(err):
    """Send errors to Discord webhook."""
    try:
        tb = traceback.format_exc()
        data = {"content": f"⚠️ **EchoProPulse Error Log:**\n```{tb}```"}
        requests.post(ERROR_WEBHOOK, json=data)
    except Exception as e:
        print(f"⚠️ Failed to send error webhook: {e}")

def log_action(user, action, result="OK"):
    """Log user actions and critical results."""
    try:
        now = datetime.now(EST)
        username = f"{user.name}#{getattr(user, 'discriminator', '0000')}"
        line = f"[{now:%Y-%m-%d %I:%M:%S %p EST}] {username} → {action} → {result}\n"
        with open(LOG_FILE, "a") as f:
            f.write(line)
        if any(word in str(result).upper() for word in ["ERROR", "FAIL", "EXCEPTION"]):
            log_error_to_discord(result)
    except Exception as e:
        print(f"⚠️ Logging error: {e}")

# ==========================================================
# HEARTBEAT SUPPORT
# ==========================================================
async def write_heartbeat():
    """Update a heartbeat timestamp every 5 minutes for watchdog."""
    while True:
        try:
            with open(HEARTBEAT_FILE, "w") as f:
                f.write(f"{datetime.now(EST).isoformat()}\n")
        except Exception as e:
            print(f"⚠️ Failed to write heartbeat: {e}")
        await asyncio.sleep(300)  # every 5 minutes

# ==========================================================
# EMBEDS + HELPERS
# ==========================================================
def embed_base(title: str, description: str):
    embed = discord.Embed(title=title, description=description, color=0x00FFB3)
    embed.set_footer(text=f"🕓 Last Updated (EST): {datetime.now(EST):%I:%M %p}")
    return embed

def is_admin(uid: int):
    return uid == ADMIN_ID

# ==========================================================
# DISCORD BOT EVENTS
# ==========================================================
@bot.event
async def on_ready():
    print(f"✅ Discord bot logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands with Discord.")
    except Exception as e:
        print(f"⚠️ Command sync failed: {e}")

    if ALERT_CHANNEL_ID:
        channel = bot.get_channel(ALERT_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                title="🚀 EchoProPulse Online",
                description=(
                    f"🤖 **Bot Status:** Active\n"
                    f"💹 **Trading:** {'🟢 Enabled' if LIVE_TRADING else '🔴 Disabled'}\n"
                    f"💰 **Wallet:** `{SOLANA_WALLET}`\n"
                    f"🕒 **Started:** {datetime.now(EST):%I:%M %p EST}"
                ),
                color=0x00FFB3,
                timestamp=datetime.now(EST)
            )
            await channel.send(embed=embed)
            print("📢 Online alert sent to Discord.")

    # Start heartbeat loop
    bot.loop.create_task(write_heartbeat())

# ==========================================================
# SLASH COMMANDS
# ==========================================================
@tree.command(name="start", description="Launch the EchoProPulse control center.")
async def start(inter: discord.Interaction):
    embed = embed_base("🚀 EchoProPulse Control Center", "Choose a category to begin monitoring or trading.")
    await inter.response.send_message(embed=embed)
    log_action(inter.user, "/start")

@tree.command(name="about", description="Display EchoProPulse information.")
async def about(inter: discord.Interaction):
    embed = embed_base(
        "🤖 EchoProPulse v6.0",
        "🔗 **Solana Trading Engine**\n🧩 **Part of EchoProtocol Suite**\n🕓 **EST Monitoring Active**"
    )
    await inter.response.send_message(embed=embed)
    log_action(inter.user, "/about")

# --- /sync Command ---
@bot.tree.command(name="sync", description="Force sync all commands (Admin only).")
async def sync(inter: discord.Interaction):
    if inter.user.id != ADMIN_ID:
        await inter.response.send_message("🚫 You are not authorized to use this command.")
        return
    try:
        synced = await bot.tree.sync()
        await inter.response.send_message(f"✅ Synced {len(synced)} commands successfully.")
    except Exception as e:
        await inter.response.send_message(f"❌ Sync failed: {e}")

# --- /force_restart Command ---
@bot.tree.command(name="force_restart", description="Force restart the EchoProPulse service (Admin only).")
async def force_restart(inter: discord.Interaction):
    if inter.user.id != ADMIN_ID:
        await inter.response.send_message("🚫 Unauthorized.")
        return
    await inter.response.send_message("⚙️ Restarting EchoProPulse service...")
    try:
        result = subprocess.run(["systemctl", "restart", "echopropulse.service"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            await inter.followup.send("✅ EchoProPulse restarted successfully.")
        else:
            await inter.followup.send(f"⚠️ Restart failed (code {result.returncode}).")
    except Exception as e:
        await inter.followup.send(f"❌ Failed to restart: {e}")

# ==========================================================
# SHUTDOWN HANDLER (FINAL STABLE)
# ==========================================================
async def send_offline_alert():
    """Send a shutdown message when the bot goes offline."""
    if not ALERT_CHANNEL_ID:
        return
    try:
        channel = bot.get_channel(ALERT_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                title="🔴 EchoProPulse Offline",
                description=f"🚨 Bot shutdown detected at {datetime.now(EST):%Y-%m-%d %I:%M %p EST}",
                color=0xFF0040,
                timestamp=datetime.now(EST)
            )
            await channel.send(embed=embed)
            print("📕 Offline alert sent.")
    except Exception as e:
        print(f"⚠️ Failed to send offline alert: {e}")


def handle_shutdown(signum, frame):
    print("⚠️ Shutdown signal received — sending offline alert...")
    try:
        asyncio.run(send_offline_alert())
    except Exception as e:
        print(f"⚠️ Could not send offline alert cleanly: {e}")
    finally:
        print("🧹 Clean shutdown complete.")
        sys.exit(0)


signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)

# ==========================================================
# RUN BOT
# ==========================================================
def run_discord_bot():
    print("✅ Starting EchoProPulse Discord Bot (v6) – Solana Monitor")
    print(f"🔍 Token detected? {'YES' if DISCORD_TOKEN else 'NO'}")
    if not DISCORD_TOKEN:
        print("❌ No Discord token found. Please verify DISCORD_BOT_TOKEN in systemd or .env")
        sys.exit(1)
    bot.run(DISCORD_TOKEN)

if __name__ == "__main__":
    run_discord_bot()
