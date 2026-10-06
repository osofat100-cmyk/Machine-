# Smart 16:9 cropper and collage

Two programs:

- **`all_layouts.py`** lists *every* possible 16:9 collage of 2–7 photos:
  every combination of photos, every layout shape, every position and every
  priority choice. Nothing is ranked or skipped.
- **`smart_collage.py`** does the smart cropping and single collages.

## all_layouts.py — every possibility

```bash
pip install -r requirements.txt
python all_layouts.py count photos/*.jpg                 # how many, and disk needed
python all_layouts.py run   photos/*.jpg -o results      # compute all of them (uses all CPU cores)
```

A possibility is made of four choices:

| choice | what varies | count for k photos |
|---|---|---|
| photos | every combination of k different photos from the pool | C(n, k) |
| shape | every slicing layout: each split puts two groups side by side or one above the other, mirror images included | 2, 6, 22, 90, 394, 1806 for k = 2..7 |
| positions | which photo goes in which slot | k! |
| priority | none, or any group of 1..k−1 photos made bigger (area × boost, default 2×; several boosts allowed: `--boost 1.5 2 3`) | 1 + (2^k − 2) × boosts |

Prioritising all k photos looks exactly like prioritising none, so it is
covered by the "none" row.

For 7 photos with one boost factor:

| k | combos | shapes | positions | priorities | possibilities |
|--:|--:|--:|--:|--:|--:|
| 2 | 21 | 2 | 2 | 3 | 252 |
| 3 | 35 | 6 | 6 | 7 | 8,820 |
| 4 | 35 | 22 | 24 | 15 | 277,200 |
| 5 | 21 | 90 | 120 | 31 | 7,030,800 |
| 6 | 7 | 394 | 720 | 63 | 125,102,880 |
| 7 | 1 | 1,806 | 5,040 | 127 | 1,155,984,480 |
| | | | | **total** | **1,288,404,432** |

Without priorities that is 11,334,624 layouts. One CPU core computes about
240,000 possibilities a second, so the full run is about 1.5 hours on one
core, or roughly 15–20 minutes on 8 cores. It writes about 14 GB of gzipped
CSV. The run shows progress with an ETA, and if stopped it resumes where it
left off: finished files are skipped.

Each result row:

```
combo_id, shape_id, perm_id, priority_mask, boost, fit_avg, fit_min, priority_share
```

- `fit_avg` / `fit_min`: share of the photo kept after cropping to its tile
  (area-weighted average, and the worst tile)
- `priority_share`: share of the canvas the priority photos get
- `combos.csv`, `shapes_k*.csv` and `images.csv` decode the ids;
  `priority_mask` bit j means image number j+1 has priority

```bash
# Explain one possibility in words (photos per slot, tile sizes, fit)
python all_layouts.py describe results --combo 56 --shape 10 --perm 5 --priority 2 --boost 2

# Draw it, or draw every row of one or more result files
python all_layouts.py render results --combo 56 --shape 10 --perm 5 --priority 2 --boost 2
python all_layouts.py render results --from results/k4/combo_0056/*.csv.gz --scale 0.5
```

Rendering is far slower than computing (about a quarter of a second per 4K
image per core), so drawing all 1.29 billion would take years and petabytes. Render
the files or rows you want to see; `--limit` and `--scale` help.

## smart_collage.py — cropping and single collages

Smart cropping and collage layout in the style of Google Photos, for turning a
mix of landscape and portrait photos into 16:9 images.

```bash
pip install -r requirements.txt

# One 16:9 image per photo
python smart_collage.py crop photos/*.jpg -o cropped/                # fill the frame (default)
python smart_collage.py crop photos/*.jpg -o cropped/ --mode blur    # fit over a blurred copy
python smart_collage.py crop photos/*.jpg -o cropped/ --mode auto    # blur only when a crop would keep <50%

# All photos in one 16:9 collage (4K by default)
python smart_collage.py collage photos/*.jpg -o collage.jpg --size 3840x2160 --gap 12

# Every combination of 2-7 different photos, ranked by how much of each photo is kept
python smart_collage.py combos photos/*.jpg -o combos/ --min 2 --max 7 --top 10
```

## How it works

**Saliency map** (computed at 512 px for speed):
- spectral-residual saliency (Hou & Zhang, 2007), mirror-padded so the image
  borders don't produce fake edges
- edge energy (Sobel)
- local colour contrast in Lab, so a colourful subject counts but a uniformly
  coloured sky or wall doesn't
- a weak centre prior
- faces (OpenCV Haar frontal + profile) added as strong blobs, plus a
  weaker blob below each face for the body

**Crop search:** every 16:9 window (at 100/90/80% zoom) is scored with
summed-area tables:
- `+` share of total saliency kept, and saliency density
- `−` saliency or edges on the crop border (it is slicing through something)
- `−` any face partly or fully cut off, or with no headroom
- `+` the subject's centroid near a rule-of-thirds line or the centre
- `−` zooming in (keep as much of the photo as possible)

**Collage:** the photos are arranged as a *slicing tree*. Every split puts
two groups of photos side by side or one above the other, so rows, columns
and rows-inside-columns are all possible. At their natural shapes no photo is
cropped, so the only crop comes from stretching the whole tree to 16:9, and
every tile shares it equally:

    fit = min(tree_aspect / (16/9), (16/9) / tree_aspect)

A dynamic program over subsets builds every tree for every subset at once.
Trees with shapes within about 2% of each other are merged, keeping the one
whose smallest tile is largest. The tree closest to 16:9 wins, as long as no
tile is smaller than a quarter of the average tile size. Each tile is then
smart-cropped to its cell.

**Combinations:** `combos` takes a pool of photos and lays out *every*
combination of 2-7 different photos. With 7 photos that is
C(7,2)+...+C(7,7) = 120 collages, and the search takes under a second. It writes
`combinations.csv`, ranking every combination by fit, and renders the top N
plus the best collage for each image count. Collages with fewer photos have
fewer possible layouts, so they usually can't reach as close to 100%. Each
one still gets the closest fit its photos allow.

Results for the example set (one 1280x720 and six portraits of
1080x1350-1620):

| images | combinations | best fit | worst fit |
|-------:|-------------:|---------:|----------:|
| 2 | 21 | 87.2% | 69.0% |
| 3 | 35 | 88.9% | 64.8% |
| 4 | 35 | 99.9% | 90.3% |
| 5 | 21 | 99.6% | 80.4% |
| 6 | 7  | 99.8% | 92.7% |
| 7 | 1  | 99.6% | 99.6% |

The layout search covers every combination for pools up to about 12 photos;
past that, rendering the collages takes far longer than the search.
