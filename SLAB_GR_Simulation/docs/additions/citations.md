# Citation and constant verification (upgrade-prompt item 1) — agent notes, 2026-09-25

Branch `up/citations2`. For the coordinator to merge into `physics_notes.md` / `README.md` /
`PROJECT_STATE.md`.

## Summary

* Every entry of `references.md`, every citation flag of `physics_notes.md` and every constant in
  `src/slab/constants.py` was checked with targeted web searches (WebSearch tool; WebFetch and curl
  are blocked by the network policy). A detail was accepted only when the search results (titles,
  URLs such as doi.org / link.aps.org / iopscience / adsabs / arxiv / svs.gsfc.nasa.gov /
  physics.nist.gov, and snippets) showed it; full texts were not read. d3-celestial was also checked
  against the npm registry metadata (`npm view d3-celestial`, run in a scratch directory).
* All "NOT RE-VERIFIED ONLINE IN THIS SESSION" and "[citation from memory]" flags are replaced by one
  of: **VERIFIED VIA WEB SEARCH (2026-09-25)**, **PARTIALLY VERIFIED** ("confirmed / not confirmed"),
  **INSUFFICIENT DATA TO VERIFY** (for textbook sections: "section number from memory — INSUFFICIENT
  DATA TO VERIFY").
* DOIs are given only where one was seen in a search result (almost always inside a doi.org or
  publisher URL). The one exception, the DOI of the original Szekeres 1960 article, was seen only in
  snippet text and in a citing article's reference list; it is given with that caveat.

### Constant values — PROMINENT

| constant | stored value | CODATA 2022 / SI / IAU | action |
|---|---|---|---|
| G | 6.67430e-11 ± 1.5e-15 | 6.674 30(15) × 10⁻¹¹ m³ kg⁻¹ s⁻² (= CODATA 2018) | none — value confirmed |
| ħ | 1.054571817e-34 | 1.054 571 817… × 10⁻³⁴ J s, exact (= h/2π) | none — wording fixed: the 10 digits are the CODATA printed digits (truncated, 7e-10 below h/2π), not "rounded" |
| l_P | 1.616255e-35 | 1.616 255(18) × 10⁻³⁵ m, relative 1.1 × 10⁻⁵ (= CODATA 2018) | **uncertainty corrected: 1.8e-41 m → 1.8e-40 m** (the stored value was a factor 10 too small; the docstring of `relative_uncertainties` already said 1.1e-5) |
| c | 299792458 | exact (SI 2019) | none |
| au | 1.495978707e11 | 149 597 870 700 m exact (IAU 2012 B2) | none |
| Julian year | 365.25 × 86400 s | IAU convention; light-year = 9 460 730 472 580 800 m | none |
| M☉ | 1.98847e30 ± 7e25 kg | not a CODATA/IAU kg value (IAU 2015 B3 defines only GM☉) | kept as in the brief; provenance documented (see table) |

**Effect of the l_P correction:** no central value and no derived number changes (r_s, GM/c³, τ, K_Planck,
r_QG are identical). Only `derived_quantities.relative_uncertainties` changes: l_P 1.11e-6 → 1.11e-5,
K_Planck 4.45e-6 → 4.45e-5, r_QG 1.39e-5 → 1.58e-5. `validation_report.json`, `docs/validation_report.md`
and the metadata exports will show the new numbers and the new source/verification strings after the
coordinator regenerates them.

**Solar mass:** 1.98847e30 kg = IAU 2015 B3 nominal (GM)☉ = 1.3271244e20 m³ s⁻² divided by the
CODATA **2014** G = 6.67408e-11 (1.988475e30 kg; this is also the "best estimate (1.988475 ± 0.000092)e30 kg"
on Wikipedia, whose ± is the CODATA 2014 G uncertainty). With the CODATA 2022 G the same ratio is
1.98841e30 kg, 3.0e-5 lower. No primary source was found for the brief's ± 0.00007e30 kg. Several
search-result *summaries* claimed that "IAU 2015 B3 set the nominal solar mass at exactly 1.98847e30 kg";
this contradicts the resolution text (IAU 2015 B3 deliberately defines no mass in kg) and was rejected.

## Files changed

| file | change |
|---|---|
| `references.md` | rewritten: full titles, author lists, page ranges and DOIs where confirmed; a status line with confirming URLs for every entry; corrections flagged in place; new entries (section 3 "Added in the 2026-09-25 upgrade", section 4 lecture notes, section 5 CODATA 2022/2014/IAU paper, section 8 sky data) |
| `physics_notes.md` | verification-status paragraph rewritten; every "[citation from memory]" flag replaced by a precise status; §1 sources → CODATA 2022; §6 propulsion note re-worded (citation correction, see below); §9 MTW exercise 31.1 removed from the Kretschmann citation and §10 gains it; §11 gains the late-time-redshift citations; §13 and §14 citation details. **No equation was changed**; the only new formula is the one-line integral πM in §6, needed by the corrected wording |
| `src/slab/constants.py` | module docstring; `source`/`verification` strings of all seven primary constants; **l_P uncertainty 1.8e-41 → 1.8e-40** |
| `references/README.md` | status column updated |
| `docs/additions/citations.md` | this file |
| `tests/test_citations.py` | NEW (8 tests) — not in my ownership list, created to satisfy "add tests for everything you add"; no other agent touches it |

## Verification table

| entry | status | confirmed details | confirming URLs | corrections made |
|---|---|---|---|---|
| CODATA 2022: Mohr, Newell, Taylor & Tiesinga, Rev. Mod. Phys. 97, 025002 (2025) | VERIFIED VIA WEB SEARCH | authors, title, journal, volume, article no., date 2025-04-30, doi:10.1103/RevModPhys.97.025002, arXiv:2409.03787; also in J. Phys. Chem. Ref. Data, doi:10.1063/5.0279860 (volume not confirmed) | https://link.aps.org/doi/10.1103/RevModPhys.97.025002 ; https://ui.adsabs.harvard.edu/abs/2025RvMP...97b5002M/abstract ; https://arxiv.org/abs/2409.03787 ; https://pubs.aip.org/aip/jpr/article-abstract/doi/10.1063/5.0279860/3363695 | new primary citation for G, ħ, l_P (was CODATA 2018) |
| G = 6.67430(15)e-11 | VERIFIED VIA WEB SEARCH | CODATA 2022 value and uncertainty, same as 2018 | https://physics.nist.gov/cgi-bin/cuu/Value?bg ; https://physics.nist.gov/cuu/pdf/wallet_2022.pdf | none |
| ħ = 1.054 571 817…e-34 J s | VERIFIED VIA WEB SEARCH | exact in CODATA 2022 | https://physics.nist.gov/cgi-bin/cuu/Value?hbar | "rounded to 10 digits" → "10 digits printed by CODATA (truncated)" |
| l_P = 1.616255(18)e-35 m | VERIFIED VIA WEB SEARCH | CODATA 2022 value, relative uncertainty 1.1e-5 | https://physics.nist.gov/cgi-bin/cuu/Value?plkl | **standard uncertainty 1.8e-41 → 1.8e-40 m** |
| CODATA 2018: Tiesinga, Mohr, Newell & Taylor, Rev. Mod. Phys. 93, 025010 (2021) | VERIFIED VIA WEB SEARCH | authors, title, journal, volume, article, date 2021-06-30, doi:10.1103/RevModPhys.93.025010 | https://link.aps.org/doi/10.1103/RevModPhys.93.025010 ; https://pml.nist.gov/cuu/pdf/RevModPhys.93.025010.pdf | DOI added; now "previous adjustment" |
| CODATA 2014: Mohr, Newell & Taylor, Rev. Mod. Phys. 88, 035009 (2016), G = 6.67408(31)e-11 | VERIFIED VIA WEB SEARCH | citation and G value | https://arxiv.org/pdf/1507.07956 ; https://www.codata.org/uploads/RMP.88.035009.pdf | new (explains the brief's M☉) |
| SI Brochure 9th ed. (BIPM 2019): c, h exact | VERIFIED VIA WEB SEARCH | c = 299 792 458 m/s, h = 6.626 070 15e-34 J s, exact from 2019-05-20 | https://www.bipm.org/documents/20126/41483022/SI-Brochure-9-EN.pdf ; https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.330-2019.pdf | none |
| IAU 2015 Resolution B3; Prša et al., Astron. J. 152, 41 (2016) | VERIFIED VIA WEB SEARCH | (GM)☉ᴺ = 1.327 124 4e20 m³ s⁻² exact; no nominal mass in kg; doi:10.3847/0004-6256/152/2/41; arXiv:1605.09788; resolution arXiv:1510.07674 | https://iopscience.iop.org/article/10.3847/0004-6256/152/2/41 ; https://arxiv.org/abs/1605.09788 ; https://arxiv.org/abs/1510.07674 ; https://www.pas.rochester.edu/~emamajek/IAU/IAUres_B3.pdf | paper citation added; false summary claim rejected |
| IAU 2012 Resolution B2 (au) | VERIFIED VIA WEB SEARCH | 149 597 870 700 m exactly, XXVIII GA Beijing | https://observatoiredeparis.psl.eu/the-new-definition-of-the-astronomical-unit.html ; https://aas.org/posts/story/2013/08/report-2012-iau-xxviii-general-assembly | none |
| Julian year / light-year (IAU) | VERIFIED VIA WEB SEARCH | light-year = c × Julian year (365.25 d) = 9 460 730 472 580 800 m | https://iauarchive.eso.org/public/themes/measuring/ ; https://en.wikipedia.org/wiki/Light-year ; https://en.wikipedia.org/wiki/Julian_year_(astronomy) | none |
| M☉ = 1.98847e30 ± 7e25 kg (brief) | PARTIALLY VERIFIED | = (GM)☉ᴺ / G_2014 / not confirmed: primary source of the ± 7e25 kg | https://en.wikipedia.org/wiki/Solar_mass ; https://arxiv.org/pdf/1507.07956 | source/verification strings rewritten; value kept |
| NASA SVS 13326 "Black Hole Accretion Disk Visualization" (Schnittman, 2019) | VERIFIED VIA WEB SEARCH | id, title, credit, release 2019-09-25, lensing + Doppler beaming | https://svs.gsfc.nasa.gov/13326/ ; https://gms.gsfc.nasa.gov/old/13326 | title "Black Hole Visualization" → SVS title; "Schwarzschild-like" and "photon ring" removed (not confirmed) |
| NASA SVS 14576 "NASA Black Hole Visualization Takes Viewers Beyond the Brink" / SVS 14585 "Beyond the Brink: Tracking a Simulated Plunge into a Black Hole" (Schnittman & Powell, 2024) | VERIFIED VIA WEB SEARCH | ids, titles, credit J. Schnittman and B. Powell, release 2024-05-06, non-rotating 4.3e6 M☉, Discover supercomputer; YouTube "360 Video: NASA Simulation Plunges Into a Black Hole", "NASA Simulation's Plunge Into a Black Hole: Explained" | https://svs.gsfc.nasa.gov/14576 ; https://svs.gsfc.nasa.gov/14585 ; https://science.nasa.gov/universe/black-holes/supermassive-black-holes/new-nasa-black-hole-visualization-takes-viewers-beyond-the-brink/ ; https://www.youtube.com/watch?v=crXGmeWFb9o ; https://www.youtube.com/watch?v=chhcwk4-esM | "NASA Simulation's Plunge Into a Black Hole" identified as the YouTube explainer title; SVS ids/dates added. Scope statement (exterior GR / methodology only) kept |
| Einstein Toolkit website | VERIFIED VIA WEB SEARCH | https://einsteintoolkit.org, community NR platform | https://www.einsteintoolkit.org/ | none |
| Löffler et al., Class. Quantum Grav. 29, 115001 (2012) | VERIFIED VIA WEB SEARCH | title, 13 authors, doi:10.1088/0264-9381/29/11/115001, arXiv:1111.3344 | https://iopscience.iop.org/article/10.1088/0264-9381/29/11/115001 ; https://arxiv.org/abs/1111.3344 | DOI added (was "INSUFFICIENT DATA TO VERIFY page/DOI") |
| Schwarzschild 1916, Sitzungsber. Preuss. Akad. Wiss. 189–196 | VERIFIED VIA WEB SEARCH | title, pages, ADS 1916SPAW.......189S | https://ui.adsabs.harvard.edu/abs/1916SPAW.......189S/abstract ; https://de.wikisource.org/wiki/%C3%9Cber_das_Gravitationsfeld_eines_Massenpunktes_nach_der_Einsteinschen_Theorie | title added |
| Eddington 1924, Nature 113, 192 | VERIFIED VIA WEB SEARCH | title "A comparison of Whitehead's and Einstein's formulæ", doi:10.1038/113192a0 | https://www.nature.com/articles/113192a0 ; https://ui.adsabs.harvard.edu/abs/1924Natur.113..192E/abstract | title, DOI added |
| Finkelstein 1958, Phys. Rev. 110, 965 | VERIFIED VIA WEB SEARCH | title, pp. 965–967, doi:10.1103/PhysRev.110.965, abstract ("unidirectional membrane") | https://link.aps.org/doi/10.1103/PhysRev.110.965 ; https://ui.adsabs.harvard.edu/abs/1958PhRv..110..965F | page range, DOI added |
| Kruskal 1960, Phys. Rev. 119, 1743 | VERIFIED VIA WEB SEARCH | title "Maximal extension of Schwarzschild metric", 1 Sept 1960, doi:10.1103/PhysRev.119.1743 | https://link.aps.org/doi/10.1103/PhysRev.119.1743 ; https://ui.adsabs.harvard.edu/abs/1960PhRv..119.1743K/abstract | title, DOI added |
| Szekeres 1960, Publ. Math. Debrecen 7, 285 | PARTIALLY VERIFIED | title, vol. 7, pp. 285–301, GRG "Golden Oldie" reprint doi:10.1023/A:1020744914721 / not confirmed on a publisher page: original DOI 10.5486/PMD.1960.7.1-4.26 (snippet text and an Am. J. Phys. reference list only; given with that caveat) | https://ui.adsabs.harvard.edu/abs/1960PMatD...7..285S/abstract ; https://link.springer.com/article/10.1023/A:1020744914721 ; https://www.semanticscholar.org/paper/On-the-singularities-of-a-Riemannian-manifold-Szekeres/588eb96cc756c5a595ef1603521f4f3ec415519f | title, page range, reprint added |
| Henry 2000, ApJ 535, 350 | VERIFIED VIA WEB SEARCH | title, pp. 350–353, doi:10.1086/308819, arXiv:astro-ph/9912320 | https://iopscience.iop.org/article/10.1086/308819 ; https://ui.adsabs.harvard.edu/abs/2000ApJ...535..350H | page range, DOI added |
| Lewis & Kwan 2007, PASA 24, 46 | VERIFIED VIA WEB SEARCH | title, 24(2) 46–52, doi:10.1071/AS07012 (exact-string search returns the Cambridge Core article/PDF), arXiv:0705.1029, abstract ("rockets can increase your remaining time, but only up to a maximum value") | https://www.cambridge.org/core/journals/publications-of-the-astronomical-society-of-australia/article/no-way-back-maximizing-survival-time-below-the-schwarzschild-event-horizon/2A1CCF5CB13E7BEFA6441B3038C635A3 ; https://arxiv.org/abs/0705.1029 | **annotation and physics_notes §6 wording corrected** ("any thrust shortens / the geodesic maximizes" overstated the paper) |
| "On strategies of motion under the black hole horizon", arXiv:1905.02150 | PARTIALLY VERIFIED | arXiv id, title; summary: maximum πM on the E = 0 geodesic, best strategy = reach it and switch the engine off / not confirmed: authors, journal | https://arxiv.org/pdf/1905.02150 | new supporting pointer (references.md §3, inside the Lewis & Kwan entry) |
| Dormand & Prince 1980, J. Comput. Appl. Math. 6, 19 | VERIFIED VIA WEB SEARCH | title "A family of embedded Runge-Kutta formulae", 6(1) 19–26, doi:10.1016/0771-050X(80)90013-3 | https://www.sciencedirect.com/science/article/pii/0771050X80900133 | title, pages, DOI added |
| Hayward 2006, PRL 96, 031103 | VERIFIED VIA WEB SEARCH | title, 26 Jan 2006, doi:10.1103/PhysRevLett.96.031103; lapse function as quoted in later papers | https://link.aps.org/doi/10.1103/PhysRevLett.96.031103 ; https://arxiv.org/pdf/2104.07506 | title, DOI added |
| Bardeen 1968, GR5 Tbilisi | PARTIALLY VERIFIED | title "Non-singular general-relativistic gravitational collapse", GR5, Tbilisi 1968 / page: 174 (common citation, "pp. 174–175" of the abstracts) vs 87 (ADS 1968qtr..conf...87B) | https://ui.adsabs.harvard.edu/abs/1968qtr..conf...87B/abstract | "p. 174" no longer stated as certain |
| Ayón-Beato & García 2000, PLB 493, 149 | VERIFIED VIA WEB SEARCH | title "The Bardeen model as a nonlinear magnetic monopole", pp. 149–152, doi:10.1016/S0370-2693(00)01125-4, arXiv:gr-qc/0009077 | https://www.sciencedirect.com/science/article/abs/pii/S0370269300011254 ; https://ui.adsabs.harvard.edu/abs/2000PhLB..493..149A/abstract ; https://inspirehep.net/literature/534086 | title, DOI added |
| Dymnikova 1992, GRG 24, 235 | VERIFIED VIA WEB SEARCH | pp. 235–242, doi:10.1007/BF00760226, abstract | https://link.springer.com/article/10.1007/BF00760226 ; https://ui.adsabs.harvard.edu/abs/1992GReGr..24..235D | page range, DOI added |
| Ashtekar, Olmedo & Singh 2018, PRL 121, 241301 | VERIFIED VIA WEB SEARCH | title "Quantum transfiguration of Kruskal black holes", 10 Dec 2018, doi:10.1103/PhysRevLett.121.241301, arXiv:1806.00648 | https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.121.241301 ; https://arxiv.org/abs/1806.00648 | title, DOI added |
| NEW: Ni & Zimmermann 1978, Phys. Rev. D 17, 1473 | VERIFIED VIA WEB SEARCH | title as in the brief, pp. 1473–1476, 15 Mar 1978, doi:10.1103/PhysRevD.17.1473 | https://link.aps.org/doi/10.1103/PhysRevD.17.1473 ; https://www.wikidata.org/wiki/Q27349197 | new entry (brief's "17, 1473?" is correct) |
| NEW: MTW §13.6 (proper reference frame of an accelerated observer) | VERIFIED VIA WEB SEARCH | section number and topic (page not confirmed) | https://en.wikipedia.org/wiki/Proper_reference_frame_(flat_spacetime) ; https://www.physicsforums.com/threads/proper-reference-frame-accelerated-observer.706593/ | new |
| NEW: Hamilton & Polhemus 2010, New J. Phys. 12, 123027 | VERIFIED VIA WEB SEARCH | title as in the brief, published 16 Dec 2010, doi:10.1088/1367-2630/12/12/123027, arXiv:1012.4043 | https://iopscience.iop.org/article/10.1088/1367-2630/12/12/123027 ; https://arxiv.org/abs/1012.4043 | new entry (brief's "12, 123027?" is correct) |
| NEW: Hamilton & Polhemus, arXiv:0903.4717 (2009) "The edge of locality" | PARTIALLY VERIFIED | title, authors, arXiv id, date, abstract / not confirmed: journal version | https://arxiv.org/abs/0903.4717 | new (cited by the camera agent) |
| NEW: d3-celestial 0.7.35 (O. Frohn, BSD-3-Clause) | VERIFIED (npm registry metadata + web search) | name, version, licence, author, repository; readme footnote naming XHIP as the star source | https://github.com/ofrohn/d3-celestial ; https://ofrohn.github.io/celestial-demo/ ; npm registry `d3-celestial` | new |
| NEW: XHIP, Anderson & Francis 2012, Astron. Lett. 38, 331 | VERIFIED VIA WEB SEARCH | pp. 331–346, doi:10.1134/S1063773712050015, arXiv:1108.4971, VizieR V/137D | https://ui.adsabs.harvard.edu/abs/2012AstL...38..331A ; https://link.springer.com/article/10.1134/S1063773712050015 ; https://arxiv.org/abs/1108.4971 | new (the star data actually used) |
| NEW: HYG database (D. Nash, astronexus) | VERIFIED VIA WEB SEARCH | author, hosting, ~120,000 stars, licences HYG 4.x CC BY-SA 4.0, 3.x CC BY-SA 2.5 | https://astronexus.com/projects/hyg ; https://codeberg.org/astronexus/hyg | new; marked **not used** (camera agent used d3-celestial/XHIP) |
| NEW: late-time exponential redshift, e-folding 4GM/c³ — Hirata, Caltech Ph 236 lecture XXIV | VERIFIED VIA WEB SEARCH | exponential increase of the redshift with time scale 4M; 10 M☉ example 4M = 200 µs | http://www.tapir.caltech.edu/~chirata/ph236/2011-12/lec24.pdf | new (lecture notes; no textbook section could be confirmed) |
| NEW: Ames & Thorne 1968, ApJ 151, 659 | PARTIALLY VERIFIED | title, pp. 659–670, abstract: flux e-folding time ~ 1/κ (order of magnitude) / no DOI seen | https://www.osti.gov/biblio/4546392 ; https://www.wikidata.org/wiki/Q40797443 | new |
| NEW: Hawking 1975, Commun. Math. Phys. 43, 199 | VERIFIED VIA WEB SEARCH | pp. 199–220, doi:10.1007/BF02345020, abstract (T = ħκ/2πk) | https://link.springer.com/article/10.1007/BF02345020 ; https://projecteuclid.org/journals/communications-in-mathematical-physics/volume-43/issue-3/Particle-creation-by-black-holes/cmp/1103899181.full | new (context only) |
| NEW: Wald §12.5, surface gravity (eq. 12.5.14), κ = 1/4M | PARTIALLY VERIFIED | formula and equation number as quoted by a secondary notes page | http://kstar.wikidot.com/surface-gravity-of-the-schwarzschild-blackhole | new |
| MTW, *Gravitation* (Freeman 1973) | VERIFIED VIA WEB SEARCH | publisher, city, year, ISBN 0-7167-0344-0; Princeton 2017 reissue | https://en.wikipedia.org/wiki/Gravitation_(book) ; https://press.princeton.edu/books/hardcover/9780691177793/gravitation | city, ISBN, reissue added |
| MTW ch. 31 (Schwarzschild geometry); exercises 31.1 "Tidal forces on infalling explorer", 31.2 "Nonradial light cones", 31.4 "How long to live?", 31.5 "Eddington–Finkelstein and Kruskal–Szekeres compared" | PARTIALLY VERIFIED | titles from a third-party solution-manual index / MTW's own text not seen | https://ebin.pub/solution-manual-for-gravitation-mtw-0716703440-9780716703440-9780691177793-9780716703341-9789570911336-9784621083277.html | **exercise 31.1 was cited for the Kretschmann scalar (physics_notes §9, TEST 5): it is the tidal-force exercise** — moved to §10 |
| MTW Box 31.2 | PARTIALLY VERIFIED | described in search results as containing Kruskal–Szekeres diagrams | https://www.physicsforums.com/threads/understanding-maximally-extended-schwarzschild-solution.282374/ | flagged |
| MTW ch. 25 cycloid ("Cycloid relation between r and t for straight-in fall") | PARTIALLY VERIFIED | TOC entry exists in ch. 25 / section (a summary said §25.3) and eq. 25.38 not confirmed | https://archive.org/stream/GravitationMisnerThorneWheeler/Gravitation%20Misner%20Thorne%20Wheeler_djvu.txt | flagged |
| MTW §37.2 | PARTIALLY VERIFIED | ch. 37 is "Detection of gravitational waves"; §37.2 on test-particle motion in the detector's proper frame per a summary | https://archive.org/stream/GravitationMisnerThorneWheeler/Gravitation%20Misner%20Thorne%20Wheeler_djvu.txt | flagged |
| MTW §25.2, §25.5, eq. 25.38, §31.2 (eq. 31.6), §31.3, §31.4, §31.5 | INSUFFICIENT DATA TO VERIFY | — | — | each flagged "section number from memory — INSUFFICIENT DATA TO VERIFY" |
| Wald, *General Relativity* (U. Chicago Press 1984) | VERIFIED VIA WEB SEARCH | publisher, city, year | https://press.uchicago.edu/ucp/books/book/chicago/G/bo5952261.html ; https://ui.adsabs.harvard.edu/abs/1984ucp..book.....W/abstract | city added |
| Wald §3.3 "Geodesics" | VERIFIED VIA WEB SEARCH | section title (deviation equation inside it: from memory) | https://faculty.etsu.edu/gardnerr/5310/notes-Wald.htm | none |
| Wald §6.1 derivation, §6.4 "The Kruskal extension" | PARTIALLY VERIFIED | titles in one search summary | https://faculty.etsu.edu/gardnerr/5310/notes-Wald.htm ; https://en.wikipedia.org/wiki/General_Relativity_(book) | flagged |
| Wald problem 6.4 (radial infall) | INSUFFICIENT DATA TO VERIFY | — | — | flagged (still cited in validation.py TEST 3) |
| Carroll, *Spacetime and Geometry* (Addison-Wesley 2004), §5.6, §5.7 | PARTIALLY VERIFIED | book data / section titles in one summary only | https://preposterousuniverse.com/spacetimeandgeometry/ ; https://en.wikipedia.org/wiki/Spacetime_and_Geometry | subtitle, city added |
| Hawking & Ellis (CUP 1973), ch. 5, §5.5 | VERIFIED VIA WEB SEARCH | ch. 5 "Exact solutions"; §5.5 "The Schwarzschild and Reissner–Nordström solutions" | https://www.cambridge.org/core/books/large-scale-structure-of-spacetime/exact-solutions/6A2049F2E72FB11E6BD6FAF60C7744FC ; https://ncatlab.org/nlab/show/Reissner-Nordstr%C3%B6m+spacetime | §5.5 title added |
| Poisson, *A Relativist's Toolkit* (CUP 2004), ch. 1, ch. 5 | VERIFIED VIA WEB SEARCH | subtitle, chapter titles "Fundamentals", "Black holes" | https://www.cambridge.org/core/books/abs/relativists-toolkit/black-holes/F4B0C7983A6B04BFBF3EC0D9B9DE45E3 | subtitle added |
| Taylor & Wheeler, *Exploring Black Holes* (Addison Wesley Longman 2000), ch. 3 | VERIFIED VIA WEB SEARCH | book data, chapter "Plunging" | https://pubs.aip.org/physicstoday/article/54/11/59/411626/Exploring-Black-Holes-Introduction-to-General ; https://ocw.mit.edu/courses/8-224-exploring-black-holes-general-relativity-astrophysics-spring-2003/pages/readings/ | none |
| Hairer, Nørsett & Wanner, *Solving ODE I*, 2nd rev. ed. (Springer 1993) | PARTIALLY VERIFIED | book data, series vol. 8; §II.4 holds embedded formulas, step-size control, starting step size / §II.5, Table 5.2, PI-control section not confirmed | https://link.springer.com/book/10.1007/978-3-540-78862-1 ; https://dl.acm.org/doi/10.5555/153158 | subtitle, series added; section flags |
| Chandrasekhar, *The Mathematical Theory of Black Holes* (Clarendon/OUP 1983), ch. 3 | VERIFIED VIA WEB SEARCH | book data, ch. 3 "The Schwarzschild space-time" | https://ui.adsabs.harvard.edu/abs/1983mtbh.book.....C/abstract ; https://global.oup.com/academic/product/the-mathematical-theory-of-black-holes-9780198503705 | publisher detail |

## Complete list of corrections

1. `constants.py`: l_P standard uncertainty 1.8e-41 m → **1.8e-40 m** (CODATA 1.616255(18)e-35 m).
2. `constants.py`: ħ described as "rounded to 10 digits" → the 10 digits printed by CODATA (truncated).
3. Primary constants citation CODATA 2018 → **CODATA 2022**, Mohr, Newell, Taylor & Tiesinga,
   Rev. Mod. Phys. 97, 025002 (2025) (values identical).
4. M☉ provenance: identified as (GM)☉ᴺ(IAU 2015 B3) / G(CODATA 2014); the "IAU 2015 nominal solar mass"
   phrasing replaced by "nominal solar mass parameter"; ± 7e25 kg marked INSUFFICIENT DATA TO VERIFY.
5. NASA 2019: title "Black Hole Visualization" → SVS 13326 "Black Hole Accretion Disk Visualization";
   unconfirmed descriptors ("Schwarzschild-like", "photon ring") removed.
6. NASA 2024: "NASA Simulation's Plunge Into a Black Hole" is the YouTube explainer title; SVS pages are
   14576 "NASA Black Hole Visualization Takes Viewers Beyond the Brink" and 14585 "Beyond the Brink:
   Tracking a Simulated Plunge into a Black Hole" (released 2024-05-06; credit Schnittman & Powell).
7. Lewis & Kwan 2007: annotation and physics_notes §6 re-worded — rockets can *increase* the remaining
   time, up to the maximum πGM/c³ of the E = 0 geodesic; the implemented inward thrust shortens it for
   E > 0.
8. MTW exercise 31.1: not the Kretschmann exercise but "Tidal forces on infalling explorer" (removed
   from physics_notes §9; added to §10).
9. Bardeen 1968: page 174 no longer given as certain (ADS lists p. 87).
10. Szekeres 1960: page range 285–301 and GRG reprint added; the original article's DOI is given only
    with a caveat (not seen on a publisher page).
11. Titles, page ranges and DOIs added to Schwarzschild, Eddington, Finkelstein, Kruskal, Henry,
    Lewis & Kwan, Dormand & Prince, Hayward, Ayón-Beato & García, Dymnikova, Ashtekar et al.,
    Löffler et al.; subtitles/series/cities added to the textbooks.
12. Unconfirmed textbook section numbers are now individually labelled instead of blanket "from memory".

## Equations added or touched (tags)

* πGM/c³ = maximal proper time from the horizon to r = 0, on the E = 0 radial geodesic:
  ∫₀^{2M} dr/√(2M/r − 1) = πM — **EXACT GR RESULT** (checked by quadrature in `tests/test_citations.py`,
  relative error < 1e-12); citation Lewis & Kwan 2007 (VERIFIED VIA WEB SEARCH, abstract) and
  arXiv:1905.02150 (PARTIALLY VERIFIED).
* "The implemented thrust shortens the remaining time for E > 0" — **EXACT GR RESULT** (argument, not a
  new formula): for radial motion u^r = −√(E² − f) depends only on (r, E), so along the thrusting
  worldline d/dτ[τ + T(r, E)] = (∂T/∂E)(dE/dτ), where T(r, E) is the free-fall remaining time; T falls
  with E for E > 0 (checked in the test) and the implemented thrust has dE/dτ = −(α/|n|) u^r > 0.
* Late-time redshift of the radially emitted signal, 1 + z ∝ exp(u/4M), e-folding time 4GM/c³ = 1/κ,
  κ = 1/4M — **EXACT GR RESULT** derived by the engine agent (`src/slab/signals.py`,
  `docs/additions/engine.md`); only its citations were added here (Hirata lecture XXIV: VERIFIED;
  Ames & Thorne 1968: PARTIALLY VERIFIED; Wald §12.5: PARTIALLY VERIFIED).
* M☉ relations: M☉(brief) = (GM)☉ᴺ / G_2014, (GM)☉ᴺ / G_2022 = 1.98841e30 kg — **LABELLING CONVENTION**
  (definitions of the adopted constants), checked in the tests.
* No other equation of physics_notes.md was changed.

## Tests added and results

`tests/test_citations.py` (8 tests, all pass):
constants equal the CODATA 2022 / SI / IAU values incl. uncertainties and exact definitions;
l_P = √(ħG/c³) within the CODATA uncertainty; propagated uncertainties use the corrected l_P value;
M☉ relations (brief = GM/G_2014 to 5e-6; GM/G_2022 is 3.0e-5 lower); no "not re-verified" /
"[citation from memory]" flag remains in references.md, physics_notes.md, references/README.md or the
constants; every bibliography entry of references.md carries a status (≥ 35 entries checked); every
DOI in references.md and constants.py appears in the verification table of this file; πM / 4M/3 and the
monotonic fall of the free-fall remaining time with E.

Full run in this worktree: `python3 -m pytest tests -q` → 34 passed (26 existing + 8 new);
`node tests/viewer/test_null_geodesics.mjs` → all checks passed. Nothing under `renders/` was touched,
so the viewer build/check was not required.

## Follow-ups for the coordinator (strings in files I do not own)

* `src/slab/validation.py`: TEST 0 reference "CODATA 2018 (Tiesinga et al. 2021)" → "CODATA 2022 (Mohr
  et al., Rev. Mod. Phys. 97, 025002 (2025); values identical to CODATA 2018)"; TEST 6 "Planck length
  CODATA 2018" → "CODATA 2022"; TEST 5 drop "MTW ex. 31.1" (it is the tidal-force exercise); TEST 3
  "Wald problem 6.4" and TEST 1/TEST 7 MTW section numbers are unverified; `verification_caveats[0]`
  ("Constant values transcribed from CODATA 2018; no network access to NIST ...") → "Constant values
  verified by web search against CODATA 2022 (2026-09-25); see references.md §5".
* `tools/summarize_scenarios.py` line 34: "(the geodesic maximizes it; Lewis & Kwan 2007)" → "(the
  maximum, πGM/c³, belongs to the E = 0 geodesic; Lewis & Kwan 2007)".
* `src/slab/curvature.py` docstring "MTW §31.2, eq. 31.6", `src/slab/geodesic.py` "MTW §25.5, Box 25.6
  analogue", `src/slab/metric.py` "§31.4, Box 31.2": section numbers unverified (flag or keep as
  pointers); `src/slab/integrators.py` "initial step guess (Hairer et al. I.4)" → "§II.4 (starting step
  size)".
* `README.md` / `docs/UPGRADE_PROMPT.md` / `PROJECT_STATE.md`: item 1 ("citations never verified online")
  can be marked done, with the remaining INSUFFICIENT DATA items listed above.
* Regenerate `validation_report.json`, `docs/validation_report.md` and the data exports so that the new
  constant strings and the corrected l_P uncertainty propagate.

## Known limitations

* Verification rests on search-result titles, URLs and snippets (and the search tool's summaries of
  them); no full text, NIST page or SVS page was opened. Summaries were cross-checked against a second
  query where possible; one summary claim (IAU nominal solar mass in kg) was demonstrably false and was
  rejected, so single-summary confirmations (marked PARTIALLY VERIFIED) should be treated with caution.
* Most MTW section/equation numbers could not be confirmed; exercise titles come from a third-party
  solution-manual index.
* No primary source was found for the brief's M☉ uncertainty (± 7e25 kg); no textbook section was found
  for the exponential late-time redshift (lecture notes and a 1968 abstract only).
* Release dates of the NASA pages come from page metadata shown in search results.
