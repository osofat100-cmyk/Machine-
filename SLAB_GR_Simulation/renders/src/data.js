// Data access layer for the precomputed trajectory (window.SLAB_DATA).
// Samples are ordered by DECREASING log10(r/r_s); columns may contain null where undefined.
// No physics is integrated here.  The only formulas evaluated are closed-form Schwarzschild relations that the
// engine also uses (tortoise coordinate, retarded time, redshift of a radial photon), applied to the exported
// samples when the engine's own columns are absent (see docs/additions/viewer.md).

const isNum = v => typeof v === 'number' && Number.isFinite(v);

// Columns that are strictly positive power laws of r along the E = 1 fall: interpolated geometrically
// (linearly in log) between samples, which is exact for a pure power law (VISUALIZATION APPROXIMATION otherwise).
const GEOMETRIC_COLUMNS = ['tau_to_center_est_years', 'tau_to_center_est_geo'];

// Playback axes.  Each axis is a "progress coordinate" s that INCREASES as the fall proceeds.
//   logr   : s = -log10(r/r_s)                                   (default; constant rate in decades of radius)
//   logtau : s = -log10(tau_to_center_est_years)                  (constant rate in decades of the classical
//            proper time remaining to r = 0 — a classical-GR extrapolation, nothing beyond r_QG is computed)
//   tau    : s = tau_years / tau_years(end)                       (linear proper time; useful only outside ~0.1 r_s)
export const AXES = {
  logr: { label: 'log10(r / r_s)', unit: 'dec/s', rate: v => v, step: 0.25, fine: 0.01,
    help: 'constant rate in decades of radius (default)' },
  logtau: { label: 'log10 τ remaining (classical-GR extrapolation)', unit: 'dec/s', rate: v => v, step: 0.25, fine: 0.01,
    help: 'constant rate in decades of the classical proper time remaining to r = 0 (column tau_to_center_est_years, a classical-GR extrapolation)' },
  tau: { label: 'proper time τ (linear; exterior)', unit: '% τ/s', rate: v => 0.02 * v, step: 0.01, fine: 0.001,
    help: 'linear in proper time: 99.9 % of τ is spent outside 0.1 r_s, the last 30 decades of r pass in one frame' },
};

export class TrajectoryData {
  constructor(raw) {
    this.raw = raw;
    this.s = raw.samples;
    this.N = raw.n_samples;
    this.meta = raw.metadata;
    this.derived = raw.metadata.derived;
    this.milestones = raw.milestones;
    this.logr = this.s.log10_r_over_rs;           // decreasing
    this.logrMax = this.logr[0];
    this.logrMin = this.logr[this.N - 1];
    this.columns = Object.keys(this.s);
    this.horizonIndex = this._firstIndexBelow(0);
    this._geometric = GEOMETRIC_COLUMNS.filter(k => this.s[k]);
    this._axes = {};
    this._signal = undefined;
    this._u0 = undefined;
  }
  _firstIndexBelow(logr) { for (let i = 0; i < this.N; i++) if (this.logr[i] <= logr) return i; return this.N - 1; }
  clampLogR(x) { return Math.min(this.logrMax, Math.max(this.logrMin, x)); }
  // fractional index for a given log10(r/r_s) (binary search on decreasing array)
  indexOf(logr) {
    logr = this.clampLogR(logr);
    let lo = 0, hi = this.N - 1;
    while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (this.logr[mid] >= logr) lo = mid; else hi = mid; }
    const a = this.logr[lo], b = this.logr[hi];
    const t = (b === a) ? 0 : (logr - a) / (b - a);
    return lo + t;
  }
  // interpolated record at fractional index p
  atIndex(p) {
    const i = Math.max(0, Math.min(this.N - 2, Math.floor(p)));
    const t = Math.max(0, Math.min(1, p - i));
    const out = { index: p };
    for (const k of this.columns) {
      const a = this.s[k][i], b = this.s[k][i + 1];
      if (a === null || b === null || a === undefined || b === undefined || typeof a === 'string' || typeof b === 'string') out[k] = (t < 0.5 ? a : b);
      else out[k] = a + (b - a) * t;
    }
    if (out.regime_code !== null && out.regime_code !== undefined) out.regime_code = Math.round(out.regime_code);
    // radius columns exactly consistent with the log axis (as in the export), not linearly interpolated
    if (isNum(out.log10_r_over_rs)) {
      const x = Math.pow(10, out.log10_r_over_rs);
      if ('r_over_rs' in out) out.r_over_rs = x;
      if ('r_geo' in out) out.r_geo = 2 * x;
      if ('r_m' in out && isNum(this.derived.r_s_m)) out.r_m = x * this.derived.r_s_m;
    }
    for (const k of this._geometric) {
      const a = this.s[k][i], b = this.s[k][i + 1];
      if (isNum(a) && isNum(b) && a > 0 && b > 0) out[k] = a * Math.pow(b / a, t);
    }
    return out;
  }
  at(logr) { return this.atIndex(this.indexOf(logr)); }
  milestone(slug) { return this.milestones.find(m => m.slug === slug); }

  // ------------------------------------------------------------------ milestones navigation
  // dir = +1: next milestone deeper in (smaller r); dir = -1: previous milestone (larger r).  null if none.
  nextMilestone(logr, dir) {
    const tol = 1e-9;
    const ms = this.milestones.filter(m => isNum(m.log10_r_over_rs)).slice().sort((a, b) => b.log10_r_over_rs - a.log10_r_over_rs);
    if (dir > 0) return ms.find(m => this.clampLogR(m.log10_r_over_rs) < logr - tol) || null;
    for (let i = ms.length - 1; i >= 0; i--) if (this.clampLogR(ms[i].log10_r_over_rs) > logr + tol) return ms[i];
    return null;
  }

  // ------------------------------------------------------------------ playback axes
  // Monotone progress coordinate per sample: nulls filled by linear interpolation in the index (clamped at the ends),
  // then made strictly increasing (cumulative max plus a tiny increment) so that playback can never stall.
  _monotone(vals, eps) {
    const N = this.N, idx = [];
    for (let i = 0; i < N; i++) if (isNum(vals[i])) idx.push(i);
    if (idx.length < 2) return null;
    const s = new Float64Array(N);
    let j = 0;
    for (let i = 0; i < N; i++) {
      if (i <= idx[0]) { s[i] = vals[idx[0]]; continue; }
      if (i >= idx[idx.length - 1]) { s[i] = vals[idx[idx.length - 1]]; continue; }
      while (idx[j + 1] < i) j++;
      const a = idx[j], b = idx[j + 1];
      s[i] = vals[a] + (vals[b] - vals[a]) * (i - a) / (b - a);
    }
    for (let i = 1; i < N; i++) if (!(s[i] > s[i - 1])) s[i] = s[i - 1] + eps;
    return s;
  }
  axis(name) {
    if (this._axes[name] !== undefined) return this._axes[name];
    let s = null;
    if (name === 'logr') s = Float64Array.from(this.logr, x => -x);
    else if (name === 'logtau') {
      const c = this.s.tau_to_center_est_years;
      if (c) s = this._monotone(c.map(v => (isNum(v) && v > 0 ? -Math.log10(v) : null)), 1e-9);
    } else if (name === 'tau') {
      const c = this.s.tau_years;
      if (c) {
        let end = -Infinity; for (const v of c) if (isNum(v) && v > end) end = v;
        if (end > 0) s = this._monotone(c.map(v => (isNum(v) ? v / end : null)), 1e-13);
      }
    }
    this._axes[name] = s;
    return s;
  }
  axisAvailable(name) { return !!AXES[name] && !!this.axis(name); }
  axisRange(name) { const s = this.axis(name); return s ? [s[0], s[this.N - 1]] : [0, 1]; }
  // progress coordinate s of the axis at a given log10(r/r_s)
  axisAt(name, logr) {
    const s = this.axis(name); if (!s) return NaN;
    const p = this.indexOf(logr), i = Math.max(0, Math.min(this.N - 2, Math.floor(p))), t = Math.max(0, Math.min(1, p - i));
    return s[i] + (s[i + 1] - s[i]) * t;
  }
  // inverse: log10(r/r_s) at progress coordinate v (clamped to the data range)
  logrAtAxis(name, v) {
    const s = this.axis(name); if (!s) return this.logrMax;
    if (!(v > s[0])) return this.logrMax;
    if (v >= s[this.N - 1]) return this.logrMin;
    let lo = 0, hi = this.N - 1;
    while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (s[mid] <= v) lo = mid; else hi = mid; }
    const t = (v - s[lo]) / (s[hi] - s[lo]);
    return this.logr[lo] + (this.logr[hi] - this.logr[lo]) * t;
  }
  // backwards-compatible helper (linear proper-time axis)
  logrForTauFraction(f) { const [a, b] = this.axisRange('tau'); return this.logrAtAxis('tau', a + f * (b - a)); }

  // ------------------------------------------------------------------ distant observer: retarded time and received signal
  // Retarded (outgoing Eddington–Finkelstein) time u = v - 2 r_*(r), r_* = r + 2M ln|r/2M - 1| (G = c = M = 1).
  // Exterior only (null inside the horizon).  Uses the engine's u_ret_geo column when present.
  retardedTimeGeo(rec) {
    if (!rec) return null;
    if (isNum(rec.u_ret_geo)) return rec.u_ret_geo;
    const r = isNum(rec.r_geo) ? rec.r_geo : (isNum(rec.log10_r_over_rs) ? 2 * Math.pow(10, rec.log10_r_over_rs) : NaN);
    if (!(r > 2) || !isNum(rec.v_geo)) return null;
    return rec.v_geo - 2 * (r + 2 * Math.log(r / 2 - 1));
  }
  _row(i) {
    const s = this.s, g = k => (s[k] ? s[k][i] : undefined);
    return { v_geo: g('v_geo'), r_geo: g('r_geo'), log10_r_over_rs: this.logr[i], u_ret_geo: g('u_ret_geo'), t_receive_years: g('t_receive_years'),
      redshift_1pz_to_infinity: g('redshift_1pz_to_infinity'), u_v: g('u_v'), u_r: g('u_r'), tau_years: g('tau_years'), r_over_rs: g('r_over_rs') };
  }
  _uStart() { if (this._u0 === undefined) { const u = this.retardedTimeGeo(this._row(0)); this._u0 = isNum(u) ? u : null; } return this._u0; }
  // reception time [Julian years] at a distant static observer of the radial signal emitted at this event, counted from
  // the reception of the signal emitted at the start; null inside the horizon (the signal never arrives)
  tReceiveYears(rec) {
    if (!rec) return null;
    if (isNum(rec.t_receive_years)) return rec.t_receive_years;
    const u = this.retardedTimeGeo(rec), u0 = this._uStart();
    if (!isNum(u) || !isNum(u0)) return null;
    return (u - u0) * this.derived.GM_over_c3_years;
  }
  // 1 + z of a radially outgoing photon received at infinity (exterior only, null inside).  Evaluated with the engine's
  // closed form 1 + z = u^v - 2 u^r / f (physics_notes §11) on the exported 4-velocity at the exact r of the record;
  // the redshift_1pz_to_infinity column is used only when the 4-velocity is missing.  Reason: the render export
  // interpolates every column linearly between engine steps, which is accurate for the smooth u^v, u^r (2e-5 at the
  // samples of the default run) but not for the steep 1 + z column near r_s (up to 2 % there).
  onePlusZ(rec) {
    if (!rec) return null;
    const r = isNum(rec.r_geo) ? rec.r_geo : (isNum(rec.log10_r_over_rs) ? 2 * Math.pow(10, rec.log10_r_over_rs) : NaN);
    if (!(r > 2)) return null;
    if (isNum(rec.u_v) && isNum(rec.u_r)) {
      const z = rec.u_v - 2 * rec.u_r / (1 - 2 / r);
      if (isNum(z) && z > 0) return z;
    }
    return isNum(rec.redshift_1pz_to_infinity) ? rec.redshift_1pz_to_infinity : null;
  }
  // Received-signal timeline {source, note, efoldYears, points: [{t, y = log10(1+z), tau, rOverRs}]} sorted by t.
  signalTimeline() {
    if (this._signal !== undefined) return this._signal;
    const efoldDefault = 4 * this.derived.GM_over_c3_years;          // late-time e-folding time 4GM/c^3 [yr]
    const st = this.raw.signal_timeline;
    let res = null;
    if (st && Array.isArray(st.t_receive_years) && Array.isArray(st.one_plus_z)) {
      const pts = [];
      for (let i = 0; i < st.t_receive_years.length; i++) {
        const t = st.t_receive_years[i], z = st.one_plus_z[i];
        if (isNum(t) && isNum(z) && z > 0) pts.push({ t, y: Math.log10(z), tau: st.tau_years ? st.tau_years[i] : null, rOverRs: st.r_over_rs ? st.r_over_rs[i] : null });
      }
      pts.sort((a, b) => a.t - b.t);
      if (pts.length >= 2) res = { source: 'engine', note: st.note || '', efoldYears: isNum(st.late_time_efold_years) ? st.late_time_efold_years : efoldDefault, points: pts };
    }
    if (!res) {
      const pts = [];
      for (let i = 0; i < this.N; i++) {
        const row = this._row(i);
        const t = this.tReceiveYears(row), z = this.onePlusZ(row);
        if (isNum(t) && isNum(z)) pts.push({ t, y: Math.log10(z), tau: row.tau_years, rOverRs: Math.pow(10, row.log10_r_over_rs) });
      }
      pts.sort((a, b) => a.t - b.t);
      res = { source: 'samples', note: 'computed in the viewer from the exported samples: u = v_geo − 2 r_*(r_geo), 1 + z = u^v − 2u^r/f (same closed form as the engine column redshift_1pz_to_infinity)',
        efoldYears: efoldDefault, points: pts };
    }
    this._signal = res;
    return res;
  }
}

export const fmt = {
  sci(x, d = 4) {
    if (x === null || x === undefined) return '—';
    if (typeof x === 'string') return x;
    if (!isFinite(x)) return x > 0 ? '+∞' : '−∞';
    if (x === 0) return '0';
    const e = Math.floor(Math.log10(Math.abs(x)));
    if (e >= -3 && e < 6) return x.toPrecision(d);
    const m = x / Math.pow(10, e);
    return `${m.toFixed(d - 1)}e${e}`;
  },
  metres(x) {
    if (x === null || x === undefined) return '—';
    const ly = 9.4607304725808e15, au = 1.495978707e11;
    if (x > 0.1 * ly) return `${fmt.sci(x)} m (${fmt.sci(x / ly, 4)} ly)`;
    if (x > 0.1 * au) return `${fmt.sci(x)} m (${fmt.sci(x / au, 4)} AU)`;
    if (x > 1e3) return `${fmt.sci(x)} m (${fmt.sci(x / 1e3, 4)} km)`;
    if (x >= 1e-9) return `${fmt.sci(x)} m`;
    if (x >= 1e-14) return `${fmt.sci(x)} m (${fmt.sci(x * 1e10, 3)} Å)`;
    return `${fmt.sci(x)} m (${fmt.sci(x * 1e15, 3)} fm)`;
  },
  years(x, d = 4) {
    if (x === null || x === undefined) return '—';
    if (typeof x === 'string') return x;
    if (!isFinite(x)) return x > 0 ? '+∞' : '−∞';
    const s = x * 365.25 * 86400;
    if (Math.abs(x) >= 1) return `${fmt.sci(x, d)} yr`;
    return `${fmt.sci(s, d)} s`;
  },
  log10(x) { if (x === null || x === undefined) return '—'; return `10^${x.toFixed(2)}`; },
};
