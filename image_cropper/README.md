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

**Collage:** a justified-rows layout. Every way of splitting the photos into
rows, over many orderings, is scored on how far each cell's shape is from
its photo's shape (the crop it needs) and on how even the tile sizes are. The
best layout is then filled exactly, and each tile is smart-cropped to its
cell.

For the example set (one 1280×720 and six portraits of 1080×1350–1620) the
collage comes out as two rows: the landscape photo and two portraits on top,
four portraits below. Each tile loses only a small strip, while cropping
every photo to 16:9 would throw away 55–63% of each portrait.
