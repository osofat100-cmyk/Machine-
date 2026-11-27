#!/usr/bin/env python3
"""
PEARL live monitor for BigONE (monitor only - places NO orders).

Every second it pulls the ticker + order book for a pair, prints a live line,
logs every tick to CSV, and prints an UP / DOWN signal when the short-term
average moves away from the long-term average by more than the spread.

Standard library only. Run:
    python3 pearl_monitor.py                 # PEARL-USDC, 1 second
    python3 pearl_monitor.py --pair PEARL-USDT
    python3 pearl_monitor.py --list          # show PEARL pairs BigONE lists
"""
import argparse
import csv
import json
import os
import signal
import sys
import time
import urllib.request
from collections import deque
from datetime import datetime, timezone

BASE = "https://api.big.one/api/v3"


def get(path, timeout=5):
    req = urllib.request.Request(BASE + path, headers={"User-Agent": "pearl-monitor/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = json.load(r)
    if body.get("code") != 0:
        raise RuntimeError(f"API error on {path}: {body}")
    return body["data"]


def list_pairs(token="PEARL"):
    for p in get("/asset_pairs"):
        if token in p["name"]:
            print(p["name"])


def snapshot(pair, depth_levels=5):
    """One reading: best bid/ask, last price, 24h stats, order book imbalance."""
    t = get(f"/asset_pairs/{pair}/ticker")
    bid = float(t["bid"]["price"]) if t.get("bid") else None
    ask = float(t["ask"]["price"]) if t.get("ask") else None
    d = get(f"/asset_pairs/{pair}/depth?limit={depth_levels}")
    bid_qty = sum(float(x["quantity"]) for x in d.get("bids", [])[:depth_levels])
    ask_qty = sum(float(x["quantity"]) for x in d.get("asks", [])[:depth_levels])
    total = bid_qty + ask_qty
    return {
        "bid": bid,
        "ask": ask,
        "mid": (bid + ask) / 2 if bid and ask else None,
        "last": float(t["close"]),
        "change24h": float(t["daily_change"]) * 100,
        "volume24h": float(t["volume"]),
        "bid_qty": bid_qty,
        "ask_qty": ask_qty,
        # +1 = all buyers in the top levels, -1 = all sellers
        "imbalance": (bid_qty - ask_qty) / total if total else 0.0,
    }


def mean(xs):
    return sum(xs) / len(xs) if xs else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pair", default="PEARL-USDC")
    ap.add_argument("--interval", type=float, default=1.0, help="seconds between readings")
    ap.add_argument("--fast", type=int, default=10, help="fast average window, in readings")
    ap.add_argument("--slow", type=int, default=60, help="slow average window, in readings")
    ap.add_argument("--min-move-pct", type=float, default=0.0,
                    help="extra % the fast avg must beat the slow avg by (on top of the spread)")
    ap.add_argument("--csv", default=None, help="log file (default logs/<pair>.csv)")
    ap.add_argument("--list", action="store_true", help="list PEARL pairs on BigONE and exit")
    args = ap.parse_args()

    if args.list:
        list_pairs()
        return

    os.makedirs("logs", exist_ok=True)
    path = args.csv or f"logs/{args.pair}.csv"
    new_file = not os.path.exists(path)
    f = open(path, "a", newline="")
    w = csv.writer(f)
    if new_file:
        w.writerow(["time_utc", "bid", "ask", "mid", "last", "spread_pct", "imbalance",
                    "fast_avg", "slow_avg", "signal"])

    mids = deque(maxlen=args.slow)
    last_signal = "WARMUP"
    stop = False

    def on_sigint(*_):
        nonlocal stop
        stop = True
    signal.signal(signal.SIGINT, on_sigint)

    print(f"Monitoring {args.pair} every {args.interval}s -> {path}   (Ctrl+C to stop)")
    print("time(UTC)  bid       ask       spread%  imbal   fast      slow      signal")
    errors = 0
    while not stop:
        start = time.time()
        try:
            s = snapshot(args.pair)
            errors = 0
        except Exception as e:  # network blip, rate limit, etc.
            errors += 1
            print(f"[warn] fetch failed ({errors}): {e}", file=sys.stderr)
            time.sleep(min(2 ** errors, 30))
            continue

        if s["mid"] is None:
            time.sleep(args.interval)
            continue

        mids.append(s["mid"])
        spread_pct = (s["ask"] - s["bid"]) / s["mid"] * 100
        fast = mean(list(mids)[-args.fast:])
        slow = mean(mids)

        sig = "WARMUP"
        if len(mids) >= args.slow:
            diff_pct = (fast - slow) / slow * 100
            # a move smaller than the spread can't be traded profitably
            threshold = spread_pct + args.min_move_pct
            if diff_pct > threshold:
                sig = "UP"
            elif diff_pct < -threshold:
                sig = "DOWN"
            else:
                sig = "FLAT"

        now = datetime.now(timezone.utc).strftime("%H:%M:%S")
        flag = "  <<<" if sig in ("UP", "DOWN") and sig != last_signal else ""
        print(f"{now}   {s['bid']:<8.4f}  {s['ask']:<8.4f}  {spread_pct:6.2f}  {s['imbalance']:+.2f}  "
              f"{fast:<8.4f}  {slow:<8.4f}  {sig}{flag}", flush=True)
        w.writerow([datetime.now(timezone.utc).isoformat(timespec="seconds"), s["bid"], s["ask"],
                    round(s["mid"], 6), s["last"], round(spread_pct, 4), round(s["imbalance"], 4),
                    round(fast, 6), round(slow, 6), sig])
        f.flush()
        last_signal = sig

        time.sleep(max(0, args.interval - (time.time() - start)))

    f.close()
    print("\nStopped. Data saved to", path)


if __name__ == "__main__":
    main()
