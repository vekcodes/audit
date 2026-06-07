"""Render the four signature RankedTag visuals as high-res PNGs.

We reuse the skill's exact SVG templates (scripts/generate_visuals.py) for
pixel-faithful brand design, but rasterize with Playwright/Chromium instead of
Cairo (which needs native DLLs unavailable on Windows).
"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from typing import List, Tuple

from . import config
from .models import CATEGORY_WEIGHTS, AuditResult

_SVG_WH = re.compile(r'<svg[^>]*\bwidth="(\d+)"[^>]*\bheight="(\d+)"', re.I)


def _load_skill_module():
    """Import skill/scripts/generate_visuals.py as a module."""
    path = config.SKILL_SCRIPTS / "generate_visuals.py"
    spec = importlib.util.spec_from_file_location("rt_generate_visuals", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_renderer(scale: float = 2.0):
    """Return a render(path, svg, scale) compatible with the skill, via Playwright."""
    from playwright.sync_api import sync_playwright

    # One browser for the whole batch.
    pw = sync_playwright().start()
    browser = pw.chromium.launch()

    def render(path, svg, scale=scale):  # noqa: A002 - signature matches skill
        m = _SVG_WH.search(svg)
        w, h = (int(m.group(1)), int(m.group(2))) if m else (1180, 660)
        page = browser.new_page(
            viewport={"width": w, "height": h}, device_scale_factor=scale
        )
        page.set_content(
            f'<!doctype html><html><head><meta charset="utf-8">'
            f'<style>html,body{{margin:0;padding:0;background:transparent}}</style>'
            f"</head><body>{svg}</body></html>",
            wait_until="networkidle",
        )
        el = page.query_selector("svg")
        (el or page).screenshot(path=str(path), omit_background=True)
        page.close()
        print("rendered", path)

    def close():
        browser.close()
        pw.stop()

    return render, close


def _scores_list(result: AuditResult) -> List[Tuple[str, int]]:
    # Canonical category order, with shorter display labels matching the skill.
    display = {
        "Technical SEO": "Technical SEO",
        "Content Quality": "Content quality",
        "On-Page SEO": "On-page SEO",
        "Schema / Structured Data": "Schema / structured data",
        "Core Web Vitals": "Core Web Vitals",
        "AI Search Readiness": "AI search readiness",
        "Images": "Images",
    }
    out = []
    for cat in CATEGORY_WEIGHTS:
        if cat in result.scores:
            out.append((display[cat], int(result.scores[cat])))
    return out


def scorecard_only(overall: int, scores: dict, out_dir: Path) -> str:
    """Render just the scorecard PNG (used by the lite/batch path). 0 tokens."""
    out_dir.mkdir(parents=True, exist_ok=True)
    gv = _load_skill_module()
    render, close = _make_renderer()
    gv.render = render
    display = {
        "Technical SEO": "Technical SEO",
        "Content Quality": "Content quality",
        "On-Page SEO": "On-page SEO",
        "Schema / Structured Data": "Schema / structured data",
        "Core Web Vitals": "Core Web Vitals",
        "AI Search Readiness": "AI search readiness",
        "Images": "Images",
    }
    pairs = [(display[c], int(scores[c])) for c in CATEGORY_WEIGHTS if c in scores]
    try:
        gv.viz_scorecard(str(out_dir), overall, pairs)
    finally:
        close()
    return "viz_scorecard.png"


def scorecard_only_batch(jobs: list) -> None:
    """Render many scorecards in ONE browser session.

    jobs: list of (overall:int, scores:dict, out_dir:Path).
    """
    if not jobs:
        return
    gv = _load_skill_module()
    render, close = _make_renderer()
    gv.render = render
    display = {
        "Technical SEO": "Technical SEO",
        "Content Quality": "Content quality",
        "On-Page SEO": "On-page SEO",
        "Schema / Structured Data": "Schema / structured data",
        "Core Web Vitals": "Core Web Vitals",
        "AI Search Readiness": "AI search readiness",
        "Images": "Images",
    }
    try:
        for overall, scores, out_dir in jobs:
            Path(out_dir).mkdir(parents=True, exist_ok=True)
            pairs = [(display[c], int(scores[c])) for c in CATEGORY_WEIGHTS
                     if c in scores]
            gv.viz_scorecard(str(out_dir), overall, pairs)
    finally:
        close()


def generate(result: AuditResult, out_dir: Path) -> List[str]:
    """Render all four visuals into out_dir. Returns the filenames written."""
    out_dir.mkdir(parents=True, exist_ok=True)
    gv = _load_skill_module()
    render, close = _make_renderer()
    gv.render = render  # monkeypatch the skill's Cairo renderer

    v = result.visuals
    faqs = v.faqs or [
        "Does it support multi-store?",
        "Is it compliant in my state?",
        "How long is onboarding?",
    ]
    meta_before = v.metaBefore or (
        "Your product gives customers real-time inventory, compliance and "
        "reporting in one platform that hel"
    )
    meta_after = v.metaAfter or (
        "Run your business on one platform — real-time inventory, built-in "
        "compliance, and one-click reporting. Book a demo."
    )
    rm = result.roadmap
    now = (rm.now if rm else None) or ["Add structured data (schema)", "Clear HTML validation errors"]
    week = (rm.week if rm else None) or ["Rewrite truncated meta", "Speed up server (TTFB)"]
    month = (rm.month if rm else None) or ["FAQ schema", "Public pricing page", "llms.txt"]

    try:
        gv.viz_scorecard(str(out_dir), result.overall or 0, _scores_list(result))
        gv.viz_richresult(str(out_dir), v.pageTitle, v.posPath, faqs[:3])
        gv.viz_meta(str(out_dir), v.pageTitle, meta_before, meta_after)
        gv.viz_roadmap(str(out_dir), now[:5], week[:5], month[:5])
    finally:
        close()

    return [
        "viz_scorecard.png",
        "viz_richresult.png",
        "viz_meta.png",
        "viz_roadmap.png",
    ]
