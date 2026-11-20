# Machine-

Tools for watching and practice-trading PEARL on BigONE. Nothing here places real orders.
Needs Python 3 only (no installs). See [PLAN.md](PLAN.md) for the research and the plan.

| File | What it does |
|---|---|
| `pearl_monitor.py` | Live price every second, logged to `logs/` |
| `fetch_history.py` | Downloads past prices into `data/` |
| `backtest.py` | Tests trading rules on past prices, with fees and spread included |
| `volatility.py` | How much PEARL moves in 1, 5, 10 and 60 minutes, spikes and drops |
| `paper_trader.py` | Runs the chosen rule live with fake money |
| `pearl_bot.py` | Runs the rules in ALGORITHM.md every second with fake money |
| `dip_bot.py` | Buy the crash, sell the pump (best result so far), fake money |
| `signals.py` | Searches history for high-odds buy and sell moments |
| `strategy.py` | The rules (normal + spike mode) and a second-by-second tester |
| `patterns.py` | Research: how far moves and spikes go before turning |
| `fetch_trades.py` | Downloads trade-by-trade history from Coinbase and Gate |

    python3 pearl_monitor.py                 # watch PEARL-USDC live
    python3 fetch_history.py --pair PEARL-USDT --period hour1 --days 150
    python3 backtest.py                      # test the rules on that history
    python3 paper_trader.py                  # practice trading, fake $1000

To try your own rule, add a function to `backtest.py` that returns 1 (hold PEARL)
or 0 (hold dollars) for each candle, and add it to `RULES`.
