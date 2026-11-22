"""Rebuild the two 'as measured' models from JBL's original GLB (all units = millimetres).

  EP3_earbud_measured_mm.glb/.stl      the loose earbud (body + hook + ear tip + housing rubber)
  EP3_case_closed_measured_mm.glb/.stl the case with its lid rotated shut on the hinge

Lid closing: +90 deg about the x axis through pivot (y0, z0), found by (a) seating the lid's flat
inner panel on the base rim and (b) centring the lid over the base footprint (see ep3_analyze.py).
"""
import os, sys
import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(HERE, "..", "models")
src = os.path.join(MODELS, "JBL_Endurance_Peak_3_original.glb")
y0, z0 = 21.20, -21.15   # hinge pivot in mm, printed by ep3_analyze.py

def close(v):
    v = v.copy(); y, z = v[:, 1].copy(), v[:, 2].copy()
    v[:, 1] = y0 - (z - z0); v[:, 2] = z0 + (y - y0)
    return v

s = trimesh.load(src, force="scene")
bud, case = trimesh.Scene(), trimesh.Scene()
for name in s.graph.nodes_geometry:
    T, g = s.graph[name]
    m = s.geometry[g].copy(); m.apply_transform(T); m.apply_scale(1000.0)
    if name.startswith("Earphone"):
        keep = np.where(m.triangles_center[:, 0] > 10)[0]          # the loose bud (x > 10 mm)
        if len(keep):
            bud.add_geometry(m.submesh([keep], append=True), node_name=name)
    elif name.startswith(("Case", "Port")):
        m.merge_vertices()
        cc = trimesh.graph.connected_components(m.face_adjacency, nodes=np.arange(len(m.faces)), min_len=1)
        lid = np.zeros(len(m.faces), bool)
        for c in cc:
            p = m.triangles[c].reshape(-1, 3)
            if p[:, 2].mean() < -23.5 and p[:, 1].mean() > 26:
                lid[c] = True
        for flag, tag in ((False, "base"), (True, "lid")):
            idx = np.where(lid == flag)[0]
            if len(idx):
                sub = m.submesh([idx], append=True)
                if flag:
                    sub.vertices = close(np.asarray(sub.vertices))
                case.add_geometry(sub, node_name=f"{name}_{tag}")

for sc, fn in ((bud, "EP3_earbud_measured_mm.glb"), (case, "EP3_case_closed_measured_mm.glb")):
    sc.apply_translation(-sc.bounds.mean(0))
    sc.export(os.path.join(MODELS, fn))
    trimesh.util.concatenate(list(sc.dump())).export(os.path.join(MODELS, fn.replace(".glb", ".stl")))
    print(fn, "extents mm", (sc.bounds[1] - sc.bounds[0]).round(2))
