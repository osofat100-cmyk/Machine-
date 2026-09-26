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

Observer state at the current sample: `(r, u^v, u^r, E_killing)` (equatorial, radial).  The
comoving tetrad is `e0 = u`, `e1 = n = (u^v, E, 0, 0)/|n|` (local outward radial direction),
`e2 = ∂_θ/r`, `e3 = ∂_φ/(r sinθ)`.  For each pixel with unit view direction `d` in the tetrad,
the past-directed photon momentum is `k = -u + d^i e_i` (so that -k·u = 1 at the eye), and the
null geodesic is integrated in the plane spanned by `n` and `d_⊥` with the EF equations
```
dv/dλ = k^v,  dr/dλ = k^r,  dψ/dλ = k^ψ,
dk^v/dλ = -(M/r²)(k^v)² + r (k^ψ)²,
dk^r/dλ = -(M f/r²)(k^v)² + (2M/r²) k^v k^r + r f (k^ψ)²,
dk^ψ/dλ = -(2/r) k^r k^ψ,
```
(same Christoffel symbols as the timelike engine) until `r > r_sky` (escape: sky direction
`ψ_∞ = ψ + atan2(r k^ψ, k^r)` in the ray plane, with the frequency ratio `g = 1/E_ph`,
`E_ph = f k^v - k^r` of the future-directed momentum) or `v < v_min` (ray traced back to the
past horizon: shown black and labelled), or the step budget is exhausted.  The sky is a
procedural star/grid pattern so that lensing, aberration and the shrinking/expanding view of the
exterior are visible.  Colour mapping of the redshift is qualitative and labelled as such.
