// Real-time dashboard (brief §17).  Pure DOM; no physics here.
import { fmt } from './data.js';

const REGIMES = ['CLASSICAL GR — VALIDATED', 'CLASSICAL GR — EXTREME CURVATURE', 'PLANCK-CURVATURE BOUNDARY', 'SPECULATIVE QUANTUM MODEL'];

export class Dashboard {
  constructor(el, data) {
    this.el = el; this.data = data;
    const d = data.derived, cfg = data.meta.config;
    this.static = {
      'Black-hole mass': `${fmt.sci(cfg.M_solar, 3)} M☉ = ${fmt.sci(d.M_kg)} kg`,
      'Schwarzschild radius r_s': `${fmt.sci(d.r_s_m)} m = ${d.r_s_ly.toLocaleString(undefined, { maximumFractionDigits: 0 })} ly`,
      'GM/c³': `${fmt.sci(d.GM_over_c3_years)} yr`,
      'r_QG (K = 1/l_P⁴)': `${fmt.sci(d.r_QG_m)} m`,
      'Coordinate system': data.meta.coordinate_system,
      'Integrator': data.meta.integrator,
    };
    this.el.innerHTML = '';
    this.regimeEl = document.createElement('div'); this.regimeEl.className = 'regime r0';
    this.el.appendChild(this.regimeEl);
    this.live = document.createElement('div'); this.live.className = 'kv';
    this.el.appendChild(this.live);
    this.distant = document.createElement('div');
    this.el.appendChild(this.distant);
    this.staticEl = document.createElement('div'); this.staticEl.className = 'kv';
    this.el.appendChild(this.staticEl);
    this.staticEl.innerHTML = '<div class="section" style="grid-column:1/3">Black hole & method</div>' +
      Object.entries(this.static).map(([k, v]) => `<div class="k">${k}</div><div class="v" style="white-space:normal;text-align:left">${v}</div>`).join('');
  }
  update(smp, state) {
    const rtol = this.data.meta.config.rtol;
    const reg = state.speculative ? 3 : (smp.regime_code ?? 0);
    this.regimeEl.className = `regime r${reg}`;
    this.regimeEl.textContent = REGIMES[reg];
    const inside = smp.log10_r_over_rs <= 0;
    const stepDesc = smp.mode_is_lnr >= 0.5
      ? `Δln r = ${fmt.sci(smp.step_h, 3)}  (Δr = ${fmt.sci(smp.step_h * smp.r_m, 3)} m)`
      : `Δτ = ${fmt.sci(smp.step_h * this.data.derived.M_s, 3)} s`;
    const rows = [
      ['Current r', fmt.metres(smp.r_m)],
      ['Current r / r_s', fmt.sci(smp.r_over_rs, 6)],
      ['log10(r / r_s)', smp.log10_r_over_rs.toFixed(4)],
      ['Proper time elapsed τ', fmt.years(smp.tau_years)],
      ['Proper time since horizon', inside ? fmt.years(smp.tau_since_horizon_years) : 'not yet crossed'],
      ['Classical τ remaining to r = 0', `${fmt.years(smp.tau_to_center_est_years)} (extrapolated GR)`],
      ['Kretschmann K', `${fmt.log10(smp.K_SI_log10)} m⁻⁴`],
      ['K / K_Planck', fmt.log10(smp.K_over_Kplanck_log10)],
      ['Curvature length K^(-1/4)', fmt.metres(smp.curvature_length_m)],
      ['Radial tidal acceleration', `${fmt.sci(smp.radial_stretch_m_s2, 3)} m/s² across ${this.data.meta.config.body_length_m} m (stretch)`],
      ['Transverse tidal acceleration', `${fmt.sci(smp.transverse_compress_m_s2, 3)} m/s² (compress)`],
      ['Tidal eigenvalues', `${fmt.sci(smp.tidal_radial_SI_per_m, 3)} / ${fmt.sci(smp.tidal_transverse_SI_per_m, 3)} s⁻² per m`],
      ['4-velocity (u^v, u^r)', `${fmt.sci(smp.u_v, 5)}, ${fmt.sci(smp.u_r, 5)}`],
      ['Killing energy E', fmt.sci(smp.E_killing, 6)],
      ['Current coordinate system', 'ingoing Eddington–Finkelstein (v, r, θ, φ)'],
      ['Numerical timestep', stepDesc],
      ['Local error estimate', `${fmt.sci((smp.err_estimate ?? 0) * rtol, 2)} (rel; tol ${fmt.sci(rtol, 1)})`],
      ['|g(u,u)+1|', fmt.sci(Math.abs(smp.norm_residual ?? 0), 2)],
      ['Light-cone slopes dr/dt_EF', `out ${smp.lc_out_drdtEF.toFixed(4)}, in ${smp.lc_in_drdtEF.toFixed(1)}, worldline ${smp.worldline_drdtEF.toFixed(4)}`],
    ];
    this.live.innerHTML = '<div class="section" style="grid-column:1/3">Infalling observer (proper-time view)</div>' +
      rows.map(([k, v]) => `<div class="k">${k}</div><div class="v">${v}</div>`).join('');
    const dist = inside
      ? [['Schwarzschild time t', '→ ∞ at the horizon (coordinate artefact)'], ['Signals to infinity', 'none: every future light cone points to smaller r'],
         ['Note', 'The distant observer never sees the crossing; the infaller crosses in finite proper time.']]
      : [['Schwarzschild time t', fmt.years(smp.t_schw_years)], ['Coordinate velocity dr/dt', `${fmt.sci(smp.dr_dt_schw, 4)} c (→ 0 at r_s: apparent freezing)`],
         ['Redshift 1+z of infaller\'s light', fmt.sci(smp.redshift_1pz_to_infinity, 4)]];
    this.distant.innerHTML = '<div class="section">Distant observer (Schwarzschild coordinates)</div><div class="kv">' +
      dist.map(([k, v]) => `<div class="k">${k}</div><div class="v" style="white-space:normal;text-align:left">${v}</div>`).join('') + '</div>';
  }
}
