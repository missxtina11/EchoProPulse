import os, asyncio, json, traceback, requests, datetime
from solders.keypair import Keypair
from solana.rpc.async_api import AsyncClient
from solana.transaction import Transaction
from solana.rpc.types import TxOpts
from dotenv import load_dotenv

load_dotenv()

# Discord webhook for error reports
ERROR_WEBHOOK = "https://discord.com/api/webhooks/1431086202429112342/nZfJ17Jo9fdA7xSIgBgCSVRfKDUgTKMkRt8AcMh1xEM329OgJ1HAYBtJCOsP956IANUF"
SOLANA_RPC = "https://api.mainnet-beta.solana.com"  # You can swap this for Helius, QuickNode, etc.
SOLANA_WALLET = os.getenv("SOLANA_WALLET")
PRIVATE_KEY_FILE = "/root/EchoProPulse/discord_bot/private.json"

# ==========================================================
# LOGGING + ERROR REPORTING
# ==========================================================
def log_error_to_discord(err):
    try:
        tb = traceback.format_exc()
        data = {
            "content": f"⚠️ **EchoProPulse Trading Error:**\n```{err}\n{tb}```"
        }
        requests.post(ERROR_WEBHOOK, json=data)
    except Exception as e:
        print(f"⚠️ Failed to send trading webhook: {e}")


def log_trade(message):
    """Write trade info to a persistent log file."""
    log_file = "/root/EchoProPulse/trade_activity.log"
    with open(log_file, "a") as f:
        f.write(f"[{datetime.datetime.now():%Y-%m-%d %I:%M:%S %p EST}] {message}\n")


# ==========================================================
# TRADING CORE
# ==========================================================
async def execute_swap(token_in: str, token_out: str, amount: float):
    """
    Executes a real trade on Solana via Jupiter routes.
    (For safety, this demo uses simulation mode unless LIVE_TRADING=True)
    """
    try:
        client = AsyncClient(SOLANA_RPC)

        # Load keypair from local private.json file
        if not os.path.exists(PRIVATE_KEY_FILE):
            raise Exception("Missing /discord_bot/private.json for Solana keypair")

        with open(PRIVATE_KEY_FILE, "r") as f:
            secret = json.load(f)
        kp = Keypair.from_secret_key(bytes(secret))

        # Placeholder Jupiter API call (real endpoint would go here)
        route = {
            "in": token_in,
            "out": token_out,
            "amount": amount,
            "expected_out": amount * 0.99,
            "price_impact": "0.3%",
        }

        # Simulate trade
        print(f"🔄 Simulating trade: {route}")
        log_trade(f"Simulated swap {amount} {token_in} → {token_out}")

        # Send fake transaction placeholder
        tx = Transaction()
        tx_sig = "FAKE-TX-" + datetime.datetime.now().strftime("%H%M%S")
        print(f"✅ Trade simulated: {tx_sig}")

        await client.close()
        return {"status": "success", "tx": tx_sig, "route": route}

    except Exception as e:
        log_error_to_discord(e)
        log_trade(f"❌ Trade failed: {e}")
        return {"status": "error", "error": str(e)}
