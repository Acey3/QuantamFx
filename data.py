"""Data retrieval for the Forex bot."""

from __future__ import annotations

import pandas as pd
import yfinance as yf

from config import INTERVAL, PERIOD, SYMBOLS



def get_data(symbol: str) -> pd.DataFrame:
    """Fetch market data for a symbol and normalize it into a single-asset DataFrame."""
    data = yf.download(
        symbol,
        period=PERIOD,

        interval=INTERVAL,
        auto_adjust=True,
    )

    if data is None or data.empty:
        raise RuntimeError(
            f"No data returned by yfinance for {symbol} (period={PERIOD}, interval={INTERVAL})."
        )


    data = data.dropna()

    if data.empty:
        raise RuntimeError(f"Data is empty after dropna() for {symbol}.")


    if "Close" not in data.columns:
        raise RuntimeError(
            f"Missing 'Close' column in yfinance response for {symbol}. "
            f"Columns={list(data.columns)}"
        )


    # Normalize Close to a 1D Series
    close = data["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]

    if getattr(close, "ndim", 1) == 2:
        close = pd.Series(close[:, 0], index=data.index)

    data = data.copy()
    data["Close"] = close
    return data

