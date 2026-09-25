// SPECULATIVE QUANTUM-GRAVITY TOY MODELS — NOT ESTABLISHED PHYSICS.
// Separate menu.  Everything here is drawn in purple hues, carries the permanent banner, and never
// re-uses the validated colour scheme.  Data: window.SLAB_DATA.speculative (written by run_simulation.py --speculative).
import { fmt } from './data.js';

const MODEL_COLORS = { hayward: '#d98cff', bardeen: '#ff8cd9', dymnikova: '#b48cff' };

export class SpeculativeView {
  constructor(container, data, opts = {}) {
    this.container = container; this.data = data; this.spec = data.raw.speculative || null;
    this.enabled = {}; this.currentLogr = null;
    try { this._build(); } catch (e) { container.innerHTML = `<div class="overlay">speculative view failed: ${e}</div>`; }
  }
  _build() {
    const c = this.container, sp = this.spec, d = this.data;
    c.style.overflow = 'auto'; c.style.padding = '48px 18px 18px 18px'; c.style.color = '#d8dee9';
    if (!sp) { c.innerHTML += `<h2 style="color:#d98cff">SPECULATIVE QUANTUM-GRAVITY TOY MODELS — NOT ESTABLISHED PHYSICS</h2><p>No toy-model data in this export. Run <code>python run_simulation.py --speculative</code>.</p>`; return; }
    const KP = Math.log10(d.derived.K_planck), tauGR = d.derived.tau_horizon_to_singularity_years;
    const rows = Object.entries(sp.models).map(([key, m]) => {
      const doc = (m.docs && m.docs[key]) || {};
      return `<tr style="border-top:1px solid #3a2a4a;vertical-align:top">
        <td style="color:${MODEL_COLORS[key] || '#d98cff'};font-weight:600"><label><input type="checkbox" data-model="${key}" checked> ${m.model}</label></td>
        <td><code>${doc.metric || '—'}</code></td><td>${doc.citation || '—'}</td><td>${doc.assumptions || '—'}</td><td>${doc.differs_from_GR || '—'}</td>
        <td><b>${doc.observational_support || 'NONE'}</b></td>
        <td>${fmt.sci(sp.core_length_m, 3)} m<br>(${fmt.sci(sp.core_length_in_planck_lengths, 2)} l_P)</td>
        <td>${m.K_max_log10_SI != null ? m.K_max_log10_SI.toFixed(2) : '—'} (Planck ${KP.toFixed(2)})</td>
        <td>${m.inner_horizon_r_m != null ? fmt.sci(m.inner_horizon_r_m, 3) + ' m' : 'none found'}</td>
        <td>${m.r_1pct_deviation_from_schwarzschild_m != null ? fmt.sci(m.r_1pct_deviation_from_schwarzschild_m, 3) + ' m' : '—'}</td>
        <td>${fmt.years(m.tau_horizon_to_stop_years)}<br>(GR to r=0: ${fmt.years(tauGR)})</td>
        <td>${m.reaches_r0_in_finite_proper_time || '—'}</td></tr>`;
    }).join('');
    c.innerHTML = `
      <div style="border:2px solid #d98cff;background:rgba(217,140,255,.12);padding:10px 14px;border-radius:6px;margin-bottom:12px">
        <div style="font-size:16px;font-weight:800;color:#d98cff">${sp.menu_title}</div>
        <div style="font-size:15px;font-weight:700;color:#d98cff;margin-top:4px">${sp.banner}</div>
        <div class="note" style="margin-top:6px;color:#c8b0d8">${sp.note}</div>
      </div>
      <p style="max-width:1100px">None of these models is selected as "the answer". They are published regular ("non-singular") black-hole
      metrics integrated with the SAME validated Eddington–Finkelstein geodesic engine (only f(r) differs), shown for comparison with the
      classical Schwarzschild trajectory that ends at r_QG. The core length (${fmt.sci(sp.core_length_m, 3)} m = ${fmt.sci(sp.core_length_in_planck_lengths, 2)} Planck lengths)
      is an arbitrary choice with no observational basis; inner-horizon (mass-inflation) instabilities are ignored; these curves are NOT predictions.
      The integration of each toy model stops at r = ${fmt.sci(sp.r_stop_m, 3)} m.</p>
      <table style="border-collapse:collapse;font-size:12px;width:100%;margin-bottom:14px">
        <thead><tr style="color:#d98cff;text-align:left"><th>model (toggle)</th><th>exact f(r) in ds² = −f dv² + 2 dv dr + r² dΩ²</th><th>citation</th><th>assumptions</th><th>where it differs from GR</th>
        <th>observational support</th><th>core length used</th><th>max log10 K [m⁻⁴]</th><th>inner horizon</th><th>r where f deviates 1 % from Schwarzschild</th><th>τ(r_s → stop)</th><th>reaches r = 0 in finite τ?</th></tr></thead>
        <tbody>${rows}</tbody></table>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
        <div><div style="color:#d98cff;font-weight:600;margin-bottom:4px">log10 K [m⁻⁴] vs log10(r / r_s) — validated Schwarzschild (green) vs toy models (dashed purple) — SPECULATIVE COMPARISON</div><canvas id="spec-k" style="width:100%;height:340px;border:1px solid #3a2a4a;border-radius:4px"></canvas></div>
        <div><div style="color:#d98cff;font-weight:600;margin-bottom:4px">metric function f(r) vs log10(r / r_s) — SPECULATIVE COMPARISON</div><canvas id="spec-f" style="width:100%;height:340px;border:1px solid #3a2a4a;border-radius:4px"></canvas></div>
      </div>
      <p class="note" style="margin-top:10px">Citations: see references.md (not re-verified online in the build session). Regime label while this menu is open: SPECULATIVE QUANTUM MODEL.</p>`;
    for (const key of Object.keys(sp.models)) this.enabled[key] = true;
    c.querySelectorAll('input[data-model]').forEach(cb => cb.addEventListener('change', e => { this.enabled[e.target.dataset.model] = e.target.checked; this._draw(); }));
    this.kCanvas = c.querySelector('#spec-k'); this.fCanvas = c.querySelector('#spec-f');
    this._draw();
  }
  _plot(canvas, series, opts) {
    const ctx = canvas.getContext('2d'); if (!ctx) return;
    const dpr = Math.min(2, window.devicePixelRatio || 1), W = canvas.clientWidth || 600, H = canvas.clientHeight || 340;
    canvas.width = W * dpr; canvas.height = H * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = '#12101a'; ctx.fillRect(0, 0, W, H);
    const L = 62, R = 16, T = 16, B = 40;
    const xs = series.flatMap(s => s.x), ys = series.flatMap(s => s.y).filter(v => v !== null && isFinite(v));
    let x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = opts.y0 ?? Math.min(...ys), y1 = opts.y1 ?? Math.max(...ys);
    if (y1 === y0) y1 = y0 + 1;
    const X = x => L + (x - x0) / (x1 - x0) * (W - L - R), Y = y => T + (1 - (y - y0) / (y1 - y0)) * (H - T - B);
    ctx.strokeStyle = '#3a2a4a'; ctx.fillStyle = '#b8a8c8'; ctx.font = '11px ui-monospace, monospace'; ctx.lineWidth = 1;
    const nx = 8, ny = 6;
    for (let i = 0; i <= nx; i++) { const x = x0 + (x1 - x0) * i / nx; ctx.beginPath(); ctx.moveTo(X(x), T); ctx.lineTo(X(x), H - B); ctx.stroke(); ctx.fillText(x.toFixed(0), X(x) - 10, H - B + 14); }
    for (let i = 0; i <= ny; i++) { const y = y0 + (y1 - y0) * i / ny; ctx.beginPath(); ctx.moveTo(L, Y(y)); ctx.lineTo(W - R, Y(y)); ctx.stroke(); ctx.fillText(y.toFixed(opts.ydigits ?? 0), 4, Y(y) + 4); }
    ctx.fillText(opts.xlabel, W / 2 - 40, H - 6); ctx.save(); ctx.translate(12, H / 2 + 40); ctx.rotate(-Math.PI / 2); ctx.fillText(opts.ylabel, 0, 0); ctx.restore();
    if (opts.hline != null) { ctx.strokeStyle = '#ff6b6b'; ctx.setLineDash([6, 4]); ctx.beginPath(); ctx.moveTo(L, Y(opts.hline)); ctx.lineTo(W - R, Y(opts.hline)); ctx.stroke(); ctx.setLineDash([]); ctx.fillStyle = '#ff6b6b'; ctx.fillText(opts.hlabel, L + 6, Y(opts.hline) - 4); }
    for (const s of series) {
      ctx.strokeStyle = s.color; ctx.lineWidth = s.width || 1.5; ctx.setLineDash(s.dash || []);
      ctx.beginPath(); let pen = false;
      for (let i = 0; i < s.x.length; i++) { const y = s.y[i]; if (y === null || !isFinite(y)) { pen = false; continue; } const px = X(s.x[i]), py = Y(Math.max(y0, Math.min(y1, y))); if (!pen) { ctx.moveTo(px, py); pen = true; } else ctx.lineTo(px, py); }
      ctx.stroke(); ctx.setLineDash([]);
    }
    if (this.currentLogr != null && this.currentLogr >= x0 && this.currentLogr <= x1) { ctx.strokeStyle = '#ffffff'; ctx.setLineDash([2, 3]); ctx.beginPath(); ctx.moveTo(X(this.currentLogr), T); ctx.lineTo(X(this.currentLogr), H - B); ctx.stroke(); ctx.setLineDash([]); ctx.fillStyle = '#fff'; ctx.fillText('observer (validated run)', X(this.currentLogr) + 4, T + 12); }
    let ly = T + 14; for (const s of series) { ctx.fillStyle = s.color; ctx.fillRect(W - R - 210, ly - 8, 18, 3); ctx.fillText(s.label, W - R - 186, ly - 4); ly += 15; }
  }
  _draw() {
    if (!this.spec || !this.kCanvas) return;
    const d = this.data, sp = this.spec;
    const lr = d.s.log10_r_over_rs, kS = d.s.K_SI_log10;
    const seriesK = [{ label: 'Schwarzschild (validated GR, stops at r_QG)', color: '#6ee7a0', width: 2.5, x: lr, y: kS }];
    const seriesF = [{ label: 'Schwarzschild f = 1 − r_s/r', color: '#6ee7a0', width: 2.5, x: lr, y: lr.map(v => 1 - 1 / Math.pow(10, v)) }];
    for (const [key, m] of Object.entries(sp.models)) {
      if (!this.enabled[key] || !m.log10_r_over_rs) continue;
      seriesK.push({ label: m.model + ' (SPECULATIVE)', color: MODEL_COLORS[key] || '#d98cff', dash: [6, 4], x: m.log10_r_over_rs, y: m.log10_K_SI });
      seriesF.push({ label: m.model + ' (SPECULATIVE)', color: MODEL_COLORS[key] || '#d98cff', dash: [6, 4], x: m.log10_r_over_rs, y: m.f });
    }
    const KP = Math.log10(d.derived.K_planck);
    this._plot(this.kCanvas, seriesK, { xlabel: 'log10(r / r_s)', ylabel: 'log10 K [m^-4]', hline: KP, hlabel: 'Planck curvature 1/l_P^4', y0: -90, y1: KP + 10 });
    const fmin = Math.min(-60, ...seriesF.flatMap(s => s.y.filter(v => v !== null && isFinite(v))));
    this._plot(this.fCanvas, seriesF, { xlabel: 'log10(r / r_s)', ylabel: 'f(r)', y0: Math.max(fmin, -60), y1: 2, ydigits: 0 });
  }
  update(smp, state) { if (smp) { this.currentLogr = smp.log10_r_over_rs; if (this.container.classList.contains('active')) this._draw(); } }
  resize() { this._draw(); }
  setMode() {}
  dispose() {}
}
