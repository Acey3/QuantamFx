"""Risk management helpers for the Forex bot."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskInputs:
    balance: float
    risk_percent: float
    stop_loss_pips: float
    pip_value_per_lot: float = 10.0  # default for many FX pairs when account currency is USD


@dataclass(frozen=True)
class RiskOutputs:
    money_at_risk: float
    lot_size: float
    take_profit_pips_1r: float
    take_profit_price_1r: float | None
    risk_reward_1r: float
    take_profit_pips_2r: float
    take_profit_price_2r: float | None
    risk_reward_2r: float


def _validate_positive(name: str, v: float) -> None:
    if v <= 0:
        raise ValueError(f"{name} must be > 0; got {v}")


def calculate_lot_size(
    balance: float,
    risk_percent: float,
    stop_loss_pips: float,
    pip_value_per_lot: float = 10.0,
) -> tuple[float, float]:
    """Return (money_at_risk, lot_size).

    lot_size is computed as:
      money_at_risk = balance * (risk_percent/100)
      lot_size = money_at_risk / (stop_loss_pips * pip_value_per_lot)
    """
    _validate_positive("balance", float(balance))
    _validate_positive("risk_percent", float(risk_percent))
    _validate_positive("stop_loss_pips", float(stop_loss_pips))
    _validate_positive("pip_value_per_lot", float(pip_value_per_lot))

    money_at_risk = balance * (risk_percent / 100.0)
    risk_per_lot = stop_loss_pips * pip_value_per_lot

    if risk_per_lot <= 0:
        raise ValueError("Invalid stop_loss_pips/pip_value_per_lot resulting in non-positive risk_per_lot")

    lot_size = money_at_risk / risk_per_lot
    return money_at_risk, lot_size


def suggest_take_profits(stop_loss_pips: float, reward_multiples: tuple[float, ...] = (1.0, 2.0)) -> dict[float, float]:
    """Return mapping multiple -> take_profit_pips."""
    _validate_positive("stop_loss_pips", float(stop_loss_pips))
    out: dict[float, float] = {}
    for m in reward_multiples:
        if m <= 0:
            continue
        out[m] = stop_loss_pips * m
    return out


def calculate_risk_reward(stop_loss_pips: float, take_profit_pips: float) -> float:
    _validate_positive("stop_loss_pips", float(stop_loss_pips))
    _validate_positive("take_profit_pips", float(take_profit_pips))
    return take_profit_pips / stop_loss_pips

