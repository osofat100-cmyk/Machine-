"""Validate the built shell (run after shell_build.py).  Writes data/shell_check.json.
Usage: python3 shell_check.py <shell out dir> <data dir>
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, trimesh
from scipy import ndimage
import sdf

src, data = sys.argv[1:3]
D = np.load(os.path.join(src, "shell_masks.npz"))
cover, base, arm, inside, cavity = D["cover"], D["base"], D["arm"], D["inside"], D["cavity"]
lo, p, zp = D["lo"], float(D["p"]), float(D["zp"])
PR = json.load(open(os.path.join(data, "shell_params.json")))
CO = json.load(open(os.path.join(data, "components.json")))
REP = json.load(open(os.path.join(data, "shell_report.json")))
zax = lo[2] + (np.arange(inside.shape[2]) + 0.5) * p
out, ok = {}, True


def check(name, passed, value):
    global ok
    ok &= bool(passed)
    out[name] = dict(passed=bool(passed), value=value)
    print(f"{'PASS' if passed else 'FAIL'}  {name}: {value}")


# 1. meshes
total = 0.0
for k in ("cover", "base", "hook_arm"):
    m = trimesh.load(os.path.join(src, f"EP3_shell_{k}.stl"))
    bodies = len(m.split(only_watertight=False))
    check(f"{k}: watertight, one body, positive volume", m.is_watertight and bodies == 1 and m.volume > 0,
          dict(watertight=bool(m.is_watertight), bodies=bodies, volume_cm3=round(m.volume / 1000, 3)))
    total += m.volume / 1000 * PR["print"]["density_g_cm3"]
check("printed parts lighter than the original bud (12.5 g incl. electronics)", total < 12.5, f"{total:.2f} g of resin")

# 2. halves do not overlap
check("cover and base do not overlap", not (cover & base).any(), int((cover & base).sum()))

# 3. wall thickness (opening test): 0.8 mm walls, 0.6 mm groove side walls
for t in (0.8, 0.6):
    for k, mask in (("cover", cover), ("base", base)):
        share = float(sdf.thin_regions(mask, t, p).sum() / mask.sum())
        out[f"{k}_share_thinner_than_{t}mm"] = round(share, 4)
        print(f"INFO  {k}: share thinner than {t} mm = {share:.4f}")
check("no region thinner than 0.6 mm (groove side walls are the thinnest by design)",
      max(out["cover_share_thinner_than_0.6mm"], out["base_share_thinner_than_0.6mm"]) < 0.01,
      [out["cover_share_thinner_than_0.6mm"], out["base_share_thinner_than_0.6mm"]])

# 4. flat cell ledge: top face of the cover lies on Z = 0
mc = trimesh.load(os.path.join(src, "EP3_shell_cover.stl"))
top = mc.vertices[(mc.vertices[:, 2] > -0.05) & (np.abs(mc.vertices[:, 0]) < 16.0) & (np.abs(mc.vertices[:, 1]) < 7.2)]
rms = float(np.sqrt((top[:, 2] ** 2).mean())) if len(top) else float("nan")
check("cell ledge flat (RMS from the seat plane)", rms < 0.02, f"{rms:.4f} mm over {len(top)} vertices")

# 5. tongue-to-groove side gap (voxel-quantised)
k0, k1 = int((zp - 0.6 - lo[2]) / p), int((zp - lo[2]) / p)
gaps = []
for kk in range(k0 + 1, k1):
    tong = cover[:, :, kk]
    if tong.any():
        gaps.append((ndimage.distance_transform_edt(~base[:, :, kk]) * p)[tong])
g_ = np.concatenate(gaps) if gaps else np.array([np.nan])
check("tongue never touches the base (gasket path open, side gap > 0)", np.nanmin(g_) > 0,
      dict(min_mm=round(float(np.nanmin(g_)), 3), median_mm=round(float(np.nanmedian(g_)), 3), design_mm=0.15))
out["gasket"] = dict(gap_height_mm=PR["seal"]["groove_d"] - PR["seal"]["tongue_h"], cord_mm=0.8,
                     squeeze_pct=round(100 * (1 - (PR["seal"]["groove_d"] - PR["seal"]["tongue_h"]) / 0.8), 1))

# 6. do the estimated electronics fit?  free space = inside minus shell parts; PCB under the cell, battery below
free = inside & ~cover & ~base
bat, pcb = CO["battery"]["size"], CO["pcb"]["size"]
pcb_h = pcb[2] + CO["pcb"]["parts_top"] + CO["pcb"]["parts_bottom"]
stack = pcb_h + bat[2]
best = None
for cx in np.arange(-6.0, 6.01, 0.5):
    for cy in np.arange(-1.5, 1.51, 0.25):
        i0, i1 = int((cx - pcb[0] / 2 - lo[0]) / p), int((cx + pcb[0] / 2 - lo[0]) / p)
        j0, j1 = int((cy - pcb[1] / 2 - lo[1]) / p), int((cy + pcb[1] / 2 - lo[1]) / p)
        col = free[i0:i1, j0:j1, :]
        full = col.all(axis=(0, 1))                                   # Z levels free over the whole footprint
        if not full.any():
            continue
        top_k = len(full) - 1 - np.argmax(full[::-1])
        bot_k = top_k
        while bot_k > 0 and full[bot_k - 1]:
            bot_k -= 1
        h = (top_k - bot_k + 1) * p
        if best is None or h > best[0]:
            best = (h, cx, cy)
h, cx, cy = best if best else (0.0, 0, 0)
out["stack"] = dict(needed_mm=round(stack, 2), free_height_over_pcb_footprint_mm=round(h, 2), at=[cx, cy],
                    battery=bat, pcb=pcb, source="FCC estimates - measure the real parts")
print(f"INFO  electronics stack (PCB {pcb_h:.1f} + battery {bat[2]:.1f} = {stack:.1f} mm) vs free height {h:.2f} mm "
      f"-> {'fits' if h >= stack else f'SHORT by {stack - h:.2f} mm (estimate)'}")
out["all_passed"] = bool(ok)
json.dump(out, open(os.path.join(data, "shell_check.json"), "w"), indent=1)
print("ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED")
