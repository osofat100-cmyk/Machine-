"""Physical milestones at which the trajectory is checkpointed.

All radii are computed from the constants at run time (nothing hard-coded
except the definitional scales 1 m, 1 km, 1 AU, 1 ly, atomic 1e-10 m and
nuclear 1e-15 m).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .constants import DerivedQuantities, AU, LIGHT_YEAR


@dataclass(frozen=True)
class Milestone:
    slug: str
    label: str
    r_geo: float          # geometrized (M = 1)
    r_m: float
    r_over_rs: float
    kind: str             # 'start' | 'gr' | 'scale' | 'boundary'
    note: str = ""


def build_milestones(dq: DerivedQuantities, r0_over_rs: float, extreme_curvature_length_m: float,
                     include_isco: bool = True, include_photon_sphere: bool = True) -> List[Milestone]:
    M_m = dq.M_m
    rs_m = dq.r_s_m
    cand = [
        ("start", "Initial conditions", r0_over_rs * rs_m, "start", "start of the numerical worldline"),
        ("isco", "ISCO (r = 6GM/c^2 = 3 r_s)", dq.r_isco_m, "gr", "innermost stable circular orbit; traversed radially (not an orbit here)"),
        ("photon_sphere", "Photon sphere (r = 3GM/c^2 = 1.5 r_s)", dq.r_photon_sphere_m, "gr", "unstable circular null orbits"),
        ("horizon", "Event horizon (r = r_s = 2GM/c^2)", rs_m, "gr", "future event horizon; regular in ingoing EF coordinates"),
        ("0.1rs", "r = 0.1 r_s", 0.1 * rs_m, "gr", ""),
        ("0.01rs", "r = 0.01 r_s", 0.01 * rs_m, "gr", ""),
        ("1ly", "r = 1 light-year", LIGHT_YEAR, "scale", ""),
        ("1e-6rs", "r = 1e-6 r_s", 1e-6 * rs_m, "gr", ""),
        ("1au", "r = 1 astronomical unit", AU, "scale", ""),
        ("extreme_curvature", "Curvature beyond direct experimental tests",
         (48.0 * M_m**2 * extreme_curvature_length_m**4) ** (1.0 / 6.0), "boundary",
         f"K^(-1/4) = {extreme_curvature_length_m:g} m: onset of 'CLASSICAL GR — EXTREME CURVATURE' label (labelling convention, see physics_notes.md)"),
        ("1km", "r = 1 km", 1e3, "scale", ""),
        ("1m", "r = 1 metre", 1.0, "scale", ""),
        ("atomic", "Atomic scale (r = 1e-10 m)", 1e-10, "scale", ""),
        ("nuclear", "Nuclear scale (r = 1e-15 m)", 1e-15, "scale", ""),
        ("r_QG", "Planck-curvature threshold r_QG (K = 1/l_P^4)", dq.r_QG_m, "boundary",
         "END OF VALIDATED CLASSICAL GR; no experimentally verified theory determines the continuation"),
    ]
    if not include_isco:
        cand = [c for c in cand if c[0] != "isco"]
    if not include_photon_sphere:
        cand = [c for c in cand if c[0] != "photon_sphere"]
    r0_m = r0_over_rs * rs_m
    out: List[Milestone] = []
    seen = set()
    for slug, label, r_m, kind, note in cand:
        if r_m > r0_m or r_m < dq.r_QG_m:
            continue
        if slug != "start" and r_m == r0_m:
            continue
        if r_m in seen:
            continue
        seen.add(r_m)
        out.append(Milestone(slug, label, r_m / M_m, r_m, r_m / rs_m, kind, note))
    out.sort(key=lambda m: -m.r_geo)
    return out
