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
    pass


@dataclass
class JobResult:
    job_id: int
    status: str
    coverage: str | None
    items: list[dict] = field(default_factory=list)
    error: str | None = None


class ConsoleClient:
    def __init__(self, base: str | None = None, key: str | None = None, *,
                 poll_every: float = 5.0, max_retries: int = 4) -> None:
        self.base = (base or os.environ.get("XP_BASE") or DEFAULT_BASE).rstrip("/")
        self.key = key or os.environ.get("XP_API_KEY", "")
        self.poll_every = poll_every
        self.max_retries = max_retries
        self._http = httpx.Client(timeout=60, headers={"User-Agent": USER_AGENT})

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
                        raise ConsoleError(f"{method} {path} -> HTTP {r.status_code}: {r.text[:300]}")
                    retry_after = r.headers.get("Retry-After")
                    time.sleep(float(retry_after) if retry_after else delay)
                    delay *= 2
                    continue
                if r.status_code >= 400:
                    raise ConsoleError(f"{method} {path} -> HTTP {r.status_code}: {r.text[:300]}")
                return r.json() if r.content else {}
            time.sleep(delay)
            delay *= 2
        raise ConsoleError(f"{method} {path}: retries exhausted")

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

    def dataset(self, kind: str = "tweets", **params) -> list[dict]:  # noqa: ANN003
        """Read the console's shared dataset store, paginating.

        X job results land in the shared store, not under the job: there is no
        ``/jobs/<id>/tweets`` (verified in content-agent, it 404s). The store is
        read by username, which also returns everything collected earlier, so the
        caller dedupes. ``username`` + ``limit`` are verified parameters; ``since``
        and ``offset`` mirror the MCP ``query_x_tweets`` tool and are passed through.
        """
        out: list[dict] = []
        seen: set[str] = set()
        offset = 0
        while True:
            page = self._request("GET", f"/datasets/{kind}",
                                 params={**params, "limit": 100, "offset": offset})
            items = page if isinstance(page, list) else page.get("items", [])
            fresh = [i for i in items if str(i.get("tweet_id", id(i))) not in seen]
            seen.update(str(i.get("tweet_id", id(i))) for i in fresh)
            out.extend(fresh)
            meta = page.get("page") if isinstance(page, dict) else None
            nxt = (meta or {}).get("next_offset")
            if not fresh or nxt is None:
                return out
            offset = nxt

    def run(self, actor: str, payload: dict, *, timeout: float = 600) -> JobResult:
        """Submit a job and wait. Items are read separately via :meth:`dataset`."""
        job_id = self.submit(actor, payload)
        state = self.wait(job_id, timeout)
        return JobResult(job_id, (state.get("status") or "").lower(), state.get("coverage"),
                         error=state.get("error"))
