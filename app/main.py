"""FastAPI service: POST /audit {website} -> public Google Doc link."""
from __future__ import annotations

import traceback
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from . import config
from .pipeline import run_pipeline

app = FastAPI(
    title="RankedTag SEO Audit API",
    description="Pass a website; get a branded, public Google Doc SEO/GEO audit.",
    version="1.0.0",
)

# The pipeline is sync + blocking (network + LLM + Playwright). Run it off the
# event loop so the server stays responsive.
_executor = ThreadPoolExecutor(max_workers=2)


class AuditRequest(BaseModel):
    website: str = Field(..., examples=["https://treez.io"])
    include_proof: bool | None = None


class AuditResponse(BaseModel):
    website: str
    client: str
    overall_score: int | None = None
    status: str | None = None
    scores: dict
    public_url: str
    edit_url: str
    document_id: str
    proof_source: str | None = None
    run_dir: str


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model": config.QWEN_MODEL,
        "qwen_configured": bool(config.QWEN_API_KEY),
        "google_configured": bool(
            config.GOOGLE_CLIENT_ID
            and config.GOOGLE_CLIENT_SECRET
            and config.GOOGLE_REFRESH_TOKEN
        ),
    }


@app.post("/audit", response_model=AuditResponse)
async def audit(req: AuditRequest):
    import asyncio

    try:
        config.require_qwen()
        config.require_google()
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _executor,
            lambda: run_pipeline(req.website, include_proof=req.include_proof),
        )
        return result
    except RuntimeError as e:  # config / preconditions
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
