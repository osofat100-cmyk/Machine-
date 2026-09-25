# First-person camera upgrade (branch `up/camera`, upgrade-prompt item 2, redesigned for users with no GPU)

For the coordinator: merge the equations/citations below into `physics_notes.md`, the user-facing parts into
`README.md` (Viewer paragraph: the first-person camera is now a **double-precision CPU renderer valid down to
r_QG**, no longer "GPU, disabled below 1e-5 r_s"), and update the `renders/src/firstperson.js` row of the Files
table in `docs/viewer_architecture.md` (not my section) to: "first-person camera view (CPU default, optional GPU);
physics in firstperson_core/table/cpu/sky.js, star data in starcatalog.js + data/".

## What changed

| file | change |
|---|---|
| `renders/src/firstperson_core.js` | rewritten physics core: exact observer state from (r, E); closed-form photon E_ph, L, b, g; **fixed** `classify()` (interior rays need b² < 27 as well as E_ph > 0); closed-form sky/past boundaries (`b27Roots`), exact solid-angle fractions (`skyFractions`); orbit-integral quadrature `psiInfExact` / `psiOfB` (adaptive Gauss–Kronrod, heap-ordered, scale-free variables); EF geodesic integrator `traceRay` now adaptive Dormand–Prince 5(4) with component-scaled relative error (works from r = 1e-37 M); `traceForward`, `deriv`, `rk4`, `stepSize`, `observerFrame`, `fOf` kept |
| `renders/src/firstperson_table.js` (new) | 1D transfer table ψ_∞(α) outside / ψ_∞(b) inside, adaptive refinement, progressive `refine(budgetMs)` |
| `renders/src/firstperson_cpu.js` (new) | pure-JS progressive CPU renderer (ImageData RGBA), star splats, `cameraAxes()` |
| `renders/src/firstperson_sky.js` (new) | celestial frame (hole placed toward Sgr A*, illustrative), RA/Dec grid with anti-aliasing, blackbody colours, log10 g colour map, star-image forward mapping |
| `renders/src/starcatalog.js` (new), `renders/src/data/stars_mag5.js`, `renders/src/data/make_star_catalog.mjs` | 1627 stars V ≤ 5.0 (HIP, RA, Dec, V, B−V) extracted from d3-celestial 0.7.35 `data/stars.6.json`, with attribution |
| `renders/src/data/blackbody_srgb.js`, `renders/src/data/make_blackbody_table.py` | Planck × tabulated CIE 1931 2° colour-matching functions → sRGB chromaticity and log10 Y, log T = 2.5…7.0 |
| `renders/src/firstperson_gpu.js` (new) | the old float32 GLSL tracer, now OPTIONAL (created only on explicit selection), with the fixed classifier and the same celestial grid |
| `renders/src/firstperson.js` | view class: CPU default, controls (renderer, resolution, background, colour layer, star exposure, FOV, look buttons), labels, colour scale, `getCanvas()`; same interface `constructor/update/resize/setMode/dispose` + new `getCanvas()` |
| `tests/viewer/test_firstperson.mjs` (new), `tests/viewer/test_firstperson_browser.mjs` (new), `tests/viewer/test_null_geodesics.mjs` | see "Tests" |
| `docs/viewer_architecture.md` | section "First-person camera (physics)" rewritten |

Generated/not committed: `renders/viewer.bundle.js`, `renders/screenshots/*`.

## Equations (units G = c = M = 1, r_s = 2; tags as required)

1. **Observer state** — EXACT GR RESULT (normalization of a radial 4-velocity with Killing energy E = f u^v − u^r):
   `a ≡ |u^r| = sqrt(E² − f) = sqrt(E² − 1 + 2/r)`, `u^v = (E + u^r)/f = 1/(E + a)` (second form avoids 0/0 at r = 2M
   and cancellation for r → 0).  Tetrad `n = (u^v, E)` has g(n, n) = f(u^v)² − 2u^v u^r = 1 exactly.
2. **Killing vector in the comoving frame** — EXACT GR RESULT: `ξ = ∂_v = E u + a n` (check: −ξ·u = E, ξ·n = −u^r = a,
   ξ·ξ = −E² + a² = −f).  For the photon seen in direction `d = dn n + dperp e⊥` (future momentum `p = u − d`, observed
   frequency 1): `E_ph = −p·ξ = E + a dn`, `L = r dperp`, `b = L/E_ph`, frequency ratio `g = ν_obs/ν_∞ = 1/E_ph`,
   radial motion of the past-directed ray: outward iff `a + E dn > 0`.  (Standard Killing-vector algebra, derived
   here; no specific textbook equation is cited.)
3. **Classification** — EXACT GR RESULT (effective potential b² ≤ r²/f(r) = r³/(r − 2), single minimum 27 at r = 3):
   see `classify()`.  **Correction:** inside the horizon a past-directed ray with E_ph > 0 enters region I through
   the future horizon moving outward; it escapes only if b² < 27, otherwise it turns at r_t < 3 and ends on the past
   horizon.  The previous code called every E_ph > 0 interior ray 'sky' and then integrated those rays until they
   failed (drawn magenta).  Verified by unconditioned EF integration (test 3/3b).
4. **Sky/past boundaries** — EXACT GR RESULT (derived here): `b² = 27` ⇔
   `(27a² + r²) dn² + 54 E a dn + 27E² − r² = 0`, `dn± = (−27Ea ± |r − 3| sqrt(r(r + 6)))/(27a² + r²)` using
   `r³ − 27r + 54 = (r − 3)²(r + 6)`; E_ph at a root `= (E r² ∓ a |r−3| sqrt(r(r+6)))/(27a² + r²)` (used to pick the
   physical roots without cancellation).  Solid-angle fractions follow exactly because dn is uniformly distributed on
   the sphere.  At r = 10M (E = 1) the root equals the aberrated static shadow `cos α' = (cos α_s + v)/(1 + v cos α_s)`,
   `sin α_s = (3√3/r) sqrt(1 − 2/r)`, `v = sqrt(2/r)`, to 1e-12 (test 4a).  The static-observer shadow formula is the
   one usually attributed to Synge (1966), MNRAS 131, 463–466, doi:10.1093/mnras/131.3.463 (bibliographic data
   confirmed by web search; that the formula appears in this exact form in the paper: INSUFFICIENT DATA TO VERIFY — it
   is re-derived here from b_c = 3√3 M and sin α = b sqrt(f)/r).
5. **Asymptotic sky angle** — EXACT GR RESULT (orbit equation `(du/dψ)² = 1/b² − u² + 2u³`, u = 1/r) evaluated by
   NUMERICAL APPROXIMATION (adaptive Gauss–Kronrod G7/K15, rtol 1e-10, accepted at 1e-7 when the photon-sphere
   near-singularity limits the attainable accuracy):
   * no turning point: `ψ = ∫_0^{w0} dw/sqrt(1 − w² + 2w³/b) = ∫_0^∞ w ds / sqrt(1 + w²(2/r − 1))`,
     `w = w0 e^{−s}`, `1/r = e^{−s}/r0` (integration in s = ln(r/r0); only ratios appear, so r0 = 1e-37 is harmless),
     breakpoints at r = 2 and r = 3, analytic tail `w1` beyond r ≥ 1e3 with w1 ≤ 1e-10;
   * exterior turning point: `r_t = (2b/√3) cos(⅓ arccos(−3√3/b))` (largest root of r³ − b²r + 2b² = 0),
     `1 − w² + 2w³/b = (w_t − w) Q(w)`, `Q(w) = (1 − 2/r_t)(w + w_t) − (2/b)w²`, `w = w_t − y²`:
     `ψ = ∫_0^{√w_t} 2dy/√Q + ∫_0^{√(w_t − w0)} 2dy/√Q` (smooth integrands; Q(w_t) = 2w_t(1 − 3/r_t) → 0 gives the
     logarithmic photon-sphere winding).
6. **EF integration (independent check)** — NUMERICAL APPROXIMATION of the EF null geodesic equations (unchanged
   Christoffel symbols): Dormand–Prince 5(4), relative error per component scaled by r, |ψ| + |h k^ψ|, |k^ψ|, and the
   momentum scale K = |k^r| + |f k^v| + r|k^ψ|; asymptote `ψ + atan2(r k^ψ, k^r)` at r = 1e7 M; 'past' when an exterior
   ray approaches r = 2 inward or an interior ray reaches v < v0 − 40 (approach to the horizon towards region III).
   Limitation: for view directions within ~1e-19 rad (at r_QG) of the sky-cone edge E_ph ≪ |k^r|, so E_ph computed
   from EF components cancels catastrophically — intrinsic to EF components, not to the renderer (which never uses
   EF components).
7. **Transfer table** — NUMERICAL APPROXIMATION (piecewise-linear interpolation of item 5, error ≤ max(2e-5 rad,
   1e-4 |ψ|) enforced by midpoint tests; intervals narrower than 2e-6 rad in α or 1e-10 relative in b are left as
   they are, sub-pixel).  kind and g are never interpolated (closed forms per pixel).
8. **Star images** — EXACT mapping given ψ(α); magnification `μ = dΩ_obs/dΩ_sky = cos α |dα| / (sin ψ |dψ|)` (EXACT
   for the axisymmetric map, VISUALIZATION APPROXIMATION through the table slope; capped at 1e8 near the axis where
   the Einstein ring forms).
9. **Star colours / brightness** — VISUALIZATION APPROXIMATION: stars as blackbodies, T from B−V by
   Ballesteros (2012), EPL 97, 34008, `T = 4600 K [1/(0.92(B−V) + 1.7) + 1/(0.92(B−V) + 0.62)]` (formula and reference
   confirmed by web search, arXiv:1201.1809); a frequency shift maps a blackbody of temperature T to one of
   temperature gT (EXACT: I_ν/ν³ invariance); visible luminance ratio Y(gT)/Y(T) from the Planck × CIE 1931 2°
   table (tabulated colour-matching functions shipped with colour-science 0.4.7; sRGB matrix IEC 61966-2-1);
   `m_obs = m − 2.5 log10(μ Y(gT)/Y(T))`.  Display mapping (limiting magnitude 6.5 + exposure, splat size) is a
   LABELLING CONVENTION.
10. **Colour layers** — qualitative tint (brightness ∝ clamp(g, 0.45, 4), hue shift; VISUALIZATION APPROXIMATION,
    labelled "qualitative"); false colour log10 g on a symmetric range ±L, L = the extreme |log10 g| over all sky
    directions (g monotone in dn), colour bar with numbers (LABELLING CONVENTION).
11. **Celestial placement** — LABELLING CONVENTION / illustrative: the hole's direction is put at the J2000 position of
    Sgr A* (RA 17h45m40.0409s, Dec −29°00′28.118″, confirmed by web search); the observer's zenith (anti-hole
    direction) is the opposite point; screen-up when looking at the hole = celestial north projected.  The SLAB is
    hypothetical and its r_s (312,000 ly) exceeds the Milky Way, so the Earth's star field is a backdrop only.

## Star data and licences

* d3-celestial 0.7.35 (npm), © 2015 Olaf Frohn, BSD-3-Clause (LICENSE file read in the installed package).
* **The package's readme names its star source as "XHIP: An Extended Hipparcos Compilation; Anderson E., Francis C.
  (2012) [VizieR V/137D]", not the HYG database** as the upgrade brief assumed.  XHIP: Astronomy Letters 38, 331–346
  (2012), arXiv:1108.4971 (confirmed by web search).  No separate data licence is stated in the package beyond its
  BSD licence: licence of the underlying catalogue INSUFFICIENT DATA TO VERIFY (acknowledgement given in the data
  module header and on screen).
* Committed extract: `renders/src/data/stars_mag5.js` (1627 stars, V ≤ 5.0, 60 kB) produced by
  `renders/src/data/make_star_catalog.mjs`.

## The view near r_QG (numbers from `firstperson_core.js`, E = 1 infall)

Deep inside, `a = sqrt(2/r) ≫ 1`.  All quantities below are from `skyFractions`, `psiInfExact`, `psiOfB`:

| r [GM/c²] | sky-cone half-angle (exterior universe) | g straight outward | ψ_∞ at view angle 45° from outward | ψ_∞ looking horizontally | view-angle width of the band showing ψ_∞ ≥ 1 rad | g in that band |
|---|---|---|---|---|---|---|
| 1.9 | 137.04° | 0.494 | 0.412 rad | 1.04 rad | 0.65 rad | 0.97 – 2.7 |
| 1 | 126.73° | 0.414 | 0.350 | 0.942 | 0.53 rad | 1.07 – 5.2 |
| 0.1 | 102.67° | 0.183 | 0.161 | 0.601 | 0.085 rad | 2.5 – 52 |
| 1e-3 | 91.28° | 2.19e-2 | 1.98e-2 | 0.178 | 2.2e-4 rad | 98 – 5.2e3 |
| 1e-6 | 90° + 7.07e-4 rad | 7.07e-4 | 6.43e-4 | 2.08e-2 | 8.0e-9 rad | 8.7e4 – 5.2e6 |
| 1e-10 | 90° + 7.07e-6 rad | 7.07e-6 | 6.43e-6 | 1.02e-3 | 8.0e-15 rad | 8.7e8 – 5.2e10 |
| 1e-30 | 90° + 7.07e-16 rad | 7.07e-16 | 6.43e-16 | 2.17e-10 | 8.0e-45 rad | 8.7e28 – 5.2e30 |
| **r_QG = 9.40e-38** | **90° + 2.17e-19 rad** | **2.17e-19** | **1.97e-19 rad** | **1.54e-13 rad** | **2.3e-55 rad** | **9.2e35 – 5.5e37** |

What the observer sees at r_QG (all established classical GR, valid up to r_QG; nothing beyond r_QG is shown):

* The exterior universe fills essentially the **outward hemisphere**: a cone of half-angle 90° + sqrt(r/2) =
  90° + 2.17e-19 rad (limit of `dn_+ → −E/a`, test 6).  The other hemisphere shows light from the past horizon
  (not modelled).  Sky fraction of all directions: 1/2 + 1.1e-19.
* The outward hemisphere is **not** a compressed image of the whole sky: every direction more than ~1e-13 rad above
  the horizontal plane shows a **hugely magnified image of a tiny patch of the sky around the zenith** (the
  anti-hole direction): at 45° the ray comes from 2e-19 rad from the zenith; looking horizontally, 1.5e-13 rad.
  This patch is **redshifted** by g = 1/(1 + a cos θ) ≈ 2e-19 (straight up), rising to g = 1 exactly in the
  horizontal plane (E_ph = E there).
* **The whole rest of the sky** (source angles ψ_∞ ≳ 1 rad from the zenith, including the multiply wound
  photon-sphere images) is squeezed into a **ring at the horizon line**, within 2.3e-55 rad of the sky-cone edge
  (just below the horizontal plane), **blueshifted by g ~ 1e36 – 5.5e37**.  This band is ~1e20 times narrower than the
  double-precision spacing of view angles near the horizontal (~5e-35 rad), so no pixel can show it; the renderer
  resolves it only in the b-parametrized table (star images then all land on the horizon row).
* Scaling (from the table): cone excess and outward g ∝ sqrt(r/2); ψ_∞(45°) ∝ r^{1/2}; ψ_∞(horizontal) ∝ r^{1/3};
  band width ∝ r^{3/2}; band blueshift ∝ 1/r.

Comparison with the literature: Hamilton & Polhemus, arXiv:0903.4717 ("The edge of locality: visualizing a black
hole from the inside", 2009) — its abstract (confirmed by web search) states that near the singularity the
observer's view is aberrated by the diverging tidal force into a horizontal plane, highly blueshifted in the
horizontal plane and highly redshifted in all other directions.  Our numbers reproduce that qualitatively and add
the scalings above.  The companion paper Hamilton & Polhemus, "Stereoscopic visualization in curved spacetime: seeing
deep inside a black hole", New J. Phys. 12, 123027 (2010), doi:10.1088/1367-2630/12/12/123027, arXiv:1012.4043 —
bibliographic data confirmed by web search; whether it contains the same statement or numbers: INSUFFICIENT DATA TO
VERIFY (full text not accessible from this environment).  Note the upgrade brief's expectation "exterior sky
compressed into a shrinking cone around the outward direction" is **not** what the equations give: the sky cone
tends to a hemisphere, and the compression is into the horizontal ring.

## Tests added and results (all run in this worktree)

* `node tests/viewer/test_firstperson.mjs` — ALL PASSED:
  1. table lookup vs direct quadrature at 600 random directions for r = 200, 10, 3.5, 2.5, 2, 1.5, 1, 1e-3, 1e-10,
     1e-30 M and r_QG: worst error ≤ 0.25 × tolerance (0 beyond 2 × tol), no unresolved rays; EF-integrated rays
     agree with the quadrature (worst relative ψ difference 7.5e-10) and with the closed-form g (≤ 4e-16 after
     conditioning);
  2. EF rays from r = 1e-30, 1e-37 M and r_QG (dn = 0.999, 0.5, 0.1, 1e-3) reach the sky; |ΔE_ph/E_ph| ≤ 5e-9,
     |ΔL/L| ≤ 3e-9; ψ_∞ equals the quadrature to < 1e-6 relative (values down to 9.7e-21 rad);
  3. `classify()` vs EF integration with the classifier disabled: 76 rays on both sides of every b² = 27 boundary at
     r = 10, 3.5, 2.5, 1, 0.3 M — no disagreement; the interior E_ph > 0, b² > 27 ray ends on the past horizon;
  4. **pixel content**: 601 × 601 image at r = 5 r_s looking at the hole (FOV 60°, CPU path): measured shadow radius
     17.310° vs analytic 17.324° (worst of 8 directions 0.25 %, requirement 2 %); closed-form boundary = analytic to 1e-12;
  5. the CPU renderer runs under Node at r = 200, 2, 0.2 M and r_QG (progressive levels, finite pixels);
  6. interior sky cone: closed form = bisection on the classifier; r_QG edge = −sqrt(r/2) to 1e-12;
  7. star forward mapping in the flat limit (r = 1e7 M): primary images within 4.5e-4 rad (= v) of the stars, |ln μ| ≤ 9e-4;
  8. Ballesteros T(B−V = 0.65) = 5778 K, blackbody colours sane; 9. closed-form turning radius residual 3e-16.
* `node tests/viewer/test_null_geodesics.mjs` — ALL PASSED (a–g).  Fixed: the file called `process.exit()` before
  test (f), which therefore never ran; (e) now bisects the shadow edge with unconditioned EF integration and compares
  with the exact aberrated formula at 0.1 % (was 25 % vs the static estimate); (g) quadrature = EF integration (1.5e-10 rad).
* `node tests/viewer/test_firstperson_browser.mjs` (after `renders/build/build.sh`) — ALL PASSED: CPU default without
  a GPU tracer; `getCanvas()` content; r_QG render (half sky / half past, labels, colour scale); playback median frame
  56 ms in software rendering; optional GPU mode renders with SwiftShader and falls back to CPU below 1e-5 r_s; zero
  console errors.  Screenshots `renders/screenshots/fpcam-*.png` (not committed).
* `node tests/viewer/check_viewer.mjs` — zero console errors; fp screenshots inspected.
* `python3 -m pytest tests -q` — 26 passed (no Python files changed).

## Known limitations

* The Earth's star field (V ≤ 5) is an illustrative backdrop at infinity; no extended sources (Milky Way band,
  galaxies); stars are blackbodies (no spectral lines, no extinction); the star display mapping is a convention.
* Linear interpolation in the table: sky angles near the b² = 27 divergences are exact only to the table tolerance;
  directions within 2e-6 rad (α table) of a divergence show the last sampled winding (sub-pixel).
* The band that carries the whole sky deep inside (width ~r^{3/2}) is not visible in pixels (physically correct: it
  is far below any angular resolution); its star images are drawn on the horizon row with their physical (tiny)
  visible-band brightness, so they are normally invisible.
* The EF integrator cannot conserve E_ph for view directions within ~r^{1/2} of the sky-cone edge deep inside
  (component cancellation); the renderer uses the conserved-quantity formulation there.
* Observer is assumed radial (L = 0), as in the main run and all current scenarios; the plunge_L3.5 scenario would
  need a non-axisymmetric (2D) transfer function.
* GPU mode keeps the old float32 RK4 with the asymptote taken at r = 400 M (sky-angle error up to ~2M/400 rad in the
  far field) and shows the grid only; it is optional and labelled.
* Resolution of the CPU image defaults to half the display resolution ("medium"); "full" costs ~4× more CPU time.
