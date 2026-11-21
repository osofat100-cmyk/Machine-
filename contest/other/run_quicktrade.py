"""Way B: quick-trade 8.0.0 (pip) ExampleStrategies in quick-trade's own backtest.

Settings from its README example: 15m candles, deposit 1000, bet=inf (whole deposit); commission 0.7% (the test's
cost). Each strategy with its own default arguments. Long only with the library's own convert_signal(SELL -> EXIT),
because the test allows no shorting. Candles start 1 Oct 00:00 (no pre-October rows, so nothing can trade before
1 Oct; indicators warm up in the first hours). Causality check: the strategy's signals on the first 70% of the
candles must equal its signals on all candles over that same stretch; if not, it looks ahead and is marked.

    venv312/bin/python run_quicktrade.py
"""
import inspect
import os
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import sealed  # noqa: E402
from quick_trade import utils  # noqa: E402
from quick_trade.trading_sys import ExampleStrategies  # noqa: E402

ARGS = {"strategy_2_sma": (55, 21)}          # README example values; others use their defaults


def candles():
    m = pd.read_csv(os.path.join(HERE, "data", "PEARL_USDT_1m.csv"), index_col=0, parse_dates=True)
    m = m[m.index >= pd.Timestamp("2026-10-01", tz="UTC")]
    d = m.resample("15min").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"})
    return d.dropna().reset_index(drop=True)


def signals(df, name):
    t = ExampleStrategies("PEARL/USDT", df=df.copy(), interval="15m")
    kw = {"plot": False} if "plot" in inspect.signature(getattr(t, name)).parameters else {}
    getattr(t, name)(*ARGS.get(name, ()), **kw)
    t.convert_signal(utils.SELL, utils.EXIT)
    return t


def main(only=None):
    df = candles()
    names = [n for n, _ in inspect.getmembers(ExampleStrategies, inspect.isfunction) if n.startswith("strategy_")
             and n not in ("strategy_collider", "strategy_diff")]
    cut = int(len(df) * 0.7)
    for name in names:
        if only and name not in only:
            continue
        try:
            t = signals(df, name)
            try:
                short = signals(df.iloc[:cut], name)
                a, b = list(t.returns[:cut - 5]), list(short.returns[:cut - 5])
                causal = (a == b) if len(a) == len(b) else None   # shorter series gave fewer signals: inconclusive
            except Exception:
                a = b = []
                causal = None                                    # check could not run on the shorter series
            out = t.backtest(deposit=1000, commission=0.7, bet=np.inf, plot=False, print_out=False, show=False)
            value = float(t.deposit_history[-1])
            n = int(t.trades)
            note = "quick-trade own backtest, 15m, long only (convert_signal), commission 0.7%"
            if causal is False:
                diff = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
                note = f"LOOKS AHEAD: signals change when later candles are added (first at candle {diff}); " + note
            if causal is None:
                note = "causality check could not run on 70% of the candles; " + note
            status = "ran (looks ahead, invalid)" if causal is False else "ran"
            print(f"{name:<34} {n:>4} trades  $1,000 -> ${value:,.2f}  causal={causal}", flush=True)
            sealed.record("quick-trade 8.0.0", name, "B", n, value, status, note)
        except Exception as e:
            err = f"{type(e).__name__}: {e}"[:160]
            print(f"{name:<34} ERROR {err}", flush=True)
            sealed.record("quick-trade 8.0.0", name, "B", "", None, "does not run as shipped", err)


if __name__ == "__main__":
    main(sys.argv[1:] or None)
