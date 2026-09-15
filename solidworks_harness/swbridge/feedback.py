"""Reading state back out of SolidWorks.

This is the half of a CAD harness that decides whether the agent is any
good. A model that can only *emit* features is writing blind: it will
happily build a feature on a failed sketch and carry on. These functions
are how it finds out it was wrong, in terms specific enough to repair.

Four channels, in ascending order of usefulness:

    get_feature_tree()      what exists now
    get_errors()            what SolidWorks thinks is broken
    get_sketch_status()     what is under-constrained
    screenshot()            what it actually looks like

The last one matters more than it sounds. Plenty of defects are
geometrically legal and visibly absurd -- a gripper whose jaws open
outward, a boss on the wrong face, an arm assembled inside its own base.
Nothing in the first three channels catches those; an image does.
"""

from __future__ import annotations

from pathlib import Path

from . import enums as E


def walk_features(model) -> list[dict]:
    """Depth-first walk of the FeatureManager tree."""
    out: list[dict] = []

    def visit(feat, depth: int) -> None:
        while feat is not None:
            try:
                name = feat.Name
                ftype = feat.GetTypeName2()
            except Exception:
                break
            # GetErrorCode2 fills a description out-param; pywin32 returns
            # it alongside the code as a tuple.
            code, desc = 0, ""
            try:
                res = feat.GetErrorCode2("")
                if isinstance(res, tuple):
                    code, desc = res[0], res[1]
                else:
                    code = res
            except Exception:
                pass
            out.append({
                "name": name,
                "type": ftype,
                "depth": depth,
                "error_code": code,
                "error": desc or "",
                "suppressed": bool(feat.IsSuppressed()) if hasattr(feat, "IsSuppressed") else False,
            })
            try:
                child = feat.GetFirstSubFeature()
                if child is not None:
                    visit(child, depth + 1)
            except Exception:
                pass
            feat = feat.GetNextFeature()

    visit(model.FirstFeature(), 0)
    return out


def get_feature_tree(model) -> str:
    """The feature tree as indented text, the way the UI shows it."""
    rows = walk_features(model)
    if not rows:
        return "(empty feature tree)"
    lines = []
    for r in rows:
        flag = ""
        if r["error_code"]:
            flag = f"  <!> {r['error'] or 'error ' + str(r['error_code'])}"
        if r["suppressed"]:
            flag += "  [suppressed]"
        lines.append("  " * r["depth"] + f"{r['name']} ({r['type']}){flag}")
    return "\n".join(lines)


def get_errors(model) -> list[dict]:
    """Every feature currently reporting a rebuild error or warning."""
    return [r for r in walk_features(model) if r["error_code"]]


def rebuild(model, force: bool = True) -> dict:
    """Rebuild and report what broke.

    Always rebuild before believing anything. SolidWorks defers a lot of
    solving, so a feature can look fine until the rebuild that exposes it.
    """
    ok = model.ForceRebuild3(False) if force else model.EditRebuild3()
    errs = get_errors(model)
    return {
        "rebuilt": bool(ok),
        "error_count": len(errs),
        "errors": errs[:20],
    }


def get_sketch_status(model) -> list[dict]:
    """Constraint status of every sketch in the part.

    This is the specific gap the MecAgent post describes: geometry that
    rebuilds cleanly while its sketches remain under-defined. A rebuild
    will never tell you about it -- an under-constrained sketch is not an
    error, it is just fragile. You have to ask.
    """
    out = []
    for r in walk_features(model):
        if "Sketch" not in (r["type"] or ""):
            continue
        try:
            model.Extension.SelectByID2(
                r["name"], E.SEL_SKETCH, 0, 0, 0, False, 0, None, 0
            )
            feat = model.SelectionManager.GetSelectedObject6(1, -1)
            sketch = feat.GetSpecificFeature2()
            status = sketch.GetConstrainedStatus()
            out.append({
                "sketch": r["name"],
                "status": E.SKETCH_STATUS.get(status, f"code {status}"),
                "fully_constrained": status == E.FULLY_CONSTRAINED,
            })
        except Exception as exc:
            out.append({"sketch": r["name"], "status": f"unreadable: {exc}",
                        "fully_constrained": False})
    model.ClearSelection2(True)
    return out


def constraint_summary(model) -> str:
    """One line per under-defined sketch, plus a headline count."""
    rows = get_sketch_status(model)
    if not rows:
        return "no sketches found"
    loose = [r for r in rows if not r["fully_constrained"]]
    head = f"{len(rows) - len(loose)}/{len(rows)} sketches fully constrained"
    if not loose:
        return head
    return head + "\n" + "\n".join(
        f"  {r['sketch']}: {r['status']}" for r in loose
    )


def screenshot(model, path: str | Path, width: int = 1400,
               height: int = 1000, view: str = "*Isometric") -> str:
    """Save a viewport image for the model to look at."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    model.ShowNamedView2(view, -1)
    model.ViewZoomtofit2()
    model.SaveBMP(str(path), width, height)
    return str(path)


def mass_properties(model) -> dict:
    """Volume, surface area, mass and centre of gravity, in SI units."""
    ext = model.Extension
    mp = ext.CreateMassProperty()
    return {
        "mass_kg": mp.Mass,
        "volume_m3": mp.Volume,
        "surface_area_m2": mp.SurfaceArea,
        "center_of_mass_m": list(mp.CenterOfMass),
    }
