"""Printer tolerance coupon (generic geometry, no JBL data): print it before the real shell.

Part A: plate with the seal groove (1.10 x 1.20), a row of test holes (0.7 0.8 0.9 1.3 1.4 1.6 2.2 mm) and an
        M1.2 insert boss (OD 3.2, Ø1.6 x 2.2 hole).
Part B: plate with the matching tongue (0.80 x 0.60) - it must drop into A's groove with a little play and leave
        a 0.6 mm gap for the gasket.  Also a 1.0 mm and a 0.8 mm wall to check warping.
Usage: python3 shell_coupon.py <out dir> [pitch]
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import sdf

out = sys.argv[1]; p = float(sys.argv[2]) if len(sys.argv) > 2 else 0.05
os.makedirs(out, exist_ok=True)
I = np.eye(3)

# Part A
g = sdf.Grid([-17, -8, -0.5], [17, 8, 5.0], p)
A = np.full(g.shape, 1e3, np.float32)
sdf.union(A, sdf.box(g, np.array([0, 0, 1.5]), I, [16, 7, 1.5]))                      # 32 x 14 x 3 plate
sdf.subtract(A, sdf.box(g, np.array([0, 3.5, 3.0 - 0.6]), I, [14, 0.55, 0.6 + 0.01]))  # groove 1.10 wide, 1.20 deep
for i, d in enumerate([0.7, 0.8, 0.9, 1.3, 1.4, 1.6, 2.2]):
    sdf.subtract(A, sdf.cylinder(g, np.array([-12 + 4 * i, -3.0, 1.5]), [0, 0, 1], d / 2, 2.0))
sdf.union(A, sdf.cylinder(g, np.array([13.0, -3.0, 4.0]), [0, 0, 1], 1.6, 1.0))         # insert boss on top
sdf.subtract(A, sdf.cylinder(g, np.array([13.0, -3.0, 4.9 - 1.1]), [0, 0, 1], 0.8, 1.1 + 0.01))
sdf.mesh(A, g).export(os.path.join(out, "coupon_A_groove_holes.stl"))

# Part B
g = sdf.Grid([-17, -8, -0.5], [17, 8, 6.0], p)
B = np.full(g.shape, 1e3, np.float32)
sdf.union(B, sdf.box(g, np.array([0, 0, 1.0]), I, [16, 7, 1.0]))                      # 32 x 14 x 2 plate
sdf.union(B, sdf.box(g, np.array([0, 3.5, 2.0 + 0.3]), I, [14, 0.40, 0.3 + 0.01]))     # tongue 0.80 x 0.60 on top
sdf.union(B, sdf.box(g, np.array([-8, -3.5, 2.0 + 2.0]), I, [6, 0.5, 2.0]))            # 1.0 mm wall, 4 mm tall
sdf.union(B, sdf.box(g, np.array([8, -3.5, 2.0 + 2.0]), I, [6, 0.4, 2.0]))             # 0.8 mm wall, 4 mm tall
sdf.mesh(B, g).export(os.path.join(out, "coupon_B_tongue_walls.stl"))
print("coupon written to", out)
