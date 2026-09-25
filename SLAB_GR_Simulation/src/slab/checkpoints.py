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


def sanitize(o):
    """Make an object strictly JSON-compliant: numpy -> python, inf/nan -> 'inf'/'-inf'/None."""
    import math
    if isinstance(o, dict):
        return {str(k): sanitize(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [sanitize(v) for v in o]
    if isinstance(o, np.ndarray):
        return [sanitize(v) for v in o.tolist()]
    if isinstance(o, (bool, np.bool_)):
        return bool(o)
    if isinstance(o, (int, np.integer)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        x = float(o)
        if math.isnan(x):
            return None
        if math.isinf(x):
            return "inf" if x > 0 else "-inf"
        return x
    return o


def _json_default(o):
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    raise TypeError(f"not serializable: {type(o)}")


def dumps(obj) -> str:
    """Strict JSON (RFC 8259: no Infinity/NaN tokens); non-finite floats become 'inf'/'-inf'/null."""
    return json.dumps(sanitize(obj), indent=2, default=_json_default, allow_nan=False)


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
    # exclusive create: fails instead of overwriting if the file appeared meanwhile
    with open(path, "x") as fh:
        fh.write(dumps(payload))
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
