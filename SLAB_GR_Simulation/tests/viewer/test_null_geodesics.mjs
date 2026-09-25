// Validation of the first-person null-geodesic equations (EF integration in firstperson_core.js; the optional GLSL
// shader in firstperson_gpu.js uses the same equations in float32).  See also tests/viewer/test_firstperson.mjs.
// Run: node tests/viewer/test_null_geodesics.mjs
import { traceRay, traceForward, fOf, classify, observerState, psiInfExact } from '../../renders/src/firstperson_core.js';

let fails = 0;
const report = (name, ok, detail) => { console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}  ${detail}`); if (!ok) fails++; };

// (a) conservation of E_ph, L and nullity along a generic ray (forward, from r = 30, impact parameter 8)
{
  const r0 = 30, b = 8; const E = 1, L = b * E;
  // inward radial-ish ray: k^r = -sqrt(E^2 - f L^2/r^2), k^v = (L^2/r^2)/(E + |k^r|) (regular root), k^psi = L/r^2
  const f = fOf(r0), kr = -Math.sqrt(E * E - f * L * L / (r0 * r0)), kv = (L * L / (r0 * r0)) / (E - kr), kp = L / (r0 * r0);
  const res = traceForward(r0, kv, kr, kp, { ch: 0.02 });
  report('(a) E_ph, L conserved and ray stays null (rel. drift < 1e-6)', res.worstE < 1e-6 && res.worstL < 1e-6 && res.worstNull < 1e-6, `E ${res.worstE.toExponential(2)} L ${res.worstL.toExponential(2)} null ${res.worstNull.toExponential(2)} kind ${res.kind}`);
}
// (b) weak-field deflection 4M/b within 2 % for b = 100 launched from r = 2000
{
  const r0 = 2000, b = 100, E = 1, L = b;
  const f = fOf(r0), kr = -Math.sqrt(E * E - f * L * L / (r0 * r0)), kv = (L * L / (r0 * r0)) / (E - kr), kp = L / (r0 * r0);
  const res = traceForward(r0, kv, kr, kp, { ch: 0.02, rSky: 2000, maxSteps: 20000 });
  // position-angle sweep from the launch point (r0, psi = 0) to the outgoing asymptote for a straight line is
  // pi - asin(b/r0); GR adds the deflection 4M/b + (15 pi/4) M^2/b^2 + O(M^3/b^3)
  const psiStraight = Math.PI - Math.asin(b / r0);
  const deflection = res.psi - psiStraight;
  const expected = 4 / b + 15 * Math.PI / 4 / (b * b);
  report('(b) weak-field deflection 4M/b + 15piM^2/4b^2 (1 %)', res.kind === 'escaped' && Math.abs(deflection / expected - 1) < 0.01, `deflection ${deflection.toExponential(4)} expected ${expected.toExponential(4)} (${((deflection / expected - 1) * 100).toFixed(2)} %)`);
}
// (c) capture threshold b_c = 3 sqrt(3) M from a static observer at r = 50
{
  const bc = 3 * Math.sqrt(3);
  const run = (b) => { const r0 = 50, E = 1, L = b; const f = fOf(r0), kr = -Math.sqrt(E * E - f * L * L / (r0 * r0)), kv = (L * L / (r0 * r0)) / (E - kr), kp = L / (r0 * r0); return traceForward(r0, kv, kr, kp, { ch: 0.02, maxSteps: 20000 }); };
  const rin = run(bc * 0.97), rout = run(bc * 1.05);
  report('(c) b < 3sqrt3 M captured, b > 1.05 x 3sqrt3 M escapes', rin.kind === 'captured' && rout.kind === 'escaped', `b=0.97 b_c -> ${rin.kind}, b=1.05 b_c -> ${rout.kind}`);
}
// (d) past-directed ray from inside the horizon (r = 1 M, E=1 infalling observer's tetrad) crosses r = 2M smoothly and reaches the sky
{
  const r0 = 1.0, x = Math.sqrt(r0 / 2); const uv = x / (1 + x), ur = -Math.sqrt(2 / r0), E = 1;
  const res = traceRay(r0, uv, ur, E, 0.3, Math.sqrt(1 - 0.09), { maxSteps: 4000, ch: 0.02 });
  report('(d) past-directed ray from r = 1M reaches the sky (crosses the horizon in EF coordinates)', res.kind === 'sky' && isFinite(res.psiInf), `kind ${res.kind} psiInf ${res.psiInf?.toFixed(4)} steps ${res.steps} E_ph ${res.Eph?.toFixed(4)}`);
  const res2 = traceRay(r0, uv, ur, E, 1.0, 0.0, { maxSteps: 4000, ch: 0.02 });
  report('(d2) looking straight outward from inside: ingoing family reaches the sky', res2.kind === 'sky', `kind ${res2.kind}`);
  const res3 = traceRay(r0, uv, ur, E, -1.0, 0.0, { maxSteps: 4000, ch: 0.02 });
  report('(d3) looking straight inward from inside: ray traced to the past horizon (not-modelled region)', res3.kind === 'past', `kind ${res3.kind} steps ${res3.steps}`);
}
// (e) infalling (E = 1) observer at r = 200 M: shadow edge by bisection on EF-integrated rays equals the
//     static-observer shadow sin(a_s) = (3 sqrt3 M/r) sqrt(1 - 2M/r) aberrated by v = sqrt(2M/r) toward the hole:
//     cos(a') = (cos a_s + v)/(1 + v cos a_s)   (0.1 %)
{
  const r0 = 200, E = 1; const x = Math.sqrt(r0 / 2); const uv = x / (1 + x), ur = -Math.sqrt(2 / r0);
  const kindAt = a => traceRay(r0, uv, ur, E, -Math.cos(a), Math.sin(a), { classify: false, maxSteps: 60000 }).kind;
  let lo = 0.001, hi = 0.2;                       // lo: past (shadow), hi: sky
  const k0 = kindAt(lo), k1 = kindAt(hi);
  for (let i = 0; i < 30; i++) { const m = 0.5 * (lo + hi); if (kindAt(m) === 'sky') hi = m; else lo = m; }
  const v = Math.sqrt(2 / r0), sS = 3 * Math.sqrt(3) / r0 * Math.sqrt(1 - 2 / r0), cS = Math.sqrt(1 - sS * sS);
  const expected = Math.acos((cS + v) / (1 + v * cS));
  report('(e) shadow edge (unconditioned EF integration) from r = 200M = aberrated static shadow (0.1 %)', k0 === 'past' && k1 === 'sky' && Math.abs(hi / expected - 1) < 1e-3, `edge ${hi.toFixed(6)} rad, analytic ${expected.toFixed(6)} rad`);
}

// (f) exact classifier vs numerical integration for exterior inward rays around the capture threshold
{
  let ok = true, detail = [];
  for (const b of [4.0, 5.0, 5.15, 5.25, 6.0, 9.0]) {
    const r0 = 50, E = 1, L = b; const f = fOf(r0), kr = -Math.sqrt(E * E - f * L * L / (r0 * r0)), kv = (L * L / (r0 * r0)) / (E - kr), kp = L / (r0 * r0);
    const num = traceForward(r0, kv, kr, kp, { ch: 0.02, maxSteps: 40000 }).kind === 'captured' ? 'past' : 'sky';
    const cls = classify(r0, kr, E, b * b);
    if (num !== cls) ok = false; detail.push(`b=${b}:${cls}/${num}`);
  }
  report('(f) exact impact-parameter classification agrees with integration', ok, detail.join(' '));
}
// (g) the conserved-quantity quadrature (psiInfExact) agrees with the EF integration for a sample of rays
{
  let worst = 0, n = 0;
  for (const r0 of [30, 6, 2.2, 0.5]) {
    const o = observerState(r0, 1);
    for (const dn of [-0.4, 0.0, 0.35, 0.8]) {
      const dp = Math.sqrt(1 - dn * dn);
      const q = psiInfExact(o, dn, dp);
      if (q.kind !== 'sky') continue;
      const t = traceRay(r0, o.uv, o.ur, 1, dn, dp, {});
      n++; worst = Math.max(worst, Math.abs(t.psiInf - q.psi));
    }
  }
  report('(g) orbit-integral quadrature = EF integration (|dpsi| < 1e-8 rad)', n > 10 && worst < 1e-8, `${n} rays, worst ${worst.toExponential(2)} rad`);
}
console.log(fails ? `${fails} FAILED` : 'ALL PASSED');
process.exit(fails ? 1 : 0);
