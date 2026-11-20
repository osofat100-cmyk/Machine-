# The PEARL rule

P = price now

**Holding USDC**
- L = lowest P since we sold
- BUY when P ≥ L × (1 + RISE)

**Holding PEARL**
- B = price we bought at, H = highest P since we bought
- If H ≥ B × 1.016 (up 1.6%, profit locked):
  SELL when P ≤ max( B × 1.015 , H × (1 − TRAIL) )
- Otherwise:
  SELL when P ≤ H × (1 − STOP)

Default settings: RISE 7%, TRAIL 3%, STOP 5%. Run it: `python3 pearl_bot.py`
(practice money). Test other settings: `python3 backtest.py --file data/PEARL-USDC_min1.csv`.
