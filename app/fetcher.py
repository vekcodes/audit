"""Fetch a website and extract the signals the audit needs.

Mirrors Step 1 of the skill methodology: grab the homepage HTML, inspect the
<head> and markup, and surface concrete signals (title, meta, schema types,
headings, robots/sitemap hints) so the model audits real data, not guesses.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from . import config

UA = "Mozilla/5.0 (compatible; RankedTagAudit/1.0; +https://rankedtag.com)"


@dataclass
class SiteData:
    url: str
    final_url: str
    status: int
    title: str = ""
    meta_description: str = ""
    meta_desc_len: int = 0
    canonical: str = ""
    og_tags: dict = field(default_factory=dict)
    h1: List[str] = field(default_factory=list)
    h2: List[str] = field(default_factory=list)
    schema_types: List[str] = field(default_factory=list)
    has_schema: bool = False
    nav_labels: List[str] = field(default_factory=list)
    img_count: int = 0
    img_missing_alt: int = 0
    word_count: int = 0
    robots_txt: Optional[str] = None
    has_sitemap: bool = False
    has_llms_txt: bool = False
    https: bool = False
    raw_html: str = ""

    def summary(self) -> str:
        """Compact, human-readable signal sheet for the prompt."""
        lines = [
            f"URL: {self.url}",
            f"Final URL: {self.final_url}  (HTTP {self.status}, HTTPS={self.https})",
            f"Title ({len(self.title)} chars): {self.title!r}",
            f"Meta description ({self.meta_desc_len} chars): {self.meta_description!r}",
            f"Canonical: {self.canonical or '(none)'}",
            f"OG tags: {json.dumps(self.og_tags, ensure_ascii=False)}",
            f"H1 ({len(self.h1)}): {self.h1[:6]}",
            f"H2 ({len(self.h2)}): {self.h2[:12]}",
            f"Schema/structured-data present: {self.has_schema}; types: {self.schema_types or '(none detected)'}",
            f"Nav labels: {self.nav_labels[:20]}",
            f"Images: {self.img_count} total, {self.img_missing_alt} missing alt text",
            f"Approx word count (homepage): {self.word_count}",
            f"robots.txt: {'present' if self.robots_txt else 'missing/unreachable'}; "
            f"sitemap referenced: {self.has_sitemap}; llms.txt: {self.has_llms_txt}",
        ]
        return "\n".join(lines)


def _abs(base: str, path: str) -> str:
    return urljoin(base, path)


def fetch_site(url: str) -> SiteData:
    if not re.match(r"^https?://", url):
        url = "https://" + url
    with httpx.Client(
        follow_redirects=True,
        timeout=30.0,
        headers={"User-Agent": UA},
    ) as client:
        resp = client.get(url)
        html = resp.text
        final_url = str(resp.url)
        data = SiteData(
            url=url,
            final_url=final_url,
            status=resp.status_code,
            https=final_url.startswith("https://"),
            raw_html=html[: config.MAX_HTML_CHARS],
        )
        _parse_html(data, html, final_url)
        _fetch_aux(client, final_url, data)
    return data


def _parse_html(data: SiteData, html: str, base: str) -> None:
    soup = BeautifulSoup(html, "lxml")

    if soup.title and soup.title.string:
        data.title = soup.title.string.strip()

    md = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
    if md and md.get("content"):
        data.meta_description = md["content"].strip()
        data.meta_desc_len = len(data.meta_description)

    canon = soup.find("link", attrs={"rel": re.compile("canonical", re.I)})
    if canon and canon.get("href"):
        data.canonical = canon["href"].strip()

    for og in soup.find_all("meta", attrs={"property": re.compile("^og:", re.I)}):
        if og.get("content"):
            data.og_tags[og["property"]] = og["content"].strip()

    data.h1 = [h.get_text(" ", strip=True) for h in soup.find_all("h1")][:10]
    data.h2 = [h.get_text(" ", strip=True) for h in soup.find_all("h2")][:20]

    # JSON-LD + microdata schema detection.
    types: List[str] = []
    for tag in soup.find_all("script", attrs={"type": re.compile("ld\\+json", re.I)}):
        try:
            payload = json.loads(tag.string or "{}")
        except Exception:
            # Sometimes multiple objects / trailing commas; grab @type strings.
            types += re.findall(r'"@type"\s*:\s*"([^"]+)"', tag.string or "")
            continue
        types += _collect_types(payload)
    for el in soup.find_all(attrs={"itemtype": True}):
        t = el["itemtype"].rstrip("/").split("/")[-1]
        if t:
            types.append(t)
    data.schema_types = sorted(set(t for t in types if t))
    data.has_schema = bool(data.schema_types)

    nav = soup.find("nav")
    if nav:
        data.nav_labels = [
            a.get_text(" ", strip=True)
            for a in nav.find_all("a")
            if a.get_text(strip=True)
        ][:30]

    imgs = soup.find_all("img")
    data.img_count = len(imgs)
    data.img_missing_alt = sum(1 for i in imgs if not (i.get("alt") or "").strip())

    text = soup.get_text(" ", strip=True)
    data.word_count = len(text.split())


def _collect_types(obj) -> List[str]:
    out: List[str] = []
    if isinstance(obj, dict):
        t = obj.get("@type")
        if isinstance(t, str):
            out.append(t)
        elif isinstance(t, list):
            out += [x for x in t if isinstance(x, str)]
        for v in obj.values():
            out += _collect_types(v)
    elif isinstance(obj, list):
        for v in obj:
            out += _collect_types(v)
    return out


def _fetch_aux(client: httpx.Client, base: str, data: SiteData) -> None:
    root = f"{urlparse(base).scheme}://{urlparse(base).netloc}"
    try:
        r = client.get(_abs(root, "/robots.txt"))
        if r.status_code == 200 and r.text:
            data.robots_txt = r.text[:4000]
            data.has_sitemap = "sitemap:" in r.text.lower()
    except Exception:
        pass
    try:
        r = client.get(_abs(root, "/llms.txt"))
        data.has_llms_txt = r.status_code == 200 and len(r.text) > 0
    except Exception:
        pass
    if not data.has_sitemap:
        try:
            r = client.get(_abs(root, "/sitemap.xml"))
            data.has_sitemap = r.status_code == 200 and "<urlset" in r.text.lower() or "<sitemapindex" in r.text.lower()
        except Exception:
            pass
