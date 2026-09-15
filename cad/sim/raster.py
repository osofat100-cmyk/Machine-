"""A software rasteriser: triangles in, a shaded image out.

There is no GPU, no display and no OpenGL in the container this runs in,
so the renderer is written from scratch on top of numpy. It is a real
z-buffered rasteriser -- not a painter's-algorithm depth sort -- because
a robot arm folds back over itself and a sorted-polygon renderer gets
those overlaps wrong in exactly the poses that matter.

Design notes:

* **No backface culling.** A CAD tessellation that has been through
  boolean cuts can carry inconsistently wound faces; culling on winding
  would punch holes in the model. Instead every triangle is drawn and the
  shading normal is flipped toward the camera, which is robust to
  whatever orientation OCCT hands over.
* **Perspective-correct interpolation** for normals and world positions,
  so shading does not swim across large triangles.
* **Bucketed, vectorised scan conversion.** Triangles are grouped by
  bounding-box size and whole groups are converted at once; a per-triangle
  Python loop over ~44k triangles a frame would dominate the runtime.
* **Linear-light shading**, sRGB-encoded at the very end.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


# --------------------------------------------------------------------
# camera
# --------------------------------------------------------------------
@dataclass
class Camera:
    eye: np.ndarray
    target: np.ndarray
    up: np.ndarray
    fov: float = 32.0          # vertical field of view, degrees
    near: float = 1.0          # mm; nothing closer is drawn

    @property
    def basis(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        fwd = self.target - self.eye
        fwd = fwd / np.linalg.norm(fwd)
        right = np.cross(fwd, self.up)
        right = right / np.linalg.norm(right)
        up = np.cross(right, fwd)
        return right, up, fwd


def look(eye, target, up=(0.0, 0.0, 1.0), fov=32.0) -> Camera:
    return Camera(np.asarray(eye, float), np.asarray(target, float),
                  np.asarray(up, float), float(fov))


def fit(points: np.ndarray, direction, w: int, h: int, fov=29.0,
        margins=(0.05, 0.05, 0.10, 0.14), up=(0.0, 0.0, 1.0)) -> Camera:
    """Place the camera so everything that will ever be on screen, is.

    Framing a robot arm by eye is a trap: the pose that overflows the
    frame is usually the one you were not looking at when you picked the
    numbers. So the caller hands over every vertex the arm visits across
    the whole program, and the distance along a fixed viewing direction
    is bisected until all of it lands inside the frame with a margin.
    """
    pts = np.asarray(points, float).reshape(-1, 3)
    lo, hi = pts.min(axis=0), pts.max(axis=0)
    d = np.asarray(direction, float)
    d = d / np.linalg.norm(d)
    span = float(np.linalg.norm(hi - lo))
    # Aim a little below centre: the margins are asymmetric because the
    # overlay is, and the bisection only moves the camera in and out.
    target = (lo + hi) / 2.0
    target[2] -= (hi[2] - lo[2]) * 0.06

    ml, mr, mt, mb = margins          # the overlay lives in the margins

    def inside(dist: float) -> bool:
        cam = Camera(target + d * dist, target, np.asarray(up, float), fov)
        sx, sy, zc = project(pts, cam, w, h)
        if (zc <= cam.near).any():
            return False
        return bool(sx.min() > ml * w and sx.max() < (1 - mr) * w
                    and sy.min() > mt * h and sy.max() < (1 - mb) * h)

    def bisect() -> float:
        lo_d, hi_d = span * 0.6, span * 12.0
        while not inside(hi_d) and hi_d < span * 400:
            hi_d *= 1.6
        for _ in range(48):
            mid = (lo_d + hi_d) / 2.0
            if inside(mid):
                hi_d = mid
            else:
                lo_d = mid
        return hi_d

    # Bisecting alone fits the content but does not centre it: the
    # camera aims at the middle of the *scene*, which is not where the
    # scene lands once the margins are asymmetric. So aim, measure where
    # it actually fell, slide the aim to correct, and repeat -- each pass
    # lets the next one close in.
    f = (h * 0.5) / np.tan(np.radians(fov) * 0.5)
    dist = bisect()
    for _ in range(4):
        cam = Camera(target + d * dist, target, np.asarray(up, float), fov)
        right, upv, _ = cam.basis
        sx, sy, _ = project(pts, cam, w, h)
        cx, cy = (sx.min() + sx.max()) / 2.0, (sy.min() + sy.max()) / 2.0
        want_x = w * (ml + 1.0 - mr) / 2.0
        want_y = h * (mt + 1.0 - mb) / 2.0
        target = target + right * (-(want_x - cx) * dist / f) \
            + upv * ((want_y - cy) * dist / f)
        dist = bisect()
    return Camera(target + d * dist, target, np.asarray(up, float), fov)


def project(verts: np.ndarray, cam: Camera, w: int, h: int):
    """World points -> (screen x, screen y, camera-space depth)."""
    right, up, fwd = cam.basis
    d = verts - cam.eye
    xc, yc, zc = d @ right, d @ up, d @ fwd
    f = (h * 0.5) / np.tan(np.radians(cam.fov) * 0.5)
    safe = np.where(np.abs(zc) < 1e-9, 1e-9, zc)
    sx = w * 0.5 + f * xc / safe
    sy = h * 0.5 - f * yc / safe
    return sx, sy, zc


# --------------------------------------------------------------------
# scan conversion
# --------------------------------------------------------------------
_CHUNK_PIXELS = 6_000_000      # candidate-fragment budget per numpy batch


def _pow2(n):
    return (1 << np.ceil(np.log2(np.maximum(n, 1))).astype(np.int64))


def _fragments(sx, sy, zc, tris, w, h, near):
    """Every (pixel, 1/depth, triangle) a triangle covers.

    Triangles are bucketed by bounding box and whole buckets are scan
    converted at once. The buckets are *rectangular*: a square bucket
    sized to the longer edge makes a long thin triangle -- which is most
    of a tessellated cylinder -- pay for a box it barely touches.
    """
    x, y, z = sx[tris], sy[tris], zc[tris]

    live = (z > near).all(axis=1)
    x0, y0 = x[:, 0], y[:, 0]
    x1, y1 = x[:, 1], y[:, 1]
    x2, y2 = x[:, 2], y[:, 2]
    area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
    live &= np.abs(area) > 1e-12
    live &= (x.max(axis=1) >= 0) & (x.min(axis=1) < w)
    live &= (y.max(axis=1) >= 0) & (y.min(axis=1) < h)

    lo_x = np.clip(np.floor(x.min(axis=1)), 0, w - 1).astype(np.int64)
    hi_x = np.clip(np.ceil(x.max(axis=1)), 0, w - 1).astype(np.int64)
    lo_y = np.clip(np.floor(y.min(axis=1)), 0, h - 1).astype(np.int64)
    hi_y = np.clip(np.ceil(y.max(axis=1)), 0, h - 1).astype(np.int64)

    ids = np.nonzero(live)[0]
    if ids.size == 0:
        return (np.zeros(0, np.int64), np.zeros(0, np.float32),
                np.zeros(0, np.int64))

    kw = _pow2(hi_x[ids] - lo_x[ids] + 1)
    kh = _pow2(hi_y[ids] - lo_y[ids] + 1)
    key = kw * (1 << 20) + kh
    order = np.argsort(key, kind="stable")
    ids, key = ids[order], key[order]
    edges = np.flatnonzero(np.diff(key)) + 1
    groups = np.split(ids, edges)

    out_pix, out_inv, out_tri = [], [], []
    for grp in groups:
        gw = int(_pow2(hi_x[grp[0]] - lo_x[grp[0]] + 1))
        gh = int(_pow2(hi_y[grp[0]] - lo_y[grp[0]] + 1))
        per = max(1, _CHUNK_PIXELS // (gw * gh))
        ax_ = np.arange(gw, dtype=np.float64)
        ay_ = np.arange(gh, dtype=np.float64)
        for s0 in range(0, grp.size, per):
            t = grp[s0:s0 + per]
            ox, oy = lo_x[t][:, None, None], lo_y[t][:, None, None]
            cx = ox + ax_[None, None, :] + 0.5
            cy = oy + ay_[None, :, None] + 0.5
            ax, ay = x0[t][:, None, None], y0[t][:, None, None]
            bx, by = x1[t][:, None, None], y1[t][:, None, None]
            gx, gy = x2[t][:, None, None], y2[t][:, None, None]
            ar = area[t][:, None, None]
            e0 = ((gx - bx) * (cy - by) - (gy - by) * (cx - bx)) / ar
            e1 = ((ax - gx) * (cy - gy) - (ay - gy) * (cx - gx)) / ar
            inside = (e0 >= 0) & (e1 >= 0) & (e0 + e1 <= 1)
            inside &= (cx < w) & (cy < h)
            if not inside.any():
                continue
            e2 = 1.0 - e0 - e1
            inv = (e0 / z[t, 0][:, None, None]
                   + e1 / z[t, 1][:, None, None]
                   + e2 / z[t, 2][:, None, None])
            inside &= inv > 0
            if not inside.any():
                continue
            ti, yi, xi = np.nonzero(inside)
            px = (ox[ti, 0, 0] + xi)
            py = (oy[ti, 0, 0] + yi)
            out_pix.append(py * w + px)
            out_inv.append(inv[ti, yi, xi].astype(np.float32))
            out_tri.append(t[ti])
    if not out_pix:
        return (np.zeros(0, np.int64), np.zeros(0, np.float32),
                np.zeros(0, np.int64))
    return (np.concatenate(out_pix), np.concatenate(out_inv),
            np.concatenate(out_tri))


def _resolve(pix, inv, tri, n_pixels):
    """Z-buffer resolve by sort.

    `np.maximum.at` is unbuffered and crawls on a million fragments.
    Positive IEEE-754 floats compare correctly as unsigned integers, so
    (pixel, ~depth) packs into one uint64 key and a single sort puts the
    nearest fragment for each pixel first.
    """
    tribuf = np.full(n_pixels, -1, np.int64)
    if pix.size == 0:
        return tribuf
    key = (pix.astype(np.uint64) << np.uint64(32)) \
        | (~inv.view(np.uint32)).astype(np.uint64)
    order = np.argsort(key, kind="stable")
    p = pix[order]
    first = np.empty(p.size, bool)
    first[0] = True
    np.not_equal(p[1:], p[:-1], out=first[1:])
    tribuf[p[first]] = tri[order][first]
    return tribuf


def depth_pass(verts, tris, cam, w, h):
    """Resolve visibility. Returns the triangle id per pixel (-1 where
    empty), the indices of covered pixels, and perspective-correct
    barycentric weights at each of them."""
    sx, sy, zc = project(verts, cam, w, h)
    pix, inv, tri = _fragments(sx, sy, zc, tris, w, h, cam.near)
    tribuf = _resolve(pix, inv, tri, w * h)
    hit = np.nonzero(tribuf >= 0)[0]
    return tribuf, hit, barycentric(sx, sy, zc, tris, tribuf, hit, w)


def barycentric(sx, sy, zc, tris, tribuf, hit, w):
    bary = np.zeros((hit.size, 3), np.float32)
    if hit.size == 0:
        return bary
    t = tris[tribuf[hit]]
    cx = (hit % w).astype(np.float64) + 0.5
    cy = (hit // w).astype(np.float64) + 0.5
    ax, ay = sx[t[:, 0]], sy[t[:, 0]]
    bx, by = sx[t[:, 1]], sy[t[:, 1]]
    gx, gy = sx[t[:, 2]], sy[t[:, 2]]
    ar = (bx - ax) * (gy - ay) - (gx - ax) * (by - ay)
    ar = np.where(np.abs(ar) < 1e-12, 1e-12, ar)
    b0 = ((gx - bx) * (cy - by) - (gy - by) * (cx - bx)) / ar
    b1 = ((ax - gx) * (cy - gy) - (ay - gy) * (cx - gx)) / ar
    b2 = 1.0 - b0 - b1
    wgt = np.stack([b0 / zc[t[:, 0]], b1 / zc[t[:, 1]], b2 / zc[t[:, 2]]], 1)
    tot = wgt.sum(1, keepdims=True)
    wgt /= np.where(np.abs(tot) < 1e-30, 1e-30, tot)
    return wgt.astype(np.float32)


def depth_and_inv(verts, tris, cam, w, h):
    """Like depth_pass, but also hands back the 1/depth buffer -- needed
    when a dynamic layer has to be composited over a cached static one."""
    sx, sy, zc = project(verts, cam, w, h)
    pix, inv, tri = _fragments(sx, sy, zc, tris, w, h, cam.near)
    tribuf = _resolve(pix, inv, tri, w * h)
    invbuf = np.zeros(w * h, np.float32)
    hit = np.nonzero(tribuf >= 0)[0]
    if hit.size:
        t = tris[tribuf[hit]]
        b = barycentric(sx, sy, zc, tris, tribuf, hit, w)
        invbuf[hit] = (b[:, 0] / zc[t[:, 0]] + b[:, 1] / zc[t[:, 1]]
                       + b[:, 2] / zc[t[:, 2]]).astype(np.float32)
        return tribuf, hit, b, invbuf
    return tribuf, hit, np.zeros((0, 3), np.float32), invbuf


def coverage(verts, tris, cam, w, h):
    """A binary coverage mask -- the ground shadow needs to know *whether*
    something covers a pixel, not what or how far."""
    sx, sy, zc = project(verts, cam, w, h)
    pix, _, _ = _fragments(sx, sy, zc, tris, w, h, cam.near)
    mask = np.zeros(w * h, np.float32)
    if pix.size:
        mask[pix] = 1.0
    return mask.reshape(h, w)


# --------------------------------------------------------------------
# colour
# --------------------------------------------------------------------
def srgb_to_linear(c):
    c = np.asarray(c, np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(c):
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92,
                    1.055 * np.power(c, 1 / 2.4) - 0.055)


def hex_to_linear(s: str) -> np.ndarray:
    s = s.lstrip("#")
    rgb = np.array([int(s[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], np.float32)
    return srgb_to_linear(rgb)


def box_downsample(img: np.ndarray, factor: int) -> np.ndarray:
    if factor == 1:
        return img
    h, w = img.shape[:2]
    h, w = h // factor * factor, w // factor * factor
    img = img[:h, :w]
    return img.reshape(h // factor, factor, w // factor, factor, -1).mean((1, 3))
