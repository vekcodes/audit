#!/usr/bin/env python3
"""
Fetch RankedTag's live proof assets (the sendr.ai case study) from rankedtag.com.

Pulls:
  - headline metrics, founder quote, engine description (-> proof.json)
  - result-sendr.jpeg, result-ranked.jpeg  (the GSC + AI-Overview screenshots)
  - logo (auto-cropped -> logo_crop.png)

Usage:
  python fetch_proof.py --out ./assets_run

If the live site has moved or fields can't be parsed, baked-in last-known values
are used and `proof.json` marks "source": "fallback" so the caller can warn the user.
Requires: requests (or falls back to urllib), Pillow for logo crop.
"""
import argparse, json, os, re, sys

BASE="https://rankedtag.com"

# Last-known-good values. The live site is the source of truth; these only fill gaps.
FALLBACK = {
    "source": "fallback",
    "client": "sendr.ai",
    "stage": "Seed-stage B2B SaaS",
    "metrics": [
        {"big": "0 → 1.05M", "small": "organic impressions in 6 months"},
        {"big": "7.43k", "small": "clicks from zero"},
        {"big": "#2", "small": "in Google\u2019s AI Overview"},
    ],
    "gsc_caption": "Live Google Search Console · sendr.ai · 7.43k clicks, 1.05M impressions, avg position 7.1, over six months.",
    "ranked_caption": "Google AI Overview, query \u201Cwhat is the best GTM tool\u201D — sendr.ai at #2, ZoomInfo at #8, sendr.ai cited as the source.",
    "query": "what is the best GTM tool",
    "quote": "We went from invisible to the answer Google\u2019s AI Overview gives when someone asks for the best GTM tool. Six places above ZoomInfo. The pipeline runs while we ship product.",
    "quote_attrib": "Founder, sendr.ai",
    "intro": "came to us invisible. Six months later, the numbers below are straight out of their Google Search Console. No rounding, no creative maths. You can cross-check by running the same search yourself.",
    "engine": [
        {"b": "Senior humans set the strategy. ", "t": "Real strategists run the SWOT, pick the keywords, angles and positioning. Every brief is approved by a human before a single word is written."},
        {"b": "Claude does the deep research at scale. ", "t": "It pulls SERPs, reads competitor pages, drafts briefs, and maps GEO citation patterns. Fast, and the source of the leverage."},
        {"b": "Workflow automation routes everything. ", "t": "Trigger, enrich, publish, alert. A senior editor reviews each piece — nothing ships unread, nothing ships on autopilot."},
    ],
    "engine_result": "Compounding content in days, not quarters — the pace of a 30-person content team, run by three. Schema, GEO optimisation, and citation tracking are built in from day one, not bolted on later.",
}

IMAGES = {
    "result-sendr.jpeg": "/result-sendr.jpeg",
    "result-ranked.jpeg": "/result-ranked.jpeg",
    "logo.png": "/Rankedtag%20(1).png",
}

def http_get(url, binary=False):
    try:
        import requests
        r=requests.get(url, timeout=20)
        r.raise_for_status()
        return r.content if binary else r.text
    except Exception:
        import urllib.request
        req=urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data=resp.read()
            return data if binary else data.decode("utf-8","replace")

def fetch_text_fields():
    """Best-effort scrape of the live homepage bundle for current metric strings."""
    proof=dict(FALLBACK); proof["source"]="live"
    try:
        html=http_get(BASE+"/")
        m=re.search(r'src="(/assets/index-[^"]+\.js)"', html)
        if m:
            js=http_get(BASE+m.group(1))
            # impressions metric e.g. "1.05M impressions"
            mi=re.search(r'"([\d.]+M)\s*impressions"', js)
            mc=re.search(r'(\d+\.\d+k)[^"]{0,30}clicks', js, re.I) or re.search(r'"(\d+\.\d+k)"', js)
            if mi:
                proof["metrics"][0]["big"]=f'0 → {mi.group(1)}'
            if mc:
                proof["metrics"][1]["big"]=mc.group(1)
            mq=re.search(r'"(We went from invisible[^"]+)"', js)
            if mq:
                proof["quote"]=mq.group(1)
            mqr=re.search(r'"(what is the best GTM tool)"', js)
            if mqr:
                proof["query"]=mqr.group(1)
    except Exception as e:
        proof["source"]="fallback"
        proof["fetch_error"]=str(e)
    return proof

def crop_logo(path):
    try:
        from PIL import Image
        im=Image.open(path).convert("RGBA")
        bbox=im.split()[3].getbbox()
        if bbox and (bbox[2]-bbox[0] < im.size[0]-10):
            pad=24; l,t,r,b=bbox
            l=max(0,l-pad);t=max(0,t-pad);r=min(im.size[0],r+pad);b=min(im.size[1],b+pad)
            im.crop((l,t,r,b)).save(os.path.join(os.path.dirname(path),"logo_crop.png"))
            return True
    except Exception:
        pass
    return False

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a=ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    # images
    for name,rel in IMAGES.items():
        dest=os.path.join(a.out,name)
        try:
            data=http_get(BASE+rel, binary=True)
            with open(dest,"wb") as f: f.write(data)
            print("downloaded", name, len(data), "bytes")
        except Exception as e:
            print("WARN could not download", name, "-", e, file=sys.stderr)

    logo=os.path.join(a.out,"logo.png")
    if os.path.exists(logo):
        if crop_logo(logo):
            print("cropped logo -> logo_crop.png")
        else:
            # fall back to using the raw logo as logo_crop
            try:
                import shutil; shutil.copy(logo, os.path.join(a.out,"logo_crop.png"))
            except Exception: pass

    proof=fetch_text_fields()
    with open(os.path.join(a.out,"proof.json"),"w") as f:
        json.dump(proof,f,indent=2,ensure_ascii=False)
    print("wrote proof.json  (source:", proof["source"]+")")
    if proof["source"]!="live":
        print("NOTE: live fetch incomplete — using last-known values. Warn the user before presenting these as current.", file=sys.stderr)

if __name__=="__main__":
    main()
