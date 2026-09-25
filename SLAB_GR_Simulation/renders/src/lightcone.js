// Local future light cone of the infalling observer, drawn from the EXACT null condition of the
// ingoing Eddington–Finkelstein metric (see physics_notes.md §8).  Nothing here is approximate
// except the drawing itself: the cone is a spacetime object embedded as a glyph in the spatial scene.
//
// Local frame at the observer: vertical = t_EF = v - r, horizontal radial = outward r, third axis =
// transverse (r dphi).  With dt_EF = 1 the null directions (a = dr, b = r dphi) satisfy
//     (2 - f) w^2 - 2 w + b^2 = 0,  w = 1 + a,   f = 1 - r_s/r,
// i.e. the cross-section of the future cone at unit EF time is the ELLIPSE
//     centre a_c = -1 + 1/(2-f),  semi-axis (radial) 1/(2-f),  semi-axis (transverse) 1/sqrt(2-f).
// Far away (f -> 1): the unit circle.  On the horizon (f = 0): centre -1/2, radial semi-axis 1/2, so the
// outgoing generator is exactly vertical (dr = 0, it lies on r = r_s).  Inside (f < 0): the whole
// ellipse lies at a < 0 — every future-directed direction decreases r.
import * as THREE from 'three';

export function coneCrossSection(f) {
  const q = 2 - f;
  return { ac: -1 + 1 / q, ar: 1 / q, at: 1 / Math.sqrt(q) };
}

export class LightCone {
  constructor(size = 1) {
    this.group = new THREE.Group();
    this.size = size;
    this.n = 40;
    const geom = new THREE.BufferGeometry();
    const pos = new Float32Array((this.n + 1) * 3 * 3);
    geom.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    this.mesh = new THREE.Mesh(geom, new THREE.MeshBasicMaterial({ color: 0xffd166, transparent: true, opacity: 0.35, side: THREE.DoubleSide, depthWrite: false }));
    this.group.add(this.mesh);
    const mk = (color) => { const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(6), 3)); return new THREE.Line(g, new THREE.LineBasicMaterial({ color })); };
    this.genOut = mk(0xffd166); this.genIn = mk(0xffd166); this.world = mk(0x7ab7ff); this.axisT = mk(0x8892a6); this.axisR = mk(0x8892a6);
    this.group.add(this.genOut, this.genIn, this.world, this.axisT, this.axisR);
    this.tip = new THREE.Mesh(new THREE.ConeGeometry(0.06 * size, 0.18 * size, 8), new THREE.MeshBasicMaterial({ color: 0x7ab7ff }));
    this.group.add(this.tip);
  }
  // f = 1 - r_s/r ; slopes: dr/dt_EF of outgoing/ingoing generators and of the worldline (from the data)
  update(f, slopeOut, slopeIn, slopeWorld) {
    const S = this.size, { ac, ar, at } = coneCrossSection(f);
    const pos = this.mesh.geometry.attributes.position.array;
    let k = 0;
    for (let i = 0; i < this.n; i++) {
      const t0 = (i / this.n) * 2 * Math.PI, t1 = ((i + 1) / this.n) * 2 * Math.PI;
      const p0 = [S * (ac + ar * Math.cos(t0)), S, S * at * Math.sin(t0)];
      const p1 = [S * (ac + ar * Math.cos(t1)), S, S * at * Math.sin(t1)];
      pos.set([0, 0, 0, ...p0, ...p1], k); k += 9;
    }
    this.mesh.geometry.attributes.position.needsUpdate = true;
    this.mesh.geometry.computeBoundingSphere();
    const setLine = (line, x, y, z) => { const a = line.geometry.attributes.position.array; a.set([0, 0, 0, x, y, z]); line.geometry.attributes.position.needsUpdate = true; };
    setLine(this.genOut, S * slopeOut, S, 0);
    setLine(this.genIn, S * slopeIn, S, 0);
    setLine(this.world, S * slopeWorld, S, 0);
    setLine(this.axisT, 0, 1.3 * S, 0);
    setLine(this.axisR, 1.3 * S, 0, 0);
    this.tip.position.set(S * slopeWorld, S, 0);
    const dir = new THREE.Vector3(S * slopeWorld, S, 0).normalize();
    this.tip.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir);
    this.mesh.material.color.set(f > 0.02 ? 0xffd166 : (f > -0.02 ? 0xff8c42 : 0xff6b6b));
  }
}

// 2D inset: the (t_EF, r) plane with the two null generators, the shaded future cone and the worldline tangent.
export function drawConeInset(canvas, smp) {
  const ctx = canvas.getContext('2d'); if (!ctx) return;
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  const W = canvas.clientWidth || 260, H = canvas.clientHeight || 200;
  if (canvas.width !== W * dpr || canvas.height !== H * dpr) { canvas.width = W * dpr; canvas.height = H * dpr; }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = 'rgba(11,14,20,0.85)'; ctx.fillRect(0, 0, W, H);
  const ox = W * 0.5, oy = H * 0.72, sc = Math.min(W, H) * 0.32;
  const rOverRs = smp.r_over_rs, f = 1 - 1 / rOverRs;
  const so = smp.lc_out_drdtEF ?? f / (2 - f), si = smp.lc_in_drdtEF ?? -1, sw = smp.worldline_drdtEF ?? 0;
  // axes: r to the right, t_EF up
  ctx.strokeStyle = '#3a4560'; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(10, oy); ctx.lineTo(W - 10, oy); ctx.moveTo(ox, H - 8); ctx.lineTo(ox, 12); ctx.stroke();
  ctx.fillStyle = '#8892a6'; ctx.font = '11px system-ui, sans-serif';
  ctx.fillText('r →', W - 30, oy - 4); ctx.fillText('t_EF ↑', ox + 4, 18);
  // shaded cone between the generators (dt = 1 -> dr = slope)
  const T = sc;
  ctx.fillStyle = f > 0.02 ? 'rgba(255,209,102,0.25)' : (f > -0.02 ? 'rgba(255,140,66,0.3)' : 'rgba(255,107,107,0.3)');
  ctx.beginPath(); ctx.moveTo(ox, oy); ctx.lineTo(ox + so * T, oy - T); ctx.lineTo(ox + si * T, oy - T); ctx.closePath(); ctx.fill();
  ctx.strokeStyle = '#ffd166'; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(ox, oy); ctx.lineTo(ox + so * T, oy - T); ctx.moveTo(ox, oy); ctx.lineTo(ox + si * T, oy - T); ctx.stroke();
  // horizon line r = r_s (vertical) when within the window
  const drWin = 1.6;   // window half-width in units of the cone scale (dr per dt = 1)
  const rsPos = (1 - rOverRs) / Math.max(1e-300, rOverRs); // (r_s - r)/r in units of r... only meaningful near horizon
  if (Math.abs(rOverRs - 1) < 0.5) {
    // place the horizon at horizontal offset proportional to (r_s - r)/r_s relative to the cone scale (schematic)
    const xh = ox + ((1 - rOverRs) / 0.5) * drWin * 0.5 * sc;
    ctx.strokeStyle = '#ff8c42'; ctx.setLineDash([4, 3]); ctx.beginPath(); ctx.moveTo(xh, 12); ctx.lineTo(xh, H - 8); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = '#ff8c42'; ctx.fillText('r = r_s', xh + 3, 30);
  }
  // worldline tangent
  ctx.strokeStyle = '#7ab7ff'; ctx.lineWidth = 2.5;
  ctx.beginPath(); ctx.moveTo(ox, oy); ctx.lineTo(ox + sw * T, oy - T); ctx.stroke();
  ctx.fillStyle = '#7ab7ff'; ctx.beginPath(); ctx.arc(ox + sw * T, oy - T, 3.5, 0, 2 * Math.PI); ctx.fill();
  ctx.fillStyle = '#d8dee9'; ctx.font = '12px system-ui, sans-serif';
  ctx.fillText('local future light cone (ingoing EF time)', 8, 14);
  ctx.font = '11px ui-monospace, monospace'; ctx.fillStyle = '#c8d0e0';
  ctx.fillText(`dr/dt_EF: out ${so.toFixed(3)}  in ${si.toFixed(1)}  worldline ${sw.toFixed(3)}`, 8, H - 22);
  const where = rOverRs > 1.001 ? 'outside r_s: cone straddles increasing and decreasing r' : (rOverRs > 0.999 ? 'AT r_s: outgoing generator is vertical (lies on the horizon)' : 'inside r_s: every future direction has dr < 0');
  ctx.fillStyle = f > 0.02 ? '#ffd166' : (f > -0.02 ? '#ff8c42' : '#ff6b6b');
  ctx.fillText(where, 8, H - 8);
}
