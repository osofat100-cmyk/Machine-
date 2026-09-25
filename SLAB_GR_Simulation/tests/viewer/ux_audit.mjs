// UX clutter audit for the SLAB viewer (measurement only; it never fails the build).
// For every tab and two screen sizes it records: overlapping visible panels, how many numbers are on
// screen at once, text smaller than 12 px, horizontal overflow, and the number of simultaneously visible
// text blocks. Output: renders/screenshots/ux/*.png and tests/viewer/ux_audit_report.json.
// Run: node tests/viewer/ux_audit.mjs   (uses the same headless Chromium as check_viewer.mjs)
import { createRequire } from 'node:module';
import path from 'node:path';
import fs from 'node:fs';
const ROOT = path.resolve(new URL('.', import.meta.url).pathname, '../..');
const require = createRequire(path.join(ROOT, 'renders/build/package.json'));
const { chromium } = require('playwright-core');
const exe = process.env.CHROMIUM_PATH || (fs.existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : chromium.executablePath());
const url = 'file://' + path.join(ROOT, 'renders/viewer.html');
const shots = path.join(ROOT, 'renders/screenshots/ux');
fs.mkdirSync(shots, { recursive: true });

const SIZES = [{ name: 'laptop', width: 1366, height: 768 }, { name: 'phone', width: 390, height: 844 }];
const STATES = [
  ['scene-start', () => { SLAB_APP.setView('scene'); SLAB_APP.jumpTo('start'); }],
  ['scene-horizon', () => { SLAB_APP.setView('scene'); SLAB_APP.jumpTo('horizon'); }],
  ['scene-rQG', () => { SLAB_APP.setView('scene'); SLAB_APP.jumpTo('r_QG'); }],
  ['causal', () => { SLAB_APP.setView('causal'); SLAB_APP.setLogR(-0.5); }],
  ['firstperson', () => { SLAB_APP.setView('fp'); SLAB_APP.setLogR(0.7); }],
  ['speculative', () => { SLAB_APP.setView('spec'); }],
];

// runs in the page: measure clutter
function measure() {
  const vis = el => { const s = getComputedStyle(el); if (s.display === 'none' || s.visibility === 'hidden' || +s.opacity === 0) return false; const r = el.getBoundingClientRect(); return r.width > 2 && r.height > 2 && r.bottom > 0 && r.right > 0 && r.top < innerHeight && r.left < innerWidth; };
  const all = [...document.querySelectorAll('body *')].filter(vis);
  // floating panels: absolutely/fixed positioned boxes with text or canvases drawn over the main view
  const panels = all.filter(el => { const p = getComputedStyle(el).position; return (p === 'absolute' || p === 'fixed') && (el.innerText || '').trim().length > 0; })
    .filter(el => !all.some(o => o !== el && o.contains(el) && ['absolute', 'fixed'].includes(getComputedStyle(o).position) && (o.innerText || '').trim().length > 0));
  const boxes = panels.map(el => ({ el, r: el.getBoundingClientRect(), label: (el.id ? '#' + el.id : el.className || el.tagName).toString().slice(0, 40) + ': ' + (el.innerText || '').trim().slice(0, 50).replace(/\s+/g, ' ') }));
  const overlaps = [];
  for (let i = 0; i < boxes.length; i++) for (let j = i + 1; j < boxes.length; j++) {
    const a = boxes[i].r, b = boxes[j].r;
    const w = Math.min(a.right, b.right) - Math.max(a.left, b.left), h = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
    if (w > 4 && h > 4) overlaps.push({ a: boxes[i].label, b: boxes[j].label, area_px: Math.round(w * h) });
  }
  // text leaves
  const leaves = all.filter(el => [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim().length > 0));
  const text = leaves.map(el => [...el.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join(' ')).join(' \n ');
  const numbers = (text.match(/[-+−]?\d+(?:[.,]\d+)?(?:e[-+−]?\d+)?/gi) || []).length;
  const tiny = leaves.filter(el => parseFloat(getComputedStyle(el).fontSize) < 12).length;
  const words = (text.match(/[A-Za-z]{2,}/g) || []).length;
  const overflowX = document.documentElement.scrollWidth > innerWidth + 1;
  return { panels: boxes.length, overlaps, numbers_visible: numbers, words_visible: words, text_blocks: leaves.length, tiny_text_blocks: tiny, horizontal_overflow: overflowX,
           panel_labels: boxes.map(b => b.label) };
}

const browser = await chromium.launch({ executablePath: exe, headless: true, args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'] });
const report = { generated: new Date().toISOString(), note: 'measurement only; see docs/DECLUTTER_PROMPT.md for targets', results: [] };
for (const size of SIZES) {
  const page = await browser.newPage({ viewport: { width: size.width, height: size.height } });
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  await page.goto(url);
  await page.waitForFunction(() => window.SLAB_APP && window.SLAB_APP.state.sample, null, { timeout: 60000 });
  for (const [name, fn] of STATES) {
    await page.evaluate(fn);
    await page.waitForTimeout(900);
    const m = await page.evaluate(measure);
    await page.screenshot({ path: path.join(shots, `${size.name}-${name}.png`) });
    report.results.push({ size: size.name, state: name, ...m });
  }
  report.results.push({ size: size.name, state: 'page-errors', errors });
  await page.close();
}
await browser.close();
fs.writeFileSync(path.join(ROOT, 'tests/viewer/ux_audit_report.json'), JSON.stringify(report, null, 2));
for (const r of report.results) if (r.state !== 'page-errors')
  console.log(`${r.size.padEnd(6)} ${r.state.padEnd(14)} panels=${String(r.panels).padStart(2)} overlaps=${String(r.overlaps.length).padStart(2)} numbers=${String(r.numbers_visible).padStart(4)} words=${String(r.words_visible).padStart(4)} tiny=${String(r.tiny_text_blocks).padStart(3)} overflowX=${r.horizontal_overflow}`);
