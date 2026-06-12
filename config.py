"""Configuration for the Forex Telegram bot."""

SYMBOLS = [
    "GC=F",      # Gold futures (Yahoo)


    "EURUSD=X",   # EUR/USD
    "GBPUSD=X",   # GBP/USD

    "USDJPY=X",   # USD/JPY
    "AUDUSD=X",   # AUD/USD
    "USDCAD=X",   # USD/CAD
    "NZDUSD=X",   # NZD/USD
    "EURGBP=X",   # EUR/GBP
    "GBPJPY=X",   # GBP/JPY
]

PERIOD = "5d"
INTERVAL = "15m"


# Telegram
# Prefer environment variables so the token is not stored in source code.
# Windows PowerShell example:
#   $env:TELEGRAM_TOKEN="..."
#   $env:TELEGRAM_CHAT_ID="..."

import os

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise RuntimeError(
        "Missing TELEGRAM_TOKEN and/or TELEGRAM_CHAT_ID environment variables."
    )


# Bot behavior
STATE_FILE = "bot_state.json"  # stores last alert to prevent duplicates


