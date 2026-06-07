"""Browserless (Vercel-safe) Google Doc builder.

Renders the audit WITHOUT any headless browser: the scorecard becomes a Docs
table with text-bar cells, the roadmap a 3-column table, the meta finding two
colored callouts. No Playwright, no PNG hosting required. Reuses the DocBuilder
primitives from gdocs.py.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from . import config
from .gdocs import (DocBuilder, GREEN, GREEN_DK, GREENTINT, INK, MUTE, PAPER,
                    PERI, RED, RED_DK, _proof_section)
from .models import CATEGORY_WEIGHTS, status_band

BAR_LEN = 22
PAPER2 = "EDE6D9"
AMBER = "C97A06"
BULLET = "•"
BLOCK = "█"


def _band_color(v: int) -> str:
    if v >= 75:
        return GREEN
    if v >= 50:
        return AMBER
    return RED


def _bar_runs(score: int) -> list:
    filled = max(0, min(BAR_LEN, round(score / 100 * BAR_LEN)))
    col = _band_color(score)
    runs = []
    if filled:
        runs.append({"text": BLOCK * filled, "color": col, "size": 10})
    if BAR_LEN - filled:
        runs.append({"text": BLOCK * (BAR_LEN - filled), "color": PAPER2,
                     "size": 10})
    return runs


def scorecard_native(b: DocBuilder, overall: int, status: str, scores: dict):
    """Overall score line + a category table with text bars (no image)."""
    band_col = _band_color(overall)
    b.para([{"text": "OVERALL SCORE   ", "bold": True, "color": MUTE, "size": 11},
            {"text": str(overall), "bold": True, "color": band_col, "size": 28},
            {"text": "  / 100   ", "color": MUTE, "size": 12},
            {"text": (status or status_band(overall)).upper(), "bold": True,
             "color": band_col, "size": 13}],
           space_before=4, space_after=8)

    display = {
        "Technical SEO": "Technical SEO",
        "Content Quality": "Content quality",
        "On-Page SEO": "On-page SEO",
        "Schema / Structured Data": "Schema / structured data",
        "Core Web Vitals": "Core Web Vitals",
        "AI Search Readiness": "AI search readiness",
        "Images": "Images",
    }
    rows = []
    for cat in CATEGORY_WEIGHTS:
        if cat not in scores:
            continue
        v = int(scores[cat])
        rows.append([
            [{"text": display[cat], "bold": True, "color": INK, "size": 9.5}],
            _bar_runs(v),
            [{"text": str(v), "bold": True, "color": _band_color(v), "size": 10}],
        ])
    b.rich_table(["Category", "Score", ""], rows, [165, 240, 45])
    b.body([{"text": "Green >=75 (healthy)  -  amber 50-74 (fair)  -  red <50 "
             "(needs attention).", "italic": True, "color": MUTE, "size": 9}],
           space_after=8)


def roadmap_native(b: DocBuilder, roadmap):
    if not roadmap:
        return
    now = roadmap.now if hasattr(roadmap, "now") else roadmap.get("now", [])
    week = roadmap.week if hasattr(roadmap, "week") else roadmap.get("week", [])
    month = roadmap.month if hasattr(roadmap, "month") else roadmap.get("month", [])

    def cell(items):
        text = "\n".join(BULLET + "  " + it for it in items) if items else " "
        return [{"text": text, "color": INK, "size": 9}]

    b.rich_table(["FIX NOW", "THIS WEEK", "THIS MONTH"],
                 [[cell(now), cell(week), cell(month)]],
                 [156, 156, 156],
                 header_fills=[RED, AMBER, GREEN])


def _asset_getter(assets: Optional[Path]):
    def get(name):
        if assets and (assets / name).exists():
            return assets / name
        return None
    return get


# ---------------------------------------------------------------- builders
def build_native_lite(lite, proof: Optional[dict] = None,
                      assets: Optional[Path] = None,
                      proof_uris: Optional[dict] = None) -> dict:
    cl = lite.client
    b = DocBuilder(f"SEO & AI-Search Audit - {lite.client}")
    if proof_uris and assets:
        for name, uri in proof_uris.items():
            b.seed_uri(assets / name, uri)

    b.band("SEO & AI-search audit", lite.client, lite.subtitle or "", title_size=34)
    b.body([{"text": "Prepared by ", "color": MUTE},
            {"text": "Bhushan Raj Shakya", "bold": True},
            {"text": " - RankedTag - the inbound engine for SaaS founders.",
             "color": MUTE}], space_after=8)

    b.eyebrow("At a glance")
    b.heading(f"Hi {cl} team - here's your snapshot")
    if lite.summary:
        b.body(lite.summary)
    scorecard_native(b, lite.overall or 0, lite.status or "", lite.scores)

    if lite.findings:
        b.eyebrow("What's costing you the most", RED)
        b.heading("The highest-impact fixes", num="1")
        for f in lite.findings:
            b.h2(f.h, color=RED_DK)
            if f.why:
                b.body(f.why)
            if f.fix:
                b.callout("What to do", f.fix, tint=GREENTINT, accent=GREEN,
                          label_color=GREEN_DK)

    if lite.quickWins:
        b.eyebrow("Start here", RED)
        b.heading("Quick wins", num="2")
        for q in lite.quickWins:
            b.bullet(q)

    if proof and config.INCLUDE_PROOF:
        _proof_section(b, proof, cl, _asset_getter(assets), lite=True)

    b.eyebrow("What happens next")
    b.heading("Let's turn this into rankings")
    b.body("This is a fast snapshot. The next step is a full deep-dive audit and a "
           "30-day plan your team can action - happy to walk you through it.")
    b.callout("Bhushan Raj Shakya",
              [{"text": "SEO & Technical Audit - RankedTag", "color": MUTE,
                "size": 10}], tint=PAPER, accent=RED, label_color=INK)
    b.body([{"text": "hello@rankedtag.com", "color": PERI, "size": 10},
            {"text": "      -      ", "color": MUTE, "size": 10},
            {"text": "rankedtag.com", "color": PERI, "size": 10,
             "link": "https://rankedtag.com", "underline": True}])
    return b.finish(config.MAKE_PUBLIC)


def build_native_full(result, proof: Optional[dict] = None,
                      assets: Optional[Path] = None,
                      proof_uris: Optional[dict] = None) -> dict:
    cl = result.clientLabel or result.client
    b = DocBuilder(f"SEO & AI-Search Audit - {result.client}")
    if proof_uris and assets:
        for name, uri in proof_uris.items():
            b.seed_uri(assets / name, uri)

    # cover
    b.band("SEO & AI-search audit", result.client, result.subtitle or "",
           title_size=34)
    b.body([{"text": "Prepared for ", "color": MUTE},
            {"text": cl + " ", "bold": True},
            {"text": f"({result.client})" +
             (f" - {result.businessType}." if result.businessType else "."),
             "color": MUTE}], space_after=2)
    b.body([{"text": "Prepared by ", "color": MUTE},
            {"text": result.consultantName, "bold": True},
            {"text": " - RankedTag.", "color": MUTE}], space_after=8)

    # note
    b.eyebrow("A quick note before you dig in")
    b.heading(f"Hi {cl} team -")
    for p in result.note:
        b.body(p)

    # why
    if result.why:
        b.eyebrow("The why")
        b.heading("Search just split into two races", num="1")
        for p in result.why.intro:
            b.body(p)
        if result.why.callout:
            b.callout(result.why.calloutLabel or f"Why this matters for {cl}",
                      result.why.callout)
        if result.why.outro:
            b.body(result.why.outro)

    # method + scorecard
    b.eyebrow("The what & how")
    b.heading("What I looked at, and how", num="2")
    if result.method and result.method.scope:
        b.body(result.method.scope)
    if result.method and result.method.how:
        b.body([{"text": "Method, in plain terms. ", "bold": True},
                {"text": result.method.how}])
    b.heading("The scorecard", num="3")
    scorecard_native(b, result.overall or 0, result.status or "", result.scores)

    # critical
    b.eyebrow("What's costing you the most", RED)
    b.heading("Fix these first", num="4")
    for f in result.critical:
        b.h2(f.heading, color=RED_DK)
        for p in f.body:
            b.body(p)
        if f.whatToDo:
            b.callout("What to do", f.whatToDo, tint=GREENTINT, accent=GREEN,
                      label_color=GREEN_DK)

    # high (meta finding -> before/after callouts)
    if result.high:
        b.eyebrow("High priority - within a week", AMBER)
        b.heading("The week-one list", num="5")
        for f in result.high:
            b.h2(f.heading)
            for p in f.body:
                b.body(p)
            if f.visual == "meta" and result.visuals.metaBefore:
                b.callout("Now - cut off mid-sentence",
                          result.visuals.metaBefore + "...", tint="FBEAE4",
                          accent=RED, label_color=RED_DK)
                if result.visuals.metaAfter:
                    b.callout("Fixed - complete, under 155 chars",
                              result.visuals.metaAfter, tint=GREENTINT,
                              accent=GREEN, label_color=GREEN_DK)
            if f.whatToDo:
                b.callout("What to do", f.whatToDo, tint=GREENTINT, accent=GREEN,
                          label_color=GREEN_DK)

    # medium
    if result.medium:
        b.eyebrow("Medium priority - within a month", GREEN_DK)
        b.heading("Worth doing this month", num="6")
        b.rich_table(["Finding", "Why it matters / what to do"],
                     [[[{"text": m.finding, "bold": True, "size": 9.5}],
                       [{"text": m.detail, "size": 9.5}]] for m in result.medium],
                     [150, 318])

    # quick wins + roadmap
    if result.quickWins:
        b.eyebrow("Start here", RED)
        b.heading("Five quick wins", num="7")
        for q in result.quickWins:
            b.bullet([{"text": q.title, "bold": True}, {"text": " - " + q.detail}])
    if result.roadmap:
        roadmap_native(b, result.roadmap)

    # action plan
    if result.actionPlan:
        b.eyebrow("The full list")
        b.heading("Recommended action plan", num="8")
        b.rich_table(["Action", "Owner", "Effort", "Expected impact"],
                     [[[{"text": a.action, "size": 9.5}],
                       [{"text": a.owner, "size": 9.5}],
                       [{"text": a.effort, "size": 9.5}],
                       [{"text": a.impact, "size": 9.5}]]
                      for a in result.actionPlan],
                     [218, 60, 60, 130])

    # competitive
    if result.competitive:
        b.eyebrow("Where you stand")
        b.heading("Competitive context", num="9")
        if result.competitive.intro:
            b.body(result.competitive.intro)
        for p in result.competitive.points:
            b.bullet(p)

    if proof and config.INCLUDE_PROOF:
        _proof_section(b, proof, cl, _asset_getter(assets), lite=True)

    # next
    b.eyebrow("What happens next")
    b.heading("Let's turn this into rankings")
    for n in (result.next or []):
        b.bullet([{"text": n.label + " ", "bold": True}, {"text": n.text}])
    if result.nextOutro:
        b.body(result.nextOutro)
    b.callout(result.consultantName,
              [{"text": "SEO & Technical Audit - RankedTag", "color": MUTE,
                "size": 10}], tint=PAPER, accent=RED, label_color=INK)
    b.body([{"text": result.consultantEmail, "color": PERI, "size": 10},
            {"text": "      -      ", "color": MUTE, "size": 10},
            {"text": "rankedtag.com", "color": PERI, "size": 10,
             "link": "https://rankedtag.com", "underline": True}])
    return b.finish(config.MAKE_PUBLIC)
