from collections.abc import Iterable


def summarize_trades(pnls: Iterable[float]) -> dict[str, float | int]:
    values = list(pnls)
    wins = [value for value in values if value > 0]
    losses = [value for value in values if value < 0]
    gross_loss = abs(sum(losses))
    equity_peak = 0.0
    equity = 0.0
    max_drawdown = 0.0
    for value in values:
        equity += value
        equity_peak = max(equity_peak, equity)
        max_drawdown = max(max_drawdown, equity_peak - equity)
    return {
        "total_trades": len(values),
        "win_trades": len(wins),
        "loss_trades": len(losses),
        "winrate": len(wins) / len(values) * 100 if values else 0.0,
        "profit_factor": sum(wins) / gross_loss if gross_loss else (float("inf") if wins else 0.0),
        "total_pnl": sum(values),
        "max_drawdown": max_drawdown,
    }