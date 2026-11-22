"""Draw the solar-charging wiring diagram (TI BQ25188 linear charger between the cell and the bud battery;
BQ25185 as the resistor-set alternative). Values from the TI datasheets as summarised in README section 10 -
check pin/ball names against the datasheet before ordering a board.
Usage: python3 wiring_diagram.py <out png>
"""
import sys
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

fig, ax = plt.subplots(figsize=(15, 8.5)); ax.set_xlim(0, 15); ax.set_ylim(0, 8.5); ax.axis("off")


def box(x, y, w, h, title, lines, fc):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05", fc=fc, ec="k", lw=1.2))
    ax.text(x + w / 2, y + h - 0.3, title, ha="center", va="top", fontsize=11, weight="bold")
    for i, t in enumerate(lines):
        ax.text(x + 0.15, y + h - 0.75 - 0.36 * i, t, ha="left", va="top", fontsize=8.6)


def wire(pts, col="k", lw=2.0, label=None, at=0):
    xs, ys = zip(*pts); ax.plot(xs, ys, color=col, lw=lw)
    if label:
        ax.text(pts[at][0] + 0.1, pts[at][1] + 0.12, label, fontsize=8.5, color=col)


box(0.3, 4.6, 3.6, 3.3, "Solar cell (the lid)", ["ANYSOLAR SM400K10TF, 33x15x1.5 mm", "10 mono-Si cells, 25 %",
    "85.7 mW at 1 sun", "Vmp 5.58 V  Imp 15.4 mA", "Voc 6.91 V (~7.7 V at -20 C)", "pads: Ø3.0 at each short end",
    "hand-solder <5 s, <400 C; no IPA"], "#cfe0ff")
box(5.6, 2.6, 4.2, 5.3, "Charger board (~3.2 x 4.4 mm)", ["Recommended: TI BQ25188, DSBGA 1.6 x 1.1 mm",
    "  no setup: powers up at 4.20 V / 10 mA", "  input regulation (VINDPM) for weak sources", "  optional: set 15 mA once over I2C",
    "Alt: TI BQ25185, WSON 2.2 x 2.0 mm,", "  VSET 24k -> 4.20 V, ISET sets the current", "IN 3-18 V, 25 V abs max (cell Voc <= 7.7 V)",
    "TS: 10 kOhm NTC taped to the battery", "C_IN >= 1 uF effective (35 V part)", "C_SYS >= 10 uF, C_BAT 1 uF",
    "glued on the cell back BESIDE '+',", "not on top of the board/battery stack"], "#ffe9c4")
box(11.4, 4.6, 3.3, 3.3, "Earbud battery (JBL)", ["Li-ion pouch 3.85 V 70 mAh", "connect on the PACK side:",
    "the battery pads on the PCB", "(after its protection IC)", "solar charger stops at 4.2 V,", "never above JBL's own charger"], "#d8f5d0")
box(11.4, 0.4, 3.3, 3.2, "JBL charging contacts", ["2 pins on the underside", "-> stay wired to JBL's PCB",
    "DO NOT connect solar here:", "voltage there = 'in case'", "-> shade would reboot or", "   disconnect the bud"], "#ffd6d6")
wire([(3.9, 7.0), (5.6, 7.0)], "#c00000", label="cell +  ->  IN", at=0)
wire([(3.9, 5.2), (4.6, 5.2), (4.6, 3.4), (5.6, 3.4)], "k", label="cell -  ->  GND", at=0)
wire([(9.8, 7.0), (11.4, 7.0)], "#c00000", label="BAT -> battery +", at=0)
wire([(9.8, 3.4), (10.6, 3.4), (10.6, 5.2), (11.4, 5.2)], "k", label="GND -> battery -", at=0)
wire([(9.8, 5.6), (10.3, 5.6), (10.3, 6.1), (11.4, 6.1)], "#7a4d00", 1.2, label="TS <- NTC on battery", at=0)
ax.text(0.3, 0.3, "Only two wires leave the cell; the charger sits on the cell's back inside the sealed shell.\n"
        "Expected at 1 sun: BQ25188 default 10 mA ~ 39 mW into the battery (15 mA ~ 58 mW if programmed)\n"
        "vs the bud's ~27 mW average use. Check every pin/ball against the TI datasheet before ordering a board.", fontsize=9.5)
ax.set_title("Solar charging wiring - JBL Endurance Peak 3 solar build", fontsize=13)
plt.savefig(sys.argv[1], dpi=110, bbox_inches="tight")
print("saved", sys.argv[1])
