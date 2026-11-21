#!/usr/bin/env python3
"""
"Buy the crash, sell the pump" bot for PEARL. PRACTICE MODE: fake money, NO real orders.

  BUY  when the price has fallen DROP% or more in the last 4 hours
       AND is at its 4-hour low (within 0.23%).
  SELL when the price is PUMP% or more above its 4-hour low
       AND near its 4-hour high (within 1.8%).

Found with signals.py on 5 months of BigONE minute data. Checks once a minute.

    python3 dip_bot.py
    python3 dip_bot.py --drop 5 --pump 11.4
    python3 dip_bot.py --reset
"""
import argparse
import csv
import json
import os
import time
from datetime import datetime, timezone

from fetch_history import get
from paper_trader import book_fill

STATE_FILE = "dip_state.json"
TRADE_LOG = "logs/dip_trades.csv"


def last_4h(pair):
    """Finished 1-minute candles for the last 4 hours + 1 minute, oldest first."""
    candles = sorted(get(f"/asset_pairs/{pair}/candles?period=min1&limit=300"), key=lambda c: c["time"])
    this_min = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:00Z")
    return [c for c in candles if c["time"] != this_min][-241:]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pair", default="PEARL-USDC")
    ap.add_argument("--signal-pair", default="PEARL-USDT", help="pair the rule reads (it was found on this one)")
    ap.add_argument("--drop", type=float, default=6.4, help="%% fall in 4 hours before buying")
    ap.add_argument("--pump", type=float, default=11.4, help="%% above the 4-hour low before selling")
    ap.add_argument("--at-low", type=float, default=0.23, help="%% above the 4h low that still counts as at the low")
    ap.add_argument("--near-high", type=float, default=1.8, help="%% below the 4h high that still counts as near it")
    ap.add_argument("--fee", type=float, default=0.2)
    ap.add_argument("--cash", type=float, default=1000.0)
    ap.add_argument("--reset", action="store_true")
    a = ap.parse_args()

    if a.reset and os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
    s = {"cash": a.cash, "coins": 0.0, "start_cash": a.cash, "trades": 0, "buy_price": 0.0}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            s = json.load(f)
    print(f"PRACTICE MODE  buy after a {a.drop}% 4-hour drop, sell {a.pump}% above the 4-hour low.  Ctrl+C to stop")

    seen = None
    try:
        while True:
            try:
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

                if s["coins"] == 0 and change4 <= -a.drop and up_from_low <= a.at_low:
                    coins, avg = book_fill(a.pair, "buy", s["cash"])
                    s.update(coins=coins * (1 - a.fee / 100), cash=0.0, buy_price=avg)
                    s["trades"] += 1
                    print(f"*** BUY  {s['coins']:.2f} PEARL at {avg:.4f}  (fell {-change4:.1f}% in 4h, at the 4h low)")
                    action = ["BUY", round(avg, 4), round(s["coins"], 4), 0, ""]
                elif s["coins"] > 0 and up_from_low >= a.pump and down_from_high <= a.near_high:
                    usdc, avg = book_fill(a.pair, "sell", s["coins"])
                    gain = (avg / s["buy_price"] - 1) * 100
                    action = ["SELL", round(avg, 4), round(s["coins"], 4), 0, round(gain, 2)]
                    s.update(cash=usdc * (1 - a.fee / 100), coins=0.0)
                    action[3] = round(s["cash"], 2)
                    s["trades"] += 1
                    print(f"*** SELL at {avg:.4f}  ({up_from_low:.1f}% above the 4h low, {gain:+.1f}% vs buy)")
                else:
                    action = None
                if action:
                    os.makedirs("logs", exist_ok=True)
                    new = not os.path.exists(TRADE_LOG)
                    with open(TRADE_LOG, "a", newline="") as f:
                        w = csv.writer(f)
                        if new:
                            w.writerow(["time_utc", "action", "avg_fill_price", "pearl", "usdc_after", "change_vs_buy_%"])
                        w.writerow([now] + action)
                with open(STATE_FILE, "w") as f:
                    json.dump(s, f, indent=2)

                tk = get(f"/asset_pairs/{a.pair}/ticker")
                value = s["cash"] + s["coins"] * float(tk["bid"]["price"])
                holding = "PEARL" if s["coins"] else "USDC"
                wait = (f"buy when 4h change <= -{a.drop}% (now {change4:+.1f}%)" if holding == "USDC" else
                        f"sell when {a.pump}%+ above 4h low (now {up_from_low:.1f}%)")
                print(f"{now[11:16]}  price {close:.4f}  holding {holding:<5}  {wait}  "
                      f"account ${value:.2f} ({(value / s['start_cash'] - 1) * 100:+.1f}%)", flush=True)
            except Exception as e:
                print(f"[warn] {e}")
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nStopped. Run again to continue from the saved state.")


if __name__ == "__main__":
    main()
