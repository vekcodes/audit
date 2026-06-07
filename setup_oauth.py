#!/usr/bin/env python3
"""One-time helper: obtain a Google OAuth refresh token for the audit API.

Prereqs (Google Cloud Console, free):
  1. Create / pick a project.
  2. Enable the **Google Docs API** and **Google Drive API**.
  3. Configure the OAuth consent screen (External; add your Gmail as a Test user).
  4. Create an OAuth client of type **Desktop app**. Note the client ID + secret.

Run:
  python setup_oauth.py --client-id XXXX --client-secret YYYY

A browser window opens for one-time consent. The script prints the
GOOGLE_REFRESH_TOKEN (and the client id/secret) to paste into your .env.
"""
from __future__ import annotations

import argparse

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--client-id", required=True)
    ap.add_argument("--client-secret", required=True)
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()

    client_config = {
        "installed": {
            "client_id": a.client_id,
            "client_secret": a.client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=a.port, prompt="consent",
                                  access_type="offline")

    if not creds.refresh_token:
        print("\nNo refresh token returned. Revoke prior access at "
              "https://myaccount.google.com/permissions and re-run.")
        return

    print("\n" + "=" * 64)
    print("Add these to your .env file:\n")
    print(f"GOOGLE_CLIENT_ID={a.client_id}")
    print(f"GOOGLE_CLIENT_SECRET={a.client_secret}")
    print(f"GOOGLE_REFRESH_TOKEN={creds.refresh_token}")
    print("=" * 64)


if __name__ == "__main__":
    main()
