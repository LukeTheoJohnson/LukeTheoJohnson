#!/usr/bin/env python3
"""Profile widget: what I've shipped, and what I've landed upstream.

Reads real data from the GitHub API and renders a clean data-viz card — no
agent theater, no synthetic loading traces. It leads with completed work:

  left   my own public projects — language, stars and a commit-activity heatmap
  right  merged pull requests grouped by the upstream project they landed in,
         plus a 12-month merged-PR cadence sparkline

Entrance motion is CSS inside the SVG (bars grow, heatmap cells sweep in, the
spark line draws once; today's active cell pulses) and is gated behind
prefers-reduced-motion, so reduced-motion viewers get the static final state.

Two timeframes are in play and both are labelled on the card: pull-request
totals cover the last year; the per-project commit heatmaps cover the last
14 days. Open PRs are de-emphasised (intent, not achievement) to a single
muted line.

Deterministic, so it runs without any API key and its output is reproducible.
Private repos are invisible to the GitHub Actions token by design and are not
shown; private commit volume already surfaces via the stats card.

Output: assets/widget.svg
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

USER = os.environ.get("WIDGET_USER", "LukeTheoJohnson")
NAME = os.environ.get("WIDGET_NAME", "Luke Johnson")
GH_TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
OUT = Path(__file__).resolve().parent.parent / "assets" / "widget.svg"

HEAT_DAYS = 14  # how many days of commit history each project heatmap shows
WINDOW_DAYS = 365  # contribution stats (PRs, reviews) cover the last year

# Scientific-Python / ML libraries, by repo name. Used only to label the
# "in review" line — the libraries data scientists actually use, currently
# in flight. Match is on the repo name (the part after the owner).
DS_STACK = {
    "numpy", "scipy", "pandas", "polars", "narwhals", "pyarrow", "duckdb",
    "ibis", "dask", "xarray", "vaex", "modin",
    "scikit-learn", "sklearn", "statsmodels", "patsy", "pingouin",
    "xgboost", "lightgbm", "catboost", "imbalanced-learn",
    "pytorch", "torch", "jax", "flax", "keras", "tensorflow",
    "transformers", "datasets", "accelerate", "tokenizers", "diffusers",
    "huggingface_hub", "sentence-transformers", "einops", "safetensors",
    "matplotlib", "seaborn", "plotly", "plotly.py", "altair", "bokeh", "holoviews",
    "pymc", "arviz", "numpyro", "lifelines", "linearmodels", "prophet",
    "statsforecast", "sktime", "darts", "tsfresh",
    "pandera", "great-expectations", "shap", "optuna", "mlflow", "wandb",
    "spacy", "nltk", "gensim", "networkx", "sympy", "scikit-image",
    "umap", "hdbscan", "faiss", "annoy",
}

# ── tokyo-night palette (matches the rest of the profile README) ─────────────
BG = "#1a1b27"
PANEL = "#24283b"
PANEL2 = "#1f2335"
FG = "#c0caf5"
MUTED = "#565f89"
SOFT = "#737aa2"  # lighter muted — legible for the subtitle
BLUE = "#70a5fd"
PURPLE = "#bb9af7"
GREEN = "#9ece6a"
ORANGE = "#e0af68"
CYAN = "#7dcfff"
# green ramp for the commit heatmap (empty → busiest), GitHub-style
HEAT = ["#2d3350", "#3b6e47", "#519a4e", "#73c05a", "#9ece6a"]
# GitHub linguist colours for the per-project language dot
LANG_COLOURS = {
    "Python": "#3572A5", "Go": "#00ADD8", "TypeScript": "#3178C6",
    "JavaScript": "#F1E05A", "Rust": "#DEA584", "HTML": "#E34C26",
    "CSS": "#663399", "Shell": "#89E051", "Jupyter Notebook": "#DA5B0B",
    "C": "#555555", "C++": "#F34B7D", "Ruby": "#701516",
}


def gh(path: str):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "oss-profile-widget",
            **({"Authorization": f"Bearer {GH_TOKEN}"} if GH_TOKEN else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def search_count(q: str) -> int:
    try:
        return int(gh(f"/search/issues?q={q}&per_page=1").get("total_count", 0))
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError) as e:
        print(f"warn: count failed for {q!r} ({e})", file=sys.stderr)
        return 0


def rel_age(iso: str) -> str:
    """Human 'updated 2d ago' from an ISO timestamp."""
    try:
        d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return "active"
    days = (datetime.now(timezone.utc) - d).days
    if days <= 0:
        return "updated today"
    if days == 1:
        return "updated yesterday"
    if days < 30:
        return f"updated {days}d ago"
    return f"updated {days // 30}mo ago"


def commit_days(repo: str, days: int = HEAT_DAYS) -> list[int]:
    """Commits per day on the default branch, oldest→newest, last `days`."""
    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        commits = gh(f"/repos/{USER}/{repo}/commits?since={since}&per_page=100")
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        print(f"warn: commits fetch failed for {repo} ({e})", file=sys.stderr)
        return [0] * days
    counts = [0] * days
    for cm in commits:
        info = cm.get("commit", {})
        ds = (info.get("author") or {}).get("date") or (
            info.get("committer") or {}
        ).get("date")
        try:
            d = datetime.fromisoformat((ds or "").replace("Z", "+00:00"))
        except ValueError:
            continue
        day = (now - d).days
        if 0 <= day < days:
            counts[days - 1 - day] += 1  # newest on the right
    return counts


# ── my own public projects (non-fork repos I push to) ────────────────────────
def collect_projects(limit: int = 4) -> list[dict]:
    try:
        repos = gh(f"/users/{USER}/repos?sort=pushed&per_page=100")
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        print(f"warn: repos fetch failed ({e})", file=sys.stderr)
        return []
    out = []
    for r in repos:
        if r.get("fork") or r.get("archived"):
            continue
        if r.get("name", "").lower() == USER.lower():
            continue  # the profile repo itself is not a project
        out.append(
            {
                "name": r["name"],
                "language": r.get("language") or "",
                "stars": r.get("stargazers_count", 0),
                "description": (r.get("description") or "").strip(),
                "pushed_at": r.get("pushed_at", ""),
            }
        )
    out.sort(key=lambda d: d["pushed_at"], reverse=True)
    out = out[:limit]
    for pr in out:  # only fetch commit history for the few we'll actually draw
        pr["heat"] = commit_days(pr["name"])
        pr["commits"] = sum(pr["heat"])
    return out


# ── my merged contributions (PRs that actually landed, grouped by repo) ───────
def collect_contributions() -> dict:
    since = (
        datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)
    ).strftime("%Y-%m-%d")
    try:
        res = gh(
            f"/search/issues?q=type:pr+author:{USER}+created:>={since}"
            f"&sort=updated&order=desc&per_page=100"
        )
        items = res.get("items", [])
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        print(f"warn: PR search failed ({e})", file=sys.stderr)
        items = []

    by_repo: dict[str, dict] = defaultdict(
        lambda: {"merged": 0, "open": 0, "owner": ""}
    )
    merged = 0
    for it in items:
        full = it.get("repository_url", "").split("/repos/", 1)[-1]
        if not full or "/" not in full:
            continue
        by_repo[full]["owner"] = full.split("/", 1)[0]
        if it.get("pull_request", {}).get("merged_at"):
            by_repo[full]["merged"] += 1
            merged += 1
        elif it.get("state") == "open":
            by_repo[full]["open"] += 1

    def is_external(repo: str) -> bool:
        return by_repo[repo]["owner"].lower() != USER.lower()

    merged_upstream = sum(s["merged"] for r, s in by_repo.items() if is_external(r))
    merged_projects = sum(
        1 for r, s in by_repo.items() if is_external(r) and s["merged"]
    )

    bars = sorted(
        (
            {"name": r.split("/", 1)[1], "value": s["merged"]}
            for r, s in by_repo.items()
            if s["merged"] and is_external(r)
        ),
        key=lambda d: d["value"],
        reverse=True,
    )[:4]

    in_review = sorted(
        r.split("/", 1)[1]
        for r, s in by_repo.items()
        if r.split("/", 1)[1].lower() in DS_STACK and s["open"] and not s["merged"]
    )[:4]

    # merged PRs bucketed by merge month, oldest → newest, for the sparkline
    monthly = [0] * 12
    now = datetime.now(timezone.utc)
    for it in items:
        merged_at = it.get("pull_request", {}).get("merged_at")
        if not merged_at:
            continue
        try:
            d = datetime.fromisoformat(merged_at.replace("Z", "+00:00"))
        except ValueError:
            continue
        mb = (now.year - d.year) * 12 + (now.month - d.month)
        if 0 <= mb < 12:
            monthly[11 - mb] += 1

    return {
        "monthly": monthly,
        "merged": merged,
        "merged_upstream": merged_upstream,
        "merged_projects": merged_projects,
        "reviewed": search_count(f"type:pr+reviewed-by:{USER}+created:>={since}"),
        "bars": bars,
        "in_review": in_review,
        "total_prs": len(items),
    }


# ── render ───────────────────────────────────────────────────────────────────
def t(s: str, n: int) -> str:
    s = str(s)
    return s if len(s) <= n else s[: n - 1] + "…"


def heat_color(n: int) -> str:
    """Map a daily commit count to a ramp colour — fixed thresholds so even a
    single commit reads as clearly green (GitHub-style), not relative-faint."""
    if n <= 0:
        return HEAT[0]
    if n <= 1:
        return HEAT[1]
    if n <= 3:
        return HEAT[2]
    if n <= 6:
        return HEAT[3]
    return HEAT[4]


def render_svg(projects: list[dict], c: dict) -> str:
    W = 860
    cx, cw = 32, 410
    sq, gap = 9, 2
    strip_w = HEAT_DAYS * (sq + gap) - gap

    # pre-measure so the total height hugs the content. Language/stars/commits
    # sit on their own right-anchored row under the heatmap, so the single
    # description line below gets nearly the full card width.
    for pr in projects:
        pr["desc_line"] = t(pr["description"] or rel_age(pr["pushed_at"]), 52)

    left_bottom = 200 + (len(projects) * 66 - 8 if projects else 22)
    bars_end = 210 + len(c["bars"]) * 30
    ir_end = bars_end + 20 if c["in_review"] else bars_end - 16
    spark_label_y = ir_end + 26
    spark_top = spark_label_y + 10
    spark_h = 36
    right_bottom = spark_top + spark_h + 6
    H = max(left_bottom, right_bottom) + 58

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    p: list[str] = []

    p.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" '
        f'font-family="\'Inter\',\'Segoe UI\',-apple-system,sans-serif">'
    )
    p.append(
        '<defs>'
        f'<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{BG}"/><stop offset="1" stop-color="{PANEL2}"/>'
        '</linearGradient>'
        f'<linearGradient id="bar" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{BLUE}"/><stop offset="1" stop-color="{PURPLE}"/>'
        '</linearGradient>'
        f'<linearGradient id="spark" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{BLUE}" stop-opacity="0.35"/>'
        f'<stop offset="1" stop-color="{BLUE}" stop-opacity="0.02"/>'
        '</linearGradient></defs>'
    )
    # one-shot entrance motion only (bars grow, cells sweep in, spark line
    # draws); the sole loop is a slow pulse on today's active heatmap cell.
    p.append(
        '<style>'
        '@media (prefers-reduced-motion: no-preference){'
        '.bar{transform-box:fill-box;transform-origin:left;'
        'animation:grow .55s cubic-bezier(.2,.7,.3,1) backwards}'
        '.cell{animation:fade .45s ease-out backwards}'
        '.pulse{animation:pulse 3s ease-in-out infinite}'
        '.line{stroke-dasharray:620;stroke-dashoffset:620;'
        'animation:draw 1s ease-out .25s forwards}'
        '.fill,.dot{animation:fade .7s ease-out .7s backwards}'
        '}'
        '@keyframes grow{from{transform:scaleX(0)}}'
        '@keyframes fade{from{opacity:0}}'
        '@keyframes draw{to{stroke-dashoffset:0}}'
        '@keyframes pulse{50%{opacity:.4}}'
        '</style>'
    )
    p.append(f'<rect width="{W}" height="{H}" rx="16" fill="url(#bg)"/>')
    p.append(
        f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="15" fill="none" '
        f'stroke="{MUTED}" stroke-opacity="0.30"/>'
    )

    # header
    p.append(
        f'<text x="32" y="50" fill="{FG}" font-size="27" font-weight="700">'
        f'{escape(NAME)}</text>'
    )
    p.append(
        f'<text x="{W-32}" y="44" fill="{CYAN}" font-size="13" text-anchor="end" '
        f'letter-spacing="2">ML · DATA SCIENCE</text>'
    )
    p.append(
        f'<text x="32" y="74" fill="{SOFT}" font-size="13.5">'
        f'Projects I build &amp; contributions upstream</text>'
    )
    p.append(
        f'<text x="{W-32}" y="74" fill="{MUTED}" font-size="12" text-anchor="end">'
        f'as of {today}</text>'
    )

    # stat row — merged-focused, last year; tight pitch so the group reads
    # as one cluster, with the timeframe tag anchoring the row's right edge
    stats = [
        (str(c["merged"]), "PRs merged", GREEN),
        (str(c["merged_upstream"]), "upstream", PURPLE),
        (str(c["merged_projects"]), "OSS projects", BLUE),
        (str(c["reviewed"]), "reviewed", CYAN),
    ]
    sx = 32
    for value, label, col in stats:
        p.append(
            f'<text x="{sx}" y="120" fill="{col}" font-size="30" '
            f'font-weight="700">{escape(value)}</text>'
        )
        p.append(
            f'<text x="{sx+2}" y="138" fill="{MUTED}" font-size="12">'
            f'{escape(label)}</text>'
        )
        sx += 130
    p.append(
        f'<text x="{W-32}" y="138" fill="{MUTED}" font-size="10.5" '
        f'text-anchor="end" letter-spacing="1">LAST YEAR</text>'
    )

    p.append(
        f'<line x1="32" y1="158" x2="{W-32}" y2="158" '
        f'stroke="{MUTED}" stroke-opacity="0.25"/>'
    )

    # ── left: my own projects (cards with commit heatmap) ────────────────────
    p.append(
        f'<text x="32" y="186" fill="{CYAN}" font-size="11.5" letter-spacing="1.5">'
        f'PERSONAL PROJECTS</text>'
    )
    p.append(
        f'<text x="442" y="186" fill="{MUTED}" font-size="10" text-anchor="end" '
        f'letter-spacing="0.5">commits / {HEAT_DAYS}d</text>'
    )
    cy = 200
    if projects:
        for pr in projects:
            p.append(
                f'<rect x="{cx}" y="{cy}" width="{cw}" height="58" rx="10" '
                f'fill="{PANEL}"/>'
            )
            p.append(
                f'<text x="{cx+16}" y="{cy+24}" fill="{FG}" font-size="15" '
                f'font-weight="600">{escape(t(pr["name"], 20))}</text>'
            )
            p.append(
                f'<text x="{cx+16}" y="{cy+48}" fill="{MUTED}" '
                f'font-size="12">{escape(pr["desc_line"])}</text>'
            )
            # daily commit heatmap, right-aligned; today's active cell pulses
            heat = pr.get("heat") or [0] * HEAT_DAYS
            x0 = cx + cw - 16 - strip_w
            for i, n in enumerate(heat):
                if i == HEAT_DAYS - 1 and n > 0:
                    anim = ' class="pulse"'
                else:
                    anim = (
                        f' class="cell" '
                        f'style="animation-delay:{0.1 + i * 0.03:.2f}s"'
                    )
                p.append(
                    f'<rect x="{x0 + i*(sq+gap)}" y="{cy+12}" width="{sq}" '
                    f'height="{sq}" rx="2" fill="{heat_color(n)}"{anim}/>'
                )
            meta = " · ".join(
                ([escape(pr["language"])] if pr["language"] else [])
                + ([f'★ {pr["stars"]}'] if pr.get("stars") else [])
                + [f'{pr.get("commits", 0)} commits']
            )
            dot = (
                f'<tspan fill="{LANG_COLOURS.get(pr["language"], MUTED)}">● </tspan>'
                if pr["language"]
                else ""
            )
            p.append(
                f'<text x="{cx+cw-16}" y="{cy+34}" fill="{MUTED}" font-size="10.5" '
                f'text-anchor="end">{dot}{meta}</text>'
            )
            cy += 66
    else:
        p.append(
            f'<text x="{cx+4}" y="{cy+18}" fill="{MUTED}" font-size="13">'
            f'building it</text>'
        )

    # ── right: merged PRs by upstream project (bars) ─────────────────────────
    bx = 470
    p.append(
        f'<text x="{bx}" y="186" fill="{CYAN}" font-size="11.5" letter-spacing="1.5">'
        f'MERGED PRs — UPSTREAM</text>'
    )
    bars = c["bars"]
    maxv = max((b["value"] for b in bars), default=1) or 1
    track_x, track_w = bx + 180, 146
    by = 210
    for i, b in enumerate(bars):
        bw = max(int((b["value"] / maxv) * track_w), 4)
        p.append(
            f'<text x="{bx}" y="{by+11}" fill="{FG}" font-size="13">'
            f'{escape(t(b["name"], 22))}</text>'
        )
        p.append(
            f'<rect x="{track_x}" y="{by}" width="{track_w}" height="14" rx="4" '
            f'fill="{PANEL}"/>'
        )
        p.append(
            f'<rect x="{track_x}" y="{by}" width="{bw}" height="14" rx="4" '
            f'fill="url(#bar)" class="bar" '
            f'style="animation-delay:{0.1 + i * 0.08:.2f}s"/>'
        )
        p.append(
            f'<text x="{track_x+track_w+10}" y="{by+11}" fill="{FG}" '
            f'font-size="12.5" font-weight="600">{b["value"]}</text>'
        )
        by += 30

    if c["in_review"]:
        names = " · ".join(c["in_review"])
        p.append(
            f'<text x="{bx}" y="{by+16}" fill="{MUTED}" font-size="11.5">'
            f'in review: {escape(t(names, 44))}</text>'
        )

    # ── merged-PR cadence, last 12 months (area sparkline) ───────────────────
    monthly = c["monthly"]
    p.append(
        f'<text x="{bx}" y="{spark_label_y}" fill="{MUTED}" font-size="10" '
        f'letter-spacing="1">MERGED PRs / MONTH</text>'
    )
    sw = W - 32 - bx
    smax = max(monthly) or 1
    step = sw / (len(monthly) - 1)
    pts = [
        (bx + i * step, spark_top + spark_h - (v / smax) * spark_h)
        for i, v in enumerate(monthly)
    ]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    base = spark_top + spark_h
    p.append(
        f'<polygon points="{pts[0][0]:.1f},{base} {line} {pts[-1][0]:.1f},{base}" '
        f'fill="url(#spark)" class="fill"/>'
    )
    p.append(
        f'<polyline points="{line}" fill="none" stroke="{CYAN}" '
        f'stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round" '
        f'class="line"/>'
    )
    p.append(
        f'<circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="3" '
        f'fill="{CYAN}" class="dot"/>'
    )

    # ── provenance, with both timeframes spelled out ─────────────────────────
    p.append(
        f'<line x1="32" y1="{H-32}" x2="{W-32}" y2="{H-32}" '
        f'stroke="{MUTED}" stroke-opacity="0.25"/>'
    )
    p.append(
        f'<text x="32" y="{H-14}" fill="{MUTED}" font-size="11">'
        f'pull requests: last year ({c["total_prs"]} analysed) · '
        f'commit heatmaps: last {HEAT_DAYS} days · GitHub API · refreshed daily'
        f'</text>'
    )

    p.append("</svg>")
    return "".join(p)


def main():
    projects = collect_projects()
    contrib = collect_contributions()
    svg = render_svg(projects, contrib)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(svg, encoding="utf-8")
    print(
        f"wrote {OUT} ({len(svg)} bytes) · "
        f"{len(projects)} projects / {contrib['merged']} merged / "
        f"{len(contrib['bars'])} bars / {len(contrib['in_review'])} in review"
    )


if __name__ == "__main__":
    main()
