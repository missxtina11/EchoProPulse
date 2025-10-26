∑ControlPanel#!/usr/bin/env python3
import os, sys, asyncio, subprocess, traceback, signal, discord, requests
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

from discord_notify import notify_main, notify_logs, notify_vps
import os
import discord
from discord import app_commands

# ===========================================
# 🎯 Slash Command Channel Restriction Helper (Final)
# ===========================================
ALLOWED_COMMAND_CHANNEL = int(os.getenv("DISCORD_CHANNEL_ID", "0"))

def restrict_to_main_channel():
    """Decorator that restricts slash commands to a specific channel."""
    def decorator(func):
        async def wrapper(interaction: discord.Interaction):
            # Restrict command execution to the allowed channel
            if interaction.channel_id != ALLOWED_COMMAND_CHANNEL:
                try:
                    await interaction.response.send_message(
                        f"⚠️ Commands can only be used in <#{ALLOWED_COMMAND_CHANNEL}>.",
                        ephemeral=True
                    )
                except Exception:
                    pass
                return
            # Call the original command
            return await func(interaction)

        # Copy metadata from the original function
        wrapper.__annotations__ = func.__annotations__
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator

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

    # =============================
    # 🔁 Command Sync (Guild-Scoped)
    # =============================
    guild = discord.Object(id=int(os.getenv("DISCORD_GUILD_ID", "0")))

    try:
        # Sync only to the current guild (your server)
        synced = await bot.tree.sync(guild=guild)
        print(f"✅ Synced {len(synced)} commands for guild {guild.id}")
        notify_logs(f"🧩 Synced {len(synced)} guild-only slash commands successfully.")
    except Exception as e:
        print(f"⚠️ Command sync failed: {e}")
        notify_logs(f"⚠️ Command sync failed: `{e}`")

    # Write heartbeat for watchdog
    await write_heartbeat()
    print("🫀 Heartbeat started.")

# =====================================================
# SLASH COMMANDS
# =====================================================

from discord.ui import View, Button

# Channel restrictions
MAIN_CHANNEL = int(os.getenv("DISCORD_CHANNEL_ID", "0"))
LOGS_CHANNEL = int(os.getenv("DISCORD_LOG_CHANNEL_ID", "0"))

# =====================================================
# INLINE BUTTON VIEW (Dynamic, Color-Coded)
# =====================================================

class ControlPanel(View):
    """Dynamic control panel that updates button colors based on trading state."""
    def __init__(self):
        super().__init__(timeout=None)
        self.refresh_buttons()

    def refresh_buttons(self):
        """Rebuild the button layout based on current trading state."""
        self.clear_items()

        # Status button (always blue)
        self.add_item(Button(label="📊 Status", style=discord.ButtonStyle.primary, custom_id="btn_status"))

        # Power button color/label based on LIVE_TRADING
        if LIVE_TRADING:
            self.add_item(Button(label="🟢 Power: ON", style=discord.ButtonStyle.success, custom_id="btn_power"))
        else:
            self.add_item(Button(label="🔴 Power: OFF", style=discord.ButtonStyle.danger, custom_id="btn_power"))

        # Logs and Admin buttons (neutral)
        self.add_item(Button(label="📜 Logs", style=discord.ButtonStyle.secondary, custom_id="btn_logs"))
        self.add_item(Button(label="🛠️ Admin Panel", style=discord.ButtonStyle.blurple, custom_id="btn_admin"))


# =====================================================
# INLINE BUTTON INTERACTION HANDLER (Refreshed)
# =====================================================

@bot.event
async def on_interaction(interaction: discord.Interaction):
    """Handle button clicks and dynamically refresh the panel."""
    if not interaction.data:
        return

    cid = interaction.data.get("custom_id")

    # Create a fresh updated panel for every interaction
    view = ControlPanel()

    if cid == "btn_status":
        await status_command(interaction)
    elif cid == "btn_power":
        await power_command(interaction)
        # After toggling, re-show updated panel
        embed = discord.Embed(
            title=f"⚙️ Trading State Updated",
            description=f"Now: {'🟢 **ON**' if LIVE_TRADING else '🔴 **OFF**'}",
            color=discord.Color.green() if LIVE_TRADING else discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    elif cid == "btn_logs":
        await interaction.response.send_message("🪵 Opening logs view...", ephemeral=True)
    elif cid == "btn_admin":
        await adminpanel(interaction)

# =====================================================
# SLASH COMMANDS
# =====================================================

@bot.tree.command(name="start", description="Open the EchoProPulse control panel")
@restrict_to_main_channel()
async def start(interaction: discord.Interaction):
    """Show the bot’s interactive control panel."""
    embed = discord.Embed(
        title=f"🚀 EchoProPulse Control Center (v{VERSION})",
        description=f"💹 Manage trading and monitor status below.\n🕒 <t:{int(__import__('time').time())}:t>",
        color=discord.Color.teal()
    )
    await interaction.response.send_message(embed=embed, view=ControlPanel(), ephemeral=True)

# =====================================================

@bot.tree.command(name="about", description="Show information about the bot")
@restrict_to_main_channel()
async def about(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 EchoProPulse Bot",
        description=f"**Version:** {VERSION}\n**Network:** Solana\n**Status:** Monitoring live wallet {SOLANA_WALLET}",
        color=discord.Color.blurple()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

# =====================================================

@bot.tree.command(name="status", description="Check bot health and connection")
@restrict_to_main_channel()
async def status_command(interaction: discord.Interaction):
    """Show bot’s online state and trading status."""
    trading = "🟢 Enabled" if LIVE_TRADING else "🔴 Disabled"
    embed = discord.Embed(
        title=f"📊 EchoProPulse Status (v{VERSION})",
        description=f"💹 Trading: {trading}\n💰 Wallet: `{SOLANA_WALLET}`",
        color=discord.Color.green() if LIVE_TRADING else discord.Color.red()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

# =====================================================
# ADMIN COMMANDS
# =====================================================

@bot.tree.command(name="power", description="Turn trading ON or OFF")
async def power_command(interaction: discord.Interaction):
    """Admin-only toggle for trading power state."""
    if not is_admin(interaction):
        await interaction.response.send_message("🚫 Unauthorized.", ephemeral=True)
        return

    global LIVE_TRADING
    LIVE_TRADING = not LIVE_TRADING
    save_state()

    state_text = "⚡ **Trading ON**" if LIVE_TRADING else "🛑 **Trading OFF**"
    await interaction.response.send_message(f"{state_text} (Set by {interaction.user.mention})", ephemeral=True)
    await post_log(f"⚙️ {interaction.user.mention} switched trading state: {state_text}")

# =====================================================

@bot.tree.command(name="adminpanel", description="Open the Admin Control Panel (main & logs channels only)")
async def adminpanel(interaction: discord.Interaction):
    """Displays admin-only controls."""
    if interaction.channel_id not in (MAIN_CHANNEL, LOGS_CHANNEL):
        await interaction.response.send_message(
            f"⚠️ This command can only be used in <#{MAIN_CHANNEL}> or <#{LOGS_CHANNEL}>.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🛠️ Admin Control Panel",
        description="Manage bot settings, trading state, and system tools.",
        color=discord.Color.orange()
    )
    await interaction.response.send_message(embed=embed, view=ControlPanel(), ephemeral=True)

# =====================================================
# INLINE BUTTON INTERACTION HANDLER
# =====================================================

@bot.event
async def on_interaction(interaction: discord.Interaction):
    """Handle button clicks and route to matching command logic."""
    if not interaction.data:
        return

    cid = interaction.data.get("custom_id")

    if cid == "btn_status":
        await status_command(interaction)
    elif cid == "btn_power":
        await power_command(interaction)
    elif cid == "btn_logs":
        await interaction.response.send_message("🪵 Opening logs view...", ephemeral=True)
    elif cid == "btn_admin":
        await adminpanel(interaction)

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
