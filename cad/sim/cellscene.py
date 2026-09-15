"""Everything in frame that is not the arm: belt, bins, chute, markings.

None of this is CAD. The five arms are the model from `robot_arm/`; the
conveyor and the bins are boxes generated here so the arms have
something to work on. The one part worth explaining is the belt top,
which is built as one quad per (zone, half) rather than as a grid: the
territory boundaries are exact numbers out of `cell.py`, and painting
them on a 20 mm grid would draw a line that disagrees with the line the
dispatcher enforces.
"""

from __future__ import annotations

import numpy as np

from . import cell as C
from .raster import hex_to_linear
from .scene import MAT_MATTE, MAT_METAL, Mesh, box_mesh, floor_mesh, merge

ARM_TINT = ("#e2a03f", "#5fb7d4", "#8bc86a", "#c58ad6", "#e2705f")
FLOOR = "#2c323b"
BELT = "#23272e"
BELT_EDGE = "#3b424e"
FRAME = "#39404c"
BIN_BODY = "#2f3644"
BIN_RIM = "#4a5364"
MARKER = "#5a6472"
CHUTE = "#3a3030"


def _quad(x0, x1, y0, y1, z, colour, material=MAT_MATTE) -> Mesh:
    v = np.array([[x0, y0, z], [x1, y0, z], [x1, y1, z], [x0, y1, z]], float)
    n = np.tile(np.array([0.0, 0.0, 1.0], np.float32), (4, 1))
    t = np.array([[0, 1, 2], [0, 2, 3]], np.int64)
    return Mesh(v, n, t, np.asarray(colour, np.float32), material)


def belt_top() -> list[Mesh]:
    """The belt surface, painted with whose territory is whose."""
    edges = sorted({C.BELT_X0, C.BELT_X1}
                   | {a.x0 for a in C.ARMS} | {a.x1 for a in C.ARMS})
    base = hex_to_linear(BELT)
    out = []
    for x0, x1 in zip(edges[:-1], edges[1:]):
        xm = (x0 + x1) / 2.0
        for side, y0, y1 in ((-1, -C.BELT_HALF_W, 0.0), (1, 0.0, C.BELT_HALF_W)):
            owner = next((a for a in C.ARMS
                          if a.side == side and a.in_window(xm)), None)
            col = base if owner is None else (
                base * 0.85 + hex_to_linear(ARM_TINT[owner.index]) * 0.16)
            out.append(_quad(x0, x1, y0, y1, C.BELT_TOP, col))
    # boundary lines, a hair proud of the surface so they always win
    line = hex_to_linear("#8c97a8")
    z = C.BELT_TOP + 0.6
    out.append(_quad(C.BELT_X0, C.BELT_X1, -2.0, 2.0, z, line * 0.55))
    for a in C.ARMS:
        y0, y1 = (-C.BELT_HALF_W, 0.0) if a.side < 0 else (0.0, C.BELT_HALF_W)
        for x in (a.x0, a.x1):
            out.append(_quad(x - 3.0, x + 3.0, y0, y1, z,
                             hex_to_linear(ARM_TINT[a.index]) * 0.9))
    return out


def conveyor() -> list[Mesh]:
    hw, cx = C.BELT_HALF_W, (C.BELT_X0 + C.BELT_X1) / 2.0
    ln = C.BELT_X1 - C.BELT_X0
    body, frame = hex_to_linear(BELT), hex_to_linear(FRAME)
    out = [box_mesh((ln, 2 * hw, C.SLAB_H), (cx, 0.0, C.BELT_TOP - C.SLAB_H / 2), body)]
    for sgn in (-1, 1):
        out.append(box_mesh((ln, C.RAIL_W, 74.0),
                            (cx, sgn * (hw + C.RAIL_W / 2), C.BELT_TOP - 20.0),
                            frame, MAT_METAL))
    for x in np.arange(C.BELT_X0 + 180.0, C.BELT_X1, 620.0):
        for sgn in (-1, 1):
            out.append(box_mesh((70.0, 70.0, C.BELT_TOP - C.SLAB_H),
                                (x, sgn * (hw - 30.0), (C.BELT_TOP - C.SLAB_H) / 2),
                                frame))
    return out


def bins() -> list[Mesh]:
    """Three open trays behind every arm, plus the reject chute."""
    body, rim = hex_to_linear(BIN_BODY), hex_to_linear(BIN_RIM)
    w, h = C.BIN_INNER, C.BIN_TOP
    out = []
    for arm in C.ARMS:
        for key, pt in arm.bins.items():
            cx, cy = pt[0], pt[1]
            out.append(box_mesh((2 * w, 2 * w, 50.0), (cx, cy, 25.0), body))
            for dx, dy, sx, sy in ((w, 0, 12.0, 2 * w), (-w, 0, 12.0, 2 * w),
                                   (0, w, 2 * w, 12.0), (0, -w, 2 * w, 12.0)):
                out.append(box_mesh((sx, sy, h - 50.0),
                                    (cx + dx, cy + dy, 50.0 + (h - 50.0) / 2),
                                    rim))
            # The bin floor carries the class colour: the designation
            # lives on the destination, not on the part.
            out.append(box_mesh((2 * w - 24, 2 * w - 24, 6.0),
                                (cx, cy, 52.0),
                                hex_to_linear(C.BY_KEY[key].colour) * 0.55))
    from .sorter import REJECT_PT
    rx, ry = REJECT_PT[0], REJECT_PT[1]
    out.append(box_mesh((300.0, 2 * C.BELT_HALF_W + 60, 40.0), (rx, ry, 20.0),
                        hex_to_linear(CHUTE)))
    for dx, dy, sx, sy in ((150, 0, 14.0, 2 * C.BELT_HALF_W + 60),
                           (0, C.BELT_HALF_W + 30, 300.0, 14.0),
                           (0, -C.BELT_HALF_W - 30, 300.0, 14.0)):
        out.append(box_mesh((sx, sy, 80.0), (rx + dx, ry + dy, 80.0), rim))
    return out


def machinery() -> list[Mesh]:
    """Everything the shot has to contain -- the floor deliberately not.

    The floor is four metres of grid in every direction; fitting the
    camera to *that* frames the room and leaves the cell a smudge in the
    middle of it.
    """
    return conveyor() + bins()


def static_scene():
    return merge([floor_mesh(half=4200.0, n=52, color=hex_to_linear(FLOOR))]
                 + conveyor() + belt_top() + bins())


def belt_markers(t: float) -> list[Mesh]:
    """Small tabs riding the belt edges, so the speed is visible.

    They sit outboard of where a box can ever be, so they can never be
    the thing a gripper closes on.
    """
    col = hex_to_linear(MARKER)
    span = C.BELT_X1 - C.BELT_X0
    out = []
    for i in range(int(span // 300.0) + 1):
        x = C.BELT_X0 + (i * 300.0 + C.BELT_SPEED * t) % span
        for sgn in (-1, 1):
            out.append(box_mesh((46.0, 16.0, 7.0),
                                (x, sgn * (C.BELT_HALF_W - 13.0),
                                 C.BELT_TOP + 3.5), col))
    return out
