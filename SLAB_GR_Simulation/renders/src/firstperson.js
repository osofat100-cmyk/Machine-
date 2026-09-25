// First-person camera: per-pixel null geodesics integrated on the GPU in ingoing Eddington–Finkelstein
// coordinates from the observer's comoving tetrad (aberration, gravitational + Doppler frequency shift
// included).  The SKY IS SYNTHETIC and the colour mapping of the frequency shift is qualitative:
// "Qualitative visualization — trajectory calculations remain relativistic."
// Equations identical to firstperson_core.js (CPU replica, validated in tests/viewer/test_null_geodesics.mjs).
import * as THREE from 'three';
import { fmt } from './data.js';
import { traceRay, observerFrame } from './firstperson_core.js';

const R_MIN_TRACE = 2e-5;   // geometrized (= 1e-5 r_s): below this, 32-bit GPU floats cannot represent the ray state

const FRAG = `
precision highp float; precision highp int;
uniform vec2 uRes; uniform float uR, uUv, uUr, uE; uniform vec3 uCamF, uCamR, uCamU; uniform float uTanH, uTanV;
uniform int uMaxSteps; uniform float uCh, uRsky;
float fOf(float r) { return 1.0 - 2.0 / r; }
void deriv(vec3 p, vec3 k, out vec3 dp, out vec3 dk) {
  float r = p.y, f = fOf(r), kv = k.x, kr = k.y, kp = k.z;
  dp = k;
  dk = vec3(-(kv*kv)/(r*r) + r*kp*kp, -(f*kv*kv)/(r*r) + (2.0/(r*r))*kv*kr + r*f*kp*kp, -(2.0/r)*kr*kp);
}
float stepSize(vec3 p, vec3 k) { float r = p.y; float rate = abs(k.y)/r + abs(k.z) + abs(k.x)/r + 1e-30; float c = uCh; if (r < 4.0) c *= 0.5; return c / rate; }
void rk4(inout vec3 p, inout vec3 k, float h) {
  vec3 d1p, d1k, d2p, d2k, d3p, d3k, d4p, d4k;
  deriv(p, k, d1p, d1k); deriv(p + 0.5*h*d1p, k + 0.5*h*d1k, d2p, d2k); deriv(p + 0.5*h*d2p, k + 0.5*h*d2k, d3p, d3k); deriv(p + h*d3p, k + h*d3k, d4p, d4k);
  p += h/6.0*(d1p + 2.0*d2p + 2.0*d3p + d4p); k += h/6.0*(d1k + 2.0*d2k + 2.0*d3k + d4k);
}
float hash(vec3 q) { return fract(sin(dot(q, vec3(12.9898, 78.233, 37.719))) * 43758.5453); }
vec3 sky(vec3 dir) {
  // synthetic celestial sphere: black hole at origin, observer on +x, polar axis +z; grid every 15 deg
  float lat = asin(clamp(dir.z, -1.0, 1.0)), lon = atan(dir.y, dir.x);
  float gl = abs(fract(lat / 0.261799 + 0.5) - 0.5), gn = abs(fract(lon / 0.261799 + 0.5) - 0.5);
  float line = smoothstep(0.03, 0.0, gl) + smoothstep(0.03, 0.0, gn);
  vec3 col = vec3(0.02, 0.03, 0.06) + vec3(0.25, 0.35, 0.6) * line;
  vec3 cell = floor(dir * 40.0);
  float h = hash(cell); if (h > 0.985) col += vec3(0.9, 0.9, 1.0) * (h - 0.985) * 50.0;   // stars
  float band = exp(-pow(dir.z / 0.15, 2.0)); col += vec3(0.35, 0.3, 0.25) * band * 0.5;          // 'galactic' band around the pole axis
  float away = smoothstep(0.995, 1.0, dir.x); col += vec3(0.9, 0.7, 0.2) * away;                    // marker: direction away from the hole
  float toward = smoothstep(0.995, 1.0, -dir.x); col += vec3(0.2, 0.9, 0.6) * toward;               // marker: direction of the hole at infinity
  return col;
}
void main() {
  vec2 ndc = (gl_FragCoord.xy / uRes) * 2.0 - 1.0;
  vec3 d = normalize(uCamF + ndc.x * uTanH * uCamR + ndc.y * uTanV * uCamU);   // tetrad components (n, theta, phi)
  float dn = d.x; float dperp = length(d.yz); vec2 tdir = dperp > 1e-9 ? d.yz / dperp : vec2(1.0, 0.0);
  float f0 = fOf(uR); float nn = -f0*uUv*uUv + 2.0*uUv*uE; float N = sqrt(max(nn, 1e-30));
  float nv = uUv / N, nr = uE / N;
  vec3 p = vec3(0.0, uR, 0.0);
  vec3 k = vec3(-uUv + dn*nv, -uUr + dn*nr, dperp / uR);
  float Eph = -(f0*k.x - k.y);                      // Killing energy of the future-directed photon (omega_obs = 1)
  float Lp = uR*uR*k.z; float b2 = (Lp*Lp)/(Eph*Eph);
  int kind = 2;                                     // 0 sky, 1 past-horizon / not modelled, 2 unresolved
  // exact classification from the conserved quantities (see firstperson_core.js classify())
  bool past = (uR < 2.0) ? (Eph <= 0.0) : ((k.y < 0.0) ? (uR <= 3.0 || b2 <= 27.0) : (uR < 3.0 && b2 > 27.0));
  float psiInf = 0.0;
  if (past) { kind = 1; }
  else for (int i = 0; i < 4000; i++) {
    if (i >= uMaxSteps) break;
    float r = p.y;
    if (r > uRsky) { psiInf = p.z + atan(r*k.z, k.y); kind = 0; break; }
    if (r < 1e-6 || p.x < -1e6) break;
    rk4(p, k, stepSize(p, k));
  }
  vec3 col;
  if (kind == 0) {
    // direction on the celestial sphere: outward radial +x, transverse in the (theta -> -z, phi -> +y) plane
    vec3 t3 = normalize(vec3(0.0, tdir.y, -tdir.x));
    vec3 dir = cos(psiInf) * vec3(1.0, 0.0, 0.0) + sin(psiInf) * t3;
    col = sky(dir);
    float g = 1.0 / Eph;                              // frequency ratio; qualitative colour shift below
    float b = clamp(pow(g, 2.0), 0.15, 6.0);
    vec3 tint = g > 1.0 ? mix(vec3(1.0), vec3(0.6, 0.75, 1.0), clamp((g - 1.0) * 0.5, 0.0, 1.0)) : mix(vec3(1.0), vec3(1.0, 0.45, 0.35), clamp((1.0 - g) * 1.5, 0.0, 1.0));
    col *= tint * b;
  } else if (kind == 1) { col = vec3(0.06, 0.0, 0.0); }
  else { col = vec3(0.6, 0.0, 0.6); }
  gl_FragColor = vec4(col, 1.0);
}`;

const VERT = `void main() { gl_Position = vec4(position, 1.0); }`;

export class FirstpersonView {
  constructor(container, data, opts = {}) {
    this.container = container; this.data = data;
    this.yaw = 0; this.pitch = 0; this.fov = 90; this.quality = 0.3; this.dirty = true; this.ready = false; this.lastR = null;
    try { this._init(); this.ready = true; } catch (e) {
      const m = document.createElement('div'); m.className = 'overlay'; m.textContent = 'first-person view unavailable (WebGL failed): ' + e; container.appendChild(m);
    }
  }
  _init() {
    this.renderer = new THREE.WebGLRenderer({ antialias: false, powerPreference: 'low-power' });
    this.renderer.setPixelRatio(1);
    this.container.appendChild(this.renderer.domElement);
    const gl = this.renderer.getContext();
    const dbg = gl.getExtension('WEBGL_debug_renderer_info');
    const rname = dbg ? String(gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL)) : '';
    this.software = /swiftshader|llvmpipe|software/i.test(rname);
    if (this.software) { this.quality = 0.08; }
    this.maxSteps = this.software ? 600 : 900;
    this.scene = new THREE.Scene(); this.camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    this.uniforms = {
      uRes: { value: new THREE.Vector2(1, 1) }, uR: { value: 200 }, uUv: { value: 1 }, uUr: { value: -0.1 }, uE: { value: 1 },
      uCamF: { value: new THREE.Vector3(-1, 0, 0) }, uCamR: { value: new THREE.Vector3(0, 0, 1) }, uCamU: { value: new THREE.Vector3(0, -1, 0) },
      uTanH: { value: 1 }, uTanV: { value: 1 }, uMaxSteps: { value: this.maxSteps }, uCh: { value: 0.05 }, uRsky: { value: 400 },
    };
    const mat = new THREE.ShaderMaterial({ uniforms: this.uniforms, vertexShader: VERT, fragmentShader: FRAG, depthTest: false, depthWrite: false });
    this.scene.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), mat));
    this.target = new THREE.WebGLRenderTarget(64, 64, { minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter });
    // blit
    this.blitScene = new THREE.Scene();
    this.blitMat = new THREE.MeshBasicMaterial({ map: this.target.texture });
    this.blitScene.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), this.blitMat));
    // DOM overlays
    this.banner = document.createElement('div'); this.banner.className = 'overlay'; this.banner.style.cssText += 'top:48px;bottom:auto;max-width:70%;';
    this.container.appendChild(this.banner);
    this.stats = document.createElement('div'); this.stats.className = 'overlay';
    this.container.appendChild(this.stats);
    const ctl = document.createElement('div'); ctl.className = 'overlay'; ctl.style.cssText += 'right:10px;left:auto;bottom:10px;pointer-events:auto;';
    ctl.innerHTML = `<button id="fp-in">look toward the hole</button> <button id="fp-out">look outward</button>
      FOV <input id="fp-fov" type="range" min="40" max="150" value="90" style="width:90px"> quality <select id="fp-q"><option value="0.08">low</option><option value="0.2">medium</option><option value="0.35">high</option></select>
      <div class="note">drag to look around</div>`;
    this.container.appendChild(ctl);
    ctl.querySelector('#fp-in').onclick = () => { this.yaw = 0; this.pitch = 0; this.dirty = true; };
    ctl.querySelector('#fp-out').onclick = () => { this.yaw = Math.PI; this.pitch = 0; this.dirty = true; };
    ctl.querySelector('#fp-fov').oninput = e => { this.fov = parseFloat(e.target.value); this.dirty = true; };
    ctl.querySelector('#fp-q').value = String(this.quality); ctl.querySelector('#fp-q').onchange = e => { this.quality = parseFloat(e.target.value); this.resize(); this.dirty = true; };
    let drag = null;
    const el = this.renderer.domElement;
    el.addEventListener('pointerdown', e => { drag = [e.clientX, e.clientY, this.yaw, this.pitch]; });
    window.addEventListener('pointermove', e => { if (!drag) return; this.yaw = drag[2] + (e.clientX - drag[0]) * 0.005; this.pitch = Math.max(-1.4, Math.min(1.4, drag[3] - (e.clientY - drag[1]) * 0.005)); this.dirty = true; });
    window.addEventListener('pointerup', () => { drag = null; });
    this.resize();
  }
  _cameraAxes() {
    // tetrad components (n outward, theta-hat, phi-hat).  Default forward = -n (toward the hole), up = -theta-hat (north), right = phi-hat.
    const cy = Math.cos(this.yaw), sy = Math.sin(this.yaw), cp = Math.cos(this.pitch), spp = Math.sin(this.pitch);
    const F0 = [-1, 0, 0], R0 = [0, 0, 1], U0 = [0, -1, 0];
    // yaw about up, then pitch about right
    const rot = (v, axis, c, s) => { // Rodrigues
      const d = v[0] * axis[0] + v[1] * axis[1] + v[2] * axis[2];
      const cr = [axis[1] * v[2] - axis[2] * v[1], axis[2] * v[0] - axis[0] * v[2], axis[0] * v[1] - axis[1] * v[0]];
      return [v[0] * c + cr[0] * s + axis[0] * d * (1 - c), v[1] * c + cr[1] * s + axis[1] * d * (1 - c), v[2] * c + cr[2] * s + axis[2] * d * (1 - c)];
    };
    let F = rot(F0, U0, cy, sy), R = rot(R0, U0, cy, sy);
    F = rot(F, R, cp, spp); const U = rot(U0, R, cp, spp);
    return { F, R, U };
  }
  update(smp, state) {
    if (!this.ready || !smp) return;
    const rGeo = 2 * smp.r_over_rs;
    const changed = this.lastR === null || Math.abs(Math.log(rGeo / this.lastR)) > 1e-4;
    if (!changed && !this.dirty) return;
    this.lastR = rGeo; this.dirty = false;
    const traceable = rGeo >= R_MIN_TRACE;
    const rUse = traceable ? rGeo : R_MIN_TRACE;
    // observer state at rUse: from the sample if traceable, else at the tracing limit (labelled)
    let uv = smp.u_v, ur = smp.u_r, E = smp.E_killing ?? 1;
    if (!traceable) { const s2 = this.data.at(Math.log10(rUse / 2)); uv = s2.u_v; ur = s2.u_r; E = s2.E_killing ?? 1; }
    const { F, R, U } = this._cameraAxes();
    const u = this.uniforms;
    u.uR.value = rUse; u.uUv.value = uv; u.uUr.value = ur; u.uE.value = E;
    u.uCamF.value.set(...F); u.uCamR.value.set(...R); u.uCamU.value.set(...U);
    const w = this.target.width, h = this.target.height;
    u.uRes.value.set(w, h);
    u.uTanH.value = Math.tan(this.fov * Math.PI / 360); u.uTanV.value = u.uTanH.value * h / w;
    u.uMaxSteps.value = this.maxSteps;
    this.renderer.setRenderTarget(this.target); this.renderer.render(this.scene, this.camera);
    this.renderer.setRenderTarget(null); this.renderer.render(this.blitScene, this.camera);
    // CPU termination statistics on a coarse grid (same equations as the shader)
    const nx = 16, ny = 10; let sky = 0, past = 0, unres = 0;
    for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
      const px = (i + 0.5) / nx * 2 - 1, py = (j + 0.5) / ny * 2 - 1;
      const d = [F[0] + px * u.uTanH.value * R[0] + py * u.uTanV.value * U[0], F[1] + px * u.uTanH.value * R[1] + py * u.uTanV.value * U[1], F[2] + px * u.uTanH.value * R[2] + py * u.uTanV.value * U[2]];
      const n = Math.hypot(...d); const dn = d[0] / n, dperp = Math.hypot(d[1], d[2]) / n;
      const res = traceRay(rUse, uv, ur, E, dn, dperp, { maxSteps: this.maxSteps });
      if (res.kind === 'sky') sky++; else if (res.kind === 'past') past++; else unres++;
    }
    const tot = nx * ny;
    const inside = rGeo <= 2;
    // exact extent of the exterior sky on the observer's celestial sphere: E_f = E + d_n |u^r|/|n| > 0
    const fr0 = observerFrame(rUse, uv, ur, E);
    const cosMax = -E * Math.sqrt(Math.max(1e-300, -fr0.f * uv * uv + 2 * uv * E)) / Math.max(1e-300, Math.abs(ur));
    const skyCone = inside ? (cosMax <= -1 ? 180 : cosMax >= 1 ? 0 : Math.acos(cosMax) * 180 / Math.PI) : null;
    this.banner.innerHTML = `<b>${this.data.raw.banner_firstperson}</b><br>Per-pixel null geodesics in ingoing Eddington–Finkelstein coordinates from the observer's comoving tetrad; ` +
      `aberration and gravitational/Doppler frequency shift included; colours qualitative; sky synthetic (grid every 15°, gold marker = direction away from the hole, green = towards it at infinity).` +
      (traceable ? '' : `<br><span style="color:#ffb454">Below r = ${fmt.sci(R_MIN_TRACE / 2, 1)} r_s the 32-bit GPU precision cannot represent the ray state: showing the view frozen at r = ${fmt.sci(R_MIN_TRACE / 2, 1)} r_s (LABELLED LIMIT).</span>`);
    this.stats.innerHTML = `r = ${fmt.sci(smp.r_m, 3)} m = ${fmt.sci(smp.r_over_rs, 3)} r_s — ${inside ? 'INSIDE the horizon' : 'outside the horizon'}<br>` +
      `pixels (coarse CPU estimate, same equations): sky ${(100 * sky / tot).toFixed(0)}%, past-horizon / not-modelled region (black) ${(100 * past / tot).toFixed(0)}%, unresolved (magenta) ${(100 * unres / tot).toFixed(0)}%<br>` +
      `look: yaw ${(this.yaw * 180 / Math.PI).toFixed(0)}° (0 = toward the hole, 180 = outward), pitch ${(this.pitch * 180 / Math.PI).toFixed(0)}°, FOV ${this.fov}°, ${this.software ? 'software GL (low quality)' : 'GPU'}` +
      (inside ? `<br>inside r_s the exterior universe (region I) occupies a cone of half-angle ${skyCone.toFixed(1)}° around the OUTWARD direction (rays with positive Killing energy); the rest of the sky is the other horizon / collapsing-matter region — not modelled, shown black` : '');
  }
  resize() {
    if (!this.ready) return;
    const w = this.container.clientWidth || 800, h = this.container.clientHeight || 600;
    this.renderer.setSize(w, h, false);
    this.target.setSize(Math.max(16, Math.round(w * this.quality)), Math.max(16, Math.round(h * this.quality)));
    this.dirty = true;
  }
  setMode() {}
  dispose() { this.renderer?.dispose(); }
}
