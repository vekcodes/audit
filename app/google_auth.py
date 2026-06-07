"""Build authenticated Google API clients from a stored OAuth refresh token."""
from __future__ import annotations

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from . import config


def _credentials() -> Credentials:
    config.require_google()
    creds = Credentials(
        token=None,
        refresh_token=config.GOOGLE_REFRESH_TOKEN,
        client_id=config.GOOGLE_CLIENT_ID,
        client_secret=config.GOOGLE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=config.GOOGLE_SCOPES,
    )
    creds.refresh(Request())
    return creds


def docs_service():
    return build("docs", "v1", credentials=_credentials(), cache_discovery=False)


def drive_service():
    return build("drive", "v3", credentials=_credentials(), cache_discovery=False)
