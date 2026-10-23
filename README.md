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
  api/                    FastAPI (read-only) serving the dashboard
frontend/                 React + Vite + Tailwind + Recharts dashboard
```

Module 8 (continuous monitoring) is Phase 2. Collectors already write timestamped metric observations, so re-running `ingest --live` on a schedule builds the time series it needs.

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

cd ../frontend && npm install && npm run build
cd ../backend && uv run xaudit serve   # http://127.0.0.1:8000
```

Tests: `cd backend && uv run pytest`. They cover the parameter parser, normaliser, features, robust statistics, the evidence guard (including negative cases), the registry schema and citations, and an end-to-end synthetic run through the API.

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
