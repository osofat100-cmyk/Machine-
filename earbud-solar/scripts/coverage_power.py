"""Sunlit, coverable area -> solar power, for a given cell technology.

A skin point is 'coverable' if
   bend:  1/|k|max >= r_min            (cell's minimum bend radius)
   Gauss: L^2 |K| / 24 <= eps          (flat tile of size L forced onto Gaussian curvature K)
For each of 400 sun directions a z-buffer keeps only the skin points that face the light first
(nothing in front of them); lit coverable area = pixels whose nearest point is coverable.
Power = mean (and best) lit coverable area x 100 mW/cm^2 (standard test sun) x efficiency.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy.spatial import cKDTree
from exterior import fib_dirs


def load(npz):
    d = np.load(npz, allow_pickle=True)
    V, va, pick, k1, k2, lab = d["V"], d["va"], d["pick"], d["k1"], d["k2"], d["lab"]
    near = cKDTree(V[pick]).query(V)[1]                 # every vertex takes its nearest measured curvature
    return V, va, k1[pick][near], k2[pick][near], lab


def coverable(k1, k2, r_min, L, eps):
    kmax = np.maximum(np.abs(k1), np.abs(k2)); K = np.abs(k1 * k2)
    ok = np.ones(len(k1), bool)
    if r_min is not None:
        ok &= 1 / np.maximum(kmax, 1e-9) >= r_min
    if L is not None:
        ok &= K <= 24 * eps / L ** 2
    return ok


def lit_area(V, mask, dirs, res=0.2):
    out = []
    for d in dirs:
        u = np.cross(d, [1, 0, 0] if abs(d[0]) < 0.9 else [0, 1, 0]); u /= np.linalg.norm(u); v = np.cross(d, u)
        x, y, z = V @ u, V @ v, V @ d
        g = np.floor((np.stack([x, y], 1) - [x.min(), y.min()]) / res).astype(np.int64)
        key = g[:, 0] * (g[:, 1].max() + 1) + g[:, 1]
        order = np.lexsort((-z, key))                    # per pixel, the point nearest the sun first
        first = order[np.r_[True, key[order][1:] != key[order][:-1]]]
        out.append(mask[first].sum() * res * res)
    return np.array(out)


if __name__ == "__main__":
    data_dir = sys.argv[1]
    dirs = fib_dirs(400)
    for part in ("earbud", "case"):
        V, va, k1, k2, lab = load(os.path.join(data_dir, f"curvature_{part}.npz"))
        full = lit_area(V, np.ones(len(V), bool), dirs)
        print(part, f"check: all-skin lit area mean {full.mean()/100:.2f} cm2, best {full.max()/100:.2f} cm2")
