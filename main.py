"""Entrypoint for the modular Forex Telegram bot."""

from __future__ import annotations

import logging
from datetime import datetime

import pandas as pd

from config import STATE_FILE, SYMBOLS
from data import get_data
from indicators import (
    apply_indicators,
    get_candlestick_pattern_alerts,
    get_macd_crossover_alert,
    get_signal,
    get_support_resistance_alert,
    get_trend_filter,
    _compute_recent_levels,
)

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
    state: BotState = load_state(STATE_FILE)

    # (symbol, message_line)
    alerts: list[tuple[str, str]] = []


    # Loop through pairs and compute indicators for each.
    for symbol in SYMBOLS:
        logger.info("Processing %s", symbol)
        try:
            df = get_data(symbol)
            df = apply_indicators(df)

            latest = df.iloc[-1]
            prev_row = df.iloc[-2] if len(df) >= 2 else latest
            # Keep existing RSI/EMA BUY/SELL signal logic
            signal = get_signal(latest)
            price = _to_float(latest["Close"])  # current market price
            rsi = _to_float(latest["rsi"])
            ema50 = _to_float(latest["ema50"])
            ema200 = _to_float(latest["ema200"])

            if signal in ("BUY 📈", "SELL 📉"):
             alerts.append(
        (
            symbol,
            signal,
            price,
            rsi,
            ema50,
            ema200,
        )
    )
            # MACD crossover alerts
            macd_alert = get_macd_crossover_alert(prev_row, latest)
            if macd_alert:
                alerts.append((symbol, macd_alert))

            # Trend filter (EMA50 vs EMA200)
            trend_alert = get_trend_filter(latest)
            if trend_alert:
                alerts.append((symbol, trend_alert))

            # Support & Resistance
            df_levels = _compute_recent_levels(df, lookback=20)
            sr_alerts = get_support_resistance_alert(df_levels, latest, lookback=20, near_threshold_pct=0.25)
            alerts.extend([(symbol, a) for a in sr_alerts])

            # Candlestick patterns
            candle_alerts = get_candlestick_pattern_alerts(prev_row, latest)
            alerts.extend([(symbol, a) for a in candle_alerts])

        except Exception:
            logger.exception("Failed computing indicators for %s", symbol)

    if not alerts:
        logger.warning("No symbols produced signals; nothing to send")
        return

    # Send signal only when conditions are met (BUY/SELL).
    logger.info("Total alerts collected: %s", len(alerts))

    for item in alerts:
     logger.info("Alert item: %s", item)
    actionable = [a for a in alerts if len(a) == 6 and a[1] in ("BUY 📈", "SELL 📉")]
    if not actionable:
        send_telegram("📊 Scan completed.\n\nNo BUY/SELL signals found.")
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

    # Prevent duplicate alerts: de-dup on full actionable message set.
    dedup_key = "|".join([str(alert) for alert in actionable])

    if state.last_signal == dedup_key:
        logger.info("Skipping duplicate alerts. last_signal=%s", dedup_key)
        return

    logger.info("Sending actionable signal update")

    try:
        send_telegram(message)
    except Exception:
        logger.exception("Telegram send failed; not updating state")
        raise
    new_state = BotState(last_signal=dedup_key)
    save_state(STATE_FILE, new_state)


if __name__ == "__main__":
    run_bot()

