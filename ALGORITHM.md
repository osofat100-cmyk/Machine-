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
