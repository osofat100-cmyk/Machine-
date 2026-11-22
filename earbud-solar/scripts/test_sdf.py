"""Checks for sdf.py (run: python3 test_sdf.py). Exits non-zero on failure."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, trimesh
import sdf

P = 0.1
ok = True


def check(name, value, target, tol):
    global ok
    good = abs(value - target) <= tol
    ok &= good
    print(f"{'PASS' if good else 'FAIL'}  {name}: {value:.4f} (target {target} +/- {tol})")


# 1. hollow sphere R10, wall 1.1 -> outer R 10.00, inner R 8.90
g = sdf.Grid([-11.5] * 3, [11.5] * 3, P)
sph = trimesh.creation.icosphere(subdivisions=6, radius=10.0)
phi = sdf.skin_sdf(sph.triangles, g)
outer = sdf.mesh(phi, g)
inner = sdf.mesh(phi + 1.1, g)
check("hollow sphere outer radius", np.linalg.norm(outer.vertices, axis=1).mean(), 10.0, 0.03)
check("hollow sphere inner radius", np.linalg.norm(inner.vertices, axis=1).mean(), 8.9, 0.03)
shell = (phi <= 0) & (phi > -1.1)
thin = sdf.thin_regions(shell, 0.8, P)
check("1.1 mm shell has no region thinner than 0.8 mm (share)", thin.sum() / shell.sum(), 0.0, 0.002)

# 2. exact flat seat: box capped by a plane -> top vertices exactly on the plane
g2 = sdf.Grid([-6, -6, -6], [6, 6, 6], P)
phi2 = np.full(g2.shape, 1e3, np.float32)
sdf.union(phi2, sdf.box(g2, np.zeros(3), np.eye(3), [4, 4, 4]))
z0 = 1.234
phi2 = np.maximum(phi2, sdf.halfspace(g2, [0, 0, z0], [0, 0, 1]))
m2 = sdf.mesh(phi2, g2)
v2 = m2.vertices
top = v2[(np.abs(v2[:, 2] - z0) < 0.05) & (np.abs(v2[:, 0]) < 3.5) & (np.abs(v2[:, 1]) < 3.5)]   # seat interior
check("flat seat plane RMS (mm)", float(np.sqrt(((top[:, 2] - z0) ** 2).mean())), 0.0, 0.001)

# 3. tongue / groove clearance 0.15 mm (groove 1.10 wide, tongue 0.80 wide, centred)
g3 = sdf.Grid([-4, -4, -3], [4, 4, 3], P / 2)
groove = sdf.box(g3, np.array([0, 0, 0.0]), np.eye(3), [0.55, 3, 1.2])
tongue = sdf.box(g3, np.array([0, 0, 0.0]), np.eye(3), [0.40, 3, 0.6])
pts = np.c_[np.full(200, 0.40), np.linspace(-2, 2, 200), np.zeros(200)]   # points on the tongue's side face
gfull = np.full(g3.shape, 1e3, np.float32); sdf.union(gfull, groove)
d = -g3.sample(gfull, pts)                      # depth of tongue face inside groove cavity = clearance
check("tongue face to groove wall, measured on the field (mm)", float(d.mean()), 0.15, 0.03)

print("ALL PASS" if ok else "SOME CHECKS FAILED")
sys.exit(0 if ok else 1)
