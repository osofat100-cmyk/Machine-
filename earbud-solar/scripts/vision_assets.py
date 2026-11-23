"""Meshes for the 'vision' video: the custom shell with the solar cell SET INTO the cover.

The printable shell (shell_build.py) seats the 33 x 15 x 1.5 mm cell on the flat face, so it stands 1.5 mm proud.
For the video the face is built up around the cell (the earbud's own outline, extruded up) to 0.2 mm below the cell top: the cell looks sunk
in, the earbud gets no thicker (the cell top stays the highest point) and the inside space is unchanged.
The raised face is smooth-unioned onto the outside of the original skin only, then the cell pocket and the end-screw well
are cut back out. Render-only: the printable STLs are not touched.

Input: models/shell/shell_masks.npz + EP3_shell_*.stl + EP3_shell_assembly_S.glb (JBL-derived, git-ignored).
Output: <out>/{cover,base,hook,pod,cell}.glb in seat frame S (mm, Z out of the face) + vision_assets.json.
Usage: python3 vision_assets.py <out dir>
"""
import json, os, sys
import numpy as np
import trimesh
import fast_simplification as fs
from scipy import ndimage
import sdf

HERE = os.path.dirname(os.path.abspath(__file__))
SHELL = os.path.join(HERE, "..", "models", "shell")
OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)

VISUAL_SCALE = 0.9                       # footprint drawn at 90 % (styling choice for the video)
CELL = np.array([33.0 * VISUAL_SCALE, 15.0 * VISUAL_SCALE, 1.5])   # SM400K10TF, DigiKey thickness
PROUD = 0.2                              # cell top above the bezel
OUTLINE_Z, INSET, TOP_R, BLEND = -1.5, 0.0, 0.9, 0.8
POCKET_CLR = 0.05
SCREW = dict(xy=(17.94, -0.18), r=1.2, z0=0.48 - 1.3)   # shell_report.json end_screw: head face 0.48, c-bore 1.3

z = np.load(os.path.join(SHELL, "shell_masks.npz"))
p = float(z["p"]); lo = z["lo"]
g = sdf.Grid(lo, lo + np.array(z["cover"].shape) * p - p, p)
g.shape = z["cover"].shape
cover = z["cover"].copy()
env = z["inside"] | z["cover"] | z["base"]

# work on the top slab only
sl = g.block([-24, -12, -5.0], [23, 12, 3.0], margin=0.0)
gs = g.sub(sl)
X, Y, Z = gs.xyz()
phi_env = sdf.sdf_from_solid(env[sl], p)

top = CELL[2] - PROUD
# plateau: the earbud's own outline (slice of the skin just below the rolled face edge), extruded straight up to
# `top` with a rounded top edge, so the face keeps its pill shape and simply rises around the cell
k_out = int(round((OUTLINE_Z - gs.lo[2]) / p - 0.5))
F = env[sl][:, :, k_out]
d2 = (ndimage.distance_transform_edt(~F) - ndimage.distance_transform_edt(F)).astype(np.float32) * p
d2 = d2[:, :, None] + np.float32(INSET)
zc = OUTLINE_Z - 1.5
dz = np.abs(Z - (top + zc) / 2) - (top - zc) / 2
wx, wy = d2 + TOP_R, dz + TOP_R
phi_bez = (np.sqrt(np.maximum(wx, 0) ** 2 + np.maximum(wy, 0) ** 2) + np.minimum(np.maximum(wx, wy), 0) - TOP_R).astype(np.float32)

h = np.clip(0.5 + 0.5 * (phi_bez - phi_env) / BLEND, 0, 1)
phi_new = phi_bez * (1 - h) + phi_env * h - BLEND * h * (1 - h)
added = (phi_new <= 0) & ~env[sl]

pocket = (np.abs(X) <= CELL[0] / 2 + POCKET_CLR) & (np.abs(Y) <= CELL[1] / 2 + POCKET_CLR) & (Z >= 0.0)
well = ((X - SCREW["xy"][0]) ** 2 + (Y - SCREW["xy"][1]) ** 2 <= SCREW["r"] ** 2) & (Z >= SCREW["z0"])
cs = cover[sl] | added
cs &= ~pocket
cs[well & added] = False
cover[sl] = cs
print("bezel voxels added:", int((added & ~pocket).sum()), f"= {(added & ~pocket).sum() * p ** 3:.1f} mm3")


def to_mesh(mask, keep=0.45):
    m = sdf.mesh(sdf.smooth(sdf.sdf_from_solid(mask, p), 0.6), g)
    m = sorted(m.split(only_watertight=False), key=lambda q: -abs(q.volume))[0]
    return decimate(polish(m), keep)


def polish(m, it=25):
    """Taubin smoothing: removes the voxel ripples (render only), keeps the volume."""
    trimesh.smoothing.filter_taubin(m, lamb=0.5, nu=-0.53, iterations=it)
    return m


def decimate(m, keep):
    v, f = fs.simplify(m.vertices.astype(np.float32), m.faces.astype(np.int64), target_reduction=1 - keep)
    return trimesh.Trimesh(v, f, process=True)


cov = to_mesh(cover)
# where does the new cover surface sit around the cell?
ring = []
ex, ey = CELL[0] / 2 + 0.4, CELL[1] / 2 + 0.4
for t in np.linspace(0, 1, 40, endpoint=False):
    for (x, y) in [(-ex + 2 * ex * t, -ey), (-ex + 2 * ex * t, ey), (-ex, -ey + 2 * ey * t), (ex, -ey + 2 * ey * t)]:
        ring.append((x, y))
ring = np.array(ring)
loc, ri, _ = cov.ray.intersects_location(np.c_[ring, np.full(len(ring), 5.0)], np.tile([0, 0, -1.0], (len(ring), 1)), multiple_hits=False)
rz = np.full(len(ring), np.nan); rz[ri] = loc[:, 2]

asm = trimesh.load(os.path.join(SHELL, "EP3_shell_assembly_S.glb"))
pod = None
for n in asm.graph.nodes_geometry:
    T, gname = asm.graph[n]
    if n == "original_pod":
        pod = asm.geometry[gname].copy(); pod.apply_transform(T)
parts = dict(cover=cov,
             base=decimate(polish(trimesh.load(os.path.join(SHELL, "EP3_shell_base.stl"))), 0.4),
             hook=decimate(polish(trimesh.load(os.path.join(SHELL, "EP3_shell_hook_arm.stl")), 40), 0.4),
             pod=trimesh.Trimesh(pod.vertices, pod.faces, process=True))
for k, m in parts.items():
    m.visual = trimesh.visual.ColorVisuals(m)
    m.export(os.path.join(OUT, f"{k}.glb"))
info = dict(cell_mm=np.round(CELL, 3).tolist(), visual_scale=VISUAL_SCALE, cell_seat_z=0.0, cell_top_z=float(CELL[2]), bezel_top_z=float(top), proud_mm=PROUD,
            ring_surface_z=dict(min=round(float(np.nanmin(rz)), 2), median=round(float(np.nanmedian(rz)), 2),
                                max=round(float(np.nanmax(rz)), 2), misses=int(np.isnan(rz).sum())),
            triangles={k: len(m.faces) for k, m in parts.items()},
            bounds={k: np.round(m.bounds, 2).tolist() for k, m in parts.items()})
json.dump(info, open(os.path.join(OUT, "vision_assets.json"), "w"), indent=1)
print(json.dumps(info, indent=1))
