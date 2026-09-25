// First-person camera: 1D transfer table (pure JavaScript, double precision, importable from Node).
//
// The observer falls radially, so the picture is axially symmetric about her radial axis: the fate of a
// pixel's ray (sky / past horizon / unresolved), its asymptotic sky angle psi_inf and its frequency ratio g
// depend only on the angle between the view direction and the outward radial direction (dn = sin(alpha),
// alpha = elevation above the plane perpendicular to the radial direction); the azimuth only rotates the
// ray plane.  kind and g are closed-form (firstperson_core.js: classify(), g = 1/(E + a dn)) and are evaluated
// per pixel; only psi_inf needs an integral, and this table stores it.
//
// Parametrization (chosen so that every feature that is resolvable in double precision is sampled):
//   exterior (r >= 2):  param = alpha in [-pi/2, pi/2]  (smooth through the tangential direction)
//   interior (r < 2):   param = b = L/E_ph in [0, sqrt 27)  (psi_inf depends on b only; deep inside the whole
//       exterior universe except a ~r^(1/2)-radian patch around the zenith is mapped into directions within
//       ~r^(3/2) of the sky-cone edge, far below the double-precision spacing of alpha, but perfectly resolved in b)
// Adaptive refinement: uniform (alpha) or geometric (b) seed samples, geometric approach sequences towards every
// logarithmic divergence (b^2 -> 27: shadow edge, sky/past boundary, photon-sphere winding), then midpoint
// bisection wherever linear interpolation misses the exact value by more than max(atol, rtol |psi|).
import { photonOf, classifyDirection, psiInfExact, psiOfB, b27Roots } from './firstperson_core.js';

const B27 = Math.sqrt(27);

export class TransferTable {
  constructor(obs, opts = {}) {
    this.obs = obs;
    this.param = obs.r < 2 ? 'b' : 'alpha';
    this.atol = opts.atol ?? 2e-5;           // rad
    this.rtol = opts.rtol ?? 1e-4;
    this.minWidthAlpha = opts.minWidthAlpha ?? 2e-6;     // rad (~1/100 of a pixel at FOV 90 deg, 2000 px)
    this.maxSamples = opts.maxSamples ?? 12000;
    this.samples = new Map();                // param -> {kind, psi}
    this.queue = [];                         // intervals awaiting the midpoint test
    this.version = 0;
    this.evals = 0;
    this.capped = 0;                         // intervals left unrefined because of minWidth / maxSamples
    this._seed(opts.coarse ?? 64);
    this._rebuild();
  }

  // direction (dn, dperp, alpha) of a table parameter value
  directionOf(p) {
    const o = this.obs;
    if (this.param === 'alpha') return { dn: Math.sin(p), dperp: Math.cos(p), alpha: p };
    // interior: invert b(dn) = r dperp / (E + a dn) on the sky branch (larger root of
    //   (b^2 a^2 + r^2) dn^2 + 2 b^2 E a dn + b^2 E^2 - r^2 = 0,  discriminant/4 = r^2 (r^2 - b^2 f))
    const b = p, r = o.r, b2 = b * b;
    const dn = Math.min(1, (-b2 * o.E * o.a + r * Math.sqrt(r * r - b2 * o.f)) / (b2 * o.a * o.a + r * r));
    const dperp = Math.sqrt(Math.max(0, 1 - dn * dn));
    return { dn, dperp, alpha: Math.atan2(dn, dperp) };
  }

  // table parameter of a view direction
  paramOf(dn, dperp) {
    if (this.param === 'alpha') return Math.atan2(dn, dperp);
    return photonOf(this.obs, dn, dperp).b;
  }

  _eval(p) {
    if (this.samples.has(p)) return this.samples.get(p);
    const d = this.directionOf(p);
    let s;
    if (this.param === 'b') {
      // exact psi from b directly (E_ph = r dperp / b stays accurate where E + a dn has cancelled)
      if (p === 0) s = { kind: 'sky', psi: 0 };
      else if (p >= B27) s = { kind: 'past', psi: NaN };
      else {
        const res = psiOfB(this.obs.r, p, true);
        s = res.ok ? { kind: 'sky', psi: res.psi } : { kind: 'unresolved', psi: res.psi };
      }
    } else {
      const res = psiInfExact(this.obs, d.dn, d.dperp);
      s = { kind: res.kind, psi: res.psi };
    }
    this.evals++;
    this.samples.set(p, s);
    return s;
  }

  _seed(n) {
    const pts = [];
    if (this.param === 'alpha') {
      for (let i = 0; i <= n; i++) pts.push(-Math.PI / 2 + Math.PI * i / n);
      for (const dnb of b27Roots(this.obs)) {
        const ab = Math.asin(dnb);
        // approach the divergence from the sky side
        const probe = 1e-9;
        const side = classifyDirection(this.obs, Math.sin(ab + probe), Math.cos(ab + probe)).kind === 'sky' ? 1 : -1;
        pts.push(ab);
        for (let k = 1; k <= 48; k++) {
          const d = 0.2 * Math.pow(2, -k * 0.75);
          if (d < this.minWidthAlpha) break;
          pts.push(ab + side * d);
        }
      }
    } else {
      pts.push(0);
      for (let i = 1; i < n; i++) pts.push(B27 * i / n);
      // geometric towards 0 (psi is linear in b there; covers the whole visible hemisphere deep inside)
      const r = this.obs.r, bSmall = 1e-3 * Math.min(1, Math.pow(r, 1.5));
      for (let b = B27 / n; b > bSmall; b *= 0.5) pts.push(b);
      pts.push(bSmall);
      // geometric towards sqrt(27) (photon-sphere winding, sky-cone edge)
      for (let k = 1; k <= 30; k++) pts.push(B27 * (1 - Math.pow(2, -k)));
    }
    const uniq = [...new Set(pts.filter(p => isFinite(p)))].sort((x, y) => x - y);
    for (const p of uniq) this._eval(p);
    for (let i = 0; i + 1 < uniq.length; i++) this.queue.push([uniq[i], uniq[i + 1]]);
  }

  _minWidth(pl, pr) {
    if (this.param === 'alpha') return this.minWidthAlpha;
    return 1e-10 * Math.max(Math.abs(pl), Math.abs(pr), 1e-300);
  }

  // Midpoint refinement for at most `budgetMs` milliseconds (or `maxEvals` evaluations).  Returns true when done.
  refine(budgetMs = Infinity, maxEvals = Infinity) {
    const t0 = (typeof performance !== 'undefined' ? performance : Date).now();
    let n = 0, changed = false;
    while (this.queue.length) {
      if (n >= maxEvals) break;
      if ((n & 15) === 0 && (typeof performance !== 'undefined' ? performance : Date).now() - t0 > budgetMs) break;
      const [pl, pr] = this.queue.pop();
      const sl = this.samples.get(pl), sr = this.samples.get(pr);
      const pm = pl + 0.5 * (pr - pl);
      if (!(pm > pl && pm < pr)) continue;
      const tooSmall = (pr - pl) < this._minWidth(pl, pr) || this.samples.size >= this.maxSamples;
      if (sl.kind !== 'sky' && sr.kind !== 'sky') continue;
      if (tooSmall) { this.capped++; continue; }
      const sm = this._eval(pm); n++; changed = true;
      let split;
      if (sl.kind === 'sky' && sr.kind === 'sky' && sm.kind === 'sky') {
        const lin = 0.5 * (sl.psi + sr.psi);
        split = Math.abs(sm.psi - lin) > Math.max(this.atol, this.rtol * Math.abs(sm.psi));
      } else split = true;                      // a kind boundary inside: bisect towards it
      if (split) { this.queue.push([pl, pm]); this.queue.push([pm, pr]); }
    }
    if (changed || !this.queue.length) this._rebuild();
    return this.queue.length === 0;
  }

  get done() { return this.queue.length === 0; }

  _rebuild() {
    const keys = [...this.samples.keys()].sort((x, y) => x - y);
    const N = keys.length;
    this.p = new Float64Array(N); this.psi = new Float64Array(N); this.kind = new Uint8Array(N); this.alpha = new Float64Array(N);
    for (let i = 0; i < N; i++) {
      const s = this.samples.get(keys[i]);
      this.p[i] = keys[i]; this.psi[i] = s.psi;
      this.kind[i] = s.kind === 'sky' ? 0 : s.kind === 'past' ? 1 : 2;
      this.alpha[i] = this.directionOf(keys[i]).alpha;
    }
    this.version++;
  }

  // psi_inf and d psi / d param at parameter value p (sky rays).  ok = false when neither neighbour is sky.
  lookup(p, out = {}) {
    const P = this.p, N = P.length;
    let lo = 0, hi = N - 1;
    if (p <= P[0]) { hi = 1; } else if (p >= P[N - 1]) { lo = N - 2; }
    else { while (hi - lo > 1) { const m = (lo + hi) >> 1; if (P[m] <= p) lo = m; else hi = m; } }
    const kl = this.kind[lo], kh = this.kind[hi];
    if (kl === 0 && kh === 0) {
      const t = (p - P[lo]) / (P[hi] - P[lo]);
      out.slope = (this.psi[hi] - this.psi[lo]) / (P[hi] - P[lo]);
      out.psi = this.psi[lo] + t * (this.psi[hi] - this.psi[lo]);
      out.ok = true;
    } else if (kl === 0 || kh === 0) {
      const i = kl === 0 ? lo : hi;
      out.psi = this.psi[i]; out.slope = 0; out.ok = true; out.clamped = true;
    } else { out.psi = NaN; out.slope = 0; out.ok = false; }
    return out;
  }
}
