#!/usr/bin/env python3
"""
Robot 2, live. PRACTICE MODE: fake money, NO real orders.

On start it downloads PEARL's minute history from BigONE and learns from all of it:
  - every buy%/sell% setting (0.1% steps) and the money it made, after the 0.7% cost per side
  - how each update interval (every 1 ... 1,440 minutes) did over that history
Then, every new minute:
  1. adds the minute and updates every setting's money
  2. finds the top of the smoothed landscape (the best setting so far)
  3. each of the 1,440 interval machines takes the new top when its interval comes round
  4. the robot picks the safest interval (middle of the biggest stretch at or above the average)
     and uses that interval's latest setting
  5. buys or sells practice money at the real PEARL-USDC order book

    python3 live_machine.py                    # live
    python3 live_machine.py --reset            # new practice account with $1,000
    python3 live_machine.py --replay-from 2026-11-13
        # test: learn from the history before that day, then feed the rest in minute by minute

The first start takes several minutes (it replays the history once); later starts reuse
data/robot2_prior_*.npz.
"""
import argparse
import csv
import json
import os
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from fetch_history import fetch, get
from landscape import COST, Market
from paper_trader import book_fill
from robots import DELTAS, HillTop, all_events, grids, landscape_picks, run_robots, safest

HISTORY = "data/PEARL-USDT_min1.csv"
STATE_FILE = "robot2_state.json"
TRADE_LOG = "logs/robot2_trades.csv"
PICK_LOG = "logs/robot2_picks.csv"
WARMUP = 240                                     # minutes needed before the 4-hour numbers exist


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


class LiveSource:
    """New finished minutes from BigONE."""

    def __init__(self, pair, last_time):
        self.pair, self.last = pair, last_time

    def next_minutes(self):
        while True:
            candles = get(f"/asset_pairs/{self.pair}/candles?period=min1&limit=50")
            this_min = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:00Z")
            new = sorted((c for c in candles if c["time"] != this_min and pd.Timestamp(c["time"]) > self.last),
                         key=lambda c: c["time"])
            if new:
                self.last = pd.Timestamp(new[-1]["time"])
                return [(pd.Timestamp(c["time"]), float(c["high"]), float(c["low"]), float(c["close"])) for c in new]
            time.sleep(5)


class ReplaySource:
    """Feeds saved minutes one batch at a time (for testing the live code)."""

    def __init__(self, df):
        self.rows = list(df[["time", "high", "low", "close"]].itertuples(index=False))
        self.i = 0

    def next_minutes(self):
        if self.i >= len(self.rows):
            return None
        r = self.rows[self.i]
        self.i += 1
        return [(r.time, float(r.high), float(r.low), float(r.close))]


def learn_history(df_hist, log):
    """Settings' state at the end of the history, the grid, and each interval's money over it."""
    m = Market(df=df_hist.set_index("time"), warmup=WARMUP)
    buy, sell = grids(m)
    ev = all_events(m, buy, sell)
    nb, ns = len(buy), len(sell)
    t, sid, kind, amt = ev
    cash = np.full(nb * ns, 1000.0)
    coins = np.zeros(nb * ns)
    for e in range(len(t)):
        if kind[e] == 1:
            coins[sid[e]], cash[sid[e]] = amt[e], 0.0
        else:
            cash[sid[e]], coins[sid[e]] = amt[e], 0.0
    log(f"learned {len(buy) * len(sell):,} settings over {m.n:,} minutes "
        f"({m.time[0]:%b %d} - {m.time[-1]:%b %d %H:%M})")

    cache = f"data/robot2_prior_{m.time[-1]:%Y%m%d%H%M}.npz"
    if os.path.exists(cache):
        F_all = np.load(cache)["F_all"]
        log(f"interval history loaded from {cache}")
    else:
        log("replaying the history once to learn how each update interval did (several minutes)...")
        PB, PS, _, _ = landscape_picks(m, ev, buy, sell, log, robot2=False)
        F_all = run_robots(m, PB, PS, lambda F: {}, {}, lambda k, iv: None)
        np.savez_compressed(cache, F_all=F_all)
    log(f"over the history the safest interval was every {safest(F_all)} minutes")
    return buy, sell, cash, coins, F_all


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pair", default="PEARL-USDC", help="pair the practice trades are priced on")
    ap.add_argument("--signal-pair", default="PEARL-USDT", help="pair the robot learns from")
    ap.add_argument("--fee", type=float, default=0.2)
    ap.add_argument("--cash", type=float, default=1000.0)
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--replay-from", help="test mode: learn before this UTC day, replay the rest")
    a = ap.parse_args()
    log = lambda *x: print(*x, flush=True)
    replay = a.replay_from is not None
    state_file = "robot2_replay_state.json" if replay else STATE_FILE
    trade_log = TRADE_LOG.replace(".csv", "_replay.csv") if replay else TRADE_LOG

    if replay:
        df = pd.read_csv(HISTORY, parse_dates=["time"])
        cut = pd.Timestamp(a.replay_from, tz="UTC")
        df_hist, source = df[df["time"] < cut].reset_index(drop=True), ReplaySource(df[df["time"] >= cut])
        if os.path.exists(state_file):
            os.remove(state_file)
    else:
        df_hist = update_history(a.signal_pair)
        source = LiveSource(a.signal_pair, df_hist["time"].iloc[-1])

    buy, sell, cash_s, coins_s, F_all = learn_history(df_hist, log)
    nb, ns = len(buy), len(sell)
    B = np.tile(buy, ns)                        # each setting's buy %  (row = sell, col = buy)
    S = np.repeat(sell, nb)                     # each setting's sell %
    top = HillTop(nb, ns)

    hi = list(df_hist["high"].astype(float))
    lo = list(df_hist["low"].astype(float))
    cl = list(df_hist["close"].astype(float))
    times = list(df_hist["time"])

    if a.reset and os.path.exists(state_file):
        os.remove(state_file)
    acct = {"cash": a.cash, "coins": 0.0, "start_cash": a.cash, "trades": 0, "buy_price": 0.0}
    if os.path.exists(state_file):
        with open(state_file) as f:
            acct = json.load(f)

    n_d = len(DELTAS)
    sh_cash, sh_coins = np.full(n_d, 1000.0), np.zeros(n_d)
    sh_b, sh_s = np.full(n_d, np.nan), np.full(n_d, np.nan)
    pend_s = pend_sh = None                     # decisions waiting for the next minute's price
    picks = {}
    T0 = len(cl) - 1
    last_pick = None
    log(f"PRACTICE MODE - robot 2 {'(replay)' if replay else '(live)'} starts at {times[-1]:%b %d %H:%M} UTC")

    k = T0
    while True:
        c = cl[k]
        # 1. fill yesterday-minute decisions at this minute's price
        if pend_s is not None:
            buy_m, sell_m = pend_s
            coins_s[buy_m], cash_s[buy_m] = cash_s[buy_m] / (c * (1 + COST)), 0.0
            cash_s[sell_m], coins_s[sell_m] = coins_s[sell_m] * c * (1 - COST), 0.0
            buy_m, sell_m = pend_sh
            sh_coins[buy_m], sh_cash[buy_m] = sh_cash[buy_m] / (c * (1 + COST)), 0.0
            sh_cash[sell_m], sh_coins[sell_m] = sh_coins[sell_m] * c * (1 - COST), 0.0
            if acct.get("pending") and replay:
                side = acct.pop("pending")
                if side == "BUY":
                    acct["coins"], acct["cash"], acct["buy_price"] = acct["cash"] / (c * (1 + COST)), 0.0, c
                else:
                    acct["cash"], acct["coins"] = acct["coins"] * c * (1 - COST), 0.0
                acct["trades"] += 1
                log_row(trade_log, ["time_utc", "action", "price", "usdc_after", "buy_pct", "sell_pct", "interval_min"],
                        [f"{times[k]:%Y-%m-%d %H:%M}", side, round(c, 4), round(acct["cash"], 2)] + acct.pop("why"))

        # 2. the three 4-hour numbers for this minute
        L, H = min(lo[k - 239:k + 1]), max(hi[k - 239:k + 1])
        U, D, R = (c / L - 1) * 100, (1 - c / H) * 100, (c / cl[k - 240] - 1) * 100
        at_low, near_high = U <= 0.23, D <= 1.8

        # 3. every setting's money so far, and the top of the smoothed landscape
        V = np.where(coins_s > 0, coins_s * c * (1 - COST), cash_s).reshape(ns, nb).astype(np.float32)
        v, (i, j) = top(V)
        picks[k] = (float(buy[j]), float(sell[i])) if v > 1000.0 else None

        # 4. interval machines take the new top when their interval comes round
        upd = ((k - T0) % DELTAS) == 0
        if picks[k]:
            sh_b[upd], sh_s[upd] = picks[k]
        F = sh_cash + sh_coins * c * (1 - COST)
        interval = safest(F_all * F / 1000.0)
        u = T0 + ((k - T0) // interval) * interval
        setting = picks.get(u)

        # 5. the robot's own decision
        holding = acct["coins"] > 0
        action = None
        if setting:
            b, s = setting
            if not holding and at_low and R <= -b:
                action = "BUY"
            elif holding and near_high and U >= s:
                action = "SELL"
        if action and replay:
            acct["pending"], acct["why"] = action, [b, s, interval]
        elif action:
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
            if action == "BUY":
                coins, avg = book_fill(a.pair, "buy", acct["cash"])
                acct.update(coins=coins * (1 - a.fee / 100), cash=0.0, buy_price=avg)
            else:
                usdc, avg = book_fill(a.pair, "sell", acct["coins"])
                acct.update(cash=usdc * (1 - a.fee / 100), coins=0.0)
            acct["trades"] += 1
            log_row(trade_log, ["time_utc", "action", "price", "usdc_after", "buy_pct", "sell_pct", "interval_min"],
                    [now, action, round(avg, 4), round(acct["cash"], 2), b, s, interval])
            log(f"*** {action} at {avg:.4f}  (setting {b}% / {s}%, updating every {interval} min)")

        # 6. decisions for every setting and every interval machine, filled next minute
        if at_low or near_high:
            hold_s = coins_s > 0
            pend_s = (~hold_s & at_low & (R <= -B), hold_s & near_high & (U >= S))
            hold_sh, has = sh_coins > 0, ~np.isnan(sh_b)
            pend_sh = (has & ~hold_sh & at_low & (R <= -np.nan_to_num(sh_b, nan=1e9)),
                       has & hold_sh & near_high & (U >= np.nan_to_num(sh_s, nan=1e9)))
        else:
            pend_s = (np.zeros(nb * ns, bool), np.zeros(nb * ns, bool))
            pend_sh = (np.zeros(n_d, bool), np.zeros(n_d, bool))

        if setting != last_pick:
            log_row(PICK_LOG.replace(".csv", "_replay.csv") if replay else PICK_LOG,
                    ["time_utc", "buy_pct", "sell_pct", "interval_min"],
                    [f"{times[k]:%Y-%m-%d %H:%M}"] + (list(setting) if setting else ["", ""]) + [interval])
            last_pick = setting
        with open(state_file, "w") as f:
            json.dump(acct, f, indent=2)
        value = acct["cash"] + acct["coins"] * c * (1 - COST)
        if not replay or (k - T0) % 1440 == 0:
            log(f"{times[k]:%b %d %H:%M}  price {c:.4f}  setting {setting[0] if setting else '-'}/"
                f"{setting[1] if setting else '-'}  every {interval} min  "
                f"holding {'PEARL' if acct['coins'] else 'USDC'}  account ${value:,.2f} "
                f"({(value / acct['start_cash'] - 1) * 100:+.1f}%)")

        # next minute (if several arrived at once, work through them one by one)
        if k + 1 >= len(cl):
            new = source.next_minutes()
            if new is None:
                hold = acct["start_cash"] * cl[-1] / cl[T0] * (1 - COST) ** 2
                log(f"\nreplay finished: robot 2 ${value:,.2f} after {acct['trades']} trades; "
                    f"just holding ${hold:,.2f}")
                return
            for t_, h_, l_, c_ in new:
                times.append(t_); hi.append(h_); lo.append(l_); cl.append(c_)
        k += 1


if __name__ == "__main__":
    main()
