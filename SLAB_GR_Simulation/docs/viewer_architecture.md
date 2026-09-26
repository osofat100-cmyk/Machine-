# Viewer architecture (renders/)

The interactive 3D viewer is a static web page that consumes the precomputed
trajectory produced by the Python physics engine.  **No physics is integrated
in the browser except the per-pixel null geodesics of the first-person camera**
(which use the same Eddington–Finkelstein equations as the engine and are
validated separately, see `tests/viewer/`).  The viewer evaluates a few
closed-form Schwarzschild relations on the exported samples (light-cone slopes
f/(2 − f), retarded time u = v − 2r_*, redshift 1 + z = u^v − 2u^r/f) — the same
formulas the engine uses — and only where the engine's own column is absent or
where evaluating the formula at the record's exact radius is more accurate than
interpolating the column (documented in `docs/additions/viewer.md`).

## Files

| file | role |
|---|---|
| `renders/viewer.html` | single page; loads `trajectory_data.js` then `viewer.bundle.js`; compact playback toolbar, help overlay (`?`) |
| `renders/trajectory_data.js` | **generated** by `run_simulation.py`: `window.SLAB_DATA = {...}` |
| `renders/src/main.js` | app entry: state, playback along three axes, keyboard / touch / toolbar controls, PNG export, view switching |
| `renders/src/data.js` | data access: interpolation in log10(r/r_s), playback axes, milestone navigation, retarded time and received-signal timeline, formatting |
| `renders/src/dashboard.js` | real-time panel (§17 of the brief); optional contract columns (reception time, inertial thrust terms) |
| `renders/src/scene3d.js` | Three.js scene: log-radius / linear-local / horizon-neighbourhood / deep-interior / curvature views, third-person camera (mouse and touch), render-then-capture |
| `renders/src/lightcone.js` | light-cone glyph (3D) and (t_EF, r) inset (2D; returns its geometry for pixel tests) |
| `renders/src/causal.js` | Kruskal–Szekeres and compactified (Penrose) diagrams and the received-signal timeline of a distant observer, synchronized |
| `renders/src/firstperson.js` | GPU null-geodesic ray tracer (GLSL) with observer tetrad, aberration and redshift |
| `renders/src/speculative.js` | separate menu "SPECULATIVE QUANTUM-GRAVITY TOY MODELS — NOT ESTABLISHED PHYSICS" |
| `renders/build/build.sh` | esbuild bundling (`three` is vendored under `renders/build/node_modules`) |
| `renders/viewer.bundle.js` | built bundle (committed so the viewer runs from `file://` with no toolchain) |

## Data contract (`window.SLAB_DATA`)

```
{
  banner_log: "LOGARITHMIC VISUALIZATION — NOT TO SCALE",
  banner_firstperson: "Qualitative visualization — trajectory calculations remain relativistic.",
  planck_message: "...",
  metadata: { metric, coordinate_system, integrator, config, derived: {M_kg, M_m, M_s, r_s_m, r_QG_m, K_planck, GM_over_c3_years, ...}, regimes },
  summary: {...},
  milestones: [{slug, label, r_m, r_over_rs, log10_r_over_rs, kind, note, tau_years, regime}],
  n_samples: N,
  samples: { <column>: number[N] | null[N] },     // uniform in log10(r/r_s) plus the milestone radii, decreasing r; nulls where undefined
  speculative: {...},                              // optional (run_simulation.py --speculative)
  signal_timeline: {...}                           // optional, see below
}
```
Columns (all length N; see `slab/io.py::COLUMN_DESCRIPTIONS`): `log10_r_over_rs, r_m, r_over_rs, tau_years,
tau_since_horizon_years, tau_to_center_est_years, v_geo, t_ef_geo, t_schw_geo, t_schw_years, u_v, u_r, E_killing,
norm_residual, K_SI_log10, K_over_Kplanck_log10, curvature_length_m, tidal_radial_SI_per_m, tidal_transverse_SI_per_m,
radial_stretch_m_s2, transverse_compress_m_s2, lc_out_drdtEF, lc_in_drdtEF, worldline_drdtEF, dr_dt_schw,
redshift_1pz_to_infinity, kruskal_U, kruskal_V, kruskal_T, kruskal_X, penrose_Ut, penrose_Vt, penrose_T, penrose_X,
step_h, err_estimate, mode_is_lnr, regime_code (0 validated, 1 extreme, 2 Planck boundary)`.

Geometrized quantities (`*_geo`, `u_v`, `u_r`, `E_killing`) are in units G = c = M = 1 (r_s = 2).

Optional columns and keys of the shared engine/viewer contract (the viewer works without them and falls back as noted):

| key | meaning | fallback when absent |
|---|---|---|
| `samples.u_ret_geo` | retarded time u = v − 2r_*(r) [GM/c³], exterior only | computed from `v_geo`, `r_geo` |
| `samples.t_receive_years` | reception time at a distant static observer of the radial signal emitted at this event, from the start signal [Julian yr]; null inside | (u − u_start)·GM/c³ from the samples |
| `samples.inertial_diff_radial_m_s2` | signed inertial (thrust) relative acceleration across `body_length_m`; exactly 0 with the engine off | dashboard rows hidden (also hidden when the column is 0 everywhere) |
| `samples.radial_total_diff_m_s2` | radial tidal + inertial, positive = separation | — |
| `signal_timeline` | `{note, eps, r_over_rs, t_receive_years, one_plus_z, tau_years, t_schw_years, late_time_efold_years}`, log-spaced in r/r_s − 1 down to ~1e-12 | timeline computed from the exterior samples (ends one sample outside r_s) |

Interpolation (`data.js::atIndex`): columns are interpolated linearly in the sample index, except `r_m`, `r_over_rs`,
`r_geo` (exactly 10^log10(r/r_s), as in the export) and `tau_to_center_est_*` (geometric, exact for the r^{3/2} law).

## Playback variable

The position is always `s = log10(r/r_s)`; the playback axis only chooses how it advances in time
(`data.js::AXES`, all three are monotone re-parametrizations of the same position, so switching never moves it):

| axis | progress coordinate | use |
|---|---|---|
| `logr` (default) | −log10(r/r_s), constant rate in decades per second | whole range, 39.3 decades |
| `logtau` | −log10(τ remaining), τ remaining = `tau_to_center_est_years` (classical-GR extrapolation) | constant rate in decades of proper time remaining: the 2.08×10⁸-yr exterior fall and the last 10⁻⁴³ s are both watchable (59 decades) |
| `tau` | τ / τ_end (linear) | exterior only: 99.9 % of τ is spent outside 0.1 r_s; below ~1 AU τ_total no longer resolves in double precision and playback reaches r_QG in one frame |

Each coordinate is made strictly increasing (cumulative maximum plus a tiny increment) so playback can never stall on
flat or missing data; axes whose column is missing are disabled in the selector. The position readout always shows
the true r, r/r_s, τ and the classical τ remaining.

## Controls

Keyboard: Space play/pause · ←/→ step along the playback axis (Shift: fine) · Home/End · [ / ] previous/next milestone ·
+/− speed · 1–4 tabs · ? help · Esc close help. Keys are ignored while a select or text field has focus and never take
Ctrl/Cmd/Alt combinations. Toolbar buttons duplicate every playback action for touch users (≥ 32 px, 44 px on
coarse pointers). 3D view: OrbitControls with one-finger orbit and two-finger pinch/pan (`touch-action: none` on the
canvas); the light-cone inset and text overlays let touches through.

## PNG export

The **PNG** button composites the active view into one image with a caption strip (r, r/r_s, log10(r/r_s), τ,
τ since horizon, classical τ remaining, regime, the view's required banner text, and the Planck-threshold message at
r_QG). WebGL views are rendered and copied in the same task (render-then-capture; no `preserveDrawingBuffer`):
3D = WebGL canvas + light-cone inset; causal = its three canvases; first person = `view.getCanvas?.()` or the first
canvas of its container after forcing a frame; speculative = its two plot canvases with their titles.
`SLAB_APP.capture()` returns the composited canvas (used by the tests).

## Tests

| test | kind | what it asserts |
|---|---|---|
| `tests/viewer/test_viewer_data.mjs` | Node | axes monotone and invertible, exact r interpolation, milestone navigation, fallback signal timeline vs the analytic E = 1 solution, late-time slope 1/(4M), engine-contract consumption |
| `tests/viewer/test_pixels_browser.mjs` | Chromium | light-cone generators measured from the inset pixels (vertical at r_s, outward outside, inward inside); causal and signal-timeline markers at the pixels predicted from the data; diagram frames verified by probing analytic curves; monotone playback on every axis; mock engine export |
| `tests/viewer/test_controls_browser.mjs` | Chromium | keyboard, toolbar, touch gestures (CDP touch events), PNG download and content, HiDPI canvas layout |
| `tests/viewer/check_viewer.mjs` | Chromium | smoke test + screenshots of every view, then runs the two browser test modules above |
| `tests/viewer/causal_check.mjs` | Chromium | causal view at several positions, layouts and panel modes, null-sample robustness |

## First-person camera (physics)

**Default renderer: double precision on the CPU, no WebGL** (`firstperson_cpu.js`); the float32 GLSL shader
(`firstperson_gpu.js`) is created only if the user selects "GPU (float32, r > 1e-5 r_s)" (disabled with a note
when the browser has no WebGL; below 1e-5 r_s the view falls back to the CPU path, labelled).  All pure-physics
modules (`firstperson_core.js`, `firstperson_table.js`, `firstperson_cpu.js`, `firstperson_sky.js`,
`starcatalog.js`, `data/*.js`) import no DOM/WebGL and are tested directly under Node.

Observer: radial, `E = E_killing` of the sample (1 for the main run), `r = 2 r_over_rs` (units GM/c²);
`a = |u^r| = sqrt(E² − 1 + 2/r)`, `u^v = 1/(E + a)` (exact for any radial unit 4-velocity, well conditioned from
r = 100 r_s down to r_QG).  Tetrad `e0 = u`, `e1 = n = (u^v, E)` (outward radial, unit), `e2 = ∂_θ/r`,
`e3 = ∂_φ/(r sinθ)`.  A pixel's unit view direction `d = dn e1 + dperp e⊥` receives the future-directed photon
`p = u − d` (observed frequency 1).  Closed forms (EXACT GR RESULTS, Killing vector `ξ = ∂_v = E u + a n`):
```
E_ph = E + a dn,   L = r dperp,   b = L/E_ph,   g = ν_obs/ν_∞ = 1/E_ph,
past-directed ray moves outward in r  iff  a + E dn > 0.
```
**Kind** (exact, `classify()`): exterior inward → past horizon iff `r ≤ 3M` or `b² ≤ 27M²`; exterior outward →
past iff `2M < r < 3M` and `b² > 27M²`; interior → exterior sky iff `E_ph > 0` **and** `b² < 27M²` (the `b²`
condition was missing before 2026-09; those rays turn at `r_t < 3M` and end on the past horizon).  The sky/past
boundaries are the roots of `(27a² + r²) dn² + 54 E a dn + 27E² − r² = 0`,
`dn± = (−27Ea ± |r−3| sqrt(r(r+6))) / (27a² + r²)`; at `r = 10M` this reproduces the aberrated static shadow
`cos α' = (cos α_s + v)/(1 + v cos α_s)` to 1e-12.

**Sky angle** `ψ_∞` (angle, seen from the hole, between the observer's outward radial direction and the source
direction at infinity, in the ray plane): the orbit integral `ψ = ∫ dw / sqrt(1 − w² + 2w³/b)` (`w = b/r`), evaluated
by adaptive Gauss–Kronrod quadrature in the scale-free variables `w`, `1/r` (substitution `w = w0 e^{−s}`,
`s = ln(r/r0)`, i.e. integration in ln r) for monotone rays, and with `w = w_t − y²` through the turning point
`r_t = (2b/√3) cos(⅓ arccos(−3√3/b))` for exterior rays that bounce.  Nothing over/underflows down to r ~ 1e-300.

**Axial symmetry → 1D transfer table** (`firstperson_table.js`): kind and g are per-pixel closed forms; only
`ψ_∞` is tabulated, as a function of the elevation `α = asin(dn)` outside the horizon and of `b ∈ [0, √27)`
inside (deep inside, the part of the sky away from the zenith lives in directions within ~r^{3/2} of the
sky-cone edge, below the double spacing of `α` but resolved in `b`).  Seeds: uniform/geometric grids plus geometric
sequences towards every `b² = 27` divergence; adaptive midpoint bisection until linear interpolation is within
`max(2e-5 rad, 1e-4 |ψ|)`.  A coarse table (≈100 samples, ~5 ms) is used for the first frame, the refined one
(500–1600 samples, 10–80 ms) for the final image.

**Pixel shading** (`CpuRenderer`): `ψ` from the table, sky direction `cos ψ n + sin ψ t` (`t` = the pixel's
azimuth), rotated into celestial J2000 by a fixed frame (`firstperson_sky.js`: the hole is placed, ILLUSTRATIVELY,
towards Sgr A*, RA 266.4168°, Dec −29.0078°; the anti-hole direction is the observer's zenith; screen up at start =
celestial north projected).  Backgrounds: **star catalogue** (default; 1627 stars V ≤ 5 from d3-celestial ←
XHIP, forward-mapped: images where `ψ(α) = Ψ + 2πk` or `2π − Ψ + 2πk`, magnification
`μ = cos α dα / (sin ψ dψ)`, blackbody colour at `g T`, `m_obs = m − 2.5 log10(μ Y(gT)/Y(T))`) or
**coordinate grid** (RA/Dec every 15°, anti-aliased with the local sky-per-pixel scale).  Layers: qualitative tint
(labelled) or **false colour log10 g** with a labelled symmetric colour scale.  Past-horizon directions: dark red
(hatched grey in false colour); unresolved (quadrature failure, essentially never): magenta.
Progressive: block sizes 8 → 4 → 2 → 1, ≤ 24 ms of work per animation frame; coarse table → coarse image →
table refinement → full image.

**Overlays**: banner "Qualitative visualization — trajectory calculations remain relativistic." + explanation
line; r in m, r_s and GM/c²; exact fractions of all directions (sky / past horizon) and of the current image
(sky / past / unresolved); inside the horizon the sky-cone half-angle and what the other directions show.
`getCanvas()` returns a canvas with the image plus baked-in banner, caption and colour scale (for screenshots).

**Validation**: `tests/viewer/test_firstperson.mjs` (Node: table vs quadrature vs EF integration at random
directions from 200 M to r_QG; rays from 1e-30, 1e-37 M and r_QG conserve E_ph, L; classifier vs unconditioned
EF integration; rendered shadow radius at 5 r_s vs analytic within 2 %; renderer in Node; interior cone; star
mapping flat limit), `tests/viewer/test_null_geodesics.mjs` (EF equations: conservation, deflection, capture,
horizon crossing, exact shadow edge), `tests/viewer/test_firstperson_browser.mjs` (headless: CPU default, no
WebGL context, r_QG render, false-colour scale, `getCanvas()`, playback frame time, optional GPU mode + fallback).
