// Node-only checks of the viewer data layer (renders/src/data.js): playback axes, milestone navigation,
// exact radius interpolation, and the received-signal timeline (fallback computed from the samples versus the
// analytic E = 1 radial solution; consumption of the engine's signal_timeline / new columns when present).
// Run:  node tests/viewer/test_viewer_data.mjs   (from SLAB_GR_Simulation; needs renders/trajectory_data.js)
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { TrajectoryData, AXES } from '../../renders/src/data.js';

const ROOT = path.resolve(new URL('.', import.meta.url).pathname, '../..');
let fails = 0;
const report = (name, ok, detail = '') => { console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}  ${detail}`); if (!ok) fails++; };

function loadRaw() {
  const ctx = { window: {} };
  vm.runInNewContext(fs.readFileSync(path.join(ROOT, 'renders/trajectory_data.js'), 'utf8'), ctx);
  return ctx.window.SLAB_DATA;
}
const raw = loadRaw();
const data = new TrajectoryData(raw);
// A 'legacy' export without the engine's signal-timeline keys, to exercise the viewer's fallback path
// regardless of whether the committed export already carries them.
const legacyRaw = JSON.parse(JSON.stringify(raw));
delete legacyRaw.signal_timeline;
delete legacyRaw.samples.u_ret_geo;
delete legacyRaw.samples.t_receive_years;
const legacy = new TrajectoryData(legacyRaw);
const N = data.N, GMyr = data.derived.GM_over_c3_years;

// ---------------------------------------------------------------------------------------------- analytic E = 1 fall
// G = c = M = 1, x = sqrt(r/2M) = sqrt(r/r_s):  v(x) = -4 B(x) + C,  B = x^3/3 - x^2/2 + x - ln(1+x)   (physics_notes §5)
// u = v - 2 r_*,  r_* = r + 2 ln(r/2 - 1)  ->  u(x) = -4B(x) + C - 2(2x^2 + 2 ln(x^2 - 1));   1 + z = x/(x - 1)   (§11)
const B = x => x * x * x / 3 - x * x / 2 + x - Math.log1p(x);
const uOfX = x => -4 * B(x) - 2 * (2 * x * x + 2 * Math.log(x * x - 1));      // without the constant C (cancels in differences)
const zOfX = x => x / (x - 1);
const isE1 = raw.metadata.config.E === 1 && (raw.metadata.config.L_over_M ?? 0) === 0 && !(raw.metadata.config.thrust_alpha_SI > 0);

// ---------------------------------------------------------------------------------------------- (1) radius columns
{
  let worst = 0;
  for (let k = 0; k < 500; k++) {
    const lr = data.logrMin + (data.logrMax - data.logrMin) * ((k * 0.6180339887) % 1);
    const s = data.at(lr);
    worst = Math.max(worst, Math.abs(s.r_over_rs / Math.pow(10, lr) - 1), Math.abs(s.r_m / (Math.pow(10, lr) * data.derived.r_s_m) - 1));
  }
  report('(1) interpolated r, r/r_s exactly consistent with the log axis', worst < 1e-12, `worst rel ${worst.toExponential(2)}`);
  const h = data.at(0);
  report('(1b) at log10(r/r_s) = 0 the record is exactly r = r_s', h.r_over_rs === 1 && h.r_geo === 2, `r/r_s = ${h.r_over_rs}`);
}

// ---------------------------------------------------------------------------------------------- (2) playback axes
for (const name of Object.keys(AXES)) {
  const s = data.axis(name);
  if (!s) { report(`(2) axis ${name} available`, false, 'missing'); continue; }
  let mono = true; for (let i = 1; i < N; i++) if (!(s[i] > s[i - 1])) { mono = false; break; }
  let worst = 0;
  for (let k = 0; k < 400; k++) {
    const lr = data.logrMin + (data.logrMax - data.logrMin) * ((k * 0.7548776662) % 1);
    const v = data.axisAt(name, lr), back = data.logrAtAxis(name, v);
    // the linear-tau axis is flat to double precision deep inside (tau saturates): round trip only where s resolves
    if (name === 'tau' && lr < -2) continue;
    worst = Math.max(worst, Math.abs(back - lr));
  }
  report(`(2) axis ${name}: strictly increasing progress coordinate, logr -> s -> logr round trip`, mono && worst < 1e-9, `worst |Δlog r| ${worst.toExponential(2)}`);
  const [a, b] = data.axisRange(name);
  report(`(2b) axis ${name}: end points map to start and r_QG`, data.logrAtAxis(name, a) === data.logrMax && data.logrAtAxis(name, b) === data.logrMin, `range [${a.toPrecision(4)}, ${b.toPrecision(4)}]`);
}
{
  // log-tau axis equals -log10(tau_to_center_est_years) at every sample (no hidden rescaling)
  const s = data.axis('logtau'), c = raw.samples.tau_to_center_est_years;
  let worst = 0; for (let i = 0; i < N; i++) worst = Math.max(worst, Math.abs(s[i] + Math.log10(c[i])));
  report('(2c) log-τ axis is -log10(classical τ remaining) at the samples', worst < 1e-9, `worst ${worst.toExponential(2)}; span ${(s[N - 1] - s[0]).toFixed(2)} decades (log r span ${(data.logrMax - data.logrMin).toFixed(2)})`);
  if (isE1) {
    // E = 1: tau_rem = (4/3) x^3 GM/c^3, x = sqrt(r/r_s)  ->  d log10 tau_rem / d log10 r = 3/2 exactly (physics_notes §13).
    // End to end the axis spans exactly 1.5x the log-r span; locally the render export's linear resampling of the
    // engine steps (rel. error <= 3.3e-4 in tau_rem, see (2e)) perturbs the slope by up to ~0.03.
    const total = (s[N - 1] - s[0]) / (data.logrMax - data.logrMin);
    let worstSlope = 0;
    for (let i = 0; i < N - 1; i++) worstSlope = Math.max(worstSlope, Math.abs((s[i + 1] - s[i]) / (data.logr[i] - data.logr[i + 1]) - 1.5));
    report('(2d) E = 1: log-τ-remaining axis advances 1.5 decades per decade of r', Math.abs(total - 1.5) < 1e-6 && worstSlope < 0.05,
      `end-to-end ${total.toFixed(9)}, worst local |slope − 1.5| ${worstSlope.toExponential(2)}`);
  }
  // remaining-time readout: geometric interpolation reproduces the samples and follows the analytic (4/3) x^3 GM/c^3
  // between them to within the export's own resampling error (3.3e-4 at the samples of the default run)
  if (isE1) {
    let worstNode = 0, worstA = 0, worstLin = 0;
    for (let i = 0; i < N; i += 13) worstNode = Math.max(worstNode, Math.abs(data.atIndex(i).tau_to_center_est_years / raw.samples.tau_to_center_est_years[i] - 1));
    for (let k = 0; k < 600; k++) {
      const lr = data.logrMin + (data.logrMax - data.logrMin) * ((k * 0.414213562) % 1);
      const ana = (4 / 3) * Math.pow(10, 1.5 * lr) * GMyr, smp = data.at(lr);
      worstA = Math.max(worstA, Math.abs(smp.tau_to_center_est_years / ana - 1));
      const p = data.indexOf(lr), i = Math.min(N - 2, Math.floor(p)), c = raw.samples.tau_to_center_est_years;
      worstLin = Math.max(worstLin, Math.abs((c[i] + (c[i + 1] - c[i]) * (p - i)) / ana - 1));
    }
    report('(2e) τ-remaining readout: exact at the samples, analytic r^{3/2} law between them', worstNode < 1e-14 && worstA < 1e-3,
      `nodes ${worstNode.toExponential(1)}, vs analytic ${worstA.toExponential(2)} (plain linear interpolation would give ${worstLin.toExponential(2)})`);
  }
}

// ---------------------------------------------------------------------------------------------- (3) milestone navigation
{
  const seen = []; let lr = data.logrMax, m;
  while ((m = data.nextMilestone(lr, +1))) { seen.push(m.slug); lr = data.clampLogR(m.log10_r_over_rs); if (seen.length > 50) break; }
  const expected = raw.milestones.filter(x => x.slug !== 'start').map(x => x.slug);
  report('(3) "]" visits every milestone after the start in order and stops at r_QG', JSON.stringify(seen) === JSON.stringify(expected), seen.join(' > '));
  const back = []; lr = data.logrMin;
  while ((m = data.nextMilestone(lr, -1))) { back.push(m.slug); lr = data.clampLogR(m.log10_r_over_rs); if (back.length > 50) break; }
  const expectedBack = raw.milestones.filter(x => x.slug !== 'r_QG').map(x => x.slug).reverse();
  report('(3b) "[" walks back to the start', JSON.stringify(back) === JSON.stringify(expectedBack), back.join(' < '));
}

// ---------------------------------------------------------------------------------------------- (4) received-signal timeline (fallback)
{
  const tl = legacy.signalTimeline();
  const pts = tl.points;
  let mono = pts.length > 10;
  for (let i = 1; i < pts.length; i++) if (!(pts[i].t > pts[i - 1].t && pts[i].y > pts[i - 1].y)) mono = false;
  const nExt = raw.samples.r_over_rs.filter(x => x > 1).length;
  report('(4) fallback timeline from the samples: every exterior sample, t_receive and 1+z increasing', tl.source === 'samples' && mono && pts.length === nExt,
    `source ${tl.source}, ${pts.length} points (exterior samples ${nExt}), t_receive ∈ [${pts[0].t.toExponential(3)}, ${pts[pts.length - 1].t.toExponential(3)}] yr, max 1+z ${Math.pow(10, pts[pts.length - 1].y).toPrecision(4)}`);
  report('(4b) late-time e-folding time is 4GM/c^3 in years', Math.abs(tl.efoldYears / (4 * GMyr) - 1) < 1e-15, `${tl.efoldYears.toExponential(6)} yr`);
  if (isE1) {
    const x0 = Math.sqrt(pts[0].rOverRs), u0 = uOfX(x0);
    let worstT = 0, worstZ = 0;
    for (const p of pts) {
      const x = Math.sqrt(p.rOverRs);
      worstT = Math.max(worstT, Math.abs(p.t - (uOfX(x) - u0) * GMyr) / GMyr);        // in units of GM/c^3
      worstZ = Math.max(worstZ, Math.abs(Math.pow(10, p.y) / zOfX(x) - 1));
    }
    // the render export interpolates v linearly (in log r) between engine steps: up to ~0.1 GM/c^3 at 100 r_s; the
    // engine's own signal_timeline (when present) is not affected
    const span = (pts[pts.length - 1].t - pts[0].t) / GMyr;
    report('(4c) fallback t_receive = (u − u_start)·GM/c³ matches the analytic E = 1 retarded time', worstT < 0.2,
      `worst |Δt| = ${worstT.toExponential(2)} GM/c^3 = ${(worstT * GMyr).toExponential(2)} yr (${(worstT / span).toExponential(1)} of the ${span.toFixed(0)} GM/c^3 span; export resampling of v)`);
    let worstCol = 0;
    raw.samples.redshift_1pz_to_infinity.forEach((zc, i) => { if (zc !== null) worstCol = Math.max(worstCol, Math.abs(zc / zOfX(Math.sqrt(raw.samples.r_over_rs[i])) - 1)); });
    report('(4d) fallback 1+z = u^v − 2u^r/f matches the analytic 1/(1 − sqrt(r_s/r))', worstZ < 1e-4,
      `worst rel ${worstZ.toExponential(2)} (the linearly resampled redshift column itself: ${worstCol.toExponential(2)})`);
  }
  // current-point helpers: outside -> finite, inside -> null (signal never arrives)
  for (const [name, d] of [['legacy export', legacy], ['current export', data]]) {
    const out = d.at(0.3), ins = d.at(-0.3);
    report(`(4e) ${name}: t_receive and 1+z defined outside, null inside the horizon`, Number.isFinite(d.tReceiveYears(out)) && Number.isFinite(d.onePlusZ(out)) && d.tReceiveYears(ins) === null && d.onePlusZ(ins) === null,
      `outside t = ${d.tReceiveYears(out).toExponential(4)} yr, 1+z = ${d.onePlusZ(out).toPrecision(5)}`);
  }
  if (raw.signal_timeline) {
    const te = data.signalTimeline();
    report('(4f) current export: the engine timeline is used and reaches r/r_s - 1 <= 1e-11', te.source === 'engine' && Math.min(...raw.signal_timeline.eps) <= 1e-11,
      `${te.points.length} points, max 1+z ${Math.pow(10, te.points[te.points.length - 1].y).toExponential(3)}`);
  }
}

// ---------------------------------------------------------------------------------------------- (5) late-time asymptote (analytic)
{
  // d ln(1+z)/d t_receive -> 1/(4 GM/c^3): check the analytic E = 1 relation at eps = r/r_s - 1 = 1e-6 ... 1e-12
  let worst = 0;
  for (const eps of [1e-6, 1e-8, 1e-10, 1e-12]) {
    const x1 = Math.sqrt(1 + eps), x2 = Math.sqrt(1 + eps * 0.5);
    const dlnz = Math.log(zOfX(x2)) - Math.log(zOfX(x1)), du = uOfX(x2) - uOfX(x1);
    worst = Math.max(worst, Math.abs(dlnz / du * 4 - 1));
  }
  report('(5) analytic late-time slope d ln(1+z)/du = 1/(4M) (e-folding 4GM/c^3)', worst < 1e-5, `worst rel dev ${worst.toExponential(2)}`);
}

// ---------------------------------------------------------------------------------------------- (6) engine contract consumption (mock)
{
  const mock = JSON.parse(JSON.stringify(raw));
  const eps = [], rr = [], tr = [], z = [], tau = [];
  const x0 = Math.sqrt(mock.samples.r_over_rs[0]), u0 = uOfX(x0);
  for (let k = 0; k <= 200; k++) {
    const e = Math.pow(10, Math.log10(x0 * x0 - 1) + (-12 - Math.log10(x0 * x0 - 1)) * k / 200), x = Math.sqrt(1 + e);
    eps.push(e); rr.push(1 + e); tr.push((uOfX(x) - u0) * GMyr); z.push(zOfX(x)); tau.push((4 / 3) * (x0 ** 3 - x ** 3) * GMyr);
  }
  mock.signal_timeline = { note: 'mock (analytic E = 1)', eps, r_over_rs: rr, t_receive_years: tr, one_plus_z: z, tau_years: tau, t_schw_years: tr.map(() => null), late_time_efold_years: 4 * GMyr };
  mock.samples.t_receive_years = mock.samples.r_over_rs.map((r, i) => (r > 1 ? 12345 + i : null));
  const d2 = new TrajectoryData(mock), tl = d2.signalTimeline();
  report('(6) engine signal_timeline is used when present', tl.source === 'engine' && tl.points.length === 201 && Math.abs(tl.points[200].y - Math.log10(zOfX(Math.sqrt(1 + 1e-12)))) < 1e-9,
    `max log10(1+z) ${tl.points[200].y.toFixed(3)}`);
  const smp = d2.atIndex(10);
  report('(6b) per-sample t_receive_years column is used when present', d2.tReceiveYears(smp) === 12355, `${d2.tReceiveYears(smp)}`);
  report('(6c) without the new keys the viewer falls back to the samples', legacy.signalTimeline().source === 'samples' && legacyRaw.signal_timeline === undefined);
}

console.log(fails ? `${fails} FAILED` : 'ALL PASSED');
process.exit(fails ? 1 : 0);
