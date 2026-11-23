"""Render the shell parts: each half outside/inside, a section through the seal, and an exploded view.
Usage: python3 render_shell.py <shell out dir> <png out dir>
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, trimesh
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from exterior import sample_triangles

src, dst = sys.argv[1:3]
L = np.array([0.35, 0.45, 0.82]); L /= np.linalg.norm(L)


def pts_of(mesh, col, spacing=0.09):
    p, i, _ = sample_triangles(mesh.triangles, spacing)
    return p, mesh.face_normals[i], np.tile(col, (len(p), 1))


def splat(ax, P, N, C, d, up, title, res=0.07):
    d = d / np.linalg.norm(d); u = np.cross(up, d); u /= np.linalg.norm(u); v = np.cross(d, u)
    x, y, z = P @ u, P @ v, P @ d
    gx = ((x - x.min()) / res).astype(int); gy = ((y - y.min()) / res).astype(int)
    key = gx * (gy.max() + 1) + gy
    o = np.lexsort((-z, key)); f = o[np.r_[True, key[o][1:] != key[o][:-1]]]
    img = np.ones((gy.max() + 1, gx.max() + 1, 3))
    sh = 0.35 + 0.65 * np.abs(N[f] @ (0.5 * d + 0.5 * L))
    img[gy[f], gx[f]] = np.clip(C[f] * sh[:, None], 0, 1)
    ax.imshow(img[::-1], extent=[0, img.shape[1] * res, 0, img.shape[0] * res]); ax.set_title(title, fontsize=10)
    ax.set_xlabel("mm"); ax.set_ylabel("mm")


M = {k: trimesh.load(os.path.join(src, f"EP3_shell_{k}.stl")) for k in ("cover", "base", "hook_arm")}
col = {"cover": (0.55, 0.58, 0.65), "base": (0.42, 0.44, 0.50), "hook_arm": (0.90, 0.45, 0.15)}
Pp = {k: pts_of(m, col[k]) for k, m in M.items()}
Z = np.array([0, 0, 1.0]); Yv = np.array([0, 1.0, 0])

fig, axs = plt.subplots(2, 3, figsize=(21, 11))
splat(axs[0, 0], *Pp["cover"], Z, Yv, "COVER from outside: 1.2 mm ledge, the solar cell is bonded on it")
splat(axs[0, 1], *Pp["cover"], -Z, Yv, "COVER from inside: tongue, screw pillars, LED sleeve, mic bosses")
splat(axs[0, 2], *Pp["base"], Z, Yv, "BASE from inside: gasket groove, screw/insert bosses, nozzle collar + rim")
splat(axs[1, 0], *Pp["base"], -Z, Yv, "BASE from outside (ear side): charging-pin holes, port, screw heads, nozzle opening")
P3 = np.vstack([Pp["hook_arm"][0]]); splat(axs[1, 1], *Pp["hook_arm"], Z + 0.4 * Yv, Yv, "HOOK ARM (flexible resin): peg end + magnet pocket at tip")
# exploded view
cell = trimesh.creation.box(extents=[33.0, 15.0, 1.5]); cell.apply_translation([0, 0, 0.75 + 14])
parts = [(cell, (0.12, 0.22, 0.6)), (M["cover"].copy().apply_translation([0, 0, 7]), col["cover"]),
         (M["base"], col["base"]), (M["hook_arm"].copy().apply_translation([0, -8, -8]), col["hook_arm"])]
pod = os.path.join(src, "EP3_shell_assembly_S.glb")
if os.path.exists(pod):
    sc = trimesh.load(pod, force="scene")
    for nd in sc.graph.nodes_geometry:
        if nd.startswith("original_pod"):
            T, g = sc.graph[nd]; m = sc.geometry[g].copy(); m.apply_transform(T); m.apply_translation([0, 0, -9])
            parts.append((m, (0.12, 0.12, 0.12)))
PE = [pts_of(m, c, 0.12) for m, c in parts]
splat(axs[1, 2], np.vstack([a[0] for a in PE]), np.vstack([a[1] for a in PE]), np.vstack([a[2] for a in PE]),
      np.array([0.75, -1.0, 0.45]), Z, "EXPLODED: cell / cover / base / original nozzle unit / hook arm", res=0.09)
plt.tight_layout(); plt.savefig(os.path.join(dst, "EP3_shell_parts.png"), dpi=85)

# section through the seal, from the voxel masks
D = np.load(os.path.join(src, "shell_masks.npz")); lo, p, zp = D["lo"], float(D["p"]), float(D["zp"])
fig, axs = plt.subplots(1, 2, figsize=(16, 6.5))
for a, xs in zip(axs, (0.0, 8.0)):
    i = int((xs - lo[0]) / p)
    img = np.ones(D["cover"].shape[1:] + (3,))
    zs = lo[2] + (np.arange(img.shape[1]) + 0.5) * p
    near_seam = (np.abs(zs - zp) < 2.0)[None, :]
    img[D["inside"][i] & ~D["cover"][i] & ~D["base"][i] & ~D["cavity"][i] & near_seam] = (0.95, 0.85, 0.3)   # gasket space
    img[D["base"][i]] = col["base"]; img[D["cover"][i]] = col["cover"]
    ext = [lo[1], lo[1] + img.shape[0] * p, lo[2], lo[2] + img.shape[1] * p]
    a.imshow(np.transpose(img, (1, 0, 2)), origin="lower", extent=ext, interpolation="nearest")
    a.axhline(zp, color="r", lw=0.6, ls="--"); a.set_xlim(-10, 10); a.set_ylim(-10, 1.5)
    a.set_title(f"Cross-section at X = {xs} mm (light = cover, dark = base, yellow = gasket space); red = seam")
    a.set_xlabel("Y (mm)"); a.set_ylabel("Z (mm), seat = 0")
plt.tight_layout(); plt.savefig(os.path.join(dst, "EP3_shell_section.png"), dpi=90)
print("saved", os.path.join(dst, "EP3_shell_parts.png"), os.path.join(dst, "EP3_shell_section.png"))
