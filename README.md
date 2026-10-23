# X Account Intelligence & Algorithm Audit

This system explains why an X account gets the reach it gets. It joins three sources:

- the published X recommendation code ([`xai-org/x-algorithm`](https://github.com/xai-org/x-algorithm));
- the account's own posting and commenting history;
- comparable peer accounts.

It then turns the result into ranked, evidence-backed experiments.

It was built for two independent audits: **Nicolas Finet (@nifinet)** and **Michel Lieben (@MichLieben)**.

## Results

| Output | Where |
|---|---|
| Report A: Nicolas Finet, complete audit | `reports/report-A-nicolas-finet.{html,pdf}` |
| Report B: Michel Lieben, complete audit | `reports/report-B-michel-lieben.{html,pdf}` |
| Report C: comparative growth intelligence | `reports/report-C-comparative.{html,pdf}` |
| CSV exports (posts, scored comments, segments, diagnostics, experiments, rewrites, benchmarks) | `reports/csv/` |
| Algorithm research (78 cited findings, 23 checked claims, parameter history) | `docs/algorithm-research.md` |
| Method and data dictionary | `docs/methodology.md` |
| Interactive dashboard | `xaudit serve` (see below) |

## Evidence rules

The system follows these rules throughout.

**Every finding carries an evidence class:**
- `repo_verified`
- `account_observed`
- `statistical_association`
- `hypothesis`
- `unsupported`
- `insufficient`

**Algorithm findings cite a file, a line range and the commit studied.** `xaudit verify-citations` re-opens each file and checks that the quoted anchor text sits inside the cited lines. All 122 citations pass at commit `07d159b`.

**The engines compute the numbers, and the prose may only restate them.** An evidence guard (`diagnostics/guard.py`) rejects any diagnostic that:
- has no evidence;
- cites an unknown finding;
- uses a number that does not appear in its evidence;
- asserts suppression ("shadowban", "penalised").

**Associations are labelled as associations.** Segment tests use ratios of medians with bootstrap confidence intervals and Benjamini–Hochberg-adjusted q-values. A multivariable model controls for month, format and topic.

**Missing data is stated, never filled in.** This audit uses public data only. Profile visits, follows, link clicks, audience data and follower history are listed as unavailable in every report.

## Architecture

```
backend/src/xaudit/
  ingest/       Module 1  console client, collectors, seed import, normaliser, dedupe, collection log
  algo/         Module 2  repo sync, code index (SQLite FTS5), param! extraction + history, findings/claims registry
  analysis/     Module 3  features, labelling, reach, engagement, segments, cadence, pipeline
  comments/     Module 4  reply roles, categories, effectiveness score, network, engagers
  diagnostics/  Module 5  hypothesis checkers, Diagnostic model, evidence guard
  recommend/    Module 6  root-cause ranking, stop/continue/start, rewrites, 30-day plan with power analysis
  reports/      Module 7  Reports A/B/C (Jinja2 -> HTML -> PDF via Chromium), CSV, algorithm doc
  benchmark/              peer selection and size-normalised comparison
  monitor/      Module 8  daily runner, metric time series, control-limit alerts, experiment tracking
  benchmark/              peer selection and size-normalised comparison
  api/                    FastAPI (read-only) serving the dashboard
frontend/                 React + Vite + Tailwind + Recharts dashboard
.github/workflows/monitor.yml   daily monitoring in GitHub Actions
```

## Monitoring (Module 8)

`xaudit monitor` runs once a day, in GitHub Actions. Each run does the following.

**Collection**
- `xaudit doctor` first checks the console API contract (health, auth, record shape, filters). If anything fails, the run stops instead of quietly collecting nothing.
- It then collects the last 14 days of posts and replies, a follower snapshot, new replies that mention each account, and thread context for new conversational comments (up to 40 per account per day). Peers are refreshed on Mondays.
- Every collection appends a new metric observation rather than overwriting. Posts therefore build 24h, 72h and 7-day view curves, and followers build a daily series.

**Analysis and alerts**
- The full audit is re-run on the updated data.
- Alerts use robust control limits: the trailing 8-week median of weekly median log views, ± 3 robust SD. They fire per account and per format, and only after 6 complete weeks of history.
- Other alerts cover follower-change outliers, failed or partial collection, changed published parameters in `xai-org/x-algorithm`, and citations that no longer match the repository.

**Experiments and reports**
- Experiments are registered in `backend/src/xaudit/config/experiments.yaml`. Setting a `start` date begins tracking; each is judged against its decision rule and is never called before its minimum sample is reached.
- A weekly report is written to `reports/weekly/` on Mondays. A monthly growth audit (Reports A/B/C plus month-over-month changes) is written to `reports/monthly/YYYY-MM/` on the 1st.

### Turning it on
1. **Add the repository secret.** Under Settings → Secrets and variables → Actions, add `XP_API_KEY`. `ANTHROPIC_API_KEY` is optional; it labels new posts with Claude, and heuristics are used otherwise. Never commit keys.
2. **Merge to the default branch.** GitHub only runs scheduled workflows from the default branch.
3. **Start it manually once.** Run the `monitor` workflow with *Run workflow* (mode `weekly`).
   - The first run has no saved state. It collects 180 days, imports the reviewed labels in `backend/seed/`, and builds the database.
   - Later runs restore the database from the previous run's `xaudit-state` artifact. Keep at least one run every 90 days so it does not expire.

Locally: `uv run xaudit monitor --dry-run` re-analyses stored data without collecting.

### Daily Slack digest
After each daily run the workflow posts a digest to a Slack channel. It covers active alerts, and for each account: followers, the last 24 hours (posts, comments, lead-magnet replies), the last 7 days against the previous 4 weeks, top and weakest posts with links, experiment status and the top barriers. If a run fails, it posts a short notice with the log link.

To enable it:
1. Create a Slack app with an **Incoming Webhook** for the channel.
2. Add the webhook URL as the repository secret `SLACK_WEBHOOK_URL`.

Without the secret the step is skipped. Preview the message locally with `uv run xaudit notify-slack --dry-run`.

### Dashboard snapshot (private web page)
`VITE_STATIC=1 npm run build` (in `frontend/`) followed by `uv run xaudit export-static` (in `backend/`) produces `frontend/dist-static/dashboard.html`. That is a single publishable page with the dashboard data exported as JSON next to it. It is published as a private claude.ai page and republished when the data changes.

## Quick start

```bash
cd backend
uv sync --all-extras
cp ../.env.example ../.env          # add XP_API_KEY for live collection (optional ANTHROPIC_API_KEY)

uv run xaudit sync-repo             # clone xai-org/x-algorithm, index code, extract parameter history
uv run xaudit ingest                # load console exports from data/raw/console (or --live with XP_API_KEY)
uv run xaudit import-labels         # optional: reviewed labels from data/labels/out
uv run xaudit run                   # analyze -> diagnose -> report (HTML, PDF, CSV)
uv run xaudit algo-docs             # regenerate docs/algorithm-research.md
uv run xaudit verify-citations      # re-check every repo citation
uv run xaudit doctor                # check the console API contract (needs XP_API_KEY)
uv run xaudit monitor --dry-run     # alerts, experiments, weekly report from stored data

cd ../frontend && npm install && npm run build
cd ../backend && uv run xaudit serve   # http://127.0.0.1:8000
```

Tests: `cd backend && uv run pytest`. They cover the parameter parser, normaliser, features, robust statistics, the evidence guard (including negative cases), the registry schema and citations, an end-to-end synthetic run through the API, control-limit alerts, experiment evaluation, and the doctor and console client against a mocked API.

## Data sources

**ThoughtPilot scraping console** (`XP_API_KEY`):
- `user-tweets` with replies, `tweet-detail` (parent post and thread), `client-engagers`, `user-info`;
- the shared dataset store.

The first dataset (2026-10-23) was exported from the console store through its MCP tools into `data/raw/console`:
- 180 days of posts and replies for both accounts;
- profiles;
- 71 reply threads;
- public replies by others;
- 90 days of original posts for 11 peers.

Files were copied programmatically and spot-checked against the source.

`data/` is git-ignored because it holds collected data, labels, the SQLite database and the cloned algorithm repository.

**Labels** (topic, hook, narrative, the reply categories from the brief):
- The app labels with Claude when `ANTHROPIC_API_KEY` is set, and with deterministic heuristics otherwise.
- The first audit used model-reviewed labels imported with `xaudit import-labels`.
- Every label row records the method that produced it.
