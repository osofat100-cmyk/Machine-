# references.md — annotated bibliography

**Verification status.** This project was built in an environment with no web access to
journals, NIST or NASA. Every entry below is given from the author's knowledge and is marked
**NOT RE-VERIFIED ONLINE IN THIS SESSION**. Bibliographic details the author is not certain of
are marked **INSUFFICIENT DATA TO VERIFY** instead of being guessed; no DOIs are given for that
reason. A later session with network access should re-verify each entry (see the upgrade prompt
in `docs/UPGRADE_PROMPT.md`).

Tags: what each source is used for in this project.

## 1. NASA / NASA Goddard black-hole visualization materials

* **NASA Goddard Space Flight Center Scientific Visualization Studio, "Black Hole Visualization"
  (J. Schnittman, 2019)** — ray-traced images of a Schwarzschild-like black hole with a thin
  accretion disk showing the photon ring, the lensed far side of the disk and Doppler beaming.
  Used only as a *qualitative visual reference* for the first-person camera (shape of the shadow,
  lensed sky). NOT RE-VERIFIED ONLINE IN THIS SESSION.
* **NASA Goddard, "NASA Simulation's Plunge Into a Black Hole" 360° visualizations
  (J. Schnittman & B. Powell, 2024)** — camera plunging through the event horizon of a
  supermassive black hole. Same use as above: methodology reference for a first-person infall
  rendering. NOT RE-VERIFIED ONLINE IN THIS SESSION.
* Scope statement (required by the brief): these visualizations validate *established exterior
  GR* and *visualization methodology* only. They say nothing about the interior beyond the
  classical description and nothing about quantum gravity; they are never cited here as evidence
  about physics at or beyond r_QG.

## 2. Einstein Toolkit

* **Einstein Toolkit documentation, https://einsteintoolkit.org** (Löffler et al., Class.
  Quantum Grav. 29, 115001 (2012) is the standard reference paper — INSUFFICIENT DATA TO VERIFY
  page/DOI). Referenced as the community standard for numerical-relativity methodology
  (evolution of the Einstein equations on a grid). Not used directly: this project integrates
  test-particle worldlines on the exact Schwarzschild background, which is an ODE problem.
  NOT RE-VERIFIED ONLINE IN THIS SESSION.

## 3. Peer-reviewed general-relativity references

* **K. Schwarzschild (1916), Sitzungsberichte der Königlich Preußischen Akademie der
  Wissenschaften, 189–196** — the exact vacuum solution. Used for: the metric (§2 of
  physics_notes.md). NOT RE-VERIFIED ONLINE IN THIS SESSION.
* **A. S. Eddington (1924), Nature 113, 192** — the coordinate transformation that removes the
  horizon singularity (advanced-time form). Used for: the ingoing EF chart.
  NOT RE-VERIFIED ONLINE IN THIS SESSION.
* **D. Finkelstein (1958), Phys. Rev. 110, 965** — "Past-future asymmetry of the gravitational
  field of a point particle": interpretation of the horizon as a one-way membrane in EF
  coordinates. Used for: horizon crossing, light-cone tilting.
  NOT RE-VERIFIED ONLINE IN THIS SESSION.
* **M. D. Kruskal (1960), Phys. Rev. 119, 1743** and **G. Szekeres (1960), Publ. Math. Debrecen
  7, 285** — maximal analytic extension; Kruskal–Szekeres coordinates. Used for: the causal
  diagram (§7). NOT RE-VERIFIED ONLINE IN THIS SESSION.
* **R. C. Henry (2000), Astrophys. J. 535, 350** — "Kretschmann scalar for a Kerr–Newman black
  hole" (gives the Schwarzschild limit 48 M²/r⁶). Used for: TEST 5.
  NOT RE-VERIFIED ONLINE IN THIS SESSION.
* **G. F. Lewis & J. Kwan (2007), Publ. Astron. Soc. Aust. 24, 46** — "No way back: maximizing
  survival time below the Schwarzschild event horizon": inside the horizon the free-fall geodesic
  maximizes the remaining proper time; thrust shortens it. Used for: the propulsion-mode notes
  (§6). NOT RE-VERIFIED ONLINE IN THIS SESSION.
* **J. R. Dormand & P. J. Prince (1980), J. Comput. Appl. Math. 6, 19** — the RK5(4) pair used by
  the integrator. NOT RE-VERIFIED ONLINE IN THIS SESSION.

## 4. Textbooks

* **C. W. Misner, K. S. Thorne & J. A. Wheeler, *Gravitation* (W. H. Freeman, 1973)** — §25.2–25.5
  (geodesics, radial infall, cycloid), §31.2–31.5 (Schwarzschild geometry, EF and Kruskal
  coordinates, Box 31.2), §37.2 (tidal forces, geodesic deviation), exercise 31.1 (Kretschmann).
  Section numbers from memory; NOT RE-VERIFIED ONLINE IN THIS SESSION.
* **R. M. Wald, *General Relativity* (University of Chicago Press, 1984)** — §3.3 (geodesic
  deviation), ch. 6 (Schwarzschild solution, §6.4 EF/Kruskal), problem 6.4 (radial infall).
* **S. M. Carroll, *Spacetime and Geometry* (Addison-Wesley, 2004)** — ch. 5 (Schwarzschild,
  §5.6 EF coordinates, §5.7 Kruskal).
* **S. W. Hawking & G. F. R. Ellis, *The Large Scale Structure of Space-Time* (Cambridge, 1973)** —
  §5.5 (Schwarzschild causal structure, Penrose diagrams).
* **E. Poisson, *A Relativist's Toolkit* (Cambridge, 2004)** — ch. 1 (geodesics, Killing
  quantities), ch. 5 (black holes).
* **E. F. Taylor & J. A. Wheeler, *Exploring Black Holes: Introduction to General Relativity*
  (Addison Wesley Longman, 2000)** — ch. 3 (plunging: proper time to the centre from the horizon,
  (2/3)(r_s/c)).
* **E. Hairer, S. P. Nørsett & G. Wanner, *Solving Ordinary Differential Equations I*, 2nd ed.
  (Springer, 1993)** — §II.4–II.5 (embedded RK pairs, step-size control, Table 5.2 Dormand–Prince
  coefficients, PI control), §II.4 initial step-size algorithm.
* **S. Chandrasekhar, *The Mathematical Theory of Black Holes* (Oxford, 1983)** — ch. 3
  (Schwarzschild: geodesics, Petrov type D structure of the curvature).
All: NOT RE-VERIFIED ONLINE IN THIS SESSION.

## 5. Constants

* **E. Tiesinga, P. J. Mohr, D. B. Newell & B. N. Taylor, "CODATA recommended values of the
  fundamental physical constants: 2018", Rev. Mod. Phys. 93, 025010 (2021)**; NIST Reference on
  Constants, Units and Uncertainty, https://physics.nist.gov/cuu/Constants/ — G, ħ, l_P (the 2022
  adjustment leaves these unchanged at the precision used). NOT RE-VERIFIED ONLINE IN THIS SESSION.
* **BIPM, *The International System of Units (SI)*, 9th ed. (2019)** — c and h exact.
* **IAU 2015 Resolution B3** (nominal solar conversion constants, GM☉ = 1.3271244e20 m³ s⁻²) —
  cited for the 3e-5 discrepancy note on M☉; **IAU 2012 Resolution B2** — astronomical unit
  exactly 149 597 870 700 m. NOT RE-VERIFIED ONLINE IN THIS SESSION.
* Solar mass 1.98847e30 kg: value specified in the project brief (commonly quoted as
  (1.98847 ± 0.00007)e30 kg); INSUFFICIENT DATA TO VERIFY its primary source in this session.

## 6. Regular black-hole toy models (SPECULATIVE menu only)

* **S. A. Hayward (2006), Phys. Rev. Lett. 96, 031103** — "Formation and evaporation of
  nonsingular black holes": f = 1 − 2Mr²/(r³ + 2Ml²). SPECULATIVE MODEL.
* **J. M. Bardeen (1968), in *Proceedings of GR5* (Tbilisi, USSR), p. 174** — first regular
  black-hole metric f = 1 − 2Mr²/(r² + g²)^{3/2}; **E. Ayón-Beato & A. García (2000), Phys. Lett.
  B 493, 149** — its nonlinear-electrodynamics source. SPECULATIVE MODEL.
* **I. Dymnikova (1992), Gen. Relativ. Gravit. 24, 235** — "Vacuum nonsingular black hole":
  de Sitter-core metric with mass function M(1 − e^{−r³/r_*³}). SPECULATIVE MODEL.
* Context only (not implemented): **A. Ashtekar, J. Olmedo & P. Singh (2018), Phys. Rev. Lett.
  121, 241301** — loop-quantum-gravity-inspired Schwarzschild interior. Mentioned to indicate the
  class of "effective LQG" interiors; the effective metric was not implemented because the author
  could not reproduce its closed form with confidence in this session (INSUFFICIENT DATA TO VERIFY).
All: NOT RE-VERIFIED ONLINE IN THIS SESSION.

## 7. Data files produced by this project (primary evidence for the validation claims)

* `validation_report.json` / `docs/validation_report.md` — every benchmark number.
* `data/trajectory.h5`, `data/trajectory.csv`, `data/trajectory_metadata.json` — the validated run.
* `tools/derive_ef_curvature.py` — symbolic derivation log for §3 and §9 of physics_notes.md.
