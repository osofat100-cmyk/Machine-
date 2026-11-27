#!/usr/bin/env python3
"""
Download the HOURLY test data for the two-AI trader (coins + stocks), 3 months: 25 Aug - 23 Nov 2026, plus history
from 1 Aug. Same coins and stocks as the minute tests, same sources (Yahoo bars, Google News headlines with a real
publication time only), saved as it arrives; re-running skips what is saved.

    python3 mixed/fetch_hourly.py -> data/sealed/hourly/{universe_crypto.csv, universe_stocks.csv, crypto_1h/,
                                                         stocks_1h/, news/}
"""
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "crypto"))
sys.path.insert(0, os.path.join(ROOT, "sp500"))
import fetch_crypto as FC  # noqa: E402
import fetch_market as FM  # noqa: E402

OUT = os.path.join(ROOT, "data", "sealed", "hourly")
P1 = int(datetime(2026, 8, 1, tzinfo=timezone.utc).timestamp())
P2 = int(datetime(2026, 11, 24, tzinfo=timezone.utc).timestamp())
NEWS_FIRST, NEWS_LAST = date(2026, 8, 22), date(2026, 11, 23)


def bars(symbol, folder, stock):
    path = os.path.join(OUT, folder, f"{symbol}.csv")
    if os.path.exists(path):
        return
    try:
        j = FC.get(f"https://query2.finance.yahoo.com/v8/finance/chart/{quote(symbol)}",
                   params={"period1": P1, "period2": P2, "interval": "1h", "includePrePost": "false"}).json()
        x = j["chart"]["result"][0]
    except (RuntimeError, KeyError, TypeError, IndexError):
        print(f"  no bars for {symbol}", flush=True)
        return
    if not x.get("timestamp"):
        print(f"  no bars for {symbol}", flush=True)
        return
    df = pd.DataFrame({"ts": x["timestamp"], **{k: x["indicators"]["quote"][0][k] for k in
                                                ("open", "high", "low", "close", "volume")}})
    df = df.drop_duplicates("ts").sort_values("ts").dropna(subset=["open", "close"])
    t = pd.to_datetime(df["ts"], unit="s", utc=True)
    if stock:                                          # New York time, regular hours only
        df["time"] = t.dt.tz_convert("America/New_York").dt.strftime("%Y-%m-%d %H:%M")
        df = df[(df["time"].str[11:] >= "09:30") & (df["time"].str[11:] < "16:00")]
    else:
        df["time"] = t.dt.strftime("%Y-%m-%d %H:%M")   # UTC, around the clock
    df[["time", "open", "high", "low", "close", "volume"]].to_csv(path, index=False, float_format="%.8g")


def seed(src, mapping):
    """Reuse headlines already downloaded for the minute tests: copy the days the hourly folder does not have yet."""
    for old, new in mapping.items():
        a, b = os.path.join(src, "news", f"{old}.jsonl"), os.path.join(OUT, "news", f"{new}.jsonl")
        if not os.path.exists(a):
            continue
        have = set()
        if os.path.exists(b):
            with open(b) as f:
                have = {json.loads(line)["day"] for line in f if line.strip()}
        with open(a) as f, open(b, "a") as g:
            for line in f:
                if line.strip() and json.loads(line)["day"] not in have:
                    g.write(line if line.endswith("\n") else line + "\n")


def main():
    os.makedirs(os.path.join(OUT, "crypto_1h"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "stocks_1h"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "news"), exist_ok=True)
    cu, su = FC.universe(), FM.universe()               # the same 100 coins and 500 stocks as the minute tests
    cu.to_csv(os.path.join(OUT, "universe_crypto.csv"), index=False)
    su.to_csv(os.path.join(OUT, "universe_stocks.csv"), index=False)
    with ThreadPoolExecutor(6) as ex:
        list(ex.map(lambda s: bars(s, "crypto_1h", False), list(cu["symbol"])))
        list(ex.map(lambda s: bars(s, "stocks_1h", True), ["SPY"] + list(su["symbol"])))
    for folder, ref in (("crypto_1h", "BTC-USD"), ("stocks_1h", "SPY")):
        d = pd.read_csv(os.path.join(OUT, folder, f"{ref}.csv"))
        print(f"{folder}: {len(os.listdir(os.path.join(OUT, folder)))} symbols; {ref} {d['time'].iloc[0]} .. "
              f"{d['time'].iloc[-1]}, {len(d)} bars", flush=True)
    days = [NEWS_FIRST + timedelta(days=i) for i in range((NEWS_LAST - NEWS_FIRST).days + 1)]
    queries = {}                                        # (module, file name, query)
    queries.update({f"crypto_market_{i}": (FC, q) for i, q in enumerate(FC.MARKET_QUERIES)})
    queries.update({f"coin_{r.symbol.split('-')[0]}": (FC, f'"{r.coin}" crypto') for r in cu.head(15).itertuples()})
    queries.update({f"stock_market_{i}": (FM, q) for i, q in enumerate(FM.MARKET_QUERIES)})
    queries.update({f"co_{r.symbol}": (FM, f'"{r.company.split(" Inc")[0].split(" Corporation")[0].split(",")[0]}"')
                    for r in su.head(15).itertuples()})
    old_names = {f"crypto_market_{i}": f"market_{i}" for i in range(len(FC.MARKET_QUERIES))}
    seed(os.path.join(ROOT, "data", "sealed", "crypto"), {**{v: k for k, v in old_names.items()},
                                                         **{k: k for k in queries if k.startswith("coin_")}})
    seed(os.path.join(ROOT, "data", "sealed", "market"), {**{f"market_{i}": f"stock_market_{i}" for i in range(len(FM.MARKET_QUERIES))},
                                                         **{k: k for k in queries if k.startswith("co_")}})
    FC.OUT = FM.OUT = OUT                               # news_query writes to OUT/news/<name>.jsonl
    with ThreadPoolExecutor(6) as ex:
        list(ex.map(lambda kv: kv[1][0].news_query(kv[0], kv[1][1], days), queries.items()))
    n = sum(len(json.loads(line)["items"]) for name in os.listdir(os.path.join(OUT, "news"))
            for line in open(os.path.join(OUT, "news", name)))
    print(f"news: {len(queries)} queries x {len(days)} days, {n} headlines with exact times", flush=True)


if __name__ == "__main__":
    main()
