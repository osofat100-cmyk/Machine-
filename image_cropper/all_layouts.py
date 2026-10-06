#!/usr/bin/env python3
"""
Enumerate EVERY possible 16:9 collage of 2-7 photos. Nothing is ranked or
filtered: every possibility is computed and written out.

A possibility is the combination of four choices:

  1. Which photos   every combination of 2-7 different photos from the pool
  2. Layout shape   every slicing layout (each split puts two groups side by
                    side or one above the other); 2, 6, 22, 90, 394 and 1806
                    distinct shapes for 2..7 photos
  3. Positions      every assignment of the chosen photos to the slots of
                    that shape (k! orderings)
  4. Priority       no priority, or any group of 1..k-1 photos made bigger.
                    A priority photo's area is multiplied by the boost
                    factor (default 2x; pass several with --boost 1.5 2 3).
                    Prioritising all k photos is the same as none, so that
                    case is the "no priority" row.

For each possibility the program records how much of each photo survives
cropping to its tile (area-weighted average and the worst tile), and what
share of the canvas the priority photos get.

The canvas is always exactly 16:9. Every possibility is checked, but one is
written only if every photo keeps at least --min-fit of itself (default
0.95). A layout far from 16:9 would have to cut into or squeeze some photo
badly, so it is dropped. --min-fit 0 writes everything.

Commands:
    python all_layouts.py count  photos/*.jpg            # how many possibilities, disk needed
    python all_layouts.py count  photos/*.jpg --min-fit 0.9 0.95   # how many pass each cutoff
    python all_layouts.py run    photos/*.jpg -o results # compute and write all of them
    python all_layouts.py describe results --combo 120 --shape 5 --perm 17 --priority 3 --boost 2
    python all_layouts.py render results --combo 120 --shape 5 --perm 17 --priority 3 --boost 2
    python all_layouts.py render results --from results/k7/combo_0120/shape_0005.csv.gz --limit 50

Output layout (results/):
    settings.json            canvas size, gap, boosts, image list
    images.csv               image_number, file, width, height
    combos.csv               combo_id, k, image numbers, file names
    shapes_k{K}.csv          shape_id, layout in slot notation, e.g. H(a,V(b,c))
    k{K}/combo_{id}/shape_{id}.csv.gz
        one row per possibility:
        combo_id, shape_id, perm_id, priority_mask, boost,
        fit_avg, fit_min, priority_share

    perm_id       index into itertools.permutations(range(k)); slot a gets the
                  combination's perm[0]-th photo, slot b perm[1]-th, ...
                  (`describe` decodes this for you)
    priority_mask bit j set = image number j+1 is a priority photo (0 = none)
"""

import argparse
import csv
import gzip
import itertools
import json
import math
import multiprocessing as mp
import os
import sys
import time

import numpy as np
from PIL import Image, ImageOps

BYTES_PER_ROW_CSV = 42   # measured average, uncompressed
BYTES_PER_ROW_GZ = 11    # measured average at gzip level 1
SLOTS = "abcdefghijklmnopqrstuvwxyz"


# ---------------------------------------------------------------------------
# Layout shapes
# ---------------------------------------------------------------------------
#
# A shape is a slicing tree in canonical form: an H node (children side by
# side) never has an H child and a V node (children stacked) never has a V
# child, so every geometric arrangement appears exactly once. Leaves are slot
# numbers 0..k-1, numbered left to right.

def _compositions(n):
    """Ordered ways to write n as a sum of >= 2 positive parts."""
    def rec(m):
        if m == 0:
            yield ()
            return
        for p in range(1, m + 1):
            for rest in rec(m - p):
                yield (p,) + rest
    return [c for c in rec(n) if len(c) >= 2]


def _gen(n, orient, start):
    if n == 1:
        yield start
        return
    other = "V" if orient == "H" else "H"
    for comp in _compositions(n):
        offsets = list(itertools.accumulate((0,) + comp[:-1]))
        options = [list(_gen(p, other, start + off)) for p, off in zip(comp, offsets)]
        for kids in itertools.product(*options):
            yield (orient, kids)


_SHAPES = {}


def shapes(k):
    """All canonical layout shapes with k slots (deterministic order)."""
    if k not in _SHAPES:
        _SHAPES[k] = [0] if k == 1 else list(_gen(k, "H", 0)) + list(_gen(k, "V", 0))
    return _SHAPES[k]


def notation(node, names=SLOTS):
    if isinstance(node, int):
        return names[node]
    orient, kids = node
    return f"{orient}({','.join(notation(c, names) for c in kids)})"


def _leaves(node):
    if isinstance(node, int):
        return [node]
    return [s for c in node[1] for s in _leaves(c)]


# ---------------------------------------------------------------------------
# Geometry (vectorised over many possibilities at once)
# ---------------------------------------------------------------------------

def _natural_aspect(node, X):
    if isinstance(node, int):
        return X[:, node]
    orient, kids = node
    a = [_natural_aspect(c, X) for c in kids]
    return sum(a) if orient == "H" else 1.0 / sum(1.0 / x for x in a)


def _natural_fracs(node, X, frac, out):
    """Area share of every slot when laid out with no cropping at all."""
    if isinstance(node, int):
        out[:, node] = frac
        return
    orient, kids = node
    a = [_natural_aspect(c, X) for c in kids]
    w = a if orient == "H" else [1.0 / x for x in a]  # side-by-side: area ~ aspect
    total = sum(w)
    for c, wc in zip(kids, w):
        _natural_fracs(c, X, frac * wc / total, out)


def _place(node, A, x, y, w, h, gap, rects):
    """Split rectangles so every slot gets exactly its target area share."""
    if isinstance(node, int):
        rects[0][:, node], rects[1][:, node] = x, y
        rects[2][:, node], rects[3][:, node] = w, h
        return
    orient, kids = node
    sums = [A[:, _leaves(c)].sum(1) for c in kids]
    total = sum(sums)
    m = len(kids)
    if orient == "H":
        avail = w - gap * (m - 1)
        cx = x
        for c, s in zip(kids, sums):
            cw = avail * s / total
            _place(c, A, cx, y, cw, h, gap, rects)
            cx = cx + cw + gap
    else:
        avail = h - gap * (m - 1)
        cy = y
        for c, s in zip(kids, sums):
            ch = avail * s / total
            _place(c, A, x, cy, w, ch, gap, rects)
            cy = cy + ch + gap


def evaluate(shape, X, boost, W, H, gap):
    """Geometry and scores for N possibilities sharing one shape.

    X:     (N, k) photo aspect ratio in each slot
    boost: (N, k) area multiplier per slot (1 = normal, >1 = priority)
    Returns fit_avg, fit_min, priority_share (each (N,)) and the tile rects.
    """
    N, k = X.shape
    frac = np.empty((N, k))
    _natural_fracs(shape, X, np.ones(N), frac)
    A = frac * boost
    A /= A.sum(1, keepdims=True)
    rects = [np.empty((N, k)) for _ in range(4)]
    _place(shape, A, np.zeros(N), np.zeros(N), np.full(N, float(W)), np.full(N, float(H)), gap, rects)
    rx, ry, rw, rh = rects
    r = (rw / rh) / X
    kept = np.minimum(r, 1.0 / r)  # share of the photo that survives the crop
    area = rw * rh
    fit_avg = (area * kept).sum(1) / area.sum(1)
    fit_min = kept.min(1)
    prio_share = (area * (boost > 1)).sum(1) / area.sum(1)
    return fit_avg, fit_min, prio_share, rects


# ---------------------------------------------------------------------------
# Counting
# ---------------------------------------------------------------------------

def priority_options(k, n_boosts):
    """No priority, plus every proper non-empty subset at every boost."""
    return 1 + (2 ** k - 2) * n_boosts


def count_table(n, min_k, max_k, n_boosts):
    rows = []
    for k in range(min_k, min(max_k, n) + 1):
        combos = math.comb(n, k)
        shp = len(shapes(k))
        perms = math.factorial(k)
        prio = priority_options(k, n_boosts)
        rows.append((k, combos, shp, perms, prio, combos * shp * perms * prio))
    return rows


def print_counts(n, min_k, max_k, boosts):
    rows = count_table(n, min_k, max_k, len(boosts))
    print(f"{n} photos, {min_k}-{max_k} per collage, boost factors {boosts}\n")
    print(f"{'k':>2} {'combos':>8} {'shapes':>7} {'positions':>10} {'priorities':>11} {'possibilities':>16}")
    for k, c, s, p, q, t in rows:
        print(f"{k:>2} {c:>8,} {s:>7,} {p:>10,} {q:>11,} {t:>16,}")
    total = sum(r[-1] for r in rows)
    no_prio = sum(c * s * p for _, c, s, p, _, _ in rows)
    print(f"{'':>2} {'':>8} {'':>7} {'':>10} {'total':>11} {total:>16,}")
    print(f"\nWithout priorities: {no_prio:,} layouts")
    print(f"Results on disk: ~{_human(total * BYTES_PER_ROW_GZ)} gzipped "
          f"(~{_human(total * BYTES_PER_ROW_CSV)} as plain CSV)")
    return total


def _human(b):
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} EB"


# ---------------------------------------------------------------------------
# Run: compute every possibility
# ---------------------------------------------------------------------------

def _load_aspects(paths):
    info = []
    for p in paths:
        with Image.open(p) as im:
            im = ImageOps.exif_transpose(im)
            info.append((os.path.abspath(p), im.width, im.height))
    return info


def _all_combos(n, min_k, max_k):
    out = []
    for k in range(min_k, min(max_k, n) + 1):
        out.extend(itertools.combinations(range(n), k))
    return out


_CTX = {}


def _init_worker(ctx):
    _CTX.update(ctx)


def _batches(combo, shape_id):
    """Evaluate every position x priority option of one (combination, shape).

    Yields (perm_ids, pool_masks, boosts, fit_avg, fit_min, share) per batch.
    """
    c = _CTX
    k = len(combo)
    shape = shapes(k)[shape_id]
    aspects = np.array([c["aspects"][i] for i in combo])
    perms = np.array(list(itertools.permutations(range(k))), dtype=np.int64)

    # Priority options: (combination-position mask, boost); mask 0 = none.
    full = (1 << k) - 1
    opts = [(0, 1.0)] + [(m, b) for m in range(1, full) for b in c["boosts"]]
    masks = np.array([m for m, _ in opts], dtype=np.int64)
    boosts = np.array([b for _, b in opts])
    pool_masks = np.array([sum(1 << combo[j] for j in range(k) if m >> j & 1) for m in masks],
                          dtype=np.int64)
    Q = len(opts)
    chunk = max(1, c["chunk_rows"] // Q)
    for p0 in range(0, len(perms), chunk):
        P = perms[p0:p0 + chunk]                                   # (p, k)
        n_p = len(P)
        X = np.repeat(aspects[P], Q, axis=0)                       # (p*Q, k)
        prio = (masks[None, :, None] >> P[:, None, :]) & 1         # (p, Q, k)
        B = np.where(prio == 1, boosts[None, :, None], 1.0).reshape(n_p * Q, k)
        fit_avg, fit_min, share, _ = evaluate(shape, X, B, c["W"], c["H"], c["gap"])
        yield (np.repeat(np.arange(p0, p0 + n_p), Q), np.tile(pool_masks, n_p),
               np.tile(boosts, n_p), fit_avg, fit_min, share)


def _task(args):
    """Compute one (combination, shape); write the possibilities that pass min_fit."""
    combo_id, combo, shape_id = args
    c = _CTX
    k = len(combo)
    dest = os.path.join(c["out"], f"k{k}", f"combo_{combo_id:04d}", f"shape_{shape_id:04d}.csv.gz")
    if os.path.exists(dest):
        return combo_id, shape_id, None  # already done (resume)

    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".tmp"
    kept = 0
    with gzip.open(tmp, "wt", compresslevel=1) as f:
        for perm_ids, masks, boosts, fit_avg, fit_min, share in _batches(combo, shape_id):
            # Every photo must keep at least min_fit of itself: one badly
            # mismatched tile rules the whole collage out.
            ok = fit_min >= c["min_fit"]
            if not ok.any():
                continue
            out = np.column_stack([
                np.full(ok.sum(), combo_id), np.full(ok.sum(), shape_id),
                perm_ids[ok], masks[ok], boosts[ok], fit_avg[ok], fit_min[ok], share[ok],
            ])
            np.savetxt(f, out, fmt="%d,%d,%d,%d,%g,%.4f,%.4f,%.4f")
            kept += len(out)
    os.replace(tmp, dest)
    return combo_id, shape_id, kept


def _count_task(args):
    """How many possibilities of one (combination, shape) pass each threshold."""
    combo_id, combo, shape_id = args
    thresholds = np.array(_CTX["thresholds"])
    counts = np.zeros(len(thresholds), dtype=np.int64)
    for *_, fit_min, _ in _batches(combo, shape_id):
        counts += (fit_min[None, :] >= thresholds[:, None]).sum(1)
    return len(combo), counts


def _make_tasks(combos):
    # Biggest tasks first so the pool stays busy to the end.
    tasks = [(cid, combo, sid) for cid, combo in enumerate(combos)
             for sid in range(len(shapes(len(combo))))]
    tasks.sort(key=lambda t: -len(t[1]))
    return tasks


def _ctx(info, boosts, W, H, gap, chunk_rows, **extra):
    return dict(aspects=[iw / ih for _, iw, ih in info], boosts=list(boosts),
                W=W, H=H, gap=gap, chunk_rows=chunk_rows, **extra)


def count_surviving(paths, size, gap, min_k, max_k, boosts, thresholds, workers, chunk_rows):
    """Exact number of possibilities whose every photo keeps >= each threshold."""
    n = len(paths)
    print_counts(n, min_k, max_k, boosts)
    info = _load_aspects(paths)
    combos = _all_combos(n, min_k, max_k)
    tasks = _make_tasks(combos)
    ctx = _ctx(info, boosts, *size, gap, chunk_rows, thresholds=list(thresholds))
    ks = list(range(min_k, min(max_k, n) + 1))
    per_k = {k: np.zeros(len(thresholds), dtype=np.int64) for k in ks}
    print(f"\nChecking every possibility against min-fit {', '.join(f'{t:.0%}' for t in thresholds)} "
          f"on {workers} processes...")
    start, last = time.time(), 0.0
    with mp.Pool(workers, initializer=_init_worker, initargs=(ctx,)) as pool:
        for i, (k, counts) in enumerate(pool.imap_unordered(_count_task, tasks), 1):
            per_k[k] += counts
            now = time.time()
            if now - last > 2 or i == len(tasks):
                last = now
                print(f"\r  {i:,}/{len(tasks):,} units  {_duration(now - start)}   ", end="", flush=True)
    print("\n\nPossibilities kept (every photo keeps at least min-fit of itself):\n")
    print(f"{'k':>2}" + "".join(f"{f'>= {t:.0%}':>16}" for t in thresholds))
    for k in ks:
        print(f"{k:>2}" + "".join(f"{v:>16,}" for v in per_k[k]))
    totals = sum(per_k.values())
    print(f"{'':>2}" + "".join(f"{v:>16,}" for v in totals))
    print("\ndisk  " + "".join(f"{_human(v * BYTES_PER_ROW_GZ):>16}" for v in totals))


def run(paths, out, size, gap, min_k, max_k, boosts, min_fit, workers, chunk_rows):
    n = len(paths)
    if n < min_k:
        sys.exit(f"need at least {min_k} photos, got {n}")
    total = print_counts(n, min_k, max_k, boosts)
    os.makedirs(out, exist_ok=True)

    info = _load_aspects(paths)
    W, H = size
    settings = {"width": W, "height": H, "gap": gap, "min_k": min_k, "max_k": max_k,
                "boosts": list(boosts), "min_fit": min_fit, "images": [i[0] for i in info]}
    settings_path = os.path.join(out, "settings.json")
    if os.path.exists(settings_path):
        with open(settings_path) as f:
            if json.load(f) != settings:
                sys.exit(f"{out}/ holds results made with different settings; "
                         "use a new --out folder (or delete the old one)")
    with open(settings_path, "w") as f:
        json.dump(settings, f, indent=2)
    with open(os.path.join(out, "images.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["image_number", "file", "width", "height"])
        for j, (p, iw, ih) in enumerate(info, 1):
            w.writerow([j, p, iw, ih])

    combos = _all_combos(n, min_k, max_k)
    with open(os.path.join(out, "combos.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["combo_id", "k", "image_numbers", "files"])
        for cid, combo in enumerate(combos):
            w.writerow([cid, len(combo), " ".join(str(i + 1) for i in combo),
                        " | ".join(os.path.basename(info[i][0]) for i in combo)])
    for k in range(min_k, min(max_k, n) + 1):
        with open(os.path.join(out, f"shapes_k{k}.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["shape_id", "layout"])
            for sid, s in enumerate(shapes(k)):
                w.writerow([sid, notation(s)])

    per_task = {k: math.factorial(k) * priority_options(k, len(boosts))
                for k in range(min_k, min(max_k, n) + 1)}
    tasks = _make_tasks(combos)
    # Resume: skip units whose result file already exists.
    todo = [t for t in tasks if not os.path.exists(os.path.join(
        out, f"k{len(t[1])}", f"combo_{t[0]:04d}", f"shape_{t[2]:04d}.csv.gz"))]
    if len(todo) < len(tasks):
        print(f"\nResuming: {len(tasks) - len(todo):,} of {len(tasks):,} units already done")
        total = sum(per_task[len(t[1])] for t in todo)
    ctx = _ctx(info, boosts, W, H, gap, chunk_rows, out=out, min_fit=min_fit)

    print(f"\nKeeping only collages where every photo keeps >= {min_fit:.0%} of itself")
    print(f"{len(todo):,} work units on {workers} processes -> {out}/")
    start, last = time.time(), 0.0
    checked = kept = 0
    with mp.Pool(workers, initializer=_init_worker, initargs=(ctx,)) as pool:
        for i, (cid, sid, rows) in enumerate(pool.imap_unordered(_task, todo), 1):
            checked += per_task[len(combos[cid])]
            kept += rows or 0
            now = time.time()
            if now - last > 2 or i == len(todo):
                last = now
                rate = checked / max(now - start, 1e-9)
                eta = (total - checked) / rate if rate else 0
                print(f"\r  {i:,}/{len(todo):,} units  checked {checked:,}/{total:,}  kept {kept:,}  "
                      f"{rate:,.0f}/s  ETA {_duration(eta)}   ", end="", flush=True)
    print(f"\nDone in {_duration(time.time() - start)}. Kept {kept:,} possibilities in {out}/")


def _duration(s):
    s = int(s)
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return (f"{d}d " if d else "") + f"{h:02d}:{m:02d}:{s:02d}"


# ---------------------------------------------------------------------------
# Describe / render individual possibilities
# ---------------------------------------------------------------------------

def _load_results(out):
    with open(os.path.join(out, "settings.json")) as f:
        settings = json.load(f)
    combos = _all_combos(len(settings["images"]), settings["min_k"], settings["max_k"])
    return settings, combos


def possibility(settings, combos, combo_id, shape_id, perm_id, priority_mask, boost):
    """Resolve ids to (shape, slot -> image index, boost per slot)."""
    combo = combos[combo_id]
    k = len(combo)
    shape = shapes(k)[shape_id]
    perm = next(itertools.islice(itertools.permutations(range(k)), perm_id, None))
    slot_images = [combo[j] for j in perm]
    slot_boost = [boost if priority_mask >> i & 1 else 1.0 for i in slot_images]
    return shape, slot_images, slot_boost


def describe(out, combo_id, shape_id, perm_id, priority_mask, boost):
    settings, combos = _load_results(out)
    shape, slot_images, slot_boost = possibility(settings, combos, combo_id, shape_id, perm_id,
                                                 priority_mask, boost)
    names = [os.path.basename(p) for p in settings["images"]]
    aspects = []
    for i in slot_images:
        with Image.open(settings["images"][i]) as im:
            im = ImageOps.exif_transpose(im)
            aspects.append(im.width / im.height)
    fit_avg, fit_min, share, rects = evaluate(shape, np.array([aspects]), np.array([slot_boost]),
                                              settings["width"], settings["height"], settings["gap"])
    print(f"layout   {notation(shape)}")
    print(f"         {notation(shape, [names[i] for i in slot_images])}")
    prio = [names[i] for i in slot_images if priority_mask >> i & 1]
    print(f"priority {', '.join(prio) if prio else 'none'}" + (f" (x{boost:g} area)" if prio else ""))
    print(f"fit      average {100 * fit_avg[0]:.2f}%  worst tile {100 * fit_min[0]:.2f}%"
          + (f"  priority share {100 * share[0]:.1f}% of canvas" if prio else ""))
    for s, i in enumerate(slot_images):
        x, y, w, h = (r[0, s] for r in rects)
        print(f"  slot {SLOTS[s]}: {names[i]:<30} x={x:7.1f} y={y:7.1f} {w:7.1f}x{h:<7.1f}")


_RENDER = {}


def _render_init(out, scale):
    settings, combos = _load_results(out)
    _RENDER.update(settings=settings, combos=combos, scale=scale, images={}, analyses={}, crops={})


def _render_one(row):
    from smart_collage import Analysis, find_best_crop
    r = _RENDER
    st = r["settings"]
    combo_id, shape_id, perm_id, mask, boost = row
    shape, slot_images, slot_boost = possibility(st, r["combos"], combo_id, shape_id, perm_id, mask, boost)
    for i in slot_images:
        if i not in r["images"]:
            r["images"][i] = ImageOps.exif_transpose(Image.open(st["images"][i])).convert("RGB")
            r["analyses"][i] = Analysis(r["images"][i])
    aspects = np.array([[r["images"][i].width / r["images"][i].height for i in slot_images]])
    s = r["scale"]
    W, H, gap = int(st["width"] * s), int(st["height"] * s), st["gap"] * s
    *_, rects = evaluate(shape, aspects, np.array([slot_boost]), W, H, gap)
    canvas = Image.new("RGB", (W, H), (255, 255, 255))
    for slot, i in enumerate(slot_images):
        x, y, w, h = (float(q[0, slot]) for q in rects)
        x0, y0, x1, y1 = round(x), round(y), round(x + w), round(y + h)
        if x1 <= x0 or y1 <= y0:
            continue
        aspect = (x1 - x0) / (y1 - y0)
        key = (i, round(aspect, 3))
        if key not in r["crops"]:  # same photo + same tile shape -> same crop
            r["crops"][key] = find_best_crop(r["analyses"][i], aspect, zooms=(1.0,))
        tile = r["images"][i].crop(r["crops"][key]).resize((x1 - x0, y1 - y0), Image.LANCZOS)
        canvas.paste(tile, (x0, y0))
    name = f"c{combo_id:04d}_s{shape_id:04d}_p{perm_id:04d}_m{mask}_b{boost:g}.jpg"
    dest = os.path.join(r["dest"], name)
    canvas.save(dest, quality=90)
    return dest


def _read_rows(files, limit):
    count = 0
    for path in files:
        opener = gzip.open if path.endswith(".gz") else open
        with opener(path, "rt") as f:
            for line in f:
                parts = line.strip().split(",")
                if not parts[0].isdigit():
                    continue  # header
                yield (int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3]), float(parts[4]))
                count += 1
                if limit and count >= limit:
                    return


def render(out, dest, rows, workers, scale):
    os.makedirs(dest, exist_ok=True)
    if workers <= 1:
        _render_worker_init(out, scale, dest)
        for row in rows:
            print(_render_one(row))
        return
    with mp.Pool(workers, initializer=_render_worker_init, initargs=(out, scale, dest)) as pool:
        for i, _ in enumerate(pool.imap_unordered(_render_one, rows, chunksize=8), 1):
            if i % 50 == 0:
                print(f"\r  rendered {i:,}", end="", flush=True)
    print(f"\nImages in {dest}/")


def _render_worker_init(out, scale, dest):
    _render_init(out, scale)
    _RENDER["dest"] = dest


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _size(s):
    w, h = (int(v) for v in s.lower().split("x"))
    return w, h


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--min", dest="min_k", type=int, default=2, help="fewest photos per collage (2)")
        p.add_argument("--max", dest="max_k", type=int, default=7, help="most photos per collage (7)")
        p.add_argument("--boost", type=float, nargs="+", default=[2.0],
                       help="area multiplier(s) for priority photos (default 2)")

    c = sub.add_parser("count", help="how many possibilities there are")
    c.add_argument("images", nargs="+")
    c.add_argument("--min-fit", type=float, nargs="+",
                   help="also compute exactly how many pass these thresholds, e.g. 0.9 0.95 0.98")
    c.add_argument("--size", type=_size, default=(3840, 2160))
    c.add_argument("--gap", type=float, default=12)
    c.add_argument("--workers", type=int, default=os.cpu_count())
    common(c)

    r = sub.add_parser("run", help="compute and write every possibility")
    r.add_argument("images", nargs="+")
    r.add_argument("-o", "--out", default="results")
    r.add_argument("--size", type=_size, default=(3840, 2160), help="canvas WIDTHxHEIGHT (3840x2160)")
    r.add_argument("--gap", type=float, default=12, help="pixels between tiles (12)")
    r.add_argument("--workers", type=int, default=os.cpu_count(), help="processes (all cores)")
    r.add_argument("--min-fit", type=float, default=0.95,
                   help="drop a collage if any photo would keep less than this share of itself "
                        "(0.95 = at most 5%% cropped or mismatched; 0 keeps everything)")
    r.add_argument("--chunk-rows", type=int, default=400_000,
                   help="possibilities computed per batch; lower it if memory is tight")
    common(r)

    d = sub.add_parser("describe", help="explain one possibility in words")
    d.add_argument("out")
    for name in ("combo", "shape", "perm"):
        d.add_argument(f"--{name}", type=int, required=True)
    d.add_argument("--priority", type=int, default=0, help="priority_mask column")
    d.add_argument("--boost", type=float, default=1.0)

    v = sub.add_parser("render", help="draw possibilities as images")
    v.add_argument("out")
    v.add_argument("--from", dest="files", nargs="+", help="result .csv.gz files: render their rows")
    v.add_argument("--limit", type=int, default=0, help="stop after this many rows (0 = all)")
    for name in ("combo", "shape", "perm"):
        v.add_argument(f"--{name}", type=int)
    v.add_argument("--priority", type=int, default=0)
    v.add_argument("--boost", type=float, default=1.0)
    v.add_argument("-d", "--dest", default=None, help="folder for images (default OUT/renders)")
    v.add_argument("--scale", type=float, default=1.0, help="render size relative to the run canvas")
    v.add_argument("--workers", type=int, default=os.cpu_count())

    a = ap.parse_args()
    if a.cmd == "count":
        if a.min_fit:
            count_surviving(a.images, a.size, a.gap, a.min_k, a.max_k, a.boost, a.min_fit,
                            a.workers, 400_000)
        else:
            print_counts(len(a.images), a.min_k, a.max_k, a.boost)
    elif a.cmd == "run":
        run(a.images, a.out, a.size, a.gap, a.min_k, a.max_k, a.boost, a.min_fit,
            a.workers, a.chunk_rows)
    elif a.cmd == "describe":
        describe(a.out, a.combo, a.shape, a.perm, a.priority, a.boost)
    else:
        dest = a.dest or os.path.join(a.out, "renders")
        if a.files:
            rows = _read_rows(a.files, a.limit)
        elif None not in (a.combo, a.shape, a.perm):
            rows = [(a.combo, a.shape, a.perm, a.priority, a.boost)]
        else:
            sys.exit("render needs --from FILES or --combo/--shape/--perm")
        render(a.out, dest, rows, a.workers, a.scale)


if __name__ == "__main__":
    main()
