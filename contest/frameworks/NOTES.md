# Contest group 5: big frameworks

Every number is in `../results.csv` (written with `sealed.record`). Code here; downloads, venvs and data are git-ignored.

| Framework | How | Script | Stand-ins (no program file edited) |
|---|---|---|---|
| Jesse 3.6.1 + jesse-ai/example-strategies 7c91e0a | B, Jesse's engine | `run_jesse.py` | candles from history (warm-up) + sealed export; strategy class passed directly (Jesse looks for `./strategies/<name>`); fills at the deciding candle's close |
| Hummingbot 20261118, V2 controllers (repo 3351ada) | B, Hummingbot's BacktestingEngineBase | `run_hummingbot_v2.py` | candle feeds built from the minutes, only finished candles, stamped at their close; BigONE trading rules; sells only from PEARL already held (spot); engine checks no USDT balance, so peak holding is reported and flagged |
| Hummingbot `scripts/simple_pmm.py` | A, price server | `run_simple_pmm.py` | SimplePMM's own methods + real BudgetChecker on a stand-in account; quote fills if the next minute's high/low reaches it, executed at the minute after that's close |
| OctoBot 2.1.1 + official tentacles | B, OctoBot IndependentBacktesting | `build_octobot_data.py`, `run_octobot.py` | data file written the way its history collector writes it, from history + sealed export; profiles copied with config changes; end value restated net of 0.7% exit cost |
| Zenbot 4.1.0 (docker `deviavir/zenbot:unstable`) | B, Zenbot `sim` | `load_zenbot_trades.py`, `run_zenbot.py` | MongoDB trades: 4 per minute (O, L/H, H/L, C); selector poloniex.PEARL-USDT (in its shipped product list); 0.7% = maker fee 0.15 + `--avg_slippage_pct 0.55` |
| Krypto-trading-bot, Superalgos, QuantConnect LEAN | not run | - | reasons in results.csv |

Settings rules fixed before the runs are in each script's docstring (timeframes for Jesse; $100 per quote = 82 PEARL
for simple_pmm / pmm_v1; grid and staggered ranges for OctoBot; grid bounds +-2% of the first close for
Hummingbot grid_strike, the backtest script's own rule).

Problems found and fixed in the harnesses (not in the programs) before recording:
- Jesse treats a folder with `strategies/` and `storage/` as a Postgres project, so it runs from outside it.
- Jesse needs a day-aligned start: history starting 16:38 gave doubled, mis-stamped higher-timeframe candles.
- Hummingbot candle timestamps were first in the wrong unit, so it tried Binance (HTTP 451); fixed.
- Hummingbot MM defaults leave `amounts_pct` as None; passing the defaults through the config validators
  (blank = equal split, as its own prompt says) makes them load.
- Zenbot's simresults.currency is already the whole account at the last close (first parse double-counted).
