#!/usr/bin/env python3
import os, sys, asyncio, subprocess, traceback, signal, discord, requests
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

from discord_notify import notify_main, notify_logs, notify_vps

# ==========================================================
# INITIAL SETUP
# ==========================================================
EST = ZoneInfo("America/New_York")
VERSION = "v10"
load_dotenv(dotenv_path="/root/EchoProPulse/discord_bot/.env")

DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
ADMIN_ID = int(os.getenv("DISCORD_ADMIN_ID", "0"))
ADMIN_ROLE_ID = int(os.getenv("DISCORD_ADMIN_ROLE_ID", "0"))
TRADE_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))
LOG_CHANNEL_ID = int(os.getenv("DISCORD_LOG_CHANNEL_ID", "0"))
VPS_STATUS_ID = int(os.getenv("DISCORD_VPS_CHANNEL_ID", "1430705433861165231"))
SOLANA_WALLET = os.getenv("SOLANA_WALLET", "Unknown Wallet")

LOG_FILE = "/root/EchoProPulse/discord_bot/bot.log"
HEARTBEAT_FILE = "/root/EchoProPulse/discord_bot/heartbeat.log"
STATE_FILE = "/root/EchoProPulse/live_state.txt"

LIVE_TRADING = os.path.exists(STATE_FILE) and open(STATE_FILE).read().strip().lower() == "true"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree

# ==========================================================
# HELPERS
# ==========================================================
def embed_base(title, desc, color=0x00ffb3):
    e = discord.Embed(title=title, description=desc, color=color, timestamp=datetime.now(EST))
    e.set_footer(text=f"🕓 Updated: {datetime.now(EST):%I:%M %p EST}")
    return e

async def post_log(msg: str, channel_id: int = LOG_CHANNEL_ID):
    """Post plain text logs or admin info."""
    try:
        ch = bot.get_channel(channel_id)
        if ch:
            await ch.send(msg)
    except Exception as e:
        print(f"[LOG_POST_ERR] {e}")

async def write_heartbeat():
    while True:
        with open(HEARTBEAT_FILE, "w") as f:
            f.write(datetime.now(EST).isoformat())
        await asyncio.sleep(300)

def save_state():
    with open(STATE_FILE, "w") as f:
        f.write(str(LIVE_TRADING).lower())

def is_admin(inter):
    if inter.user.id == ADMIN_ID:
        return True
    return any(r.id == ADMIN_ROLE_ID for r in getattr(inter.user, "roles", []))

# ==========================================================
# BOT EVENTS
# ==========================================================
@bot.event
async def on_ready():
    print(f"✅ EchoProPulse Bot ({VERSION}) logged in as {bot.user}")

    # Log to console + logs channel
    from discord_notify import notify_main, notify_logs, notify_vps

    # --- Main channel: bot is online / public notification
    notify_main(f"✅ **EchoProPulse {VERSION}** is now online and synced!")
    
    # --- Logs channel: admin info
    notify_logs(
        f"🟢 **EchoProPulse {VERSION} started**\n"
        f"💰 Wallet: `{SOLANA_WALLET}`\n"
        f"⚙️ Trading: {'ENABLED' if LIVE_TRADING else 'DISABLED'}"
    )

    # --- VPS channel: system status confirmation
    notify_vps(f"🖥️ VPS heartbeat OK • Bot started cleanly at {datetime.now(EST):%I:%M %p EST}")

    try:
        await tree.sync()
        print("✅ Commands synced")
        notify_logs("🔄 Slash commands synced successfully.")
    except Exception as e:
        print(f"⚠️ Sync failed: {e}")
        notify_logs(f"⚠️ Command sync failed: `{e}`")

    # Write heartbeat for watchdog
    await write_heartbeat()
    print("🫀 Heartbeat started.")

# ==========================================================
# SLASH COMMANDS
# ==========================================================
@tree.command(name="start", description="Launch the control panel.")
async def start(inter: discord.Interaction):
    embed = embed_base("🚀 EchoProPulse Control Center", "Select an option below:")
    await inter.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="about", description="Bot information.")
async def about(inter: discord.Interaction):
    embed = embed_base(
        f"🤖 EchoProPulse {VERSION}",
        f"💹 Trading: {'🟢 Enabled' if LIVE_TRADING else '🔴 Disabled'}\n💰 Wallet: `{SOLANA_WALLET}`"
    )
    await inter.response.send_message(embed=embed, ephemeral=True)

# ==========================================================
# ADMIN COMMANDS
# ==========================================================
@tree.command(name="toggle", description="Enable or disable trading mode (admin only).")
async def toggle(inter: discord.Interaction):
    global LIVE_TRADING
    if not is_admin(inter):
        await inter.response.send_message("🚫 Unauthorized.", ephemeral=True)
        return
    LIVE_TRADING = not LIVE_TRADING
    save_state()
    status = "🟢 Enabled" if LIVE_TRADING else "🔴 Disabled"
    await inter.response.send_message(f"Trading is now {status}", ephemeral=True)
    await post_log(f"⚙️ {inter.user.mention} toggled trading to {status}")

# ==========================================================
# SHUTDOWN HANDLER
# ==========================================================
async def graceful_shutdown():
    await post_log("🔴 EchoProPulse shutting down cleanly...")
    print("🧹 Clean shutdown complete.")
    await bot.close()

def handle_signal(signum, frame):
    asyncio.run(graceful_shutdown())
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)

# ==========================================================
# RUN BOT
# ==========================================================
def run():
    print(f"✅ Starting EchoProPulse {VERSION}")
    bot.run(DISCORD_TOKEN)

if __name__ == "__main__":
    run()
