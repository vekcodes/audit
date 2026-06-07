# Audit Content & Voice

How the document is structured, the `audit.json` the build script reads, and the voice that makes it land.

## Document structure (in order)

1. **Cover** — logo, ink hero band with the client domain, a one-line positioning subtitle, the overall score + status, and an "Inside:" line previewing the sections.
2. **A quick note** — a short, warm, first-person opening ("Hi <client> team —"). Why you ran the audit, how you looked at the site, what to expect, and a nod to the proof at the end. Signed with a first name.
3. **The why** — the "search just split into two races" framing: traditional Google ranking *and* AI-assistant discovery (ChatGPT/Claude/Perplexity/Gemini/AI Overviews). Make it specific to the client's niche, and tie it to their weakest relevant score (usually AI-search readiness). One periwinkle "why this matters for <client>" callout.
4. **The what & how** — what pages were reviewed and the plain-English methodology. No black box; say the team can verify each finding.
5. **The scorecard** — one line of intro, then the `viz_scorecard.png` with a muted italic caption explaining the color bands.
6. **Fix these first (critical)** — each critical finding as an H2 + paragraph. The schema finding embeds `viz_richresult.png` and a green "what to do" callout.
7. **The week-one list (high)** — each high finding as H2 + paragraph. The meta finding embeds `viz_meta.png`.
8. **Worth doing this month (medium)** — a two-column table (Finding | Why it matters / what to do).
9. **Five quick wins** — a red-bulleted list ordered by return, then `viz_roadmap.png`.
10. **Recommended action plan** — the full four-column table (Action | Owner | Effort | Expected impact).
11. **Competitive context** — red-bulleted observations about the main rivals.
12. **Proof — not promises** — ink band header, then the live sendr.ai case: a 3-cell metric strip, the two screenshots with captions, a founder-quote callout, the "how we out-content the giants" three-piece engine (senior humans + Claude + workflow automation), and a green "what this means for <client>" callout tying it back.
13. **What happens next** — a short red-bulleted plan (this week / together / then), the "four clients a month" line, and a signature callout block with name, role, email, and rankedtag.com.

Use `pageBreakBefore` to start each major section cleanly, but avoid forcing a break that leaves a near-empty orphan page — if a section's intro is short, let it flow. (Verify in the PDF preview.)

## The house voice

This is the differentiator. Write like a sharp, generous consultant talking to a founder — not like an SEO tool.

- **First person, warm, direct.** "I couldn't find any schema markup at all" beats "No structured data was detected."
- **Plain English over jargon.** When a term is unavoidable (TTFB, E-E-A-T, canonical), define it in half a sentence.
- **Lead with why it matters, then the fix.** Every finding answers "so what?" for a busy non-technical reader.
- **Reassuring, not alarmist.** "None of this is scary; most of it is an afternoon's work." Frame gaps as fixable and additive.
- **Specific to the client.** Reference their actual niche, their actual strongest segment, their real competitors.
- **Honest about proof.** Use the exact figures from `proof.json`. Never round up or embellish.
- **No filler praise, no hype.** Confidence comes from specificity, not adjectives.

Example rewrites:
- Tool voice: "Meta description exceeds recommended length and is truncated." → House voice: "The POS page's meta description is cut off mid-sentence. When a snippet reads as incomplete, Google often discards it and writes its own — usually weaker and off-message."
- Tool voice: "Structured data not implemented." → House voice: "I couldn't find any schema markup at all. It's the highest-leverage fix in the report because it's purely additive — no risk to existing rankings, and the upside lands fast."

## audit.json schema

The build script reads one JSON object. All text fields accept plain strings; the script handles styling and smart quotes. Keep findings to a tight heading + one or two paragraphs.

```json
{
  "client": "treez.io",
  "clientLabel": "Treez",
  "businessType": "SaaS / cannabis retail technology",
  "overall": 62,
  "status": "Fair",
  "subtitle": "Technical SEO + AI-search (GEO) readiness, scored — with a prioritised plan you can hand straight to your team.",
  "consultantFirstName": "Bhushan",
  "consultantName": "Bhushan Raj Shakya",
  "consultantEmail": "hello@rankedtag.com",

  "note": ["Para 1 of the opening note.", "Para 2.", "Para 3."],

  "why": {
    "intro": ["The two-races framing, para 1.", "Para 2 with the 40% stat."],
    "calloutLabel": "Why this matters for Treez specifically",
    "callout": "One paragraph tying it to their niche and weakest score.",
    "outro": "The good-news closer."
  },

  "method": {
    "scope": "Which pages were reviewed.",
    "how": "Plain-English methodology paragraph."
  },

  "critical": [
    {"heading": "No structured data anywhere on the site",
     "body": ["Para 1.", "Para 2."],
     "visual": "richresult",
     "whatToDo": "Add Organization + SoftwareApplication to the homepage, FAQPage to the product page, BreadcrumbList across templates."}
  ],

  "high": [
    {"heading": "The POS meta description is cut off mid-sentence",
     "body": ["Para."],
     "visual": "meta"}
  ],

  "medium": [
    {"finding": "Redundant \u201C| Home\u201D in homepage title",
     "detail": "Why it matters and what to do."}
  ],

  "quickWins": [
    {"title": "Add FAQPage schema to the product page", "detail": "The FAQ content already exists — a ~two-hour job."}
  ],

  "roadmap": {
    "now": ["Add structured data (schema)", "Clear HTML validation errors"],
    "week": ["Rewrite truncated meta", "Speed up server (TTFB)"],
    "month": ["FAQ schema", "Public pricing page", "llms.txt"]
  },

  "actionPlan": [
    {"action": "Add FAQPage schema to product page", "owner": "Dev", "effort": "2 hrs", "impact": "FAQ rich results in search"}
  ],

  "competitive": {
    "intro": "The main players are A, B, C.",
    "points": ["Observation 1.", "Observation 2."]
  },

  "next": [
    {"label": "This week:", "text": "knock out the five quick wins."},
    {"label": "Together:", "text": "I'll walk your team through any finding."},
    {"label": "Then:", "text": "we re-test once the first round is live."}
  ],
  "nextOutro": "The 'four clients a month' line."
}
```

Fields the script fills from `proof.json` (do NOT duplicate in audit.json): the metric strip numbers, founder quote, engine bullets, and the "proof" screenshots. The build script merges `proof.json` automatically when given `--assets`.

The `visual` field on a finding can be `"richresult"`, `"meta"`, or omitted. Only one finding should carry each visual.
