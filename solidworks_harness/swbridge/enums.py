"""SolidWorks API constants, in one place.

The SolidWorks type library exposes these as COM enums, but pywin32's
late binding does not surface them by name, so they are transcribed
here.

IMPORTANT -- confirm these against your own install before trusting a
run. `python -m swbridge.probe` prints the values the live type library
reports and diffs them against this table. Enum values have been stable
for many releases, but a silently wrong constant produces geometry that
is subtly wrong rather than an error, which is the worst failure mode
there is.
"""

# swDocumentTypes_e
DOC_PART = 1
DOC_ASSEMBLY = 2
DOC_DRAWING = 3

# swUserPreferenceStringValue_e -- default template paths
PREF_TEMPLATE_PART = 8
PREF_TEMPLATE_ASSEMBLY = 9
PREF_TEMPLATE_DRAWING = 10

# swSelectType_e (as the string names SelectByID2 expects)
SEL_PLANE = "PLANE"
SEL_FACE = "FACE"
SEL_EDGE = "EDGE"
SEL_VERTEX = "VERTEX"
SEL_SKETCH = "SKETCH"
SEL_COMPONENT = "COMPONENT"
SEL_SKETCHSEGMENT = "SKETCHSEGMENT"

# swEndConditions_e
END_BLIND = 0
END_THROUGH_ALL = 1
END_UP_TO_NEXT = 2
END_UP_TO_VERTEX = 3
END_UP_TO_SURFACE = 4
END_OFFSET_FROM_SURFACE = 5
END_MID_PLANE = 6

# swMateType_e
MATE_COINCIDENT = 0
MATE_CONCENTRIC = 1
MATE_PERPENDICULAR = 2
MATE_PARALLEL = 3
MATE_TANGENT = 4
MATE_DISTANCE = 5
MATE_ANGLE = 6

# swMateAlign_e
ALIGN_ALIGNED = 0
ALIGN_ANTI_ALIGNED = 1
ALIGN_CLOSEST = 2

# swAddComponentConfigOptions_e
COMP_CONFIG_CURRENT = 1
COMP_CONFIG_NEW = 2
COMP_CONFIG_NAMED = 3

# swConstrainedStatus_e -- what ISketch::GetConstrainedStatus returns.
# This is the enum the whole "not yet fully constrained" problem turns
# on, so it is the first thing `probe.py` checks.
SKETCH_STATUS = {
    0: "unknown",
    1: "under_constrained",
    2: "fully_constrained",
    3: "over_constrained",
    4: "no_solution",
    5: "invalid_solution",
}
FULLY_CONSTRAINED = 2

# swFileSaveError_e / save options
SAVE_SILENT = 1
SAVE_AS_COPY = 2

# --- unit conversion -------------------------------------------------
# The SolidWorks API is metres and radians internally, regardless of what
# the document's display units are set to. Passing 50 when you meant
# 50 mm builds a 50-metre part that still rebuilds cleanly. Convert at
# the boundary, once, and never pass a raw number to a COM call.
MM = 1.0e-3


def mm(value: float) -> float:
    """Millimetres -> metres, for any length crossing the COM boundary."""
    return value * MM


def deg(value: float) -> float:
    """Degrees -> radians, for any angle crossing the COM boundary."""
    from math import radians
    return radians(value)
