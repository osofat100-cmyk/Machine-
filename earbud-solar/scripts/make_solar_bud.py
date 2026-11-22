"""Flatten the earbud's outward face under a real cell and set the cell on it.

Cell: ANYSOLAR SM400K10L - 33 x 15 x 1.8 mm, 10 mono-Si cells in series, 25 % cell efficiency,
Pmax 85.7 mW, Vmax 5.58 V, Voc 6.91 V, Isc 16.4 mA, 1.7 g (distributor table of ANYSOLAR data).
1. Best placement of the 33 x 15 footprint on the outward face (rotation + position search).
2. Flat seat = plane parallel to the face's best-fit plane, at the lowest surface point under the
   footprint; every earbud vertex above it inside the footprint (+0.3 mm) is pushed down onto it.
3. Cell = 10 strips on a thin base, 1.8 mm total, sitting on the seat.
Seat level = 5th percentile of the surface under the footprint (95 % supported).
Usage: python3 make_solar_bud.py <earbud glb> <data dir> <out dir>
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, trimesh
from scipy import ndimage
from scipy.signal import fftconvolve
from matplotlib.path import Path

glb, data, out = sys.argv[1:4]
CELL_L, CELL_W, CELL_H, N_CELLS = 33.0, 15.0, 1.8, 10
F = json.load(open(os.path.join(data, "flat_face.json")))
M = np.load(os.path.join(data, "flat_face_maps.npz"))
H, D, res = M["H"], M["D"], float(M["res"])
panel = ndimage.binary_fill_holes(M["panel"])
n = np.array(F["view_normal"]); n /= np.linalg.norm(n)
u = np.cross(n, [1, 0, 0]); u /= np.linalg.norm(u); v = np.cross(n, u)
plane = H - D                                    # fitted plane height on the grid

# ---- 1. best placement (exact rotation of the footprint, scored by overlap with the face) ----
gi, gj = np.meshgrid(np.arange(H.shape[0]), np.arange(H.shape[1]), indexing="ij")
# panel's long direction (PCA) -> try the cell's long side along it, rotated -6..+6 deg
pi_, pj_ = np.nonzero(panel); Xc = np.c_[pi_, pj_] - [pi_.mean(), pj_.mean()]
w_, V_ = np.linalg.eigh(Xc.T @ Xc); pca_long = V_[:, 1]
best = None
half = int(np.ceil(np.hypot(CELL_L, CELL_W) / 2 / res)) + 2
ki, kj = np.meshgrid(np.arange(-half, half + 1), np.arange(-half, half + 1), indexing="ij")
for ang in np.arange(-6, 6.01, 0.25):
    t = np.radians(ang); la = np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]]) @ pca_long
    sa = np.array([-la[1], la[0]])
    kern = (np.abs(ki * la[0] + kj * la[1]) <= CELL_L / 2 / res) & (np.abs(ki * sa[0] + kj * sa[1]) <= CELL_W / 2 / res)
    s = fftconvolve(panel.astype(float), kern[::-1, ::-1].astype(float), mode="same")   # overlap count per centre
    k = np.unravel_index(np.argmax(s), s.shape)
    if best is None or s[k] / kern.sum() > best[0]:
        best = (s[k] / kern.sum(), ang, np.array(k, float), la, sa)
score, ang, centre, long_axis, short_axis = best
corners = np.array([centre + sx * CELL_L / 2 / res * long_axis + sy * CELL_W / 2 / res * short_axis
                    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
inside = Path(corners).contains_points(np.c_[gi.ravel(), gj.ravel()]).reshape(H.shape)
overlap = (inside & panel).sum() / inside.sum()

# ---- 2. seat plane (parallel to the fitted plane, through the lowest point under the footprint) ----
dlow, dmax = np.nanmin(D[inside]), np.nanmax(D[inside])
dmin = np.nanpercentile(D[inside], 5)          # seat level: 95 % of the footprint supported, rounded corners overhang
s = trimesh.load(glb, force="scene")
allv = np.vstack([s.geometry[s.graph[nd][1]].vertices @ s.graph[nd][0][:3, :3].T + s.graph[nd][0][:3, 3] for nd in s.graph.nodes_geometry])
x0, y0 = (allv @ u).min(), (allv @ v).min()
ii, jj = np.nonzero(panel)
A_ = np.c_[ii * res, jj * res, np.ones(len(ii))]
pc = np.linalg.lstsq(A_, plane[ii, jj], rcond=None)[0]       # plane: h = pc0*X + pc1*Y + pc2 (X,Y in mm from origin)
seat = lambda X, Y: pc[0] * X + pc[1] * Y + pc[2] + dmin
foot = Path(corners * res)                                    # footprint in mm (grid frame)
grow = Path(np.array([centre + sx * (CELL_L / 2 + 0.3) / res * long_axis + sy * (CELL_W / 2 + 0.3) / res * short_axis
                      for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]) * res)
moved = 0
new = trimesh.Scene()
orig_h = []
for nd in s.graph.nodes_geometry:
    T, g = s.graph[nd]; m = s.geometry[g].copy(); m.apply_transform(T)
    p = m.vertices.copy(); orig_h.append(p @ n)
    X, Y, h = p @ u - x0, p @ v - y0, p @ n
    sh = seat(X, Y)
    k = grow.contains_points(np.c_[X, Y]) & (h > sh)
    p[k] += ((sh[k] - h[k]))[:, None] * n
    moved += int(k.sum()); m.vertices = p
    new.add_geometry(m, node_name=nd)

# ---- 3. the cell: base + 10 strips, total 1.8 mm, bottom on the seat ----
def box3d(c2, L, W, z0, z1, along, across):
    pts2 = [c2 + sx * L / 2 * along + sy * W / 2 * across for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    bot = [x0u * u + y0v * v + (seat(x0u - x0, y0v - y0) + z0) * n for x0u, y0v in [(q[0] + x0, q[1] + y0) for q in pts2]]
    top = [b + (z1 - z0) * n for b in bot]
    V = np.array(bot + top)
    Fc = [[0, 1, 2], [0, 2, 3], [4, 6, 5], [4, 7, 6], [0, 4, 5], [0, 5, 1], [1, 5, 6], [1, 6, 2], [2, 6, 7], [2, 7, 3], [3, 7, 4], [3, 4, 0]]
    mm = trimesh.Trimesh(V, Fc); mm.fix_normals(); return mm
c_mm = centre * res; la, sa = long_axis, short_axis
base = box3d(c_mm, CELL_L, CELL_W, 0.0, 1.5, la, sa)        # PCB + encapsulation body
base.visual = trimesh.visual.ColorVisuals(base, face_colors=np.tile([40, 40, 45, 255], (12, 1)))
new.add_geometry(base, node_name="SM400K10L_body")
pitch = (CELL_L - 1.0) / N_CELLS
for c in range(N_CELLS):
    cc = c_mm + (-CELL_L / 2 + 0.5 + pitch * (c + 0.5)) * la
    strip = box3d(cc, pitch - 0.25, CELL_W - 1.0, 1.5, CELL_H, la, sa)
    strip.visual = trimesh.visual.ColorVisuals(strip, face_colors=np.tile([25, 45, 120, 255], (12, 1)))
    new.add_geometry(strip, node_name=f"SM400K10L_cell_{c+1}")
new.export(os.path.join(out, "EP3_earbud_flat_face_SM400K10L.glb"))

orig_h = np.concatenate(orig_h)
new_top = max((g.vertices @ n).max() for g in new.dump())
res_out = dict(cell="ANYSOLAR SM400K10L", cell_mm=[CELL_L, CELL_W, CELL_H], footprint_on_face_pct=round(100 * overlap, 1),
               rotation_deg=float(ang), shaved_mm=round(float(dmax - dmin), 2), corner_overhang_share_pct=5.0,
               max_gap_under_corners_mm=round(float(dmin - dlow), 2),
               cell_top_above_original_face_top_mm=round(float(new_top - orig_h.max()), 2),
               earbud_depth_along_face_normal_mm=[round(float(np.ptp(orig_h)), 2), round(float(new_top - orig_h.min()), 2)],
               vertices_moved=moved)
json.dump(res_out, open(os.path.join(data, "solar_bud_SM400K10L.json"), "w"), indent=1)
print(json.dumps(res_out))
