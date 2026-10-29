"""SVG charts for the profile README, rendered from merged ledger items.

Every bar, column and segment carries data-* attributes with the number it
draws, so tests can check each chart against data/ledger.json.
"""
import html
import math
from collections import OrderedDict

MONO = "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace"
TIMELINE_START = "2026-07"
INTERACTIVE_URL = "https://adityaai.dev/upstream"
DURATION = 1.5
STYLE = """<style>
    .grow-x { transform-box: fill-box; transform-origin: left center; animation: grow-x 0.6s cubic-bezier(.2,.7,.2,1) both; }
    .grow-y { transform-box: fill-box; transform-origin: center bottom; animation: grow-y 0.6s cubic-bezier(.2,.7,.2,1) both; }
    .fade { animation: fade 0.35s ease-out both; }
    .draw { stroke-dasharray: 1; stroke-dashoffset: 0; animation: draw 0.9s ease-in-out both; }
    @keyframes grow-x { from { transform: scaleX(0); } to { transform: scaleX(1); } }
    @keyframes grow-y { from { transform: scaleY(0); } to { transform: scaleY(1); } }
    @keyframes fade { from { opacity: 0; } to { opacity: 1; } }
    @keyframes draw { from { stroke-dashoffset: 1; } to { stroke-dashoffset: 0; } }
    @media (prefers-reduced-motion: reduce) { .grow-x, .grow-y, .fade, .draw { animation: none; } }
  </style>"""
WIDTH = 840
# Sizes are in SVG units. The README shows every chart full width (about 830px
# on desktop), so these are close to the on-screen pixel sizes.
LABEL = 17     # project names, month names, values
HEADER = 14    # card title
ROW = 40       # vertical step between bars
BAR = 26       # bar thickness
TOP = 84       # first row below the card title
THEMES = {
    "dark": {"bg": "#09090b", "border": "#27272a", "text": "#fafafa", "muted": "#a1a1aa",
             "accent": "#CAFF4A", "accent_text": "#CAFF4A", "track": "#18181b", "bar_stroke": "none",
             "second": "#52525b"},
    "light": {"bg": "#ffffff", "border": "#e4e4e7", "text": "#09090b", "muted": "#52525b",
              "accent": "#CAFF4A", "accent_text": "#3f6212", "track": "#f4f4f5", "bar_stroke": "#3f6212",
              "second": "#a1a1aa"},
}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
e = html.escape


def by_project(items, name_of):
    groups = OrderedDict()
    for p in sorted(items, key=lambda p: p["merged_at"]):
        groups.setdefault(p["repo"], []).append(p)
    return sorted(((name_of(r), prs) for r, prs in groups.items()), key=lambda g: (-len(g[1]), g[0].lower()))


def months(items):
    last = max([p["merged_at"][:7] for p in items] + [TIMELINE_START])
    y, m = map(int, TIMELINE_START.split("-"))
    out = []
    while f"{y:04d}-{m:02d}" <= last:
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def delay(i, n, span=0.9):
    """Stagger start times so the last element finishes within DURATION."""
    step = min(0.12, span / max(n - 1, 1))
    return f'style="animation-delay:{i * step:.2f}s"'


def frame(t, height, header, label, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
            f'viewBox="0 0 {WIDTH} {height}" role="img" aria-label="{e(label)}">\n'
            f'  {STYLE}\n'
            f'  <rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{height - 1}" rx="14" fill="{t["bg"]}" stroke="{t["border"]}"/>\n'
            f'  <circle cx="34" cy="40" r="5" fill="{t["accent"]}" stroke="{t["bar_stroke"]}"/>\n'
            f'  <text x="50" y="45" fill="{t["accent_text"]}" font-family="{e(MONO)}" font-size="{HEADER}" font-weight="700" letter-spacing="2">{e(header)}</text>\n'
            + "".join(f"  {line}\n" for line in body) + "</svg>\n")


def text(x, y, s, fill, size=LABEL, anchor="start", weight="400", extra=""):
    return (f'<text {extra}x="{x}" y="{y}" fill="{fill}" font-family="{e(MONO)}" font-size="{size}" '
            f'font-weight="{weight}" text-anchor="{anchor}">{e(str(s))}</text>')


def projects_chart(items, name_of, theme):
    t = THEMES[theme]
    groups = by_project(items, name_of)
    top = max(len(prs) for _, prs in groups)
    x0, span = 240, 520
    body = []
    for i, (name, prs) in enumerate(groups):
        y = TOP + i * ROW
        w = max(6, round(span * len(prs) / top))
        body.append(text(28, y + BAR // 2 + 6, name, t["text"]))
        body.append(f'<rect x="{x0}" y="{y}" width="{span}" height="{BAR}" rx="5" fill="{t["track"]}"/>')
        body.append(f'<rect class="grow-x" {delay(i, len(groups))} data-label="{e(name)}" data-value="{len(prs)}" '
                    f'x="{x0}" y="{y}" width="{w}" height="{BAR}" rx="5" fill="{t["accent"]}" stroke="{t["bar_stroke"]}"/>')
        body.append(text(x0 + w + 12, y + BAR // 2 + 6, len(prs), t["text"], weight="700",
                         extra=f'class="fade" style="animation-delay:{DURATION - 0.35:.2f}s" '))
    label = "Merged PRs by project: " + ", ".join(f"{n} {len(p)}" for n, p in groups)
    return frame(t, TOP + len(groups) * ROW + 18, f"MERGED PRS BY PROJECT · {len(items)} TOTAL", label, body)


def timeline_chart(items, theme):
    t = THEMES[theme]
    ms = months(items)
    counts = [sum(1 for p in items if p["merged_at"][:7] == m) for m in ms]
    top = max(counts) or 1
    base, tall = 272, 160
    slot = (WIDTH - 96) / len(ms)
    # Monospace glyphs are about 0.6em wide. Drop the year from month labels
    # once "Aug 2026" no longer fits its slot, then label every step-th month,
    # so labels never overlap however long the ledger runs.
    glyph = 0.6 * LABEL
    full = slot >= 8 * glyph + 12
    step = 1 if full else math.ceil((3 * glyph + 12) / slot)
    shown_year = None
    body = [f'<line x1="48" y1="{base}" x2="{WIDTH - 48}" y2="{base}" stroke="{t["border"]}"/>']
    points = []
    for i, (m, c) in enumerate(zip(ms, counts)):
        cx = 48 + slot * (i + 0.5)
        h = round(tall * c / top)
        w = min(120, slot * 0.55)
        name = f"{MONTHS[int(m[5:]) - 1]} {m[:4]}"
        points.append(f"{cx:.1f},{base - h}")
        body.append(f'<rect class="grow-y" {delay(i, len(ms), 0.5)} data-label="{m}" data-value="{c}" '
                    f'x="{cx - w / 2:.1f}" y="{base - h}" width="{w:.1f}" height="{h}" rx="4" '
                    f'fill="{t["accent"]}" fill-opacity="0.35" stroke="{t["bar_stroke"] if c else "none"}"/>')
        body.append(text(round(cx), base - h - 16, c, t["text"], size=LABEL + 3, anchor="middle", weight="700",
                         extra=f'class="fade" style="animation-delay:{DURATION - 0.35:.2f}s" '))
        if i % step == 0:
            body.append(text(round(cx), base + 30, name if full else name[:3], t["muted"], anchor="middle"))
            if not full and m[:4] != shown_year:
                shown_year = m[:4]
                body.append(text(round(cx), base + 50, m[:4], t["muted"], size=LABEL - 3, anchor="middle"))
    body.append(f'<polyline class="draw" style="animation-delay:0.6s" pathLength="1" points="{" ".join(points)}" '
                f'fill="none" stroke="{t["accent_text"]}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>')
    for i, pt in enumerate(points):
        x, y = pt.split(",")
        body.append(f'<circle class="fade" style="animation-delay:{min(0.6 + 0.9 * i / max(len(points) - 1, 1), DURATION - 0.35):.2f}s" '
                    f'cx="{x}" cy="{y}" r="6" fill="{t["accent"]}" stroke="{t["bg"]}" stroke-width="2"/>')
    label = "Merges per month: " + ", ".join(
        f"{MONTHS[int(m[5:]) - 1]} {m[:4]} {c}" for m, c in zip(ms, counts))
    first = f"{MONTHS[int(ms[0][5:]) - 1].upper()} {ms[0][:4]}"
    return frame(t, base + (56 if full else 70), f"MERGES PER MONTH · SINCE {first}", label, body)


def proofs_chart(items, name_of, theme):
    t = THEMES[theme]
    groups = by_project(items, name_of)
    tested = sum(1 for p in items if p["proof"])
    size, gap, x0 = BAR - 4, 6, 240
    body, seen = [], 0
    for i, (name, prs) in enumerate(groups):
        y = TOP + i * ROW
        n = sum(1 for p in prs if p["proof"])
        body.append(text(28, y + size // 2 + 6, name, t["text"]))
        body.append(f'<g data-label="{e(name)}" data-tested="{n}" data-total="{len(prs)}">')
        for j, p in enumerate(sorted(prs, key=lambda p: not p["proof"])):
            x = x0 + j * (size + gap)
            k, seen = seen, seen + 1
            fade = f'class="fade" {delay(k, len(items), 1.1)} '
            if p["proof"]:
                body.append(f'  <rect {fade}x="{x}" y="{y}" width="{size}" height="{size}" rx="3" fill="{t["accent"]}" stroke="{t["bar_stroke"]}"/>')
            else:
                body.append(f'  <rect {fade}x="{x + 0.5}" y="{y + 0.5}" width="{size - 1}" height="{size - 1}" rx="3" fill="none" stroke="{t["second"]}"/>')
        body.append("</g>")
        body.append(text(x0 + len(prs) * (size + gap) + 8, y + size // 2 + 6, f"{n}/{len(prs)}", t["muted"]))
    h = TOP + len(groups) * ROW
    body.append(f'<rect x="28" y="{h + 2}" width="16" height="16" rx="3" fill="{t["accent"]}" stroke="{t["bar_stroke"]}"/>')
    body.append(text(54, h + 16, "ships a regression test", t["muted"], size=LABEL - 2))
    body.append(f'<rect x="328.5" y="{h + 2.5}" width="15" height="15" rx="3" fill="none" stroke="{t["second"]}"/>')
    body.append(text(354, h + 16, "no test", t["muted"], size=LABEL - 2))
    label = f"{tested} of {len(items)} merged fixes ship a regression test"
    return frame(t, h + 40, f"{tested} OF {len(items)} MERGED FIXES SHIP A REGRESSION TEST", label, body)


def lines_chart(items, name_of, theme):
    t = THEMES[theme]
    groups = by_project(items, name_of)
    sums = [(n, sum(p["additions"] for p in prs), sum(p["deletions"] for p in prs)) for n, prs in groups]
    sums.sort(key=lambda s: (-(s[1] + s[2]), s[0].lower()))
    top = max(a + d for _, a, d in sums) or 1
    x0, span = 240, 440
    body = []
    for i, (name, a, d) in enumerate(sums):
        y = TOP + i * ROW
        wa, wd = round(span * a / top), round(span * d / top)
        body.append(text(28, y + BAR // 2 + 6, name, t["text"]))
        body.append(f'<rect class="grow-x" {delay(i, len(sums), 0.6)} data-label="{e(name)}" data-kind="additions" data-value="{a}" x="{x0}" y="{y}" '
                    f'width="{max(wa, 2)}" height="{BAR}" rx="5" fill="{t["accent"]}" stroke="{t["bar_stroke"]}"/>')
        body.append(f'<rect class="grow-x" style="animation-delay:{0.3 + i * min(0.12, 0.6 / max(len(sums) - 1, 1)):.2f}s" data-label="{e(name)}" data-kind="deletions" data-value="{d}" x="{x0 + max(wa, 2)}" y="{y}" '
                    f'width="{wd}" height="{BAR}" rx="5" fill="{t["second"]}"/>')
        body.append(text(x0 + max(wa, 2) + wd + 10, y + BAR // 2 + 6, f"+{a} −{d}", t["muted"],
                         extra=f'class="fade" style="animation-delay:{DURATION - 0.35:.2f}s" '))
    total_a, total_d = sum(s[1] for s in sums), sum(s[2] for s in sums)
    label = "Lines changed by project: " + ", ".join(f"{n} +{a} -{d}" for n, a, d in sums)
    return frame(t, TOP + len(sums) * ROW + 18, f"LINES CHANGED BY PROJECT · +{total_a} −{total_d}", label, body)


def render_all(items, name_of):
    out = {}
    for theme in THEMES:
        out[f"assets/charts/projects-{theme}.svg"] = projects_chart(items, name_of, theme)
        out[f"assets/charts/timeline-{theme}.svg"] = timeline_chart(items, theme)
        out[f"assets/charts/proofs-{theme}.svg"] = proofs_chart(items, name_of, theme)
        out[f"assets/charts/lines-{theme}.svg"] = lines_chart(items, name_of, theme)
    return out


def picture(name, alt):
    # The <a> and <picture> tags each sit on their own line so GitHub parses the
    # whole element as one HTML block. With both on one line the <source> lines
    # start a separate block, the <picture> ends up empty and every theme falls
    # back to the dark <img>.
    return (f'<a href="{INTERACTIVE_URL}">\n<picture>\n'
            f'  <source media="(prefers-color-scheme: dark)" srcset="assets/charts/{name}-dark.svg">\n'
            f'  <source media="(prefers-color-scheme: light)" srcset="assets/charts/{name}-light.svg">\n'
            f'  <img src="assets/charts/{name}-dark.svg" alt="{e(alt)}" width="100%">\n'
            "</picture>\n</a>")
