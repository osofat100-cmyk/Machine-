# references/

Reference material index for SLAB_GR_Simulation.  The annotated bibliography with
verification flags is `../references.md`; equation-level citations are in `../physics_notes.md`.

Source classes required by the project brief and where each is used:

| class | used for | verification status in this build |
|---|---|---|
| NASA / NASA Goddard black-hole visualizations (Schnittman 2019; Schnittman & Powell 2024) | visual sanity reference for the first-person view (shadow, lensed sky, aberration) — **not** evidence about interior quantum physics | not fetched (no network egress); described from the author's knowledge |
| Einstein Toolkit documentation | methodological reference for numerical relativity (not used directly: this project integrates test-particle worldlines on an exact background) | not fetched |
| peer-reviewed GR references | equations (Schwarzschild, Eddington–Finkelstein, Kruskal–Szekeres, Kretschmann, thrust inside the horizon) | citations from memory; flagged in references.md |
| textbooks (MTW, Wald, Carroll, Hawking & Ellis, Poisson, Taylor & Wheeler, Hairer–Nørsett–Wanner) | derivations, sign conventions, numerical method | citations from memory; flagged |
| CODATA / NIST / IAU | constants | transcribed values; cross-checked internally (TEST 0) |
| regular black-hole toy models (Hayward, Bardeen, Dymnikova) | SPECULATIVE menu only | flagged |

Anything that could not be verified in this environment is marked "NOT RE-VERIFIED ONLINE IN THIS
SESSION" or "INSUFFICIENT DATA TO VERIFY" rather than filled in.
