#!/usr/bin/env python3
"""
Download the test prices, 1 Oct - 20 Nov 2026, into a sealed file that only price_server.py opens.

  1 Oct 00:00 - 13 Nov 17:59   BigONE PEARL-USDT, fresh download
  13 Nov 18:00 - 20 Nov 23:59  Coinbase PEARL-USD (Coinbase started trading PEARL at 17:21 on 13 Nov;
                               18:00 is its first full hour)

Minutes with no trade get a flat candle at the last close, so every minute is there.

    python3 fetch_sealed.py        # -> data/sealed/PEARL_oct1_nov20.csv
"""
import json
import os
import time
import urllib.request

import pandas as pd

from fetch_history import fetch

START, SWITCH, END = "2026-10-01T00:00:00Z", "2026-11-13T18:00:00Z", "2026-11-21T00:00:00Z"
OUT = "data/sealed/PEARL_oct1_nov20.csv"


def bigone():
    days = (pd.Timestamp.now(tz="UTC") - pd.Timestamp(START)).total_seconds() / 86400 + 0.5
    df = pd.DataFrame(fetch("PEARL-USDT", "min1", days))
    df["time"] = pd.to_datetime(df["time"])
    df = df[(df["time"] >= pd.Timestamp(START)) & (df["time"] < pd.Timestamp(SWITCH))]
    return df[["time", "high", "low", "close", "volume"]].astype({c: float for c in ("high", "low", "close", "volume")})


def coinbase(start=SWITCH, end=END):
    rows, t = [], pd.Timestamp(start)
    while t < pd.Timestamp(end):
        u = min(t + pd.Timedelta(minutes=300), pd.Timestamp(end))
        url = (f"https://api.exchange.coinbase.com/products/PEARL-USD/candles?granularity=60"
               f"&start={t.strftime('%Y-%m-%dT%H:%M:%SZ')}&end={u.strftime('%Y-%m-%dT%H:%M:%SZ')}")
        for attempt in range(5):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "price-client/1.0"})
                with urllib.request.urlopen(req, timeout=20) as r:
                    batch = json.load(r)
                break
            except Exception:
                if attempt == 4:
                    raise
                time.sleep(2 ** attempt)
        rows += [{"time": pd.Timestamp(c[0], unit="s", tz="UTC"), "low": float(c[1]), "high": float(c[2]),
                  "close": float(c[4]), "volume": float(c[5])} for c in batch]
        t = u
        time.sleep(0.2)
    df = pd.DataFrame(rows).drop_duplicates("time").sort_values("time")
    return df[(df["time"] >= pd.Timestamp(start)) & (df["time"] < pd.Timestamp(end))]


def fill(df, start, end, source):
    """Every minute from start to end; a minute with no trade is flat at the last close."""
    full = pd.date_range(start, pd.Timestamp(end) - pd.Timedelta(minutes=1), freq="min", tz="UTC")
    df = df.set_index("time").reindex(full)
    missing = int(df["close"].isna().sum())
    df["close"] = df["close"].ffill()
    df["high"] = df["high"].fillna(df["close"])
    df["low"] = df["low"].fillna(df["close"])
    df["volume"] = df["volume"].fillna(0.0)
    df["source"] = source
    return df.rename_axis("time").reset_index(), missing


def main():
    os.makedirs("data/sealed", exist_ok=True)
    b, mb = fill(bigone(), START, SWITCH, "BigONE PEARL-USDT")
    c, mc = fill(coinbase(), SWITCH, END, "Coinbase PEARL-USD")
    out = pd.concat([b, c], ignore_index=True)
    assert out["close"].notna().all() and out["time"].is_monotonic_increasing
    out.to_csv(OUT, index=False, date_format="%Y-%m-%dT%H:%M:%SZ")
    print(f"{len(out):,} minutes -> {OUT}")
    print(f"  BigONE   {len(b):,} minutes, {mb:,} with no trade (flat)")
    print(f"  Coinbase {len(c):,} minutes, {mc:,} with no trade (flat)")


if __name__ == "__main__":
    main()
