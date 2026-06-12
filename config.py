import os
from dotenv import load_dotenv

load_dotenv()

SYMBOLS = [
    "GC=F",
    "EURUSD=X",
    "GBPUSD=X",
    "USDJPY=X",
    "AUDUSD=X",
    "USDCAD=X",
    "NZDUSD=X",
    "EURGBP=X",
    "GBPJPY=X",
]

PERIOD = "5d"
INTERVAL = "15m"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise RuntimeError(
        "Missing TELEGRAM_TOKEN and/or TELEGRAM_CHAT_ID. Check your .env file."
    )

STATE_FILE = "bot_state.json"