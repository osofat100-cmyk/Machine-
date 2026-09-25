// First-person camera view.  DEFAULT: double-precision CPU renderer (no WebGL needed; firstperson_cpu.js) driven by
// the exact 1D transfer table (firstperson_table.js) — valid from r = 100 r_s down to r_QG.  OPTIONAL: float32 GPU
// shader (firstperson_gpu.js), created only if the user picks it, limited to r > 1e-5 r_s.
// "Qualitative visualization — trajectory calculations remain relativistic."  (sky = illustrative backdrop,
// colours qualitative unless the false-colour log10 g layer is selected).
// Interface used by main.js: constructor(container, data, opts) / update(sample, state) / resize() / setMode(mode) /
// dispose() / getCanvas().  Properties yaw, pitch, fov, dirty are also set directly by tests/viewer/check_viewer.mjs.
import { fmt } from './data.js';
import { observerState, skyFractions } from './firstperson_core.js';
import { TransferTable } from './firstperson_table.js';
import { CpuRenderer, cameraAxes, KIND_SKY, KIND_PAST, KIND_UNRESOLVED } from './firstperson_cpu.js';
import { celestialFrame, gScaleRange, gColor, HOLE_DIRECTION } from './firstperson_sky.js';
import { loadStars, STAR_ATTRIBUTION } from './starcatalog.js';
import { GpuTracer, R_MIN_GPU, webglAvailable } from './firstperson_gpu.js';

const BUDGET_MS = 24;           // CPU work per animation frame (keeps the UI responsive)
const TABLE_CACHE = 6;

export class FirstpersonView {
  constructor(container, data, opts = {}) {
    this.container = container; this.data = data; this.opts = opts;
    this.yaw = 0; this.pitch = 0; this.fov = 90; this.quality = 0.5; this.dirty = true; this.ready = true;
    this.engine = 'cpu'; this.background = 'stars'; this.layer = 'tint'; this.exposure = 0;
    this.lastKey = null; this.tables = new Map(); this.cpu = new CpuRenderer(); this.phase = 'idle';
    this.M = celestialFrame(); this.stars = loadStars();
    this.gpu = null; this.gpuNote = webglAvailable() ? '' : 'WebGL is not available in this browser: GPU mode disabled.';
    this._buildDom();
    this.resize();
  }

  _buildDom() {
    const c = this.container;
    if (getComputedStyle(c).position === 'static') c.style.position = 'relative';
    this.canvas = document.createElement('canvas');
    this.canvas.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;';
    c.appendChild(this.canvas);
    this.ctx = this.canvas.getContext('2d');
    this.banner = document.createElement('div'); this.banner.className = 'overlay';
    this.banner.style.cssText += 'top:48px;bottom:auto;max-width:min(58%, 720px);white-space:normal;font-size:11px;';
    c.appendChild(this.banner);
    this.stats = document.createElement('div'); this.stats.className = 'overlay'; this.stats.style.cssText += 'max-width:calc(100% - 500px);white-space:normal;font-size:11px;';
    c.appendChild(this.stats);
    // colour scale (false-colour layer)
    this.scale = document.createElement('div'); this.scale.className = 'overlay';
    this.scale.style.cssText += 'right:10px;left:auto;top:48px;bottom:auto;text-align:center;display:none;';
    this.scaleCanvas = document.createElement('canvas'); this.scaleCanvas.width = 18; this.scaleCanvas.height = 200;
    this.scaleCanvas.style.cssText = 'width:18px;height:200px;display:inline-block;vertical-align:middle;';
    this.scaleLabel = document.createElement('div');
    this.scale.append(this.scaleLabel);
    c.appendChild(this.scale);
    const ctl = document.createElement('div'); ctl.className = 'overlay';
    ctl.style.cssText += 'right:10px;left:auto;bottom:10px;pointer-events:auto;text-align:right;line-height:1.9;width:470px;font-size:11px;';
    const gpuDisabled = this.gpuNote ? 'disabled' : '';
    ctl.innerHTML = `<button id="fp-in">look toward the hole</button> <button id="fp-out">look outward</button>
      FOV <input id="fp-fov" type="range" min="40" max="160" value="90" style="width:90px;vertical-align:middle"><br>
      renderer <select id="fp-engine"><option value="cpu">CPU (double precision, exact, default)</option><option value="gpu" ${gpuDisabled}>GPU (float32, r &gt; 1e-5 r_s)</option></select>
      resolution <select id="fp-q"><option value="0.35">low</option><option value="0.5">medium</option><option value="0.75">high</option><option value="1">full</option></select><br>
      background <select id="fp-bg"><option value="stars">star catalogue</option><option value="grid">coordinate grid</option></select>
      colour <select id="fp-layer"><option value="tint">qualitative tint</option><option value="gmap">false colour: log10 g</option></select>
      stars <select id="fp-exp"><option value="0">exposure ×1</option><option value="5">×100</option><option value="10">×10^4</option></select>
      <div class="note" id="fp-note">drag to look around</div>`;
    c.appendChild(ctl);
    this.ctl = ctl;
    const q = s => ctl.querySelector(s);
    q('#fp-in').onclick = () => { this.yaw = 0; this.pitch = 0; this.dirty = true; };
    q('#fp-out').onclick = () => { this.yaw = Math.PI; this.pitch = 0; this.dirty = true; };
    q('#fp-fov').oninput = e => { this.fov = parseFloat(e.target.value); this.dirty = true; };
    q('#fp-q').value = String(this.quality); q('#fp-q').onchange = e => { this.quality = parseFloat(e.target.value); this.resize(); };
    q('#fp-bg').onchange = e => { this.background = e.target.value; this.dirty = true; };
    q('#fp-layer').onchange = e => { this.layer = e.target.value; this.dirty = true; };
    q('#fp-exp').onchange = e => { this.exposure = parseFloat(e.target.value); this.dirty = true; };
    q('#fp-engine').onchange = e => this.setEngine(e.target.value);
    if (this.gpuNote) q('#fp-note').textContent = this.gpuNote + ' Drag to look around.';
    let drag = null;
    this.canvas.addEventListener('pointerdown', e => { drag = [e.clientX, e.clientY, this.yaw, this.pitch]; });
    this._onMove = e => { if (!drag) return; this.yaw = drag[2] + (e.clientX - drag[0]) * 0.005; this.pitch = Math.max(-1.5, Math.min(1.5, drag[3] - (e.clientY - drag[1]) * 0.005)); this.dirty = true; };
    this._onUp = () => { drag = null; };
    window.addEventListener('pointermove', this._onMove);
    window.addEventListener('pointerup', this._onUp);
  }

  setEngine(name) {
    if (name === 'gpu' && !this.gpu) {
      try { this.gpu = new GpuTracer(this.container); this.container.insertBefore(this.gpu.canvas, this.canvas); this.gpu.canvas.addEventListener('pointerdown', e => this.canvas.dispatchEvent(new PointerEvent('pointerdown', e))); }
      catch (err) {
        this.gpu = null; this.gpuNote = 'GPU mode unavailable (WebGL failed: ' + err + ').';
        const sel = this.ctl.querySelector('#fp-engine'); sel.value = 'cpu'; sel.querySelector('option[value=gpu]').disabled = true;
        this.ctl.querySelector('#fp-note').textContent = this.gpuNote; name = 'cpu';
      }
    }
    this.engine = name;
    this.ctl.querySelector('#fp-engine').value = name;
    this.dirty = true;
    this.resize();
  }

  getCanvas() {
    // A canvas with the current image PLUS the baked-in labels (banner, r, colour scale) at display resolution.
    const src = (this._gpuActive() ? this.gpu.canvas : this.canvas);
    const W = this.container.clientWidth || src.width, H = this.container.clientHeight || src.height;
    const out = document.createElement('canvas'); out.width = W; out.height = H;
    const x = out.getContext('2d');
    x.imageSmoothingEnabled = true; x.drawImage(src, 0, 0, W, H);
    x.fillStyle = 'rgba(0,0,0,0.6)'; x.fillRect(0, 0, W, 38);
    x.fillStyle = '#ffb454'; x.font = 'bold 13px sans-serif';
    x.fillText(this.data.raw.banner_firstperson, 8, 15);
    x.fillStyle = '#d8dee9'; x.font = '11px sans-serif';
    x.fillText(this._captionLine || '', 8, 31);
    if (this.layer === 'gmap' && !this._gpuActive()) this._drawScale(x, W - 70, 50, 16, Math.min(260, H - 100));
    return out;
  }

  _gpuActive() { return this.engine === 'gpu' && this.gpu && this.obs && this.obs.r >= R_MIN_GPU; }

  _drawScale(x, X, Y, w, h) {
    const L = this.gRange;
    for (let i = 0; i < h; i++) { const c = gColor(L * (1 - 2 * i / (h - 1)), L); x.fillStyle = `rgb(${255 * c[0] | 0},${255 * c[1] | 0},${255 * c[2] | 0})`; x.fillRect(X, Y + i, w, 1); }
    x.strokeStyle = '#ccc'; x.strokeRect(X, Y, w, h);
    x.fillStyle = '#fff'; x.font = '11px sans-serif';
    x.fillText(`+${fmt.sci(L, 3)}`, X + w + 3, Y + 8); x.fillText('0', X + w + 3, Y + h / 2 + 4); x.fillText(`−${fmt.sci(L, 3)}`, X + w + 3, Y + h);
    x.fillText('log10 g', X - 8, Y - 6);
  }

  _table(obs) {
    const key = `${obs.r}|${obs.E}`;
    let t = this.tables.get(key);
    if (!t) {
      t = new TransferTable(obs);
      this.tables.set(key, t);
      if (this.tables.size > TABLE_CACHE) this.tables.delete(this.tables.keys().next().value);
    }
    return t;
  }

  _startRender(opts) {
    const W = this.canvas.width, H = this.canvas.height;
    const { F, R, U } = cameraAxes(this.yaw, this.pitch);
    const tanH = Math.tan(this.fov * Math.PI / 360);
    this.cam = { F, R, U, tanH, tanV: tanH * H / W };
    this.cpu.start({ width: W, height: H, obs: this.obs, table: this.table, cam: this.cam, M: this.M, background: this.background, layer: this.layer,
      gRange: this.gRange, stars: this.stars, exposure: this.exposure, ...opts });
    this.imageData = new ImageData(this.cpu.rgba, W, H);
  }

  update(smp, state) {
    if (!smp) return;
    const rGeo = 2 * smp.r_over_rs;
    const E = (smp.E_killing === null || smp.E_killing === undefined || !isFinite(smp.E_killing)) ? 1 : smp.E_killing;
    const key = `${rGeo}|${E}`;
    let restart = false;
    if (key !== this.lastKey) {
      this.lastKey = key; this.sample = smp;
      this.obs = observerState(rGeo, E);
      this.table = this._table(this.obs);
      this.fractions = skyFractions(this.obs);
      this.gRange = gScaleRange(this.obs, isNaN(this.fractions.dnMinSky) ? 1 : this.fractions.dnMinSky);
      restart = true;
    }
    if (this.dirty) {
      this.dirty = false; restart = true;
      // keep the controls in sync with state set programmatically (tests, other modules)
      const q = sel => this.ctl.querySelector(sel);
      q('#fp-bg').value = this.background; q('#fp-layer').value = this.layer; q('#fp-exp').value = String(this.exposure);
      q('#fp-fov').value = String(this.fov); q('#fp-engine').value = this.engine;
    }
    if (this._gpuActive()) {
      if (restart) {
        const { F, R, U } = cameraAxes(this.yaw, this.pitch); const tanH = Math.tan(this.fov * Math.PI / 360);
        this.cam = { F, R, U, tanH, tanV: tanH * this.gpu.canvas.height / this.gpu.canvas.width };
        this.gpu.render(this.obs, this.cam, this.M); this._updateText();
      }
      this.gpu.canvas.style.display = ''; this.canvas.style.display = 'none';
      return;
    }
    if (this.gpu) { this.gpu.canvas.style.display = 'none'; }
    this.canvas.style.display = '';
    if (restart) {
      // coarse image first (block 8), then finish the table, then the progressive full-resolution image
      this.phase = this.table.done ? 'render' : 'coarse';
      this._startRender(this.phase === 'coarse' ? { maxLevel: 0 } : {});
    }
    const t0 = performance.now();
    let changed = false;
    while (performance.now() - t0 < BUDGET_MS && this.phase !== 'idle') {
      const left = BUDGET_MS - (performance.now() - t0);
      if (this.phase === 'coarse') { changed = this.cpu.step(left) || changed; if (this.cpu.done) this.phase = 'table'; }
      else if (this.phase === 'table') { if (this.table.refine(left)) { this.phase = 'render'; this._startRender({ startLevel: 1 }); this.cpu.step(0); } }
      else if (this.phase === 'render') { changed = this.cpu.step(left) || changed; if (this.cpu.done) this.phase = 'idle'; }
    }
    if (changed || restart) { this.ctx.putImageData(this.imageData, 0, 0); this._updateText(); }
  }

  _updateText() {
    const smp = this.sample, o = this.obs, fr = this.fractions;
    const inside = o.r < 2;
    const gpu = this._gpuActive();
    const lvlC = this.cpu.levelCounts;
    const tot = lvlC ? lvlC[0] + lvlC[1] + lvlC[2] : 0;
    const pc = v => (100 * v).toFixed(v < 0.001 && v > 0 ? 4 : 1);
    const coneDeg = inside && !isNaN(fr.dnMinSky) ? Math.acos(Math.max(-1, Math.min(1, fr.dnMinSky))) * 180 / Math.PI : null;
    const coneStr = coneDeg === null ? '' : (Math.abs(fr.dnMinSky) < 1e-6 ? `90° + ${fmt.sci(Math.asin(-fr.dnMinSky), 3)} rad` : `${coneDeg.toFixed(3)}°`);
    this._captionLine = `r = ${fmt.sci(smp.r_m, 3)} m = ${fmt.sci(smp.r_over_rs, 3)} r_s (${inside ? 'inside' : 'outside'} the horizon) — ` +
      `${gpu ? 'GPU float32' : 'CPU double precision'}; sky: ${this.background === 'stars' ? 'Earth J2000 bright stars' : 'RA/Dec grid'} at infinity, hole placed toward Sgr A* (ILLUSTRATIVE)` +
      (this.layer === 'gmap' ? '; false colour = log10 g' : '; colours qualitative');
    this.banner.innerHTML = `<b>${this.data.raw.banner_firstperson}</b><br>` +
      `Each pixel's past light ray is followed exactly (Schwarzschild null geodesic from the falling observer's own frame: aberration, lensing and the frequency ratio g = ν_seen/ν_emitted-at-infinity included; ` +
      `the picture is symmetric about the radial direction, so one exact 1D table of sky angles serves all pixels). ` +
      `Backdrop: ${gpu ? 'RA/Dec grid every 15° (GPU float32 mode: no star catalogue, sky angle taken at r = 400 M)' : this.background === 'stars' ? STAR_ATTRIBUTION : 'RA/Dec grid every 15°'}; the hole is placed in the direction of ${HOLE_DIRECTION.label} — ` +
      `green ring = 2.5° around the hole's direction, gold ring = 2.5° around the opposite direction. ${this.layer === 'gmap' ? 'Hatched grey' : 'Dark red'} = rays ending on the past horizon (not modelled), magenta = unresolved.` +
      (this.layer === 'gmap' ? ` False colour: log10 g (red = redshift, blue = blueshift), scale at right.` : ` Colour tint is qualitative.`) +
      (this.engine === 'gpu' && !gpu ? `<br><span style="color:#ffb454">GPU float32 cannot represent the ray state below r = ${fmt.sci(R_MIN_GPU / 2, 1)} r_s: showing the double-precision CPU renderer instead (LABELLED LIMIT).</span>` : '');
    const tableState = this.table.done ? `${this.table.p.length} samples` : `refining (${this.table.p.length} samples)`;
    this.stats.innerHTML = `r = ${fmt.sci(smp.r_m, 3)} m = ${fmt.sci(smp.r_over_rs, 3)} r_s = ${fmt.sci(o.r, 3)} GM/c² — ${inside ? 'INSIDE the horizon' : 'outside the horizon'}<br>` +
      `all directions (exact): exterior sky ${pc(fr.sky)} %, past horizon / not modelled ${pc(fr.past)} %` +
      (tot ? `; this image: sky ${pc(lvlC[KIND_SKY] / tot)} %, past ${pc(lvlC[KIND_PAST] / tot)} %, unresolved ${pc(lvlC[KIND_UNRESOLVED] / tot)} %` : '') + '<br>' +
      (gpu ? `GPU float32 shader` : `CPU: table ${tableState}, image ${this.phase === 'idle' ? 'complete' : 'refining'}${this.background === 'stars' ? `, ${this.cpu.starCount} star images drawn` : ''}`) +
      `; look: yaw ${(this.yaw * 180 / Math.PI).toFixed(0)}° (0 = toward the hole, 180 = outward), pitch ${(this.pitch * 180 / Math.PI).toFixed(0)}°, FOV ${this.fov}°` +
      (inside ? `<br>Inside r_s the exterior universe is seen only along rays whose photons have positive Killing energy AND impact parameter b < 3√3 GM/c²: ` +
        `a cone of half-angle ${coneStr} around the OUTWARD direction. All other directions (${this.layer === 'gmap' ? 'hatched grey' : 'dark red'}) show light that left the past horizon ` +
        `(the white-hole / other-universe region of the eternal solution; for a real hole, the collapsing star) — not modelled.` : '') +
      (o.r < 1e-6 ? `<br>Deep inside, the whole exterior sky except a tiny patch around the outward direction is squeezed into an unresolvably thin, strongly blueshifted ring at the edge of this cone; ` +
        `the rest of the outward view is a hugely magnified, strongly redshifted image of that patch (see docs: first-person camera near r_QG).` : '');
    if (this.layer === 'gmap' && !gpu) {
      this.scale.style.display = '';
      const x = this.scaleCanvas.getContext('2d'); const h = this.scaleCanvas.height;
      for (let i = 0; i < h; i++) { const c = gColor(this.gRange * (1 - 2 * i / (h - 1)), this.gRange); x.fillStyle = `rgb(${255 * c[0] | 0},${255 * c[1] | 0},${255 * c[2] | 0})`; x.fillRect(0, i, 18, 1); }
      this.scaleLabel.innerHTML = `log10 g<br>+${fmt.sci(this.gRange, 3)} (blue)<br>`;
      this.scaleLabel.appendChild(this.scaleCanvas);
      this.scaleLabel.insertAdjacentHTML('beforeend', `<br>−${fmt.sci(this.gRange, 3)} (red)<br><span class="note">g = ν_seen / ν_emitted at ∞</span>`);
    } else this.scale.style.display = 'none';
  }

  resize() {
    const w = this.container.clientWidth || 800, h = this.container.clientHeight || 600;
    const W = Math.max(32, Math.round(w * this.quality)), H = Math.max(32, Math.round(h * this.quality));
    if (this.canvas.width !== W || this.canvas.height !== H) { this.canvas.width = W; this.canvas.height = H; }
    if (this.gpu) this.gpu.setSize(Math.max(16, Math.round(w * Math.min(this.quality, 0.35))), Math.max(16, Math.round(h * Math.min(this.quality, 0.35))));
    this.dirty = true;
  }

  setMode() {}

  dispose() {
    window.removeEventListener('pointermove', this._onMove);
    window.removeEventListener('pointerup', this._onUp);
    this.gpu?.dispose();
  }
}
