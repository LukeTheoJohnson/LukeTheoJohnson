#!/usr/bin/env python3
"""Regenerate the data-driven sections of the profile README.

Polls the GitHub API (no other repos need to know about us) and rewrites two
marked blocks in README.md in place:

  <!-- OSS:START -->      …open-source PRs to repos I don't own, grouped by repo
  <!-- OSS:END -->
  <!-- FEATURED:START --> …my own repos, top by stars, using each repo's own
  <!-- FEATURED:END -->     GitHub description (so the copy lives at the source)

Idempotent: if nothing changed, the file is left byte-identical so the workflow
commits nothing. Never hard-fails the build — on API trouble it leaves the
existing block untouched.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

USER = (
    os.environ.get("WIDGET_USER")
    or os.environ.get("GITHUB_REPOSITORY_OWNER")  # set by GitHub Actions
    or "LukeTheoJohnson"
)
GH_TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
README = Path(__file__).resolve().parent.parent / "README.md"
FEATURED_COUNT = int(os.environ.get("FEATURED_COUNT", "3"))


def gh(path: str):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "profile-readme-updater",
            **({"Authorization": f"Bearer {GH_TOKEN}"} if GH_TOKEN else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def replace_block(text: str, name: str, body: str) -> str:
    """Swap the content between <!-- name:START --> and <!-- name:END -->."""
    pattern = re.compile(
        rf"(<!-- {name}:START -->).*?(<!-- {name}:END -->)", re.DOTALL
    )
    if not pattern.search(text):
        print(f"warn: no {name} markers in README; skipping", file=sys.stderr)
        return text
    return pattern.sub(rf"\1\n{body}\n\2", text)


# ── Open Source: PRs to repos I don't own ────────────────────────────────────
def build_oss() -> str | None:
    try:
        # newest first; merged + open PRs authored by me
        res = gh(
            f"/search/issues?q=type:pr+author:{USER}&sort=updated&order=desc&per_page=100"
        )
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        print(f"warn: OSS search failed ({e}); leaving block", file=sys.stderr)
        return None

    by_repo: dict[str, list[dict]] = defaultdict(list)
    latest: dict[str, str] = {}
    for it in res.get("items", []):
        repo_url = it.get("repository_url", "")  # …/repos/{owner}/{name}
        full = repo_url.split("/repos/", 1)[-1]
        owner = full.split("/", 1)[0]
        if not full or owner.lower() == USER.lower():
            continue  # skip repos I own — those are "Featured", not "Open Source"
        by_repo[full].append(it)
        when = it.get("pull_request", {}).get("merged_at") or it.get("updated_at", "")
        latest[full] = max(latest.get(full, ""), when or "")

    if not by_repo:
        return None

    order = sorted(by_repo, key=lambda r: latest.get(r, ""), reverse=True)
    lines = []
    for full in order:
        owner, name = full.split("/", 1)
        prs = sorted(by_repo[full], key=lambda p: p.get("number", 0))
        refs = ", ".join(f"[#{p['number']}]({p['html_url']}){pr_tag(p)}" for p in prs)
        title = clean_title(prs[0].get("title", ""))
        lines.append(
            f"- **[{name}](https://github.com/{full})** — {title} ({refs})"
        )
    return "\n".join(lines)


def pr_tag(p: dict) -> str:
    """Three-way status: merged (no tag), still open, or closed-unmerged."""
    if p.get("pull_request", {}).get("merged_at"):
        return ""
    return " (open)" if p.get("state") == "open" else " (closed)"


def clean_title(s: str) -> str:
    """Strip the upstream's own trailing issue ref and tidy whitespace."""
    s = re.sub(r"\s*\(#\d+\)\s*$", "", str(s)).strip()
    return t(s, 72)


# ── Featured: my own repos, top by stars, using their own descriptions ───────
def build_featured() -> str | None:
    try:
        repos = gh(f"/users/{USER}/repos?sort=pushed&per_page=100")
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        print(f"warn: repos fetch failed ({e}); leaving block", file=sys.stderr)
        return None

    candidates = [
        r
        for r in repos
        if not r.get("fork")
        and not r.get("archived")
        and r.get("name", "").lower() != USER.lower()  # skip the profile repo itself
        and r.get("description")
    ]
    if not candidates:
        return None
    candidates.sort(
        key=lambda r: (r.get("stargazers_count", 0), r.get("pushed_at", "")),
        reverse=True,
    )
    lines = [
        f"- **[{r['name']}]({r['html_url']})** — {r['description'].strip()}"
        for r in candidates[:FEATURED_COUNT]
    ]
    return "\n".join(lines)


def t(s: str, n: int) -> str:
    s = str(s)
    return s if len(s) <= n else s[: n - 1] + "…"


def main():
    text = original = README.read_text(encoding="utf-8")

    oss = build_oss()
    if oss:
        text = replace_block(text, "OSS", oss)

    featured = build_featured()
    if featured:
        text = replace_block(text, "FEATURED", featured)

    if text != original:
        README.write_text(text, encoding="utf-8")
        print(f"updated {README} ({datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC})")
    else:
        print("no README change")


if __name__ == "__main__":
    main()
