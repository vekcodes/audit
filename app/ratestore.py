"""Upstash Redis-backed rate limiter + result cache + per-URL dedup lock.

Lets a fast caller (Clay ~80/min) hit the API while we pace the actual Google
Docs work under the 60-writes/min quota:

  - acquire_slot():  global sliding-window limiter (default 25 audits/min)
  - acquire_lock()/release_lock():  one in-flight audit per URL (no duplicates)
  - get_cached()/set_cached():  return a previously built doc instantly (idempotent)

Reads credentials from the env vars set by Vercel's Upstash/KV integration
(UPSTASH_REDIS_REST_URL/TOKEN or KV_REST_API_URL/TOKEN). If none are present, all
calls are no-ops that ALLOW the request — so the app still works without Redis
(just without pacing). Every Redis error also fails open (never blocks an audit).
"""
from __future__ import annotations

import json
import os
import random
import time

import httpx

REDIS_URL = (os.getenv("UPSTASH_REDIS_REST_URL")
             or os.getenv("KV_REST_API_URL") or "").rstrip("/")
REDIS_TOKEN = (os.getenv("UPSTASH_REDIS_REST_TOKEN")
               or os.getenv("KV_REST_API_TOKEN") or "")
RATE_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "25"))
CACHE_TTL = int(os.getenv("RESULT_CACHE_TTL", str(7 * 24 * 3600)))
LOCK_TTL = int(os.getenv("AUDIT_LOCK_TTL", "120"))
WINDOW_MS = 60_000

ENABLED = bool(REDIS_URL and REDIS_TOKEN)


def _pipeline(commands):
    """Run an array of Redis commands via the Upstash REST pipeline endpoint."""
    r = httpx.post(
        REDIS_URL + "/pipeline",
        headers={"Authorization": f"Bearer {REDIS_TOKEN}"},
        json=commands,
        timeout=15,
    )
    r.raise_for_status()
    return [row.get("result") for row in r.json()]


def _cmd(*args):
    return _pipeline([[str(a) for a in args]])[0]


# ---------------------------------------------------------------- cache
def get_cached(url: str):
    if not ENABLED:
        return None
    try:
        v = _cmd("GET", f"audit:{url}")
        return json.loads(v) if v else None
    except Exception:
        return None


def set_cached(url: str, data: dict):
    if not ENABLED:
        return
    try:
        _cmd("SET", f"audit:{url}", json.dumps(data), "EX", CACHE_TTL)
    except Exception:
        pass


# ---------------------------------------------------------------- per-URL lock
def acquire_lock(url: str) -> bool:
    if not ENABLED:
        return True
    try:
        return _cmd("SET", f"lock:{url}", "1", "NX", "EX", LOCK_TTL) == "OK"
    except Exception:
        return True  # fail open


def release_lock(url: str):
    if not ENABLED:
        return
    try:
        _cmd("DEL", f"lock:{url}")
    except Exception:
        pass


# ---------------------------------------------------------------- rate limiter
def acquire_slot() -> bool:
    """Sliding-window limiter over a sorted set. True if a slot was available."""
    if not ENABLED:
        return True
    now = int(time.time() * 1000)
    member = f"{now}-{random.randint(0, 1_000_000)}"
    try:
        res = _pipeline([
            ["ZREMRANGEBYSCORE", "rl:docs", "0", str(now - WINDOW_MS)],
            ["ZADD", "rl:docs", str(now), member],
            ["ZCARD", "rl:docs"],
            ["EXPIRE", "rl:docs", "120"],
        ])
        count = res[2]
        if isinstance(count, int) and count > RATE_PER_MIN:
            _cmd("ZREM", "rl:docs", member)  # over limit — give the slot back
            return False
        return True
    except Exception:
        return True  # fail open


def status() -> dict:
    return {"redis_enabled": ENABLED, "rate_limit_per_min": RATE_PER_MIN}
