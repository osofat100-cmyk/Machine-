// CPU validation of the first-person ray tracer equations (shared with the GLSL shader).
// Run: node tests/viewer/test_null_geodesics.mjs
import { traceRay, traceForward, fOf, classify } from '../../renders/src/firstperson_core.js';

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
// (e) exterior static-like observer far away sees the shadow with angular radius ~ 3sqrt3 M / r
{
  const r0 = 200, E = 1; const x = Math.sqrt(r0 / 2); const uv = x / (1 + x), ur = -Math.sqrt(2 / r0);
  // scan angles from the hole direction (-n): d_n = -cos a, d_perp = sin a
  let edge = null;
  for (let a = 0.005; a < 0.2; a += 0.0025) { const res = traceRay(r0, uv, ur, E, -Math.cos(a), Math.sin(a), { maxSteps: 4000, ch: 0.02 }); if (res.kind === 'sky') { edge = a; break; } }
  const expected = Math.asin(3 * Math.sqrt(3) / r0);   // static observer estimate; infalling observer sees it slightly aberrated (smaller)
  report('(e) shadow edge angle from r = 200M within 25 % of asin(3sqrt3 M/r)', edge !== null && Math.abs(edge / expected - 1) < 0.25, `edge ${edge?.toFixed(4)} rad, static estimate ${expected.toFixed(4)} rad`);
}
console.log(fails ? `${fails} FAILED` : 'ALL PASSED');
process.exit(fails ? 1 : 0);

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
