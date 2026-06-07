#!/usr/bin/env python3
"""Drive the full 600-site batch: URLs -> lite audits -> public Google Docs.

Resumable & checkpointed. Each phase writes to a run directory so a crash,
rate-limit, or 24h batch wait can be resumed by re-running the same command.

Usage:
  # 1. put one URL per line in urls.txt, then:
  python run_batch.py --urls urls.txt --name run1

  # phases run in order; re-run the same command to resume from where it stopped.
  # control individual phases:
  python run_batch.py --urls urls.txt --name run1 --phase fetch
  python run_batch.py --name run1 --phase submit
  python run_batch.py --name run1 --phase collect
  python run_batch.py --name run1 --phase docs

Phases: fetch -> submit -> collect -> scorecards -> docs  (default: all)
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

from app import batch, config, gdocs, proof as proof_mod, visuals
from app.lite import parse_lite


def log(msg: str):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_json(p: Path, default):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def save_json(p: Path, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


# ----------------------------------------------------------------- phases
def phase_fetch(run: Path, urls_file: Path):
    summ_p = run / "summaries.json"
    if summ_p.exists():
        log(f"fetch: already done ({len(load_json(summ_p, {}))} sites). skipping.")
        return
    urls = [u.strip() for u in urls_file.read_text(encoding="utf-8").splitlines()
            if u.strip() and not u.strip().startswith("#")]
    log(f"fetch: {len(urls)} URLs...")
    sites, errs = batch.fetch_many(urls)
    summaries = {u: s.summary() for u, s in sites.items()}
    save_json(summ_p, summaries)
    save_json(run / "fetch_errors.json", errs)
    log(f"fetch: {len(summaries)} ok, {len(errs)} failed "
        f"(see fetch_errors.json).")


def phase_submit(run: Path, model: str):
    bid_p = run / "batch_id.txt"
    if bid_p.exists():
        log(f"submit: batch already created ({bid_p.read_text().strip()}).")
        return
    summaries = load_json(run / "summaries.json", {})
    if not summaries:
        raise SystemExit("submit: no summaries.json — run fetch first.")
    jsonl = run / "requests.jsonl"
    mapping = batch.build_jsonl_summaries(summaries, jsonl, model=model)
    save_json(run / "mapping.json", mapping)
    log(f"submit: uploading {len(mapping)} requests...")
    bid = batch.submit(jsonl)
    bid_p.write_text(bid)
    log(f"submit: batch id {bid}")


def phase_collect(run: Path):
    results_p = run / "lite_results.json"
    if results_p.exists():
        log(f"collect: already have {len(load_json(results_p, {}))} results.")
        return
    bid = (run / "batch_id.txt").read_text().strip()
    mapping = load_json(run / "mapping.json", {})
    log(f"collect: polling batch {bid} (can take up to 24h)...")
    b = batch.poll(bid, interval=30, on_tick=lambda x: log(
        f"  status={x.status} counts={getattr(x,'request_counts',None)}"))
    log(f"collect: final status {b.status}")
    contents, errs = batch.fetch_results(b)
    parsed = {}
    perr = dict(errs)
    for cid, content in contents.items():
        url = mapping.get(cid, cid)
        try:
            parsed[url] = parse_lite(content, fallback_client=url).model_dump()
        except Exception as e:  # noqa: BLE001
            perr[cid] = f"parse: {e}"
    save_json(results_p, parsed)
    save_json(run / "collect_errors.json", perr)
    log(f"collect: {len(parsed)} parsed, {len(perr)} errors.")


def phase_scorecards(run: Path):
    results = load_json(run / "lite_results.json", {})
    assets = run / "assets"
    jobs = []
    for i, (url, r) in enumerate(results.items()):
        out = assets / f"{i:04d}"
        if (out / "viz_scorecard.png").exists():
            continue
        jobs.append((r.get("overall", 0), r.get("scores", {}), out))
    log(f"scorecards: rendering {len(jobs)} (of {len(results)})...")
    visuals.scorecard_only_batch(jobs)
    # record index->dir mapping
    idx = {url: str(assets / f"{i:04d}") for i, url in enumerate(results.keys())}
    save_json(run / "asset_dirs.json", idx)
    log("scorecards: done.")


def _proof_assets(run: Path):
    """Fetch proof once and pre-upload its images, returning (proof, uris, dir)."""
    if not config.INCLUDE_PROOF:
        return None, None, None
    pdir = run / "proof"
    proof = proof_mod.fetch_proof(pdir)
    if not proof:
        return None, None, None
    drive = gdocs.google_auth.drive_service()
    uris = {}
    for name in ("result-sendr.jpeg", "result-ranked.jpeg", "logo_crop.png"):
        p = pdir / name
        if p.exists():
            uri, _ = gdocs._upload_public_image(drive, p)
            uris[name] = uri
    return proof, uris, pdir


def _with_retry(fn, *a, tries=6, **k):
    from googleapiclient.errors import HttpError
    delay = 2
    for n in range(tries):
        try:
            return fn(*a, **k)
        except HttpError as e:
            code = getattr(e, "status_code", None) or getattr(
                getattr(e, "resp", None), "status", None)
            if int(code or 0) in (403, 429, 500, 503) and n < tries - 1:
                log(f"  rate/err {code}, backing off {delay}s...")
                time.sleep(delay)
                delay = min(delay * 2, 60)
                continue
            raise


def phase_docs(run: Path):
    config.require_google()
    results = load_json(run / "lite_results.json", {})
    asset_dirs = load_json(run / "asset_dirs.json", {})
    out_csv = run / "results.csv"
    done = {}
    if out_csv.exists():
        with out_csv.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                done[row["website"]] = row
    log(f"docs: {len(results)} sites, {len(done)} already built.")

    proof, proof_uris, proof_dir = (None, None, None)
    todo = [u for u in results if u not in done]
    if todo:
        log("docs: fetching + uploading shared proof assets once...")
        try:
            proof, proof_uris, proof_dir = _proof_assets(run)
        except Exception as e:  # noqa: BLE001
            log(f"docs: proof unavailable ({e}); continuing without it.")

    from app.lite import LiteResult
    new_rows = []
    for i, url in enumerate(todo):
        r = LiteResult.model_validate(results[url])
        assets = Path(asset_dirs.get(url, run / "assets" / f"{i:04d}"))
        # copy shared proof images into this doc's assets dir path keys
        try:
            res = _with_retry(gdocs.build_lite_doc, r,
                              proof, (proof_dir or assets), proof_uris)
            row = {"website": url, "client": r.client, "overall": r.overall,
                   "status": r.status, "public_url": res["public_url"],
                   "document_id": res["document_id"]}
            log(f"  [{len(done)+len(new_rows)+1}/{len(results)}] {url} "
                f"-> {res['public_url']}")
        except Exception as e:  # noqa: BLE001
            row = {"website": url, "client": r.client, "overall": r.overall,
                   "status": r.status, "public_url": "", "document_id": "",
                   "error": str(e)[:300]}
            log(f"  FAILED {url}: {e}")
        new_rows.append(row)
        # checkpoint every row
        _append_csv(out_csv, row)
        time.sleep(0.5)  # gentle throttle
    log(f"docs: complete. {out_csv}")


def _append_csv(path: Path, row: dict):
    fields = ["website", "client", "overall", "status", "public_url",
              "document_id", "error"]
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if not exists:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in fields})


# ----------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="run1", help="run directory name")
    ap.add_argument("--urls", help="path to urls.txt (one per line)")
    ap.add_argument("--model", default="qwen-flash")
    ap.add_argument("--phase", default="all",
                    choices=["all", "fetch", "submit", "collect",
                             "scorecards", "docs"])
    a = ap.parse_args()
    run = config.RUNS_DIR / f"batch-{a.name}"
    run.mkdir(parents=True, exist_ok=True)

    order = ["fetch", "submit", "collect", "scorecards", "docs"]
    phases = order if a.phase == "all" else [a.phase]
    for ph in phases:
        if ph == "fetch":
            if not a.urls:
                raise SystemExit("fetch needs --urls")
            phase_fetch(run, Path(a.urls))
        elif ph == "submit":
            phase_submit(run, a.model)
        elif ph == "collect":
            phase_collect(run)
        elif ph == "scorecards":
            phase_scorecards(run)
        elif ph == "docs":
            phase_docs(run)
    log("ALL DONE.")


if __name__ == "__main__":
    main()
