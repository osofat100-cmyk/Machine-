#!/usr/bin/env python3
"""
PEARL bot - the user's rule (see ALGORITHM.md). PRACTICE MODE: fake money, NO real orders.

Checks the price every second.
  Holding USDC:  buy once price rises RISE% above its lowest point.
  Holding PEARL: once price is up TARGET% over the buy price, sell when it drops
                 TRAIL% from its highest point - but never below +FLOOR%.
                 Before reaching TARGET%, sell if it drops STOP% from its highest point.

    python3 pearl_bot.py                       # default settings
    python3 pearl_bot.py --rise 5 --trail 2 --stop 5
    python3 pearl_bot.py --reset               # start again with fake $1000
"""
import argparse
import csv
import json
import os
import time
from datetime import datetime, timezone

from fetch_history import get
from paper_trader import book_fill

STATE_FILE = "bot_state.json"
TRADE_LOG = "logs/bot_trades.csv"


def sell_line(s, a):
    """Price at which we sell while holding PEARL."""
    if s["high"] >= s["buy_price"] * (1 + a.target / 100):
        return max(s["buy_price"] * (1 + a.floor / 100), s["high"] * (1 - a.trail / 100))
    return s["high"] * (1 - a.stop / 100)


def log_trade(row):
    os.makedirs("logs", exist_ok=True)
    new = not os.path.exists(TRADE_LOG)
    with open(TRADE_LOG, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["time_utc", "action", "avg_fill_price", "pearl", "usdc_after", "profit_%"])
        w.writerow(row)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pair", default="PEARL-USDC")
    ap.add_argument("--rise", type=float, default=7.0, help="%% rise from the low before buying")
    ap.add_argument("--trail", type=float, default=3.0, help="%% drop from the high that sells, once in profit")
    ap.add_argument("--stop", type=float, default=5.0, help="%% drop from the high that sells, before profit")
    ap.add_argument("--target", type=float, default=1.6, help="%% gain that switches on the profit lock")
    ap.add_argument("--floor", type=float, default=1.5, help="%% gain we never sell below once locked")
    ap.add_argument("--fee", type=float, default=0.2, help="exchange fee %% per trade")
    ap.add_argument("--cash", type=float, default=1000.0, help="fake starting USDC")
    ap.add_argument("--interval", type=float, default=1.0, help="seconds between checks")
    ap.add_argument("--reset", action="store_true")
    a = ap.parse_args()

    if a.reset and os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            s = json.load(f)
    else:
        s = {"mode": "USDC", "cash": a.cash, "coins": 0.0, "start_cash": a.cash,
             "low": None, "high": 0.0, "buy_price": 0.0, "trades": 0}

    print(f"PRACTICE MODE {a.pair}  rise {a.rise}%  trail {a.trail}%  stop {a.stop}%  "
          f"lock at +{a.target}%, floor +{a.floor}%   Ctrl+C to stop")
    fee, last_print = a.fee / 100, 0.0
    try:
        while True:
            t0 = time.time()
            try:
                t = get(f"/asset_pairs/{a.pair}/ticker")
                bid, ask = float(t["bid"]["price"]), float(t["ask"]["price"])
            except Exception as e:
                print(f"[warn] {e}")
                time.sleep(2)
                continue
            p = (bid + ask) / 2
            now = datetime.now(timezone.utc).isoformat(timespec="seconds")
            acted = False

            if s["mode"] == "USDC":
                s["low"] = p if s["low"] is None else min(s["low"], p)
                line = s["low"] * (1 + a.rise / 100)
                if p >= line:
                    coins, avg = book_fill(a.pair, "buy", s["cash"])
                    s.update(mode="PEARL", coins=coins * (1 - fee), cash=0.0, buy_price=p, high=p)
                    s["trades"] += 1
                    log_trade([now, "BUY", round(avg, 4), round(s["coins"], 4), 0, ""])
                    print(f"*** BUY  {s['coins']:.2f} PEARL at {avg:.4f}")
                    acted = True
            else:
                s["high"] = max(s["high"], p)
                line = sell_line(s, a)
                if p <= line:
                    usdc, avg = book_fill(a.pair, "sell", s["coins"])
                    sold, gain = s["coins"], (p / s["buy_price"] - 1) * 100
                    s.update(mode="USDC", cash=usdc * (1 - fee), coins=0.0, low=p)
                    s["trades"] += 1
                    log_trade([now, "SELL", round(avg, 4), round(sold, 4), round(s["cash"], 2), round(gain, 2)])
                    print(f"*** SELL {sold:.2f} PEARL at {avg:.4f}  (price {gain:+.2f}% vs buy)")
                    acted = True

            with open(STATE_FILE, "w") as f:
                json.dump(s, f, indent=2)

            if acted or t0 - last_print >= 10:
                value = s["cash"] + s["coins"] * bid
                if s["mode"] == "USDC":
                    nxt = f"buy at {s['low'] * (1 + a.rise / 100):.4f} (low {s['low']:.4f})"
                else:
                    locked = s["high"] >= s["buy_price"] * (1 + a.target / 100)
                    nxt = (f"sell at {sell_line(s, a):.4f} (bought {s['buy_price']:.4f}, high {s['high']:.4f}"
                           f"{', profit locked' if locked else ''})")
                print(f"{now[11:19]}  price {p:.4f}  holding {s['mode']:<5}  {nxt}  "
                      f"account ${value:.2f} ({(value / s['start_cash'] - 1) * 100:+.1f}%)  trades {s['trades']}",
                      flush=True)
                last_print = t0
            time.sleep(max(0.0, a.interval - (time.time() - t0)))
    except KeyboardInterrupt:
        print("\nStopped. Run again to continue from the saved state.")


if __name__ == "__main__":
    main()
