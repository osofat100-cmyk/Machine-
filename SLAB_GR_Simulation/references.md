# references.md — annotated bibliography

**Verification status (session of 2026-09-25).** Every entry below was checked with targeted web
searches (several queries per entry: title, authors, journal, volume, page, year, DOI). Direct page
fetches (WebFetch, curl) were blocked by the environment's network policy, so a detail counts as
confirmed only when the search results (titles, URLs such as doi.org / link.aps.org / iopscience /
adsabs / arxiv / svs.gsfc.nasa.gov, and snippets) showed it. The full texts were **not** read.
Each entry carries exactly one status:

* **VERIFIED VIA WEB SEARCH (2026-09-25)** — the listed details were confirmed; confirming URLs given.
* **PARTIALLY VERIFIED** — "confirmed: … / not confirmed: …".
* **INSUFFICIENT DATA TO VERIFY** — nothing reliable was found; the detail is kept only as a pointer.

Rules applied: a DOI or page number is given only if it was seen in a search result (normally as
part of a doi.org or publisher URL; the one exception is flagged). Textbook section, equation and
exercise numbers are the weakest part: each is marked individually, and those not confirmed are
labelled "section number from memory — INSUFFICIENT DATA TO VERIFY". Every correction made in this
session is listed in `docs/additions/citations.md`.

Tags: what each source is used for in this project.

## 1. NASA / NASA Goddard black-hole visualization materials

* **NASA Goddard Space Flight Center Scientific Visualization Studio (SVS), "Black Hole Accretion
  Disk Visualization", SVS page 13326, credit NASA's Goddard Space Flight Center/Jeremy Schnittman,
  released 25 September 2019, https://svs.gsfc.nasa.gov/13326/** — ray-traced views of a black hole
  surrounded by a thin accretion disk: the black hole's gravity redirects and distorts light from
  different parts of the disk, and relativistic Doppler beaming brightens the approaching side.
  Used only as a *qualitative visual reference* for the first-person camera (shape of the shadow,
  lensed images).
  Status: **VERIFIED VIA WEB SEARCH (2026-09-25)**: SVS id 13326, title, credit (Schnittman), release
  date 2019-09-25 (page metadata as shown in the search results), content (lensing of the disk,
  Doppler beaming). URLs: https://svs.gsfc.nasa.gov/13326/ , https://gms.gsfc.nasa.gov/old/13326 .
  Not confirmed (removed from the description): that the page describes the hole as
  "Schwarzschild-like" and shows a "photon ring" — INSUFFICIENT DATA TO VERIFY.
* **NASA Goddard SVS, "NASA Black Hole Visualization Takes Viewers Beyond the Brink", SVS page 14576,
  credit NASA's Goddard Space Flight Center/J. Schnittman and B. Powell, https://svs.gsfc.nasa.gov/14576 ;
  companion page "Beyond the Brink: Tracking a Simulated Plunge into a Black Hole", SVS page 14585,
  https://svs.gsfc.nasa.gov/14585 ; released 6 May 2024; NASA Science feature "New NASA Black Hole
  Visualization Takes Viewers Beyond the Brink" (6 May 2024),
  https://science.nasa.gov/universe/black-holes/supermassive-black-holes/new-nasa-black-hole-visualization-takes-viewers-beyond-the-brink/**
  — supercomputer (Discover, NASA Center for Climate Simulation) visualization of a camera that
  approaches, orbits and in one scenario crosses the event horizon of a *non-rotating* black hole of
  4.3 million solar masses. 360° and explainer versions on NASA Goddard's YouTube channel:
  "360 Video: NASA Simulation Plunges Into a Black Hole" (https://www.youtube.com/watch?v=crXGmeWFb9o)
  and "NASA Simulation's Plunge Into a Black Hole: Explained" (https://www.youtube.com/watch?v=chhcwk4-esM).
  Same use as above: methodology reference for a first-person infall rendering.
  Status: **VERIFIED VIA WEB SEARCH (2026-09-25)**: SVS ids 14576 and 14585 with their titles, credit
  "J. Schnittman and B. Powell" (SVS 14576), release date 2024-05-06, non-rotating 4.3e6 M☉ hole,
  Discover supercomputer, the two YouTube titles. URLs as listed, plus
  https://www.eurekalert.org/news-releases/1043682 . Correction: "NASA Simulation's Plunge Into a
  Black Hole" is the title of the YouTube explainer, not of the SVS release.
* Scope statement (required by the brief): these visualizations validate *established exterior
  GR* and *visualization methodology* only. They say nothing about the interior beyond the
  classical description and nothing about quantum gravity; they are never cited here as evidence
  about physics at or beyond r_QG.

## 2. Einstein Toolkit

* **Einstein Toolkit, https://einsteintoolkit.org** — community-driven, freely accessible software
  platform for numerical relativity and relativistic astrophysics (Cactus framework, Carpet mesh
  refinement, BSSN evolution). Standard reference paper: **F. Löffler, J. Faber, E. Bentivegna,
  T. Bode, P. Diener, R. Haas, I. Hinder, B. C. Mundim, C. D. Ott, E. Schnetter, G. Allen,
  M. Campanelli & P. Laguna, "The Einstein Toolkit: a community computational infrastructure for
  relativistic astrophysics", Class. Quantum Grav. 29, 115001 (2012), doi:10.1088/0264-9381/29/11/115001,
  arXiv:1111.3344.** Referenced as the community standard for numerical-relativity methodology
  (evolution of the Einstein equations on a grid). Not used directly: this project integrates
  test-particle worldlines on the exact Schwarzschild background, which is an ODE problem.
  Status: **VERIFIED VIA WEB SEARCH (2026-09-25)**: website, paper title, author list, journal,
  volume, article number, year, DOI, arXiv id. URLs: https://www.einsteintoolkit.org/ ,
  https://iopscience.iop.org/article/10.1088/0264-9381/29/11/115001 , https://arxiv.org/abs/1111.3344 .

## 3. Peer-reviewed general-relativity references

* **K. Schwarzschild, "Über das Gravitationsfeld eines Massenpunktes nach der Einsteinschen Theorie",
  Sitzungsberichte der Königlich Preußischen Akademie der Wissenschaften (Berlin), 1916, 189–196** —
  the exact vacuum solution. Used for: the metric (§2 of physics_notes.md).
  Status: **VERIFIED VIA WEB SEARCH (2026-09-25)**: title, venue, year, pages 189–196 (ADS bibcode
  1916SPAW.......189S). URLs: https://ui.adsabs.harvard.edu/abs/1916SPAW.......189S/abstract ,
  https://de.wikisource.org/wiki/%C3%9Cber_das_Gravitationsfeld_eines_Massenpunktes_nach_der_Einsteinschen_Theorie .
* **A. S. Eddington, "A comparison of Whitehead's and Einstein's formulæ", Nature 113, 192 (1924),
  doi:10.1038/113192a0** — introduces the coordinates that are regular at the horizon (advanced-time
  form). Used for: the ingoing EF chart.
  Status: **VERIFIED VIA WEB SEARCH (2026-09-25)**: title, journal, volume, page, year, DOI.
  URLs: https://www.nature.com/articles/113192a0 , https://ui.adsabs.harvard.edu/abs/1924Natur.113..192E/abstract .
* **D. Finkelstein, "Past-future asymmetry of the gravitational field of a point particle", Phys. Rev.
  110, 965–967 (1958), doi:10.1103/PhysRev.110.965** — the surface r = 2m "acts as a perfect
  unidirectional membrane" (abstract). Used for: horizon crossing, light-cone tilting.
  Status: **VERIFIED VIA WEB SEARCH (2026-09-25)**: title, journal, volume, pages, year, DOI, abstract
  statement. URLs: https://link.aps.org/doi/10.1103/PhysRev.110.965 ,
  https://ui.adsabs.harvard.edu/abs/1958PhRv..110..965F .
* **M. D. Kruskal, "Maximal extension of Schwarzschild metric", Phys. Rev. 119, 1743 (1960),
  doi:10.1103/PhysRev.119.1743** and **G. Szekeres, "On the singularities of a Riemannian manifold",
  Publ. Math. Debrecen 7, 285–301 (1960)** (reprinted as a "Golden Oldie" in Gen. Relativ. Gravit.,
  2002, doi:10.1023/A:1020744914721) — maximal analytic extension; Kruskal–Szekeres coordinates.
  Used for: the causal diagram (§7).
  Status (Kruskal): **VERIFIED VIA WEB SEARCH (2026-09-25)**: title, journal, volume, page, year
  (issue of 1 September 1960), DOI. URLs: https://link.aps.org/doi/10.1103/PhysRev.119.1743 ,
  https://ui.adsabs.harvard.edu/abs/1960PhRv..119.1743K/abstract .
  Status (Szekeres): **PARTIALLY VERIFIED**: confirmed: title, journal, volume 7, first page 285 (ADS
  bibcode 1960PMatD...7..285S), page range 285–301, GRG reprint (Springer URL with the DOI above) /
  not confirmed on a publisher page: the original article's DOI 10.5486/PMD.1960.7.1-4.26 — it appears
  in search-result text (Semantic Scholar, OUCI) and, by exact-string search, in the reference list of
  an Am. J. Phys. article ("Modified Fronsdal coordinates for maximally extended Schwarzschild
  spacetime"), but no doi.org or publisher link was seen; given here only with this caveat.
  URLs: https://ui.adsabs.harvard.edu/abs/1960PMatD...7..285S/abstract ,
  https://link.springer.com/article/10.1023/A:1020744914721 .
* **R. C. Henry, "Kretschmann scalar for a Kerr–Newman black hole", Astrophys. J. 535, 350–353 (2000),
  doi:10.1086/308819, arXiv:astro-ph/9912320** (gives the Schwarzschild limit 48 M²/r⁶).
  Used for: TEST 5.
  Status: **VERIFIED VIA WEB SEARCH (2026-09-25)**: title, journal, volume, pages, year, DOI, arXiv id.
  URLs: https://iopscience.iop.org/article/10.1086/308819 ,
  https://ui.adsabs.harvard.edu/abs/2000ApJ...535..350H , https://arxiv.org/pdf/astro-ph/9912320 .
  (That the paper displays the Schwarzschild limit explicitly: from memory; the limit itself is
  re-derived in this repository, TEST 5.)
* **G. F. Lewis & J. Kwan, "No way back: maximizing survival time below the Schwarzschild event
  horizon", Publ. Astron. Soc. Aust. 24(2), 46–52 (2007), doi:10.1071/AS07012, arXiv:0705.1029** —
  inside the horizon rockets "can increase your remaining time, but only up to a maximum value",
  contrary to the popular "the more you struggle, the less time you have" (abstract). Used for: the
  propulsion-mode notes (§6).
  Status: **VERIFIED VIA WEB SEARCH (2026-09-25)**: title, authors, journal, volume, issue, pages, year,
  DOI (https://doi.org/10.1071/AS07012 as given in the search results; an exact-string search for the
  DOI returns the Cambridge Core article and PDF pages), arXiv id, abstract statement.
  URLs: https://www.cambridge.org/core/journals/publications-of-the-astronomical-society-of-australia/article/no-way-back-maximizing-survival-time-below-the-schwarzschild-event-horizon/2A1CCF5CB13E7BEFA6441B3038C635A3 ,
  https://arxiv.org/abs/0705.1029 .
  **Correction:** the previous annotation ("free fall maximizes the remaining proper time; thrust
  shortens it") misstated the paper. The maximum remaining time from the horizon, πGM/c³, belongs to
  the E = 0 free-fall geodesic; an observer who enters with E > 0 can approach it with suitable thrust
  and should then switch the engine off (also stated in the search-result summary of arXiv:1905.02150,
  "On strategies of motion under the black hole horizon" — bibliographic details of that preprint not
  checked). The thrust mode implemented here (a = −α n/|n|, which always raises E) shortens the
  remaining time of any observer with E > 0, i.e. of every observer who entered from outside
  (physics_notes.md §6).
* **J. R. Dormand & P. J. Prince, "A family of embedded Runge-Kutta formulae", J. Comput. Appl. Math.
  6(1), 19–26 (1980), doi:10.1016/0771-050X(80)90013-3** — the RK5(4) pair used by the integrator.
  Status: **VERIFIED VIA WEB SEARCH (2026-09-25)**: title, journal, volume, issue, pages, year, DOI.
  URL: https://www.sciencedirect.com/science/article/pii/0771050X80900133 .

### Added in the 2026-09-25 upgrade (accelerated-observer terms, first-person view, signals)

* **W.-T. Ni & M. Zimmermann, "Inertial and gravitational effects in the proper reference frame of an
  accelerated, rotating observer", Phys. Rev. D 17, 1473–1476 (1978), doi:10.1103/PhysRevD.17.1473** —
  metric of an accelerated, rotating observer's proper reference frame to second order in distance
  (inertial, Coriolis, centripetal and curvature terms). Used for: the inertial (Rindler-type)
  differential terms of the thrust mode (`src/slab/accelerated.py`).
  Status: **VERIFIED VIA WEB SEARCH (2026-09-25)**: title, authors, journal, volume, issue 6, pages,
  date (15 March 1978), DOI, abstract content. URLs: https://link.aps.org/doi/10.1103/PhysRevD.17.1473 ,
  https://www.wikidata.org/wiki/Q27349197 .
* **A. J. S. Hamilton & G. Polhemus, "Stereoscopic visualization in curved spacetime: seeing deep
  inside a black hole", New J. Phys. 12, 123027 (2010), doi:10.1088/1367-2630/12/12/123027,
  arXiv:1012.4043.** Used for: literature context of the first-person view deep inside.
  Status: **VERIFIED VIA WEB SEARCH (2026-09-25)**: title, authors, journal, volume, article number,
  year (published 16 Dec 2010), DOI, arXiv id. URLs:
  https://iopscience.iop.org/article/10.1088/1367-2630/12/12/123027 , https://arxiv.org/abs/1012.4043 .
  Whether it contains the specific near-singularity statements quoted by the camera notes:
  INSUFFICIENT DATA TO VERIFY (full text not read).
* **A. J. S. Hamilton & G. Polhemus, "The edge of locality: visualizing a black hole from the inside",
  arXiv:0903.4717 (2009)** — abstract: near the singularity the observer's view is aberrated by the
  diverging tidal force into a horizontal plane, highly blueshifted in that plane and highly
  redshifted in all other directions. Used for: comparison with the first-person camera near r_QG.
  Status: **PARTIALLY VERIFIED**: confirmed: title, authors (JILA, Boulder), arXiv id, submission date
  27 March 2009, abstract statement (https://arxiv.org/abs/0903.4717) / not confirmed: journal
  publication — INSUFFICIENT DATA TO VERIFY (cite as the arXiv preprint).
* **W. L. Ames & K. S. Thorne, "The optical appearance of a star that is collapsing through its
  gravitational radius", Astrophys. J. 151, 659–670 (1968)** — abstract: "the order of magnitude of
  the e-folding time for the decay of the observed flux is given by the reciprocal of the surface
  gravity of the resultant black hole". Used for: the late-time exponential dimming/redshift of an
  infalling source (distant-observer signal timeline, e-folding time 4GM/c³ = 1/κ).
  Status: **PARTIALLY VERIFIED**: confirmed: title, authors, journal, volume, pages, year, abstract
  statement (https://www.osti.gov/biblio/4546392 , https://www.wikidata.org/wiki/Q40797443) / not
  confirmed: a DOI (none seen). The abstract speaks of the *flux* e-folding time "in order of
  magnitude"; the exact statement for the redshift of the radially emitted signal, 1 + z ∝ e^{u/4M},
  is taken from the lecture notes below and is re-derived in this repository.
* **S. W. Hawking, "Particle creation by black holes", Commun. Math. Phys. 43, 199–220 (1975),
  doi:10.1007/BF02345020** — context only: the same exponential relation between retarded time and
  affine parameter at the horizon (rate κ, the surface gravity) underlies Hawking radiation; the
  abstract gives the temperature ħκ/2πk. Not used for any number here.
  Status: **VERIFIED VIA WEB SEARCH (2026-09-25)**: title, journal, volume, pages, year, DOI, abstract.
  URLs: https://link.springer.com/article/10.1007/BF02345020 ,
  https://projecteuclid.org/journals/communications-in-mathematical-physics/volume-43/issue-3/Particle-creation-by-black-holes/cmp/1103899181.full .

## 4. Textbooks

Publisher/edition data are verified; section/equation/exercise numbers are marked one by one.

* **C. W. Misner, K. S. Thorne & J. A. Wheeler, *Gravitation* (W. H. Freeman, San Francisco, 1973),
  ISBN 0-7167-0344-0** (reissued by Princeton University Press, 2017).
  Status of the book: **VERIFIED VIA WEB SEARCH (2026-09-25)**: authors, publisher, year, ISBN
  (https://en.wikipedia.org/wiki/Gravitation_(book)); Princeton reissue
  (https://press.princeton.edu/books/hardcover/9780691177793/gravitation).
  Sections cited in physics_notes.md:
  - ch. 31 is the Schwarzschild-geometry chapter — PARTIALLY VERIFIED (a solution-manual index lists
    "Chapter 31: Schwarzschild geometry"; https://ebin.pub/solution-manual-for-gravitation-mtw-0716703440-9780716703440-9780691177793-9780716703341-9789570911336-9784621083277.html).
  - exercise 31.1 = "Tidal forces on infalling explorer"; 31.4 "How long to live?"; 31.5
    "Eddington–Finkelstein and Kruskal–Szekeres compared" — PARTIALLY VERIFIED: titles as listed in the
    third-party solution-manual index above; MTW's own exercise text not seen. **Correction:** exercise
    31.1 was previously cited for the Kretschmann scalar; it is the tidal-force exercise.
  - Box 31.2 contains Kruskal–Szekeres diagrams — PARTIALLY VERIFIED (search-result description only).
  - the cycloid relation "between r and t for straight-in fall" is a table-of-contents entry of
    ch. 25 — PARTIALLY VERIFIED (archive.org full-text TOC snippet); its section number (a search
    summary said §25.3) and the equation number 25.38: section number from memory — INSUFFICIENT DATA
    TO VERIFY.
  - §13.6, proper reference frame of an accelerated observer — **VERIFIED VIA WEB SEARCH
    (2026-09-25)** (section number and topic: https://en.wikipedia.org/wiki/Proper_reference_frame_(flat_spacetime) ,
    https://www.physicsforums.com/threads/proper-reference-frame-accelerated-observer.706593/ ; page
    number not confirmed).
  - ch. 37 is "Detection of gravitational waves" (archive.org TOC snippet); that §37.2 treats
    test-particle motion / accelerations in a detector's proper reference frame — PARTIALLY VERIFIED
    (search summary only).
  - §25.2, §25.5, eq. 25.38, §31.2 (eq. 31.6), §31.3, §31.4, §31.5: section number from memory —
    INSUFFICIENT DATA TO VERIFY.
* **R. M. Wald, *General Relativity* (University of Chicago Press, Chicago, 1984)**.
  Status: **VERIFIED VIA WEB SEARCH (2026-09-25)** (book): https://press.uchicago.edu/ucp/books/book/chicago/G/bo5952261.html ,
  https://ui.adsabs.harvard.edu/abs/1984ucp..book.....W/abstract .
  Sections: §3.3 "Geodesics" (geodesic deviation) — section title VERIFIED (class notes that follow
  Wald: https://faculty.etsu.edu/gardnerr/5310/notes-Wald.htm), that it contains the deviation
  equation: from memory; ch. 6 "The Schwarzschild solution" with §6.1 derivation and §6.4 "The Kruskal
  extension" — PARTIALLY VERIFIED (one search summary lists these section titles); problem 6.4 (radial
  infall): INSUFFICIENT DATA TO VERIFY; §12.5, surface gravity κ² = −½(∇ᵃχᵇ)(∇ₐχ_b), eq. (12.5.14),
  κ = 1/4M for Schwarzschild — PARTIALLY VERIFIED (secondary notes page
  http://kstar.wikidot.com/surface-gravity-of-the-schwarzschild-blackhole).
* **S. M. Carroll, *Spacetime and Geometry: An Introduction to General Relativity* (Addison-Wesley,
  San Francisco, 2004)** — ch. 5 "The Schwarzschild solution": §5.6 "Schwarzschild black holes" (EF
  coordinates), §5.7 "The maximally extended Schwarzschild solution" (Kruskal).
  Status: **PARTIALLY VERIFIED**: confirmed: author, title, publisher, year
  (https://preposterousuniverse.com/spacetimeandgeometry/ , https://en.wikipedia.org/wiki/Spacetime_and_Geometry) /
  the §5.6 and §5.7 titles appeared in one search summary but could not be reproduced by a second
  search — treat as not fully verified.
* **S. W. Hawking & G. F. R. Ellis, *The Large Scale Structure of Space-Time* (Cambridge University
  Press, 1973)** — ch. 5 "Exact solutions", §5.5 "The Schwarzschild and Reissner–Nordström solutions"
  (causal structure, Penrose diagrams).
  Status: **VERIFIED VIA WEB SEARCH (2026-09-25)**: book, publisher, year; ch. 5 "Exact solutions"
  (https://www.cambridge.org/core/books/large-scale-structure-of-spacetime/exact-solutions/6A2049F2E72FB11E6BD6FAF60C7744FC);
  §5.5 title (as cited at https://ncatlab.org/nlab/show/Reissner-Nordstr%C3%B6m+spacetime).
* **E. Poisson, *A Relativist's Toolkit: The Mathematics of Black-Hole Mechanics* (Cambridge
  University Press, 2004)** — ch. 1 "Fundamentals" (geodesics, Killing quantities), ch. 5 "Black holes".
  Status: **VERIFIED VIA WEB SEARCH (2026-09-25)**: full title, publisher, year, chapter titles
  (https://www.cambridge.org/core/books/abs/relativists-toolkit/black-holes/F4B0C7983A6B04BFBF3EC0D9B9DE45E3).
  Correction: subtitle added.
* **E. F. Taylor & J. A. Wheeler, *Exploring Black Holes: Introduction to General Relativity*
  (Addison Wesley Longman, 2000)** — ch. 3 "Plunging" (proper time to the centre from the horizon,
  (2/3)(r_s/c)).
  Status: **VERIFIED VIA WEB SEARCH (2026-09-25)** for authors, title, publisher, year and the chapter
  title "Plunging" (https://pubs.aip.org/physicstoday/article/54/11/59/411626/Exploring-Black-Holes-Introduction-to-General ,
  https://ocw.mit.edu/courses/8-224-exploring-black-holes-general-relativity-astrophysics-spring-2003/pages/readings/);
  the (2/3)(r_s/c) statement in that chapter: from memory (the number itself is TEST 4 of this project).
  A later second edition with E. Bertschinger exists; the first edition is the one cited.
* **E. Hairer, S. P. Nørsett & G. Wanner, *Solving Ordinary Differential Equations I: Nonstiff
  Problems*, 2nd revised ed., Springer Series in Computational Mathematics 8 (Springer, Berlin, 1993)**
  — §II.4 embedded Runge–Kutta formulas, automatic step-size control and starting step size; §II.5
  Table 5.2 (Dormand–Prince coefficients); PI step control as used in Hairer's DOPRI5 code.
  Status: **PARTIALLY VERIFIED**: confirmed: authors, title, edition, series and volume, publisher,
  year (https://link.springer.com/book/10.1007/978-3-540-78862-1 , https://dl.acm.org/doi/10.5555/153158);
  that embedded formulas and "Automatic Step Size Control" / "Starting Step Size" are in §II.4 (search
  summary of a PDF of the book) / not confirmed: §II.5, Table 5.2 and the section treating PI control —
  section number from memory — INSUFFICIENT DATA TO VERIFY.
* **S. Chandrasekhar, *The Mathematical Theory of Black Holes* (Clarendon Press / Oxford University
  Press, Oxford, 1983)** — ch. 3 "The Schwarzschild space-time" (geodesics, Petrov type D structure).
  Status: **VERIFIED VIA WEB SEARCH (2026-09-25)**: author, title, publisher, year, ch. 3 title
  (https://ui.adsabs.harvard.edu/abs/1983mtbh.book.....C/abstract ,
  https://global.oup.com/academic/product/the-mathematical-theory-of-black-holes-9780198503705);
  the Petrov-type-D discussion in ch. 3: from memory.

### Lecture notes (added 2026-09-25)

* **C. M. Hirata, "Lecture XXIV: External appearance of a black hole", Caltech Ph 236 (General
  Relativity) lecture notes, 2011–12, http://www.tapir.caltech.edu/~chirata/ph236/2011-12/lec24.pdf** —
  the redshift of the surface of a collapsing star, as seen from far away, increases exponentially
  with time on the time scale 4M (= 4GM/c³ = 1/κ; for a 10 M☉ hole 4M = 200 µs). Used for: the
  standard statement behind the late-time exponential redshift (e-folding time 4GM/c³) of the
  distant-observer signal timeline.
  Status: **VERIFIED VIA WEB SEARCH (2026-09-25)**: author, title, course, URL, the exponential
  redshift with time scale 4M and the 10 M☉ example. Lecture notes, not peer reviewed; no textbook
  section for this statement could be confirmed (MTW ch. 32, Shapiro & Teukolsky 1983, Frolov &
  Novikov 1998 were searched: INSUFFICIENT DATA TO VERIFY a section number).

## 5. Constants

* **P. J. Mohr, D. B. Newell, B. N. Taylor & E. Tiesinga, "CODATA recommended values of the
  fundamental physical constants: 2022", Rev. Mod. Phys. 97, 025002 (2025),
  doi:10.1103/RevModPhys.97.025002, arXiv:2409.03787** (also published in J. Phys. Chem. Ref. Data,
  doi:10.1063/5.0279860 — volume/article number INSUFFICIENT DATA TO VERIFY); NIST Reference on
  Constants, Units and Uncertainty, https://physics.nist.gov/cuu/Constants/ — the values used:
  G = 6.674 30(15) × 10⁻¹¹ m³ kg⁻¹ s⁻², ħ = 1.054 571 817… × 10⁻³⁴ J s (exact), l_P = 1.616 255(18) × 10⁻³⁵ m
  (relative standard uncertainty 1.1 × 10⁻⁵).
  Status: **VERIFIED VIA WEB SEARCH (2026-09-25)**: citation (authors, title, journal, volume, article
  number, publication date 30 April 2025, DOI, arXiv id) and the three values with uncertainties.
  URLs: https://link.aps.org/doi/10.1103/RevModPhys.97.025002 ,
  https://ui.adsabs.harvard.edu/abs/2025RvMP...97b5002M/abstract , https://arxiv.org/abs/2409.03787 ,
  https://physics.nist.gov/cgi-bin/cuu/Value?bg , https://physics.nist.gov/cgi-bin/cuu/Value?hbar ,
  https://physics.nist.gov/cgi-bin/cuu/Value?plkl , https://physics.nist.gov/cuu/pdf/wallet_2022.pdf .
  6.67430e-11 and 1.616255e-35 ARE the CODATA 2022 values (identical to CODATA 2018).
  **Correction:** the code stored the standard uncertainty of l_P as 1.8e-41 m; the CODATA value
  1.616 255(18)e-35 m means 1.8e-40 m (relative 1.1e-5). Fixed in `src/slab/constants.py`; central
  values and all derived numbers are unchanged, only the propagated uncertainty of K_Planck and r_QG
  changes.
* **E. Tiesinga, P. J. Mohr, D. B. Newell & B. N. Taylor, "CODATA recommended values of the
  fundamental physical constants: 2018", Rev. Mod. Phys. 93, 025010 (2021),
  doi:10.1103/RevModPhys.93.025010** — the previous adjustment, cited by the first build; same values
  for G, ħ and l_P.
  Status: **VERIFIED VIA WEB SEARCH (2026-09-25)**: authors, title, journal, volume, article number,
  date (30 June 2021), DOI. URL: https://link.aps.org/doi/10.1103/RevModPhys.93.025010 .
* **BIPM, *The International System of Units (SI)*, 9th ed. (2019)** — c = 299 792 458 m s⁻¹ and
  h = 6.626 070 15 × 10⁻³⁴ J s exact (defining constants, effective 20 May 2019).
  Status: **VERIFIED VIA WEB SEARCH (2026-09-25)**: both values, exactness, date.
  URLs: https://www.bipm.org/documents/20126/41483022/SI-Brochure-9-EN.pdf ,
  https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.330-2019.pdf .
* **IAU 2015 Resolution B3** (nominal solar and planetary conversion constants): nominal solar mass
  parameter (GM)☉ᴺ = 1.327 124 4 × 10²⁰ m³ s⁻² exactly; the resolution deliberately does *not* define a
  solar mass in kilograms (G is five orders of magnitude less precise than GM☉) and recommends quoting
  masses as (GM)/G with the adopted G stated. Paper: **A. Prša et al., "Nominal values for selected
  solar and planetary quantities: IAU 2015 Resolution B3", Astron. J. 152, 41 (2016),
  doi:10.3847/0004-6256/152/2/41, arXiv:1605.09788** (resolution text: arXiv:1510.07674).
  Status: **VERIFIED VIA WEB SEARCH (2026-09-25)**: GM value and its exactness, the no-kilogram
  policy, the paper's journal, volume, article, year, DOI. URLs:
  https://iopscience.iop.org/article/10.3847/0004-6256/152/2/41 , https://arxiv.org/abs/1605.09788 ,
  https://arxiv.org/abs/1510.07674 , https://www.pas.rochester.edu/~emamajek/IAU/IAUres_B3.pdf .
  (Search-result summaries that claim "IAU 2015 B3 set the nominal solar mass at exactly
  1.98847e30 kg" contradict the resolution text and were rejected.)
* **IAU 2012 Resolution B2** (XXVIII General Assembly, Beijing) — astronomical unit = 149 597 870 700 m
  exactly. Status: **VERIFIED VIA WEB SEARCH (2026-09-25)**. URLs:
  https://observatoiredeparis.psl.eu/the-new-definition-of-the-astronomical-unit.html ,
  https://aas.org/posts/story/2013/08/report-2012-iau-xxviii-general-assembly .
* **Julian year and light-year** — IAU: the light-year is the distance light travels in vacuum in one
  Julian year of 365.25 days (86 400 s each); with the exact c this is 9 460 730 472 580 800 m.
  Status: **VERIFIED VIA WEB SEARCH (2026-09-25)**. URLs: https://iauarchive.eso.org/public/themes/measuring/ ,
  https://en.wikipedia.org/wiki/Light-year , https://en.wikipedia.org/wiki/Julian_year_(astronomy) .
* **Solar mass 1.98847e30 kg (± 7e25 kg)** — value specified in the project brief and kept.
  Status: **PARTIALLY VERIFIED**: confirmed: 1.98847e30 kg equals (GM)☉ᴺ/G with the CODATA 2014
  G = 6.674 08(31) × 10⁻¹¹ (Mohr, Newell & Taylor, Rev. Mod. Phys. 88, 035009 (2016); verified via
  https://arxiv.org/pdf/1507.07956 , https://www.codata.org/uploads/RMP.88.035009.pdf): 1.3271244e20 /
  6.67408e-11 = 1.988475e30 kg, which is the "best estimate (1.988475 ± 0.000092)e30 kg" shown on
  https://en.wikipedia.org/wiki/Solar_mass (the ± 0.000092 is the CODATA 2014 G uncertainty) / not
  confirmed: a primary source for the brief's ± 0.00007e30 kg — INSUFFICIENT DATA TO VERIFY.
  Consequence (unchanged, documented): with the CODATA 2022 G the same ratio is 1.98841e30 kg,
  3.0e-5 below the brief's value — below every other uncertainty that matters here.

## 6. Regular black-hole toy models (SPECULATIVE menu only)

* **S. A. Hayward, "Formation and evaporation of nonsingular black holes", Phys. Rev. Lett. 96, 031103
  (2006), doi:10.1103/PhysRevLett.96.031103** — f = 1 − 2Mr²/(r³ + 2Ml²). SPECULATIVE MODEL.
  Status: **VERIFIED VIA WEB SEARCH (2026-09-25)**: title, journal, volume, article, date (26 Jan
  2006), DOI; the lapse function f = 1 − 2Mr²/(r³ + 2Ml²) as quoted in later papers (e.g.
  https://arxiv.org/pdf/2104.07506). URL: https://link.aps.org/doi/10.1103/PhysRevLett.96.031103 .
* **J. M. Bardeen, "Non-singular general-relativistic gravitational collapse", in *Proceedings of the
  International Conference GR5* (Tbilisi, USSR, 1968)** — first regular black-hole metric
  f = 1 − 2Mr²/(r² + g²)^{3/2}. SPECULATIVE MODEL.
  Status: **PARTIALLY VERIFIED**: confirmed: author, title, conference, place, year / not confirmed:
  the page — later literature cites p. 174 (also "pp. 174–175" of the GR5 abstracts), while the ADS
  record is 1968qtr..conf...87B (p. 87); INSUFFICIENT DATA TO VERIFY which is correct.
  URL: https://ui.adsabs.harvard.edu/abs/1968qtr..conf...87B/abstract . Correction: the previous
  entry gave "p. 174" as certain.
* **E. Ayón-Beato & A. García, "The Bardeen model as a nonlinear magnetic monopole", Phys. Lett. B 493,
  149–152 (2000), doi:10.1016/S0370-2693(00)01125-4, arXiv:gr-qc/0009077** — nonlinear-electrodynamics
  source of the Bardeen metric. SPECULATIVE MODEL.
  Status: **VERIFIED VIA WEB SEARCH (2026-09-25)**: title, journal, volume, pages, year, DOI, arXiv id.
  URLs: https://www.sciencedirect.com/science/article/abs/pii/S0370269300011254 ,
  https://ui.adsabs.harvard.edu/abs/2000PhLB..493..149A/abstract , https://inspirehep.net/literature/534086 .
* **I. Dymnikova, "Vacuum nonsingular black hole", Gen. Relativ. Gravit. 24, 235–242 (1992),
  doi:10.1007/BF00760226** — de Sitter-core metric with mass function M(1 − e^{−r³/r_*³}).
  SPECULATIVE MODEL.
  Status: **VERIFIED VIA WEB SEARCH (2026-09-25)**: title, journal, volume, pages, year, DOI, abstract
  (Schwarzschild at large r, de Sitter at small r); mass-function form as quoted in later papers.
  URLs: https://link.springer.com/article/10.1007/BF00760226 , https://ui.adsabs.harvard.edu/abs/1992GReGr..24..235D .
* Context only (not implemented): **A. Ashtekar, J. Olmedo & P. Singh, "Quantum transfiguration of
  Kruskal black holes", Phys. Rev. Lett. 121, 241301 (2018), doi:10.1103/PhysRevLett.121.241301,
  arXiv:1806.00648** — loop-quantum-gravity effective description of the full Kruskal spacetime.
  Mentioned to indicate the class of "effective LQG" interiors; the effective metric was not
  implemented because its closed form could not be reproduced with confidence.
  Status: **VERIFIED VIA WEB SEARCH (2026-09-25)**: title, authors, journal, volume, article, date
  (10 Dec 2018), DOI, arXiv id. URLs: https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.121.241301 ,
  https://arxiv.org/abs/1806.00648 . Its effective metric: INSUFFICIENT DATA TO VERIFY (not used).

## 7. Data files produced by this project (primary evidence for the validation claims)

* `validation_report.json` / `docs/validation_report.md` — every benchmark number.
* `data/trajectory.h5`, `data/trajectory.csv`, `data/trajectory_metadata.json` — the validated run.
* `tools/derive_ef_curvature.py` — symbolic derivation log for §3 and §9 of physics_notes.md.
(Internal files, not external citations: no verification status applies.)

## 8. Sky data for the first-person camera (added 2026-09-25)

* **d3-celestial, O. Frohn, version 0.7.35 (npm), BSD-3-Clause licence,
  https://github.com/ofrohn/d3-celestial** — source package of the star list used for the physically
  motivated sky (its `data/stars.6.json`). Its readme names the star data source as XHIP (next entry).
  Status: **VERIFIED (2026-09-25)** via the npm registry metadata (name, version 0.7.35, licence
  BSD-3-Clause, author Olaf Frohn, repository URL; readme footnote naming XHIP) and via web search
  (https://github.com/ofrohn/d3-celestial , https://ofrohn.github.io/celestial-demo/).
* **E. Anderson & C. Francis, "XHIP: An extended Hipparcos compilation", Astron. Lett. 38, 331–346
  (2012), doi:10.1134/S1063773712050015, arXiv:1108.4971; VizieR catalogue V/137D** — the underlying
  star catalogue of d3-celestial's star files. Licence of the catalogue data beyond the package's BSD
  release: INSUFFICIENT DATA TO VERIFY (CDS/VizieR usage asks for acknowledgement; acknowledged here
  and in the viewer).
  Status: **VERIFIED VIA WEB SEARCH (2026-09-25)**: authors, title, journal, volume, pages, year, DOI
  (Springer URL), arXiv id, VizieR id. URLs: https://ui.adsabs.harvard.edu/abs/2012AstL...38..331A ,
  https://link.springer.com/article/10.1134/S1063773712050015 , https://arxiv.org/abs/1108.4971 ,
  https://ui.adsabs.harvard.edu/abs/2012yCat.5137....0A/abstract .
* **HYG stellar database (Hipparcos, Yale Bright Star, Gliese), D. Nash, The Astronomy Nexus,
  https://astronexus.com/projects/hyg ; https://codeberg.org/astronexus/hyg** — named in the upgrade
  brief as a candidate catalogue. **Not used**: the star field was built from d3-celestial/XHIP.
  Status: **VERIFIED VIA WEB SEARCH (2026-09-25)**: author, hosting, content (~120,000 stars from the
  three catalogues), licences: HYG 4.x CC BY-SA 4.0, HYG 3.x CC BY-SA 2.5 (astronexus pages).
