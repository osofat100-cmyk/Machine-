// Inside parts for the vision video, built in seat frame S (mm, Z out of the face).
// Placement and sizes come from data/vision_layout.json (checked against the shell by vision_layout_check.py):
//   battery  - Li-ion pouch as in JBL's FCC photo: white label, kapton tape over the terminal end, red/black leads
//   pcb      - green board, ENIG pads, silkscreen; chips are KiCad 3D models (U2 = LTC4070EMS8E package, MS8E)
//   speaker  - 10 mm dynamic driver (JBL spec), facing down into the nozzle, leads up to the board
import * as THREE from "three";
import { VRMLLoader } from "three/addons/loaders/VRMLLoader.js";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";

const canvasTex = (wmm, hmm, pxmm, draw) => {
  const c = document.createElement("canvas"); c.width = Math.round(wmm * pxmm); c.height = Math.round(hmm * pxmm);
  const g = c.getContext("2d");
  g.setTransform(pxmm, 0, 0, -pxmm, 0, c.height);          // draw in mm, y up (matches the S frame seen from above)
  draw(g);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t;
};
const text = (g, s, x, y, size, color, align = "center", bold = false) => {
  g.save(); g.translate(x, y); g.scale(1, -1);
  g.font = `${bold ? "700" : "500"} ${size}px Inter, sans-serif`; g.fillStyle = color; g.textAlign = align; g.textBaseline = "middle";
  g.fillText(s, 0, 0); g.restore();
};

// ---------------- wires ----------------
function wire(points, radius, color, gloss = 0.45) {
  const curve = new THREE.CatmullRomCurve3(points.map(p => new THREE.Vector3(...p)), false, "centripetal");
  const m = new THREE.Mesh(new THREE.TubeGeometry(curve, Math.max(40, points.length * 24), radius, 10, false),
    new THREE.MeshPhysicalMaterial({ color, roughness: gloss, clearcoat: 0.6, clearcoatRoughness: 0.3 }));
  m.castShadow = true; return m;
}
function tubeGeo(points, radius) {
  const curve = new THREE.CatmullRomCurve3(points.map(p => new THREE.Vector3(...p)), false, "centripetal");
  return new THREE.TubeGeometry(curve, Math.max(60, points.length * 10), radius, 10, false);
}
// point lists of two leads twisted around `path` (all of it), then each to its own end points
function twistedPoints(path, pitch, ends, radius) {
  const c = new THREE.CatmullRomCurve3(path.map(p => new THREE.Vector3(...p)), false, "centripetal");
  const L = c.getLength(), n = Math.max(30, Math.round(L / 0.5)), frames = c.computeFrenetFrames(n, false);
  const out = [[], []];
  for (let i = 0; i <= n; i++) {
    const u = i / n, p = c.getPointAt(u), th = (2 * Math.PI * u * L) / pitch;
    for (let k = 0; k < 2; k++) {
      const a = th + k * Math.PI;
      out[k].push(p.clone().add(frames.normals[i].clone().multiplyScalar(Math.cos(a) * radius * 1.05))
        .add(frames.binormals[i].clone().multiplyScalar(Math.sin(a) * radius * 1.05)).toArray());
    }
  }
  return [0, 1].map(k => [...out[k], ...ends[k]]);
}
// two leads twisted around one path for the first `twistLen` mm, then each to its own end point
function twistedPair(path, twistLen, pitch, ends, radius, colors) {
  const c = new THREE.CatmullRomCurve3(path.map(p => new THREE.Vector3(...p)), false, "centripetal");
  const L = c.getLength(), n = 60, frames = c.computeFrenetFrames(n, false);
  const out = [[], []];
  for (let i = 0; i <= n; i++) {
    const u = i / n, s = u * L; if (s > twistLen) break;
    const p = c.getPointAt(u), th = (2 * Math.PI * s) / pitch;
    for (let k = 0; k < 2; k++) {
      const a = th + k * Math.PI, o = frames.normals[i].clone().multiplyScalar(Math.cos(a) * radius * 1.05)
        .add(frames.binormals[i].clone().multiplyScalar(Math.sin(a) * radius * 1.05));
      out[k].push(p.clone().add(o).toArray());
    }
  }
  return [0, 1].map(k => wire([...out[k], ...ends[k]], radius, colors[k]));
}

// ---------------- battery ----------------
function battery(B) {
  const [L, W, H] = B.size, tl = B.terminal_len;
  const top = canvasTex(L, W, 48, g => {
    g.fillStyle = "#f4f4f1"; g.fillRect(0, 0, L, W);
    g.fillStyle = "#d9a225"; g.fillRect(0, 0, tl, W);                       // kapton over the terminal end (u = 0 -> -x)
    g.fillStyle = "rgba(255,240,190,0.35)"; g.fillRect(0.3, 0.4, tl - 0.6, W - 0.8);
    g.fillStyle = "#c6cacf"; g.fillRect(L - 0.7, 0, 0.7, W);                 // pouch seal at the far end
    text(g, "⊕", tl / 2, W * 0.72, 1.5, "#5a4010"); text(g, "⊖", tl / 2, W * 0.28, 1.5, "#5a4010");
    // crossed-out bin, recycling mark, cell text, QR code (as on the FCC photo)
    g.strokeStyle = "#222"; g.lineWidth = 0.18;
    const bx = tl + 3.2, by = W / 2;
    g.strokeRect(bx - 0.9, by - 1.2, 1.8, 2.2); g.beginPath(); g.moveTo(bx - 1.4, by - 1.6); g.lineTo(bx + 1.4, by + 1.6);
    g.moveTo(bx + 1.4, by - 1.6); g.lineTo(bx - 1.4, by + 1.6); g.stroke();
    const rx = tl + 8.5;
    for (let k = 0; k < 3; k++) { g.beginPath(); g.arc(rx, by, 1.3, k * 2.1 + 0.2, k * 2.1 + 1.6); g.stroke(); }
    text(g, "Li-ion 00", tl + 12.6, by, 0.95, "#333");
    const qx = L - 5.6, qy = by - 1.6, q = 3.2 / 21;
    let seed = 7; const rnd = () => ((seed = (seed * 9301 + 49297) % 233280) / 233280);
    g.fillStyle = "#111";
    for (let i = 0; i < 21; i++) for (let j = 0; j < 21; j++) {
      const finder = (i < 7 && j < 7) || (i > 13 && j < 7) || (i < 7 && j > 13);
      const on = finder ? ((i % 14 === 0 || i % 14 === 6 || j % 14 === 0 || j % 14 === 6 || (i % 14 > 1 && i % 14 < 5 && j % 14 > 1 && j % 14 < 5))) : rnd() > 0.5;
      if (on) g.fillRect(qx + i * q, qy + j * q, q, q);
    }
  });
  const white = new THREE.MeshPhysicalMaterial({ color: 0xf2f2ef, roughness: 0.55, clearcoat: 0.3 });
  const mats = [
    new THREE.MeshPhysicalMaterial({ color: 0xc4c8cd, roughness: 0.3, metalness: 0.8 }),        // +x: pouch seal
    new THREE.MeshPhysicalMaterial({ color: 0xd9a225, roughness: 0.25, clearcoat: 0.8 }),       // -x: kapton
    white, white,
    new THREE.MeshPhysicalMaterial({ map: top, roughness: 0.5, clearcoat: 0.35, clearcoatRoughness: 0.4 }),
    white,
  ];
  const m = new THREE.Mesh(new RoundedBoxGeometry(L, W, H, 3, 0.6), mats);
  m.castShadow = m.receiveShadow = true;
  const grp = new THREE.Group(); grp.add(m); grp.position.set(...B.centre);
  return grp;
}

// ---------------- PCB ----------------
const FOOT = {   // simplified pad patterns (mm) for the board texture
  "QFN-40-1EP_5x5mm_P0.4mm_EP3.6x3.6mm": g => { g.fillRect(-1.8, -1.8, 3.6, 3.6); for (let i = 0; i < 10; i++) { const s = -1.8 + i * 0.4; g.fillRect(s - 0.1, 2.3, 0.2, 0.7); g.fillRect(s - 0.1, -3.0, 0.2, 0.7); g.fillRect(2.3, s - 0.1, 0.7, 0.2); g.fillRect(-3.0, s - 0.1, 0.7, 0.2); } },
  "MSOP-8-1EP_3x3mm_P0.65mm_EP1.68x1.88mm": g => { g.fillRect(-0.94, -0.84, 1.88, 1.68); for (let i = 0; i < 4; i++) { const s = -0.975 + i * 0.65; g.fillRect(-2.6, s - 0.2, 1.1, 0.4); g.fillRect(1.5, s - 0.2, 1.1, 0.4); } },
  "SOT-23-6": g => { for (let i = 0; i < 3; i++) { const s = -0.95 + i * 0.95; g.fillRect(-1.6, s - 0.3, 1.0, 0.6); g.fillRect(0.6, s - 0.3, 1.0, 0.6); } },
  "WSON-8-1EP_2x2mm_P0.5mm_EP0.9x1.6mm": g => { g.fillRect(-0.45, -0.8, 0.9, 1.6); for (let i = 0; i < 4; i++) { const s = -0.75 + i * 0.5; g.fillRect(-1.25, s - 0.12, 0.55, 0.24); g.fillRect(0.7, s - 0.12, 0.55, 0.24); } },
  "Crystal_SMD_2520-4Pin_2.5x2.0mm": g => { for (const sx of [-1, 1]) for (const sy of [-1, 1]) g.fillRect(sx * 0.85 - 0.5, sy * 0.65 - 0.4, 1.0, 0.8); },
  "L_0805_2012Metric": g => { g.fillRect(-1.35, -0.7, 0.8, 1.4); g.fillRect(0.55, -0.7, 0.8, 1.4); },
  "C_0603_1608Metric": g => { g.fillRect(-1.1, -0.45, 0.6, 0.9); g.fillRect(0.5, -0.45, 0.6, 0.9); },
  "C_0402_1005Metric": g => { g.fillRect(-0.75, -0.3, 0.45, 0.6); g.fillRect(0.3, -0.3, 0.45, 0.6); },
  "R_0402_1005Metric": g => { g.fillRect(-0.75, -0.3, 0.45, 0.6); g.fillRect(0.3, -0.3, 0.45, 0.6); },
  "LED_0402_1005Metric": g => { g.fillRect(-0.75, -0.3, 0.45, 0.6); g.fillRect(0.3, -0.3, 0.45, 0.6); },
};
async function pcb(P, parts, pads, kicadUnits) {
  const [L, W, T] = P.size, [cx, cy] = P.centre, ox = L / 2 - cx, oy = W / 2 - cy;   // board-texture coords = S + (ox, oy)
  const tex = canvasTex(L, W, 64, g => {
    g.fillStyle = "#1b5e34"; g.fillRect(0, 0, L, W);
    g.strokeStyle = "#2a7a47"; g.lineWidth = 0.18; g.lineCap = "round";                  // traces under the mask
    const tr = (pts) => { g.beginPath(); g.moveTo(pts[0][0] + ox, pts[0][1] + oy); for (const p of pts.slice(1)) g.lineTo(p[0] + ox, p[1] + oy); g.stroke(); };
    const at = r => parts.find(q => q.ref === r).xy;
    const u1 = at("U1"), u2 = at("U2"), u3 = at("U3"), y1 = at("Y1"), l1 = at("L1");
    tr([pads.bat_plus, [u2[0], pads.bat_plus[1]], [u2[0], u2[1] + 2.4]]); tr([pads.bat_minus, [u2[0], pads.bat_minus[1]], [u2[0], u2[1] - 2.4]]);
    tr([[u2[0] + 0.3, pads.bat_plus[1]], [u1[0] - 1.5, pads.bat_plus[1]], [u1[0] - 1.5, u1[1] + 2.6]]);
    tr([[u1[0] + 2.6, u1[1] + 0.6], [u3[0] - 1.2, u1[1] + 0.6], [u3[0] - 1.2, u3[1]]]); tr([[u1[0] + 2.6, u1[1] - 0.8], [y1[0] - 1.3, y1[1]]]);
    tr([[u1[0] + 1.2, u1[1] + 2.6], [u1[0] + 1.2, l1[1] + 1.1], [l1[0], l1[1] + 1.1], [l1[0], l1[1] + 0.6]]);
    tr([[u1[0] + 2.6, u1[1] - 1.6], [pads.spk_plus[0] - 1.2, u1[1] - 1.6], [pads.spk_plus[0] - 1.2, pads.spk_plus[1]], pads.spk_plus]);
    tr([[u1[0] + 2.6, u1[1] - 2.0], [pads.spk_minus[0] - 0.8, u1[1] - 2.0], pads.spk_minus]);
    g.fillStyle = "#d8b45a";                                                                // ENIG pads
    for (const q of parts) { g.save(); g.translate(q.xy[0] + ox, q.xy[1] + oy); g.rotate((q.rot * Math.PI) / 180); FOOT[q.model](g); g.restore(); }
    for (const k of Object.keys(pads)) { const [x, y] = pads[k]; g.beginPath(); g.ellipse(x + ox, y + oy, 0.75, 0.6, 0, 0, 7); g.fill(); }
    g.fillStyle = "#1a1a1a";
    for (const k of ["bat_plus", "bat_minus"]) { const [x, y] = pads[k]; g.beginPath(); g.arc(x + ox, y + oy, 0.32, 0, 7); g.fill(); }   // lead holes
    g.fillStyle = "#0e3a1f"; for (const v of [[-1.0, 0.4], [6.6, 3.4], [6.6, -3.1], [10.6, 0.6], [0.8, -2.0], [5.0, 1.8]]) { g.beginPath(); g.arc(v[0] + ox, v[1] + oy, 0.16, 0, 7); g.fill(); }
    g.strokeStyle = "#eef2ee"; g.lineWidth = 0.09;                                           // silkscreen
    for (const q of parts) {
      if (q.model.startsWith("C_0402") || q.model.startsWith("R_0402") || q.model.startsWith("LED")) continue;
      if (q.ref === "U2") continue;
      const lab = { U1: [-3.4, 2.6], U3: [0, 1.5], Y1: [0, -1.6], L1: [1.4, 0], C1: [0, 1.3], C2: [0, 1.3] }[q.ref] || [0, 1.2];
      text(g, q.ref, q.xy[0] + ox + lab[0], q.xy[1] + oy + lab[1], 0.62, "#eef2ee");
    }
    text(g, "B+", pads.bat_plus[0] + ox + 1.5, pads.bat_plus[1] + oy, 0.62, "#eef2ee", "left", true);
    text(g, "B−", pads.bat_minus[0] + ox + 1.5, pads.bat_minus[1] + oy, 0.62, "#eef2ee", "left", true);
    text(g, "SPK", pads.spk_plus[0] + ox, pads.spk_plus[1] + oy + 1.2, 0.55, "#eef2ee");
    text(g, "SOLAR-EP3  REV A", 0.9, 0.85, 0.55, "#eef2ee", "left");
    g.strokeRect(0.35, 0.35, L - 0.7, W - 0.7);
  });
  // rounded-rectangle board
  const r = P.corner_r, s = new THREE.Shape();
  s.moveTo(-L / 2 + r, -W / 2); s.lineTo(L / 2 - r, -W / 2); s.quadraticCurveTo(L / 2, -W / 2, L / 2, -W / 2 + r);
  s.lineTo(L / 2, W / 2 - r); s.quadraticCurveTo(L / 2, W / 2, L / 2 - r, W / 2); s.lineTo(-L / 2 + r, W / 2);
  s.quadraticCurveTo(-L / 2, W / 2, -L / 2, W / 2 - r); s.lineTo(-L / 2, -W / 2 + r); s.quadraticCurveTo(-L / 2, -W / 2, -L / 2 + r, -W / 2);
  const geo = new THREE.ExtrudeGeometry(s, { depth: T, bevelEnabled: false, curveSegments: 6 });
  geo.translate(0, 0, -T / 2);
  tex.repeat.set(1 / L, 1 / W); tex.offset.set(0.5, 0.5);
  const board = new THREE.Mesh(geo, [new THREE.MeshPhysicalMaterial({ map: tex, roughness: 0.42, clearcoat: 0.5, clearcoatRoughness: 0.25 }),
    new THREE.MeshStandardMaterial({ color: 0x9c8f5c, roughness: 0.8 })]);
  board.castShadow = board.receiveShadow = true;
  const grp = new THREE.Group(); grp.add(board); grp.position.set(...P.centre);
  // KiCad models on the top side
  const loader = new VRMLLoader(), cache = {};
  for (const q of parts) {
    if (!cache[q.model]) cache[q.model] = await loader.loadAsync(`/assets/kicad/${q.model}.wrl`);
    const o = cache[q.model].clone(true);
    o.traverse(m => {
      if (!m.isMesh) return;
      const c = m.material.color || new THREE.Color(0x333333), hsl = {}; c.getHSL(hsl);
      const metal = hsl.l > 0.55 && hsl.s < 0.25;
      m.material = new THREE.MeshPhysicalMaterial({ color: c, roughness: metal ? 0.28 : 0.55, metalness: metal ? 0.9 : 0.0, clearcoat: metal ? 0 : 0.2 });
      m.castShadow = true;
    });
    o.scale.setScalar(kicadUnits); o.rotation.z = (q.rot * Math.PI) / 180;
    o.position.set(q.xy[0] - cx, q.xy[1] - cy, T / 2);
    grp.add(o);
  }
  // solder fillets on the lead pads
  const solder = new THREE.MeshPhysicalMaterial({ color: 0xcfd2d4, roughness: 0.2, metalness: 1.0 });
  grp.userData.solderPads = Object.fromEntries(Object.entries(pads).map(([k, [x, y]]) => [k, [x, y, P.centre[2] + T / 2]]));
  grp.userData.solder = [];
  for (const k of ["bat_plus", "bat_minus"]) {
    const b = new THREE.Mesh(new THREE.SphereGeometry(0.72, 16, 10), solder); b.scale.set(1, 1, 0.45);
    b.position.set(pads[k][0] - cx, pads[k][1] - cy, T / 2 + 0.12); grp.add(b); grp.userData.solder.push(b);
  }
  return grp;
}

// ---------------- speaker (10 mm dynamic driver, face down) ----------------
function speaker(S) {
  const g = new THREE.Group(), h = S.h, R = S.d / 2;
  const add = (geo, mat, z) => { const m = new THREE.Mesh(geo, mat); m.rotation.x = Math.PI / 2; m.position.z = z; m.castShadow = m.receiveShadow = true; g.add(m); return m; };
  const steel = new THREE.MeshPhysicalMaterial({ color: 0x8c9096, roughness: 0.35, metalness: 0.9 });
  const black = new THREE.MeshPhysicalMaterial({ color: 0x141518, roughness: 0.6 });
  const nickel = new THREE.MeshPhysicalMaterial({ color: 0xd0d3d6, roughness: 0.18, metalness: 1.0 });
  add(new THREE.CylinderGeometry(R, R, 0.45, 48), steel, -h / 2 + 0.22);                 // front frame
  add(new THREE.CylinderGeometry(R - 0.3, R - 0.2, 0.9, 48), black, -h / 2 + 0.9);        // basket
  add(new THREE.CylinderGeometry(R - 0.6, R - 0.6, 0.3, 48), black, -h / 2 + 1.5);        // back plate
  add(new THREE.CylinderGeometry(3.1, 3.1, 1.35, 40), nickel, h / 2 - 0.68);             // magnet cup
  add(new THREE.TorusGeometry(3.1, 0.12, 8, 40), nickel, h / 2).rotation.x = 0;
  const gold = new THREE.MeshPhysicalMaterial({ color: 0xd8b45a, roughness: 0.25, metalness: 1.0 });
  for (const a of [-0.61, 0.61]) { const t = new THREE.Mesh(new THREE.BoxGeometry(0.9, 1.3, 0.2), gold); t.position.set(3.85 * Math.cos(a), 3.85 * Math.sin(a), -h / 2 + 1.75); t.rotation.z = a; g.add(t); }
  g.position.set(...S.centre);
  return g;
}

// a wire whose shape is set every frame
function dynWire(color, radius, rough = 0.4) {
  const m = new THREE.Mesh(new THREE.BufferGeometry(), new THREE.MeshPhysicalMaterial({ color, roughness: rough, clearcoat: 0.6, clearcoatRoughness: 0.3 }));
  m.castShadow = true; m.userData.radius = radius; m.userData.pts = [];
  m.userData.set = pts => { m.geometry.dispose(); m.geometry = tubeGeo(pts, radius); m.userData.pts = pts; };
  return m;
}
const mix3 = (a, b, k) => a.map((v, i) => v + (b[i] - v) * k);
const mixPts = (A, B, k) => A.map((p, i) => mix3(p, B[i], k));
// wire carried by a moving part (route fixed to the part) that plugs into a fixed pad and then folds as the part lowers:
//   carried: the final route moved by the part's offset `off`;  plugged (c = 1): each point pulled toward its final
//   place by how far along the wire it is (0 at the part, 1 at the pad), plus a sideways fold that peaks mid-way down
function carriedWire(route, carry, c, fold, foldDir, foldAmp) {
  const n = route.length, carried = route.map(carry);
  const plugged = route.map((p, i) => {
    const w = i / (n - 1), q = mix3(carried[i], p, w), b = Math.sin(Math.PI * w) * foldAmp * fold;
    return [q[0] + foldDir[0] * b, q[1] + foldDir[1] * b, q[2] + foldDir[2] * b];
  });
  return mixPts(carried, plugged, c);
}

export async function buildInternals(L) {
  const B = L.battery, P = L.pcb, S = L.speaker, pads = L.pads;
  const bat = battery(B), board = await pcb(P, L.parts, pads, L.kicad.units_mm), spk = speaker(S);
  const pcbTop = P.centre[2] + P.size[2] / 2, batTop = B.centre[2] + B.size[2] / 2, xEnd = B.centre[0] - B.size[0] / 2;
  const yc = B.centre[1], zc = B.centre[2], pcbLeft = P.centre[0] - P.size[0] / 2;
  const T = batTop, pT = pcbTop, BP = pads.bat_plus, BM = pads.bat_minus;
  // speaker leads: from the two tabs (on the +x side) straight up to the board's underside pads
  const tabZ = S.centre[2] - S.h / 2 + 1.85, under = P.centre[2] - P.size[2] / 2 - 0.1;
  const tab = a => [S.centre[0] + 3.85 * Math.cos(a), S.centre[1] + 3.85 * Math.sin(a), tabZ];
  const sl = [[tab(0.61), pads.spk_plus, 0xb52020], [tab(-0.61), pads.spk_minus, 0x1a1a1a]].map(([t0, pd, col]) =>
    wire([t0, [t0[0] + 0.25, t0[1], t0[2] + 0.9], [pd[0] + 0.3, pd[1], under - 0.6], [pd[0], pd[1], under]], 0.13, col));
  for (const w of sl) { w.position.sub(spk.position); spk.add(w); }

  // ---- LTC4070 (MS8E, KiCad model) on the battery top, NTC (pin 2) linked to VCC (pin 8) ----
  const LT = L.ltc, lx = LT.centre_xy[0], ly = LT.centre_xy[1];
  const ltc = new THREE.Group();
  const ic = (await new VRMLLoader().loadAsync(`/assets/kicad/${LT.model}.wrl`));
  ic.traverse(m => { if (m.isMesh) { const c = m.material.color || new THREE.Color(0x333333), h = {}; c.getHSL(h);
    const metal = h.l > 0.55 && h.s < 0.25;
    m.material = new THREE.MeshPhysicalMaterial({ color: c, roughness: metal ? 0.28 : 0.55, metalness: metal ? 0.9 : 0, clearcoat: metal ? 0 : 0.2 }); m.castShadow = true; } });
  ic.scale.setScalar(L.kicad.units_mm); ltc.add(ic);
  const tip = (pin, side) => [lx + side * LT.lead_tip_x, ly + LT.pins_mm[pin][1], T + 0.12];
  const p8 = tip("8", 1), p5 = tip("5", 1), p2 = tip("2", -1);
  const ntc = wire([p2, [p2[0] + 0.15, p2[1] + 0.1, T + 1.35], [lx, ly + 0.75, T + 1.6], [p8[0] - 0.15, p8[1] - 0.05, T + 1.35], p8], 0.09, 0xe08a1e, 0.35);
  ntc.position.set(-lx, -ly, -T); ltc.add(ntc);
  ntc.userData.pts = [p2, [p2[0] + 0.15, p2[1] + 0.1, T + 1.35], [lx, ly + 0.75, T + 1.6], [p8[0] - 0.15, p8[1] - 0.05, T + 1.35], p8]; ntc.userData.radius = 0.09;                 // built in S, kept relative to the chip
  const joint = new THREE.MeshPhysicalMaterial({ color: 0xcfd2d4, roughness: 0.2, metalness: 1.0 });
  for (const q of [p8, p5, p2]) { const b = new THREE.Mesh(new THREE.SphereGeometry(0.22, 12, 8), joint); b.position.set(q[0] - lx, q[1] - ly, q[2] - T); ltc.add(b); }
  ltc.position.set(lx, ly, T);
  // chip wires: VCC (pin 8) to B+, GND (pin 5) to B-  (final, folded routes)
  const vccRoute = [[p8[0] + 0.12, p8[1], T + 0.2], [-7.3, 1.3, T + 0.75], [-6.9, 1.7, pT + 0.55], [-6.5, 2.0, pT + 0.5], [-6.15, 2.15, pT + 0.3], [BP[0], BP[1], pT - 0.05]];
  const gndRoute = [[p5[0] + 0.12, p5[1], T + 0.2], [-7.3, -1.2, T + 0.75], [-6.9, -1.9, pT + 0.55], [-6.5, -2.35, pT + 0.5], [-6.15, -2.55, pT + 0.3], [BM[0], BM[1], pT - 0.05]];
  const vcc = dynWire(0xc81e1e, 0.15), gnd = dynWire(0x141414, 0.15);
  const ltcWires = new THREE.Group(); ltcWires.add(vcc, gnd);
  function updateLTC({ h, c, fold }) {         // h: chip height above its seat, c: plugged 0..1, fold 0..1
    const carry = p => [p[0], p[1], p[2] + h];
    vcc.userData.set(carriedWire(vccRoute, carry, c, fold, [-0.6, 0.8, 0.25], 0.9));
    gnd.userData.set(carriedWire(gndRoute, carry, c, fold, [-0.6, -0.8, 0.25], 0.9));
  }

  // ---- panel wires: + pad (at -x seen from above) to B+, - pad to B-; routed above the chips, under the panel ----
  const PP = L.panel_pads_xy.plus, PM = L.panel_pads_xy.minus;
  // flat just under the panel, bends sideways (in the panel's plane) and out to the window's sides, then down to the pads
  const plusRoute = [[PP[0], PP[1], -0.24], [PP[0] + 0.15, 0.6, -0.3], [-11.0, 1.5, -0.34], [-12.2, 2.7, -0.36], [-11.0, 4.5, -0.38],
    [-8.5, 4.85, -0.4], [-6.6, 4.4, -0.6], [-6.0, 3.2, -1.4], [BP[0], BP[1], pT - 0.05]];
  const minusRoute = [[PM[0], PM[1], -0.24], [PM[0] - 0.15, -0.6, -0.3], [11.0, -1.5, -0.34], [12.2, -2.7, -0.36], [11.0, -4.8, -0.38],
    [6.0, -5.1, -0.4], [0.0, -5.1, -0.4], [-4.0, -5.0, -0.43], [-5.4, -4.2, -0.9], [-5.85, -3.3, -1.8], [BM[0], BM[1], pT - 0.05]];
  const pRed = dynWire(0xc81e1e, 0.22), pBlk = dynWire(0x141414, 0.22);
  const panelWires = new THREE.Group(); panelWires.add(pRed, pBlk);
  function updatePanelWires({ carry, c, fold }) {   // carry: maps a point of the seated panel to where it is now
    pRed.userData.set(carriedWire(plusRoute, carry, c, fold, [0.3, -1.0, 0.0], 0.9));     // folds sideways, not down
    pBlk.userData.set(carriedWire(minusRoute, carry, c, fold, [0.0, 1.0, 0.0], 1.0));
  }

  for (const o of [bat, board, spk, ltc]) o.userData.final = o.position.clone();

  // ---- battery leads (twisted red/black pair), rebuilt every frame ----
  //   blend 0 = standing up out of the window, ends in the air;  blend 1 = split around the LTC, into the board pads
  const leadMats = [0xc81e1e, 0x141414].map(c => new THREE.MeshPhysicalMaterial({ color: c, roughness: 0.4, clearcoat: 0.6, clearcoatRoughness: 0.3 }));
  const leads = new THREE.Group();
  const leadMeshes = leadMats.map(m => { const o = new THREE.Mesh(new THREE.BufferGeometry(), m); o.castShadow = true; o.userData.radius = 0.26; o.userData.pts = []; leads.add(o); return o; });
  function updateLeads({ batOff, pcbOff, blend, lift = 0, sway = 0 }) {
    const A = xEnd + batOff[0], y0 = yc + batOff[1], z0 = zc + batOff[2], Tb = batTop + batOff[2];
    const pT2 = pcbTop + pcbOff[2];
    const head = [[A + 0.3, y0, z0 + 0.3], [A - 0.8, y0 + 0.2, z0 + 0.7], [A - 0.6, y0 + 0.3, Tb + 0.65], [A + 0.6, y0 + 0.4, Tb + 0.7]];
    const up = [[A + 3.0, y0 + 0.5, Tb + 0.7], [A + 4.6, y0 + 0.5, Tb + 0.72], [A + 6.0, y0 + 0.5 + 0.4 * sway, Tb + 3.5 + 0.5 * lift]];
    const fin = [[A + 2.5, y0 + 0.35, Tb + 0.68], [A + 3.4, y0 + 0.3, Tb + 0.66], [A + 4.0, y0 + 0.2, Tb + 0.58]];
    const mid = up.map((p, i) => mix3(p, fin[i], blend));
    const ends = [[BP, 1], [BM, -1]].map(([pd, s]) => {
      const eu = [[A + 6.6, y0 + s * 0.3 + sway, Tb + 8.5 + lift], [A + 6.75, y0 + s * 0.4 + sway, Tb + 9.4 + lift],
        [A + 6.8, y0 + s * 0.45 + sway, Tb + 9.8 + lift], [A + 6.85, y0 + s * 0.5 + sway, Tb + 10.2 + lift], [A + 6.9, y0 + s * 0.55 + sway, Tb + 10.5 + lift]];
      const ef = [[-13.3, s > 0 ? 1.9 : -1.6, Tb + 0.36], [-11.0, s > 0 ? 3.0 : -2.9, Tb + 0.31], [-8.8, s > 0 ? 3.0 : -3.0, Tb + 0.31],
        [pcbLeft + pcbOff[0] - 0.6, s > 0 ? 2.8 : -2.9, pT2 + 0.4], [pd[0] + pcbOff[0], pd[1] + pcbOff[1], pT2 + 0.25 - 0.35 * blend]];
      return eu.map((p, i) => mix3(p, ef[i], blend));
    });
    const pts = twistedPoints([...head, ...mid], 2.6, ends, 0.26);
    leadMeshes.forEach((m, k) => { m.geometry.dispose(); m.geometry = tubeGeo(pts[k], 0.26); m.userData.pts = pts[k]; });
  }
  return { speaker: spk, battery: bat, pcb: board, leads, updateLeads, ltc, ltcChip: ic, ntc, ltcWires, updateLTC, panelWires, updatePanelWires,
           wires: { leadRed: leadMeshes[0], leadBlack: leadMeshes[1], ltcVCC: vcc, ltcGND: gnd, panelPlus: pRed, panelMinus: pBlk },
           padsS: { BP: [BP[0], BP[1], pT], BM: [BM[0], BM[1], pT], p8, p5, PP: [PP[0], PP[1], 0], PM: [PM[0], PM[1], 0] } };
}

// ---------------- the solar panel (ANYSOLAR SM400K10TF look) ----------------
// front: near-black monocrystalline cells with a fine regular dot pattern, 5 x 2 cells (datasheet drawing: 6.00 x 6.80 mm
// cells, 0.30 gaps, 0.90 side margins), slim grey edge; back: black board, two gold pads, white IXOLAR print (DigiKey photo)
export function buildPanel(cx, cy, ct) {
  const front = canvasTex(33, 15, 72, g => {
    g.fillStyle = "#3a3e45"; g.fillRect(0, 0, 33, 15);
    g.fillStyle = "#0b0c0e"; g.fillRect(0.25, 0.25, 32.5, 14.5);
    for (let i = 0; i < 5; i++) for (let j = 0; j < 2; j++) {
      const x0 = 0.9 + i * 6.3, y0 = 0.55 + j * 7.1;
      const gr = g.createLinearGradient(x0, y0, x0 + 6, y0 + 6.8);
      gr.addColorStop(0, "#0f1013"); gr.addColorStop(0.5, "#0a0b0d"); gr.addColorStop(1, "#0e0f12");
      g.fillStyle = gr; g.fillRect(x0, y0, 6.0, 6.8);
      g.fillStyle = "rgba(140,150,170,0.11)";
      for (let a = 0; a < 6.0 / 0.28; a++) for (let b = 0; b < 6.8 / 0.28; b++) {
        const x = x0 + 0.14 + a * 0.28 + ((b % 2) ? 0.14 : 0), y = y0 + 0.14 + b * 0.28;
        if (x < x0 + 5.95) { g.beginPath(); g.arc(x, y, 0.055, 0, 7); g.fill(); }
      }
    }
  });
  const back = canvasTex(33, 15, 48, g => {
    g.fillStyle = "#141517"; g.fillRect(0, 0, 33, 15);
    g.fillStyle = "#d6b25a";
    for (const x of [3.0, 30.0]) { g.beginPath(); g.arc(x, 7.5, 1.5, 0, 7); g.fill(); }
    text(g, "\u2212", 5.6, 7.5, 2.0, "#f2f2f2", "center", true); text(g, "+", 27.4, 7.5, 2.0, "#f2f2f2", "center", true);
    text(g, "IXOLAR\u2122", 16.5, 10.6, 1.35, "#f2f2f2"); text(g, "SM400K10TF", 16.5, 8.7, 1.35, "#f2f2f2");
    text(g, "R3.0", 16.5, 6.8, 1.35, "#f2f2f2"); text(g, "WWW.ANYSOLAR.BIZ", 16.5, 4.9, 0.95, "#f2f2f2");
  });
  const side = new THREE.MeshPhysicalMaterial({ color: 0x18191c, roughness: 0.35, clearcoat: 0.5 });
  const top = new THREE.MeshPhysicalMaterial({ map: front, roughness: 0.4, metalness: 0.0, clearcoat: 0.6, clearcoatRoughness: 0.18, envMapIntensity: 0.55 });
  const bot = new THREE.MeshPhysicalMaterial({ map: back, roughness: 0.55 });
  const m = new THREE.Mesh(new THREE.BoxGeometry(cx, cy, ct), [side, side, side, side, top, bot]);
  m.castShadow = m.receiveShadow = true;
  return m;
}
