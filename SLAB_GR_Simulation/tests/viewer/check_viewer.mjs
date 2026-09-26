// Headless smoke test of the viewer: opens renders/viewer.html from file://, switches through every
// view / scene mode / camera, records console errors and takes screenshots into renders/screenshots/.
// It then runs the pixel-content checks (tests/viewer/test_pixels_browser.mjs: light-cone generators read back from
// the inset pixels, causal / signal-timeline markers at their predicted pixels, playback-axis monotonicity, mock
// engine export) and the control checks (tests/viewer/test_controls_browser.mjs: keyboard, touch gestures, toolbar,
// PNG export, HiDPI layout).  Any failed check or console error fails the run.
// Run:  node tests/viewer/check_viewer.mjs   (from SLAB_GR_Simulation; uses renders/build/node_modules/playwright-core)
import { createRequire } from 'node:module';
import path from 'node:path';
import fs from 'node:fs';
import { runPixelChecks, runContractChecks } from './test_pixels_browser.mjs';
import { runControlChecks } from './test_controls_browser.mjs';
const ROOT = path.resolve(new URL('.', import.meta.url).pathname, '../..');
const require = createRequire(path.join(ROOT, 'renders/build/package.json'));
const { chromium } = require('playwright-core');

const url = 'file://' + path.join(ROOT, 'renders/viewer.html');
const shots = path.join(ROOT, 'renders/screenshots');
fs.mkdirSync(shots, { recursive: true });
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || '/opt/pw-browsers/chromium', headless: true,
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--no-sandbox'] });
const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
const errors = [];
page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
page.on('pageerror', e => errors.push(String(e)));
await page.goto(url);
await page.waitForFunction(() => window.SLAB_APP && window.SLAB_APP.state.sample, null, { timeout: 30000 });
const steps = [
  ['scene-log-start', () => { SLAB_APP.setView('scene'); SLAB_APP.setSceneMode('log'); SLAB_APP.jumpTo('start'); }],
  ['scene-log-horizon', () => { SLAB_APP.jumpTo('horizon'); }],
  ['scene-horizon-mode', () => { SLAB_APP.setSceneMode('horizon'); SLAB_APP.setLogR(0.02); }],
  ['scene-linear', () => { SLAB_APP.setSceneMode('linear'); SLAB_APP.jumpTo('photon_sphere'); }],
  ['scene-deep', () => { SLAB_APP.setSceneMode('deep'); SLAB_APP.jumpTo('1m'); }],
  ['scene-curvature', () => { SLAB_APP.setSceneMode('curvature'); SLAB_APP.jumpTo('atomic'); }],
  ['scene-rQG', () => { SLAB_APP.setSceneMode('log'); SLAB_APP.jumpTo('r_QG'); }],
  ['causal-outside', () => { SLAB_APP.setView('causal'); SLAB_APP.jumpTo('photon_sphere'); }],
  ['causal-inside', () => { SLAB_APP.setLogR(-0.5); }],
  ['fp-outside', () => { SLAB_APP.setView('fp'); SLAB_APP.setLogR(0.7); }],
  ['fp-horizon', () => { SLAB_APP.setLogR(0.0); }],
  ['fp-inside', () => { SLAB_APP.setLogR(-0.7); }],
  ['fp-inside-outward', () => { SLAB_APP.views.fp.yaw = Math.PI; SLAB_APP.views.fp.dirty = true; }],
  ['fp-inside-outward-wide', () => { SLAB_APP.views.fp.fov = 140; SLAB_APP.views.fp.dirty = true; }],
  ['spec', () => { SLAB_APP.setView('spec'); }],
  // upgrade (viewer2): received-signal timeline, log-τ playback axis, help overlay
  ['causal-signal-only', () => { SLAB_APP.setView('causal'); SLAB_APP.views.causal.setMode('signal'); SLAB_APP.setLogR(0.05); }],
  ['causal-all-horizon', () => { SLAB_APP.views.causal.setMode('both'); SLAB_APP.jumpTo('horizon'); }],
  ['scene-axis-logtau-deep', () => { SLAB_APP.setView('scene'); SLAB_APP.setAxis('logtau'); SLAB_APP.setLogR(-30); }],
  ['scene-help-overlay', () => { SLAB_APP.setAxis('logr'); SLAB_APP.toggleHelp(true); }],
  ['scene-help-closed', () => { SLAB_APP.toggleHelp(false); SLAB_APP.jumpTo('photon_sphere'); }],
];
const results = [];
for (const [name, fn] of steps) {
  await page.evaluate(fn);
  await page.waitForTimeout(700);
  const st = await page.evaluate(() => ({ logr: SLAB_APP.state.logr, view: SLAB_APP.state.view, regime: SLAB_APP.state.sample.regime_code, r_m: SLAB_APP.state.sample.r_m }));
  await page.screenshot({ path: path.join(shots, `${name}.png`) });
  results.push({ name, ...st });
}
const checks = [];
const report = (name, ok, detail = '') => { checks.push({ name, ok, detail }); console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}  ${detail}`); };
await runPixelChecks(page, report);
await page.close();          // an idle page keeps rendering WebGL frames (software GL): close it before the next contexts
await runContractChecks(browser, report);
await runControlChecks(browser, report);
await browser.close();
const failed = checks.filter(c => !c.ok);
console.log(JSON.stringify({ results, errors, checks: { total: checks.length, failed: failed.map(c => c.name) } }, null, 2));
if (errors.length) { console.error(`${errors.length} console/page errors`); process.exit(1); }
if (failed.length) { console.error(`${failed.length} failed checks`); process.exit(1); }
console.log(`OK: ${results.length} screenshot steps, ${checks.length} pixel/control checks passed, zero console errors`);
