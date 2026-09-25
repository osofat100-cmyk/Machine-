// Interactive 3D view of the infall.  All physics is precomputed by the Python engine; this module only
// maps the true radius to a screen radius (LOGARITHMIC by default — NOT TO SCALE) and draws shells,
// the worldline, the observer and its local light cone.
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { fmt } from './data.js';
import { LightCone, drawConeInset } from './lightcone.js';

const REGIME_COLORS = [0x6ee7a0, 0xffb454, 0xff6b6b];
const SHORT = { isco: 'ISCO 3 r_s', photon_sphere: 'photon sphere 1.5 r_s', '0.1rs': '0.1 r_s', '0.01rs': '0.01 r_s', '1ly': '1 ly', '1e-6rs': '1e-6 r_s', '1au': '1 AU',
  extreme_curvature: 'extreme-curvature onset', '1km': '1 km', '1m': '1 m', atomic: '1 Å', nuclear: '1 fm', r_QG: 'r_QG (end of validated GR)' };
const MODE_LABEL = {
  log: 'LOGARITHMIC VISUALIZATION — NOT TO SCALE  (screen radius ∝ log10 r; whole range 100 r_s → r_QG)',
  deep: 'LOGARITHMIC VISUALIZATION — NOT TO SCALE  (deep interior: 10⁻⁶ r_s → r_QG)',
  curvature: 'LOGARITHMIC VISUALIZATION — NOT TO SCALE  (shells coloured by log10 Kretschmann K)',
  linear: 'LINEAR LOCAL VIEW — true proportions within the window around the observer',
  horizon: 'LINEAR VIEW OF THE HORIZON NEIGHBOURHOOD (0.85–1.15 r_s) — true proportions',
};

function makeLabel(text, color = '#d8dee9', size = 22) {
  const lines = text.split('\n');
  const c = document.createElement('canvas'); const ctx = c.getContext('2d');
  ctx.font = `${size}px system-ui, sans-serif`;
  const w = Math.max(...lines.map(l => ctx.measureText(l).width)) + 16, h = lines.length * (size + 6) + 10;
  c.width = Math.ceil(w); c.height = Math.ceil(h);
  ctx.font = `${size}px system-ui, sans-serif`; ctx.fillStyle = 'rgba(11,14,20,0.6)'; ctx.fillRect(0, 0, c.width, c.height);
  ctx.fillStyle = color; ctx.textBaseline = 'top';
  lines.forEach((l, i) => ctx.fillText(l, 8, 5 + i * (size + 6)));
  const tex = new THREE.CanvasTexture(c); tex.minFilter = THREE.LinearFilter;
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthTest: false }));
  sp.scale.set(c.width / 60, c.height / 60, 1);
  return sp;
}

function kColor(logK, lo, hi) {
  const t = Math.max(0, Math.min(1, (logK - lo) / (hi - lo)));
  return new THREE.Color().setHSL(0.66 * (1 - t), 0.9, 0.35 + 0.3 * t);
}

export class Scene3dView {
  constructor(container, data, opts = {}) {
    this.container = container; this.data = data; this.opts = opts;
    this.mode = 'log'; this.follow = false; this.showLabels = true; this.ready = false;
    try { this._init(); this.ready = true; } catch (e) {
      const msg = document.createElement('div'); msg.className = 'overlay';
      msg.textContent = '3D view unavailable (WebGL failed): ' + e; container.appendChild(msg);
    }
  }
  _init() {
    const d = this.data;
    this.renderer = new THREE.WebGLRenderer({ antialias: false, alpha: false, powerPreference: 'low-power' });
    this.renderer.setPixelRatio(Math.min(1.5, window.devicePixelRatio || 1));
    this.renderer.setClearColor(0x0b0e14);
    this.container.appendChild(this.renderer.domElement);
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(50, 1, 0.01, 5000);
    this.camera.position.set(52, 30, 58);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true; this.controls.dampingFactor = 0.1;
    this.scene.add(new THREE.AmbientLight(0xffffff, 0.7));
    const dl = new THREE.DirectionalLight(0xffffff, 0.6); dl.position.set(1, 2, 1); this.scene.add(dl);
    this.group = new THREE.Group(); this.scene.add(this.group);
    this.logK = { lo: Math.min(...d.s.K_SI_log10.filter(x => x !== null)), hi: Math.max(...d.s.K_SI_log10.filter(x => x !== null)) };
    // overlays
    this.overlay = document.createElement('div'); this.overlay.className = 'overlay'; this.overlay.style.top = '48px'; this.overlay.style.bottom = 'auto'; this.overlay.style.maxWidth = '60%';
    this.container.appendChild(this.overlay);
    this.inset = document.createElement('canvas'); this.inset.style.cssText = 'position:absolute;right:10px;bottom:10px;width:280px;height:190px;border:1px solid #2b3549;border-radius:4px;';
    this.container.appendChild(this.inset);
    this.legend = document.createElement('div'); this.legend.className = 'overlay'; this.legend.style.cssText += 'right:10px;left:auto;top:100px;bottom:auto;display:none;max-height:45%;overflow:auto;pointer-events:auto;';
    this.container.appendChild(this.legend);
    this._buildControls();
    this._rebuild();
    this.resize();
  }
  _buildControls() {
    const c = this.opts.controls; if (!c) return;
    c.innerHTML = `
      <label>scene mode <select id="scene-mode">
        <option value="log">log-radius view (whole range)</option><option value="linear">linear local view</option>
        <option value="horizon">event-horizon neighbourhood</option><option value="deep">deep-interior view</option>
        <option value="curvature">curvature view</option></select></label>
      <label><input type="checkbox" id="scene-follow"> camera follows observer</label>
      <label><input type="checkbox" id="scene-labels" checked> shell labels</label>
      <button id="scene-reset">reset camera</button>
      <div class="note">Drag to orbit, wheel to zoom. The black hole is at the origin; the observer falls along the +x axis (equatorial plane = xz).</div>`;
    c.querySelector('#scene-mode').addEventListener('change', e => (window.SLAB_APP ? window.SLAB_APP.setSceneMode(e.target.value) : this.setMode(e.target.value)));
    c.querySelector('#scene-follow').addEventListener('change', e => { this.follow = e.target.checked; });
    c.querySelector('#scene-labels').addEventListener('change', e => { this.showLabels = e.target.checked; this.labels.forEach(l => l.visible = this.showLabels); });
    c.querySelector('#scene-reset').addEventListener('click', () => { this.camera.position.set(52, 30, 58); this.controls.target.set(0, 0, 0); });
  }
  // ---- radial mapping (true r/r_s -> screen radius) --------------------------------------------
  mapR(rOverRs, ref) {
    const d = this.data, lr = Math.log10(rOverRs);
    switch (this.mode) {
      case 'linear': return 12 * rOverRs / ref;                       // observer at screen radius 12
      case 'horizon': return 20 * rOverRs;                            // horizon at screen radius 20
      case 'deep': { const hi = -6, lo = d.logrMin; return lr > hi ? NaN : 1 + 30 * (lr - lo) / (hi - lo); }
      default: return 1 + 30 * (lr - d.logrMin) / (d.logrMax - d.logrMin);
    }
  }
  _clear() { while (this.group.children.length) { const o = this.group.children.pop(); o.traverse?.(x => { x.geometry?.dispose?.(); x.material?.dispose?.(); }); } this.labels = []; }
  _shell(R, color, opacity, wire = true) {
    // A shell is drawn as three great circles (equator + two meridians): far less clutter than a wireframe sphere.
    if (!wire) {
      const m = new THREE.Mesh(new THREE.SphereGeometry(R, 40, 24), new THREE.MeshPhongMaterial({ color, transparent: true, opacity, depthWrite: false }));
      this.group.add(m); return m;
    }
    const g = new THREE.Group();
    const mat = new THREE.LineBasicMaterial({ color, transparent: true, opacity: Math.min(1, opacity * 2.2) });
    const n = 96, pts = [];
    for (let i = 0; i <= n; i++) { const a = i / n * 2 * Math.PI; pts.push(new THREE.Vector3(R * Math.cos(a), 0, R * Math.sin(a))); }
    const ring = new THREE.BufferGeometry().setFromPoints(pts);
    const eq = new THREE.Line(ring, mat); g.add(eq);
    const m1 = new THREE.Line(ring, mat); m1.rotation.x = Math.PI / 2; g.add(m1);
    const m2 = new THREE.Line(ring, mat); m2.rotation.z = Math.PI / 2; g.add(m2);
    this.group.add(g); return g;
  }
  _rebuild(refROverRs = 1) {
    this._clear();
    const d = this.data, mode = this.mode;
    const legendRows = [];
    const shellsVisible = (r) => mode === 'linear' ? (r / refROverRs > 0.03 && r / refROverRs < 3.5) : mode === 'horizon' ? (r > 0.84 && r < 1.16) : true;
    // horizon
    if (shellsVisible(1)) {
      const Rh = this.mapR(1, refROverRs);
      if (isFinite(Rh)) {
        this._shell(Rh, 0xff8c42, 0.18, false); this._shell(Rh * 1.002, 0xff8c42, 0.25, true);
        this._label('r_s  event horizon', Rh, 3, '#ff8c42');
        legendRows.push(`<tr><td style="color:#ff8c42">r_s</td><td>event horizon (not a physical wall — crossed continuously)</td><td>${fmt.sci(d.derived.r_s_m, 3)} m</td><td>1</td><td>${Rh.toFixed(1)}</td></tr>`);
      }
    }
    // milestone shells
    for (const m of d.milestones) {
      if (m.slug === 'horizon' || m.slug === 'start') continue;
      if (!shellsVisible(m.r_over_rs)) continue;
      const R = this.mapR(m.r_over_rs, refROverRs); if (!isFinite(R)) continue;
      let color = 0x3f5c8a, op = 0.35;
      if (mode === 'curvature') { const i = d.indexOf(m.log10_r_over_rs); const lk = d.atIndex(i).K_SI_log10; color = kColor(lk, this.logK.lo, this.logK.hi).getHex(); op = 0.5; }
      if (m.slug === 'r_QG') { this._shell(R, 0xff6b6b, 0.9, false); this._shell(R * 1.001, 0xff6b6b, 0.5, true); }
      else this._shell(R, color, op, true);
      const idx = d.milestones.indexOf(m);
      this._label(SHORT[m.slug] || m.slug, R, idx, m.slug === 'r_QG' ? '#ff6b6b' : '#c8d0e0');
      legendRows.push(`<tr><td style="color:${m.slug === 'r_QG' ? '#ff6b6b' : '#c8d0e0'}">${SHORT[m.slug] || m.slug}</td><td>${m.label}</td><td>${fmt.sci(m.r_m, 3)} m</td><td>${fmt.sci(m.r_over_rs, 3)}</td><td>${R.toFixed(1)}</td></tr>`);
    }
    if (mode === 'horizon') { for (const x of [0.9, 1.1]) { const R = this.mapR(x, refROverRs); this._shell(R, 0x3f5c8a, 0.3, true); this._label(`${x} r_s`, R, x > 1 ? 5 : 1, '#c8d0e0'); } }
    // worldline coloured by regime (radial, along +x, in the equatorial plane)
    const pts = [], cols = [];
    for (let i = 0; i < d.N; i++) {
      const r = d.s.r_over_rs[i]; const R = this.mapR(r, refROverRs); if (!isFinite(R)) continue;
      if (mode === 'linear' && (r / refROverRs < 0.02 || r / refROverRs > 4)) continue;
      if (mode === 'horizon' && (r < 0.84 || r > 1.16)) continue;
      const ph = d.s.phi ? (d.s.phi[i] ?? 0) : 0;
      pts.push(R * Math.cos(ph), 0, R * Math.sin(ph));
      const c = new THREE.Color(REGIME_COLORS[d.s.regime_code[i] ?? 0]); cols.push(c.r, c.g, c.b);
    }
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3)); g.setAttribute('color', new THREE.Float32BufferAttribute(cols, 3));
    this.group.add(new THREE.Line(g, new THREE.LineBasicMaterial({ vertexColors: true, linewidth: 2 })));
    // observer marker + trail + cone
    this.marker = new THREE.Mesh(new THREE.SphereGeometry(0.45, 16, 12), new THREE.MeshPhongMaterial({ color: 0xffffff, emissive: 0x7ab7ff, emissiveIntensity: 0.8 }));
    this.group.add(this.marker);
    this.cone = new LightCone(2.2); this.group.add(this.cone.group);
    this.coneLabel = makeLabel('local future light cone\n(t_EF up, r outward; exact null directions)', '#ffd166', 18); this.group.add(this.coneLabel); this.labels.push(this.coneLabel);
    // axes hint
    const ax = new THREE.AxesHelper(3); ax.position.set(0, 0, 0); this.group.add(ax);
    this.legend.style.display = 'block';
    const wasOpen = this.legend.querySelector('details')?.open ?? false;
    this.legend.innerHTML = (mode === 'curvature' ? `<b>shell colour = log10 K [m⁻⁴]</b>: blue ${this.logK.lo.toFixed(1)} … red ${this.logK.hi.toFixed(1)} (Planck ${Math.log10(d.derived.K_planck).toFixed(1)}); observer colour = regime<br>` : '') +
      `<details${wasOpen ? ' open' : ''}><summary style="cursor:pointer">shell legend (${legendRows.length} shells; screen radius ${mode === 'linear' || mode === 'horizon' ? 'proportional to r' : 'logarithmic in r — NOT TO SCALE'}) — click to expand</summary>` +
      `<table style="border-collapse:collapse;font-size:11px"><tr style="color:#8892a6"><th>tag</th><th>shell</th><th>true r</th><th>r/r_s</th><th>screen R</th></tr>${legendRows.join('')}</table></details>`;
    this.labels.forEach(l => l.visible = this.showLabels);
  }
  _label(text, R, idx, color) {
    // short tag on the shell's equator, azimuth spread by index so tags of nested shells do not overlap
    const sp = makeLabel(text, color, 26); sp.scale.multiplyScalar(0.55);
    const a = 0.6 + 0.55 * (idx % 9);
    sp.position.set(R * Math.cos(a), 0.06 * R + 0.3, R * Math.sin(a));
    this.group.add(sp); this.labels.push(sp);
  }
  setMode(mode) { if (!this.ready) return; this.mode = MODE_LABEL[mode] ? mode : 'log'; this._lastRef = null; const sel = this.opts.controls?.querySelector('#scene-mode'); if (sel) sel.value = this.mode; }
  update(smp, state) {
    if (!this.ready || !smp) return;
    const r = smp.r_over_rs;
    const needRebuild = this.mode !== this._builtMode || (this.mode === 'linear' && (!this._lastRef || Math.abs(Math.log10(r / this._lastRef)) > 0.15));
    if (needRebuild) { this._rebuild(r); this._builtMode = this.mode; this._lastRef = r; }
    const R = this.mapR(r, this._lastRef || r);
    const ph = smp.phi ?? 0;
    const visible = isFinite(R);
    this.marker.visible = visible; this.cone.group.visible = visible; this.coneLabel.visible = visible && this.showLabels;
    if (visible) {
      this.marker.position.set(R * Math.cos(ph), 0, R * Math.sin(ph));
      this.marker.material.emissive.set(REGIME_COLORS[state?.speculative ? 2 : (smp.regime_code ?? 0)]);
      this.cone.group.position.copy(this.marker.position);
      this.cone.group.rotation.y = -ph;   // local radial axis = outward direction at the observer
      const f = 1 - 1 / r;
      this.cone.update(f, smp.lc_out_drdtEF ?? f / (2 - f), smp.lc_in_drdtEF ?? -1, smp.worldline_drdtEF ?? 0);
      this.coneLabel.position.set(this.marker.position.x + 1.5, 3.4, this.marker.position.z + 1.5);
      if (this.follow) this.controls.target.lerp(this.marker.position, 0.2);
    }
    const inside = r <= 1;
    this.overlay.innerHTML = `<b>${MODE_LABEL[this.mode]}</b><br>true radius r = ${fmt.metres(smp.r_m)}  ·  r/r_s = ${fmt.sci(r, 5)}  ·  ${inside ? 'INSIDE the horizon' : 'outside the horizon'}` +
      (this.mode === 'deep' && !isFinite(R) ? '<br>(observer still outside the deep-interior window r ≤ 10⁻⁶ r_s)' : '') +
      (this.mode === 'horizon' && (r < 0.84 || r > 1.16) ? '<br>(observer outside the 0.85–1.15 r_s window)' : '');
    drawConeInset(this.inset, smp);
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }
  resize() {
    if (!this.ready) return;
    const w = this.container.clientWidth || 800, h = this.container.clientHeight || 600;
    this.renderer.setSize(w, h, false); this.camera.aspect = w / h; this.camera.updateProjectionMatrix();
  }
  dispose() { this.renderer?.dispose(); }
}
