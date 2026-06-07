# Assets

This folder is intentionally empty in the shipped skill. The audit's runtime
assets — the four generated visuals, the live sendr.ai proof screenshots, the
cropped logo, and proof.json — are produced fresh into a working directory
(e.g. ./assets_run) by scripts/fetch_proof.py and scripts/generate_visuals.py,
then consumed by scripts/build_audit_docx.js via --assets.

Nothing needs to live here permanently; the proof is always fetched live so the
numbers and screenshots stay current.
