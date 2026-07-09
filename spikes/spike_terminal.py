#!/usr/bin/env python3
"""Spike 01 — TERMINAL.

The profile as a live shell session: window chrome, a monospace scrollback of
`gh`/`git`/`ls` output, block-glyph sparklines, and a blinking prompt. Leans
hard into the CLI/hacker identity of a Claude Code statusline author.
"""

from __future__ import annotations

from common import (BG, BLUE, CYAN, FG, FONT_MONO, GREEN, INK, MUTED, ORANGE,
                    PURPLE, RED, blocks, esc, kfmt, lang_colour, t, txt)

W = 900
PAD = 28
LH = 21          # line height
BODY_TOP = 78    # first baseline below the title bar
FS = 13.5


def _row(y: float) -> float:
    return BODY_TOP + y * LH


def render(data: dict) -> str:
    projects = data["projects"]
    c = data["contrib"]
    user = data["user"]

    lines: list[str] = []
    ln = 0  # running line index

    def emit(cells):
        """cells: list of (x, text, fill, weight) tuples on one line."""
        nonlocal ln
        y = _row(ln)
        for x, s, fill, weight in cells:
            lines.append(txt(PAD + x, y, s, fill=fill, size=FS,
                             weight=weight, family=FONT_MONO))
        ln += 1

    def gap(n=1):
        nonlocal ln
        ln += n

    # prompt + command
    emit([(0, "luke@github", GREEN, 600), (96, "~/dev", BLUE, None),
          (150, "% gh me --window 365d", FG, None)])
    gap()

    # headline contribution summary, each with a proportional block bar
    bar = "█" * max(1, round(c["merged_upstream"] / max(c["total_prs"], 1) * 12))
    emit([(0, "merged", MUTED, None),
          (74, str(c["merged_upstream"]), GREEN, 700),
          (110, "upstream PRs", FG, None),
          (250, bar, GREEN, None),
          (400, f"across {c['merged_projects']} projects", MUTED, None)])
    emit([(0, "opened", MUTED, None),
          (74, str(c["total_prs"]), CYAN, 700),
          (110, "PRs authored", FG, None),
          (250, "reviewed", MUTED, None),
          (340, str(c["reviewed"]), PURPLE, 700),
          (370, "PRs", FG, None)])
    gap()

    # ls -la of my own projects
    emit([(0, "~/projects", BLUE, None),
          (110, "% ls -la --sort=pushed", FG, None)])
    for p in projects:
        spark = blocks(p.get("heat") or [0], 8)
        lc = lang_colour(p["language"])
        emit([
            (0, "drwxr-xr-x", MUTED, None),
            (110, esc(t(p["name"], 24)), FG, 600),
            (330, esc(p["language"] or "—"), lc, None),
            (430, spark, GREEN, None),
            (600, f"{p['commits']}c", ORANGE, None),
            (660, f"★{kfmt(p['stars'])}", MUTED, None),
        ])
    gap()

    # git log of merged upstream landings, as ascii bars
    emit([(0, "~/oss", BLUE, None),
          (72, "% git log --merged --author=me", FG, None)])
    maxv = max((b["value"] for b in c["bars"]), default=1) or 1
    for b in c["bars"]:
        reps = max(1, round(b["value"] / maxv * 14))
        emit([
            (0, esc(t(b["name"], 26)), FG, None),
            (250, "█" * reps, GREEN, None),
            (560, str(b["value"]), GREEN, 700),
            (600, f"★{kfmt(b['stars'])}", ORANGE, None),
        ])
    gap()

    # 12-month merged cadence as a single block sparkline
    cadence = blocks(c["monthly"], 8)
    emit([(0, "merged/mo", MUTED, None),
          (110, cadence, GREEN, None),
          (360, "12 mo →", MUTED, None)])
    gap()

    # closing prompt with a blinking cursor block
    y = _row(ln)
    lines.append(txt(PAD, y, "luke@github", GREEN, size=FS, weight=600,
                     family=FONT_MONO))
    lines.append(txt(PAD + 96, y, "~/dev %", BLUE, size=FS, family=FONT_MONO))
    cursor_x = PAD + 96 + 62
    lines.append(
        f'<rect x="{cursor_x}" y="{y-12}" width="9" height="15" fill="{GREEN}" '
        f'class="cursor"/>'
    )
    ln += 1

    H = _row(ln) + 16

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" font-family="{FONT_MONO}">',
        '<style>'
        '@media (prefers-reduced-motion: no-preference){'
        '.cursor{animation:blink 1.1s steps(1) infinite}}'
        '@keyframes blink{50%{opacity:0}}'
        '</style>',
        # window body + border
        f'<rect width="{W}" height="{H}" rx="12" fill="{INK}"/>',
        f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="11" fill="none" '
        f'stroke="{MUTED}" stroke-opacity="0.35"/>',
        # title bar
        f'<path d="M0 12 A12 12 0 0 1 12 0 H{W-12} A12 12 0 0 1 {W} 12 V40 H0 Z" '
        f'fill="{BG}"/>',
        f'<line x1="0" y1="40" x2="{W}" y2="40" stroke="{MUTED}" '
        f'stroke-opacity="0.35"/>',
        f'<circle cx="24" cy="20" r="6" fill="{RED}"/>',
        f'<circle cx="44" cy="20" r="6" fill="{ORANGE}"/>',
        f'<circle cx="64" cy="20" r="6" fill="{GREEN}"/>',
        txt(W / 2, 25, f"{esc(data['name'].lower().replace(' ', '_'))}@github: ~/dev",
            fill=MUTED, size=12.5, anchor="middle", family=FONT_MONO),
    ]
    out.extend(lines)
    out.append("</svg>")
    return "".join(out)
