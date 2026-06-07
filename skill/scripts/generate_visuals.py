#!/usr/bin/env python3
"""
Generate the four signature RankedTag audit visuals as high-res PNGs.

Usage:
  python generate_visuals.py --out ./assets_run \
      --overall 62 \
      --scores "Technical SEO=72,Content quality=68,On-page SEO=65,Schema / structured data=35,Core Web Vitals=65,AI search readiness=40,Images=78" \
      --client "treez.io"

Optional flags tailor the rich-result and meta visuals to the client:
  --pos-path "products › point-of-sale"   breadcrumb shown in the rich-result mock
  --page-title "Point of Sale | Treez"    title shown in both mocks
  --meta-before "Treez POS gives dispensaries real-time inventory, compliance and reporting in one platform that hel"
  --meta-after  "Run your dispensary on Treez POS — real-time inventory, built-in compliance, and one-click reporting. Book a demo."
  --faqs "Does Treez support multi-store?|Is Treez compliant in my state?|How long is onboarding?"
  --now "Add structured data (schema)|Clear 40 HTML validation errors"
  --week "Rewrite truncated meta|Speed up server (TTFB)|Fix og:url + crawlable blog|Add author bylines (E-E-A-T)"
  --month "FAQ schema on product page|Public pricing page|llms.txt for AI crawlers|Title + breadcrumb tidy-up"

Requires: cairosvg  (pip install cairosvg --break-system-packages)
"""
import argparse, os, math, sys

# ---- Brand palette ----
INK="#161618"; INK2="#2A2B33"; PAPER="#F4EFE7"; PAPER2="#EDE6D9"; LINE="#E0D7C7"
RED="#FF3B14"; RED_DK="#C8260A"; PERI="#A6B0F0"; PERI_DK="#6B77E0"
GREEN="#2D8A5C"; GREEN_DK="#1F4D3F"; AMBER="#D97706"; MUTE="#6E6E76"; WHITE="#FFFFFF"
FONT="Helvetica, Arial, sans-serif"

def tier_color(v):
    if v >= 75: return GREEN
    if v >= 50: return AMBER
    return RED

def tier_label(v):
    if v >= 75: return ("GOOD", GREEN)
    if v >= 50: return ("FAIR", AMBER)
    return ("POOR", RED)

def star(cx, cy, r, fill):
    pts=[]
    for k in range(10):
        ang=-math.pi/2 + k*math.pi/5
        rr=r if k%2==0 else r*0.42
        pts.append(f"{cx+rr*math.cos(ang):.1f},{cy+rr*math.sin(ang):.1f}")
    return f'<polygon points="{" ".join(pts)}" fill="{fill}"/>'

def stars_row(x, cy, r, n, fill):
    return "".join(star(x+i*(2*r+6)+r, cy, r, fill) for i in range(n))

def caret(x, cy, fill):
    return f'<polygon points="{x},{cy-5} {x+12},{cy-5} {x+6},{cy+4}" fill="{fill}"/>'

def esc(s):
    return (s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;"))

def render(path, svg, scale=2.0):
    import cairosvg
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=path, scale=scale)
    print("rendered", path)


def viz_scorecard(out, overall, scores):
    W,H=1180,660; left_w=360
    label,labelcol=tier_label(overall)
    row_top=60; row_h=(H-100)/len(scores)
    bar_x=770; bar_w=W-bar_x-95
    rows=[]
    for i,(name,val) in enumerate(scores):
        cy=row_top+i*row_h+row_h/2; col=tier_color(val); fw=bar_w*(val/100.0)
        rows.append(f'''
      <text x="{left_w+40}" y="{cy+6}" font-family="{FONT}" font-size="23" font-weight="600" fill="{INK}">{esc(name)}</text>
      <rect x="{bar_x}" y="{cy-13}" width="{bar_w}" height="26" rx="13" fill="{PAPER2}"/>
      <rect x="{bar_x}" y="{cy-13}" width="{fw:.0f}" height="26" rx="13" fill="{col}"/>
      <text x="{bar_x+bar_w+18}" y="{cy+8}" font-family="{FONT}" font-size="26" font-weight="700" fill="{col}">{val}</text>''')
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <rect x="2" y="2" width="{W-4}" height="{H-4}" rx="22" fill="{PAPER}" stroke="{LINE}" stroke-width="2"/>
  <rect x="0" y="0" width="{left_w}" height="{H}" rx="22" fill="{INK}"/>
  <rect x="{left_w-22}" y="0" width="22" height="{H}" fill="{INK}"/>
  <text x="{left_w/2}" y="120" text-anchor="middle" font-family="{FONT}" font-size="22" font-weight="700" fill="{PERI}" letter-spacing="2">OVERALL SCORE</text>
  <text x="{left_w/2}" y="320" text-anchor="middle" font-family="{FONT}" font-size="170" font-weight="800" fill="{WHITE}">{overall}</text>
  <text x="{left_w/2}" y="370" text-anchor="middle" font-family="{FONT}" font-size="34" font-weight="600" fill="{MUTE}">out of 100</text>
  <rect x="{left_w/2-70}" y="420" width="140" height="50" rx="25" fill="{labelcol}"/>
  <text x="{left_w/2}" y="453" text-anchor="middle" font-family="{FONT}" font-size="26" font-weight="700" fill="{WHITE}">{label}</text>
  <text x="{left_w/2}" y="540" text-anchor="middle" font-family="{FONT}" font-size="20" fill="{MUTE}">A solid base with</text>
  <text x="{left_w/2}" y="568" text-anchor="middle" font-family="{FONT}" font-size="20" fill="{MUTE}">clear, fixable gaps</text>
  <text x="{left_w+40}" y="40" font-family="{FONT}" font-size="20" font-weight="700" fill="{MUTE}" letter-spacing="2">CATEGORY BREAKDOWN</text>
  {''.join(rows)}
</svg>'''
    render(os.path.join(out,"viz_scorecard.png"), svg)


def viz_richresult(out, title, pos_path, faqs):
    W,H=1180,560
    f1,f2,f3=(faqs+["","",""])[:3]
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <rect x="0" y="0" width="{W}" height="{H}" rx="22" fill="{PAPER}" stroke="{LINE}" stroke-width="2"/>
  <text x="40" y="56" font-family="{FONT}" font-size="30" font-weight="800" fill="{INK}">The same page, two very different search results</text>
  <rect x="40" y="90" width="525" height="420" rx="16" fill="{WHITE}" stroke="{LINE}" stroke-width="2"/>
  <rect x="40" y="90" width="525" height="50" rx="16" fill="#FBE9E4"/><rect x="40" y="118" width="525" height="22" fill="#FBE9E4"/>
  <circle cx="68" cy="115" r="7" fill="{RED}"/>
  <text x="86" y="122" font-family="{FONT}" font-size="22" font-weight="700" fill="{RED_DK}">TODAY — plain blue link</text>
  <text x="72" y="182" font-family="{FONT}" font-size="20" fill="{GREEN_DK}">www.{esc(pos_path.split("›")[0].strip()) or "site"} › ...</text>
  <text x="72" y="222" font-family="{FONT}" font-size="26" font-weight="600" fill="{PERI_DK}">{esc(title)}</text>
  <text x="72" y="262" font-family="{FONT}" font-size="20" fill="{MUTE}">A plain description with no enhancements,</text>
  <text x="72" y="290" font-family="{FONT}" font-size="20" fill="{MUTE}">competing for a single line...</text>
  <line x1="72" y1="330" x2="533" y2="330" stroke="{LINE}" stroke-width="1.5"/>
  <text x="72" y="372" font-family="{FONT}" font-size="19" fill="{MUTE}">No stars. No FAQ. No breadcrumb.</text>
  <text x="72" y="400" font-family="{FONT}" font-size="19" fill="{MUTE}">Competing for one thin line</text>
  <text x="72" y="428" font-family="{FONT}" font-size="19" fill="{MUTE}">on the page.</text>
  <text x="72" y="478" font-family="{FONT}" font-size="20" font-weight="700" fill="{RED_DK}">Takes up ~1 line of space</text>
  <rect x="615" y="90" width="525" height="420" rx="16" fill="{WHITE}" stroke="{GREEN}" stroke-width="2.5"/>
  <rect x="615" y="90" width="525" height="50" rx="16" fill="#E6F1EC"/><rect x="615" y="118" width="525" height="22" fill="#E6F1EC"/>
  <circle cx="643" cy="115" r="7" fill="{GREEN}"/>
  <text x="661" y="122" font-family="{FONT}" font-size="22" font-weight="700" fill="{GREEN_DK}">WITH SCHEMA — rich result</text>
  <text x="647" y="182" font-family="{FONT}" font-size="20" fill="{GREEN_DK}">www.{esc(pos_path) or "site › page"}</text>
  <text x="647" y="222" font-family="{FONT}" font-size="26" font-weight="600" fill="{PERI_DK}">{esc(title)}</text>
  {stars_row(649,250,11,5,AMBER)}
  <text x="804" y="258" font-family="{FONT}" font-size="20" fill="{MUTE}">4.8  ·  312 reviews</text>
  <text x="647" y="294" font-family="{FONT}" font-size="20" fill="{MUTE}">A richer result that earns more of the page...</text>
  <line x1="647" y1="322" x2="1108" y2="322" stroke="{LINE}" stroke-width="1.5"/>
  {caret(649,348,INK)}<text x="675" y="352" font-family="{FONT}" font-size="19" font-weight="600" fill="{INK}">{esc(f1)}</text>
  {caret(649,380,INK)}<text x="675" y="384" font-family="{FONT}" font-size="19" font-weight="600" fill="{INK}">{esc(f2)}</text>
  {caret(649,412,INK)}<text x="675" y="416" font-family="{FONT}" font-size="19" font-weight="600" fill="{INK}">{esc(f3)}</text>
  <text x="647" y="478" font-family="{FONT}" font-size="20" font-weight="700" fill="{GREEN_DK}">Takes up 4–5× the space</text>
</svg>'''
    render(os.path.join(out,"viz_richresult.png"), svg)


def viz_meta(out, title, before, after):
    W,H=1180,470
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <rect x="0" y="0" width="{W}" height="{H}" rx="22" fill="{PAPER}" stroke="{LINE}" stroke-width="2"/>
  <text x="40" y="56" font-family="{FONT}" font-size="30" font-weight="800" fill="{INK}">The meta description, before and after</text>
  <rect x="40" y="90" width="1100" height="150" rx="16" fill="{WHITE}" stroke="{RED}" stroke-width="2.5"/>
  <text x="64" y="132" font-family="{FONT}" font-size="22" font-weight="700" fill="{RED_DK}">NOW · cut off mid-sentence</text>
  <text x="64" y="172" font-family="{FONT}" font-size="22" font-weight="600" fill="{PERI_DK}">{esc(title)}</text>
  <text x="64" y="206" font-family="{FONT}" font-size="20" fill="{MUTE}">{esc(before)}<tspan fill="{RED}" font-weight="700">…</tspan></text>
  <text x="64" y="232" font-family="{FONT}" font-size="18" fill="{RED_DK}" font-style="italic">→ Google often throws this away and writes its own weaker snippet.</text>
  <rect x="40" y="262" width="1100" height="150" rx="16" fill="{WHITE}" stroke="{GREEN}" stroke-width="2.5"/>
  <text x="64" y="304" font-family="{FONT}" font-size="22" font-weight="700" fill="{GREEN_DK}">FIXED · complete, benefit-led, under 155 characters</text>
  <text x="64" y="344" font-family="{FONT}" font-size="22" font-weight="600" fill="{PERI_DK}">{esc(title)}</text>
  <text x="64" y="378" font-family="{FONT}" font-size="20" fill="{MUTE}">{esc(after)}</text>
  <text x="64" y="404" font-family="{FONT}" font-size="18" fill="{GREEN_DK}" font-style="italic">→ You control the snippet. Higher click-through, on message.</text>
</svg>'''
    render(os.path.join(out,"viz_meta.png"), svg)


def viz_roadmap(out, now, week, month):
    W,H=1180,420
    phases=[("FIX NOW",RED,f"{len(now)} critical",now),
            ("THIS WEEK",AMBER,f"{len(week)} high-priority",week),
            ("THIS MONTH",GREEN,"quick wins + polish",month)]
    col_w=(W-80-40)/3; blocks=[]
    for i,(title,col,sub,items) in enumerate(phases):
        x=40+i*(col_w+20)
        item_t="".join(f'<text x="{x+28}" y="{200+j*42}" font-family="{FONT}" font-size="20" fill="{INK}">•  {esc(it)}</text>'
                       for j,it in enumerate(items[:5]))
        blocks.append(f'''
      <rect x="{x}" y="90" width="{col_w}" height="{H-130}" rx="16" fill="{WHITE}" stroke="{LINE}" stroke-width="2"/>
      <rect x="{x}" y="90" width="{col_w}" height="58" rx="16" fill="{col}"/><rect x="{x}" y="120" width="{col_w}" height="28" fill="{col}"/>
      <text x="{x+24}" y="128" font-family="{FONT}" font-size="26" font-weight="800" fill="{WHITE}">{title}</text>
      <text x="{x+28}" y="178" font-family="{FONT}" font-size="19" font-weight="700" fill="{col}" letter-spacing="1">{sub.upper()}</text>
      {item_t}''')
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <rect x="0" y="0" width="{W}" height="{H}" rx="22" fill="{PAPER}" stroke="{LINE}" stroke-width="2"/>
  <text x="40" y="56" font-family="{FONT}" font-size="30" font-weight="800" fill="{INK}">A simple 30-day sequence</text>
  {''.join(blocks)}
</svg>'''
    render(os.path.join(out,"viz_roadmap.png"), svg)


def parse_scores(s):
    out=[]
    for part in s.split(","):
        if "=" in part:
            k,v=part.rsplit("=",1); out.append((k.strip(), int(float(v))))
    return out

def split_pipe(s):
    return [x.strip() for x in s.split("|") if x.strip()] if s else []

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--overall", type=int, required=True)
    ap.add_argument("--scores", required=True, help='"Cat=NN,Cat=NN,..."')
    ap.add_argument("--client", default="your site")
    ap.add_argument("--page-title", default="Product | Your Brand")
    ap.add_argument("--pos-path", default="products › product")
    ap.add_argument("--faqs", default="Does it support multi-store?|Is it compliant in my state?|How long is onboarding?")
    ap.add_argument("--meta-before", default="Your product gives customers real-time inventory, compliance and reporting in one platform that hel")
    ap.add_argument("--meta-after", default="Run your business on one platform — real-time inventory, built-in compliance, and one-click reporting. Book a demo.")
    ap.add_argument("--now", default="Add structured data (schema)|Clear HTML validation errors")
    ap.add_argument("--week", default="Rewrite truncated meta|Speed up server (TTFB)|Fix og:url + crawlable blog|Add author bylines (E-E-A-T)")
    ap.add_argument("--month", default="FAQ schema on product page|Public pricing page|llms.txt for AI crawlers|Title + breadcrumb tidy-up")
    a=ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    try:
        import cairosvg  # noqa
    except ImportError:
        sys.exit("cairosvg not installed. Run: pip install cairosvg --break-system-packages")
    scores=parse_scores(a.scores)
    viz_scorecard(a.out, a.overall, scores)
    viz_richresult(a.out, a.page_title, a.pos_path, split_pipe(a.faqs))
    viz_meta(a.out, a.page_title, a.meta_before, a.meta_after)
    viz_roadmap(a.out, split_pipe(a.now), split_pipe(a.week), split_pipe(a.month))
    print("ALL VISUALS DONE ->", a.out)

if __name__=="__main__":
    main()
