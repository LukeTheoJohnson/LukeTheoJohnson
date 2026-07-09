#!/usr/bin/env python3
"""Spike 04 — ORBITAL.

An instrument panel. Left: a 270-degree gauge for merge-rate (merged / opened).
Right: a 12-spoke radial clock of merged PRs per month. Below: my projects as
an orbit-legend. Circular metaphors throughout — the antithesis of the current
linear-bar layout.
"""

from __future__ import annotations

import calendar
from datetime import datetime, timezone

from common import (BG, BLUE, CYAN, FG, FONT_SANS, GREEN, MUTED, ORANGE, PANEL,
                    PANEL2, PURPLE, arc, blocks, esc, kfmt, lang_colour, polar,
                    t, txt)

W, H = 900, 460


def render(data: dict) -> str:
    projects = data["projects"]
    c = data["contrib"]

    p: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" font-family="{FONT_SANS}">',
        '<defs>'
        f'<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{BG}"/><stop offset="1" '
        f'stop-color="{PANEL2}"/></linearGradient>'
        f'<linearGradient id="gauge" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{CYAN}"/><stop offset="1" '
        f'stop-color="{GREEN}"/></linearGradient>'
        '</defs>',
        '<style>'
        '@media (prefers-reduced-motion: no-preference){'
        '.gval{stroke-dasharray:1000;stroke-dashoffset:1000;'
        'animation:draw 1.3s ease-out .2s forwards}'
        '.spoke{transform-box:fill-box;transform-origin:bottom;'
        'animation:grow .6s ease-out backwards}}'
        '@keyframes draw{to{stroke-dashoffset:0}}'
        '@keyframes grow{from{transform:scaleY(0)}}'
        '</style>',
        f'<rect width="{W}" height="{H}" rx="16" fill="url(#bg)"/>',
        f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="15" fill="none" '
        f'stroke="{MUTED}" stroke-opacity="0.3"/>',
    ]

    # header
    p.append(txt(32, 46, esc(data["name"]), fill=FG, size=24, weight=700))
    p.append(txt(W - 32, 46, "INSTRUMENTATION · 365D", fill=CYAN, size=11,
                 anchor="end", spacing=2))

    # ── left instrument: merge-rate gauge (270 degrees, 135 → 405) ───────────
    gcx, gcy, gr = 232, 260, 118
    A0, SPAN = 135, 270
    rate = c["merged"] / c["total_prs"] if c["total_prs"] else 0
    # tick ring
    for i in range(11):
        a = A0 + SPAN * i / 10
        x1, y1 = polar(gcx, gcy, gr + 6, a)
        x2, y2 = polar(gcx, gcy, gr + (14 if i % 5 == 0 else 10), a)
        p.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                 f'stroke="{MUTED}" stroke-opacity="0.5" stroke-width="1.5"/>')
    # track + value arc
    p.append(f'<path d="{arc(gcx, gcy, gr, A0, A0 + SPAN)}" fill="none" '
             f'stroke="{PANEL}" stroke-width="16" stroke-linecap="round"/>')
    p.append(f'<path d="{arc(gcx, gcy, gr, A0, A0 + SPAN * rate)}" fill="none" '
             f'stroke="url(#gauge)" stroke-width="16" stroke-linecap="round" '
             f'class="gval"/>')
    # centre readout
    p.append(txt(gcx, gcy - 2, f"{rate*100:.0f}%", fill=FG, size=52,
                 weight=800, anchor="middle"))
    p.append(txt(gcx, gcy + 24, "MERGE RATE", fill=GREEN, size=12, weight=600,
                 anchor="middle", spacing=2))
    p.append(txt(gcx, gcy + 44, f"{c['merged']} merged of {c['total_prs']} opened",
                 fill=MUTED, size=12, anchor="middle"))
    # 0 / 100 end labels
    lx0, ly0 = polar(gcx, gcy, gr + 26, A0)
    lx1, ly1 = polar(gcx, gcy, gr + 26, A0 + SPAN)
    p.append(txt(lx0, ly0 + 4, "0", fill=MUTED, size=10, anchor="middle"))
    p.append(txt(lx1, ly1 + 4, "100", fill=MUTED, size=10, anchor="middle"))

    # small readouts under the gauge
    reads = [(str(c["merged_upstream"]), "UPSTREAM", CYAN),
             (str(c["merged_projects"]), "PROJECTS", PURPLE),
             (str(c["reviewed"]), "REVIEWED", ORANGE)]
    rx = 92
    for val, lab, col in reads:
        p.append(txt(rx, 418, val, fill=col, size=22, weight=700,
                     anchor="middle"))
        p.append(txt(rx, 434, lab, fill=MUTED, size=9.5, anchor="middle",
                     spacing=1))
        rx += 94

    # divider
    p.append(f'<line x1="470" y1="80" x2="470" y2="{H-30}" stroke="{MUTED}" '
             f'stroke-opacity="0.25"/>')

    # ── right instrument: 12-month radial clock of merged PRs ────────────────
    ccx, ccy, cin, cout = 690, 252, 38, 116
    monthly = c["monthly"]
    maxm = max(monthly) or 1
    now = datetime.now(timezone.utc)
    p.append(txt(690, 92, "MERGED PRs / MONTH", fill=MUTED, size=11,
                 anchor="middle", spacing=2))
    # guide rings
    for rr in (cin, (cin + cout) / 2, cout):
        p.append(f'<circle cx="{ccx}" cy="{ccy}" r="{rr:.0f}" fill="none" '
                 f'stroke="{MUTED}" stroke-opacity="0.15"/>')
    for i, v in enumerate(monthly):
        a = -90 + i * 30  # month 0 at top, clockwise
        length = cin + (v / maxm) * (cout - cin)
        x1, y1 = polar(ccx, ccy, cin, a)
        x2, y2 = polar(ccx, ccy, length, a)
        col = GREEN if v == maxm and v else (CYAN if v else MUTED)
        wsel = 11 if v else 2
        op = 1 if v else 0.25
        p.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                 f'stroke="{col}" stroke-width="{wsel}" stroke-linecap="round" '
                 f'stroke-opacity="{op}" class="spoke" '
                 f'style="animation-delay:{0.3+i*0.04:.2f}s"/>')
        if v:
            tx, ty = polar(ccx, ccy, length + 12, a)
            p.append(txt(tx, ty + 3, str(v), fill=col, size=12, weight=700,
                         anchor="middle"))
    # month labels at the four cardinals
    for i in (0, 3, 6, 9):
        m = now.month - (11 - i)
        y = now.year
        while m <= 0:
            m += 12
        lx, ly = polar(ccx, ccy, cout + 22, -90 + i * 30)
        p.append(txt(lx, ly + 3, calendar.month_abbr[m], fill=MUTED, size=9.5,
                     anchor="middle"))
    p.append(f'<circle cx="{ccx}" cy="{ccy}" r="{cin}" fill="{PANEL}"/>')
    p.append(txt(ccx, ccy - 2, str(sum(monthly)), fill=FG, size=26,
                 weight=800, anchor="middle"))
    p.append(txt(ccx, ccy + 16, "merged", fill=MUTED, size=10,
                 anchor="middle"))

    # ── footer: projects as an orbit legend ──────────────────────────────────
    p.append(f'<line x1="32" y1="{H-56}" x2="{W-32}" y2="{H-56}" '
             f'stroke="{MUTED}" stroke-opacity="0.25"/>')
    # (kept minimal; the gauge readouts already sit at y=418 on the left half)
    fx = 496
    p.append(txt(fx, H - 36, "PROJECTS", fill=MUTED, size=9.5, spacing=1.5))
    fx += 4
    fy = H - 18
    colw = 100
    for pr in projects:
        p.append(f'<circle cx="{fx+4}" cy="{fy-4}" r="4.5" '
                 f'fill="{lang_colour(pr["language"])}"/>')
        p.append(txt(fx + 14, fy, esc(t(pr["name"], 12)), fill=FG, size=11,
                     weight=600))
        p.append(txt(fx + 14, fy + 13, f"{pr['commits']}c", fill=MUTED,
                     size=9.5))
        fx += colw
    p.append("</svg>")
    return "".join(p)
