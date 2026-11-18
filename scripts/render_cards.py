#!/usr/bin/env python3
"""
Render the profile README's cards as animated SVGs into cards/.

Design: Matched to zoubaa.dev & GitHub profile @zoubaax:
- Deep obsidian background (#070707 / #0c1017)
- Electric Cyan brand accent (#00F2EA)
- Emerald (#10b981), Amber (#f59e0b), and Sky (#38bdf8) accents
- Typography: Clash Display, Satoshi, and Fira Code subset as WOFF data URIs

Every card is a standalone SVG displayed via <img> in the README, adhering
strictly to GitHub's constraints:
- Inline CSS animations & SMIL <animate> / <set>
- Fonts subset with pyftsubset embedded as base64 WOFF
- Staggered top-to-bottom animation delays
- Full prefers-reduced-motion support
- STATIC=1 preview / screenshot mode

Run daily by .github/workflows/update-profile-art.yml.
"""
import base64
import datetime
import json
import os
import re
from html import escape

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
DATA_FILE = os.path.join(ROOT, "data", "contributions.json")
OUT_DIR = os.path.join(ROOT, "cards")
FONTS_DIR = os.path.join(ROOT, "fonts")
PORTRAIT_FILE = os.path.join(ROOT, "assets", "portrait.txt")

# ---- Brand Design Tokens ----------------------------------------------------
BG_DARK = "#070707"
CARD_BG = "#0c1017"
CARD_SURFACE = "#111622"
CARD_BORDER = "#1e2638"
RULE = "#1e293b"

BRAND_CYAN = "#00F2EA"        # Core brand accent
BRAND_SKY = "#38bdf8"         # Sky blue accent
BRAND_EMERALD = "#10b981"     # Backend & DevOps green
BRAND_AMBER = "#f59e0b"       # Hackathon Winner 1st place gold
BRAND_PURPLE = "#a855f7"      # AI / Cloud purple

TEXT_MAIN = "#f8fafc"         # Bright white
TEXT_SOFT = "#94a3b8"         # Soft slate
TEXT_MUTED = "#64748b"        # Muted slate

W = 880  # Full card width, GitHub's README column at 100%
GAP = 12
BOTTOM = 12

FONT_FAMILY_DISPLAY = "'Clash Display', -apple-system, system-ui, sans-serif"
FONT_FAMILY_BODY = "Satoshi, -apple-system, system-ui, sans-serif"
FONT_FAMILY_MONO = "'Fira Code', 'Geist Mono', ui-monospace, SFMono-Regular, monospace"

FONT_FILES = {
    "clash-600": ("Clash Display", "normal", 600, "clash-600.woff"),
    "clash-700": ("Clash Display", "normal", 700, "clash-700.woff"),
    "satoshi-400": ("Satoshi", "normal", 400, "satoshi-400.woff"),
    "satoshi-700": ("Satoshi", "normal", 700, "satoshi-700.woff"),
    "fira-400": ("Fira Code", "normal", 400, "firacode-400.woff"),
}

BASE_CSS = """
@keyframes rise{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}
@keyframes fade{from{opacity:0}to{opacity:1}}
@keyframes grow{from{transform:scaleY(0)}to{transform:scaleY(1)}}
@keyframes pop{0%{opacity:0;transform:scale(.3)}70%{opacity:1;transform:scale(1.15)}100%{opacity:1;transform:none}}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.3;transform:scale(.85)}}
@keyframes nudge{0%,100%{transform:none}50%{transform:translateX(5px)}}
@keyframes nudgeup{0%,100%{transform:none}50%{transform:translate(3px,-3px)}}
@keyframes tilein{0%{opacity:0;transform:translateY(80px) scale(.7) rotate(-7deg)}55%{opacity:1;transform:translateY(-8px) scale(1.04) rotate(1.5deg)}75%{transform:translateY(3px) scale(.99) rotate(-.6deg)}100%{opacity:1;transform:none}}
@keyframes slidein{from{opacity:0;transform:translateX(-24px)}to{opacity:1;transform:none}}
@keyframes arrowin{0%{opacity:0;transform:translateX(-25px)}60%{opacity:1;transform:translateX(5px)}100%{opacity:1;transform:none}}
@keyframes roll{from{transform:translateY(50px)}to{transform:none}}
@keyframes sheen{0%{transform:translateX(-260px) skewX(-20deg)}22%,100%{transform:translateX(440px) skewX(-20deg)}}
@keyframes ring{0%{opacity:.8;transform:scale(.25)}100%{opacity:0;transform:scale(2.5)}}

.r{opacity:0;animation:rise .8s cubic-bezier(.2,.7,.2,1) both;transform-box:fill-box}
.f{opacity:0;animation:fade .9s ease-out both}
.g{transform-box:fill-box;transform-origin:bottom;transform:scaleY(0);animation:grow .8s cubic-bezier(.2,.7,.2,1) both}
.p{opacity:0;transform-box:fill-box;transform-origin:center;animation:pop .45s ease-out both}
.live{animation:pulse 1.8s ease-in-out infinite;transform-box:fill-box;transform-origin:center}
.n{transform-box:fill-box;animation:nudge 2s ease-in-out infinite}
.nu{transform-box:fill-box;animation:nudgeup 1.8s ease-in-out infinite}
.ti{opacity:0;transform-box:fill-box;transform-origin:50% 60%;animation:tilein 1.1s cubic-bezier(.2,.8,.2,1) both}
.sl{opacity:0;transform-box:fill-box;animation:slidein .6s cubic-bezier(.2,.7,.2,1) both}
.ai{opacity:0;transform-box:fill-box;animation:arrowin .7s cubic-bezier(.2,.7,.2,1) both}
.ro{transform-box:fill-box;animation:roll .8s cubic-bezier(.15,.8,.2,1) both}
.sh{animation:sheen 5.5s ease-in-out infinite}
.rg{opacity:0;transform-box:fill-box;transform-origin:center;animation:ring 1.1s ease-out both}

@media (prefers-reduced-motion: reduce){
  .r,.f,.g,.p,.live,.n,.nu,.ti,.sl,.ai,.ro,.rg{animation:none!important;opacity:1!important;transform:none!important}
  .sh,.rg{display:none!important}
}
"""


def font_face(keys):
    out = []
    for k in keys:
        if k not in FONT_FILES:
            continue
        fam, style, weight, fn = FONT_FILES[k]
        path = os.path.join(FONTS_DIR, fn)
        if os.path.exists(path):
            b64 = base64.b64encode(open(path, "rb").read()).decode()
            out.append(
                f"@font-face{{font-family:'{fam}';font-style:{style};font-weight:{weight};"
                f"src:url(data:font/woff;base64,{b64}) format('woff');font-display:swap;}}"
            )
    return "".join(out)


def svg(w, h, body, fonts, label, extra_css="", left=0, right=0, bottom=BOTTOM):
    """Render self-contained SVG card padded to align on GitHub's column grid."""
    if left:
        body = f'<g transform="translate({left:.3f} 0)">{body}</g>'
    w_total, h_total = w + left + right, h + bottom
    css = font_face(fonts) + BASE_CSS + extra_css
    if os.environ.get("STATIC"):
        css += (
            "\n.r,.f,.g,.p,.live,.n,.nu,.ti,.sl,.ai,.ro{animation:none!important;opacity:1!important;transform:none!important}"
            "\n.sh,.rg{display:none!important}"
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w_total:.3f}" height="{h_total}" '
        f'viewBox="0 0 {w_total:.3f} {h_total}" role="img" aria-label="{escape(label)}">'
        f"<title>{escape(label)}</title><style>{css}</style>{body}</svg>"
    )


def write_card(filename, content):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    kb = len(content.encode("utf-8")) / 1024
    print(f"wrote cards/{filename} ({kb:.1f} KB)")


def d(sec):
    return f'style="animation-delay:{sec:.2f}s"'


def wrap_text(text, max_len):
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > max_len:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        lines.append(line)
    return lines


def text_lines(x, y, lines, line_height, attrs):
    return "".join(
        f'<text x="{x}" y="{y + i * line_height}" {attrs}>{escape(l)}</text>'
        for i, l in enumerate(lines)
    )


# ==============================================================================
# 1. HERO CARD
# ==============================================================================
def render_hero():
    h = 420
    portrait_svg = []

    if os.path.exists(PORTRAIT_FILE):
        raw_lines = [line.rstrip() for line in open(PORTRAIT_FILE).readlines() if line.strip()]
        for i, txt in enumerate(raw_lines[:36]):
            delay = 0.20 + i * 0.016
            portrait_svg.append(
                f'<text class="f" style="animation-delay:{delay:.3f}s;animation-duration:.35s" '
                f'xml:space="preserve" x="20" y="{26 + i * 11}" fill="{BRAND_CYAN}" opacity="0.82" '
                f'font-size="8.8" font-family="{FONT_FAMILY_MONO}">{escape(txt)}</text>'
            )

    body = f"""
<defs>
  <linearGradient id="cyan-sweep" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="650" y2="0">
    <stop offset="0" stop-color="{TEXT_MAIN}"/>
    <stop offset=".40" stop-color="{TEXT_MAIN}"/>
    <stop offset=".50" stop-color="{BRAND_CYAN}"/>
    <stop offset=".60" stop-color="{TEXT_MAIN}"/>
    <stop offset="1" stop-color="{TEXT_MAIN}"/>
    <animateTransform attributeName="gradientTransform" type="translate" values="-650 0;650 0;650 0"
      keyTimes="0;.45;1" dur="6.5s" begin="1.4s" repeatCount="indefinite"/>
  </linearGradient>
  <linearGradient id="hero-border" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="{BRAND_CYAN}" stop-opacity=".45"/>
    <stop offset="50%" stop-color="{CARD_BORDER}" stop-opacity=".7"/>
    <stop offset="100%" stop-color="{BRAND_SKY}" stop-opacity=".3"/>
  </linearGradient>
</defs>

<!-- Card Base -->
<rect width="{W}" height="{h}" rx="16" fill="{CARD_BG}" stroke="url(#hero-border)" stroke-width="1.2"/>

<!-- Kicker / Live Status -->
<g class="f" {d(0.05)}>
  <rect class="live" x="48" y="46" width="9" height="9" rx="2" fill="{BRAND_EMERALD}"/>
  <text x="68" y="55" font-family="{FONT_FAMILY_MONO}" font-size="11.5" letter-spacing="1.2" fill="{TEXT_MUTED}">FULL-STACK SOFTWARE ENGINEER &amp; DEVOPS</text>
</g>

<!-- Name -->
<text class="r" {d(0.18)} x="46" y="145" font-family="{FONT_FAMILY_DISPLAY}" font-weight="700" font-size="78" letter-spacing="-1.5" fill="{TEXT_MAIN}">Mohammed</text>
<text class="r" {d(0.32)} x="46" y="222" font-family="{FONT_FAMILY_DISPLAY}" font-weight="700" font-size="78" letter-spacing="-1.5" fill="url(#cyan-sweep)">Zoubaa</text>

<!-- One-line Bio & Highlights -->
<g class="r" {d(0.50)}>
  {text_lines(48, 272, [
      "Crafting scalable distributed backends, microservices & modern web UIs.",
      "1st Place Winner at Build with Gemma Hackathon 2026."
  ], 25, f'font-family="{FONT_FAMILY_BODY}" font-size="16" fill="{TEXT_SOFT}"')}
</g>

<!-- Bottom Metadata & Links -->
<g class="f" {d(0.75)}>
  <text x="48" y="365" font-family="{FONT_FAMILY_MONO}" font-size="12" fill="{TEXT_MUTED}">PORTFOLIO</text>
  <text x="136" y="365" font-family="{FONT_FAMILY_MONO}" font-size="13" font-weight="600" fill="{BRAND_CYAN}">zoubaa.dev</text>
  <text class="nu" x="228" y="365" font-family="{FONT_FAMILY_MONO}" font-size="13" fill="{BRAND_CYAN}">&#8599;</text>

  <text x="270" y="365" font-family="{FONT_FAMILY_MONO}" font-size="12" fill="{TEXT_MUTED}">LOC</text>
  <text x="306" y="365" font-family="{FONT_FAMILY_MONO}" font-size="13" fill="{TEXT_MAIN}">Morocco &#183; Open to Remote</text>
</g>

<!-- ASCII Portrait Terminal Panel -->
<g transform="translate(530 42)">
  <rect width="308" height="336" rx="12" fill="#080c14" stroke="{CARD_BORDER}" stroke-width="1"/>
  <circle cx="22" cy="18" r="4" fill="#ef4444" opacity=".8"/>
  <circle cx="36" cy="18" r="4" fill="#eab308" opacity=".8"/>
  <circle cx="50" cy="18" r="4" fill="#22c55e" opacity=".8"/>
  <text x="70" y="22" font-family="{FONT_FAMILY_MONO}" font-size="10" fill="{TEXT_MUTED}">zoubaa@dev:~$ portrait</text>
  <g transform="translate(6 28) scale(0.68)">
    {''.join(portrait_svg)}
  </g>
</g>
"""
    write_card(
        "hero.svg",
        svg(
            W,
            h,
            body,
            ["clash-700", "satoshi-400", "satoshi-700", "fira-400"],
            "Mohammed Zoubaa - Full-Stack Software Engineer & DevOps",
        ),
    )


# ==============================================================================
# 2. THREE LINKED TILES (BUILD, INNOVATE, CONNECT)
# ==============================================================================
TILE_W, TILE_H = 880 / 3 - 8, 215  # 285.333 px


def count_up_animation(num, word, x, y, attrs, begin, dur=1.1, frames=18):
    """Number counts up with SMIL <set> frames (runs natively inside <img>)."""
    m = re.match(r"([\d.,]+)(.*)", num)
    if not m:
        return f'<text x="{x}" y="{y}" {attrs}>{escape(num)} {escape(word)}</text>'

    num_str, suf = m.group(1).replace(",", ""), m.group(2)
    val = float(num_str)
    has_comma = "," in m.group(1)
    dec = len(num_str.split(".")[1]) if "." in num_str else 0
    tail = f' <tspan font-family="{FONT_FAMILY_BODY}" font-size="17" fill="{TEXT_MUTED}">{escape(word)}</tspan>'

    if os.environ.get("STATIC"):
        formatted = f"{int(val):,}" if has_comma else num
        return f'<text x="{x}" y="{y}" {attrs}>{escape(formatted)}{tail}</text>'

    out = []
    for i in range(frames + 1):
        e = 1 - (1 - i / frames) ** 3
        cur = val * e
        if has_comma:
            txt = f"{int(round(cur)):,}{suf}" if i < frames else num
        else:
            txt = f"{cur:.{dec}f}{suf}" if i < frames else num

        on = begin + dur * i / frames
        off = "" if i == frames else f'<set attributeName="opacity" to="0" begin="{begin + dur * (i + 1) / frames:.3f}s"/>'
        out.append(
            f'<text x="{x}" y="{y}" {attrs} opacity="0">{escape(txt)}{tail}'
            f'<set attributeName="opacity" to="1" begin="{on:.3f}s"/>{off}</text>'
        )
    return "".join(out)


def render_tile(name, label, accent_color, num, word, blurb, delay, pos):
    lines = wrap_text(blurb, 32)
    blurb_svg = "".join(
        f'<text class="r" {d(delay + 0.65 + i * 0.08)} x="24" y="{154 + i * 20}" '
        f'font-family="{FONT_FAMILY_BODY}" font-size="13.5" fill="{TEXT_SOFT}">{escape(l)}</text>'
        for i, l in enumerate(lines)
    )

    body = f"""
<defs>
  <clipPath id="tile-clip-{name}"><rect width="{TILE_W:.2f}" height="{TILE_H}" rx="14"/></clipPath>
  <clipPath id="num-slot-{name}"><rect x="0" y="58" width="{TILE_W:.2f}" height="66"/></clipPath>
  <linearGradient id="sheen-grad-{name}" x1="0" x2="1">
    <stop offset="0" stop-color="#fff" stop-opacity="0"/>
    <stop offset=".5" stop-color="#fff" stop-opacity=".22"/>
    <stop offset="1" stop-color="#fff" stop-opacity="0"/>
  </linearGradient>
</defs>

<g class="ti" {d(delay)}>
  <g clip-path="url(#tile-clip-{name})">
    <!-- Tile Background -->
    <rect width="{TILE_W:.2f}" height="{TILE_H}" rx="14" fill="{CARD_BG}" stroke="{CARD_BORDER}" stroke-width="1.2"/>
    
    <!-- Top accent border glow -->
    <rect x="0" y="0" width="{TILE_W:.2f}" height="3" fill="{accent_color}"/>

    <!-- Pulsing ring from corner -->
    <circle class="rg" {d(delay + 0.45)} cx="{TILE_W - 35:.2f}" cy="{TILE_H - 35}" r="55" fill="none" stroke="{accent_color}" stroke-opacity=".4" stroke-width="2"/>
    
    <!-- Sweeping sheen -->
    <rect class="sh" style="animation-delay:{delay + 1.2:.2f}s" x="0" y="-20" width="85" height="{TILE_H + 40}" fill="url(#sheen-grad-{name})" transform="translate(-260 0)"/>
  </g>

  <!-- Header label -->
  <g class="sl" {d(delay + 0.25)}>
    <rect x="24" y="26" width="6" height="6" rx="1.5" fill="{accent_color}"/>
    <text x="38" y="33" font-family="{FONT_FAMILY_MONO}" font-size="11.5" letter-spacing="1.5" fill="{TEXT_MAIN}">{label}</text>
  </g>

  <!-- Arrow -->
  <g class="ai" {d(delay + 0.35)}>
    <text class="n" style="animation-delay:{delay + 1.1:.2f}s" x="{TILE_W - 34:.2f}" y="33" font-family="{FONT_FAMILY_MONO}" font-size="14" fill="{accent_color}">&#8594;</text>
  </g>

  <!-- Number Count-up in slot -->
  <g clip-path="url(#num-slot-{name})">
    <g class="ro" {d(delay + 0.40)}>
      {count_up_animation(num, word, 22, 110, f'font-family="{FONT_FAMILY_DISPLAY}" font-weight="700" font-size="44" fill="{TEXT_MAIN}"', delay + 0.40)}
    </g>
  </g>

  <!-- Blurb description -->
  {blurb_svg}
</g>
"""
    write_card(
        f"tile-{name}.svg",
        svg(
            TILE_W,
            TILE_H,
            body,
            ["clash-700", "satoshi-400", "satoshi-700", "fira-400"],
            f"{label}: {num} {word}. {blurb}",
            left=4 * pos,
            right=8 - 4 * pos,
        ),
    )


# ==============================================================================
# 3. CONTRIBUTION GRAPH (HEATMAP IN BRAND CYAN)
# ==============================================================================
CYAN_SCALE = [
    "#121722",   # Level 0: dark empty slate
    "#0b3d47",   # Level 1: deep teal
    "#096875",   # Level 2: medium teal
    "#0891a2",   # Level 3: bright cyan/teal
    "#00cdd8",   # Level 4: vibrant cyan
    BRAND_CYAN,  # Level 5: electric cyan #00F2EA
]


def level_for_count(c):
    if c == 0:
        return 0
    if c <= 2:
        return 1
    if c <= 5:
        return 2
    if c <= 10:
        return 3
    if c <= 20:
        return 4
    return 5


def render_heatmap(data):
    days = data["days"]
    first = datetime.date.fromisoformat(days[0]["date"])
    lead = (first.weekday() + 1) % 7  # sunday = 0
    cell, step, gx, gy = 12, 15, 44, 88
    cells, months, seen = [], [], set()

    for i, day in enumerate(days):
        k = i + lead
        col, row = divmod(k, 7)
        date = datetime.date.fromisoformat(day["date"])
        if date.day <= 7 and (date.year, date.month) not in seen and row == 0:
            seen.add((date.year, date.month))
            months.append((col, date.strftime("%b")))

        c = day["count"]
        delay = 0.85 + col * 0.024 + row * 0.015
        color = CYAN_SCALE[level_for_count(c)]
        cells.append(
            f'<rect class="p" style="animation-delay:{delay:.2f}s" x="{gx + col * step}" y="{gy + row * step}" '
            f'width="{cell}" height="{cell}" rx="2.5" fill="{color}">'
            f'<title>{day["date"]}: {c} contribution{"s" if c != 1 else ""}</title></rect>'
        )

    ncols = (len(days) + lead + 6) // 7
    right = gx + ncols * step - 3
    labels = "".join(
        f'<text x="{gx + col * step}" y="{gy + 7 * step + 18}" font-family="{FONT_FAMILY_MONO}" font-size="11" fill="{TEXT_MUTED}">{m}</text>'
        for col, m in months
        if col < ncols - 6
    )

    legend_x = right - len(CYAN_SCALE) * 15
    legend = "".join(
        f'<rect x="{legend_x + i * 15}" y="{gy + 7 * step + 8}" width="11" height="11" rx="2.5" fill="{c}"/>'
        for i, c in enumerate(CYAN_SCALE)
    )
    h = gy + 7 * step + 42

    body = f"""
<rect width="{W}" height="{h}" rx="16" fill="{CARD_BG}" stroke="{CARD_BORDER}" stroke-width="1.2"/>
<text class="r" {d(0.7)} x="44" y="52" font-family="{FONT_FAMILY_DISPLAY}" font-weight="700" font-size="28" fill="{TEXT_MAIN}">Every day, <tspan fill="{BRAND_CYAN}">in cyan</tspan></text>
<text class="f" {d(0.7)} x="{right}" y="50" text-anchor="end" font-family="{FONT_FAMILY_MONO}" font-size="11" letter-spacing="1" fill="{TEXT_MUTED}">REFRESHED DAILY</text>
{''.join(cells)}
<g class="f" {d(2.1)}>
  {labels}
  <text x="{legend_x - 10}" y="{gy + 7 * step + 18}" text-anchor="end" font-family="{FONT_FAMILY_MONO}" font-size="10.5" fill="{TEXT_MUTED}">less</text>
  {legend}
  <text x="{legend_x + len(CYAN_SCALE) * 15 + 4}" y="{gy + 7 * step + 18}" font-family="{FONT_FAMILY_MONO}" font-size="10.5" fill="{TEXT_MUTED}">more</text>
</g>
"""
    write_card(
        "heatmap.svg",
        svg(
            W,
            h,
            body,
            ["clash-700", "fira-400"],
            f'Contribution Graph: {data["total_contributions"]:,} contributions in the last year',
        ),
    )


# ==============================================================================
# 4. ACTIVITY CHART (MONTHLY BREAKDOWN & STREAK STATS)
# ==============================================================================
def render_activity(data):
    h = 340
    monthly = data["monthly"][-12:]
    best = max(monthly[:-1] or monthly, key=lambda m: m["total"])
    top = max(best["total"], 1)

    x0, x1, base, maxh, gap = 44, 580, 286, 135, 10
    bw = (x1 - x0 - gap * (len(monthly) - 1)) / len(monthly)
    bars = []

    for i, m in enumerate(monthly):
        partial = i == len(monthly) - 1
        is_best = m is best
        bh = max(6, round(m["total"] / top * maxh))
        x = x0 + i * (bw + gap)
        fill = BRAND_CYAN if is_best else ("#253248" if partial else "#182234")
        label = datetime.date.fromisoformat(m["month"] + "-01").strftime("%b")

        bars.append(
            f'<rect class="g" style="animation-delay:{2.0 + i * 0.06:.2f}s" x="{x:.1f}" y="{base - bh}" '
            f'width="{bw:.1f}" height="{bh}" rx="4" fill="{fill}"><title>{label}: {m["total"]:,}</title></rect>'
            f'<text class="f" style="animation-delay:{2.0 + i * 0.06:.2f}s" x="{x + bw / 2:.1f}" y="{base + 22}" '
            f'text-anchor="middle" font-family="{FONT_FAMILY_MONO}" font-size="11" fill="{TEXT_MUTED}">{label}</text>'
        )

        if is_best:
            bars.append(
                f'<text class="p" style="animation-delay:2.9s" x="{x + bw / 2:.1f}" y="{base - bh - 8}" '
                f'text-anchor="middle" font-family="{FONT_FAMILY_MONO}" font-weight="600" font-size="11.5" fill="{BRAND_CYAN}">{m["total"]:,}</text>'
            )

    cs = data["current_streak"]["length"]
    ls = data["longest_streak"]["length"]
    streak_note = "current streak, and the longest" if cs >= ls else f"current streak, longest {ls} days"
    total_days = len(data["days"])
    active_days = data["active_days"]

    stats = [
        (f'{cs} <tspan font-family="{FONT_FAMILY_BODY}" font-size="18" fill="{TEXT_MUTED}">days</tspan>', streak_note),
        (f'{active_days} <tspan font-family="{FONT_FAMILY_BODY}" font-size="18" fill="{TEXT_MUTED}">/ {total_days}</tspan>', "days with a commit"),
        (f'{data["best_day"]["count"]}', f'commits on busiest day ({data["best_day"]["date"]})'),
    ]

    side = []
    for i, (big, small) in enumerate(stats):
        y = 100 + i * 86
        side.append(
            f'<g class="r" {d(2.4 + i * 0.14)}>'
            f'<text x="630" y="{y}" font-family="{FONT_FAMILY_DISPLAY}" font-weight="700" font-size="34" fill="{TEXT_MAIN}">{big}</text>'
            f'<text x="630" y="{y + 22}" font-family="{FONT_FAMILY_BODY}" font-size="13.5" fill="{TEXT_MUTED}">{small}</text></g>'
        )
        if i < 2:
            side.append(f'<rect class="f" {d(2.4)} x="630" y="{y + 38}" width="206" height="1" fill="{RULE}"/>')

    body = f"""
<rect width="{W}" height="{h}" rx="16" fill="{CARD_BG}" stroke="{CARD_BORDER}" stroke-width="1.2"/>
<text class="f" {d(1.8)} x="44" y="50" font-family="{FONT_FAMILY_MONO}" font-size="11.5" letter-spacing="1.2" fill="{TEXT_MUTED}">THE LAST 12 MONTHS ON GITHUB</text>
<text class="r" {d(1.9)} x="42" y="104" font-family="{FONT_FAMILY_DISPLAY}" font-weight="700" font-size="46" fill="{TEXT_MAIN}">{data["total_contributions"]:,} <tspan font-family="{FONT_FAMILY_BODY}" font-size="22" font-weight="400" fill="{BRAND_CYAN}">contributions</tspan></text>
{''.join(bars)}
{''.join(side)}
"""
    write_card(
        "activity.svg",
        svg(
            W,
            h,
            body,
            ["clash-700", "satoshi-400", "satoshi-700", "fira-400"],
            f'{data["total_contributions"]:,} contributions in the last year, {cs}-day streak',
        ),
    )


# ==============================================================================
# 5. FEATURED REPO CARDS
# ==============================================================================
REPO_W, REPO_H = 880 / 3 - 8, 176
FEATURED_REPOS = [
    ("ats-nexus", "AI-powered ATS CV Maker & Checker with Multi-LLM support (Groq, Gemini, BYOK).", "Python", BRAND_SKY, 0),
    ("gemma-hackathon", "1st Place Winner at Build with Gemma Hackathon Casablanca: AI developer toolkit.", "Python", BRAND_AMBER, 1),
    ("linkmakeup", "Digital identity & portfolio bio-link SaaS platform for creators and developers.", "JavaScript", BRAND_EMERALD, 0),
]


def render_repo_card(i, name, desc, lang, color, stars):
    delay = 3.8 + i * 0.12
    meta = f"{lang}  &#183;  &#9733; {stars}" if stars else f"{lang}  &#183;  featured"
    lines = wrap_text(desc, 32)
    desc_svg = text_lines(24, 68, lines, 20, f'font-family="{FONT_FAMILY_BODY}" font-size="13.5" fill="{TEXT_SOFT}"')

    body = f"""
<rect width="{REPO_W:.2f}" height="{REPO_H}" rx="14" fill="{CARD_BG}" stroke="{CARD_BORDER}" stroke-width="1.2"/>
<rect x="0" y="0" width="{REPO_W:.2f}" height="2.5" fill="{color}"/>
<g class="r" {d(delay)}>
  <rect x="24" y="26" width="7" height="7" rx="1.5" fill="{color}"/>
  <text x="38" y="34" font-family="{FONT_FAMILY_DISPLAY}" font-weight="600" font-size="17" fill="{TEXT_MAIN}">{escape(name)}</text>
  {desc_svg}
  <text x="24" y="{REPO_H - 22}" font-family="{FONT_FAMILY_MONO}" font-size="11.5" fill="{TEXT_MUTED}">{escape(meta)}</text>
</g>
"""
    write_card(
        f"repo-{name}.svg",
        svg(
            REPO_W,
            REPO_H,
            body,
            ["clash-600", "satoshi-400", "satoshi-700", "fira-400"],
            f"{name}: {desc}",
            left=4 * i,
            right=8 - 4 * i,
        ),
    )


def render_section_title(title_text, accent_text):
    body = (
        f'<text class="r" {d(3.5)} x="4" y="44" font-family="{FONT_FAMILY_DISPLAY}" font-weight="700" font-size="32" fill="{TEXT_MAIN}">'
        f'{escape(title_text)} <tspan fill="{BRAND_CYAN}">{escape(accent_text)}</tspan></text>'
    )
    write_card(
        "title-projects.svg",
        svg(W, 60, body, ["clash-700"], f"{title_text} {accent_text}", bottom=0),
    )


# ==============================================================================
# MAIN ORCHESTRATOR
# ==============================================================================
if __name__ == "__main__":
    if not os.path.exists(DATA_FILE):
        print(f"data file missing: {DATA_FILE}. Run fetch_contributions.py first.")
        exit(1)

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("Rendering SVG Cards...")
    # 1. Hero
    render_hero()

    # 2. Contribution Heatmap
    render_heatmap(data)

    # 3. Monthly Activity Breakdown
    render_activity(data)

    # 4. Three Linked World Tiles
    render_tile(
        name="build",
        label="SYSTEMS",
        accent_color=BRAND_CYAN,
        num=f"{data['total_contributions']:,}",
        word="commits",
        blurb="Microservices, Spring Boot, Docker, Kubernetes & automated CI/CD.",
        delay=2.7,
        pos=0,
    )
    render_tile(
        name="innovate",
        label="HACKATHONS",
        accent_color=BRAND_AMBER,
        num="1st",
        word="place",
        blurb="Build with Gemma Hackathon Winner (Casablanca). AI & LLM tooling.",
        delay=2.9,
        pos=1,
    )
    render_tile(
        name="connect",
        label="EXPAND",
        accent_color=BRAND_EMERALD,
        num=f"{data['active_days']}",
        word="active days",
        blurb="Bio-link SaaS, full-stack open-source apps & articles on zoubaa.dev.",
        delay=3.1,
        pos=2,
    )

    # 5. Featured Repos
    render_section_title("Featured", "Projects")
    for i, (name, desc, lang, color, stars) in enumerate(FEATURED_REPOS):
        render_repo_card(i, name, desc, lang, color, stars)

    print("All animated SVG cards rendered successfully into cards/!")
