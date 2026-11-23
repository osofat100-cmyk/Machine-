"""Largest flat rectangle on the earbud's outward face (the JBL-lettered panel, away from the ear).

1. View the earbud from outside along the face direction n0 (found by searching 4000 directions
   for the most outer-skin area facing one way, on the side away from the ear tip).
2. Height map of the top-most surface (z-buffer of dense surface samples, 0.05 mm pixels).
3. The "JBL" letters (part Earphone_Plastic_2 inside the panel) are replaced by flat filler
   at the panel's height (user request).
4. Robust plane fit to the panel; "flat at tolerance t" = surface inside a slab of thickness t.
5. Largest rectangle in the flat region over in-plane rotations (maximal-rectangle algorithm).
Usage: python3 flat_face.py <earbud measured glb> <out dir>
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, trimesh
from scipy import ndimage
from exterior import sample_triangles

glb, outdir = sys.argv[1], sys.argv[2]
s = trimesh.load(glb, force="scene"); P = {}
for node in s.graph.nodes_geometry:
    T, g = s.graph[node]; m = s.geometry[g].copy(); m.apply_transform(T); P[node] = m
n = np.array([-0.031, -0.051, 0.998]); n /= np.linalg.norm(n)
u = np.cross(n, [1, 0, 0]); u /= np.linalg.norm(u); v = np.cross(n, u)
res = 0.05
pts, labs = [], []
for k, m in P.items():
    p, _, _ = sample_triangles(m.triangles, 0.025); pts.append(p); labs += [k] * len(p)
p = np.vstack(pts); labs = np.array(labs)
x, y, h = p @ u, p @ v, p @ n
x0, y0 = x.min(), y.min()
gx = ((x - x0) / res).astype(int); gy = ((y - y0) / res).astype(int)
key = gx * (gy.max() + 1) + gy
o = np.lexsort((-h, key)); first = o[np.r_[True, key[o][1:] != key[o][:-1]]]
H = np.full((gx.max() + 1, gy.max() + 1), np.nan); H[gx[first], gy[first]] = h[first]
PART = np.full(H.shape, "", dtype=object); PART[gx[first], gy[first]] = labs[first]

# panel = top region; robust plane fit h = a*X + b*Y + c on it
top = np.nanmax(H)
cand = np.isfinite(H) & (H > top - 1.5)
lab, nl = ndimage.label(cand); panel = lab == (np.argmax(ndimage.sum(cand, lab, range(1, nl + 1))) + 1)
I, J = np.nonzero(panel)
letters = panel & (PART == "Earphone_Plastic_2")
use = panel & ~letters
for _ in range(4):
    ii, jj = np.nonzero(use)
    A = np.c_[ii * res, jj * res, np.ones(len(ii))]
    coef = np.linalg.lstsq(A, H[ii, jj], rcond=None)[0]
    plane = coef[0] * np.arange(H.shape[0])[:, None] * res + coef[1] * np.arange(H.shape[1])[None, :] * res + coef[2]
    use = panel & ~letters & (np.abs(H - plane) < 0.3)
D = H - plane                    # deviation from the fitted plane (mm)
letter_dev = D[letters]
D[letters] = 0.0                 # JBL letters -> flat filler
tilt = np.degrees(np.arctan(np.hypot(coef[0], coef[1])))


def max_rect(mask):
    best = (0, None)
    hgt = np.zeros(mask.shape[1], int)
    for i in range(mask.shape[0]):
        hgt = np.where(mask[i], hgt + 1, 0)
        st = []
        for j in range(len(hgt) + 1):
            hj = hgt[j] if j < len(hgt) else 0
            start = j
            while st and st[-1][1] >= hj:
                k, hk = st.pop()
                if hk * (j - k) > best[0]:
                    best = (hk * (j - k), (i - hk + 1, k, hk, j - k))
                start = k
            st.append((start, hj))
    return best


def best_rect(mask, coarse=3.0):
    best = (0, None, 0.0)
    for ang in list(np.arange(0, 180, coarse)):
        a, r = max_rect(ndimage.rotate(mask.astype(np.uint8), ang, order=0, reshape=True).astype(bool))
        if a > best[0]: best = (a, r, ang)
    for ang in np.arange(best[2] - coarse, best[2] + coarse + 0.01, 0.5):
        a, r = max_rect(ndimage.rotate(mask.astype(np.uint8), ang, order=0, reshape=True).astype(bool))
        if a > best[0]: best = (a, r, ang)
    return best


results = {}
for t in (0.05, 0.10, 0.20, 0.30, 0.50, 1.00):
    flat = np.isfinite(D) & (np.abs(D) <= t / 2) & ndimage.binary_dilation(panel, iterations=40)
    lab, nl = ndimage.label(flat)
    if nl == 0: continue
    keep = lab == (np.argmax(ndimage.sum(flat, lab, range(1, nl + 1))) + 1)
    a, (i0, j0, hh, ww), ang = best_rect(keep)
    dims = sorted([hh * res, ww * res], reverse=True)
    results[t] = dict(flat_region_cm2=round(float(keep.sum() * res * res / 100), 3), rect_mm=[round(d, 2) for d in dims],
                      rect_cm2=round(dims[0] * dims[1] / 100, 3), angle_deg=float(ang), rect_rot=[int(i0), int(j0), int(hh), int(ww)])
    print(f"slab {t:.2f} mm: flat region {keep.sum()*res*res/100:5.2f} cm2 | largest rectangle {dims[0]:5.2f} x {dims[1]:5.2f} mm = {dims[0]*dims[1]/100:5.3f} cm2 (rotation {ang:.1f} deg)")
summary = dict(view_normal=n.round(4).tolist(), panel_area_cm2=round(float(panel.sum() * res * res / 100), 3),
               panel_tilt_vs_view_deg=round(float(tilt), 2), letters_area_cm2=round(float(letters.sum() * res * res / 100), 3),
               letters_depth_mm_p5_p95=np.percentile(letter_dev, [5, 95]).round(3).tolist(),
               panel_deviation_mm_p5_p95=np.percentile(D[panel], [5, 95]).round(3).tolist(), rectangles=results)
print(json.dumps({k: v for k, v in summary.items() if k != "rectangles"}))
json.dump(summary, open(os.path.join(outdir, "flat_face.json"), "w"), indent=1)
np.savez_compressed(os.path.join(outdir, "flat_face_maps.npz"), H=H, D=D, panel=panel, letters=letters, res=res)

# ---- curvature of the panel: quadric fit D = a i^2 + b ij + c j^2 + d i + e j + f (mm) ----
ii, jj = np.nonzero(panel & ~letters)
X, Y = ii * res, jj * res
Q = np.c_[X * X, X * Y, Y * Y, X, Y, np.ones(len(X))]
qa, qb, qc, qd, qe, qf = np.linalg.lstsq(Q, D[ii, jj], rcond=None)[0]
Hs = np.array([[2 * qa, qb], [qb, 2 * qc]])
kv, kvec = np.linalg.eigh(Hs)                     # principal curvatures of the panel (1/mm)
resid = D[ii, jj] - Q @ np.array([qa, qb, qc, qd, qe, qf])
radii = [round(float(1 / abs(k)), 1) if abs(k) > 1e-6 else float("inf") for k in kv]
print(f"panel shape fit: principal radii {radii} mm (signs {np.sign(kv).tolist()}), fit residual RMS {np.sqrt((resid**2).mean()):.3f} mm")
summary["panel_principal_radii_mm"] = radii
summary["panel_quadric_rms_mm"] = round(float(np.sqrt((resid ** 2).mean())), 3)

# ---- largest rectangle inside the whole panel outline (for a cell that bends to follow it) ----
a_, r_, ang_ = best_rect(ndimage.binary_fill_holes(panel))
dims = sorted([r_[2] * res, r_[3] * res], reverse=True)
summary["panel_rectangle_mm"] = [round(d, 2) for d in dims]
print(f"largest rectangle inside the whole panel outline: {dims[0]:.2f} x {dims[1]:.2f} mm = {dims[0]*dims[1]/100:.3f} cm2")
json.dump(summary, open(os.path.join(outdir, "flat_face.json"), "w"), indent=1)
