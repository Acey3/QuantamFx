"""Entrypoint for the modular Forex Telegram bot."""

from __future__ import annotations

import logging
from datetime import datetime

import pandas as pd

from config import STATE_FILE, SYMBOLS
from data import get_data
from indicators import apply_indicators, get_signal
from logging_utils import setup_logging
from state import BotState, load_state, save_state
from telegram_bot import send_telegram

logger = logging.getLogger(__name__)


def _to_float(x) -> float:
    if isinstance(x, pd.Series):
        x = x.iloc[0]
    return float(x)


def run_bot() -> None:
    setup_logging()

    now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    prev: BotState = load_state(STATE_FILE)

    alerts: list[tuple[str, str, float, float, float, float]] = []

    # Loop through pairs and compute indicators for each.
    for symbol in SYMBOLS:
        logger.info("Processing %s", symbol)
        try:
            df = get_data(symbol)
            df = apply_indicators(df)

            latest = df.iloc[-1]
            signal = get_signal(latest)

            price = _to_float(latest["Close"])  # current market price
            rsi = _to_float(latest["rsi"])
            ema50 = _to_float(latest["ema50"])
            ema200 = _to_float(latest["ema200"])

            alerts.append((symbol, signal, price, rsi, ema50, ema200))
        except Exception:
            logger.exception("Failed computing indicators for %s", symbol)

    if not alerts:
        logger.warning("No symbols produced signals; nothing to send")
        return

    # Send signal only when conditions are met (BUY/SELL).
    actionable = [a for a in alerts if a[1] in ("BUY 📈", "SELL 📉")]
    if not actionable:
        logger.info("No actionable signals (BUY/SELL); nothing to send")
        return

    # Include pair name in alert.
    lines = ["📊 FOREX ALERTS", f"Time (UTC): {now}", ""]
    for symbol, signal, price, rsi, ema50, ema200 in actionable:
        lines.append(f"Pair: {symbol}")
        lines.append(f"Price: {price:.5f}")
        lines.append(f"RSI: {rsi:.2f}")
        lines.append(f"EMA50: {ema50:.5f}")
        lines.append(f"EMA200: {ema200:.5f}")
        lines.append(f"Signal: {signal}")
        lines.append("")

    message = "\n".join(lines).rstrip() + "\n"

    # Prevent duplicate alerts: de-dup on actionable set.
    dedup_key = "|".join([f"{sym}:{sig}" for sym, sig, *_ in actionable])
    if prev.last_signal == dedup_key:
        logger.info("Skipping duplicate alerts. last_signal=%s", dedup_key)
        return

    logger.info("Sending actionable signal update")

    try:
        send_telegram(message)
    except Exception:
        logger.exception("Telegram send failed; not updating state")
        raise

    save_state(STATE_FILE, BotState(last_signal=dedup_key))


if __name__ == "__main__":
    run_bot()

