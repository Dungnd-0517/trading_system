from dataclasses import dataclass


@dataclass(frozen=True)
class StrategySuggestion:
    risk_multiplier: float
    stop_loss_multiplier: float
    trading_allowed: bool
    rationale: str


def suggest_parameters(atr: float, baseline_atr: float, high_impact_news: bool = False) -> StrategySuggestion:
    if atr <= 0 or baseline_atr <= 0:
        raise ValueError("ATR values must be positive")
    if high_impact_news:
        return StrategySuggestion(0.0, 1.0, False, "High-impact event: pause paper entries")
    volatility_ratio = atr / baseline_atr
    if volatility_ratio >= 1.8:
        return StrategySuggestion(0.5, 1.5, True, "Elevated volatility: halve size and widen stop")
    if volatility_ratio >= 1.3:
        return StrategySuggestion(0.75, 1.25, True, "Volatility above baseline")
    return StrategySuggestion(1.0, 1.0, True, "Volatility within normal range")