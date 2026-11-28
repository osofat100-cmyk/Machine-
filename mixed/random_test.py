#!/usr/bin/env python3
"""Random-trader test: was the AI's result skill or luck?
Many random traders go through the same hours as the teams (hourly_server.py, 25 Aug - 23 Nov), under Team 1's limits:
10 holdings, buy only a coin or stock below its own 24-hour average (stocks only while the stock market is open),
never sell below break-even, 0.05% per side. DHN-USD is never bought: its price data jumps 10x in an hour on 2 Oct
(the teams had it blocked from 15 Sep). Each hour, each trader with chance P picks one random holding that is above
break-even, sells it and buys a random dip symbol (a coin with chance COIN, like the teams' mix). They never hold cash on purpose. Prices stay in memory; only account values are saved.
    python3 mixed/random_test.py N P1,P2,...   -> mixed/random_test.json (N traders for each chance P)"""
import json
import os
import random
import sys

os.environ.update({"STEP_MIN": "60", "AVG_DAYS": "1", "BLOCK": "DHN-USD", "BLOCK_FROM": "2026-09-15 12:00",
                   "TAG": "zz_random"})
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mixed_trader as M  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
N = int(sys.argv[1]) if len(sys.argv) > 1 else 200
PS = [float(x) for x in (sys.argv[2] if len(sys.argv) > 2 else "0.05").split(",")]
START, COIN, SLOTS = "2026-08-25 00:00", 0.95, 10
CHECK = ["2026-09-21 09:00", "2026-09-27 07:00", "2026-10-12 00:00", "2026-11-20 23:00"]
rng = random.Random(1)
names = [f"r{p}_{i}" for p in PS for i in range(N)]
chance = {n: float(n[1:].split("_")[0]) for n in names}
entries = {n: {} for n in names}
pending = {n: [] for n in names}
sells = {n: 0 for n in names}
hist = {n: [] for n in names}
view, orders = M.View(), {}
with M.Server() as srv:
    while True:
        out = srv.next(orders)
        if out.get("done"):
            break
        view.add(out)
        st, accs, orders = out["step"], out["accounts"], {}
        for n in names:                                    # fills: entry price is the open of the hour it filled
            held = accs.get(n, {}).get("shares", {})
            for s in pending[n]:
                if s in held and s not in entries[n]:
                    entries[n][s] = st["open"][s]
            for s in list(entries[n]):
                if s not in held:
                    entries[n].pop(s)
            pending[n] = []
            if n in accs:
                hist[n].append((st["time"], accs[n]["value"]))
        if st["time"] < START or out["last_step"]:
            continue
        c = st["close"]
        dips = {"crypto": [], "stock": []}
        for s, k in view.kind.items():
            a = view.avg24(s)
            if s in c and a and c[s] < a and s not in M.BAD_SYMBOLS and s != "SPY" and \
                    (k == "crypto" or st["stock_market_open"]):
                dips[k].append(s)

        def pick(own):
            k = "stock" if (rng.random() > COIN and st["stock_market_open"] and dips["stock"]) else "crypto"
            free = [s for s in dips[k] if s not in own]
            return rng.choice(free) if free else None

        for n in names:
            held = accs.get(n, {}).get("shares", {})
            own, acts = set(held), []
            if not held:                                   # first hour: fill all 10 slots
                for _ in range(SLOTS):
                    s = pick(own)
                    if s:
                        own.add(s)
                        acts.append({"action": "BUY", "symbol": s, "split": True})
            elif rng.random() < chance[n]:
                winners = sorted(x for x in held if x in entries[n] and c[x] * 0.9995 >= entries[n][x] * 1.0005
                                 and (view.kind.get(x) == "crypto" or st["stock_market_open"]))
                if winners:
                    s = rng.choice(winners)
                    b = pick(own)
                    if b:
                        acts = [{"action": "SELL", "symbol": s}, {"action": "BUY", "symbol": b, "split": True}]
                        sells[n] += 1
            if acts:
                orders[n] = acts
                pending[n] = [a["symbol"] for a in acts if a["action"] == "BUY"]


def at(h, t):
    xs = [v for tt, v in h if tt <= t]
    return xs[-1] if xs else None


res = {}
for p in PS:
    grp = [n for n in names if chance[n] == p]
    res[str(p)] = {"sells": [sells[n] for n in grp], "end": [hist[n][-1][1] for n in grp],
                   "peak": [max(v for _, v in hist[n]) for n in grp],
                   **{t: [at(hist[n], t) for n in grp] for t in CHECK}}
    e = sorted(res[str(p)]["end"])
    print(f"P={p}: average sells {sum(res[str(p)]['sells']) / len(grp):.0f}, end median ${e[len(e) // 2]:.0f}, "
          f"range ${e[0]:.0f}-${e[-1]:.0f}", flush=True)
json.dump(res, open(os.path.join(HERE, "random_test.json"), "w"))
