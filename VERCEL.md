# Deploy to Vercel

The API runs on Vercel as a Python serverless function (browserless — the
scorecard/roadmap render as native Google Docs tables, no Chromium).

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/audit` | `{ "website": "...", "mode": "lite" }` → public Google Doc |
| `GET`  | `/api/oauth/start` | one-time: authorize your Google account |
| `GET`  | `/api/oauth/callback` | Google redirects here; shows the refresh token |
| `GET`  | `/api/health` | status + whether Google is authorized |

## Step 1 — Deploy

Easiest is the Vercel CLI (this folder isn't a git repo yet):

```powershell
npm i -g vercel
vercel            # first run: links/creates the project, deploys a preview
vercel --prod     # production deploy
```

(Or push the folder to GitHub and "Import Project" in the Vercel dashboard.)

## Step 2 — Set Environment Variables (Vercel → Project → Settings → Environment Variables)

```
QWEN_API_KEY           = <your Qwen key>
QWEN_BASE_URL          = <your Qwen OpenAI-compatible base URL>
QWEN_MODEL             = qwen3.7-max
GOOGLE_CLIENT_ID       = <your Google OAuth client id>
GOOGLE_CLIENT_SECRET   = <your Google OAuth client secret>
GOOGLE_REDIRECT_URI    = https://<your-app>.vercel.app/api/oauth/callback
INCLUDE_PROOF          = false
MAKE_PUBLIC            = true
```

> Real values live only in your local `.env` (gitignored) and in the Vercel
> dashboard — never commit them.

Redeploy after setting them (`vercel --prod`).

## Step 3 — Register the redirect URI

Google Cloud Console → APIs & Services → Credentials → your OAuth client →
**Authorized redirect URIs** → add **exactly**:

```
https://<your-app>.vercel.app/api/oauth/callback
```

Save (wait ~30s).

## Step 4 — Authorize once (in the browser)

Visit:

```
https://<your-app>.vercel.app/api/oauth/start
```

Pick **shakyabhusan3@gmail.com** → (Advanced → Go to … unsafe, if shown) → **Allow**.
The callback page shows your **GOOGLE_REFRESH_TOKEN**.

## Step 5 — Save the token + redeploy

Add it in Vercel env vars:

```
GOOGLE_REFRESH_TOKEN = 1//0g...   (from the callback page)
```

Then `vercel --prod`. Done — fully headless from now on.

## Step 6 — Use it

```bash
curl -X POST https://<your-app>.vercel.app/api/audit \
  -H "Content-Type: application/json" \
  -d '{"website":"https://stripe.com","mode":"lite"}'
```

Returns `{ "public_url": "https://docs.google.com/document/d/.../view", ... }`.

### Notes
- `mode": "lite"` (~5s) is the Vercel default and fits the 60s function limit.
- `"mode": "full"` is the deep ~110s audit — needs Vercel **Pro** and
  `maxDuration` raised to 300 in `vercel.json`.
- `GOOGLE_REDIRECT_URI` must match the registered URI **exactly** (scheme, host,
  path, no trailing slash differences).
