(() => {
  // ../src/data.js
  var TrajectoryData = class {
    constructor(raw2) {
      this.raw = raw2;
      this.s = raw2.samples;
      this.N = raw2.n_samples;
      this.meta = raw2.metadata;
      this.derived = raw2.metadata.derived;
      this.milestones = raw2.milestones;
      this.logr = this.s.log10_r_over_rs;
      this.logrMax = this.logr[0];
      this.logrMin = this.logr[this.N - 1];
      this.columns = Object.keys(this.s);
      this.horizonIndex = this._firstIndexBelow(0);
    }
    _firstIndexBelow(logr) {
      for (let i = 0; i < this.N; i++) if (this.logr[i] <= logr) return i;
      return this.N - 1;
    }
    clampLogR(x) {
      return Math.min(this.logrMax, Math.max(this.logrMin, x));
    }
    // fractional index for a given log10(r/r_s) (binary search on decreasing array)
    indexOf(logr) {
      logr = this.clampLogR(logr);
      let lo = 0, hi = this.N - 1;
      while (hi - lo > 1) {
        const mid = lo + hi >> 1;
        if (this.logr[mid] >= logr) lo = mid;
        else hi = mid;
      }
      const a = this.logr[lo], b = this.logr[hi];
      const t = b === a ? 0 : (logr - a) / (b - a);
      return lo + t;
    }
    // interpolated record at fractional index p
    atIndex(p) {
      const i = Math.max(0, Math.min(this.N - 2, Math.floor(p)));
      const t = Math.max(0, Math.min(1, p - i));
      const out = { index: p };
      for (const k of this.columns) {
        const a = this.s[k][i], b = this.s[k][i + 1];
        if (a === null || b === null || a === void 0 || b === void 0 || typeof a === "string" || typeof b === "string") out[k] = t < 0.5 ? a : b;
        else out[k] = a + (b - a) * t;
      }
      if (out.regime_code !== null) out.regime_code = Math.round(out.regime_code);
      return out;
    }
    at(logr) {
      return this.atIndex(this.indexOf(logr));
    }
    milestone(slug) {
      return this.milestones.find((m) => m.slug === slug);
    }
    // proper-time axis helper (exterior only): logr as a function of tau fraction
    logrForTauFraction(f) {
      const tau = this.s.tau_years;
      const target = f * tau[this.N - 1];
      for (let i = 0; i < this.N - 1; i++) if (tau[i + 1] >= target) {
        const t = (target - tau[i]) / Math.max(1e-300, tau[i + 1] - tau[i]);
        return this.logr[i] + (this.logr[i + 1] - this.logr[i]) * t;
      }
      return this.logrMin;
    }
  };
  var fmt = {
    sci(x, d = 4) {
      if (x === null || x === void 0) return "\u2014";
      if (typeof x === "string") return x;
      if (!isFinite(x)) return x > 0 ? "+\u221E" : "\u2212\u221E";
      if (x === 0) return "0";
      const e = Math.floor(Math.log10(Math.abs(x)));
      if (e >= -3 && e < 6) return x.toPrecision(d);
      const m = x / Math.pow(10, e);
      return `${m.toFixed(d - 1)}e${e}`;
    },
    metres(x) {
      if (x === null || x === void 0) return "\u2014";
      const ly = 9460730472580800, au = 149597870700;
      if (x > 0.1 * ly) return `${fmt.sci(x)} m (${fmt.sci(x / ly, 4)} ly)`;
      if (x > 0.1 * au) return `${fmt.sci(x)} m (${fmt.sci(x / au, 4)} AU)`;
      if (x > 1e3) return `${fmt.sci(x)} m (${fmt.sci(x / 1e3, 4)} km)`;
      if (x >= 1e-9) return `${fmt.sci(x)} m`;
      if (x >= 1e-14) return `${fmt.sci(x)} m (${fmt.sci(x * 1e10, 3)} \xC5)`;
      return `${fmt.sci(x)} m (${fmt.sci(x * 1e15, 3)} fm)`;
    },
    years(x) {
      if (x === null || x === void 0) return "\u2014";
      if (typeof x === "string") return x;
      if (!isFinite(x)) return x > 0 ? "+\u221E" : "\u2212\u221E";
      const s = x * 365.25 * 86400;
      if (Math.abs(x) >= 1) return `${fmt.sci(x)} yr`;
      if (Math.abs(s) >= 1) return `${fmt.sci(s)} s`;
      return `${fmt.sci(s)} s`;
    },
    log10(x) {
      if (x === null || x === void 0) return "\u2014";
      return `10^${x.toFixed(2)}`;
    }
  };

  // ../src/dashboard.js
  var REGIMES = ["CLASSICAL GR \u2014 VALIDATED", "CLASSICAL GR \u2014 EXTREME CURVATURE", "PLANCK-CURVATURE BOUNDARY", "SPECULATIVE QUANTUM MODEL"];
  var Dashboard = class {
    constructor(el, data2) {
      this.el = el;
      this.data = data2;
      const d = data2.derived, cfg = data2.meta.config;
      this.static = {
        "Black-hole mass": `${fmt.sci(cfg.M_solar, 3)} M\u2609 = ${fmt.sci(d.M_kg)} kg`,
        "Schwarzschild radius r_s": `${fmt.sci(d.r_s_m)} m = ${d.r_s_ly.toLocaleString(void 0, { maximumFractionDigits: 0 })} ly`,
        "GM/c\xB3": `${fmt.sci(d.GM_over_c3_years)} yr`,
        "r_QG (K = 1/l_P\u2074)": `${fmt.sci(d.r_QG_m)} m`,
        "Coordinate system": data2.meta.coordinate_system,
        "Integrator": data2.meta.integrator
      };
      this.el.innerHTML = "";
      this.regimeEl = document.createElement("div");
      this.regimeEl.className = "regime r0";
      this.el.appendChild(this.regimeEl);
      this.live = document.createElement("div");
      this.live.className = "kv";
      this.el.appendChild(this.live);
      this.distant = document.createElement("div");
      this.el.appendChild(this.distant);
      this.staticEl = document.createElement("div");
      this.staticEl.className = "kv";
      this.el.appendChild(this.staticEl);
      this.staticEl.innerHTML = '<div class="section" style="grid-column:1/3">Black hole & method</div>' + Object.entries(this.static).map(([k, v]) => `<div class="k">${k}</div><div class="v" style="white-space:normal;text-align:left">${v}</div>`).join("");
    }
    update(smp, state2) {
      const rtol = this.data.meta.config.rtol;
      const reg = state2.speculative ? 3 : smp.regime_code ?? 0;
      this.regimeEl.className = `regime r${reg}`;
      this.regimeEl.textContent = REGIMES[reg];
      const inside = smp.log10_r_over_rs <= 0;
      const stepDesc = smp.mode_is_lnr >= 0.5 ? `\u0394ln r = ${fmt.sci(smp.step_h, 3)}  (\u0394r = ${fmt.sci(smp.step_h * smp.r_m, 3)} m)` : `\u0394\u03C4 = ${fmt.sci(smp.step_h * this.data.derived.M_s, 3)} s`;
      const rows = [
        ["Current r", fmt.metres(smp.r_m)],
        ["Current r / r_s", fmt.sci(smp.r_over_rs, 6)],
        ["log10(r / r_s)", smp.log10_r_over_rs.toFixed(4)],
        ["Proper time elapsed \u03C4", fmt.years(smp.tau_years)],
        ["Proper time since horizon", inside ? fmt.years(smp.tau_since_horizon_years) : "not yet crossed"],
        ["Classical \u03C4 remaining to r = 0", `${fmt.years(smp.tau_to_center_est_years)} (extrapolated GR)`],
        ["Kretschmann K", `${fmt.log10(smp.K_SI_log10)} m\u207B\u2074`],
        ["K / K_Planck", fmt.log10(smp.K_over_Kplanck_log10)],
        ["Curvature length K^(-1/4)", fmt.metres(smp.curvature_length_m)],
        ["Radial tidal acceleration", `${fmt.sci(smp.radial_stretch_m_s2, 3)} m/s\xB2 across ${this.data.meta.config.body_length_m} m (stretch)`],
        ["Transverse tidal acceleration", `${fmt.sci(smp.transverse_compress_m_s2, 3)} m/s\xB2 (compress)`],
        ["Tidal eigenvalues", `${fmt.sci(smp.tidal_radial_SI_per_m, 3)} / ${fmt.sci(smp.tidal_transverse_SI_per_m, 3)} s\u207B\xB2 per m`],
        ["4-velocity (u^v, u^r)", `${fmt.sci(smp.u_v, 5)}, ${fmt.sci(smp.u_r, 5)}`],
        ["Killing energy E", fmt.sci(smp.E_killing, 6)],
        ["Current coordinate system", "ingoing Eddington\u2013Finkelstein (v, r, \u03B8, \u03C6)"],
        ["Numerical timestep", stepDesc],
        ["Local error estimate", `${fmt.sci((smp.err_estimate ?? 0) * rtol, 2)} (rel; tol ${fmt.sci(rtol, 1)})`],
        ["|g(u,u)+1|", fmt.sci(Math.abs(smp.norm_residual ?? 0), 2)],
        ["Light-cone slopes dr/dt_EF", `out ${smp.lc_out_drdtEF.toFixed(4)}, in ${smp.lc_in_drdtEF.toFixed(1)}, worldline ${smp.worldline_drdtEF.toFixed(4)}`]
      ];
      this.live.innerHTML = '<div class="section" style="grid-column:1/3">Infalling observer (proper-time view)</div>' + rows.map(([k, v]) => `<div class="k">${k}</div><div class="v">${v}</div>`).join("");
      const dist = inside ? [
        ["Schwarzschild time t", "\u2192 \u221E at the horizon (coordinate artefact)"],
        ["Signals to infinity", "none: every future light cone points to smaller r"],
        ["Note", "The distant observer never sees the crossing; the infaller crosses in finite proper time."]
      ] : [
        ["Schwarzschild time t", fmt.years(smp.t_schw_years)],
        ["Coordinate velocity dr/dt", `${fmt.sci(smp.dr_dt_schw, 4)} c (\u2192 0 at r_s: apparent freezing)`],
        ["Redshift 1+z of infaller's light", fmt.sci(smp.redshift_1pz_to_infinity, 4)]
      ];
      this.distant.innerHTML = '<div class="section">Distant observer (Schwarzschild coordinates)</div><div class="kv">' + dist.map(([k, v]) => `<div class="k">${k}</div><div class="v" style="white-space:normal;text-align:left">${v}</div>`).join("") + "</div>";
    }
  };

  // ../src/scene3d.js
  var Scene3dView = class {
    constructor(container, data2, opts = {}) {
      this.container = container;
      this.data = data2;
      this.opts = opts;
      this.el = document.createElement("div");
      this.el.className = "overlay";
      this.el.textContent = "scene3d view: not implemented yet";
      container.appendChild(this.el);
    }
    update(sample, state2) {
    }
    resize() {
    }
    setMode(mode) {
    }
    dispose() {
    }
  };

  // ../src/causal.js
  var CausalView = class {
    constructor(container, data2, opts = {}) {
      this.container = container;
      this.data = data2;
      this.opts = opts;
      this.el = document.createElement("div");
      this.el.className = "overlay";
      this.el.textContent = "causal view: not implemented yet";
      container.appendChild(this.el);
    }
    update(sample, state2) {
    }
    resize() {
    }
    setMode(mode) {
    }
    dispose() {
    }
  };

  // ../src/firstperson.js
  var FirstpersonView = class {
    constructor(container, data2, opts = {}) {
      this.container = container;
      this.data = data2;
      this.opts = opts;
      this.el = document.createElement("div");
      this.el.className = "overlay";
      this.el.textContent = "firstperson view: not implemented yet";
      container.appendChild(this.el);
    }
    update(sample, state2) {
    }
    resize() {
    }
    setMode(mode) {
    }
    dispose() {
    }
  };

  // ../src/speculative.js
  var SpeculativeView = class {
    constructor(container, data2, opts = {}) {
      this.container = container;
      this.data = data2;
      this.opts = opts;
      this.el = document.createElement("div");
      this.el.className = "overlay";
      this.el.textContent = "speculative view: not implemented yet";
      container.appendChild(this.el);
    }
    update(sample, state2) {
    }
    resize() {
    }
    setMode(mode) {
    }
    dispose() {
    }
  };

  // ../src/main.js
  var raw = window.SLAB_DATA;
  var data = new TrajectoryData(raw);
  var $ = (id) => document.getElementById(id);
  var state = {
    logr: data.logrMax,
    // current position: log10(r / r_s)
    playing: false,
    speedDecPerS: 2,
    axis: "logr",
    view: "scene",
    sceneMode: "log",
    // log | linear | horizon | deep | curvature
    camera: "third",
    // third | first
    speculative: false,
    sample: null
  };
  var dashboard = new Dashboard($("dashboard"), data);
  var views = {
    scene: new Scene3dView($("view-scene"), data, { controls: $("controls") }),
    causal: new CausalView($("view-causal"), data, {}),
    fp: new FirstpersonView($("view-fp"), data, {}),
    spec: new SpeculativeView($("view-spec"), data, {})
  };
  function setView(name) {
    state.view = name;
    state.speculative = name === "spec";
    document.querySelectorAll("header .tabs button").forEach((b) => b.classList.toggle("active", b.dataset.view === name));
    document.querySelectorAll(".view").forEach((v) => v.classList.toggle("active", v.id === `view-${name}`));
    $("banner").classList.toggle("hidden", !(name === "scene" && state.sceneMode !== "linear" && state.sceneMode !== "horizon"));
    $("spec-banner").classList.toggle("hidden", name !== "spec");
    views[name].resize();
    render(true);
  }
  function setLogR(x) {
    state.logr = data.clampLogR(x);
    render(true);
  }
  function setSceneMode(mode) {
    state.sceneMode = mode;
    views.scene.setMode(mode);
    $("banner").classList.toggle("hidden", !(state.view === "scene" && mode !== "linear" && mode !== "horizon"));
    render(true);
  }
  function render(force) {
    const smp = data.at(state.logr);
    state.sample = smp;
    dashboard.update(smp, state);
    const frac = (data.logrMax - state.logr) / (data.logrMax - data.logrMin);
    $("slider").value = String(frac);
    $("pos").textContent = `log10(r/r_s) = ${state.logr.toFixed(3)}   r = ${fmt.sci(smp.r_m, 3)} m`;
    const atEnd = state.logr <= data.logrMin + 1e-9;
    $("planck").classList.toggle("hidden", !(atEnd && !state.speculative));
    $("planck").textContent = raw.planck_message;
    views[state.view].update(smp, state);
  }
  var last = performance.now();
  function loop(now) {
    const dt = (now - last) / 1e3;
    last = now;
    if (state.playing) {
      if (state.axis === "logr") state.logr -= state.speedDecPerS * dt;
      else {
        const frac = (data.logrMax - state.logr) / (data.logrMax - data.logrMin);
        const tau = data.at(state.logr).tau_years, tauEnd = data.s.tau_years[data.N - 1];
        const f = Math.min(1, tau / tauEnd + 0.02 * state.speedDecPerS * dt);
        state.logr = data.logrForTauFraction(f);
      }
      if (state.logr <= data.logrMin) {
        state.logr = data.logrMin;
        state.playing = false;
        $("play").textContent = "\u25B6 Play";
      }
      render(false);
    } else if (state.view === "scene" || state.view === "fp") {
      views[state.view].update(state.sample || data.at(state.logr), state);
    }
    requestAnimationFrame(loop);
  }
  document.querySelectorAll("header .tabs button").forEach((b) => b.addEventListener("click", () => setView(b.dataset.view)));
  $("play").addEventListener("click", () => {
    state.playing = !state.playing;
    $("play").textContent = state.playing ? "\u275A\u275A Pause" : "\u25B6 Play";
    if (state.playing && state.logr <= data.logrMin) state.logr = data.logrMax;
  });
  $("speed").addEventListener("change", (e) => {
    state.speedDecPerS = parseFloat(e.target.value);
  });
  $("axis").addEventListener("change", (e) => {
    state.axis = e.target.value;
  });
  $("slider").addEventListener("input", (e) => {
    const f = parseFloat(e.target.value);
    state.playing = false;
    $("play").textContent = "\u25B6 Play";
    setLogR(data.logrMax - f * (data.logrMax - data.logrMin));
  });
  window.addEventListener("resize", () => {
    Object.values(views).forEach((v) => v.resize());
    render(true);
  });
  window.addEventListener("keydown", (e) => {
    if (e.key === " ") {
      $("play").click();
      e.preventDefault();
    }
    if (e.key === "ArrowRight") setLogR(state.logr - 0.25);
    if (e.key === "ArrowLeft") setLogR(state.logr + 0.25);
    if (e.key >= "1" && e.key <= "4") setView(["scene", "causal", "fp", "spec"][parseInt(e.key) - 1]);
  });
  {
    const s = raw.summary;
    $("validation").innerHTML = `steps ${s.n_steps_total}, RHS evals ${s.n_rhs_evals_total}, rejected ${s.n_rejected_total}<br>max |g(u,u)+1| = ${fmt.sci(s.max_abs_norm_residual, 2)}; max conditioned E drift = ${fmt.sci(s.max_E_drift_conditioned, 2)}<br>\u03C4(horizon\u2192r_QG) = ${fmt.years(s.tau_since_horizon_years_at_end)} (analytic 4GM/3c\xB3 = ${fmt.years(data.derived.tau_horizon_to_singularity_years)})<br>See validation_report.json for TESTS 0\u20138.`;
  }
  window.SLAB_APP = {
    state,
    data,
    setView,
    setLogR,
    setSceneMode,
    views,
    render,
    setCamera(c) {
      state.camera = c;
      render(true);
    },
    jumpTo(slug) {
      const m = data.milestone(slug);
      if (m) setLogR(m.log10_r_over_rs);
    }
  };
  setView("scene");
  render(true);
  requestAnimationFrame(loop);
})();
