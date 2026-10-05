#!/usr/bin/env python3
"""
Smart 16:9 cropping and collage layout, in the spirit of Google Photos.

Two things are done here:

1. Smart crop: every image gets a saliency map (spectral-residual saliency,
   edge energy, local colour contrast, and detected faces). A window of the
   target aspect ratio is slid over the image and scored on how much of the
   salient content it keeps, whether it slices through a face or a busy edge,
   and how well the subject sits on the rule-of-thirds grid. Summed-area
   tables make each window O(1) to score.

2. Collage: images are packed into a 16:9 canvas with a justified-rows layout.
   Every ordering/row split is scored on how much each photo has to be
   cropped to fill its cell and how uneven the tile sizes are; the best one
   wins and each cell is then smart-cropped to its exact shape.

Portraits cropped all the way down to 16:9 lose most of the frame, so the
crop command also offers Google-Photos-style "blur" fill (the photo sits on a
blurred, dimmed copy of itself) and an "auto" mode that picks per image.

Usage:
    python smart_collage.py crop    img1.jpg img2.jpg ... -o out_dir [--mode crop|blur|auto]
    python smart_collage.py collage img1.jpg img2.jpg ... -o collage.jpg [--size 3840x2160]
"""

import argparse
import itertools
import math
import os
import random

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
# Collage layout (justified rows)
# ---------------------------------------------------------------------------

def _row_partitions(n, max_rows):
    """All ways to split a sequence of n items into consecutive rows."""
    for k in range(1, min(n, max_rows)):
        for cuts in itertools.combinations(range(1, n), k):
            bounds = (0,) + cuts + (n,)
            yield [range(bounds[i], bounds[i + 1]) for i in range(len(bounds) - 1)]
    yield [range(0, n)]


def _evaluate_layout(aspects, rows, W, H, gap):
    """Lay rows out to exactly fill W x H. Returns (cost, cells)."""
    natural = []
    for row in rows:
        s = sum(aspects[i] for i in row)
        natural.append((W - gap * (len(row) - 1)) / s)
    avail_h = H - gap * (len(rows) - 1)
    stretch = avail_h / sum(natural)  # >1 means cells get taller than the photos

    cells, cost, areas = [], 0.0, []
    y = 0.0
    for row, nh in zip(rows, natural):
        rh = nh * stretch
        x = 0.0
        for j, i in enumerate(row):
            cw = aspects[i] * nh
            cells.append((i, x, y, cw, rh))
            areas.append(cw * rh)
            # Crop cost: how far the cell aspect is from the photo's aspect.
            cost += abs(math.log((cw / rh) / aspects[i])) * (cw * rh) / (W * H)
            x += cw + gap
        y += rh + gap

    # Uneven tiles look messy; huge ones swamp the rest.
    areas = np.array(areas)
    balance = float(np.std(areas) / np.mean(areas))
    tiny = sum(1 for (_, _, _, cw, rh) in cells if min(cw, rh) < 0.12 * min(W, H))
    return 2.0 * cost + 0.25 * balance + 0.5 * tiny, cells


def plan_collage(aspects, W, H, gap, tries=400, seed=0):
    """Search orderings and row splits for the least-crop, best-balanced layout."""
    n = len(aspects)
    rng = random.Random(seed)
    orders = {tuple(range(n))}
    # Alternate wide/tall so rows mix shapes, plus random shuffles.
    by_aspect = sorted(range(n), key=lambda i: aspects[i])
    interleaved = [x for pair in itertools.zip_longest(by_aspect[::-1], by_aspect)
                   for x in pair if x is not None]
    orders.add(tuple(dict.fromkeys(interleaved)))
    if n <= 6:
        orders.update(itertools.permutations(range(n)))
    else:
        for _ in range(tries):
            p = list(range(n))
            rng.shuffle(p)
            orders.add(tuple(p))

    max_rows = max(2, math.ceil(math.sqrt(n)) + 1)
    best = (math.inf, None)
    for order in orders:
        ordered = [aspects[i] for i in order]
        for rows in _row_partitions(n, max_rows):
            cost, cells = _evaluate_layout(ordered, rows, W, H, gap)
            if cost < best[0]:
                best = (cost, [(order[i], x, y, w, h) for (i, x, y, w, h) in cells])
    return best[1]


def make_collage(paths, out_path, size=(3840, 2160), gap=12, background=(255, 255, 255)):
    W, H = size
    images = [ImageOps.exif_transpose(Image.open(p)).convert("RGB") for p in paths]
    analyses = [Analysis(im) for im in images]
    aspects = [im.width / im.height for im in images]

    canvas = Image.new("RGB", (W, H), background)
    for idx, x, y, cw, ch in plan_collage(aspects, W, H, gap):
        x0, y0 = int(round(x)), int(round(y))
        x1, y1 = int(round(x + cw)), int(round(y + ch))
        # Collage tiles are already small: keep as much of each photo as fits.
        tile = smart_crop(images[idx], (x1 - x0) / (y1 - y0), analyses[idx], zooms=(1.0,))
        canvas.paste(tile.resize((x1 - x0, y1 - y0), Image.LANCZOS), (x0, y0))
    canvas.save(out_path, quality=92)
    return out_path


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

    args = ap.parse_args()
    if args.cmd == "crop":
        crop_all(args.images, args.out_dir, args.mode, args.width)
    else:
        w, h = (int(v) for v in args.size.lower().split("x"))
        make_collage(args.images, args.output, (w, h), args.gap)
        print(f"Saved {args.output}")


if __name__ == "__main__":
    main()
