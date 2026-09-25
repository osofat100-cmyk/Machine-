// SLAB GR Simulation viewer — app entry.  Physics is precomputed by the Python engine; this
// file only handles state, playback and wiring of the view modules.
import { TrajectoryData, fmt } from './data.js';
import { Dashboard } from './dashboard.js';
import { Scene3dView } from './scene3d.js';
import { CausalView } from './causal.js';
import { FirstpersonView } from './firstperson.js';
import { SpeculativeView } from './speculative.js';

const raw = window.SLAB_DATA;
const data = new TrajectoryData(raw);
const $ = id => document.getElementById(id);

const state = {
  logr: data.logrMax,      // current position: log10(r / r_s)
  playing: false,
  speedDecPerS: 2,
  axis: 'logr',
  view: 'scene',
  sceneMode: 'log',        // log | linear | horizon | deep | curvature
  camera: 'third',         // third | first
  speculative: false,
  sample: null,
};

const dashboard = new Dashboard($('dashboard'), data);
const views = {
  scene: new Scene3dView($('view-scene'), data, { controls: $('controls') }),
  causal: new CausalView($('view-causal'), data, {}),
  fp: new FirstpersonView($('view-fp'), data, {}),
  spec: new SpeculativeView($('view-spec'), data, {}),
};

function setView(name) {
  state.view = name;
  state.speculative = (name === 'spec');
  document.querySelectorAll('header .tabs button').forEach(b => b.classList.toggle('active', b.dataset.view === name));
  document.querySelectorAll('.view').forEach(v => v.classList.toggle('active', v.id === `view-${name}`));
  $('banner').classList.toggle('hidden', !(name === 'scene' && state.sceneMode !== 'linear' && state.sceneMode !== 'horizon'));
  $('spec-banner').classList.toggle('hidden', name !== 'spec');
  views[name].resize();
  render(true);
}
function setLogR(x) { state.logr = data.clampLogR(x); render(true); }
function setSceneMode(mode) { state.sceneMode = mode; views.scene.setMode(mode); $('banner').classList.toggle('hidden', !(state.view === 'scene' && mode !== 'linear' && mode !== 'horizon')); render(true); }

function render(force) {
  const smp = data.at(state.logr);
  state.sample = smp;
  dashboard.update(smp, state);
  const frac = (data.logrMax - state.logr) / (data.logrMax - data.logrMin);
  $('slider').value = String(frac);
  $('pos').textContent = `log10(r/r_s) = ${state.logr.toFixed(3)}   r = ${fmt.sci(smp.r_m, 3)} m`;
  const atEnd = state.logr <= data.logrMin + 1e-9;
  $('planck').classList.toggle('hidden', !(atEnd && !state.speculative));
  $('planck').textContent = raw.planck_message;
  views[state.view].update(smp, state);
}

// playback
let last = performance.now();
function loop(now) {
  const dt = (now - last) / 1000; last = now;
  if (state.playing) {
    if (state.axis === 'logr') state.logr -= state.speedDecPerS * dt;
    else {
      const frac = (data.logrMax - state.logr) / (data.logrMax - data.logrMin);
      // proper-time playback: advance tau fraction linearly (only meaningful outside ~0.1 r_s)
      const tau = data.at(state.logr).tau_years, tauEnd = data.s.tau_years[data.N - 1];
      const f = Math.min(1, tau / tauEnd + 0.02 * state.speedDecPerS * dt);
      state.logr = data.logrForTauFraction(f);
    }
    if (state.logr <= data.logrMin) { state.logr = data.logrMin; state.playing = false; $('play').textContent = '▶ Play'; }
    render(false);
  } else if (state.view === 'scene' || state.view === 'fp') {
    views[state.view].update(state.sample || data.at(state.logr), state);  // camera orbit / redraw
  }
  requestAnimationFrame(loop);
}

// UI wiring
document.querySelectorAll('header .tabs button').forEach(b => b.addEventListener('click', () => setView(b.dataset.view)));
$('play').addEventListener('click', () => { state.playing = !state.playing; $('play').textContent = state.playing ? '❚❚ Pause' : '▶ Play'; if (state.playing && state.logr <= data.logrMin) state.logr = data.logrMax; });
$('speed').addEventListener('change', e => { state.speedDecPerS = parseFloat(e.target.value); });
$('axis').addEventListener('change', e => { state.axis = e.target.value; });
$('slider').addEventListener('input', e => { const f = parseFloat(e.target.value); state.playing = false; $('play').textContent = '▶ Play'; setLogR(data.logrMax - f * (data.logrMax - data.logrMin)); });
window.addEventListener('resize', () => { Object.values(views).forEach(v => v.resize()); render(true); });
window.addEventListener('keydown', e => {
  if (e.key === ' ') { $('play').click(); e.preventDefault(); }
  if (e.key === 'ArrowRight') setLogR(state.logr - 0.25);
  if (e.key === 'ArrowLeft') setLogR(state.logr + 0.25);
  if (e.key >= '1' && e.key <= '4') setView(['scene', 'causal', 'fp', 'spec'][parseInt(e.key) - 1]);
});

// validation summary
{
  const s = raw.summary;
  $('validation').innerHTML = `steps ${s.n_steps_total}, RHS evals ${s.n_rhs_evals_total}, rejected ${s.n_rejected_total}<br>` +
    `max |g(u,u)+1| = ${fmt.sci(s.max_abs_norm_residual, 2)}; max conditioned E drift = ${fmt.sci(s.max_E_drift_conditioned, 2)}<br>` +
    `τ(horizon→r_QG) = ${fmt.years(s.tau_since_horizon_years_at_end)} (analytic 4GM/3c³ = ${fmt.years(data.derived.tau_horizon_to_singularity_years)})<br>` +
    `See validation_report.json for TESTS 0–8.`;
}

// public API for tests / console
window.SLAB_APP = { state, data, setView, setLogR, setSceneMode, views, render,
  setCamera(c) { state.camera = c; render(true); },
  jumpTo(slug) { const m = data.milestone(slug); if (m) setLogR(m.log10_r_over_rs); } };

setView('scene');
render(true);
requestAnimationFrame(loop);
