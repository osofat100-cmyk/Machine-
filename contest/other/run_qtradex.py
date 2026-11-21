"""Way B: QTradeX (GitHub source; the PyPI 1.4.0 wheel does not import) + every bot in QTradeX-AI-Agents, in QTradeX's
own backtest engine. The bots need that engine (Buy/Sell/Thresholds signals, its wallet), so way A is not possible.

Data: daily candles (QTradeX's default candle size) built from 25 Jun-30 Sep history + the sealed minutes walked from
the price server (sealed.export_minutes). Each bot gets exactly its own warm-up (autorange) of days before 1 Oct; trading
starts 1 Oct. Wallet 1,000 USDT, fee 0.7% per side. Each bot's shipped default tune (its __init__), not the tunes/ files.
Look-ahead: the engine computes Tulip indicators (causal) on the whole series and steps day by day; a market order fills
at that day's close, a price/threshold order inside that day's range.

    PYTHONPATH=stubs xvfb-run -a venv312/bin/python run_qtradex.py
"""
import glob
import importlib.util
import inspect
import os
import sys
import traceback

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import sealed  # noqa: E402
import qtradex as qx  # noqa: E402
from qtradex.core.backtest import backtest  # noqa: E402

OCT1 = int(pd.Timestamp("2026-10-01", tz="UTC").timestamp())
DAY = 86400


def daily():
    m = pd.read_csv(os.path.join(HERE, "data", "PEARL_USDT_1m.csv"), index_col=0, parse_dates=True)
    d = m.resample("1D").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}).dropna()
    d = d[d.index >= pd.Timestamp("2026-06-26", tz="UTC")]           # first full day
    return {"unix": np.array([int(t.timestamp()) for t in d.index], dtype=float),
            "open": d["Open"].values.astype(float), "high": d["High"].values.astype(float),
            "low": d["Low"].values.astype(float), "close": d["Close"].values.astype(float),
            "volume": d["Volume"].values.astype(float)}


def run_bot(cls, candles):
    bot = cls()
    warm = int(bot.autorange())
    begin = OCT1 - DAY * (warm + 1)
    if begin < candles["unix"][0]:
        return None, f"needs {warm} warm-up days, history before 1 Oct has {int((OCT1 - candles['unix'][0]) / DAY)}"
    data = qx.Data(exchange="bigone", asset="PEARL", currency="USDT", begin=begin, end=int(candles["unix"][-1]),
                   candle_size=DAY, placeholder=True)
    data.raw_candles = {k: v.copy() for k, v in candles.items()}
    data.begin, data.end = begin, int(candles["unix"][-1])
    wallet = qx.PaperWallet({"PEARL": 0, "USDT": 1000}, fee=0.7)
    _, raw, _ = backtest(bot, data, wallet, plot=False, show=False, return_states=True)
    first = raw["unix"][0]
    assert first >= OCT1, f"engine traded before 1 Oct ({first})"
    trades = [t for t in raw["trades"] if t is not None]
    # wallet.value() is QTradeX's blend of USDT and PEARL value (not dollars), so value it in USDT directly
    last = wallet["PEARL"] * candles["close"][-1] + wallet["USDT"]
    return (last, len(trades), pd.Timestamp(first, unit="s").date()), None


def main():
    candles = daily()
    for path in sorted(glob.glob(os.path.join(HERE, "downloads", "qtx_agents", "*.py"))):
        name = os.path.basename(path)[:-3]
        if name == "qi_indicators_test":
            continue
        try:
            spec = importlib.util.spec_from_file_location(f"qtx_{name}", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            classes = [c for _, c in inspect.getmembers(mod, inspect.isclass)
                       if issubclass(c, qx.BaseBot) and c is not qx.BaseBot and c.__module__ == mod.__name__]
            if not classes:
                sealed.record("QTradeX-AI-Agents", name, "none", "", None, "does not run as shipped", "no bot class")
                continue
            res, why = run_bot(classes[0], candles)
            if res is None:
                print(f"{name:<24} skipped: {why}")
                sealed.record("QTradeX-AI-Agents", name, "B", "", None, "cannot run here", why)
                continue
            value, n, first = res
            if not np.isfinite(value):
                print(f"{name:<24} {n:>3} trades  wallet became NaN")
                sealed.record("QTradeX-AI-Agents", f"{name} ({classes[0].__name__}, default tune)", "B", n, None,
                              "does not run as shipped", "wallet balance became NaN inside the engine")
                continue
            print(f"{name:<24} {n:>3} trades  $1,000 -> ${value:,.2f}  (first tick {first})", flush=True)
            sealed.record("QTradeX-AI-Agents", f"{name} ({classes[0].__name__}, default tune)", "B", n, value, "ran",
                          "QTradeX own engine, daily candles, fee 0.7%/side")
        except Exception as e:
            err = f"{type(e).__name__}: {e}"[:160]
            print(f"{name:<24} ERROR {err}")
            traceback.print_exc(limit=2, file=sys.stdout)
            sealed.record("QTradeX-AI-Agents", name, "B", "", None, "does not run as shipped", err)


if __name__ == "__main__":
    main()
