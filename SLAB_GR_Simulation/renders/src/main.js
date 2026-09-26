// SLAB GR Simulation viewer — app entry.  Physics is precomputed by the Python engine; this file only handles
// state, playback, keyboard/touch controls, PNG export and the wiring of the view modules.
import { TrajectoryData, fmt, AXES } from './data.js';
import { Dashboard, REGIMES, REGIME_COLORS } from './dashboard.js';
import { Scene3dView } from './scene3d.js';
import { CausalView } from './causal.js';
import { FirstpersonView } from './firstperson.js';
import { SpeculativeView } from './speculative.js';

const raw = window.SLAB_DATA;
const data = new TrajectoryData(raw);
const $ = id => document.getElementById(id);
const isNum = v => typeof v === 'number' && Number.isFinite(v);

const SPEEDS = [0.1, 0.25, 0.5, 1, 2, 4, 8, 16];     // decades per second on the log axes (x 2 % of τ per second on the linear-τ axis)
const VIEW_NAMES = ['scene', 'causal', 'fp', 'spec'];
const VIEW_TITLES = { scene: '3D view', causal: 'Causal / Kruskal diagram', fp: 'First-person camera',
  spec: 'SPECULATIVE QUANTUM-GRAVITY TOY MODELS — NOT ESTABLISHED PHYSICS' };

const state = {
  logr: data.logrMax,      // current position: log10(r / r_s)  (the playback axes are all re-parametrizations of it)
  playing: false,
  speedIndex: 4,
  speedDecPerS: SPEEDS[4],
  axis: 'logr',            // logr | logtau | tau   (see data.js AXES)
  view: 'scene',
  sceneMode: 'log',        // log | linear | horizon | deep | curvature
  camera: 'third',         // third | first
  speculative: false,
  help: false,
  sample: null,
};

const dashboard = new Dashboard($('dashboard'), data);
const views = {
  scene: new Scene3dView($('view-scene'), data, { controls: $('controls') }),
  causal: new CausalView($('view-causal'), data, {}),
  fp: new FirstpersonView($('view-fp'), data, {}),
  spec: new SpeculativeView($('view-spec'), data, {}),
};

// ------------------------------------------------------------------------------------------------ views
function setView(name) {
  if (!views[name]) return;
  state.view = name;
  state.speculative = (name === 'spec');
  document.querySelectorAll('header .tabs button').forEach(b => b.classList.toggle('active', b.dataset.view === name));
  document.querySelectorAll('.view').forEach(v => v.classList.toggle('active', v.id === `view-${name}`));
  $('banner').classList.toggle('hidden', !(name === 'scene' && state.sceneMode !== 'linear' && state.sceneMode !== 'horizon'));
  $('spec-banner').classList.toggle('hidden', name !== 'spec');
  views[name].resize();
  render(true);
}
function setSceneMode(mode) { state.sceneMode = mode; views.scene.setMode(mode); $('banner').classList.toggle('hidden', !(state.view === 'scene' && mode !== 'linear' && mode !== 'horizon')); render(true); }

// ------------------------------------------------------------------------------------------------ position and playback
function setLogR(x) { state.logr = data.clampLogR(x); render(true); }
function pause() { if (state.playing) { state.playing = false; updatePlayButton(); } }
function updatePlayButton() { $('play').textContent = state.playing ? '❚❚ Pause' : '▶ Play'; }
function togglePlay(force) {
  state.playing = typeof force === 'boolean' ? force : !state.playing;
  if (state.playing && state.logr <= data.logrMin) state.logr = data.logrMax;   // replay from the start
  updatePlayButton();
}
function axisRate(axis) { return AXES[axis].rate(state.speedDecPerS); }
function setAxis(axis) {
  if (!data.axisAvailable(axis)) return false;
  state.axis = axis;                     // the position (state.logr) is unchanged: only the playback parametrization changes
  $('axis').value = axis;
  fillSpeedOptions();
  render(true);
  return true;
}
// deterministic playback step (also used by the tests): advance the progress coordinate of the active axis by rate * dt
function advance(dt, opts = {}) {
  const ax = state.axis, [, s1] = data.axisRange(ax);
  const s = data.axisAt(ax, state.logr) + axisRate(ax) * dt;
  if (s >= s1) { state.logr = data.logrMin; if (state.playing) { state.playing = false; updatePlayButton(); } }
  else state.logr = data.logrAtAxis(ax, s);
  if (!opts.noRender) render(false);
}
function step(dir, fine) {
  pause();
  const ax = state.axis, A = AXES[ax];
  setLogR(data.logrAtAxis(ax, data.axisAt(ax, state.logr) + dir * (fine ? A.fine : A.step)));
}
function goStart() { pause(); setLogR(data.logrMax); }
function goEnd() { pause(); setLogR(data.logrMin); }
function milestone(dir) {
  pause();
  const m = data.nextMilestone(state.logr, dir);
  if (m) setLogR(m.log10_r_over_rs);
  return m ? m.slug : null;
}
function setSpeedIndex(i) {
  state.speedIndex = Math.max(0, Math.min(SPEEDS.length - 1, i));
  state.speedDecPerS = SPEEDS[state.speedIndex];
  $('speed').value = String(state.speedIndex);
}
function speed(dir) { setSpeedIndex(state.speedIndex + dir); }
function fillSpeedOptions() {
  const A = AXES[state.axis];
  $('speed').innerHTML = SPEEDS.map((v, i) => {
    const r = A.rate(v);
    const lbl = A.unit === 'dec/s' ? `${v} dec/s` : `${+(100 * r).toPrecision(3)} % τ/s`;
    return `<option value="${i}"${i === state.speedIndex ? ' selected' : ''}>${lbl}</option>`;
  }).join('');
}
function sliderFraction() {
  const [a, b] = data.axisRange(state.axis);
  return b > a ? (data.axisAt(state.axis, state.logr) - a) / (b - a) : 0;
}

// ------------------------------------------------------------------------------------------------ rendering
function readout(smp) {
  const rem = isNum(smp.tau_to_center_est_years) ? fmt.years(smp.tau_to_center_est_years) : '—';
  return {
    line1: `r = ${fmt.sci(smp.r_m, 4)} m   r/r_s = ${fmt.sci(smp.r_over_rs, 4)}`,
    line2: `τ = ${fmt.years(smp.tau_years)}   τ remaining ≈ ${rem}`,
    rem,
  };
}
function render(force) {
  const smp = data.at(state.logr);
  state.sample = smp;
  dashboard.update(smp, state);
  $('slider').value = String(sliderFraction());
  const ro = readout(smp);
  const pos = $('pos');
  pos.innerHTML = `${ro.line1}\n${ro.line2.replace(/τ remaining ≈ .*$/, m => `<span class="rem" title="classical proper time remaining to r = 0: a classical-GR extrapolation (the validated run stops at r_QG)">${m} (GR extrap.)</span>`)}`;
  $('slider').setAttribute('aria-valuetext', `${ro.line1}; ${ro.line2}`);
  const atEnd = state.logr <= data.logrMin + 1e-9;
  $('planck').classList.toggle('hidden', !(atEnd && !state.speculative));
  $('planck').textContent = raw.planck_message;
  views[state.view].update(smp, state);
}

let last = performance.now();
function loop(now) {
  const dt = Math.min(0.25, (now - last) / 1000); last = now;
  if (state.playing) advance(dt);
  else if (state.view === 'scene' || state.view === 'fp') views[state.view].update(state.sample || data.at(state.logr), state);  // camera orbit / redraw
  requestAnimationFrame(loop);
}

// ------------------------------------------------------------------------------------------------ help overlay
function toggleHelp(force) {
  state.help = typeof force === 'boolean' ? force : !state.help;
  $('help').classList.toggle('hidden', !state.help);
  if (state.help) $('help-close').focus({ preventScroll: true });
}

// ------------------------------------------------------------------------------------------------ PNG export
function bannersFor(viewName) {
  const out = [];
  if (viewName === 'scene') {
    const lbl = views.scene.modeLabel ? views.scene.modeLabel() : raw.banner_log;
    out.push({ text: lbl, color: '#ffb454' });
    if (!/NOT TO SCALE/.test(lbl) && state.sceneMode !== 'linear' && state.sceneMode !== 'horizon') out.push({ text: raw.banner_log, color: '#ffb454' });
  } else if (viewName === 'fp') out.push({ text: raw.banner_firstperson, color: '#ffb454' });
  else if (viewName === 'spec') {
    const sp = raw.speculative || {};
    out.push({ text: sp.menu_title || VIEW_TITLES.spec, color: '#d98cff' });
    out.push({ text: sp.banner || 'SPECULATIVE MODEL — NOT experimentally established.', color: '#d98cff' });
  } else if (viewName === 'causal') out.push({ text: 'Exact Schwarzschild coordinate maps (G = c = M = 1); angular directions suppressed; worldline precomputed by the engine, stops at r_QG.', color: '#8892a6' });
  return out;
}
// caption-strip lines: [{text, color, bold}]
function captionLines() {
  const smp = state.sample || data.at(state.logr);
  const reg = state.speculative ? 3 : Math.max(0, Math.min(2, smp.regime_code ?? 0));
  const who = state.view === 'spec' ? 'validated-run observer: ' : '';
  const lines = [
    { text: `SLAB GR Simulation — M = 10^18 M☉ Schwarzschild infall — ${VIEW_TITLES[state.view]}`, color: '#d8dee9', bold: true },
    { text: `${who}r = ${fmt.metres(smp.r_m)}   r/r_s = ${fmt.sci(smp.r_over_rs, 6)}   log10(r/r_s) = ${isNum(smp.log10_r_over_rs) ? smp.log10_r_over_rs.toFixed(4) : '—'}`, color: '#d8dee9' },
    { text: `proper time τ = ${fmt.years(smp.tau_years, 6)}   τ since horizon = ${smp.log10_r_over_rs <= 0 ? fmt.years(smp.tau_since_horizon_years) : 'not yet crossed'}   ` +
      `classical τ remaining to r = 0 ≈ ${fmt.years(smp.tau_to_center_est_years)} (classical-GR extrapolation)`, color: '#d8dee9' },
    { text: `Regime: ${REGIMES[reg]}`, color: REGIME_COLORS[reg], bold: true },
    ...bannersFor(state.view).map(b => ({ ...b, bold: true })),
  ];
  const extra = views[state.view].captionExtra ? views[state.view].captionExtra() : [];
  for (const t of extra) lines.push({ text: t, color: '#8892a6' });
  if (state.logr <= data.logrMin + 1e-9 && !state.speculative) for (const t of String(raw.planck_message).split('\n')) lines.push({ text: t, color: '#ff6b6b', bold: true });
  return lines;
}
function wrapText(ctx, text, maxW) {
  const words = String(text).split(' '), out = []; let cur = '';
  for (const w of words) { const t = cur ? cur + ' ' + w : w; if (ctx.measureText(t).width > maxW && cur) { out.push(cur); cur = w; } else cur = t; }
  if (cur) out.push(cur);
  return out;
}
// Composite the current view into one canvas with a caption strip below it.  WebGL views are rendered and copied in
// the same task (render-then-capture), so no preserveDrawingBuffer is needed.
function capture() {
  const name = state.view, view = views[name], container = $(`view-${name}`);
  let spec;
  if (typeof view.captureLayers === 'function') spec = view.captureLayers();
  else {
    // generic path (first-person camera): force a fresh frame, then copy its canvas immediately
    try { if (typeof view.renderNow === 'function') view.renderNow(); else { view.dirty = true; view.update(state.sample || data.at(state.logr), state); } } catch (e) { /* capture what is there */ }
    const c = (typeof view.getCanvas === 'function' && view.getCanvas()) || container.querySelector('canvas');
    const box = container.getBoundingClientRect();
    const layers = [];
    if (c) { const b = c.getBoundingClientRect(); layers.push(b.width > 0 ? { canvas: c, x: b.left - box.left, y: b.top - box.top, w: b.width, h: b.height } : { canvas: c, x: 0, y: 0, w: box.width, h: box.height }); }
    spec = { width: box.width, height: box.height, background: '#000', layers };
  }
  const W = Math.max(320, Math.round(spec.width || 800)), H = Math.max(40, Math.round(spec.height || 600));
  const scale = Math.min(2, Math.max(1, window.devicePixelRatio || 1));
  const meas = document.createElement('canvas').getContext('2d');
  const LINE = 17, PAD = 8;
  const wrapped = [];
  for (const ln of captionLines()) {
    meas.font = `${ln.bold ? 600 : 400} 12.5px system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`;
    for (const t of wrapText(meas, ln.text, W - 2 * PAD)) wrapped.push({ ...ln, text: t });
  }
  const capH = wrapped.length * LINE + 2 * PAD;
  const out = document.createElement('canvas');
  out.width = Math.round(W * scale); out.height = Math.round((H + capH) * scale);
  const ctx = out.getContext('2d');
  ctx.setTransform(scale, 0, 0, scale, 0, 0);
  ctx.fillStyle = spec.background || '#0b0e14'; ctx.fillRect(0, 0, W, H);
  for (const L of spec.layers || []) { try { ctx.drawImage(L.canvas, L.x, L.y, L.w, L.h); } catch (e) { /* a layer that cannot be read is skipped */ } }
  for (const t of spec.texts || []) { ctx.font = '600 12px system-ui, sans-serif'; ctx.fillStyle = t.color || '#d8dee9'; ctx.fillText(wrapText(ctx, t.text, t.maxW || W)[0] || '', t.x, t.y); }
  // caption strip
  ctx.fillStyle = '#131824'; ctx.fillRect(0, H, W, capH);
  ctx.fillStyle = '#2b3549'; ctx.fillRect(0, H, W, 1);
  ctx.textBaseline = 'alphabetic';
  wrapped.forEach((ln, i) => {
    ctx.font = `${ln.bold ? 600 : 400} 12.5px system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`;
    ctx.fillStyle = ln.color || '#d8dee9';
    ctx.fillText(ln.text, PAD, H + PAD + 13 + i * LINE);
  });
  out.dataset.imageHeight = String(H); out.dataset.captionHeight = String(capH); out.dataset.scale = String(scale);
  return out;
}
function pngName() { return `slab_${state.view}_log10r_${state.logr.toFixed(3)}.png`; }
function savePNG() {
  const c = capture(), name = pngName();
  return new Promise((resolve, reject) => {
    c.toBlob(blob => {
      if (!blob) { reject(new Error('PNG encoding failed')); return; }
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = name; a.style.display = 'none';
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 10000);
      resolve(name);
    }, 'image/png');
  });
}

// ------------------------------------------------------------------------------------------------ UI wiring
document.querySelectorAll('header .tabs button').forEach(b => b.addEventListener('click', () => setView(b.dataset.view)));
$('play').addEventListener('click', () => togglePlay());
$('btn-start').addEventListener('click', goStart);
$('btn-end').addEventListener('click', goEnd);
$('btn-back').addEventListener('click', e => step(-1, e.shiftKey));
$('btn-fwd').addEventListener('click', e => step(+1, e.shiftKey));
$('btn-prev-ms').addEventListener('click', () => milestone(-1));
$('btn-next-ms').addEventListener('click', () => milestone(+1));
$('btn-png').addEventListener('click', () => { savePNG().catch(e => console.warn('PNG export failed:', e)); });
$('btn-help').addEventListener('click', () => toggleHelp());
$('help-close').addEventListener('click', () => toggleHelp(false));
$('speed').addEventListener('change', e => setSpeedIndex(parseInt(e.target.value, 10)));
$('axis').addEventListener('change', e => { if (!setAxis(e.target.value)) e.target.value = state.axis; });
$('slider').addEventListener('input', e => {
  const f = parseFloat(e.target.value), [a, b] = data.axisRange(state.axis);
  pause(); setLogR(data.logrAtAxis(state.axis, a + f * (b - a)));
});
window.addEventListener('resize', () => { Object.values(views).forEach(v => v.resize()); render(true); });

function onKey(e) {
  if (e.ctrlKey || e.metaKey || e.altKey) return;                        // leave browser shortcuts alone
  const t = e.target, tag = t && t.tagName ? t.tagName : '';
  if (tag === 'SELECT' || tag === 'TEXTAREA' || (t && t.isContentEditable)) return;
  if (tag === 'INPUT' && !['range', 'checkbox', 'radio', 'button'].includes(t.type)) return;
  const other = tag === 'INPUT' && t.type === 'range' && t.id !== 'slider';   // e.g. the FOV slider keeps its own arrow keys
  let handled = true;
  switch (e.key) {
    case ' ': case 'Spacebar': togglePlay(); break;
    case 'ArrowRight': if (other) return; step(+1, e.shiftKey); break;
    case 'ArrowLeft': if (other) return; step(-1, e.shiftKey); break;
    case 'Home': if (other) return; goStart(); break;
    case 'End': if (other) return; goEnd(); break;
    case ']': milestone(+1); break;
    case '[': milestone(-1); break;
    case '+': case '=': speed(+1); break;
    case '-': case '_': speed(-1); break;
    case '1': case '2': case '3': case '4': setView(VIEW_NAMES[parseInt(e.key, 10) - 1]); break;
    case '?': toggleHelp(); break;
    case 'Escape': if (state.help) toggleHelp(false); else handled = false; break;
    default: handled = false;
  }
  if (handled) { e.preventDefault(); if (tag === 'BUTTON' || tag === 'INPUT') t.blur(); }
}
window.addEventListener('keydown', onKey);

// axis options that the export cannot support are disabled (e.g. no tau_to_center_est_years column)
for (const opt of $('axis').options) { if (!data.axisAvailable(opt.value)) { opt.disabled = true; opt.textContent += ' — unavailable in this export'; } }
fillSpeedOptions();

// validation summary
{
  const s = raw.summary;
  $('validation').innerHTML = `steps ${s.n_steps_total}, RHS evals ${s.n_rhs_evals_total}, rejected ${s.n_rejected_total}<br>` +
    `max |g(u,u)+1| = ${fmt.sci(s.max_abs_norm_residual, 2)}; max conditioned E drift = ${fmt.sci(s.max_E_drift_conditioned, 2)}<br>` +
    `τ(horizon→r_QG) = ${fmt.years(s.tau_since_horizon_years_at_end)} (analytic 4GM/3c³ = ${fmt.years(data.derived.tau_horizon_to_singularity_years)})<br>` +
    `See validation_report.json for TESTS 0–8.`;
}

// public API for tests / console
window.SLAB_APP = { state, data, views, setView, setLogR, setSceneMode, render, setAxis, advance, step, milestone, speed, setSpeedIndex,
  togglePlay, toggleHelp, goStart, goEnd, capture, savePNG, captionLines, readout: () => readout(state.sample || data.at(state.logr)),
  sliderFraction, speeds: SPEEDS,
  setCamera(c) { state.camera = c; render(true); },
  jumpTo(slug) { const m = data.milestone(slug); if (m) setLogR(m.log10_r_over_rs); } };

setView('scene');
render(true);
requestAnimationFrame(loop);
