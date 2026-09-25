# SLAB_GR_Simulation — validation report

Generated: 2026-09-25T22:53:24.800816+00:00  ·  status: **VALIDATED**  ·  11/11 tests passed  ·  wall time 12.7 s

Every number below is computed by `src/slab/validation.py` from the constants in `src/slab/constants.py`; nothing is typed in by hand. Tags: **EXACT GR RESULT** (closed-form consequence of the Schwarzschild solution), **NUMERICAL** (integrated/rooted value with the quoted error), **BRIEF** (value quoted in the project brief, used only as a comparison target).

## 1. Physical constants and provenance

| symbol | value | unit | source | verification status |
|---|---|---|---|---|
| G | 6.6743e-11 | m^3 kg^-1 s^-2 | CODATA 2022 recommended value, 6.67430(15)e-11 (P. J. Mohr, D. B. Newell, B. N. Taylor & E. Tiesinga, Rev. Mod. Phys. 97, 025002 (2025), doi:10.1103/RevModPhys.97.025002); NIST Reference on Constants, https://physics.nist.gov/cuu/Constants/ ; identical to the CODATA 2018 value (Tiesinga et al., Rev. Mod. Phys. 93, 025010 (2021)) | VERIFIED VIA WEB SEARCH (2026-09-25): value and standard uncertainty are CODATA 2022 (https://physics.nist.gov/cgi-bin/cuu/Value?bg ; https://physics.nist.gov/cuu/pdf/wallet_2022.pdf) |
| c | 299792458.0 | m s^-1 | SI Brochure 9th ed. (BIPM 2019): defining constant c = 299 792 458 m/s, exact since 20 May 2019 | EXACT BY DEFINITION — VERIFIED VIA WEB SEARCH (2026-09-25) (https://www.bipm.org/documents/20126/41483022/SI-Brochure-9-EN.pdf ; https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.330-2019.pdf) |
| hbar | 1.054571817e-34 | J s | h = 6.62607015e-34 J s exact (SI Brochure 9th ed., BIPM 2019); hbar = h/(2 pi) = 1.054571817...e-34 J s, listed as exact in CODATA 2022 (Mohr et al., Rev. Mod. Phys. 97, 025002 (2025)) and CODATA 2018 | EXACT (derived from exact h; the 10 digits printed by CODATA, 1.054 571 817..., i.e. truncated, 7e-10 relative below h/(2 pi)) — VERIFIED VIA WEB SEARCH (2026-09-25) (https://physics.nist.gov/cgi-bin/cuu/Value?hbar) |
| l_P | 1.616255e-35 | m | CODATA 2022 recommended value, 1.616255(18)e-35 m, relative standard uncertainty 1.1e-5 (Mohr et al., Rev. Mod. Phys. 97, 025002 (2025)); identical to CODATA 2018; NIST Reference on Constants | VERIFIED VIA WEB SEARCH (2026-09-25) (https://physics.nist.gov/cgi-bin/cuu/Value?plkl); also cross-checked internally against sqrt(hbar G/c^3) (validation TEST 0). CORRECTED 2026-09-25: standard uncertainty was stored as 1.8e-41 m (factor 10 too small), now 1.8e-40 m; central value unchanged |
| M_sun | 1.98847e+30 | kg | Value specified in the project brief, (1.98847 +/- 0.00007)e30 kg. It equals the IAU 2015 Resolution B3 nominal solar mass parameter (GM)_sun = 1.3271244e20 m^3 s^-2 (exact; Prsa et al., Astron. J. 152, 41 (2016)) divided by the CODATA 2014 G = 6.67408e-11 (1.988475e30 kg). IAU 2015 B3 defines no solar mass in kg and recommends quoting (GM)/G with the adopted G. NOTE: divided by the CODATA 2022 G the same GM_sun gives 1.98841e30 kg; the 3.0e-5 relative difference is far below every other uncertainty in this project and is documented rather than hidden. | PARTIALLY VERIFIED (2026-09-25): GM_sun value and the CODATA 2014 G confirmed by web search (https://iopscience.iop.org/article/10.3847/0004-6256/152/2/41 ; https://arxiv.org/pdf/1507.07956); primary source of the brief's value and of its +/- 7e25 kg uncertainty: INSUFFICIENT DATA TO VERIFY. Kept as specified in the brief |
| year_julian | 31557600.0 | s | IAU convention: Julian year = 365.25 days of 86400 s, the year in the IAU definition of the light-year (c x Julian year = 9 460 730 472 580 800 m); used for all year conversions in this project | EXACT BY CONVENTION — VERIFIED VIA WEB SEARCH (2026-09-25) (https://iauarchive.eso.org/public/themes/measuring/) |
| au | 149597870700.0 | m | IAU 2012 Resolution B2 (XXVIII General Assembly, Beijing): au = 149 597 870 700 m exactly | EXACT BY DEFINITION — VERIFIED VIA WEB SEARCH (2026-09-25) (https://observatoiredeparis.psl.eu/the-new-definition-of-the-astronomical-unit.html) |

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
| relative_uncertainties | {'G': 2.2474266964325848e-05, 'M_sun': 3.5202944977797e-05, 'l_P': 1.1136856498510445e-05, 'M_kg': 3.5202944977797e-05, 'GM_and_all_lengths_and_times_in_SI (r_s, GM/c^3, tau, K^-1/4)': 4.1765296726990835e-05, 'K_SI (∝ M^2)': 8.353059345398167e-05, 'K_planck (∝ l_P^-4)': 4.454742599404178e-05, 'r_QG (∝ (G M)^(1/3) l_P^(2/3))': 1.577782656968404e-05, 'tidal_SI (∝ G M / r^3 at fixed r)': 4.1765296726990835e-05, 'note': 'geometrized results (in units of GM/c^2, GM/c^3) carry no constant uncertainty at all'} |

Brief expectations (comparison targets only): M_kg = 1.98847e+48, r_s_m = 2.95334e+21, r_s_ly = 312168.0, GM_over_c3_years = 156084.0, tau_horizon_to_singularity_years = 208112.0, r_QG_m = 1.39e-16

## 3. Tests

### TEST 0 — Constant provenance and internal consistency  ·  **PASS**

Equation(s): `l_P = sqrt(hbar G / c^3);  M = 1e18 M_sun`  
Reference: CODATA 2022 (Mohr, Newell, Taylor & Tiesinga, Rev. Mod. Phys. 97, 025002 (2025)); G and l_P unchanged from CODATA 2018

| check | value | expected | error | tolerance | result | note |
|---|---|---|---|---|---|---|
| l_P (CODATA) vs sqrt(hbar G/c^3) | 1.616255e-35 | 1.616255e-35 | 1.480493e-08 | 1.000000e-06 | ok | internal consistency of the CODATA constants |
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
| u^v at horizon (numerical) vs 1/2 | 0.5 | 0.5 | 9.181544e-14 | 1.000000e-09 | ok |  |
| u^r at horizon (numerical) vs -1 | -1 | -1 | 1.014744e-13 | 1.000000e-09 | ok |  |
| rejected steps in the segment ending on the horizon, excluding the segment's first step | 0 | 0 | 0 | 0 | ok | total rejections 1 (first-step rejections are a segment-restart artefact of the carried-over step size) |
| step-size ratio min/max in the segment ending on the horizon (no collapse) | 0.388441363 | — | — | — | ok | informational; must stay well above ~1e-3 |
| no step-size collapse ending on the horizon: min step > 1e-3 x max step | 0.00257439113 | — | 0.00257439113 | 1 | ok |  |
| max normalized error estimate in the segment ending on the horizon | 0.769536365 | — | 0.769536365 | 1 | ok |  |
| rejected steps in the segment starting on the horizon, excluding the segment's first step | 0 | 0 | 0 | 0 | ok | total rejections 2 (first-step rejections are a segment-restart artefact of the carried-over step size) |
| step-size ratio min/max in the segment starting on the horizon (no collapse) | 0.22579962 | — | — | — | ok | informational; must stay well above ~1e-3 |
| no step-size collapse starting on the horizon: min step > 1e-3 x max step | 0.00442870542 | — | 0.00442870542 | 1 | ok |  |
| max normalized error estimate in the segment starting on the horizon | 0.658815235 | — | 0.658815235 | 1 | ok |  |

### TEST 3 — Radial E = 1 geodesic vs analytic solution  ·  **PASS**

Equation(s): `dr/dtau = -c sqrt(r_s/r) ;  u^v = x/(1+x), x = sqrt(r/2M) ; v(r) = -4M[x^3/3 - x^2/2 + x - ln(1+x)] + C`  
Reference: Taylor & Wheeler, Exploring Black Holes (2000) ch. 3; MTW (1973) ch. 25 and ch. 31 (section numbers from memory — INSUFFICIENT DATA TO VERIFY)

| check | value | expected | error | tolerance | result | note |
|---|---|---|---|---|---|---|
| max |u^r/u^r_analytic - 1| over all steps | 1.500350e-11 | — | 1.500350e-11 | 1.000000e-09 | ok |  |
| max |u^v/u^v_analytic - 1| over all steps | 1.683854e-11 | — | 1.683854e-11 | 1.000000e-09 | ok |  |
| max relative error of Delta v per milestone segment (vs series-evaluated analytic v(r)) | 1.709822e-12 | — | 1.709822e-12 | 1.000000e-09 | ok |  |
| max relative error of Delta tau per milestone segment | 1.498698e-11 | — | 1.498698e-11 | 1.000000e-09 | ok |  |

Per-segment comparison with the analytic E = 1 solution (geometrized units):

| from | to | Δv numeric | Δv analytic | rel. err | Δτ numeric | Δτ analytic | rel. err |
|---|---|---|---|---|---|---|---|
| start | isco | 1159.90556 | 1159.90556 | 1.593706e-13 | 1326.40513 | 1326.40513 | 1.301085e-13 |
| isco | photon_sphere | 2.68629606 | 2.68629606 | 2.859976e-13 | 4.47871349 | 4.47871349 | 1.687627e-13 |
| photon_sphere | horizon | 0.589155639 | 0.589155639 | 2.129407e-13 | 1.11615641 | 1.11615641 | 1.185663e-13 |
| horizon | 0.1rs | 0.552749415 | 0.552749415 | 8.817520e-14 | 1.29116963 | 1.29116963 | 9.922766e-14 |
| 0.1rs | 0.01rs | 0.00790258245 | 0.00790258245 | 7.617118e-14 | 0.0408303688 | 0.0408303688 | 1.485314e-13 |
| 0.01rs | 1ly | 9.261411e-05 | 9.261411e-05 | 6.248432e-13 | 0.00133332569 | 0.00133332569 | 3.060720e-13 |
| 1ly | 1e-6rs | 9.247906e-12 | 9.247906e-12 | 1.691248e-12 | 6.311283e-09 | 6.311283e-09 | 1.684694e-12 |
| 1e-6rs | 1au | 9.992007e-13 | 9.992007e-13 | 1.120295e-12 | 1.333333e-09 | 1.333333e-09 | 1.822228e-12 |
| 1au | extreme_curvature | 2.554153e-21 | 2.554153e-21 | 1.684805e-12 | 4.722781e-16 | 4.722781e-16 | 3.623992e-12 |
| extreme_curvature | 1km | 1.164060e-23 | 1.164060e-23 | 1.320975e-12 | 8.402735e-18 | 8.402735e-18 | 3.944854e-12 |
| 1km | 1m | 1.146497e-37 | 1.146497e-37 | 1.709822e-12 | 2.626969e-28 | 2.626969e-28 | 7.085629e-12 |
| 1m | atomic | 1.146498e-43 | 1.146498e-43 | 1.653018e-12 | 8.307468e-33 | 8.307468e-33 | 8.275337e-12 |
| atomic | nuclear | 1.146498e-63 | 1.146498e-63 | 1.691198e-12 | 8.307468e-48 | 8.307468e-48 | 1.287683e-11 |
| nuclear | r_QG | 1.124418e-73 | 1.124418e-73 | 1.694945e-12 | 2.491243e-55 | 2.491243e-55 | 1.498698e-11 |

### TEST 4 — Horizon-to-singularity proper-time benchmark  ·  **PASS**

Equation(s): `tau(r_s -> 0) = (2/3) r_s/c = 4GM/(3c^3) for E = 1 radial free fall`  
Reference: MTW §25.5 eq. (25.38) (cycloid solution); Taylor & Wheeler 'Exploring Black Holes' (2000) ch. 3

| check | value | expected | error | tolerance | result | note |
|---|---|---|---|---|---|---|
| tau(horizon -> r_QG) numeric [GM/c^3] | 1.33333333 | 1.33333333 | 2.273182e-13 | 1.000000e-09 | ok | analytic 4M/3 (1 - (r_QG/2M)^(3/2)); the missing tail (r_QG -> 0) is 1.358e-56 GM/c^3 |
| tau(horizon -> r_QG) [yr] vs 4GM/(3c^3) in years | 2.081121e+05 | 2.081121e+05 | 2.273910e-13 | 1.000000e-09 | ok |  |
| 4GM/(3c^3) [yr] vs brief 208,112 | 2.081121e+05 | 2.081120e+05 | 7.015461e-07 | 1.000000e-05 | ok |  |
| tau(r0 -> r_QG) numeric vs analytic | 1333.33333 | 1333.33333 | 1.302851e-13 | 1.000000e-09 | ok |  |

### TEST 5 — Kretschmann scalar  ·  **PASS**

Equation(s): `K = R_abcd R^abcd = 48 G^2 M^2/(c^4 r^6)  (contraction of the EF Riemann tensor vs closed form)`  
Reference: Henry 2000, ApJ 535, 350, doi:10.1086/308819

| check | value | expected | error | tolerance | result | note |
|---|---|---|---|---|---|---|
| max rel diff: einsum contraction vs 48M^2/r^6 over r in {100..r_QG} incl. r = 2M | 4.215378e-16 | — | 4.215378e-16 | 1.000000e-12 | ok |  |
| SI conversion at r = r_s: 48G^2M^2/(c^4 r^6) vs geometrized/M_m^4 | 1.577349e-85 | 1.577349e-85 | 0 | 1.000000e-12 | ok |  |
| log10 K at r_s [m^-4] | -84.8020722 | — | — | — | ok | informational |
| tidal eigenvalues (-2M/r^3, M/r^3, M/r^3) [r = 10 .. 1e-30] and radial tetrad vector vs closed form | 3.750000e-16 | — | 3.750000e-16 | 1.000000e-09 | ok | comoving frame built from the Killing energy (well conditioned); plain Gram–Schmidt checked for r >= M |
| radial tidal eigenvalue at r_QG vs -2M/r^3 (explicit contraction) | -2.409663e+111 | -2.409663e+111 | 2.216064e-16 | 1.000000e-09 | ok |  |
| radial tidal eigenvalue at r_QG vs -2M/r^3 (closed form used in outputs) | -2.409663e+111 | -2.409663e+111 | 0 | 1.000000e-12 | ok |  |
| orbital-motion tidal eigenvalues: closed form -(2+3L^2/r^2), 1+3L^2/r^2, 1 (x M/r^3) vs explicit contraction | 1.193437e-15 | — | 1.193437e-15 | 1.000000e-09 | ok |  |

### TEST 6 — Quantum-curvature radius  ·  **PASS**

Equation(s): `48 G^2 M^2/(c^4 r_QG^6) = 1/l_P^4  ->  r_QG = (48 G^2 M^2 l_P^4/c^4)^(1/6)`  
Reference: definition; Planck length CODATA 2022

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
| max |g(u,u) + 1| over all steps (raw) | 3.000711e-11 | — | 3.000711e-11 | 1.000000e-09 | ok | well conditioned for radial motion (terms O(1)); see the conditioned version for L != 0 |
| max |g(u,u) + 1| / conditioning scale | 1.500355e-11 | — | 1.500355e-11 | 1.000000e-09 | ok |  |
| max |L - L0| (benchmark has L = 0: trivially conserved) | 0 | — | 0 | 1.000000e-12 | ok |  |
| L = 3.5 plunge: max |L - L0| / L0 over all steps | 4.229147e-10 | — | 4.229147e-10 | 1.000000e-08 | ok | 7416 steps, modes ['tau', 'tau', 'tau']... ; u^theta stays exactly 0: True |
| L = 3.5 plunge: max conditioned |g(u,u)+1| | 6.371459e-12 | — | 6.371459e-12 | 1.000000e-09 | ok |  |
| L = 3.5 plunge: max conditioned E drift | 2.233547e-12 | — | 2.233547e-12 | 1.000000e-09 | ok |  |
| max |E(u) - E_k| where E is well conditioned (|f u^v|,|u^r| < 10, i.e. r > 0.01 r_s) | 5.941914e-12 | — | 5.941914e-12 | 1.000000e-09 | ok | E(u) = f u^v - u^r from the integrated 4-velocity vs the separately carried Killing energy E_k |
| max |E - E0| / conditioning scale (all steps) | 1.995972e-12 | — | 1.995972e-12 | 1.000000e-09 | ok | E = f u^v - u^r cancels two terms ~sqrt(2M/r) ~ 1e19 at r_QG; the raw drift 6.134e+06 is rtol x that magnitude, i.e. tolerance-level error of the huge velocity components, not an error in the conserved energy itself (see physics_notes.md §4) |

### TEST 8 — Convergence with tolerance + independent integrator/formulation cross-checks  ·  **PASS**

Equation(s): `error(tau_h->QG), error(Delta v) vs analytic for rtol = 1e-6 .. 1e-12; SciPy DOP853; first-integral form`  
Reference: Hairer, Nørsett & Wanner 1993 ch. II; Dormand & Prince 1980

| check | value | expected | error | tolerance | result | note |
|---|---|---|---|---|---|---|
| errors decrease monotonically with tolerance (exemption only below 1e-12) | 1 | 1 | 0 | 0 | ok |  |
| error(tau) at rtol=1e-12 (uncapped step) | 2.273182e-13 | — | 2.273182e-13 | 1.000000e-09 | ok |  |
| max error(u^r) at rtol=1e-12 (uncapped step) | 1.500350e-11 | — | 1.500350e-11 | 1.000000e-09 | ok |  |
| convergence ratio error(rtol=1e-6)/error(rtol=1e-10) >= 100 (checked as 100/ratio <= 1) | 0.00259290597 | — | 0.00259290597 | 1 | ok | ratio = 3.857e+04 over four decades of tolerance |
| SciPy DOP853 (rtol 1e-13) tau(h -> QG) vs analytic | 1.33333333 | 1.33333333 | 4.662937e-15 | 1.000000e-09 | ok |  |
| SciPy DOP853 Delta v(h -> QG) vs analytic | 0.560744611 | 0.560744611 | 8.315616e-15 | 1.000000e-09 | ok |  |
| first-integral formulation tau(h -> QG) vs analytic | 1.33333333 | 1.33333333 | 2.191580e-13 | 1.000000e-09 | ok |  |
| first-integral formulation Delta v(h -> QG) vs analytic | 0.560744611 | 0.560744611 | 3.771726e-13 | 1.000000e-09 | ok |  |
| second-order vs first-integral tau(h -> QG) (two formulations agree) | 4.464762e-13 | — | 4.464762e-13 | 2.000000e-09 | ok |  |
| mpmath quadrature self-test: tau(r_s -> 1e-30 r_s) for E = 1 vs closed form (35 digits) | 2.256949e-36 | — | 2.256949e-36 | 1.000000e-28 | ok |  |
| 1 g rocket (no closed form) vs mpmath: quadrature error estimate | 2.565561e-39 | — | 2.565561e-39 | 1.000000e-25 | ok |  |
| 1 g rocket vs mpmath: errors decrease monotonically with rtol | 1 | 1 | 0 | 0 | ok |  |
| 1 g rocket vs mpmath at rtol=1e-12: max rel error of dtau per milestone segment (r0 -> r_QG) | 6.456496e-12 | — | 6.456496e-12 | 1.000000e-09 | ok |  |
| 1 g rocket vs mpmath at rtol=1e-12: max rel error of dv per milestone segment | 5.818694e-12 | — | 5.818694e-12 | 1.000000e-09 | ok |  |
| 1 g rocket vs mpmath at rtol=1e-12: max rel error of u^r at milestones | 6.475131e-12 | — | 6.475131e-12 | 1.000000e-09 | ok |  |
| 1 g rocket: carried Killing energy vs exact E(r) = 1 + alpha (r0 - r) at milestones | 9.765081e-14 | — | 9.765081e-14 | 1.000000e-09 | ok |  |
| 1 g rocket: convergence ratio error(rtol=1e-6)/error(rtol=1e-10) >= 100 (checked as 100/ratio <= 1) | 0.00227774639 | — | 0.00227774639 | 1 | ok | ratio = 4.390e+04 |
| L = 3.5 plunge vs mpmath: quadrature error estimate | 3.137345e-38 | — | 3.137345e-38 | 1.000000e-25 | ok |  |
| L = 3.5 plunge vs mpmath at rtol=1e-12: max rel error of (dtau, dv per segment; accumulated phi and u^r at milestones), r0 = 100 r_s -> r_QG | 4.331629e-11 | — | 4.331629e-11 | 1.000000e-09 | ok |  |
| L = 3.5 plunge: error at rtol=1e-8 > error at rtol=1e-12 (convergence) | 1 | 1 | 0 | 0 | ok |  |

Convergence with tolerance (step cap lifted so that the error controller alone sets the step):

| rtol | steps | rel. err τ(h→r_QG) | rel. err Δv(h→r_QG) | max rel. err u^r | wall [s] |
|---|---|---|---|---|---|
| 1e-06 | 258 | 7.536573e-08 | 2.181327e-07 | 1.059515e-04 | 0.05 |
| 1e-08 | 585 | 8.286633e-10 | 7.581093e-10 | 5.443173e-07 | 0.11 |
| 1e-10 | 1411 | 9.606482e-12 | 2.986494e-12 | 2.747224e-09 | 0.26 |
| 1e-12 | 3471 | 2.273182e-13 | 1.480972e-13 | 1.500350e-11 | 0.65 |

1 g rocket (no closed form) vs 35-digit mpmath quadrature reference, milestone segments r0 -> r_QG, step cap lifted:

| max_rel_err_dtau_per_segment | max_rel_err_dv_per_segment | max_rel_err_u_r_at_milestones | max_rel_err_E_at_milestones | rtol | steps | wall_s |
|---|---|---|---|---|---|---|
| 6.679433e-05 | 1.977293e-06 | 6.748448e-05 | 1.583673e-08 | 1.000000e-06 | 295 | 1.14424229 |
| 3.360052e-07 | 1.985345e-08 | 3.397616e-07 | 4.572552e-10 | 1.000000e-08 | 651 | 0.0913236141 |
| 1.521405e-09 | 3.792195e-10 | 1.534429e-09 | 7.251584e-12 | 1.000000e-10 | 1539 | 0.210634232 |
| 6.456496e-12 | 5.818694e-12 | 6.475131e-12 | 9.765081e-14 | 1.000000e-12 | 3769 | 0.509701729 |

Reference used for the 1 g rocket:

* method: `35-digit mpmath tanh-sinh quadrature of dtau/dr = 1/sqrt(E(r)^2 - f), dv/dr = u^v/|u^r|, E(r) = 1 + alpha (r0 - r) (exact); milestone segments r0 -> r_QG`
* alpha_geo: `1.611799e+05`
* quad_rel_err_max: `2.565561e-39`
* E_at_horizon: `3.191363e+07`

L = 3.5 GM/c plunge vs 35-digit mpmath quadrature reference (r0 = 100 r_s -> r_QG):

| max_rel_err_dtau_per_segment | max_rel_err_dv_per_segment | max_rel_err_u_r_at_milestones | max_rel_err_phi_at_milestones | rtol | steps | wall_s |
|---|---|---|---|---|---|---|
| 4.214268e-07 | 1.349589e-07 | 4.239610e-07 | 8.036501e-08 | 1.000000e-08 | 1895 | 1.21598268 |
| 4.330802e-09 | 9.094475e-10 | 4.364546e-09 | 5.604537e-10 | 1.000000e-10 | 4749 | 0.600439548 |
| 4.292783e-11 | 6.852962e-12 | 4.331629e-11 | 4.289672e-12 | 1.000000e-12 | 11968 | 1.55404472 |

### TEST 9 — Accelerated observer's proper reference frame: inertial (Rindler-type) differential term  ·  **PASS**

Equation(s): `d^2 xi^i/dtau^2 = -a^i - [R^i_0j0 + a^i a_j] xi^j  =>  differential along the thrust axis: -(lambda_radial + a^2) L`  
Reference: MTW §13.6 (proper reference frame, linear order); Ni & Zimmermann 1978, Phys. Rev. D 17, 1473 (second-order metric); exact Rindler solution (flat space)

| check | value | expected | error | tolerance | result | note |
|---|---|---|---|---|---|---|
| flat space: engine-integrated thrusting observer vs exact hyperbola (a = 1, tau <= 2) | 8.090639e-12 | — | 8.090639e-12 | 1.000000e-09 | ok |  |
| flat space: free particle at the observer, rest-frame position vs (1/a)(1/cosh(a tau) - 1) | 7.081835e-12 | — | 7.081835e-12 | 1.000000e-09 | ok |  |
| flat space: free particle L ahead, separation vs exact L/cosh(a tau) (relative to L) | 5.452441e-11 | — | 5.452441e-11 | 1.000000e-08 | ok | separation shrinks to 0.2658 L at a tau = 2 (exact 1/cosh 2 = 0.2658) |
| flat space: measured differential acceleration at tau = 0 vs -a^2 L | -0.0999999998 | -0.1 | 2.237302e-09 | 1.000000e-06 | ok |  |
| flat space: measured acceleration of the co-located free particle vs -a | -0.999999998 | -1 | 1.568909e-09 | 1.000000e-06 | ok |  |
| hovering observer (r0 = 2 r_s, particle ahead (outward)): engine thrust holds r fixed | 0 | — | 0 | 1.000000e-10 | ok |  |
| hovering (r0 = 2 r_s, particle ahead (outward)): co-located free particle accelerates at -a | -0.0883883476 | -0.0883883476 | 4.286352e-14 | 1.000000e-06 | ok |  |
| hovering (r0 = 2 r_s, particle ahead (outward)): measured differential acceleration vs exact lapse value | 2.343474e-05 | 2.343474e-05 | 7.513700e-10 | 1.000000e-05 | ok |  |
| hovering (r0 = 2 r_s, particle ahead (outward)): measured vs -(lambda + a^2) L  [a^2/|lambda| = 0.250] | 2.343474e-05 | 2.343750e-05 | 1.178623e-04 | 0.02 | ok | first order in L = 1e-3 M |
| hovering (r0 = 2 r_s, particle ahead (outward)): tidal-only prediction -lambda L would be wrong by (informational) | 0.333490502 | — | — | — | ok | shows that the inertial term is required in an accelerated frame |
| hovering observer (r0 = 1.1 r_s, particle ahead (outward)): engine thrust holds r fixed | 0 | — | 0 | 1.000000e-10 | ok |  |
| hovering (r0 = 1.1 r_s, particle ahead (outward)): co-located free particle accelerates at -a | -0.685253056 | -0.685253056 | 2.911275e-12 | 1.000000e-06 | ok |  |
| hovering (r0 = 1.1 r_s, particle ahead (outward)): measured differential acceleration vs exact lapse value | -2.815243e-04 | -2.815243e-04 | 9.369872e-09 | 1.000000e-05 | ok |  |
| hovering (r0 = 1.1 r_s, particle ahead (outward)): measured vs -(lambda + a^2) L  [a^2/|lambda| = 2.500] | -2.815243e-04 | -2.817431e-04 | 7.765605e-04 | 0.02 | ok | first order in L = 1e-3 M |
| hovering (r0 = 1.1 r_s, particle ahead (outward)): tidal-only prediction -lambda L would be wrong by (informational) | 1.66718478 | — | — | — | ok | shows that the inertial term is required in an accelerated frame |
| hovering observer (r0 = 1.1 r_s, particle behind (inward)): engine thrust holds r fixed | 0 | — | 0 | 1.000000e-10 | ok |  |
| hovering (r0 = 1.1 r_s, particle behind (inward)): co-located free particle accelerates at -a | -0.685253056 | -0.685253056 | 2.911275e-12 | 1.000000e-06 | ok |  |
| hovering (r0 = 1.1 r_s, particle behind (inward)): measured differential acceleration vs exact lapse value | -2.819619e-04 | -2.819619e-04 | 2.150412e-08 | 1.000000e-05 | ok |  |
| hovering (r0 = 1.1 r_s, particle behind (inward)): measured vs -(lambda + a^2) L  [a^2/|lambda| = 2.500] | -2.819619e-04 | -2.817431e-04 | 7.766674e-04 | 0.02 | ok | first order in L = 1e-3 M |
| hovering (r0 = 1.1 r_s, particle behind (inward)): tidal-only prediction -lambda L would be wrong by (informational) | 1.66614929 | — | — | — | ok | shows that the inertial term is required in an accelerated frame |
| thrust_1g: inertial_diff_radial_m_s2 = -a^2 L/c^2 at every step (engine on) | 0 | — | 0 | 1.000000e-15 | ok | a = 9.81 m/s^2, L = 2 m: a^2 L/c^2 = 2.1415e-15 m/s^2 |
| thrust_1g: radial_total_diff = radial_stretch + inertial_diff | 1.877572e-16 | — | 1.877572e-16 | 1.000000e-12 | ok |  |
| free-fall benchmark: inertial_diff_radial_m_s2 exactly 0 (engine off) | 0 | 0 | 0 | 0 | ok |  |
| thrust_1g: carried Killing energy vs exact E(r) = 1 + alpha (r0 - r) at every step (max rel) | 3.434641e-09 | — | 3.434641e-09 | 1.000000e-08 | ok | the maximum sits in the first steps (r0 - r ~ 1e-9 M) where r = exp(ln r) is rounded to ~3e-14 and dE/dr = alpha = 1.6e5; inside the horizon max rel = 5.7e-14 (milestones: TEST 8) |
| thrust_1g: ratio |inertial|/|tidal| at the start (100 r_s) (informational) | 1.039159e+17 | — | — | — | ok |  |
| thrust_1g: ratio |inertial|/|tidal| at the horizon (informational) | 1.039159e+11 | — | — | — | ok |  |
| thrust_1g: crossover radius r_x/r_s where the two are equal (informational) | 2.127025e-04 | — | — | — | ok | = 66.4 ly; below r_x the tidal (curvature) term dominates |

Flat-space (Rindler) check, engine-integrated observer and free particles (geometrized units):

* a_geo: `1`
* L_geo: `0.1`
* tau_max: `2`
* observer_vs_exact_hyperbola_max_abs: `8.090639e-12`
* xi_origin_vs_exact_max_abs: `7.081835e-12`
* xi_ahead_vs_exact_max_abs: `6.613102e-12`
* separation_vs_L_over_cosh_max_rel: `5.452441e-11`
* separation_at_tau_max_over_L: `0.265802229`
* measured_diff_accel_at_0: `-0.0999999998`
* predicted_inertial_term_-a2L: `-0.1`
* measured_origin_accel_at_0: `-0.999999998`
* predicted_origin_accel_-a: `-1`

Static (hovering) observer held by the engine in Schwarzschild: measured vs predicted differential acceleration:

| r0_geo | r0_over_rs | L_geo | direction | a_geo | lambda_radial_geo | a2_over_abs_lambda | observer_hover_max_abs_dr | measured_origin_accel_along_r | predicted_-a | measured_diff_accel | exact_lapse_diff_accel | predicted_-(lambda+a2)L | tidal_only_prediction_-lambdaL |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4 | 2 | 0.001 | outward (ahead of the outward thrust) | 0.0883883476 | -0.03125 | 0.25 | 0 | -0.0883883476 | -0.0883883476 | 2.343474e-05 | 2.343474e-05 | 2.343750e-05 | 3.125000e-05 |
| 2.2 | 1.1 | 0.001 | outward (ahead of the outward thrust) | 0.685253056 | -0.1878287 | 2.5 | 0 | -0.685253056 | -0.685253056 | -2.815243e-04 | -2.815243e-04 | -2.817431e-04 | 1.878287e-04 |
| 2.2 | 1.1 | 0.001 | inward (behind) | 0.685253056 | -0.1878287 | 2.5 | 0 | -0.685253056 | -0.685253056 | -2.819619e-04 | -2.819619e-04 | -2.817431e-04 | 1.878287e-04 |

thrust_1g: inertial term (-a^2 L/c^2) vs radial tidal stretching across 2 m at the milestones:

| milestone | r_over_rs | radial_stretch_m_s2 | inertial_diff_m_s2 | abs_ratio_inertial_to_tidal |
|---|---|---|---|---|
| start | 100 | 2.060842e-32 | -2.141542e-15 | 1.039159e+17 |
| isco | 3 | 7.632748e-28 | -2.141542e-15 | 2.805729e+12 |
| photon_sphere | 1.5 | 6.106198e-27 | -2.141542e-15 | 3.507161e+11 |
| horizon | 1 | 2.060842e-26 | -2.141542e-15 | 1.039159e+11 |
| 0.1rs | 0.1 | 2.060842e-23 | -2.141542e-15 | 1.039159e+08 |
| 0.01rs | 0.01 | 2.060842e-20 | -2.141542e-15 | 1.039159e+05 |
| 1ly | 3.203401e-06 | 6.269180e-10 | -2.141542e-15 | 3.415984e-06 |
| 1e-6rs | 1.000000e-06 | 2.060842e-08 | -2.141542e-15 | 1.039159e-07 |
| 1au | 5.065380e-11 | 1.585654e+05 | -2.141542e-15 | 1.350573e-20 |
| extreme_curvature | 3.411835e-12 | 5.188965e+08 | -2.141542e-15 | 4.127108e-24 |
| 1km | 3.385998e-19 | 5.308658e+29 | -2.141542e-15 | 4.034055e-45 |
| 1m | 3.385998e-22 | 5.308658e+38 | -2.141542e-15 | 4.034055e-54 |
| atomic | 3.385998e-32 | 5.308658e+68 | -2.141542e-15 | 4.034055e-84 |
| nuclear | 3.385998e-37 | 5.308658e+83 | -2.141542e-15 | 4.034055e-99 |
| r_QG | 4.698882e-38 | 1.986374e+86 | -2.141542e-15 | 1.078116e-101 |

Radius where the radial tidal term equals the inertial term (1 g):

* r_x_over_rs: `2.127025e-04`
* r_x_m: `6.281828e+17`
* r_x_ly: `66.3989759`
* definition: `2GM L/r^3 = a^2 L/c^2 (radial motion): inertial term dominates for r > r_x, curvature below`

### TEST 10 — Distant-observer received-signal timeline  ·  **PASS**

Equation(s): `u = v - 2 r_*;  1+z = du/dtau = u^v - 2u^r/f;  1+z ~ exp(u/4M) (kappa = 1/4M);  E = 1: 1+z = 1/(1 - sqrt(r_s/r))`  
Reference: MTW §31.3–31.4 (freezing/redshift at the horizon, from memory); surface gravity kappa = 1/4M: Wald §12.5 (from memory)

| check | value | expected | error | tolerance | result | note |
|---|---|---|---|---|---|---|
| timeline reaches eps = r/r_s - 1 <= 1.1e-12 | 1.000089e-12 | — | 1.000089e-12 | 1.100000e-12 | ok | 281 emission radii |
| E = 1: 1+z vs closed form 1/(1 - sqrt(r_s/r)) over eps = 99 .. 1e-12 (max rel) | 5.218048e-15 | — | 5.218048e-15 | 1.000000e-09 | ok |  |
| E = 1: t_receive vs closed form Delta v(r) - 2 Delta r_*(r) (max abs error / max(1, |value|)) | 5.253006e-15 | — | 5.253006e-15 | 1.000000e-09 | ok |  |
| dense output (one ln r integration, Hairer continuous extension) vs exact per-radius integration: 1+z | 2.522427e-13 | — | 2.522427e-13 | 1.000000e-09 | ok |  |
| dense vs exact: t_receive (max abs / max(1,|value|)) | 3.632386e-12 | — | 3.632386e-12 | 1.000000e-09 | ok |  |
| E = 1: 4M d ln(1+z)/du for eps <= 1e-8 -> 1 (redshift e-folds every 4GM/c^3) | 0.999999998 | 1 | 2.165739e-09 | 0.01 | ok | max local deviation 1.88e-08 |
| E = 1: reception time per decade of eps -> 4M ln 10 = 9.2103 M | 9.21034038 | 9.21034037 | 1.353591e-09 | 0.01 | ok |  |
| t_receive strictly increasing (-> infinity as eps -> 0) | 1 | 1 | 0 | 0 | ok | t_receive(eps_min) = 2.634833e+08 yr; +1.4376e+06 yr per further decade of eps, without bound |
| emitter proper time at eps_min vs horizon-crossing proper time of the main run (finite) | 1332 | 1332 | 1.246117e-13 | 1.000000e-09 | ok | proper time elapsed over the last 4.0 decades of eps: 1.994e-08 GM/c^3 while t_receive advanced 36.83 GM/c^3 |
| trajectory columns u_ret_geo / t_receive_years are null inside the horizon and finite outside | 1 | 1 | 0 | 0 | ok |  |
| thrust_1g (E -> 3.2e7): 4M d ln(1+z)/du for eps <= 1e-8 -> 1 | 0.999999998 | 1 | 2.154787e-09 | 0.01 | ok |  |
| thrust_1g (E -> 3.2e7): t_receive strictly increasing, timeline reaches eps <= 1.1e-12 | 1 | 1 | 0 | 0 | ok |  |
| L = 3.5 plunge from 20 r_s (tau mode): 4M d ln(1+z)/du for eps <= 1e-8 -> 1 | 0.999999998 | 1 | 2.142986e-09 | 0.01 | ok |  |
| L = 3.5 plunge from 20 r_s (tau mode): t_receive strictly increasing, timeline reaches eps <= 1.1e-12 | 1 | 1 | 0 | 0 | ok |  |

Late-time received-signal behaviour, E = 1 benchmark:

* n: `81`
* eps_range: `[9.971325987123691e-09, 1.000088900582341e-12]`
* dln1pz_du: `0.249999999`
* dln1pz_du_times_4M: `0.999999998`
* max_local_dev_of_4M_dln1pz_du_from_1: `1.883788e-08`
* t_receive_per_decade_geo: `9.21034038`
* t_receive_per_decade_expected_4Mln10: `9.21034037`
* tau_increment_over_range_geo: `1.994044e-08`
* t_receive_increment_over_range_geo: `36.8295199`

Late-time received-signal behaviour, thrust_1g:

* n: `81`
* eps_range: `[9.971325987123691e-09, 1.000088900582341e-12]`
* dln1pz_du: `0.249999999`
* dln1pz_du_times_4M: `0.999999998`
* max_local_dev_of_4M_dln1pz_du_from_1: `1.874262e-08`
* t_receive_per_decade_geo: `9.21034038`
* t_receive_per_decade_expected_4Mln10: `9.21034037`
* tau_increment_over_range_geo: `6.248393e-16`
* t_receive_increment_over_range_geo: `36.8295199`

Late-time received-signal behaviour, L = 3.5 plunge:

* n: `81`
* eps_range: `[9.853944327176123e-09, 1.000088900582341e-12]`
* dln1pz_du: `0.249999999`
* dln1pz_du_times_4M: `0.999999998`
* max_local_dev_of_4M_dln1pz_du_from_1: `1.861747e-08`
* t_receive_per_decade_geo: `9.21034039`
* t_receive_per_decade_expected_4Mln10: `9.21034037`
* tau_increment_over_range_geo: `1.970594e-08`
* t_receive_increment_over_range_geo: `36.7821529`

## 4. Benchmark run summary

* n_steps_total: `3471`
* n_rhs_evals_total: `20966`
* n_rejected_total: `22`
* max_err_estimate: `0.769536365`
* max_abs_norm_residual: `3.000711e-11`
* max_abs_E_drift_raw: `6.133761e+06`
* max_E_drift_conditioned: `1.995972e-12`
* max_abs_E_drift_where_well_conditioned: `5.941914e-12`
* max_abs_L_drift: `0`
* max_tidal_closed_form_reldiff: `3.081180e-16`
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

* Constants checked against CODATA 2022 (Rev. Mod. Phys. 97, 025002 (2025)) by web search on 2026-09-25; NIST pages themselves could not be fetched from the build environment (see references.md).
* M_sun = 1.98847e30 kg as specified in the brief; IAU 2015 nominal GM_sun/G gives 1.98841e30 kg (3e-5 relative).
* All 'years' are Julian years (365.25 d).

Where a value could not be independently verified in this build environment it is marked above; no gap was filled with an assumption.
