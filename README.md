
<a href="https://github.com/LukeTheoJohnson?tab=repositories">
<img src="assets/widget.svg" alt="Profile widget: my public projects (language, stars and a 14-day commit heatmap each) and merged open-source contributions grouped by upstream project and a 12-month merged-PR cadence chart — refreshed daily from the GitHub API" width="100%"/>
</a>

---

## Use this widget on your own profile

**Fork this repo** — the GitHub Actions workflow runs daily and regenerates `assets/widget.svg` automatically. No API keys or secrets needed; the workflow uses the built-in `GITHUB_TOKEN`.

Your GitHub username is detected automatically from the Actions environment, so the widget shows your data immediately after forking. To customise it, add these repository variables under **Settings → Secrets and variables → Actions → Variables**:

| Variable | Default | Description |
|---|---|---|
| `WIDGET_NAME` | your GitHub username | Display name shown in the header |
| `WIDGET_TAGLINE` | *(none)* | Short tagline shown top-right (e.g. `OPEN SOURCE · PYTHON · ML`) |
| `WIDGET_PROJECT_LIMIT` | `6` | Max own-project cards shown on the left |
| `WIDGET_BAR_LIMIT` | `6` | Max merged-PR repo bars shown on the right |
| `WIDGET_CORE_STARS` | `10000` | Star threshold for the "key insight" caption to call a project "core" |

Then embed the widget in your profile README:

```markdown
<a href="https://github.com/YOUR_USERNAME?tab=repositories">
<img src="assets/widget.svg" width="100%"/>
</a>
```

**What it shows:**
- Left — your non-fork public repos, sorted by recent activity, each with language, star count, and a 14-day commit heatmap
- Right — your merged pull requests grouped by upstream project over the last year, plus a 12-month cadence sparkline
- A generated "key insight" caption highlighting your highest-impact open-source contributions

Private repos are never included — merged-PR data is explicitly scoped to public repositories so a local token and the Actions token produce identical output.

<div align="center">

<!-- <img src="https://capsule-render.vercel.app/api?type=waving&color=0:2ac3de,30:7aa2f7,65:bb9af7,100:9d7cd8&height=100&section=footer&animation=twinkling" width="100%"/> -->

</div>

<!-- <img src="https://capsule-render.vercel.app/api?type=waving&color=0:2ac3de,30:7aa2f7,65:bb9af7,100:9d7cd8&height=180&section=header&text=Luke%20Johnson&fontSize=70&fontColor=ffffff&animation=fadeIn" width="100%"/> -->
