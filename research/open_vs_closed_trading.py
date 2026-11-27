#!/usr/bin/env python3
"""Open-weight vs closed AI models in published trading benchmarks (numbers copied from each paper's results table).
    python3 research/open_vs_closed_trading.py -> research/open_vs_closed_trading.png"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["text.parse_math"] = False
OPEN, CLOSED, INK, INK2, GRID, SURF = "#1baf7a", "#6250d6", "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
# (panel title, baseline label, baseline value, {model: (return %, open?)})
P = [
 ("StockBench (Tsinghua): US stocks, Mar-Jun 2025, avg of 3 runs", "buy & hold", 0.4,
  {"Kimi-K2": (1.9, 1), "Qwen3-235B-Ins": (2.4, 1), "GLM-4.5": (2.3, 1), "Qwen3-235B-Think": (2.5, 1),
   "Qwen3-30B-Think": (2.1, 1), "Qwen3-Coder": (0.2, 1), "DeepSeek-V3.1": (1.1, 1), "DeepSeek-V3": (0.2, 1),
   "GPT-OSS-120B": (-0.9, 1), "GPT-OSS-20B": (-2.8, 1), "OpenAI o3": (1.9, 0), "Claude 4 Sonnet": (2.2, 0), "GPT-5": (0.3, 0)}),
 ("AI-Trader (HKU): Nasdaq-100 stocks, Oct-Nov 2025", "QQQ", 1.87,
  {"MiniMax-M2": (9.56, 1), "DeepSeek-V3.1": (8.39, 1), "Claude 3.7 Sonnet": (3.11, 0), "GPT-5": (1.56, 0),
   "Qwen3-Max": (0.39, 0), "Gemini 2.5 Flash": (-0.06, 0)}),
 ("AI-Trader (HKU): crypto, 1-14 Nov 2025", "crypto index", -14.30,
  {"DeepSeek-V3.1": (-12.18, 1), "MiniMax-M2": (-14.80, 1), "Claude 3.7 Sonnet": (-15.30, 0), "GPT-5": (-16.41, 0),
   "Qwen3-Max": (-16.85, 0), "Gemini 2.5 Flash": (-18.63, 0)}),
 ("LiveTradeBench (UIUC): US stocks, live Aug-Oct 2025", None, None,
  {"Qwen2.5-72B": (5.15, 1), "Qwen3-235B-Ins": (3.52, 1), "Qwen3-235B-Think": (1.78, 1), "Llama 3.3 70B": (2.72, 1),
   "Llama 4 Scout": (4.65, 1), "Llama 4 Maverick": (4.46, 1), "Kimi-K2": (3.07, 1), "DeepSeek-V3.1": (2.46, 1),
   "DeepSeek-R1": (2.10, 1), "Claude 3.7 Sonnet": (3.63, 0), "Claude Sonnet 4": (2.45, 0), "Claude Opus 4": (3.93, 0),
   "Claude Opus 4.1": (3.73, 0), "Grok 3": (3.22, 0), "Grok 4": (4.30, 0), "Gemini 2.5 Flash": (2.10, 0),
   "Gemini 2.5 Pro": (1.95, 0), "GPT-4o": (3.55, 0), "GPT-4.1": (6.25, 0), "GPT-5": (5.31, 0), "OpenAI o3": (6.04, 0)}),
 ("PolyBench: prediction markets, Feb 2026, one week", "break even", 0,
  {"MiMo-V2-Flash": (17.6, 1), "DeepSeek-V3.2": (-11.4, 1), "GPT-OSS-120B": (-17.8, 1), "MiniMax-M2.5": (-25.2, 1),
   "Trinity-Large": (-9.2, 1), "Gemini 3 Flash": (6.2, 0), "Grok 4.1 Fast": (-12.1, 0)}),
 ("'Beta, Not Alpha': 56 US stocks, 2 Jan-11 Nov 2026", "SPY", 12.1,
  {"Llama 3.2 3B (tiny)": (-0.6, 1), "GPT-5.6 Luna": (7.8, 0), "Gemini 3.5 Flash": (6.3, 0), "Claude Haiku 4.5": (7.2, 0),
   "Claude Sonnet 4.6": (8.1, 0), "Claude Haiku 5.5": (2.4, 0)}),
]
fig, axes = plt.subplots(len(P), 1, figsize=(12, 3.1 * len(P)), facecolor=SURF)
for ax, (title, bl, bv, d) in zip(axes, P):
    items = sorted(d.items(), key=lambda x: x[1][0])
    ys = range(len(items))
    for y, (name, (v, op)) in zip(ys, items):
        c = OPEN if op else CLOSED
        ax.plot([0, v], [y, y], color=c, lw=2, solid_capstyle="round")
        ax.plot(v, y, "o", ms=8, color=c, mec=SURF, mew=2)
        ax.annotate(f"{name}  {v:+.1f}%", (v, y), xytext=(8 if v >= 0 else -8, 0), textcoords="offset points",
                    ha="left" if v >= 0 else "right", va="center", fontsize=7.5, color=INK2)
    for op, c in ((1, OPEN), (0, CLOSED)):
        vals = [v for v, o in d.values() if o == op]
        if len(vals) > 1:
            m = sum(vals) / len(vals)
            ax.axvline(m, color=c, lw=1, ls=(0, (3, 2)))
    if bl:
        ax.axvline(bv, color=INK, lw=1.5)
        ax.annotate(bl, (bv, len(items) - 0.5), xytext=(3, 0), textcoords="offset points", fontsize=8, color=INK)
    ax.axvline(0, color=GRID, lw=1)
    lo, hi = min(v for v, _ in d.values()), max(v for v, _ in d.values())
    pad = (hi - lo) * 0.45 + 1
    ax.set_xlim(min(lo, bv or 0, 0) - pad, max(hi, bv or 0, 0) + pad)
    ax.set_yticks([])
    ax.set_title(title, loc="left", fontsize=11, color=INK, weight="bold")
    ax.set_facecolor(SURF)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8)
    ax.set_xlabel("Return (%)", color=INK2, fontsize=8)
axes[0].plot([], [], "o", color=OPEN, label="open-weight (anyone can download)")
axes[0].plot([], [], "o", color=CLOSED, label="closed (ChatGPT, Claude, Gemini, Grok, Qwen-Max)")
axes[0].plot([], [], color=INK2, ls=(0, (3, 2)), label="group average")
axes[0].legend(loc="lower right", fontsize=8, frameon=False)
fig.tight_layout()
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "open_vs_closed_trading.png")
fig.savefig(out, dpi=110, facecolor=SURF)
print(out)
