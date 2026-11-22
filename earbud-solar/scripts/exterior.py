"""Outer-skin ("exterior") surface math for multi-part product meshes.

1. Sample every triangle densely, mark surface voxels (pitch p).
2. Seal seams with a morphological closing, fill enclosed space -> solid.
   Exterior voxels = everything not solid.
3. A triangle's exterior fraction = share of its sample points whose
   +/- normal offset lands in an exterior voxel. Exact exterior area =
   sum(triangle area x exterior fraction)  (uses the original triangles,
   so the voxels only classify, they don't approximate the area).
4. Silhouette (sun-catching) area for a direction = area of the 2-D shadow
   of the exterior samples, rasterised at fine resolution (holes preserved).
"""
import numpy as np
from scipy import ndimage


def sample_triangles(tri, spacing):
    """Deterministic barycentric lattice: every point of every triangle is within ~spacing of a sample."""
    a, b, c = tri[:, 0], tri[:, 1], tri[:, 2]
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    emax = np.max(np.stack([np.linalg.norm(b - a, axis=1), np.linalg.norm(c - a, axis=1), np.linalg.norm(c - b, axis=1)]), 0)
    k = np.maximum(1, np.ceil(emax / spacing).astype(int))
    P, I = [], []
    for kk in np.unique(k):
        sel = np.where(k == kk)[0]
        ii, jj = np.meshgrid(np.arange(kk + 1), np.arange(kk + 1), indexing="ij")
        m = (ii + jj) <= kk
        u, v = ii[m] / kk, jj[m] / kk
        if kk > 1:  # nudge off shared edges so each point has a unique owner
            u = u * (1 - 1e-6) + 1e-7; v = v * (1 - 1e-6) + 1e-7
        p = a[sel][:, None] + u[None, :, None] * (b - a)[sel][:, None] + v[None, :, None] * (c - a)[sel][:, None]
        P.append(p.reshape(-1, 3)); I.append(np.repeat(sel, len(u)))
    return np.vstack(P), np.concatenate(I), area


def exterior_area(tri, pitch, seal_mm):
    normals = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    nl = np.linalg.norm(normals, axis=1)
    normals = normals / np.where(nl == 0, 1, nl)[:, None]
    pts, idx, area = sample_triangles(tri, pitch * 0.5)
    pad = int(np.ceil(seal_mm / pitch)) + 4
    lo = pts.min(0) - pad * pitch
    shape = np.ceil((pts.max(0) + pad * pitch - lo) / pitch).astype(int) + 1
    occ = np.zeros(shape, bool)
    ijk = np.floor((pts - lo) / pitch).astype(int)
    occ[ijk[:, 0], ijk[:, 1], ijk[:, 2]] = True
    r = max(1, int(round(seal_mm / pitch)))
    ball = ndimage.generate_binary_structure(3, 1)
    grown = ndimage.binary_dilation(occ, structure=ball, iterations=r)   # thicken skin: seals seams < ~2*seal_mm
    filled = ndimage.binary_fill_holes(grown)                             # fill everything enclosed
    solid = ndimage.binary_erosion(filled, structure=ball, iterations=r, border_value=0) | occ  # thin back
    exterior = ~solid
    hit = np.zeros(len(pts), bool)
    for sgn in (1, -1):
        q = pts + sgn * normals[idx] * (1.5 * pitch)
        qi = np.clip(np.floor((q - lo) / pitch).astype(int), 0, np.array(shape) - 1)
        hit |= exterior[qi[:, 0], qi[:, 1], qi[:, 2]]
    frac = np.bincount(idx, weights=hit, minlength=len(tri)) / np.bincount(idx, minlength=len(tri))
    return float((area * frac).sum()), frac, area, pts[hit]


def fib_dirs(n):
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    th = np.pi * (1 + 5 ** 0.5) * i
    return np.stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)], 1)


def silhouette_areas(pts, dirs, res):
    """Shadow area (mm^2) of a point-sampled surface for each direction."""
    out = []
    for d in dirs:
        u = np.cross(d, [1, 0, 0] if abs(d[0]) < 0.9 else [0, 1, 0]); u /= np.linalg.norm(u)
        v = np.cross(d, u)
        P = np.stack([pts @ u, pts @ v], 1)
        g = np.floor((P - P.min(0)) / res).astype(int)
        img = np.zeros(g.max(0) + 1, bool)
        img[g[:, 0], g[:, 1]] = True
        img = ndimage.binary_closing(img, iterations=1)
        img = ndimage.binary_fill_holes(img) if False else img
        out.append(img.sum() * res * res)
    return np.array(out)
