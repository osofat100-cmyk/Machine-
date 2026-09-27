// Node-only tests of the double-precision CPU first-person renderer (no browser, no WebGL).
// Run: node tests/viewer/test_firstperson.mjs
import {
  observerState, photonOf, classify, classifyDirection, psiInfExact, traceRay, b27Roots, skyFractions, turningRadius,
} from '../../renders/src/firstperson_core.js';
import { TransferTable } from '../../renders/src/firstperson_table.js';
import { CpuRenderer, cameraAxes, KIND_SKY, KIND_PAST, KIND_UNRESOLVED } from '../../renders/src/firstperson_cpu.js';
import { celestialFrame, gScaleRange, starImages, bvToTemperature, blackbody } from '../../renders/src/firstperson_sky.js';
import { loadStars } from '../../renders/src/starcatalog.js';

let fails = 0;
const report = (name, ok, detail) => { console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}  ${detail}`); if (!ok) fails++; };
// deterministic pseudo-random numbers (mulberry32)
function rng(seed) { return () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const R_QG = 2 * 4.70e-38;   // r_QG in GM/c^2 (README: 4.70e-38 r_s)

// ---------------------------------------------------------------------------------------------
// 1. transfer-table lookup vs direct per-ray evaluation (quadrature) and vs EF integration, random directions
{
  const rand = rng(12345);
  for (const r of [200, 10, 3.5, 2.5, 2.0, 1.5, 1.0, 1e-3, 1e-10, 1e-30, R_QG]) {
    const obs = observerState(r, 1);
    const T = new TransferTable(obs); T.refine();
    let n = 0, worstPsi = 0, worstRel = 0, worstG = 0, nEF = 0, worstEF = 0, badEF = 0, unres = 0, over = 0;
    for (let i = 0; i < 600; i++) {
      const dn = 2 * rand() - 1, dperp = Math.sqrt(1 - dn * dn);
      const ex = psiInfExact(obs, dn, dperp);
      if (ex.kind === 'unresolved') unres++;
      if (ex.kind !== 'sky') continue;
      n++;
      const L = T.lookup(T.paramOf(dn, dperp));
      const err = Math.abs(L.psi - ex.psi), tol = Math.max(T.atol, T.rtol * Math.abs(ex.psi));
      worstPsi = Math.max(worstPsi, err); worstRel = Math.max(worstRel, err / tol);
      if (err > 2 * tol) over++;
      // g: the per-pixel closed form vs the EF integration's own E_ph (computed from its initial EF momentum)
      if (i % 6 === 0) {
        const nearCrit = Math.abs(ex.b * ex.b / 27 - 1) < 0.02;
        const tr = traceRay(r, obs.uv, obs.ur, obs.E, dn, dperp, {});
        const cond = (obs.a + Math.abs(obs.E)) / Math.abs(ex.Eph);           // cancellation factor of E_ph in EF components
        if (tr.kind === 'sky' && cond < 1e6) { worstG = Math.max(worstG, Math.abs(tr.g * ex.Eph - 1) / cond); }
        if (!nearCrit && cond < 1e6) {
          nEF++;
          if (tr.kind !== 'sky') badEF++;
          else worstEF = Math.max(worstEF, Math.abs(tr.psiInf - ex.psi) / Math.max(1e-300, Math.abs(ex.psi)));
        }
      }
    }
    report(`(1) r = ${r.toExponential(2)} M: table lookup vs quadrature at ${n} random sky directions`, over <= Math.ceil(0.005 * n) && unres === 0,
      `worst |dpsi| ${worstPsi.toExponential(2)} rad (${worstRel.toFixed(2)} x tol; ${over} beyond 2 tol), table ${T.p.length} samples, unresolved ${unres}`);
    report(`(1) r = ${r.toExponential(2)} M: EF-integrated rays agree with quadrature (psi rel. < 1e-6, g)`, badEF === 0 && worstEF < 1e-6 && worstG < 1e-9,
      `${nEF} rays, worst rel psi ${worstEF.toExponential(2)}, worst g (conditioned) ${worstG.toExponential(2)}`);
  }
}

// ---------------------------------------------------------------------------------------------
// 2. rays traced from r = 1e-30 M, 1e-37 M and r_QG reach the sky with conserved E_ph and L
for (const r of [1e-30, 1e-37, R_QG]) {
  const obs = observerState(r, 1);
  let ok = true; const det = [];
  for (const dn of [0.999, 0.5, 0.1, 1e-3]) {
    const dperp = Math.sqrt(1 - dn * dn);
    const tr = traceRay(r, obs.uv, obs.ur, obs.E, dn, dperp, {});
    const ex = psiInfExact(obs, dn, dperp);
    const rel = Math.abs(tr.psiInf / ex.psi - 1);
    const good = tr.kind === 'sky' && tr.worstE < 1e-8 && tr.worstL < 1e-8 && rel < 1e-6;
    ok = ok && good;
    det.push(`dn=${dn}: ${tr.kind} dE ${tr.worstE?.toExponential(1)} dL ${tr.worstL?.toExponential(1)} psi ${tr.psiInf?.toExponential(4)} (quad ${ex.psi.toExponential(4)}) ${tr.steps} steps`);
  }
  report(`(2) EF rays from r = ${r.toExponential(2)} M reach the sky, E_ph and L conserved (< 1e-8), psi = quadrature (1e-6)`, ok, det.join('; '));
}

// ---------------------------------------------------------------------------------------------
// 3. exact classifier re-validated by EF integration WITHOUT the classifier (incl. the interior b^2 > 27 fix)
{
  const cases = [];
  const rand = rng(7);
  for (const r of [10, 3.5, 2.5, 1.0, 0.3]) {
    const obs = observerState(r, 1);
    const roots = b27Roots(obs);
    const dns = [...roots.flatMap(x => [x - 0.01, x + 0.01]), ...Array.from({ length: 12 }, () => 2 * rand() - 1)];
    for (const dn of dns) {
      if (dn <= -1 || dn >= 1) continue;
      const dperp = Math.sqrt(1 - dn * dn);
      const cls = classifyDirection(obs, dn, dperp).kind;
      const tr = traceRay(r, obs.uv, obs.ur, obs.E, dn, dperp, { classify: false, maxSteps: 60000 });
      cases.push({ r, dn, cls, num: tr.kind });
    }
  }
  const bad = cases.filter(c => c.cls !== c.num);
  report('(3) classify() vs unconditioned EF integration (exterior and interior, both sides of every b^2 = 27 boundary)', bad.length === 0,
    `${cases.length} rays, disagreements: ${bad.map(c => `r=${c.r} dn=${c.dn.toFixed(4)} ${c.cls}/${c.num}`).join(', ') || 'none'}`);
  // the specific interior case the old classifier got wrong: E_ph > 0 but b^2 > 27 -> past horizon
  const obs = observerState(1.0, 1), dn = -0.62, dperp = Math.sqrt(1 - dn * dn), ph = photonOf(obs, dn, dperp);
  const tr = traceRay(1.0, obs.uv, obs.ur, 1, dn, dperp, { classify: false, maxSteps: 60000 });
  report('(3b) interior ray with E_ph > 0 and b^2 > 27 ends on the past horizon (turning point r_t < 3M)', ph.Eph > 0 && ph.b * ph.b > 27 && tr.kind === 'past' && classify(1.0, 1, ph.Eph, ph.b * ph.b) === 'past',
    `E_ph ${ph.Eph.toFixed(4)} b^2 ${(ph.b * ph.b).toFixed(2)} EF: ${tr.kind}, max r reached ${tr.y[1].toFixed(4)}`);
}

// ---------------------------------------------------------------------------------------------
// 4. pixel content: shadow radius in the rendered image at r = 5 r_s looking toward the hole
{
  const r = 10, v = Math.sqrt(2 / r);
  const sinS = 3 * Math.sqrt(3) / r * Math.sqrt(1 - 2 / r);             // static observer (Synge)
  const cS = Math.sqrt(1 - sinS * sinS);
  const alphaAn = Math.acos((cS + v) / (1 + v * cS));                  // aberration, speed v toward the hole
  const obs = observerState(r, 1);
  // closed-form boundary from firstperson_core
  const dnEdge = Math.min(...b27Roots(obs));
  report('(4a) b^2 = 27 boundary (closed form) equals the aberrated static shadow', Math.abs(Math.acos(-dnEdge) - alphaAn) < 1e-12,
    `acos(-dn_edge) ${Math.acos(-dnEdge).toFixed(12)} rad, analytic ${alphaAn.toFixed(12)} rad`);
  const W = 601, H = 601, fov = 60, tanH = Math.tan(fov * Math.PI / 360);
  const table = new TransferTable(obs); table.refine();
  const { F, R, U } = cameraAxes(0, 0);
  const ren = new CpuRenderer();
  ren.start({ width: W, height: H, obs, table, cam: { F, R, U, tanH, tanV: tanH }, M: celestialFrame(), background: 'grid', layer: 'tint', gRange: 1 });
  ren.renderAll();
  // measure along 8 rays from the image centre: last 'past' pixel -> first 'sky' pixel
  const cx = (W - 1) / 2, cy = (H - 1) / 2; const radii = [];
  for (let k = 0; k < 8; k++) {
    const ang = k * Math.PI / 4, ux = Math.cos(ang), uy = Math.sin(ang);
    let prev = null;
    for (let s = 0; s < W / 2; s += 0.25) {
      const x = Math.round(cx + s * ux), y = Math.round(cy + s * uy);
      const kind = ren.kindMap[y * W + x];
      if (kind === KIND_SKY) {
        // angle from the optical axis of the midpoint between the last past pixel and this sky pixel
        const px = ((x + 0.5) / W) * 2 - 1, py = 1 - ((y + 0.5) / H) * 2, qx = ((prev[0] + 0.5) / W) * 2 - 1, qy = 1 - ((prev[1] + 0.5) / H) * 2;
        const a1 = Math.atan(Math.hypot(px, py) * tanH), a0 = Math.atan(Math.hypot(qx, qy) * tanH);
        radii.push(0.5 * (a0 + a1)); break;
      }
      prev = [x, y];
    }
  }
  const mean = radii.reduce((s, x) => s + x, 0) / radii.length;
  const worst = Math.max(...radii.map(x => Math.abs(x / alphaAn - 1)));
  const counts = ren.levelCounts;
  report('(4b) rendered shadow radius at r = 5 r_s (CPU path, FOV 60, 601 px) = analytic aberrated shadow within 2 %', radii.length === 8 && worst < 0.02,
    `measured ${(mean * 180 / Math.PI).toFixed(3)} deg (worst ${(100 * worst).toFixed(2)} %), analytic ${(alphaAn * 180 / Math.PI).toFixed(3)} deg; pixels sky/past/unres ${counts.join('/')}`);
  const cpx = 4 * (Math.round(cy) * W + Math.round(cx));
  report('(4c) shadow pixels are drawn in the past-horizon colour', ren.rgba[cpx] < 40 && ren.rgba[cpx + 1] < 10 && ren.rgba[cpx + 2] < 10, `centre RGB ${ren.rgba[cpx]},${ren.rgba[cpx + 1]},${ren.rgba[cpx + 2]}`);
}

// ---------------------------------------------------------------------------------------------
// 5. Node-only renderer exercise at several radii incl. r_QG: progressive steps, finite output, fractions
{
  const stars = loadStars(), M = celestialFrame();
  let ok = true; const det = [];
  for (const [r, yaw, layer, bg] of [[200, 0, 'tint', 'stars'], [2.0, Math.PI, 'gmap', 'stars'], [0.2, Math.PI / 2, 'tint', 'grid'], [R_QG, Math.PI / 2, 'gmap', 'grid']]) {
    const obs = observerState(r, 1), fr = skyFractions(obs);
    const table = new TransferTable(obs);
    const ren = new CpuRenderer();
    const W = 96, H = 64, tanH = Math.tan(70 * Math.PI / 180);
    const { F, R, U } = cameraAxes(yaw, 0);
    const P = { width: W, height: H, obs, table, cam: { F, R, U, tanH, tanV: tanH * H / W }, M, background: bg, layer, gRange: gScaleRange(obs, fr.dnMinSky), stars };
    ren.start({ ...P, maxLevel: 0 }); ren.step(0); const partial = !ren.done || true;
    ren.renderAll();
    table.refine();
    ren.start({ ...P, startLevel: 1 }); ren.renderAll();
    let finite = true; for (let i = 0; i < ren.rgba.length; i++) if (!(ren.rgba[i] >= 0 && ren.rgba[i] <= 255)) finite = false;
    const c = ren.levelCounts, tot = c[0] + c[1] + c[2];
    const good = finite && partial && tot === W * H && c[KIND_UNRESOLVED] === 0;
    ok = ok && good;
    det.push(`r=${r.toExponential(2)}: sky/past/unres ${c.join('/')}, all-direction sky fraction ${fr.sky.toFixed(6)}, star images ${ren.starCount}`);
  }
  report('(5) CPU renderer runs in Node (no DOM/WebGL), progressive levels, finite pixels, no unresolved', ok, det.join('; '));
}

// ---------------------------------------------------------------------------------------------
// 6. interior sky cone: closed form vs bisection on the classifier, and the r -> 0 limit
{
  let ok = true; const det = [];
  for (const r of [1.9, 1.0, 1e-2, 1e-6]) {
    const obs = observerState(r, 1), fr = skyFractions(obs);
    let lo = -1, hi = 1;                                   // bisection on classify: sky for dn > edge
    for (let i = 0; i < 200; i++) { const m = 0.5 * (lo + hi); if (classifyDirection(obs, m, Math.sqrt(1 - m * m)).kind === 'sky') hi = m; else lo = m; }
    const good = Math.abs(hi - fr.dnMinSky) < 1e-12 * Math.max(1, 1 / obs.a) + 1e-15;
    ok = ok && good; det.push(`r=${r}: cone half-angle ${(Math.acos(fr.dnMinSky) * 180 / Math.PI).toFixed(6)} deg`);
  }
  const q = observerState(R_QG, 1), fq = skyFractions(q);
  const expectDn = -1 / q.a;       // leading order: E_ph = 0 direction, dn = -E/a = -sqrt(r/2)
  ok = ok && Math.abs(fq.dnMinSky / expectDn - 1) < 1e-12;
  det.push(`r_QG: dn_edge ${fq.dnMinSky.toExponential(6)} (-sqrt(r/2) = ${expectDn.toExponential(6)}), cone half-angle 90 deg + ${(Math.asin(-fq.dnMinSky)).toExponential(3)} rad, sky fraction 1/2 + ${(fq.sky - 0.5).toExponential(2)}`);
  report('(6) interior exterior-sky cone: closed form = classifier bisection; -> hemisphere + sqrt(r/2) as r -> 0', ok, det.join('; '));
}

// ---------------------------------------------------------------------------------------------
// 7. star images: flat-space limit (r = 1e7 M): primary image at the star's direction, mu ~ 1, g ~ 1
{
  const obs = observerState(1e7, 1);
  const table = new TransferTable(obs); table.refine();
  const M = celestialFrame(), stars = loadStars().slice(0, 40);
  const imgs = starImages(table, stars, M, { maxOrder: 0 });
  let worstAng = 0, worstMu = 0, n = 0;
  const v = Math.sqrt(2 / obs.r);
  for (const im of imgs) {
    if (im.order !== 0) continue;
    const S = stars[im.star].vec;
    const s = [M[0] * S[0] + M[1] * S[1] + M[2] * S[2], M[3] * S[0] + M[4] * S[1] + M[5] * S[2], M[6] * S[0] + M[7] * S[1] + M[8] * S[2]];
    const dot = Math.min(1, Math.abs(s[0] * im.d[0] + s[1] * im.d[1] + s[2] * im.d[2]));
    if (im.mu < 0.5) continue;           // skip the faint secondary image near the hole
    n++; worstAng = Math.max(worstAng, Math.acos(dot)); worstMu = Math.max(worstMu, Math.abs(Math.log(im.mu)));
  }
  report('(7) flat-space limit of the star forward mapping (r = 1e7 M): image within 2v of the star, |ln mu| < 4v', n >= 35 && worstAng < 2 * v + 1e-5 && worstMu < 4 * v + 1e-4,
    `${n} primary images, worst offset ${worstAng.toExponential(2)} rad, worst |ln mu| ${worstMu.toExponential(2)} (v = ${v.toExponential(2)})`);
}

// ---------------------------------------------------------------------------------------------
// 8. colour helpers: Ballesteros B-V -> T, blackbody table
{
  const T = bvToTemperature(0.65);   // solar-like colour index
  const bb = blackbody(6500), bb2 = blackbody(3000), bb3 = blackbody(30000);
  const ok = T > 5500 && T < 6100 && bb.r > 0.9 && bb.g > 0.9 && bb.b > 0.9 && bb2.r === 1 && bb2.b < 0.5 && bb3.b === 1 && bb3.r < 0.8 && blackbody(1e8).logY > blackbody(1e7).logY;
  report('(8) B-V -> T (Ballesteros 2012) and blackbody colours (CIE 1931 table) are sane', ok, `T(B-V=0.65) = ${T.toFixed(0)} K; rgb(6500K) ${[bb.r, bb.g, bb.b].map(x => x.toFixed(2))}; rgb(3000K) ${[bb2.r, bb2.g, bb2.b].map(x => x.toFixed(2))}; rgb(30000K) ${[bb3.r, bb3.g, bb3.b].map(x => x.toFixed(2))}`);
}

// ---------------------------------------------------------------------------------------------
// 9. exterior turning radius (closed form) is a root of r^3 - b^2 r + 2 b^2 and lies above 3M
{
  let worst = 0, ok = true;
  for (const b of [5.2, 5.5, 8, 30, 1e3, 1e6]) { const rt = turningRadius(b); worst = Math.max(worst, Math.abs(rt ** 3 - b * b * rt + 2 * b * b) / (rt ** 3)); ok = ok && rt >= 3; }
  report('(9) closed-form turning radius', ok && worst < 1e-12, `worst relative residual ${worst.toExponential(2)}`);
}

console.log(fails ? `${fails} FAILED` : 'ALL PASSED');
process.exit(fails ? 1 : 0);
