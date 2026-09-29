"""SVG charts for the profile README, rendered from merged ledger items.

Every bar, column and segment carries data-* attributes with the number it
draws, so tests can check each chart against data/ledger.json.
"""
import html
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
            f'  <circle cx="34" cy="36" r="4" fill="{t["accent"]}" stroke="{t["bar_stroke"]}"/>\n'
            f'  <text x="48" y="40" fill="{t["accent_text"]}" font-family="{e(MONO)}" font-size="11" letter-spacing="2.6">{e(header)}</text>\n'
            + "".join(f"  {line}\n" for line in body) + "</svg>\n")


def text(x, y, s, fill, size=12, anchor="start", weight="400", extra=""):
    return (f'<text {extra}x="{x}" y="{y}" fill="{fill}" font-family="{e(MONO)}" font-size="{size}" '
            f'font-weight="{weight}" text-anchor="{anchor}">{e(str(s))}</text>')


def projects_chart(items, name_of, theme):
    t = THEMES[theme]
    groups = by_project(items, name_of)
    top = max(len(prs) for _, prs in groups)
    x0, span, row = 220, 520, 30
    body = []
    for i, (name, prs) in enumerate(groups):
        y = 70 + i * row
        w = max(4, round(span * len(prs) / top))
        body.append(text(28, y + 14, name, t["text"]))
        body.append(f'<rect x="{x0}" y="{y}" width="{span}" height="18" rx="4" fill="{t["track"]}"/>')
        body.append(f'<rect class="grow-x" {delay(i, len(groups))} data-label="{e(name)}" data-value="{len(prs)}" '
                    f'x="{x0}" y="{y}" width="{w}" height="18" rx="4" fill="{t["accent"]}" stroke="{t["bar_stroke"]}"/>')
        body.append(text(x0 + w + 10, y + 14, len(prs), t["text"], weight="700",
                         extra=f'class="fade" style="animation-delay:{DURATION - 0.35:.2f}s" '))
    label = "Merged PRs by project: " + ", ".join(f"{n} {len(p)}" for n, p in groups)
    return frame(t, 70 + len(groups) * row + 24, f"MERGED PRS BY PROJECT · {len(items)} TOTAL", label, body)


def timeline_chart(items, theme):
    t = THEMES[theme]
    ms = months(items)
    counts = [sum(1 for p in items if p["merged_at"][:7] == m) for m in ms]
    top = max(counts) or 1
    base, tall = 200, 120
    slot = (WIDTH - 96) / len(ms)
    body = [f'<line x1="48" y1="{base}" x2="{WIDTH - 48}" y2="{base}" stroke="{t["border"]}"/>']
    points = []
    for i, (m, c) in enumerate(zip(ms, counts)):
        cx = 48 + slot * (i + 0.5)
        h = round(tall * c / top)
        w = min(96, slot * 0.5)
        name = f"{MONTHS[int(m[5:]) - 1]} {m[:4]}"
        points.append(f"{cx:.1f},{base - h}")
        body.append(f'<rect class="grow-y" {delay(i, len(ms), 0.5)} data-label="{m}" data-value="{c}" '
                    f'x="{cx - w / 2:.1f}" y="{base - h}" width="{w:.1f}" height="{h}" rx="4" '
                    f'fill="{t["accent"]}" fill-opacity="0.35" stroke="{t["bar_stroke"] if c else "none"}"/>')
        body.append(text(round(cx), base - h - 14, c, t["text"], size=14, anchor="middle", weight="700",
                         extra=f'class="fade" style="animation-delay:{DURATION - 0.35:.2f}s" '))
        body.append(text(round(cx), base + 22, name, t["muted"], anchor="middle"))
    body.append(f'<polyline class="draw" style="animation-delay:0.6s" pathLength="1" points="{" ".join(points)}" '
                f'fill="none" stroke="{t["accent_text"]}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>')
    for i, pt in enumerate(points):
        x, y = pt.split(",")
        body.append(f'<circle class="fade" style="animation-delay:{min(0.6 + 0.9 * i / max(len(points) - 1, 1), DURATION - 0.35):.2f}s" '
                    f'cx="{x}" cy="{y}" r="5" fill="{t["accent"]}" stroke="{t["bg"]}" stroke-width="2"/>')
    label = "Merges per month: " + ", ".join(
        f"{MONTHS[int(m[5:]) - 1]} {m[:4]} {c}" for m, c in zip(ms, counts))
    first = f"{MONTHS[int(ms[0][5:]) - 1].upper()} {ms[0][:4]}"
    return frame(t, 244, f"MERGES PER MONTH · SINCE {first}", label, body)


def proofs_chart(items, name_of, theme):
    t = THEMES[theme]
    groups = by_project(items, name_of)
    tested = sum(1 for p in items if p["proof"])
    size, gap, x0, row = 16, 6, 220, 30
    body, seen = [], 0
    for i, (name, prs) in enumerate(groups):
        y = 70 + i * row
        n = sum(1 for p in prs if p["proof"])
        body.append(text(28, y + 13, name, t["text"]))
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
        body.append(text(x0 + len(prs) * (size + gap) + 8, y + 13, f"{n}/{len(prs)}", t["muted"]))
    h = 70 + len(groups) * row
    body.append(f'<rect x="28" y="{h + 2}" width="12" height="12" rx="3" fill="{t["accent"]}" stroke="{t["bar_stroke"]}"/>')
    body.append(text(48, h + 12, "ships a regression test", t["muted"], size=11))
    body.append(f'<rect x="248.5" y="{h + 2.5}" width="11" height="11" rx="3" fill="none" stroke="{t["second"]}"/>')
    body.append(text(268, h + 12, "no test", t["muted"], size=11))
    label = f"{tested} of {len(items)} merged fixes ship a regression test"
    return frame(t, h + 36, f"{tested} OF {len(items)} MERGED FIXES SHIP A REGRESSION TEST", label, body)


def lines_chart(items, name_of, theme):
    t = THEMES[theme]
    groups = by_project(items, name_of)
    sums = [(n, sum(p["additions"] for p in prs), sum(p["deletions"] for p in prs)) for n, prs in groups]
    sums.sort(key=lambda s: (-(s[1] + s[2]), s[0].lower()))
    top = max(a + d for _, a, d in sums) or 1
    x0, span, row = 220, 480, 30
    body = []
    for i, (name, a, d) in enumerate(sums):
        y = 70 + i * row
        wa, wd = round(span * a / top), round(span * d / top)
        body.append(text(28, y + 14, name, t["text"]))
        body.append(f'<rect class="grow-x" {delay(i, len(sums), 0.6)} data-label="{e(name)}" data-kind="additions" data-value="{a}" x="{x0}" y="{y}" '
                    f'width="{max(wa, 2)}" height="18" rx="4" fill="{t["accent"]}" stroke="{t["bar_stroke"]}"/>')
        body.append(f'<rect class="grow-x" style="animation-delay:{0.3 + i * min(0.12, 0.6 / max(len(sums) - 1, 1)):.2f}s" data-label="{e(name)}" data-kind="deletions" data-value="{d}" x="{x0 + max(wa, 2)}" y="{y}" '
                    f'width="{wd}" height="18" rx="4" fill="{t["second"]}"/>')
        body.append(text(x0 + max(wa, 2) + wd + 10, y + 14, f"+{a} −{d}", t["muted"],
                         extra=f'class="fade" style="animation-delay:{DURATION - 0.35:.2f}s" '))
    total_a, total_d = sum(s[1] for s in sums), sum(s[2] for s in sums)
    label = "Lines changed by project: " + ", ".join(f"{n} +{a} -{d}" for n, a, d in sums)
    return frame(t, 70 + len(sums) * row + 24, f"LINES CHANGED BY PROJECT · +{total_a} −{total_d}", label, body)


def render_all(items, name_of):
    out = {}
    for theme in THEMES:
        out[f"assets/charts/projects-{theme}.svg"] = projects_chart(items, name_of, theme)
        out[f"assets/charts/timeline-{theme}.svg"] = timeline_chart(items, theme)
        out[f"assets/charts/proofs-{theme}.svg"] = proofs_chart(items, name_of, theme)
        out[f"assets/charts/lines-{theme}.svg"] = lines_chart(items, name_of, theme)
    return out


def picture(name, alt):
    return (f'<a href="{INTERACTIVE_URL}"><picture>\n'
            f'  <source media="(prefers-color-scheme: dark)" srcset="assets/charts/{name}-dark.svg">\n'
            f'  <source media="(prefers-color-scheme: light)" srcset="assets/charts/{name}-light.svg">\n'
            f'  <img src="assets/charts/{name}-dark.svg" alt="{e(alt)}" width="100%">\n'
            "</picture></a>")
