"""Draw the flat rectangles on the outward face and export a GLB with solar plates placed on it.
Run after flat_face.py.  Usage: python3 render_flat_face.py <earbud glb> <data dir> <out dir>
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, trimesh
from scipy import ndimage
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

glb, data, out = sys.argv[1:4]
F = json.load(open(os.path.join(data, "flat_face.json")))
M = np.load(os.path.join(data, "flat_face_maps.npz"))
H, D, panel, letters, res = M["H"], M["D"], M["panel"], M["letters"], float(M["res"])
n = np.array(F["view_normal"]); n /= np.linalg.norm(n)
u = np.cross(n, [1, 0, 0]); u /= np.linalg.norm(u); v = np.cross(n, u)


def max_rect(mask):
    best = (0, None); hgt = np.zeros(mask.shape[1], int)
    for i in range(mask.shape[0]):
        hgt = np.where(mask[i], hgt + 1, 0); st = []
        for j in range(len(hgt) + 1):
            hj = hgt[j] if j < len(hgt) else 0; start = j
            while st and st[-1][1] >= hj:
                k, hk = st.pop()
                if hk * (j - k) > best[0]: best = (hk * (j - k), (i - hk + 1, k, hk, j - k))
                start = k
            st.append((start, hj))
    return best


def rect_corners(mask, angles):
    """Rotate pixel coordinates exactly (nearest-neighbour inverse map), return rectangle corners in (i, j)."""
    ci, cj = (np.array(mask.shape) - 1) / 2
    best = (0, None)
    for a in angles:
        t = np.radians(a); R = np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])
        L = int(np.ceil(np.hypot(*mask.shape))) + 2
        p, q = np.meshgrid(np.arange(L) - L / 2, np.arange(L) - L / 2, indexing="ij")
        src = np.tensordot(R.T, np.stack([p, q]), 1)
        si, sj = np.rint(src[0] + ci).astype(int), np.rint(src[1] + cj).astype(int)
        ok = (si >= 0) & (sj >= 0) & (si < mask.shape[0]) & (sj < mask.shape[1])
        rot = np.zeros_like(ok); rot[ok] = mask[si[ok], sj[ok]]
        area, r = max_rect(rot)
        if area > best[0]:
            i0, j0, hh, ww = r
            pc = np.array([[i0, j0], [i0 + hh, j0], [i0 + hh, j0 + ww], [i0, j0 + ww]], float) - L / 2 - 0.5
            corners = (R.T @ pc.T).T + [ci, cj]
            best = (area, dict(angle=a, corners=corners, dims=sorted([hh * res, ww * res], reverse=True)))
    return best[1]


rects = {}
for t in ("0.5", "1.0"):
    tol = float(t)
    flat = np.isfinite(D) & (np.abs(D) <= tol / 2) & ndimage.binary_dilation(panel, iterations=40)
    lab, nl = ndimage.label(flat); keep = lab == (np.argmax(ndimage.sum(flat, lab, range(1, nl + 1))) + 1)
    a0 = F["rectangles"][str(tol)]["angle_deg"] if str(tol) in F["rectangles"] else 0.0
    rects[t] = rect_corners(keep, np.arange(a0 - 3, a0 + 3.01, 0.5))
rects["panel"] = rect_corners(ndimage.binary_fill_holes(panel), np.arange(-6, 6.01, 0.5))

# commercial 23 x 8 mm tile centred in the 1.0 mm rectangle, long side along the rectangle's long side
c1 = rects["1.0"]["corners"]; ctr = c1.mean(0)
e1, e2 = c1[1] - c1[0], c1[3] - c1[0]
long, short = (e1, e2) if np.linalg.norm(e1) >= np.linalg.norm(e2) else (e2, e1)
lu, su = long / np.linalg.norm(long), short / np.linalg.norm(short)
tile = np.array([ctr + sx * 11.5 / res * lu + sy * 4.0 / res * su for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
rects["tile_23x8"] = dict(corners=tile, dims=[23.0, 8.0])

# ---- figure ----
fig, ax = plt.subplots(1, 2, figsize=(15, 7.5))
ext = [0, H.shape[0] * res, 0, H.shape[1] * res]
ax[0].imshow(H.T, origin="lower", cmap="Greys_r", extent=ext)
Dp = np.where(panel, D, np.nan)
im = ax[0].imshow(Dp.T, origin="lower", cmap="coolwarm", extent=ext, vmin=-1, vmax=1)
plt.colorbar(im, ax=ax[0], label="bulge above (+) / below (-) the flat plane, mm")
ax[0].set_title("Outward face (away from the ear) - JBL letters treated as flat")
ax[1].imshow(H.T, origin="lower", cmap="Greys_r", extent=ext)
style = {"0.5": ("tab:orange", "flat within 0.5 mm"), "1.0": ("tab:green", "flat within 1.0 mm"),
         "panel": ("tab:purple", "whole panel (cell bends 37.8 mm)"), "tile_23x8": ("tab:blue", "off-the-shelf 23x8 mm tile")}
for k, (col, name) in style.items():
    c = rects[k]["corners"] * res; d = rects[k]["dims"]
    ax[1].fill(c[:, 0], c[:, 1], facecolor=col, alpha=0.25 if k != "tile_23x8" else 0.6, edgecolor=col, lw=2,
               label=f"{name}: {d[0]:.1f} x {d[1]:.1f} mm = {d[0]*d[1]/100:.2f} cm2")
for a in ax:
    a.set_xlabel("mm"); a.set_ylabel("mm"); a.set_aspect("equal")
ax[1].legend(fontsize=8, loc="upper right"); ax[1].set_title("Largest rectangles on the outward face")
plt.tight_layout(); plt.savefig(os.path.join(out, "EP3_outward_face_rectangles.png"), dpi=110)

# ---- GLB: earbud + plates sitting on the face ----
s = trimesh.load(glb, force="scene")
x0y0 = None
pts = []
for node in s.graph.nodes_geometry:
    T, g = s.graph[node]; m = s.geometry[g].copy(); m.apply_transform(T); pts.append(m.vertices)
allp = np.vstack(pts)
# recover the map origin used in flat_face.py (min of samples ~ min of vertices along u, v)
x0, y0 = (allp @ u).min(), (allp @ v).min()
for k, rgba in (("1.0", [40, 170, 60, 255]), ("tile_23x8", [30, 80, 200, 255])):
    c = rects[k]["corners"]
    ii = np.clip(np.rint(c[:, 0]).astype(int), 0, H.shape[0] - 1); jj = np.clip(np.rint(c[:, 1]).astype(int), 0, H.shape[1] - 1)
    poly = np.array([[x0 + ci * res, y0 + cj * res] for ci, cj in c])
    from matplotlib.path import Path
    gi, gj = np.meshgrid(np.arange(H.shape[0]), np.arange(H.shape[1]), indexing="ij")
    inside = Path(c).contains_points(np.c_[gi.ravel(), gj.ravel()]).reshape(H.shape)
    top = np.nanmax(H[inside]) + (0.05 if k == "1.0" else 0.35)
    thick = 0.3 if k == "1.0" else 1.8
    base = [p[0] * u + p[1] * v + top * n for p in poly]
    verts = np.array(base + [b + thick * n for b in base])
    faces = [[0, 1, 2], [0, 2, 3], [4, 6, 5], [4, 7, 6], [0, 4, 5], [0, 5, 1], [1, 5, 6], [1, 6, 2], [2, 6, 7], [2, 7, 3], [3, 7, 4], [3, 4, 0]]
    plate = trimesh.Trimesh(verts, faces); plate.fix_normals()
    plate.visual = trimesh.visual.ColorVisuals(plate, face_colors=np.tile(rgba, (len(plate.faces), 1)))
    s.add_geometry(plate, node_name=f"solar_{k}")
s.export(os.path.join(out, "EP3_earbud_with_solar_rectangle.glb"))
json.dump({k: dict(dims_mm=[round(x, 2) for x in r["dims"]], area_cm2=round(r["dims"][0] * r["dims"][1] / 100, 3))
           for k, r in rects.items()}, open(os.path.join(data, "flat_face_rectangles.json"), "w"), indent=1)
print({k: [round(x, 2) for x in r["dims"]] for k, r in rects.items()})
