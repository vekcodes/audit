"""Vercel Python entrypoint — exposes the ASGI app for the @vercel/python runtime."""
import sys
from pathlib import Path

# Ensure the project root is importable when Vercel runs this file from /api.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.vercel_app import app  # noqa: E402

# Vercel's Python runtime serves a module-level ASGI `app`.
