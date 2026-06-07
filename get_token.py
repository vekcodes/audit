#!/usr/bin/env python3
"""Robust 2-step OAuth refresh-token minter (manual code exchange, PKCE).

Avoids the loopback-server 'state mismatch' problems entirely.

Step 1 — generate the consent URL:
    python get_token.py url --client-id <ID>

  Open the printed URL, approve as your Google account. The browser will then
  try to load http://localhost:8765/?code=...  and show "can't reach this site"
  — THAT IS FINE. Copy the FULL address-bar URL.

Step 2 — exchange the code for tokens (writes them into .env):
    python get_token.py exchange --client-id <ID> --client-secret <SECRET> --response "<paste the full localhost URL>"

  (You can also pass --code <code> instead of --response.)
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import secrets
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

BASE = Path(__file__).resolve().parent
STATE_FILE = BASE / ".oauth_state.json"
ENV_FILE = BASE / ".env"
REDIRECT = "http://localhost:8765/"
SCOPES = ("https://www.googleapis.com/auth/documents "
          "https://www.googleapis.com/auth/drive")
AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"


def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def cmd_url(a):
    verifier = _b64url(secrets.token_bytes(48))
    challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
    state = secrets.token_urlsafe(16)
    STATE_FILE.write_text(json.dumps(
        {"verifier": verifier, "state": state, "client_id": a.client_id}))
    params = {
        "response_type": "code",
        "client_id": a.client_id,
        "redirect_uri": REDIRECT,
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    print("\nOpen this URL, approve, then copy the FULL localhost URL you land on:\n")
    print(AUTH_URI + "?" + urlencode(params))
    print()


def _extract_code(a) -> str:
    if a.code:
        return a.code
    if a.response:
        q = parse_qs(urlparse(a.response.strip()).query)
        if "code" in q:
            return q["code"][0]
        # maybe they pasted just the code
        if re.match(r"^[0-9A-Za-z\-_/.]+$", a.response.strip()):
            return a.response.strip()
    raise SystemExit("Provide --code or --response (the full localhost URL).")


def _write_env(client_id, client_secret, refresh_token):
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else []
    vals = {
        "GOOGLE_CLIENT_ID": client_id,
        "GOOGLE_CLIENT_SECRET": client_secret,
        "GOOGLE_REFRESH_TOKEN": refresh_token,
    }
    seen = set()
    out = []
    for ln in lines:
        m = re.match(r"^(GOOGLE_CLIENT_ID|GOOGLE_CLIENT_SECRET|GOOGLE_REFRESH_TOKEN)=",
                     ln)
        if m:
            out.append(f"{m.group(1)}={vals[m.group(1)]}")
            seen.add(m.group(1))
        else:
            out.append(ln)
    for k, v in vals.items():
        if k not in seen:
            out.append(f"{k}={v}")
    ENV_FILE.write_text("\n".join(out) + "\n", encoding="utf-8")


def cmd_exchange(a):
    code = _extract_code(a)
    st = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    verifier = st.get("verifier")
    if not verifier:
        raise SystemExit("No .oauth_state.json — run the 'url' step first.")
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": a.client_id,
        "client_secret": a.client_secret,
        "redirect_uri": REDIRECT,
        "code_verifier": verifier,
    }
    r = httpx.post(TOKEN_URI, data=data, timeout=30)
    if r.status_code != 200:
        raise SystemExit(f"Token exchange failed ({r.status_code}): {r.text}")
    tok = r.json()
    refresh = tok.get("refresh_token")
    if not refresh:
        raise SystemExit("No refresh_token returned. Revoke prior access at "
                         "https://myaccount.google.com/permissions and retry.\n"
                         + json.dumps(tok, indent=2))
    _write_env(a.client_id, a.client_secret, refresh)
    try:
        STATE_FILE.unlink()
    except OSError:
        pass
    print("\nSUCCESS - wrote GOOGLE_CLIENT_ID / SECRET / REFRESH_TOKEN to .env")
    print("GOOGLE_REFRESH_TOKEN=" + refresh)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("url")
    u.add_argument("--client-id", required=True)
    u.set_defaults(func=cmd_url)
    e = sub.add_parser("exchange")
    e.add_argument("--client-id", required=True)
    e.add_argument("--client-secret", required=True)
    e.add_argument("--code")
    e.add_argument("--response")
    e.set_defaults(func=cmd_exchange)
    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
