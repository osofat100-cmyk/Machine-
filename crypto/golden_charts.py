"""Charts of the golden-rule runs: money over market time against the yardstick (Bitcoin / SPY)."""
import csv
import os
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
plt.rcParams["text.parse_math"] = False

ROOT = "/home/user/Machine-"
SLOTS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def load(path, bench):
    if not os.path.exists(path):
        return [], [], []
    rows = [r for r in csv.DictReader(open(path)) if r.get("time") not in (None, "time")]
    t = [datetime.strptime(r["time"], "%Y-%m-%d %H:%M") for r in rows]
    return t, [float(r["value"]) for r in rows], [float(r[bench]) for r in rows]


def tx(t, stock):
    """Stocks: count trading minutes so nights and weekends take no room."""
    if not stock:
        return t
    return [DAYS.setdefault(x.date(), len(DAYS)) * 390 + (x.hour * 60 + x.minute - 570) for x in t]


DAYS = {}


def panel(ax, title, runs, bench_name, bench_key, stock=False):
    bench = {}
    for i, (label, path) in enumerate(runs):
        t, v, b = load(path, bench_key)
        if not t:
            continue
        bench.update(zip(t, b))
        x = tx(t, stock)
        ax.plot(x, v, color=SLOTS[i], lw=2, label=label, solid_capstyle="round")
        ax.annotate(f"{label}  ${v[-1]:,.0f}", (x[-1], v[-1]), xytext=(4, 0), textcoords="offset points",
                    fontsize=8, color=INK2, va="center")
    if bench:
        bt = sorted(bench)
        bx, by = tx(bt, stock), [bench[x] for x in bt]
        ax.plot(bx, by, color=INK, lw=2, ls=(0, (4, 3)), label=f"Holding {bench_name}")
        ax.annotate(f"{bench_name}  ${by[-1]:,.0f}", (bx[-1], by[-1]), xytext=(4, 0),
                    textcoords="offset points", fontsize=8, color=INK, va="center", weight="bold")
    ax.axhline(1000, color=INK2, lw=1, alpha=0.5)
    ax.set_title(title, loc="left", fontsize=12, color=INK, weight="bold")
    ax.set_ylabel("Money ($, started at $1,000)", color=INK2, fontsize=9)
    ax.grid(axis="y", color=GRID, lw=1)
    ax.set_facecolor(SURF)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8)
    if stock:
        ax.set_xticks([d * 390 for d in DAYS.values()], [k.strftime("%d %b") for k in DAYS])
    else:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.legend(loc="upper left", fontsize=8, frameon=False, ncol=3)


def crypto():
    c = f"{ROOT}/crypto"
    speeds_a = [2, 3, 4, 10, 15, 30, 60]
    speeds_b = [2, 3, 4, 5, 10, 15, 30, 60]
    fig, axes = plt.subplots(2, 1, figsize=(13, 10), facecolor=SURF)
    panel(axes[0], "Crypto, first version (golden rule only)",
          [(f"every {k}", f"{c}/answers_1m_every{k}_v4a_ultrafast.csv") for k in speeds_a], "Bitcoin", "btc_hold")
    panel(axes[1], "Crypto, second version (golden rule + spread the risk + trade rarely)",
          [(f"every {k}", f"{c}/answers_1m_every{k}_v4b_ultrafast.csv") for k in speeds_b], "Bitcoin", "btc_hold")
    for ax in axes:
        ax.set_xlabel("Market time (UTC); runs end where they have reached so far", color=INK2, fontsize=9)
    fig.tight_layout()
    out = f"{c}/golden_rule_chart.png"
    fig.savefig(out, dpi=110, facecolor=SURF)
    print(out)


def stock():
    g = f"{ROOT}/sp500/golden"
    speeds = [1, 2, 3, 4, 5, 10, 15, 30]
    fig, axes = plt.subplots(2, 1, figsize=(13, 9), facecolor=SURF)
    for ax, (v, name) in zip(axes, (("v4a", "first version (golden rule only)"),
                                    ("v4b", "second version (golden rule + spread the risk + trade rarely)"))):
        panel(ax, f"Stocks, {name}",
              [(f"every {k}", f"{g}/answers_1m{'' if k == 1 else f'_every{k}'}_{v}_ultrafast.csv") for k in speeds],
              "SPY", "spy_hold", stock=True)
        ax.set_xlabel("Trading days (New York, 9:30-16:00; nights left out); runs end where they have reached so far",
                      color=INK2, fontsize=9)
    fig.tight_layout()
    out = f"{g}/golden_rule_chart.png"
    fig.savefig(out, dpi=110, facecolor=SURF)
    print(out)


crypto()
stock()
