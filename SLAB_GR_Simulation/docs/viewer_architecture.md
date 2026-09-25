# Viewer architecture (renders/)

The interactive 3D viewer is a static web page that consumes the precomputed
trajectory produced by the Python physics engine.  **No physics is integrated
in the browser except the per-pixel null geodesics of the first-person camera**
(which use the same Eddington–Finkelstein equations as the engine and are
validated separately, see `tests/viewer/`).

## Files

| file | role |
|---|---|
| `renders/viewer.html` | single page; loads `trajectory_data.js` then `viewer.bundle.js` |
| `renders/trajectory_data.js` | **generated** by `run_simulation.py`: `window.SLAB_DATA = {...}` |
| `renders/src/main.js` | app entry: state, playback, UI wiring, view switching |
| `renders/src/data.js` | data access: interpolation in log10(r/r_s), milestones, formatting |
| `renders/src/dashboard.js` | real-time panel (§17 of the brief) |
| `renders/src/scene3d.js` | Three.js scene: log-radius / linear-local / horizon-neighbourhood / deep-interior / curvature views, third-person camera |
| `renders/src/lightcone.js` | light-cone glyph (3D) and (t_EF, r) inset (2D) |
| `renders/src/causal.js` | Kruskal–Szekeres and compactified (Penrose) diagrams, synchronized |
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
  metadata: { metric, coordinate_system, integrator, config, derived: {M_kg, M_m, M_s, r_s_m, r_QG_m, K_planck, ...}, regimes },
  summary: {...},
  milestones: [{slug, label, r_m, r_over_rs, log10_r_over_rs, kind, note, tau_years, regime}],
  n_samples: N,
  samples: { <column>: number[N] | null[N] }      // uniform in log10(r/r_s), decreasing r; nulls where undefined
}
```
Columns (all length N; see `slab/io.py::COLUMN_DESCRIPTIONS`): `log10_r_over_rs, r_m, r_over_rs, tau_years,
tau_since_horizon_years, tau_to_center_est_years, v_geo, t_ef_geo, t_schw_geo, t_schw_years, u_v, u_r, E_killing,
norm_residual, K_SI_log10, K_over_Kplanck_log10, curvature_length_m, tidal_radial_SI_per_m, tidal_transverse_SI_per_m,
radial_stretch_m_s2, transverse_compress_m_s2, lc_out_drdtEF, lc_in_drdtEF, worldline_drdtEF, dr_dt_schw,
redshift_1pz_to_infinity, kruskal_U, kruskal_V, kruskal_T, kruskal_X, penrose_Ut, penrose_Vt, penrose_T, penrose_X,
step_h, err_estimate, mode_is_lnr, regime_code (0 validated, 1 extreme, 2 Planck boundary)`.

Geometrized quantities (`*_geo`, `u_v`, `u_r`, `E_killing`) are in units G = c = M = 1 (r_s = 2).

## Playback variable

Proper time is useless as a playback axis (99.9999% of it is spent outside 0.1 r_s and the last
30 decades of radius take < 1e-10 of the total), so the default playback parameter is
`s = log10(r/r_s)` (sample index), with proper time displayed.  A "proper-time playback" mode is
available for the exterior.

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
