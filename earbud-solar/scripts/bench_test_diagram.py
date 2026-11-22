"""Connection drawing: ANYSOLAR SM400K10TF panel -> TI BQ25188EVM -> battery. Nothing else.
Connector names from TI's BQ25188EVM user guide SLUUD46 (Table 2-1).
Usage: python3 bench_test_diagram.py <out png>
"""
import sys
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

fig, ax = plt.subplots(figsize=(13, 5.6)); ax.set_xlim(0, 13); ax.set_ylim(0, 5.6); ax.axis("off")


def box(x, y, w, h, title, lines, fc):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05", fc=fc, ec="k", lw=1.4))
    ax.text(x + w / 2, y + h - 0.3, title, ha="center", va="top", fontsize=13, weight="bold")
    for i, t in enumerate(lines):
        ax.text(x + w / 2, y + h - 0.95 - 0.42 * i, t, ha="center", va="top", fontsize=11)


box(0.3, 1.0, 3.2, 3.6, "Solar panel", ["SM400K10TF", "+ pad on one end", "- pad on the other end"], "#cfe0ff")
box(4.9, 1.0, 3.2, 3.6, "TI BQ25188EVM", ["J2 = VIN / GND", "J4 = battery plug", "(or J3 = VBAT / GND)"], "#ffe9c4")
box(9.5, 1.0, 3.2, 3.6, "Battery", ["3.7 V LiPo", "JST-PH 2 mm plug"], "#d8f5d0")

ax.plot([3.5, 4.9], [3.4, 3.4], color="#c00000", lw=3); ax.text(4.2, 3.55, "+  ->  J2 VIN", ha="center", fontsize=11, color="#c00000", weight="bold")
ax.plot([3.5, 4.9], [2.0, 2.0], color="k", lw=3);       ax.text(4.2, 2.15, "-  ->  J2 GND", ha="center", fontsize=11, weight="bold")
ax.plot([8.1, 9.5], [3.4, 3.4], color="#c00000", lw=3); ax.text(8.8, 3.55, "J4 +  ->  +", ha="center", fontsize=11, color="#c00000", weight="bold")
ax.plot([8.1, 9.5], [2.0, 2.0], color="k", lw=3);       ax.text(8.8, 2.15, "J4 -  ->  -", ha="center", fontsize=11, weight="bold")
ax.set_title("Where to connect: panel -> TI board -> battery", fontsize=14)
plt.savefig(sys.argv[1], dpi=110, bbox_inches="tight")
print("saved", sys.argv[1])
