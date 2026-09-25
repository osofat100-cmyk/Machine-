// Shared CPU implementation of the first-person null-geodesic tracer (used by the on-screen
// termination statistics and by tests/viewer/test_null_geodesics.mjs).  The GLSL shader in
// firstperson.js implements EXACTLY the same equations and step rule; keep them in sync.
//
// Geometrized M = 1 (r_s = 2), ingoing Eddington–Finkelstein coordinates (v, r, psi) in the ray plane.
// Null geodesic equations (Christoffel symbols of ds^2 = -f dv^2 + 2 dv dr + r^2 dpsi^2, f = 1 - 2/r):
//   dk^v   = -(1/r^2) (k^v)^2 + r (k^psi)^2
//   dk^r   = -(f/r^2) (k^v)^2 + (2/r^2) k^v k^r + r f (k^psi)^2
//   dk^psi = -(2/r) k^r k^psi
export function fOf(r) { return 1 - 2 / r; }

export function deriv(p, k, out) {
  const r = p[1], f = fOf(r), kv = k[0], kr = k[1], kp = k[2];
  out[0] = kv; out[1] = kr; out[2] = kp;
  out[3] = -(kv * kv) / (r * r) + r * kp * kp;
  out[4] = -(f * kv * kv) / (r * r) + (2 / (r * r)) * kv * kr + r * f * kp * kp;
  out[5] = -(2 / r) * kr * kp;
}

export function stepSize(p, k, ch) {
  const r = p[1];
  const rate = Math.abs(k[1]) / r + Math.abs(k[2]) + Math.abs(k[0]) / r + 1e-30;
  let c = ch;
  if (r < 4) c *= 0.5;
  return c / rate;
}

// One RK4 step in the affine parameter.
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

// Observer tetrad: u = (uv, ur), n = (uv, E)/|n| (outward radial), transverse unit vectors 1/r.
export function observerFrame(r, uv, ur, E) {
  const f = fOf(r);
  const nn = -f * uv * uv + 2 * uv * E;           // g(n,n) with n = (uv, E)
  const N = Math.sqrt(Math.max(nn, 1e-300));
  return { f, nv: uv / N, nr: E / N };
}

// EXACT classification of a past-directed null ray (Schwarzschild, M = 1) from its conserved quantities.
// Eph = Killing energy of the future-directed photon, b2 = (L/Eph)^2 impact parameter squared.
//   exterior, moving inward (k^r < 0): no turning point below r iff r <= 3M or b^2 <= 27 M^2  -> reaches the past
//       horizon ('past'); otherwise it turns around and escapes to the sky.
//   exterior, moving outward: escapes unless 2M < r < 3M and b^2 > 27 M^2 (turns around above r, falls back).
//   interior (r < 2M): Eph > 0 -> came through the future horizon from region I (sky); Eph <= 0 -> came from the
//       other horizon (region III / collapsing matter: not modelled, 'past').
// (The effective potential r^2/f(r) = r^3/(r-2M) has its single minimum 27 M^2 at the photon sphere r = 3M.)
export function classify(r, kr, Eph, b2) {
  if (r < 2) return Eph > 0 ? 'sky' : 'past';
  if (kr < 0) return (r <= 3 || b2 <= 27) ? 'past' : 'sky';
  return (r < 3 && b2 > 27) ? 'past' : 'sky';
}

// Trace a past-directed ray from the observer for a view direction d = (d_n, d_perp) in the tetrad.
// Returns {kind: 'sky'|'past'|'unresolved', psiInf, g (frequency ratio omega_obs/omega_sky), steps}
export function traceRay(r0, uv, ur, E, dn, dperp, opts = {}) {
  const ch = opts.ch ?? 0.05, maxSteps = opts.maxSteps ?? 600, rSky = opts.rSky ?? 400;
  const fr = observerFrame(r0, uv, ur, E);
  const p = [0, r0, 0];
  const k = [-uv + dn * fr.nv, -ur + dn * fr.nr, dperp / r0];      // past-directed: k = -u + d^i e_i,  -k.u = 1
  const Eph = -(fOf(r0) * k[0] - k[1]);                              // Killing energy of the future-directed photon
  const L = r0 * r0 * k[2];
  const b2 = (L * L) / (Eph * Eph);
  if (classify(r0, k[1], Eph, b2) === 'past') return { kind: 'past', steps: 0, Eph, L, p: p.slice(), k: k.slice() };
  let steps = 0;
  for (; steps < maxSteps; steps++) {
    const r = p[1];
    if (r > rSky) {
      const psiInf = p[2] + Math.atan2(r * k[2], k[1]);
      return { kind: 'sky', psiInf, g: 1 / Eph, steps, Eph, L, p: p.slice(), k: k.slice() };
    }
    if (r < 1e-6 || p[0] < -1e6) return { kind: 'unresolved', steps, Eph, L, p: p.slice(), k: k.slice() };
    rk4(p, k, stepSize(p, k, ch));
  }
  return { kind: 'unresolved', steps, Eph, L, p: p.slice(), k: k.slice() };
}

// Forward-in-time tracer for tests (future-directed k): returns 'captured' (r < 2.0001 then decreasing), 'escaped' or 'unresolved'.
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
