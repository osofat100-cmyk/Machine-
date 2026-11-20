#!/usr/bin/env python3
"""
The live machine. PRACTICE MODE: fake money, NO real orders.

Every day it downloads the latest PEARL prices from BigONE, re-runs the
buy%/sell% landscape on the last WINDOW days, and moves to the top of the
smoothed hill. Every minute it checks the "buy the crash, sell the pump" rule
with that setting and trades fake money at the real order-book price.

    python3 live_machine.py                 # re-pick daily from the last 30 days
    python3 live_machine.py --window 60 --refit-hours 168
    python3 live_machine.py --reset

The week-by-week test of this machine (landscape.py walk) made $3,471 from
$1,000 between Jul 30 and Nov 20, while just holding made $6,025.
"""
import argparse
import csv
import json
import os
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from dip_bot import last_4h
from fetch_history import fetch, get
from landscape import Market, best_setting
from paper_trader import book_fill

STATE_FILE = "machine_state.json"
TRADE_LOG = "logs/machine_trades.csv"
PICK_LOG = "logs/machine_picks.csv"


def log(path, header, row):
    os.makedirs("logs", exist_ok=True)
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(header)
        w.writerow(row)


def refit(pair, window_days):
    """Download the last window_days of minute prices and find the top of the smoothed hill."""
    candles = fetch(pair, "min1", window_days + 0.2)
    df = pd.DataFrame(candles).astype({"open": float, "high": float, "low": float, "close": float, "volume": float})
    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").sort_index()
    m = Market(df=df, warmup=240)
    buy_steps = np.round(np.arange(0.5, 26.0001, 0.5), 2)
    sell_steps = np.round(np.arange(0.5, 45.0001, 0.5), 2)
    b, s, score = best_setting(m, None, buy_steps, sell_steps)
    return float(b), float(s), float(score), m.n


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pair", default="PEARL-USDC", help="pair the practice trades are priced on")
    ap.add_argument("--signal-pair", default="PEARL-USDT", help="pair the rule reads and is fitted on")
    ap.add_argument("--window", type=float, default=30, help="days of history used to pick the setting")
    ap.add_argument("--refit-hours", type=float, default=24, help="hours between re-picks")
    ap.add_argument("--fee", type=float, default=0.2)
    ap.add_argument("--cash", type=float, default=1000.0)
    ap.add_argument("--reset", action="store_true")
    a = ap.parse_args()

    if a.reset and os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
    s = {"cash": a.cash, "coins": 0.0, "start_cash": a.cash, "trades": 0, "buy_price": 0.0,
         "buy_pct": None, "sell_pct": None, "last_refit": 0.0}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            s = json.load(f)
    print(f"PRACTICE MODE - live machine, re-picks every {a.refit_hours:g}h from the last {a.window:g} days.  Ctrl+C to stop")

    seen = None
    try:
        while True:
            try:
                if time.time() - s["last_refit"] >= a.refit_hours * 3600:
                    print("re-picking the setting from fresh BigONE data...", flush=True)
                    b, sp, score, n = refit(a.signal_pair, a.window)
                    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
                    print(f"*** NEW SETTING  buy after a {b}% drop, sell {sp}% above the low  "
                          f"(top of the smoothed hill over {n:,} minutes: ${score:,.0f} from $1,000)", flush=True)
                    log(PICK_LOG, ["time_utc", "buy_pct", "sell_pct", "smoothed_$_in_window"], [now, b, sp, round(score)])
                    s.update(buy_pct=b, sell_pct=sp, last_refit=time.time())

                c = last_4h(a.signal_pair)
                if len(c) < 241 or c[-1]["time"] == seen:
                    time.sleep(5)
                    continue
                seen = c[-1]["time"]
                close = float(c[-1]["close"])
                low4 = min(float(x["low"]) for x in c[-240:])
                high4 = max(float(x["high"]) for x in c[-240:])
                change4 = (close / float(c[0]["close"]) - 1) * 100
                up_from_low = (close / low4 - 1) * 100
                down_from_high = (1 - close / high4) * 100
                now = datetime.now(timezone.utc).isoformat(timespec="seconds")
                header = ["time_utc", "action", "avg_fill_price", "pearl", "usdc_after", "change_vs_buy_%", "buy_pct", "sell_pct"]

                if s["coins"] == 0 and change4 <= -s["buy_pct"] and up_from_low <= 0.23:
                    coins, avg = book_fill(a.pair, "buy", s["cash"])
                    s.update(coins=coins * (1 - a.fee / 100), cash=0.0, buy_price=avg)
                    s["trades"] += 1
                    log(TRADE_LOG, header, [now, "BUY", round(avg, 4), round(s["coins"], 4), 0, "", s["buy_pct"], s["sell_pct"]])
                    print(f"*** BUY  {s['coins']:.2f} PEARL at {avg:.4f}  (fell {-change4:.1f}% in 4h)")
                elif s["coins"] > 0 and up_from_low >= s["sell_pct"] and down_from_high <= 1.8:
                    usdc, avg = book_fill(a.pair, "sell", s["coins"])
                    gain = (avg / s["buy_price"] - 1) * 100
                    sold = s["coins"]
                    s.update(cash=usdc * (1 - a.fee / 100), coins=0.0)
                    s["trades"] += 1
                    log(TRADE_LOG, header, [now, "SELL", round(avg, 4), round(sold, 4), round(s["cash"], 2),
                                            round(gain, 2), s["buy_pct"], s["sell_pct"]])
                    print(f"*** SELL at {avg:.4f}  ({gain:+.1f}% vs buy)")
                with open(STATE_FILE, "w") as f:
                    json.dump(s, f, indent=2)

                tk = get(f"/asset_pairs/{a.pair}/ticker")
                value = s["cash"] + s["coins"] * float(tk["bid"]["price"])
                holding = "PEARL" if s["coins"] else "USDC"
                wait = (f"buy when 4h change <= -{s['buy_pct']}% (now {change4:+.1f}%)" if holding == "USDC" else
                        f"sell when {s['sell_pct']}%+ above 4h low (now {up_from_low:.1f}%)")
                print(f"{now[11:16]}  price {close:.4f}  setting {s['buy_pct']}/{s['sell_pct']}  holding {holding:<5}  "
                      f"{wait}  account ${value:.2f} ({(value / s['start_cash'] - 1) * 100:+.1f}%)", flush=True)
            except Exception as e:
                print(f"[warn] {e}", flush=True)
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nStopped. Run again to continue from the saved state.")


if __name__ == "__main__":
    main()
