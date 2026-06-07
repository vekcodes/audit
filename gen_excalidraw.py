#!/usr/bin/env python3
"""Generate architecture.excalidraw (importable at excalidraw.com)."""
import json

elements = []
_seed = [1000]


def _n():
    _seed[0] += 1
    return _seed[0]


def rect(eid, x, y, w, h, bg="#ffffff", stroke="#1e1e1e", sw=2):
    elements.append({
        "id": eid, "type": "rectangle", "x": x, "y": y, "width": w, "height": h,
        "angle": 0, "strokeColor": stroke, "backgroundColor": bg,
        "fillStyle": "solid", "strokeWidth": sw, "strokeStyle": "solid",
        "roughness": 1, "opacity": 100, "groupIds": [], "frameId": None,
        "roundness": {"type": 3}, "seed": _n(), "version": 1,
        "versionNonce": _n(), "isDeleted": False, "boundElements": [],
        "updated": 1, "link": None, "locked": False,
    })


def text(eid, x, y, s, size=16, color="#1e1e1e", w=None, align="left"):
    lines = s.split("\n")
    width = w or max(len(ln) for ln in lines) * size * 0.55
    height = len(lines) * size * 1.25
    elements.append({
        "id": eid, "type": "text", "x": x, "y": y, "width": width,
        "height": height, "angle": 0, "strokeColor": color,
        "backgroundColor": "transparent", "fillStyle": "solid",
        "strokeWidth": 2, "strokeStyle": "solid", "roughness": 1,
        "opacity": 100, "groupIds": [], "frameId": None, "roundness": None,
        "seed": _n(), "version": 1, "versionNonce": _n(), "isDeleted": False,
        "boundElements": [], "updated": 1, "link": None, "locked": False,
        "text": s, "fontSize": size, "fontFamily": 1, "textAlign": align,
        "verticalAlign": "top", "baseline": int(size * 0.85),
        "containerId": None, "originalText": s, "lineHeight": 1.25,
    })


def arrow(eid, x1, y1, x2, y2, color="#1e1e1e", sw=2, dashed=False):
    elements.append({
        "id": eid, "type": "arrow", "x": x1, "y": y1,
        "width": abs(x2 - x1), "height": abs(y2 - y1), "angle": 0,
        "strokeColor": color, "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": sw,
        "strokeStyle": "dashed" if dashed else "solid", "roughness": 1,
        "opacity": 100, "groupIds": [], "frameId": None,
        "roundness": {"type": 2}, "seed": _n(), "version": 1,
        "versionNonce": _n(), "isDeleted": False, "boundElements": [],
        "updated": 1, "link": None, "locked": False,
        "points": [[0, 0], [x2 - x1, y2 - y1]], "lastCommittedPoint": None,
        "startBinding": None, "endBinding": None,
        "startArrowhead": None, "endArrowhead": "arrow",
    })


# ---- title ----
text("title", 60, 30, "RankedTag SEO Audit API  —  Architecture", 28, "#1971c2")
text("sub", 60, 70,
     "website  ->  Qwen audit  ->  public Google Doc   (Vercel serverless, "
     "rate-limited & cached)", 14, "#868e96")

# ---- Clay ----
rect("clay", 60, 300, 210, 120, "#a5d8ff")
text("clay_t", 80, 320, "CLAY\n\n600 rows\n~80 calls / min", 16)

# ---- Vercel container ----
rect("vercel", 360, 130, 400, 520, "#f1f3f5", "#adb5bd", 2)
text("vercel_t", 378, 142, "VERCEL  —  Python serverless (FastAPI)", 16, "#495057")

# handler
rect("handler", 386, 185, 348, 250, "#ffffff")
text("handler_t", 400, 196,
     "POST /api/audit  { website, mode }\n\n"
     "1.  cache hit?  -> return URL instantly\n"
     "2.  acquire per-URL lock (dedup)\n"
     "3.  WAIT for a rate slot (<=30s)\n"
     "4.  fetch site signals\n"
     "5.  Qwen lite audit -> scores+findings\n"
     "6.  build native Google Doc\n"
     "7.  share public + cache result\n"
     "8.  return { public_url, scores }", 13)

# oauth
rect("oauth", 386, 450, 348, 55, "#fff3bf")
text("oauth_t", 400, 460,
     "GET /api/oauth/start  ->  /callback\n(one-time consent -> refresh token)", 12)

# builder
rect("builder", 386, 520, 348, 60, "#e9ecef")
text("builder_t", 400, 530,
     "Native Doc builder (NO browser):\nbands, callouts, monospace score bars", 12)

text("note_writes", 386, 595,
     "~2 Google write calls per audit", 12, "#868e96")

# ---- Upstash Redis ----
rect("redis", 830, 150, 240, 150, "#ffc9c9")
text("redis_t", 848, 162,
     "UPSTASH REDIS\n\n- rate limiter (25/min,\n  sliding window)\n"
     "- result cache (7d,\n  idempotent)\n- per-URL dedup lock", 13)

# ---- Qwen ----
rect("qwen", 830, 330, 240, 95, "#ffec99")
text("qwen_t", 848, 345,
     "QWEN MaaS (Alibaba)\nqwen-flash (lite) /\nqwen3.7-max (full)\n"
     "the audit brain", 13)

# ---- Google ----
rect("google", 830, 455, 240, 95, "#b2f2bb")
text("google_t", 848, 470,
     "GOOGLE APIs\nDocs API (create/format)\nDrive API (share public)\n"
     "+ retry/backoff on 429", 12)

# ---- Public Doc ----
rect("doc", 830, 585, 240, 70, "#d3f9d8", "#2f9e44", 2)
text("doc_t", 848, 600, "PUBLIC GOOGLE DOC\n(anyone with the link)", 14, "#2b8a3e")

# ---- arrows ----
arrow("a_clay", 270, 350, 386, 300)          # Clay -> handler
text("a_clay_t", 250, 250, "POST {website}", 12, "#1971c2")
arrow("a_ret", 386, 410, 270, 400, "#2f9e44")  # handler -> Clay (return)
text("a_ret_t", 250, 430, "200 { public_url }", 12, "#2f9e44")
text("a_429", 60, 440,
     "429 = 'retry' (not failure);\nClay retries, cache makes it free", 11, "#e8590c")

arrow("a_redis", 734, 250, 830, 225)         # handler <-> redis
arrow("a_redis2", 830, 245, 734, 280, "#c92a2a")
arrow("a_qwen", 734, 320, 830, 370)          # handler -> qwen
arrow("a_google", 734, 360, 830, 500)        # handler -> google
arrow("a_doc", 950, 550, 950, 585, "#2f9e44")  # google -> doc

# ---- scaling note ----
rect("scale", 360, 680, 710, 60, "#fff9db", "#f08c00", 2)
text("scale_t", 376, 690,
     "SCALING:  Google cap ~25-30 audits/min.  To run Clay's 80/min in real time:"
     "  request a Docs write-quota increase, then set RATE_LIMIT_PER_MIN=80.", 12,
     "#e67700")

doc = {
    "type": "excalidraw",
    "version": 2,
    "source": "https://excalidraw.com",
    "elements": elements,
    "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
    "files": {},
}

with open("architecture.excalidraw", "w", encoding="utf-8") as f:
    json.dump(doc, f, indent=2)
print("wrote architecture.excalidraw with", len(elements), "elements")
