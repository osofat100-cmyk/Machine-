# Machine-

Tools for watching and practice-trading PEARL on BigONE. Nothing here places real orders.
Robot 2 needs Python 3 with numpy and pandas. The plan is in [docs/machine_math.pdf](docs/machine_math.pdf); the checks and test results are in [docs/robot2_analysis.md](docs/robot2_analysis.md).

**Robot 2 (the main robot)**

| File | What it does |
|---|---|
| `engine.py` | Robot 2 itself: settings landscape, pick, update intervals, trajectory watcher, library |
| `live_machine.py` | Runs the engine on live BigONE minutes with practice money |
| `checks.py` | Structural checks of the engine (cost, no look-ahead, restart, ...) |
| `traj_sweep.py` | Chooses the watcher's sensitivity on early data, checks it on unseen data |
| `robustness.py` | Changes one assumption at a time to show how fragile the result is |
| `trajectories.py` | Chart of where the watcher splits the price history |
| `fetch_history.py` | Downloads minute prices into `data/` |
| `docs/machine_math.pdf` | The plan and its math |
| `docs/robot2_analysis.md` | What the checks found and the test results |

**Earlier experiments** (kept for reference; their results used a flat cost and thin-market fills)

| File | What it does |
|---|---|
| `robots.py`, `frozen.py` | Four-robot comparison; learn-a-month-then-freeze test |
| `machine_sim.py`, `machine_speed.py`, `machine_1to120.py` | First adaptive machine and the update-interval tests |
| `landscape.py`, `sweep.py`, `sweep_lines.py` | Settings landscape and the 1-100% sweeps |
| `signals.py`, `dip_bot.py` | Search that found the buy-the-crash rule, and its first bot |
| `patterns.py`, `strategy.py`, `pearl_bot.py`, `fetch_trades.py` | Spike research and the spike bot |
| `backtest.py`, `paper_trader.py`, `volatility.py` | First rules, the trend practice trader, movement report |
| `pearl_monitor.py` | Live price every second |

    python3 fetch_history.py --pair PEARL-USDT --period min1 --days 150
    python3 live_machine.py                  # robot 2, practice money
    python3 checks.py                        # verify the engine

To try your own rule, add a function to `backtest.py` that returns 1 (hold PEARL)
or 0 (hold dollars) for each candle, and add it to `RULES`.
