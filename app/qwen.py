"""Thin wrapper around the Qwen (Alibaba Model Studio) OpenAI-compatible API."""
from __future__ import annotations

import json
import re
from typing import Optional

from openai import OpenAI

from . import config


def _client() -> OpenAI:
    config.require_qwen()
    return OpenAI(api_key=config.QWEN_API_KEY, base_url=config.QWEN_BASE_URL)


def chat_json(system: str, user: str, *, max_tokens: int = 8000,
              temperature: float = 0.6, model: Optional[str] = None) -> dict:
    """Call the model and parse a single JSON object out of the reply.

    qwen3.7-max is a thinking model: its reasoning goes to `reasoning_content`
    and the user-facing answer to `content`, so `content` is usually clean JSON.
    We still strip code fences / surrounding prose defensively.
    """
    client = _client()
    resp = client.chat.completions.create(
        model=model or config.QWEN_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    content = resp.choices[0].message.content or ""
    return _extract_json(content)


def _extract_json(text: str) -> dict:
    text = text.strip()
    # Strip ```json ... ``` fences if present.
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    # Fast path.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Fall back to the first balanced { ... } block.
    start = text.find("{")
    if start == -1:
        raise ValueError("Model returned no JSON object:\n" + text[:1000])
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    raise ValueError("Could not parse JSON from model output:\n" + text[:1000])
