"""The cell overlay: who owns what, what each arm is doing, what got missed.

Everything drawn here is read back out of the simulation -- the joint
vectors that placed the solids, the dispatcher's own claim table, the
counters it keeps. The arm-to-arm clearance is the one number worth
watching: it is measured from the placed triangles every frame, and it
is the promise that five arms sharing a belt never touch.
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

from . import cell as C
from . import raster as R
from .cellscene import ARM_TINT
from .hud import MONO, MONO_B, SANS, SANS_B, font

INK = (232, 238, 246)
DIM = (138, 150, 168)
FAINT = (86, 96, 112)
WARN = (226, 112, 95)
PANEL = (10, 14, 20, 180)
STATE_COLOUR = {
    "IDLE": (118, 130, 148),
    "TRACK": (110, 200, 226),
    "DESCEND": (110, 200, 226),
    "CLOSE": (226, 200, 90),
    "LIFT": (150, 210, 130),
    "DROP": (150, 210, 130),
    "OPEN": (226, 200, 90),
    "RETURN": (138, 150, 168),
}


def build_meta(frames, fps: int) -> dict:
    return {
        "title": "Five-arm sort cell — picking off a moving belt",
        "subtitle": "11-part arm from robot_arm.assembly, five instances "
                    "— github.com/osofat100-cmyk/Machine-",
        "duration": len(frames) / fps,
        "tint": [tuple(int(ARM_TINT[i].lstrip("#")[j:j + 2], 16)
                       for j in (0, 2, 4)) for i in range(len(C.ARMS))],
    }


def _panel(d, box, radius=7):
    d.rounded_rectangle(box, radius=radius, fill=PANEL)


def draw(img: np.ndarray, fr, meta: dict, cam: R.Camera,
         clearance: float | None = None) -> np.ndarray:
    h, w = img.shape[:2]
    s = w / 1600.0
    pic = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), "RGB")
    over = Image.new("RGBA", pic.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)

    f_title = font(SANS_B, int(24 * s))
    f_sub = font(SANS, int(13 * s))
    f_lab = font(SANS_B, int(11 * s))
    f_num = font(MONO_B, int(17 * s))
    f_sm = font(MONO, int(12 * s))
    f_tiny = font(MONO_B, int(11 * s))
    px = int(30 * s)

    _tags(d, fr, cam, w, h, s, meta)
    _arm_labels(d, fr, cam, w, h, s, meta)

    d.text((px, int(26 * s)), meta["title"], font=f_title, fill=INK)
    d.text((px, int(56 * s)), meta["subtitle"], font=f_sub, fill=DIM)

    # ---- counters, top right ----------------------------------------
    c = fr.counts
    bx = w - px - int(340 * s)
    _panel(d, (bx - int(14 * s), int(20 * s), w - px + int(14 * s),
               int(112 * s)))
    d.text((bx, int(28 * s)), f"{fr.t:05.2f} s", font=f_num, fill=INK)
    d.text((bx + int(118 * s), int(30 * s)),
           f"BELT {C.BELT_SPEED:.0f} mm/s", font=f_lab, fill=DIM)
    if clearance is not None:
        col = INK if clearance >= 80 else WARN
        d.text((bx + int(118 * s), int(48 * s)),
               f"MIN ARM GAP {clearance:5.0f} mm", font=f_lab, fill=col)
    row = int(70 * s)
    d.text((bx, row), "SEEN", font=f_lab, fill=DIM)
    d.text((bx + int(46 * s), row - int(2 * s)), f"{c['seen']:3d}",
           font=f_sm, fill=INK)
    d.text((bx + int(96 * s), row), "PICKED", font=f_lab, fill=DIM)
    d.text((bx + int(150 * s), row - int(2 * s)), f"{c['picked']:3d}",
           font=f_sm, fill=INK)
    d.text((bx + int(208 * s), row), "MISSED", font=f_lab, fill=DIM)
    d.text((bx + int(266 * s), row - int(2 * s)), f"{c['missed']:3d}",
           font=f_sm, fill=WARN if c["missed"] else DIM)
    row = int(90 * s)
    for i, cls in enumerate(C.CLASSES):
        x = bx + i * int(112 * s)
        col = tuple(int(cls.colour.lstrip("#")[j:j + 2], 16) for j in (0, 2, 4))
        d.rectangle((x, row + int(3 * s), x + int(9 * s), row + int(12 * s)),
                    fill=col)
        d.text((x + int(15 * s), row), f"{cls.name.upper():<6} {c[cls.key]:3d}",
               font=f_tiny, fill=DIM)

    # ---- the five arms, along the bottom ----------------------------
    n = len(C.ARMS)
    cw = (w - 2 * px - (n - 1) * int(12 * s)) / n
    top = h - int(96 * s)
    for i, arm in enumerate(C.ARMS):
        x0 = px + i * (cw + int(12 * s))
        _panel(d, (x0, top, x0 + cw, h - int(26 * s)))
        tint = meta["tint"][i]
        d.rectangle((x0, top, x0 + int(4 * s), h - int(26 * s)), fill=tint)
        d.text((x0 + int(14 * s), top + int(8 * s)), arm.name,
               font=f_num, fill=tint)
        d.text((x0 + int(56 * s), top + int(13 * s)),
               "NEAR SIDE" if arm.side < 0 else "FAR SIDE",
               font=f_lab, fill=FAINT)
        phase = fr.phases[i]
        d.text((x0 + int(14 * s), top + int(34 * s)), phase,
               font=f_lab, fill=STATE_COLOUR.get(phase, DIM))
        tgt = fr.targets[i]
        if tgt is not None:
            hit = next((sn for sn in fr.parcels if sn.pid == tgt), None)
            if hit is not None:
                d.text((x0 + int(84 * s), top + int(34 * s)),
                       f"#{tgt:02d}  {hit.size:.0f} mm  {hit.key}",
                       font=f_lab, fill=INK)
        d.text((x0 + int(14 * s), top + int(52 * s)),
               f"x {arm.x0:+5.0f} .. {arm.x1:+5.0f}", font=f_tiny, fill=FAINT)
    return np.asarray(Image.alpha_composite(pic.convert("RGBA"), over)
                      .convert("RGB"))


def _tags(d, fr, cam, w, h, s, meta):
    """A size on every box still on the belt, and nothing else.

    These used to be filled panels carrying the size class *and* the arm
    that had claimed it, which put an opaque card over every box in the
    frame -- covering the one thing the shot is of. The claim already
    shows on the arm's own card at the bottom. What cannot be read off
    the picture is how big a box is, so that is all that is left here,
    drawn as bare type with a thin shadow rather than a card.
    """
    pts, keep = [], []
    for sn in fr.parcels:
        if sn.state != "belt":
            continue
        pts.append(sn.pose[:3, 3] + (0.0, 0.0, sn.size / 2.0 + 26.0))
        keep.append(sn)
    if not pts:
        return
    sx, sy, zc = R.project(np.array(pts), cam, w, h)
    f_tag = font(MONO_B, int(13 * s))
    for sn, x, y, z in zip(keep, sx, sy, zc):
        if z <= cam.near or not (0 < x < w and 0 < y < h):
            continue
        cls = C.classify(sn.size)
        col = tuple(int(cls.colour.lstrip("#")[j:j + 2], 16) for j in (0, 2, 4))
        text = f"{sn.size:.0f}"
        tw = d.textlength(text, font=f_tag)
        for ox, oy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            d.text((x - tw / 2 + ox, y + oy), text, font=f_tag, fill=(6, 9, 14))
        d.text((x - tw / 2, y), text, font=f_tag, fill=col)


def _arm_labels(d, fr, cam, w, h, s, meta):
    pts = np.array([a.origin + (0.0, 0.0, 30.0) for a in C.ARMS])
    sx, sy, zc = R.project(pts, cam, w, h)
    f = font(SANS_B, int(13 * s))
    for i, (x, y, z) in enumerate(zip(sx, sy, zc)):
        if z <= cam.near:
            continue
        d.text((x - int(9 * s), y - int(7 * s)), C.ARMS[i].name, font=f,
               fill=meta["tint"][i])
