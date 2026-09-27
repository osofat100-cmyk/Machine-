# Viewer upgrade (viewer2): log-τ playback, keyboard/touch controls, PNG export, received-signal timeline, pixel tests

Scope: upgrade-prompt items 8 (viewer polish) and 5 (viewer side of the distant-observer signal timeline).
Files changed: `renders/src/{main,data,dashboard,causal,scene3d,lightcone,speculative}.js`, `renders/viewer.html`,
`tests/viewer/{check_viewer,causal_check}.mjs`, new `tests/viewer/test_viewer_data.mjs`,
`tests/viewer/test_pixels_browser.mjs`, `tests/viewer/test_controls_browser.mjs`, `docs/viewer_architecture.md`
(all sections except "First-person camera (physics)"), this file. `firstperson*.js` untouched (interface unchanged).
No engine file, no generated artefact is part of this change.

Tags as in `physics_notes.md`: EXACT GR RESULT · NUMERICAL APPROXIMATION · VISUALIZATION APPROXIMATION ·
SPECULATIVE MODEL · LABELLING CONVENTION. Citation status: this session had no access to the sources; every
literature citation below is **[citation from memory — not re-verified online]**, given at chapter level only;
section/equation numbers are deliberately not given (**INSUFFICIENT DATA TO VERIFY**). Results marked
**[VERIFIED FROM CODE]** are reproduced numerically by the tests listed at the end.

## 1. What changed for the user

* **Playback along proper time with a log-warped axis.** New axis "log10 τ remaining (GR extrap.)": constant rate in
  decades of the classical proper time remaining to r = 0 (column `tau_to_center_est_years`). The default stays
  log10(r/r_s); the linear-τ axis is kept (exterior use). Switching axes never moves the position. The readout under
  the slider always shows r, r/r_s, τ and "τ remaining ≈ … (GR extrap.)".
* **Keyboard and touch.** Space, ←/→ (Shift = fine), Home/End, [ ], + −, 1–4, ? (help overlay), Esc. A compact
  toolbar (⇤ « ‹ ▶ › » ⇥, speed, axis, slider, readout, PNG, ?) duplicates every action for touch users; buttons
  ≥ 32 px, 44 px on coarse pointers. OrbitControls touch: one finger orbits, two fingers pinch-zoom/pan.
* **PNG export** of the current view with a caption strip (r, r/r_s, τ, remaining time, regime, required banners;
  Planck-threshold message at r_QG).
* **Received-signal timeline** in the causal tab (panel selector: all panels / Kruskal / Penrose / signal): log10(1+z)
  versus reception time t_receive of a distant static observer, (a) whole exterior fall, (b) late-time approach with
  the exact asymptote; current emission point marked; statement that light emitted at or after horizon crossing never
  arrives while the infaller crosses in finite proper time.
* Fixes found on the way: the 3D canvas is now laid out at the container size on HiDPI screens (it was drawn at its
  buffer size and cropped when devicePixelRatio > 1); the light-cone inset text no longer overflows; the 3D overlay
  says "AT the horizon" at r = r_s instead of "INSIDE"; the causal panel area scrolls on small screens instead of
  shrinking the diagrams.

## 2. Equations and conventions used by the viewer

### 2.1 Retarded time and reception time — EXACT GR RESULT (definitions), exterior only

    r_* = r + 2M ln|r/2M − 1|,   u = t − r_* = v − 2 r_*      (G = c = 1, M = 1 in the code)

u is constant along every outgoing radial null ray (outgoing Eddington–Finkelstein / retarded time; same sources as
`physics_notes.md` §2: MTW ch. 31, Carroll ch. 5 — [citation from memory — not re-verified online]). A static observer
at R → ∞ receives the ray at Schwarzschild time t = u + r_*(R), and his proper time is t, so reception-time
*differences* equal differences of u:

    t_receive = (u − u_start) · GM/c³        [Julian years; LABELLING CONVENTION: t_receive = 0 for the start signal]

Undefined (null) for emission at r ≤ r_s: no outgoing ray from there reaches infinity. Used from the engine columns
`u_ret_geo` / `t_receive_years` when exported, otherwise evaluated in `data.js::retardedTimeGeo` from `v_geo`, `r_geo`.

### 2.2 Redshift of the infaller's radially outgoing light — EXACT GR RESULT (`physics_notes.md` §11)

Outgoing radial null covector normalized at infinity (Killing energy 1): k_μ = (k_v, k_r) = (−1, 2/f), since the
outgoing direction is dr/dv = f/2. Then ω_emitted/ω_∞ = −k_μ u^μ:

    1 + z = u^v − 2 u^r / f        (E = 1 radial fall: 1 + z = 1/(1 − √(r_s/r)))

[VERIFIED FROM CODE] against the analytic E = 1 form to 2.4e-5 at every exterior sample (`test_viewer_data.mjs` 4d).

NUMERICAL APPROXIMATION (render export): the export interpolates every column linearly between engine steps. For the
smooth 4-velocity this is accurate (the closed form above reproduces the analytic E = 1 redshift to 2.4e-5), but the
steep `redshift_1pz_to_infinity` column itself deviates by up to 2.1e-2 near r_s. The viewer therefore evaluates the
closed form on (u^v, u^r) at the record's exact r and uses the column only when the 4-velocity is missing. The same
choice is used for the dashboard's 1+z row, the timeline fallback and the current-point marker, so they agree.

### 2.3 Late-time asymptote — EXACT GR RESULT (asymptotic)

Near the horizon, along the infaller's worldline r − 2M ∝ e^{−u/4M} and 1 + z ∝ 1/f, hence

    ln(1 + z) = t_receive / (4GM/c³) + const   (t_receive → ∞),    e-folding time 4GM/c³ = 6.2434e5 yr for this hole.

4GM/c³ = 1/κ with the Schwarzschild surface gravity κ = c⁴/(4GM) (Wald ch. 12; exponential redshift of a collapsing
surface: MTW ch. 32 — [citation from memory — chapter level only; section/equation numbers INSUFFICIENT DATA TO
VERIFY]). [VERIFIED FROM CODE]: from the analytic E = 1 relations u(x) = −4B(x) − 4x² − 4 ln(x² − 1) + const,
1 + z = x/(x − 1), x = √(r/r_s), the slope d ln(1+z)/du equals 1/(4M) to 1.4e-6 for r/r_s − 1 = 1e-6 … 1e-12
(`test_viewer_data.mjs` 5). Drawn as a dashed line through the last timeline point (VISUALIZATION: anchoring point).
The plot concerns radially emitted photons only; the total received flux of an extended emitter (other photon paths)
is not modelled.

### 2.4 Light-cone inset slopes — EXACT GR RESULT (`physics_notes.md` §8), evaluated at the displayed r

    dr/dt_EF = f/(2 − f) (outgoing),  −1 (ingoing),   f = 1 − r_s/r

Evaluated at the record's exact radius instead of interpolating `lc_out_drdtEF` between samples (identical at the
samples; avoids interpolating a nonlinear function). At r = r_s, f = 0 exactly (the record's r/r_s is exactly
10^0 = 1), so the outgoing generator is drawn exactly vertical; the pixel test measures it.

### 2.5 Interpolation of the samples — VISUALIZATION APPROXIMATION / LABELLING CONVENTION

* r_m, r_over_rs, r_geo at a fractional position: exactly 10^log10(r/r_s) (as in the export), not linear interpolation.
* `tau_to_center_est_*`: geometric (log-linear) interpolation between samples — exact for the E = 1 law
  τ_rem = (2/3)√(r³/2GM)/c ∝ r^{3/2} (`physics_notes.md` §13). Accuracy is then limited by the export's own linear
  resampling of the engine steps: 3.3e-4 relative at the samples of the default run (plain linear interpolation: 5.7e-4).
* All other columns: linear in the sample index (unchanged).

### 2.6 Playback axes — LABELLING CONVENTION

Progress coordinates (increase as the fall proceeds), all monotone re-parametrizations of the same position:
s_logr = −log10(r/r_s); s_logtau = −log10(τ_rem) with τ_rem = `tau_to_center_est_years`, a **classical-GR
extrapolation** (exact for E = 1, L = 0 without thrust; a free-fall quadrature otherwise, as labelled by the engine;
nothing beyond r_QG is computed or shown); s_tau = τ/τ_end. Playback advances s at a constant rate (dec/s for the log
axes, 2 %·speed of τ per second for the linear axis). Each s is made strictly increasing (cumulative maximum + 1e-9 dec,
resp. 1e-13) so playback cannot stall on flat or missing data (NUMERICAL APPROXIMATION of the inverse map; exact
for the default data, whose τ_rem is strictly decreasing). For the default E = 1 run s_logtau = 1.5 s_logr + const
end to end (59.0 vs 39.3 decades) [VERIFIED FROM CODE]. The linear-τ axis reaches r_QG in one frame once τ_total stops
resolving in double precision (below ~1 AU): labelled in the help overlay.

### 2.7 PNG caption strip — LABELLING CONVENTION

Caption lines: title and view; r (m and a natural unit), r/r_s, log10(r/r_s); τ, τ since horizon, classical τ remaining
(labelled "classical-GR extrapolation"); regime (SPECULATIVE QUANTUM MODEL in the toy-model menu); the view's required
banner ("LOGARITHMIC VISUALIZATION — NOT TO SCALE" / the linear-view label; "Qualitative visualization — trajectory
calculations remain relativistic."; "SPECULATIVE QUANTUM-GRAVITY TOY MODELS — NOT ESTABLISHED PHYSICS" +
"SPECULATIVE MODEL — NOT experimentally established."); the Planck-threshold message at r_QG.

## 3. Data contract consumed (engine side is not part of this change)

Optional per-sample columns `u_ret_geo`, `t_receive_years`, `inertial_diff_radial_m_s2`, `radial_total_diff_m_s2`
and the top-level `signal_timeline` (see `docs/viewer_architecture.md`). Without them the viewer falls back to the
samples (timeline ends one sample outside r_s, 1+z ≤ 130 for the default export; engine timeline: to r/r_s − 1 ≈ 1e-12,
1+z ≈ 2e12). The inertial rows appear in the dashboard only when the column is non-zero somewhere (engine on); the
reception-time row appears outside the horizon. Tested with a mock export (analytic E = 1 timeline; fabricated
inertial values used only to test the display, never shown in committed material).

## 4. Tests added and results (this worktree, software GL, 2026-09-25)

* `node tests/viewer/test_viewer_data.mjs` (Node, 22 checks) — ALL PASSED: exact r interpolation (8e-15); three axes
  strictly monotone and invertible (round trip ≤ 1e-11 dec); log-τ axis = −log10 τ_rem at the samples; E = 1 slope 1.5;
  τ_rem readout vs analytic (3.2e-4, export-limited); milestone navigation both ways; fallback timeline vs analytic E = 1
  (Δt ≤ 0.10 GM/c³ = 1.6e4 yr, i.e. 6e-5 of the span, from the export's linear resampling of v; 1+z to 2.4e-5); late-time
  slope 1/(4M) to 1.4e-6; engine timeline / column consumption and fallback.
* `node tests/viewer/test_pixels_browser.mjs` (Chromium, 58 checks) — ALL PASSED. Light-cone generators measured from the
  inset pixels: at r = r_s outgoing dr/dt_EF = 0.0 (x-spread 0 px over 51 rows, apex on the axis), ingoing −0.998; outside
  (log r = 0.3, 1.0) 0.3331 / 0.8188 vs f/(2 − f) = 0.3323 / 0.8182; inside (−0.3, −1.0) −0.3331 / −0.834 vs −0.3323 /
  −0.8182 with both generators negative. Kruskal and Penrose markers found within 0.6 px of the pixel predicted from
  kruskal_X/T, penrose_X/T at four positions; diagram frames confirmed by probing the drawn horizon and singularity
  curves at their analytic pixels. Signal-timeline markers within 0.6 px of the predicted pixel in both sub-plots, curve
  through the data, no marker inside r_s, asymptote slope log10(e)/(4GM/c³). Playback: r strictly decreasing, τ
  non-decreasing, τ_rem strictly decreasing on all three axes and across axis switches (no jump), constant rate to
  1e-13 on the log axes, readout at r_QG "τ remaining ≈ 6.689e-44 s". Mock engine export: timeline consumed (301 points,
  log10(1+z) to 12.3), late slope = asymptote to 1e-6, dashboard rows. Mutation check: a 0.05 error in the outgoing slope
  and a 2-px marker offset both make the tests fail.
* `node tests/viewer/test_controls_browser.mjs` (Chromium, 55 checks) — ALL PASSED: every key binding, focused-select
  keys not hijacked, toolbar buttons (mouse and touch tap), no double activation of Space after a click, one-finger
  orbit (Δazimuth 1.59 rad) and two-finger pinch (distance 83.5 → 20.9) via CDP touch events, `touch-action: none`,
  PNG download for 3D (log and linear), causal, first-person, speculative and r_QG (valid PNG, size = capture,
  non-blank image region, caption with all required texts), HiDPI canvas layout.
* `node tests/viewer/check_viewer.mjs` now also runs the two browser modules (111 checks) after the screenshot steps
  (20 steps incl. signal-only panel, log-τ axis deep inside, help overlay): zero console errors, all checks passed.
* `node tests/viewer/causal_check.mjs`: new steps for the signal-only mode (outside/inside), the panel selector, narrow
  and 1024×700 layouts; zero console errors.
* Unchanged and passing: `python3 -m pytest tests -q` (26), `node tests/viewer/test_null_geodesics.mjs`.

## 5. Known limitations

* Fallback timeline: limited by the exported samples (last exterior sample r/r_s = 1.016, 1+z ≈ 130; t_receive error
  up to 0.1 GM/c³ from the export's linear resampling of v). The engine's `signal_timeline` removes both limits.
* Radial photons only (no total flux / luminosity curve, no finite-distance observer).
* The log-τ axis is exact only for the E = 1, L = 0, unthrusted fall; for thrust scenarios it plays at a constant rate in
  log10 of the engine's free-fall estimate (labelled by the engine), monotone by construction.
* Linear-τ playback cannot resolve the interior below ~1 AU (τ_total is a double); it jumps to r_QG (labelled).
* PNG export rasterizes canvases only: DOM overlays (3D mode label box, shell legend, dashboard, causal DOM caption) are
  replaced by the caption strip. The first-person capture forces a frame through the current interface
  (`dirty` + `update`, or `renderNow()`/`getCanvas()` if the rewritten view provides them); a view that renders
  asynchronously would be captured one frame late.
* Touch was tested with synthetic CDP touch events in headless Chromium only, not on real devices; the phone-width
  layout (fixed 360 px sidebar) is left to the declutter pass. ArrowUp/Down are not bound (left for the camera/scroll).
* The causal tab now shows three panels; below about 900 px of panel height the panel area scrolls.
