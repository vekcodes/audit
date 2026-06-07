"""Batch pipeline: many websites -> one Qwen batch job -> lite audit results.

Uses the OpenAI-compatible Batch API exposed by the Qwen MaaS endpoint
(/v1/files + /v1/batches). One JSONL line per site, ~1k tokens each.
"""
from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from openai import OpenAI

from . import config
from .fetcher import SiteData, fetch_site
from .lite import LITE_SYS, build_user


def _client() -> OpenAI:
    config.require_qwen()
    return OpenAI(api_key=config.QWEN_API_KEY, base_url=config.QWEN_BASE_URL)


# ---------------------------------------------------------------- fetch
def fetch_many(urls: List[str], max_workers: int = 16
               ) -> Tuple[Dict[str, SiteData], Dict[str, str]]:
    """Fetch many sites in parallel. Returns ({url: SiteData}, {url: error})."""
    ok: Dict[str, SiteData] = {}
    err: Dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(fetch_site, u): u for u in urls}
        for fut in as_completed(futs):
            u = futs[fut]
            try:
                ok[u] = fut.result()
            except Exception as e:  # noqa: BLE001
                err[u] = f"{type(e).__name__}: {e}"
    return ok, err


# ---------------------------------------------------------------- build
def build_jsonl(sites: Dict[str, SiteData], out_path: Path,
                model: Optional[str] = None, max_tokens: int = 1100
                ) -> Dict[str, str]:
    """Write one batch request per site. Returns {custom_id: url} mapping."""
    model = model or "qwen-flash"
    mapping: Dict[str, str] = {}
    with out_path.open("w", encoding="utf-8") as f:
        for i, (url, site) in enumerate(sites.items()):
            cid = f"site-{i:04d}"
            mapping[cid] = url
            line = {
                "custom_id": cid,
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": LITE_SYS},
                        {"role": "user", "content": build_user(site)},
                    ],
                    "temperature": 0.4,
                    "max_tokens": max_tokens,
                    "enable_thinking": False,
                },
            }
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    return mapping


# ---------------------------------------------------------------- submit
def build_jsonl_summaries(summaries: Dict[str, str], out_path: Path,
                          model: Optional[str] = None, max_tokens: int = 1600
                          ) -> Dict[str, str]:
    """Like build_jsonl but from persisted {url: signals-summary} (resumable)."""
    model = model or "qwen-flash"
    mapping: Dict[str, str] = {}
    with out_path.open("w", encoding="utf-8") as f:
        for i, (url, summary) in enumerate(summaries.items()):
            cid = f"site-{i:04d}"
            mapping[cid] = url
            line = {
                "custom_id": cid,
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": LITE_SYS},
                        {"role": "user", "content": "SIGNALS:\n" + summary},
                    ],
                    "temperature": 0.4,
                    "max_tokens": max_tokens,
                    "enable_thinking": False,
                },
            }
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    return mapping


def submit(jsonl_path: Path) -> str:
    c = _client()
    up = c.files.create(file=open(jsonl_path, "rb"), purpose="batch")
    batch = c.batches.create(
        input_file_id=up.id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
    )
    return batch.id


def status(batch_id: str):
    return _client().batches.retrieve(batch_id)


def poll(batch_id: str, *, interval: int = 20, timeout: int = 86400,
         on_tick=None):
    """Block until the batch reaches a terminal state or timeout."""
    c = _client()
    start = time.time()
    terminal = {"completed", "failed", "expired", "cancelled"}
    while True:
        b = c.batches.retrieve(batch_id)
        if on_tick:
            on_tick(b)
        if b.status in terminal:
            return b
        if time.time() - start > timeout:
            return b
        time.sleep(interval)


# ---------------------------------------------------------------- results
def fetch_results(batch) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Download output + error files. Returns ({custom_id: content}, {cid: err})."""
    c = _client()
    contents: Dict[str, str] = {}
    errors: Dict[str, str] = {}
    if getattr(batch, "output_file_id", None):
        text = c.files.content(batch.output_file_id).text
        for line in text.splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            cid = obj.get("custom_id", "")
            resp = (obj.get("response") or {}).get("body") or {}
            try:
                contents[cid] = resp["choices"][0]["message"]["content"]
            except Exception:
                errors[cid] = json.dumps(obj.get("error") or resp)[:500]
    if getattr(batch, "error_file_id", None):
        try:
            text = c.files.content(batch.error_file_id).text
            for line in text.splitlines():
                if not line.strip():
                    continue
                obj = json.loads(line)
                errors[obj.get("custom_id", "")] = json.dumps(
                    obj.get("error") or obj)[:500]
        except Exception:
            pass
    return contents, errors
