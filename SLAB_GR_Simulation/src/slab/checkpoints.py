"""Versioned checkpoints.  A checkpoint file is NEVER overwritten: a new
version number is allocated whenever a file for the same milestone exists."""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
from pathlib import Path
from typing import Optional

import numpy as np


def _json_default(o):
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, float) and (o != o or o in (float("inf"), float("-inf"))):
        return str(o)
    raise TypeError(f"not serializable: {type(o)}")


def dumps(obj) -> str:
    return json.dumps(obj, indent=2, default=_json_default, allow_nan=True)


def config_hash(config: dict) -> str:
    return hashlib.sha256(json.dumps(config, sort_keys=True, default=_json_default).encode()).hexdigest()[:16]


def write_checkpoint(ckpt_dir: Path, index: int, slug: str, payload: dict) -> Path:
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    version = 1
    while True:
        path = ckpt_dir / f"ckpt_{index:02d}_{slug}_v{version:03d}.json"
        if not path.exists():
            break
        version += 1
    payload = dict(payload)
    payload["checkpoint_version"] = version
    payload["written_utc"] = _dt.datetime.now(_dt.timezone.utc).isoformat()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(dumps(payload))
    os.replace(tmp, path)  # atomic; never overwrites an existing checkpoint
    return path


def latest_checkpoint(ckpt_dir: Path, config_hash_value: Optional[str] = None) -> Optional[Path]:
    if not ckpt_dir.exists():
        return None
    best = None
    for p in sorted(ckpt_dir.glob("ckpt_*_v*.json")):
        try:
            d = json.loads(p.read_text())
        except Exception:
            continue
        if config_hash_value is not None and d.get("config_hash") != config_hash_value:
            continue
        key = (d.get("milestone_index", -1), d.get("checkpoint_version", 0))
        if best is None or key > best[0]:
            best = (key, p)
    return best[1] if best else None


def load_checkpoint(path: Path) -> dict:
    return json.loads(path.read_text())
