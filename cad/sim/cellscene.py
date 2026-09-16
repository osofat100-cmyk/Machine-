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
    """The belt surface, with each arm's stretch marked off.

    Marked, not painted. This used to fill every window with that arm's
    colour, which put five saturated panels down the middle of the shot
    and made the whole thing look colour-coded -- the one thing the cell
    is not, since it sorts on measured size. The boundaries are drawn as
    thin lines instead, in one neutral grey, and the colour lives on the
    bins where the designations are.
    """
    base = hex_to_linear(BELT)
    out = [_quad(C.BELT_X0, C.BELT_X1, -C.BELT_HALF_W, C.BELT_HALF_W,
                 C.BELT_TOP, base)]
    line = hex_to_linear("#798496")
    z = C.BELT_TOP + 0.6
    for arm in C.ARMS:
        for x in (arm.x0, arm.x1):
            out.append(_quad(x - 3.0, x + 3.0, -C.BELT_HALF_W,
                             C.BELT_HALF_W, z, line * 0.7))
    return out


def conveyor() -> list[Mesh]:
    hw, cx = C.BELT_HALF_W, (C.BELT_X0 + C.BELT_X1) / 2.0
    ln = C.BELT_X1 - C.BELT_X0
    body, frame = hex_to_linear(BELT), hex_to_linear(FRAME)
    out = [box_mesh((ln, 2 * hw, C.SLAB_H), (cx, 0.0, C.BELT_TOP - C.SLAB_H / 2), body)]
    # Side frames, and their tops are flush with the running surface --
    # not proud of it. They used to stand 17 mm above it, which is
    # nothing on the machine and everything on screen: the near rail is
    # between the camera and every box on the belt, so each box looked
    # sunk into the belt by 17 mm. On a 42 mm box that is 40 per cent of
    # it. Nothing was ever in the wrong place; the frame was just taller
    # than the thing it carries.
    rail_h = 74.0
    for sgn in (-1, 1):
        out.append(box_mesh((ln, C.RAIL_W, rail_h),
                            (cx, sgn * (hw + C.RAIL_W / 2),
                             C.BELT_TOP - rail_h / 2.0),
                            frame, MAT_METAL))
    for x in np.arange(C.BELT_X0 + 180.0, C.BELT_X1, 620.0):
        for sgn in (-1, 1):
            out.append(box_mesh((70.0, 70.0, C.BELT_TOP - C.SLAB_H),
                                (x, sgn * (hw - 30.0), (C.BELT_TOP - C.SLAB_H) / 2),
                                frame))
    return out


def _slab(half, centre, colour) -> Mesh:
    return box_mesh(tuple(2.0 * np.asarray(half)), tuple(centre), colour)


def bins() -> list[Mesh]:
    """Three open trays behind every arm, plus the reject chute.

    Every slab here comes from `cell`, which is also what the solver
    collides boxes against. Drawn walls and collided walls that are
    written out separately drift, and a box then comes to rest a
    centimetre inside a wall with nothing reporting it.
    """
    body, rim = hex_to_linear(BIN_BODY), hex_to_linear(BIN_RIM)
    w = C.BIN_INNER
    out = []
    for arm in C.ARMS:
        for key, pt in arm.bins.items():
            cx, cy = pt[0], pt[1]
            out.append(box_mesh((2 * w, 2 * w, C.BIN_BASE_H),
                                (cx, cy, C.BIN_BASE_H / 2), body))
            for half, centre in C.bin_walls(cx, cy):
                out.append(_slab(half, centre, rim))
            # The bin floor carries the class colour: the designation
            # lives on the destination, not on the part.
            out.append(box_mesh((2 * w - 24, 2 * w - 24, 6.0),
                                (cx, cy, C.BIN_FLOOR_Z - 3.0),
                                hex_to_linear(C.BY_KEY[key].colour) * 0.55))
    out.append(_slab(C.CHUTE_HALF,
                     C.CHUTE_PT + (0.0, 0.0, C.CHUTE_FLOOR_Z / 2.0),
                     hex_to_linear(CHUTE)))
    for half, centre in C.chute_walls():
        out.append(_slab(half, centre, rim))
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

    They stand 7 mm proud of the belt, so where they sit is not a
    decorating decision: a box must never be able to ride through one.
    They used to be placed at `BELT_HALF_W - 13`, which put their inner
    edge 3 mm inside the furthest a box edge reaches -- while the
    docstring said they were outboard of it. Both numbers come off
    `BELT_EDGE_MARGIN` now, so they cannot drift apart again.
    """
    col = hex_to_linear(MARKER)
    span = C.BELT_X1 - C.BELT_X0
    half_w, clear = 8.0, 2.0
    y = C.BELT_HALF_W - C.BELT_EDGE_MARGIN + clear + half_w
    out = []
    for i in range(int(span // 300.0) + 1):
        x = C.BELT_X0 + (i * 300.0 + C.BELT_SPEED * t) % span
        for sgn in (-1, 1):
            out.append(box_mesh((46.0, 2 * half_w, 7.0),
                                (x, sgn * y, C.BELT_TOP + 3.5), col))
    return out
