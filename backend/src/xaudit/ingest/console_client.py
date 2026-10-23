"""ThoughtPilot scraping console client.

Ported from content-agent/scripts/xpilot/client.py. Same contract:
POST /jobs {actor, input} -> poll GET /jobs/{id} -> GET /jobs/{id}/results.

Two lessons carried over from that client:
- Cloudflare blocks the default urllib User-Agent on POST, so identify honestly.
- A job can report "succeeded" with ``coverage="partial"`` and zero items. The
  caller must see coverage, otherwise "the scraper had no account available"
  is indistinguishable from "the account posted nothing".
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

import httpx

DEFAULT_BASE = "https://scraping.thought-pilot.co/api"
USER_AGENT = "x-algorithm-bot/0.1 (+https://github.com/thoughtpilot99/x-algorithm-bot)"


class ConsoleError(RuntimeError):
    def __init__(self, msg: str, status: int | None = None) -> None:
        super().__init__(msg)
        self.status = status


@dataclass
class JobResult:
    job_id: int
    status: str
    coverage: str | None
    items: list[dict] = field(default_factory=list)
    error: str | None = None


class ConsoleClient:
    def __init__(self, base: str | None = None, key: str | None = None, *,
                 poll_every: float = 5.0, max_retries: int = 4,
                 transport: httpx.BaseTransport | None = None) -> None:
        self.base = (base or os.environ.get("XP_BASE") or DEFAULT_BASE).rstrip("/")
        self.key = key or os.environ.get("XP_API_KEY", "")
        self.poll_every = poll_every
        self.max_retries = max_retries
        self.truncated_reads = 0  # dataset reads that hit max_pages
        self._http = httpx.Client(timeout=60, headers={"User-Agent": USER_AGENT}, transport=transport)

    def available(self) -> bool:
        return bool(self.key)

    def _request(self, method: str, path: str, **kw) -> dict:  # noqa: ANN003
        if not self.key:
            raise ConsoleError("XP_API_KEY not set (add it to .env or the environment)")
        delay = 2.0
        for attempt in range(self.max_retries + 1):
            try:
                r = self._http.request(method, f"{self.base}{path}",
                                       headers={"X-API-Key": self.key}, **kw)
            except httpx.TransportError as e:
                if attempt == self.max_retries:
                    raise ConsoleError(f"{method} {path}: {e}") from e
            else:
                if r.status_code == 429 or r.status_code >= 500:
                    if attempt == self.max_retries:
                        raise ConsoleError(f"{method} {path} -> HTTP {r.status_code}: {r.text[:300]}",
                                           r.status_code)
                    retry_after = r.headers.get("Retry-After")
                    time.sleep(float(retry_after) if retry_after else delay)
                    delay *= 2
                    continue
                if r.status_code >= 400:
                    raise ConsoleError(f"{method} {path} -> HTTP {r.status_code}: {r.text[:300]}", r.status_code)
                return r.json() if r.content else {}
            time.sleep(delay)
            delay *= 2
        raise ConsoleError(f"{method} {path}: retries exhausted")

    def health(self) -> dict:
        """Unauthenticated liveness check."""
        r = self._http.get(f"{self.base}/health")
        r.raise_for_status()
        return r.json() if r.content else {}

    def page(self, kind: str = "tweets", **params) -> dict:  # noqa: ANN003
        """One raw page of the dataset store, with its ``page`` metadata (used by the doctor)."""
        out = self._request("GET", f"/datasets/{kind}", params=params)
        return out if isinstance(out, dict) else {"items": out, "page": None}

    def submit(self, actor: str, payload: dict) -> int:
        job = self._request("POST", "/jobs", json={"actor": actor, "input": payload})
        if "id" not in job:
            raise ConsoleError(f"{actor}: no job id in {str(job)[:200]}")
        return int(job["id"])

    def wait(self, job_id: int, timeout: float = 600) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            state = self._request("GET", f"/jobs/{job_id}")
            if (state.get("status") or "").lower() in {"succeeded", "failed", "cancelled"}:
                return state
            time.sleep(self.poll_every)
        raise ConsoleError(f"job {job_id} did not finish in {timeout}s")

    def dataset(self, kind: str = "tweets", max_pages: int = 60, **params) -> list[dict]:  # noqa: ANN003
        """Read the console's shared dataset store, paginating.

        X job results land in the shared store, not under the job: there is no
        ``/jobs/<id>/tweets`` (verified in content-agent, it 404s). The store is
        read by username, which also returns everything collected earlier, so the
        caller dedupes. ``username`` + ``limit`` are verified parameters; ``since``
        and ``offset`` mirror the MCP ``query_x_tweets`` tool and are passed through.
        """
        out: list[dict] = []
        seen: set[str] = set()
        offset, page_size = 0, 100
        for _ in range(max_pages):
            page = self._request("GET", f"/datasets/{kind}",
                                 params={**params, "limit": page_size, "offset": offset})
            items = page if isinstance(page, list) else page.get("items", [])
            fresh = [i for i in items if str(i.get("tweet_id", id(i))) not in seen]
            seen.update(str(i.get("tweet_id", id(i))) for i in fresh)
            out.extend(fresh)
            meta = page.get("page") if isinstance(page, dict) else None
            if not fresh:
                return out
            if meta and meta.get("next_offset") is not None:
                offset = meta["next_offset"]
            elif meta and meta.get("truncated") is False:
                return out
            elif len(items) >= page_size:
                # The store answered without paging metadata (seen live on 2026-10-23):
                # keep paging by count until a short page arrives.
                offset += len(items)
            else:
                return out
        self.truncated_reads += 1
        return out

    # Where a job's own items can be read. The MCP tool exposes "get_job_results(job_id, kind)";
    # its REST path is not documented in content-agent, so the known shapes are tried in order
    # and the one that answered is remembered for the rest of the run.
    RESULT_PATHS = ("/jobs/{id}/results", "/jobs/{id}/items", "/jobs/{id}/{kind}")
    _result_path: str | None = None

    def job_items(self, job_id: int, kind: str = "tweets", limit: int = 100) -> list[dict]:
        paths = [self._result_path] if self._result_path else list(self.RESULT_PATHS)
        last: Exception | None = None
        for tmpl in paths:
            path = tmpl.format(id=job_id, kind=kind)
            out: list[dict] = []
            offset = 0
            try:
                while True:
                    page = self._request("GET", path, params={"kind": kind, "limit": limit, "offset": offset})
                    items = page if isinstance(page, list) else page.get("items", [])
                    out.extend(items)
                    meta = page.get("page") if isinstance(page, dict) else None
                    if not items or not meta or not meta.get("truncated"):
                        break
                    offset = meta.get("next_offset", offset + len(items))
            except ConsoleError as e:
                if e.status == 404:
                    last = e
                    continue
                raise
            self._result_path = tmpl
            return out
        raise ConsoleError(f"no job-results endpoint answered for job {job_id}: {last}", 404)

    def run(self, actor: str, payload: dict, *, timeout: float = 600) -> JobResult:
        """Submit a job and wait. Items are read separately via :meth:`dataset`."""
        job_id = self.submit(actor, payload)
        state = self.wait(job_id, timeout)
        return JobResult(job_id, (state.get("status") or "").lower(), state.get("coverage"),
                         error=state.get("error"))
