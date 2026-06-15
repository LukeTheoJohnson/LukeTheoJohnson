#!/usr/bin/env python3
"""Agentic data-science profile widget.

Pulls real GitHub activity, runs a Claude agent loop to analyze it and decide
what to surface, then renders an SVG that *shows* the agent working rather than
describing it. Degrades to a deterministic analysis when no API key is present,
so it runs and tests without a secret.

Output: assets/widget.svg
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
import urllib.error
from collections import Counter
from datetime import datetime, timezone
from html import escape
from pathlib import Path

USER = os.environ.get("WIDGET_USER", "LukeTheoJohnson")
GH_TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY")
MODEL = os.environ.get("WIDGET_MODEL", "claude-haiku-4-5")
OUT = Path(__file__).resolve().parent.parent / "assets" / "widget.svg"

# ── tokyo-night palette (matches the rest of the profile README) ─────────────
BG = "#1a1b27"
PANEL = "#24283b"
PANEL2 = "#1f2335"
FG = "#c0caf5"
MUTED = "#565f89"
BLUE = "#70a5fd"
PURPLE = "#bb9af7"
GREEN = "#9ece6a"
ORANGE = "#e0af68"
RED = "#f7768e"
CYAN = "#7dcfff"


# ── 1. fetch real GitHub activity ────────────────────────────────────────────
def gh(path: str):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "agentic-ds-widget",
            **({"Authorization": f"Bearer {GH_TOKEN}"} if GH_TOKEN else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def collect_stats() -> dict:
    """Derive a compact activity profile from public events + repos."""
    try:
        events = gh(f"/users/{USER}/events/public?per_page=100")
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        print(f"warn: events fetch failed ({e}); using empty set", file=sys.stderr)
        events = []
    try:
        repos = gh(f"/users/{USER}/repos?sort=pushed&per_page=100")
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        print(f"warn: repos fetch failed ({e}); using empty set", file=sys.stderr)
        repos = []

    pushes = [e for e in events if e.get("type") == "PushEvent"]
    commits = sum(len(e.get("payload", {}).get("commits", [])) for e in pushes)
    repos_touched = sorted({e["repo"]["name"] for e in events if e.get("repo")})
    prs = sum(1 for e in events if e.get("type") == "PullRequestEvent")
    event_types = Counter(e.get("type", "?") for e in events)

    langs = Counter()
    for repo in repos:
        if repo.get("language") and not repo.get("fork"):
            langs[repo["language"]] += 1

    msgs = []
    for e in pushes:
        for c in e.get("payload", {}).get("commits", []):
            m = (c.get("message") or "").splitlines()[0].strip()
            if m:
                msgs.append(m)

    return {
        "user": USER,
        "events_observed": len(events),
        "commits": commits,
        "pull_requests": prs,
        "repos_touched": repos_touched[:12],
        "repos_touched_count": len(repos_touched),
        "top_languages": langs.most_common(6),
        "event_type_breakdown": dict(event_types),
        "recent_commit_messages": msgs[:20],
    }


# ── 2. agent loop: Claude analyzes + decides what to render ──────────────────
def analyze_with_claude(stats: dict) -> dict | None:
    if not ANTHROPIC_KEY:
        return None
    try:
        import anthropic
    except ImportError:
        print("warn: anthropic SDK not installed; using fallback", file=sys.stderr)
        return None

    schema = {
        "headline": "<=58 chars, the single most interesting pattern in the data",
        "steps": ["3 short past-tense agent-action lines, <=46 chars each, e.g. 'scanned 100 public events'"],
        "insight": "<=150 chars, a concrete data-grounded observation a reviewer would find sharp",
        "chart": {
            "title": "<=22 chars",
            "bars": [{"label": "<=12 chars", "value": "number"}],
            "note": "<=40 chars, one-line read of the chart",
        },
    }
    prompt = (
        "You are a data-science agent analyzing a developer's recent GitHub activity. "
        "Find the most interesting real pattern and decide how to visualize it. "
        "Pick chart bars from the actual numbers in the data (languages, event types, or repo counts). "
        "Be specific and grounded — no fluff, no marketing language.\n\n"
        f"ACTIVITY DATA:\n{json.dumps(stats, indent=2)}\n\n"
        f"Respond with ONLY valid JSON matching this schema:\n{json.dumps(schema, indent=2)}"
    )
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
        resp = client.messages.create(
            model=MODEL,
            max_tokens=700,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1].lstrip("json").strip()
        data = json.loads(text)
        data["_engine"] = f"claude · {MODEL}"
        return data
    except Exception as e:  # noqa: BLE001 — never let the widget hard-fail the build
        print(f"warn: claude analysis failed ({e}); using fallback", file=sys.stderr)
        return None


def analyze_fallback(stats: dict) -> dict:
    """Deterministic analysis when no LLM is available."""
    langs = stats["top_languages"]
    top_lang = langs[0][0] if langs else "Python"
    bars = [{"label": l, "value": v} for l, v in langs[:5]] or [
        {"label": "Python", "value": 1}
    ]
    return {
        "headline": f"{stats['commits']} commits across {stats['repos_touched_count']} repos lately",
        "steps": [
            f"scanned {stats['events_observed']} public events",
            f"counted {stats['commits']} commits, {stats['pull_requests']} PRs",
            f"ranked {len(langs)} languages by repo count",
        ],
        "insight": (
            f"Most active in {top_lang}. Recent work spans "
            f"{stats['repos_touched_count']} repositories — consistent multi-project cadence."
        ),
        "chart": {
            "title": "Languages by repo",
            "bars": bars,
            "note": f"top: {top_lang}",
        },
        "_engine": "deterministic (no API key)",
    }


# ── 3. render SVG (looks like an agent session, not a badge) ─────────────────
def t(s: str, n: int) -> str:
    s = str(s)
    return s if len(s) <= n else s[: n - 1] + "…"


def render_svg(a: dict, stats: dict) -> str:
    W, H = 860, 404
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    steps = (a.get("steps") or [])[:3]
    bars = (a.get("chart") or {}).get("bars") or []
    bars = bars[:5]
    maxv = max((float(b.get("value", 0)) for b in bars), default=1) or 1

    # left column: agent trace. right column: chart.
    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" font-family="\'Fira Code\',\'JetBrains Mono\',monospace">'
    )
    parts.append(
        '<defs>'
        f'<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{BG}"/><stop offset="1" stop-color="{PANEL2}"/>'
        '</linearGradient>'
        f'<linearGradient id="bar" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{BLUE}"/><stop offset="1" stop-color="{PURPLE}"/>'
        '</linearGradient></defs>'
    )
    parts.append(f'<rect width="{W}" height="{H}" rx="14" fill="url(#bg)"/>')
    parts.append(
        f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="13" fill="none" '
        f'stroke="{MUTED}" stroke-opacity="0.35"/>'
    )

    # title bar
    parts.append(f'<circle cx="26" cy="28" r="6" fill="{RED}"/>')
    parts.append(f'<circle cx="46" cy="28" r="6" fill="{ORANGE}"/>')
    parts.append(f'<circle cx="66" cy="28" r="6" fill="{GREEN}"/>')
    parts.append(
        f'<text x="92" y="33" fill="{MUTED}" font-size="13">'
        f'agent://data-science · {escape(USER)}</text>'
    )
    parts.append(
        f'<text x="{W-22}" y="33" fill="{MUTED}" font-size="12" text-anchor="end">'
        f'{now}</text>'
    )
    parts.append(
        f'<line x1="16" y1="48" x2="{W-16}" y2="48" stroke="{MUTED}" stroke-opacity="0.25"/>'
    )

    # headline
    parts.append(
        f'<text x="26" y="86" fill="{FG}" font-size="22" font-weight="700">'
        f'{escape(t(a.get("headline","analysis"), 46))}</text>'
    )

    # agent trace (left)
    y = 128
    parts.append(f'<text x="26" y="{y}" fill="{CYAN}" font-size="12">▌ AGENT TRACE</text>')
    y += 26
    for s in steps:
        parts.append(f'<text x="30" y="{y}" fill="{GREEN}" font-size="13">▸</text>')
        parts.append(
            f'<text x="48" y="{y}" fill="{FG}" font-size="13">{escape(t(s, 44))}</text>'
        )
        y += 24
    # blinking-style cursor line
    parts.append(
        f'<text x="30" y="{y}" fill="{PURPLE}" font-size="13">▸ '
        f'<tspan fill="{MUTED}">rendering insight</tspan> '
        f'<tspan fill="{GREEN}">✓</tspan></text>'
    )

    # insight callout (left, below trace)
    iy = y + 28
    parts.append(
        f'<rect x="26" y="{iy}" width="490" height="104" rx="9" fill="{PANEL}" '
        f'stroke="{BLUE}" stroke-opacity="0.5"/>'
    )
    parts.append(
        f'<text x="42" y="{iy+26}" fill="{ORANGE}" font-size="11" '
        f'letter-spacing="1">INSIGHT</text>'
    )
    # word-wrap full insight, cap at 3 lines, ellipsize at a word boundary
    words, lines, cur = a.get("insight", "").split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > 52:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    if len(lines) > 3:
        lines = lines[:3]
        lines[2] = lines[2][:49].rstrip() + "…"
    for i, ln in enumerate(lines):
        parts.append(
            f'<text x="42" y="{iy+50+i*20}" fill="{FG}" font-size="13.5">{escape(ln)}</text>'
        )

    # chart (right)
    cx, cw = 556, 280
    parts.append(
        f'<text x="{cx}" y="128" fill="{CYAN}" font-size="12">▌ '
        f'{escape(t((a.get("chart") or {}).get("title","data"), 24))}</text>'
    )
    by = 150
    for b in bars:
        label = t(b.get("label", "?"), 12)
        val = float(b.get("value", 0))
        bw = int((val / maxv) * (cw - 96))
        parts.append(
            f'<text x="{cx}" y="{by+13}" fill="{MUTED}" font-size="11">{escape(label)}</text>'
        )
        parts.append(
            f'<rect x="{cx+78}" y="{by+2}" width="{max(bw,3)}" height="14" rx="4" fill="url(#bar)"/>'
        )
        parts.append(
            f'<text x="{cx+86+max(bw,3)}" y="{by+13}" fill="{FG}" font-size="11">'
            f'{int(val) if val==int(val) else val}</text>'
        )
        by += 26
    note = (a.get("chart") or {}).get("note")
    if note:
        parts.append(
            f'<text x="{cx}" y="{by+14}" fill="{MUTED}" font-size="11" '
            f'font-style="italic">{escape(t(note,40))}</text>'
        )

    # footer: prove it's machine-generated
    parts.append(
        f'<line x1="16" y1="{H-40}" x2="{W-16}" y2="{H-40}" stroke="{MUTED}" stroke-opacity="0.25"/>'
    )
    parts.append(
        f'<text x="26" y="{H-18}" fill="{MUTED}" font-size="11">'
        f'engine: {escape(a.get("_engine","?"))} · '
        f'{stats["events_observed"]} events analyzed · regenerated daily by github actions</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


def main():
    stats = collect_stats()
    analysis = analyze_with_claude(stats) or analyze_fallback(stats)
    svg = render_svg(analysis, stats)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(svg, encoding="utf-8")
    print(f"wrote {OUT} ({len(svg)} bytes) · engine={analysis.get('_engine')}")


if __name__ == "__main__":
    main()
