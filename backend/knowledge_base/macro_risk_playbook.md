# MACRO RISK MANAGEMENT & NEWS CIRCUIT BREAKER PLAYBOOK

## 1. High-Impact Macroeconomic Events for Gold (XAUUSD)
Gold is intensely sensitive to US real yields, USD strength, and monetary policy expectations.
- **Top-Tier Events (3-Star / Red Flags)**:
  - US Consumer Price Index (CPI) and Core CPI.
  - US Non-Farm Payrolls (NFP) and Unemployment Rate.
  - FOMC Interest Rate Decision, Economic Projections, and Press Conference.
  - US GDP Preliminary/Advanced Reports.
- **Geopolitical Shocks**: Sudden military escalations or banking liquidity crises trigger immediate flight to safety (gold surges regardless of technical resistance).

## 2. News Circuit Breaker Protocol
- **Hard Freeze Buffer**: All new automated trade execution MUST be completely halted 30 minutes before and 30 minutes after any scheduled 3-star economic event.
- **Pending Orders Cancellation**: Cancel all pending limit orders (Buy Limits, Sell Limits) 15 minutes before the release to prevent slippage fills during wide spreads.
- **Existing Position Protection**: If an open position is in profit >= 1.5R, move Stop Loss to Breakeven prior to the event. If in slight loss, reduce position size by 50% or enforce tight trailing.

## 3. Dynamic Volatility & ATR Stop Loss Adaptation
- **Normal Volatility Regime**: ATR(14) on M15 is within 15-25 points. Standard Stop Loss multiplier is `1.50 * ATR`.
- **High Volatility Regime (News/Geopolitical)**: ATR(14) expands above 35 points. Stop Loss multiplier must be dynamically increased to `2.00 - 2.50 * ATR`, and lot size must be inversely scaled down to keep total risk at or below 1.0% of account balance.
- **Capital Preservation Rules**:
  - Maximum account risk per trade: `1.0%` (can be throttled down to `0.5%` during chop).
  - Maximum concurrent open positions: `2`.
  - Daily Max Drawdown Circuit Breaker: If cumulative daily loss reaches `3.0%`, all trading is locked for the remainder of the 24-hour cycle.
