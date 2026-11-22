# Self-powered earbuds: area, power and energy-harvesting analysis

Working notes for one question: **could earbuds run on energy from their own surface?**
Rule used throughout: only numbers a source states (or exact math on them); anything not found is marked "not found".

Status (2026-11-22): earbud chosen, true areas measured from the maker's 3D model, every harvesting type compared → **solar wins**. Next step in progress: which solar technology can physically fit a small, irregular, doubly-curved shape.

---

## 1. Ranking earbuds by surface area ÷ power use

Power per bud = battery energy ÷ rated hours. Area = bounding box from published dimensions, 2(HW+HD+WD).
Only models with a stated energy (or mAh **and** voltage) **and** published bud dimensions can be ranked.

| # | Earbud | Battery per bud (source) | Rated h | Power | Box area | cm²/mW |
|---|---|---|---|---|---|---|
| 1 | **JBL Endurance Peak 3** | 70 mAh × 3.85 V = 269.5 mWh (JBL sheet) | 10 | 26.95 mW | 96.53 cm² | **3.58** |
| 2 | Oladance OWS Pro | 150 mAh × 3.82 V (52audio label photo); dims/runtime retailer-only | 16 | 35.81 mW | 97.20 cm² | 2.71 |
| 3 | JBL Live Beam 3 | 68 mAh × 3.85 V (JBL) | 12 | 21.82 mW | 39.40 cm² | 1.81 |
| 4 | Technics EAH-AZ100 | 85 mAh × 3.7 V (Technics) | 12 | 26.21 mW | 34.42 cm² | 1.31 |
| 5 | Cambridge Melomania M100 | 0.404 Wh (FCC battery photo, partly glared) | 16 | 25.25 mW | 27.40 cm² | 1.09 |
| 6 | JBL Tune Buds 2 | 68 mAh × 3.85 V (JBL) | 12 | 21.82 mW | 22.31 cm² | 1.02 |
| 7 | Beats Solo Buds | 105 mAh / 0.403 Wh (52audio label photo) | 18 | 22.39 mW | 22.41 cm² | 1.00 |

Not rankable (missing mAh or dimensions): Audio-Technica ATH-CKS50TW, Sony WF-1000XM5 (bud 0.366 Wh per 52audio, no dims), Sony WF-C710N (0.269 Wh, no dims), and others. 29 models were checked in total.

## 2. JBL Endurance Peak 3 — true geometry from JBL's own 3D model

**Source:** the 3D/AR viewer on JBL Canada's product page loads JBL's model (Blender export, real scale, 23 named parts, case shown open with one bud inside and one beside it). Fetched like any page visitor; kept out of git (see `.gitignore`), recreate with `scripts/fetch_jbl_model.py`.

**Method** (`scripts/exterior.py`, `scripts/ep3_analyze.py`):
1. Densely sample every triangle → voxelise (0.15 mm bud / 0.25 mm case) → thicken, fill enclosed space, thin back → everything not solid is "outside".
2. **Exact outer-skin area** = Σ (original triangle area × share of its samples that face outside). Voxels only classify; area comes from the real triangles.
3. **Sun-catching area** = 2-D shadow of the outer skin from 400 evenly spread directions (holes, e.g. the ear-hook loop, preserved).
4. Case: lid rotated +90° shut about a hinge pivot fitted by seating the lid's inner panel on the base rim and centring it over the base footprint. The compliance-label sticker (sits 0.012 mm off the case bottom) is excluded as a duplicate surface.

**Validation** (same code): sphere 5025.6 vs 5026.2 mm²; hollow box with a 0.4 mm seam + hidden cavity 5144.0 vs 5144.0 mm² (cavity excluded); torus 2365.9 vs 2366.4 mm², top shadow 761.8 vs 754.0 mm² (hole kept); box shadow best/mean 704/552 vs 700/550 mm²; sphere volume 4189 vs 4188 mm³. The two buds in the model measure 4657.6 vs 4657.1 mm².

**Scale check vs JBL datasheet:** case within ~1 % (91.25 vs 90.93 mm long, 35.18 vs 35.57 mm tall, base shell 57.6 vs 57.94 mm deep). Bud: best orientation at true scale within 3.5 %; uniform ×1.0315 brings all three within 1.3 % → both "model" and "datasheet-scaled" values below.

| | Earbud (model / datasheet-scaled) | Case, lid closed (model / scaled) |
|---|---|---|
| **Outer skin** | **46.6 / 49.6 cm²** | **158.5 / 160.0 cm²** |
| Old box estimate | 96.5 cm² (true = 48 % of it) | 211.3 cm² (true = 75 %) |
| Convex-hull area (lower-bound check) | 43.9 cm² | 152.2 cm² |
| Shadow, best angle | 11.8 / 12.6 cm² | 48.9 / 49.3 cm² |
| Shadow, lying flat (sun overhead) | – | 48.5 / 48.9 cm² |
| Shadow, all-angle average | 9.2 / 9.8 cm² | 38.1 / 38.5 cm² |
| Shadow, worst angle | 5.7 / 6.1 cm² | 19.3 / 19.5 cm² |
| Volume | 9.42 cm³ | – |
| Ear-contact rubber (tip + housing over-mould) | ≤ 10.6 cm² | – |

Parts check: the three rubber pieces are the ear tip (outer wall 14 mm), the tip's inner wall (12.9 mm) and the rubber over the driver housing (16.6 mm) — all one earbud (verified by colour render).

## 3. Solar on the earbud and case (best bendable cell: certified 33.6 % flexible Si-perovskite tandem, standard test sun 100 mW/cm²)

- **Earbud fully covered:** 192–398 mW depending on angle vs **27 mW** used → 7–15× its draw in direct sun (not worn). Break-even needs only **0.80 cm²** of cell in direct sun (7–14 % of its shadow).
- **Case fully covered** (battery 950 mAh × 3.7 V = 3,515 mWh):

| Case vs sun | Power | Refill both buds (539 mWh) | Listening per hour of sun | Fill case battery |
|---|---|---|---|---|
| Best angle | 1.64 W | ≥ 20 min | ≤ 30.5 h | ≥ 2.1 h |
| Lying flat | 1.63 W | ≥ 20 min | ≤ 30.2 h | ≥ 2.2 h |
| Average | 1.28 W | ≥ 25 min | ≤ 23.8 h | ≥ 2.7 h |
| Worst | 0.65 W | ≥ 50 min | ≤ 12.1 h | ≥ 5.4 h |

No charging losses included (none published for these parts). Real sun is often below the 1000 W/m² rating condition. Head shading when worn not modelled (needs a head model).

## 4. Every harvesting type compared (`scripts/harvest_compare.py`)

| Type | Basis from the 3D model | Power typical → best | Share of 26.95 mW | Runtime (10 h normally) |
|---|---|---|---|---|
| **Sunlight** (full sun) | shadow 9.2 cm² | **309 → 398 mW** | **11–15×** | **indefinite in sun** |
| Indoor light 1000 lux | shadow 9.2 cm² | 0.18 → 1.5 mW | 0.7–5.7 % | 10.1 → 10.6 h |
| Body heat (thermoelectric) | ear rubber ≤ 10.6 cm² | 0.15 → 0.76 mW | 0.5–2.8 % | 10.05 → 10.3 h |
| Sweat biofuel cell | ear rubber ≤ 10.6 cm² | 0.72 → 12.8 mW (peak, while sweating, arm data) | 2.7–47 % | 10.3 → 19 h |
| Motion, electromagnetic | **whole** bud volume (impossible bound) | 0.47 → 13.7 mW (wrist/leg data) | 1.8–51 % | 10.2 → 20 h |
| Motion, triboelectric | **whole** skin (impossible bound) | 0.22 → 2.4 mW | 0.8–8.7 % | 10.1 → 11 h |
| Jaw / ear canal | per chew | 0.01 → 0.07 mW while chewing (44 µJ/cycle = 1.6 ms of music) | ≤ 0.3 % | ~10 h |
| Radio waves | ideal antenna aperture | 0.001 → 0.04 mW | ≤ 0.1 % | ~10 h |
| Sound 90–100 dB | whole skin, 100 % conversion | 0.005 → 0.05 mW | ≤ 0.2 % | ~10 h |

**Conclusion:** solar is the only source that can run the bud on its own; heat/motion/sweat add percent-level top-ups at best.

## 5. Next: which solar technology can fit a small doubly-curved shape — in progress

## Reproduce

```bash
pip install trimesh scipy shapely scikit-image rtree numpy
python3 scripts/fetch_jbl_model.py          # JBL's GLB -> models/ (git-ignored)
python3 scripts/ep3_analyze.py models/JBL_Endurance_Peak_3_original.glb data/out.json
python3 scripts/export_measured.py          # measured earbud + closed case GLB/STL -> models/
python3 scripts/harvest_compare.py
```

## Sources
- JBL Endurance Peak 3 spec sheet — https://be.jbl.com/on/demandware.static/-/Sites-masterCatalog_Harman/default/dw8aefc1cc/pdfs/JBL%20Endurance%20Peak%203_EN.pdf
- JBL Canada product page (3D viewer) — https://ca.jbl.com/en_CA/ENDURANCE-PEAK-3.html
- JBL Live Beam 3 — https://static.dstewart.com/media/wysiwyg/information-centers/jbl/sales-assets/spec-sheets/pdfs/JBL_Live_Beam_3_Specsheet_EN.pdf ; JBL Tune Buds 2 — https://support.jbl.com/on/demandware.static/-/Sites-masterCatalog_Harman/default/dwe2c55a89/pdfs/JBL_TUNE_BUDS_2_Specsheet_ES.pdf
- Technics EAH-AZ100 — https://jp.technics.com/support/downloads/TWS/oi/gb/en/5/pages/id_oi01_761.html , https://help.na.panasonic.com/answers/features-specifications-technics-headphones-earbuds-model-eah-az100-k-eah-az100-s/
- Cambridge M100 — https://www.cambridgeaudio.com/gbr/en/products/melomania/melomania-m100 ; FCC photo — https://fccid.io/YKBCA0908-043/Internal-Photos/Internal-Photos-6952860
- 52audio teardowns: Beats Solo Buds https://www.52audio.com/archives/212545.html , Oladance OWS Pro https://www.52audio.com/archives/181397.html , Sony WF-1000XM5 https://www.52audio.com/archives/179869.html
- Beats Solo Buds — https://www.beatsbydre.com/earbuds/solo-buds
- 33.6 % flexible tandem — https://news.cgtn.com/news/2026-01-07/Chinese-researchers-achieve-breakthrough-in-flexible-solar-cells-1JJrDGUCtag/p.html
- Standard test conditions — https://www.ise.fraunhofer.de/en/service-units/callab/callab-pv-modules/stc-messungen.html
- Indoor PV review — https://pubs.rsc.org/en/Content/ArticleLanding/2026/EL/D5EL00210A ; lux→irradiance — https://arxiv.org/pdf/2011.14217 ; 1000 lux cell outputs — https://eprints.soton.ac.uk/355658/1/Nanoenergy2013_Abstract_solar_yi_20Draft_20v1_204.pdf
- Thermoelectric — https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10131832/ , https://www.sciencedirect.com/science/article/abs/pii/S1385894725004814
- Sweat biofuel — https://techxplore.com/news/2017-06-skin-based-biofuel-cell-scavenging-energy.pdf , https://pubs.rsc.org/en/content/articlehtml/2025/ee/d4ee03646h , https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9820692
- Motion — https://www.researchgate.net/publication/270595245 , https://www.researchgate.net/publication/344800296 , https://spiral.imperial.ac.uk/server/api/core/bitstreams/12da4dfe-fc47-4ee7-ae7c-1e40e101e389/content , https://pmc.ncbi.nlm.nih.gov/articles/PMC6738370
- Jaw/ear canal — https://www.osti.gov/etdeweb/biblio/22483829 , https://techxplore.com/news/2014-09-piezoelectric-chin-device-harvests-jaw.html
- Ambient RF — https://t4awstest.cc.ic.ac.uk/media/imperial-college/faculty-of-engineering/electrical-and-electronic-engineering/public/optical-and-semiconductor-devices/pubs/2013_07_TMTT.pdf , https://arxiv.org/pdf/1408.3198
- Real-world solar earbud case mod — https://hackaday.com/2021/08/11/wireless-earbuds-charge-themselves
