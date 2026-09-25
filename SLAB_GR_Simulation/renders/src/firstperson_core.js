// First-person camera: physics core (pure JavaScript, double precision, importable from Node).
//
// Geometrized units G = c = M = 1 (r_s = 2).  Schwarzschild in ingoing Eddington–Finkelstein (EF) form
//   ds^2 = -f dv^2 + 2 dv dr + r^2 dOmega^2,   f = 1 - 2/r.
//
// Two independent ways of following a past-directed light ray from the observer's eye:
//   (1) psiInfExact(): the orbit is fixed by the conserved Killing energy E_ph and angular momentum L
//       (EXACT GR RESULT: Killing symmetries), so the asymptotic sky angle is the orbit integral
//           psi_inf = INT dw / sqrt(1 - w^2 + 2 w^3 / b),   w = b/r,  b = L/E_ph,
//       evaluated by adaptive Gauss–Kronrod quadrature in scale-free variables (NUMERICAL APPROXIMATION of an
//       exact integral, relative accuracy ~1e-10).  Works unchanged from r = 400 M down to r_QG ~ 1e-37 M.
//       Used by the renderer (via the transfer table in firstperson_table.js).
//   (2) traceRay(): integrates the second-order EF geodesic equations (same Christoffel symbols as the
//       timelike engine) with an adaptive Dormand–Prince 5(4) step and a relative, component-scaled error
//       norm, so that it also works from r ~ 1e-37 M (step sizes and momenta scale like powers of r; nothing
//       over/underflows).  Used as the independent reference in tests/viewer/.
//
// Observer: radial, 4-velocity u = (u^v, u^r) with Killing energy E = f u^v - u^r.  Comoving tetrad
//   e0 = u,  e1 = n = (u^v, E)/|n| (outward radial; |n| = 1 for a normalized u),  e2 = d_theta/r,  e3 = d_phi/(r sin theta).
// A view direction d = dn e1 + dperp e_perp (dn^2 + dperp^2 = 1) receives the future-directed photon
// p = u - d (observed frequency -p.u = 1).  With a = |u^r| = sqrt(E^2 - f) (EXACT, any radial unit u):
//   E_ph = -p.xi = E + dn a        (xi = d_v Killing vector = E u + a n)
//   L    = r dperp,   b = L / E_ph,   g = omega_obs / omega_inf = 1 / E_ph
// and the past-directed ray moves outward in r iff a + E dn > 0.

export function fOf(r) { return 1 - 2 / r; }

// ---------------------------------------------------------------------------------------------
// Observer state from (r, E): exact for any radially moving unit timelike vector (geodesic or thrusting).
//   a = |u^r| = sqrt(E^2 - 1 + 2/r),  u^v = 1/(E + a)   (well conditioned everywhere, incl. r = 2 and r -> 0)
export function observerState(r, E = 1) {
  const a = Math.sqrt(Math.max(0, E * E - 1 + 2 / r));
  return { r, E, a, uv: 1 / (E + a), ur: -a, f: fOf(r) };
}

// Conserved quantities of the photon seen in direction (dn, dperp).
export function photonOf(obs, dn, dperp) {
  const Eph = obs.E + dn * obs.a;
  const L = obs.r * dperp;
  return { Eph, L, b: L / Eph, outward: obs.a + obs.E * dn > 0, g: 1 / Eph };
}

// EXACT classification of a past-directed null ray from its conserved quantities (Schwarzschild, M = 1).
//   r = observer radius, kr = sign of dr/dlambda of the PAST-directed ray, Eph = Killing energy of the
//   future-directed photon, b2 = (L/Eph)^2.  Effective potential: b^2 <= r^2/f(r), minimum 27 at r = 3.
//   exterior, moving inward:  reaches the past horizon ('past') iff r <= 3 or b^2 <= 27; otherwise it has
//       a turning point above r = 3 and escapes to the sky;
//   exterior, moving outward: escapes unless 2 < r < 3 and b^2 > 27 (inner turning point, falls back);
//   interior (r < 2): a past-directed ray always moves to larger r.  Eph <= 0: it leaves region II through
//       the horizon towards region III / white hole (not modelled, 'past').  Eph > 0: it enters region I
//       through the future horizon at r = 2 moving outward; from there it escapes iff b^2 < 27, otherwise it
//       meets the inner turning point r_t < 3 and ends on the past horizon of region I ('past').
//       (Fixed 2026-09: the previous version returned 'sky' for every Eph > 0 inside; the b^2 > 27 rays
//       were then integrated until they failed and drawn magenta.)
// b2 == 27 exactly (unstable circular orbit) is assigned to 'past' on the exterior-inward branch and to
// 'sky' elsewhere (measure zero; the quadrature then reports 'unresolved').
export function classify(r, kr, Eph, b2) {
  if (r < 2) return (Eph > 0 && b2 < 27) ? 'sky' : 'past';
  if (kr < 0) return (r <= 3 || b2 <= 27) ? 'past' : 'sky';
  return (r < 3 && b2 > 27) ? 'past' : 'sky';
}

export function classifyDirection(obs, dn, dperp) {
  const ph = photonOf(obs, dn, dperp);
  return { ...ph, kind: classify(obs.r, ph.outward ? 1 : -1, ph.Eph, ph.b * ph.b) };
}

// EXACT boundaries (in dn = cos of the angle from the outward radial direction) of the directions whose
// rays have b^2 = 27, i.e. the edge of the shadow (exterior) or of the exterior-sky cone (interior):
//   (27 a^2 + r^2) dn^2 + 54 E a dn + 27 E^2 - r^2 = 0
//   dn_pm = (-27 E a  pm  |r - 3| sqrt(r (r + 6))) / (27 a^2 + r^2)          [uses r^3 - 27 r + 54 = (r-3)^2 (r+6)]
// Only roots with E_ph = E + a dn > 0 are physical; at a root E_ph = (E r^2 -+ a s)/A exactly (evaluated in this
// form because E + a dn cancels catastrophically deep inside, where dn -> -E/a).
export function b27Roots(obs) {
  const { r, E, a } = obs;
  const A = 27 * a * a + r * r;
  const s = Math.abs(r - 3) * Math.sqrt(r * (r + 6));
  const out = [];
  const lo = (-27 * E * a - s) / A, hi = (-27 * E * a + s) / A;
  if (lo >= -1 && lo <= 1 && (E * r * r - a * s) > 0) out.push(lo);
  if (hi >= -1 && hi <= 1 && (E * r * r + a * s) > 0) out.push(hi);
  return out;
}

// Exact solid-angle fractions of the observer's sky (dn is uniformly distributed on the sphere, so the
// fraction of directions with dn in a set S is |S|/2).  Returns {sky, past, cuts:[dn...], dnMinSky}.
export function skyFractions(obs) {
  const cuts = [-1, 1, ...b27Roots(obs)];
  const dnTan = -obs.a / obs.E;                      // tangential (dr/dlambda = 0) direction
  if (dnTan > -1 && dnTan < 1) cuts.push(dnTan);
  const dnE0 = -obs.E / obs.a;                        // E_ph = 0
  if (dnE0 > -1 && dnE0 < 1) cuts.push(dnE0);
  cuts.sort((x, y) => x - y);
  let sky = 0, dnMinSky = NaN;
  for (let i = 0; i + 1 < cuts.length; i++) {
    const lo = cuts[i], hi = cuts[i + 1];
    if (hi <= lo) continue;
    const mid = lo + 0.5 * (hi - lo);
    if (classifyDirection(obs, mid, Math.sqrt(1 - mid * mid)).kind === 'sky') { sky += hi - lo; if (isNaN(dnMinSky)) dnMinSky = lo; }
  }
  // interior: the exterior sky is the cone dn > dnMinSky around the outward direction (half-angle acos(dnMinSky))
  return { sky: sky / 2, past: 1 - sky / 2, cuts, dnMinSky };
}

// ---------------------------------------------------------------------------------------------
// Adaptive Gauss–Kronrod (G7, K15) quadrature.  Returns {value, err, ok}.
const XGK = [0.991455371120812639206854697526329, 0.949107912342758524526189684047851, 0.864864423359769072789712788640926,
  0.741531185599394439863864773280788, 0.586087235467691130294144845693013, 0.405845151377397166906606412076961,
  0.207784955007898467600689403773245, 0.0];
const WGK = [0.022935322010529224963732008058970, 0.063092092629978553290700663189204, 0.104790010322250183839876322541518,
  0.140653259715525918745189590510238, 0.169004726639267902826583426598550, 0.190350578064785409913256402421014,
  0.204432940075298892414161999234649, 0.209482141084727828012999174891714];
const WG = [0.129484966168869693270611432679082, 0.279705391489276667901467771423780, 0.381830050505118944950369775488975,
  0.417959183673469387755102040816327];

function gk15(F, a, b) {
  const c = 0.5 * (a + b), h = 0.5 * (b - a);
  const fc = F(c);
  let rk = fc * WGK[7], rg = fc * WG[3];
  for (let j = 0; j < 7; j++) {
    const x = h * XGK[j];
    const f1 = F(c - x), f2 = F(c + x);
    rk += WGK[j] * (f1 + f2);
    if (j & 1) rg += WG[(j - 1) >> 1] * (f1 + f2);
  }
  return { value: rk * h, err: Math.abs((rk - rg) * h) };
}

// Globally adaptive: always bisect the interval with the largest error estimate (binary max-heap, O(n log n)).
// `breaks` (optional) are interior points where the integrand has a sharp feature.
export function integrate(F, a, b, opts = {}) {
  const rtol = opts.rtol ?? 1e-11, atol = opts.atol ?? 0, maxIntervals = opts.maxIntervals ?? 4000;
  const pts = [a, ...(opts.breaks ?? []).filter(x => x > a && x < b).sort((x, y) => x - y), b];
  const heap = [];
  const push = (it) => { heap.push(it); let i = heap.length - 1; while (i > 0) { const q = (i - 1) >> 1; if (heap[q].err >= heap[i].err) break; [heap[q], heap[i]] = [heap[i], heap[q]]; i = q; } };
  const pop = () => { const top = heap[0], last = heap.pop(); if (heap.length) { heap[0] = last; let i = 0; for (;;) { const l = 2 * i + 1, r = l + 1; let m = i; if (l < heap.length && heap[l].err > heap[m].err) m = l; if (r < heap.length && heap[r].err > heap[m].err) m = r; if (m === i) break; [heap[m], heap[i]] = [heap[i], heap[m]]; i = m; } } return top; };
  let total = 0, err = 0, n = 0;
  for (let i = 0; i + 1 < pts.length; i++) { const it = { a: pts[i], b: pts[i + 1], ...gk15(F, pts[i], pts[i + 1]) }; total += it.value; err += it.err; push(it); n++; }
  for (;;) {
    if (!isFinite(total)) return { value: total, err: Infinity, ok: false, n };
    if (err <= Math.max(atol, rtol * Math.abs(total))) return { value: total, err, ok: true, n };
    // budget exhausted / interval indivisible: accept at the looser `accept` level (near-critical rays, where
    // the integrand itself carries a relative round-off ~1e-16/|P| from the cancellation in P = 1 - w^2 + 2w^3/b)
    const fin = () => ({ value: total, err, ok: err <= (opts.accept ?? 1e-7) * Math.abs(total), n });
    if (n >= maxIntervals) return fin();
    const w = pop();
    const m = 0.5 * (w.a + w.b);
    if (!(m > w.a && m < w.b)) return fin();
    const L = { a: w.a, b: m, ...gk15(F, w.a, m) }, R = { a: m, b: w.b, ...gk15(F, m, w.b) };
    total += L.value + R.value - w.value; err += L.err + R.err - w.err;
    if (heap.length === 0 || n % 64 === 0) { total = L.value + R.value; err = L.err + R.err; for (const it of heap) { total += it.value; err += it.err; } }  // re-sum (round-off)
    push(L); push(R); n++;
  }
}

// Outer turning point of an exterior orbit with b^2 > 27: largest root of r^3 - b^2 r + 2 b^2 = 0 (EXACT, trigonometric).
export function turningRadius(b) {
  return (2 * b / Math.sqrt(3)) * Math.cos(Math.acos(-3 * Math.sqrt(3) / b) / 3);
}

// psi swept by a ray without turning point from r0 to infinity:
//   psi = INT_0^{w0} dw / sqrt(1 - w^2 + 2 w^3/b),   w0 = b/r0.
// Substituting w = w0 e^{-s} (s = ln(r/r0), i.e. integration in ln r) the integrand is
//   w / sqrt(1 + w^2 (2/r - 1)),  w = w0 e^{-s},  1/r = e^{-s}/r0,
// which only contains the ratios w and 1/r: no over/underflow for r0 down to 1e-300.  The tail beyond
// r_1 (where w_1 <= 1e-10 and r_1 >= 1e3) is added analytically (psi_tail = w_1 (1 + O(w_1^2, w_1^2/r_1))).
function psiMonotone(r0, b, qopts) {
  if (b === 0) return { value: 0, ok: true, n: 0 };
  const w0 = b / r0;
  const sMax = Math.max(0, Math.log(w0 * 1e10), Math.log(1e3 / r0)) + 1;
  const F = s => { const e = Math.exp(-s), w = w0 * e, invr = e / r0; return w / Math.sqrt(1 + w * w * (2 * invr - 1)); };
  // breakpoints: photon sphere r = 3 (near-critical rays linger there) and the horizon r = 2
  const res = integrate(F, 0, sMax, { ...qopts, breaks: [Math.log(3 / r0), Math.log(2 / r0)] });
  return { value: res.value + w0 * Math.exp(-sMax), ok: res.ok, n: res.n };
}

// psi swept by an exterior ray moving inward from r0 with b^2 > 27: in to the turning point r_t, then out.
//   P(w) = 1 - w^2 + (2/b) w^3 = (w_t - w) Q(w),  Q(w) = (1 - 2/r_t)(w + w_t) - (2/b) w^2,   w_t = b/r_t
// and w = w_t - y^2 removes the inverse-square-root endpoint singularity:  dpsi = 2 dy / sqrt(Q(w_t - y^2)).
//   psi = INT_0^{sqrt(w_t)} + INT_0^{sqrt(w_t - w0)}.   Q(w_t) = 2 w_t (1 - 3/r_t) -> 0 at the photon sphere
// (logarithmic winding divergence, handled by the adaptive quadrature up to its interval budget).
function psiTurning(r0, b, qopts) {
  const rt = turningRadius(b), wt = b / rt, ft = 1 - 2 / rt;
  const F = y => { const w = wt - y * y; return 2 / Math.sqrt(Math.max(1e-300, ft * (w + wt) - (2 / b) * w * w)); };
  const d0 = Math.max(0, b * (r0 - rt) / (r0 * rt));
  const A = integrate(F, 0, Math.sqrt(wt), qopts), B = integrate(F, 0, Math.sqrt(d0), qopts);
  return { value: A.value + B.value, ok: A.ok && B.ok, n: A.n + B.n, rt };
}

// psi_inf of a sky ray with impact parameter b seen from r0 (outward: no turning point; else exterior turning).
export function psiOfB(r0, b, outward, opts = {}) {
  const qopts = { rtol: opts.rtol ?? 1e-10, maxIntervals: opts.maxIntervals ?? 500, accept: opts.accept ?? 1e-7 };
  const res = outward ? psiMonotone(r0, b, qopts) : psiTurning(r0, b, qopts);
  return { psi: res.value, ok: res.ok && isFinite(res.value) };
}

// Asymptotic sky angle psi_inf (angle, seen from the hole, between the observer's outward radial direction and
// the direction of the source at infinity, measured in the ray plane towards the view direction's transverse
// component) for the observer `obs` and view direction (dn, dperp).  Returns {kind, psi, g, Eph, b, outward}.
export function psiInfExact(obs, dn, dperp, opts = {}) {
  const ph = classifyDirection(obs, dn, dperp);
  if (ph.kind !== 'sky') return { ...ph };
  const res = psiOfB(obs.r, ph.b, ph.outward, opts);
  if (!res.ok) return { ...ph, kind: 'unresolved', psi: res.psi };
  return { ...ph, psi: res.psi };
}

// ---------------------------------------------------------------------------------------------
// Direct integration of the EF null-geodesic equations (independent reference for the tests).
//   dv/dl = k^v, dr/dl = k^r, dpsi/dl = k^psi
//   dk^v   = -(1/r^2) (k^v)^2 + r (k^psi)^2
//   dk^r   = -(f/r^2) (k^v)^2 + (2/r^2) k^v k^r + r f (k^psi)^2
//   dk^psi = -(2/r) k^r k^psi
export function deriv(p, k, out) {
  const r = p[1], f = fOf(r), kv = k[0], kr = k[1], kp = k[2];
  out[0] = kv; out[1] = kr; out[2] = kp;
  out[3] = -(kv * kv) / (r * r) + r * kp * kp;
  out[4] = -(f * kv * kv) / (r * r) + (2 / (r * r)) * kv * kr + r * f * kp * kp;
  out[5] = -(2 / r) * kr * kp;
}

// Legacy fixed-rule step size + RK4 (kept for traceForward, used by the capture/deflection tests).
export function stepSize(p, k, ch) {
  const r = p[1];
  const rate = Math.abs(k[1]) / r + Math.abs(k[2]) + Math.abs(k[0]) / r + 1e-300;
  let c = ch;
  if (r < 4) c *= 0.5;
  return c / rate;
}
export function rk4(p, k, h) {
  const d1 = new Float64Array(6), d2 = new Float64Array(6), d3 = new Float64Array(6), d4 = new Float64Array(6);
  const p2 = [0, 0, 0], k2 = [0, 0, 0];
  deriv(p, k, d1);
  for (let i = 0; i < 3; i++) { p2[i] = p[i] + 0.5 * h * d1[i]; k2[i] = k[i] + 0.5 * h * d1[3 + i]; }
  deriv(p2, k2, d2);
  for (let i = 0; i < 3; i++) { p2[i] = p[i] + 0.5 * h * d2[i]; k2[i] = k[i] + 0.5 * h * d2[3 + i]; }
  deriv(p2, k2, d3);
  for (let i = 0; i < 3; i++) { p2[i] = p[i] + h * d3[i]; k2[i] = k[i] + h * d3[3 + i]; }
  deriv(p2, k2, d4);
  for (let i = 0; i < 3; i++) {
    p[i] += h / 6 * (d1[i] + 2 * d2[i] + 2 * d3[i] + d4[i]);
    k[i] += h / 6 * (d1[3 + i] + 2 * d2[3 + i] + 2 * d3[3 + i] + d4[3 + i]);
  }
}

// Observer tetrad from the EF components: n = (uv, E)/|n| (outward radial).
export function observerFrame(r, uv, ur, E) {
  const f = fOf(r);
  const nn = -f * uv * uv + 2 * uv * E;           // g(n,n) with n = (uv, E); = 1 for a normalized u
  const N = Math.sqrt(Math.max(nn, 1e-300));
  return { f, nv: uv / N, nr: E / N };
}

// Dormand–Prince 5(4) tableau
const DP_C = [0, 1 / 5, 3 / 10, 4 / 5, 8 / 9, 1, 1];
const DP_A = [[], [1 / 5], [3 / 40, 9 / 40], [44 / 45, -56 / 15, 32 / 9], [19372 / 6561, -25360 / 2187, 64448 / 6561, -212 / 729],
  [9017 / 3168, -355 / 33, 46732 / 5247, 49 / 176, -5103 / 18656], [35 / 384, 0, 500 / 1113, 125 / 192, -2187 / 6784, 11 / 84]];
const DP_B = [35 / 384, 0, 500 / 1113, 125 / 192, -2187 / 6784, 11 / 84, 0];
const DP_E = [71 / 57600, 0, -71 / 16695, 71 / 1920, -17253 / 339200, 22 / 525, -1 / 40];   // b - b*

function rhs(y, out) {   // y = [v, r, psi, kv, kr, kpsi]
  const r = y[1], f = fOf(r), kv = y[3], kr = y[4], kp = y[5], ir = 1 / r;
  out[0] = kv; out[1] = kr; out[2] = kp;
  out[3] = -(kv * ir) * (kv * ir) + r * kp * kp;
  out[4] = -f * (kv * ir) * (kv * ir) + 2 * (kv * ir) * (kr * ir) + r * f * kp * kp;
  out[5] = -2 * (kr * ir) * kp;
}

// Adaptive DP5(4) integration of a past-directed ray (the EF equations above) from the observer's eye.
// Error norm: every component relative to its natural scale (r for r, |psi| + |dpsi| for psi, the momentum
// scale K = |k^r| + |f k^v| + r|k^psi| for the momenta), so the integration is scale-free and works from
// r ~ 1e-37 M outwards.  Termination: r > rFar -> 'sky' with psi_inf = psi + atan2(r k^psi, k^r) (flat
// asymptote; residual bending O(b/rFar^2)); exterior ray moving inward with r < 2(1 + 1e-7) -> 'past'
// (approaches the past horizon); interior ray with v < v0 - vPast -> 'past' (approaches the horizon towards
// region III / white hole, v -> -infinity); maxSteps -> 'unresolved'.
// opts.classify (default true): return immediately with the exact classification for 'past' rays.
export function traceRay(r0, uv, ur, E, dn, dperp, opts = {}) {
  const rtol = opts.rtol ?? 1e-10, maxSteps = opts.maxSteps ?? 20000, rFar = opts.rFar ?? opts.rSky ?? 1e7, vPast = opts.vPast ?? 40;
  const fr = observerFrame(r0, uv, ur, E);
  const y = new Float64Array([0, r0, 0, -uv + dn * fr.nv, -ur + dn * fr.nr, dperp / r0]);
  const f0 = fOf(r0);
  const Eph = -(f0 * y[3] - y[4]);            // Killing energy of the future-directed photon
  const L = r0 * r0 * y[5];
  const b2 = (L * L) / (Eph * Eph);
  const conserved = (yy) => { const f = fOf(yy[1]); return { Eph: -(f * yy[3] - yy[4]), L: yy[1] * yy[1] * yy[5] }; };
  if ((opts.classify ?? true) && classify(r0, y[4], Eph, b2) === 'past') return { kind: 'past', steps: 0, Eph, L, y };
  const K = Array.from({ length: 7 }, () => new Float64Array(6));
  const yt = new Float64Array(6), yn = new Float64Array(6);
  let h = 0.02 * r0 / (Math.abs(y[4]) + r0 * Math.abs(y[5]) + Math.abs(y[3]) + 1e-300);
  let steps = 0, rejected = 0, worstE = 0, worstL = 0;
  rhs(y, K[0]);
  while (steps < maxSteps) {
    for (let s = 1; s < 7; s++) {
      for (let i = 0; i < 6; i++) { let acc = 0; for (let j = 0; j < s; j++) acc += DP_A[s][j] * K[j][i]; yt[i] = y[i] + h * acc; }
      rhs(yt, K[s]);
    }
    for (let i = 0; i < 6; i++) { let acc = 0; for (let j = 0; j < 7; j++) acc += DP_B[j] * K[j][i]; yn[i] = y[i] + h * acc; }
    // scaled error
    const r = y[1], f = fOf(r);
    const Ks = Math.abs(y[4]) + Math.abs(f * y[3]) + r * Math.abs(y[5]) + 1e-300;
    const sc = [1 + Math.abs(y[0]), r, Math.abs(y[2]) + Math.abs(h * y[5]) + 1e-300, Ks / Math.max(1, Math.abs(f)), Ks, Math.abs(y[5]) + 1e-300];   // k^psi keeps its sign: relative
    let err = 0;
    for (let i = 0; i < 6; i++) { let acc = 0; for (let j = 0; j < 7; j++) acc += DP_E[j] * K[j][i]; err = Math.max(err, Math.abs(h * acc) / sc[i]); }
    err /= rtol;
    if (!(yn[1] > 0) || !isFinite(err)) { h *= 0.2; rejected++; if (rejected > 200) break; continue; }
    if (err <= 1) {
      y.set(yn); rhs(y, K[0]); steps++;
      const c = conserved(y);
      worstE = Math.max(worstE, Math.abs(c.Eph / Eph - 1)); worstL = Math.max(worstL, Math.abs(c.L / L - 1) || 0);
      const rr = y[1];
      if (rr > rFar) {
        const psiInf = y[2] + Math.atan2(rr * y[5], y[4]);
        return { kind: 'sky', psiInf, g: 1 / Eph, steps, rejected, Eph, L, worstE, worstL, y };
      }
      if (rr >= 2 && y[4] < 0 && rr < 2 * (1 + 1e-7)) return { kind: 'past', steps, rejected, Eph, L, worstE, worstL, y };
      if (rr < 2 && y[0] < -vPast) return { kind: 'past', steps, rejected, Eph, L, worstE, worstL, y };
    } else rejected++;
    h *= Math.min(5, Math.max(0.2, 0.9 * Math.pow(Math.max(err, 1e-10), -0.2)));
  }
  return { kind: 'unresolved', steps, rejected, Eph, L, worstE, worstL, y };
}

// Forward-in-time tracer for tests (future-directed k): 'captured' (r < 1), 'escaped' or 'unresolved'.
export function traceForward(r0, kv, kr, kp, opts = {}) {
  const ch = opts.ch ?? 0.05, maxSteps = opts.maxSteps ?? 4000, rSky = opts.rSky ?? 400;
  const p = [0, r0, 0], k = [kv, kr, kp];
  const Eph0 = fOf(r0) * kv - kr, L0 = r0 * r0 * kp;
  let worstE = 0, worstL = 0, worstNull = 0;
  for (let s = 0; s < maxSteps; s++) {
    const r = p[1], f = fOf(r);
    const Eph = f * k[0] - k[1], L = r * r * k[2];
    const nul = -f * k[0] * k[0] + 2 * k[0] * k[1] + r * r * k[2] * k[2];
    worstE = Math.max(worstE, Math.abs(Eph / Eph0 - 1)); worstL = Math.max(worstL, Math.abs(L - L0) / Math.max(1e-300, Math.abs(L0)));
    worstNull = Math.max(worstNull, Math.abs(nul) / (Math.abs(f * k[0] * k[0]) + Math.abs(2 * k[0] * k[1]) + r * r * k[2] * k[2]));
    if (r > rSky) return { kind: 'escaped', psi: p[2] + Math.atan2(r * k[2], k[1]), worstE, worstL, worstNull, steps: s };
    if (r < 1.0) return { kind: 'captured', worstE, worstL, worstNull, steps: s };
    rk4(p, k, stepSize(p, k, ch));
  }
  return { kind: 'unresolved', worstE, worstL, worstNull, steps: maxSteps };
}
