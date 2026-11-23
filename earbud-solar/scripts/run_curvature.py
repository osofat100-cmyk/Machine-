"""Curvature map + coverage tables for the measured earbud and closed case.

Validated settings (sphere R=10: median |k| 0.1001, p10-p90 0.0956-0.1047; cylinder R=5:
k_max 0.207 vs 0.200, k_min ~0): earbud pitch 0.10 mm / sigma 2.5 vox / fit radius 1.5 mm;
case pitch 0.15 mm / sigma 2.0 vox / fit radius 1.5 mm.
Curvature is evaluated on a uniform random sample of skin vertices (area-weighted shares).
Usage: python3 run_curvature.py <models dir> <out.npz>
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, trimesh
from scipy.spatial import cKDTree
from curvature import outer_skin_mesh, principal_curvatures, vertex_area, coverage_tables
from exterior import sample_triangles

models, out = sys.argv[1], sys.argv[2]
rng = np.random.default_rng(0)
res = {}
for label, fn, pitch, sig in (("earbud", "EP3_earbud_measured_mm.glb", 0.10, 2.5),
                              ("case", "EP3_case_closed_measured_mm.glb", 0.15, 2.0)):
    sc = trimesh.load(os.path.join(models, fn), force="scene")
    tris, names = [], []
    for node in sc.graph.nodes_geometry:
        T, g = sc.graph[node]; m = sc.geometry[g].copy(); m.apply_transform(T)
        if label == "case" and node.startswith("Complience"):
            continue                                   # sticker overlay, not a surface
        tris.append(m.triangles); names += [node] * len(m.triangles)
    tri = np.vstack(tris); names = np.array(names)
    skin = outer_skin_mesh(tri, pitch, sigma_vox=sig)
    va = vertex_area(skin)
    pick = rng.choice(len(skin.vertices), size=min(60000, len(skin.vertices)), replace=False)
    sub = trimesh.Trimesh(skin.vertices, skin.faces, process=False)
    k1f, k2f = np.full(len(skin.vertices), np.nan), np.full(len(skin.vertices), np.nan)
    # curvature only at picked vertices (neighbourhoods still use the full skin)
    from curvature import cKDTree as _T  # noqa
    V, N = skin.vertices, skin.vertex_normals
    tree = cKDTree(V)
    for i in pick:
        nb = tree.query_ball_point(V[i], 1.5)
        n = N[i]; t = np.cross(n, [1, 0, 0] if abs(n[0]) < 0.9 else [0, 1, 0]); t /= np.linalg.norm(t); s = np.cross(n, t)
        d = V[nb] - V[i]; x, y, z = d @ t, d @ s, d @ n
        A = np.stack([x * x, x * y, y * y, x, y, np.ones_like(x)], 1)
        a, bxy, c, fx, fy, _ = np.linalg.lstsq(A, z, rcond=None)[0]
        w = np.sqrt(1 + fx * fx + fy * fy); E, F, G = 1 + fx * fx, fx * fy, 1 + fy * fy
        L, M, Nn = 2 * a / w, bxy / w, 2 * c / w
        K = (L * Nn - M * M) / (E * G - F * F); H = (E * Nn - 2 * F * M + G * L) / (2 * (E * G - F * F))
        dsc = np.sqrt(max(H * H - K, 0)); k1f[i], k2f[i] = H + dsc, H - dsc
    # region label of each skin vertex = nearest original part
    p, idx, _ = sample_triangles(tri, pitch)
    lab = names[idx][cKDTree(p).query(V)[1]]
    k1, k2, w, labp = k1f[pick], k2f[pick], va[pick], lab[pick]
    A, bend, tiles = coverage_tables(k1, k2, w)
    out_r = {"skin_area_mm2": float(skin.area), "bend": bend, "tiles": tiles}
    if label == "earbud":
        notr = ~np.isin(labp, ["Earphone_Rubber"])
        _, bend2, tiles2 = coverage_tables(k1, k2, w, notr)
        out_r.update(nonrubber_share=float(w[notr].sum() / w.sum()), bend_nonrubber=bend2, tiles_nonrubber=tiles2)
    res[label] = out_r
    np.savez_compressed(out.replace(".npz", f"_{label}.npz"), V=V, F=skin.faces, va=va, pick=pick, k1=k1f, k2=k2f, lab=lab)
    print(label, json.dumps(out_r)[:2000], flush=True)
json.dump(res, open(out.replace(".npz", ".json"), "w"), indent=1)
