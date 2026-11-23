"""Check the vision-video inside parts (data/vision_layout.json) against the shell: nothing may poke outside the
earbud (outside_earbud must be 0) and parts must not overlap each other. in_shell_material counts voxels hidden inside
the shell walls / seal ledge (invisible in the render, but a real fit problem for the printable shell).
Usage: python3 vision_layout_check.py"""
import json, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
L = json.load(open(os.path.join(HERE, "..", "data", "vision_layout.json")))
z = np.load(os.path.join(HERE, "..", "models", "shell", "shell_masks.npz"))
p, lo = float(z["p"]), z["lo"]
solid = z["cover"] | z["base"]
env = z["inside"] | z["cover"] | z["base"]


def grid(lo_, hi_):
    ax = [np.arange(a, b, p / 2) for a, b in zip(lo_, hi_)]
    return np.stack(np.meshgrid(*ax, indexing="ij"), -1).reshape(-1, 3)


def box_pts(c, s, r=0.0):
    c, s = np.array(c), np.array(s)
    P = grid(c - s / 2, c + s / 2)
    if r:
        q = np.abs(P[:, :2] - c[:2]) - (s[:2] / 2 - r)
        P = P[np.hypot(np.maximum(q[:, 0], 0), np.maximum(q[:, 1], 0)) <= r]
    return P


def cyl_pts(c, d, h):
    c = np.array(c); P = grid(c - [d / 2, d / 2, h / 2], c + [d / 2, d / 2, h / 2])
    return P[np.hypot(P[:, 0] - c[0], P[:, 1] - c[1]) <= d / 2]


B, PCB, S = L["battery"], L["pcb"], L["speaker"]
parts = {"battery": box_pts(B["centre"], B["size"], B["corner_r"]),
         "pcb": box_pts(PCB["centre"], PCB["size"], PCB["corner_r"]),
         "speaker": cyl_pts(S["centre"], S["d"], S["h"])}
top = PCB["centre"][2] + PCB["size"][2] / 2
parts["pcb_parts_envelope"] = box_pts([PCB["centre"][0], PCB["centre"][1], top + 0.65], [PCB["size"][0] - 1, PCB["size"][1] - 1, 1.3])
rep = {}
for k, P in parts.items():
    ijk = np.floor((P - lo) / p).astype(int)
    hit = solid[ijk[:, 0], ijk[:, 1], ijk[:, 2]]
    out = ~env[ijk[:, 0], ijk[:, 1], ijk[:, 2]]
    rep[k] = dict(points=len(P), in_shell_material=int(hit.sum()), outside_earbud=int(out.sum()),
                  worst=np.round(P[hit].mean(0), 2).tolist() if hit.any() else None,
                  z_range=[round(float(P[:, 2].min()), 2), round(float(P[:, 2].max()), 2)])
names = ["battery", "pcb", "speaker", "pcb_parts_envelope"]
for i, a in enumerate(names):
    for b in names[i + 1:]:
        A = set(map(tuple, np.round(parts[a] / (p / 2)).astype(int)))
        n = sum(1 for t in map(tuple, np.round(parts[b] / (p / 2)).astype(int)) if t in A)
        if n: rep[f"overlap {a}/{b}"] = n
print(json.dumps(rep, indent=1))
