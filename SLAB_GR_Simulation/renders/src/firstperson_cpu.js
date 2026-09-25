// First-person camera: double-precision CPU renderer (pure JavaScript; no DOM, no WebGL; importable from Node).
//
// Every pixel: view direction d in the observer's tetrad -> (dn, dperp, azimuth) -> EXACT kind and g from the
// conserved quantities (firstperson_core.js) -> psi_inf from the transfer table (firstperson_table.js) -> sky
// direction cos(psi) n + sin(psi) t (t = azimuth unit vector) -> celestial J2000 direction -> background colour.
// Stars are forward-mapped (firstperson_sky.js starImages) and splatted on top.
// Progressive: levels with block sizes 8, 4, 2, 1 (each level only computes the pixels it adds); `step(budgetMs)`
// returns after the time budget so the page stays responsive.
import { classify } from './firstperson_core.js';
import { gridShade, gColor, qualitativeTint, starImages } from './firstperson_sky.js';

export const KIND_SKY = 0, KIND_PAST = 1, KIND_UNRESOLVED = 2;
const BLOCKS = [8, 4, 2, 1];
const now = () => (typeof performance !== 'undefined' ? performance : Date).now();

export class CpuRenderer {
  constructor() { this.width = 0; this.height = 0; this.params = null; this.done = true; this._starKey = null; this._imgs = []; }

  // params: {width, height, obs, table, cam:{F,R,U,tanH,tanV}, M (celestial frame), background:'stars'|'grid',
  //          layer:'tint'|'gmap', gRange (half-range of log10 g), stars (loadStars()), exposure (mag), startLevel}
  start(params) {
    const { width: W, height: H } = params;
    if (W !== this.width || H !== this.height) {
      this.width = W; this.height = H;
      this.bg = new Uint8ClampedArray(W * H * 4);
      this.rgba = new Uint8ClampedArray(W * H * 4);
      this.kindMap = new Uint8Array(W * H);
      this.star = new Float32Array(W * H * 3);
      for (let i = 3; i < this.bg.length; i += 4) { this.bg[i] = 255; this.rgba[i] = 255; }
    }
    this.params = params;
    this.level = params.startLevel ?? 0;
    this.row = 0;
    this.done = false;
    this.counts = [0, 0, 0];
    this.levelCounts = null;
    this.pixelsDone = 0;
    this._buildStarLayer();
  }

  _buildStarLayer() {
    const P = this.params, W = this.width, H = this.height;
    this.star.fill(0);
    this.starCount = 0;
    if (P.background !== 'stars' || !P.stars) return;
    const key = `${P.table.version}|${P.table.p.length}|${P.obs.r}|${P.obs.E}`;
    if (this._starKey !== key || this._starTable !== P.table) { this._imgs = starImages(P.table, P.stars, P.M); this._starKey = key; this._starTable = P.table; }
    const { F, R, U, tanH, tanV } = P.cam;
    const mLim = 6.5 + (P.exposure ?? 0);
    for (const im of this._imgs) {
      const d = im.d;
      const dF = d[0] * F[0] + d[1] * F[1] + d[2] * F[2];
      if (dF <= 1e-6) continue;
      const px = (d[0] * R[0] + d[1] * R[1] + d[2] * R[2]) / (dF * tanH);
      const py = (d[0] * U[0] + d[1] * U[1] + d[2] * U[2]) / (dF * tanV);
      if (px < -1.05 || px > 1.05 || py < -1.05 || py > 1.05) continue;
      const x = (px + 1) * W / 2 - 0.5, y = (1 - py) * H / 2 - 0.5;
      const s = mLim - im.mObs;
      if (!isFinite(s)) continue;
      let peak, rad;
      if (s > 0.5) { peak = Math.min(1, 0.18 + 0.1 * s); rad = Math.min(5, 0.7 + 0.28 * s); }
      else { peak = 0.2 * Math.pow(10, 0.4 * (s - 0.5)); rad = 0.7; }
      if (peak < 0.004) continue;
      this.starCount++;
      const R2 = Math.ceil(2.5 * rad), inv = 1 / (2 * rad * rad);
      const x0 = Math.max(0, Math.floor(x - R2)), x1 = Math.min(W - 1, Math.ceil(x + R2));
      const y0 = Math.max(0, Math.floor(y - R2)), y1 = Math.min(H - 1, Math.ceil(y + R2));
      for (let yy = y0; yy <= y1; yy++) for (let xx = x0; xx <= x1; xx++) {
        const w = peak * Math.exp(-((xx - x) * (xx - x) + (yy - y) * (yy - y)) * inv);
        const o = 3 * (yy * W + xx);
        this.star[o] += w * im.r; this.star[o + 1] += w * im.gg; this.star[o + 2] += w * im.b;
      }
    }
  }

  // Shade one pixel (x, y); returns the kind and writes RGB (0..1) into col.
  shadePixel(x, y, col) {
    const P = this.params, W = this.width, H = this.height, obs = P.obs, T = P.table;
    const { F, R, U, tanH, tanV } = P.cam;
    const px = ((x + 0.5) / W) * 2 - 1, py = 1 - ((y + 0.5) / H) * 2;
    let d0 = F[0] + px * tanH * R[0] + py * tanV * U[0];
    let d1 = F[1] + px * tanH * R[1] + py * tanV * U[1];
    let d2 = F[2] + px * tanH * R[2] + py * tanV * U[2];
    const nrm = 1 / Math.hypot(d0, d1, d2); d0 *= nrm; d1 *= nrm; d2 *= nrm;
    const dn = d0, dperp = Math.hypot(d1, d2);
    const Eph = obs.E + dn * obs.a, outward = obs.a + obs.E * dn > 0;
    const b = obs.r * dperp / Eph;
    const kind = classify(obs.r, outward ? 1 : -1, Eph, b * b);
    if (kind === 'past') {
      if (P.layer === 'gmap') { const h = ((x + y) & 7) < 2 ? 0.2 : 0.1; col[0] = h; col[1] = h; col[2] = h; }   // hatched grey
      else { col[0] = 0.075; col[1] = 0.012; col[2] = 0.012; }                                               // dark red
      return KIND_PAST;
    }
    const param = T.param === 'alpha' ? Math.atan2(dn, dperp) : b;
    const L = T.lookup(param, this._lk || (this._lk = {}));
    if (!L.ok) { col[0] = 0.6; col[1] = 0; col[2] = 0.6; return KIND_UNRESOLVED; }
    const psi = L.psi, cp = Math.cos(psi), sp = Math.sin(psi);
    const t1 = dperp > 0 ? d1 / dperp : 1, t2 = dperp > 0 ? d2 / dperp : 0;
    const M = P.M;
    const s0 = cp, s1 = sp * t1, s2 = sp * t2;
    const S = this._S || (this._S = [0, 0, 0]);
    S[0] = M[0] * s0 + M[3] * s1 + M[6] * s2; S[1] = M[1] * s0 + M[4] * s1 + M[7] * s2; S[2] = M[2] * s0 + M[5] * s1 + M[8] * s2;
    // angular size of this pixel on the sky (for grid anti-aliasing)
    const pixAng = 2 * tanH / W * dF2(px, py, tanH, tanV);
    const dPdA = T.param === 'alpha' ? 1 : obs.r * Math.abs(obs.E * dn + obs.a) / (Eph * Eph);
    const stretch = Math.max(Math.abs(L.slope) * dPdA, Math.abs(sp) / Math.max(dperp, 1e-300));
    const pixSky = pixAng * stretch;
    const g = 1 / Eph;
    const gs = this._gs || (this._gs = [0, 0]);
    if (P.layer === 'gmap') {
      gColor(Math.log10(g), P.gRange, col);
      gridShade(S, 30, pixSky, gs);
      const I = 0.35 * gs[0];
      col[0] = col[0] * 0.85 + I; col[1] = col[1] * 0.85 + I; col[2] = col[2] * 0.85 + I;
    } else if (P.background === 'grid') {
      gridShade(S, 15, pixSky, gs);
      const tint = qualitativeTint(g, this._tint || (this._tint = [1, 1, 1]));
      col[0] = (0.02 + 0.4 * gs[0]) * tint[0]; col[1] = (0.03 + 0.55 * gs[0]) * tint[1]; col[2] = (0.06 + 0.85 * gs[0]) * tint[2];
    } else {
      gridShade(S, 30, pixSky, gs);
      const tint = qualitativeTint(g, this._tint || (this._tint = [1, 1, 1]));
      const I = 0.16 * gs[0];
      col[0] = (0.004 + 0.5 * I) * tint[0]; col[1] = (0.006 + 0.65 * I) * tint[1]; col[2] = (0.014 + I) * tint[2];
    }
    if (gs[1] === 1) { col[0] = 0.2; col[1] = 0.9; col[2] = 0.6; }        // hole direction marker (green)
    else if (gs[1] === 2) { col[0] = 0.95; col[1] = 0.75; col[2] = 0.2; } // anti-hole direction marker (gold)
    return KIND_SKY;
  }

  // Progressive work for at most budgetMs.  Returns true if pixels changed.
  step(budgetMs = 20) {
    if (this.done) return false;
    const t0 = now(), W = this.width, H = this.height, bg = this.bg, km = this.kindMap;
    const col = [0, 0, 0];
    let changed = false;
    while (!this.done) {
      const B = BLOCKS[this.level], prevB = this.level > 0 && this.level > (this.params.startLevel ?? 0) ? BLOCKS[this.level - 1] : 0;
      const y = this.row;
      if (y % B === 0) {
        for (let x = 0; x < W; x += B) {
          if (prevB && x % prevB === 0 && y % prevB === 0) continue;
          const kind = this.shadePixel(x, y, col);
          const r = Math.min(255, 255 * col[0]) | 0, g = Math.min(255, 255 * col[1]) | 0, b = Math.min(255, 255 * col[2]) | 0;
          const ye = Math.min(H, y + B), xe = Math.min(W, x + B);
          for (let yy = y; yy < ye; yy++) for (let xx = x; xx < xe; xx++) { const o = yy * W + xx; bg[4 * o] = r; bg[4 * o + 1] = g; bg[4 * o + 2] = b; km[o] = kind; }
        }
        changed = true;
      }
      this.row += 1;
      if (this.row >= H) {
        this.row = 0;
        this.levelCounts = this._count();
        this.level++;
        if (this.level >= BLOCKS.length || (this.params.maxLevel !== undefined && this.level > this.params.maxLevel)) this.done = true;
      }
      if ((this.row & 7) === 0 && now() - t0 > budgetMs) break;
    }
    if (changed) this.composite();
    return changed;
  }

  renderAll() { while (!this.done) this.step(Infinity); return this; }

  _count() {
    const c = [0, 0, 0], km = this.kindMap;
    for (let i = 0; i < km.length; i++) c[km[i]]++;
    return c;
  }

  composite() {
    const bg = this.bg, st = this.star, out = this.rgba, N = this.width * this.height;
    for (let i = 0; i < N; i++) {
      out[4 * i] = bg[4 * i] + 255 * st[3 * i];
      out[4 * i + 1] = bg[4 * i + 1] + 255 * st[3 * i + 1];
      out[4 * i + 2] = bg[4 * i + 2] + 255 * st[3 * i + 2];
    }
  }
}

// 1/|d|^2-type factor: the pixel's angular size shrinks off-axis like 1/(1 + px^2 tanH^2 + py^2 tanV^2)
function dF2(px, py, tanH, tanV) { return 1 / (1 + px * px * tanH * tanH + py * py * tanV * tanV); }

// Camera axes (tetrad components: 0 = n outward radial, 1 = theta-hat, 2 = phi-hat) for yaw/pitch.
// Default (yaw = pitch = 0): forward = -n (towards the hole), up = -theta-hat, right = phi-hat (right-handed).
export function cameraAxes(yaw, pitch) {
  const cy = Math.cos(yaw), sy = Math.sin(yaw), cp = Math.cos(pitch), spp = Math.sin(pitch);
  const F0 = [-1, 0, 0], R0 = [0, 0, 1], U0 = [0, -1, 0];
  const rot = (v, axis, c, s) => {   // Rodrigues
    const d = v[0] * axis[0] + v[1] * axis[1] + v[2] * axis[2];
    const cr = [axis[1] * v[2] - axis[2] * v[1], axis[2] * v[0] - axis[0] * v[2], axis[0] * v[1] - axis[1] * v[0]];
    return [v[0] * c + cr[0] * s + axis[0] * d * (1 - c), v[1] * c + cr[1] * s + axis[1] * d * (1 - c), v[2] * c + cr[2] * s + axis[2] * d * (1 - c)];
  };
  let F = rot(F0, U0, cy, sy), R = rot(R0, U0, cy, sy);
  F = rot(F, R, cp, spp); const U = rot(U0, R, cp, spp);
  return { F, R, U };
}
