#!/usr/bin/env python3
"""
Download PEARL trade-by-trade history (exact time of every trade).
BigONE only keeps its last 200 trades, so other exchanges supply the
second-by-second history.

    python3 fetch_trades.py                  # Coinbase PEARL-USD, everything since listing
    python3 fetch_trades.py --source gate --from-days-ago 14 --to-days-ago 7
                                             # Gate PEARL-USDT (they keep 30 days)

Output: data/<source>_trades.csv with columns time, price, size, side
"""
import argparse
import csv
import json
import os
import time
import urllib.request
from datetime import datetime, timezone


def fetch_json(url):
    for attempt in range(6):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "pearl-monitor/1.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r), r.headers
        except Exception:
            if attempt == 5:
                raise
            time.sleep(2 ** attempt)


def coinbase():
    base = "https://api.exchange.coinbase.com/products/PEARL-USD/trades?limit=1000"
    trades, after = {}, None
    while True:
        batch, headers = fetch_json(base + (f"&after={after}" if after else ""))
        for t in batch:
            trades[int(t["trade_id"])] = (t["time"], t["price"], t["size"], t["side"])
        after = headers.get("cb-after")
        if not batch or not after:
            break
        if len(trades) % 20000 < 1000:
            print(f"  {len(trades)} trades, back to {batch[-1]['time']}", flush=True)
        time.sleep(0.15)
    return [trades[k] for k in sorted(trades)]


def gate_window(start, end):
    """All trades between two unix times; splits the window if it hits the 1000 limit."""
    url = ("https://api.gateio.ws/api/v4/spot/trades?currency_pair=PEARL_USDT&limit=1000"
           f"&from={start}&to={end}")
    batch, _ = fetch_json(url)
    if isinstance(batch, list) and len(batch) >= 1000 and end - start > 1:
        mid = (start + end) // 2
        return gate_window(start, mid) + gate_window(mid + 1, end)
    return batch if isinstance(batch, list) else []


def gate(start_days_ago, end_days_ago, step=300):
    """Gate keeps 30 days of trades. Downloads in 5-minute windows, 4 at a time."""
    from concurrent.futures import ThreadPoolExecutor
    now = int(time.time())
    starts = range(now - int(start_days_ago * 86400), now - int(end_days_ago * 86400), step)
    trades = {}
    with ThreadPoolExecutor(4) as pool:
        for i, batch in enumerate(pool.map(lambda s: gate_window(s, s + step - 1), starts)):
            for t in batch:
                ts = datetime.fromtimestamp(float(t["create_time_ms"]) / 1000, timezone.utc)
                trades[int(t["id"])] = (ts.isoformat().replace("+00:00", "Z"), t["price"], t["amount"], t["side"])
            if i % 288 == 0:
                print(f"  {len(trades)} trades so far", flush=True)
    return [trades[k] for k in sorted(trades)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", choices=["coinbase", "gate"], default="coinbase")
    ap.add_argument("--from-days-ago", type=float, default=29.9, help="gate only")
    ap.add_argument("--to-days-ago", type=float, default=0, help="gate only")
    args = ap.parse_args()
    os.makedirs("data", exist_ok=True)
    rows = coinbase() if args.source == "coinbase" else gate(args.from_days_ago, args.to_days_ago)
    out = f"data/{args.source}_trades.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time", "price", "size", "side"])
        w.writerows(rows)
    print(f"{len(rows)} trades {rows[0][0]} -> {rows[-1][0]} => {out}")


if __name__ == "__main__":
    main()
