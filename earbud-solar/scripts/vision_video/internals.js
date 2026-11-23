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
    g.fillStyle = "#0e3a1f"; for (const v of [[-1.0, 0.4], [6.6, 3.4], [6.6, -3.1], [10.6, 0.6], [0.8, -2.0], [5.0, 1.8]]) { g.beginPath(); g.arc(v[0] + ox, v[1] + oy, 0.16, 0, 7); g.fill(); }
    g.strokeStyle = "#eef2ee"; g.lineWidth = 0.09;                                           // silkscreen
    for (const q of parts) {
      if (q.model.startsWith("C_0402") || q.model.startsWith("R_0402") || q.model.startsWith("LED")) continue;
      if (q.ref === "U2") continue;
      const lab = { U1: [-3.4, 2.6], U3: [0, 1.5], Y1: [0, -1.6], L1: [1.4, 0], C1: [0, 1.3], C2: [0, 1.3] }[q.ref] || [0, 1.2];
      text(g, q.ref, q.xy[0] + ox + lab[0], q.xy[1] + oy + lab[1], 0.62, "#eef2ee");
    }
    const u2p = at("U2"); text(g, "LTC4070", u2p[0] + ox, u2p[1] + oy + 3.3, 0.62, "#eef2ee", "center", true);
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
  for (const k of ["bat_plus", "bat_minus"]) {
    const b = new THREE.Mesh(new THREE.SphereGeometry(0.55, 16, 10), solder); b.scale.z = 0.45;
    b.position.set(pads[k][0] - cx, pads[k][1] - cy, T / 2 + 0.12); grp.add(b);
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
  for (const sx of [-1, 1]) { const t = new THREE.Mesh(new THREE.BoxGeometry(0.9, 1.3, 0.2), gold); t.position.set(sx * 3.85, 0, -h / 2 + 1.75); g.add(t); }
  g.position.set(...S.centre);
  return g;
}

export async function buildInternals(L) {
  const B = L.battery, P = L.pcb, S = L.speaker, pads = L.pads;
  const bat = battery(B), board = await pcb(P, L.parts, pads, L.kicad.units_mm), spk = speaker(S);
  const pcbTop = P.centre[2] + P.size[2] / 2, batTop = B.centre[2] + B.size[2] / 2, xEnd = B.centre[0] - B.size[0] / 2;
  // battery leads: out of the kapton end, up and back over the label, twisted, up onto the board pads
  const path = [[xEnd + 0.4, B.centre[1], B.centre[2] + 0.3], [xEnd - 0.7, B.centre[1] + 0.2, B.centre[2] + 0.9],
    [xEnd + 0.4, B.centre[1] + 0.4, batTop + 0.35], [xEnd + 6, B.centre[1] + 0.5, batTop + 0.33], [P.centre[0] - P.size[0] / 2 - 2.8, 0.2, batTop + 0.35]];
  const [red, blk] = twistedPair(path, 15.5, 2.6, [
    [[P.centre[0] - P.size[0] / 2 - 0.9, pads.bat_plus[1] * 0.7, pcbTop + 0.35], [pads.bat_plus[0], pads.bat_plus[1], pcbTop + 0.25]],
    [[P.centre[0] - P.size[0] / 2 - 0.9, pads.bat_minus[1] * 0.7, pcbTop + 0.35], [pads.bat_minus[0], pads.bat_minus[1], pcbTop + 0.25]],
  ], 0.26, [0xc81e1e, 0x141414]);
  for (const w of [red, blk]) { w.position.sub(bat.position); bat.add(w); }
  // speaker leads: from the tabs up to the board's underside
  const tabZ = S.centre[2] - S.h / 2 + 1.85, under = P.centre[2] - P.size[2] / 2 - 0.1;
  const sr = wire([[S.centre[0] + 3.85, S.centre[1], tabZ], [S.centre[0] + 4.3, S.centre[1] + 0.8, tabZ + 0.9], [pads.spk_plus[0] + 0.3, pads.spk_plus[1], under - 0.4], [pads.spk_plus[0], pads.spk_plus[1], under]], 0.13, 0xb52020);
  const sb = wire([[S.centre[0] - 3.85, S.centre[1], tabZ], [S.centre[0] - 3.2, S.centre[1] - 1.2, tabZ + 1.0], [pads.spk_minus[0] - 1.5, pads.spk_minus[1], under - 0.5], [pads.spk_minus[0], pads.spk_minus[1], under]], 0.13, 0x1a1a1a);
  for (const w of [sr, sb]) { w.position.sub(spk.position); spk.add(w); }
  for (const o of [bat, board, spk]) o.userData.final = o.position.clone();
  return { speaker: spk, battery: bat, pcb: board };
}
