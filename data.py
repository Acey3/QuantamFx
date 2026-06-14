"""Data retrieval for the Forex bot."""

from __future__ import annotations

import pandas as pd
import yfinance as yf
from dataclasses import dataclass

from config import INTERVAL, PERIOD, SYMBOLS


@dataclass
class MarketMetadata:
    status: str
    price: float | None = None
    bid: float | None = None
    ask: float | None = None


def get_market_metadata(symbol: str) -> MarketMetadata:
    """Fetch market status and latest price info."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        state = info.get("marketState", "UNKNOWN")

        # Mid-price is often more accurate for Forex
        bid = info.get("bid")
        ask = info.get("ask")
        price = info.get("regularMarketPrice")

        # Heuristic: if bid/ask are available, mid-price is best
        current_price = price
        if bid is not None and ask is not None and bid > 0 and ask > 0:
            current_price = (bid + ask) / 2

        return MarketMetadata(status=state, price=current_price, bid=bid, ask=ask)
    except Exception:
        return MarketMetadata(status="UNKNOWN")


def get_data(symbol: str) -> pd.DataFrame:
    """Fetch market data for a symbol and normalize it into a single-asset DataFrame."""
    ticker = yf.Ticker(symbol)
    
    # Use history instead of download for potentially better metadata handling
    data = ticker.history(
        period=PERIOD,
        interval=INTERVAL,
        auto_adjust=True,
    )

    if data is None or data.empty:
        # Fallback to download if history fails
        data = yf.download(
            symbol,
            period=PERIOD,
            interval=INTERVAL,
            auto_adjust=True,
            progress=False
        )

    if data is None or data.empty:
        raise RuntimeError(
            f"No data returned for {symbol} (period={PERIOD}, interval={INTERVAL})."
        )

    data = data.dropna()
    if data.empty:
        raise RuntimeError(f"Data is empty after dropna() for {symbol}.")

    # Ensure OHLC columns are present and properly named
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    # Standardize column names
    rename_map = {col: col.capitalize() for col in data.columns}
    data = data.rename(columns=rename_map)

    if "Close" not in data.columns:
        raise RuntimeError(
            f"Missing 'Close' column in data for {symbol}. "
            f"Columns={list(data.columns)}"
        )

    # Normalize columns to Series
    for col in ["Open", "High", "Low", "Close"]:
        if col in data.columns:
            series = data[col]
            if isinstance(series, pd.DataFrame):
                data[col] = series.iloc[:, 0]
            elif getattr(series, "ndim", 1) == 2:
                data[col] = series.iloc[:, 0]

    return data
