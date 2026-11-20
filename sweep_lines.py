"""Line graphs of the buy/sell sweep (reads data/sweep_all.csv from: python3 sweep.py --all)."""
import sys, os

import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

m = pd.read_csv("data/sweep_all.csv", index_col=0); m.columns = m.columns.astype(float)
steps = m.index.values.astype(float)            # same 0.5..100 for both
HOLD = 4183
surface, ink, ink2, muted, gridc = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
colors = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
plt.rcParams.update({"font.size": 12, "text.color": ink, "axes.labelcolor": ink2,
                     "xtick.color": muted, "ytick.color": muted, "axes.edgecolor": "#c3c2b7"})

def smooth(y, k=7):
    pad = np.pad(np.asarray(y, float), k // 2, mode="edge")
    return np.convolve(pad, np.ones(k) / k, mode="valid")

fig, axes = plt.subplots(2, 1, figsize=(12, 13), facecolor=surface)
fig.subplots_adjust(hspace=0.35, right=0.84)
charts = [
    (axes[0], "SELL %  (how far it rises above the 4-hour low before we sell)",
     "One line per BUY setting: moving the SELL % from 0.5 to 100", [1, 5, 10, 20], "buy",
     lambda v: m[v].values),
    (axes[1], "BUY %  (how far PEARL falls in 4 hours before we buy)",
     "One line per SELL setting: moving the BUY % from 0.5 to 100", [5, 10, 30, 50], "sell",
     lambda v: m.loc[v].values),
]
for ax, xlabel, title, values, word, get in charts:
    ax.set_facecolor(surface)
    for lvl, txt in ((HOLD, f"just holding ${HOLD:,}"), (1000, "start $1,000")):
        ax.axhline(lvl, color=muted, lw=1, ls=(0, (4, 3)), zorder=1)
        ax.text(100, lvl, f" {txt}", color=ink2, fontsize=10, va="center", ha="left", clip_on=False)
    for v, col in zip(values, colors):
        y = smooth(get(v))
        ax.plot(steps, y, color=col, lw=2.2, zorder=3, label=f"{word} {v:g}%")
        k = int(np.argmax(y))
        ax.plot([steps[k]], [y[k]], "o", ms=8, color=col, mec=surface, mew=2, zorder=4)
        ax.annotate(f"{word} {v:g}%: peak ${y[k]:,.0f}", (steps[k], y[k]), xytext=(6, 6),
                    textcoords="offset points", fontsize=10, color=ink, zorder=5,
                    bbox=dict(boxstyle="round,pad=0.15", fc=surface, ec="none", alpha=0.8))
    ax.set_xlim(0.5, 100); ax.set_ylim(0, None)
    ax.set_xticks(range(0, 101, 10))
    ax.set_xlabel(xlabel); ax.set_ylabel("final money ($)")
    ax.set_title(title, loc="left", fontsize=13, color=ink, pad=10)
    ax.grid(axis="y", color=gridc, lw=0.8)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    ax.legend(loc="upper right", frameon=True, facecolor=surface, edgecolor=gridc, fontsize=10)
fig.suptitle("What $1,000 became (Jul 2 - Nov 20), PEARL on BigONE, 1.4% cost per trade",
             x=0.06, ha="left", fontsize=15, y=0.95)
fig.savefig("sweep_lines.png", dpi=110, facecolor=surface, bbox_inches="tight")
print("ok")
