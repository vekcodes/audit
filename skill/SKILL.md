---
name: rankedtag-audit
description: >
  All-in-one SEO & AI-search (GEO) audit skill. Self-contained: it bundles the full
  audit methodology (7 scored categories, weights, priority buckets, action plan) AND
  RankedTag's signature branded Word deliverable, so it works anywhere on its own with
  no other audit skill installed. Two modes — a quick inline SEO report in chat, and a
  polished, client-winning branded .docx with a cover, scorecard dashboard, custom
  explainer graphics, a humanized narrative, and a live "proof" case study pulled from
  rankedtag.com. Use whenever the user wants to audit a website's SEO, says "audit my
  site", "full SEO check", "analyze my website", "SEO report", "website health check",
  gives a URL and asks what's wrong with their SEO, OR wants a RankedTag audit, a branded
  audit "to send/win a client", one "made attractive" with screenshots, or mentions
  RankedTag / rankedtag.com. The single skill for any SEO-audit request; it supersedes
  the plain seo-audit skill.
---

# RankedTag Audit

A complete, standalone SEO & AI-search audit skill. It runs the analysis itself and can deliver the result two ways: a fast **inline report** in chat, or RankedTag's signature **branded Word document** built to win a client. Everything it needs is bundled here — methodology, visual design system, and a live proof section — so it runs anywhere without depending on any other skill.

## What this produces

- **Inline mode**: a structured SEO report in chat — health score, per-category breakdown, issues by priority, top 5 quick wins, and an owner-assigned action plan. (This is the classic audit output.)
- **Document mode**: a multi-page `.docx` with a branded cover, a humanized opening note, a "why this matters" section, methodology, a **scorecard dashboard** graphic, custom explainer visuals for the biggest findings, prioritized findings (critical → high → medium), five quick wins, a 30-day roadmap graphic, a full action plan, competitive context, and a **proof case study** (sendr.ai, with live screenshots from rankedtag.com).

## The workflow

Follow these steps in order. Read the reference files when you reach the step that needs them — don't load everything upfront.

### Step 0 — Decide the output mode

Pick based on what the user asked for:

- **Document mode** (the full branded pipeline, Steps 1–6) when they want something presentable — a deliverable "to send/win a client", a "branded/designed/pretty" audit, an audit "with screenshots", a RankedTag audit, or any file they'll share externally. When in doubt for a client-facing request, prefer this.
- **Inline mode** when they just want to know what's wrong — "audit my site", "what's wrong with my SEO", a quick check, or an answer in chat. Run the methodology (Step 2) and present the results using the **Inline output format** documented at the end of `references/audit-methodology.md`. You can skip Steps 1, 3, 4, 5. Always offer at the end: "Want me to turn this into a branded RankedTag document you could send a client?"

If unsure which they want, ask once, briefly. Everything below (Steps 1–6) is the document pipeline.

### Step 1 — Read the docx skill first

This skill produces a Word document. Before writing any build code, read `/mnt/skills/public/docx/SKILL.md` (the standard public docx skill, present across Claude surfaces) for the docx-js patterns, table rules, and image embedding. The build script here follows those conventions. This is the only external skill touched, and only for document mode.

### Step 2 — Gather the audit data

Typical start is a **URL**. Fetch and analyze it, then score it. The full methodology — what to check across the 7 categories, the scoring weights, and the priority definitions — is in `references/audit-methodology.md`. Read that file and run the audit.

If the user instead hands you findings or an existing audit (e.g. a prior `.docx`), skip the analysis and extract the scores, findings, and action items from what they gave you. Either way, you need: an overall score, per-category scores, a list of findings bucketed by priority, and an owner-assigned action plan.

Capture the numbers you'll need for the visuals: overall score (0–100), and a score for each of the 7 categories.

### Step 3 — Fetch the live proof

The proof section uses RankedTag's real results for sendr.ai, fetched fresh each time so the numbers and screenshots stay current. Run:

```bash
python scripts/fetch_proof.py --out ./assets_run
```

This pulls the headline metrics (impressions, clicks, AI-Overview rank), the founder quote, the engine description, and the two screenshots (`result-sendr.jpeg`, `result-ranked.jpeg`) plus the logo from rankedtag.com into `./assets_run/`. It writes a `proof.json` with the text fields. If the fetch fails (site moved, offline), the script falls back to the last-known values baked into it — but always try the live fetch first. Read `proof.json` after it runs so you can quote the current numbers in the doc.

### Step 4 — Generate the branded visuals

Render the four signature graphics with the client's real numbers. Read `references/design-system.md` first — it defines the brand palette, the voice, and exactly what each visual should contain. Then run:

```bash
python scripts/generate_visuals.py \
  --out ./assets_run \
  --overall 62 \
  --scores "Technical SEO=72,Content quality=68,On-page SEO=65,Schema / structured data=35,Core Web Vitals=65,AI search readiness=40,Images=78" \
  --client "treez.io"
```

This writes `viz_scorecard.png`, `viz_richresult.png`, `viz_meta.png`, and `viz_roadmap.png`. The rich-result and meta visuals illustrate the two findings RankedTag almost always leads with (missing schema, truncated meta) — pass `--pos-path` and `--meta-before/--meta-after` to tailor them to the client, or accept the sensible defaults. Run `python scripts/generate_visuals.py --help` for all flags.

Always open the rendered PNGs with the `view` tool to confirm text doesn't overflow before building the doc. Regenerate if anything clips.

### Step 5 — Build the document

The build script assembles everything into the branded `.docx`. It reads a single `audit.json` describing the content (cover text, sections, findings, tables, proof) and emits the styled document. Read `references/design-system.md` for the layout spec and `references/audit-content.md` for the section-by-section structure and the house voice, then write `audit.json` for this client and run:

```bash
node scripts/build_audit_docx.js --data ./audit.json --assets ./assets_run --out ./rankedtag_audit_<client>.docx
```

### Step 6 — Validate, preview, deliver

```bash
python /mnt/skills/public/docx/scripts/office/validate.py ./rankedtag_audit_<client>.docx
```

Then convert to PDF and rasterize a few pages with `soffice.py` + `pdftoppm` (see the docx skill) and `view` them. Check for orphan pages, clipped images, and overflowing tables. Fix and rebuild if needed. When it's clean, present the `.docx` with `present_files`.

## Principles that make this deliverable land

These are the things that separate a RankedTag audit from a generic report. They're elaborated in the reference files, but at a glance:

- **Humanized, first-person voice.** It reads like a sharp consultant wrote it, not a tool. Warm, direct, no corporate stiffness. See the voice guide in `references/audit-content.md`.
- **Show, don't just tell.** Abstract findings (missing schema, a truncated meta tag) get a custom visual so a non-technical client instantly *gets it*.
- **Proof, not promises.** The sendr.ai case study with real Search Console screenshots is the trust anchor. Never round up or invent numbers — use exactly what `fetch_proof.py` returns.
- **Why / what / how.** Lead with why it matters (the two-races framing), then what you found, then how to fix it, with owners and effort.
- **On-brand throughout.** Cream paper, ink, signature red, periwinkle accents, Arial. The palette is in `references/design-system.md`.

## Reference files

- `references/audit-methodology.md` — the complete audit engine (fully bundles the seo-audit methodology): 7-category checks, the exact scoring weights, crawl config, priority definitions, **and the inline output format**. Read in Step 2 for both modes.
- `references/design-system.md` — brand palette, visual specs, layout rules. Read in Steps 4–5 (document mode).
- `references/audit-content.md` — section-by-section document structure, the `audit.json` schema, and the house voice with examples. Read in Step 5 (document mode).

This skill is self-contained: it does not depend on a separate `seo-audit` skill being installed. The only external file it touches is the standard public docx skill, and only when building a document.

## A note on honesty

The proof numbers and screenshots are real and belong to RankedTag's track record. Present them exactly as fetched. If a fetched figure looks implausible or the fetch fell back to baked-in defaults, say so to the user rather than presenting stale data as current. The credibility of the whole deliverable rests on this.
