// Pixel-content checks of the viewer (not just "no console errors"):
//   (A) light-cone inset: the generators are read back from the inset canvas pixels and their slopes measured;
//       at r = r_s the outgoing generator is exactly vertical, outside it tilts outward, inside both tilt inward;
//   (B) causal diagrams: the current-point marker is found in the canvas pixels at the position predicted from the
//       sample's kruskal_T/X (penrose_T/X); the diagram's frame is verified independently by probing the drawn
//       horizon and singularity lines at their analytic positions;
//   (C) received-signal timeline: marker at the pixel predicted from (t_receive, log10(1+z)); curve through the data;
//       no marker inside the horizon; the engine's signal_timeline is consumed when present (mock export);
//   (D) playback axes: the position moves monotonically on every axis and across axis switches; constant rate in
//       log10(r/r_s) and in log10(τ remaining); the readout always shows r, τ and the remaining time.
// Run standalone:  node tests/viewer/test_pixels_browser.mjs      (also run by tests/viewer/check_viewer.mjs)
import { createRequire } from 'node:module';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const URL_VIEWER = 'file://' + path.join(ROOT, 'renders/viewer.html');
const SHOTS = path.join(ROOT, 'renders/screenshots');

// in-page helpers (serialized into page.evaluate)
const PAGE_HELPERS = `
window.__px = {
  rgb(hex) { const n = parseInt(hex.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; },
  // disc of colour 'col' near (cx, cy) [canvas px]: best-scoring centre (hits within radius 3), refined by the centroid
  findDisc(canvas, cx, cy, col, R = 14) {
    const ctx = canvas.getContext('2d');
    const x0 = Math.max(0, Math.round(cx - R)), y0 = Math.max(0, Math.round(cy - R));
    const w = Math.min(canvas.width - x0, 2 * R + 1), h = Math.min(canvas.height - y0, 2 * R + 1);
    const img = ctx.getImageData(x0, y0, w, h).data;
    const hit = (x, y) => { if (x < 0 || y < 0 || x >= w || y >= h) return false; const i = (y * w + x) * 4;
      return Math.abs(img[i] - col[0]) < 40 && Math.abs(img[i + 1] - col[1]) < 40 && Math.abs(img[i + 2] - col[2]) < 40; };
    let best = { n: -1 };
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      let n = 0; for (let dy = -3; dy <= 3; dy++) for (let dx = -3; dx <= 3; dx++) if (dx * dx + dy * dy <= 9 && hit(x + dx, y + dy)) n++;
      if (n > best.n) best = { x, y, n };
    }
    let sx = 0, sy = 0, n = 0;
    for (let dy = -4; dy <= 4; dy++) for (let dx = -4; dx <= 4; dx++) if (dx * dx + dy * dy <= 12.25 && hit(best.x + dx, best.y + dy)) { sx += best.x + dx; sy += best.y + dy; n++; }
    return n ? { x: x0 + sx / n + 0.5, y: y0 + sy / n + 0.5, score: best.n } : { x: NaN, y: NaN, score: 0 };
  },
  // is there a pixel of colour col within 'rad' px of (cx, cy)?
  near(canvas, cx, cy, col, rad = 2, tol = 45) {
    const ctx = canvas.getContext('2d'), x0 = Math.round(cx - rad), y0 = Math.round(cy - rad), s = 2 * rad + 1;
    const img = ctx.getImageData(x0, y0, s, s).data;
    for (let i = 0; i < img.length; i += 4) if (Math.abs(img[i] - col[0]) < tol && Math.abs(img[i + 1] - col[1]) < tol && Math.abs(img[i + 2] - col[2]) < tol) return true;
    return false;
  },
};`;

// ------------------------------------------------------------------------------------------ (A) light-cone inset
async function measureInset(page, logr) {
  await page.evaluate(lr => { SLAB_APP.setView('scene'); SLAB_APP.setSceneMode('log'); SLAB_APP.setLogR(lr); }, logr);
  await page.waitForTimeout(120);
  return page.evaluate(() => {
    const v = SLAB_APP.views.scene; v.renderNow();
    const g = v.insetGeom, c = v.inset, img = c.getContext('2d').getImageData(0, 0, c.width, c.height).data, W = c.width, d = g.dpr;
    // generator colour #ffd166 (anti-aliased edges keep its hue); excludes the translucent cone fill, the orange horizon
    // marker (#ff8c42), the blue worldline and the grey axes
    const yellow = i => { const r = img[i], gg = img[i + 1], b = img[i + 2]; return r > 190 && gg > 150 && b < 175 && gg / r > 0.72 && gg / r < 0.95 && r - b > 90; };
    const rows = [];
    for (let y = Math.ceil((g.oy - g.T + 2) * d); y <= Math.floor((g.oy - 8) * d); y++) {
      const cl = []; let cur = null;
      for (let x = 0; x < W; x++) if (yellow((y * W + x) * 4)) {
        if (cur && x - cur.last <= 2) { cur.sum += x; cur.n++; cur.last = x; } else { cur = { sum: x, n: 1, last: x }; cl.push(cur); }
      }
      rows.push({ y: y + 0.5, xs: cl.map(k => k.sum / k.n + 0.5) });
    }
    return { g, rows, rOverRs: SLAB_APP.state.sample.r_over_rs };
  });
}
function fitLine(pts) {       // least squares x = a + b y
  const n = pts.length; if (n < 3) return null;
  let sy = 0, sx = 0, syy = 0, sxy = 0; for (const [y, x] of pts) { sy += y; sx += x; syy += y * y; sxy += x * y; }
  const b = (n * sxy - sx * sy) / (n * syy - sy * sy), a = (sx - b * sy) / n;
  return { a, b, n, spread: Math.max(...pts.map(p => p[1])) - Math.min(...pts.map(p => p[1])) };
}
function analyseInset(m) {
  const out = [], inn = [];
  for (const r of m.rows) if (r.xs.length >= 2) { out.push([r.y, Math.max(...r.xs)]); inn.push([r.y, Math.min(...r.xs)]); }
  const fo = fitLine(out), fi = fitLine(inn), d = m.g.dpr;
  // dr/dt_EF = -dx/dy (t_EF up = -y; one unit of t and of r are both T pixels)
  return { sOut: fo ? -fo.b : NaN, sIn: fi ? -fi.b : NaN, apexOut: fo ? (fo.a + fo.b * m.g.oy * d) / d : NaN, spreadOut: fo ? fo.spread / d : NaN, nRows: out.length,
    expected: (() => { const f = 1 - 1 / m.rOverRs; return f / (2 - f); })() };
}

export async function runPixelChecks(page, report, opts = {}) {
  await page.addScriptTag({ content: PAGE_HELPERS });
  const shots = opts.shots !== false;
  // ---------------------------------------------------------------- (A)
  {
    const h = analyseInset(await measureInset(page, 0));
    if (shots) await page.screenshot({ path: path.join(SHOTS, 'pixel-cone-horizon.png') });
    report('(A1) r = r_s: outgoing generator exactly vertical in the inset pixels', h.nRows > 20 && Math.abs(h.sOut) < 0.01 && h.spreadOut <= 1.0 && Math.abs(h.apexOut - (await page.evaluate(() => SLAB_APP.views.scene.insetGeom.ox))) <= 1.0,
      `measured dr/dt_EF = ${h.sOut.toExponential(2)} over ${h.nRows} rows, x-spread ${h.spreadOut.toFixed(2)} px, apex x offset ${(h.apexOut - (await page.evaluate(() => SLAB_APP.views.scene.insetGeom.ox))).toFixed(2)} px`);
    report('(A1b) r = r_s: ingoing generator at 45° (dr/dt_EF = −1)', Math.abs(h.sIn + 1) < 0.03, `measured ${h.sIn.toFixed(4)}`);
    for (const lr of [0.3, 1.0]) {
      const o = analyseInset(await measureInset(page, lr));
      report(`(A2) outside (log10 r/r_s = ${lr}): outgoing generator tilts outward, slope f/(2−f) = ${o.expected.toFixed(4)}`, o.sOut > 0 && Math.abs(o.sOut - o.expected) < 0.03 && Math.abs(o.sIn + 1) < 0.03,
        `measured out ${o.sOut.toFixed(4)}, in ${o.sIn.toFixed(4)} (${o.nRows} rows)`);
    }
    for (const lr of [-0.3, -1.0]) {
      const o = analyseInset(await measureInset(page, lr));
      if (shots && lr === -0.3) await page.screenshot({ path: path.join(SHOTS, 'pixel-cone-inside.png') });
      report(`(A3) inside (log10 r/r_s = ${lr}): both generators tilt inward, outgoing slope ${o.expected.toFixed(4)}`, o.sOut < 0 && o.sIn < 0 && Math.abs(o.sOut - o.expected) < 0.03,
        `measured out ${o.sOut.toFixed(4)}, in ${o.sIn.toFixed(4)} (${o.nRows} rows)`);
    }
  }
  // ---------------------------------------------------------------- (B)
  {
    await page.evaluate(() => { SLAB_APP.setView('causal'); SLAB_APP.views.causal.setMode('both'); });
    for (const lr of [0.1, -0.2, -0.6, -1.5]) {
      await page.evaluate(x => SLAB_APP.setLogR(x), lr);
      await page.waitForTimeout(120);
      const r = await page.evaluate(() => {
        const cv = SLAB_APP.views.causal, smp = SLAB_APP.state.sample, P = window.__px, res = {};
        for (const [name, kx, kt] of [['kruskal', 'kruskal_X', 'kruskal_T'], ['penrose', 'penrose_X', 'penrose_T']]) {
          const p = cv[name], m = p.map, X = smp[kx], T = smp[kt];
          if (!m || !Number.isFinite(X) || !Number.isFinite(T)) { res[name] = { skipped: true, X, T }; continue; }
          const px = (x, t) => [(m.ox + (x - m.xmin) * m.scale) * p.dpr, (m.oy + (m.ymax - t) * m.scale) * p.dpr];
          const [ex, ey] = px(X, T);
          const col = P.rgb(p.marker ? p.marker.color : '#6ee7a0');
          const found = P.findDisc(p.canvas, ex, ey, col);
          // independent check of the frame: analytic curves drawn by the diagram must be at their predicted pixels
          const hz = P.rgb('#7ab7ff'), sg = P.rgb('#ff6b6b');
          const probes = name === 'kruskal'
            ? [['horizon T = X', -0.6, -0.6, hz], ['horizon T = −X', 0.6, -0.6, hz], ['horizon T = −X (II/III)', -0.9, 0.9, hz], ['singularity T² − X² = 1', 1.6, Math.sqrt(1 + 1.6 * 1.6), sg], ['singularity', -1.2, Math.sqrt(1 + 1.44), sg]]
            : [['future horizon T̃ = X̃', 0.12, 0.12, hz], ['singularity T̃ = π/4', -0.45, Math.PI / 4, sg], ['singularity', 0.3, Math.PI / 4, sg]];
          const probeRes = probes.map(([lbl, x, t, c]) => { const [qx, qy] = px(x, t); return [lbl, P.near(p.canvas, qx, qy, c, Math.max(2, Math.round(2 * p.dpr)))]; });
          res[name] = { X, T, expected: [ex, ey], found: [found.x, found.y], score: found.score, probes: probeRes, dpr: p.dpr };
        }
        return res;
      });
      for (const name of ['kruskal', 'penrose']) {
        const q = r[name];
        if (q.skipped) { report(`(B) ${name} marker at log10 r/r_s = ${lr}`, false, `coordinates not finite: ${q.X}, ${q.T}`); continue; }
        const dx = q.found[0] - q.expected[0], dy = q.found[1] - q.expected[1];
        report(`(B) ${name} current-point marker at the pixel predicted from ${name === 'kruskal' ? 'kruskal_X/T' : 'penrose_X/T'} (log10 r/r_s = ${lr})`,
          q.score >= 20 && Math.hypot(dx, dy) <= 1.0 * q.dpr,
          `X = ${q.X.toFixed(4)}, T = ${q.T.toFixed(4)} -> predicted (${q.expected[0].toFixed(1)}, ${q.expected[1].toFixed(1)}), found (${q.found[0].toFixed(1)}, ${q.found[1].toFixed(1)}), score ${q.score}`);
        if (lr === 0.1) {
          const bad = q.probes.filter(p => !p[1]).map(p => p[0]);
          report(`(B0) ${name} frame: analytic horizon / singularity curves drawn at their predicted pixels`, bad.length === 0, bad.length ? `missing: ${bad.join(', ')}` : `${q.probes.length} probes found`);
        }
      }
    }
    if (shots) await page.screenshot({ path: path.join(SHOTS, 'pixel-causal-markers.png') });
    // off-chart at the start: no marker drawn in the Kruskal window, compactified marker present
    await page.evaluate(() => SLAB_APP.jumpTo('start'));
    await page.waitForTimeout(100);
    const st = await page.evaluate(() => ({ k: SLAB_APP.views.causal.kruskal.marker, p: SLAB_APP.views.causal.penrose.marker, X: SLAB_APP.state.sample.kruskal_X }));
    report('(B1) start (X ~ 1e171): no Kruskal marker (off-chart, labelled), compactified marker present', st.k === null && st.p !== null, `kruskal_X = ${st.X}`);
  }
  // ---------------------------------------------------------------- (C)
  await checkSignal(page, report, 'samples', shots);
  // ---------------------------------------------------------------- (D)
  await checkPlayback(page, report);
}

async function checkSignal(page, report, expectSource, shots) {
  await page.evaluate(() => { SLAB_APP.setView('causal'); SLAB_APP.views.causal.setMode('both'); });
  for (const lr of [0.3, 0.05]) {
    await page.evaluate(x => SLAB_APP.setLogR(x), lr);
    await page.waitForTimeout(120);
    const r = await page.evaluate(() => {
      const cv = SLAB_APP.views.causal, p = cv.signal, d = SLAB_APP.data, smp = SLAB_APP.state.sample, P = window.__px;
      const t = d.tReceiveYears(smp), y = Math.log10(d.onePlusZ(smp)), tl = d.signalTimeline();
      const res = { source: tl.source, n: tl.points.length, t, y, plots: [] };
      for (const q of p.plots || []) {
        const X = v => (q.px0 + (v - q.x0) / (q.x1 - q.x0) * (q.px1 - q.px0)) * p.dpr, Y = v => (q.py1 - (v - q.y0) / (q.y1 - q.y0) * (q.py1 - q.py0)) * p.dpr;
        const inRange = t >= q.x0 && t <= q.x1 && y >= q.y0 && y <= q.y1;
        const ex = X(t), ey = Y(y);
        const found = inRange ? P.findDisc(p.canvas, ex, ey, P.rgb('#6ee7a0')) : null;
        // curve through the data: pick data points inside the plot (away from the marker) and look for the curve colour
        const inside = tl.points.filter(pt => pt.t > q.x0 && pt.t < q.x1 && pt.y > q.y0 && pt.y < q.y1 && Math.hypot(X(pt.t) - ex, Y(pt.y) - ey) > 12 * p.dpr);
        const probe = inside.filter((_, i) => i % Math.max(1, Math.floor(inside.length / 6)) === 0).slice(0, 6);
        const curveOk = probe.filter(pt => P.near(p.canvas, X(pt.t), Y(pt.y), P.rgb('#7ab7ff'), Math.max(2, Math.round(2 * p.dpr)))).length;
        res.plots.push({ title: q.title, inRange, expected: [ex, ey], found: found ? [found.x, found.y, found.score] : null, curveProbes: probe.length, curveOk,
          slopeCheck: q.asymptote.slopePerYear * tl.efoldYears / Math.LOG10E, dpr: p.dpr });
      }
      return res;
    });
    report(`(C) signal timeline source = ${expectSource}`, r.source === expectSource, `${r.source}, ${r.n} points`);
    for (const q of r.plots) {
      if (!q.inRange) continue;
      const dd = Math.hypot(q.found[0] - q.expected[0], q.found[1] - q.expected[1]);
      report(`(C1) ${q.title}: emission marker at the pixel predicted from (t_receive, log10 1+z) (log10 r/r_s = ${lr})`, q.found[2] >= 20 && dd <= 1.0 * q.dpr,
        `t = ${r.t.toExponential(5)} yr, log10(1+z) = ${r.y.toFixed(4)}; predicted (${q.expected[0].toFixed(1)}, ${q.expected[1].toFixed(1)}), found (${q.found[0].toFixed(1)}, ${q.found[1].toFixed(1)}), score ${q.found[2]}`);
      report(`(C2) ${q.title}: curve drawn through the timeline data`, q.curveProbes >= 3 && q.curveOk === q.curveProbes, `${q.curveOk}/${q.curveProbes} data points on the curve`);
      report(`(C3) ${q.title}: asymptote slope = log10(e)/(4GM/c³)`, Math.abs(q.slopeCheck - 1) < 1e-12, `ratio ${q.slopeCheck}`);
    }
  }
  if (shots) await page.screenshot({ path: path.join(SHOTS, `pixel-signal-${expectSource}.png`) });
  await page.evaluate(() => SLAB_APP.setLogR(-0.3));
  await page.waitForTimeout(100);
  const ins = await page.evaluate(() => ({ marker: SLAB_APP.views.causal.signal.marker, all: SLAB_APP.views.causal.signal.markerAll }));
  report('(C4) inside the horizon: no emission marker (light never reaches the distant observer)', ins.marker === null && ins.all.length === 0);
}

async function checkPlayback(page, report) {
  const axes = await page.evaluate(() => ['logr', 'logtau', 'tau'].filter(a => SLAB_APP.data.axisAvailable(a)));
  report('(D0) all three playback axes available with the default export', axes.length === 3, axes.join(', '));
  for (const ax of axes) {
    const r = await page.evaluate(a => {
      const A = SLAB_APP; A.togglePlay(false); A.setView('spec'); A.setAxis(a); A.setSpeedIndex(4); A.goStart(); A.togglePlay(true);
      const rate = a === 'tau' ? 0.02 * A.state.speedDecPerS : A.state.speedDecPerS, dt = 0.05;
      const rec = []; let k = 0;
      while (A.state.logr > A.data.logrMin && k++ < 5000) {
        const s0 = A.data.axisAt(a, A.state.logr); A.advance(dt, { noRender: true });
        const smp = A.data.at(A.state.logr);
        rec.push([A.state.logr, smp.tau_years, smp.tau_to_center_est_years, A.data.axisAt(a, A.state.logr) - s0]);
      }
      return { rec, rate, dt, end: A.state.logr === A.data.logrMin, playing: A.state.playing };
    }, ax);
    let monoR = true, monoTau = true, monoRem = true, rateDev = 0;
    for (let i = 1; i < r.rec.length; i++) {
      if (!(r.rec[i][0] < r.rec[i - 1][0])) monoR = false;
      if (r.rec[i][1] < r.rec[i - 1][1]) monoTau = false;
      if (!(r.rec[i][2] < r.rec[i - 1][2])) monoRem = false;
    }
    for (let i = 0; i < r.rec.length - 1; i++) rateDev = Math.max(rateDev, Math.abs(r.rec[i][3] / (r.rate * r.dt) - 1));
    const constRate = ax === 'tau' ? true : rateDev < 1e-6;
    report(`(D1) axis ${ax}: playback moves r monotonically inward, τ never decreases, τ remaining strictly decreases, stops at r_QG`,
      monoR && monoTau && monoRem && r.end && !r.playing, `${r.rec.length} frames of ${r.dt} s`);
    if (ax !== 'tau') report(`(D2) axis ${ax}: constant rate ${r.rate} dec/s in its coordinate`, constRate, `max rel. deviation ${rateDev.toExponential(2)}`);
  }
  // axis switches: the position never jumps, and playback stays monotonic across switches
  const sw = await page.evaluate(() => {
    const A = SLAB_APP; A.setAxis('logr'); A.goStart(); A.togglePlay(true);
    const seq = [['logr', 150], ['logtau', 150], ['tau', 80], ['logr', 100000]];
    let prev = A.state.logr, mono = true, jumps = 0;
    for (const [ax, n] of seq) {
      const before = A.state.logr; A.setAxis(ax); if (A.state.logr !== before) jumps++;
      for (let k = 0; k < n && A.state.logr > A.data.logrMin; k++) { A.advance(0.05, { noRender: true }); if (!(A.state.logr < prev)) mono = false; prev = A.state.logr; }
    }
    return { mono, jumps, end: A.state.logr === A.data.logrMin };
  });
  report('(D3) switching the playback axis keeps the position and playback stays monotonic', sw.mono && sw.jumps === 0 && sw.end, `jumps ${sw.jumps}`);
  // rendered playback: readout always shows true r, τ and the remaining time (also at the deepest point, in seconds)
  const ro = await page.evaluate(async () => {
    const A = SLAB_APP; A.setView('scene'); A.setAxis('logtau'); A.goStart(); A.togglePlay(true);
    const texts = [];
    for (let k = 0; k < 12; k++) { A.advance(0.4); texts.push(document.getElementById('pos').textContent); }
    A.goEnd(); texts.push(document.getElementById('pos').textContent);
    A.togglePlay(false); A.setAxis('logr');
    return texts;
  });
  const okAll = ro.every(t => /r = \S+ m/.test(t) && /r\/r_s = /.test(t) && /τ = /.test(t) && /τ remaining ≈ \S+ (yr|s)/.test(t));
  report('(D4) position readout shows r, r/r_s, τ and τ remaining at every frame (log-τ playback)', okAll && /τ remaining ≈ [0-9.]+e-4\d s/.test(ro[ro.length - 1]),
    `last: ${ro[ro.length - 1].replace(/\n/g, ' | ')}`);
}

// ------------------------------------------------------------------------------------------ engine-contract mock
// Augments window.SLAB_DATA before the viewer runs with an ANALYTIC E = 1 signal_timeline and the new per-sample
// columns (test data only — the real export comes from the engine).
export const MOCK_CONTRACT = `(() => {
  let D;
  Object.defineProperty(window, 'SLAB_DATA', { configurable: true, get() { return D; }, set(raw) {
    const s = raw.samples, GMyr = raw.metadata.derived.GM_over_c3_years, N = raw.n_samples;
    const B = x => x * x * x / 3 - x * x / 2 + x - Math.log1p(x);
    const u = x => -4 * B(x) - 2 * (2 * x * x + 2 * Math.log(x * x - 1));
    const x0 = Math.sqrt(s.r_over_rs[0]), u0 = u(x0);
    const e0 = x0 * x0 - 1, st = { note: 'TEST MOCK: analytic E = 1 timeline', eps: [], r_over_rs: [], t_receive_years: [], one_plus_z: [], tau_years: [], t_schw_years: [], late_time_efold_years: 4 * GMyr };
    for (let k = 0; k <= 300; k++) { const e = Math.pow(10, Math.log10(e0) + (-12 - Math.log10(e0)) * k / 300), x = Math.sqrt(1 + e);
      st.eps.push(e); st.r_over_rs.push(1 + e); st.t_receive_years.push((u(x) - u0) * GMyr); st.one_plus_z.push(x / (x - 1)); st.tau_years.push((4 / 3) * (x0 ** 3 - x ** 3) * GMyr); st.t_schw_years.push(null); }
    raw.signal_timeline = st;
    s.u_ret_geo = s.r_geo.map((r, i) => r > 2 ? s.v_geo[i] - 2 * (r + 2 * Math.log(r / 2 - 1)) : null);
    s.t_receive_years = s.u_ret_geo.map(v => v === null ? null : (v - s.u_ret_geo[0]) * GMyr);
    // window.__MOCK_THRUST: fabricated non-zero inertial term on the first 50 samples (display test only)
    s.inertial_diff_radial_m_s2 = s.r_geo.map((r, i) => (window.__MOCK_THRUST && i < 50 ? -1e-3 : 0));
    s.radial_total_diff_m_s2 = s.radial_stretch_m_s2.map((v, i) => v + s.inertial_diff_radial_m_s2[i]);
    D = raw;
  } });
})();`;

export async function runContractChecks(browser, report, opts = {}) {
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push(String(e)));
  await page.addInitScript({ content: MOCK_CONTRACT });
  await page.goto(URL_VIEWER);
  await page.waitForFunction(() => window.SLAB_APP && window.SLAB_APP.state.sample, null, { timeout: 30000 });
  await page.addScriptTag({ content: PAGE_HELPERS });
  const info = await page.evaluate(() => {
    const d = SLAB_APP.data, tl = d.signalTimeline(), smp = d.at(0.3);
    const n = tl.points.length, a = tl.points[n - 2], b = tl.points[n - 1];
    return { source: tl.source, n, maxY: b.y, lateSlopeRatio: ((b.y - a.y) / (b.t - a.t)) * tl.efoldYears / Math.LOG10E,
      usesColumn: d.tReceiveYears(smp) === smp.t_receive_years, inertialRows: /Inertial/.test(document.getElementById('dashboard').textContent) };
  });
  report('(E1) engine signal_timeline consumed (mock export with the new keys)', info.source === 'engine' && info.n === 301 && info.maxY > 12, `${info.n} points, max log10(1+z) = ${info.maxY.toFixed(3)}`);
  report('(E2) late-time slope of the exported timeline equals the drawn asymptote 1/(4GM/c³)', Math.abs(info.lateSlopeRatio - 1) < 1e-4, `ratio ${info.lateSlopeRatio.toFixed(6)}`);
  report('(E3) per-sample t_receive_years column used for the current point; inertial rows hidden when the engine is off everywhere', info.usesColumn && !info.inertialRows);
  await checkSignal(page, report, 'engine', opts.shots !== false);
  await page.evaluate(() => SLAB_APP.setLogR(0.02));
  await page.waitForTimeout(150);
  if (opts.shots !== false) await page.screenshot({ path: path.join(SHOTS, 'causal-signal-engine-mock.png') });
  const dashOut = await page.evaluate(() => { SLAB_APP.setLogR(0.3); return document.getElementById('dashboard').textContent; });
  const dashIn = await page.evaluate(() => { SLAB_APP.setLogR(-0.3); return document.getElementById('dashboard').textContent; });
  report('(E4) dashboard: reception-time row outside the horizon, none inside', /Signal received at t_receive\s*2\.45\d+e8 yr after the start signal/.test(dashOut) && !/Signal received at t_receive/.test(dashIn));
  await page.close();
  // engine-on display (fabricated test column): inertial rows appear, with "engine off here" where the column is 0
  const p2 = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  p2.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  p2.on('pageerror', e => errors.push(String(e)));
  await p2.addInitScript({ content: 'window.__MOCK_THRUST = true;' });
  await p2.addInitScript({ content: MOCK_CONTRACT });
  await p2.goto(URL_VIEWER);
  await p2.waitForFunction(() => window.SLAB_APP && window.SLAB_APP.state.sample, null, { timeout: 30000 });
  const on = await p2.evaluate(() => { SLAB_APP.setLogR(1.9); return document.getElementById('dashboard').textContent; });
  const off = await p2.evaluate(() => { SLAB_APP.setLogR(-1); return document.getElementById('dashboard').textContent; });
  report('(E5) dashboard: inertial (thrust) differential and radial total rows when the engine was on', /Inertial \(thrust\) differential\s*-0\.00100 m\/s² across 2 m/.test(on) && /Radial total \(tidal \+ inertial\)/.test(on) && /0 \(engine off here\)/.test(off));
  await p2.close();
  report('(E6) no console errors with the extended export', errors.length === 0, errors.join(' | '));
}

// ------------------------------------------------------------------------------------------ standalone
const isMain = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isMain) {
  const require = createRequire(path.join(ROOT, 'renders/build/package.json'));
  const { chromium } = require('playwright-core');
  const executablePath = process.env.CHROMIUM_PATH || (fs.existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : chromium.executablePath());
  fs.mkdirSync(SHOTS, { recursive: true });
  const browser = await chromium.launch({ executablePath, headless: true,
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--no-sandbox'] });
  let fails = 0;
  const report = (name, ok, detail = '') => { console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}  ${detail}`); if (!ok) fails++; };
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push(String(e)));
  await page.goto(URL_VIEWER);
  await page.waitForFunction(() => window.SLAB_APP && window.SLAB_APP.state.sample, null, { timeout: 30000 });
  await runPixelChecks(page, report);
  report('no console errors', errors.length === 0, errors.join(' | '));
  await page.close();
  await runContractChecks(browser, report);
  await browser.close();
  console.log(fails ? `${fails} FAILED` : 'ALL PASSED');
  process.exit(fails ? 1 : 0);
}
