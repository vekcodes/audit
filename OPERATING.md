# Operating Procedure — RankedTag SEO Audit API

API: `https://audit-plum-five.vercel.app`

## How it handles Clay's ~80 calls/min

Google Docs allows **60 writes/min/user** (≈30 audits/min). Clay sends faster than
that, so the server **paces** the work instead of failing:

```
Clay (≈80/min)
   │  POST /api/audit { website }
   ▼
┌──────────────────────────────────────────────┐
│ 1. Cached already?  → return public_url (instant) │
│ 2. Same URL in flight?  → 429 "processing"        │
│ 3. Global slot free (≤25/min)?                    │
│       no  → 429 "rate_limited" (Retry-After)      │
│       yes → build Google Doc → cache → return URL │
└──────────────────────────────────────────────┘
```

- **429s are normal and expected.** Clay automatically backs off and retries 429s
  (it respects `Retry-After`). Rows that get a 429 are *not* failures — they fill
  in on a later retry.
- **Idempotent:** once a site is audited, the result is cached for 7 days, so
  retries (or duplicate rows) return the same URL instantly — no re-audit, no
  wasted tokens or writes.
- **Net effect:** Clay can fire at 80/min; the server drains at ~25/min; every row
  ends up with a `public_url`. A 600-row list completes in ~25–30 min.

---

## ONE-TIME SETUP (required for pacing)

Without Redis the limiter is a no-op (it "fails open"), so you'd still hit Google
429s under load. Add Redis — one click, no separate signup:

1. Vercel → your project → **Storage** tab → **Create Database** → **Upstash for
   Redis** (Marketplace) → connect it to the project. This auto-adds
   `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` to your env vars.
2. **Redeploy** (Deployments → ⋯ → Redeploy).
3. Verify: open `https://audit-plum-five.vercel.app/api/health` — it should show
   `"redis_enabled": true` and `"rate_limit_per_min": 25`.

Optional tuning (Vercel env vars):
- `RATE_LIMIT_PER_MIN` — audits/min cap. Default `25` (= 50 writes/min, safely
  under 60). Raise it **only** after a Google quota increase (below).
- `RESULT_CACHE_TTL` — cache seconds (default 604800 = 7 days).

---

## CLAY SETUP

1. Add an **HTTP API** enrichment column.
2. Method **POST**, URL `https://audit-plum-five.vercel.app/api/audit`
3. Header `Content-Type: application/json`
4. Body:
   ```json
   { "website": "{{your_domain_column}}", "mode": "lite" }
   ```
5. Map the response field **`public_url`** to a column (also useful:
   `overall_score`, `status`).
6. **Enable retries / auto-retry on error** (Clay does this for 429s by default).
   Leave Clay's rate where it is (~80/min is fine — the server paces it).

### Running a batch
- Run the column over your rows. Expect a wave of 429s while it drains — that's
  the pacing working.
- When the run settles, use **Run → only empty / error cells** once or twice to
  mop up any rows still showing a 429. They'll resolve from cache/queue quickly.
- Done when every row has a `public_url`.

---

## GO FASTER (optional): raise the Google quota

Default ceiling is 60 writes/min. To lift it:

1. Google Cloud Console → **IAM & Admin → Quotas & System Limits**.
2. Filter service = **Google Docs API**, find **Write requests per minute per
   user**.
3. Select it → **Edit Quota** → request e.g. **300** (or 600) → submit
   (usually approved in ~1–2 days, free).
4. After approval, set Vercel env `RATE_LIMIT_PER_MIN` to ~ (new_limit ÷ 2)
   (e.g. 150) and redeploy. Now Clay's 80/min runs essentially in real time.

---

## QUICK REFERENCE

| Symptom | Meaning / action |
|---|---|
| Many `429` during a run | Normal pacing. Clay retries; re-run empty/error cells after. |
| `/api/health` `redis_enabled: false` | Upstash not connected → add it + redeploy. |
| `400 GOOGLE_REFRESH_TOKEN missing` | Token env var not set → re-do `/api/oauth/start`. |
| Same site returns instantly | Served from the 7-day cache (idempotent). |
| Want a fresh re-audit of a site | Wait for cache TTL or change the URL slightly; (or we add a `?fresh=1` flag). |
| Need deep audit | `"mode": "full"` — needs Vercel Pro (raise `maxDuration` to 300). |

## Endpoints
- `POST /api/audit` — `{website, mode}` → `{public_url, scores, ...}`
- `GET  /api/health` — config + redis + rate-limit status
- `GET  /api/oauth/start` — re-authorize Google if the token is ever revoked
