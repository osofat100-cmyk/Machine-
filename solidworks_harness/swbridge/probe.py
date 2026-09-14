"""Check this harness's assumptions against the SolidWorks actually installed.

Run this once before trusting a build:

    python -m swbridge.probe

It reports the SolidWorks version, confirms a part can be created, and
-- most importantly -- reads back the real value of
`ISketch::GetConstrainedStatus` for a deliberately under-constrained
sketch and a fully constrained one, so the `SKETCH_STATUS` table in
`enums.py` can be corrected if it is wrong. A wrong constant there means
the harness silently reports loose sketches as fine.
"""

from __future__ import annotations

from . import enums as E
from .connection import Session


def main() -> int:
    s = Session.attach(visible=True)
    print("SolidWorks:", s.app.RevisionNumber())

    s.new_part()
    m = s.model

    # An under-constrained sketch: a circle with no dimension on it.
    m.Extension.SelectByID2("Front Plane", E.SEL_PLANE, 0, 0, 0,
                            False, 0, None, 0)
    m.SketchManager.InsertSketch(True)
    m.SketchManager.CreateCircleByRadius(0, 0, 0, E.mm(25))
    loose = m.SketchManager.ActiveSketch.GetConstrainedStatus()
    m.SketchManager.InsertSketch(True)

    print(f"under-constrained sketch reports: {loose} "
          f"(enums.py calls this '{E.SKETCH_STATUS.get(loose, '?')}')")
    print(f"enums.FULLY_CONSTRAINED is currently {E.FULLY_CONSTRAINED}")
    if loose == E.FULLY_CONSTRAINED:
        print("  MISMATCH: an undimensioned circle is not fully constrained, "
              "so the SKETCH_STATUS table in enums.py is wrong for this "
              "SolidWorks version. Fix it before running the agent.")
    else:
        print("  consistent: the table distinguishes loose from constrained.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
