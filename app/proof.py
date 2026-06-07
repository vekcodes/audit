"""Fetch the live RankedTag proof assets (sendr.ai case study).

Wraps the skill's scripts/fetch_proof.py, which downloads the GSC + AI-Overview
screenshots and writes proof.json (with a 'source' field: live|fallback).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from . import config


def fetch_proof(out_dir: Path) -> Optional[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    script = config.SKILL_SCRIPTS / "fetch_proof.py"
    # Force UTF-8 so the skill's plain open(...,"w") doesn't crash on Windows
    # cp1252 when writing the "→" arrow in proof.json.
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    try:
        subprocess.run(
            [sys.executable, str(script), "--out", str(out_dir)],
            check=True,
            capture_output=True,
            text=True,
            timeout=90,
            env=env,
        )
    except Exception as e:  # noqa: BLE001 - proof is optional, never fatal
        print(f"[proof] fetch failed, continuing without proof: {e}")
        return None
    pj = out_dir / "proof.json"
    if pj.exists():
        return json.loads(pj.read_text(encoding="utf-8"))
    return None
