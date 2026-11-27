#!/usr/bin/env python3
"""Full 1-300 graph of all_stories.csv: end value per story size, the averages, and each size's pick.

    python3 spikes/all_stories_full_graph.py   -> spikes/all_stories_full_graph.png
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
r = pd.read_csv(os.path.join(HERE, "all_stories.csv"))
f, a = r[r.version == "fixed"].reset_index(drop=True), r[r.version == "adaptive"].reset_index(drop=True)
buy = f["first_pick"].str.split("/").str[0].str.rstrip("%").astype(int)
sell = f["first_pick"].str.split("/").str[1].str.rstrip("%").astype(int)
hold = 740.78
avg_all, avg_98 = f["end_$"].mean(), f[f.story_size <= 98]["end_$"].mean()

fig, (a1, a2) = plt.subplots(2, 1, figsize=(18, 11), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
a1.axvspan(98.5, 300.5, color="khaki", alpha=0.35, label="sizes 99-300: one block covers buy 1-99%, so buy is always its middle, 50%")
a1.plot(f.story_size, f["end_$"], lw=1.8, label="fixed pick (from everything before 22 Oct)")
a1.plot(a.story_size, a["end_$"], lw=1.2, alpha=0.8, label="re-picked every day")
a1.axhline(avg_all, color="purple", ls="-.", label=f"average of all 300 fixed = \\${avg_all:,.2f}")
a1.axhline(avg_98, color="green", ls="-.", label=f"average of sizes 1-98 fixed = \\${avg_98:,.2f}")
a1.axhline(1000, color="black", ls="--", lw=0.8, label="\\$1,000 start")
a1.axhline(hold, color="grey", ls=":", lw=2, label=f"just holding PEARL (\\${hold:,.2f})")
a1.axvline(85, color="red", lw=1, label="size 85, locked before the test")
a1.set_ylabel("\\$ on 20 Nov (start \\$1,000 on 22 Oct)")
a1.set_title("Every story size 1-300 on the last month (22 Oct - 20 Nov), one minute at a time")
a1.legend(fontsize=9, loc="lower right")
a1.grid(alpha=0.3)
a2.axvspan(98.5, 300.5, color="khaki", alpha=0.35)
a2.plot(f.story_size, buy, color="tab:blue", label="buy after this % fall")
a2.plot(f.story_size, sell / 3, color="tab:red", label="sell after this % rise (divided by 3 to fit)")
a2.set_xlabel("story size k (k x k buy/sell pairs merged into one block; 1 = full detail)")
a2.set_ylabel("the fixed pick")
a2.legend(fontsize=9)
a2.grid(alpha=0.3)
a2.set_xlim(0, 301)
fig.tight_layout()
fig.savefig(os.path.join(HERE, "all_stories_full_graph.png"), dpi=110)
print(f"averages: all 300 = {avg_all:,.2f}, sizes 1-98 = {avg_98:,.2f}")
print("sizes 99-300 picks:", sorted(f[f.story_size >= 99]["first_pick"].unique())[:5], "... all buy 50%:",
      (buy[f.story_size >= 99] == 50).all(), "| their end $:", f[f.story_size >= 99]["end_$"].unique())
