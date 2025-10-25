import os, discord
from discord.ext import commands
from dotenv import load_dotenv
from ai_engine.ai_router import route_ai_analysis

load_dotenv()
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

@bot.command()
async def analyze(ctx):
    token_data = {"symbol": "STB", "price": 0.004, "volume24h": 150000}
    result = route_ai_analysis("chart", token_data)
    await ctx.send(result)

async def run_discord_bot():
    await bot.start(os.getenv("DISCORD_BOT_TOKEN"))
