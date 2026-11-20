# Best rule so far: buy the crash, sell the pump (`dip_bot.py`)
- **Buy** when PEARL has fallen 6.4%+ in the last 4 hours and is at its 4-hour low.
- **Sell** when it is 11.4%+ above its 4-hour low and near its 4-hour high (within 1.8%).

| Period | This rule | Just holding |
|---|---|---|
| Jul 02 – Jul 30 | $991 | $665 |
| Jul 30 – Aug 28 | $1,498 | $920 |
| Aug 28 – Sep 25 | $2,009 | $3,978 |
| Sep 25 – Oct 23 | $2,325 | $1,751 |
| Oct 23 – Nov 20 | $1,096 | $931 |
| All 5 months | $7,297 | $4,183 |

59 trades, 42 winners. Held normally 13 hours; normally 11 hours between trades.
Best trade +39.8%, worst −19.5%.

# The PEARL rule

## Normal mode
- **Holding USDC:** buy when the price rises 7% above its lowest point.
- **Holding PEARL, before +1.6%:** sell if it drops 5% from its highest point.
- **Holding PEARL, after +1.6%:** never sell below +1.5%. Sell when it drops 3% from its highest point.

## Spike mode (a fast move within 30 seconds)
- **Fast drop of 5%, holding USDC:** buy. Sell at +2%, or at −10%, or after 30 minutes.
- **Fast rise of 2%, holding PEARL:** sell right away.
- **Fast rise of 2%, holding USDC:** don't buy for 10 minutes.

## Research behind it (`patterns.py`)
| | |
|---|---|
| Fast rise of 2%+ in 10–60 s | turned back 1.6% first 75–93% of the time |
| Fast drop of 2%+ in 10–60 s | bounced 1.6% first 75–100% of the time |
| Up-move once it's +3% | went 1.6% more 60% of the time (BigONE, 5 months) |
| Up-move once it's +5% | went 1.6% more 80% of the time, but turns give back 5% |

## Test results (1.4% cost per round trip)
| Data | Spikes only | Normal only | Both | Just holding |
|---|---|---|---|---|
| Coinbase Nov 13–20 | $1,020 | $420 | $726 | $1,299 |
| Gate Nov 6–13 | $1,016 | $701 | $753 | $883 |

Run: `python3 pearl_bot.py` or `python3 pearl_bot.py --spikes-only` (practice money).
