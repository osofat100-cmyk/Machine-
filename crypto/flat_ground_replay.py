#!/usr/bin/env python3
"""
Flat-ground (market-free) gain of every finished crypto golden-rule run, measured with "twins".

The data is read the same way the traders read it: through crypto/crypto_server.py (the only program that opens the
sealed data). This program replays every run's saved orders through ONE server pass, exactly as the trader did
(same decision minutes, same golden-rule blocking, same fills at the next step's open, same 0.05% costs), and checks
that it reproduces each run's recorded money to the cent. Then it builds twins that copy the run's timing, money
flows, costs and number of coins held, but replace each coin it picked:

  size twin    each pick -> the equal-weight basket of all coins in the same size group, bought and sold at the same
               minutes (a "characteristic-matched benchmark", Daniel, Grinblatt, Titman & Wermers 1997, with size
               as the characteristic). Same market, same size of coins, same timing, no picking skill.
  market twin  each pick -> the equal-weight basket of all 100 coins.
  random twins each pick -> ONE coin drawn at random from the same size group (not already held), 1,000 times
               ("random portfolios", Burns 2006). The share of random twins that ended with at least the run's money
               is the chance that luck alone does as well (a p-value).

Flat-ground gain = run's money - size twin's money, at every hourly mark. Both share the market's moves with the same
invested amount and timing, so the market's pattern cancels; what is left is the effect of WHICH coins were picked.
A check measures how much market pattern is left: the correlation of the hourly flat-ground changes with the hourly
move of the whole market (equal-weight of all 100 coins) and with Bitcoin.

    python3 crypto/flat_ground_replay.py      -> crypto/flat_ground.json, crypto/flat_ground_chart.png
"""
import csv
import http.client
import json
import math
import os
import random
import socket
import subprocess
import sys
from datetime import datetime

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
COST = 0.0005
HOUR, WARMUP = 60, 61
RUNS = [(v, k) for v in ("v4a", "v4b") for k in (2, 3, 4, 5, 10, 15, 30, 60)]
N_RANDOM = 1000


class Server:
    def __enter__(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        self.proc = subprocess.Popen([sys.executable, os.path.join(HERE, "crypto_server.py"), "--port", str(self.port)],
                                     stdout=subprocess.PIPE, text=True, env={**os.environ, "STEP_MIN": "1"})
        line = self.proc.stdout.readline()
        if not line.startswith("ready"):
            self.proc.kill()
            raise RuntimeError(line)
        self.conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=300)
        return self

    def next(self, orders):
        self.conn.request("POST", "/next", body=json.dumps({"orders": orders}))
        return json.loads(self.conn.getresponse().read())

    def __exit__(self, *exc):
        self.conn.close()
        self.proc.terminate()
        self.proc.wait(timeout=30)


def replay(specs=None):
    """One server pass for all runs. Returns prices per step, size groups, executed trades and recorded values.
    specs: optional list of (name, version, decide_every, model_tag); default = the 16 golden-rule ultrafast runs."""
    runs = {}
    specs = specs or [(f"{v}_{k}", v, k, "ultrafast") for v, k in RUNS]
    for name, v, k, tag in specs:
        p = os.path.join(HERE, f"answers_1m_every{k}_{v}_{tag}.csv")
        res = os.path.join(HERE, f"result_1m_every{k}_{v}_{tag}.json")
        if not os.path.exists(res):
            continue
        saved = [r for r in csv.DictReader(open(p)) if r.get("time") and r["time"] != "time"]
        runs[name] = {"v": v, "k": k, "saved": saved, "n": 0, "entries": {}, "pending": [], "trades": [],
                      "recorded": {r["time"]: float(r["value"]) for r in saved if r["value"]},
                      "final": json.load(open(res))["ai"]["value"]}
    steps, groups, orders, step_i, btc_sent = [], {}, {}, 0, False
    values = {name: [] for name in runs}
    with Server() as srv:
        while True:
            out = srv.next(orders)
            if out.get("done"):
                break
            if out.get("universe"):
                groups = {u["symbol"]: u["size"] for u in out["universe"]}
            st = out["step"]
            kidx = len(steps)
            steps.append({"time": st["time"], "open": st["open"], "close": st["close"]})
            accs = out["accounts"]
            for name, r in runs.items():
                acc = accs.get(name, {"value": 1000.0, "cash": 1000.0, "shares": {}})
                values[name].append(acc["value"])
                for od in r["pending"]:                     # same bookkeeping of buy prices as the trader
                    if od["action"] == "BUY" and od["symbol"] in acc["shares"] and od["symbol"] not in r["entries"]:
                        r["entries"][od["symbol"]] = st["open"][od["symbol"]]
                    if od["action"] == "SELL" and od["symbol"] not in acc["shares"]:
                        r["entries"].pop(od["symbol"], None)
                before = r.get("held", set())
                now = set(acc["shares"])
                sold = sorted(before - now)
                bought = list(dict.fromkeys(od["symbol"] for od in r["pending"]      # a repeated BUY is refused
                                            if od["action"] == "BUY" and od["symbol"] in now - before))
                if sold or bought:
                    r["trades"].append((kidx, sold, bought))
                r["held"] = now
            orders = {}
            for r in runs.values():
                r["pending"] = []
            if kidx + 1 <= WARMUP or out["last_step"]:
                continue
            step_i += 1
            if not btc_sent:
                orders["btc_hold"] = [{"action": "BUY", "symbol": "BTC-USD", "all": True}]
                btc_sent = True
            for name, r in runs.items():
                if (step_i - 1) % r["k"]:
                    continue
                row = r["saved"][r["n"]]
                assert row["time"] == st["time"], (name, row["time"], st["time"])
                acts = json.loads(row["actions"])
                acc = accs.get(name, {"shares": {}})
                owned = set(acc["shares"])
                blocked = [a for a in acts if (a["action"] == "BUY") == (a["symbol"] in owned)]
                blocked += [a for a in acts if a["action"] == "SELL" and a["symbol"] in owned and a not in blocked
                            and a["symbol"] in r["entries"]
                            and st["close"][a["symbol"]] * 0.9995 < r["entries"][a["symbol"]] * 1.0005]
                acts = [dict(a, split=True) if a["action"] == "BUY" else a for a in acts if a not in blocked]
                orders[name] = acts
                r["pending"] = acts
                r["n"] += 1
    for name, r in runs.items():                             # the replay must give the recorded money exactly
        assert abs(values[name][-1] - r["final"]) < 0.01, (name, values[name][-1], r["final"])
        for kidx, st in enumerate(steps):
            if st["time"] in r["recorded"]:
                assert abs(values[name][kidx] - r["recorded"][st["time"]]) < 0.011, (name, st["time"])
    return steps, groups, runs, values


def twin(steps, trades, marks, pick):
    """Copy of a run with the same timing, money flows and costs; pick(sym, held_coins) gives {coin: weight}."""
    cash, pos, out, t = 1000.0, {}, [], 0
    for kidx in range(len(steps)):
        while t < len(trades) and trades[t][0] == kidx:
            _, sold, bought = trades[t]
            o = steps[kidx]["open"]
            for s in sold:                                   # sells first, as the server does
                basket = pos.pop(s)
                cash += sum(q * o[c] for c, q in basket.items()) * (1 - COST)
            for s in bought:                                 # cash split evenly over the empty slots
                spend = cash / max(1, 10 - len(pos)) / (1 + COST)
                held = {c for b in pos.values() for c in b}
                w = pick(s, held, o)
                pos[s] = {c: spend * wt / o[c] for c, wt in w.items()}
                cash -= spend * (1 + COST)
            t += 1
        if kidx in marks:
            c = steps[kidx]["close"]
            out.append(cash + sum(q * c[x] for b in pos.values() for x, q in b.items()))
    return np.array(out)


def main():
    cache = os.environ.get("REPLAY_CACHE")                  # optional scratch cache of the server pass (not committed)
    if cache and os.path.exists(cache):
        import pickle
        steps, groups, runs, values = pickle.load(open(cache, "rb"))
    else:
        steps, groups, runs, values = replay()
        if cache:
            import pickle
            pickle.dump((steps, groups, runs, values), open(cache, "wb"))
    by_group = {}
    for s, g in groups.items():
        by_group.setdefault(g, []).append(s)
    first = WARMUP                                           # first decision step (18 Nov 05:31)
    marks = sorted({i for i, st in enumerate(steps) if i >= first and st["time"].endswith(":31")} | {len(steps) - 1})
    mark_set = set(marks)
    times = [steps[i]["time"] for i in marks]

    def basket(members, o):
        live = [c for c in members if c in o]
        return {c: 1 / len(live) for c in live}

    size_pick = lambda s, held, o: basket(by_group[groups[s]], o)
    market_pick = lambda s, held, o: basket(list(groups), o)
    self_pick = lambda s, held, o: {s: 1.0}
    # whole-market and Bitcoin moves at the same marks, for the "pattern left" check
    ew = np.array([np.mean([steps[i]["close"][c] / steps[first]["close"][c] for c in groups if c in steps[first]["close"]])
                   for i in marks])
    btc = np.array([steps[i]["close"]["BTC-USD"] / steps[first]["close"]["BTC-USD"] for i in marks])
    rng = random.Random(7)
    table = []
    for name, r in runs.items():
        run_v = np.array([values[name][i] for i in marks])
        me = twin(steps, r["trades"], mark_set, self_pick)
        assert np.allclose(me, run_v, atol=0.02), (name, me[-1], run_v[-1])     # twin logic = server logic
        size_t = twin(steps, r["trades"], mark_set, size_pick)
        mkt_t = twin(steps, r["trades"], mark_set, market_pick)
        rand_end = []
        for _ in range(N_RANDOM):
            def rpick(s, held, o):
                pool = [c for c in by_group[groups[s]] if c in o and c not in held] or [c for c in by_group[groups[s]] if c in o]
                return {rng.choice(pool): 1.0}
            rand_end.append(twin(steps, r["trades"], {len(steps) - 1}, rpick)[-1])
        rand_end = np.array(rand_end)
        flat = run_v - size_t
        d_flat, d_raw = np.diff(flat), np.diff(run_v)
        d_ew, d_btc = np.diff(np.log(ew)), np.diff(np.log(btc))
        corr = lambda a, b: float(np.corrcoef(a, b)[0, 1])
        table.append({
            "run": f"{'First' if r['v'] == 'v4a' else 'Second'} every {r['k']}", "end": float(run_v[-1]),
            "size_twin_end": float(size_t[-1]), "market_twin_end": float(mkt_t[-1]),
            "flat_vs_size": float(flat[-1]), "flat_vs_market": float(run_v[-1] - mkt_t[-1]),
            "random_median": float(np.median(rand_end)), "random_p5": float(np.percentile(rand_end, 5)),
            "random_p95": float(np.percentile(rand_end, 95)),
            "p_luck": float((1 + np.sum(rand_end >= run_v[-1])) / (1 + N_RANDOM)),
            "corr_market_before": corr(d_raw, d_ew), "corr_market_after": corr(d_flat, d_ew),
            "corr_btc_before": corr(d_raw, d_btc), "corr_btc_after": corr(d_flat, d_btc),
            "trades": sum(len(s) + len(b) for _, s, b in r["trades"]),
            "curve": [round(float(x), 2) for x in flat]})
    json.dump({"times": times, "runs": table}, open(os.path.join(HERE, "flat_ground.json"), "w"), indent=1)
    table.sort(key=lambda d: -d["flat_vs_size"])
    for d in table:
        print(f"{d['run']:16s} end {d['end']:8.2f} | size twin {d['size_twin_end']:8.2f} flat {d['flat_vs_size']:+7.2f} | "
              f"market twin {d['market_twin_end']:8.2f} flat {d['flat_vs_market']:+7.2f} | random median "
              f"{d['random_median']:8.2f} [{d['random_p5']:.0f}-{d['random_p95']:.0f}] p {d['p_luck']:.3f} | corr mkt "
              f"{d['corr_market_before']:+.2f}->{d['corr_market_after']:+.2f} btc {d['corr_btc_before']:+.2f}->"
              f"{d['corr_btc_after']:+.2f}")
    chart(times, table, ew)


def chart(times, table, ew):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    plt.rcParams["text.parse_math"] = False
    SLOTS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
    INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
    t = [datetime.strptime(x, "%Y-%m-%d %H:%M") for x in times]
    fig, axes = plt.subplots(3, 1, figsize=(13, 13), facecolor=SURF, sharex=True,
                             gridspec_kw={"height_ratios": [1, 2.2, 2.2]})
    ax = axes[0]
    ax.plot(t, 1000 * ew - 1000, color=INK, lw=2)
    ax.axhline(0, color=INK2, lw=1, alpha=0.6)
    ax.set_title("The crypto market for reference: $1,000 spread over all 100 coins", loc="left", fontsize=12,
                 color=INK, weight="bold")
    ax.set_ylabel("Gain ($)", color=INK2, fontsize=9)
    for name, ax in (("First", axes[1]), ("Second", axes[2])):
        rows = [d for d in table if d["run"].startswith(name)]
        rows.sort(key=lambda d: int(d["run"].split()[-1]))
        ends = []
        for i, d in enumerate(rows):
            y = np.array(d["curve"])
            k = d["run"].split()[-1]
            ax.plot(t, y, color=SLOTS[i], lw=2, label=f"every {k} min", solid_capstyle="round")
            ends.append([y[-1], y[-1], k])
        ends.sort()
        for j in range(1, len(ends)):
            ends[j][1] = max(ends[j][1], ends[j - 1][1] + 7)
        for y_end, y_lab, k in ends:
            ax.annotate(f"every {k}  {y_end:+.0f}", (t[-1], y_end), xytext=(8, y_lab - y_end), textcoords="offset points",
                        fontsize=8, color=INK2, va="center")
        ax.axhline(0, color=INK2, lw=1, alpha=0.6)
        ax.set_title(f"{name} version: flat-ground gain = run minus its size-matched twin", loc="left", fontsize=12,
                     color=INK, weight="bold")
        ax.set_ylabel("Gain from the coins picked ($)", color=INK2, fontsize=9)
        ax.legend(loc="upper left", fontsize=8, frameon=False, ncol=4)
    for ax in axes:
        ax.grid(axis="y", color=GRID, lw=1)
        ax.set_facecolor(SURF)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(GRID)
        ax.tick_params(colors=INK2, labelsize=8)
    axes[2].xaxis.set_major_formatter(mdates.DateFormatter("%d %b %H:%M"))
    axes[2].set_xlabel("Market time (UTC)", color=INK2, fontsize=9)
    fig.tight_layout()
    out = os.path.join(HERE, "flat_ground_chart.png")
    fig.savefig(out, dpi=110, facecolor=SURF)
    print(out)


if __name__ == "__main__":
    main()
