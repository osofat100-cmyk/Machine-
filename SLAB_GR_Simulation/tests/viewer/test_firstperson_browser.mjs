// Headless-browser checks of the first-person camera (CPU default path; the headless Chromium has software GL only).
// Run (after renders/build/build.sh): node tests/viewer/test_firstperson_browser.mjs
// Screenshots: renders/screenshots/fpcam-*.png (generated, not committed).
import { createRequire } from 'node:module';
import path from 'node:path';
import fs from 'node:fs';
const ROOT = path.resolve(new URL('.', import.meta.url).pathname, '../..');
const require = createRequire(path.join(ROOT, 'renders/build/package.json'));
const { chromium } = require('playwright-core');

let fails = 0;
const report = (name, ok, detail) => { console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}  ${detail}`); if (!ok) fails++; };
const shots = path.join(ROOT, 'renders/screenshots');
fs.mkdirSync(shots, { recursive: true });
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || '/opt/pw-browsers/chromium', headless: true,
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--no-sandbox'] });
const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
const errors = [];
page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
page.on('pageerror', e => errors.push(String(e)));
await page.goto('file://' + path.join(ROOT, 'renders/viewer.html'));
await page.waitForFunction(() => window.SLAB_APP && window.SLAB_APP.state.sample, null, { timeout: 30000 });

// wait until the CPU renderer reports a finished image
const settle = async (ms = 20000) => page.waitForFunction(() => { const v = SLAB_APP.views.fp; return v.phase === 'idle' && v.table && v.table.done; }, null, { timeout: ms });

// 1. default path is the CPU renderer and creates no WebGL context in the first-person view
await page.evaluate(() => { SLAB_APP.setView('fp'); SLAB_APP.setLogR(0.7); });
await settle();
let st = await page.evaluate(() => { const v = SLAB_APP.views.fp; return { engine: v.engine, gpu: !!v.gpu, canvases: v.container.querySelectorAll('canvas').length, ctx: v.canvas.getContext('2d') !== null }; });
report('(b1) default renderer is CPU, no GPU tracer created', st.engine === 'cpu' && !st.gpu && st.ctx, JSON.stringify(st));
await page.screenshot({ path: path.join(shots, 'fpcam-5rs-stars.png') });

// 2. getCanvas() returns a canvas with the image (non-trivial pixel content) and the baked labels
const gc = await page.evaluate(() => { const c = SLAB_APP.views.fp.getCanvas(); const x = c.getContext('2d'); const d = x.getImageData(0, 0, c.width, c.height).data; let lit = 0; for (let i = 0; i < d.length; i += 4) if (d[i] + d[i + 1] + d[i + 2] > 60) lit++; return { w: c.width, h: c.height, lit, isCanvas: c instanceof HTMLCanvasElement }; });
report('(b2) getCanvas() returns an HTMLCanvasElement with image content', gc.isCanvas && gc.w > 100 && gc.h > 100 && gc.lit > 500, JSON.stringify(gc));

// 3. near r_QG: CPU path still renders (no float32 limit), fractions and labels present, false-colour scale shown
await page.evaluate(() => { SLAB_APP.jumpTo('r_QG'); const v = SLAB_APP.views.fp; v.yaw = Math.PI / 2; v.fov = 150; v.layer = 'gmap'; v.dirty = true; });
await settle();
st = await page.evaluate(() => { const v = SLAB_APP.views.fp; return { r: v.obs.r, banner: v.banner.textContent, stats: v.stats.textContent, scale: v.scale.style.display, counts: v.cpu.levelCounts }; });
report('(b3) r_QG: image rendered in double precision, half sky / half past-horizon, labels + colour scale', st.r < 1e-36 && st.banner.includes('Qualitative visualization — trajectory calculations remain relativistic.') &&
  st.stats.includes('INSIDE the horizon') && st.stats.includes('exterior sky') && st.scale !== 'none' && st.counts[0] > 0 && st.counts[1] > 0 && st.counts[2] === 0,
  `r = ${st.r.toExponential(3)} M, pixel counts ${st.counts}, scale display '${st.scale}'`);
await page.screenshot({ path: path.join(shots, 'fpcam-rQG-gmap.png') });

// 4. inside, looking outward, false colour, star catalogue
await page.evaluate(() => { SLAB_APP.setLogR(-1.0); const v = SLAB_APP.views.fp; v.yaw = Math.PI; v.fov = 120; v.layer = 'gmap'; v.dirty = true; });
await settle();
await page.screenshot({ path: path.join(shots, 'fpcam-inside-outward-gmap.png') });
await page.evaluate(() => { const v = SLAB_APP.views.fp; v.layer = 'tint'; v.background = 'grid'; v.yaw = Math.PI / 2; v.dirty = true; });
await settle();
await page.screenshot({ path: path.join(shots, 'fpcam-inside-side-grid.png') });

// 5. playback stays responsive: frame time while playing through the interior
await page.evaluate(() => { const v = SLAB_APP.views.fp; v.background = 'stars'; v.dirty = true; SLAB_APP.setLogR(0.5); });
const perf = await page.evaluate(async () => {
  const t = []; let last = performance.now();
  document.getElementById('play').click();
  await new Promise(res => { let n = 0; const f = () => { const now = performance.now(); t.push(now - last); last = now; if (++n < 60) requestAnimationFrame(f); else res(); }; requestAnimationFrame(f); });
  document.getElementById('play').click();
  t.sort((a, b) => a - b); return { median: t[t.length >> 1], p90: t[Math.floor(t.length * 0.9)] };
});
report('(b4) playback with the CPU renderer stays interactive (median frame < 120 ms in software)', perf.median < 120, JSON.stringify(perf));

// 6. optional GPU mode (software WebGL here): selectable, renders, falls back to CPU below 1e-5 r_s
await page.evaluate(() => { SLAB_APP.setLogR(0.7); const v = SLAB_APP.views.fp; v.yaw = 0; v.fov = 90; v.layer = 'tint'; v.setEngine('gpu'); });
await page.waitForTimeout(1500);
st = await page.evaluate(() => { const v = SLAB_APP.views.fp; return { engine: v.engine, gpu: !!v.gpu, note: v.gpuNote, active: v._gpuActive() }; });
await page.screenshot({ path: path.join(shots, 'fpcam-gpu-5rs.png') });
const gpuOk = st.engine === 'gpu' ? st.gpu && st.active : st.note.length > 0;
report('(b5) GPU (float32) option works when WebGL exists, otherwise disabled with a note', gpuOk, JSON.stringify(st));
await page.evaluate(() => { SLAB_APP.jumpTo('r_QG'); });
await page.waitForTimeout(800);
st = await page.evaluate(() => { const v = SLAB_APP.views.fp; return { active: v._gpuActive(), banner: v.banner.textContent }; });
report('(b6) GPU mode below 1e-5 r_s falls back to the CPU renderer with a label', !st.active && (st.banner.includes('LABELLED LIMIT') || !gpuOk), `gpu active ${st.active}`);
await page.evaluate(() => SLAB_APP.views.fp.setEngine('cpu'));

await browser.close();
report('(b7) zero console / page errors', errors.length === 0, errors.slice(0, 5).join(' | '));
console.log(fails ? `${fails} FAILED` : 'ALL PASSED');
process.exit(fails ? 1 : 0);
