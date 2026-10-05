# Smart 16:9 cropper and collage

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
