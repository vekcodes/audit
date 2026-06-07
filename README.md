# RankedTag SEO Audit API

Pass a website URL → get a branded, **public Google Doc** SEO & AI-search (GEO)
audit, generated with the bundled `rankedtag-audit` skill.

```
POST /audit  { "website": "https://treez.io" }
        │
        ▼
  fetch + analyze the site (homepage signals, schema, meta, robots, llms.txt)
        │
        ▼
  Qwen (qwen3.7-max) runs the full RankedTag methodology + writes the
  humanized, first-person narrative  →  validated audit JSON
        │
        ▼
  render 4 branded visuals (scorecard, rich-result, meta, roadmap) — Playwright
        │
        ▼
  fetch live proof case study (sendr.ai) from rankedtag.com
        │
        ▼
  build a native Google Doc (Docs API) with embedded visuals + brand styling
        │
        ▼
  share it public (anyone with the link)  →  return the URL
```

## Architecture

| Concern | Choice |
|---|---|
| Audit brain | **Qwen `qwen3.7-max`** via your OpenAI-compatible MaaS endpoint |
| Server | **FastAPI** (Python) |
| Visuals | Skill's exact SVGs, rasterized with **Playwright/Chromium** (Cairo-free) |
| Output | **Native Google Docs API** + Drive public share |
| Google auth | **OAuth refresh token** (your personal Gmail) |

## Setup

### 1. Install (already done if you see `.venv/`)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
```

### 2. Configure Qwen

Already wired in `.env` (`QWEN_API_KEY`, `QWEN_BASE_URL`, `QWEN_MODEL`).

### 3. Configure Google (one-time)

In the [Google Cloud Console](https://console.cloud.google.com/) (free):

1. Create or select a project.
2. **APIs & Services → Library**: enable **Google Docs API** and **Google Drive API**.
3. **OAuth consent screen**: User type *External*; add your Gmail under **Test users**.
4. **Credentials → Create credentials → OAuth client ID → Desktop app**. Copy the
   **Client ID** and **Client secret**.
5. Get a refresh token (opens a browser once):

   ```powershell
   .\.venv\Scripts\python.exe setup_oauth.py --client-id YOUR_ID --client-secret YOUR_SECRET
   ```

6. Paste the three printed values into `.env`:
   `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`.

## Run

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then:

```powershell
curl -X POST http://localhost:8000/audit -H "Content-Type: application/json" -d '{\"website\":\"https://treez.io\"}'
```

Response:

```json
{
  "website": "https://treez.io",
  "client": "treez.io",
  "overall_score": 62,
  "status": "Fair",
  "scores": { "...": 0 },
  "public_url": "https://docs.google.com/document/d/<id>/view",
  "edit_url": "https://docs.google.com/document/d/<id>/edit",
  "document_id": "<id>",
  "proof_source": "live",
  "run_dir": "runs/treez.io-..."
}
```

`GET /health` reports whether Qwen and Google are configured.

## Notes

- A full audit takes ~1.5–3 min (the model does deep reasoning over the site).
- Each run's artifacts (audit.json, the 4 PNGs, proof assets) are kept under `runs/`.
- Set `MAKE_PUBLIC=false` in `.env` to create private docs.
- Set `INCLUDE_PROOF=false` to skip the sendr.ai case study.
- The skill itself lives in `skill/` (extracted from `rankedtag-audit.skill`); the
  audit methodology, house voice, and design system come straight from it.
