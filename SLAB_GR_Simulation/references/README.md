# references/

Reference material index for SLAB_GR_Simulation.  The annotated bibliography with a verification
status for every entry is `../references.md`; equation-level citations and their flags are in
`../physics_notes.md`; the verification table (entry | status | confirmed details | confirming URLs |
corrections) is `../docs/additions/citations.md`.

Verification method (session of 2026-09-25): targeted web searches, several per entry (title, authors,
journal, volume, page, year, DOI).  Direct page fetches were blocked by the environment's network
policy, so a detail was accepted only when search-result titles, URLs (doi.org, link.aps.org,
iopscience, adsabs, arxiv, svs.gsfc.nasa.gov, physics.nist.gov, ...) or snippets showed it.  Full
texts were not read; textbook section numbers are therefore verified only where a table of contents
or a citing page showed them.

Source classes required by the project brief and where each is used:

| class | used for | verification status (2026-09-25) |
|---|---|---|
| NASA / NASA Goddard black-hole visualizations: SVS 13326 "Black Hole Accretion Disk Visualization" (Schnittman, 2019); SVS 14576 / 14585 "Beyond the Brink" plunge (Schnittman & Powell, 2024) | visual sanity reference for the first-person view (shadow, lensed sky, aberration) — **not** evidence about interior quantum physics | VERIFIED VIA WEB SEARCH (page ids, titles, credits, dates); earlier titles corrected |
| Einstein Toolkit (einsteintoolkit.org; Löffler et al., CQG 29, 115001 (2012)) | methodological reference for numerical relativity (not used directly: this project integrates test-particle worldlines on an exact background) | VERIFIED VIA WEB SEARCH |
| peer-reviewed GR references (Schwarzschild 1916, Eddington 1924, Finkelstein 1958, Kruskal 1960, Szekeres 1960, Henry 2000, Lewis & Kwan 2007, Dormand & Prince 1980; added: Ni & Zimmermann 1978, Hamilton & Polhemus 2009/2010, Ames & Thorne 1968, Hawking 1975) | equations (Schwarzschild, Eddington–Finkelstein, Kruskal–Szekeres, Kretschmann, thrust inside the horizon, accelerated-frame terms, late-time redshift) | VERIFIED VIA WEB SEARCH (titles, volumes, pages, DOIs) except: Szekeres DOI, Hamilton & Polhemus 2009 journal version, Ames & Thorne DOI — PARTIALLY VERIFIED; Lewis & Kwan annotation corrected |
| textbooks (MTW, Wald, Carroll, Hawking & Ellis, Poisson, Taylor & Wheeler, Hairer–Nørsett–Wanner, Chandrasekhar) | derivations, sign conventions, numerical method | publisher/year/edition VERIFIED; section numbers individually flagged — many "section number from memory — INSUFFICIENT DATA TO VERIFY"; MTW exercise 31.1 citation corrected |
| CODATA 2022 / NIST / BIPM SI / IAU | constants | VERIFIED VIA WEB SEARCH (G, ħ, l_P are the CODATA 2022 values; c, h, au, Julian year exact); l_P uncertainty corrected in the code; M☉ primary source PARTIALLY VERIFIED |
| regular black-hole toy models (Hayward 2006, Bardeen 1968, Ayón-Beato & García 2000, Dymnikova 1992; context: Ashtekar–Olmedo–Singh 2018) | SPECULATIVE menu only | VERIFIED VIA WEB SEARCH except Bardeen's page number (174 vs 87: INSUFFICIENT DATA TO VERIFY) |
| sky data: d3-celestial 0.7.35 (O. Frohn, BSD-3-Clause) with XHIP (Anderson & Francis 2012); HYG database (not used) | star field of the first-person camera | VERIFIED (npm registry metadata + web search); licence of the XHIP data beyond the package's BSD release: INSUFFICIENT DATA TO VERIFY |
| lecture notes: C. M. Hirata, Caltech Ph 236 lecture XXIV | late-time exponential redshift, e-folding time 4GM/c³ | VERIFIED VIA WEB SEARCH (not peer reviewed) |

Anything that could not be confirmed is marked "PARTIALLY VERIFIED" or "INSUFFICIENT DATA TO VERIFY"
rather than filled in.
