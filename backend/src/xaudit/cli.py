"""Command line: `xaudit <command>`. `xaudit run` executes the full audit from stored data."""

from __future__ import annotations

import json
from pathlib import Path

import typer

app = typer.Typer(no_args_is_help=True, add_completion=False, help=__doc__)


def _print(obj) -> None:  # noqa: ANN001
    typer.echo(json.dumps(obj, indent=2, default=str))


@app.command("sync-repo")
def sync_repo(commits: int = 50) -> None:
    """Clone/fetch xai-org/x-algorithm, rebuild the code index and parameter history."""
    from xaudit.algo import indexer, param_extract, registry, repo_sync

    st = repo_sync.sync()
    _print({"sha": st.sha, "previous": st.previous_sha, "index": indexer.build(),
            "params": param_extract.extract_history(commits), "citations": {
                k: v for k, v in registry.verify().items() if k != "results"}})


@app.command()
def status(needs_backfill: bool = typer.Option(False, "--needs-backfill",
                                               help="Print only true/false: is a full-history backfill needed?")) -> None:
    """Posts, history depth and labels per client in the database."""
    from xaudit.ingest import status as st

    if needs_backfill:
        typer.echo("true" if st.needs_backfill() else "false")
    else:
        _print(st.data_status())


@app.command("verify-citations")
def verify_citations() -> None:
    """Re-check every finding/claim citation against the repository."""
    from xaudit.algo import registry

    r = registry.verify()
    _print({k: v for k, v in r.items() if k != "results"})
    raise typer.Exit(1 if r["failures"] else 0)


@app.command()
def doctor(handle: str = "nifinet", as_json: bool = False) -> None:
    """Check the console API contract (health, auth, record shape, filters). Exit 1 if collection would fail."""
    from xaudit.db.session import session
    from xaudit.ingest import doctor as dr
    from xaudit.ingest.store import finish_run, log_run

    rep = dr.run(handle=handle)
    with session() as s:
        run = log_run(s, source="console_live", actor="doctor", params=rep.as_dict())
        finish_run(run, status="succeeded" if rep.ok else "failed", items=len(rep.checks),
                   error=None if rep.ok else "; ".join(c.name for c in rep.checks if not c.ok))
    if as_json:
        _print(rep.as_dict())
    else:
        for c in rep.checks:
            typer.echo(f"[{'ok' if c.ok else ('FAIL' if c.blocking else 'warn')}] {c.name}: {c.detail}")
    raise typer.Exit(0 if rep.ok else 1)


@app.command()
def monitor(dry_run: bool = typer.Option(False, help="Skip collection; re-analyse stored data only"),
            peers: bool | None = typer.Option(None, "--peers/--no-peers", help="Default: Mondays"),
            weekly: bool | None = typer.Option(None, "--weekly/--no-weekly", help="Default: Mondays"),
            monthly: bool | None = typer.Option(None, "--monthly/--no-monthly", help="Default: 1st of month"),
            threads_cap: int = 40, pdf: bool = True) -> None:
    """Daily monitoring: collect, re-analyse, alerts, experiments, weekly/monthly reports."""
    from xaudit.monitor.snapshot import run as mrun

    _print(mrun(dry_run=dry_run, peers=peers, weekly=weekly, monthly=monthly, threads_cap=threads_cap, pdf=pdf))


@app.command()
def ingest(from_seed: bool = typer.Option(True, "--from-seed/--live"), days: int | None = None,
           missing_only: bool = typer.Option(False, "--missing-only",
                                             help="Live: only clients whose full-history backfill hasn't succeeded")) -> None:
    """Load data: from console JSON exports under data/raw/console (default) or live via XP_API_KEY."""
    if from_seed:
        from xaudit.ingest.seed_import import import_seed

        _print(import_seed())
        return
    from datetime import UTC, datetime

    from xaudit.db.session import load_artifact, save_artifact
    from xaudit.ingest.collectors import collect_all
    from xaudit.ingest.status import data_status, missing_backfill
    from xaudit.settings import analysis_cfg, clients

    handles = missing_backfill() if missing_only else list(clients())
    if not handles:
        _print({"backfill": "nothing missing"})
        return
    out = collect_all(days, handles=handles)
    # A client counts as backfilled only when its own timeline step succeeded.
    timeline = {r["handle"]: r.get("status") for r in out if r.get("handle") in handles and "coverage" in r}
    prev = load_artifact("backfill_done") or {}
    marks = {**(prev.get("clients") or {}),
             **{h: "ok" if timeline.get(h) == "succeeded" else "failed" for h in handles}}
    save_artifact("backfill_done", {"days": days or analysis_cfg()["extended_window_days"], "clients": marks,
                                    "at": datetime.now(UTC).isoformat(), "found": data_status()["clients"]})
    _print({"handles": handles, "backfill": marks, "results": out})


@app.command("import-labels")
def import_labels(folder: Path = typer.Option(Path("../data/labels/out"), help="Folder of content_*/reply_*.jsonl"),
                  method: str = "llm:claude-sonnet-session-review") -> None:
    """Import JSONL labels (content_*.jsonl / reply_*.jsonl) produced by a reviewer or LLM run."""
    from xaudit.analysis.classify import import_labels as imp
    from xaudit.analysis.dataset import load_posts
    from xaudit.settings import clients

    df = load_posts(list(clients()))
    texts = dict(zip(df["tweet_id"], df["text"], strict=True))
    out = {}
    for f in sorted(folder.glob("*.jsonl")):
        out[f.name] = imp(f, "content" if f.name.startswith("content") else "reply", method, texts)
    _print(out)


@app.command()
def classify(use_llm: bool = True) -> None:
    """Label any unlabelled posts (Claude if ANTHROPIC_API_KEY is set, else heuristics)."""
    from xaudit.analysis.classify import classify as cls
    from xaudit.analysis.dataset import load_posts
    from xaudit.analysis.features import add_features
    from xaudit.settings import clients

    for h, c in clients().items():
        df = add_features(load_posts(h))
        _print({h: cls(df, context=f"{c['name']}: {c.get('positioning_hint', '')}", use_llm=use_llm)})


@app.command()
def analyze() -> None:
    """Run reach/engagement/segment/cadence/comment/benchmark engines."""
    from xaudit.analysis.pipeline import run

    _print(run())


@app.command()
def diagnose() -> None:
    """Run hypothesis checkers (evidence guard enforced) and recommendations."""
    from xaudit.diagnostics.engine import run as drun
    from xaudit.recommend.compare import compare
    from xaudit.recommend.engine import run as rrun
    from xaudit.settings import clients

    for h in clients():
        drun(h)
        rrun(h)
    compare()
    typer.echo("diagnostics + recommendations stored")


@app.command("export-rewrite-requests")
def export_rewrite_requests() -> None:
    """Write the selected underperforming posts for rewrite drafting (data/labels/rewrite_requests)."""
    from xaudit.recommend.engine import export_rewrite_requests as exp
    from xaudit.settings import clients

    _print([str(exp(h)) for h in clients()])


@app.command()
def report(pdf: bool = True) -> None:
    """Render Reports A/B/C (HTML, PDF) and CSV exports into reports/."""
    from xaudit.reports.render import render_all

    _print(render_all(pdf=pdf))


@app.command("algo-docs")
def algo_docs() -> None:
    """Regenerate docs/algorithm-research.md from the findings registry."""
    from xaudit.reports.algo_doc import write

    typer.echo(str(write()))


@app.command("notify-slack")
def notify_slack(dry_run: bool = typer.Option(False, help="Print the digest instead of posting it")) -> None:
    """Post the daily digest to Slack (needs SLACK_WEBHOOK_URL)."""
    import os

    from xaudit.monitor import slack

    payload = slack.build_digest()
    if dry_run:
        _print(payload)
        return
    if not os.environ.get("SLACK_WEBHOOK_URL"):
        typer.echo("SLACK_WEBHOOK_URL not set; digest not posted.")
        return
    slack.post(payload)
    typer.echo("Slack digest posted.")


@app.command("export-static")
def export_static(out: Path = typer.Option(Path("../frontend/dist-static"), help="Static build folder")) -> None:
    """Write the dashboard's data as static JSON (plus report PDFs) for a snapshot page."""
    from xaudit.reports.static_export import export, publish_page

    r = export(out)
    page = publish_page(out) if (out / "index.html").exists() else None
    _print({"out": r["out"], "files": r["files"], "publish_page": str(page) if page else None})


@app.command()
def run(pdf: bool = True) -> None:
    """Full audit from stored data: analyze -> diagnose -> report."""
    analyze()
    diagnose()
    report(pdf)


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Serve the API and the built dashboard."""
    import uvicorn

    uvicorn.run("xaudit.api.app:app", host=host, port=port)


if __name__ == "__main__":
    app()
