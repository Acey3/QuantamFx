"""Backtesting engine for the Forex bot.

Implements a simple deterministic backtest based on the bot's existing
signal-generation logic in indicators.py::get_signal().

Metrics:
- Total Trades
- Win Rate
- Profit Factor
- Max Drawdown

Trade model:
- Single open position at a time (no overlapping trades).
- Entry at close price of the signal candle.
- Fixed SL/TP distances from config.py defaults.

Outcome model (bar-based approximation):
- For BUY: TP reached if a future bar's High >= TP before a future bar's Low <= SL.
- For SELL: TP reached if a future bar's Low <= TP before a future bar's High >= SL.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any, List, Literal

import pandas as pd

from config import ACCOUNT_BALANCE, RISK_PERCENT, RISK_REWARD_RATIO, STOP_LOSS_PIPS
from data import get_data
from indicators import apply_indicators, get_signal
from risk import calculate_lot_size


TradeSide = Literal["BUY", "SELL"]


@dataclass(frozen=True)
class TradeResult:
    side: TradeSide
    entry_time: Any
    exit_time: Any
    entry_price: float
    exit_price: float
    pnl_cash: float
    outcome: Literal["WIN", "LOSS"]
    sl_price: float
    tp_price: float


@dataclass(frozen=True)
class BacktestMetrics:
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    profit_factor: float
    max_drawdown: float


def _pip_size(symbol: str) -> float:
    return 0.01 if "JPY" in symbol else 0.0001


def _to_float_scalar(x: Any) -> float:
    if isinstance(x, pd.Series):
        return float(x.iloc[0])
    return float(x)


def _extract_trade_side(signal: str) -> TradeSide | None:
    if signal == "BUY 📈":
        return "BUY"
    if signal == "SELL 📉":
        return "SELL"
    return None


def _simulate_one_trade(
    df: pd.DataFrame,
    symbol: str,
    start_idx: int,
    side: TradeSide,
    entry_price: float,
    lot_size: float,
    stop_loss_pips: float,
    risk_reward_ratio: float,
) -> TradeResult:
    pip_size = _pip_size(symbol)

    if side == "BUY":
        sl_price = entry_price - stop_loss_pips * pip_size
        tp_price = entry_price + (stop_loss_pips * risk_reward_ratio) * pip_size
    else:
        sl_price = entry_price + stop_loss_pips * pip_size
        tp_price = entry_price - (stop_loss_pips * risk_reward_ratio) * pip_size

    # Walk forward until TP or SL is hit.
    for j in range(start_idx + 1, len(df)):
        high = _to_float_scalar(df.iloc[j]["High"])
        low = _to_float_scalar(df.iloc[j]["Low"])

        if side == "BUY":
            tp_hit = high >= tp_price
            sl_hit = low <= sl_price
        else:
            tp_hit = low <= tp_price
            sl_hit = high >= sl_price

        # assume SL first for conservative backtesting if both hit
        if tp_hit and sl_hit:
            exit_price = sl_price
            pips_moved = (exit_price - entry_price) / pip_size
            pnl_cash = lot_size * pips_moved * 10.0
            return TradeResult(
                side=side,
                entry_time=df.index[start_idx],
                exit_time=df.index[j],
                entry_price=float(entry_price),
                exit_price=float(exit_price),
                pnl_cash=float(pnl_cash),
                outcome="LOSS",
                sl_price=float(sl_price),
                tp_price=float(tp_price),
            )

        if tp_hit:
            exit_price = tp_price
            pips_moved = (exit_price - entry_price) / pip_size
            pnl_cash = lot_size * pips_moved * 10.0
            return TradeResult(
                side=side,
                entry_time=df.index[start_idx],
                exit_time=df.index[j],
                entry_price=float(entry_price),
                exit_price=float(exit_price),
                pnl_cash=float(pnl_cash),
                outcome="WIN",
                sl_price=float(sl_price),
                tp_price=float(tp_price),
            )

        if sl_hit:
            exit_price = sl_price
            pips_moved = (exit_price - entry_price) / pip_size
            pnl_cash = lot_size * pips_moved * 10.0
            return TradeResult(
                side=side,
                entry_time=df.index[start_idx],
                exit_time=df.index[j],
                entry_price=float(entry_price),
                exit_price=float(exit_price),
                pnl_cash=float(pnl_cash),
                outcome="LOSS",
                sl_price=float(sl_price),
                tp_price=float(tp_price),
            )

    # end -> close at last close.
    last_close = _to_float_scalar(df.iloc[-1]["Close"])
    exit_price = last_close
    pips_moved = (exit_price - entry_price) / pip_size
    pnl_cash = lot_size * pips_moved * 10.0
    outcome: Literal["WIN", "LOSS"] = "WIN" if pnl_cash >= 0 else "LOSS"

    return TradeResult(
        side=side,
        entry_time=df.index[start_idx],
        exit_time=df.index[-1],
        entry_price=float(entry_price),
        exit_price=float(exit_price),
        pnl_cash=float(pnl_cash),
        outcome=outcome,
        sl_price=float(sl_price),
        tp_price=float(tp_price),
    )


def run_backtest(
    symbol: str,
    starting_balance: float = ACCOUNT_BALANCE,
    risk_percent: float = RISK_PERCENT,
    stop_loss_pips: float = STOP_LOSS_PIPS,
    risk_reward_ratio: float = RISK_REWARD_RATIO,
) -> tuple[BacktestMetrics, List[TradeResult]]:
    df = get_data(symbol)
    df = apply_indicators(df)

    for col in ["Open", "High", "Low", "Close"]:
        if col not in df.columns:
            raise RuntimeError(f"Missing {col} in data for {symbol}")

    equity = float(starting_balance)
    peak_equity = equity
    max_drawdown = 0.0

    trades: List[TradeResult] = []

    i = 0
    while i < len(df) - 2:
        latest = df.iloc[i]
        signal = get_signal(latest)
        side = _extract_trade_side(signal)

        if side is None:
            i += 1
            continue

        entry_price = _to_float_scalar(latest["Close"])

        _, lot_size = calculate_lot_size(
            balance=equity,
            risk_percent=risk_percent,
            stop_loss_pips=stop_loss_pips,
            pip_value_per_lot=10.0,
        )

        result = _simulate_one_trade(
            df=df,
            symbol=symbol,
            start_idx=i,
            side=side,
            entry_price=entry_price,
            lot_size=lot_size,
            stop_loss_pips=stop_loss_pips,
            risk_reward_ratio=risk_reward_ratio,
        )

        trades.append(result)
        equity += result.pnl_cash

        peak_equity = max(peak_equity, equity)
        if peak_equity > 0:
            dd = (peak_equity - equity) / peak_equity
            max_drawdown = max(max_drawdown, dd)

        exit_pos = df.index.get_loc(result.exit_time)
        i = int(exit_pos) + 1

    wins = sum(1 for t in trades if t.outcome == "WIN")
    losses = sum(1 for t in trades if t.outcome == "LOSS")
    total_trades = len(trades)

    win_rate = (wins / total_trades) * 100.0 if total_trades else 0.0

    profit_sum = sum(t.pnl_cash for t in trades if t.pnl_cash > 0)
    loss_sum = -sum(t.pnl_cash for t in trades if t.pnl_cash < 0)
    profit_factor = (profit_sum / loss_sum) if loss_sum > 0 else (float("inf") if profit_sum > 0 else 0.0)

    metrics = BacktestMetrics(
        total_trades=total_trades,
        wins=wins,
        losses=losses,
        win_rate=win_rate,
        profit_factor=float(profit_factor),
        max_drawdown=float(max_drawdown),
    )
    return metrics, trades


def _format_metrics(metrics: BacktestMetrics) -> str:
    pf = metrics.profit_factor
    pf_str = "inf" if pf == float("inf") else f"{pf:.4f}"
    return (
        f"Total Trades: {metrics.total_trades}\n"
        f"Win Rate: {metrics.win_rate:.2f}% ({metrics.wins}W/{metrics.losses}L)\n"
        f"Profit Factor: {pf_str}\n"
        f"Max Drawdown: {metrics.max_drawdown * 100:.2f}%"
    )


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run backtest for the bot strategy")
    parser.add_argument("--symbol", required=True, help="Ticker like EURUSD=X")
    parser.add_argument("--starting-balance", type=float, default=ACCOUNT_BALANCE)
    parser.add_argument("--risk-percent", type=float, default=RISK_PERCENT)
    parser.add_argument("--stop-loss-pips", type=float, default=STOP_LOSS_PIPS)
    parser.add_argument("--risk-reward-ratio", type=float, default=RISK_REWARD_RATIO)

    args = parser.parse_args(argv)

    metrics, _trades = run_backtest(
        symbol=args.symbol,
        starting_balance=args.starting_balance,
        risk_percent=args.risk_percent,
        stop_loss_pips=args.stop_loss_pips,
        risk_reward_ratio=args.risk_reward_ratio,
    )

    print(_format_metrics(metrics))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
