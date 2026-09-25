"""Geometrized <-> SI unit conversions.

Internally G = c = 1 and M = 1, so
    length unit  L0 = GM/c^2  = M_m   [m]
    time unit    T0 = GM/c^3  = M_s   [s]
    r_s = 2 (geometrized)
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .constants import DerivedQuantities, c, YEAR, LIGHT_YEAR, AU


@dataclass(frozen=True)
class Units:
    dq: DerivedQuantities

    # ---- lengths ---------------------------------------------------------
    def r_to_SI(self, r_geo: float) -> float:
        return r_geo * self.dq.M_m

    def r_from_SI(self, r_m: float) -> float:
        return r_m / self.dq.M_m

    def r_over_rs(self, r_geo: float) -> float:
        return r_geo / 2.0

    # ---- times -----------------------------------------------------------
    def t_to_SI(self, t_geo: float) -> float:
        return t_geo * self.dq.M_s

    def t_to_years(self, t_geo: float) -> float:
        return t_geo * self.dq.M_s / YEAR

    # ---- curvature -------------------------------------------------------
    def kretschmann_to_SI(self, K_geo: float) -> float:
        return K_geo / self.dq.M_m**4

    def log10_kretschmann_to_SI(self, log10K_geo: float) -> float:
        return log10K_geo - 4.0 * math.log10(self.dq.M_m)

    # ---- tidal tensor eigenvalues (1/length^2 geo -> 1/s^2 SI) -----------
    def tidal_to_SI(self, E_geo: float) -> float:
        """E_geo has units 1/M^2.  In SI, relative acceleration per metre of
        separation is E_SI [s^-2] = E_geo * c^2 / M_m^2."""
        return E_geo * c**2 / self.dq.M_m**2

    # ---- proper acceleration (geo 1/M -> m/s^2) --------------------------
    def accel_to_SI(self, a_geo: float) -> float:
        return a_geo * c**2 / self.dq.M_m

    def accel_from_SI(self, a_SI: float) -> float:
        return a_SI * self.dq.M_m / c**2

    # ---- convenience -----------------------------------------------------
    @staticmethod
    def m_to_ly(x_m: float) -> float:
        return x_m / LIGHT_YEAR

    @staticmethod
    def m_to_au(x_m: float) -> float:
        return x_m / AU
