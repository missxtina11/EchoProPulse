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
ADMIN_ROLE_ID = int(os.getenv("DISCORD_ADMIN_ROLE_ID", "1431735725514297394"))
ALERT_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))

LOG_FILE = "/root/EchoProPulse/discord_activity.log"
HEARTBEAT_FILE = "/root/EchoProPulse/discord_bot/heartbeat.log"
STATE_FILE = "/root/EchoProPulse/live_state.txt"

# ==========================================================
# LOAD / SAVE PERSISTENT TRADING STATE
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
    """Save trading state persistently."""
    try:
        with open(STATE_FILE, "w") as f:
            f.write(str(LIVE_TRADING).lower())
        print(f"💾 Saved trading state: {'ENABLED' if LIVE_TRADING else 'DISABLED'}")
    except Exception as e:
        print(f"⚠️ Failed to save live state: {e}")

# ==========================================================
# DISCORD CLIENT SETUP
# ==========================================================
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree

# ==========================================================
# LOGGING
# ==========================================================
ERROR_WEBHOOK = "https://discord.com/api/webhooks/1431086202407995402/your_private_error_webhook"

def log_error_to_discord(err):
    """Send exceptions to Discord webhook."""
    try:
        tb = traceback.format_exc()
        data = {"content": f"⚠️ **EchoProPulse Error Log:**\n```{tb[:1800]}```"}
        requests.post(ERROR_WEBHOOK, json=data, timeout=10)
    except Exception as e:
        print(f"⚠️ Failed to send error webhook: {e}")

def log_action(user, action, result="OK"):
    """Log user actions and results."""
    try:
        now = datetime.now(EST)
        username = f"{user.name}#{getattr(user, 'discriminator', '0000')}"
        line = f"[{now:%Y-%m-%d %I:%M:%S %p EST}] {username}: {action} -> {result}\n"
        with open(LOG_FILE, "a") as f:
            f.write(line)
        if "ERROR" in str(result).upper():
            log_error_to_discord(result)
    except Exception as e:
        print(f"⚠️ Logging error: {e}")

# ==========================================================
# HELPER FUNCTIONS
# ==========================================================
def is_admin_user(inter):
    """Check if user is authorized via ID or AdminPanel role."""
    if inter.user.id == ADMIN_ID:
        return True
    if any(role.id == ADMIN_ROLE_ID for role in getattr(inter.user, "roles", [])):
        return True
    return False

def embed_base(title, description):
    embed = discord.Embed(title=title, description=description, color=0x00FFB3, timestamp=datetime.now(EST))
    embed.set_footer(text=f"🕓 Last Updated (EST): {datetime.now(EST):%I:%M %p}")
    return embed

async def write_heartbeat():
    """Write heartbeat every 5 minutes for watchdog."""
    while True:
        try:
            with open(HEARTBEAT_FILE, "w") as f:
                f.write(f"{datetime.now(EST).isoformat()}\n")
        except Exception as e:
            print(f"⚠️ Heartbeat write failed: {e}")
        await asyncio.sleep(300)

# ==========================================================
# CONTROL PANEL BUTTONS
# ==========================================================
class ControlPanel(discord.ui.View):
    def __init__(self, is_admin: bool):
        super().__init__(timeout=None)
        categories = ["Market", "Wallet", "AI", "Trade", "Utility"]
        for c in categories:
            self.add_item(discord.ui.Button(label=c, style=discord.ButtonStyle.primary))
        if is_admin:
            self.add_item(discord.ui.Button(label="Admin Panel", style=discord.ButtonStyle.danger, custom_id="admin_panel"))

# ==========================================================
# BOT EVENTS
# ==========================================================
@bot.event
async def on_ready():
    print(f"✅ Discord bot logged in as {bot.user}")
    try:
        synced = await tree.sync()
        print(f"✅ Synced {len(synced)} slash commands with Discord.")
    except Exception as e:
        print(f"⚠️ Command sync failed: {e}")
    channel = bot.get_channel(ALERT_CHANNEL_ID)
    if channel:
        status_text = "🟢 Enabled" if LIVE_TRADING else "🔴 Disabled"
        embed = embed_base("🚀 EchoProPulse Online", f"💹 **Trading:** {status_text}\n💰 **Wallet:** `{SOLANA_WALLET}`")
        await channel.send(embed=embed)
        print("📢 Online alert sent.")
    bot.loop.create_task(write_heartbeat())

# ==========================================================
# SLASH COMMANDS
# ==========================================================
@tree.command(name="start", description="Launch the EchoProPulse Control Panel.")
async def start(inter: discord.Interaction):
    is_admin = is_admin_user(inter)
    embed = embed_base("🚀 EchoProPulse Control Center", "Choose a category below:")
    await inter.response.send_message(embed=embed, view=ControlPanel(is_admin), ephemeral=True)
    log_action(inter.user, "/start")

@tree.command(name="about", description="Display bot information.")
async def about(inter: discord.Interaction):
    embed = embed_base("🤖 EchoProPulse v7", "🔗 Solana Trading Suite\n🧩 Powered by EchoProtocol\n📅 Build: Oct 2025")
    await inter.response.send_message(embed=embed, ephemeral=True)
    log_action(inter.user, "/about")

@tree.command(name="sync", description="Force resync all commands (Admin only).")
async def sync(inter: discord.Interaction):
    if not is_admin_user(inter):
        await inter.response.send_message("🚫 Unauthorized.", ephemeral=True)
        return
    try:
        synced = await tree.sync()
        await inter.response.send_message(f"✅ Synced {len(synced)} commands.")
    except Exception as e:
        await inter.response.send_message(f"❌ Sync failed: {e}")

@tree.command(name="force_restart", description="Force restart the EchoProPulse service.")
async def force_restart(inter: discord.Interaction):
    if not is_admin_user(inter):
        await inter.response.send_message("🚫 Unauthorized.", ephemeral=True)
        return
    await inter.response.send_message("⚙️ Restarting EchoProPulse service...", ephemeral=True)
    try:
        subprocess.run(["systemctl", "restart", "echopropulse.service"], check=True)
    except Exception as e:
        await inter.followup.send(f"❌ Restart failed: {e}")

# ==========================================================
# INTERACTION HANDLER FOR ADMIN PANEL
# ==========================================================
@bot.event
async def on_interaction(inter: discord.Interaction):
    if inter.type != discord.InteractionType.component:
        return
    cid = inter.data.get("custom_id", "")
    if cid == "admin_panel":
        if not is_admin_user(inter):
            await inter.response.send_message("🚫 Unauthorized access.", ephemeral=True)
            log_action(inter.user, "admin_panel", "DENIED")
            return

        global LIVE_TRADING
        embed = embed_base("🛠️ Admin Panel", "Control system trading and status below:")
        view = discord.ui.View()

        async def start_trading(interaction):
            global LIVE_TRADING
            LIVE_TRADING = True
            save_live_state()
            await interaction.response.edit_message(embed=embed_base("🟢 Trading Enabled", "Trading is now active."), view=None)
            ch = bot.get_channel(ALERT_CHANNEL_ID)
            if ch:
                await ch.send(f"🟢 Trading enabled by {interaction.user.mention}")
            log_action(interaction.user, "Start Trading")

        async def stop_trading(interaction):
            global LIVE_TRADING
            LIVE_TRADING = False
            save_live_state()
            await interaction.response.edit_message(embed=embed_base("🔴 Trading Disabled", "Trading is now paused."), view=None)
            ch = bot.get_channel(ALERT_CHANNEL_ID)
            if ch:
                await ch.send(f"🔴 Trading stopped by {interaction.user.mention}")
            log_action(interaction.user, "Stop Trading")

        view.add_item(discord.ui.Button(label="🟢 Start Trading", style=discord.ButtonStyle.success, custom_id="start_trade"))
        view.add_item(discord.ui.Button(label="🔴 Stop Trading", style=discord.ButtonStyle.danger, custom_id="stop_trade"))

        await inter.response.send_message(embed=embed, view=view, ephemeral=True)
        log_action(inter.user, "Admin Panel Opened")

# ==========================================================
# SHUTDOWN HANDLER
# ==========================================================
async def send_offline_alert():
    ch = bot.get_channel(ALERT_CHANNEL_ID)
    if ch:
        embed = embed_base("🔴 EchoProPulse Offline", f"Shutdown at {datetime.now(EST):%I:%M %p EST}")
        await ch.send(embed=embed)
        print("📕 Offline alert sent.")

def handle_shutdown(signum, frame):
    print("⚠️ Shutdown signal received — sending offline alert.")
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
    print("✅ Starting EchoProPulse Discord Bot (v7) – Unified Control Panel")
    print(f"🔍 Token detected? {'YES' if DISCORD_TOKEN else 'NO'}")
    if not DISCORD_TOKEN:
        print("❌ No Discord token found. Please verify environment variable DISCORD_BOT_TOKEN.")
        sys.exit(1)
    bot.run(DISCORD_TOKEN)

if __name__ == "__main__":
    run_discord_bot()
