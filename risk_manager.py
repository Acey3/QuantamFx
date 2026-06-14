"""Risk management calculator used by the Forex bot.

This module provides a single function to compute:
- amount of money at risk
- suggested lot size
- take profit distance (in pips)

It is intentionally lightweight and production-ready (type hints + validation).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TradePlan:
    money_risked: float
    lot_size: float
    stop_loss_pips: float
    take_profit_pips: float
    risk_reward_ratio: float


def calculate_trade_plan(
    account_balance: float,
    risk_percent: float,
    stop_loss_pips: float,
    risk_reward_ratio: float,
    pip_value: float = 10.0,
) -> TradePlan:
    """Calculate a basic FX risk trade plan.

    Formulae:
      money_risked = account_balance * (risk_percent / 100)
      lot_size = money_risked / (stop_loss_pips * pip_value)
      take_profit_pips = stop_loss_pips * risk_reward_ratio

    Args:
        account_balance: Account balance in account currency.
        risk_percent: Risk per trade in percent (e.g., 2 means 2%).
        stop_loss_pips: Stop loss distance in pips.
        risk_reward_ratio: R:R ratio (e.g., 2 means TP is 2x SL).
        pip_value: $ value per pip for 1 standard lot (default $10).

    Returns:
        TradePlan with computed money_risked, lot_size, SL/TP pips and RR.

    Raises:
        ValueError: on invalid inputs.
    """

    account_balance = float(account_balance)
    risk_percent = float(risk_percent)
    stop_loss_pips = float(stop_loss_pips)
    risk_reward_ratio = float(risk_reward_ratio)
    pip_value = float(pip_value)

    if account_balance <= 0:
        raise ValueError("account_balance must be > 0")
    if risk_percent <= 0:
        raise ValueError("risk_percent must be > 0")
    if stop_loss_pips <= 0:
        raise ValueError("stop_loss_pips must be > 0")
    if risk_reward_ratio <= 0:
        raise ValueError("risk_reward_ratio must be > 0")
    if pip_value <= 0:
        raise ValueError("pip_value must be > 0")

    money_risked = account_balance * (risk_percent / 100.0)
    lot_size = money_risked / (stop_loss_pips * pip_value)
    take_profit_pips = stop_loss_pips * risk_reward_ratio

    return TradePlan(
        money_risked=money_risked,
        lot_size=lot_size,
        stop_loss_pips=stop_loss_pips,
        take_profit_pips=take_profit_pips,
        risk_reward_ratio=risk_reward_ratio,
    )

