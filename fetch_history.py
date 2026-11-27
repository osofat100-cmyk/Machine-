#!/usr/bin/env python3
"""
Download PEARL price history (candles) from BigONE into data/<pair>_<period>.csv

    python3 fetch_history.py                          # PEARL-USDC + PEARL-USDT, 1-minute, 30 days
    python3 fetch_history.py --pair PEARL-USDT --period hour1 --days 150

Periods: min1 min5 min15 min30 hour1 hour4 day1
"""
import argparse
import csv
import json
import os
import time
import urllib.request
from datetime import datetime, timedelta, timezone

BASE = "https://api.big.one/api/v3"


def get(path):
    for attempt in range(5):
        try:
            req = urllib.request.Request(BASE + path, headers={"User-Agent": "pearl-monitor/1.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                body = json.load(r)
            if body.get("code") == 0:
                return body["data"]
            raise RuntimeError(body)
        except Exception as e:
            if attempt == 4:
                raise
            time.sleep(2 ** attempt)


def fetch(pair, period, days):
    """Walk backwards 500 candles at a time until we have `days` of history."""
    oldest_wanted = datetime.now(timezone.utc) - timedelta(days=days)
    rows, cursor = {}, None
    while True:
        q = f"/asset_pairs/{pair}/candles?period={period}&limit=500"
        if cursor:
            q += f"&time={cursor}"
        batch = get(q)
        new = [c for c in batch if c["time"] not in rows]
        if not new:
            break
        for c in new:
            rows[c["time"]] = c
        cursor = min(c["time"] for c in batch)
        if datetime.fromisoformat(cursor.replace("Z", "+00:00")) < oldest_wanted:
            break
        time.sleep(0.25)  # be polite to the API
    return [rows[t] for t in sorted(rows)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pair", action="append", help="repeatable; default both PEARL pairs")
    ap.add_argument("--period", default="min1")
    ap.add_argument("--days", type=float, default=30)
    args = ap.parse_args()

    os.makedirs("data", exist_ok=True)
    for pair in args.pair or ["PEARL-USDC", "PEARL-USDT"]:
        candles = fetch(pair, args.period, args.days)
        path = f"data/{pair}_{args.period}.csv"
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["time", "open", "high", "low", "close", "volume"])
            for c in candles:
                w.writerow([c["time"], c["open"], c["high"], c["low"], c["close"], c["volume"]])
        if candles:
            print(f"{pair} {args.period}: {len(candles)} candles, {candles[0]['time']} -> {candles[-1]['time']}  => {path}")
        else:
            print(f"{pair} {args.period}: no data")


if __name__ == "__main__":
    main()
