"""Connection drawing: ANYSOLAR SM400K10TF panel -> TI BQ25188EVM -> battery. Nothing else.
Sources: panel pads from the ANYSOLAR SM400K10TF datasheet (back-side view: Ø3.0 pads 3.0 mm from each short end,
'-' left / '+' right with the printed text upright); EVM pins from TI SLUUD46 Figure 3-2 (J2: pin 2 VIN, pin 1 GND;
J4: pin 1 VBAT, pin 2 GND; J5 factory-connected); earbud battery from JBL's FCC internal photos (two wires,
red to the (+) tab, black to the (-) tab).
Usage: python3 bench_test_diagram.py <out png>
"""
import sys
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, Rectangle

fig, ax = plt.subplots(figsize=(14, 6.4)); ax.set_xlim(0, 14); ax.set_ylim(0, 6.4); ax.axis("off")


def box(x, y, w, h, title, lines, fc):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05", fc=fc, ec="k", lw=1.4))
    ax.text(x + w / 2, y + h - 0.3, title, ha="center", va="top", fontsize=13, weight="bold")
    for i, t in enumerate(lines):
        ax.text(x + w / 2, y + h - 0.95 - 0.4 * i, t, ha="center", va="top", fontsize=10.5)


# panel, drawn as its back side
box(0.3, 0.9, 3.9, 4.6, "Solar panel (back side)", ["SM400K10TF"], "#cfe0ff")
ax.add_patch(Rectangle((0.6, 2.95), 3.3, 1.2, fc="white", ec="k"))
ax.text(2.25, 3.55, "IXOLAR\nSM400K10TF", ha="center", va="center", fontsize=7)
ax.add_patch(Circle((0.95, 3.55), 0.17, fc="gold", ec="k")); ax.text(1.3, 3.45, "-", ha="center", fontsize=14, weight="bold")
ax.add_patch(Circle((3.55, 3.55), 0.17, fc="gold", ec="k")); ax.text(3.2, 3.45, "+", ha="center", fontsize=14, weight="bold", color="#c00000")
ax.text(2.25, 1.55, "printed text upright:\n- pad LEFT, + pad RIGHT", ha="center", va="center", fontsize=10.5)

box(5.3, 0.9, 3.4, 4.6, "TI BQ25188EVM", ["J2 pin 2 = VIN", "J2 pin 1 = GND", "", "J4 pin 1 = + (VBAT)", "J4 pin 2 = - (GND)", "",
    "leave jumper J5 on", "(as it comes from TI)"], "#ffe9c4")
box(9.8, 0.9, 3.9, 4.6, "Battery", ["2 wires only:", "red  = +", "black = -", "", "(JBL earbud battery:", "red to the (+) tab,", "black to the (-) tab)"], "#d8f5d0")

ax.plot([3.55, 3.55, 5.3], [3.72, 4.55, 4.55], color="#c00000", lw=3)
ax.text(4.3, 4.7, "+ pad -> J2 pin 2 (VIN)", ha="center", fontsize=10, color="#c00000", weight="bold")
ax.plot([0.95, 0.95, 4.75, 4.75, 5.3], [3.38, 2.45, 2.45, 4.0, 4.0], color="k", lw=3)
ax.text(2.75, 2.12, "- pad -> J2 pin 1 (GND)", ha="center", fontsize=10, weight="bold")
ax.plot([8.7, 9.8], [3.8, 3.8], color="#c00000", lw=3); ax.text(9.25, 3.95, "J4 pin 1 -> red", ha="center", fontsize=10, color="#c00000", weight="bold")
ax.plot([8.7, 9.8], [2.6, 2.6], color="k", lw=3);       ax.text(9.25, 2.75, "J4 pin 2 -> black", ha="center", fontsize=10, weight="bold")
ax.set_title("Where to connect: panel -> TI board -> battery", fontsize=14)
plt.savefig(sys.argv[1], dpi=110, bbox_inches="tight")
print("saved", sys.argv[1])
