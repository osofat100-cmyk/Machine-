# Engine upgrade notes (branch `up/engine`) — for merging into physics_notes.md / README.md

Scope: upgrade-prompt items 4 (accelerated-observer inertial terms), 5 (engine side: received-signal
timeline) and 7 (numerics polish: dense output, high-precision reference, safe event/step clean-ups).
All results below come from `src/slab/validation.py` (TESTS 8–10) and the new pytest files; every
number can be regenerated with `python run_simulation.py --validate-only`.

Tags as in physics_notes.md: **EXACT GR RESULT**, **NUMERICAL APPROXIMATION**, **VISUALIZATION
APPROXIMATION**, **SPECULATIVE MODEL**, **LABELLING CONVENTION**. Nothing in this upgrade touches the
region beyond r_QG, the speculative toy models or the Planck-threshold stop.

---

## 1. Accelerated observer: inertial (Rindler-type) differential term (thrust mode)

### 1.1 Equation — EXACT GR RESULT (to first order in the separation, like the tidal columns)

In the proper reference frame of an observer with proper acceleration a^i (spatial axes Fermi–Walker
transported = non-rotating; t = the observer's proper time on x = 0) the metric is

    g_00 = -[(1 + a_j x^j)^2 + R_0i0j x^i x^j] + O(x^3),   g_0i = O(x^2),   g_ij = delta_ij + O(x^2).

For a free particle momentarily at rest at x^i = xi^i, dx^i/dt = 0, the geodesic equation gives
d²x^i/dt² = -Gamma^i_00 = (1/2) d_i g_00 (the O(x²) parts of g_0i, g_ij do not contribute at rest), so

    d²xi^i/dt² = -a^i - a^i (a_j xi^j) - R^i_0j0 xi^j + O(xi², velocity terms).

The first term is the uniform "falling behind" of every free particle. The **differential** acceleration of
a free particle at xi relative to one released at the observer is

    delta a^i = -[ R^i_0j0 + a^i a_j ] xi^j = -[ E^i_j + a^i a_j ] xi^j.

**Sign convention:** positive = separation (same as `radial_stretch_m_s2`). Along the thrust axis,
xi = ±L a_hat (ahead or behind — the term is even in xi's direction), the inertial part is **-a² L < 0: an
approach (compression)** of magnitude a² L/c² in SI units. It is zero transverse to the thrust axis
(a_j xi^j = 0) and exactly zero when the engine is off. The engine's thrust axis is n = (u^v, E, 0, 0)/|n|,
which is an eigen-direction of the tidal tensor for every 4-velocity (E_1j = 0 for j ≠ 1 in the conditioned
tetrad — checked for L = 0 and L = 3 in `tests/test_accelerated_frame.py`), so the radial terms simply add:

    radial_total = -(lambda_radial + a²) L          (per unit c² in SI: -(lambda_SI + a²/c²) L).

Derivation of the lapse form (static case, used in the check): for a static metric ds² = -N(xi)² dt² + dxi²
a particle at rest has d²xi/dt² = -N N'; with N(0) = 1, N'(0) = a and N''(0) = R_0101 = lambda_radial,
the expansion gives -a - (a² + lambda) xi, the same formula.

Citations: MTW, *Gravitation* (1973), §13.6 "The proper reference frame of an accelerated observer"
(section title and subject **verified by WebSearch**; MTW give the metric to first order in x, which contains
the -a^i term but not the a² term; equation numbers NOT verified — INSUFFICIENT DATA TO VERIFY).
W.-T. Ni & M. Zimmermann, "Inertial and gravitational effects in the proper reference frame of an accelerated,
rotating observer", Phys. Rev. D 17, 1473–1476 (1978), DOI 10.1103/PhysRevD.17.1473 (**bibliographic data
verified by WebSearch** — APS landing page and Wikidata; the abstract confirms a metric to second order in
distance and equations of motion to first order with inertial, curvature and "red-shift" corrections; that
their g_00 is written as -(1 + a·x)² - R_0l0m x^l x^m is from memory — **not verified against the paper
text**). The formula used here is in any case established independently in this repository by the exact
Rindler comparison below. Related (not used): W.-Q. Li & W.-T. Ni, J. Math. Phys. 20, 1473 (1979), "Coupled
inertial and gravitational effects in the proper reference frame of an accelerated, rotating observer" (title,
journal, volume and page seen in a WebSearch result URL; authors from memory).

### 1.2 Exact energy law for the radial rocket — EXACT GR RESULT (derived here)

With radial thrust of constant proper acceleration alpha (|n| = 1 for L = 0), dE/dtau = -alpha u^r =
-alpha dr/dtau, hence **E(r) = E0 + alpha (r0 − r)** while the engine is on (geometrized). For 1 g,
alpha = 1.61180e5 (unit c⁴/GM) and E = 3.19136e7 at the horizon (matches the scenario table). The engine's
separately carried E_k satisfies it to 1e-13 at the milestones (TEST 8) and to 3e-9 relative at every step (the
maximum sits in the first steps, where r = exp(ln r) is rounded to ~3e-14 and dE/dr = alpha = 1.6e5).

### 1.3 Outputs (per-sample columns: CSV, HDF5 /trajectory, render export samples)

* `inertial_diff_radial_m_s2` = -a² L/c² where the engine is on (L = `body_length_m`), exactly 0 otherwise.
* `radial_total_diff_m_s2` = `radial_stretch_m_s2` + `inertial_diff_radial_m_s2` (positive = separation).

### 1.4 The 1 g scenario honestly compared (thrust_1g, a = 9.81 m/s², L = 2 m)

a² L/c² = **2.142e-15 m/s²** (compression), constant along the whole run. Radial tidal stretching across 2 m
(`radial_stretch_m_s2`, boost-invariant, identical to free fall at the same r):

| milestone | r / r_s | tidal stretch [m/s²] | inertial [m/s²] | |inertial| / tidal |
|---|---|---|---|---|
| start | 100 | 2.06e-32 | -2.14e-15 | 1.0e17 |
| ISCO | 3 | 7.63e-28 | -2.14e-15 | 2.8e12 |
| horizon | 1 | 2.06e-26 | -2.14e-15 | 1.0e11 |
| 0.01 r_s | 1e-2 | 2.06e-20 | -2.14e-15 | 1.0e5 |
| 1 ly | 3.2e-6 | 6.27e-10 | -2.14e-15 | 3.4e-6 |
| r_QG | 4.7e-38 | 1.99e86 | -2.14e-15 | 1.1e-101 |

The two are equal at r_x = (2GM c²/a²)^{1/3} = **2.127e-4 r_s = 6.28e17 m = 66.4 ly** (inside the horizon).
Outside r_x the (tiny) inertial compression dominates the (even tinier) tidal stretching — for this
10¹⁸ M☉ hole a 1 g rocket's own acceleration is the larger differential effect everywhere outside and down to
~66 ly from the centre; both are physically negligible there (< 3e-15 m/s² across 2 m). Inside r_x
curvature takes over and grows as r⁻³ without bound. All values are displayed, never used to stop the run
(indestructible traveller).

### 1.5 Validation — TEST 9 (all pass) and `tests/test_accelerated_frame.py`

Independent numerical checks, no use of the formula being tested:

* **Flat space, exact Rindler** (engine thrust + engine geodesics with a flat `FlatEF` metric f = 1): observer
  worldline vs the exact hyperbola 8e-12; free particles' positions in the observer's instantaneous rest
  frame vs xi_l(tau) = (1/a + l)/cosh(a tau) − 1/a: 7e-12; separation vs L/cosh(a tau): 5e-11 relative
  (shrinks to 0.266 L at a tau = 2); measured differential acceleration at tau = 0: −0.09999999978 vs −a² L =
  −0.1; co-located particle −0.9999999984 vs −a.
* **Schwarzschild, hovering observer held by the engine** (static, outward thrust a = M/(r0²√f0); the rest frame
  is the slice t = const where proper radial distance is exact, F(r) = √(r(r−2M)) + 2M ln(√r + √(r−2M))), free
  particles released from rest at the observer and L = 1e-3 M ahead/behind; second derivative of the separation
  from a polynomial fit:

  | r0 | a²/|lambda| | measured | exact lapse value | −(lambda + a²)L | tidal-only −lambda L |
  |---|---|---|---|---|---|
  | 2 r_s, ahead | 0.25 | +2.34347e-5 | +2.34347e-5 | +2.34375e-5 | +3.125e-5 (33 % off) |
  | 1.1 r_s, ahead | 2.50 | −2.81524e-4 | −2.81524e-4 | −2.81743e-4 | +1.878e-4 (**wrong sign**) |
  | 1.1 r_s, behind | 2.50 | −2.81962e-4 | −2.81962e-4 | −2.81743e-4 | +1.878e-4 (**wrong sign**) |

  Agreement with the exact lapse value 1e-8; with the first-order formula 8e-4 (= O(L/(r0 − 2M))); the observer
  stays at r0 to < 1e-10 (after the round-off clamp of §3.6).
* **Output columns** on thrust_1g: inertial column exactly −a² L/c² at every step; total = sum to 1e-16;
  benchmark free fall: exactly 0; carried energy vs E(r) law (§1.2); thrust window (engine on below 10 r_s only):
  0 above, −a² L/c² below (`test_thrust_columns_window_and_energy_law`).

### 1.6 Limitations

* First order in the separation (as the tidal columns); particles released at rest in the frame (no
  velocity-dependent terms); the frame is non-rotating (Fermi–Walker). For L ≠ 0 the engine's comoving tetrad
  (u, n, e_θ, e_φ) is not proven to be Fermi–Walker transported; Coriolis/centrifugal terms of a rotating
  frame are NOT included (they vanish for radial motion, which is the only thrust scenario shipped).
* The transverse inertial term is zero by construction (a·xi = 0); no transverse column was added.
* Engine switch-on/off transients (jerk) are not modelled: the thrust window is a step function.

---

## 2. Distant-observer received-signal timeline

### 2.1 Equations — EXACT GR RESULT

* Retarded (outgoing null) coordinate **u = t − r_* = v − 2 r_*(r)**, r_* = r + 2M ln|r/2M − 1|.
  Radially outgoing light rays are the lines u = const (from ds² = −f dv² + 2 dv dr: outgoing dr/dv = f/2 ⇔
  dv = 2 dr/f = 2 dr_*), so a distant static observer receives the radial signal emitted at (v, r) at
  t_obs = u + const. **t_receive = (u − u_start) GM/c³** is the reception interval between the start signal and
  the signal from the event.
* Along the emitter's worldline **du/dtau = u^v − 2u^r/f = 1 + z**, the emitted/received frequency ratio of the
  radially outgoing photon (the existing `redshift_1pz_to_infinity`; E = 1: 1 + z = 1/(1 − √(r_s/r))).
  Proof: an outgoing radial null vector has k^v = 2k^r/f (dr/dv = f/2). Lowering with the EF metric,
  k_v = −f k^v + k^r = −k^r and k_r = k^v. The conserved k_v is normalized to −1 (unit frequency at infinity),
  so k^r = 1, k^v = 2/f, k_r = 2/f, and the emitted frequency is −k·u = −(k_v u^v + k_r u^r) = u^v − 2u^r/f.
  Since dr_*/dr = 1/f, du/dtau = u^v − 2u^r/f is the same expression.
* **Late time:** near the horizon u^r → −E_h (finite, any E, L, thrust), f ≈ eps/(1 + eps) with eps = r/r_s − 1,
  so 1 + z ≈ 2E_h/f and u = v − 2r − 4M ln eps + O(eps): **1 + z ∝ exp(u/4M)**. The observed signal e-folds in
  redshift every 4GM/c³ = 1/kappa (surface gravity kappa = 1/4M; for this hole 4GM/c³ = 624,336 yr); t_receive
  → ∞ (logarithmically in eps: 4M ln 10 = 9.2103 GM/c³ = 1.44e6 yr per decade of eps) while the emitter's
  proper time converges. Signals emitted at r ≤ r_s never arrive (columns are null there).
  Citations (all from memory, **not re-verified online**): MTW §31.3–31.4 (apparent freezing/redshift of an
  infaller), Wald §12.5 (surface gravity), Carroll §5.6 (tortoise coordinate). The formulas are verified in
  this repository against the E = 1 closed forms (TEST 10).

### 2.2 Outputs (shared data contract)

Per-sample columns (CSV, HDF5 /trajectory, render samples): `u_ret_geo` (GM/c³; NaN/null at and inside r_s),
`t_receive_years` ((u − u_start) GM/c³ in Julian years; NaN/null inside).

Table `signal_timeline` — render export key `window.SLAB_DATA.signal_timeline`, file `data/signal_timeline.csv`
(written by `io.write_csv` next to trajectory.csv), HDF5 group `/signal_timeline` (attrs: note, method, status,
late_time_efold_years, column_descriptions_json), summary in trajectory_metadata.json
(`signal_timeline_summary`):

    note, eps (r/r_s − 1, log-spaced 20 per decade from the start radius down to 1.0e-12; 281 points for 100 r_s),
    r_over_rs, t_receive_years, one_plus_z, tau_years (emitter proper time since start),
    t_schw_years (Schwarzschild t of emission since the start event), late_time_efold_years (4GM/c³ in yr)

The CSV/HDF5 additionally carry u_ret_geo, tau_geo, t_receive_geo and E_killing. LABELLING CONVENTION: both
t_receive and t_schw are measured from the start event (t_schw_years in the per-sample columns is the absolute
v − r_*, as before). Benchmark (E = 1) at eps = 1e-12: t_receive = 2.635e8 yr, 1 + z = 2.0e12, tau = 2.079e8 yr.
thrust_1g at eps = 1e-12: t_receive = 8.19e7 yr, 1 + z = 6.4e19, tau = 17.31 yr.

### 2.3 Method — NUMERICAL APPROXIMATION

The eps grid resolves the late-time approach that the milestone grid cannot. Default method `exact`: the
emitter state at each requested radius is obtained by integrating to it with the driver's own
`Simulation.integrate_segment` (event-located in tau mode, exact end point in ln r mode) for the general
scenario (any E, L, thrust, thrust window) — no E = 1 closed form is used. Method `dense`: one ln r integration
with the new dense output (available where the exterior is integrated in ln r); used as a cross-check. Near the
horizon f is evaluated as (r − 2M)/r (exact subtraction; 1 − 2M/r loses all digits of f at eps ~ 1e-12), and
the reported eps is that of the double-precision radius actually reached (exact subtraction), not the nominal
target. The per-sample `redshift_1pz_to_infinity` and `dr_dt_schw` columns now also use this f (improves them
in the last steps before the horizon; no change elsewhere).

### 2.4 Validation — TEST 10 (all pass) and `tests/test_signal_timeline.py`

* E = 1: 1 + z vs 1/(1 − √(r_s/r)) over eps = 99 … 1e-12: max rel error 2.9e-15; t_receive vs the closed form
  Δv(r) − 2Δr_*(r): 9.6e-15; dense-output route vs exact route: 2.5e-13 (1+z), 3.6e-12 (t_receive).
* Late-time law for eps ≤ 1e-8: 4M d ln(1+z)/du = 0.9999999978 (E = 1), 0.9999999978 (thrust_1g, E → 3.2e7),
  0.9999999979 (L = 3.5 plunge, tau mode); local deviation ≤ 1.9e-8; t_receive per decade 9.2103404 vs
  4M ln 10 = 9.2103404; emitter proper time over the last 4 decades 2e-8 GM/c³ (6e-16 for the rocket) while
  t_receive advances 36.8 GM/c³; tau(eps_min) equals the main run's horizon-crossing proper time to 1.3e-13.
* E < 1 fall from rest at 10 r_s (turning point at the start): 1 + z(start) = 1/√f0 exactly, same late-time law.
* Export tests: columns present and null inside, CSV/HDF5/JSON/render key written and consistent.

### 2.5 Limitations

* Radial signals only (emitted straight outward); no off-radial rays, intensity, beaming or arrival
  direction; observer static at large r (u is the retarded time at infinity).
* Exterior only by construction (no signal from r ≤ r_s reaches the observer). The start signal is the one
  emitted at the start radius; nothing before the start is modelled.
* Resolution of eps near 1e-12 is limited by double precision of r (ulp(2M) ≈ 4e-16): the effective eps is
  exact, but eps < ~1e-14 would require a horizon-relative variable.

---

## 3. Numerics polish

### 3.1 Dense output — NUMERICAL APPROXIMATION (method verified exactly)

`DormandPrince54.integrate(..., t_eval=..., dense_output=True)`: Hairer's 4th-order continuous extension of
DOPRI5,

    y(x_old + theta h) = r1 + theta (r2 + theta1 (r3 + theta (r4 + theta1 r5))),  theta1 = 1 − theta,
    r1 = y_old, r2 = y_new − y_old, r3 = h k1 − r2, r4 = r2 − h k7 − r3, r5 = h Σ d_i k_i,
    d1 = −12715105075/11282082432, d3 = 87487479700/32700410799, d4 = −10690763975/1880347072,
    d5 = 701980252875/199316789632, d6 = −1453857185/822651844, d7 = 69997945/29380423.

Returns `res.x_eval`, `res.y_eval` (points actually reached, integration order; t_eval may be unsorted) and
`res.dense` (callable on the whole range). The accepted step sequence is identical with and without dense
output (tested bitwise). The event-shortened final step gets its own interpolant. Components changed by an
`after_step` projection are interpolated from the raw RK step (documented; the ln r driver resets r = e^x).

Verification: `tools/verify_dopri5_dense_output.py` (run by pytest) proves with exact rationals and a symbolic
theta that b_i(0) = 0, b_i(1) = b_i (the 5th-order weights: end points exact), b_i'(0) = δ_i1, b_i'(1) = δ_i7
(Hermite match of h k1, h k7), and that **all eight order conditions up to order 4 hold identically in theta**
(and that it is not 5th order — as expected); the tableau's 5th-order weights pass three order-5 conditions.
Source of the coefficients: Hairer & Wanner's DOPRI5 code / Hairer, Nørsett & Wanner I §II.6 (section number
from memory); a WebSearch for the six numerators returned the DOPRI5 sources that contain them (scipy
`dopri5.f`, Numerical Recipes 3 `stepperdopr5.h`, `dde/dopri_5.c`) — pages not fetched (WebFetch blocked), so
the denominators are verified only by the exact order-condition derivation (a mistyped digit breaks it).
Numerical tests: interpolation error at theta = 1/2 scales as h^5 (ratios 24–40 per halving, 2^5 = 32);
E = 1 geodesic (engine RHS, ln r mode) at 400 random off-grid radii 100 r_s → 1e-30 r_s: u^r, u^v, tau, v all
within 1e-9 of the analytic solution; backward integration with an event.

### 3.2 Exactly representable steps (safe clean-up, changes results only at round-off level)

The step is now shortened to the representable x_new − x (never lengthened) before the stages are evaluated.
Previously the stages used hd while the recorded x_new = x + hd was rounded; in ln r mode with Δx ~ 1e-8 at
x ~ 5 this is a 1e-7 relative quantization that accumulated as a phase error (seen as 1.5e-7 relative error of
the carried energy vs the exact law in the first 1 g steps; now 3e-9, the rounding of exp(x) itself). If no
progress is possible (x + h == x) the integrator stops with status `step_size_underflow` instead of spinning.
Benchmark: 3471 steps as before, RHS evaluations 20960 → 20966; all 26 original tests unchanged.

### 3.3 Thrust window bug fix (latent before this upgrade)

A thrust window edge (`thrust_r_on_min/max_over_rs`, engine switching) inside a milestone segment made the
integrator creep towards the jump in dy/dx Zeno-fashion (2 million rejected steps, 264 s, then
`max_steps_exceeded`). Segments are now split at window edges (`Simulation.integrate_segment` → pieces →
`_concat_results`), and the engine state is decided once per piece (at its geometric-mean radius) so the
right-hand side is smooth within each piece. The default window [0, ∞) is unaffected. Covered by
`test_thrust_columns_window_and_energy_law` (0.4 s).

### 3.4 High-precision references for scenarios WITHOUT a closed form (TEST 8 extension)

`src/slab/reference.py`: 35-digit mpmath tanh-sinh quadrature of first integrals (shares no code with the RK
engine), split per decade of r and normalized per piece (mp.quad's stopping test is absolute). Self-test:
tau(r_s → 1e-30 r_s) for E = 1 vs closed form to 2e-36; quadrature error estimates ≤ 3e-38.

* 1 g rocket over the full run r0 = 100 r_s → r_QG (E(r) exact, tau = ∫dr/√(E(r)² − f), v = ∫u^v/|u^r| dr —
  elliptic-type): step cap lifted, per-segment Δtau / Δv / u^r / E errors

  | rtol | steps | Δtau | Δv | u^r | E |
  |---|---|---|---|---|---|
  | 1e-6 | 295 | 6.7e-5 | 2.0e-6 | 6.7e-5 | 1.6e-8 |
  | 1e-8 | 651 | 3.4e-7 | 2.0e-8 | 3.4e-7 | 4.6e-10 |
  | 1e-10 | 1539 | 1.5e-9 | 3.8e-10 | 1.5e-9 | 7.3e-12 |
  | 1e-12 | 3769 | 6.5e-12 | 5.8e-12 | 6.5e-12 | 9.8e-14 |

* L = 3.5 GM/c plunge, 100 r_s → r_QG (tau mode with event-located milestones outside, ln r inside):
  Δtau 4.2e-7 → 4.3e-9 → 4.3e-11, Δv 1.3e-7 → 9.1e-10 → 6.9e-12, accumulated phi 8.0e-8 → 5.6e-10 → 4.3e-12
  for rtol 1e-8, 1e-10, 1e-12 (11968 steps at 1e-12).

Whole validation suite (TESTS 0–10): 12.6 s wall (was 5 s; budget 3 min).

### 3.5 Event interface

Kept unchanged (secant on the step length, end point exactly on an RK step); `_locate_event` and `_rk_step`
now also return the stage matrix of the final step for its dense output. Not replaced by root finding on the
interpolant, to keep milestone states bitwise tied to genuine RK steps.

### 3.6 Round-off clamp at turning points

`initial_state_radial` already set E² − V = 0 for tiny negative round-off; it now also does so for positive
round-off ≤ 8 ulp·max(E², V) (e.g. E = √f(r0) typed for "rest"): √(1e-16) had produced a spurious
u^r ≈ −1e-8 (the hovering observer then drifted 3e-9 M).

---

## 4. Files changed (engine agent)

`src/slab/integrators.py` (dense output, representable steps, no-progress guard), `src/slab/trajectory.py`
(new columns, signal_timeline(), thrust-window splitting, accurate f), `src/slab/io.py` (column descriptions,
signal_timeline CSV/HDF5/JSON/render export), `src/slab/validation.py` (TEST 8 extension, TESTS 9–10),
`src/slab/geodesic.py` (round-off clamp), new `src/slab/accelerated.py`, `src/slab/signals.py`,
`src/slab/reference.py`; `tools/verify_dopri5_dense_output.py` (new), `tools/render_validation_report.py`
(renders the new tables); tests: `tests/test_physics.py` (TEST 9/10 parametrization),
new `tests/test_dense_output.py`, `tests/test_accelerated_frame.py`, `tests/test_signal_timeline.py`.

## 5. Tests and results (this branch)

* `python3 -m pytest tests -q` → **45 passed** (26 original + 2 new TEST ids + 17 new) in ~23 s.
* `python3 run_simulation.py --validate-only` → **11/11 tests passed** (12.6–12.9 s).
* Full run `python3 run_simulation.py --skip-validation --speculative` → new files/keys present
  (data/signal_timeline.csv, /signal_timeline, signal_timeline in trajectory_data.js, 4 new sample columns);
  Planck message printed at r_QG as before; thrust_1g run to scratch: same.
* `node tests/viewer/test_null_geodesics.mjs` → ALL PASSED; `node tests/viewer/check_viewer.mjs` with the new
  export and the unchanged bundle → zero console errors (renders/ not modified by this branch).

## 6. Suggested merges into the shared docs (coordinator)

* physics_notes.md §10 last sentence ("the geodesic-deviation equation acquires extra terms … (not displayed)")
  → replace by §1 above; §11: add u, t_receive, 1 + z = du/dτ and the late-time law (§2.1); §13: dense output,
  representable steps, thrust-window splitting, high-precision references (§3); add TESTS 9–10 to README's
  validation list ("TEST 9 accelerated frame · TEST 10 signal timeline") and update "26 tests" counts.
* PROJECT_STATE.md "Documented, not changed: inertial (Rindler) differential terms … not displayed" → done.
* references.md: add Ni & Zimmermann 1978 (verified bibliographic data above).

## 7. Known limitations (summary)

See §1.6, §2.5. Additionally: phi is stored as an absolute angle (unlike v_seg/tau_seg), so per-segment phi
increments below ~1e-15 rad deep inside are not resolvable (TEST 8 therefore compares accumulated phi);
the mpmath references cover radial thrust with the engine on everywhere and geodesic plunges without turning
points only (no reference for thrust windows or L ≠ 0 with thrust).
