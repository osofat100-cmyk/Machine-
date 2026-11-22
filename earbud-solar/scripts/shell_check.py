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
# The opening shares above also count the slivers shaved off every sharp convex edge (lid-cut rim, seam faces),
# so the pass/fail test uses sdf.thin_walls: removed material with no surviving thick material nearby.
spots = []
for k, m_ in (("cover", cover), ("base", base)):
    tw = sdf.thin_walls(m_, 0.6, p)
    out[f"{k}_thin_wall_share_0.6mm"] = round(float(tw.sum() / m_.sum()), 5)
    lab, n = ndimage.label(tw, structure=np.ones((3, 3, 3)))
    for j in range(1, n + 1):
        c = np.argwhere(lab == j)
        if len(c) >= 10:
            spots.append(dict(part=k, voxels=int(len(c)), mm3=round(len(c) * p ** 3, 3),
                              at=[round(float(v), 2) for v in lo + (c.mean(0) + 0.5) * p]))
    print(f"INFO  {k}: genuinely thin (<0.6 mm) share = {tw.sum() / m_.sum():.5f}")
out["thin_spots"] = sorted(spots, key=lambda d: -d["voxels"])[:12]
for d in out["thin_spots"]:
    print("      thin spot", d)
check("no thin walls below 0.6 mm (sharp-edge slivers excluded)",
      max(out["cover_thin_wall_share_0.6mm"], out["base_thin_wall_share_0.6mm"]) < 0.002,
      [out["cover_thin_wall_share_0.6mm"], out["base_thin_wall_share_0.6mm"]])

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

# 5b. side ports: every ray between the hole and the seat edge must run through solid material from the skin to the
#     seat depth (no gap that lets water around the membrane / light-pipe seal)
FE = PR["features"]; W = PR["walls"]
def lab_(q):
    i = tuple(((np.asarray(q) - lo) / p).astype(int))
    return 1 if (cover[i] or base[i]) else (2 if inside[i] else 0)
port_res = {}
for name, pr_ in REP.get("ports", {}).items():
    sk, d = np.array(pr_["skin_point"]), np.array(pr_["dir"])
    need = pr_.get("seat_depth_mm", pr_.get("seal_depth_mm"))
    r_in = (FE["mic"]["hole_d"] if name.startswith("mic") else FE["led"]["hole_d"]) / 2 + 0.15
    r_out = (FE["mic"]["recess_d"] / 2 if name.startswith("mic") else FE["led"]["sleeve_od"] / 2) - 0.15
    u = np.cross(d, [0, 0, 1.0]); u /= np.linalg.norm(u); v = np.cross(d, u)
    worst = np.inf
    for rr in np.linspace(r_in, r_out, 3):
        for ang in np.linspace(0, 2 * np.pi, 16, endpoint=False):
            q0 = sk + rr * (np.cos(ang) * u + np.sin(ang) * v)
            ts = np.arange(0.5, -(need + 1.0), -p / 2)
            labs = [lab_(q0 + t_ * d) for t_ in ts]
            # solid run = from the last outside sample to the first empty inside sample (a ray that grazes the
            # curved skin can touch one surface voxel, step outside again, then enter the wall)
            k2 = next((j for j, l_ in enumerate(labs) if l_ == 2), len(labs))
            outs = [j for j in range(k2) if labs[j] == 0]
            k1 = (outs[-1] + 1) if outs else 0
            worst = min(worst, (k2 - k1) * p / 2)
    port_res[name] = dict(min_solid_from_skin_mm=round(float(worst), 2), needed_mm=round(need - 0.15, 2))
check("side ports backed by solid material from the skin to the seat (no bypass gap)",
      all(r_["min_solid_from_skin_mm"] >= r_["needed_mm"] for r_ in port_res.values()), port_res)

# 6. do the estimated electronics fit?  free space = inside minus shell parts; PCB under the cell, battery below
free = inside & ~cover & ~base
cb, cc = PR["features"].get("charger", {}).get("board"), REP.get("charger_centre")
if cb and cc:                                                         # the charger board on the cell back is an obstacle too
    sl_ = tuple(slice(max(0, int((cc[a] - cb[a] / 2 - lo[a]) / p)), int((cc[a] + cb[a] / 2 - lo[a]) / p) + 1) for a in range(3))
    free[sl_] = False
bat, pcb = CO["battery"]["size"], CO["pcb"]["size"]
pcb_h = pcb[2] + CO["pcb"]["parts_top"] + CO["pcb"]["parts_bottom"]
stack = pcb_h + bat[2]
yc0 = REP.get("paddle_outline", {}).get("centre_y", 0.0)


def foot(cx, cy, L, Wd):
    i0, i1 = int((cx - L / 2 - lo[0]) / p), int((cx + L / 2 - lo[0]) / p)
    j0, j1 = int((cy - Wd / 2 - lo[1]) / p), int((cy + Wd / 2 - lo[1]) / p)
    return slice(max(i0, 0), i1), slice(max(j0, 0), j1)


def lowest_fit(fs, h, zmin_k=0):
    """lowest k such that a box of height h over footprint fs is free; None if none."""
    col = free[fs[0], fs[1], :].all(axis=(0, 1)); nh = int(np.ceil(h / p))
    run = 0
    for k in range(len(col)):
        run = run + 1 if col[k] else 0
        if run >= nh and k - nh + 1 >= zmin_k:
            return k - nh + 1
    return None


# two boxes (battery + PCB with its parts), each free to slide along X/Y, either one at the bottom. The best layout's
# margin = how much thicker the battery could be (or how much is missing, if negative).
best = None
for order in ("battery_bottom", "pcb_bottom"):
    (L1, W1, h1), (L2, W2, h2) = ((bat[0], bat[1], bat[2]), (pcb[0], pcb[1], pcb_h)) if order == "battery_bottom" \
        else ((pcb[0], pcb[1], pcb_h), (bat[0], bat[1], bat[2]))
    for x1 in np.arange(-8.0, 8.01, 0.5):
        for y1 in (yc0 - 1.0, yc0, yc0 + 1.0):
            f1 = foot(x1, y1, L1, W1)
            for x2 in np.arange(-8.0, 8.01, 0.5):
                for y2 in (yc0 - 1.0, yc0, yc0 + 1.0):
                    f2 = foot(x2, y2, L2, W2)
                    # margin search: shrink/grow the battery by d until the pair stops fitting
                    for d in np.arange(2.0, -3.01, -0.12):
                        hh1 = h1 + (d if order == "battery_bottom" else 0); hh2 = h2 + (d if order == "pcb_bottom" else 0)
                        if hh1 <= 0 or hh2 <= 0: continue
                        k1 = lowest_fit(f1, hh1)
                        if k1 is None: continue
                        top1 = k1 + int(np.ceil(hh1 / p))
                        ov = not (abs(x1 - x2) >= (L1 + L2) / 2 or abs(y1 - y2) >= (W1 + W2) / 2)
                        k2 = lowest_fit(f2, hh2, top1 if ov else 0)
                        if k2 is None: continue
                        if best is None or d > best[0]:
                            best = (round(float(d), 2), order, [x1, y1], [x2, y2])
                        break
mg = best[0] if best else None
out["stack"] = dict(needed_mm=round(stack, 2), battery=bat, pcb=pcb, pcb_with_parts_h=pcb_h,
                    best_layout=dict(order=best[1], bottom_box_centre=best[2], top_box_centre=best[3]) if best else None,
                    battery_thickness_margin_mm=mg, source="FCC estimates - measure the real parts")
print(f"INFO  electronics (battery {bat[2]:.1f} + PCB with parts {pcb_h:.1f} = {stack:.1f} mm), two boxes placed freely: "
      + (f"{'fits' if mg >= 0 else 'SHORT'}: battery could be {mg:+.2f} mm thicker/thinner and still fit ({best[1]})"
         if best else "no layout found"))
out["all_passed"] = bool(ok)
json.dump(out, open(os.path.join(data, "shell_check.json"), "w"), indent=1)
print("ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED")
