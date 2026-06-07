"""Web OAuth helpers for the deployed (Vercel) app.

Lets you authorize once by visiting the live app — no localhost, no loopback.
The callback exchanges the code and shows the refresh token to paste into the
host's env vars.
"""
from __future__ import annotations

from urllib.parse import urlencode

import httpx

from . import config

AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"
SCOPES = ("https://www.googleapis.com/auth/documents "
          "https://www.googleapis.com/auth/drive")


def build_auth_url(redirect_uri: str, state: str = "rt-audit") -> str:
    params = {
        "response_type": "code",
        "client_id": config.GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    return AUTH_URI + "?" + urlencode(params)


def exchange_code(code: str, redirect_uri: str) -> dict:
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": config.GOOGLE_CLIENT_ID,
        "client_secret": config.GOOGLE_CLIENT_SECRET,
        "redirect_uri": redirect_uri,
    }
    r = httpx.post(TOKEN_URI, data=data, timeout=30)
    r.raise_for_status()
    return r.json()
