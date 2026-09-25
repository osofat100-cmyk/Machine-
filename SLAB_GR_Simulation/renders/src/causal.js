// Causal-structure view: Kruskal–Szekeres diagram and compactified (Penrose-type) diagram,
// drawn on two synchronized 2D canvases.  No physics is integrated here: the observer's
// worldline is the precomputed radial geodesic (columns kruskal_T/X, penrose_T/X of the data
// file); the coordinate curves (r = const, t = const, horizon, singularity) are the exact
// analytic Kruskal relations for the Schwarzschild metric in geometrized units G = c = M = 1
// (r_s = 2).  Every visual simplification is labelled on screen.
import { fmt } from './data.js';

const M = 1;                 // geometrized mass; r_s = 2M = 2
const RS = 2 * M;
const KWIN = 2.6;            // Kruskal window: |T|, |X| <= KWIN
const PI = Math.PI, PI2 = PI / 2, PI4 = PI / 4;

const COL = {
  bg: '#0b0e14', panel: '#10151f', axis: '#3a4560', text: '#d8dee9', dim: '#8892a6',
  horizon: '#7ab7ff', sing: '#ff6b6b', rconst: '#6b7ea3', tconst: '#4b8a76', world: '#f0f0f6',
  regionI: 'rgba(122,183,255,0.06)', regionII: 'rgba(255,107,107,0.08)', regionX: 'rgba(0,0,0,0.35)',
  regime: ['#6ee7a0', '#ffb454', '#ff6b6b', '#d98cff'], accent: '#7ab7ff',
};
const REGIME_NAMES = ['CLASSICAL GR — VALIDATED', 'CLASSICAL GR — EXTREME CURVATURE', 'PLANCK-CURVATURE BOUNDARY', 'SPECULATIVE QUANTUM MODEL'];
const FONT = (px, weight = 400) => `${weight} ${px}px system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`;

// UV = c(r): the Kruskal relation T^2 - X^2 = (1 - r/2M) exp(r/2M)
const cOfR = r => (1 - r / (2 * M)) * Math.exp(r / (2 * M));
const isNum = v => typeof v === 'number' && Number.isFinite(v);

// Liang–Barsky clipping of segment (x0,y0)-(x1,y1) to the box [xmin,xmax]×[ymin,ymax]; returns null if fully outside.
function clipSegment(x0, y0, x1, y1, xmin, xmax, ymin, ymax) {
  let t0 = 0, t1 = 1;
  const dx = x1 - x0, dy = y1 - y0;
  const p = [-dx, dx, -dy, dy], q = [x0 - xmin, xmax - x0, y0 - ymin, ymax - y0];
  for (let i = 0; i < 4; i++) {
    if (p[i] === 0) { if (q[i] < 0) return null; continue; }
    const r = q[i] / p[i];
    if (p[i] < 0) { if (r > t1) return null; if (r > t0) t0 = r; }
    else { if (r < t0) return null; if (r < t1) t1 = r; }
  }
  return [x0 + t0 * dx, y0 + t0 * dy, x0 + t1 * dx, y0 + t1 * dy];
}

// compactified coordinates (T~, X~) of the Kruskal point (U, V)
function compactify(U, V) { const Ut = Math.atan(U), Vt = Math.atan(V); return [(Vt - Ut) / 2, (Vt + Ut) / 2]; }   // [Xt, Tt]

export class CausalView {
  constructor(container, data, opts = {}) {
    this.container = container; this.data = data; this.opts = opts;
    this.mode = 'both';               // both | kruskal | penrose
    this.sample = null; this.state = null;
    this.ok = false; this._errLogged = false;
    try {
      this._buildDom();
      this._prepareWorldlines();
      this.ok = true;
    } catch (e) {
      this._fail('Causal view could not be initialised: ' + (e && e.message ? e.message : String(e)));
    }
  }

  // ---------------------------------------------------------------- DOM
  _buildDom() {
    const root = document.createElement('div');
    root.style.cssText = 'position:absolute;inset:0;display:flex;flex-direction:column;background:' + COL.bg + ';overflow:hidden;';
    this.root = root;
    const panels = document.createElement('div');
    panels.style.cssText = 'flex:1 1 auto;display:flex;flex-direction:row;min-height:0;gap:2px;padding:2px;';
    this.panels = panels;
    this.kruskal = this._makePanel('kruskal');
    this.penrose = this._makePanel('penrose');
    panels.appendChild(this.kruskal.wrap); panels.appendChild(this.penrose.wrap);
    const cap = document.createElement('div');
    cap.style.cssText = 'flex:0 0 auto;background:#131824;border-bottom:1px solid #222a3a;padding:6px 10px;font-size:12px;line-height:1.35;color:' + COL.text +
      ';display:grid;grid-template-columns:auto 1fr;gap:2px 14px;max-height:34%;overflow:auto;';
    this.caption = cap;
    root.appendChild(cap);          // caption panel on top (the app's Planck banner overlays the bottom of the view)
    root.appendChild(panels);
    this.container.appendChild(root);
    try {
      if (typeof ResizeObserver !== 'undefined') { this.ro = new ResizeObserver(() => this.resize()); this.ro.observe(root); }
    } catch (e) { this.ro = null; }
  }
  _makePanel(name) {
    const wrap = document.createElement('div');
    wrap.style.cssText = 'flex:1 1 0;min-width:0;min-height:0;position:relative;background:' + COL.panel + ';';
    const canvas = document.createElement('canvas');
    canvas.style.cssText = 'position:absolute;left:0;top:0;width:100%;height:100%;display:block;';
    wrap.appendChild(canvas);
    let ctx = null;
    try { ctx = canvas.getContext('2d'); } catch (e) { ctx = null; }
    if (!ctx) {
      const msg = document.createElement('div');
      msg.style.cssText = 'position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:' + COL.sing + ';padding:12px;text-align:center;';
      msg.textContent = `2D canvas unavailable: the ${name} diagram cannot be drawn in this browser.`;
      wrap.appendChild(msg);
    }
    return { name, wrap, canvas, ctx, w: 0, h: 0, dpr: 1 };
  }
  _fail(msg) {
    try {
      const el = document.createElement('div');
      el.style.cssText = 'position:absolute;left:10px;top:10px;z-index:3;color:' + COL.sing + ';background:rgba(0,0,0,.6);padding:8px;border-radius:4px;';
      el.textContent = msg;
      this.container.appendChild(el);
    } catch (e) { /* nothing more we can do */ }
  }

  // ---------------------------------------------------------------- data
  _prepareWorldlines() {
    const s = this.data.s, N = this.data.N;
    const kx = s.kruskal_X || [], kt = s.kruskal_T || [], px = s.penrose_X || [], pt = s.penrose_T || [];
    // list of polylines (broken at null / non-finite / 'inf' entries)
    const build = (X, T) => {
      const lines = []; let cur = null; let skipped = 0;
      for (let i = 0; i < N; i++) {
        const x = X[i], t = T[i];
        if (isNum(x) && isNum(t)) { if (!cur) { cur = []; lines.push(cur); } cur.push(x, t); }
        else { cur = null; skipped++; }
      }
      return { lines, skipped };
    };
    this.wlK = build(kx, kt);
    this.wlP = build(px, pt);
  }

  // ---------------------------------------------------------------- public interface
  update(sample, state) {
    this.sample = sample || null; this.state = state || null;
    if (!this.ok) return;
    try { this._draw(); } catch (e) { this._logOnce(e); }
  }
  resize() {
    if (!this.ok) return;
    try {
      const W = this.root.clientWidth, H = this.root.clientHeight;
      if (W === 0 || H === 0) return;   // hidden (display:none): nothing to lay out
      const stacked = this.mode === 'both' && (W < 820 || W < 1.1 * H);
      this.panels.style.flexDirection = stacked ? 'column' : 'row';
      this.kruskal.wrap.style.display = (this.mode === 'penrose') ? 'none' : '';
      this.penrose.wrap.style.display = (this.mode === 'kruskal') ? 'none' : '';
      for (const p of [this.kruskal, this.penrose]) {
        const w = p.wrap.clientWidth, h = p.wrap.clientHeight;
        const dpr = Math.min(2, Math.max(1, window.devicePixelRatio || 1));
        p.w = w; p.h = h; p.dpr = dpr;
        if (p.canvas.width !== Math.round(w * dpr) || p.canvas.height !== Math.round(h * dpr)) {
          p.canvas.width = Math.round(w * dpr); p.canvas.height = Math.round(h * dpr);
        }
      }
      this._draw();
    } catch (e) { this._logOnce(e); }
  }
  setMode(mode) {
    this.mode = (mode === 'kruskal' || mode === 'penrose') ? mode : 'both';
    this.resize();
  }
  dispose() {
    try { if (this.ro) this.ro.disconnect(); } catch (e) { /* ignore */ }
    try { if (this.root && this.root.parentNode) this.root.parentNode.removeChild(this.root); } catch (e) { /* ignore */ }
    this.ok = false;
  }
  _logOnce(e) {
    if (this._errLogged) return; this._errLogged = true;
    try { console.warn('CausalView draw problem (suppressed further):', e); } catch (_) { /* ignore */ }
    this._fail('Causal view: drawing problem — ' + (e && e.message ? e.message : String(e)));
  }

  // ---------------------------------------------------------------- drawing helpers
  _regimeIndex() {
    const s = this.sample;
    if (this.state && this.state.speculative) return 3;
    const c = s && isNum(s.regime_code) ? Math.round(s.regime_code) : 0;
    return Math.max(0, Math.min(3, c));
  }
  _draw() {
    if (!this.ok) return;
    if (this.kruskal.w === 0 && this.penrose.w === 0) return;
    if (this.mode !== 'penrose') this._drawKruskal(this.kruskal);
    if (this.mode !== 'kruskal') this._drawPenrose(this.penrose);
    this._drawCaption();
  }
  _wrap(ctx, text, maxW) {
    const words = text.split(' '), lines = []; let cur = '';
    for (const w of words) {
      const t = cur ? cur + ' ' + w : w;
      if (ctx.measureText(t).width > maxW && cur) { lines.push(cur); cur = w; } else cur = t;
    }
    if (cur) lines.push(cur);
    return lines;
  }
  // common frame: title, subtitle, status line, wrapped footer notes; returns the world→pixel mapping (equal scale in both axes)
  _frame(p, title, subtitle, status, statusColor, worldBox, notes) {
    const { ctx, w, h, dpr } = p;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = COL.panel; ctx.fillRect(0, 0, w, h);
    ctx.textBaseline = 'alphabetic'; ctx.textAlign = 'left';
    ctx.fillStyle = COL.text; ctx.font = FONT(13, 600); ctx.fillText(title, 10, 17);
    ctx.fillStyle = COL.dim; ctx.font = FONT(11); ctx.fillText(subtitle, 10, 31);
    ctx.fillStyle = statusColor; ctx.font = FONT(11, 600);
    const stLines = this._wrap(ctx, status, w - 20).slice(0, 2);
    stLines.forEach((n, i) => ctx.fillText(n, 10, 45 + 13 * i));
    const compact = Math.min(w - 60, h - 40 - 13 * stLines.length - 50) < 380;   // small plot: fewer labels, shorter notes
    ctx.fillStyle = COL.dim; ctx.font = FONT(10.5);
    const lines = [];
    for (const n of (compact ? notes.slice(0, 1) : notes)) lines.push(...this._wrap(ctx, n, w - 20));
    const noteH = 13 * lines.length + 6;
    lines.forEach((n, i) => ctx.fillText(n, 10, h - noteH + 12 + 13 * i));
    const top = 40 + 13 * stLines.length, bottom = noteH + 4, side = compact ? 8 : 30;
    const availW = Math.max(10, w - 2 * side), availH = Math.max(10, h - top - bottom);
    const [xmin, xmax, ymin, ymax] = worldBox;
    const scale = Math.min(availW / (xmax - xmin), availH / (ymax - ymin));   // equal scale: 45° stays 45°
    const pw = (xmax - xmin) * scale, ph = (ymax - ymin) * scale;
    const ox = side + (availW - pw) / 2, oy = top + (availH - ph) / 2;
    return { x: X => ox + (X - xmin) * scale, y: T => oy + (ymax - T) * scale, scale, ox, oy, pw, ph, xmin, xmax, ymin, ymax, compact };
  }
  _polyline(ctx, m, pts, xmin, xmax, ymin, ymax) {
    // pts: flat [x0, y0, x1, y1, ...] in world coords; clipped segment by segment to the world box
    ctx.beginPath();
    let open = false, lx = NaN, ly = NaN;
    for (let i = 2; i < pts.length; i += 2) {
      const seg = clipSegment(pts[i - 2], pts[i - 1], pts[i], pts[i + 1], xmin, xmax, ymin, ymax);
      if (!seg) { open = false; continue; }
      const [a, b, c, d] = seg;
      if (!open || a !== lx || b !== ly) ctx.moveTo(m.x(a), m.y(b));
      ctx.lineTo(m.x(c), m.y(d)); open = true; lx = c; ly = d;
    }
    ctx.stroke();
  }
  // text with a dark backing box; opts.angle rotates about (x, y)
  _label(ctx, text, x, y, color, opts = {}) {
    ctx.save();
    ctx.translate(x, y); if (opts.angle) ctx.rotate(opts.angle);
    ctx.font = opts.font || FONT(10.5);
    ctx.textAlign = opts.align || 'left';
    const wdt = ctx.measureText(text).width, hgt = opts.size || 11;
    const dx = opts.align === 'right' ? -wdt : (opts.align === 'center' ? -wdt / 2 : 0);
    ctx.fillStyle = 'rgba(12,16,24,0.8)';
    ctx.fillRect(dx - 2, -hgt + 1, wdt + 4, hgt + 3);
    ctx.fillStyle = color; ctx.fillText(text, 0, 0);
    ctx.restore();
  }
  _cone(ctx, m, X, T, len, color) {
    // future light cone: two 45° segments upward from (X, T); null directions are exactly ±45° in both diagrams
    ctx.strokeStyle = color; ctx.lineWidth = 1.5; ctx.setLineDash([]);
    ctx.beginPath();
    ctx.moveTo(m.x(X - len), m.y(T + len)); ctx.lineTo(m.x(X), m.y(T)); ctx.lineTo(m.x(X + len), m.y(T + len));
    ctx.stroke();
    ctx.globalAlpha = 0.22; ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(m.x(X - len), m.y(T + len)); ctx.lineTo(m.x(X), m.y(T)); ctx.lineTo(m.x(X + len), m.y(T + len)); ctx.closePath();
    ctx.fill(); ctx.globalAlpha = 1;
  }
  _currentPoint(ctx, m, X, T, color) {
    ctx.fillStyle = color; ctx.strokeStyle = '#fff'; ctx.lineWidth = 1.2;
    ctx.beginPath(); ctx.arc(m.x(X), m.y(T), 4.5, 0, 2 * PI); ctx.fill(); ctx.stroke();
  }
  _worldline(ctx, m, wl, box) {
    ctx.lineWidth = 2; ctx.setLineDash([]); ctx.strokeStyle = COL.world;
    for (const ln of wl.lines) this._polyline(ctx, m, ln, box[0], box[1], box[2], box[3]);
  }

  // ---------------------------------------------------------------- Kruskal–Szekeres
  _drawKruskal(p) {
    if (!p.ctx || p.w === 0) return;
    const ctx = p.ctx, s = this.sample;
    const box = [-KWIN, KWIN, -KWIN, KWIN];
    const reg = this._regimeIndex(), col = COL.regime[reg];
    const X = s ? s.kruskal_X : null, T = s ? s.kruskal_T : null;
    let status, onChart = false;
    if (!isNum(X) || !isNum(T)) status = 'observer: Kruskal coordinates undefined (exp overflow) · ' + REGIME_NAMES[reg];
    else if (Math.abs(X) > KWIN || Math.abs(T) > KWIN) status = `observer off-chart: X = ${fmt.sci(X, 3)}, T = ${fmt.sci(T, 3)} (early exterior: exponentially large coordinates) · ${REGIME_NAMES[reg]}`;
    else { onChart = true; status = `observer: X = ${X.toFixed(3)}, T = ${T.toFixed(3)} · ${REGIME_NAMES[reg]}`; }
    const notes = [
      'Exact Kruskal map of the (t, r) plane of Schwarzschild; angular directions suppressed (each point is a 2-sphere). ' +
      'Light cones are always at 45° in these coordinates — this is the point of the diagram. White: precomputed infall; wedge: future light cone.',
      'The worldline is not integrated in the browser. ' +
      'Regions III/IV (maximal extension) are not covered by the ingoing EF chart of the simulation. ' +
      'Time origin: horizon crossing at V = 1 (T = X = 1/2); early exterior points have exponentially large X.' +
      (this.wlK.skipped ? ` ${this.wlK.skipped} samples without finite Kruskal coordinates skipped.` : ''),
    ];
    const m = this._frame(p, 'Kruskal–Szekeres diagram (T vertical, X horizontal)', `G = c = M = 1, r_s = 2M; window |T|, |X| ≤ ${KWIN}`, status, col, box, notes);
    ctx.save();
    ctx.beginPath(); ctx.rect(m.ox, m.oy, m.pw, m.ph); ctx.clip();
    ctx.fillStyle = COL.bg; ctx.fillRect(m.ox, m.oy, m.pw, m.ph);
    // region tints: I (X > |T|), II (T > |X|), III/IV darker
    const C = m.x(0), R = m.y(0), L = m.scale * KWIN;
    ctx.fillStyle = COL.regionX; ctx.fillRect(m.ox, m.oy, m.pw, m.ph);
    ctx.fillStyle = COL.regionI; ctx.beginPath(); ctx.moveTo(C, R); ctx.lineTo(C + L, R - L); ctx.lineTo(C + L, R + L); ctx.closePath(); ctx.fill();
    ctx.fillStyle = COL.regionII; ctx.beginPath(); ctx.moveTo(C, R); ctx.lineTo(C - L, R - L); ctx.lineTo(C + L, R - L); ctx.closePath(); ctx.fill();
    // axes + ticks
    ctx.strokeStyle = COL.axis; ctx.lineWidth = 1; ctx.setLineDash([]);
    ctx.beginPath(); ctx.moveTo(m.x(-KWIN), R); ctx.lineTo(m.x(KWIN), R); ctx.moveTo(C, m.y(-KWIN)); ctx.lineTo(C, m.y(KWIN)); ctx.stroke();
    ctx.fillStyle = COL.dim; ctx.font = FONT(10); ctx.textAlign = 'center';
    for (const v of [-2, -1, 1, 2]) {
      ctx.beginPath(); ctx.moveTo(m.x(v), R - 3); ctx.lineTo(m.x(v), R + 3); ctx.moveTo(C - 3, m.y(v)); ctx.lineTo(C + 3, m.y(v)); ctx.stroke();
      ctx.fillText(String(v), m.x(v), R + 13); ctx.fillText(String(v), C + 12, m.y(v) + 4);
    }
    ctx.fillText('X', m.x(KWIN) - 10, R - 6); ctx.fillText('T', C + 12, m.y(KWIN) + 14);

    // t = const lines through the origin: T/X = tanh(t/4M) in I (and X/T = tanh(t/4M) in II)
    const tList = [-8, -3, -1, 1, 3, 8];
    ctx.strokeStyle = COL.tconst; ctx.lineWidth = 0.8; ctx.setLineDash([3, 4]);
    for (const t of tList) {
      const k = Math.tanh(t / (4 * M));
      ctx.beginPath(); ctx.moveTo(C, R); ctx.lineTo(m.x(KWIN), m.y(k * KWIN)); ctx.moveTo(C, R); ctx.lineTo(m.x(k * KWIN), m.y(KWIN)); ctx.stroke();
    }
    ctx.setLineDash([]);
    if (!m.compact) for (const t of tList) {
      const k = Math.tanh(t / (4 * M));
      this._label(ctx, `t = ${t > 0 ? '+' : '−'}${Math.abs(t)}M`, m.x(KWIN) - 4, m.y(k * KWIN) + (t > 0 ? 11 : -3), COL.tconst, { align: 'right', font: FONT(9.5) });
    }

    // r = const hyperbolae (exact): T² − X² = c(r) = (1 − r/2M) e^{r/2M}
    const rList = [0.3, 0.6, 0.8, 1.25, 1.5, 2, 3];
    const outside = [];
    ctx.strokeStyle = COL.rconst; ctx.lineWidth = 1; ctx.setLineDash([]);
    const NPT = 160;
    for (const rr of rList) {
      const c = cOfR(rr * RS), pts = [];
      if (c > 0) {          // interior (region II): T = +sqrt(c + X²)
        for (let i = 0; i <= NPT; i++) { const x = -KWIN + 2 * KWIN * i / NPT; pts.push(x, Math.sqrt(c + x * x)); }
      } else {              // exterior (region I): X = +sqrt(-c + T²)
        const X0 = Math.sqrt(-c);
        if (X0 > KWIN) { outside.push(`${rr} r_s (X₀ = ${X0.toFixed(2)})`); continue; }
        for (let i = 0; i <= NPT; i++) { const t = -KWIN + 2 * KWIN * i / NPT; pts.push(Math.sqrt(-c + t * t), t); }
      }
      this._polyline(ctx, m, pts, -KWIN, KWIN, -KWIN, KWIN);
    }
    // labels for r = const, just below each curve, staggered in X (the interior curves crowd towards r = 0)
    if (!m.compact) for (const [rr, x] of [[0.3, 0.0], [0.6, -1.3], [0.8, 0.75]]) {
      const c = cOfR(rr * RS), t = Math.sqrt(c + x * x);
      this._label(ctx, `r = ${rr} r_s`, m.x(x), m.y(t) + 11, COL.rconst, { align: 'center', font: FONT(9.5) });
    }
    if (!m.compact) for (const [rr, t] of [[1.25, -0.5], [1.5, -1.25]]) {
      const c = cOfR(rr * RS), x = Math.sqrt(-c + t * t);
      this._label(ctx, `r = ${rr} r_s`, m.x(x) + 4, m.y(t) + 4, COL.rconst, { align: 'left', font: FONT(9.5) });
    }
    // horizon r = r_s: T = ±X
    ctx.strokeStyle = COL.horizon; ctx.lineWidth = 1.4;
    ctx.beginPath(); ctx.moveTo(m.x(-KWIN), m.y(-KWIN)); ctx.lineTo(m.x(KWIN), m.y(KWIN)); ctx.moveTo(m.x(-KWIN), m.y(KWIN)); ctx.lineTo(m.x(KWIN), m.y(-KWIN)); ctx.stroke();
    this._label(ctx, m.compact ? 'r = r_s (event horizon)' : 'r = r_s (event horizon), T = +X', m.x(1.45), m.y(1.45) + 12, COL.horizon, { align: 'center', angle: -PI4, font: FONT(10, 600) });
    if (!m.compact) this._label(ctx, 'T = −X', m.x(-1.6), m.y(1.6) + 12, COL.horizon, { align: 'center', angle: PI4, font: FONT(9.5) });
    // future singularity r = 0: T = +sqrt(1 + X²)  (bold)
    ctx.strokeStyle = COL.sing; ctx.lineWidth = 3;
    { const pts = []; for (let i = 0; i <= NPT; i++) { const x = -KWIN + 2 * KWIN * i / NPT; pts.push(x, Math.sqrt(1 + x * x)); } this._polyline(ctx, m, pts, -KWIN, KWIN, -KWIN, KWIN); }
    if (m.compact) {
      this._label(ctx, 'r = 0 (classical singularity)', m.x(0), m.y(1.0) - 21, COL.sing, { align: 'center', font: FONT(10, 600) });
      this._label(ctx, 'GR invalid before this: r_QG', m.x(0), m.y(1.0) - 8, COL.sing, { align: 'center', font: FONT(10, 600) });
    } else this._label(ctx, 'r = 0 (classical singularity) — GR invalid before this: r_QG', m.x(0), m.y(1.0) - 8, COL.sing, { align: 'center', font: FONT(10.5, 600) });
    // region labels
    this._label(ctx, m.compact ? 'I (exterior)' : 'I  (exterior, X > |T|)', m.x(1.6), m.y(-0.35), COL.text, { align: 'center', font: FONT(12, 600) });
    this._label(ctx, m.compact ? 'II (interior)' : 'II  (black-hole interior, T > |X|)', m.x(0), m.y(0.4), COL.text, { align: 'center', font: FONT(12, 600) });
    this._label(ctx, 'III  (not covered)', m.x(-1.55), m.y(-0.35), COL.dim, { align: 'center', font: FONT(11) });
    this._label(ctx, m.compact ? 'IV (not covered)' : 'IV  (white-hole region, not covered)', m.x(0), m.y(-1.1), COL.dim, { align: 'center', font: FONT(11) });
    if (!m.compact) this._label(ctx, 'dashed: t = const, T/X = tanh(t/4M)', m.x(-KWIN) + 4, m.y(-KWIN) - 18, COL.tconst, { font: FONT(9.5) });
    if (outside.length && !m.compact) this._label(ctx, `outside this window: r = ${outside.join(', ')}`, m.x(-KWIN) + 4, m.y(-KWIN) - 5, COL.rconst, { font: FONT(9.5) });

    // observer worldline (precomputed radial geodesic) and current point with its future light cone
    this._worldline(ctx, m, this.wlK, box);
    if (onChart) { this._cone(ctx, m, X, T, 0.42, col); this._currentPoint(ctx, m, X, T, col); }
    ctx.restore();
  }

  // ---------------------------------------------------------------- compactified (Penrose-type)
  _drawPenrose(p) {
    if (!p.ctx || p.w === 0) return;
    const ctx = p.ctx, s = this.sample;
    const padX = 0.2, padT = 0.2;
    const box = [-PI4 - padX, PI2 + padX, -PI4 - padT, PI4 + padT];    // X~ range, T~ range
    const reg = this._regimeIndex(), col = COL.regime[reg];
    const X = s ? s.penrose_X : null, T = s ? s.penrose_T : null;
    const onChart = isNum(X) && isNum(T);
    const status = onChart ? `observer: X̃ = ${X.toFixed(3)}, T̃ = ${T.toFixed(3)} · ${REGIME_NAMES[reg]} · synchronized with the Kruskal diagram`
      : 'observer: compactified coordinates undefined (exp overflow) · ' + REGIME_NAMES[reg];
    const notes = [
      'Ũ = atan U, Ṽ = atan V, T̃ = (Ṽ + Ũ)/2, X̃ = (Ṽ − Ũ)/2: conformal compactification of Kruskal; only the region covered by the ' +
      'ingoing EF chart (I ∪ II, V > 0) is drawn. Light cones are always at 45° — this is the point of the diagram.',
      'Angular directions suppressed (each point is a 2-sphere). White line: precomputed radial infall; r_QG (end of the validated run) ' +
      'is indistinguishable from r = 0 at this resolution.' + (this.wlP.skipped ? ` ${this.wlP.skipped} samples without finite coordinates skipped.` : ''),
    ];
    const m = this._frame(p, 'Compactified (Penrose-type) diagram (T̃ vertical, X̃ horizontal)', 'Schwarzschild, regions I and II (ingoing Eddington–Finkelstein chart)', status, col, box, notes);
    ctx.save();
    ctx.beginPath(); ctx.rect(m.ox, m.oy, m.pw, m.ph); ctx.clip();
    ctx.fillStyle = COL.bg; ctx.fillRect(m.ox, m.oy, m.pw, m.ph);
    // covered region: i⁻ (−π/4, π/4) → i⁰ (0, π/2) → i⁺ (π/4, π/4) → left end of the singularity (π/4, −π/4) → back along V = 0
    const P = (Tt, Xt) => [m.x(Xt), m.y(Tt)];
    const iM = P(-PI4, PI4), i0 = P(0, PI2), iP = P(PI4, PI4), sL = P(PI4, -PI4), O = P(0, 0);
    ctx.fillStyle = COL.regionI; ctx.beginPath(); ctx.moveTo(...O); ctx.lineTo(...iM); ctx.lineTo(...i0); ctx.lineTo(...iP); ctx.closePath(); ctx.fill();
    ctx.fillStyle = COL.regionII; ctx.beginPath(); ctx.moveTo(...O); ctx.lineTo(...iP); ctx.lineTo(...sL); ctx.closePath(); ctx.fill();
    // r = const curves: U V = c(r), parametrized by V = e^s > 0, U = c / V
    ctx.strokeStyle = COL.rconst; ctx.lineWidth = 1; ctx.setLineDash([]);
    const rList = [0.3, 0.6, 0.8, 1.25, 1.5, 2, 3, 5, 10];
    for (const rr of rList) {
      const c = cOfR(rr * RS), pts = [];
      for (let i = 0; i <= 200; i++) { const V = Math.exp(-14 + 28 * i / 200); pts.push(...compactify(c / V, V)); }
      this._polyline(ctx, m, pts, box[0], box[1], box[2], box[3]);
    }
    // labels for a few r = const curves (interior: at chosen V; exterior: at chosen T̃, solved for V by bisection)
    const labInt = (rr, V, dx, dy, align) => { const [Xt, Tt] = compactify(cOfR(rr * RS) / V, V); this._label(ctx, `r = ${rr} r_s`, m.x(Xt) + dx, m.y(Tt) + dy, COL.rconst, { align, font: FONT(9.5) }); };
    const labExt = (rr, Tt0, dx, dy) => {
      const c = cOfR(rr * RS); let lo = -14, hi = 14;
      for (let k = 0; k < 60; k++) { const mid = (lo + hi) / 2, V = Math.exp(mid); if (compactify(c / V, V)[1] < Tt0) lo = mid; else hi = mid; }
      const V = Math.exp((lo + hi) / 2), [Xt, Tt] = compactify(c / V, V);
      this._label(ctx, `r = ${rr} r_s`, m.x(Xt) + dx, m.y(Tt) + dy, COL.rconst, { align: 'right', font: FONT(9.5) });
    };
    if (!m.compact) {
      labInt(0.8, 0.5, 0, 12, 'center'); labInt(0.6, 0.32, 0, 12, 'center');
      labExt(1.25, -0.02, -3, 4); labExt(1.5, -0.15, -3, 4); labExt(2, -0.28, -3, 4); labExt(3, -0.41, -3, 4);
    }
    // boundaries
    ctx.lineWidth = 1.4; ctx.strokeStyle = COL.accent;
    ctx.beginPath(); ctx.moveTo(...i0); ctx.lineTo(...iP); ctx.stroke();      // 𝓘⁺ : Ṽ = π/2  (T̃ + X̃ = π/2)
    ctx.beginPath(); ctx.moveTo(...iM); ctx.lineTo(...i0); ctx.stroke();      // 𝓘⁻ : Ũ = −π/2 (T̃ − X̃ = −π/2)
    ctx.strokeStyle = COL.horizon; ctx.lineWidth = 1.6; ctx.beginPath(); ctx.moveTo(...O); ctx.lineTo(...iP); ctx.stroke();   // future horizon Ũ = 0
    ctx.lineWidth = 1; ctx.setLineDash([5, 4]); ctx.beginPath(); ctx.moveTo(...iM); ctx.lineTo(...sL); ctx.stroke(); ctx.setLineDash([]);   // Ṽ = 0 (dashed)
    ctx.strokeStyle = COL.sing; ctx.lineWidth = 3.5; ctx.beginPath(); ctx.moveTo(...sL); ctx.lineTo(...iP); ctx.stroke();   // singularity Ũ + Ṽ = π/2
    ctx.fillStyle = COL.accent;
    for (const q of [i0, iP, iM]) { ctx.beginPath(); ctx.arc(q[0], q[1], 3, 0, 2 * PI); ctx.fill(); }
    // labels (rotated along the 45° boundaries)
    const cp = m.compact;
    if (cp) this._label(ctx, 'i⁰', i0[0] + 6, i0[1] + 4, COL.accent, { font: FONT(10.5) });
    else this._label(ctx, 'i⁰ (spatial infinity)', i0[0] - 4, i0[1] + 17, COL.accent, { align: 'right', font: FONT(10.5) });
    this._label(ctx, 'i⁺', iP[0] + 8, iP[1] - 2, COL.accent, { font: FONT(10.5) });
    this._label(ctx, 'i⁻', iM[0] - 6, iM[1] + 12, COL.accent, { align: 'right', font: FONT(10.5) });
    // 𝓘⁺ runs from i⁰ up-left to i⁺ (canvas angle +45°), 𝓘⁻ from i⁻ up-right to i⁰ (canvas angle −45°); labels sit just outside the region
    this._label(ctx, cp ? '𝓘⁺ (Ṽ = π/2)' : '𝓘⁺  future null infinity (Ṽ = π/2)', m.x(PI2 - PI4 / 2) + 9, m.y(PI4 / 2) - 9, COL.accent, { align: 'center', angle: PI4, font: FONT(10) });
    this._label(ctx, cp ? '𝓘⁻ (Ũ = −π/2)' : '𝓘⁻  past null infinity (Ũ = −π/2)', m.x(PI2 - PI4 / 2) + 12, m.y(-PI4 / 2) + 12, COL.accent, { align: 'center', angle: -PI4, font: FONT(10) });
    this._label(ctx, cp ? 'r = r_s horizon' : 'r = r_s future horizon (Ũ = 0)', m.x(0.5), m.y(0.5) + 13, COL.horizon, { align: 'center', angle: -PI4, font: FONT(10, 600) });
    this._label(ctx, cp ? 'past horizon Ṽ = 0 (not covered)' : 'past horizon Ṽ = 0 (not covered by ingoing EF chart)', m.x(-0.2), m.y(0.2) + 13, COL.horizon, { align: 'center', angle: PI4, font: FONT(9.5) });
    this._label(ctx, 'r = 0 (classical singularity)', m.x(0), m.y(PI4) - 20, COL.sing, { align: 'center', font: FONT(10.5, 600) });
    this._label(ctx, 'GR invalid before this: r_QG', m.x(0), m.y(PI4) - 7, COL.sing, { align: 'center', font: FONT(10.5, 600) });
    this._label(ctx, 'I  (exterior)', m.x(0.72), m.y(0.16), COL.text, { align: 'center', font: FONT(12, 600) });
    this._label(ctx, 'II  (interior)', m.x(-0.02), m.y(0.35), COL.text, { align: 'center', font: FONT(12, 600) });
    if (!cp) this._label(ctx, 'III / IV: not covered', m.x(-0.55), m.y(-0.15), COL.dim, { align: 'center', font: FONT(10) });

    // worldline and current point
    this._worldline(ctx, m, this.wlP, box);
    if (onChart) { this._cone(ctx, m, X, T, 0.13, col); this._currentPoint(ctx, m, X, T, col); }
    ctx.restore();
  }

  // ---------------------------------------------------------------- caption
  _drawCaption() {
    const s = this.sample, reg = this._regimeIndex(), col = COL.regime[reg];
    const v = (x, d = 4) => (isNum(x) ? fmt.sci(x, d) : 'exp overflow');
    const rows = s ? [
      ['Kruskal (U, V)', `${v(s.kruskal_U)}, ${v(s.kruskal_V)}`],
      ['Kruskal (T, X)', `${v(s.kruskal_T)}, ${v(s.kruskal_X)}`],
      ['Compactified (Ũ, Ṽ, T̃, X̃)', `${v(s.penrose_Ut)}, ${v(s.penrose_Vt)}, ${v(s.penrose_T)}, ${v(s.penrose_X)}`],
      ['Position', `r / r_s = ${v(s.r_over_rs, 5)}   (Schwarzschild t = ${v(s.t_schw_geo, 5)} M, EF v = ${v(s.v_geo, 5)} M)`],
    ] : [['Coordinates', '—']];
    const note = (this.data.meta && this.data.meta.kruskal_time_origin_note) || 'Time origin: horizon crossing at V = 1 (T = X = 1/2).';
    const html = rows.map(([k, val]) => `<div style="color:${COL.dim}">${k}</div><div style="font-family:ui-monospace,Menlo,Consolas,monospace;font-variant-numeric:tabular-nums">${val}</div>`).join('') +
      `<div style="color:${COL.dim}">Regime</div><div style="color:${col};font-weight:700">${REGIME_NAMES[reg]}</div>` +
      `<div style="grid-column:1/3;color:${COL.text};font-weight:600;margin-top:2px">Inside r_s every future-directed causal curve reaches smaller r: the singularity is in the future, not at a place.</div>` +
      `<div style="grid-column:1/3;color:${COL.dim}">Both diagrams are exact Schwarzschild coordinate maps (G = c = M = 1, r_s = 2) with angular directions suppressed; the worldline is the precomputed ` +
      `radial infall of the engine (not integrated in the browser) and stops at r_QG, where the validated integration stops. ${note}</div>`;
    if (this.caption.innerHTML !== html) this.caption.innerHTML = html;
  }
}
