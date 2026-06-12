"""Indicator calculations for the Forex bot."""

from __future__ import annotations

import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator


def apply_indicators(data: pd.DataFrame) -> pd.DataFrame:
    """Compute RSI + EMA indicators and return a trimmed DataFrame."""
    data = data.copy()

    close = data["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]

    if getattr(close, "ndim", 1) == 2:
        close = pd.Series(close[:, 0], index=data.index)

    data["rsi"] = RSIIndicator(close, window=14).rsi()
    data["ema50"] = EMAIndicator(close, window=50).ema_indicator()
    data["ema200"] = EMAIndicator(close, window=200).ema_indicator()

    data = data.dropna()

    if data.empty:
        raise RuntimeError(
            "Not enough data to compute indicators (RSI/EMA). "
            "Need at least EMA200 window worth of valid bars."
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

    if rsi < 45 and ema50 > ema200:
        return "BUY 📈"
    if rsi > 55 and ema50 < ema200:
        return "SELL 📉"
    return "NO SIGNAL ⚪"

