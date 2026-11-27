#!/usr/bin/env python3
"""The whole-market line the teams read (the average coin, plus the average stock while the stock market is open,
chained hour by hour into one level), with its 3-day and 2-week averages. Prices come from hourly_server.py and stay
in memory; only the picture is saved. Up and down stretches are labelled afterwards by looking at the whole picture,
so the labels use hindsight and are not something a trader could have known at the time.
    python3 mixed/market_chart.py -> mixed/market_chart.png"""
import os
import sys

os.environ.update({"STEP_MIN": "60", "AVG_DAYS": "1", "MKT_AVGS": "1", "BLOCK": "DHN-USD",
                   "BLOCK_FROM": "2026-09-15 12:00", "TAG": "zz_market"})
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd  # noqa: E402
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.dates as mdates  # noqa: E402
import mixed_trader as M  # noqa: E402

plt.rcParams["text.parse_math"] = False
HERE = os.path.dirname(os.path.abspath(__file__))
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
COL = {"up": "#16855c", "down": "#c0392b", "flat": "#8f8d86"}
# stretches read off the picture (hindsight). Argument 1: the edges, comma-separated; argument 2: the kind of each
# stretch between them (up, down or flat), comma-separated.
LABELS = [x.split(",") for x in sys.argv[1:3]]   # an end written as "low:A:B" or "high:A:B" snaps to the
# lowest or highest hour between A and B

view, t, v = M.View(), [], []
with M.Server() as srv:
    while True:
        out = srv.next({})
        if out.get("done"):
            break
        view.add(out)
        t.append(out["step"]["time"])
        v.append(view.idx[-1])
s = pd.Series(v, index=pd.to_datetime(t))
s = s[s.index >= "2026-08-25"]
s = s / s.iloc[0] * 100
def snap(x):
    if ":" not in x or x.count(":") < 2 or x.split(":")[0] not in ("low", "high"):
        return x
    k, a, b = x.split(":", 2)
    seg = s[a:b]
    return str(seg.idxmin() if k == "low" else seg.idxmax())


marks = [snap(x) for x in LABELS[0]] if LABELS else []
LABELS = [(marks[i], marks[i + 1], LABELS[1][i]) for i in range(len(marks) - 1)] if LABELS else []
fig, ax = plt.subplots(figsize=(14, 6.6), facecolor=SURF)
for a, b, kind in LABELS:
    ax.axvspan(pd.Timestamp(a), pd.Timestamp(b), color=COL[kind], alpha=0.10, lw=0)
    seg = s[a:b]
    ax.text(pd.Timestamp(a) + (pd.Timestamp(b) - pd.Timestamp(a)) / 2, s.max() * 1.01,
            f"{kind.upper()}\n{100 * (seg.iloc[-1] / seg.iloc[0] - 1):+.0f}%", ha="center", va="bottom", fontsize=9,
            color=COL[kind], weight="bold")
ax.plot(s.index, s, color=INK2, lw=0.8, alpha=0.6, label="Whole market, hour by hour")
ax.plot(s.index, s.rolling(72, min_periods=1).mean(), color="#eb6834", lw=2.2, label="3-day average")
ax.plot(s.index, s.rolling(336, min_periods=1).mean(), color="#2a78d6", lw=2.2, label="2-week average")
ax.axhline(100, color=INK2, lw=1, alpha=0.4)
ax.set_ylim(s.min() * 0.97, s.max() * 1.08)
ax.set_title(f"The whole-market line the AIs read, 25 Aug to {s.index[-1]:%d %b} (25 Aug = 100)", loc="left",
             fontsize=12.5, color=INK, weight="bold")
ax.set_ylabel("Whole-market level", color=INK2, fontsize=9)
ax.legend(loc="lower center", fontsize=9.5, frameon=False)
ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=0))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
ax.grid(axis="y", color=GRID, lw=1)
ax.set_facecolor(SURF)
for sp in ("top", "right"):
    ax.spines[sp].set_visible(False)
for sp in ("left", "bottom"):
    ax.spines[sp].set_color(GRID)
ax.tick_params(colors=INK2, labelsize=8.5)
fig.tight_layout()
fig.savefig(os.path.join(HERE, "market_chart.png"), dpi=120, facecolor=SURF)
for d in pd.date_range("2026-08-25", s.index[-1], freq="7D"):
    print(f"{d:%d %b}: {s[s.index >= d].iloc[0]:.1f}")
print(f"end {s.index[-1]:%d %b %H:%M}: {s.iloc[-1]:.1f}, high {s.max():.1f} on {s.idxmax():%d %b}, low {s.min():.1f} on {s.idxmin():%d %b}")
# when the 3-day average crosses the 2-week average (both use only the hours before, no hindsight)
a3, a14 = s.rolling(72, min_periods=72).mean(), s.rolling(336, min_periods=336).mean()
below = (a3 < a14)[a14.notna()]
for when, b in below[below != below.shift()].items():
    print(f"{when:%d %b %H:%M}: 3-day goes {'BELOW' if b else 'ABOVE'} 2-week, market {s[when]:.1f}")
