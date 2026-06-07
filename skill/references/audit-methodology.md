# Audit Methodology

The analysis engine behind a RankedTag audit. This produces the scores, findings, and action plan that the document then dresses up. Run every category, score it, then bucket findings by priority.

## Step 1 — Fetch & detect

Fetch the homepage HTML (use `web_fetch`, and the raw HTML via curl/bash for `<head>` and markup inspection). Detect the business type from signals: navigation labels, meta tags, schema types, product/service language, pricing pages, blog presence.

Business types: SaaS, E-commerce, Local Business, Publisher/Blog, Agency, Marketplace, Non-profit. The type shapes which findings matter most (e.g. SaaS → SoftwareApplication schema and pricing pages; E-commerce → Product schema and reviews).

## Step 2 — Crawl (as far as tooling allows)

Follow internal links to map the site. In a tool-rich environment, crawl up to ~500 pages respecting robots.txt with these settings:

```
Max pages: 500
Respect robots.txt: Yes
Follow redirects: Yes (max 3 hops)
Timeout per page: 30s
Concurrent requests: 5
Delay between requests: 1s
```

In the chat sandbox you typically can't crawl at scale — instead, fetch the key templates the audit hinges on: homepage, the primary product/service page, and the blog/archive. Be explicit in the writeup about what was actually reviewed.

## Step 3 — Run all checks

Run each module and collect findings. For each finding, record the **observation** (what you saw) and the **reasoning** (why it matters) so the client can verify independently.

1. **Technical SEO** — robots.txt, sitemaps, canonicals, security headers (HTTPS), JS rendering reliability, IndexNow, HTML validity (W3C errors), server response time (TTFB).
2. **Content Quality** — E-E-A-T signals (author bylines, credentials, especially for YMYL-adjacent niches), readability, thin content, AI citation readiness.
3. **Schema / Structured Data** — detection and validation; opportunities for Organization, SoftwareApplication, Product, FAQPage, BreadcrumbList, Review.
4. **Sitemap** — structure, URL quality, missing pages.
5. **On-Page SEO** — title tags (length, keyword value, redundant suffixes like "| Home"), meta descriptions (truncation, completeness, ~155 char target), H1–H6 structure, internal links, og/canonical consistency, duplicate content.
6. **AI Search Readiness (GEO)** — llms.txt presence, AI crawler access, citability, whether content is structured for ChatGPT/Claude/Perplexity/Gemini and Google AI Overviews to quote.
7. **Images** — alt text, file hygiene, lazy-loading, weight.
8. **Competitor gaps** — identify the top competitors for the main keywords; note where they earn rich results, pricing-page coverage, or AI-Overview citations the client doesn't.

## Step 4 — Score

### Scoring weights

| Category | Weight |
|----------|--------|
| Technical SEO | 22% |
| Content Quality | 23% |
| On-Page SEO | 20% |
| Schema / Structured Data | 10% |
| Core Web Vitals | 10% |
| AI Search Readiness | 10% |
| Images | 5% |

Score each category 0–100, apply weights, produce the overall **SEO Health Score**. Round to a whole number.

Status bands (used for color in the scorecard visual): **Good** ≥ 75, **Fair** 50–74, **Poor** < 50.

## Step 5 — Bucket findings by priority

- **Critical — fix immediately**: blocks indexing or causes penalties, or a purely-additive high-leverage fix (e.g. no structured data at all).
- **High — fix within a week**: significantly impacts rankings or the page-experience signals.
- **Medium — fix within a month**: optimization opportunities, often near-free because content already exists.
- **Low — backlog**: nice to have.

## Step 6 — Quick wins & action plan

Pick the **five quick wins**: highest impact for least effort, ordered by estimated return. These go in their own section and seed the "FIX NOW" / "THIS WEEK" columns of the roadmap visual.

Build the **action plan**: every recommendation with a suggested **owner** (Dev / Content / Marketing) and rough **effort** (minutes / hours / days / weeks) and **expected impact**.

## What the document needs from this step

When you finish the analysis, you should be able to fill in:

- `overall` score and the 7 `scores`
- findings grouped as critical / high / medium, each with a short heading + a plain-English paragraph
- the five quick wins
- the action-plan rows (action, owner, effort, impact)
- competitive context bullets
- the two "lead findings" to illustrate visually (usually missing schema → rich-result visual, truncated meta → before/after visual)

---

## Inline output format (the classic SEO report)

When the user wants a quick report in chat rather than the branded document (Step 0, inline mode), present the results in this structure. Keep the house voice (warm, plain-English, why-then-fix) from `audit-content.md`, but deliver it as a chat report, not a file.

### Executive summary

```
SEO Health Score: XX/100  [████████░░]

Business Type: [Detected type]
Pages Audited: [N]
Critical Issues: [N]
Quick Wins Available: [N]
```

### Category breakdown

| Category | Score | Status |
|----------|-------|--------|
| Technical SEO | XX/100 | Good / Fair / Poor |
| Content Quality | XX/100 | Good / Fair / Poor |
| On-Page SEO | XX/100 | Good / Fair / Poor |
| Schema | XX/100 | Good / Fair / Poor |
| Core Web Vitals | XX/100 | Good / Fair / Poor |
| AI Search Readiness | XX/100 | Good / Fair / Poor |
| Images | XX/100 | Good / Fair / Poor |

### Issues by priority

- **Critical — fix immediately**
- **High — fix within 1 week**
- **Medium — fix within 1 month**
- **Low — backlog**

### Top 5 quick wins

Highest-impact, lowest-effort fixes ranked by estimated traffic impact.

### Detailed findings

One short section per category with specific page-level findings (observation + reasoning).

### Action plan

Ordered checklist of all recommended fixes with owner (Dev / Content / Marketing) and estimated effort (minutes / hours / days / weeks) and expected impact.

After delivering an inline report, offer to upgrade it: "Want me to turn this into a branded RankedTag document you could send a client?" If yes, proceed to the document pipeline (Steps 1–6 of SKILL.md) reusing the scores and findings you already produced.
