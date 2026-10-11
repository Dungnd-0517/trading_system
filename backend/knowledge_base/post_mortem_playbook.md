# REFLEXION ENGINE POST-MORTEM TAXONOMY & LESSONS LEARNED

## 1. Root Cause Classification Categories
When a trade hits Stop Loss or experiences unexpected drawdown, the Reflexion Agent categorizes the failure under one of the following root causes:

### Category: EARLY_ENTRY
- **Symptoms**: Entering before candle closes to confirm structural change (CHoCH or BOS).
- **Root Cause**: Impatience and front-running lower-timeframe confirmations.
- **Rule to Add**: Always require a full candle body close on the M15 timeframe beyond the structural pivot before placing limit orders at the POI.

### Category: FOMO_CHASING
- **Symptoms**: Market execution after a large green/red displacement bar has already moved 40+ points away from the POI.
- **Root Cause**: Fear of missing out when seeing rapid price expansion.
- **Rule to Add**: If price has already moved past 50% of the projected move to the target, the setup is invalidated. Do not chase.

### Category: SL_TOO_TIGHT
- **Symptoms**: Stop Loss is tagged by a wick spike by 2-5 points before price reverses and flies to the Take Profit target.
- **Root Cause**: Placing Stop Loss exactly on the swing high/low without accounting for spread widening and ATR buffer.
- **Rule to Add**: Always add a minimum of `0.5 * ATR(14)` or 15 points beyond the swing structural level to absorb liquidity sweeps.

### Category: COUNTER_TREND_WITHOUT_HTF_ALIGNMENT
- **Symptoms**: Attempting to catch a top or bottom against a strong Higher Timeframe (H4/D1) trend.
- **Root Cause**: Treating lower-timeframe pullback signals as full trend reversals.
- **Rule to Add**: Counter-trend trades are strictly capped at 0.5% risk and must only target the internal Equilibrium (50%) of the dealing range, not swing highs/lows.

### Category: TRADED_DURING_NEWS_SPIKE
- **Symptoms**: Severe slippage, massive spread expansion, instant stop-out within seconds of high-impact news.
- **Root Cause**: Failure to heed the News Circuit Breaker calendar alerts.
- **Rule to Add**: Mandatory execution halt when economic events have impact stars >= 3.
