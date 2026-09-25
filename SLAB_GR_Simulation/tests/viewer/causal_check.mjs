// Headless check of the causal (Kruskal / Penrose) view: several positions along the trajectory, both layouts
// (wide side-by-side and narrow stacked), single-panel modes, and robustness to null sample fields.
// Run:  node tests/viewer/causal_check.mjs   (from SLAB_GR_Simulation; writes renders/screenshots/causal-*.png)
import { createRequire } from 'node:module';
import path from 'node:path';
import fs from 'node:fs';
const ROOT = path.resolve(new URL('.', import.meta.url).pathname, '../..');
const require = createRequire(path.join(ROOT, 'renders/build/package.json'));
const { chromium } = require('playwright-core');

const url = 'file://' + path.join(ROOT, 'renders/viewer.html');
const shots = path.join(ROOT, 'renders/screenshots');
fs.mkdirSync(shots, { recursive: true });
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || '/opt/pw-browsers/chromium', headless: true,
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--no-sandbox'] });
const errors = [];
const results = [];
async function run(viewport, steps) {
  const page = await browser.newPage({ viewport });
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push(String(e)));
  await page.goto(url);
  await page.waitForFunction(() => window.SLAB_APP && window.SLAB_APP.state.sample, null, { timeout: 30000 });
  for (const [name, fn] of steps) {
    await page.evaluate(fn);
    await page.waitForTimeout(400);
    const st = await page.evaluate(() => ({ logr: SLAB_APP.state.logr, regime: SLAB_APP.state.sample.regime_code,
      X: SLAB_APP.state.sample.kruskal_X, T: SLAB_APP.state.sample.kruskal_T, caption: SLAB_APP.views.causal.caption.textContent.slice(0, 160) }));
    await page.screenshot({ path: path.join(shots, `${name}.png`) });
    results.push({ name, ...st });
  }
  await page.close();
}
await run({ width: 1400, height: 900 }, [
  ['causal-start', () => { SLAB_APP.setView('causal'); SLAB_APP.jumpTo('start'); }],
  ['causal-isco', () => { SLAB_APP.jumpTo('isco'); }],
  ['causal-horizon', () => { SLAB_APP.jumpTo('horizon'); }],
  ['causal-extreme', () => { SLAB_APP.jumpTo('extreme_curvature'); }],
  ['causal-rQG', () => { SLAB_APP.jumpTo('r_QG'); }],
  ['causal-mode-kruskal', () => { SLAB_APP.views.causal.setMode('kruskal'); SLAB_APP.setLogR(-0.3); }],
  ['causal-mode-penrose', () => { SLAB_APP.views.causal.setMode('penrose'); }],
  ['causal-null-sample', () => { SLAB_APP.views.causal.setMode('both'); SLAB_APP.views.causal.update({ kruskal_X: null, kruskal_T: 'inf', penrose_X: null, penrose_T: undefined, regime_code: null }, SLAB_APP.state); }],
  ['causal-no-sample', () => { SLAB_APP.views.causal.update(null, null); SLAB_APP.views.causal.resize(); }],
]);
await run({ width: 900, height: 1100 }, [
  ['causal-narrow', () => { SLAB_APP.setView('causal'); SLAB_APP.setLogR(-0.2); }],
]);
await browser.close();
console.log(JSON.stringify({ results, errors }, null, 2));
if (errors.length) { console.error(`${errors.length} console/page errors`); process.exit(1); }
