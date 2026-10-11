# SMART MONEY CONCEPTS (SMC) & ICT TRADING RULES

## 1. Dealing Range and Equilibrium
The Dealing Range is formed by the current High and Low of the higher timeframe structure (H4/H1).
- **Equilibrium**: The exact 50% midpoint between the Swing High and Swing Low: `(High + Low) / 2`.
- **Discount Zone**: Any price level strictly BELOW Equilibrium (`Price < Equilibrium`). Long entries are only permitted in the Discount Zone.
- **Premium Zone**: Any price level strictly ABOVE Equilibrium (`Price > Equilibrium`). Short entries are only permitted in the Premium Zone.
- **Rule**: Never buy in the Premium Zone and never sell in the Discount Zone, regardless of lower timeframe signals.

## 2. Order Block (OB) Identification and Mitigation
An Order Block is the last opposite-direction candle before an aggressive displacement that breaks market structure (BOS or CHoCH).
- **Bullish Order Block**: The last bearish candle prior to a strong upward displacement breaking structure.
- **Bearish Order Block**: The last bullish candle prior to a strong downward displacement breaking structure.
- **Validation Criteria**: The displacement leg MUST create a Fair Value Gap (FVG) and cause a Break of Structure.
- **Entry Execution**: Wait for price to retrace and tap the Order Block. Stop Loss is set below the low of the Bullish OB (or above the high of the Bearish OB) with an ATR buffer.

## 3. Fair Value Gap (FVG) and Imbalance
A Fair Value Gap is a 3-candle price pattern where there is an imbalance between buyers and sellers:
- **Bullish FVG**: The low of Candle 3 does not overlap with the high of Candle 1 (`Low[3] > High[1]`). The gap between them must exceed `0.3 * ATR(14)`.
- **Bearish FVG**: The high of Candle 3 does not overlap with the low of Candle 1 (`High[3] < Low[1]`).
- **Consequent Encroachment (CE)**: The 50% midpoint of the FVG. Price frequently reacts strongly at the CE level.
- **Trade Execution**: Limit orders are placed at the top of the Bullish FVG (or bottom of the Bearish FVG), or at the 50% CE level with SL beyond the Candle 1 extremity.

## 4. Market Structure: BOS vs CHoCH
- **Fractal Swing High/Low**: Requires 3 lower candles on the left and 3 lower candles on the right (7-candle fractal window).
- **Break of Structure (BOS)**: A candle CLOSE beyond the previous Swing High in an uptrend (or Swing Low in a downtrend). BOS signifies trend continuation.
- **Change of Character (CHoCH)**: A candle CLOSE beyond the opposite swing level (e.g. price closes below the most recent higher low in an uptrend). CHoCH signals structural trend reversal.
- **Rule**: Candle wicks breaching a level without closing beyond it represent a Liquidity Sweep, NOT a BOS/CHoCH.

## 5. Liquidity Sweeps and Turtle Soup
Institutions seek liquidity where retail stop orders cluster.
- **Buy-Side Liquidity (BSL)**: Stops sitting above previous daily/session highs, equal highs (EQH).
- **Sell-Side Liquidity (SSL)**: Stops sitting below previous daily/session lows, equal lows (EQL).
- **Sweep Pattern**: Price thrusts past the liquidity pool, sweeps stops, but closes back inside the previous range with a long rejection wick.
- **Turtle Soup Setup**: Upon a verified sweep of Asian session high/low during London or NY AM, look for an immediate lower-timeframe CHoCH in the reverse direction.

## 6. Kill Zones and Timing
High-probability SMC setups require confluence between Price Level and Time Window.
- **London Kill Zone (02:00 - 05:00 NY / 13:00 - 16:00 ICT)**: Sets the daily high or low in 70% of trending days. Often creates the Judith Swing (false move) sweeping Asian range.
- **New York AM Kill Zone (07:00 - 10:00 NY / 18:00 - 21:00 ICT)**: Peak liquidity session. Major reactions to US economic releases and trend continuations.
- **Silver Bullet**: 03:00-04:00 NY, 10:00-11:00 NY, 14:00-15:00 NY. High probability 1R:2R scalping setups targeting the nearest opposing FVG.
