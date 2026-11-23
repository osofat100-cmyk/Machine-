"""Where can a solar sheet or tile physically go on the measured earbud / case?

1. Build a clean, closed outer-skin mesh: voxel solid (same pipeline as exterior.py) ->
   light Gaussian smoothing -> marching cubes.
2. Principal curvatures k1, k2 at every vertex from a least-squares quadric fit over a
   neighbourhood of radius rho (Monge patch: E,F,G / L,M,N fundamental forms).
3. Coverage rules (pure geometry):
   - bending: a sheet with minimum bend radius r_min fits only where 1/|k|max >= r_min
   - Gauss: a flat tile of size L forced onto Gaussian curvature K needs in-plane strain
       eps = L^2 |K| / 24      (geodesic circle: C = 2*pi*rho*(1 - K rho^2 / 6), rho = L/2)
     so it fits only where |K| <= 24 eps / L^2
"""
import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree
from skimage import measure
import trimesh
from exterior import sample_triangles


def outer_skin_mesh(tri, pitch, seal_mm=0.3, sigma_vox=1.0):
    pts, idx, _ = sample_triangles(tri, pitch * 0.5)
    pad = 10
    lo = pts.min(0) - pad * pitch
    shape = np.ceil((pts.max(0) + pad * pitch - lo) / pitch).astype(int) + 1
    occ = np.zeros(shape, bool)
    ijk = np.floor((pts - lo) / pitch).astype(int)
    occ[ijk[:, 0], ijk[:, 1], ijk[:, 2]] = True
    r = max(1, int(round(seal_mm / pitch)))
    b = ndimage.generate_binary_structure(3, 1)
    solid = ndimage.binary_erosion(ndimage.binary_fill_holes(ndimage.binary_dilation(occ, b, iterations=r)), b, iterations=r) | occ
    f = ndimage.gaussian_filter(solid.astype(np.float32), sigma_vox)
    v, faces, _, _ = measure.marching_cubes(f, 0.5, spacing=(pitch,) * 3)
    m = trimesh.Trimesh(v + lo, faces, process=True)
    m.fix_normals()
    return m


def principal_curvatures(m, rho):
    V, N = m.vertices, m.vertex_normals
    tree = cKDTree(V)
    k1 = np.zeros(len(V)); k2 = np.zeros(len(V))
    for start in range(0, len(V), 4000):
        sl = range(start, min(start + 4000, len(V)))
        nbrs = tree.query_ball_point(V[start:start + 4000], rho)
        for i, nb in zip(sl, nbrs):
            n = N[i]
            t = np.cross(n, [1, 0, 0] if abs(n[0]) < 0.9 else [0, 1, 0]); t /= np.linalg.norm(t)
            s = np.cross(n, t)
            d = V[nb] - V[i]
            x, y, z = d @ t, d @ s, d @ n
            A = np.stack([x * x, x * y, y * y, x, y, np.ones_like(x)], 1)
            if len(x) < 8:
                continue
            a, bxy, c, fx, fy, _ = np.linalg.lstsq(A, z, rcond=None)[0]
            fxx, fxy, fyy = 2 * a, bxy, 2 * c
            w = np.sqrt(1 + fx * fx + fy * fy)
            E, F, G = 1 + fx * fx, fx * fy, 1 + fy * fy
            L, M, Nn = fxx / w, fxy / w, fyy / w
            K = (L * Nn - M * M) / (E * G - F * F)
            H = (E * Nn - 2 * F * M + G * L) / (2 * (E * G - F * F))
            disc = np.sqrt(max(H * H - K, 0))
            k1[i], k2[i] = H + disc, H - disc
    return k1, k2


def vertex_area(m):
    va = np.zeros(len(m.vertices))
    np.add.at(va, m.faces.ravel(), np.repeat(m.area_faces / 3, 3))
    return va


def coverage_tables(k1, k2, va, mask=None):
    if mask is None:
        mask = np.ones(len(va), bool)
    A = va[mask].sum()
    kmax = np.maximum(np.abs(k1), np.abs(k2))[mask]
    K = np.abs(k1 * k2)[mask]
    w = va[mask]
    bend = {r: float(w[1 / np.maximum(kmax, 1e-9) >= r].sum() / A) for r in (0.5, 1, 2, 3, 5, 10, 20, 50)}
    tiles = {}
    for L in (1, 2, 3, 5, 10, 20):
        tiles[L] = {eps: float(w[K <= 24 * eps / L ** 2].sum() / A) for eps in (0.001, 0.005, 0.01, 0.02, 0.05, 0.2)}
    return A, bend, tiles
