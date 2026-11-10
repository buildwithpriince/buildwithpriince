#!/usr/bin/env python3
"""
Render the animated SVG cards for the GitHub profile README.

    python scripts/render_readme_cards.py          # writes cards/*.svg
    STATIC=1 python scripts/render_readme_cards.py # final frame -> .preview/ (+ preview.html)

Everything in a card must survive being shown through <img>: an inline <style>
with CSS keyframes, SMIL (<animate>/<set>), and fonts embedded as base64 WOFF
(subset with pyftsubset). No scripts, no external requests.
Edit the CONFIG block below; nothing else needs touching.
"""
import base64, html, json, math, os, random, subprocess, sys, textwrap
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATIC = os.environ.get("STATIC") == "1"
OUT = ROOT / (".preview" if STATIC else "cards")

# ───────────────────────────── CONFIG ─────────────────────────────
DATA_FILE = ROOT / "data" / "contributions.json"
PORTRAIT = ROOT / "assets" / "portrait.jpg"   # set to None to skip the portrait
PORTRAIT_CROP = (0.20, 0.38, 0.53, 0.60)      # l, t, r, b as fractions of the photo

NAME_FIRST, NAME_LAST = "Prince", "Agrawal"
EYEBROW = "CSE @ MSU BARODA  /  OPEN TO INTERNSHIPS"
TAGLINE = ["I build full-stack and AI products,", "and ship them. SWE & AI engineering."]
SITE, SITE_URL = "buildwithpriince.in", "https://buildwithpriince.in"

# Palette. Swap these to match your site exactly.
BG, CARD, LINE = "#0B0B0F", "#121217", "#26262E"
INK, MUTE, ACCENT = "#F5F2EA", "#8C8A94", "#C6FF3D"
GRAPH_WORD = "in lime"                          # "Every day, <GRAPH_WORD>"

# value: number -> counts up; text -> rises in; "@longest" etc. come from data.
TILES = [
    dict(id="tile-build", label="BUILD", value="Full", suffix=" stack", dec=0,
         sub="React, TypeScript, Node, FastAPI. Frontends on Vercel, backends on Render.",
         url=SITE_URL, bg="#3D5AFE", fg="#FFFFFF"),
    dict(id="tile-hack", label="HACK", value=4, suffix=" hackathons", dec=0,
         sub="TetraTHON top 44, SIH 2026, Decode SIH and Odoo, with team Fivestack.",
         url=f"https://github.com/buildwithpriince", bg="#FF4D3D", fg="#FFFFFF"),
    dict(id="tile-streak", label="SHIP", value="@longest", suffix=" days", dec=0,
         sub="Longest streak of days with a commit in the last year.",
         url=f"https://github.com/buildwithpriince?tab=overview", bg="#FFC61A", fg="#15120A"),
]

# One card per repo. Fix the slugs/URLs to your real repos.
REPOS = [
    dict(id="repo-portfolio", name="buildwithpriince-portfolio",
         url="https://github.com/buildwithpriince/buildwithpriince-portfolio",
         desc="My portfolio at buildwithpriince.in: kinetic typography, live project data and an ask-about-my-work chat.",
         lang="TypeScript", color="#3178C6", tags="REACT / VITE / TS"),
    dict(id="repo-medikiosk", name="MediKiosk",
         url="https://github.com/buildwithpriince/MediKiosk",
         desc="AI clinical history-taking platform built at the MSU hackathon with team Fivestack.",
         lang="TypeScript", color="#3178C6", tags="AI / FASTAPI / SUPABASE"),
    dict(id="repo-globetrotter", name="GlobeTrotter",
         url="https://github.com/buildwithpriince/GlobeTrotter",
         desc="Multi-city travel planning web app built for the Odoo x LDCE hackathon.",
         lang="TypeScript", color="#3178C6", tags="REACT / NODE / FIREBASE"),
]

# Timeline (seconds): the page plays top to bottom.
T_TILES, T_CHART, T_REPOS, T_GRAPH = 1.8, 3.0, 4.4, 5.6
# ──────────────────────────────────────────────────────────────────

FONT_SRC = {  # key: (family alias, local fallback, file, weight, style)
    "d": ("PA Display", "Space Grotesk", "display-700.woff", 700, "normal"),
    "b": ("PA Body", "Space Grotesk", "body-400.woff", 400, "normal"),
    "s": ("PA Serif", "Instrument Serif", "serif-italic.woff", 400, "italic"),
    "m": ("PA Mono", "JetBrains Mono", "mono-400.woff", 400, "normal"),
}
UNICODES = "U+0020-007E"          # printable ASCII only; arrows are drawn as paths
_font_cache = {}


def esc(s):
    return html.escape(str(s), quote=True)


def font_b64(key):
    """Subset with the pyftsubset CLI (cached in fonts/.subset), return base64."""
    if key in _font_cache:
        return _font_cache[key]
    src = ROOT / "fonts" / FONT_SRC[key][2]
    out = ROOT / "fonts" / ".subset" / src.name
    out.parent.mkdir(parents=True, exist_ok=True)
    if not out.exists() or out.stat().st_mtime < src.stat().st_mtime:
        subprocess.run([sys.executable, "-m", "fontTools.subset", str(src),
                        f"--unicodes={UNICODES}", "--flavor=woff",
                        "--layout-features=kern,liga", "--no-hinting",
                        f"--output-file={out}"], check=True)
    _font_cache[key] = base64.b64encode(out.read_bytes()).decode()
    return _font_cache[key]


def css(fonts):
    faces = ""
    for k in fonts:
        fam, _, _, w, st = FONT_SRC[k]
        faces += (f"@font-face{{font-family:'{fam}';font-weight:{w};font-style:{st};"
                  f"src:url(data:font/woff;base64,{font_b64(k)}) format('woff')}}")
    fam = {k: f"'{v[0]}','{v[1]}'," + ("monospace" if k == "m" else "system-ui,sans-serif")
           for k, v in FONT_SRC.items()}
    s = faces
    s += (f".fd{{font-family:{fam['d']};font-weight:700}}.fb{{font-family:{fam['b']}}}"
          f".fs{{font-family:{fam['s']};font-style:italic;font-weight:400}}"
          f".fm{{font-family:{fam['m']}}}.tb{{transform-box:fill-box;transform-origin:center}}"
          ".tbb{transform-box:fill-box;transform-origin:50% 100%}.static{display:none}")
    if not STATIC:
        s += ("@keyframes rise{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}"
              "@keyframes fade{from{opacity:0}to{opacity:1}}"
              "@keyframes grow{from{transform:scaleY(0)}to{transform:scaleY(1)}}"
              "@keyframes pop{0%{opacity:0;transform:scale(.2)}65%{transform:scale(1.18)}100%{opacity:1;transform:scale(1)}}"
              "@keyframes swing{0%{opacity:0;transform:translateY(46px) rotate(-7deg)}70%{opacity:1;transform:translateY(-7px) rotate(1.2deg)}100%{opacity:1;transform:none}}"
              "@keyframes ring{0%{opacity:.7;transform:scale(.3)}100%{opacity:0;transform:scale(2.6)}}"
              "@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.35;transform:scale(1.7)}}"
              "@keyframes nudge{0%,100%{transform:translate(0,0)}50%{transform:translate(3px,-3px)}}"
              "@keyframes sweep{0%{transform:translateX(0)}35%,100%{transform:translateX(620px)}}"
              ".c{animation:pop .45s var(--d) cubic-bezier(.2,.9,.3,1.2) both}"
              "@media (prefers-reduced-motion:reduce){*{animation:none!important}"
              ".frame,.sm,.fx{display:none!important}.static{display:inline!important}}")
    return s


def an(name, dur, delay, ease="cubic-bezier(.2,.8,.2,1)", loop=False):
    if STATIC:
        return ""
    it = " infinite" if loop else " both"
    return f' style="animation:{name} {dur}s {delay:.3f}s {ease}{it}"'


def svg(w, h, title, body, fonts, defs=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="{esc(title)}"><title>{esc(title)}</title>'
            f'<defs><style>{css(fonts)}</style>{defs}</defs>{body}</svg>')


def mix(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def arrow(x, y, color, s=1, delay=0, size=7):
    d = f"M{-size},{size} L{size},{-size} M{-size * .4:.1f},{-size} H{size} V{size * .4:.1f}"
    return (f'<g transform="translate({x},{y}) scale({s})"><g{an("nudge", 2.4, delay, "ease-in-out", True)}>'
            f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" '
            f'stroke-linejoin="round"/></g></g>')


# Count-up text: N SMIL frames (CSS can't change text), one <text> per value.
N_FRAMES = 18


def big(x, y, val, suffix="", size=52, delay=0.0, dec=0, fill=INK, sfill=None, dur=1.1):
    sf = f' fill="{sfill}"' if sfill else ""

    def txt(v, cls="", pre="", attrs=""):
        return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" class="{cls}" {attrs}>{pre}'
                f'<tspan class="fd">{esc(v)}</tspan><tspan class="fs"{sf}>{esc(suffix)}</tspan></text>')

    if not isinstance(val, (int, float)):
        return f'<g{an("rise", .8, delay)}>{txt(val)}</g>'
    fmt = lambda v: f"{v:,.{dec}f}"
    if STATIC:
        return txt(fmt(val))
    out = txt(fmt(val), "static")
    step = dur / N_FRAMES
    for i in range(N_FRAMES):
        t = i / (N_FRAMES - 1)
        v = val * (1 - (1 - t) ** 3)
        last = i == N_FRAMES - 1
        s = (f'<set attributeName="visibility" to="visible" begin="{delay + i * step:.3f}s"'
             + ("" if last else f' dur="{step:.3f}s"') + (' fill="freeze"' if last else "") + "/>")
        out += txt(fmt(val if last else v), "frame", s, 'visibility="hidden"')
    return out


# ───────────────────────────── data ─────────────────────────────
def load_days():
    raw = json.loads(DATA_FILE.read_text())
    found = {}

    def walk(o):  # tolerant: any {date, count|contributionCount} dict, anywhere in the file
        if isinstance(o, dict):
            c = o.get("count", o.get("contributionCount"))
            if "date" in o and c is not None:
                found[date.fromisoformat(o["date"][:10])] = int(c)
            else:
                for v in o.values():
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(raw)
    if not found:
        sys.exit(f"No contribution days found in {DATA_FILE}")
    if isinstance(raw, dict) and raw.get("sample"):
        print("warning: data/contributions.json is sample data; run fetch_contributions.py", file=sys.stderr)
    return found


def stats(days):
    last = max(days)
    start = last - timedelta(days=364)
    win = [(start + timedelta(days=i)) for i in range(365)]
    cnt = [days.get(d, 0) for d in win]
    # streaks
    longest = run = 0
    for c in cnt:
        run = run + 1 if c > 0 else 0
        longest = max(longest, run)
    i = len(cnt) - 1
    if cnt[i] == 0:
        i -= 1                                  # today may not have a commit yet
    cur = 0
    while i >= 0 and cnt[i] > 0:
        cur += 1
        i -= 1
    # months: 12 calendar months ending with the last data month
    months = []
    y, m = last.year, last.month
    for _ in range(12):
        months.append((y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    months.reverse()
    per = [sum(c for d, c in days.items() if (d.year, d.month) == ym and d >= start) for ym in months]
    return dict(last=last, start=start, total=sum(cnt), active=sum(1 for c in cnt if c), span=365,
                longest=longest, current=cur, busiest=max(cnt), months=months, per=per,
                best=max(range(12), key=lambda k: per[k]))


# ───────────────────────────── portrait ─────────────────────────────
def ascii_portrait(cols=116, rows=58):
    try:
        import numpy as np
        from PIL import Image, ImageFilter, ImageOps
    except ImportError:
        return []
    if not PORTRAIT or not Path(PORTRAIT).exists():
        return []
    im = Image.open(PORTRAIT).convert("RGB")
    W, H = im.size
    l, t, r, b = PORTRAIT_CROP
    im = im.crop((int(l * W), int(t * H), int(r * W), int(b * H)))
    hi = im.resize((cols * 3, rows * 3), Image.LANCZOS)
    a = np.asarray(hi).astype(float)
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    lum = .299 * R + .587 * G + .114 * B
    sky = (B > R + 8) & (lum > 85)               # blue-ish and bright: the sky
    sky = np.asarray(Image.fromarray((sky * 255).astype("uint8")).filter(ImageFilter.MaxFilter(5))) > 127
    sub = ~sky
    lo, hi_ = np.percentile(lum[sub], [3, 97])
    tone = np.clip((lum - lo) / (hi_ - lo + 1e-6), 0, 1)
    blur = np.asarray(Image.fromarray((tone * 255).astype("uint8")).filter(ImageFilter.GaussianBlur(14))).astype(float) / 255
    v = np.clip(.5 + 1.9 * (tone - blur) + .35 * (tone - .5), 0, 1)   # local contrast keeps the face readable
    v = np.where(sub, v ** 1.1, 0)
    v[v < .22] = 0                                # drop speckle so the sky stays clean
    v = np.asarray(Image.fromarray((v * 255).astype("uint8")).resize((cols, rows), Image.BOX)).astype(float) / 255
    ramp = " .,:;-~+=*#%@"
    lines = []
    for row in v:
        lines.append("".join(ramp[min(int(x * len(ramp)), len(ramp) - 1)] for x in row).rstrip())
    return lines


# ───────────────────────────── cards ─────────────────────────────
def card_hero(S):
    W, H = 960, 400
    rows = ascii_portrait()
    fs, adv, pitch = 4.8, 4.8 * .6, 5.6
    px = W - 56 - 116 * adv
    py = (H - 58 * pitch) / 2 + pitch
    b = f'<rect width="{W}" height="{H}" rx="30" fill="{CARD}" stroke="{LINE}"/>'
    b += (f'<circle cx="{W - 190}" cy="{H / 2}" r="210" fill="url(#glow)"/>')
    # eyebrow
    b += (f'<circle cx="60" cy="62" r="4.5" fill="{ACCENT}" class="tb"{an("pulse", 2.2, 1.2, "ease-in-out", True)}/>'
          f'<text x="76" y="67" font-size="13" letter-spacing="2" fill="{MUTE}" class="fm"{an("fade", .8, .1)}>{esc(EYEBROW)}</text>')
    # name
    b += f'<g{an("rise", .9, .15)}><text x="54" y="176" font-size="112" fill="{INK}" class="fd" letter-spacing="-3">{esc(NAME_FIRST)}</text></g>'
    last = esc(NAME_LAST)
    plain = f'<text x="54" y="276" font-size="116" fill="{ACCENT}" class="fs">{last}</text>'
    if STATIC:
        b += plain
    else:
        b += (f'<g{an("rise", .9, .4)}><g class="static">{plain}</g>'
              f'<text class="fs sm" x="54" y="276" font-size="116" fill="url(#shine)">{last}</text></g>')
    for i, ln in enumerate(TAGLINE):
        b += (f'<text x="56" y="{322 + i * 26}" font-size="20" fill="{INK}" opacity=".78" class="fb"'
              f'{an("rise", .8, 1.0 + i * .12)}>{esc(ln)}</text>')
    b += (f'<g{an("rise", .8, 1.35)}><text x="56" y="378" font-size="14" fill="{ACCENT}" class="fm">{esc(SITE)}</text>'
          f'{arrow(60 + len(SITE) * 8.4 + 12, 373, ACCENT, .9, 1.6, 6)}</g>')
    # portrait, printed in row by row like a slow terminal
    for i, ln in enumerate(rows):
        lead = len(ln) - len(ln.lstrip(" "))
        b += (f'<text x="{px + lead * adv:.2f}" y="{py + i * pitch:.2f}" font-size="{fs}" fill="{INK}" '
              f'opacity=".88" class="fm" xml:space="preserve"{an("fade", .5, .5 + i * .018, "ease-out")}>{esc(ln.lstrip(" "))}</text>')
    defs = (f'<radialGradient id="glow"><stop offset="0" stop-color="{ACCENT}" stop-opacity=".10"/>'
            f'<stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/></radialGradient>')
    if not STATIC:  # the shine is a gradient whose gradientTransform is animated with SMIL
        defs += (f'<linearGradient id="shine" gradientUnits="userSpaceOnUse" x1="54" y1="0" x2="440" y2="0">'
                 f'<stop offset="0" stop-color="{ACCENT}"/><stop offset=".38" stop-color="{ACCENT}"/>'
                 f'<stop offset=".5" stop-color="#FFFFFF"/><stop offset=".62" stop-color="{ACCENT}"/>'
                 f'<stop offset="1" stop-color="{ACCENT}"/>'
                 f'<animateTransform attributeName="gradientTransform" type="translate" '
                 f'values="-460 0;460 0;460 0" keyTimes="0;.3;1" dur="6s" begin="1.8s" repeatCount="indefinite"/>'
                 f'</linearGradient>')
    return svg(W, H, f"{NAME_FIRST} {NAME_LAST}", b, "dbsm", defs)


def card_tile(t, S, idx):
    W, H = 320, 240
    d0 = T_TILES + idx * .25
    val = t["value"]
    if isinstance(val, str) and val.startswith("@"):
        val = S[val[1:]]
    b = (f'<clipPath id="clip"><rect width="{W}" height="{H}" rx="26"/></clipPath>'
         f'<g class="tb"{an("swing", 1.1, d0, "cubic-bezier(.2,.9,.25,1.1)")}>'
         f'<rect width="{W}" height="{H}" rx="26" fill="{t["bg"]}"/>')
    b += f'<text x="28" y="46" font-size="13" letter-spacing="2" fill="{t["fg"]}" opacity=".85" class="fm">{esc(t["label"])}</text>'
    b += arrow(290, 38, t["fg"], 1, d0 + 1)
    b += big(28, 142, val, t["suffix"], 46, d0 + .5, t["dec"], t["fg"])
    for i, ln in enumerate(textwrap.wrap(t["sub"], 34)[:3]):
        b += f'<text x="28" y="{180 + i * 21}" font-size="14.5" fill="{t["fg"]}" opacity=".88" class="fb">{esc(ln)}</text>'
    if not STATIC:
        b += (f'<circle cx="290" cy="38" r="14" fill="none" stroke="{t["fg"]}" stroke-width="1.6" class="tb fx"'
              f'{an("ring", 3.4, d0 + 1.4, "ease-out", True)}/>'
              f'<g clip-path="url(#clip)" class="fx"><g{an("sweep", 5.5, d0 + 2.5, "ease-in-out", True)}>'
              f'<rect x="-140" y="-20" width="70" height="300" fill="#fff" opacity=".22" transform="skewX(-18)"/></g></g>')
    b += "</g>"
    return svg(W, H, f'{t["label"]}: {val}{t["suffix"]}', b, "dbsm")


def card_chart(S):
    W, H = 960, 330
    b = f'<rect width="{W}" height="{H}" rx="30" fill="{CARD}" stroke="{LINE}"/>'
    d = T_CHART
    b += f'<text x="48" y="58" font-size="13" letter-spacing="2" fill="{MUTE}" class="fm"{an("fade", .8, d)}>THE LAST 12 MONTHS ON GITHUB</text>'
    b += big(48, 130, S["total"], " contributions", 60, d + .2, 0, INK, ACCENT, 1.3)
    base, maxh, bw, pitch, x0 = 268, 104, 36, 50, 48
    mx = max(max(S["per"]), 1)
    names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    for i, ((y, m), v) in enumerate(zip(S["months"], S["per"])):
        h = max(6, maxh * v / mx)
        x = x0 + i * pitch
        col = ACCENT if i == S["best"] else ("#34343D" if i == 11 else INK)
        bd = d + .7 + i * .07
        b += (f'<rect x="{x}" y="{base - h:.1f}" width="{bw}" height="{h:.1f}" rx="5" fill="{col}" '
              f'class="tbb"{an("grow", .8, bd)}/>')
        b += f'<text x="{x + bw / 2}" y="{base + 26}" text-anchor="middle" font-size="12" fill="{MUTE}" class="fm">{names[m - 1]}</text>'
        if i == S["best"]:
            b += (f'<text x="{x + bw / 2}" y="{base - h - 9:.1f}" text-anchor="middle" font-size="12" fill="{ACCENT}" '
                  f'class="fm tb"{an("pop", .6, bd + .7)}>{v:,}</text>')
    # right-hand stats
    sx = 720
    cur_sub = "current streak, and the longest" if S["current"] == S["longest"] else f"current streak (best {S['longest']})"
    rows = [(S["current"], " days", cur_sub, None), (S["active"], f" / {S['span']}", "days with a commit", MUTE),
            (S["busiest"], "", "on the busiest day", None)]
    for i, (v, suf, sub, sf) in enumerate(rows):
        y = 96 + i * 84
        b += big(sx, y, v, suf, 40, d + 1.0 + i * .25, 0, INK, sf or ACCENT, 1.0)
        b += f'<text x="{sx}" y="{y + 24}" font-size="13.5" fill="{MUTE}" class="fb"{an("fade", .8, d + 1.2 + i * .25)}>{esc(sub)}</text>'
        if i < 2:
            b += f'<line x1="{sx}" x2="{W - 48}" y1="{y + 42}" y2="{y + 42}" stroke="{LINE}"/>'
    return svg(W, H, f"{S['total']:,} contributions in the last 12 months", b, "dbsm")


def card_repo(r, idx):
    W, H = 960, 148
    d = T_REPOS + idx * .25
    b = (f'<g{an("rise", .8, d)}><rect width="{W}" height="{H}" rx="26" fill="{CARD}" stroke="{LINE}"/>'
         f'<circle cx="52" cy="40" r="6" fill="{r["color"]}"/>'
         f'<text x="68" y="45" font-size="13" letter-spacing="1.5" fill="{MUTE}" class="fm">{esc(r["lang"].upper())}</text>'
         f'<text x="48" y="82" font-size="28" fill="{INK}" class="fd" letter-spacing="-.5">{esc(r["name"])}</text>')
    for i, ln in enumerate(textwrap.wrap(r["desc"], 92)[:2]):
        b += f'<text x="48" y="{110 + i * 21}" font-size="14.5" fill="{MUTE}" class="fb">{esc(ln)}</text>'
    b += (f'<text x="{W - 100}" y="45" text-anchor="end" font-size="12" letter-spacing="1.5" fill="{MUTE}" class="fm">{esc(r["tags"])}</text>'
          f'<circle cx="{W - 60}" cy="{H / 2 + 2}" r="26" fill="none" stroke="{LINE}" stroke-width="1.5"/>'
          f'{arrow(W - 60, H / 2 + 2, ACCENT, 1.1, d + 1)}</g>')
    return svg(W, H, f'{r["name"]}: {r["desc"]}', b, "dbm")


def card_graph(days, S):
    W, H = 960, 296
    d = T_GRAPH
    cell, gap = 12, 4
    pitch = cell + gap
    last = S["last"]
    # weeks start on Sunday; 53 columns ending with the week of the last day
    wk_end = last - timedelta(days=(last.weekday() + 1) % 7)
    wk0 = wk_end - timedelta(weeks=52)
    nz = sorted(c for c in days.values() if c > 0)
    q = [nz[int(len(nz) * p)] for p in (.25, .5, .75)] if nz else [1, 2, 3]
    cols = [mix(CARD, "#26262E", 0) if False else "#1D1D24"] + [mix("#1D1D24", ACCENT, t) for t in (.28, .52, .76, 1)]
    lvl = lambda c: 0 if c == 0 else 1 + sum(c > x for x in q)
    gx, gy = 56, 88
    b = f'<rect width="{W}" height="{H}" rx="30" fill="{CARD}" stroke="{LINE}"/>'
    b += (f'<text x="56" y="58" font-size="30" fill="{INK}" class="fd" letter-spacing="-.5"{an("rise", .8, d)}>Every day, '
          f'<tspan class="fs" fill="{ACCENT}" font-size="34">{esc(GRAPH_WORD)}</tspan></text>'
          f'<text x="{W - 56}" y="56" text-anchor="end" font-size="12" letter-spacing="2" fill="{MUTE}" class="fm"{an("fade", .8, d)}>REFRESHED DAILY</text>')
    prev_m = None
    for w in range(53):
        ws = wk0 + timedelta(weeks=w)
        if ws.month != prev_m and ws + timedelta(days=6) <= last + timedelta(days=6):
            if prev_m is not None or ws.day <= 7:
                b += (f'<text x="{gx + w * pitch}" y="{gy + 7 * pitch + 20}" font-size="12" fill="{MUTE}" class="fm">'
                      f'{ws.strftime("%b")}</text>')
            prev_m = ws.month
        for dow in range(7):
            day = ws + timedelta(days=dow)
            if day > last or day < S["start"]:
                continue
            dl = d + .3 + w * .02 + dow * .012
            sty = "" if STATIC else f' class="c tb" style="--d:{dl:.3f}s"'
            b += (f'<rect x="{gx + w * pitch}" y="{gy + dow * pitch}" width="{cell}" height="{cell}" rx="3" '
                  f'fill="{cols[lvl(days.get(day, 0))]}"{sty}/>')
    lx = W - 56 - 5 * pitch - 40
    ly = gy + 7 * pitch + 54
    b += f'<text x="{lx}" y="{ly}" font-size="12" fill="{MUTE}" class="fm" text-anchor="end">less</text>'
    for i, c in enumerate(cols):
        b += f'<rect x="{lx + 10 + i * pitch}" y="{ly - 10}" width="{cell}" height="{cell}" rx="3" fill="{c}"/>'
    b += f'<text x="{lx + 18 + 5 * pitch}" y="{ly}" font-size="12" fill="{MUTE}" class="fm">more</text>'
    return svg(W, H, "Contribution graph for the last year", b, "dm")


def preview(files):
    imgs = "".join(f'<img src="{f}" style="display:block;width:100%;margin:0 0 8px">' for f in files)
    return (f'<!doctype html><meta charset="utf-8"><body style="margin:0;background:#0d1117;display:flex;'
            f'justify-content:center"><div style="width:830px;padding:24px 0">{imgs}</div>')


def main():
    days = load_days()
    S = stats(days)
    OUT.mkdir(parents=True, exist_ok=True)
    outputs = {"hero.svg": card_hero(S)}
    for i, t in enumerate(TILES):
        outputs[f'{t["id"]}.svg'] = card_tile(t, S, i)
    outputs["chart.svg"] = card_chart(S)
    for i, r in enumerate(REPOS):
        outputs[f'{r["id"]}.svg'] = card_repo(r, i)
    outputs["graph.svg"] = card_graph(days, S)
    for name, s in outputs.items():
        (OUT / name).write_text(s, encoding="utf-8")
        print(f"{name:26s}{len(s) / 1024:7.1f} KB")
    if STATIC:
        (OUT / "preview.html").write_text(preview(list(outputs)))
        print(f"\nOpen {OUT / 'preview.html'} in a browser and screenshot it.")


if __name__ == "__main__":
    main()
