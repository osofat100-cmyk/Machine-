import sys, json
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, trimesh
from exterior import exterior_area, fib_dirs, silhouette_areas

GLB = sys.argv[1]
PUB_BUD = np.array([51.92, 40.65, 29.34])    # JBL spec sheet H*W*D
PUB_CASE = np.array([90.93, 57.94, 35.57])   # JBL spec sheet H*W*D
s = trimesh.load(GLB, force="scene")

parts = {}
for name in s.graph.nodes_geometry:
    T, g = s.graph[name]
    m = s.geometry[g].copy(); m.apply_transform(T); m.apply_scale(1000.0)  # metres -> mm
    m.merge_vertices()
    parts[name] = m

def components(m):
    cc = trimesh.graph.connected_components(m.face_adjacency, nodes=np.arange(len(m.faces)), min_len=1)
    return [np.asarray(c) for c in cc]

# ---------------- earbuds: split by position (one loose, one in the case) ----------------
bud_out, bud_in = [], []
for n, m in parts.items():
    if not n.startswith("Earphone"):
        continue
    c = m.triangles_center
    bud_out.append((n, m.triangles[c[:, 0] > 10]))
    bud_in.append((n, m.triangles[c[:, 0] <= 10]))

def analyse(label, named_tris, pub, pitch, seal, res):
    tri = np.vstack([t for _, t in named_tris if len(t)])
    owner = np.concatenate([[n] * len(t) for n, t in named_tris if len(t)])
    mesh = trimesh.Trimesh(vertices=tri.reshape(-1, 3), faces=np.arange(len(tri) * 3).reshape(-1, 3), process=False)
    obb = np.sort(mesh.bounding_box_oriented.primitive.extents)[::-1]
    ratio = np.sort(pub)[::-1] / obb
    A, frac, area, P = exterior_area(tri, pitch, seal)
    hull = trimesh.convex.convex_hull(mesh.vertices)
    sil = silhouette_areas(P, fib_dirs(400), res)
    by = {}
    for n in np.unique(owner):
        k = owner == n
        by[n] = (float((area[k] * frac[k]).sum()), float(area[k].sum()))
    return dict(label=label, obb=obb.round(2).tolist(), pub=np.sort(pub)[::-1].tolist(), ratio=ratio.round(4).tolist(),
                raw_total=float(area.sum()), exterior=A, hull=float(hull.area), sil_max=float(sil.max()),
                sil_min=float(sil.min()), sil_mean=float(sil.mean()), by_part=by)

res = []
res.append(analyse("earbud (loose, outside case)", bud_out, PUB_BUD, 0.15, 0.3, 0.1))
res.append(analyse("earbud (sitting in case)", bud_in, PUB_BUD, 0.15, 0.3, 0.1))

# ---------------- case: split lid from base, rotate lid shut ----------------
lid, base = [], []
for n, m in parts.items():
    if not n.startswith(("Case", "Port")):  # "Complience" = sticker overlay, excluded
        continue
    for c in components(m):
        t = m.triangles[c]; ctr = t.reshape(-1, 3).mean(0)
        (lid if (ctr[2] < -23.5 and ctr[1] > 26) else base).append((n, t))
lid_pts = np.vstack([t.reshape(-1, 3) for _, t in lid]); base_pts = np.vstack([t.reshape(-1, 3) for _, t in base])
plate = parts["Case_Inner_Plastic"].vertices                      # flat inner panel of the lid
z_plate = float(np.median(plate[:, 2]))
y_rim = float(parts["Case_Inner_Plastic_Lower"].vertices[:, 1].max())   # top of base rim
lid_y = (lid_pts[:, 1].min(), lid_pts[:, 1].max()); base_z = (base_pts[:, 2].min(), base_pts[:, 2].max())
# +90 deg about x through pivot (y0,z0):  y' = y0 - (z - z0),  z' = z0 + (y - y0)
# seat lid panel on rim:  y0 + z0 = y_rim + z_plate ; centre lid over base footprint: z0 - y0 = mean(base_z) - mean(lid_y)
S1 = y_rim + z_plate; S2 = np.mean(base_z) - np.mean(lid_y)
z0 = (S1 + S2) / 2; y0 = (S1 - S2) / 2
def close(t):
    p = t.reshape(-1, 3).copy(); y, z = p[:, 1].copy(), p[:, 2].copy()
    p[:, 1] = y0 - (z - z0); p[:, 2] = z0 + (y - y0)
    return p.reshape(-1, 3, 3)
closed = base + [(n, close(t)) for n, t in lid]
print(f"hinge pivot y0={y0:.2f} z0={z0:.2f}; lid panel z={z_plate:.2f}; rim y={y_rim:.2f}")
r = analyse("charging case (lid closed)", closed, PUB_CASE, 0.25, 0.5, 0.15)
allp = np.vstack([t.reshape(-1, 3) for _, t in closed]); r["axis_bbox"] = (allp.max(0) - allp.min(0)).round(2).tolist()
res.append(r)
json.dump(res, open(sys.argv[2], "w"), indent=1)
for r in res:
    print(json.dumps({k: v for k, v in r.items() if k != "by_part"}))
