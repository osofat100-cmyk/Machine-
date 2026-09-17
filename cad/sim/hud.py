"""Telemetry overlay: what the controller would be showing you.

Everything drawn here is read back out of the simulation -- the joint
vector actually used to place the solids, the tool pose recomputed from
it, the jaw opening derived from the finger placement. Nothing is
annotation for its own sake; if a number on screen disagrees with the
picture, the picture is wrong.
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import raster as R

SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
SANS_B = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
MONO = "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"
MONO_B = "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf"

INK = (232, 238, 246)
DIM = (140, 152, 170)
AMBER = (226, 160, 63)
CYAN = (110, 200, 226)
RED = (214, 92, 66)
PANEL = (12, 16, 22, 165)

_FONTS: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def font(path: str, size: int):
    key = (path, size)
    if key not in _FONTS:
        _FONTS[key] = ImageFont.truetype(path, size)
    return _FONTS[key]


def _panel(d: ImageDraw.ImageDraw, box, radius=6):
    d.rounded_rectangle(box, radius=radius, fill=PANEL)


def draw(img: np.ndarray, st, meta: dict, cam: R.Camera,
         trail: list[np.ndarray] | None = None) -> np.ndarray:
    """`img` is float rgb in [0,1]; returns a uint8 RGB array."""
    h, w = img.shape[:2]
    s = w / 1280.0                                   # layout scale
    pic = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), "RGB")

    if trail and len(trail) > 1:
        pic = _trail(pic, trail, cam, w, h)

    over = Image.new("RGBA", pic.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)

    f_title = font(SANS_B, int(21 * s))
    f_sub = font(SANS, int(12 * s))
    f_lab = font(SANS_B, int(11 * s))
    f_num = font(MONO_B, int(15 * s))
    f_small = font(MONO, int(12 * s))
    px = int(26 * s)

    # ---- title ------------------------------------------------------
    d.text((px, int(24 * s)), meta["title"], font=f_title, fill=INK)
    d.text((px, int(50 * s)), meta["subtitle"], font=f_sub, fill=DIM)

    # ---- phase + clock (top right) ----------------------------------
    clock = f"{st.t:05.2f} s"
    tw = d.textlength(clock, font=f_num)
    d.text((w - px - tw, int(26 * s)), clock, font=f_num, fill=INK)
    pw = d.textlength(st.phase, font=f_lab)
    d.text((w - px - pw, int(50 * s)), st.phase, font=f_lab, fill=AMBER)

    # ---- joints (bottom left) ---------------------------------------
    bw, bh, gap = int(118 * s), int(5 * s), int(20 * s)
    x0 = px
    y0 = h - int(36 * s) - 6 * gap
    _panel(d, (x0 - int(12 * s), y0 - int(26 * s),
               x0 + bw + int(96 * s), y0 + 6 * gap + int(6 * s)), int(7 * s))
    d.text((x0, y0 - int(22 * s)), "JOINTS", font=f_lab, fill=DIM)
    for i, (q, (lo, hi)) in enumerate(zip(st.joints, meta["limits"])):
        y = y0 + i * gap
        d.text((x0, y), f"J{i + 1}", font=f_small, fill=DIM)
        bx = x0 + int(22 * s)
        d.rectangle((bx, y + int(5 * s), bx + bw, y + int(5 * s) + bh),
                    fill=(38, 45, 56))
        mid = bx + bw / 2
        frac = float(np.clip(q / max(abs(lo), abs(hi)), -1, 1))
        d.rectangle((min(mid, mid + frac * bw / 2), y + int(5 * s),
                     max(mid, mid + frac * bw / 2), y + int(5 * s) + bh),
                    fill=AMBER if abs(frac) < 0.9 else RED)
        d.rectangle((mid - 1, y + int(3 * s), mid, y + int(9 * s)), fill=DIM)
        d.text((bx + bw + int(10 * s), y), f"{q:+7.1f}°",
               font=f_small, fill=INK)

    # ---- tool (bottom right) ----------------------------------------
    tx = w - px - int(190 * s)
    ty = h - int(36 * s) - 4 * gap
    _panel(d, (tx - int(12 * s), ty - int(26 * s),
               w - px + int(12 * s), ty + 4 * gap + int(6 * s)), int(7 * s))
    d.text((tx, ty - int(22 * s)), "TOOL CENTRE POINT", font=f_lab, fill=DIM)
    p = st.tcp[:3, 3]
    for i, (lab, val) in enumerate((("X", p[0]), ("Y", p[1]), ("Z", p[2]))):
        y = ty + i * gap
        d.text((tx, y), lab, font=f_small, fill=DIM)
        d.text((tx + int(20 * s), y), f"{val:+8.1f} mm", font=f_small, fill=INK)
    y = ty + 3 * gap
    d.text((tx, y), "JAW", font=f_small, fill=DIM)
    col = CYAN if st.holding else INK
    tag = "HOLDING" if st.holding else "OPEN"
    d.text((tx + int(20 * s), y), f"{st.gap:8.1f} mm", font=f_small, fill=col)
    d.text((tx + int(122 * s), y), tag, font=f_small, fill=col if st.holding else DIM)

    # ---- timeline ---------------------------------------------------
    ly, lx1, lx2 = h - int(20 * s), px, w - px
    d.rectangle((lx1, ly, lx2, ly + int(3 * s)), fill=(40, 47, 58))
    total = meta["duration"]
    for a, b, name in meta["segments"]:
        xa = lx1 + (lx2 - lx1) * a / total
        xb = lx1 + (lx2 - lx1) * b / total
        d.rectangle((xa, ly, max(xa + 1, xb - 1), ly + int(3 * s)),
                    fill=(70, 82, 100))
    xp = lx1 + (lx2 - lx1) * min(st.t / total, 1.0)
    d.rectangle((lx1, ly, xp, ly + int(3 * s)), fill=AMBER)
    d.ellipse((xp - int(3 * s), ly - int(2 * s),
               xp + int(3 * s), ly + int(5 * s)), fill=INK)

    return np.asarray(Image.alpha_composite(pic.convert("RGBA"), over)
                      .convert("RGB"))


def _trail(pic: Image.Image, trail, cam: R.Camera, w: int, h: int):
    """The path the tool centre point has actually taken, projected with
    the same camera that drew the arm."""
    pts = np.asarray(trail, float)
    sx, sy, zc = R.project(pts, cam, w, h)
    over = Image.new("RGBA", pic.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    n = len(pts)
    for i in range(1, n):
        if zc[i] <= 1 or zc[i - 1] <= 1:
            continue
        a = int(200 * (i / n) ** 2.2)
        d.line((sx[i - 1], sy[i - 1], sx[i], sy[i]),
               fill=(*CYAN, a), width=max(1, int(2 * w / 1280)))
    return Image.alpha_composite(pic.convert("RGBA"), over).convert("RGB")
