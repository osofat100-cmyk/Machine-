# physics_notes.md — equations implemented in SLAB_GR_Simulation

Every equation carries a classification tag and a citation.

Tags: **EXACT GR RESULT** — closed-form consequence of the Schwarzschild solution;
**NUMERICAL APPROXIMATION** — computed by an integrator/root finder with the quoted error;
**VISUALIZATION APPROXIMATION** — used only for rendering; **SPECULATIVE MODEL** — not established
physics; **LABELLING CONVENTION** — a display choice, not physics.

Citation verification status (2026-09-25): every citation was checked by targeted web searches
(page fetches were blocked, so only search-result titles, URLs and snippets count; full texts were
not read). Flags used below: **[VERIFIED VIA WEB SEARCH]** — bibliographic data (and, for
textbooks, the section title) confirmed; **[PARTIALLY VERIFIED]** — some details confirmed, the
rest not; **[section number from memory — INSUFFICIENT DATA TO VERIFY]** — the textbook is
verified but that section/equation/exercise number was not found. Confirming URLs and every
correction are in `references.md` and `docs/additions/citations.md`. Equations marked
**[VERIFIED FROM CODE]** are reproduced/derived inside this repository (symbolically in
`tools/derive_ef_curvature.py` or numerically in `src/slab/validation.py` and `tests/`); that status
does not depend on any citation.

Units: geometrized G = c = 1 with M = 1 inside the engine; r_s = 2M = 2. SI conversion in
`src/slab/units.py`: length unit M_m = GM/c², time unit M_s = GM/c³.

---

## 1. Constants and derived scales — EXACT (definitions)

| quantity | formula | value for M = 10¹⁸ M☉ |
|---|---|---|
| M | 10¹⁸ × 1.98847e30 kg | 1.98847e48 kg |
| GM/c² | — | 1.476670e21 m |
| r_s | 2GM/c² | 2.953339e21 m = 312,168 ly (Julian) |
| GM/c³ | — | 4.925640e12 s = 156,084 yr |
| 4GM/(3c³) | proper time horizon → r = 0, E = 1 | 6.567520e12 s = 208,112 yr |
| K_Planck | 1/l_P⁴ | 1.465e139 m⁻⁴ |
| r_QG | (48 G² M² l_P⁴ / c⁴)^{1/6} | 1.387739e-16 m = 4.699e-38 r_s |

Sources: CODATA 2022 (Mohr, Newell, Taylor & Tiesinga, Rev. Mod. Phys. 97, 025002 (2025)) for
G = 6.67430(15)e-11, ħ (exact) and l_P = 1.616255(18)e-35 m — identical to CODATA 2018 (Tiesinga et
al. 2021) [VERIFIED VIA WEB SEARCH]; SI Brochure 9th ed. (2019) for the exact c and h [VERIFIED VIA
WEB SEARCH]; IAU for the Julian year / light-year and IAU 2012 B2 for the au [VERIFIED VIA WEB
SEARCH]; M☉ = 1.98847e30 kg as specified in the brief [PARTIALLY VERIFIED: it equals the IAU 2015 B3
nominal GM☉ divided by the CODATA 2014 G; the brief's ± 7e25 kg has no traced primary source; with
the CODATA 2022 G the ratio is 1.98841e30 kg, 3.0e-5 lower]. Internal consistency check
l_P = √(ħG/c³) passes to 1.5e-8 (TEST 0) [VERIFIED FROM CODE].

## 2. Schwarzschild metric and the ingoing Eddington–Finkelstein chart — EXACT GR RESULT

Schwarzschild coordinates (t, r, θ, φ):

    ds² = −f c² dt² + f⁻¹ dr² + r²(dθ² + sin²θ dφ²),   f = 1 − r_s/r = 1 − 2M/r.

Schwarzschild (1916) [VERIFIED VIA WEB SEARCH]; MTW ch. 31 [PARTIALLY VERIFIED: chapter topic];
Wald §6.1 [PARTIALLY VERIFIED: section title]. The chart is singular at
r = r_s (g_tt → 0, g_rr → ∞) although the geometry is regular there; therefore the horizon crossing
is **never** integrated in (t, r).

Ingoing Eddington–Finkelstein coordinates (v, r, θ, φ), v = t + r_*, dr_*/dr = 1/f,
r_* = r + 2M ln|r/2M − 1| (tortoise coordinate):

    ds² = −f dv² + 2 dv dr + r² dΩ².

Eddington (1924), Finkelstein (1958) [VERIFIED VIA WEB SEARCH]; MTW §31.4 and Box 31.2 [section
number from memory — INSUFFICIENT DATA TO VERIFY; Box 31.2 is described in search results as holding
Kruskal–Szekeres diagrams]; MTW exercise 31.5 "Eddington–Finkelstein and Kruskal–Szekeres compared"
[PARTIALLY VERIFIED: title from a solution-manual index]; Wald §6.4 [PARTIALLY VERIFIED]; Carroll §5.6
[PARTIALLY VERIFIED]. Metric, inverse (g^{vv} = 0, g^{vr} = 1, g^{rr} = f, g^{θθ} = r⁻²,
g^{φφ} = (r sinθ)⁻²), Christoffel symbols, Riemann tensor and the geodesic right-hand sides are all
finite at r = 2M (TEST 2) [VERIFIED FROM CODE]. This is the chart used for **all** integration.

Kruskal–Szekeres coordinates would also be regular; they are used only for the causal diagram
(§7) because exp(v/4M) overflows for the exterior part of the trajectory and because the EF form
keeps the equations of motion simple.

## 3. Christoffel symbols of the EF metric — EXACT GR RESULT [VERIFIED FROM CODE: sympy]

With f' = df/dr:

    Γ^v_vv = f'/2        Γ^v_θθ = −r          Γ^v_φφ = −r sin²θ
    Γ^r_vv = f f'/2      Γ^r_vr = −f'/2       Γ^r_θθ = −r f      Γ^r_φφ = −r f sin²θ
    Γ^θ_rθ = 1/r         Γ^θ_φφ = −sinθ cosθ  Γ^φ_rφ = 1/r       Γ^φ_θφ = cotθ

(all others zero). Re-derived symbolically by `tools/derive_ef_curvature.py`.

## 4. Timelike worldline — EXACT equations, NUMERICAL solution

Second-order geodesic equation with optional 4-acceleration a^μ:

    du^μ/dτ = −Γ^μ_αβ u^α u^β + a^μ,    dx^μ/dτ = u^μ,

explicitly (`slab.geodesic.rhs_tau`):

    du^v/dτ = −(f'/2)(u^v)² + r[(u^θ)² + sin²θ (u^φ)²]
    du^r/dτ = −(f f'/2)(u^v)² + f' u^v u^r + r f[(u^θ)² + sin²θ (u^φ)²]
    du^θ/dτ = −(2/r) u^r u^θ + sinθ cosθ (u^φ)²
    du^φ/dτ = −(2/r) u^r u^φ − 2 cotθ u^θ u^φ.

MTW §25.2 (geodesic equation) [section number from memory — INSUFFICIENT DATA TO VERIFY];
Wald §3.3 "Geodesics" [VERIFIED VIA WEB SEARCH: section title].

Constants of motion (Killing vectors ∂_v and ∂_φ) and normalization:

    E = f u^v − u^r = −u_v,    L = r² sin²θ u^φ,    g(u,u) = −f (u^v)² + 2 u^v u^r + r²[(u^θ)² + sin²θ (u^φ)²] = −1.

Initial data at r₀ with given (E, L), inward (`initial_state_radial`):

    u^r = −√(E² − f(1 + L²/r²)),   u^v = (1 + L²/r²)/(E + |u^r|)   [this root is regular at f = 0],
    u^φ = L/(r² sin²θ).

The independent variable is τ outside where a turning point can occur (E < 1 or L ≠ 0) and
**ln r** inside the horizon and along the E = 1 radial fall (where u^r < 0 is guaranteed):
dy/d(ln r) = (dy/dτ) · r/u^r. Conditioning of E and g(u,u): deep inside, f u^v and u^r are both
~√(2M/r) (10¹⁹ at r_QG) while E = O(1), so E evaluated from the 4-velocity cancels
catastrophically; the engine carries E as its own state variable (dE/dτ = 0 for geodesics,
−a_v with thrust) and reports the *conditioned* drift (E(u) − E_k)/max(|f u^v|, |u^r|)
(TEST 7). The same holds for g(u,u) when L ≠ 0 (u^φ = L/r² ~ 10⁷⁴ at r_QG). [VERIFIED FROM CODE]

Cross-check formulation (first integrals, `rhs_first_integral_lnr`): u^r and u^v reconstructed
from (E, L) at each step; agrees with the second-order integration to 5e-13 in τ (TEST 8).

## 5. Analytic E = 1 radial free fall — EXACT GR RESULT [VERIFIED FROM CODE]

With x = √(r/2M):

    dr/dτ = −√(2M/r) = −c √(r_s/r)          u^v = x/(1 + x)
    τ(r) = −(4M/3) x³ + const   ⇒   τ(r_s → 0) = 4M/3 = 4GM/(3c³)
    v(r) = −4M B(x) + const,   B(x) = x³/3 − x²/2 + x − ln(1 + x) = Σ_{n≥4} (−1)ⁿ xⁿ/n
    t(r) = v − r_*  (→ +∞ as r → r_s: coordinate freezing).

MTW §25.5 (radial geodesics, eq. 25.38 family), §31.4 for the EF form [section/equation numbers
from memory — INSUFFICIENT DATA TO VERIFY; ch. 25 contains the table-of-contents entry "Cycloid
relation between r and t for straight-in fall" — PARTIALLY VERIFIED]; Taylor & Wheeler 2000 ch. 3 "Plunging" [VERIFIED
VIA WEB SEARCH: chapter title]. The series form of B(x) is used for x < 0.05 to avoid cancellation.
Fall from rest at r₀ (E² = f(r₀)) follows the cycloid r = (r₀/2)(1 + cos η),
τ = √(r₀³/8M)(η + sin η) (MTW eq. 25.38 [equation number from memory — INSUFFICIENT DATA TO
VERIFY]) — checked to 2e-12 in `tests/test_physics.py` [VERIFIED FROM CODE].
Benchmark (numbers regenerated with every run; see `validation_report.json` / `docs/validation_report.md`
for the current values): numerical τ(r_s → r_QG) matches 4M/3 to ~1e-13 relative (TEST 4) and u^r
matches −√(2M/r) to ~1e-11 at every step (TEST 3).

## 6. Propulsion — EXACT equations, NUMERICAL solution

Constant proper acceleration α along the local radial axis:

    a^μ = −(α/|n|) n^μ,   n = (u^v, E, 0, 0),   |n|² = g(n,n) = 1 + r²[(u^θ)² + sin²θ (u^φ)²].

n is orthogonal to u (g(n,u) = u^v(−f u^v + u^r + E) = 0), continuous through the horizon, and
outward-pointing outside (n^r = E > 0). Consequences: g(u,u) = −1 is preserved by the continuous
equations, g(a,a) = α² (unit test), and dE/dτ = −a_v = −(α/|n|) u^r. No massive observer can
locally exceed c: the 4-velocity stays normalized (monitored) and the speed relative to the local
E = 1 free-faller, v_rel = √(1 − 1/γ²) with γ = −g(u, u_ff), is < 1 by construction.

Physics note (wording corrected 2026-09-25 after checking the citation): once inside the horizon every
observer reaches r = 0 in finite proper time. The longest possible remaining time from the horizon is
πGM/c³, along the free-fall geodesic with E = 0 (EXACT GR RESULT: ∫₀^{2M} dr/√(2M/r − 1) = πM,
checked in `tests/test_citations.py`); an observer who enters with E > 0 can lengthen the remaining
time with suitably directed thrust, but only up to that maximum (Lewis & Kwan 2007, PASA 24(2),
46–52, whose abstract states that rockets "can increase your remaining time, but only up to a
maximum value") [VERIFIED VIA WEB SEARCH]. The thrust implemented here, a = −α n/|n|, always raises
E (dE/dτ above, u^r < 0) and therefore shortens the remaining time of every observer with E > 0 —
which includes everyone who entered from outside. (The previous wording, "any thrust shortens the
remaining proper time; the geodesic maximizes it", overstated the paper.) The 1 g
scenario (`data/scenarios/thrust_1g`) illustrates the exterior counterpart: 17.3 proper years to
the horizon and 0.0097 yr inside, versus 208,112 yr for free fall.

Exact energy law of the radial rocket (EXACT GR RESULT, derived in `docs/additions/engine.md` §1.2):
with L = 0, |n| = 1 and dE/dτ = −α u^r = −α dr/dτ, so **E(r) = E₀ + α (r₀ − r)** while the engine is on
(geometrized). For 1 g, α = 1.61180e5 c⁴/(GM) and E = 3.19136e7 at the horizon; the integrated E_k
follows this law to ~1e-13 at the milestones and ~3e-9 at every step (TEST 9). Thrust windows
(`thrust_r_on_min/max_over_rs`) split segments at the window edges so that the right-hand side is
smooth within each piece (a window edge inside a segment previously caused a Zeno-like stall).

## 7. Kruskal–Szekeres and compactified coordinates — EXACT GR RESULT

    V_K = e^{v/4M},   U_K = −(r/2M − 1) e^{r/2M} e^{−v/4M},   T = (V_K + U_K)/2,   X = (V_K − U_K)/2,
    T² − X² = U_K V_K = (1 − r/2M) e^{r/2M}   (r = const are hyperbolae; r = 2M ⇔ U_K = 0 ⇔ T = ±X;
    r = 0 ⇔ T² − X² = 1).

Kruskal (1960) [VERIFIED VIA WEB SEARCH], Szekeres (1960) [VERIFIED VIA WEB SEARCH: journal, volume,
pages]; MTW §31.5 [section number from memory — INSUFFICIENT DATA TO VERIFY]; Wald §6.4 "The Kruskal
extension" [PARTIALLY VERIFIED: section title]. The expression for
U_K is smooth through r = 2M. Compactified (Penrose-type) coordinates: Ũ = atan U_K, Ṽ = atan V_K,
T̃ = (Ṽ + Ũ)/2, X̃ = (Ṽ − Ũ)/2, in which the future singularity is the line Ũ + Ṽ = π/2 and the
horizon Ũ = 0. LABELLING CONVENTION: the Schwarzschild time origin (an exact symmetry) is chosen
so that the observer crosses the horizon at v = 0 (V_K = 1), otherwise e^{v/4M} overflows for the
exterior part of the worldline.

## 8. Light cones and causal structure — EXACT GR RESULT

Radial null directions in the EF chart: ingoing dv = 0; outgoing dr/dv = f/2. In terms of
t_EF = v − r: dr/dt_EF = −1 (ingoing) and f/(2 − f) (outgoing) — equal to +1 far away, 0 on the
horizon (the outgoing generator lies on r = r_s) and → −1 as r → 0. Inside r_s both future null
generators, hence every future-directed causal curve, have dr < 0: the singularity is in the
future of every observer, not at a place. (MTW Box 31.2 [section number from memory — INSUFFICIENT
DATA TO VERIFY]; MTW exercise 31.2 "Nonradial light cones" [PARTIALLY VERIFIED: title from a
solution-manual index]; Hawking & Ellis §5.5 "The Schwarzschild and Reissner–Nordström solutions"
[VERIFIED VIA WEB SEARCH: section title].) The observer's worldline slope
dr/dt_EF = u^r/(u^v − u^r) lies inside the cone at every
step (stored with the trajectory). In Kruskal/compactified coordinates all radial light cones are
at 45° (VISUALIZATION of the same fact).

## 9. Curvature — EXACT GR RESULT [VERIFIED FROM CODE: sympy + einsum contraction]

Independent covariant Riemann components in the EF coordinate basis, general f(r):

    R_vrvr = f''/2          R_vθvθ = r f f'/2          R_vθrθ = −r f'/2
    R_rθrθ = 0              R_θφθφ = r²(1 − f) sin²θ   (φ analogues with sin²θ)

For Schwarzschild: −2M/r³, M f/r, −M/r, 0, 2Mr sin²θ — all finite at r = 2M.

Kretschmann scalar:

    K = R_abcd R^abcd = f''² + 4f'²/r² + 4(1 − f)²/r⁴ = 48 M²/r⁶ = 48 G² M²/(c⁴ r⁶).

Henry (2000), ApJ 535, 350–353 [VERIFIED VIA WEB SEARCH]. (Correction 2026-09-25: MTW exercise
31.1, previously cited here, is the exercise "Tidal forces on infalling explorer" according to a
solution-manual index — it belongs to §10, not to the Kretschmann scalar.) TEST 5 computes K by explicit
index contraction of the components above and matches 48M²/r⁶ to 4e-16 at r = 100 … r_QG,
including r = 2M. Values: log₁₀ K(r_s) = −84.8 m⁻⁴, log₁₀ K(r_QG) = 139.17 m⁻⁴ = log₁₀ K_Planck.

Planck-curvature radius (definition + NUMERICAL root, TEST 6):

    48 G² M²/(c⁴ r_QG⁶) = 1/l_P⁴  ⇒  r_QG = (48 G² M² l_P⁴/c⁴)^{1/6} = 1.387739e-16 m,

found also by a log-space Brent root (agreement 3e-15) and by a 40-digit mpmath evaluation
(agreement 2e-15); the brief's 1.39e-16 m is reproduced to 0.16 %.

## 10. Tidal gravity — EXACT GR RESULT for the tensor, linear (geodesic-deviation) approximation for Δa

Geodesic deviation: D²ξ^i/dτ² = −E_ij ξ^j with E_ij = R_{μανβ} e_i^μ u^α e_j^ν u^β in the comoving
orthonormal frame (MTW §31.2 eq. 31.6 and §37.2 [section/equation numbers from memory —
INSUFFICIENT DATA TO VERIFY; ch. 37 is "Detection of gravitational waves"]; MTW exercise 31.1 "Tidal
forces on infalling explorer" [PARTIALLY VERIFIED: title from a solution-manual index]; Wald §3.3
[VERIFIED VIA WEB SEARCH: section title]). The relation
Δa = −λ L between the eigenvalue λ and the relative acceleration across a proper length L is the
*weak-separation (linear) approximation* — exact for the tensor, first order in L/r for a finite
body.

In the frame of any radially moving observer the curvature 2-form of ds² = −f dv² + 2 dv dr +
r² dΩ² is diagonal with A = R_0101 = f''/2, B = R_0202 = R_0303 = f'/2r, C = R_2323 = (1 − f)/r²,
R_1212 = R_1313 = −B; because R_1212 = −R_0202 these components are invariant under radial boosts
(this is why the Schwarzschild tidal field is the same for a static and for a radially infalling
observer, at any speed). Removing the observer's radial velocity by such a boost leaves only the
transverse rapidity t² = r²[(u^θ)² + sin²θ (u^φ)²] = L²/r² (equatorial), and the tidal matrix
becomes block-diagonal with **exact eigenvalues**

    λ_radial = A(1 + t²) − B t²,   λ_⊥ = B(1 + t²) + C t²,   λ_∥ = B,
    Schwarzschild:  λ = −(M/r³)(2 + 3L²/r²),   +(M/r³)(1 + 3L²/r²),   +M/r³.

Radial motion (L = 0): (−2M/r³, M/r³, M/r³) — radial stretching 2GM L/r³ (identical in form to
the Newtonian expression, but here exact for any radial velocity), transverse compression GM L/r³.
Derivation in this repository (`slab.curvature.tidal_eigenvalues_exact`), cross-checked against
(i) the explicit contraction of the EF Riemann tensor with a Gram–Schmidt comoving tetrad,
(ii) the static-orthonormal-frame Riemann tensor boosted with the observer's velocity (exterior),
(iii) a numeric 4×4 frame matrix (`tests/test_physics.py`). The explicit contraction is kept only
as a cross-check because for L ≠ 0 deep inside it cancels terms of order 10³³³ (NUMERICAL note).
SI: λ_SI [s⁻²] = λ_geo c²/M_m².

**Accelerated (thrusting) observer — inertial term (EXACT GR RESULT to first order in the separation).**
In the proper reference frame of an observer with proper acceleration a^i (non-rotating,
Fermi–Walker transported axes), g₀₀ = −[(1 + a·x)² + R₀ᵢ₀ⱼ xⁱ xʲ] + O(x³); for a free particle momentarily
at rest at ξ, d²ξⁱ/dt² = −aⁱ − aⁱ(a·ξ) − Rⁱ₀ⱼ₀ ξʲ. The differential acceleration relative to a particle
released at the observer is therefore

    δaⁱ = −[ Eⁱⱼ + aⁱ aⱼ ] ξʲ,

so along the thrust axis the inertial part is −a²L (an approach, a²L/c² in SI; zero transversally and
exactly zero with the engine off). The thrust axis is a tidal eigen-direction for every radial
4-velocity, so the radial terms add: `radial_total_diff_m_s2` = −(λ_radial + a²) L. Outputs:
`inertial_diff_radial_m_s2`, `radial_total_diff_m_s2`. For the 1 g rocket a²L/c² = 2.14e-15 m/s² across
2 m; it exceeds the tidal stretch everywhere outside r_x = (2GMc²/a²)^{1/3} = 2.13e-4 r_s (66 ly) and is
negligible inside. Validation (TEST 9, independent of the formula): exact Rindler motion in flat space
(measured −0.09999999978 vs −a²L = −0.1) and a hovering observer in Schwarzschild, where the
tidal-only prediction even has the wrong sign at 1.1 r_s while −(λ + a²)L matches the exact lapse value;
the exported column is also checked against |a| recomputed from the exported 4-acceleration.
Citations: MTW §13.6 "The proper reference frame of an accelerated observer" [VERIFIED VIA WEB SEARCH:
section title; equation numbers INSUFFICIENT DATA TO VERIFY]; Ni & Zimmermann 1978, Phys. Rev. D 17,
1473–1476, doi:10.1103/PhysRevD.17.1473 [VERIFIED VIA WEB SEARCH: bibliographic data; paper text not
checked]. Limitations: first order in L, particles released at rest, no rotation terms (none arise
for radial motion), engine switching modelled as a step. Full derivation and tables:
`docs/additions/engine.md` §1.

The traveller is indestructible by definition: tidal values are displayed (1.99e86 m/s² across 2 m
at r_QG) but never terminate the run.

## 11. Distant-observer quantities — EXACT GR RESULT (r > r_s only)

    t = v − r_*,   dt/dτ = u^v − u^r/f,   dr/dt = u^r/(dt/dτ),
    1 + z = ω_em/ω_∞ = u^v − 2u^r/f   for a radially outgoing photon from the infaller received at infinity
            (for E = 1: 1 + z = 1/(1 − √(r_s/r))).

dr/dt → 0 and 1 + z → ∞ as r → r_s: the distant observer never sees the crossing (apparent
freezing), while the infaller crosses at finite τ (Δτ from r₀ = 100 r_s to r_s: 2.08e8 yr).
Inside the horizon no signal reaches infinity; the corresponding fields are undefined (null).
MTW §31.3–31.4 [section numbers from memory — INSUFFICIENT DATA TO VERIFY]; Wald §6.4 [PARTIALLY
VERIFIED]. Late-time behaviour: the received redshift of a radially emitted signal grows
exponentially with e-folding time 4GM/c³ = 1/κ (surface gravity κ = 1/4M) — standard statement in
C. M. Hirata's Caltech Ph 236 lecture XXIV [VERIFIED VIA WEB SEARCH]; flux e-folding time ~ 1/κ in
Ames & Thorne 1968, ApJ 151, 659 [PARTIALLY VERIFIED: abstract]; κ via Wald §12.5 [PARTIALLY
VERIFIED].

**Received-signal timeline (EXACT GR RESULT; implemented in `src/slab/signals.py`).** The retarded time
u = t − r_* = v − 2r_*(r) is constant along outgoing radial light rays (outgoing dr/dv = f/2), so a distant
static observer receives the signal emitted at (v, r) at t_obs = u + const; `t_receive` = (u − u_start)
GM/c³ is the reception interval since the start signal. Along the emitter's worldline du/dτ = u^v −
2u^r/f = 1 + z (the emitted/received frequency ratio). Near the horizon u^r → −E_h and f ≈ ε/(1 + ε),
ε = r/r_s − 1, so 1 + z ∝ exp(u/4M): the redshift e-folds every 4GM/c³ = 624,336 yr for this hole and
t_receive grows by 4M ln 10 per decade of ε, while the emitter's proper time converges. Outputs:
per-sample `u_ret_geo`, `t_receive_years` (null at and inside r_s) and the `signal_timeline` table
(ε log-spaced down to 1e-12, obtained by integrating the actual scenario — any E, L, thrust — to each
radius) in `data/signal_timeline.csv`, HDF5 `/signal_timeline` and the render export. Validation
(TEST 10): E = 1 closed forms to ~3e-15; 4M d ln(1+z)/du → 1 to ~2e-9 for the E = 1 fall, the 1 g
rocket and the L = 3.5 plunge. Limitations: radial photons only (no intensity or beaming), observer
static at infinity, ε ≳ 1e-14 in double precision. Details: `docs/additions/engine.md` §2.

## 12. Physics-regime labels — LABELLING CONVENTION

* **CLASSICAL GR — VALIDATED**: curvature length ℓ_K = K^{−1/4} ≥ 10 km, i.e. within the range where
  GR has been tested directly (neutron-star surfaces, binary-black-hole mergers have ℓ_K ~ 10–100 km).
* **CLASSICAL GR — EXTREME CURVATURE**: ℓ_K < 10 km down to 10 l_P — classical GR still
  self-consistent but untested; begins at r = 1.0e10 m = 3.4e-12 r_s for this hole.
* **PLANCK-CURVATURE BOUNDARY**: ℓ_K ≤ 10 l_P (K/K_P ≥ 1e-4); the validated run stops at r_QG.
* **SPECULATIVE QUANTUM MODEL**: anything under the toy-model menu.

The thresholds (10 km, 10 l_P) are configuration values, not physics results; the equations are
identical classical GR everywhere up to r_QG.

## 13. Numerical scheme — NUMERICAL APPROXIMATION

Dormand–Prince RK5(4) pair with FSAL and PI-type step control (Dormand & Prince 1980, J. Comput.
Appl. Math. 6, 19–26 [VERIFIED VIA WEB SEARCH]; Hairer, Nørsett & Wanner 1993, §II.4 [PARTIALLY
VERIFIED: embedded formulas and step-size control are in §II.4], §II.5, Table 5.2 and the PI-control
section [section numbers from memory — INSUFFICIENT DATA TO VERIFY]). Error norm
‖δ/(atol + rtol·max(|y|,|y_new|))‖_rms ≤ 1 with atol = 0 (relative-only control) for r, u^v, u^r
(they span 40 decades) and atol = 1e-14 for the O(1) components; rtol = 1e-12 by default.
Independent variable ln r inside (step ≤ 0.05 ⇒ Δlog₁₀K ≤ 0.13 per step: the step in r and τ
shrinks automatically as K ~ r⁻⁶ rises), τ outside with a step limit Δr/r ≤ 0.05. Each milestone
radius is hit exactly (event location by secant iteration on the step length, or by the end point
of the ln r segment). v and τ are integrated per segment (v_seg, τ_seg) with offsets, so their
relative error control stays tight at every scale. The trajectory never steps through r = 0: the
last segment ends at r_QG > 0 by construction (test `test_never_steps_through_r_zero`).
Convergence (TEST 8, step cap lifted): the error of u^r and of τ falls monotonically with rtol from
1e-6 to 1e-12 (the current table is in `docs/validation_report.md`); SciPy DOP853 at rtol 1e-13 agrees
with the analytic τ to ~1e-14. For scenarios WITHOUT a closed form (1 g rocket over the whole run,
L = 3.5 plunge) TEST 8 compares against 35-digit mpmath quadratures of the first integrals
(`src/slab/reference.py`, sharing no code with the Runge–Kutta engine): at rtol = 1e-12 the per-segment
Δτ, Δv and u^r agree to ~1e-11.

Other numerical details (NUMERICAL APPROXIMATION): PI step control with the DOPRI5 coefficients
(β = 0.04); steps shortened to exactly representable x_new − x; a no-progress guard; failed segments
raise instead of being recorded as reached. **Dense output**: Hairer's 4th-order continuous extension of
DOPRI5 (coefficients d₁, d₃…d₇ verified symbolically in `tools/verify_dopri5_dense_output.py`: end
points, Hermite derivatives and all order-4 conditions hold exactly; error ∝ h⁵ numerically); it
refuses to extrapolate outside the integrated range.

Proper time as a double: τ_total ≈ 1333 M is stored with 1e-16 relative resolution, so the last
30 decades of radius (Δτ < 1e-10 τ) are represented exactly in the per-segment increments
(`dtau_segment_geo`), not in τ_total's last digits. The "classical proper time remaining to r = 0"
is a classical-GR extrapolation assuming free fall from the current (E, L): (2/3)√(r³/2GM)/c exactly
for E = 1, L = 0 (and the small-r asymptote for any L = 0 worldline, since u^r → −√(2M/r)); for L ≠ 0
it is the quadrature ∫₀^r dr′/√(E² − f(1 + L²/r′²)), whose small-r behaviour is ∝ r^{5/2}/L because
(u^r)² → 2ML²/r³ there. Thrust is ignored in this estimate.

## 14. What the simulation does NOT claim

* Nothing at or beyond r_QG is computed; at r_QG the program prints
  "PLANCK-CURVATURE THRESHOLD REACHED. CLASSICAL GENERAL RELATIVITY IS NO LONGER RELIABLE.
  NO EXPERIMENTALLY VERIFIED THEORY DETERMINES THE CONTINUATION." and stops.
* The toy models in `src/slab/speculative/` (Hayward 2006, Bardeen 1968, Dymnikova 1992 regular
  black holes) are SPECULATIVE MODELS integrated with the project's EF geodesic code (first-integral
  form, core units) for comparison only — these toy runs are not validated physics; their
  core length (10⁴ l_P here) is an arbitrary choice with no observational basis; inner-horizon
  instabilities are ignored; none is selected as "the answer" (banner: "SPECULATIVE MODEL — NOT
  experimentally established."). Numerical notes: they are integrated in units of their core length
  with the first-integral (E, L) formulation, because inside a de Sitter-like core (f' < 0) the
  second-order u^v equation has an exponentially growing mode (~e per e-fold of r); all three share the
  same de Sitter core radius (for Bardeen g = (2Mℓ²)^{1/3}); the E = 1 infaller approaches r = 0 only
  asymptotically (r ∝ e^{−τ/ℓ}) and the curvature saturates at the de Sitter value K = 24/ℓ⁴
  (log10 K = 124.5 m⁻⁴ for ℓ = 10⁴ l_P, below the Planck value 139.2). Inner-horizon and 1 %-deviation
  radii are found by root finding on f; `tests/test_speculative_models.py` checks the metric functions
  and derivatives against sympy (150-digit evaluation), the de Sitter core (f = 1 − r², K → 24) and
  u^r = −r in the core. The exported proper time is accumulated from the horizon and cannot resolve
  core-scale intervals (~ℓ) in double precision.
* NASA Goddard visualizations (SVS 13326, 2019; SVS 14576/14585, 2024 — see references.md §1) are
  used only as a qualitative reference for the appearance of the exterior (shadow, lensed sky) and
  for visualization methodology; they are not evidence about interior quantum physics.
* The first-person camera (§15) computes every pixel's past light ray exactly, but its star backdrop is
  the Earth's sky placed around a hypothetical hole (illustrative), stars are drawn as blackbody point
  sources, and the default colour tint is qualitative — it is labelled "Qualitative visualization —
  trajectory calculations remain relativistic."

## 15. First-person camera — EXACT ray physics, VISUALIZATION of the sky (CPU, double precision)

The default renderer needs no GPU and works down to r_QG. Full derivations, tests and the table of
the view near r_QG: `docs/additions/camera.md`; architecture: `docs/viewer_architecture.md`.

* **Observer and photons (EXACT GR RESULT, derived here).** Radial observer with Killing energy E:
  a ≡ |u^r| = √(E² − f), u^v = 1/(E + a); comoving radial axis n = (u^v, E) with g(n,n) = 1; the Killing
  vector is ξ = ∂_v = E u + a n. A photon seen in direction d = dₙ n + d⊥ e⊥ (future momentum p = u − d,
  observed frequency 1) has E_ph = E + a dₙ, L = r d⊥, impact parameter b = L/E_ph and frequency ratio
  g = ν_obs/ν_∞ = 1/E_ph.
* **Axial symmetry.** The observer moves radially, so a pixel's fate depends only on the angle to the
  radial axis: a 1D transfer table of the asymptotic sky angle ψ_∞ (orbit integral
  (du/dψ)² = 1/b² − u² + 2u³, adaptive Gauss–Kronrod in scale-free ln r variables; closed-form turning
  radius r_t = (2b/√3) cos(⅓ arccos(−3√3/b))) serves every pixel (NUMERICAL APPROXIMATION: table error
  ≤ max(2e-5 rad, 1e-4|ψ|)). Classification of a past-directed ray is exact from (E_ph, b²) with the
  single effective-potential extremum b² = 27M² at r = 3M; inside the horizon a ray reaches the exterior
  sky only if E_ph > 0 AND b² < 27 (this corrected an earlier classifier). The sky/past boundary
  b² = 27 has closed-form roots; at r = 10M it equals the aberrated static shadow
  cos α′ = (cos α_s + v)/(1 + v cos α_s), sin α_s = (3√3M/r)√(1 − 2M/r), v = √(2M/r), to 1e-12; the
  rendered shadow at 5 r_s matches it to 0.25 % (pixel test). Static shadow formula usually
  attributed to Synge 1966, MNRAS 131, 463 [VERIFIED VIA WEB SEARCH: bibliographic data; formula
  re-derived here].
* **Near r_QG (numbers from the code).** The exterior universe fills essentially the outward
  hemisphere (half-angle 90° + √(r/2) rad); almost all of it is a hugely magnified, redshifted image
  (g ≈ 2e-19 straight up) of a tiny patch around the anti-hole direction, while the rest of the sky
  is squeezed into a ring at the horizontal, blueshifted by g ~ 1e36–5e37 and far narrower than a
  pixel. The other hemisphere shows the past horizon (region III / collapsing matter — not modelled).
  Qualitatively as described in the abstract of Hamilton & Polhemus, arXiv:0903.4717 [PARTIALLY
  VERIFIED: abstract]; see also Hamilton & Polhemus 2010, New J. Phys. 12, 123027 [VERIFIED VIA WEB
  SEARCH: bibliographic data].
* **Sky and colours (VISUALIZATION APPROXIMATION / LABELLING CONVENTION).** 1627 stars with V ≤ 5
  from the d3-celestial package (BSD-3-Clause; data from XHIP, Anderson & Francis 2012), placed with
  the hole towards Sgr A* (illustrative); stars as blackbodies with T from B−V (Ballesteros 2012, EPL
  97, 34008), shifted T → gT (exact for blackbodies), magnification μ = cos α |dα| / (sin ψ |dψ|);
  optional false-colour map of log₁₀ g with a numeric colour bar. An optional float32 GPU mode
  remains (falls back to the CPU renderer below 1e-5 r_s).

## 16. Viewer conventions — LABELLING CONVENTION / VISUALIZATION APPROXIMATION

Details: `docs/additions/viewer.md`. The viewer displays precomputed data and computes only
presentation quantities:

* r, r/r_s at a fractional sample position are exactly 10^log10(r/r_s); the classical time remaining is
  interpolated geometrically (exact for the E = 1 law ∝ r^{3/2}); other columns linearly.
* Light-cone inset slopes f/(2 − f) and −1 are evaluated at the displayed r (exactly vertical at r_s;
  measured from pixels in `tests/viewer/test_pixels_browser.mjs`).
* Playback axes: −log₁₀(r/r_s) (default), −log₁₀(classical τ remaining) (labelled a classical-GR
  extrapolation), and linear τ; all are monotone reparametrizations of the same position.
* The received-signal plot uses the engine's `signal_timeline`; for older exports it falls back to
  u = v − 2r_* from the samples, with 1 + z = u^v − 2u^r/f evaluated at the displayed r.
