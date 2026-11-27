#!/usr/bin/env python3
"""Fair comparison: the SAME four AIs, tested at about the SAME time (Aug-Nov 2025), split by stocks and crypto.
Stocks: average of LiveTradeBench (US stocks, live 18 Aug-24 Oct 2025) and AI-Trader (Nasdaq-100, 1 Oct-7 Nov 2025).
Crypto: AI-Trader (10 coins, 1-14 Nov 2025). Only these four AIs appear in both papers.
    python3 research/same_models_same_time.py -> research/same_models_same_time.png"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["text.parse_math"] = False
OPEN, CLOSED, INK, INK2, GRID, SURF = "#1baf7a", "#6250d6", "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
#             name, open?, LiveTradeBench stocks, AI-Trader stocks, AI-Trader crypto
M = [("DeepSeek-V3.1\n(open-source)", 1, 2.46, 8.39, -12.18),
     ("Claude 3.7 Sonnet\n(closed)", 0, 3.63, 3.11, -15.30),
     ("GPT-5 / ChatGPT\n(closed)", 0, 5.31, 1.56, -16.41),
     ("Gemini 2.5 Flash\n(closed)", 0, 2.10, -0.06, -18.63)]
fig, axes = plt.subplots(1, 2, figsize=(13, 5.8), facecolor=SURF)
panels = [("STOCKS, Aug-Nov 2025\naverage of 2 tests (LiveTradeBench + AI-Trader)", [(a + b) / 2 for _, _, a, b, _ in M], None),
          ("CRYPTO, 1-14 Nov 2025\nAI-Trader (crypto market fell 14.3%)", [c for *_, c in M], -14.30)]
for ax, (title, vals, mkt) in zip(axes, panels):
    order = sorted(range(len(M)), key=lambda i: -vals[i])
    for x, i in enumerate(order):
        v = vals[i]
        ax.bar(x, v, color=OPEN if M[i][1] else CLOSED, width=0.6)
        ax.annotate(f"{v:+.1f}%", (x, v), xytext=(0, 4 if v >= 0 else -4), textcoords="offset points", ha="center",
                    va="bottom" if v >= 0 else "top", fontsize=11, color=INK, weight="bold")
        ax.annotate(f"#{x + 1}", (x, 0), xytext=(0, -14 if v >= 0 else 6), textcoords="offset points", ha="center",
                    fontsize=9, color=INK2)
    ax.set_xticks(range(len(M)), [M[i][0] for i in order], fontsize=9, color=INK2)
    if mkt is not None:
        ax.axhline(mkt, color=INK, lw=1.5, ls=(0, (4, 3)))
        ax.annotate("market (holding the coins)", (len(M) - 0.6, mkt), xytext=(0, 4), textcoords="offset points",
                    ha="right", fontsize=8, color=INK)
    ax.axhline(0, color=INK2, lw=1)
    lo, hi = min(vals + [0, mkt or 0]), max(vals + [0])
    pad = (hi - lo) * 0.18 + 0.5
    ax.set_ylim(lo - pad, hi + pad)
    ax.set_title(title, fontsize=11, color=INK, weight="bold")
    ax.set_ylabel("Return (%)", color=INK2, fontsize=9)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(axis="y", colors=INK2, labelsize=8)
    ax.set_facecolor(SURF)
fig.suptitle("Same 4 AIs, same months: open-source DeepSeek came 1st in both stocks and crypto",
             fontsize=13, color=INK, weight="bold", x=0.01, ha="left")
fig.tight_layout(rect=(0, 0, 1, 0.95))
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "same_models_same_time.png")
fig.savefig(out, dpi=110, facecolor=SURF)
print(out)
