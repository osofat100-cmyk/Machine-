#!/usr/bin/env python3
"""
Robot 2, live. PRACTICE MODE: fake money, NO real orders.

This runs robot2.py, the same code the tests run (python3 robot2.py, python3 robot2.py check).

On start it downloads PEARL's minute history from BigONE and feeds all of it to the robot, so it
starts with its 100 lines, its trajectory library, its accuracy record and its timing machines
already built. Its practice account starts with $1,000 in USDC. Then, every new minute:
  1. the robot takes the minute and decides (see robot2.py)
  2. if the robot buys, the practice account puts the same share of its money (Kelly) into PEARL
     at the real PEARL-USDC order book; if it sells, the practice account sells everything
The robot is saved every hour, so a restart continues where it stopped.

    python3 live_machine.py                         # live
    python3 live_machine.py --reset                 # rebuild from history, new $1,000 practice account
    python3 live_machine.py --replay-from 2026-11-13
        # test: learn from the history before that day, then feed the rest in minute by minute
"""
import argparse
import csv
import os
import pickle
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from robot2 import Robot2, feed
from fetch_history import fetch, get
from paper_trader import book_fill

HISTORY = "data/PEARL-USDT_min1.csv"
STATE_FILE = "data/robot2_state.pkl"
TRADE_LOG = "logs/robot2_trades.csv"
ETA = 14.0          # watcher sensitivity (traj_sweep.py)


def log_row(path, header, row):
    os.makedirs("logs", exist_ok=True)
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(header)
        w.writerow(row)


def update_history(pair):
    """Append any minutes missing from the saved history file."""
    df = pd.read_csv(HISTORY, parse_dates=["time"])
    last = df["time"].iloc[-1]
    gap_days = (pd.Timestamp.now(tz="UTC") - last).total_seconds() / 86400
    if gap_days > 1 / 1440:
        new = pd.DataFrame(fetch(pair, "min1", gap_days + 0.05))
        new["time"] = pd.to_datetime(new["time"])
        for col in ("open", "high", "low", "close", "volume"):
            new[col] = new[col].astype(float)
        this_min = pd.Timestamp.now(tz="UTC").floor("min")
        new = new[(new["time"] > last) & (new["time"] < this_min)]
        df = pd.concat([df, new[df.columns]], ignore_index=True)
        df.to_csv(HISTORY, index=False, date_format="%Y-%m-%dT%H:%M:%SZ")
    return df


def new_minutes(pair, last_ts):
    """Finished minutes after last_ts (minutes since 1970), oldest first. Waits until there is one."""
    while True:
        candles = get(f"/asset_pairs/{pair}/candles?period=min1&limit=100")
        this_min = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:00Z")
        rows = []
        for c in candles:
            ts = int(pd.Timestamp(c["time"]).value // 60_000_000_000)
            if c["time"] != this_min and ts > last_ts:
                rows.append((ts, float(c["high"]), float(c["low"]), float(c["close"])))
        if rows:
            return sorted(rows)
        time.sleep(5)


def save(engine, acct):
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "wb") as f:
        pickle.dump({"engine": engine, "acct": acct}, f, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(tmp, STATE_FILE)


def follow(e, acct, pair, fee, log):
    """Make the practice account follow the robot's buys and sells, at the real order book."""
    want = (e.coins > 0 and e.pending != "SELL") or e.pending == "BUY"
    if want == (acct["coins"] > 0):
        return False
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    if want:
        put = e.f_next * acct["cash"]
        coins, avg = book_fill(pair, "buy", put)
        acct.update(coins=coins * (1 - fee / 100), cash=acct["cash"] - put)
    else:
        usdc, avg = book_fill(pair, "sell", acct["coins"])
        acct.update(cash=acct["cash"] + usdc * (1 - fee / 100), coins=0.0)
    acct["trades"] += 1
    s = e.setting or ("", "")
    log_row(TRADE_LOG, ["time_utc", "action", "price", "usdc_after", "buy_pct", "sell_pct", "interval_min"],
            [now, "BUY" if want else "SELL", round(avg, 4), round(acct["cash"], 2), s[0], s[1], e.interval])
    log(f"*** {'BUY' if want else 'SELL'} at {avg:.4f}  (setting {s[0]}% / {s[1]}%, updating every {e.interval} min"
        f"{f', putting in {e.f_next:.0%}' if want else ''})")
    return True


def stamp(ts_min):
    return str(np.datetime64(int(ts_min), "m")).replace("T", " ")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pair", default="PEARL-USDC", help="pair the practice trades are priced on")
    ap.add_argument("--signal-pair", default="PEARL-USDT", help="pair the robot learns from")
    ap.add_argument("--eta", type=float, default=ETA, help="watcher sensitivity")
    ap.add_argument("--risk", default="kelly", help="share of money per buy: kelly, or a number 0.01-1")
    ap.add_argument("--fee", type=float, default=0.2)
    ap.add_argument("--cash", type=float, default=1000.0)
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--replay-from", help="test mode: learn before this UTC day, replay the rest")
    a = ap.parse_args()
    log = lambda *x: print(*x, flush=True)
    risk = "kelly" if a.risk == "kelly" else float(a.risk)
    make = lambda: Robot2(eta=a.eta, risk=risk)

    # ---------------------------------------------------------------- replay test
    if a.replay_from:
        df = pd.read_csv(HISTORY, parse_dates=["time"])
        cut = pd.Timestamp(a.replay_from, tz="UTC")
        log(f"learning from the history before {a.replay_from}...")
        e = feed(make(), df[df["time"] < cut], log)
        e.cash, e.coins, e.pending, e.trades, e.fills = a.cash, 0.0, None, [], []
        rest = df[df["time"] >= cut]
        k0 = e.n - 1
        log(f"replaying {len(rest):,} minutes from {a.replay_from} as if live")
        feed(e, rest, log, every=1440)
        hold = a.cash * e.cl[e.n - 1] * (1 - e.kap[e.n - 1]) / (e.cl[k0] * (1 + e.kap[k0]))
        for ts, act, price, value, setting, interval, f in e.trades:
            log(f"  {stamp(ts)}  {act:<4} at {price:.4f}  account ${value:,.2f}  "
                f"setting {setting}  every {interval} min" + (f"  put in {f:.0%}" if f is not None else ""))
        log(f"replay finished: robot 2 ${e.value():,.2f} after {len(e.trades)} trades; just holding ${hold:,.2f}")
        return

    # ---------------------------------------------------------------- live
    df = update_history(a.signal_pair)
    e = acct = None
    if os.path.exists(STATE_FILE) and not a.reset:
        try:
            with open(STATE_FILE, "rb") as f:
                st = pickle.load(f)
            e, acct = st["engine"], st["acct"]
            if not isinstance(e, Robot2) or e.eta != a.eta or e.risk != risk:
                e = acct = None
        except Exception as err:
            log(f"saved state not usable ({err}); rebuilding")
    if e is None:
        log("building the robot from the whole history (a few minutes)...")
        e = feed(make(), df, log)
        e.cash, e.coins, e.pending, e.trades, e.fills = a.cash, 0.0, None, [], []
        acct = {"cash": a.cash, "coins": 0.0, "start_cash": a.cash, "trades": 0}
    else:
        missed = df[df["time"].values.astype("datetime64[m]").astype(np.int64) > e.ts[e.n - 1]]
        if len(missed):
            log(f"catching up {len(missed):,} minutes since the last run")
            feed(e, missed)
    save(e, acct)
    log(f"PRACTICE MODE - robot 2 live from {stamp(e.ts[e.n - 1])} UTC, {len(e.library) + 1} trajectories known")

    last_save = time.time()
    try:
        while True:
            try:
                for ts, high, low, close in new_minutes(a.signal_pair, int(e.ts[e.n - 1])):
                    e.step(ts, high, low, close)
                if follow(e, acct, a.pair, a.fee, log):
                    save(e, acct)
                bid = float(get(f"/asset_pairs/{a.pair}/ticker")["bid"]["price"])
                value = acct["cash"] + acct["coins"] * bid
                s = e.setting
                log(f"{stamp(e.ts[e.n - 1])[5:]}  price {e.cl[e.n - 1]:.4f}  "
                    f"setting {f'{s[0]}/{s[1]}' if s else 'none yet'}  every {e.interval} min  "
                    f"line {e.line + 1}%  trajectory {len(e.library) + 1} (library {e.w * 100:.0f}%)  "
                    f"holding {'PEARL' if acct['coins'] else 'USDC'}  "
                    f"account ${value:,.2f} ({(value / acct['start_cash'] - 1) * 100:+.1f}%)")
                if time.time() - last_save > 3600:
                    save(e, acct)
                    last_save = time.time()
            except Exception as err:
                log(f"[warn] {err}")
                time.sleep(10)
    except KeyboardInterrupt:
        save(e, acct)
        log("\nStopped. Run again to continue from the saved state.")


if __name__ == "__main__":
    main()
