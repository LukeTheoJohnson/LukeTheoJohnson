#!/usr/bin/env python3
"""Spike 03 — EDITORIAL.

Swiss/magazine treatment: a masthead, one enormous hero statistic, a hairline
grid, and a numbered index of work. Near-monochrome with a single green accent;
the boldness comes from typographic scale and restraint, not decoration.
"""

from __future__ import annotations

from common import (BG, FG, FONT_SANS, GREEN, MUTED, PANEL, blocks, esc, kfmt,
                    lang_colour, t, txt)

W, H = 900, 424
PAD = 44


def _rule(y, x1=PAD, x2=W - PAD, op=0.5, col=MUTED, dash=""):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{col}" '
            f'stroke-opacity="{op}"{d}/>')


def render(data: dict) -> str:
    projects = data["projects"]
    c = data["contrib"]

    p: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" font-family="{FONT_SANS}">',
        '<style>'
        '@media (prefers-reduced-motion: no-preference){'
        '.rise{animation:rise .7s cubic-bezier(.2,.7,.3,1) backwards}}'
        '@keyframes rise{from{opacity:0;transform:translateY(10px)}}'
        '</style>',
        f'<rect width="{W}" height="{H}" fill="{BG}"/>',
        f'<rect x="6" y="6" width="{W-12}" height="{H-12}" fill="none" '
        f'stroke="{MUTED}" stroke-opacity="0.35"/>',
    ]

    # ── masthead ─────────────────────────────────────────────────────────────
    p.append(_rule(30, op=0.8))
    p.append(txt(PAD, 74, esc(data["name"].upper()), fill=FG, size=40,
                 weight=800, spacing=-1))
    p.append(txt(W - PAD, 52, "MACHINE LEARNING · DATA SCIENCE", fill=MUTED,
                 size=11, anchor="end", spacing=3))
    p.append(txt(W - PAD, 72, "OPEN-SOURCE DISPATCH · LAST 365 DAYS",
                 fill=GREEN, size=11, anchor="end", spacing=2))
    p.append(_rule(92, op=0.8))

    # ── hero statistic ───────────────────────────────────────────────────────
    p.append(txt(PAD, 128, "PULL REQUESTS MERGED UPSTREAM", fill=GREEN,
                 size=13, weight=600, spacing=3, extra='class="rise"'))
    p.append(txt(PAD - 4, 236, str(c["merged_upstream"]), fill=FG, size=132,
                 weight=800, spacing=-4, extra='class="rise"'))
    # unit + gloss to the right of the numeral
    hero_w = 84 * len(str(c["merged_upstream"]))
    gx = PAD + hero_w + 8
    p.append(txt(gx, 168, "PRs", fill=MUTED, size=22, weight=600))
    p.append(txt(gx, 202, f"across {c['merged_projects']} external", fill=FG,
                 size=15))
    p.append(txt(gx, 222, "repositories", fill=FG, size=15))

    # secondary stat stack, right column
    sx = W - PAD - 210
    stats = [
        (str(c["total_prs"]), "PULL REQUESTS AUTHORED"),
        (str(c["merged"]), "MERGED IN TOTAL"),
        (str(c["reviewed"]), "REVIEWS GIVEN"),
    ]
    sy = 132
    for i, (val, label) in enumerate(stats):
        p.append(_rule(sy - 22, x1=sx, x2=W - PAD, op=0.3))
        p.append(txt(sx, sy + 4, val, fill=FG, size=30, weight=700))
        p.append(txt(sx + 66, sy, label, fill=MUTED, size=10.5, spacing=1.5))
        p.append(txt(sx + 66, sy + 15, "last 365 days", fill=MUTED, size=10,
                     opacity=0.7))
        sy += 42

    # ── selected work: numbered index ────────────────────────────────────────
    iy = 292
    p.append(txt(PAD, iy, "SELECTED WORK", fill=MUTED, size=11, spacing=3))
    p.append(txt(W - PAD, iy, "COMMITS · 14 DAYS", fill=MUTED, size=10,
                 anchor="end", spacing=1.5))
    iy += 12
    p.append(_rule(iy, op=0.5))
    row_h = 27
    for i, pr in enumerate(projects):
        ry = iy + 8 + i * row_h + 12
        p.append(txt(PAD, ry, f"{i+1:02d}", fill=GREEN, size=13, weight=700,
                     family="'JetBrains Mono',monospace"))
        p.append(txt(PAD + 40, ry, esc(t(pr["name"], 28)), fill=FG, size=16,
                     weight=600))
        meta = f"{pr['language'] or '—'} · ★{kfmt(pr['stars'])}"
        p.append(txt(PAD + 320, ry, esc(meta), fill=MUTED, size=12))
        # commit block spark + count, right aligned
        p.append(txt(W - PAD - 44, ry, blocks(pr.get("heat") or [0], 8),
                     fill=lang_colour(pr["language"]), size=13,
                     family="'JetBrains Mono',monospace", anchor="end"))
        p.append(txt(W - PAD, ry, str(pr["commits"]), fill=FG, size=14,
                     weight=600, anchor="end"))
        p.append(_rule(iy + 8 + (i + 1) * row_h, op=0.2))

    p.append("</svg>")
    return "".join(p)
