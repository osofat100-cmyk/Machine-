"""Physical constants with provenance, plus derived SLAB quantities.

Every derived quantity (Schwarzschild radius, GM/c^3, Planck curvature,
r_QG, ...) is COMPUTED here from the primary constants; nothing derived is
hard-coded.  Expected values quoted in the project brief are stored
separately in :data:`BRIEF_EXPECTATIONS` purely so the validation suite can
compare against them.

Verification status of the constant values (2026-09-25 session):
    The build environment had no web egress to physics.nist.gov, so the
    CODATA values below are transcribed from the CODATA 2018 recommended
    values as known to the author (the 2022 adjustment left G, hbar-derived
    l_P and c unchanged to the precision quoted here).  They agree with the
    values given in the project brief.  Status: "TRANSCRIBED FROM CODATA
    2018 — NOT RE-VERIFIED ONLINE IN THIS SESSION".
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict

# --------------------------------------------------------------------------
# Primary constants (SI)
# --------------------------------------------------------------------------
PRIMARY_CONSTANTS: Dict[str, dict] = {
    "G": {
        "value": 6.67430e-11,
        "uncertainty": 1.5e-15,
        "unit": "m^3 kg^-1 s^-2",
        "description": "Newtonian constant of gravitation",
        "source": "CODATA 2018 recommended value (Tiesinga, Mohr, Newell & Taylor, "
                  "Rev. Mod. Phys. 93, 025010 (2021)); NIST Reference on Constants, "
                  "https://physics.nist.gov/cuu/Constants/ ; unchanged in CODATA 2022 at this precision",
        "verification": "TRANSCRIBED — NOT RE-VERIFIED ONLINE IN THIS SESSION (network egress blocked)",
    },
    "c": {
        "value": 299792458.0,
        "uncertainty": 0.0,
        "unit": "m s^-1",
        "description": "speed of light in vacuum (exact by definition of the SI metre)",
        "source": "SI Brochure 9th ed. (BIPM 2019); CODATA",
        "verification": "EXACT BY DEFINITION",
    },
    "hbar": {
        "value": 1.054571817e-34,
        "uncertainty": 0.0,
        "unit": "J s",
        "description": "reduced Planck constant h/(2 pi); h is exact in the 2019 SI, hbar quoted to 10 digits",
        "source": "CODATA 2018; h = 6.62607015e-34 J s exact (SI 2019)",
        "verification": "EXACT (derived from exact h; rounded to 10 significant digits)",
    },
    "l_P": {
        "value": 1.616255e-35,
        "uncertainty": 1.8e-41,
        "unit": "m",
        "description": "Planck length sqrt(hbar G / c^3)",
        "source": "CODATA 2018 recommended value; NIST Reference on Constants",
        "verification": "TRANSCRIBED — cross-checked internally against sqrt(hbar G/c^3) (see validation TEST 0)",
    },
    "M_sun": {
        "value": 1.98847e30,
        "uncertainty": 7.0e25,
        "unit": "kg",
        "description": "solar mass",
        "source": "Value specified in the project brief, (1.98847 +/- 0.00007)e30 kg. "
                  "NOTE: the IAU 2015 nominal solar mass parameter GM_sun = 1.3271244e20 m^3 s^-2 "
                  "divided by CODATA G gives 1.98841e30 kg; the 3e-5 relative difference is far "
                  "below every other uncertainty in this project and is documented rather than hidden.",
        "verification": "AS SPECIFIED IN BRIEF — NOT RE-VERIFIED ONLINE IN THIS SESSION",
    },
    "year_julian": {
        "value": 365.25 * 86400.0,
        "uncertainty": 0.0,
        "unit": "s",
        "description": "Julian year (exact, IAU convention used for the light-year)",
        "source": "IAU; used for all year conversions in this project",
        "verification": "EXACT BY CONVENTION",
    },
    "au": {
        "value": 1.495978707e11,
        "uncertainty": 0.0,
        "unit": "m",
        "description": "astronomical unit (exact since IAU 2012 Resolution B2)",
        "source": "IAU 2012 Resolution B2",
        "verification": "EXACT BY DEFINITION (transcribed)",
    },
}

G = PRIMARY_CONSTANTS["G"]["value"]
c = PRIMARY_CONSTANTS["c"]["value"]
hbar = PRIMARY_CONSTANTS["hbar"]["value"]
l_P = PRIMARY_CONSTANTS["l_P"]["value"]
M_sun = PRIMARY_CONSTANTS["M_sun"]["value"]
YEAR = PRIMARY_CONSTANTS["year_julian"]["value"]
AU = PRIMARY_CONSTANTS["au"]["value"]
LIGHT_YEAR = c * YEAR  # m, exact given exact c and Julian year

# Values quoted in the project brief; used ONLY as comparison targets.
BRIEF_EXPECTATIONS = {
    "M_kg": 1.98847e48,
    "r_s_m": 2.95334e21,
    "r_s_ly": 312168.0,
    "GM_over_c3_years": 156084.0,
    "tau_horizon_to_singularity_years": 208112.0,
    "r_QG_m": 1.39e-16,
}


@dataclass
class DerivedQuantities:
    """All derived quantities for a black hole of mass ``M_solar`` solar masses."""

    M_solar: float
    M_kg: float = field(init=False)
    GM: float = field(init=False)            # m^3 s^-2
    M_m: float = field(init=False)           # geometric mass GM/c^2  [m]  (length unit)
    M_s: float = field(init=False)           # GM/c^3 [s]                  (time unit)
    r_s_m: float = field(init=False)         # Schwarzschild radius 2GM/c^2
    r_s_ly: float = field(init=False)
    r_s_over_c_s: float = field(init=False)  # light-crossing time r_s/c
    GM_over_c3_years: float = field(init=False)
    tau_horizon_to_singularity_s: float = field(init=False)   # 4GM/(3c^3)  (E=1 radial geodesic)
    tau_horizon_to_singularity_years: float = field(init=False)
    K_planck: float = field(init=False)      # 1/l_P^4  [m^-4]
    r_QG_m: float = field(init=False)        # radius where K = K_planck
    r_QG_over_rs: float = field(init=False)
    l_P_over_M: float = field(init=False)    # Planck length in geometrized units (M = 1)
    r_photon_sphere_m: float = field(init=False)
    r_isco_m: float = field(init=False)
    l_P_from_hbar_G_c: float = field(init=False)  # internal consistency check

    def __post_init__(self) -> None:
        self.M_kg = self.M_solar * M_sun
        self.GM = G * self.M_kg
        self.M_m = self.GM / c**2
        self.M_s = self.GM / c**3
        self.r_s_m = 2.0 * self.M_m
        self.r_s_ly = self.r_s_m / LIGHT_YEAR
        self.r_s_over_c_s = self.r_s_m / c
        self.GM_over_c3_years = self.M_s / YEAR
        self.tau_horizon_to_singularity_s = 4.0 * self.M_s / 3.0
        self.tau_horizon_to_singularity_years = self.tau_horizon_to_singularity_s / YEAR
        self.K_planck = 1.0 / l_P**4
        # K = 48 G^2 M^2 / (c^4 r^6) = 48 M_m^2 / r^6  ->  r_QG = (48 M_m^2 l_P^4)^(1/6)
        self.r_QG_m = (48.0 * self.M_m**2 * l_P**4) ** (1.0 / 6.0)
        self.r_QG_over_rs = self.r_QG_m / self.r_s_m
        self.l_P_over_M = l_P / self.M_m
        self.r_photon_sphere_m = 3.0 * self.M_m
        self.r_isco_m = 6.0 * self.M_m
        self.l_P_from_hbar_G_c = math.sqrt(hbar * G / c**3)

    def relative_uncertainties(self) -> dict:
        """First-order propagation of the quoted constant uncertainties (independent, in quadrature).
        The many digits printed elsewhere are for numerical reproducibility; the PHYSICAL precision of
        every SI quantity is limited by these (G: 2.2e-5, M_sun: 3.5e-5, l_P: 1.1e-5 relative)."""
        uG = PRIMARY_CONSTANTS["G"]["uncertainty"] / G
        uM = PRIMARY_CONSTANTS["M_sun"]["uncertainty"] / M_sun
        ul = PRIMARY_CONSTANTS["l_P"]["uncertainty"] / l_P
        uGM = math.hypot(uG, uM)
        return {
            "G": uG, "M_sun": uM, "l_P": ul,
            "M_kg": uM, "GM_and_all_lengths_and_times_in_SI (r_s, GM/c^3, tau, K^-1/4)": uGM,
            "K_SI (∝ M^2)": 2.0 * uGM, "K_planck (∝ l_P^-4)": 4.0 * ul,
            "r_QG (∝ (G M)^(1/3) l_P^(2/3))": math.hypot(uGM / 3.0, 2.0 * ul / 3.0),
            "tidal_SI (∝ G M / r^3 at fixed r)": uGM,
            "note": "geometrized results (in units of GM/c^2, GM/c^3) carry no constant uncertainty at all",
        }

    def as_dict(self) -> dict:
        d = {k: getattr(self, k) for k in self.__dataclass_fields__}
        d["relative_uncertainties"] = self.relative_uncertainties()
        return d


def kretschmann_SI(r_m: float, M_m: float) -> float:
    """Kretschmann scalar K = 48 G^2 M^2 /(c^4 r^6) in m^-4, written as 48 M_m^2/r^6."""
    return 48.0 * M_m**2 / r_m**6


def log10_kretschmann_SI(r_m: float, M_m: float) -> float:
    """log10 of the Kretschmann scalar, evaluated in log space to avoid overflow."""
    return math.log10(48.0) + 2.0 * math.log10(M_m) - 6.0 * math.log10(r_m)
