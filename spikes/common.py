#!/usr/bin/env python3
"""Shared foundation for the profile-widget spikes.

Each spike is a bold reinvention of the live widget (assets/widget.svg) that
consumes the *same* real GitHub data — so we compare concepts, not mock-ups.
Data is fetched once (via the live generator's own collectors) and cached to
spikes/data.json; every spike renders from that snapshot.
"""

from __future__ import annotations

import importlib.util
import json
import math
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
CACHE = HERE / "data.json"

# ── tokyo-night palette (shared identity across every spike) ─────────────────
BG = "#1a1b27"
PANEL = "#24283b"
PANEL2 = "#1f2335"
INK = "#12131c"       # deeper than BG, for terminal / high-contrast grounds
FG = "#c0caf5"
MUTED = "#565f89"
BLUE = "#70a5fd"
PURPLE = "#bb9af7"
GREEN = "#9ece6a"
ORANGE = "#e0af68"
CYAN = "#7dcfff"
RED = "#f7768e"

LANG_COLOURS = {
    "Python": "#3572A5", "Go": "#00ADD8", "TypeScript": "#3178C6",
    "JavaScript": "#F1E05A", "Rust": "#DEA584", "HTML": "#E34C26",
    "CSS": "#663399", "Shell": "#89E051", "Jupyter Notebook": "#DA5B0B",
    "C": "#555555", "C++": "#F34B7D", "Ruby": "#701516",
}

FONT_SANS = "'Inter','Segoe UI',-apple-system,BlinkMacSystemFont,sans-serif"
FONT_MONO = "'JetBrains Mono','SF Mono','Fira Code','Cascadia Code',Consolas,monospace"

# 8-level block glyphs (index 0 == blank) for text sparklines
BLOCKS = " ▁▂▃▄▅▆▇█"


def esc(s) -> str:
    return escape(str(s))


def t(s, n: int) -> str:
    s = str(s)
    return s if len(s) <= n else s[: n - 1] + "…"


def kfmt(n: int) -> str:
    return f"{n / 1000:.1f}k".replace(".0k", "k") if n >= 1000 else str(n)


def lang_colour(lang: str) -> str:
    return LANG_COLOURS.get(lang, MUTED)


def blocks(values, levels: int = 8) -> str:
    """Render a list of counts as an 8-level block sparkline string."""
    top = max(values, default=0)
    if top <= 0:
        return BLOCKS[0] * len(values)
    return "".join(BLOCKS[max(0, min(levels, round(v / top * levels)))] for v in values)


def txt(x, y, s, fill=FG, size=13, weight=None, anchor=None,
        family=None, spacing=None, opacity=None, extra="") -> str:
    """One <text> element. Caller escapes any dynamic `s` with esc()."""
    a = f'x="{x}" y="{y}" fill="{fill}" font-size="{size}"'
    if weight:
        a += f' font-weight="{weight}"'
    if anchor:
        a += f' text-anchor="{anchor}"'
    if family:
        a += f' font-family="{family}"'
    if spacing is not None:
        a += f' letter-spacing="{spacing}"'
    if opacity is not None:
        a += f' opacity="{opacity}"'
    if extra:
        a += " " + extra
    return f"<text {a}>{s}</text>"


def polar(cx: float, cy: float, r: float, deg: float) -> tuple[float, float]:
    """Point on a circle. 0deg = right, angles increase clockwise on screen."""
    a = math.radians(deg)
    return cx + r * math.cos(a), cy + r * math.sin(a)


def arc(cx: float, cy: float, r: float, a0: float, a1: float) -> str:
    """SVG path 'd' for a clockwise stroke arc from a0 to a1 (degrees)."""
    x0, y0 = polar(cx, cy, r, a0)
    x1, y1 = polar(cx, cy, r, a1)
    large = 1 if (a1 - a0) % 360 > 180 else 0
    return f"M{x0:.2f},{y0:.2f} A{r:.2f},{r:.2f} 0 {large} 1 {x1:.2f},{y1:.2f}"


def load_data(refresh: bool = False) -> dict:
    """Real projects + contribution data, cached to spikes/data.json."""
    if CACHE.exists() and not refresh:
        return json.loads(CACHE.read_text(encoding="utf-8"))

    spec = importlib.util.spec_from_file_location(
        "widgetgen", REPO / "agent" / "generate.py"
    )
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)  # top-level only defines constants + fns

    data = {
        "name": gen.NAME,
        "user": gen.USER,
        "projects": gen.collect_projects(),
        "contrib": gen.collect_contributions(),
    }
    CACHE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data
