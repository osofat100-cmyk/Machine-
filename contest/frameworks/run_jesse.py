"""Jesse 3.6.1 + jesse-ai/example-strategies (commit 7c91e0a), way B: Jesse's own backtest engine.

Candles: 25 Jun - 30 Sep history (warm-up only) + the sealed 1 Oct - 20 Nov minutes exported through the price
server (sealed.export_minutes; their open = previous close). Missing minutes = flat candle at the last close,
volume 0 (same rule as fetch_sealed.py). Spot, 1,000 USDT, fee 0.7% per side.

Timeframe rule (fixed before any run): the one in the strategy's docstring or its shipped results file;
TurtleRules' docstring is a 20-day breakout -> 1D; no timeframe documented -> 1h (the repo's most common one).
Strategies are unchanged copies of downloads/example-strategies/<name>/__init__.py in jesse_project/strategies/.

    venv_jesse/bin/python run_jesse.py
"""
import importlib
import os
import sys
import traceback

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import sealed  # noqa: E402

STRATS = {"Donchian": "6h", "IFR2": "1h", "KDJstrategy": "1D", "MACD_EMA": "1h", "RSI2": "3h",
          "SMACrossover": "3h", "SimpleBollinger": "1h", "TradingView_RSI": "1h", "TurtleRules": "1D",
          "DUAL_THRUST": "1h", "MAGen": "1h"}
EXCHANGE, SYMBOL = "Binance Spot", "PEARL-USDT"
DATA_ROUTES = {"DUAL_THRUST": ["4h"]}  # it reads 4h anchor candles; Jesse needs that declared (config)


def minutes(df):
    df = df.copy()
    df["t"] = pd.to_datetime(df["time"], utc=True)
    df = df.set_index("t")[["open", "high", "low", "close", "volume"]].astype(float)
    full = pd.date_range(df.index[0], df.index[-1], freq="min")
    df = df[~df.index.duplicated()].reindex(full)
    df["close"] = df["close"].ffill()
    for c in ("open", "high", "low"):
        df[c] = df[c].fillna(df["close"])
    df["volume"] = df["volume"].fillna(0.0)
    ts = (df.index.view("int64") // 10 ** 6).astype(np.float64)
    return np.column_stack([ts, df["open"], df["close"], df["high"], df["low"], df["volume"]])


def load():
    h = sealed.history_before_oct()
    hist = minutes(h[h["time"] >= pd.Timestamp("2026-06-26", tz="UTC")])  # Jesse needs a day-aligned start
    test = minutes(pd.read_csv(os.path.join(HERE, "data", "sealed_minutes.csv")))
    gap = int((test[0, 0] - hist[-1, 0]) // 60000)
    assert gap == 1, f"history and test not continuous ({gap})"
    return hist, test


def strategy_class(name):
    return getattr(importlib.import_module(f"strategies.{name}"), name)


def main():
    sys.path.insert(0, os.path.join(HERE, "jesse_project"))
    os.chdir(HERE)  # not inside jesse_project: Jesse treats strategies/ + storage/ as a Postgres project
    from jesse import research

    hist, test = load()
    key = f"{EXCHANGE}-{SYMBOL}"
    config = {"starting_balance": 1000, "fee": 0.007, "type": "spot", "exchange": EXCHANGE, "warm_up_candles": 0}
    for name, tf in STRATS.items():
        try:
            res = research.backtest(
                config, [{"exchange": EXCHANGE, "strategy": strategy_class(name), "symbol": SYMBOL, "timeframe": tf}],
                [{"exchange": EXCHANGE, "symbol": SYMBOL, "timeframe": t} for t in DATA_ROUTES.get(name, [])],
                {key: {"exchange": EXCHANGE, "symbol": SYMBOL, "candles": test}},
                warmup_candles={key: {"exchange": EXCHANGE, "symbol": SYMBOL, "candles": hist}})
            m = res["metrics"]
            end = m.get("finishing_balance", 1000 + m.get("net_profit", 0))
            trades = m.get("total", 0)
            print(f"{name:<16} {tf:>3}  trades {trades:>4}  end ${end:,.2f}", flush=True)
            sealed.record("Jesse 3.6.1 example-strategies", f"{name} ({tf})", "B", trades, end, "ran",
                          "Jesse engine fills at the deciding candle's close")
        except Exception as e:
            err = f"{type(e).__name__}: {e}".replace("\n", " ")[:300]
            print(f"{name:<16} {tf:>3}  ERROR {err}", flush=True)
            traceback.print_exc(limit=3)
            sealed.record("Jesse 3.6.1 example-strategies", f"{name} ({tf})", "B", "", None,
                          "does not run as shipped", err)


if __name__ == "__main__":
    main()
