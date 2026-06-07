"""Build the branded RankedTag audit natively as a Google Doc and share it public.

Strategy
--------
The Docs API builds documents by inserting content at integer indexes. We use a
forward cursor (always append at the current end) tracked locally for text and
images, and refresh from a live GET around tables (whose index spans are awkward
to precompute). Images must be referenced by a publicly fetchable URI, so each
generated PNG / screenshot is uploaded to Drive, made public, and referenced by
its Drive download URL.

The heavy .docx chrome (charcoal bands, left-rule tinted callouts, zebra tables)
is reproduced as faithfully as the Docs API allows via paragraph shading,
paragraph borders, and table cell styling.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PIL import Image

from . import config, google_auth
from .models import AuditResult

# ---- palette (hex) ----
INK = "161618"; RED = "FF3B14"; RED_DK = "C8260A"; GREEN = "2D8A5C"
GREEN_DK = "1F4D3F"; AMBER = "C97A06"; PERI = "6B77E0"; MUTE = "6E6E76"
PAPER = "F4EFE7"; LINE = "E0D7C7"; WHITE = "FFFFFF"
REDTINT = "FBEAE4"; GREENTINT = "E6F1EC"; PERITINT = "EEF0FB"
PERI_LIGHT = "A6B0F0"; INK_SUB = "E6E1D8"

FONT = "Arial"
CONTENT_W_PT = 468  # 6.5in usable width on US Letter, 1in margins


def _rgb(hex_color: str) -> dict:
    h = hex_color.lstrip("#")
    return {
        "red": int(h[0:2], 16) / 255,
        "green": int(h[2:4], 16) / 255,
        "blue": int(h[4:6], 16) / 255,
    }


def _color(hex_color: str) -> dict:
    return {"color": {"rgbColor": _rgb(hex_color)}}


# ======================================================================
# Drive image hosting + sharing
# ======================================================================
def _upload_public_image(drive, path: Path) -> tuple[str, str]:
    from googleapiclient.http import MediaFileUpload

    mime = "image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    meta = {"name": f"rt-audit-asset-{path.name}"}
    media = MediaFileUpload(str(path), mimetype=mime, resumable=False)
    f = drive.files().create(body=meta, media_body=media, fields="id").execute()
    fid = f["id"]
    drive.permissions().create(
        fileId=fid, body={"role": "reader", "type": "anyone"}
    ).execute()
    return f"https://drive.google.com/uc?export=download&id={fid}", fid


# ======================================================================
# Document builder
# ======================================================================
class DocBuilder:
    def __init__(self, title: str):
        self.docs = google_auth.docs_service()
        self.drive = google_auth.drive_service()
        doc = self.docs.documents().create(body={"title": title}).execute()
        self.doc_id = doc["documentId"]
        self.cursor = self._end_index()
        self.reqs: List[dict] = []
        self._asset_ids: List[str] = []
        self._uri_cache: dict = {}

    # ---- low-level ----
    def _end_index(self) -> int:
        doc = self.docs.documents().get(documentId=self.doc_id).execute()
        return doc["body"]["content"][-1]["endIndex"] - 1

    def _flush(self):
        if self.reqs:
            self.docs.documents().batchUpdate(
                documentId=self.doc_id, body={"requests": self.reqs}
            ).execute()
            self.reqs = []

    # ---- text primitives ----
    def text(self, s: str, *, color=INK, bold=False, italic=False, size=10.5,
             link: Optional[str] = None, underline=False) -> tuple:
        """Queue an insertText at the cursor; return the (start, end) range."""
        start = self.cursor
        self.reqs.append({"insertText": {"location": {"index": start}, "text": s}})
        end = start + len(s)
        style = {
            "foregroundColor": _color(color),
            "bold": bold,
            "italic": italic,
            "underline": underline,
            "fontSize": {"magnitude": size, "unit": "PT"},
            "weightedFontFamily": {"fontFamily": FONT},
        }
        fields = "foregroundColor,bold,italic,underline,fontSize,weightedFontFamily"
        if link:
            style["link"] = {"url": link}
            fields += ",link"
        self.reqs.append({
            "updateTextStyle": {
                "range": {"startIndex": start, "endIndex": end},
                "textStyle": style,
                "fields": fields,
            }
        })
        self.cursor = end
        return start, end

    def para(self, runs: List[dict], *, align=None, space_before=0, space_after=6,
             named_style=None, shading=None, left_border=None, bullet_color=None,
             indent=None):
        """Compose a paragraph from runs (each {text,...}) and end it with \\n.

        Paragraph-level styling (alignment, shading, borders, named style) is
        applied across the whole paragraph including its terminating newline.
        """
        para_start = self.cursor
        if bullet_color:
            self.text("•  ", color=bullet_color, bold=True,
                      size=runs[0].get("size", 10.5))
        for r in runs:
            self.text(r["text"], color=r.get("color", INK), bold=r.get("bold", False),
                      italic=r.get("italic", False), size=r.get("size", 10.5),
                      link=r.get("link"), underline=r.get("underline", False))
        self.text("\n")
        para_end = self.cursor

        ps = {}
        fields = []
        if named_style:
            ps["namedStyleType"] = named_style
            fields.append("namedStyleType")
        if align:
            ps["alignment"] = align
            fields.append("alignment")
        ps["spaceAbove"] = {"magnitude": space_before, "unit": "PT"}
        ps["spaceBelow"] = {"magnitude": space_after, "unit": "PT"}
        fields += ["spaceAbove", "spaceBelow"]
        if shading:
            ps["shading"] = {"backgroundColor": _color(shading)}
            fields.append("shading")
        if left_border:
            ps["borderLeft"] = {
                "color": _color(left_border),
                "width": {"magnitude": 3, "unit": "PT"},
                "padding": {"magnitude": 8, "unit": "PT"},
                "dashStyle": "SOLID",
            }
            fields.append("borderLeft")
        if indent is not None:
            ps["indentStart"] = {"magnitude": indent, "unit": "PT"}
            ps["indentFirstLine"] = {"magnitude": indent, "unit": "PT"}
            fields += ["indentStart", "indentFirstLine"]
        self.reqs.append({
            "updateParagraphStyle": {
                "range": {"startIndex": para_start, "endIndex": para_end},
                "paragraphStyle": ps,
                "fields": ",".join(fields),
            }
        })
        return para_start, para_end

    # ---- higher-level blocks ----
    def heading(self, txt, *, num=None, color=INK, space_before=18):
        runs = []
        if num:
            runs.append({"text": num + "  ", "bold": True, "color": RED, "size": 15})
        runs.append({"text": txt, "bold": True, "color": color, "size": 15})
        self.para(runs, named_style="HEADING_1", space_before=space_before,
                  space_after=7)

    def h2(self, txt, color=INK):
        self.para([{"text": txt, "bold": True, "color": color, "size": 12.5}],
                  named_style="HEADING_2", space_before=12, space_after=4)

    def eyebrow(self, txt, color=RED):
        self.para([{"text": txt.upper(), "bold": True, "color": color, "size": 9}],
                  space_before=10, space_after=2)

    def body(self, runs, *, space_after=7, align=None):
        if isinstance(runs, str):
            runs = [{"text": runs}]
        self.para(runs, space_after=space_after, align=align)

    def bullet(self, runs, color=RED):
        if isinstance(runs, str):
            runs = [{"text": runs}]
        self.para(runs, bullet_color=color, indent=18, space_after=4)

    def callout(self, label, runs, *, tint=PERITINT, accent=PERI, label_color=None):
        if isinstance(runs, str):
            runs = [{"text": runs}]
        lc = label_color or accent
        # label line + body, both shaded & sharing a left rule.
        self.para([{"text": label.upper(), "bold": True, "color": lc, "size": 8.5}],
                  shading=tint, left_border=accent, space_before=8, space_after=1,
                  indent=2)
        self.para(runs, shading=tint, left_border=accent, space_after=8, indent=2)

    def band(self, eyebrow_txt, title, sub="", *, title_size=30):
        self.para([{"text": eyebrow_txt.upper(), "bold": True,
                    "color": PERI_LIGHT, "size": 11}],
                  shading=INK, space_before=10, space_after=2, indent=4)
        self.para([{"text": title, "bold": True, "color": WHITE, "size": title_size}],
                  shading=INK, space_after=2 if sub else 10, indent=4)
        if sub:
            self.para([{"text": sub, "color": INK_SUB, "size": 11.5}],
                      shading=INK, space_after=10, indent=4)

    def image(self, path: Path, *, width_pt=CONTENT_W_PT, align="CENTER",
              caption: Optional[str] = None):
        uri = self._uri_for(path)
        try:
            with Image.open(path) as im:
                iw, ih = im.size
        except Exception:
            iw, ih = (1180, 660)
        h_pt = round(width_pt * ih / iw, 1)
        start = self.cursor
        self.reqs.append({
            "insertInlineImage": {
                "location": {"index": start},
                "uri": uri,
                "objectSize": {
                    "width": {"magnitude": width_pt, "unit": "PT"},
                    "height": {"magnitude": h_pt, "unit": "PT"},
                },
            }
        })
        self.cursor += 1
        self.text("\n")
        img_para_end = self.cursor
        self.reqs.append({
            "updateParagraphStyle": {
                "range": {"startIndex": start, "endIndex": img_para_end},
                "paragraphStyle": {"alignment": align,
                                   "spaceAbove": {"magnitude": 6, "unit": "PT"},
                                   "spaceBelow": {"magnitude": 4, "unit": "PT"}},
                "fields": "alignment,spaceAbove,spaceBelow",
            }
        })
        if caption:
            self.para([{"text": caption, "italic": True, "color": MUTE, "size": 9}],
                      align="CENTER", space_after=10)

    def _uri_for(self, path: Path) -> str:
        key = str(path)
        if key not in self._uri_cache:
            uri, fid = _upload_public_image(self.drive, path)
            self._uri_cache[key] = uri
            self._asset_ids.append(fid)
        return self._uri_cache[key]

    def seed_uri(self, path: Path, uri: str):
        """Pre-register an already-uploaded image so it isn't re-uploaded.

        Lets the batch driver upload shared assets (proof screenshots) once and
        reuse the public URI across all 600 docs.
        """
        self._uri_cache[str(path)] = uri

    # ---- tables ----
    def table(self, headers: List[str], rows: List[List[str]],
              col_widths_pt: List[float]):
        """Insert a real Docs table and fill it (header dark, body striped)."""
        self._flush()
        end = self._end_index()
        n_rows = len(rows) + 1
        n_cols = len(headers)
        self.docs.documents().batchUpdate(
            documentId=self.doc_id,
            body={"requests": [{
                "insertTable": {"location": {"index": end},
                                "rows": n_rows, "columns": n_cols}
            }]},
        ).execute()

        doc = self.docs.documents().get(documentId=self.doc_id).execute()
        table_el, table_start = self._find_last_table(doc)
        grid = table_el["table"]["tableRows"]

        # Column widths.
        col_reqs = []
        for ci, w in enumerate(col_widths_pt):
            col_reqs.append({
                "updateTableColumnProperties": {
                    "tableStartLocation": {"index": table_start},
                    "columnIndices": [ci],
                    "tableColumnProperties": {
                        "widthType": "FIXED_WIDTH",
                        "width": {"magnitude": w, "unit": "PT"},
                    },
                    "fields": "widthType,width",
                }
            })

        # Build cell-fill requests in REVERSE document order so indexes are stable.
        cell_reqs = []
        cell_style_reqs = []
        all_rows = [headers] + rows
        flat = []  # (start_index, text, is_header, col)
        for ri, row in enumerate(grid):
            for ci, cell in enumerate(row["tableCells"]):
                cstart = cell["content"][0]["startIndex"]
                flat.append((cstart, all_rows[ri][ci], ri == 0, ci, cell))
        for cstart, txt, is_header, ci, cell in sorted(flat, key=lambda x: -x[0]):
            txt = str(txt)
            cell_reqs.append({"insertText": {"location": {"index": cstart}, "text": txt}})
            cell_reqs.append({
                "updateTextStyle": {
                    "range": {"startIndex": cstart, "endIndex": cstart + len(txt)},
                    "textStyle": {
                        "bold": is_header,
                        "foregroundColor": _color(WHITE if is_header else INK),
                        "fontSize": {"magnitude": 9 if is_header else 9.5, "unit": "PT"},
                        "weightedFontFamily": {"fontFamily": FONT},
                    },
                    "fields": "bold,foregroundColor,fontSize,weightedFontFamily",
                }
            })

        # Cell background shading (header ink; body zebra).
        for ri, row in enumerate(grid):
            for ci in range(n_cols):
                fill = INK if ri == 0 else (PAPER if ri % 2 == 0 else WHITE)
                cell_style_reqs.append({
                    "updateTableCellStyle": {
                        "tableStartLocation": {"index": table_start},
                        "tableRange": {
                            "tableCellLocation": {
                                "tableStartLocation": {"index": table_start},
                                "rowIndex": ri, "columnIndex": ci,
                            },
                            "rowSpan": 1, "columnSpan": 1,
                        },
                        "tableCellStyle": {"backgroundColor": _color(fill),
                                           "paddingTop": {"magnitude": 4, "unit": "PT"},
                                           "paddingBottom": {"magnitude": 4, "unit": "PT"},
                                           "paddingLeft": {"magnitude": 6, "unit": "PT"},
                                           "paddingRight": {"magnitude": 6, "unit": "PT"}},
                        "fields": "backgroundColor,paddingTop,paddingBottom,paddingLeft,paddingRight",
                    }
                })

        self.docs.documents().batchUpdate(
            documentId=self.doc_id,
            body={"requests": cell_reqs + col_reqs + cell_style_reqs},
        ).execute()
        self.cursor = self._end_index()

    def rich_table(self, headers: List[str], rows, col_widths_pt: List[float],
                   header_fills: Optional[List[str]] = None):
        """Like table() but each cell is a list of styled runs (or a string),
        with optional per-column header fill colors. Used by native visuals."""
        self._flush()
        end = self._end_index()
        n_rows = len(rows) + 1
        n_cols = len(headers)
        self.docs.documents().batchUpdate(
            documentId=self.doc_id,
            body={"requests": [{
                "insertTable": {"location": {"index": end},
                                "rows": n_rows, "columns": n_cols}
            }]},
        ).execute()

        doc = self.docs.documents().get(documentId=self.doc_id).execute()
        table_el, table_start = self._find_last_table(doc)
        grid = table_el["table"]["tableRows"]

        def norm(cell, is_header):
            if isinstance(cell, str):
                return [{"text": cell, "bold": is_header,
                         "color": WHITE if is_header else INK,
                         "size": 9 if is_header else 9.5}]
            return cell

        # collect (cell_start, runs) and process in reverse start order
        flat = []
        all_rows = [[norm(h, True) for h in headers]] + [
            [norm(c, False) for c in row] for row in rows]
        for ri, row in enumerate(grid):
            for ci, cell in enumerate(row["tableCells"]):
                cstart = cell["content"][0]["startIndex"]
                flat.append((cstart, all_rows[ri][ci]))

        text_reqs = []
        for cstart, runs in sorted(flat, key=lambda x: -x[0]):
            idx = cstart
            for r in runs:
                txt = str(r.get("text", ""))
                if not txt:
                    continue
                text_reqs.append({"insertText": {"location": {"index": idx},
                                                 "text": txt}})
                style = {
                    "bold": r.get("bold", False),
                    "italic": r.get("italic", False),
                    "underline": r.get("underline", False),
                    "foregroundColor": _color(r.get("color", INK)),
                    "fontSize": {"magnitude": r.get("size", 9.5), "unit": "PT"},
                    "weightedFontFamily": {"fontFamily": FONT},
                }
                fields = ("bold,italic,underline,foregroundColor,fontSize,"
                          "weightedFontFamily")
                if r.get("link"):
                    style["link"] = {"url": r["link"]}
                    fields += ",link"
                text_reqs.append({"updateTextStyle": {
                    "range": {"startIndex": idx, "endIndex": idx + len(txt)},
                    "textStyle": style, "fields": fields}})
                idx += len(txt)

        style_reqs = []
        for ci, w in enumerate(col_widths_pt):
            style_reqs.append({"updateTableColumnProperties": {
                "tableStartLocation": {"index": table_start},
                "columnIndices": [ci],
                "tableColumnProperties": {"widthType": "FIXED_WIDTH",
                                          "width": {"magnitude": w, "unit": "PT"}},
                "fields": "widthType,width"}})
        for ri, row in enumerate(grid):
            for ci in range(n_cols):
                if ri == 0:
                    fill = (header_fills[ci] if header_fills else INK)
                else:
                    fill = PAPER if ri % 2 == 0 else WHITE
                style_reqs.append({"updateTableCellStyle": {
                    "tableStartLocation": {"index": table_start},
                    "tableRange": {"tableCellLocation": {
                        "tableStartLocation": {"index": table_start},
                        "rowIndex": ri, "columnIndex": ci},
                        "rowSpan": 1, "columnSpan": 1},
                    "tableCellStyle": {"backgroundColor": _color(fill),
                                       "paddingTop": {"magnitude": 4, "unit": "PT"},
                                       "paddingBottom": {"magnitude": 4, "unit": "PT"},
                                       "paddingLeft": {"magnitude": 6, "unit": "PT"},
                                       "paddingRight": {"magnitude": 6, "unit": "PT"}},
                    "fields": ("backgroundColor,paddingTop,paddingBottom,"
                               "paddingLeft,paddingRight")}})

        self.docs.documents().batchUpdate(
            documentId=self.doc_id,
            body={"requests": text_reqs + style_reqs},
        ).execute()
        self.cursor = self._end_index()

    @staticmethod
    def _find_last_table(doc):
        last = None
        for el in doc["body"]["content"]:
            if "table" in el:
                last = (el, el["startIndex"])
        return last

    # ---- finish ----
    def finish(self, make_public: bool) -> dict:
        self._flush()
        url = f"https://docs.google.com/document/d/{self.doc_id}/edit"
        if make_public:
            self.drive.permissions().create(
                fileId=self.doc_id, body={"role": "reader", "type": "anyone"}
            ).execute()
        return {
            "document_id": self.doc_id,
            "edit_url": url,
            "public_url": f"https://docs.google.com/document/d/{self.doc_id}/view"
            if make_public else url,
        }


# ======================================================================
# Assemble the audit document
# ======================================================================
def build_doc(result: AuditResult, proof: Optional[dict], assets: Path) -> dict:
    cl = result.clientLabel or result.client
    b = DocBuilder(f"SEO & AI-Search Audit — {result.client}")

    def asset(name: str) -> Optional[Path]:
        p = assets / name
        return p if p.exists() else None

    # ---------- COVER ----------
    logo = asset("logo_crop.png")
    if logo:
        b.image(logo, width_pt=130, align="START")
    b.band("SEO & AI-search audit", result.client, result.subtitle or "",
           title_size=34)
    b.body([{"text": "Prepared for ", "color": MUTE},
            {"text": cl + " ", "bold": True},
            {"text": f"({result.client})" +
             (f" — {result.businessType}." if result.businessType else "."),
             "color": MUTE}], space_after=2)
    b.body([{"text": "Prepared by ", "color": MUTE},
            {"text": result.consultantName, "bold": True},
            {"text": " · RankedTag — the inbound engine for SaaS founders.",
             "color": MUTE}], space_after=2)
    inside = ("why this matters now · how the site was assessed · the scorecard · "
              "what's costing you the most · a 30-day plan · the full action list")
    if proof:
        inside += f" · and proof of this exact engine in the wild for {proof.get('client','sendr.ai')}"
    b.body([{"text": "Inside: ", "bold": True},
            {"text": inside + ".", "color": MUTE}], space_after=8)

    # ---------- NOTE ----------
    b.eyebrow("A quick note before you dig in")
    b.heading(f"Hi {cl} team —")
    for p in result.note:
        b.body(p)
    b.body([{"text": "— " + result.consultantFirstName,
             "italic": True, "color": MUTE}])

    # ---------- WHY ----------
    if result.why:
        b.eyebrow("The why")
        b.heading("Search just split into two races", num="1")
        for p in result.why.intro:
            b.body(p)
        if result.why.callout:
            b.callout(result.why.calloutLabel or f"Why this matters for {cl}",
                      result.why.callout, tint=PERITINT, accent=PERI)
        if result.why.outro:
            b.body(result.why.outro)

    # ---------- METHOD + SCORECARD ----------
    b.eyebrow("The what & how")
    b.heading("What I looked at, and how", num="2")
    if result.method and result.method.scope:
        b.body(result.method.scope)
    if result.method and result.method.how:
        b.body([{"text": "Method, in plain terms. ", "bold": True},
                {"text": result.method.how}])
    b.heading("The scorecard", num="3")
    b.body("Schema and AI-search readiness are usually the two areas pulling the "
           "score down. Both are addressed directly in the plan that follows.",
           space_after=4)
    if asset("viz_scorecard.png"):
        b.image(asset("viz_scorecard.png"),
                caption="Read it like a dashboard: green is healthy, amber is "
                "fair-but-improvable, red needs attention.")

    # ---------- CRITICAL ----------
    b.eyebrow("What's costing you the most", RED)
    b.heading("Fix these first", num="4")
    for f in result.critical:
        b.h2(f.heading, color=RED_DK)
        for p in f.body:
            b.body(p)
        if f.visual == "richresult" and asset("viz_richresult.png"):
            b.image(asset("viz_richresult.png"))
        elif f.visual == "meta" and asset("viz_meta.png"):
            b.image(asset("viz_meta.png"))
        if f.whatToDo:
            b.callout("What to do", f.whatToDo, tint=GREENTINT, accent=GREEN,
                      label_color=GREEN_DK)

    # ---------- HIGH ----------
    if result.high:
        b.eyebrow("High priority — within a week", AMBER)
        b.heading("The week-one list", num="5")
        for f in result.high:
            b.h2(f.heading)
            for p in f.body:
                b.body(p)
            if f.visual == "meta" and asset("viz_meta.png"):
                b.image(asset("viz_meta.png"))
            elif f.visual == "richresult" and asset("viz_richresult.png"):
                b.image(asset("viz_richresult.png"))
            if f.whatToDo:
                b.callout("What to do", f.whatToDo, tint=GREENTINT, accent=GREEN,
                          label_color=GREEN_DK)

    # ---------- MEDIUM ----------
    if result.medium:
        b.eyebrow("Medium priority — within a month", GREEN_DK)
        b.heading("Worth doing this month", num="6")
        b.body("Lower urgency, still genuine value. Several are nearly free "
               "because the content already exists.")
        b.table(["Finding", "Why it matters / what to do"],
                [[m.finding, m.detail] for m in result.medium],
                [150, 318])

    # ---------- QUICK WINS ----------
    if result.quickWins:
        b.eyebrow("Start here", RED)
        b.heading("Five quick wins", num="7")
        b.body("If the team can only touch a handful of things first, these return "
               "the most for the least effort. Ordered by estimated return.",
               space_after=4)
        for q in result.quickWins:
            b.bullet([{"text": q.title, "bold": True},
                      {"text": " — " + q.detail}])
        if asset("viz_roadmap.png"):
            b.image(asset("viz_roadmap.png"))

    # ---------- ACTION PLAN ----------
    if result.actionPlan:
        b.eyebrow("The full list")
        b.heading("Recommended action plan", num="8")
        b.body("Every recommendation, with a suggested owner and rough effort.")
        b.table(["Action", "Owner", "Effort", "Expected impact"],
                [[a.action, a.owner, a.effort, a.impact] for a in result.actionPlan],
                [218, 60, 60, 130])

    # ---------- COMPETITIVE ----------
    if result.competitive:
        b.eyebrow("Where you stand")
        b.heading("Competitive context", num="9")
        if result.competitive.intro:
            b.body(result.competitive.intro)
        for p in result.competitive.points:
            b.bullet(p)

    # ---------- PROOF ----------
    if proof:
        _proof_section(b, proof, cl, asset)

    # ---------- NEXT ----------
    b.eyebrow("What happens next")
    b.heading("Let’s turn this into rankings")
    b.body("Here’s how I’d suggest we play it:")
    nexts = result.next or [
        {"label": "This week:", "text": "knock out the five quick wins above."},
        {"label": "Together:", "text": "I’ll walk your team through any finding."},
        {"label": "Then:", "text": "we re-test once the first round is live."},
    ]
    for n in nexts:
        lbl = n.label if hasattr(n, "label") else n["label"]
        txt = n.text if hasattr(n, "text") else n["text"]
        b.bullet([{"text": lbl + " ", "bold": True}, {"text": txt}])
    if result.nextOutro:
        b.body(result.nextOutro)
    # signature
    b.callout(result.consultantName,
              [{"text": "SEO & Technical Audit · RankedTag", "color": MUTE,
                "size": 10}], tint=PAPER, accent=RED, label_color=INK)
    b.body([{"text": result.consultantEmail, "color": PERI, "size": 10},
            {"text": "      ·      ", "color": MUTE, "size": 10},
            {"text": "rankedtag.com", "color": PERI, "size": 10,
             "link": "https://rankedtag.com", "underline": True}])

    return b.finish(config.MAKE_PUBLIC)


def build_lite_doc(lite, proof: Optional[dict], assets: Path,
                   proof_uris: Optional[dict] = None) -> dict:
    """Build a triage-grade (lite) public Google Doc. Table-free to minimise
    API calls at 600-doc scale. `proof_uris` lets shared screenshots be reused."""
    cl = lite.client
    consultant_name = "Bhushan Raj Shakya"
    consultant_email = "hello@rankedtag.com"
    b = DocBuilder(f"SEO & AI-Search Audit — {lite.client}")
    if proof_uris:
        for name, uri in proof_uris.items():
            b.seed_uri(assets / name, uri)

    def asset(name: str) -> Optional[Path]:
        p = assets / name
        return p if p.exists() else None

    # ---- cover ----
    b.band("SEO & AI-search audit", lite.client, lite.subtitle or "", title_size=34)
    b.body([{"text": "Prepared by ", "color": MUTE},
            {"text": consultant_name, "bold": True},
            {"text": " · RankedTag — the inbound engine for SaaS founders.",
             "color": MUTE}], space_after=2)
    inside = ("the scorecard · the highest-impact fixes · quick wins")
    if proof:
        inside += f" · and proof of this engine in the wild for {proof.get('client','sendr.ai')}"
    b.body([{"text": "Inside: ", "bold": True},
            {"text": inside + ".", "color": MUTE}], space_after=8)

    # ---- at a glance ----
    b.eyebrow("At a glance")
    b.heading(f"Hi {cl} team — here’s your snapshot")
    if lite.summary:
        b.body(lite.summary)
    if asset("viz_scorecard.png"):
        b.image(asset("viz_scorecard.png"),
                caption="Green is healthy, amber is fair-but-improvable, red needs "
                "attention. The lost points cluster in a few fixable themes.")

    # ---- findings ----
    if lite.findings:
        b.eyebrow("What’s costing you the most", RED)
        b.heading("The highest-impact fixes", num="1")
        for f in lite.findings:
            b.h2(f.h, color=RED_DK)
            if f.why:
                b.body(f.why)
            if f.fix:
                b.callout("What to do", f.fix, tint=GREENTINT, accent=GREEN,
                          label_color=GREEN_DK)

    # ---- quick wins ----
    if lite.quickWins:
        b.eyebrow("Start here", RED)
        b.heading("Quick wins", num="2")
        b.body("Highest return for the least effort — a good place to start.",
               space_after=4)
        for q in lite.quickWins:
            b.bullet(q)

    # ---- proof ----
    if proof:
        _proof_section(b, proof, cl, asset, lite=True)

    # ---- next + signature ----
    b.eyebrow("What happens next")
    b.heading("Let’s turn this into rankings")
    b.body("This is a fast snapshot. The next step is a full deep-dive audit and a "
           "30-day plan your team can action — and I’m happy to walk you through it.")
    b.callout(consultant_name,
              [{"text": "SEO & Technical Audit · RankedTag", "color": MUTE,
                "size": 10}], tint=PAPER, accent=RED, label_color=INK)
    b.body([{"text": consultant_email, "color": PERI, "size": 10},
            {"text": "      ·      ", "color": MUTE, "size": 10},
            {"text": "rankedtag.com", "color": PERI, "size": 10,
             "link": "https://rankedtag.com", "underline": True}])

    return b.finish(config.MAKE_PUBLIC)


def _proof_section(b: DocBuilder, proof: dict, cl: str, asset, lite: bool = False):
    pc = proof.get("client", "sendr.ai")
    b.band("Proof — not promises", f"What this exact engine did for {pc}",
           f"{proof.get('stage','')}, competing against the category leaders, "
           "with no enterprise budget." if proof.get("stage") else "",
           title_size=24)
    b.body([{"text": f"{cl} doesn’t need to take my word for the plan above — "
             "here’s the same playbook already in the wild. "},
            {"text": pc + " ", "bold": True},
            {"text": proof.get("intro", "")}])
    metrics = proof.get("metrics", [])[:3]
    if metrics and lite:
        # Table-free metric strip (one paragraph) to save API calls at scale.
        runs = []
        for i, m in enumerate(metrics):
            if i:
                runs.append({"text": "    ·    ", "color": MUTE})
            runs.append({"text": m.get("big", ""), "bold": True, "color": GREEN_DK,
                         "size": 12})
            runs.append({"text": " " + m.get("small", ""), "color": MUTE})
        b.para(runs, space_after=8)
    elif metrics:
        b.table([m.get("big", "") for m in metrics],
                [[m.get("small", "") for m in metrics]],
                [156, 156, 156])
    b.h2("The receipts")
    if asset("result-sendr.jpeg"):
        b.body([{"text": "1. Real Google Search Console — last 6 months. ",
                 "bold": True},
                {"text": "From a standing start, climbing the whole way."}],
               space_after=2)
        b.image(asset("result-sendr.jpeg"),
                caption=proof.get("gsc_caption", ""))
    if asset("result-ranked.jpeg"):
        b.body([{"text": "2. Ranked #2 in Google’s AI Overview — above ZoomInfo. ",
                 "bold": True},
                {"text": f"For the query “{proof.get('query','')}”, "
                 f"{pc} is the cited source."}], space_after=2)
        b.image(asset("result-ranked.jpeg"), width_pt=350,
                caption=proof.get("ranked_caption", ""))
    if proof.get("quote"):
        b.callout("In the founder’s words",
                  [{"text": f"“{proof['quote']}”", "italic": True,
                    "size": 11},
                   {"text": "  — " + proof.get("quote_attrib", ""), "color": MUTE}],
                  tint=PAPER, accent=RED, label_color=RED_DK)
    b.h2("How we out-content the giants")
    for e in proof.get("engine", []):
        b.bullet([{"text": e.get("b", ""), "bold": True}, {"text": e.get("t", "")}])
    if proof.get("engine_result"):
        b.callout("The result", proof["engine_result"], tint=PERITINT, accent=PERI)
    b.callout(f"What this means for {cl}",
              [{"text": "The audit you just read is step one of this exact process — "
                "same diagnosis, same stack, same obsession with being the cited "
                f"answer, pointed at {cl}’s biggest opportunities."}],
              tint=GREENTINT, accent=GREEN, label_color=GREEN_DK)
