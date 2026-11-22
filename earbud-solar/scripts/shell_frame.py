"""Seat frame S and feature anchors for the shell build.

S: origin = centre of the cell's bottom face (the flat seat), Z = seat normal (out of the face),
X = cell long axis, Y = Z x X.  Anchors (in S, mm): charging pins, window beside them, LED, mic ports
(round openings in the body found as boundary loops of Earphone_Plastic), nozzle mesh, pod over-mould axis,
cell solder pads (datasheet: Ø3.0 at 3.0 mm from each short end, centred).
Usage: python3 shell_frame.py <solar bud glb> <data dir>
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, trimesh, networkx as nx

glb, data = sys.argv[1:3]
s = trimesh.load(glb, force="scene")
P = {}
for nd in s.graph.nodes_geometry:
    T, g = s.graph[nd]; m = s.geometry[g].copy(); m.apply_transform(T); P[nd] = m
cell_name = [k for k in P if k.endswith("_body")][0]
cell = cell_name.replace("_body", "")
V = P[cell_name].vertices
bud_c = np.vstack([m.vertices for k, m in P.items() if k.startswith("Earphone")]).mean(0)
_, _, Vt = np.linalg.svd(V - V.mean(0))
X, Z = Vt[0], Vt[2]
if np.dot(V.mean(0) - bud_c, Z) < 0: Z = -Z
Y = np.cross(Z, X)
origin = V[np.argsort(V @ Z)[:4]].mean(0)
R = np.stack([X, Y, Z])
toS = lambda p: (np.asarray(p) - origin) @ R.T
dirS = lambda d: np.asarray(d) @ R.T


def outward(m, centre):
    n = (m.face_normals * m.area_faces[:, None]).sum(0); n /= np.linalg.norm(n)
    return n if np.dot(centre - bud_c, n) > 0 else -n


def local_normal(m, c, r=1.5):
    k = np.linalg.norm(m.triangles_center - c, axis=1) < r
    n = (m.face_normals[k] * m.area_faces[k, None]).sum(0); n /= np.linalg.norm(n)
    return n if np.dot(c - bud_c, n) > 0 else -n


A = {}
pins = P["Earphone_Pins"].copy(); pins.merge_vertices()
cc = trimesh.graph.connected_components(pins.face_adjacency, nodes=np.arange(len(pins.faces)), min_len=1)
pin_c = [pins.submesh([c], append=True).vertices.mean(0) for c in cc]
pin_n = -Z if True else None                       # pins face the ear side (checked: parallel to the seat normal)
A["pins"] = [dict(centre=toS(c).round(3).tolist(), dir=[0, 0, -1], diam=1.2) for c in sorted(pin_c, key=lambda p: toS(p)[0])]
w = P["Earphone_Glossy_2"]; wc = w.vertices.mean(0)
A["window"] = dict(centre=toS(wc).round(3).tolist(), dir=[0, 0, -1], size=[2.9, 2.2])
led = P["Earphone_Light"]; lc = led.vertices.mean(0)
A["led"] = dict(centre=toS(lc).round(3).tolist(), dir=dirS(outward(led, lc)).round(4).tolist(), diam=0.8)
fab = P["Earphone_Fabric"]; fc = fab.vertices.mean(0)
A["nozzle_mesh"] = dict(centre=toS(fc).round(3).tolist(), dir=dirS(outward(fab, fc)).round(4).tolist())

# mic ports: round boundary loops (1.2-1.7 mm) in the body skin, merged when concentric, LED excluded
pl = P["Earphone_Plastic"].copy(); pl.merge_vertices()
e = pl.edges_sorted; u, cnt = np.unique(e, axis=0, return_counts=True)
G = nx.Graph(); G.add_edges_from(u[cnt == 1])
loops = []
for comp in nx.connected_components(G):
    p = pl.vertices[list(comp)]; c = p.mean(0); r = np.linalg.norm(p - c, axis=1)
    if len(p) >= 8 and 1.2 < 2 * r.mean() < 1.7 and r.std() < 0.25 * r.mean() and np.linalg.norm(c - lc) > 1.0:
        loops.append((c, 2 * r.mean()))
mics = []
for c, d in loops:
    for mm in mics:
        if np.linalg.norm(mm["c"] - c) < 1.0:
            mm["d"] = max(mm["d"], d); break
    else:
        mics.append(dict(c=c, d=d))
A["mic_ports"] = [dict(centre=toS(m_["c"]).round(3).tolist(), dir=dirS(local_normal(pl, m_["c"])).round(4).tolist(),
                       original_opening_diam=round(float(m_["d"]), 2)) for m_ in mics]

# pod over-mould (largest rubber piece): centre + symmetry axis (smallest extent)
rub = P["Earphone_Rubber"].copy(); rub.merge_vertices()
cc = trimesh.graph.connected_components(rub.face_adjacency, nodes=np.arange(len(rub.faces)), min_len=1)
pod = max((rub.submesh([c], append=True) for c in cc), key=lambda m: m.bounding_box_oriented.primitive.extents.max())
_, _, pv = np.linalg.svd(pod.vertices - pod.vertices.mean(0))
A["pod_overmould"] = dict(centre=toS(pod.vertices.mean(0)).round(3).tolist(), axis=dirS(pv[2]).round(4).tolist(),
                          diam=round(float(pod.bounding_box_oriented.primitive.extents.max()), 2))
A["cell"] = dict(model=cell, size=[33.0, 15.0], pads=[dict(centre=[-13.5, 0.0, 0.0], diam=3.0),
                                                       dict(centre=[13.5, 0.0, 0.0], diam=3.0)],
                 note="pad polarity: datasheet shows '-' and '+' at the two short ends; check with a meter")
frame = dict(origin_measured_frame=origin.round(4).tolist(), R_rows_XYZ=R.round(6).tolist(), cell=cell)
json.dump(frame, open(os.path.join(data, "shell_frame.json"), "w"), indent=1)
json.dump(A, open(os.path.join(data, "shell_anchors.json"), "w"), indent=1)
print(json.dumps(A, indent=1))
