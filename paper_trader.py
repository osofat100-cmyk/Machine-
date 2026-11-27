#!/usr/bin/env python3
"""
PRACTICE trader for PEARL on BigONE. Uses FAKE money - places NO real orders.

It follows the one rule that held up in backtest.py:
    hold PEARL while the 24-hour average price is above the 168-hour (7-day)
    average; otherwise hold dollars.

Each pretend trade is filled at the real live order-book price and pays the
real fee, so the result is close to what a real account would have got.

    python3 paper_trader.py            # keep running, checks once a minute
    python3 paper_trader.py --once     # check one time and exit
    python3 paper_trader.py --reset    # start again with a fresh fake $1000

State is kept in paper_state.json, trades are logged to logs/paper_trades.csv.
"""
import argparse
import csv
import json
import os
import time
from datetime import datetime, timezone

from backtest import sma
from fetch_history import get

STATE_FILE = "paper_state.json"
TRADE_LOG = "logs/paper_trades.csv"


def closed_hourly_closes(pair):
    """Closing prices of finished hourly candles, oldest first."""
    candles = get(f"/asset_pairs/{pair}/candles?period=hour1&limit=500")
    this_hour = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:00:00Z")
    done = sorted((c for c in candles if c["time"] != this_hour), key=lambda c: c["time"])
    return done[-1]["time"], [float(c["close"]) for c in done]


def book_fill(pair, side, amount):
    """Average price we'd really get by walking the order book.
    side='buy': amount is dollars to spend. side='sell': amount is PEARL to sell.
    Returns (coins_or_dollars_received_before_fee, average_price)."""
    depth = get(f"/asset_pairs/{pair}/depth?limit=50")
    levels = depth["asks"] if side == "buy" else depth["bids"]
    left, got = amount, 0.0
    for lv in levels:
        price, qty = float(lv["price"]), float(lv["quantity"])
        if side == "buy":
            take = min(left, price * qty)      # dollars spent at this level
            got += take / price
        else:
            take = min(left, qty)              # coins sold at this level
            got += take * price
        left -= take
        if left <= 1e-9:
            break
    if left > 1e-9:
        raise RuntimeError("order book too thin for this order size")
    avg = amount / got if side == "buy" else got / amount
    return got, avg


def load_state(start_cash):
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"cash": start_cash, "coins": 0.0, "start_cash": start_cash,
            "started": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "start_price": None, "trades": 0}


def save_state(s):
    with open(STATE_FILE, "w") as f:
        json.dump(s, f, indent=2)


def log_trade(row):
    os.makedirs("logs", exist_ok=True)
    new = not os.path.exists(TRADE_LOG)
    with open(TRADE_LOG, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["time_utc", "action", "price", "pearl", "dollars", "fee_dollars", "account_value"])
        w.writerow(row)


def check(args, state):
    last_candle, closes = closed_hourly_closes(args.signal_pair)
    if len(closes) < args.slow:
        print(f"need {args.slow} hourly candles, only have {len(closes)} - waiting")
        return None
    fast, slow = sma(closes, args.fast)[-1], sma(closes, args.slow)[-1]
    want_pearl = fast > slow

    t = get(f"/asset_pairs/{args.trade_pair}/ticker")
    bid, ask = float(t["bid"]["price"]), float(t["ask"]["price"])
    if state["start_price"] is None:
        state["start_price"] = (bid + ask) / 2
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    fee = args.fee / 100

    if want_pearl and state["coins"] == 0:
        coins, avg = book_fill(args.trade_pair, "buy", state["cash"])
        fee_usd = state["cash"] * fee
        state["coins"], spent, state["cash"] = coins * (1 - fee), state["cash"], 0.0
        state["trades"] += 1
        log_trade([now, "BUY", round(avg, 4), round(state["coins"], 4), round(spent, 2),
                   round(fee_usd, 2), round(state["coins"] * bid, 2)])
        print(f"*** PRACTICE BUY  {state['coins']:.2f} PEARL at avg {avg:.4f} (fee ${fee_usd:.2f})")
    elif not want_pearl and state["coins"] > 0:
        dollars, avg = book_fill(args.trade_pair, "sell", state["coins"])
        fee_usd = dollars * fee
        sold, state["coins"], state["cash"] = state["coins"], 0.0, dollars * (1 - fee)
        state["trades"] += 1
        log_trade([now, "SELL", round(avg, 4), round(sold, 4), round(state["cash"], 2),
                   round(fee_usd, 2), round(state["cash"], 2)])
        print(f"*** PRACTICE SELL {sold:.2f} PEARL at avg {avg:.4f} (fee ${fee_usd:.2f})")
    save_state(state)

    value = state["cash"] + state["coins"] * bid
    hold_value = state["start_cash"] * ((bid + ask) / 2) / state["start_price"]
    holding = "PEARL" if state["coins"] > 0 else "dollars"
    print(f"{now[11:19]} UTC  price {bid:.4f}/{ask:.4f}  24h avg {fast:.4f}  7d avg {slow:.4f}  "
          f"trend {'UP' if want_pearl else 'DOWN'}  holding {holding}  "
          f"account ${value:.2f} ({(value / state['start_cash'] - 1) * 100:+.1f}%)  "
          f"just-holding would be ${hold_value:.2f}  trades {state['trades']}", flush=True)
    return last_candle


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--signal-pair", default="PEARL-USDT", help="pair used to read the trend (has the longest history)")
    ap.add_argument("--trade-pair", default="PEARL-USDC", help="pair the pretend trades are priced on")
    ap.add_argument("--fast", type=int, default=24, help="fast average, in hours")
    ap.add_argument("--slow", type=int, default=168, help="slow average, in hours")
    ap.add_argument("--fee", type=float, default=0.2, help="exchange fee %% per trade")
    ap.add_argument("--cash", type=float, default=1000.0, help="fake starting dollars")
    ap.add_argument("--interval", type=int, default=60, help="seconds between checks")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--reset", action="store_true")
    args = ap.parse_args()

    if args.reset and os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
    state = load_state(args.cash)
    print("PRACTICE MODE - fake money, no real orders.  Ctrl+C to stop.")

    seen = None
    try:
        while True:
            try:
                # the trend only changes when an hourly candle finishes, so one line per hour is enough
                last_candle, _ = closed_hourly_closes(args.signal_pair)
                if last_candle != seen:
                    seen = check(args, state) or seen
            except Exception as e:
                print(f"[warn] {e}")
            if args.once:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped. Run again to continue from the saved state.")


if __name__ == "__main__":
    main()
