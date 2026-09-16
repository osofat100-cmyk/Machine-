"""Turn the repo's CAD assembly into triangles, once, and re-place them.

`assembly.build_assembly` rebuilds all fourteen solids every time it is
called -- about 1.3 s. Four hundred frames of that is nine minutes of
rebuilding geometry that never changes, which is also the wrong thing to
do on principle: the assembly docstring is explicit that driving the pose
"is a matter of changing `ArmParams.joints` -- no geometry is rebuilt,
only re-placed".

So this module does what the docstring describes. The fourteen prototypes
are tessellated once. Per frame, the *placement* half of `build_assembly`
is re-run -- the real function, with the real chain -- against stand-in
solids, purely to read back the `Location` of each of the fifteen
instances. Those locations then move the cached triangles.

The consequence worth stating: nothing here re-derives the kinematics.
If `assembly.py` changes how a part is mated, this animation changes with
it, because it is calling that code, not copying it.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from build123d import Box, Location

from robot_arm import assembly as A
from robot_arm import parts as P
from robot_arm.params import ArmParams

from .raster import hex_to_linear

# material ids understood by shade()
MAT_METAL = 0
MAT_FLOOR = 1
MAT_MATTE = 2


@dataclass
class Mesh:
    verts: np.ndarray        # (n, 3) float32
    normals: np.ndarray      # (n, 3) float32, smooth within a BRep face
    tris: np.ndarray         # (m, 3) int32
    color: np.ndarray        # (3,) linear rgb
    material: int = MAT_METAL


@dataclass
class Scene:
    verts: np.ndarray
    normals: np.ndarray
    tris: np.ndarray
    tri_color: np.ndarray    # (m, 3)
    tri_mat: np.ndarray      # (m,)

    @property
    def n_tris(self) -> int:
        return len(self.tris)


def merge(meshes: list[Mesh]) -> Scene:
    verts, normals, tris, cols, mats = [], [], [], [], []
    off = 0
    for m in meshes:
        verts.append(m.verts)
        normals.append(m.normals)
        tris.append(m.tris + off)
        cols.append(np.repeat(m.color[None, :], len(m.tris), axis=0))
        mats.append(np.full(len(m.tris), m.material, np.int32))
        off += len(m.verts)
    return Scene(
        np.concatenate(verts).astype(np.float64),
        np.concatenate(normals).astype(np.float32),
        np.concatenate(tris).astype(np.int64),
        np.concatenate(cols).astype(np.float32),
        np.concatenate(mats),
    )


# --------------------------------------------------------------------
# tessellation
# --------------------------------------------------------------------
def _vertex_normals(verts: np.ndarray, tris: np.ndarray) -> np.ndarray:
    """Area-weighted vertex normals.

    OCCT triangulates each BRep face separately and build123d concatenates
    the results, so vertices are shared *within* a face and duplicated
    *across* faces. Averaging therefore smooths a cylinder along its
    circumference while leaving every real edge crisp -- which is the
    behaviour you want, for free.
    """
    fn = np.cross(verts[tris[:, 1]] - verts[tris[:, 0]],
                  verts[tris[:, 2]] - verts[tris[:, 0]])
    vn = np.zeros_like(verts)
    for k in range(3):
        np.add.at(vn, tris[:, k], fn)
    n = np.linalg.norm(vn, axis=1, keepdims=True)
    return (vn / np.where(n < 1e-12, 1.0, n)).astype(np.float32)


def tessellate_parts(p: ArmParams, deflection=0.3, angular=0.22) -> dict[str, Mesh]:
    """Tessellate the fourteen prototypes once, in their own frames."""
    lib = P.build_all(p)
    out: dict[str, Mesh] = {}
    for key, part in lib.items():
        vs, ts = part.tessellate(deflection, angular)
        verts = np.array([[v.X, v.Y, v.Z] for v in vs], np.float64)
        tris = np.array(ts, np.int64).reshape(-1, 3)
        out[key] = Mesh(verts, _vertex_normals(verts, tris), tris,
                        hex_to_linear(A._COLORS[key]), MAT_METAL)
    return out


# --------------------------------------------------------------------
# placements, read back out of the repo's own assembly code
# --------------------------------------------------------------------
def _stub_library(p: ArmParams) -> dict:
    """Stand-in solids: same keys, negligible cost to move."""
    return {k: Box(1, 1, 1) for k in A._COLORS}


def placements(p: ArmParams) -> list[tuple[str, str, np.ndarray]]:
    """(part key, instance label, 4x4 world matrix) for all fifteen
    instances.

    Calls the real `build_assembly`, with the geometry swapped out. The
    placement arithmetic -- the joint chain, the 180-degree flip on the
    elbow yoke, the gripper's mirrored jaw, the four actuator drops -- is
    the repo's, untouched.
    """
    real, P.build_all = P.build_all, _stub_library
    try:
        asm = A.build_assembly(p)
    finally:
        P.build_all = real
    return [(c.label.split(".")[0], c.label, loc_matrix(c.location))
            for c in asm.children]


def loc_matrix(loc: Location) -> np.ndarray:
    t = loc.wrapped.Transformation()
    m = np.eye(4)
    for i in range(3):
        for j in range(4):
            m[i, j] = t.Value(i + 1, j + 1)
    return m


def transform(mesh: Mesh, m: np.ndarray) -> Mesh:
    r, t = m[:3, :3], m[:3, 3]
    return Mesh(mesh.verts @ r.T + t,
                (mesh.normals @ r.T).astype(np.float32),
                mesh.tris, mesh.color, mesh.material)


def arm_instances(p: ArmParams, protos: dict[str, Mesh]) -> list[tuple[str, Mesh]]:
    return [(label, transform(protos[key], m))
            for key, label, m in placements(p)]


def arm_meshes(p: ArmParams, protos: dict[str, Mesh]) -> list[Mesh]:
    return [m for _, m in arm_instances(p, protos)]


# --------------------------------------------------------------------
# scenery -- not part of the CAD model; context for the motion
# --------------------------------------------------------------------
def box_mesh(size, center, color, material=MAT_MATTE, m=None) -> Mesh:
    sx, sy, sz = (np.asarray(size, float) / 2.0)
    c = np.array([[-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
                  [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]], float)
    corners = c * [sx, sy, sz]
    quads = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
             (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    verts, normals, tris = [], [], []
    for q in quads:
        base = len(verts)
        pts = corners[list(q)]
        n = np.cross(pts[1] - pts[0], pts[2] - pts[0])
        n = n / np.linalg.norm(n)
        verts.extend(pts)
        normals.extend([n] * 4)
        tris.extend([(base, base + 1, base + 2), (base, base + 2, base + 3)])
    verts = np.array(verts) + np.asarray(center, float)
    mesh = Mesh(verts, np.array(normals, np.float32),
                np.array(tris, np.int64), np.asarray(color, np.float32), material)
    return transform(mesh, m) if m is not None else mesh


def floor_mesh(half=1500.0, n=26, color=None) -> Mesh:
    """A finite ground plane, subdivided so no single triangle covers the
    whole frame (the rasteriser buckets by bounding box; one giant
    triangle is the pathological case). The grid itself is procedural,
    drawn from the interpolated world position at shading time."""
    g = np.linspace(-half, half, n + 1)
    gx, gy = np.meshgrid(g, g, indexing="ij")
    verts = np.stack([gx.ravel(), gy.ravel(), np.zeros(gx.size)], axis=1)
    idx = np.arange((n + 1) ** 2).reshape(n + 1, n + 1)
    a, b = idx[:-1, :-1].ravel(), idx[1:, :-1].ravel()
    c, d = idx[1:, 1:].ravel(), idx[:-1, 1:].ravel()
    tris = np.concatenate([np.stack([a, b, c], 1), np.stack([a, c, d], 1)])
    normals = np.tile(np.array([0, 0, 1], np.float32), (len(verts), 1))
    if color is None:
        color = hex_to_linear("#2b3038")
    return Mesh(verts, normals, tris, np.asarray(color, np.float32),
                MAT_FLOOR)


def measure_jaw_gap(pose, protos) -> float:
    """The claw's opening, measured off the placed triangles.

    `kinematics.jaw_gap` is arithmetic *about* geometry that lives in
    `parts.grabber_jaw`, and a summary can be wrong. This model's was,
    once, by 2 mm: the jaws stood a millimetre clear of a part the
    program reported as gripped, and every check that asked the
    arithmetic agreed with it.

    So this asks the triangles instead. It transforms the placed jaws
    back into the J6 frame, takes the band of them level with the grip
    ridges, and reports twice the closest the mesh comes to the tool
    axis -- which is the widest box the claw is actually closed on.

    Measured *in each jaw's own plane*, not as a three-dimensional
    radius. A ridge is a cylinder lying across its finger, and its
    closest line to the tool axis runs along the middle of it, where a
    mesh has no vertices at all -- only at the ends, 9 mm out to either
    side. Taking `hypot(x, y)` there answers a question nobody asked and
    reports a 32 mm grip as 36.7 mm, which is how this was found.
    """
    from .kinematics import jaw_ridge
    inv = np.linalg.inv(loc_matrix(A.joint_frames(pose).j6))
    _, ridge_z = jaw_ridge(pose, pose.grab_open)
    near = np.inf
    for label, mesh in arm_instances(pose, protos):
        if not label.startswith("10_grabber_jaw"):
            continue
        i = int(label.rsplit(".", 1)[1]) - 1
        a = 2.0 * np.pi * i / pose.grab_jaws
        radial = np.array([np.cos(a), np.sin(a), 0.0])
        local = (inv[:3, :3] @ mesh.verts.T).T + inv[:3, 3]
        band = local[np.abs(local[:, 2] - ridge_z) < 0.6]
        if band.size:
            near = min(near, float((band @ radial).min()))
    return 2.0 * near
