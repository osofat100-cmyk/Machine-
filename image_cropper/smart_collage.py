#!/usr/bin/env python3
"""
Smart 16:9 cropping and collage layout, in the spirit of Google Photos.

Three things are done here:

1. Smart crop: every image gets a saliency map (spectral-residual saliency,
   edge energy, local colour contrast, and detected faces). A window of the
   target aspect ratio is slid over the image and scored on how much of the
   salient content it keeps, whether it slices through a face or a busy edge,
   and how well the subject sits on the rule-of-thirds grid. Summed-area
   tables make each window O(1) to score.

2. Collage: photos are arranged as a slicing tree (every split puts two
   groups side by side or one above the other), searched exhaustively over
   all trees. The tree whose shape is closest to 16:9 wins, so as much of
   each photo as possible is kept, and each tile is then smart-cropped to
   its exact cell.

3. Combinations: given a pool of photos, every combination of 2-7 distinct
   photos is laid out and ranked by fit (the share of each photo kept).

Portraits cropped all the way down to 16:9 lose most of the frame, so the
crop command also offers Google-Photos-style "blur" fill (the photo sits on a
blurred, dimmed copy of itself) and an "auto" mode that picks per image.

Usage:
    python smart_collage.py crop    img1.jpg img2.jpg ... -o out_dir [--mode crop|blur|auto]
    python smart_collage.py collage img1.jpg img2.jpg ... -o collage.jpg [--size 3840x2160]
    python smart_collage.py combos  img1.jpg ... img7.jpg -o combos/ [--min 2 --max 7 --top 10]
"""

import argparse
import itertools
import math
import os

import cv2
import numpy as np
from PIL import Image, ImageFilter, ImageOps

TARGET_ASPECT = 16 / 9
ANALYSIS_MAX_SIDE = 512  # saliency is computed on a downscaled copy

_CASCADES = None


def _cascades():
    global _CASCADES
    if _CASCADES is None:
        if not hasattr(cv2, "CascadeClassifier"):  # OpenCV 5 moved Haar cascades to contrib
            print("warning: Haar cascades unavailable, face detection disabled "
                  "(pip install 'opencv-python-headless<5')")
            _CASCADES = []
            return _CASCADES
        base = cv2.data.haarcascades
        _CASCADES = [
            cv2.CascadeClassifier(os.path.join(base, name))
            for name in ("haarcascade_frontalface_default.xml",
                         "haarcascade_profileface.xml")
        ]
    return _CASCADES


# ---------------------------------------------------------------------------
# Saliency
# ---------------------------------------------------------------------------

def _normalize(m):
    m = m.astype(np.float32)
    lo, hi = float(m.min()), float(m.max())
    return (m - lo) / (hi - lo) if hi > lo else np.zeros_like(m)


def _spectral_residual(gray):
    """Hou & Zhang (2007) spectral-residual saliency."""
    h, w = gray.shape
    small = cv2.resize(gray, (64, 64), interpolation=cv2.INTER_AREA).astype(np.float32)
    # Mirror-pad so the FFT's wrap-around doesn't invent edges at the borders.
    small = np.pad(small, 16, mode="reflect")
    spectrum = np.fft.fft2(small)
    log_amp = np.log(np.abs(spectrum) + 1e-8)
    phase = np.angle(spectrum)
    residual = log_amp - cv2.blur(log_amp, (3, 3))
    sal = np.abs(np.fft.ifft2(np.exp(residual + 1j * phase))) ** 2
    sal = cv2.GaussianBlur(sal.astype(np.float32)[16:-16, 16:-16], (9, 9), 2.5)
    return _normalize(cv2.resize(sal, (w, h), interpolation=cv2.INTER_LINEAR))


def detect_faces(bgr):
    """Return face boxes (x, y, w, h) in the coordinates of `bgr`."""
    gray = cv2.equalizeHist(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY))
    min_side = max(20, min(gray.shape) // 20)
    boxes = []
    for i, cascade in enumerate(_cascades()):
        for flip in (False, True) if i == 1 else (False,):  # profile: both sides
            img = cv2.flip(gray, 1) if flip else gray
            found = cascade.detectMultiScale(img, scaleFactor=1.1, minNeighbors=6,
                                             minSize=(min_side, min_side))
            for (x, y, w, h) in found:
                if flip:
                    x = gray.shape[1] - x - w
                boxes.append((int(x), int(y), int(w), int(h)))
    return _merge_boxes(boxes)


def _merge_boxes(boxes):
    merged = []
    for b in sorted(boxes, key=lambda b: -b[2] * b[3]):
        if all(_iou(b, m) < 0.3 for m in merged):
            merged.append(b)
    return merged


def _iou(a, b):
    ax2, ay2, bx2, by2 = a[0] + a[2], a[1] + a[3], b[0] + b[2], b[1] + b[3]
    iw = max(0, min(ax2, bx2) - max(a[0], b[0]))
    ih = max(0, min(ay2, by2) - max(a[1], b[1]))
    inter = iw * ih
    union = a[2] * a[3] + b[2] * b[3] - inter
    return inter / union if union else 0.0


class Analysis:
    """Saliency map, face boxes and edge map for one image (analysis scale)."""

    def __init__(self, img: Image.Image):
        self.full_size = img.size
        scale = ANALYSIS_MAX_SIDE / max(img.size)
        self.scale = min(1.0, scale)
        small = img.convert("RGB")
        if self.scale < 1.0:
            small = small.resize((max(1, round(img.width * self.scale)),
                                  max(1, round(img.height * self.scale))), Image.LANCZOS)
        rgb = np.asarray(small)
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        sr = _spectral_residual(gray)

        gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        self.edges = _normalize(cv2.GaussianBlur(np.hypot(gx, gy), (0, 0), 2))

        # Local colour contrast in Lab: a colourful subject against its
        # surroundings, not a uniformly saturated sky or wall.
        lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
        surround = cv2.GaussianBlur(lab, (0, 0), max(w, h) / 8)
        sat = _normalize(cv2.GaussianBlur(np.linalg.norm(lab - surround, axis=2), (0, 0), 4))

        # Gentle centre prior: photographers tend to centre the subject.
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        center = np.exp(-(((xx - w / 2) / (0.6 * w)) ** 2 + ((yy - h / 2) / (0.6 * h)) ** 2))

        # No skin-tone term: sand, wood and beige walls trigger it constantly.
        # People are handled by the face detector below instead.
        sal = 0.45 * sr + 0.25 * self.edges + 0.20 * sat + 0.10 * center

        self.faces = detect_faces(bgr)
        for (x, y, fw, fh) in self.faces:
            # Faces dominate, and the area just below (body/shoulders) matters too.
            cx, cy = x + fw / 2, y + fh / 2
            blob = np.exp(-(((xx - cx) / (0.8 * fw)) ** 2 + ((yy - cy) / (0.8 * fh)) ** 2))
            body = np.exp(-(((xx - cx) / (1.2 * fw)) ** 2 + ((yy - cy - 1.5 * fh) / (1.5 * fh)) ** 2))
            sal += 3.0 * blob + 0.6 * body

        self.saliency = _normalize(sal) ** 1.5  # sharpen: favour the true peaks
        self.size = (w, h)
        self.sal_ii = cv2.integral(self.saliency.astype(np.float64))
        self.edge_ii = cv2.integral(self.edges.astype(np.float64))
        self.total = float(self.sal_ii[-1, -1]) or 1.0


def _rect_sum(ii, x, y, w, h):
    return ii[y + h, x + w] - ii[y, x + w] - ii[y + h, x] + ii[y, x]


# ---------------------------------------------------------------------------
# Smart crop
# ---------------------------------------------------------------------------

def find_best_crop(analysis: Analysis, aspect: float, zooms=(1.0, 0.9, 0.8)):
    """Best crop box (left, top, right, bottom) in full-resolution pixels."""
    w, h = analysis.size
    best, best_score = None, -math.inf

    for zoom in zooms:
        if w / h > aspect:
            ch = max(1, int(h * zoom))
            cw = min(w, max(1, int(round(ch * aspect))))
        else:
            cw = max(1, int(w * zoom))
            ch = min(h, max(1, int(round(cw / aspect))))

        step_x = max(1, (w - cw) // 40)
        step_y = max(1, (h - ch) // 40)
        band = max(2, min(cw, ch) // 25)  # thickness of the border strip

        for y in range(0, h - ch + 1, step_y):
            for x in range(0, w - cw + 1, step_x):
                score = _score_crop(analysis, x, y, cw, ch, band)
                score -= 0.35 * (1.0 - zoom)  # prefer keeping more of the photo
                if score > best_score:
                    best_score, best = score, (x, y, zoom)

    x, y, zoom = best
    s = 1.0 / analysis.scale
    fw, fh = analysis.full_size
    left = int(round(x * s))
    top = int(round(y * s))
    # Re-derive size at full res so the output aspect is exact.
    if fw / fh > aspect:
        crop_h = max(1, int(fh * zoom))
        crop_w = min(fw, max(1, int(round(crop_h * aspect))))
    else:
        crop_w = max(1, int(fw * zoom))
        crop_h = min(fh, max(1, int(round(crop_w / aspect))))
    left = min(max(0, left), fw - crop_w)
    top = min(max(0, top), fh - crop_h)
    return (left, top, left + crop_w, top + crop_h)


def _score_crop(a: Analysis, x, y, cw, ch, band):
    inside = _rect_sum(a.sal_ii, x, y, cw, ch)
    coverage = inside / a.total
    density = inside / (cw * ch)

    # Penalise cropping through salient stuff: saliency/edges on the border.
    border = 0.0
    for (bx, by, bw, bh) in ((x, y, cw, band), (x, y + ch - band, cw, band),
                             (x, y, band, ch), (x + cw - band, y, band, ch)):
        border += _rect_sum(a.sal_ii, bx, by, bw, bh) + 0.5 * _rect_sum(a.edge_ii, bx, by, bw, bh)
    border /= max(1.0, 4 * band * (cw + ch) / 2)

    # Faces: losing one is very bad, cutting one in half is worse.
    face_pen = 0.0
    for (fx, fy, fw, fh) in a.faces:
        ix = max(0, min(x + cw, fx + fw) - max(x, fx))
        iy = max(0, min(y + ch, fy + fh) - max(y, fy))
        frac = (ix * iy) / (fw * fh)
        if frac < 0.999:
            face_pen += 1.5 * (1 - frac) + (1.0 if frac > 0 else 0.0)
        # Leave headroom above the face.
        if fy - y < 0.25 * fh and frac > 0:
            face_pen += 0.3

    # Rule of thirds: where does the saliency centroid sit inside the crop?
    thirds = _thirds_score(a, x, y, cw, ch)

    return 1.0 * coverage + 0.3 * density - 0.5 * border - face_pen + 0.15 * thirds


def _thirds_score(a: Analysis, x, y, cw, ch):
    region = a.saliency[y:y + ch, x:x + cw]
    total = float(region.sum())
    if total <= 0:
        return 0.0
    ys, xs = np.indices(region.shape, dtype=np.float32)
    cx = float((region * xs).sum()) / total / cw
    cy = float((region * ys).sum()) / total / ch
    dx = min(abs(cx - 1 / 3), abs(cx - 2 / 3), abs(cx - 0.5))
    dy = min(abs(cy - 1 / 3), abs(cy - 2 / 3), abs(cy - 0.5))
    return 1.0 - 3.0 * math.hypot(dx, dy)


def smart_crop(img: Image.Image, aspect: float, analysis: Analysis = None,
               zooms=(1.0, 0.9, 0.8)) -> Image.Image:
    analysis = analysis or Analysis(img)
    return img.crop(find_best_crop(analysis, aspect, zooms))


def blur_fill(img: Image.Image, aspect: float, out_w: int, analysis: Analysis = None) -> Image.Image:
    """Google-Photos-style fit: photo over a blurred, dimmed copy of itself.

    The photo is trimmed slightly (smart crop to at most ~20% off) so it uses
    more of the frame without losing its subject.
    """
    out_h = int(round(out_w / aspect))
    analysis = analysis or Analysis(img)
    src_aspect = img.width / img.height
    # Allow a mild crop toward the target shape, never more than 20% of a side.
    trim_aspect = src_aspect * 1.25 if src_aspect < aspect else src_aspect / 1.25
    trim_aspect = min(trim_aspect, aspect) if src_aspect < aspect else max(trim_aspect, aspect)
    fg = img.crop(find_best_crop(analysis, trim_aspect, zooms=(1.0,)))

    bg = ImageOps.fit(img, (out_w, out_h), Image.LANCZOS, centering=_saliency_center(analysis))
    bg = bg.filter(ImageFilter.GaussianBlur(radius=out_w / 30))
    bg = Image.blend(bg, Image.new("RGB", bg.size, (0, 0, 0)), 0.35)

    fg = ImageOps.contain(fg, (out_w, out_h), Image.LANCZOS)
    bg.paste(fg, ((out_w - fg.width) // 2, (out_h - fg.height) // 2))
    return bg


def _saliency_center(a: Analysis):
    sal = a.saliency
    total = float(sal.sum()) or 1.0
    ys, xs = np.indices(sal.shape, dtype=np.float32)
    return (float((sal * xs).sum()) / total / sal.shape[1],
            float((sal * ys).sum()) / total / sal.shape[0])


def crop_retention(img: Image.Image, aspect: float) -> float:
    """Fraction of the image area a full-size crop to `aspect` keeps."""
    a = img.width / img.height
    return min(a, aspect) / max(a, aspect)


# ---------------------------------------------------------------------------
# Collage layout (slicing trees)
# ---------------------------------------------------------------------------
#
# A collage is a "slicing tree": every internal node puts its two children
# side by side (H) or one above the other (V). Laid out at their natural
# aspect ratios no photo is cropped at all; the only crop comes from
# stretching the whole tree to the canvas shape, and that stretch is shared
# evenly by every tile. So a layout's "fit" (share of each photo kept) is
#
#     fit = min(tree_aspect / canvas_aspect, canvas_aspect / tree_aspect)
#
# A dynamic program over subsets builds every tree for every subset of the
# pool at once: a subset's trees are all ways of splitting it in two and
# joining a tree of each half with H or V. Trees whose aspects are within
# ~2% of each other are merged, keeping the one whose smallest tile is
# largest, so the search stays exact up to that rounding.

ASPECT_BUCKET = 0.02  # log-aspect resolution when merging near-identical trees
MAX_LOG_ASPECT = 3.0  # trees wider/taller than e^3 (~20:1) can't help


class _Trees:
    """All (bucketed) slicing trees for one subset, as parallel arrays."""
    __slots__ = ("aspect", "minfrac", "sumsq", "left", "li", "ri", "vert")

    def __init__(self, aspect, minfrac, sumsq, left, li, ri, vert):
        self.aspect, self.minfrac, self.sumsq = aspect, minfrac, sumsq
        self.left, self.li, self.ri, self.vert = left, li, ri, vert


def _combine(A, B, vert):
    """Join every tree of A with every tree of B, horizontally or vertically."""
    a1 = A.aspect[:, None]
    a2 = B.aspect[None, :]
    if vert:  # stacked: equal widths, heights (and areas) ~ 1/aspect
        w1, w2 = 1 / a1, 1 / a2
        aspect = 1 / (w1 + w2)
    else:     # side by side: equal heights, widths (and areas) ~ aspect
        w1, w2 = a1, a2
        aspect = a1 + a2
    f1, f2 = w1 / (w1 + w2), w2 / (w1 + w2)
    minfrac = np.minimum(A.minfrac[:, None] * f1, B.minfrac[None, :] * f2)
    sumsq = A.sumsq[:, None] * f1 ** 2 + B.sumsq[None, :] * f2 ** 2
    li, ri = np.meshgrid(np.arange(len(A.aspect)), np.arange(len(B.aspect)), indexing="ij")
    return aspect.ravel(), minfrac.ravel(), sumsq.ravel(), li.ravel(), ri.ravel()


def build_trees(aspects, max_size=None):
    """Slicing trees for every subset (bitmask) of `aspects` up to max_size."""
    n = len(aspects)
    max_size = max_size or n
    table = {}
    for i, a in enumerate(aspects):
        table[1 << i] = _Trees(np.array([a]), np.ones(1), np.ones(1),
                               np.array([-1]), np.zeros(1, int), np.zeros(1, int), np.zeros(1, bool))

    masks = sorted((m for m in range(1, 1 << n) if 2 <= bin(m).count("1") <= max_size),
                   key=lambda m: bin(m).count("1"))
    for S in masks:
        low = S & -S
        parts = []
        sub = (S - 1) & S
        while sub:
            if sub & low:  # each unordered split once: left half holds S's lowest bit
                A, B = table[sub], table[S ^ sub]
                for vert in (False, True):
                    asp, mf, sq, li, ri = _combine(A, B, vert)
                    parts.append((asp, mf, sq, np.full(len(asp), sub), li, ri, np.full(len(asp), vert)))
            sub = (sub - 1) & S
        asp, mf, sq, left, li, ri, vert = (np.concatenate(c) for c in zip(*parts))

        logs = np.log(asp)
        keep = np.abs(logs) <= MAX_LOG_ASPECT
        bucket = np.round(logs / ASPECT_BUCKET).astype(np.int64)
        # Per bucket keep the tree whose smallest tile is largest (then the
        # most even tiles), so no photo ends up as a thumbnail.
        order = np.lexsort((sq, -mf, bucket))
        order = order[keep[order]]
        first = np.ones(len(order), bool)
        first[1:] = bucket[order][1:] != bucket[order][:-1]
        idx = order[first]
        table[S] = _Trees(asp[idx], mf[idx], sq[idx], left[idx], li[idx], ri[idx], vert[idx])
    return table


def best_tree(table, mask, canvas_aspect):
    """Pick the tree for `mask` with the best fit, discouraging lopsided tiles.

    Returns (index, fit) where fit is the share of every photo kept.
    """
    T = table[mask]
    k = bin(mask).count("1")
    fit = np.minimum(T.aspect / canvas_aspect, canvas_aspect / T.aspect)
    imbalance = k * T.sumsq - 1  # squared coefficient of variation of tile areas
    tiny = T.minfrac < 0.25 / k  # smallest tile under a quarter of the average
    score = fit - 0.03 * imbalance - 1.0 * tiny
    i = int(np.argmax(score))
    return i, float(fit[i])


def tree_cells(table, mask, idx, x, y, w, h, gap):
    """Lay a tree out into the rectangle (x, y, w, h). Yields (image, x, y, w, h)."""
    T = table[mask]
    left = int(T.left[idx])
    if left < 0:
        yield (mask.bit_length() - 1, x, y, w, h)
        return
    right = mask ^ left
    li, ri = int(T.li[idx]), int(T.ri[idx])
    a1, a2 = table[left].aspect[li], table[right].aspect[ri]
    if T.vert[idx]:
        h1 = (h - gap) * (1 / a1) / (1 / a1 + 1 / a2)
        yield from tree_cells(table, left, li, x, y, w, h1, gap)
        yield from tree_cells(table, right, ri, x, y + h1 + gap, w, h - h1 - gap, gap)
    else:
        w1 = (w - gap) * a1 / (a1 + a2)
        yield from tree_cells(table, left, li, x, y, w1, h, gap)
        yield from tree_cells(table, right, ri, x + w1 + gap, y, w - w1 - gap, h, gap)


def plan_collage(aspects, W, H, gap, table=None, mask=None):
    """Best layout for the given photos. Returns (cells, fit)."""
    table = table or build_trees(aspects)
    mask = mask if mask is not None else (1 << len(aspects)) - 1
    idx, fit = best_tree(table, mask, W / H)
    return list(tree_cells(table, mask, idx, 0.0, 0.0, W, H, gap)), fit


def render_collage(images, analyses, cells, size, out_path, background=(255, 255, 255)):
    W, H = size
    canvas = Image.new("RGB", (W, H), background)
    for idx, x, y, cw, ch in cells:
        x0, y0 = int(round(x)), int(round(y))
        x1, y1 = int(round(x + cw)), int(round(y + ch))
        # Collage tiles are already small: keep as much of each photo as fits.
        tile = smart_crop(images[idx], (x1 - x0) / (y1 - y0), analyses[idx], zooms=(1.0,))
        canvas.paste(tile.resize((x1 - x0, y1 - y0), Image.LANCZOS), (x0, y0))
    canvas.save(out_path, quality=92)
    return out_path


def _load(paths):
    images = [ImageOps.exif_transpose(Image.open(p)).convert("RGB") for p in paths]
    return images, [im.width / im.height for im in images]


def make_collage(paths, out_path, size=(3840, 2160), gap=12, background=(255, 255, 255)):
    images, aspects = _load(paths)
    cells, fit = plan_collage(aspects, size[0], size[1], gap)
    render_collage(images, [Analysis(im) for im in images], cells, size, out_path, background)
    return out_path, fit


def explore_combinations(paths, out_dir, size=(3840, 2160), gap=12, min_k=2, max_k=7,
                         render_top=10, render_best_per_size=True):
    """Lay out every combination of min_k..max_k distinct photos from `paths`.

    Every combination gets its best layout and a fit score (share of each
    photo kept). Results go to combinations.csv, ranked best first; the top
    collages, and the best one for each image count, are rendered.
    """
    W, H = size
    images, aspects = _load(paths)
    n = len(images)
    max_k = min(max_k, n)
    if min_k > max_k:
        raise SystemExit(f"need at least {min_k} images, got {n}")
    total = sum(math.comb(n, k) for k in range(min_k, max_k + 1))
    print(f"{n} photos -> {total} combinations of {min_k}-{max_k} images")

    table = build_trees(aspects, max_k)
    results = []
    for k in range(min_k, max_k + 1):
        for combo in itertools.combinations(range(n), k):
            mask = sum(1 << i for i in combo)
            idx, fit = best_tree(table, mask, W / H)
            results.append((fit, k, combo, mask, idx))
    results.sort(key=lambda r: (-r[0], -r[1]))

    os.makedirs(out_dir, exist_ok=True)
    names = [os.path.basename(p) for p in paths]
    with open(os.path.join(out_dir, "combinations.csv"), "w") as f:
        f.write("rank,num_images,fit_percent,images\n")
        for rank, (fit, k, combo, _, _) in enumerate(results, 1):
            f.write(f"{rank},{k},{100 * fit:.2f},{' '.join(names[i] for i in combo)}\n")

    to_render = {}
    for rank, r in enumerate(results[:render_top], 1):
        to_render[r[3]] = f"top{rank:02d}"
    if render_best_per_size:
        for k in range(min_k, max_k + 1):
            best = next(r for r in results if r[1] == k)
            to_render.setdefault(best[3], f"best_{k}_images")

    analyses = {}
    by_mask = {r[3]: r for r in results}
    for mask, label in to_render.items():
        fit, k, combo, _, idx = by_mask[mask]
        for i in combo:
            if i not in analyses:
                analyses[i] = Analysis(images[i])
        cells = list(tree_cells(table, mask, idx, 0.0, 0.0, W, H, gap))
        dest = os.path.join(out_dir, f"{label}_{k}img_{100 * fit:.1f}pct.jpg")
        render_collage(images, analyses, cells, size, dest)

    print(f"\n{'rank':>4}  {'imgs':>4}  {'fit':>7}  images")
    for rank, (fit, k, combo, _, _) in enumerate(results[:15], 1):
        print(f"{rank:>4}  {k:>4}  {100 * fit:6.2f}%  {', '.join(names[i] for i in combo)}")
    print("\nBest per image count:")
    for k in range(min_k, max_k + 1):
        fits = [r[0] for r in results if r[1] == k]
        print(f"  {k} images: best {100 * max(fits):6.2f}%  worst {100 * min(fits):6.2f}%  "
              f"({len(fits)} combinations)")
    print(f"\nFull ranking in {os.path.join(out_dir, 'combinations.csv')}")
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def crop_all(paths, out_dir, mode="crop", width=1920, auto_threshold=0.5):
    os.makedirs(out_dir, exist_ok=True)
    outputs = []
    for p in paths:
        img = ImageOps.exif_transpose(Image.open(p)).convert("RGB")
        analysis = Analysis(img)
        use_blur = mode == "blur" or (mode == "auto" and crop_retention(img, TARGET_ASPECT) < auto_threshold)
        if use_blur:
            out = blur_fill(img, TARGET_ASPECT, width, analysis)
        else:
            out = smart_crop(img, TARGET_ASPECT, analysis)
            if out.width > width:
                out = out.resize((width, int(round(width / TARGET_ASPECT))), Image.LANCZOS)
        name = os.path.splitext(os.path.basename(p))[0] + "_16x9.jpg"
        dest = os.path.join(out_dir, name)
        out.save(dest, quality=92)
        outputs.append(dest)
        print(f"{p}: {img.width}x{img.height} -> {out.width}x{out.height} "
              f"({'blur fill' if use_blur else 'smart crop'}, faces={len(analysis.faces)})")
    return outputs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("crop", help="smart-crop each image to 16:9")
    c.add_argument("images", nargs="+")
    c.add_argument("-o", "--out-dir", default="cropped")
    c.add_argument("--mode", choices=("crop", "blur", "auto"), default="crop",
                   help="crop: fill frame; blur: fit over blurred copy; auto: blur when a crop would keep <50%%")
    c.add_argument("--width", type=int, default=1920)

    k = sub.add_parser("collage", help="lay all images out in one 16:9 collage")
    k.add_argument("images", nargs="+")
    k.add_argument("-o", "--output", default="collage_16x9.jpg")
    k.add_argument("--size", default="3840x2160", help="WIDTHxHEIGHT (default 3840x2160)")
    k.add_argument("--gap", type=int, default=12, help="pixels between tiles")

    m = sub.add_parser("combos", help="try every combination of 2-7 images, rank by fit")
    m.add_argument("images", nargs="+")
    m.add_argument("-o", "--out-dir", default="combinations")
    m.add_argument("--size", default="3840x2160", help="WIDTHxHEIGHT (default 3840x2160)")
    m.add_argument("--gap", type=int, default=12, help="pixels between tiles")
    m.add_argument("--min", dest="min_k", type=int, default=2, help="fewest images per collage")
    m.add_argument("--max", dest="max_k", type=int, default=7, help="most images per collage")
    m.add_argument("--top", type=int, default=10, help="render this many best collages")

    args = ap.parse_args()
    if args.cmd == "crop":
        crop_all(args.images, args.out_dir, args.mode, args.width)
        return
    w, h = (int(v) for v in args.size.lower().split("x"))
    if args.cmd == "collage":
        _, fit = make_collage(args.images, args.output, (w, h), args.gap)
        print(f"Saved {args.output} (keeps {100 * fit:.1f}% of each photo)")
    else:
        explore_combinations(args.images, args.out_dir, (w, h), args.gap,
                             args.min_k, args.max_k, args.top)


if __name__ == "__main__":
    main()
