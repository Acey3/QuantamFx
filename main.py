"""Entrypoint for the modular Forex Telegram bot."""

from __future__ import annotations

import logging
from datetime import datetime
from collections import defaultdict

import pandas as pd

from config import (
    STATE_FILE,
    SYMBOLS,
    ACCOUNT_BALANCE,
    RISK_PERCENT as CONFIG_RISK_PERCENT,
    STOP_LOSS_PIPS as CONFIG_STOP_LOSS_PIPS,
    RISK_REWARD_RATIO,
)

from data import get_data, get_market_metadata
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
from risk import calculate_lot_size, calculate_risk_reward, suggest_take_profits
from database import init_db, log_scan, log_signal, log_alert

from risk_config import DEFAULT_PIP_VALUE_PER_LOT, DEFAULT_RISK_PERCENT, DEFAULT_REWARD_MULTIPLES

logger = logging.getLogger(__name__)


def _to_float(x) -> float:
    if isinstance(x, pd.Series):
        x = x.iloc[0]
    return float(x)


def run_bot() -> None:
    setup_logging()
    init_db()

    now_utc = datetime.utcnow()
    now_str = now_utc.replace(microsecond=0).isoformat() + "Z"
    state: BotState = load_state(STATE_FILE)

    # (symbol, message_line)
    all_alerts: list[tuple] = []
    closed_symbols: list[str] = []

    # Loop through pairs and compute indicators for each.
    for symbol in SYMBOLS:
        logger.info("Processing %s", symbol)
        
        # Check market status and get accurate price
        meta = get_market_metadata(symbol)
        if meta.status in ("CLOSED", "PRE", "POST"):
            logger.info("Market for %s is %s. Skipping.", symbol, meta.status)
            closed_symbols.append(symbol)
            continue

        try:
            df = get_data(symbol)
            df = apply_indicators(df)

            latest = df.iloc[-1]
            
            # Check for stale data
            bar_time = latest.name
            if hasattr(bar_time, "date"):
                if meta.status == "REGULAR" and bar_time.date() < now_utc.date():
                    logger.info("Market for %s is open but no new bars for today yet. (Latest bar: %s)", symbol, bar_time)
                    continue

            prev_row = df.iloc[-2] if len(df) >= 2 else latest
            
            # Store latest timestamp for de-duplication
            ts_str = str(latest.name)

            # Signal logic
            signal = get_signal(latest)
            
            # Use metadata price if available for higher accuracy, fallback to bar close
            price = meta.price if meta.price else _to_float(latest["Close"])
            
            rsi = _to_float(latest["rsi"])
            ema50 = _to_float(latest["ema50"])
            ema200 = _to_float(latest["ema200"])
            macd_line = _to_float(latest["macd_line"])
            macd_signal = _to_float(latest["macd_signal"])

            # Log this signal state to DB
            log_signal(
                symbol=symbol,
                bar_time=ts_str,
                price=price,
                rsi=rsi,
                ema50=ema50,
                ema200=ema200,
                macd_line=macd_line,
                macd_signal=macd_signal,
                signal_type=signal,
                is_actionable=(signal in ("BUY 📈", "SELL 📉"))
            )

            if signal in ("BUY 📈", "SELL 📉"):
                all_alerts.append(
                    (
                        symbol,
                        signal,
                        price,
                        rsi,
                        ema50,
                        ema200,
                        ts_str
                    )
                )

            # MACD crossover alerts
            macd_alert = get_macd_crossover_alert(prev_row, latest)
            if macd_alert:
                all_alerts.append((symbol, macd_alert, ts_str))

            # Trend filter (EMA50 vs EMA200)
            trend_alert = get_trend_filter(latest)
            if trend_alert:
                all_alerts.append((symbol, trend_alert, ts_str))

            # Support & Resistance
            df_levels = _compute_recent_levels(df, lookback=20)
            sr_alerts = get_support_resistance_alert(df_levels, latest, lookback=20, near_threshold_pct=0.25)
            for a in sr_alerts:
                all_alerts.append((symbol, a, ts_str))

            # Candlestick patterns
            candle_alerts = get_candlestick_pattern_alerts(prev_row, latest)
            for a in candle_alerts:
                all_alerts.append((symbol, a, ts_str))

        except Exception:
            logger.exception("Failed computing indicators for %s", symbol)

    # Prevent duplicate alerts
    dedup_key = "|".join(sorted([str(a) for a in all_alerts]))

    if not all_alerts:
        logger.info("No alerts found.")
        log_scan("No alerts found")
        if len(closed_symbols) == len(SYMBOLS):
            if state.last_signal != "MARKETS_CLOSED":
                msg = "💤 Markets are currently closed. Bot is in standby."
                send_telegram(msg)
                save_state(STATE_FILE, BotState(last_signal="MARKETS_CLOSED"))
                log_alert(msg, "MARKETS_CLOSED")
        elif state.last_signal != "NONE":
            msg = "📊 Scan completed.\n\nNo trading signals found."
            send_telegram(msg)
            save_state(STATE_FILE, BotState(last_signal="NONE"))
            log_alert(msg, "NONE")
        return

    if state.last_signal == dedup_key:
        logger.info("Skipping duplicate alerts. last_signal=%s", dedup_key)
        log_scan(f"Duplicate alerts skipped: {dedup_key[:50]}...")
        return

    # Filter actionable (BUY/SELL) for the main formatted message
    actionable = [a for a in all_alerts if len(a) == 7 and a[1] in ("BUY 📈", "SELL 📉")]
    info_alerts = [a for a in all_alerts if len(a) < 7 or a[1] not in ("BUY 📈", "SELL 📉")]

    lines = ["📊 FOREX ALERTS", f"Time (UTC): {now_str}", ""]
    
    for alert in actionable:
        symbol, signal, price, rsi, ema50, ema200, ts = alert
        money_at_risk, lot_size = calculate_lot_size(
            balance=ACCOUNT_BALANCE,
            risk_percent=CONFIG_RISK_PERCENT,
            stop_loss_pips=CONFIG_STOP_LOSS_PIPS,
            pip_value_per_lot=DEFAULT_PIP_VALUE_PER_LOT,
        )
        take_profits = suggest_take_profits(CONFIG_STOP_LOSS_PIPS, reward_multiples=DEFAULT_REWARD_MULTIPLES)
        tp_1r_pips = take_profits.get(DEFAULT_REWARD_MULTIPLES[0])
        tp_2r_pips = take_profits.get(DEFAULT_REWARD_MULTIPLES[1]) if len(DEFAULT_REWARD_MULTIPLES) > 1 else None

        rr_1r = calculate_risk_reward(CONFIG_STOP_LOSS_PIPS, tp_1r_pips) if tp_1r_pips is not None else 0.0
        rr_2r = calculate_risk_reward(CONFIG_STOP_LOSS_PIPS, tp_2r_pips) if tp_2r_pips is not None else 0.0

        pip_size = 0.01 if "JPY" in symbol else 0.0001
        sl_price = price - (CONFIG_STOP_LOSS_PIPS * pip_size) if signal.startswith("BUY") else price + (CONFIG_STOP_LOSS_PIPS * pip_size)

        tp_1r_price = (price + (tp_1r_pips * pip_size) if signal.startswith("BUY") else price - (tp_1r_pips * pip_size)) if tp_1r_pips is not None else None
        tp_2r_price = (price + (tp_2r_pips * pip_size) if signal.startswith("BUY") else price - (tp_2r_pips * pip_size)) if tp_2r_pips is not None else None

        lines.append(f"Pair: {symbol}")
        lines.append(f"Signal: {signal}")
        lines.append(f"Price: {price:.5f}")
        lines.append(f"SL: {sl_price:.5f} (−{CONFIG_STOP_LOSS_PIPS:.1f} pips)")
        if tp_1r_price: lines.append(f"TP @1R: {tp_1r_price:.5f} (+{tp_1r_pips:.1f} pips) (RR={rr_1r:.2f})")
        if tp_2r_price: lines.append(f"TP @2R: {tp_2r_price:.5f} (+{tp_2r_pips:.1f} pips) (RR={rr_2r:.2f})")
        lines.append(f"Lot Size: {lot_size:.4f} | Risk: ${money_at_risk:.2f}")
        lines.append(f"RSI: {rsi:.2f} | EMA50/200: {ema50:.5f}/{ema200:.5f}")
        lines.append(f"Bar Time: {ts}")
        lines.append("")

    if info_alerts:
        if actionable:
            lines.append("--- Additional Info ---")
        else:
            lines.append("ℹ️ Market Updates (No BUY/SELL yet):")
        
        grouped = defaultdict(list)
        for a in info_alerts:
            grouped[a[0]].append(a[1])
        
        for sym, msg_list in grouped.items():
            lines.append(f"• {sym}:")
            for m in msg_list:
                lines.append(f"  - {m}")
            lines.append("")

    message = "\n".join(lines).rstrip() + "\n"

    try:
        send_telegram(message)
        save_state(STATE_FILE, BotState(last_signal=dedup_key))
        log_alert(message, dedup_key)
        log_scan("Success: Alert sent")
    except Exception:
        logger.exception("Telegram send failed")
        log_scan("Error: Telegram send failed")


if __name__ == "__main__":
    run_bot()
