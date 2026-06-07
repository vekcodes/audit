"""Lite audit: a low-token, batch-friendly variant of the full audit.

Input is the extracted site SIGNALS only (no raw HTML) and the model is asked
for compact JSON (scores + top findings + quick wins). ~1k tokens/site, so 600
sites fit inside a 1M-token batch budget. Produces a triage-grade audit that
still drives a real scorecard + a presentable public Google Doc.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from .fetcher import SiteData
from .models import CATEGORY_WEIGHTS, status_band
from .qwen import _extract_json

LITE_SYS = (
    "You are RankedTag's SEO & AI-search (GEO) auditor. From the website SIGNALS, "
    "produce a tight, accurate audit. Score these 7 categories 0-100, justified by "
    "the signals (be honest; schema and AI-search readiness are usually weakest): "
    "Technical SEO, Content Quality, On-Page SEO, Schema / Structured Data, "
    "Core Web Vitals, AI Search Readiness, Images. Then give the 4 highest-impact "
    "findings and 3 quick wins. Specific, plain-English, no fluff.\n"
    "Return ONLY this compact JSON (no markdown, no prose):\n"
    '{"client":"<bare domain>","businessType":"<detected>",'
    '"subtitle":"<one-line positioning>",'
    '"summary":"<2-sentence plain-English overview of the site\'s SEO health>",'
    '"scores":{"Technical SEO":0,"Content Quality":0,"On-Page SEO":0,'
    '"Schema / Structured Data":0,"Core Web Vitals":0,"AI Search Readiness":0,'
    '"Images":0},'
    '"findings":[{"h":"<short heading>","why":"<why it matters>","fix":"<what to do>"}],'
    '"quickWins":["<high-return, low-effort fix>"]}'
)


class LiteFinding(BaseModel):
    h: str
    why: str = ""
    fix: str = ""


class LiteResult(BaseModel):
    client: str
    businessType: str = ""
    subtitle: str = "SEO & AI-search (GEO) snapshot — scored, with the highest-impact fixes."
    summary: str = ""
    scores: Dict[str, int] = Field(default_factory=dict)
    findings: List[LiteFinding] = Field(default_factory=list)
    quickWins: List[str] = Field(default_factory=list)
    overall: Optional[int] = None
    status: Optional[str] = None

    def finalize(self) -> "LiteResult":
        total = 0.0
        wsum = 0
        for cat, weight in CATEGORY_WEIGHTS.items():
            val = self.scores.get(cat)
            if val is None:
                continue
            total += int(val) * weight
            wsum += weight
        self.overall = round(total / wsum) if wsum else 0
        self.status = status_band(self.overall)
        return self


def build_user(site: SiteData) -> str:
    return "SIGNALS:\n" + site.summary()


def parse_lite(content: str, fallback_client: str = "") -> LiteResult:
    raw = _extract_json(content)
    if not raw.get("client") and fallback_client:
        raw["client"] = fallback_client
    return LiteResult.model_validate(raw).finalize()


def run_lite(site, model: str = "qwen-flash") -> LiteResult:
    """Single-site lite audit via a fast, non-thinking model (~1-3s)."""
    from openai import OpenAI
    from . import config

    config.require_qwen()
    client = OpenAI(api_key=config.QWEN_API_KEY, base_url=config.QWEN_BASE_URL)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": LITE_SYS},
            {"role": "user", "content": build_user(site)},
        ],
        temperature=0.4,
        max_tokens=1100,
        extra_body={"enable_thinking": False},
    )
    content = resp.choices[0].message.content or ""
    return parse_lite(content, fallback_client=site.final_url)
