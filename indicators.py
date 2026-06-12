"""Indicator calculations for the Forex bot."""

from __future__ import annotations

import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, MACD


def apply_indicators(data: pd.DataFrame) -> pd.DataFrame:
    """Compute RSI + EMA + MACD and return a trimmed DataFrame."""
    data = data.copy()

    close = data["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]

    if getattr(close, "ndim", 1) == 2:
        close = pd.Series(close[:, 0], index=data.index)

    data["rsi"] = RSIIndicator(close, window=14).rsi()
    data["ema50"] = EMAIndicator(close, window=50).ema_indicator()
    data["ema200"] = EMAIndicator(close, window=200).ema_indicator()

    # ta.MACD uses `window_sign` (not window_signals) in some versions.
    macd = MACD(close=close, window_slow=26, window_fast=12, window_sign=9)
    data["macd_line"] = macd.macd()
    data["macd_signal"] = macd.macd_signal()
    data["macd_hist"] = macd.macd_diff()


    data = data.dropna()

    if data.empty:
        raise RuntimeError(
            "Not enough data to compute indicators (RSI/EMA/MACD). "
            "Need enough bars for the largest window (EMA200) to be valid."
        )

    return data


def get_signal(latest: pd.Series) -> str:
    """Convert latest indicator values into a trading signal."""
    rsi_val = latest["rsi"]
    ema50_val = latest["ema50"]
    ema200_val = latest["ema200"]

    # Ensure scalars
    if isinstance(rsi_val, pd.Series):
        rsi_val = rsi_val.iloc[0]
    if isinstance(ema50_val, pd.Series):
        ema50_val = ema50_val.iloc[0]
    if isinstance(ema200_val, pd.Series):
        ema200_val = ema200_val.iloc[0]

    rsi = float(rsi_val)
    ema50 = float(ema50_val)
    ema200 = float(ema200_val)

    if rsi < 50 and ema50 > ema200:
        return "BUY 📈"
    if rsi > 50 and ema50 < ema200:
        return "SELL 📉"
    return "NO SIGNAL ⚪"


def _scalar(x):
    if isinstance(x, pd.Series):
        return x.iloc[0]
    return x


def get_trend_filter(latest: pd.Series) -> str | None:
    """Trend filter based on EMA50 vs EMA200."""
    ema50 = float(_scalar(latest["ema50"]))
    ema200 = float(_scalar(latest["ema200"]))
    if ema50 > ema200:
        return "TREND: BULLISH ✅ (EMA50 > EMA200)"
    if ema50 < ema200:
        return "TREND: BEARISH ❌ (EMA50 < EMA200)"
    return None


def get_macd_crossover_alert(prev: pd.Series, latest: pd.Series) -> str | None:
    """Detect MACD line/signal crossovers."""
    prev_macd = float(_scalar(prev["macd_line"]))
    prev_sig = float(_scalar(prev["macd_signal"]))
    macd = float(_scalar(latest["macd_line"]))
    sig = float(_scalar(latest["macd_signal"]))

    # Bullish crossover: previously below signal, now above
    if prev_macd <= prev_sig and macd > sig:
        return "MACD CROSS: BULLISH 📈 (MACD line crossed above Signal)"

    # Bearish crossover: previously above signal, now below
    if prev_macd >= prev_sig and macd < sig:
        return "MACD CROSS: BEARISH 📉 (MACD line crossed below Signal)"

    return None


def _compute_recent_levels(df: pd.DataFrame, lookback: int) -> pd.DataFrame:
    """Adds recent high/low rolling levels for support/resistance detection."""
    out = df.copy()

    # Require OHLC for support/resistance + candlestick patterns.
    if "High" not in out.columns or "Low" not in out.columns:
        return out

    out["recent_high"] = out["High"].rolling(window=lookback, min_periods=lookback).max()
    out["recent_low"] = out["Low"].rolling(window=lookback, min_periods=lookback).min()
    return out


def get_support_resistance_alert(
    df_with_levels: pd.DataFrame,
    latest: pd.Series,
    lookback: int = 20,
    near_threshold_pct: float = 0.25,
) -> list[str]:
    """Detect recent highs/lows and alert when price is near key levels."""
    alerts: list[str] = []

    if "recent_high" not in df_with_levels.columns or "recent_low" not in df_with_levels.columns:
        return alerts
    if pd.isna(latest.get("recent_high")) or pd.isna(latest.get("recent_low")):
        return alerts

    price = float(_scalar(latest["Close"]))
    r_high = float(_scalar(latest["recent_high"]))
    r_low = float(_scalar(latest["recent_low"]))

    alerts.append(f"S/R: recent_high={r_high:.5f}, recent_low={r_low:.5f}")

    # Distance to levels (percentage of price)
    if r_high != 0:
        dist_high_pct = abs(price - r_high) / abs(price) * 100
        if dist_high_pct <= near_threshold_pct:
            alerts.append(
                f"Near Resistance: {r_high:.5f} (±{near_threshold_pct}%)"
            )

    if r_low != 0:
        dist_low_pct = abs(price - r_low) / abs(price) * 100
        if dist_low_pct <= near_threshold_pct:
            alerts.append(f"Near Support: {r_low:.5f} (±{near_threshold_pct}%)")

    return alerts


def _candle_body_size(c: pd.Series) -> float:
    return abs(float(_scalar(c["Close"])) - float(_scalar(c["Open"])))


def get_candlestick_pattern_alerts(prev: pd.Series, latest: pd.Series) -> list[str]:
    """Detect bullish/bearish engulfing, pin bars, doji."""
    alerts: list[str] = []

    required = ["Open", "Close", "High", "Low"]
    for col in required:
        if col not in prev.index or col not in latest.index:
            return alerts

    o1, c1, h1, l1 = (float(_scalar(prev[x])) for x in ("Open", "Close", "High", "Low"))
    o2, c2, h2, l2 = (float(_scalar(latest[x])) for x in ("Open", "Close", "High", "Low"))

    # Doji: very small body relative to range
    body2 = abs(c2 - o2)
    range2 = max(h2 - l2, 1e-12)
    if body2 / range2 <= 0.1:
        alerts.append("Candle: DOJI 🟦")

    # Pin bar: long wick and small body. Use heuristic based on wicks.
    upper_wick = h2 - max(o2, c2)
    lower_wick = min(o2, c2) - l2
    body_ratio = body2 / range2
    # Bullish pin bar: long lower wick, small body
    if body_ratio <= 0.25 and lower_wick / range2 >= 0.6:
        alerts.append("Candle: BULLISH PIN BAR 🧱")
    # Bearish pin bar: long upper wick, small body
    if body_ratio <= 0.25 and upper_wick / range2 >= 0.6:
        alerts.append("Candle: BEARISH PIN BAR 🧱")

    # Engulfing patterns
    prev_bear = c1 < o1
    prev_bull = c1 > o1
    latest_bull = c2 > o2
    latest_bear = c2 < o2

    # Bullish engulfing: prev bear, latest bull, body engulfs previous body
    if prev_bear and latest_bull:
        if c2 >= o1 and o2 <= c1:
            alerts.append("Candle: BULLISH ENGULFING 🔔")

    # Bearish engulfing: prev bull, latest bear, body engulfs previous body
    if prev_bull and latest_bear:
        if c2 <= o1 and o2 >= c1:
            alerts.append("Candle: BEARISH ENGULFING 🔔")

    return alerts


