#!/usr/bin/env python3
import os
import sys
import asyncio
import discord
import subprocess
import traceback
import requests
import signal
import aiohttp
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# ==========================================================
# CONFIG / CONSTANTS
# ==========================================================
VERSION = "v9"
EST = ZoneInfo("America/New_York")
START_TIME = datetime.now(EST)

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN")
SOLANA_WALLET = os.getenv("SOLANA_WALLET", "Unknown Wallet")
ADMIN_ID = int(os.getenv("DISCORD_ADMIN_ID", "1166517382064373841"))
ADMIN_ROLE_ID = int(os.getenv("DISCORD_ADMIN_ROLE_ID", "1431735725514297394"))
ALERT_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))

LOG_FILE = "/root/EchoProPulse/discord_activity.log"
HEARTBEAT_FILE = "/root/EchoProPulse/discord_bot/heartbeat.log"
STATE_FILE = "/root/EchoProPulse/live_state.txt"
ERROR_WEBHOOK = os.getenv("DISCORD_ERROR_WEBHOOK",
    "https://discord.com/api/webhooks/1431086202407995402/your_private_error_webhook")

LIVE_TRADING = False

# ==========================================================
# STATE MANAGEMENT
# ==========================================================
def load_live_state():
    global LIVE_TRADING
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                LIVE_TRADING = f.read().strip().lower() == "true"
                print(f"🔁 Restored trading state: {'ENABLED' if LIVE_TRADING else 'DISABLED'}")
        except Exception as e:
            print(f"⚠️ Could not load trading state: {e}")

def save_live_state():
    try:
        with open(STATE_FILE, "w") as f:
            f.write(str(LIVE_TRADING).lower())
        print(f"💾 Saved trading state: {'ENABLED' if LIVE_TRADING else 'DISABLED'}")
    except Exception as e:
        print(f"⚠️ Failed to save trading state: {e}")

load_live_state()

# ==========================================================
# DISCORD CLIENT
# ==========================================================
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree
session = None

# ==========================================================
# LOGGING / ERROR REPORTING
# ==========================================================
def log_error_to_discord(err: str):
    """Send traceback or error messages to Discord webhook."""
    try:
        tb = traceback.format_exc()
        data = {"content": f"⚠️ **EchoProPulse Error Log ({VERSION})**\n```{tb[:1800]}\n{err}```"}
        requests.post(ERROR_WEBHOOK, json=data, timeout=10)
    except Exception as e:
        print(f"⚠️ Failed to send webhook: {e}")

def log_action(user, action, result="OK"):
    now = datetime.now(EST)
    username = f"{user.name}#{getattr(user, 'discriminator', '0000')}"
    line = f"[{now:%Y-%m-%d %I:%M:%S %p EST}] {username}: {action} -> {result}\n"
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line)
    except Exception as e:
        print(f"⚠️ Logging error: {e}")
    if "ERROR" in str(result).upper():
        log_error_to_discord(result)

# ==========================================================
# HELPERS
# ==========================================================
def is_admin_user(inter):
    if inter.user.id == ADMIN_ID:
        return True
    if any(role.id == ADMIN_ROLE_ID for role in getattr(inter.user, "roles", [])):
        return True
    return False

def embed_base(title, description, color=0x00FFB3):
    embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now(EST))
    embed.set_footer(text=f"🕓 Updated: {datetime.now(EST):%I:%M %p EST}")
    return embed

async def write_heartbeat():
    """Heartbeat for watchdog + recovery."""
    while True:
        try:
            with open(HEARTBEAT_FILE, "w") as f:
                f.write(datetime.now(EST).isoformat())
        except Exception as e:
            print(f"⚠️ Heartbeat write error: {e}")
        await asyncio.sleep(300)

async def restart_service_safe():
    """Safely restart the systemd service."""
    try:
        print("♻️ Restarting EchoProPulse service...")
        proc = await asyncio.create_subprocess_exec("systemctl", "restart", "echopropulse.service")
        await proc.wait()
        if proc.returncode == 0:
            print("✅ Service restarted successfully.")
        else:
            raise Exception(f"systemctl exit code {proc.returncode}")
    except Exception as e:
        log_error_to_discord(f"Service restart failed: {e}")
        print(f"❌ Restart failed: {e}")

def uptime_str():
    delta = datetime.now(EST) - START_TIME
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes = remainder // 60
    return f"{hours}h {minutes}m"

# ==========================================================
# BUTTONS
# ==========================================================
class ControlPanel(discord.ui.View):
    def __init__(self, is_admin):
        super().__init__(timeout=None)
        for label in ["Market", "Wallet", "AI", "Trade", "Utility"]:
            self.add_item(discord.ui.Button(label=label, style=discord.ButtonStyle.primary))
        if is_admin:
            self.add_item(discord.ui.Button(label="Admin Panel", style=discord.ButtonStyle.danger, custom_id="admin_panel"))

# ==========================================================
# BOT EVENTS
# ==========================================================
@bot.event
async def on_ready():
    global session
    session = aiohttp.ClientSession()
    print(f"✅ EchoProPulse Bot ({VERSION}) logged in as {bot.user}")
    try:
        synced = await tree.sync()
        print(f"✅ Synced {len(synced)} slash commands with Discord.")
    except Exception as e:
        print(f"⚠️ Sync error: {e}")

    ch = bot.get_channel(ALERT_CHANNEL_ID)
    if ch:
        status = "🟢 Enabled" if LIVE_TRADING else "🔴 Disabled"
        embed = embed_base("🚀 EchoProPulse Online",
                           f"💹 **Trading:** {status}\n💰 **Wallet:** `{SOLANA_WALLET}`\n🕒 **Uptime:** {uptime_str()}")
        await ch.send(embed=embed)
        print("📢 Online alert sent.")

        # Send a green "service started" notification
        start_embed = embed_base("✅ EchoProPulse Service Started",
                                 f"🧩 Version: {VERSION}\n💹 Trading: {status}\n"
                                 f"💰 Wallet: `{SOLANA_WALLET}`\n🕒 Started at {datetime.now(EST):%I:%M %p EST}")
        await ch.send(embed=start_embed)
        print("💚 Service-start alert sent.")

    # ✅ Schedule GitHub update check (runs every 24 hours)
    async def daily_update_task():
        while True:
            await check_github_updates()
            await asyncio.sleep(86400)  # 24 hours (in seconds)

    bot.loop.create_task(daily_update_task())

    # ✅ Start heartbeat writer
    bot.loop.create_task(write_heartbeat())

    if LIVE_TRADING:
        await restart_service_safe()

# ==========================================================
# SLASH COMMANDS
# ==========================================================
@tree.command(name="start", description="Launch the EchoProPulse control center.")
async def start(inter: discord.Interaction):
    is_admin = is_admin_user(inter)
    embed = embed_base("🚀 EchoProPulse Control Center", "Choose a category to begin.")

    # --- respond right away ---
    await inter.response.defer(ephemeral=True)

    # now safely follow-up with the view/buttons
    await inter.followup.send(embed=embed, view=ControlPanel(is_admin), ephemeral=True)
    log_action(inter.user, "/start")

@tree.command(name="status", description="Show current EchoProPulse status and uptime.")
async def status(inter: discord.Interaction):
    hb_age = "N/A"
    if os.path.exists(HEARTBEAT_FILE):
        try:
            with open(HEARTBEAT_FILE, "r") as f:
                t = datetime.fromisoformat(f.read().strip())
                age = datetime.now(EST) - t
                hb_age = f"{int(age.total_seconds() // 60)} min ago"
        except Exception:
            pass
    desc = (f"💹 **Trading:** {'🟢 Enabled' if LIVE_TRADING else '🔴 Disabled'}\n"
            f"🕒 **Uptime:** {uptime_str()}\n"
            f"💰 **Wallet:** `{SOLANA_WALLET}`\n"
            f"❤️ **Heartbeat:** {hb_age}\n"
            f"⚙️ **Version:** {VERSION}")
    await inter.response.send_message(embed=embed_base("📊 EchoProPulse Status", desc), ephemeral=True)
    log_action(inter.user, "/status")

@tree.command(name="about", description="Information about EchoProPulse bot.")
async def about(inter: discord.Interaction):
    embed = embed_base(f"🤖 EchoProPulse {VERSION}",
                       "🔗 Solana Trading Suite\n🧩 EchoProtocol\n📅 Build: Oct 2025\n♻️ Auto-recovery enabled")
    await inter.response.send_message(embed=embed, ephemeral=True)
    log_action(inter.user, "/about")

# ==========================================================
# ADMIN UTILITIES
# ==========================================================
@tree.command(name="reload", description="Reload and re-sync all EchoProPulse commands (admin only).")
async def reload(inter: discord.Interaction):
    if not is_admin_user(inter):
        await inter.response.send_message("🚫 Unauthorized.", ephemeral=True)
        return
    await inter.response.defer(ephemeral=True)
    try:
        synced = await tree.sync()
        msg = f"✅ Reloaded and synced {len(synced)} commands."
        print(msg)
        await inter.followup.send(msg, ephemeral=True)
        log_action(inter.user, "/reload")
    except Exception as e:
        await inter.followup.send(f"⚠️ Reload failed: {e}", ephemeral=True)
        log_error_to_discord(e)

# ==========================================================
# ADMIN PANEL
# ==========================================================
@bot.event
async def on_interaction(inter: discord.Interaction):
    if inter.type != discord.InteractionType.component:
        return

    cid = inter.data.get("custom_id", "")
    if cid == "admin_panel":
        if not is_admin_user(inter):
            await inter.response.send_message("🚫 Unauthorized.", ephemeral=True)
            log_action(inter.user, "admin_panel", "DENIED")
            return

        embed = embed_base("🛠️ Admin Panel", "Control system trading below:")
        view = discord.ui.View()

        async def start_cb(i):
            global LIVE_TRADING
            LIVE_TRADING = True
            save_live_state()
            await i.response.edit_message(embed=embed_base("🟢 Trading Enabled", "Trading is now active."), view=None)
            ch = bot.get_channel(ALERT_CHANNEL_ID)
            if ch:
                await ch.send(f"🟢 Trading enabled by {i.user.mention}")
            await restart_service_safe()
            log_action(i.user, "Start Trading")

        async def stop_cb(i):
            global LIVE_TRADING
            LIVE_TRADING = False
            save_live_state()
            await i.response.edit_message(embed=embed_base("🔴 Trading Disabled", "Trading paused."), view=None)
            ch = bot.get_channel(ALERT_CHANNEL_ID)
            if ch:
                await ch.send(f"🔴 Trading stopped by {i.user.mention}")
            log_action(i.user, "Stop Trading")

        b1 = discord.ui.Button(label="🟢 Start Trading", style=discord.ButtonStyle.success)
        b2 = discord.ui.Button(label="🔴 Stop Trading", style=discord.ButtonStyle.danger)
        b1.callback = start_cb
        b2.callback = stop_cb
        view.add_item(b1)
        view.add_item(b2)

        await inter.response.send_message(embed=embed, view=view, ephemeral=True)
        log_action(inter.user, "Admin Panel Opened")

# ==========================================================
# SHUTDOWN / CLEANUP
# ==========================================================
async def send_offline_alert():
    ch = bot.get_channel(ALERT_CHANNEL_ID)
    if ch:
        embed = embed_base("🔴 EchoProPulse Offline",
                           f"Bot shutdown at {datetime.now(EST):%I:%M %p EST}")
        try:
            await ch.send(embed=embed)
        except Exception as e:
            print(f"⚠️ Failed to send offline alert: {e}")

async def graceful_shutdown():
    print("⚠️ Shutdown signal received.")
    await send_offline_alert()
    if session and not session.closed:
        await session.close()
    print("🧹 Shutdown complete.")
    await bot.close()

def handle_signal(sig, frame):
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(graceful_shutdown())
    except RuntimeError:
        asyncio.run(graceful_shutdown())

signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)

#==========================================================
# GITHUB AUTO-UPDATE NOTIFIER
#==========================================================
import aiohttp

GITHUB_REPO = "missxtina11/EchoProPulse"  # 👈 replace with your actual repo
LAST_COMMIT_FILE = "/root/EchoProPulse/discord_bot/last_commit.txt"

async def check_github_updates():
    """Daily check for new commits on GitHub."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/commits/main"
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url) as r:
                if r.status == 200:
                    data = await r.json()
                    latest = data["sha"]
                    old = ""
                    if os.path.exists(LAST_COMMIT_FILE):
                        with open(LAST_COMMIT_FILE) as f:
                            old = f.read().strip()
                    if latest != old:
                        with open(LAST_COMMIT_FILE, "w") as f:
                            f.write(latest)
                        ch = bot.get_channel(ALERT_CHANNEL_ID)
                        if ch:
                            await ch.send(embed=embed_base(
                                "🔔 Update Available",
                                f"New commit detected on **{GITHUB_REPO}**\n"
                                f"Commit SHA: `{latest[:7]}`\nPull latest to update EchoProPulse."))
                            print("🆕 GitHub update alert sent.")
    except Exception as e:
        print(f"⚠️ GitHub update check failed: {e}")

# ==========================================================
# RUN BOT
# ==========================================================
def run_discord_bot():
    print(f"✅ Starting EchoProPulse Discord Bot ({VERSION})")
    print(f"🔍 Token found? {'YES' if DISCORD_TOKEN else 'NO'}")
    if not DISCORD_TOKEN:
        print("❌ Missing DISCORD_BOT_TOKEN in .env")
        sys.exit(1)
    print("=======================================")
    print("✅ Environment Loaded Successfully")
    print(f"🔹 Wallet: {SOLANA_WALLET}")
    print(f"🔹 Admin ID: {ADMIN_ID}")
    print(f"🔹 Channel ID: {ALERT_CHANNEL_ID}")
    print(f"🔹 Version: {VERSION}")
    print("=======================================")

    try:
        bot.run(DISCORD_TOKEN, reconnect=True)
    except Exception as e:
        log_error_to_discord(f"Startup failed: {e}")
        print(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_discord_bot()
