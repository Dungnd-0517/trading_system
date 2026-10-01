import math
from dataclasses import dataclass


@dataclass(frozen=True)
class RiskDecision:
    allowed: bool
    reason: str


@dataclass
class SymbolSpec:
    tick_size: float = 0.01
    tick_value: float = 1.0
    volume_min: float = 0.01
    volume_max: float = 100.0
    volume_step: float = 0.01


def lot_size(balance: float, risk_pct: float, entry: float, stop_loss: float, spec: SymbolSpec) -> float:
    risk_money = balance * risk_pct / 100
    per_lot = abs(entry - stop_loss) / spec.tick_size * spec.tick_value
    if per_lot <= 0 or spec.volume_step <= 0:
        return 0.0
    lots = math.floor(risk_money / per_lot / spec.volume_step) * spec.volume_step
    lots = min(lots, spec.volume_max)
    return round(lots, 2) if lots >= spec.volume_min else 0.0


def check_order(risk_amount: float, equity: float, daily_loss_pct: float, max_risk_pct: float = 1.0) -> RiskDecision:
    if equity <= 0 or risk_amount < 0 or daily_loss_pct < 0:
        return RiskDecision(False, "Invalid risk or equity values")
    if daily_loss_pct >= 5.0:
        return RiskDecision(False, "Daily loss limit reached")
    if risk_amount / equity * 100 > max_risk_pct:
        return RiskDecision(False, "Order risk exceeds configured limit")
    return RiskDecision(True, "ok")