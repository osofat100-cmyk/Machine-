# SLAB_GR_Simulation — validation report

Generated: 2026-09-25T15:33:17.373049+00:00  ·  status: **VALIDATED**  ·  9/9 tests passed  ·  wall time 6.0 s

Every number below is computed by `src/slab/validation.py` from the constants in `src/slab/constants.py`; nothing is typed in by hand. Tags: **EXACT GR RESULT** (closed-form consequence of the Schwarzschild solution), **NUMERICAL** (integrated/rooted value with the quoted error), **BRIEF** (value quoted in the project brief, used only as a comparison target).

## 1. Physical constants and provenance

| symbol | value | unit | source | verification status |
|---|---|---|---|---|
| G | 6.6743e-11 | m^3 kg^-1 s^-2 | CODATA 2018 recommended value (Tiesinga, Mohr, Newell & Taylor, Rev. Mod. Phys. 93, 025010 (2021)); NIST Reference on Constants, https://physics.nist.gov/cuu/Constants/ ; unchanged in CODATA 2022 at this precision | TRANSCRIBED — NOT RE-VERIFIED ONLINE IN THIS SESSION (network egress blocked) |
| c | 299792458.0 | m s^-1 | SI Brochure 9th ed. (BIPM 2019); CODATA | EXACT BY DEFINITION |
| hbar | 1.054571817e-34 | J s | CODATA 2018; h = 6.62607015e-34 J s exact (SI 2019) | EXACT (derived from exact h; rounded to 10 significant digits) |
| l_P | 1.616255e-35 | m | CODATA 2018 recommended value; NIST Reference on Constants | TRANSCRIBED — cross-checked internally against sqrt(hbar G/c^3) (see validation TEST 0) |
| M_sun | 1.98847e+30 | kg | Value specified in the project brief, (1.98847 +/- 0.00007)e30 kg. NOTE: the IAU 2015 nominal solar mass parameter GM_sun = 1.3271244e20 m^3 s^-2 divided by CODATA G gives 1.98841e30 kg; the 3e-5 relative difference is far below every other uncertainty in this project and is documented rather than hidden. | AS SPECIFIED IN BRIEF — NOT RE-VERIFIED ONLINE IN THIS SESSION |
| year_julian | 31557600.0 | s | IAU; used for all year conversions in this project | EXACT BY CONVENTION |
| au | 149597870700.0 | m | IAU 2012 Resolution B2 | EXACT BY DEFINITION (transcribed) |

## 2. Derived quantities (computed at run time)

| quantity | value |
|---|---|
| M_solar | 1.000000e+18 |
| M_kg | 1.988470e+48 |
| GM | 1.327165e+38 |
| M_m | 1.476670e+21 |
| M_s | 4.925640e+12 |
| r_s_m | 2.953339e+21 |
| r_s_ly | 3.121682e+05 |
| r_s_over_c_s | 9.851280e+12 |
| GM_over_c3_years | 1.560841e+05 |
| tau_horizon_to_singularity_s | 6.567520e+12 |
| tau_horizon_to_singularity_years | 2.081121e+05 |
| K_planck | 1.465414e+139 |
| r_QG_m | 1.387739e-16 |
| r_QG_over_rs | 4.698882e-38 |
| l_P_over_M | 1.094527e-56 |
| r_photon_sphere_m | 4.430009e+21 |
| r_isco_m | 8.860018e+21 |
| l_P_from_hbar_G_c | 1.616255e-35 |

Brief expectations (comparison targets only): M_kg = 1.98847e+48, r_s_m = 2.95334e+21, r_s_ly = 312168.0, GM_over_c3_years = 156084.0, tau_horizon_to_singularity_years = 208112.0, r_QG_m = 1.39e-16

## 3. Tests

### TEST 0 — Constant provenance and internal consistency  ·  **PASS**

Equation(s): `l_P = sqrt(hbar G / c^3);  M = 1e18 M_sun`  
Reference: CODATA 2018 (Tiesinga et al. 2021)

| check | value | expected | error | tolerance | result | note |
|---|---|---|---|---|---|---|
| l_P (CODATA) vs sqrt(hbar G/c^3) | 1.616255e-35 | 1.616255e-35 | 1.480493e-08 | 1.000000e-06 | ok | consistency of transcribed constants |
| M [kg] vs brief 1.98847e48 | 1.988470e+48 | 1.988470e+48 | 0 | 1.000000e-05 | ok |  |

### TEST 1 — Schwarzschild radius  ·  **PASS**

Equation(s): `r_s = 2GM/c^2 ; GM/c^3`  
Reference: Schwarzschild 1916; MTW §31.2

| check | value | expected | error | tolerance | result | note |
|---|---|---|---|---|---|---|
| r_s [m] recomputed inline vs DerivedQuantities | 2.953339e+21 | 2.953339e+21 | 0 | 1.000000e-15 | ok |  |
| r_s [m] vs brief 2.95334e21 | 2.953339e+21 | 2.953340e+21 | 2.092320e-07 | 1.000000e-05 | ok |  |
| r_s [ly] vs brief 312,168 | 3.121682e+05 | 3.121680e+05 | 7.015461e-07 | 1.000000e-05 | ok | Julian light-year 9.4607304725808e15 m |
| GM/c^3 [yr] vs brief 156,084 | 1.560841e+05 | 1.560840e+05 | 7.015461e-07 | 1.000000e-05 | ok | Julian year |

### TEST 2 — Horizon regularity of the integration coordinates (ingoing Eddington–Finkelstein)  ·  **PASS**

Equation(s): `ds^2 = -f dv^2 + 2 dv dr + r^2 dOmega^2, f = 1 - 2M/r ; all metric, Christoffel, Riemann and RHS quantities finite at r = 2M`  
Reference: Eddington 1924; Finkelstein 1958; MTW Box 31.2; Wald §6.4

| check | value | expected | error | tolerance | result | note |
|---|---|---|---|---|---|---|
| metric g_ab at r = 2M | 4 | finite | — | — | ok |  |
| inverse metric g^ab at r = 2M | 1 | finite | — | — | ok |  |
| Christoffel symbols at r = 2M | 2 | finite | — | — | ok |  |
| Riemann tensor R_abcd at r = 2M | 4 | finite | — | — | ok |  |
| geodesic RHS dy/dtau at r = 2M | 1 | finite | — | — | ok |  |
| geodesic RHS dy/dlnr at r = 2M | 2 | finite | — | — | ok |  |
| |RHS(2M(1+eps)) - RHS(2M(1-eps))|_max, eps=1e-6 | 1.000000e-06 | — | 1.000000e-06 | 1.000000e-04 | ok | continuity of the equations of motion through the horizon |
| Kruskal U at horizon | 0 | 0 | 0 | 1.000000e-300 | ok |  |
| Kruskal (T, X) at horizon | 0.5 | finite | — | — | ok |  |
| u^v at horizon (numerical) vs 1/2 | 0.5 | 0.5 | 1.163514e-13 | 1.000000e-09 | ok |  |
| u^r at horizon (numerical) vs -1 | -1 | -1 | 1.330047e-13 | 1.000000e-09 | ok |  |
| rejected steps in the segment ending on the horizon | 0 | 0 | 0 | 0 | ok | no step-size collapse approaching r = 2M |
| max normalized error estimate in that segment | 0.555956842 | — | 0.555956842 | 1 | ok |  |
| first accepted step size (ln r) just inside the horizon | 9.967501e-05 | — | — | — | ok | informational: ln r step immediately after crossing |
| rejected steps in the segment starting on the horizon | 0 | 0 | 0 | 0 | ok |  |

### TEST 3 — Radial E = 1 geodesic vs analytic solution  ·  **PASS**

Equation(s): `dr/dtau = -c sqrt(r_s/r) ;  u^v = x/(1+x), x = sqrt(r/2M) ; v(r) = -4M[x^3/3 - x^2/2 + x - ln(1+x)] + C`  
Reference: MTW §25.5 & Box 31.2; Wald problem 6.4

| check | value | expected | error | tolerance | result | note |
|---|---|---|---|---|---|---|
| max |u^r/u^r_analytic - 1| over all steps | 2.366860e-11 | — | 2.366860e-11 | 1.000000e-09 | ok |  |
| max |u^v/u^v_analytic - 1| over all steps | 2.628930e-11 | — | 2.628930e-11 | 1.000000e-09 | ok |  |
| max relative error of Delta v per milestone segment (vs series-evaluated analytic v(r)) | 3.063148e-12 | — | 3.063148e-12 | 1.000000e-09 | ok |  |
| max relative error of Delta tau per milestone segment | 2.416101e-11 | — | 2.416101e-11 | 1.000000e-09 | ok |  |

Per-segment comparison with the analytic E = 1 solution (geometrized units):

| from | to | Δv numeric | Δv analytic | rel. err | Δτ numeric | Δτ analytic | rel. err |
|---|---|---|---|---|---|---|---|
| start | isco | 1159.90556 | 1159.90556 | 2.121020e-13 | 1326.40513 | 1326.40513 | 1.731352e-13 |
| isco | photon_sphere | 2.68629606 | 2.68629606 | 3.608860e-13 | 4.47871349 | 4.47871349 | 2.133827e-13 |
| photon_sphere | horizon | 0.589155639 | 0.589155639 | 2.743731e-13 | 1.11615641 | 1.11615641 | 1.547728e-13 |
| horizon | 0.1rs | 0.552749415 | 0.552749415 | 1.110726e-13 | 1.29116963 | 1.29116963 | 1.313864e-13 |
| 0.1rs | 0.01rs | 0.00790258245 | 0.00790258245 | 1.804401e-13 | 0.0408303688 | 0.0408303688 | 2.815979e-13 |
| 0.01rs | 1ly | 9.261411e-05 | 9.261411e-05 | 2.082176e-12 | 0.00133332569 | 0.00133332569 | 1.430017e-12 |
| 1ly | 1e-6rs | 9.247906e-12 | 9.247906e-12 | 3.063148e-12 | 6.311283e-09 | 6.311283e-09 | 3.644490e-12 |
| 1e-6rs | 1au | 9.992007e-13 | 9.992007e-13 | 3.051658e-12 | 1.333333e-09 | 1.333333e-09 | 4.039952e-12 |
| 1au | extreme_curvature | 2.554153e-21 | 2.554153e-21 | 3.045168e-12 | 4.722781e-16 | 4.722781e-16 | 6.849611e-12 |
| extreme_curvature | 1km | 1.164060e-23 | 1.164060e-23 | 3.030984e-12 | 8.402735e-18 | 8.402735e-18 | 7.630067e-12 |
| 1km | 1m | 1.146497e-37 | 1.146497e-37 | 3.039178e-12 | 2.626969e-28 | 2.626969e-28 | 1.224153e-11 |
| 1m | atomic | 1.146498e-43 | 1.146498e-43 | 3.041852e-12 | 8.307468e-33 | 8.307468e-33 | 1.421107e-11 |
| atomic | nuclear | 1.146498e-63 | 1.146498e-63 | 3.036247e-12 | 8.307468e-48 | 8.307468e-48 | 2.087158e-11 |
| nuclear | r_QG | 1.124418e-73 | 1.124418e-73 | 3.045090e-12 | 2.491243e-55 | 2.491243e-55 | 2.416101e-11 |

### TEST 4 — Horizon-to-singularity proper-time benchmark  ·  **PASS**

Equation(s): `tau(r_s -> 0) = (2/3) r_s/c = 4GM/(3c^3) for E = 1 radial free fall`  
Reference: MTW §25.5 eq. (25.38) (cycloid solution); Taylor & Wheeler 'Exploring Black Holes' (2000) ch. 3

| check | value | expected | error | tolerance | result | note |
|---|---|---|---|---|---|---|
| tau(horizon -> r_QG) numeric [GM/c^3] | 1.33333333 | 1.33333333 | 2.273182e-13 | 1.000000e-09 | ok | analytic 4M/3 (1 - (r_QG/2M)^(3/2)); the missing tail (r_QG -> 0) is 1.358e-56 GM/c^3 |
| tau(horizon -> r_QG) [yr] vs 4GM/(3c^3) in years | 2.081121e+05 | 2.081121e+05 | 2.273910e-13 | 1.000000e-09 | ok |  |
| 4GM/(3c^3) [yr] vs brief 208,112 | 2.081121e+05 | 2.081120e+05 | 7.015461e-07 | 1.000000e-05 | ok |  |
| tau(r0 -> r_QG) numeric vs analytic | 1333.33333 | 1333.33333 | 1.734293e-13 | 1.000000e-09 | ok |  |

### TEST 5 — Kretschmann scalar  ·  **PASS**

Equation(s): `K = R_abcd R^abcd = 48 G^2 M^2/(c^4 r^6)  (contraction of the EF Riemann tensor vs closed form)`  
Reference: Henry 2000, ApJ 535, 350; MTW ex. 31.1

| check | value | expected | error | tolerance | result | note |
|---|---|---|---|---|---|---|
| max rel diff: einsum contraction vs 48M^2/r^6 over r in {100..r_QG} incl. r = 2M | 4.215378e-16 | — | 4.215378e-16 | 1.000000e-12 | ok |  |
| SI conversion at r = r_s: 48G^2M^2/(c^4 r^6) vs geometrized/M_m^4 | 1.577349e-85 | 1.577349e-85 | 0 | 1.000000e-12 | ok |  |
| log10 K at r_s [m^-4] | -84.8020722 | — | — | — | ok | informational |
| tidal eigenvalues (-2M/r^3, M/r^3, M/r^3) [r = 10 .. 1e-30] and radial tetrad vector vs closed form | 3.750000e-16 | — | 3.750000e-16 | 1.000000e-09 | ok | comoving frame built from the Killing energy (well conditioned); plain Gram–Schmidt checked for r >= M |
| radial tidal eigenvalue at r_QG vs -2M/r^3 (explicit contraction) | -2.409663e+111 | -2.409663e+111 | 2.216064e-16 | 1.000000e-09 | ok |  |
| radial tidal eigenvalue at r_QG vs -2M/r^3 (boost-invariant frame method used in outputs) | -2.409663e+111 | -2.409663e+111 | 0 | 1.000000e-09 | ok |  |
| orbital tidal eigenvalues: theta eigenvalue (M/r^3)(1+3L^2/r^2), traceless, independent of radial velocity | 7.455749e-09 | — | 7.455749e-09 | 1.000000e-08 | ok |  |

### TEST 6 — Quantum-curvature radius  ·  **PASS**

Equation(s): `48 G^2 M^2/(c^4 r_QG^6) = 1/l_P^4  ->  r_QG = (48 G^2 M^2 l_P^4/c^4)^(1/6)`  
Reference: definition; Planck length CODATA 2018

| check | value | expected | error | tolerance | result | note |
|---|---|---|---|---|---|---|
| r_QG numerical root (log-space brentq) vs closed form | 1.387739e-16 | 1.387739e-16 | 2.842252e-15 | 1.000000e-12 | ok |  |
| r_QG closed form (double) vs mpmath 40-digit | 1.387739e-16 | 1.387739e-16 | 1.954048e-15 | 1.000000e-14 | ok |  |
| r_QG vs brief 1.39e-16 m (brief quoted to 3 s.f.) | 1.387739e-16 | 1.390000e-16 | 0.00162634144 | 0.005 | ok |  |
| K(r_QG) / K_Planck | 1 | 1 | 1.232348e-14 | 1.000000e-12 | ok |  |

Step-by-step calculation:

* 48 G^2 M^2 / c^4 [m^2]: `1.0466656206800605e+44`
* l_P^4 [m^4]: `6.824007974056665e-140`
* product [m^6]: `7.142454541691702e-96`
* r_QG = product^(1/6) [m]: `1.387739385393499e-16`
* r_QG / r_s: `4.698882200332483e-38`
* mpmath_40_digits: `1.38773938539349614119226886232e-16`

### TEST 7 — Conserved quantities along the geodesic  ·  **PASS**

Equation(s): `E = f u^v - u^r = const ; L = r^2 sin^2 u^phi = const ; g(u,u) = -1`  
Reference: Killing symmetries; MTW §25.2

| check | value | expected | error | tolerance | result | note |
|---|---|---|---|---|---|---|
| max |g(u,u) + 1| over all steps (raw) | 4.733747e-11 | — | 4.733747e-11 | 1.000000e-09 | ok | well conditioned for radial motion (terms O(1)); see the conditioned version for L != 0 |
| max |g(u,u) + 1| / conditioning scale | 2.366873e-11 | — | 2.366873e-11 | 1.000000e-09 | ok |  |
| max |L - L0| | 0 | — | 0 | 1.000000e-12 | ok |  |
| max |E(u) - E_k| where E is well conditioned (|f u^v|,|u^r| < 10, i.e. r > 0.01 r_s) | 1.013056e-11 | — | 1.013056e-11 | 1.000000e-09 | ok | E(u) = f u^v - u^r from the integrated 4-velocity vs the separately carried Killing energy E_k |
| max |E - E0| / conditioning scale (all steps) | 2.648724e-12 | — | 2.648724e-12 | 1.000000e-09 | ok | E = f u^v - u^r cancels two terms ~sqrt(2M/r) ~ 1e19 at r_QG; raw drift = 1.204e+07 is round-off of those terms, not integration error (see physics_notes.md) |

### TEST 8 — Convergence with tolerance + independent integrator/formulation cross-checks  ·  **PASS**

Equation(s): `error(tau_h->QG), error(Delta v) vs analytic for rtol = 1e-6 .. 1e-12; SciPy DOP853; first-integral form`  
Reference: Hairer, Nørsett & Wanner 1993 ch. II; Dormand & Prince 1980

| check | value | expected | error | tolerance | result | note |
|---|---|---|---|---|---|---|
| errors decrease monotonically with tolerance (until the ~1e-11 round-off floor) | 1 | 1 | 0 | 0 | ok |  |
| error(tau) at rtol=1e-12 (uncapped step) | 2.273182e-13 | — | 2.273182e-13 | 1.000000e-09 | ok |  |
| max error(u^r) at rtol=1e-12 (uncapped step) | 2.366860e-11 | — | 2.366860e-11 | 1.000000e-09 | ok |  |
| convergence ratio error(rtol=1e-6)/error(rtol=1e-10) > 10 | 40864.2939 | — | — | — | ok | informational: how much the error shrinks over four decades of tolerance |
| SciPy DOP853 (rtol 1e-13) tau(h -> QG) vs analytic | 1.33333333 | 1.33333333 | 4.496403e-15 | 1.000000e-09 | ok |  |
| SciPy DOP853 Delta v(h -> QG) vs analytic | 0.560744611 | 0.560744611 | 1.049352e-14 | 1.000000e-09 | ok |  |
| first-integral formulation tau(h -> QG) vs analytic | 1.33333333 | 1.33333333 | 2.974287e-13 | 1.000000e-09 | ok |  |
| first-integral formulation Delta v(h -> QG) vs analytic | 0.560744611 | 0.560744611 | 5.120043e-13 | 1.000000e-09 | ok |  |
| second-order vs first-integral tau(h -> QG) (two formulations agree) | 5.247469e-13 | — | 5.247469e-13 | 2.000000e-09 | ok |  |

Convergence with tolerance (step cap lifted so that the error controller alone sets the step):

| rtol | steps | rel. err τ(h→r_QG) | rel. err Δv(h→r_QG) | max rel. err u^r | wall [s] |
|---|---|---|---|---|---|
| 1e-06 | 258 | 1.001206e-07 | 5.003674e-07 | 1.789952e-04 | 0.15 |
| 1e-08 | 538 | 1.067406e-09 | 1.363904e-09 | 8.782141e-07 | 0.27 |
| 1e-10 | 1246 | 1.318762e-11 | 3.391979e-12 | 4.380234e-09 | 0.80 |
| 1e-12 | 3041 | 2.273182e-13 | 1.480972e-13 | 2.366860e-11 | 1.93 |

## 4. Benchmark run summary

* n_steps_total: `3041`
* n_rhs_evals_total: `21294`
* n_rejected_total: `0`
* max_err_estimate: `0.598925941`
* max_abs_norm_residual: `4.733747e-11`
* max_abs_E_drift_raw: `1.203610e+07`
* max_E_drift_conditioned: `2.648724e-12`
* max_abs_E_drift_where_well_conditioned: `1.013056e-11`
* max_abs_L_drift: `0`
* max_tidal_closed_form_reldiff: `3.828812e-16`
* tau_total_years_at_end: `2.081121e+08`
* tau_since_horizon_years_at_end: `2.081121e+05`

### Milestones

| milestone | r [m] | r / r_s | τ total [yr] | log10 K [m⁻⁴] | log10 K/K_P | radial stretch [m/s² per 2 m] | regime |
|---|---|---|---|---|---|---|---|
| start | 2.953339e+23 | 100 | 0 | -96.802 | -235.968 | 2.060842e-32 | CLASSICAL GR — VALIDATED |
| isco | 8.860018e+21 | 3 | 2.070308e+08 | -87.665 | -226.831 | 7.632748e-28 | CLASSICAL GR — VALIDATED |
| photon_sphere | 4.430009e+21 | 1.5 | 2.077298e+08 | -85.859 | -225.025 | 6.106198e-27 | CLASSICAL GR — VALIDATED |
| horizon | 2.953339e+21 | 1 | 2.079040e+08 | -84.802 | -223.968 | 2.060842e-26 | CLASSICAL GR — VALIDATED |
| 0.1rs | 2.953339e+20 | 0.1 | 2.081056e+08 | -78.802 | -217.968 | 2.060842e-23 | CLASSICAL GR — VALIDATED |
| 0.01rs | 2.953339e+19 | 0.01 | 2.081119e+08 | -72.802 | -211.968 | 2.060842e-20 | CLASSICAL GR — VALIDATED |
| 1ly | 9.460730e+15 | 3.203401e-06 | 2.081121e+08 | -51.836 | -191.002 | 6.269180e-10 | CLASSICAL GR — VALIDATED |
| 1e-6rs | 2.953339e+15 | 1.000000e-06 | 2.081121e+08 | -48.802 | -187.968 | 2.060842e-08 | CLASSICAL GR — VALIDATED |
| 1au | 1.495979e+11 | 5.065380e-11 | 2.081121e+08 | -23.030 | -162.196 | 1.585654e+05 | CLASSICAL GR — VALIDATED |
| extreme_curvature | 1.007631e+10 | 3.411835e-12 | 2.081121e+08 | -16.000 | -155.166 | 5.188965e+08 | CLASSICAL GR — EXTREME CURVATURE |
| 1km | 1000 | 3.385998e-19 | 2.081121e+08 | 26.020 | -113.146 | 5.308658e+29 | CLASSICAL GR — EXTREME CURVATURE |
| 1m | 1 | 3.385998e-22 | 2.081121e+08 | 44.020 | -95.146 | 5.308658e+38 | CLASSICAL GR — EXTREME CURVATURE |
| atomic | 1.000000e-10 | 3.385998e-32 | 2.081121e+08 | 104.020 | -35.146 | 5.308658e+68 | CLASSICAL GR — EXTREME CURVATURE |
| nuclear | 1.000000e-15 | 3.385998e-37 | 2.081121e+08 | 134.020 | -5.146 | 5.308658e+83 | CLASSICAL GR — EXTREME CURVATURE |
| r_QG | 1.387739e-16 | 4.698882e-38 | 2.081121e+08 | 139.166 | -0.000 | 1.986374e+86 | PLANCK-CURVATURE BOUNDARY |

## 5. Verification caveats

* Constant values transcribed from CODATA 2018; no network access to NIST in the build session (INSUFFICIENT DATA TO RE-VERIFY ONLINE).
* M_sun = 1.98847e30 kg as specified in the brief; IAU 2015 nominal GM_sun/G gives 1.98841e30 kg (3e-5 relative).
* All 'years' are Julian years (365.25 d).

Where a value could not be independently verified in this build environment it is marked above; no gap was filled with an assumption.
