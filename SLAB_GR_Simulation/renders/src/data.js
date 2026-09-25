// Data access layer for the precomputed trajectory (window.SLAB_DATA).
// Samples are ordered by DECREASING log10(r/r_s); columns may contain null where undefined.

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
    if (out.regime_code !== null) out.regime_code = Math.round(out.regime_code);
    return out;
  }
  at(logr) { return this.atIndex(this.indexOf(logr)); }
  milestone(slug) { return this.milestones.find(m => m.slug === slug); }
  // proper-time axis helper (exterior only): logr as a function of tau fraction
  logrForTauFraction(f) {
    const tau = this.s.tau_years;
    const target = f * tau[this.N - 1];
    for (let i = 0; i < this.N - 1; i++) if (tau[i + 1] >= target) {
      const t = (target - tau[i]) / Math.max(1e-300, tau[i + 1] - tau[i]);
      return this.logr[i] + (this.logr[i + 1] - this.logr[i]) * t;
    }
    return this.logrMin;
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
  years(x) {
    if (x === null || x === undefined) return '—';
    if (typeof x === 'string') return x;
    if (!isFinite(x)) return x > 0 ? '+∞' : '−∞';
    const s = x * 365.25 * 86400;
    if (Math.abs(x) >= 1) return `${fmt.sci(x)} yr`;
    if (Math.abs(s) >= 1) return `${fmt.sci(s)} s`;
    return `${fmt.sci(s)} s`;
  },
  log10(x) { if (x === null || x === undefined) return '—'; return `10^${x.toFixed(2)}`; },
};
