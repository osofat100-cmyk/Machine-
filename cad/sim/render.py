"""Shading, ground shadow, and the static/dynamic split that makes the
whole thing fast enough to animate.

The expensive part of a frame is not the arm. It is the ground plane:
a handful of triangles that each cover a quarter of the screen, scan
converted again and again to produce exactly the same pixels. So the
camera is fixed, the floor and the fixtures are shaded **once** into a
cached layer with its own depth buffer, and each frame rasterises only
what actually moves -- the fifteen arm instances and the payload --
compositing them against that cached depth.

Everything is lit in linear space: a key light, a cool fill, a rim, a
hemisphere ambient, Blinn-Phong highlights, and a projected soft shadow
on the floor. sRGB encoding happens once, at the end.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import raster as R
from .scene import MAT_FLOOR, MAT_METAL, Scene

SUN = np.array([-0.40, -0.66, 0.64]);   SUN /= np.linalg.norm(SUN)
FILL = np.array([0.76, 0.34, 0.24]);    FILL /= np.linalg.norm(FILL)
RIM = np.array([0.18, 0.88, -0.06]);    RIM /= np.linalg.norm(RIM)

SUN_COL = R.srgb_to_linear([1.00, 0.97, 0.92]) * 1.95
FILL_COL = R.srgb_to_linear([0.58, 0.68, 0.88]) * 0.55
RIM_COL = R.srgb_to_linear([0.78, 0.88, 1.00]) * 0.50
SKY = R.srgb_to_linear([0.52, 0.58, 0.68]) * 0.50
GND_BOUNCE = R.srgb_to_linear([0.30, 0.26, 0.22]) * 0.34

BG_TOP = R.srgb_to_linear([0.043, 0.055, 0.075])
BG_BOT = R.srgb_to_linear([0.145, 0.165, 0.196])

SHADOW_STRENGTH = 0.68
FLOOR_FADE = 1900.0


def background(w: int, h: int) -> np.ndarray:
    t = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None, None]
    return ((BG_TOP * (1 - t) + BG_BOT * t)
            * np.ones((h, w, 1), np.float32)).reshape(-1, 3)


def _grid(world: np.ndarray, base: np.ndarray):
    """Procedural floor: a 100 mm grid with every fifth line brighter,
    faded out with distance so the plane's own edge never shows."""
    col = np.repeat(np.asarray(base, np.float64)[None, :], len(world), axis=0)
    for pitch, gain, wide in ((100.0, 1.5, 1.2), (500.0, 4.0, 1.9)):
        d = np.abs((world[:, :2] + pitch / 2) % pitch - pitch / 2)
        col += base * gain * np.exp(-(d / wide) ** 2).max(axis=1)[:, None]
    r = np.linalg.norm(world[:, :2], axis=1)
    # a pool of light around the machine, and a fade that reaches zero
    # before the plane's own edge could ever show
    col *= 0.45 + 0.75 * np.exp(-(r / 900.0) ** 2)[:, None]
    t = np.clip(1.0 - r / FLOOR_FADE, 0.0, 1.0)
    return col, t * t * (3.0 - 2.0 * t)


def shade(scene: Scene, cam: R.Camera, tribuf, hit, bary):
    """Linear-light colour for every covered pixel."""
    tid = tribuf[hit]
    tri = scene.tris[tid]
    b = bary[:, :, None]
    n = (scene.normals[tri[:, 0]] * b[:, 0]
         + scene.normals[tri[:, 1]] * b[:, 1]
         + scene.normals[tri[:, 2]] * b[:, 2]).astype(np.float64)
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
    pos = (scene.verts[tri[:, 0]] * b[:, 0]
           + scene.verts[tri[:, 1]] * b[:, 1]
           + scene.verts[tri[:, 2]] * b[:, 2])

    view = cam.eye - pos
    view /= np.maximum(np.linalg.norm(view, axis=1, keepdims=True), 1e-9)
    # A tessellation that has been through boolean cuts can hand back
    # inconsistently wound faces. Face the normal at the camera rather
    # than trusting the winding; culling on it would punch holes.
    n = np.where((n * view).sum(1, keepdims=True) < 0, -n, n)

    mat = scene.tri_mat[tid]
    base = scene.tri_color[tid].astype(np.float64)
    alpha = np.ones(len(hit))
    floor = mat == MAT_FLOOR
    if floor.any():
        base[floor], alpha[floor] = _grid(pos[floor], scene.tri_color[tid][floor][0])

    hemi = 0.5 + 0.5 * n[:, 2:3]
    amb = SKY * hemi + GND_BOUNCE * (1.0 - hemi)
    diff = (np.clip(n @ SUN, 0, None)[:, None] * SUN_COL
            + np.clip(n @ FILL, 0, None)[:, None] * FILL_COL
            + np.clip(n @ RIM, 0, None)[:, None] * RIM_COL)
    col = base * (amb + diff)

    metal = (mat == MAT_METAL)[:, None]
    hv = SUN + view
    hv /= np.maximum(np.linalg.norm(hv, axis=1, keepdims=True), 1e-9)
    ndh = np.clip((n * hv).sum(1, keepdims=True), 0, 1)
    col += np.where(metal, np.power(ndh, 52.0) * 0.34,
                    np.power(ndh, 14.0) * 0.05) * SUN_COL
    fres = np.power(1.0 - np.clip((n * view).sum(1, keepdims=True), 0, 1), 4.5)
    col += np.where(floor[:, None], 0.0, fres * SKY * 1.5)
    return col, alpha, floor


@dataclass
class Static:
    """The parts of the frame that never change: floor and fixtures."""
    rgb: np.ndarray          # (W*H, 3) linear
    invz: np.ndarray         # (W*H,) float32, 0 = background
    floor: np.ndarray        # (W*H,) float, 1 = solid floor
    w: int
    h: int


def bake(scene: Scene, cam: R.Camera, w: int, h: int,
         casters: tuple[np.ndarray, np.ndarray] | None = None) -> Static:
    rgb = background(w, h).astype(np.float64)
    tribuf, hit, bary, invz = R.depth_and_inv(scene.verts, scene.tris, cam, w, h)
    floor_mask = np.zeros(w * h, np.float64)
    if hit.size:
        col, alpha, floor = shade(scene, cam, tribuf, hit, bary)
        a = alpha[:, None]
        rgb[hit] = col * a + rgb[hit] * (1.0 - a)
        # Weight the floor mask by that same alpha: past the fade the
        # floor *is* the background, and a shadow must not print on it.
        floor_mask[hit] = floor * alpha
    st = Static(rgb, invz, floor_mask, w, h)
    if casters is not None:
        cast_shadow(st, cam, casters, scale=2)
    return st


def project_to_floor(verts: np.ndarray) -> np.ndarray:
    """Slide every vertex down the light direction onto z = 0."""
    out = verts - np.outer(verts[:, 2] / SUN[2], SUN)
    out[:, 2] = 0.30                      # a hair above the floor
    return out


def cast_shadow(st: Static, cam: R.Camera, casters, scale: int = 2,
                out: np.ndarray | None = None, blocked=None):
    """Darken the floor where the casters block the key light.

    Rasterised at 1/scale and blurred on the way back up: a shadow edge
    is soft anyway, so full resolution buys nothing but time.
    """
    verts, tris = casters
    sw, sh = st.w // scale, st.h // scale
    cam_s = R.Camera(cam.eye, cam.target, cam.up, cam.fov, cam.near)
    mask = R.coverage(project_to_floor(verts), tris, cam_s, sw, sh)
    mask = _blur(mask, max(1, int(round(3 / scale)) + 1))
    mask = np.repeat(np.repeat(mask, scale, axis=0), scale, axis=1)
    mask = _fit(mask, st.h, st.w).reshape(-1)
    live = st.floor if blocked is None else (st.floor * ~blocked)
    target = st.rgb if out is None else out
    target *= (1.0 - SHADOW_STRENGTH * mask * live)[:, None]
    return target


def _fit(a: np.ndarray, h: int, w: int) -> np.ndarray:
    if a.shape == (h, w):
        return a
    out = np.zeros((h, w), a.dtype)
    out[:a.shape[0], :a.shape[1]] = a[:h, :w]
    return out


def frame(st: Static, dynamic: Scene, cam: R.Camera, ss: int,
          casters=None) -> np.ndarray:
    """Composite one animated frame over the cached static layer."""
    w, h = st.w, st.h
    rgb = st.rgb.copy()

    tribuf, hit, bary, invz = R.depth_and_inv(dynamic.verts, dynamic.tris,
                                              cam, w, h)
    covered = np.zeros(w * h, bool)
    covered[hit] = True
    if casters is not None:
        cast_shadow(st, cam, casters, scale=2, out=rgb, blocked=covered)

    if hit.size:
        win = invz[hit] > st.invz[hit]
        sel = hit[win]
        col, _, _ = shade(dynamic, cam, tribuf, hit, bary)
        rgb[sel] = col[win]

    img = R.box_downsample(rgb.reshape(h, w, 3), ss)
    return R.linear_to_srgb(tonemap(img))


def tonemap(x: np.ndarray, exposure: float = 1.05) -> np.ndarray:
    """Filmic curve (the Narkowicz ACES fit). Downsample in linear light
    first, tone map second: averaging clipped pixels loses the highlight
    rolloff that makes a specular edge read as metal."""
    x = np.maximum(x * exposure, 0.0)
    return np.clip((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14),
                   0.0, 1.0)


def _box1d(a: np.ndarray, radius: int, axis: int) -> np.ndarray:
    k = 2 * radius + 1
    pad = [(radius + 1, radius) if i == axis else (0, 0) for i in range(a.ndim)]
    c = np.cumsum(np.pad(a, pad, mode="edge"), axis=axis)
    n = a.shape[axis]
    return (np.take(c, np.arange(k, k + n), axis=axis)
            - np.take(c, np.arange(0, n), axis=axis)) / k


def _blur(mask: np.ndarray, radius: int) -> np.ndarray:
    """Separable box blur run twice -- a cheap stand-in for the soft edge
    a real area light would give."""
    if radius < 1:
        return mask
    out = mask
    for _ in range(2):
        out = _box1d(_box1d(out, radius, 0), radius, 1)
    return np.clip(out, 0.0, 1.0)
