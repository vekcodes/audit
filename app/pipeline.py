"""End-to-end orchestration: website URL -> public Google Doc."""
from __future__ import annotations

import re
import time
from pathlib import Path

from . import config, gdocs, proof as proof_mod, visuals
from .auditor import run_audit
from .fetcher import fetch_site


def _slug(url: str) -> str:
    s = re.sub(r"^https?://", "", url).strip("/")
    s = re.sub(r"[^a-zA-Z0-9._-]+", "-", s)
    return s[:60] or "site"


def run_pipeline(website: str, *, include_proof: bool | None = None) -> dict:
    include_proof = config.INCLUDE_PROOF if include_proof is None else include_proof
    run_dir = config.RUNS_DIR / f"{_slug(website)}-{int(time.time())}"
    run_dir.mkdir(parents=True, exist_ok=True)

    # 1. Fetch + analyze the site signals.
    site = fetch_site(website)

    # 2. Run the audit via Qwen (the quality core).
    result = run_audit(site)
    (run_dir / "audit.json").write_text(
        result.model_dump_json(indent=2), encoding="utf-8"
    )

    # 3. Render the four branded visuals.
    visuals.generate(result, run_dir)

    # 4. Fetch the live proof case study (optional, non-fatal).
    proof = proof_mod.fetch_proof(run_dir) if include_proof else None

    # 5. Build the native Google Doc and share it public.
    doc = gdocs.build_doc(result, proof, run_dir)

    return {
        "website": website,
        "client": result.client,
        "overall_score": result.overall,
        "status": result.status,
        "scores": result.scores,
        "proof_source": (proof or {}).get("source") if proof else None,
        "run_dir": str(run_dir),
        **doc,
    }
