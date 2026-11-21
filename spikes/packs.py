#!/usr/bin/env python3
"""
Packs: runs of neighbouring story sizes whose results stay within a $50 band (highest - lowest <= $50).
For each pack: sizes, how many, average $, lowest/highest, and how many DIFFERENT buy/sell picks are inside
(a pack where every size has the same pick is one robot repeated).

  practice months (stories.csv, gain over 22 Jul - 21 Oct, each month picked before it): a fair way to choose
  last month (all_stories.csv, fixed pick): what each pack did on 22 Oct - 20 Nov

    python3 spikes/packs.py   -> spikes/packs.txt, spikes/packs_graph.png
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BAND = 50.0


def packs(sizes, values, picks):
    out, start = [], 0
    for i in range(1, len(values) + 1):
        if i == len(values) or max(values[start:i + 1]) - min(values[start:i + 1]) > BAND:
            out.append({"sizes": f"{sizes[start]}-{sizes[i - 1]}", "first": sizes[start], "last": sizes[i - 1],
                        "count": i - start, "average_$": round(sum(values[start:i]) / (i - start), 2),
                        "lowest_$": min(values[start:i]), "highest_$": max(values[start:i]),
                        "different_picks": len(set(picks[start:i]))})
            start = i
    return pd.DataFrame(out)


def main():
    st = pd.read_csv(os.path.join(HERE, "stories.csv"))
    al = pd.read_csv(os.path.join(HERE, "all_stories.csv"))
    fx = al[al.version == "fixed"].reset_index(drop=True)
    final = (st["final_buy_%"].astype(int).astype(str) + "%/" + st["final_sell_%"].astype(int).astype(str) + "%").tolist()
    lines = []

    pr = packs(st.story_size.tolist(), st["gain_$"].round(2).tolist(), final)
    lm = packs(fx.story_size.tolist(), fx["end_$"].tolist(), fx.first_pick.tolist())
    for p in (pr, lm):
        p["last_month_avg_$"] = [round(fx[(fx.story_size >= a) & (fx.story_size <= b)]["end_$"].mean(), 2)
                                 for a, b in zip(p["first"], p["last"])]
    lines.append(f"PACKS ON THE PRACTICE MONTHS (chosen without seeing the last month); band ${BAND:.0f}")
    lines.append(pr.sort_values("average_$", ascending=False).drop(columns=["first", "last"]).to_string(index=False))
    lines.append(f"\nPACKS ON THE LAST MONTH (picking from these = choosing after seeing the answer); band ${BAND:.0f}")
    lines.append(lm.sort_values("average_$", ascending=False).drop(columns=["first", "last"]).to_string(index=False))
    txt = "\n".join(lines)
    print(txt)
    with open(os.path.join(HERE, "packs.txt"), "w") as f:
        f.write(txt + "\n")

    fig, axes = plt.subplots(2, 1, figsize=(18, 11), sharex=True)
    for ax, (title, x, y, p) in zip(axes, (
            ("Practice months 22 Jul - 21 Oct (each month picked before it): \\$ after all three",
             st.story_size, st["gain_$"], pr),
            ("Last month 22 Oct - 20 Nov, fixed pick", fx.story_size, fx["end_$"], lm))):
        ax.plot(x, y, color="black", lw=1.2)
        for _, row in p.iterrows():
            if row["count"] >= 3:
                ax.hlines(row["average_$"], row["first"] - 0.5, row["last"] + 0.5, lw=6, alpha=0.45,
                          color="tab:green" if row["different_picks"] > 1 else "tab:orange")
                ax.annotate(f"{row['count']} sizes\n\\${row['average_$']:,.0f}\n{row['different_picks']} picks",
                            ((row["first"] + row["last"]) / 2, row["average_$"]), fontsize=7, ha="center",
                            va="bottom")
        ax.axhline(1000, color="grey", ls="--", lw=0.8)
        ax.set_title(title + "   (bars = packs of 3+ sizes within \\$50; green = different picks, orange = one pick repeated)")
        ax.set_ylabel("\\$")
        ax.grid(alpha=0.3)
    axes[1].set_xlabel("story size")
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "packs_graph.png"), dpi=110)
    print("saved spikes/packs_graph.png")


if __name__ == "__main__":
    main()
