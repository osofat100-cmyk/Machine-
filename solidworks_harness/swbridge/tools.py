"""The tool surface the model drives SolidWorks through.

Design notes, which are most of the actual engineering here:

* **Millimetres in, metres out.** Every length in a tool signature is mm
  and is converted once, at the COM boundary, by `enums.mm`. The model
  never sees SolidWorks' native metres-and-radians, because mixing the
  two is the single easiest way to build a part that is 1000x too big
  and still rebuilds cleanly.

* **Every tool returns text, and the text says what happened.** Not
  "ok" -- the resulting feature name, the rebuild status, the error if
  there was one. A tool that returns nothing teaches the model that
  nothing can go wrong.

* **The surface is small on purpose.** Sketch, extrude, revolve, cut,
  fillet, pattern, mate. Roughly what a first-year CAD course covers.
  Wrapping all ~2000 SolidWorks API calls would be worse, not better:
  the model would spend its context choosing between eight kinds of
  extrude instead of thinking about the part.

* **Failures come back as text, never as exceptions.** A raised
  exception ends the turn; a returned error message is something the
  model can read and act on.
"""

from __future__ import annotations

import functools
from pathlib import Path

from anthropic import beta_tool

from . import enums as E
from . import feedback as FB
from .connection import Session

# The live session. `agent_loop.run()` sets this before starting.
SESSION: Session | None = None


def _model():
    if SESSION is None:
        raise RuntimeError("no SolidWorks session bound; call bind() first")
    return SESSION.require_model()


def bind(session: Session) -> None:
    global SESSION
    SESSION = session


def _guard(fn):
    """Turn exceptions into readable text the model can recover from.

    `functools.wraps` is load-bearing, not tidiness: `@beta_tool` builds
    the tool's JSON schema by introspecting the signature, and a bare
    `*args, **kwargs` wrapper erases it. Without the wraps, every tool
    here fails schema generation at import time.
    """
    @functools.wraps(fn)
    def wrapper(*a, **kw):
        try:
            return fn(*a, **kw)
        except Exception as exc:
            return f"ERROR in {fn.__name__}: {type(exc).__name__}: {exc}"
    return wrapper


# =====================================================================
# documents
# =====================================================================
@beta_tool
@_guard
def new_part(name: str) -> str:
    """Create a new empty part document and make it active.

    Args:
        name: A short name for the part, used when it is saved.
    """
    SESSION.new_part()
    return f"created part '{name}'. Active document is now empty."


@beta_tool
@_guard
def save_part(path: str) -> str:
    """Save the active document to disk.

    Args:
        path: Full path ending in .SLDPRT or .SLDASM.
    """
    ok = SESSION.save_as(path)
    return f"saved to {path}" if ok else f"SAVE FAILED for {path}"


# =====================================================================
# sketching
# =====================================================================
@beta_tool
@_guard
def start_sketch(plane: str) -> str:
    """Open a new sketch on a named plane or a previously selected face.

    Args:
        plane: "Front Plane", "Top Plane", "Right Plane", or the name of
            a face already selected with select_face.
    """
    m = _model()
    if plane.lower().endswith("plane"):
        ok = m.Extension.SelectByID2(plane, E.SEL_PLANE, 0, 0, 0,
                                     False, 0, None, 0)
        if not ok:
            return f"ERROR: could not select '{plane}'. Valid names are " \
                   f"'Front Plane', 'Top Plane', 'Right Plane'."
    m.SketchManager.InsertSketch(True)
    return f"sketch opened on {plane}. Draw, then call finish_sketch."


@beta_tool
@_guard
def sketch_circle(cx: float, cy: float, radius: float) -> str:
    """Draw a circle in the open sketch.

    Args:
        cx: Centre X in mm, in sketch coordinates.
        cy: Centre Y in mm, in sketch coordinates.
        radius: Radius in mm.
    """
    m = _model()
    m.SketchManager.CreateCircleByRadius(E.mm(cx), E.mm(cy), 0.0, E.mm(radius))
    return f"circle r={radius}mm at ({cx}, {cy})"


@beta_tool
@_guard
def sketch_rectangle(x1: float, y1: float, x2: float, y2: float) -> str:
    """Draw a corner-to-corner rectangle in the open sketch.

    Args:
        x1: First corner X in mm.
        y1: First corner Y in mm.
        x2: Opposite corner X in mm.
        y2: Opposite corner Y in mm.
    """
    m = _model()
    m.SketchManager.CreateCornerRectangle(
        E.mm(x1), E.mm(y1), 0.0, E.mm(x2), E.mm(y2), 0.0
    )
    return f"rectangle ({x1},{y1}) to ({x2},{y2}) mm"


@beta_tool
@_guard
def sketch_line(x1: float, y1: float, x2: float, y2: float) -> str:
    """Draw a line segment in the open sketch.

    Args:
        x1: Start X in mm.
        y1: Start Y in mm.
        x2: End X in mm.
        y2: End Y in mm.
    """
    m = _model()
    m.SketchManager.CreateLine(E.mm(x1), E.mm(y1), 0.0,
                               E.mm(x2), E.mm(y2), 0.0)
    return f"line ({x1},{y1}) -> ({x2},{y2}) mm"


@beta_tool
@_guard
def finish_sketch() -> str:
    """Close the open sketch and report whether it is fully constrained.

    Always read the constraint status in the reply. A sketch that is
    under-constrained will still extrude, and will still be wrong the
    moment any dimension changes.
    """
    m = _model()
    name = None
    try:
        active = m.SketchManager.ActiveSketch
        status = active.GetConstrainedStatus()
        name = m.SketchManager.ActiveSketch.GetName() if hasattr(
            m.SketchManager.ActiveSketch, "GetName") else "sketch"
        verdict = E.SKETCH_STATUS.get(status, f"code {status}")
    except Exception:
        verdict = "unknown"
    m.SketchManager.InsertSketch(True)
    return (f"sketch closed ({name or 'unnamed'}). Constraint status: "
            f"{verdict}. Add dimensions or relations if it is not "
            f"fully_constrained.")


# =====================================================================
# features
# =====================================================================
@beta_tool
@_guard
def extrude(depth: float, both_directions: bool = False,
            draft_degrees: float = 0.0) -> str:
    """Extrude the most recently closed sketch into a solid.

    Args:
        depth: Extrusion depth in mm.
        both_directions: Extrude symmetrically about the sketch plane.
        draft_degrees: Draft angle in degrees, 0 for none.
    """
    m = _model()
    feat = m.FeatureManager.FeatureExtrusion3(
        True,                       # solid
        False,                      # flip side to cut (n/a)
        both_directions,            # direction
        E.END_BLIND, E.END_BLIND,   # end conditions
        E.mm(depth), E.mm(depth),   # depths
        False, False,               # draft outward
        False, False,
        E.deg(draft_degrees), E.deg(draft_degrees),
        False, False, False, False,
        True,                       # merge result
        True, True,                 # use feature scope / auto select
        0, 0.0, False,
    )
    if feat is None:
        return ("ERROR: extrude failed. Usual causes: the sketch is not "
                "closed, the profile self-intersects, or no sketch is "
                "selected. Call get_feature_tree to see the current state.")
    return f"extruded {depth}mm -> feature '{feat.Name}'"


@beta_tool
@_guard
def cut_extrude(depth: float, through_all: bool = False) -> str:
    """Cut a pocket or hole using the most recently closed sketch.

    Args:
        depth: Cut depth in mm. Ignored when through_all is true.
        through_all: Cut all the way through the material.
    """
    m = _model()
    end = E.END_THROUGH_ALL if through_all else E.END_BLIND
    feat = m.FeatureManager.FeatureCut4(
        True, False, False,
        end, E.END_BLIND,
        E.mm(depth), E.mm(depth),
        False, False, False, False,
        E.deg(0), E.deg(0),
        False, False, False, False, False,
        True, True, True,
        False, False, False,
    )
    if feat is None:
        return ("ERROR: cut failed. The sketch must lie on or project "
                "onto existing material.")
    return f"cut {'through all' if through_all else str(depth) + 'mm'} " \
           f"-> feature '{feat.Name}'"


@beta_tool
@_guard
def revolve(angle_degrees: float = 360.0) -> str:
    """Revolve the most recently closed sketch about its centreline.

    Args:
        angle_degrees: Angle of revolution, 360 for a full solid.
    """
    m = _model()
    feat = m.FeatureManager.FeatureRevolve2(
        True, True, False, False, False, False,
        0, 0,
        E.deg(angle_degrees), E.deg(0),
        False, False,
        E.deg(0), E.deg(0),
        True, True, True,
    )
    if feat is None:
        return ("ERROR: revolve failed. The sketch needs exactly one "
                "centreline, and the profile must not cross the axis.")
    return f"revolved {angle_degrees} deg -> feature '{feat.Name}'"


@beta_tool
@_guard
def fillet_edges(radius: float, edge_picks: str) -> str:
    """Round selected edges.

    Args:
        radius: Fillet radius in mm.
        edge_picks: Semicolon-separated "x,y,z" points in mm, each lying
            on an edge to be rounded.
    """
    m = _model()
    m.ClearSelection2(True)
    picked = 0
    for chunk in edge_picks.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        x, y, z = (float(v) for v in chunk.split(","))
        if m.Extension.SelectByID2("", E.SEL_EDGE, E.mm(x), E.mm(y), E.mm(z),
                                   True, 0, None, 0):
            picked += 1
    if picked == 0:
        return ("ERROR: no edges selected. The points must lie exactly on "
                "an edge; use get_feature_tree and a screenshot to locate "
                "them.")
    feat = m.FeatureManager.FeatureFillet3(
        195, E.mm(radius), 0, 0, 0, 0, 0,
        None, None, None, None, None, None, None,
    )
    if feat is None:
        return (f"ERROR: fillet of {radius}mm on {picked} edge(s) failed. "
                f"The radius is probably larger than the adjacent "
                f"geometry allows -- try a smaller one.")
    return f"filleted {picked} edge(s) at r={radius}mm -> '{feat.Name}'"


@beta_tool
@_guard
def circular_pattern(count: int, axis_pick: str, angle_degrees: float = 360.0) -> str:
    """Pattern the last feature around an axis.

    Args:
        count: Number of instances including the original.
        axis_pick: "x,y,z" point in mm on the axis or cylindrical face.
        angle_degrees: Total angle to spread the instances over.
    """
    m = _model()
    x, y, z = (float(v) for v in axis_pick.split(","))
    m.ClearSelection2(True)
    m.Extension.SelectByID2("", E.SEL_EDGE, E.mm(x), E.mm(y), E.mm(z),
                            False, 1, None, 0)
    feat = m.FeatureManager.FeatureCircularPattern4(
        count, E.deg(angle_degrees), False, "NULL", False, True, False,
    )
    if feat is None:
        return "ERROR: circular pattern failed; check the axis selection."
    return f"patterned {count}x -> '{feat.Name}'"


# =====================================================================
# assembly
# =====================================================================
@beta_tool
@_guard
def new_assembly(name: str) -> str:
    """Create a new empty assembly document.

    Args:
        name: A short name for the assembly.
    """
    SESSION.new_assembly()
    return f"created assembly '{name}'"


@beta_tool
@_guard
def insert_component(path: str, x: float = 0.0, y: float = 0.0,
                     z: float = 0.0) -> str:
    """Insert a saved part into the active assembly.

    Args:
        path: Full path to the .SLDPRT file.
        x: Placement X in mm.
        y: Placement Y in mm.
        z: Placement Z in mm.
    """
    m = _model()
    comp = m.AddComponent5(path, E.COMP_CONFIG_CURRENT, "", False, "",
                           E.mm(x), E.mm(y), E.mm(z))
    if comp is None:
        return f"ERROR: could not insert {path}. Is the part saved?"
    return f"inserted {Path(path).name} at ({x},{y},{z}) mm"


@beta_tool
@_guard
def add_mate(mate_type: str, face_picks: str, distance: float = 0.0,
             angle_degrees: float = 0.0, aligned: bool = True) -> str:
    """Mate two selected faces or edges together.

    Args:
        mate_type: One of coincident, concentric, parallel,
            perpendicular, tangent, distance, angle.
        face_picks: Two semicolon-separated "x,y,z" points in mm, one on
            each face to be mated.
        distance: Separation in mm, for a distance mate.
        angle_degrees: Angle, for an angle mate.
        aligned: Alignment direction; flip this if the part lands
            backwards.
    """
    m = _model()
    kinds = {
        "coincident": E.MATE_COINCIDENT, "concentric": E.MATE_CONCENTRIC,
        "perpendicular": E.MATE_PERPENDICULAR, "parallel": E.MATE_PARALLEL,
        "tangent": E.MATE_TANGENT, "distance": E.MATE_DISTANCE,
        "angle": E.MATE_ANGLE,
    }
    if mate_type not in kinds:
        return f"ERROR: unknown mate '{mate_type}'. Use one of {sorted(kinds)}."
    m.ClearSelection2(True)
    picks = [p for p in face_picks.split(";") if p.strip()]
    if len(picks) != 2:
        return "ERROR: add_mate needs exactly two picks, separated by ';'."
    for p in picks:
        x, y, z = (float(v) for v in p.split(","))
        m.Extension.SelectByID2("", E.SEL_FACE, E.mm(x), E.mm(y), E.mm(z),
                                True, 0, None, 0)
    align = E.ALIGN_ALIGNED if aligned else E.ALIGN_ANTI_ALIGNED
    err = 0
    mate = m.AddMate5(
        kinds[mate_type], align, False,
        E.mm(distance), E.mm(distance), E.mm(distance),
        0, 0,
        E.deg(angle_degrees), E.deg(angle_degrees), E.deg(angle_degrees),
        False, False, 0, err,
    )
    if mate is None:
        return (f"ERROR: {mate_type} mate failed. The two faces may be "
                f"incompatible, or the mate may over-constrain the "
                f"assembly. Try flipping 'aligned'.")
    return f"added {mate_type} mate"


# =====================================================================
# feedback -- the tools that let the model see what it built
# =====================================================================
@beta_tool
@_guard
def get_feature_tree() -> str:
    """Show the current feature tree, with any errors marked."""
    return FB.get_feature_tree(_model())


@beta_tool
@_guard
def rebuild_and_check() -> str:
    """Force a rebuild and report every feature that failed."""
    r = FB.rebuild(_model())
    if r["error_count"] == 0:
        return "rebuild clean: no feature errors"
    lines = [f"rebuild produced {r['error_count']} error(s):"]
    for e in r["errors"]:
        lines.append(f"  {e['name']} ({e['type']}): "
                     f"{e['error'] or 'code ' + str(e['error_code'])}")
    return "\n".join(lines)


@beta_tool
@_guard
def check_constraints() -> str:
    """Report which sketches are not fully constrained.

    Run this before declaring a part finished. Rebuilding clean is not
    the same as being properly defined.
    """
    return FB.constraint_summary(_model())


@beta_tool
@_guard
def take_screenshot(path: str, view: str = "*Isometric") -> str:
    """Save an image of the model so it can be looked at.

    Args:
        path: Where to write the .bmp file.
        view: A named view, e.g. *Isometric, *Front, *Top, *Right.
    """
    out = FB.screenshot(_model(), path, view=view)
    return f"screenshot saved to {out}"


@beta_tool
@_guard
def get_mass_properties() -> str:
    """Report mass, volume and centre of gravity of the active model."""
    mp = FB.mass_properties(_model())
    cg = mp["center_of_mass_m"]
    return (f"mass {mp['mass_kg'] * 1000:.1f} g, "
            f"volume {mp['volume_m3'] * 1e9:.0f} mm3, "
            f"CG at ({cg[0] * 1000:.1f}, {cg[1] * 1000:.1f}, "
            f"{cg[2] * 1000:.1f}) mm")


#: Everything the agent is allowed to do, in one list.
ALL_TOOLS = [
    new_part, save_part,
    start_sketch, sketch_circle, sketch_rectangle, sketch_line, finish_sketch,
    extrude, cut_extrude, revolve, fillet_edges, circular_pattern,
    new_assembly, insert_component, add_mate,
    get_feature_tree, rebuild_and_check, check_constraints,
    take_screenshot, get_mass_properties,
]
