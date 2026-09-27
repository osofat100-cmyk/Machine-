// First-person camera: celestial sphere, backgrounds, star images, colour maps (pure JavaScript, Node-importable).
//
// VISUALIZATION APPROXIMATIONS (all labelled in the viewer):
//  * the sky is the Earth's J2000 sky (bright-star list from d3-celestial, see starcatalog.js) placed at
//    infinity around the hole; the hole's direction is put at a FIXED, ILLUSTRATIVE celestial position
//    (the J2000 position of Sagittarius A*).  The SLAB is hypothetical (its r_s = 312,000 ly exceeds the size of
//    the Milky Way), so this is a backdrop, not a prediction of what a real observer would see;
//  * stars are treated as blackbodies with T from B-V (Ballesteros 2012, EPL 97, 34008; formula confirmed by web
//    search); a frequency shift g maps a blackbody of temperature T to one of temperature g T (EXACT), so the
//    shifted colour and the visible-band luminance change are taken from the blackbody table
//    (data/blackbody_srgb.js: Planck x tabulated CIE 1931 colour-matching functions);
//  * star brightness on screen: m_obs = m - 2.5 log10( mu * Y(gT)/Y(T) ), mu = dOmega_obs/dOmega_sky the
//    lensing/aberration magnification of the image (from the transfer table), then a display mapping
//    (LABELLING CONVENTION: a limiting magnitude + exposure setting, not a photometric model of an eye/camera);
//  * the coordinate grid and its colour tint are qualitative.
import { BLACKBODY, BB_LOGT0, BB_DLOGT } from './data/blackbody_srgb.js';

const D2R = Math.PI / 180;

// Illustrative placement of the black hole on the celestial sphere: J2000 position of Sgr A*
// (RA 17h45m40.0409s, Dec -29d00'28.118" — confirmed by web search; used only as a backdrop orientation).
export const HOLE_DIRECTION = { ra_deg: 266.416837, dec_deg: -29.007811, label: 'Sgr A* direction (illustrative placement)' };

export function raDecToVec(raDeg, decDeg) {
  const ra = raDeg * D2R, de = decDeg * D2R;
  return [Math.cos(de) * Math.cos(ra), Math.cos(de) * Math.sin(ra), Math.sin(de)];
}

// Rotation from the observer's tetrad basis (n = outward radial, theta-hat, phi-hat) to celestial J2000
// Cartesian axes.  n -> X = anti-hole direction, -theta-hat (screen 'up' when looking at the hole) -> the
// projection of the celestial north pole onto the plane orthogonal to X, phi-hat -> X x theta-hat-image
// (a proper rotation: in flat space the sky direction of a view direction d is M d, no mirror image).
export function celestialFrame(hole = HOLE_DIRECTION) {
  const H = raDecToVec(hole.ra_deg, hole.dec_deg);
  const X = [-H[0], -H[1], -H[2]];
  const z = [0, 0, 1], zx = z[0] * X[0] + z[1] * X[1] + z[2] * X[2];
  let N = [z[0] - zx * X[0], z[1] - zx * X[1], z[2] - zx * X[2]];
  const nN = Math.hypot(...N); N = N.map(v => v / nN);
  const T = [-N[0], -N[1], -N[2]];                                  // image of theta-hat
  const P = [X[1] * T[2] - X[2] * T[1], X[2] * T[0] - X[0] * T[2], X[0] * T[1] - X[1] * T[0]];   // image of phi-hat
  // column-major: M[0..2] = X, M[3..5] = T, M[6..8] = P
  return Float64Array.from([...X, ...T, ...P]);
}

// ---------------------------------------------------------------------------------------------
// Blackbody colours
// Ballesteros (2012), EPL 97, 34008:  T = 4600 K [ 1/(0.92 (B-V) + 1.7) + 1/(0.92 (B-V) + 0.62) ]
export function bvToTemperature(bv) {
  if (bv === null || !isFinite(bv)) bv = 0.6;
  return 4600 * (1 / (0.92 * bv + 1.7) + 1 / (0.92 * bv + 0.62));
}

// {logY, r, g, b} for temperature T (K).  Below 10^2.5 K: Y -> 0 (Wien tail, treated as invisible);
// above 10^7 K: Rayleigh-Jeans, Y proportional to T with the limiting chromaticity.
const BB_N = BLACKBODY.length, BB_LOGT1 = BB_LOGT0 + (BB_N - 1) * BB_DLOGT;
export function blackbody(T, out = {}) {
  const lt = Math.log10(T);
  if (!(lt >= BB_LOGT0)) { out.logY = -Infinity; out.r = 1; out.g = 0; out.b = 0; return out; }
  if (lt >= BB_LOGT1) { const e = BLACKBODY[BB_N - 1]; out.logY = e[1] + (lt - BB_LOGT1); out.r = e[2]; out.g = e[3]; out.b = e[4]; return out; }
  const x = (lt - BB_LOGT0) / BB_DLOGT, i = Math.min(BB_N - 2, Math.floor(x)), t = x - i;
  const a = BLACKBODY[i], c = BLACKBODY[i + 1];
  out.logY = a[1] + t * (c[1] - a[1]); out.r = a[2] + t * (c[2] - a[2]); out.g = a[3] + t * (c[3] - a[3]); out.b = a[4] + t * (c[4] - a[4]);
  return out;
}

// ---------------------------------------------------------------------------------------------
// Frequency-shift false colour: diverging map of log10 g on [-L, L] (red = redshift, blue = blueshift).
const GSTOPS = [[-1, 0.30, 0.00, 0.05], [-0.66, 0.72, 0.08, 0.10], [-0.33, 1.00, 0.55, 0.30], [0, 0.93, 0.93, 0.93],
  [0.33, 0.45, 0.70, 1.00], [0.66, 0.15, 0.30, 0.85], [1, 0.12, 0.00, 0.38]];
export function gColor(log10g, L, out = [0, 0, 0]) {
  let t = log10g / L; if (!(t > -1)) t = -1; if (t > 1) t = 1;
  let i = 0; while (i < GSTOPS.length - 2 && t > GSTOPS[i + 1][0]) i++;
  const a = GSTOPS[i], c = GSTOPS[i + 1], u = (t - a[0]) / (c[0] - a[0]);
  out[0] = a[1] + u * (c[1] - a[1]); out[1] = a[2] + u * (c[2] - a[2]); out[2] = a[3] + u * (c[3] - a[3]);
  return out;
}
// Symmetric colour-scale half-range for an observer: the extreme log10 g over all sky directions
// (g = 1/(E + a dn) is monotone in dn, so the extremes are at dn = 1 and at the lowest sky direction dnMin).
export function gScaleRange(obs, dnMin) {
  const l1 = Math.abs(Math.log10(1 / (obs.E + obs.a)));
  const Emin = obs.E + obs.a * dnMin;
  const l2 = Emin > 0 ? Math.abs(Math.log10(1 / Emin)) : 0;
  const raw = Math.max(l1, l2);
  if (raw <= 2) return Math.max(0.25, Math.ceil(raw * 4) / 4);
  return Math.ceil(raw);
}

// Qualitative tint of the background by g (LABELLED qualitative: not a radiometric model).
export function qualitativeTint(g, out = [1, 1, 1]) {
  const b = Math.min(4, Math.max(0.45, g));
  if (g > 1) { const u = Math.min(1, (g - 1) * 0.5); out[0] = (1 - 0.4 * u) * b; out[1] = (1 - 0.25 * u) * b; out[2] = b; }
  else { const u = Math.min(1, (1 - g) * 1.5); out[0] = b; out[1] = (1 - 0.55 * u) * b; out[2] = (1 - 0.65 * u) * b; }
  return out;
}

// ---------------------------------------------------------------------------------------------
// Coordinate grid on the celestial sphere (RA/Dec lines every `stepDeg`) with anti-aliasing: `pixSky` is the
// angular size of the pixel on the sky (radians); when it exceeds the line spacing the grid fades to its mean.
// Returns intensity in [0, 1] in out[0], marker code in out[1] (1 = hole direction, 2 = anti-hole, 0 none).
const HOLE_VEC = raDecToVec(HOLE_DIRECTION.ra_deg, HOLE_DIRECTION.dec_deg);
export function gridShade(S, stepDeg, pixSky, out = [0, 0]) {
  const step = stepDeg * D2R, base = 0.0045;                     // line half-width 0.26 deg
  const dec = Math.asin(Math.max(-1, Math.min(1, S[2]))), ra = Math.atan2(S[1], S[0]);
  const hw = Math.max(base, 0.6 * pixSky);
  let I = 0;
  if (hw > 0.5 * step) I = Math.min(1, 2 * base / step * 2);     // unresolved: mean coverage of two line families
  else {
    const dd = Math.abs(dec - Math.round(dec / step) * step);
    const dr = Math.abs(ra - Math.round(ra / step) * step) * Math.cos(dec);
    const w = base / hw;                                          // energy-conserving widening
    I = Math.max(0, 1 - dd / hw) * w + Math.max(0, 1 - dr / hw) * w;
    if (Math.abs(dec) < hw) I += 0.6 * (1 - Math.abs(dec) / hw) * w;   // celestial equator emphasized
    I = Math.min(1, I);
  }
  // markers: 2.5 deg rings (no filled centre: deep inside, the whole outward hemisphere is a hugely magnified image
  // of a ~1e-18 rad patch around the anti-hole direction, and a filled dot would then paint the entire view)
  const c = S[0] * HOLE_VEC[0] + S[1] * HOLE_VEC[1] + S[2] * HOLE_VEC[2];
  const ang = Math.acos(Math.max(-1, Math.min(1, Math.abs(c))));
  const ringR = 2.5 * D2R;
  out[1] = 0;
  // markers only where the pixel resolves them (else a single pixel covering many degrees of sky would be painted)
  if (pixSky < 0.3 * ringR && Math.abs(ang - ringR) < Math.max(base, 0.6 * pixSky)) out[1] = c > 0 ? 1 : 2;
  out[0] = I;
  return out;
}

// ---------------------------------------------------------------------------------------------
// Star images.  For a star at celestial direction S: in the tetrad, cos(Psi) = n.s and the azimuth unit
// vector t = s_perp/|s_perp|.  A ray at elevation alpha and azimuth +t reaches the sky at angle psi(alpha) from
// n towards t, so images satisfy psi(alpha) = Psi + 2 pi k (azimuth +t) or psi(alpha) = 2 pi - Psi + 2 pi k
// (azimuth -t).  All solutions are found on the piecewise-linear transfer table (every order k that the table
// resolves).  Magnification mu = dOmega_obs/dOmega_sky = cos(alpha) |d alpha| / (sin(psi) |d psi|).
export function starImages(table, stars, M, opts = {}) {
  const obs = table.obs, P = table.p, PSI = table.psi, K = table.kind, N = P.length;
  const images = [];
  const bb = {}, bb0 = {};
  const maxOrder = opts.maxOrder ?? 6;
  for (let si = 0; si < stars.length; si++) {
    const st = stars[si];
    const S = st.vec;
    // tetrad components s = M^T S
    const s0 = M[0] * S[0] + M[1] * S[1] + M[2] * S[2];
    const s1 = M[3] * S[0] + M[4] * S[1] + M[5] * S[2];
    const s2 = M[6] * S[0] + M[7] * S[1] + M[8] * S[2];
    const sp = Math.hypot(s1, s2);
    const Psi = Math.atan2(sp, s0);
    const t1 = sp > 0 ? s1 / sp : 1, t2 = sp > 0 ? s2 / sp : 0;
    for (let i = 0; i + 1 < N; i++) {
      if (K[i] !== 0 || K[i + 1] !== 0) continue;
      const pa = PSI[i], pb = PSI[i + 1];
      const lo = Math.min(pa, pb), hi = Math.max(pa, pb);
      for (let side = 0; side < 2; side++) {
        const base = side === 0 ? Psi : 2 * Math.PI - Psi;
        let k = Math.ceil((lo - base) / (2 * Math.PI));
        for (; k <= maxOrder; k++) {
          const target = base + 2 * Math.PI * k;
          if (target > hi) break;
          if (target < lo || pb === pa) continue;
          const u = (target - pa) / (pb - pa);
          const p = P[i] + u * (P[i + 1] - P[i]);
          const dir = table.directionOf(p);
          // frequency ratio: alpha table -> from dn; b table -> E_ph = r dperp / b (accurate in the deep band)
          const Eph = table.param === 'b' ? obs.r * dir.dperp / p : obs.E + obs.a * dir.dn;
          const g = 1 / Eph;
          const slopeP = (pb - pa) / (P[i + 1] - P[i]);                // dpsi/dparam
          const dPdAlpha = table.param === 'b' ? obs.r * (obs.E * dir.dn + obs.a) / (Eph * Eph) : 1;   // |db/dalpha|
          const mu = Math.min(1e8, Math.abs(dir.dperp) / Math.max(1e-300, Math.abs(Math.sin(target)) * Math.abs(slopeP) * dPdAlpha));
          blackbody(st.T * g, bb); blackbody(st.T, bb0);
          const logF = Math.log10(mu) + (bb.logY - bb0.logY);          // visible-band flux ratio
          const mObs = st.mag - 2.5 * logF;
          const sgn = side === 0 ? 1 : -1;
          images.push({ star: si, order: k, dn: dir.dn, d: [dir.dn, dir.dperp * sgn * t1, dir.dperp * sgn * t2], g, mu, mObs, r: bb.r, gg: bb.g, b: bb.b });
        }
      }
    }
  }
  return images;
}
