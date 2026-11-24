#!/usr/bin/env python3
"""One simple chart: average return of open-source vs closed AIs in each published trading test, next to the market.
Numbers are the averages of the per-model returns in research/open_vs_closed_trading.py.
    python3 research/open_vs_closed_simple.py -> research/open_vs_closed_simple.png"""
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
plt.rcParams["text.parse_math"] = False
OPEN, CLOSED, MKT, INK, INK2, GRID, SURF = "#1baf7a", "#6250d6", "#898781", "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
NAMES = ["StockBench: US stocks 2025", "AI-Trader: US stocks 2025", "AI-Trader: crypto 2025",
         "LiveTradeBench: US stocks 2025", "PolyBench: betting markets 2026", "Beta-not-Alpha: US stocks 2026*"]


def main():
    import open_vs_closed_trading as T                  # the per-model numbers (builds the detailed chart too)
    rows = []
    for name, (_, _, bv, d) in zip(NAMES, T.P):
        o = [v for v, op in d.values() if op]
        c = [v for v, op in d.values() if not op]
        rows.append((name, sum(o) / len(o), len(o), sum(c) / len(c), len(c), bv))
    fig, axes = plt.subplots(2, 3, figsize=(13, 8), facecolor=SURF)
    for ax, (name, o, no, c, nc, bv) in zip(axes.flat, rows):
        labels, vals, cols = [f"Open-source\n({no} AIs)", f"Closed\n({nc} AIs)"], [o, c], [OPEN, CLOSED]
        if bv is not None:
            labels.append("Break even" if name.startswith("Poly") else "Market"); vals.append(bv); cols.append(MKT)
        ax.bar(range(len(vals)), vals, color=cols, width=0.6)
        for x, v in enumerate(vals):
            ax.annotate(f"{v:+.1f}%", (x, v), xytext=(0, 4 if v >= 0 else -4), textcoords="offset points",
                        ha="center", va="bottom" if v >= 0 else "top", fontsize=10, color=INK, weight="bold")
        ax.set_xticks(range(len(vals)), labels, fontsize=9, color=INK2)
        ax.axhline(0, color=INK2, lw=1)
        lo, hi = min(vals + [0]), max(vals + [0])
        pad = (hi - lo) * 0.25 + 0.5
        ax.set_ylim(lo - pad, hi + pad)
        win = "Open-source did better" if o > c else "Closed did better"
        ax.set_title(f"{name}\n{win}", fontsize=10.5, color=INK, weight="bold")
        ax.set_ylabel("Average return (%)", color=INK2, fontsize=8)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        for sp in ("left", "bottom"):
            ax.spines[sp].set_color(GRID)
        ax.tick_params(axis="y", colors=INK2, labelsize=8)
        ax.set_facecolor(SURF)
    fig.suptitle("Open-source vs closed AIs (ChatGPT, Claude, Gemini, Grok): average return in each published trading test",
                 fontsize=12.5, color=INK, weight="bold", x=0.01, ha="left")
    fig.text(0.01, 0.005, "* only one open-source AI in that test (a tiny 3B Llama), so it is not a fair comparison. "
             "LiveTradeBench published no market number for its stock list.", fontsize=8, color=INK2)
    fig.tight_layout(rect=(0, 0.02, 1, 0.96))
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "open_vs_closed_simple.png")
    fig.savefig(out, dpi=110, facecolor=SURF)
    print(out)
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
