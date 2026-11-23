"""Exact surface-area math for a 3D model (STL/OBJ/GLB/3MF/PLY).

Surface area  S = sum over triangles of 1/2 * |(v1 - v0) x (v2 - v0)|
Lit area from direction d (convex hull): A(d) = sum over faces of max(0, n.d) * area
Cauchy's formula: average shadow area over all directions = S_hull / 4
Usage: python3 -I mesh_area.py <model file> [published H W D in mm]
"""
import sys
import numpy as np
import trimesh

path = sys.argv[1]
pub = [float(x) for x in sys.argv[2:5]] if len(sys.argv) >= 5 else None

scene = trimesh.load(path, force="scene")
mesh = scene.to_geometry() if hasattr(scene, "to_geometry") else scene.dump(concatenate=True)

ext = np.sort(mesh.extents)[::-1]
print(f"file: {path}")
print(f"triangles: {len(mesh.faces):,}   watertight: {mesh.is_watertight}")
print(f"model bounding box (model units, sorted): {ext.round(3)}")
print(f"raw surface area (model units^2): {mesh.area:.4f}")

scale = 1.0
if pub:
    p = np.sort(np.array(pub))[::-1]
    ratios = p / ext
    print(f"published dims mm (sorted): {p}   ratio published/model per axis: {ratios.round(4)}")
    scale = float(ratios.mean())
    print(f"uniform scale used = mean ratio = {scale:.5f}  (axis spread {100*(ratios.max()-ratios.min())/scale:.1f}%)")

S = mesh.area * scale**2               # mm^2
hull = mesh.convex_hull
S_hull = hull.area * scale**2
print(f"\nSURFACE AREA (scaled): {S:,.1f} mm^2 = {S/100:.2f} cm^2")
print(f"convex-hull area:      {S_hull:,.1f} mm^2 = {S_hull/100:.2f} cm^2")
if mesh.is_watertight:
    print(f"volume:                {abs(mesh.volume)*scale**3:,.1f} mm^3")

# lit (projected) area from many directions on the sphere (Fibonacci lattice)
n = 20000
i = np.arange(n) + 0.5
phi = np.arccos(1 - 2 * i / n)
theta = np.pi * (1 + 5 ** 0.5) * i
dirs = np.stack([np.cos(theta) * np.sin(phi), np.sin(theta) * np.sin(phi), np.cos(phi)], 1)
fa = hull.area_faces * scale**2
proj = np.clip(dirs @ hull.face_normals.T, 0, None) @ fa   # mm^2 per direction
print(f"lit area, best direction:    {proj.max():,.1f} mm^2 = {proj.max()/100:.2f} cm^2")
print(f"lit area, worst direction:   {proj.min():,.1f} mm^2 = {proj.min()/100:.2f} cm^2")
print(f"lit area, all-direction mean:{proj.mean():,.1f} mm^2 = {proj.mean()/100:.2f} cm^2  (Cauchy check S_hull/4 = {S_hull/4/100:.2f} cm^2)")
