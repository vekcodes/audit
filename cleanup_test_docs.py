#!/usr/bin/env python3
"""Trash the audit docs + uploaded asset images created during testing.

Safe: it moves files to Drive Trash (recoverable ~30 days), and only touches
files named like the audit deliverable / our uploaded assets.

Usage:
  python cleanup_test_docs.py            # dry run (lists what it would trash)
  python cleanup_test_docs.py --yes      # actually trash them
"""
import sys

from app import google_auth

DRY = "--yes" not in sys.argv
drive = google_auth.drive_service()

queries = [
    "name contains 'SEO & AI-Search Audit' and mimeType='application/vnd.google-apps.document' and trashed=false",
    "name contains 'rt-audit-asset' and trashed=false",
]

found = []
for q in queries:
    page = None
    while True:
        resp = drive.files().list(q=q, fields="nextPageToken, files(id,name)",
                                  pageSize=100, pageToken=page).execute()
        found += resp.get("files", [])
        page = resp.get("nextPageToken")
        if not page:
            break

print(f"{'[DRY RUN] would trash' if DRY else 'trashing'} {len(found)} files")
for f in found:
    print("  -", f["name"], f["id"])
    if not DRY:
        drive.files().update(fileId=f["id"], body={"trashed": True}).execute()

if DRY:
    print("\nRe-run with --yes to actually trash them.")
