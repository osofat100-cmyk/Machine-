#!/usr/bin/env python3
"""
PEARL bot - normal mode + spike mode (rules in ALGORITHM.md, code in strategy.py).
PRACTICE MODE: fake money, NO real orders. Checks the price every second.

    python3 pearl_bot.py                    # both modes
    python3 pearl_bot.py --spikes-only      # spike mode only
    python3 pearl_bot.py --reset            # start again with fake $1000
    python3 pearl_bot.py --rise 5 --drop-spike 4 ...   (see --help)
"""
import argparse
import csv
import json
import os
import time
from datetime import datetime, timezone

from fetch_history import get
from paper_trader import book_fill
from strategy import Strategy

STATE_FILE = "bot_state.json"
TRADE_LOG = "logs/bot_trades.csv"
SAVED = ("mode", "kind", "low", "high", "buy_price", "buy_time", "no_buy_until")


def log_trade(row):
    os.makedirs("logs", exist_ok=True)
    new = not os.path.exists(TRADE_LOG)
    with open(TRADE_LOG, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["time_utc", "action", "reason", "avg_fill_price", "pearl", "usdc_after", "price_change_%"])
        w.writerow(row)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pair", default="PEARL-USDC")
    for name, default, text in [
            ("rise", 7.0, "%% rise from the low before buying (normal mode)"),
            ("trail", 3.0, "%% drop from the high that sells once in profit"),
            ("stop", 5.0, "%% drop from the high that sells before profit"),
            ("rise_spike", 2.0, "%% fast rise that counts as a spike"),
            ("drop_spike", 5.0, "%% fast drop that counts as a spike"),
            ("spike_secs", 30, "seconds a spike must happen within"),
            ("bounce", 2.0, "%% gain that sells a spike buy"),
            ("bounce_stop", 10.0, "%% loss that sells a spike buy"),
            ("bounce_secs", 1800, "seconds before a spike buy is sold anyway")]:
        ap.add_argument("--" + name.replace("_", "-"), type=type(default), default=default, help=text)
    ap.add_argument("--spikes-only", action="store_true")
    ap.add_argument("--fee", type=float, default=0.2, help="exchange fee %% per trade")
    ap.add_argument("--cash", type=float, default=1000.0, help="fake starting USDC")
    ap.add_argument("--reset", action="store_true")
    a = ap.parse_args()

    strat = Strategy(rise=999 if a.spikes_only else a.rise, trail=a.trail, stop=a.stop,
                     rise_spike=a.rise_spike, drop_spike=a.drop_spike, spike_secs=a.spike_secs,
                     bounce=a.bounce, bounce_stop=a.bounce_stop, bounce_secs=a.bounce_secs)
    if a.reset and os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
    acct = {"cash": a.cash, "coins": 0.0, "start_cash": a.cash, "trades": 0}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            saved = json.load(f)
        acct = saved["account"]
        for k in SAVED:
            setattr(strat, k, saved["strategy"][k])

    print(f"PRACTICE MODE {a.pair} {'(spikes only)' if a.spikes_only else ''}  Ctrl+C to stop")
    fee, last_print = a.fee / 100, 0.0
    try:
        while True:
            t0 = time.time()
            try:
                tk = get(f"/asset_pairs/{a.pair}/ticker")
                bid, ask = float(tk["bid"]["price"]), float(tk["ask"]["price"])
            except Exception as e:
                print(f"[warn] {e}")
                time.sleep(2)
                continue
            price = (bid + ask) / 2
            now = datetime.now(timezone.utc).isoformat(timespec="seconds")
            buy_price = strat.buy_price
            action, why = strat.update(t0, price)

            if action == "BUY":
                coins, avg = book_fill(a.pair, "buy", acct["cash"])
                acct.update(coins=coins * (1 - fee), cash=0.0)
                acct["trades"] += 1
                log_trade([now, "BUY", why, round(avg, 4), round(acct["coins"], 4), 0, ""])
                print(f"*** BUY  {acct['coins']:.2f} PEARL at {avg:.4f}  ({why})")
            elif action == "SELL":
                usdc, avg = book_fill(a.pair, "sell", acct["coins"])
                sold = acct["coins"]
                acct.update(cash=usdc * (1 - fee), coins=0.0)
                acct["trades"] += 1
                change = (price / buy_price - 1) * 100
                log_trade([now, "SELL", why, round(avg, 4), round(sold, 4), round(acct["cash"], 2), round(change, 2)])
                print(f"*** SELL {sold:.2f} PEARL at {avg:.4f}  ({why}, price {change:+.2f}% vs buy)")

            with open(STATE_FILE, "w") as f:
                json.dump({"account": acct, "strategy": {k: getattr(strat, k) for k in SAVED}}, f, indent=2)

            if action or t0 - last_print >= 10:
                value = acct["cash"] + acct["coins"] * bid
                if strat.mode == "USDC":
                    nxt = "spike buys only" if a.spikes_only else f"buy at {strat.buy_line():.4f}"
                else:
                    nxt = f"sell at {strat.sell_line():.4f} (bought {strat.buy_price:.4f}, high {strat.high:.4f})"
                print(f"{now[11:19]}  price {price:.4f}  holding {strat.mode:<5}  {nxt}  "
                      f"account ${value:.2f} ({(value / acct['start_cash'] - 1) * 100:+.1f}%)  trades {acct['trades']}",
                      flush=True)
                last_print = t0
            time.sleep(max(0.0, 1.0 - (time.time() - t0)))
    except KeyboardInterrupt:
        print("\nStopped. Run again to continue from the saved state.")


if __name__ == "__main__":
    main()
