#!/usr/bin/env python3
"""Spike 02 — CONSTELLATION.

The profile as a knowledge graph: a central "me" node, edges out to the
upstream repos I've landed PRs in (node size = merged count, label carries the
star weight) and to my own projects (node size = commits, colour = language).
A faint starfield and orbit rings sell the constellation metaphor.
"""

from __future__ import annotations

import math
import random

from common import (BG, BLUE, CYAN, FG, FONT_SANS, GREEN, MUTED, PANEL, PANEL2,
                    PURPLE, ORANGE, blocks, esc, kfmt, lang_colour, polar, t, txt)

W, H = 900, 460
ME = (322, 236)  # centre node


def _starfield(n=95) -> list[str]:
    rnd = random.Random(7)  # deterministic
    out = []
    for _ in range(n):
        x = rnd.uniform(0, W)
        y = rnd.uniform(70, H - 20)
        r = rnd.choice([0.6, 0.8, 1.0, 1.4])
        o = rnd.uniform(0.05, 0.35)
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{FG}" '
                   f'opacity="{o:.2f}"/>')
    return out


def _node(x, y, r, fill, stroke, glow_id) -> list[str]:
    return [
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r+6:.1f}" fill="url(#{glow_id})"/>',
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="1.5"/>',
    ]


def render(data: dict) -> str:
    projects = data["projects"]
    c = data["contrib"]
    bars = c["bars"]

    p: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" font-family="{FONT_SANS}">',
        '<defs>'
        f'<radialGradient id="bg"><stop offset="0" stop-color="{PANEL2}"/>'
        f'<stop offset="1" stop-color="{BG}"/></radialGradient>'
        f'<radialGradient id="glowg"><stop offset="0" stop-color="{GREEN}" '
        f'stop-opacity="0.55"/><stop offset="1" stop-color="{GREEN}" '
        f'stop-opacity="0"/></radialGradient>'
        f'<radialGradient id="glowc"><stop offset="0" stop-color="{CYAN}" '
        f'stop-opacity="0.5"/><stop offset="1" stop-color="{CYAN}" '
        f'stop-opacity="0"/></radialGradient>'
        f'<radialGradient id="glowp"><stop offset="0" stop-color="{PURPLE}" '
        f'stop-opacity="0.5"/><stop offset="1" stop-color="{PURPLE}" '
        f'stop-opacity="0"/></radialGradient>'
        '</defs>',
        '<style>'
        '@media (prefers-reduced-motion: no-preference){'
        '.edge{stroke-dasharray:340;stroke-dashoffset:340;'
        'animation:draw 1.1s ease-out forwards}'
        '.pop{animation:pop .5s cubic-bezier(.2,.8,.3,1.2) backwards}}'
        '@keyframes draw{to{stroke-dashoffset:0}}'
        '@keyframes pop{from{opacity:0;transform:scale(.4)}}'
        '</style>',
        f'<rect width="{W}" height="{H}" rx="16" fill="url(#bg)"/>',
        f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="15" fill="none" '
        f'stroke="{MUTED}" stroke-opacity="0.3"/>',
    ]
    p += _starfield()

    # header
    p.append(txt(32, 46, esc(data["name"]), fill=FG, size=24, weight=700))
    p.append(txt(32, 68, "open-source footprint", fill=MUTED, size=13))
    p.append(txt(W - 32, 46, "CONTRIBUTION GRAPH", fill=CYAN, size=11,
                 anchor="end", spacing=2))
    p.append(txt(W - 32, 68,
                 f"{c['merged_upstream']} merged · {c['merged_projects']} "
                 f"projects · {c['reviewed']} reviewed",
                 fill=MUTED, size=12, anchor="end"))

    mx, my = ME
    # faint orbit rings around me
    for rr in (150, 250):
        p.append(f'<circle cx="{mx}" cy="{my}" r="{rr}" fill="none" '
                 f'stroke="{MUTED}" stroke-opacity="0.14" stroke-dasharray="2 5"/>')

    # ── upstream repos: right hemisphere, size by merged value ───────────────
    maxv = max((b["value"] for b in bars), default=1) or 1
    up_angles = [-46, -17, 15, 44][: len(bars)]
    for i, b in enumerate(bars):
        ang = up_angles[i]
        nx, ny = polar(mx, my, 210, ang)
        r = 16 + b["value"] / maxv * 18
        sw = 1.5 + b["value"] / maxv * 4
        p.append(f'<line x1="{mx}" y1="{my}" x2="{nx:.1f}" y2="{ny:.1f}" '
                 f'stroke="{CYAN}" stroke-opacity="0.7" stroke-width="{sw:.1f}" '
                 f'class="edge"/>')
        p += [f'<g class="pop" style="transform-box:fill-box;'
              f'transform-origin:{nx:.1f}px {ny:.1f}px;'
              f'animation-delay:{0.4+i*0.1:.2f}s">'] + _node(
            nx, ny, r, PANEL, CYAN, "glowc") + ['</g>']
        p.append(txt(nx + r + 9, ny - 1, esc(t(b["name"], 22)), fill=FG,
                     size=13, weight=600))
        p.append(txt(nx + r + 9, ny + 15,
                     f"{b['value']} merged  ★{kfmt(b['stars'])}",
                     fill=MUTED, size=11))

    # ── my projects: left hemisphere, size by commits, colour by language ────
    maxc = max((pr["commits"] for pr in projects), default=1) or 1
    pj_angles = [150, 176, 202, 228][: len(projects)]
    for i, pr in enumerate(projects):
        ang = pj_angles[i]
        nx, ny = polar(mx, my, 152, ang)
        r = 11 + pr["commits"] / maxc * 15
        col = lang_colour(pr["language"])
        p.append(f'<line x1="{mx}" y1="{my}" x2="{nx:.1f}" y2="{ny:.1f}" '
                 f'stroke="{col}" stroke-opacity="0.6" stroke-width="2" '
                 f'class="edge"/>')
        p += [f'<g class="pop" style="transform-box:fill-box;'
              f'transform-origin:{nx:.1f}px {ny:.1f}px;'
              f'animation-delay:{0.6+i*0.1:.2f}s">',
              f'<circle cx="{nx:.1f}" cy="{ny:.1f}" r="{r+5:.1f}" '
              f'fill="{col}" opacity="0.18"/>',
              f'<circle cx="{nx:.1f}" cy="{ny:.1f}" r="{r:.1f}" fill="{col}"/>',
              '</g>']
        p.append(txt(nx - r - 9, ny - 1, esc(t(pr["name"], 20)), fill=FG,
                     size=12.5, weight=600, anchor="end"))
        p.append(txt(nx - r - 9, ny + 14, f"{pr['commits']}c · {pr['language']}",
                     fill=MUTED, size=10.5, anchor="end"))

    # ── me: the central node ─────────────────────────────────────────────────
    initials = "".join(w[0] for w in data["name"].split()[:2]).upper()
    p += _node(mx, my, 37, PANEL, GREEN, "glowg")
    p.append(txt(mx, my + 8, esc(initials), fill=GREEN, size=27, weight=800,
                 anchor="middle"))

    # legend footer
    ly = H - 22
    p.append(f'<circle cx="34" cy="{ly-4}" r="5" fill="{CYAN}"/>')
    p.append(txt(46, ly, "upstream repo (size = PRs merged)", fill=MUTED, size=11))
    p.append(f'<circle cx="330" cy="{ly-4}" r="5" fill="{GREEN}"/>')
    p.append(txt(342, ly, "my project (size = commits, colour = language)",
                 fill=MUTED, size=11))

    p.append("</svg>")
    return "".join(p)
