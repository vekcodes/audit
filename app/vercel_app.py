"""Vercel-safe FastAPI app.

Endpoints (routing-agnostic via catch-all, so they work no matter how Vercel
rewrites the path):
  POST <any>                      -> run audit, return public Google Doc link
  GET  .../api/oauth/start        -> redirect to Google consent  (one-time)
  GET  .../api/oauth/callback     -> exchange code, show refresh token to save
  GET  <any other>                -> health / usage

Browserless (native Docs rendering) — no Playwright in the import chain.
"""
from __future__ import annotations

import asyncio
import html
import traceback
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from . import config, oauth_web
from .pipeline_native import run_native

app = FastAPI(title="RankedTag SEO Audit API (Vercel)", version="1.0.0")
_executor = ThreadPoolExecutor(max_workers=2)


class AuditRequest(BaseModel):
    website: str = Field(..., examples=["https://treez.io"])
    mode: str = Field("lite", description="'lite' (fast) or 'full' (deep)")


def _redirect_uri(request: Request) -> str:
    if config.GOOGLE_REDIRECT_URI:
        return config.GOOGLE_REDIRECT_URI
    # Derive from the request; force https except on localhost.
    host = request.headers.get("x-forwarded-host") or request.url.hostname or ""
    proto = request.headers.get("x-forwarded-proto") or (
        "http" if host.startswith("localhost") or host.startswith("127.") else "https")
    port = f":{request.url.port}" if request.url.port and "localhost" in host else ""
    return f"{proto}://{host}{port}/api/oauth/callback"


def _health():
    return {
        "status": "ok",
        "service": "rankedtag-seo-audit",
        "qwen_configured": bool(config.QWEN_API_KEY),
        "google_configured": bool(
            config.GOOGLE_CLIENT_ID and config.GOOGLE_CLIENT_SECRET
            and config.GOOGLE_REFRESH_TOKEN),
        "needs_authorization": not bool(config.GOOGLE_REFRESH_TOKEN),
        "authorize_at": "/api/oauth/start",
        "usage": 'POST with {"website": "https://example.com", "mode": "lite"}',
    }


@app.get("/{path:path}")
def get_any(path: str, request: Request):
    qp = request.query_params
    redirect_uri = _redirect_uri(request)

    # OAuth callback (Google appended ?code=... or ?error=...)
    if "error" in qp:
        return HTMLResponse(f"<h2>Authorization error</h2><p>{html.escape(qp['error'])}</p>",
                            status_code=400)
    if "code" in qp:
        try:
            tok = oauth_web.exchange_code(qp["code"], redirect_uri)
        except Exception as e:  # noqa: BLE001
            return HTMLResponse(f"<h2>Token exchange failed</h2><pre>{html.escape(str(e))}</pre>",
                                status_code=400)
        refresh = tok.get("refresh_token")
        if not refresh:
            return HTMLResponse(
                "<h2>No refresh token returned</h2><p>Revoke prior access at "
                "<a href='https://myaccount.google.com/permissions'>Google permissions</a> "
                "and try again.</p>", status_code=400)
        return HTMLResponse(
            "<h2>✅ Authorized</h2><p>Add this to your Vercel project's "
            "Environment Variables as <code>GOOGLE_REFRESH_TOKEN</code>, then redeploy:</p>"
            f"<textarea rows='4' style='width:100%;font-family:monospace'>{html.escape(refresh)}</textarea>"
            "<p>After redeploy, POST a website to this app to generate a Google Doc.</p>")

    # OAuth start
    if path.rstrip("/").endswith("oauth/start") or "login" in qp or "connect" in qp:
        return RedirectResponse(oauth_web.build_auth_url(redirect_uri))

    return JSONResponse(_health())


@app.post("/{path:path}")
async def post_audit(path: str, req: AuditRequest):
    try:
        config.require_qwen()
        config.require_google()
        mode = req.mode if req.mode in ("lite", "full") else "lite"
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor, lambda: run_native(req.website, mode))
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
