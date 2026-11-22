"""Bench-test wiring: ANYSOLAR SM400K10TF -> TI BQ25188EVM -> small LiPo, with a meter in series.
Connector names from TI's BQ25188EVM user guide SLUUD46 (Table 2-1, Table 2-2); BQ25188 power-on defaults
(4.20 V, 10 mA) from datasheet SLUSFJ3 register resets. Usage: python3 bench_test_diagram.py <out png>
"""
import sys
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

fig, ax = plt.subplots(figsize=(15, 8.8)); ax.set_xlim(0, 15); ax.set_ylim(0, 8.8); ax.axis("off")


def box(x, y, w, h, title, lines, fc, fs=8.8):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05", fc=fc, ec="k", lw=1.2))
    ax.text(x + w / 2, y + h - 0.28, title, ha="center", va="top", fontsize=11, weight="bold")
    for i, t in enumerate(lines):
        ax.text(x + 0.15, y + h - 0.72 - 0.34 * i, t, ha="left", va="top", fontsize=fs)


def wire(pts, col, label=None, lw=2.2, at=0, dy=0.12):
    xs, ys = zip(*pts); ax.plot(xs, ys, color=col, lw=lw)
    if label:
        ax.text(pts[at][0] + 0.1, pts[at][1] + dy, label, fontsize=9, color=col, weight="bold")


box(0.3, 4.3, 3.6, 3.9, "Solar panel SM400K10TF", ["33 x 15 mm, 85.7 mW at full sun", "back: one round pad at each",
    "short end (+ and -)", "find + in the sun with the meter:", "  open circuit ~6.9 V", "solder thin wires: < 5 s, < 400 C",
    "do not clean it with alcohol"], "#cfe0ff")
box(5.4, 2.6, 4.4, 5.6, "TI BQ25188EVM", ["J2  VIN / GND   <- panel", "J4  battery JST-PH 2 mm  -> LiPo",
    "J3  VBAT / GND  (same, bare wires)", "", "Jumpers: leave as shipped", "  (J5 on, J10 on)", "J7 OFF (its LED wastes 10 mA)",
    "No USB, no USB2ANY needed:", "  charges at 4.20 V / 10 mA by itself", "Stops after 6 h non-stop charging;",
    "  shading the panel resets it"], "#ffe9c4")
box(11.3, 4.6, 3.4, 3.6, "Small LiPo", ["3.7 V, 50-150 mAh", "JST-PH 2 mm plug", "CHECK + / - against the", "markings at J4 before",
    "plugging in (plugs come", "wired both ways)"], "#d8f5d0")
box(11.3, 1.0, 3.4, 3.0, "Multimeter", ["mA range, in series in the", "battery + wire (red path)", "expected in full sun:",
    "  about 10 mA into the LiPo", "  (~39 mW; bud uses ~27 mW)"], "#eeeeee")
wire([(3.9, 7.3), (5.4, 7.3)], "#c00000", "panel +  ->  J2 VIN")
wire([(3.9, 5.0), (4.6, 5.0), (4.6, 3.2), (5.4, 3.2)], "k", "panel -  ->  J2 GND")
wire([(9.8, 7.3), (10.5, 7.3), (10.5, 3.6), (11.3, 3.6)], "#c00000", "J4 / J3 +  ->  meter (mA)", dy=0.15)
wire([(13.0, 4.0), (13.0, 4.6)], "#c00000", "meter -> LiPo +", at=0, dy=0.05)
wire([(9.8, 3.2), (10.2, 3.2), (10.2, 5.0), (11.3, 5.0)], "k", "J4 / J3 -  ->  LiPo -", dy=-0.3)
ax.text(0.3, 1.6, "Later, on the opened earbud: J3 VBAT / GND go to the bud's own battery pads on its circuit board\n"
        "(battery still connected). Only the panel may power the board then - never USB or a bench supply -\n"
        "and never connect anything to the earbud's two case charging pins.", fontsize=9.5)
ax.set_title("Bench test: does the panel charge a battery faster than the earbud uses it?", fontsize=13)
plt.savefig(sys.argv[1], dpi=110, bbox_inches="tight")
print("saved", sys.argv[1])
