#!/usr/bin/env python3
# =====================================================
# ⚡ EchoProPulse v10 — Solana MEV Monitor Bot
# =====================================================
import os
import sys
import signal
import asyncio
import discord
import psutil
import platform
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from discord import app_commands, ButtonStyle, Embed
from discord.ext import commands, tasks
from discord.ui import View, Button
from dotenv import load_dotenv

# =====================================================
# 🔧 ENV & CONFIG
# =====================================================
load_dotenv("/root/EchoProPulse/discord_bot/.env")

VERSION = "v10"
EST = ZoneInfo("America/New_York")

DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))
ADMIN_ID = int(os.getenv("DISCORD_ADMIN_ID", "0"))
ADMIN_ROLE_ID = int(os.getenv("DISCORD_ADMIN_ROLE_ID", "0"))
MAIN_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))
LOGS_CHANNEL_ID = int(os.getenv("DISCORD_LOG_CHANNEL_ID", "0"))
VPS_CHANNEL_ID = int(os.getenv("DISCORD_VPS_CHANNEL_ID", "0"))
SOLANA_WALLET = os.getenv("SOLANA_WALLET", "Unknown")

LOG_FILE = "/root/EchoProPulse/discord_bot/bot.log"
HEARTBEAT_FILE = "/root/EchoProPulse/discord_bot/heartbeat.txt"
STATE_FILE = "/root/EchoProPulse/live_state.txt"

LIVE_TRADING = os.path.exists(STATE_FILE) and open(STATE_FILE).read().strip() == "true"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree

# =====================================================
# 🧩 IMPORT DISCORD NOTIFY HELPERS
# =====================================================
from discord_notify import notify_main, notify_logs, notify_vps

# =====================================================
# ⚙️ HELPERS
# =====================================================
def is_admin(inter):
    if inter.user.id == ADMIN_ID:
        return True
    return any(r.id == ADMIN_ROLE_ID for r in getattr(inter.user, "roles", []))

def save_state():
    with open(STATE_FILE, "w") as f:
        f.write(str(LIVE_TRADING).lower())

async def post_log(msg: str, channel_id: int = LOGS_CHANNEL_ID):
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

# =====================================================
# 🎛️ CONTROL PANEL VIEW
# =====================================================
class ControlPanel(View):
    def __init__(self, is_admin=False):
        super().__init__(timeout=None)

        # SYSTEM CONTROLS
        self.add_item(Button(label="📊 Status", style=ButtonStyle.success, custom_id="btn_status"))
        self.add_item(Button(label="🪵 Logs", style=ButtonStyle.secondary, custom_id="btn_logs"))
        self.add_item(Button(label="🔄 Restart", style=ButtonStyle.danger, custom_id="btn_restart"))

        # TRADING CONTROLS
        self.add_item(Button(label="💹 Toggle Trading", style=ButtonStyle.primary, custom_id="btn_power"))

        # ANALYTICS
        self.add_item(Button(label="📈 Diagnostics", style=ButtonStyle.success, custom_id="btn_diagnostics"))
        self.add_item(Button(label="👛 Wallets", style=ButtonStyle.secondary, custom_id="btn_wallets"))
        self.add_item(Button(label="📊 Holders", style=ButtonStyle.secondary, custom_id="btn_holders"))

        # ADMIN
        if is_admin:
            self.add_item(Button(label="🧩 Admin Panel", style=ButtonStyle.blurple, custom_id="btn_admin"))
            self.add_item(Button(label="🔁 Sync", style=ButtonStyle.success, custom_id="btn_sync"))
            self.add_item(Button(label="⛔ Shutdown", style=ButtonStyle.danger, custom_id="btn_shutdown"))

# =====================================================
# 🚀 BOT EVENTS
# =====================================================
@bot.event
async def on_ready():
    print(f"✅ EchoProPulse ({VERSION}) logged in as {bot.user}")

    notify_logs(f"🪵 ✅ **EchoProPulse {VERSION}** is now online and synced.")
    notify_logs(
        f"🟢 **EchoProPulse {VERSION} started**\n"
        f"💰 Wallet: `{SOLANA_WALLET}`\n"
        f"⚙️ Trading: {'ENABLED' if LIVE_TRADING else 'DISABLED'}"
    )
    notify_vps(f"🖥️ VPS heartbeat OK • Bot started cleanly at {datetime.now(EST):%I:%M %p EST}")

    try:
        guild = discord.Object(id=GUILD_ID)
        synced = await bot.tree.sync(guild=guild)
        print(f"✅ Synced {len(synced)} commands for guild {GUILD_ID}")
        notify_logs(f"🧩 Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"⚠️ Sync failed: {e}")
        notify_logs(f"⚠️ Command sync failed: `{e}`")

    await write_heartbeat()

# =====================================================
# 🧠 SLASH COMMANDS (MEV-ONLY)
# =====================================================

@tree.command(name="start", description="Open the EchoProPulse MEV Control Center")
async def start(inter: discord.Interaction):
    embed = Embed(
        title=f"🚀 EchoProPulse Control Center ({VERSION})",
        description=f"💹 Manage MEV bot status and system diagnostics.\n🕒 {datetime.now(EST):%I:%M %p EST}",
        color=discord.Color.teal()
    )
    await inter.response.send_message(embed=embed, view=ControlPanel(is_admin=is_admin(inter)), ephemeral=True)

@tree.command(name="status", description="Check MEV bot status")
async def status_command(inter: discord.Interaction):
    trading = "🟢 Enabled" if LIVE_TRADING else "🔴 Disabled"
    embed = Embed(
        title=f"📊 EchoProPulse Status ({VERSION})",
        description=f"💹 Trading: {trading}\n💰 Wallet: `{SOLANA_WALLET}`",
        color=discord.Color.green() if LIVE_TRADING else discord.Color.red()
    )
    await inter.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="power", description="Toggle trading ON/OFF (Admin only)")
async def power_command(inter: discord.Interaction):
    global LIVE_TRADING
    if not is_admin(inter):
        await inter.response.send_message("🚫 Admin only.", ephemeral=True)
        return
    LIVE_TRADING = not LIVE_TRADING
    save_state()
    state_text = "⚡ Trading ENABLED" if LIVE_TRADING else "⛔ Trading DISABLED"
    await inter.response.send_message(state_text, ephemeral=True)
    notify_logs(f"⚙️ {inter.user.mention} toggled trading: {state_text}")

@tree.command(name="diagnostics", description="Run VPS diagnostics (Admin only)")
async def diagnostics(inter: discord.Interaction):
    if not is_admin(inter):
        await inter.response.send_message("🚫 Admin only.", ephemeral=True)
        return
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    embed = Embed(
        title="🧠 System Diagnostics",
        description=f"CPU: {cpu}% | MEM: {mem}% | DISK: {disk}%",
        color=0x2ECC71 if cpu < 70 else 0xE67E22 if cpu < 90 else 0xE74C3C
    )
    await inter.response.send_message(embed=embed, ephemeral=True)
    notify_logs(f"🧠 Diagnostics by {inter.user.mention}: CPU {cpu}%, MEM {mem}%, DISK {disk}%")

@tree.command(name="restart", description="Restart the EchoProPulse bot (Admin only)")
async def restart(inter: discord.Interaction):
    if not is_admin(inter):
        await inter.response.send_message("🚫 Admin only.", ephemeral=True)
        return
    await inter.response.send_message("🔄 Restarting EchoProPulse...", ephemeral=True)
    notify_logs(f"🔁 Restart initiated by {inter.user.mention}")
    os.system("systemctl restart echopropulse.service")

@tree.command(name="shutdown", description="Shutdown the EchoProPulse bot (Admin only)")
async def shutdown(inter: discord.Interaction):
    if not is_admin(inter):
        await inter.response.send_message("🚫 Admin only.", ephemeral=True)
        return
    notify_logs(f"⛔ Manual shutdown by {inter.user.mention}")
    await inter.response.send_message("⛔ Bot shutting down...", ephemeral=True)
    await bot.close()

# =====================================================
# 🖥️ VPS AUTO STATUS LOOP
# =====================================================
@tasks.loop(hours=1)
async def vps_status_report():
    try:
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        uptime = str(datetime.utcnow() - datetime.utcfromtimestamp(psutil.boot_time()))
        color = 0x00FF00 if cpu < 70 else 0xE67E22 if cpu < 90 else 0xE74C3C

        embed = Embed(title="🖥️ VPS Health Report", color=color)
        embed.add_field(name="💾 Memory", value=f"{mem:.1f}%", inline=True)
        embed.add_field(name="🔥 CPU", value=f"{cpu:.1f}%", inline=True)
        embed.add_field(name="📦 Disk", value=f"{disk:.1f}%", inline=True)
        embed.add_field(name="⏱️ Uptime", value=uptime.split('.')[0], inline=False)
        embed.set_footer(text=f"EchoProPulse v{VERSION} • {datetime.now(EST):%I:%M %p EST}")

        ch = bot.get_channel(VPS_CHANNEL_ID)
        if ch:
            await ch.send(embed=embed)
            print(f"✅ VPS report sent to {VPS_CHANNEL_ID}")
    except Exception as e:
        print(f"❌ VPS report error: {e}")

@bot.event
async def on_ready():
    if not vps_status_report.is_running():
        vps_status_report.start()

# =====================================================
# 🧹 SHUTDOWN HANDLER
# =====================================================
async def graceful_shutdown():
    await post_log("🔴 EchoProPulse shutting down cleanly.", LOGS_CHANNEL_ID)
    print("🧹 Clean shutdown complete.")
    await bot.close()

def handle_signal(signum, frame):
    asyncio.run(graceful_shutdown())
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)

# =====================================================
# 🏁 RUN
# =====================================================
def run():
    print(f"✅ Starting EchoProPulse {VERSION}")
    bot.run(DISCORD_TOKEN)

if __name__ == "__main__":
    run()
