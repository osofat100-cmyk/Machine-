"""SLAB_GR_Simulation physics engine.

Numerical simulation of an observer falling radially into a Schwarzschild
("Stupendously LArge Black hole", SLAB) of mass 1e18 solar masses.

Internal units are geometrized: G = c = 1 and the black-hole mass M = 1, so
lengths are measured in units of GM/c^2, times in units of GM/c^3 and the
Schwarzschild radius is r_s = 2.  Conversion to SI is done only at the
interface (see :mod:`slab.units`).

Regime boundary: the validated classical-GR integration stops at r_QG where
the Kretschmann scalar reaches the Planck curvature 1/l_P^4.  Everything in
:mod:`slab.speculative` is a toy model and is NOT established physics.
"""
__version__ = "0.1.0"
