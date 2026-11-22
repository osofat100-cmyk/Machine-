"""Gate 1: does the flat-face + solar-cell earbud still fit the CLOSED JBL case and line up with its pins?

1. Original GLB in mm: loose bud (Earphone_* faces with centre x > 10), in-case bud (x <= 10), case parts.
2. Register loose bud -> in-case bud: Kabsch on anchor points (2 pins, window, LED, nozzle mesh; both pin
   orderings; reflection allowed since the in-case bud may be the other ear), refined by ICP on body samples.
3. Move the solar bud (measured frame + loose-bud centre) into the case pose; close the lid (same hinge as
   export_measured.py).
4. Voxel check (0.1 mm): case-surface voxels inside the bud solid = collision (depth by distance transform);
   gap from the cell top to the nearest case surface. The original in-case bud is the baseline.
Usage: python3 case_fit.py <models dir> <data dir> [cell model, default SM400K10TF]
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, trimesh
from scipy import ndimage
from scipy.spatial import cKDTree
from exterior import sample_triangles

models, data = sys.argv[1:3]
CELL = sys.argv[3] if len(sys.argv) > 3 else "SM400K10TF"
Y0, Z0 = 21.20, -21.15          # lid hinge pivot (mm, original frame) from ep3_analyze.py
PITCH = 0.12

orig = trimesh.load(os.path.join(models, "JBL_Endurance_Peak_3_original.glb"), force="scene")
loose, incase, case = {}, {}, {}
for nd in orig.graph.nodes_geometry:
    T, g = orig.graph[nd]; m = orig.geometry[g].copy(); m.apply_transform(T); m.apply_scale(1000.0)
    if nd.startswith("Earphone"):
        c = m.triangles_center
        a, b = np.where(c[:, 0] > 10)[0], np.where(c[:, 0] <= 10)[0]
        if len(a): loose[nd] = m.submesh([a], append=True)
        if len(b): incase[nd] = m.submesh([b], append=True)
    elif nd.startswith(("Case", "Port")) and not nd.startswith("Complience"):
        case[nd] = m
m_loose = trimesh.util.concatenate(list(loose.values())).bounds.mean(0)   # export_measured recentring


def anchors(P):
    pins = P["Earphone_Pins"]; pins.merge_vertices()
    cc = trimesh.graph.connected_components(pins.face_adjacency, nodes=np.arange(len(pins.faces)), min_len=1)
    pc = sorted([pins.submesh([c], append=True).vertices.mean(0) for c in cc], key=lambda p: p[0])
    return np.array(pc + [P["Earphone_Glossy_2"].vertices.mean(0), P["Earphone_Light"].vertices.mean(0),
                          P["Earphone_Fabric"].vertices.mean(0)])


def kabsch(A, B, allow_reflection):
    ca, cb = A.mean(0), B.mean(0)
    U, S, Vt = np.linalg.svd((A - ca).T @ (B - cb))
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    D = np.diag([1, 1, d if not allow_reflection else 1])
    R = Vt.T @ D @ U.T
    return R, cb - R @ ca


A0, B0 = anchors(loose), anchors(incase)
best = None
for perm in ([0, 1, 2, 3, 4], [1, 0, 2, 3, 4]):
    for refl in (False, True):
        R, t = kabsch(A0[perm], B0, refl)
        rms = np.sqrt((((A0[perm] @ R.T + t) - B0) ** 2).sum(1).mean())
        if best is None or rms < best[0]:
            best = (rms, R, t, refl, perm)
rms0, R, t, refl, perm = best
# ICP refine on the plastic body
src, _, _ = sample_triangles(loose["Earphone_Plastic"].triangles, 0.4)
dst, _, _ = sample_triangles(incase["Earphone_Plastic"].triangles, 0.4)
tree = cKDTree(dst)
for _ in range(30):
    cur = src @ R.T + t
    d, j = tree.query(cur)
    keep = d < np.percentile(d, 90)
    dR, dt = kabsch(cur[keep], dst[j[keep]], False)
    R, t = dR @ R, dR @ t + dt
icp_rms = float(np.sqrt((tree.query(src @ R.T + t)[0] ** 2).mean()))
pin_err = np.linalg.norm((A0[perm][:2] @ R.T + t) - B0[:2], axis=1)

# solar bud (measured frame -> original frame -> case pose)
sb = trimesh.load(os.path.join(models, f"EP3_earbud_flat_face_{CELL}.glb"), force="scene")
solar, cell = [], []
for nd in sb.graph.nodes_geometry:
    T, g = sb.graph[nd]; m = sb.geometry[g].copy(); m.apply_transform(T)
    tri = (m.triangles.reshape(-1, 3) + m_loose) @ R.T + t
    (cell if nd.startswith("SM400K10") else solar).append(tri.reshape(-1, 3, 3))
solar_tri = np.vstack(solar + cell); cell_tri = np.vstack(cell)
base_tri = np.vstack([m.triangles for m in incase.values()])


def close_lid(tri):
    p = tri.reshape(-1, 3).copy(); y, z = p[:, 1].copy(), p[:, 2].copy()
    p[:, 1] = Y0 - (z - Z0); p[:, 2] = Z0 + (y - Y0)
    return p.reshape(-1, 3, 3)


case_tri = []
for nd, m in case.items():
    m.merge_vertices()
    cc = trimesh.graph.connected_components(m.face_adjacency, nodes=np.arange(len(m.faces)), min_len=1)
    for c in cc:
        tr = m.triangles[c]; ctr = tr.reshape(-1, 3).mean(0)
        case_tri.append(close_lid(tr) if (ctr[2] < -23.5 and ctr[1] > 26) else tr)
case_tri = np.vstack(case_tri)

lo = np.minimum(base_tri.reshape(-1, 3).min(0), solar_tri.reshape(-1, 3).min(0)) - 3
hi = np.maximum(base_tri.reshape(-1, 3).max(0), solar_tri.reshape(-1, 3).max(0)) + 3
shape = np.ceil((hi - lo) / PITCH).astype(int) + 1


def vox_surface(tri):
    p, _, _ = sample_triangles(tri, PITCH * 0.5)
    k = np.all((p >= lo) & (p < hi), 1); p = p[k]
    occ = np.zeros(shape, bool); ijk = np.floor((p - lo) / PITCH).astype(int); occ[tuple(ijk.T)] = True
    return occ


def vox_solid(tri):
    occ = vox_surface(tri); b = ndimage.generate_binary_structure(3, 1)
    return ndimage.binary_erosion(ndimage.binary_fill_holes(ndimage.binary_dilation(occ, b, iterations=3)), b, iterations=3) | occ


case_surf = vox_surface(case_tri)
dist_to_case = ndimage.distance_transform_edt(~case_surf) * PITCH
out = dict(registration=dict(anchor_rms_mm=round(float(rms0), 3), icp_rms_mm=round(icp_rms, 3), mirrored=bool(refl),
                             pin_error_mm=[round(float(e), 3) for e in pin_err]))
for label, tri in (("original_bud_baseline", base_tri), ("solar_bud", solar_tri)):
    sol = vox_solid(tri)
    inner = ndimage.binary_erosion(sol, iterations=2)                 # ignore 0.2 mm skin contact
    hit = case_surf & inner
    depth = ndimage.distance_transform_edt(sol)[hit] * PITCH if hit.any() else np.array([0.0])
    out[label] = dict(case_surface_voxels_inside_bud=int(hit.sum()), max_penetration_mm=round(float(depth.max()), 2))
cp, _, _ = sample_triangles(cell_tri, PITCH * 0.5)
ijk = np.clip(np.floor((cp - lo) / PITCH).astype(int), 0, shape - 1)
out["cell_min_gap_to_case_mm"] = round(float(dist_to_case[tuple(ijk.T)].min()), 2)
out["cell"] = CELL
json.dump(out, open(os.path.join(data, f"case_fit_{CELL}.json"), "w"), indent=1)
np.savez_compressed(os.path.join(models, "case_fit_pose.npz"), R=R, t=t, m_loose=m_loose)
print(json.dumps(out, indent=1))
