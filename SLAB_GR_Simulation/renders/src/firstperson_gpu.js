// OPTIONAL first-person GPU path: per-pixel EF null geodesics in a GLSL fragment shader (32-bit floats).
// Created ONLY when the user explicitly selects 'GPU (float32, r > 1e-5 r_s)'; the default renderer is the
// double-precision CPU path (firstperson_cpu.js), which needs no WebGL.  Float32 cannot represent the ray state
// below r ~ 1e-5 r_s (R_MIN_GPU); the view then falls back to the CPU renderer (labelled).
// Background: RA/Dec coordinate grid in the same celestial frame as the CPU path (no star catalogue on the GPU).
// Classification: the exact rule of firstperson_core.js classify() (incl. the interior b^2 < 27 condition).
import * as THREE from 'three';

export const R_MIN_GPU = 2e-5;     // geometrized (= 1e-5 r_s)

const FRAG = `
precision highp float; precision highp int;
uniform vec2 uRes; uniform float uR, uUv, uUr, uE; uniform vec3 uCamF, uCamR, uCamU; uniform float uTanH, uTanV;
uniform int uMaxSteps; uniform float uCh, uRsky; uniform mat3 uMcel;
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
float gridLine(float x, float stepRad, float hw) { float d = abs(x - floor(x / stepRad + 0.5) * stepRad); return max(0.0, 1.0 - d / hw); }
void main() {
  vec2 ndc = (gl_FragCoord.xy / uRes) * 2.0 - 1.0;
  vec3 d = normalize(uCamF + ndc.x * uTanH * uCamR + ndc.y * uTanV * uCamU);
  float dn = d.x; float dperp = length(d.yz); vec2 tdir = dperp > 1e-9 ? d.yz / dperp : vec2(1.0, 0.0);
  float f0 = fOf(uR); float nn = -f0*uUv*uUv + 2.0*uUv*uE; float N = sqrt(max(nn, 1e-30));
  float nv = uUv / N, nr = uE / N;
  vec3 p = vec3(0.0, uR, 0.0);
  vec3 k = vec3(-uUv + dn*nv, -uUr + dn*nr, dperp / uR);
  float Eph = uE + dn * abs(uUr);                   // exact E_ph = E + a dn (a = |u^r|)
  float Lp = uR*dperp; float b2 = (Lp*Lp)/(Eph*Eph);
  bool past = (uR < 2.0) ? !(Eph > 0.0 && b2 < 27.0) : ((k.y < 0.0) ? (uR <= 3.0 || b2 <= 27.0) : (uR < 3.0 && b2 > 27.0));
  int kind = 2; float psiInf = 0.0;
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
    vec3 s = vec3(cos(psiInf), sin(psiInf) * tdir.x, sin(psiInf) * tdir.y);
    vec3 S = uMcel * s;
    float dec = asin(clamp(S.z, -1.0, 1.0)), ra = atan(S.y, S.x);
    float I = min(1.0, gridLine(dec, 0.261799, 0.006) + gridLine(ra, 0.261799, 0.006 / max(0.05, cos(dec))));
    col = vec3(0.02, 0.03, 0.06) + vec3(0.4, 0.55, 0.85) * I;
    float g = 1.0 / Eph;
    float bq = clamp(g, 0.45, 4.0);
    vec3 tint = g > 1.0 ? mix(vec3(1.0), vec3(0.6, 0.75, 1.0), clamp((g - 1.0) * 0.5, 0.0, 1.0)) : mix(vec3(1.0), vec3(1.0, 0.45, 0.35), clamp((1.0 - g) * 1.5, 0.0, 1.0));
    col *= tint * bq;
  } else if (kind == 1) { col = vec3(0.075, 0.012, 0.012); }
  else { col = vec3(0.6, 0.0, 0.6); }
  gl_FragColor = vec4(col, 1.0);
}`;
const VERT = `void main() { gl_Position = vec4(position, 1.0); }`;

// Cheap availability test that does NOT create a WebGL context.
export function webglAvailable() { return typeof window !== 'undefined' && (typeof window.WebGL2RenderingContext !== 'undefined' || typeof window.WebGLRenderingContext !== 'undefined'); }

export class GpuTracer {
  constructor(container) {
    this.renderer = new THREE.WebGLRenderer({ antialias: false, powerPreference: 'low-power', preserveDrawingBuffer: true });
    this.renderer.setPixelRatio(1);
    this.canvas = this.renderer.domElement;
    this.canvas.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;';
    container.appendChild(this.canvas);
    this.scene = new THREE.Scene(); this.camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    this.uniforms = {
      uRes: { value: new THREE.Vector2(1, 1) }, uR: { value: 200 }, uUv: { value: 1 }, uUr: { value: -0.1 }, uE: { value: 1 },
      uCamF: { value: new THREE.Vector3() }, uCamR: { value: new THREE.Vector3() }, uCamU: { value: new THREE.Vector3() },
      uTanH: { value: 1 }, uTanV: { value: 1 }, uMaxSteps: { value: 900 }, uCh: { value: 0.05 }, uRsky: { value: 400 },
      uMcel: { value: new THREE.Matrix3() },
    };
    const mat = new THREE.ShaderMaterial({ uniforms: this.uniforms, vertexShader: VERT, fragmentShader: FRAG, depthTest: false, depthWrite: false });
    this.scene.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), mat));
  }
  setSize(w, h) { this.renderer.setSize(w, h, false); }
  render(obs, cam, M) {
    const u = this.uniforms, c = this.canvas;
    u.uRes.value.set(c.width, c.height);
    u.uR.value = obs.r; u.uUv.value = obs.uv; u.uUr.value = obs.ur; u.uE.value = obs.E;
    u.uCamF.value.set(...cam.F); u.uCamR.value.set(...cam.R); u.uCamU.value.set(...cam.U);
    u.uTanH.value = cam.tanH; u.uTanV.value = cam.tanV;
    u.uMcel.value.fromArray(Array.from(M));
    this.renderer.render(this.scene, this.camera);
  }
  dispose() { this.renderer.dispose(); this.canvas.remove(); }
}
