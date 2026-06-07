"""Central configuration, loaded from environment / .env."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# ---- Qwen (Alibaba Model Studio, OpenAI-compatible) ----
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")
QWEN_BASE_URL = os.getenv(
    "QWEN_BASE_URL",
    "https://ws-ehgi71swnl3l8e0i.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1",
)
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen3.7-max")

# ---- Google OAuth (user account / personal Gmail) ----
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN", "")
# Exact callback URL registered on the OAuth client (web flow). If blank, the
# app derives it from the incoming request host + /api/oauth/callback.
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "")
# Scopes: create/edit docs + manage Drive file sharing for files we create.
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]

# ---- Paths ----
SKILL_DIR = BASE_DIR / "skill"
SKILL_SCRIPTS = SKILL_DIR / "scripts"
SKILL_REFS = SKILL_DIR / "references"

# On read-only hosts (Vercel), only /tmp is writable. Fall back gracefully.
import tempfile  # noqa: E402

_IS_SERVERLESS = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))
try:
    RUNS_DIR = Path(tempfile.gettempdir()) / "runs" if _IS_SERVERLESS \
        else BASE_DIR / "runs"
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    RUNS_DIR = Path(tempfile.gettempdir()) / "runs"
    RUNS_DIR.mkdir(parents=True, exist_ok=True)

# ---- Behaviour toggles ----
# Whether to fetch the live RankedTag proof case study (sendr.ai) per audit.
INCLUDE_PROOF = os.getenv("INCLUDE_PROOF", "true").lower() == "true"
# Make the resulting Google Doc world-readable (anyone with the link).
MAKE_PUBLIC = os.getenv("MAKE_PUBLIC", "true").lower() == "true"
# How much homepage HTML (chars) to hand the model.
MAX_HTML_CHARS = int(os.getenv("MAX_HTML_CHARS", "60000"))


def require_qwen() -> None:
    if not QWEN_API_KEY:
        raise RuntimeError("QWEN_API_KEY is not set. Add it to .env.")


def require_google() -> None:
    missing = [
        name
        for name, val in {
            "GOOGLE_CLIENT_ID": GOOGLE_CLIENT_ID,
            "GOOGLE_CLIENT_SECRET": GOOGLE_CLIENT_SECRET,
            "GOOGLE_REFRESH_TOKEN": GOOGLE_REFRESH_TOKEN,
        }.items()
        if not val
    ]
    if missing:
        raise RuntimeError(
            "Missing Google OAuth config: "
            + ", ".join(missing)
            + ". Run `python setup_oauth.py` once to generate the refresh token."
        )
