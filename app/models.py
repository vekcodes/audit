"""Pydantic schema for the structured audit the LLM must return.

This mirrors the `audit.json` shape documented in the skill's
references/audit-content.md, plus the per-category scores and the
parameters the visual generator needs.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

# Category weights from skill/references/audit-methodology.md (sum = 100).
CATEGORY_WEIGHTS: Dict[str, int] = {
    "Technical SEO": 22,
    "Content Quality": 23,
    "On-Page SEO": 20,
    "Schema / Structured Data": 10,
    "Core Web Vitals": 10,
    "AI Search Readiness": 10,
    "Images": 5,
}


class CriticalFinding(BaseModel):
    heading: str
    body: List[str] = Field(default_factory=list)
    visual: Optional[str] = None  # "richresult" | "meta" | None
    whatToDo: Optional[str] = None


class HighFinding(BaseModel):
    heading: str
    body: List[str] = Field(default_factory=list)
    visual: Optional[str] = None
    whatToDo: Optional[str] = None


class MediumFinding(BaseModel):
    finding: str
    detail: str


class QuickWin(BaseModel):
    title: str
    detail: str


class Roadmap(BaseModel):
    now: List[str] = Field(default_factory=list)
    week: List[str] = Field(default_factory=list)
    month: List[str] = Field(default_factory=list)


class ActionItem(BaseModel):
    action: str
    owner: str
    effort: str
    impact: str


class Competitive(BaseModel):
    intro: str = ""
    points: List[str] = Field(default_factory=list)


class WhySection(BaseModel):
    intro: List[str] = Field(default_factory=list)
    calloutLabel: Optional[str] = None
    callout: Optional[str] = None
    outro: Optional[str] = None


class MethodSection(BaseModel):
    scope: str = ""
    how: str = ""


class NextStep(BaseModel):
    label: str
    text: str


class Visuals(BaseModel):
    """Parameters that tailor the four generated PNGs to this client."""
    pageTitle: str = "Product | Your Brand"
    posPath: str = "products › product"
    faqs: List[str] = Field(default_factory=list)
    metaBefore: str = ""
    metaAfter: str = ""


class AuditResult(BaseModel):
    # identity
    client: str
    clientLabel: Optional[str] = None
    businessType: str = ""
    subtitle: str = (
        "Technical SEO + AI-search (GEO) readiness, scored — with a prioritised "
        "plan you can hand straight to your team."
    )

    # consultant (brand constants; model may keep defaults)
    consultantFirstName: str = "Bhushan"
    consultantName: str = "Bhushan Raj Shakya"
    consultantEmail: str = "hello@rankedtag.com"

    # scores
    scores: Dict[str, int]
    overall: Optional[int] = None  # computed server-side from weights
    status: Optional[str] = None  # computed server-side

    # narrative sections
    note: List[str] = Field(default_factory=list)
    why: Optional[WhySection] = None
    method: Optional[MethodSection] = None
    critical: List[CriticalFinding] = Field(default_factory=list)
    high: List[HighFinding] = Field(default_factory=list)
    medium: List[MediumFinding] = Field(default_factory=list)
    quickWins: List[QuickWin] = Field(default_factory=list)
    roadmap: Optional[Roadmap] = None
    actionPlan: List[ActionItem] = Field(default_factory=list)
    competitive: Optional[Competitive] = None
    next: List[NextStep] = Field(default_factory=list)
    nextOutro: Optional[str] = None

    visuals: Visuals = Field(default_factory=Visuals)

    def finalize(self) -> "AuditResult":
        """Compute overall score + status band from category scores & weights."""
        if not self.clientLabel:
            self.clientLabel = self.client
        total = 0.0
        wsum = 0
        for cat, weight in CATEGORY_WEIGHTS.items():
            val = self.scores.get(cat)
            if val is None:
                continue
            total += val * weight
            wsum += weight
        if wsum:
            self.overall = round(total / wsum)
        self.status = status_band(self.overall or 0)
        return self


def status_band(score: int) -> str:
    if score >= 75:
        return "Good"
    if score >= 50:
        return "Fair"
    return "Poor"
