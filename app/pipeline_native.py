"""Single-site pipeline that builds a Google Doc WITHOUT a browser (Vercel-safe).

mode="lite" (default): fast ~1-3s audit via qwen-flash.
mode="full": deep ~110s audit via qwen3.7-max (needs a host with a long timeout).
Both render the doc natively (no Playwright, no PNG hosting).
"""
from __future__ import annotations

from . import config, gdocs_native
from .fetcher import fetch_site
from .lite import run_lite


def run_native(website: str, mode: str = "lite") -> dict:
    site = fetch_site(website)
    if mode == "full":
        from .auditor import run_audit  # lazy: avoids importing on cold start
        result = run_audit(site)
        doc = gdocs_native.build_native_full(result, proof=None)
        return {
            "website": website, "mode": "full", "client": result.client,
            "overall_score": result.overall, "status": result.status,
            "scores": result.scores, **doc,
        }
    lite = run_lite(site)
    doc = gdocs_native.build_native_lite(lite, proof=None)
    return {
        "website": website, "mode": "lite", "client": lite.client,
        "overall_score": lite.overall, "status": lite.status,
        "scores": lite.scores, **doc,
    }
