// Keyboard / touch / toolbar controls, help overlay and PNG export of the viewer.
//   keyboard: Space, ← →, Shift+arrows, Home/End, [ ], + −, 1–4, ?, Esc (and no hijacking of focused selects);
//   toolbar buttons (mouse and touch taps); OrbitControls one-finger orbit and two-finger pinch (CDP touch events);
//   PNG export: the download is a valid PNG of the composited view + caption strip, the image region is not blank
//   (render-then-capture of the WebGL views), and the caption carries r, τ, remaining time, regime and the banners;
//   HiDPI: the 3D canvas is laid out at the container size.
// Run standalone:  node tests/viewer/test_controls_browser.mjs      (also run by tests/viewer/check_viewer.mjs)
import { createRequire } from 'node:module';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const URL_VIEWER = 'file://' + path.join(ROOT, 'renders/viewer.html');
const SHOTS = path.join(ROOT, 'renders/screenshots');

async function openPage(browser, ctxOpts, errors) {
  const context = await browser.newContext({ viewport: { width: 1400, height: 900 }, acceptDownloads: true, ...ctxOpts });
  const page = await context.newPage();
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push(String(e)));
  await page.goto(URL_VIEWER);
  await page.waitForFunction(() => window.SLAB_APP && window.SLAB_APP.state.sample, null, { timeout: 30000 });
  return { context, page };
}
const st = page => page.evaluate(() => ({ logr: SLAB_APP.state.logr, playing: SLAB_APP.state.playing, speedIndex: SLAB_APP.state.speedIndex, view: SLAB_APP.state.view,
  help: !document.getElementById('help').classList.contains('hidden'), max: SLAB_APP.data.logrMax, min: SLAB_APP.data.logrMin, axis: SLAB_APP.state.axis }));

export async function runControlChecks(browser, report, opts = {}) {
  const shots = opts.shots !== false;
  const errors = [];
  // ------------------------------------------------------------------------------------------ keyboard
  {
    const { context, page } = await openPage(browser, {}, errors);
    const k = async key => { await page.keyboard.press(key); return st(page); };
    let s = await st(page);
    s = await k('End'); report('(K1) End -> r_QG (end of the validated run)', s.logr === s.min);
    s = await k('Home'); report('(K2) Home -> start', s.logr === s.max);
    s = await k('ArrowRight'); report('(K3) → steps 0.25 dec inward on the log r axis', Math.abs(s.logr - (s.max - 0.25)) < 1e-12, `logr ${s.logr}`);
    s = await k('Shift+ArrowRight'); report('(K4) Shift+→ fine step (0.01 dec)', Math.abs(s.logr - (s.max - 0.26)) < 1e-12, `logr ${s.logr}`);
    s = await k('ArrowLeft'); report('(K5) ← steps back', Math.abs(s.logr - (s.max - 0.01)) < 1e-12, `logr ${s.logr}`);
    await k('Home');
    s = await k(']'); const isco = await page.evaluate(() => SLAB_APP.data.milestone('isco').log10_r_over_rs);
    report('(K6) ] -> next milestone (ISCO)', Math.abs(s.logr - isco) < 1e-12, `logr ${s.logr}`);
    s = await k(']'); s = await k(']');
    report('(K7) ] ] -> photon sphere, horizon', Math.abs(s.logr) < 1e-12, `logr ${s.logr}`);
    s = await k('['); report('(K8) [ -> previous milestone (photon sphere)', Math.abs(s.logr - Math.log10(1.5)) < 1e-9, `logr ${s.logr}`);
    const sp0 = s.speedIndex;
    s = await k('+'); report('(K9) + faster', s.speedIndex === sp0 + 1);
    s = await k('-'); s = await k('-'); report('(K10) − slower', s.speedIndex === sp0 - 1);
    s = await k('Space'); report('(K11) Space plays', s.playing === true);
    await page.waitForTimeout(300);
    s = await k('Space'); report('(K12) Space pauses (and playback advanced the position inward)', s.playing === false && s.logr < Math.log10(1.5), `logr ${s.logr}`);
    s = await k('2'); report('(K13) 2 -> causal tab', s.view === 'causal');
    s = await k('4'); report('(K14) 4 -> speculative menu', s.view === 'spec');
    s = await k('1'); report('(K15) 1 -> 3D view', s.view === 'scene');
    s = await k('?'); report('(K16) ? opens the help overlay', s.help === true);
    if (shots) await page.screenshot({ path: path.join(SHOTS, 'help-overlay.png') });
    s = await k('Escape'); report('(K17) Esc closes the help overlay', s.help === false);
    // a focused <select> keeps its keys (no view switch, no step)
    await page.focus('#speed');
    const before = await st(page);
    await page.keyboard.press('3');
    s = await st(page); report('(K18) keys typed into a focused select are not hijacked', s.view === before.view && s.logr === before.logr);
    await page.evaluate(() => document.activeElement.blur());
    // toolbar buttons (mouse)
    await page.click('#btn-end'); s = await st(page); report('(T1) toolbar ⇥ -> end', s.logr === s.min);
    await page.click('#btn-start'); s = await st(page); report('(T2) toolbar ⇤ -> start', s.logr === s.max);
    await page.click('#btn-next-ms'); s = await st(page); report('(T3) toolbar » -> next milestone', Math.abs(s.logr - isco) < 1e-12);
    await page.click('#btn-fwd'); s = await st(page); report('(T4) toolbar › -> step', Math.abs(s.logr - (isco - 0.25)) < 1e-12);
    await page.click('#btn-help'); s = await st(page); report('(T5) toolbar ? -> help', s.help);
    await page.click('#help-close'); s = await st(page); report('(T6) help close button', !s.help);
    // Space right after clicking a toolbar button toggles playback exactly once (no double activation)
    await page.click('#btn-back'); await page.keyboard.press('Space'); await page.waitForTimeout(200);
    s = await st(page); report('(T7) Space after a button click toggles playback once', s.playing === true);
    await page.keyboard.press('Space');
    // axis selector
    await page.selectOption('#axis', 'logtau'); s = await st(page); report('(T8) axis selector -> log10 τ remaining', s.axis === 'logtau');
    const opt = await page.evaluate(() => [...document.getElementById('speed').options].map(o => o.textContent));
    report('(T9) speed options labelled in decades per second on the log axes', opt.every(t => /dec\/s/.test(t)), opt.join(', '));
    await page.selectOption('#axis', 'logr');
    // hit targets
    const sizes = await page.evaluate(() => [...document.querySelectorAll('#toolbar button')].map(b => { const r = b.getBoundingClientRect(); return [b.id, Math.round(r.width), Math.round(r.height)]; }));
    report('(T10) toolbar buttons are at least 32 px (44 px on coarse pointers via CSS)', sizes.every(([, w, h]) => w >= 32 && h >= 32), sizes.map(x => x.join(':')).join(' '));
    await context.close();
  }
  // ------------------------------------------------------------------------------------------ touch
  {
    const { context, page } = await openPage(browser, { hasTouch: true, isMobile: false }, errors);
    await page.evaluate(() => { SLAB_APP.setView('scene'); SLAB_APP.jumpTo('photon_sphere'); });
    await page.waitForTimeout(300);
    const cdp = await context.newCDPSession(page);
    const box = await page.evaluate(() => { const r = SLAB_APP.views.scene.renderer.domElement.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2, ta: getComputedStyle(SLAB_APP.views.scene.renderer.domElement).touchAction }; });
    report('(G0) 3D canvas has touch-action: none (gestures go to OrbitControls, not page scroll/zoom)', box.ta === 'none', box.ta);
    const cam = () => page.evaluate(() => { const v = SLAB_APP.views.scene, p = v.camera.position, t = v.controls.target; return { az: Math.atan2(p.x - t.x, p.z - t.z), dist: p.distanceTo(t) }; });
    const touch = (type, pts) => cdp.send('Input.dispatchTouchEvent', { type, touchPoints: pts.map(([x, y], i) => ({ x, y, id: i + 1 })) });
    const c0 = await cam();
    await touch('touchStart', [[box.x, box.y]]);
    for (let i = 1; i <= 10; i++) { await touch('touchMove', [[box.x + 18 * i, box.y]]); await page.waitForTimeout(16); }
    await touch('touchEnd', []);
    await page.waitForTimeout(600);
    const c1 = await cam();
    report('(G1) one-finger drag orbits the 3D camera', Math.abs(c1.az - c0.az) > 0.2 && Math.abs(c1.dist / c0.dist - 1) < 0.05, `Δazimuth ${(c1.az - c0.az).toFixed(3)} rad, distance ratio ${(c1.dist / c0.dist).toFixed(3)}`);
    await touch('touchStart', [[box.x - 40, box.y], [box.x + 40, box.y]]);
    for (let i = 1; i <= 10; i++) { await touch('touchMove', [[box.x - 40 - 12 * i, box.y], [box.x + 40 + 12 * i, box.y]]); await page.waitForTimeout(16); }
    await touch('touchEnd', []);
    await page.waitForTimeout(600);
    const c2 = await cam();
    report('(G2) two-finger pinch-out zooms the 3D camera in', c2.dist < 0.85 * c1.dist, `distance ${c1.dist.toFixed(2)} -> ${c2.dist.toFixed(2)}`);
    // touch taps on the toolbar
    const l0 = await page.evaluate(() => SLAB_APP.state.logr);
    await page.tap('#btn-next-ms');
    const l1 = await page.evaluate(() => SLAB_APP.state.logr);
    report('(G3) touch tap on a toolbar button (» next milestone)', Math.abs(l1) < 1e-12 && l0 > 0, `logr ${l0.toFixed(4)} -> ${l1}`);
    if (shots) await page.screenshot({ path: path.join(SHOTS, 'touch-after-gestures.png') });
    await context.close();
  }
  // ------------------------------------------------------------------------------------------ PNG export
  {
    const { context, page } = await openPage(browser, {}, errors);
    const cases = [
      ['scene', () => { SLAB_APP.setView('scene'); SLAB_APP.setSceneMode('log'); SLAB_APP.jumpTo('horizon'); }, ['LOGARITHMIC VISUALIZATION — NOT TO SCALE']],
      ['scene-linear', () => { SLAB_APP.setView('scene'); SLAB_APP.setSceneMode('linear'); SLAB_APP.jumpTo('photon_sphere'); }, ['LINEAR LOCAL VIEW']],
      ['causal', () => { SLAB_APP.setSceneMode('log'); SLAB_APP.setView('causal'); SLAB_APP.setLogR(0.1); }, ['Exact Schwarzschild coordinate maps', 'Kruskal (T, X)']],
      ['fp', () => { SLAB_APP.setView('fp'); SLAB_APP.setLogR(0.7); }, ['Qualitative visualization — trajectory calculations remain relativistic.']],
      ['spec', () => { SLAB_APP.setView('spec'); }, ['SPECULATIVE QUANTUM-GRAVITY TOY MODELS — NOT ESTABLISHED PHYSICS', 'SPECULATIVE MODEL — NOT experimentally established.', 'SPECULATIVE QUANTUM MODEL']],
      ['end', () => { SLAB_APP.setView('scene'); SLAB_APP.jumpTo('r_QG'); }, ['PLANCK-CURVATURE THRESHOLD REACHED.', 'CLASSICAL GENERAL RELATIVITY IS NO LONGER RELIABLE.', 'PLANCK-CURVATURE BOUNDARY']],
    ];
    for (const [name, fn, required] of cases) {
      await page.evaluate(fn);
      await page.waitForTimeout(name === 'fp' ? 1200 : 400);
      const [dl] = await Promise.all([page.waitForEvent('download', { timeout: 20000 }), page.click('#btn-png')]);
      const file = await dl.path();
      const buf = fs.readFileSync(file);
      const sig = buf.subarray(0, 8).toString('hex') === '89504e470d0a1a0a';
      const W = buf.readUInt32BE(16), H = buf.readUInt32BE(20);
      if (shots) fs.copyFileSync(file, path.join(SHOTS, `export-${name}.png`));
      const a = await page.evaluate(() => {
        const c = SLAB_APP.capture(), ctx = c.getContext('2d'), sc = parseFloat(c.dataset.scale), ih = Math.round(parseFloat(c.dataset.imageHeight) * sc);
        const img = ctx.getImageData(0, 0, c.width, ih).data, cap = ctx.getImageData(0, ih, c.width, c.height - ih).data;
        const colors = new Set(); let nonBg = 0, n = 0;
        const bg = [img[0], img[1], img[2]];
        for (let i = 0; i < img.length; i += 4 * 7) { n++; colors.add((img[i] >> 4) * 256 + (img[i + 1] >> 4) * 16 + (img[i + 2] >> 4)); if (Math.abs(img[i] - bg[0]) + Math.abs(img[i + 1] - bg[1]) + Math.abs(img[i + 2] - bg[2]) > 30) nonBg++; }
        let text = 0; for (let i = 0; i < cap.length; i += 4) if (cap[i] + cap[i + 1] + cap[i + 2] > 300) text++;
        return { w: c.width, h: c.height, colors: colors.size, nonBg: nonBg / n, capText: text, lines: SLAB_APP.captionLines().map(l => l.text), name: `slab_${SLAB_APP.state.view}_log10r_${SLAB_APP.state.logr.toFixed(3)}.png` };
      });
      const joined = a.lines.join('\n');
      const missing = required.filter(r => !joined.includes(r));
      const basics = /r = /.test(joined) && /r\/r_s = /.test(joined) && /proper time τ = /.test(joined) && /classical τ remaining to r = 0/.test(joined) && /Regime: /.test(joined);
      report(`(P1) ${name}: PNG download (valid signature, ${W}×${H}, file ${dl.suggestedFilename()})`, sig && W === a.w && H === a.h && dl.suggestedFilename() === a.name);
      report(`(P2) ${name}: captured image region is not blank (render-then-capture)`, a.colors >= 12 && a.nonBg > 0.03, `${a.colors} colour bins, ${(100 * a.nonBg).toFixed(1)} % non-background`);
      report(`(P3) ${name}: caption strip has r, r/r_s, τ, τ remaining, regime and the required banners`, basics && missing.length === 0 && a.capText > 500, missing.length ? `missing ${missing.join(' | ')}` : `${a.lines.length} caption lines`);
    }
    await context.close();
  }
  // ------------------------------------------------------------------------------------------ HiDPI layout
  {
    const { context, page } = await openPage(browser, { deviceScaleFactor: 2 }, errors);
    await page.waitForTimeout(300);
    const r = await page.evaluate(() => {
      const v = SLAB_APP.views.scene, c = v.renderer.domElement.getBoundingClientRect(), b = v.container.getBoundingClientRect();
      return { cw: c.width, ch: c.height, bw: b.width, bh: b.height, buf: v.renderer.domElement.width };
    });
    report('(H1) HiDPI (dpr 2): 3D canvas laid out at the container size (not cropped)', Math.abs(r.cw - r.bw) < 1 && Math.abs(r.ch - r.bh) < 1 && r.buf > r.bw, `css ${r.cw}×${r.ch}, container ${r.bw}×${r.bh}, buffer width ${r.buf}`);
    await context.close();
  }
  report('(Z) no console errors in the control / export checks', errors.length === 0, errors.join(' | '));
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
  await runControlChecks(browser, report);
  await browser.close();
  console.log(fails ? `${fails} FAILED` : 'ALL PASSED');
  process.exit(fails ? 1 : 0);
}
