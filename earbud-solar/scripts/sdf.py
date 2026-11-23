"""Small signed-distance-field (SDF) toolkit on a regular voxel grid (negative = inside).

Used to turn JBL's zero-thickness skin into printable solids: build a solid, take its signed distance,
offset it (hollowing), combine with exact primitives (boxes, cylinders, half-spaces), mesh with marching
cubes. Validated by test_sdf.py.
"""
import numpy as np
from scipy import ndimage
from skimage import measure
import trimesh
from exterior import sample_triangles


class Grid:
    """Voxel centres at lo + (i + 0.5) * p."""
    def __init__(self, lo, hi, p):
        self.p = float(p)
        self.lo = np.asarray(lo, float)
        self.shape = tuple(int(n) for n in np.ceil((np.asarray(hi, float) - self.lo) / p).astype(int) + 1)

    def axes(self):
        return [(self.lo[i] + (np.arange(self.shape[i]) + 0.5) * self.p).astype(np.float32) for i in range(3)]

    def xyz(self, sl=(slice(None),) * 3):
        ax = self.axes()
        return np.meshgrid(ax[0][sl[0]], ax[1][sl[1]], ax[2][sl[2]], indexing="ij", sparse=True)

    def index(self, pts):
        return np.floor((np.asarray(pts) - self.lo) / self.p).astype(int)

    def block(self, lo, hi, margin=1.0):
        """Slices covering the world box [lo, hi] (+margin), clipped to the grid."""
        a = np.clip(self.index(np.asarray(lo) - margin), 0, np.array(self.shape) - 1)
        b = np.clip(self.index(np.asarray(hi) + margin) + 1, 1, np.array(self.shape))
        return tuple(slice(int(i), int(j)) for i, j in zip(a, b))

    def sub(self, sl):
        """Grid of a cropped sub-block (slices)."""
        g = Grid.__new__(Grid)
        g.p = self.p
        g.lo = self.lo + np.array([s.indices(n)[0] for s, n in zip(sl, self.shape)]) * self.p
        g.shape = tuple(len(range(*s.indices(n))) for s, n in zip(sl, self.shape))
        return g

    def sample(self, field, pts):
        ijk = np.clip(self.index(pts), 0, np.array(self.shape) - 1)
        return field[ijk[:, 0], ijk[:, 1], ijk[:, 2]]


def solid_from_tris(tri, grid, seal_mm=0.3):
    """Enclosed solid of a (possibly open, multi-part) triangle skin: dilate -> fill -> erode."""
    pts, _, _ = sample_triangles(tri, grid.p * 0.5)
    k = np.all((pts >= grid.lo) & (pts < grid.lo + np.array(grid.shape) * grid.p), axis=1)
    ijk = grid.index(pts[k])
    occ = np.zeros(grid.shape, bool)
    occ[ijk[:, 0], ijk[:, 1], ijk[:, 2]] = True
    r = max(1, int(round(seal_mm / grid.p)))
    b = ndimage.generate_binary_structure(3, 1)
    grown = ndimage.binary_dilation(occ, b, iterations=r)
    return ndimage.binary_erosion(ndimage.binary_fill_holes(grown), b, iterations=r, border_value=0) | occ


def sdf_from_solid(solid, p):
    """Signed distance (mm) of a voxel solid; the surface sits half a voxel outside the solid voxels."""
    d_out = ndimage.distance_transform_edt(~solid).astype(np.float32)
    d_in = ndimage.distance_transform_edt(solid).astype(np.float32)
    return np.where(solid, -(d_in - 0.5), d_out - 0.5).astype(np.float32) * np.float32(p)


def skin_sdf(tri, grid, seal_mm=0.3, sigma_vox=1.0):
    """Signed distance of the solid enclosed by a triangle skin. Voxels touched by the skin are counted as
    solid, which puts the surface +p/2 outside on average; that half-voxel bias is removed here."""
    phi = sdf_from_solid(solid_from_tris(tri, grid, seal_mm), grid.p) + np.float32(0.5 * grid.p)
    return smooth(phi, sigma_vox) if sigma_vox else phi


def redistance(phi, p):
    return sdf_from_solid(phi <= 0, p)


def smooth(phi, sigma_vox=1.0):
    return ndimage.gaussian_filter(phi, sigma_vox).astype(np.float32)


# ---------- exact primitives (evaluated on a sub-block) ----------
def _local(grid, sl, centre, R):
    X, Y, Z = grid.xyz(sl)
    d = [X - centre[0], Y - centre[1], Z - centre[2]]
    return [R[i, 0] * d[0] + R[i, 1] * d[1] + R[i, 2] * d[2] for i in range(3)]


def box(grid, centre, R, half):
    """Box with rows of R as its axes and half-sizes `half`. Returns (slices, sdf block)."""
    ext = np.abs(R.T) @ np.asarray(half)
    sl = grid.block(centre - ext, centre + ext)
    q = [np.abs(c) - h for c, h in zip(_local(grid, sl, centre, R), half)]
    outside = np.sqrt(sum(np.maximum(c, 0) ** 2 for c in q))
    inside = np.minimum(np.maximum(np.maximum(q[0], q[1]), q[2]), 0)
    return sl, (outside + inside).astype(np.float32)


def cylinder(grid, centre, axis, radius, half_len):
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    a = np.cross(axis, [1, 0, 0] if abs(axis[0]) < 0.9 else [0, 1, 0]); a /= np.linalg.norm(a)
    b = np.cross(axis, a)
    R = np.stack([a, b, axis])
    ext = np.abs(R.T) @ np.array([radius, radius, half_len])
    sl = grid.block(centre - ext, centre + ext)
    x, y, z = _local(grid, sl, centre, R)
    dr = np.sqrt(x * x + y * y) - radius
    dz = np.abs(z) - half_len
    outside = np.sqrt(np.maximum(dr, 0) ** 2 + np.maximum(dz, 0) ** 2)
    return sl, (outside + np.minimum(np.maximum(dr, dz), 0)).astype(np.float32)


def halfspace(grid, point, normal):
    """Signed distance to a plane; negative on the side opposite the normal (full grid)."""
    n = np.asarray(normal, float) / np.linalg.norm(normal)
    X, Y, Z = grid.xyz()
    return ((X - point[0]) * n[0] + (Y - point[1]) * n[1] + (Z - point[2]) * n[2]).astype(np.float32)


def union(phi, prim):
    sl, v = prim
    phi[sl] = np.minimum(phi[sl], v)


def subtract(phi, prim):
    sl, v = prim
    phi[sl] = np.maximum(phi[sl], -v)


# ---------- meshing & checks ----------
def mesh(phi, grid, level=0.0):
    v, f, _, _ = measure.marching_cubes(phi, level, spacing=(grid.p,) * 3)
    m = trimesh.Trimesh(v + grid.lo + 0.5 * grid.p, f[:, ::-1], process=True)
    if m.volume < 0:
        m.invert()
    return m


def thin_regions(solid, min_t, p):
    """Voxels of `solid` that vanish under an opening with a ball of diameter min_t (= thinner than min_t)."""
    r = max(1, int(round(min_t / 2 / p)))
    ball = np.zeros((2 * r + 1,) * 3, bool)
    g = np.indices(ball.shape) - r
    ball[(g ** 2).sum(0) <= r * r] = True
    return solid & ~ndimage.binary_opening(solid, structure=ball)


def thin_walls(solid, min_t, p):
    """Voxels of genuinely thin material (sheets, fins, needles thinner than min_t).
    An opening also shaves every sharp convex edge of a thick part; those slivers lie right next to
    material that survives the opening.  Material of a real thin wall has no survivor nearby, so only
    removed voxels farther than (ball radius + 1 voxel) from the opened solid are reported."""
    r = max(1, int(round(min_t / 2 / p)))
    ball = np.zeros((2 * r + 1,) * 3, bool)
    g = np.indices(ball.shape) - r
    ball[(g ** 2).sum(0) <= r * r] = True
    opened = ndimage.binary_opening(solid, structure=ball)
    far = ndimage.distance_transform_edt(~opened) > r + 1
    return solid & ~opened & far
