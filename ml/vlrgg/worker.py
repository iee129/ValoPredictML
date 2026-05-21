from __future__ import annotations

import argparse
import csv
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import multiprocessing as mp
import os
from pathlib import Path
import sqlite3
import sys
import time
from typing import Any
from urllib.robotparser import RobotFileParser

import requests

from ml.vlrgg_client import DEFAULT_API_BASE_URL, VLRGGClient
from ml.vlrgg_rate_limit import VLRGGRateLimitError, raise_for_limit_like_response


CANONICAL_PLAN_PATH = Path(".omc/plans/vlrgg_worker_auto_collection.md")
DEFAULT_SOURCES = ("match_details", "events", "teams", "players")
SOURCE_PRIORITY = ("match_details", "events", "teams", "players")
SOURCE_ID_COLUMNS = {
    "match_details": ("match_id", "candidate_id", "id"),
    "events": ("event_id", "candidate_id", "id"),
    "teams": ("team_id", "candidate_id", "id"),
    "players": ("player_id", "candidate_id", "id"),
}
SOURCE_CSV_FILES = {
    "match_details": "vlrgg_match_details_raw.csv",
    "events": "vlrgg_event_details.csv",
    "teams": "vlrgg_team_profiles.csv",
    "players": "vlrgg_player_profiles.csv",
}
SOURCE_PAYLOAD_IDS = {
    "match_details": "match_id",
    "events": "event_id",
    "teams": "team_id",
    "players": "player_id",
}
USER_AGENT = "ValoPredicML/1.0 (academic research; non-commercial)"
ROBOTS_URL = "https://www.vlr.gg/robots.txt"
ROBOTS_ALLOWED_PATHS = (
    "/",
    "/stats",
    "/events",
    "/event/",
    "/event/stats/",
    "/event/agents/",
    "/event/matches/",
    "/matches/results",
    "/player/",
    "/team/",
    "/team/stats/",
    "/team/transactions/",
)
ROBOTS_BLOCKED_PATHS = ("/search/auto", "/rr", "/rr/")
JOB_DONE_STATUSES = ("completed", "error")
QUEUE_ACTIVE_STATUSES = ("pending", "retry", "in_progress")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def unix_now() -> float:
    return time.time()


def parse_utc(value: str | None) -> float:
    if not value:
        return 0.0
    text = str(value).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return 0.0


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def clean_id(value: Any) -> str:
    text = str(value or "").strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return ""
    return text


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class Job:
    id: int
    source: str
    job_key: str
    payload: dict[str, Any]
    attempts: int


@dataclass(frozen=True)
class PreflightResult:
    ok: bool
    reason: str
    detail: dict[str, Any]


class QueueStore:
    def __init__(self, queue_path: Path) -> None:
        self.queue_path = Path(queue_path)
        ensure_parent(self.queue_path)
        self.init()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.queue_path), timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    @contextmanager
    def connection(self) -> Any:
        conn = self.connect()
        try:
            yield conn
        finally:
            conn.close()

    def init(self) -> None:
        with self.connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    job_key TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    claimed_by TEXT,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    next_retry_at REAL NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    error TEXT,
                    UNIQUE(source, job_key)
                );
                CREATE INDEX IF NOT EXISTS idx_jobs_claim
                    ON jobs(status, source, next_retry_at, updated_at);
                CREATE TABLE IF NOT EXISTS results (
                    source TEXT NOT NULL,
                    job_key TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    worker_id TEXT NOT NULL,
                    raw_sha256 TEXT NOT NULL,
                    PRIMARY KEY(source, job_key)
                );
                CREATE TABLE IF NOT EXISTS worker_status (
                    worker_id TEXT PRIMARY KEY,
                    pid INTEGER,
                    status TEXT NOT NULL,
                    source TEXT,
                    job_key TEXT,
                    jobs_completed INTEGER NOT NULL DEFAULT 0,
                    jobs_failed INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    last_seen TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS rate_limits (
                    scope TEXT PRIMARY KEY,
                    last_slot_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS run_metadata (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL
                );
                """
            )

    def set_metadata(self, key: str, value: Any) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO run_metadata(key, value_json)
                VALUES(?, ?)
                ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json
                """,
                (key, json_dumps(value)),
            )

    def upsert_job(self, source: str, job_key: str, payload: dict[str, Any]) -> bool:
        now = utc_now()
        with self.connection() as conn:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO jobs(
                    source, job_key, payload_json, status, attempts,
                    next_retry_at, updated_at
                )
                VALUES(?, ?, ?, 'pending', 0, 0, ?)
                """,
                (source, job_key, json_dumps(payload), now),
            )
            return cur.rowcount > 0

    def release_stale_claims(self, stale_after_seconds: float) -> int:
        cutoff = unix_now() - max(float(stale_after_seconds), 0.0)
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT id, updated_at FROM jobs WHERE status = 'in_progress'"
            ).fetchall()
            stale_ids = [row["id"] for row in rows if parse_utc(row["updated_at"]) < cutoff]
            if not stale_ids:
                return 0
            placeholders = ",".join("?" for _ in stale_ids)
            conn.execute(
                f"""
                UPDATE jobs
                SET status = 'retry',
                    claimed_by = NULL,
                    next_retry_at = ?,
                    updated_at = ?,
                    error = 'claim lease expired'
                WHERE id IN ({placeholders})
                """,
                (unix_now(), utc_now(), *stale_ids),
            )
            return len(stale_ids)

    def claim_job(
        self,
        *,
        worker_id: str,
        source_order: list[str],
        stale_after_seconds: float,
    ) -> Job | None:
        self.release_stale_claims(stale_after_seconds)
        now = unix_now()
        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                for source in source_order:
                    row = conn.execute(
                        """
                        SELECT id, source, job_key, payload_json, attempts
                        FROM jobs
                        WHERE source = ?
                          AND status IN ('pending', 'retry')
                          AND next_retry_at <= ?
                        ORDER BY attempts ASC, updated_at ASC, id ASC
                        LIMIT 1
                        """,
                        (source, now),
                    ).fetchone()
                    if row is None:
                        continue
                    conn.execute(
                        """
                        UPDATE jobs
                        SET status = 'in_progress',
                            claimed_by = ?,
                            attempts = attempts + 1,
                            updated_at = ?,
                            error = NULL
                        WHERE id = ? AND status IN ('pending', 'retry')
                        """,
                        (worker_id, utc_now(), row["id"]),
                    )
                    conn.execute("COMMIT")
                    payload = json.loads(row["payload_json"] or "{}")
                    return Job(
                        id=int(row["id"]),
                        source=str(row["source"]),
                        job_key=str(row["job_key"]),
                        payload=payload if isinstance(payload, dict) else {},
                        attempts=int(row["attempts"]) + 1,
                    )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
        return None

    def complete_job(
        self,
        *,
        job: Job,
        worker_id: str,
        result_payload: dict[str, Any],
    ) -> None:
        now = utc_now()
        raw_json = json_dumps(result_payload)
        raw_sha = hashlib.sha256(raw_json.encode("utf-8")).hexdigest()
        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    """
                    INSERT INTO results(source, job_key, payload_json, fetched_at, worker_id, raw_sha256)
                    VALUES(?, ?, ?, ?, ?, ?)
                    ON CONFLICT(source, job_key) DO UPDATE SET
                        payload_json = excluded.payload_json,
                        fetched_at = excluded.fetched_at,
                        worker_id = excluded.worker_id,
                        raw_sha256 = excluded.raw_sha256
                    """,
                    (job.source, job.job_key, raw_json, now, worker_id, raw_sha),
                )
                conn.execute(
                    """
                    UPDATE jobs
                    SET status = 'completed',
                        claimed_by = NULL,
                        next_retry_at = 0,
                        updated_at = ?,
                        error = NULL
                    WHERE id = ?
                    """,
                    (now, job.id),
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def fail_job(
        self,
        *,
        job: Job,
        worker_id: str,
        error: str,
        max_attempts: int,
        retry_backoff_seconds: float,
        max_retry_backoff_seconds: float,
    ) -> str:
        attempts = max(job.attempts, 1)
        if attempts >= max_attempts:
            status = "error"
            next_retry_at = 0.0
        else:
            status = "retry"
            backoff = min(
                float(max_retry_backoff_seconds),
                float(retry_backoff_seconds) * (2 ** max(attempts - 1, 0)),
            )
            next_retry_at = unix_now() + max(backoff, 1.0)
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET status = ?,
                    claimed_by = NULL,
                    next_retry_at = ?,
                    updated_at = ?,
                    error = ?
                WHERE id = ?
                """,
                (status, next_retry_at, utc_now(), error[:2000], job.id),
            )
            conn.execute(
                """
                INSERT INTO worker_status(
                    worker_id, pid, status, source, job_key,
                    jobs_completed, jobs_failed, last_error, last_seen
                )
                VALUES(?, ?, 'failed_job', ?, ?, 0, 1, ?, ?)
                ON CONFLICT(worker_id) DO UPDATE SET
                    status = 'failed_job',
                    source = excluded.source,
                    job_key = excluded.job_key,
                    jobs_failed = worker_status.jobs_failed + 1,
                    last_error = excluded.last_error,
                    last_seen = excluded.last_seen
                """,
                (worker_id, os.getpid(), job.source, job.job_key, error[:2000], utc_now()),
            )
        return status

    def update_worker_status(
        self,
        *,
        worker_id: str,
        status: str,
        source: str | None = None,
        job_key: str | None = None,
        completed_delta: int = 0,
        failed_delta: int = 0,
        error: str | None = None,
    ) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO worker_status(
                    worker_id, pid, status, source, job_key,
                    jobs_completed, jobs_failed, last_error, last_seen
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(worker_id) DO UPDATE SET
                    pid = excluded.pid,
                    status = excluded.status,
                    source = excluded.source,
                    job_key = excluded.job_key,
                    jobs_completed = worker_status.jobs_completed + excluded.jobs_completed,
                    jobs_failed = worker_status.jobs_failed + excluded.jobs_failed,
                    last_error = COALESCE(excluded.last_error, worker_status.last_error),
                    last_seen = excluded.last_seen
                """,
                (
                    worker_id,
                    os.getpid(),
                    status,
                    source,
                    job_key,
                    completed_delta,
                    failed_delta,
                    error,
                    utc_now(),
                ),
            )

    def reserve_request_slot(self, *, scope: str, min_interval_seconds: float) -> float:
        interval = max(float(min_interval_seconds), 0.0)
        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute(
                    "SELECT last_slot_at FROM rate_limits WHERE scope = ?",
                    (scope,),
                ).fetchone()
                now = time.monotonic()
                last_slot = float(row["last_slot_at"]) if row else 0.0
                slot = max(now, last_slot + interval)
                conn.execute(
                    """
                    INSERT INTO rate_limits(scope, last_slot_at)
                    VALUES(?, ?)
                    ON CONFLICT(scope) DO UPDATE SET last_slot_at = excluded.last_slot_at
                    """,
                    (scope, slot),
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
        wait_seconds = max(slot - time.monotonic(), 0.0)
        if wait_seconds > 0:
            time.sleep(wait_seconds)
        return wait_seconds

    def counts_by_source_status(self) -> dict[str, dict[str, int]]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT source, status, COUNT(*) AS count
                FROM jobs
                GROUP BY source, status
                ORDER BY source, status
                """
            ).fetchall()
        counts: dict[str, dict[str, int]] = {}
        for row in rows:
            counts.setdefault(str(row["source"]), {})[str(row["status"])] = int(row["count"])
        return counts

    def backlog_counts(self) -> dict[str, int]:
        counts = self.counts_by_source_status()
        backlog: dict[str, int] = {}
        for source, source_counts in counts.items():
            backlog[source] = sum(
                int(source_counts.get(status, 0))
                for status in ("pending", "retry", "in_progress")
            )
        return backlog

    def has_active_jobs(self) -> bool:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM jobs
                WHERE status IN ('pending', 'retry', 'in_progress')
                """
            ).fetchone()
        return bool(row and int(row["count"]) > 0)

    def result_counts(self) -> dict[str, int]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT source, COUNT(*) AS count FROM results GROUP BY source ORDER BY source"
            ).fetchall()
        return {str(row["source"]): int(row["count"]) for row in rows}

    def worker_rows(self) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT worker_id, pid, status, source, job_key, jobs_completed,
                       jobs_failed, last_error, last_seen
                FROM worker_status
                ORDER BY worker_id
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def result_rows(self, source: str) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT source, job_key, payload_json, fetched_at, worker_id, raw_sha256
                FROM results
                WHERE source = ?
                ORDER BY fetched_at, job_key
                """,
                (source,),
            ).fetchall()
        return [dict(row) for row in rows]


def ordered_sources(sources: list[str]) -> list[str]:
    seen = set()
    ordered: list[str] = []
    for source in SOURCE_PRIORITY:
        if source in sources and source not in seen:
            ordered.append(source)
            seen.add(source)
    for source in sources:
        if source not in seen:
            ordered.append(source)
            seen.add(source)
    return ordered


def preferred_sources_for_workers(sources: list[str], workers: int) -> list[str | None]:
    ordered = ordered_sources(sources)
    preferred: list[str | None] = []
    for index in range(max(int(workers), 0)):
        preferred.append(ordered[index] if index < len(ordered) else None)
    return preferred


def source_order_for_worker(
    *,
    sources: list[str],
    preferred_source: str | None,
    backlog: dict[str, int],
) -> list[str]:
    ordered = ordered_sources(sources)
    result: list[str] = []
    if preferred_source in ordered and backlog.get(str(preferred_source), 0) > 0:
        result.append(str(preferred_source))
    remaining = [source for source in ordered if source not in result]
    remaining.sort(
        key=lambda source: (
            -int(backlog.get(source, 0)),
            SOURCE_PRIORITY.index(source) if source in SOURCE_PRIORITY else len(SOURCE_PRIORITY),
            source,
        )
    )
    return result + remaining


def iter_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def extract_source_key(source: str, row: dict[str, Any]) -> str:
    for column in SOURCE_ID_COLUMNS[source]:
        value = clean_id(row.get(column))
        if value:
            return value
    if source == "match_details":
        url = clean_id(row.get("source_url") or row.get("url") or row.get("match_page"))
        match_id = VLRGGClient.extract_match_id(url)
        return match_id or ""
    if source == "events":
        url = clean_id(row.get("source_url") or row.get("url") or row.get("url_path"))
        event_id = VLRGGClient.extract_event_id(url)
        return event_id or ""
    return ""


def candidate_rows_for_source(args: argparse.Namespace, source: str) -> list[dict[str, Any]]:
    paths_by_source = {
        "match_details": [Path(args.match_candidates_file)],
        "events": [Path(args.event_candidates_file)],
        "teams": [Path(args.team_candidates_file)],
        "players": [Path(args.player_candidates_file)],
    }
    rows: list[dict[str, Any]] = []
    for path in paths_by_source.get(source, []):
        for row in iter_csv_rows(path):
            if source == "match_details":
                candidate_type = clean_id(row.get("candidate_type")).lower()
                if candidate_type and candidate_type != "match":
                    continue
            rows.append(row)
    return rows


def seed_from_report(path: Path, sources: set[str]) -> list[tuple[str, str, dict[str, Any]]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    jobs: list[tuple[str, str, dict[str, Any]]] = []
    if "match_details" in sources:
        pending = payload.get("pending_match_details", [])
        if isinstance(pending, list):
            for item in pending:
                if isinstance(item, dict):
                    key = clean_id(item.get("match_id") or item.get("candidate_id"))
                    job_payload = dict(item)
                else:
                    key = clean_id(item)
                    job_payload = {"match_id": key, "source_report": str(path)}
                if key:
                    jobs.append(("match_details", key, job_payload))
    return jobs


def seed_queue(args: argparse.Namespace, store: QueueStore) -> dict[str, int]:
    enabled_sources = set(args.sources)
    inserted: dict[str, int] = {source: 0 for source in args.sources}
    max_per_source = max(int(args.max_seed_jobs_per_source), 0)
    for source in args.sources:
        rows = candidate_rows_for_source(args, source)
        seen = 0
        for row in rows:
            job_key = extract_source_key(source, row)
            if not job_key:
                continue
            payload = dict(row)
            payload.setdefault(SOURCE_PAYLOAD_IDS[source], job_key)
            payload.setdefault("seed_source", "csv")
            if store.upsert_job(source, job_key, payload):
                inserted[source] += 1
            seen += 1
            if max_per_source and seen >= max_per_source:
                break
    for report_file in args.report_file:
        for source, job_key, payload in seed_from_report(Path(report_file), enabled_sources):
            if max_per_source and inserted.get(source, 0) >= max_per_source:
                continue
            if store.upsert_job(source, job_key, payload):
                inserted[source] = inserted.get(source, 0) + 1
    return inserted


def robots_allows(text: str, path: str) -> bool:
    parser = RobotFileParser()
    parser.set_url(ROBOTS_URL)
    parser.parse(text.splitlines())
    return bool(parser.can_fetch("*", f"https://www.vlr.gg{path}"))


def check_robots_policy(timeout_seconds: float = 15.0) -> PreflightResult:
    try:
        response = requests.get(
            ROBOTS_URL,
            headers={"User-Agent": USER_AGENT},
            timeout=timeout_seconds,
        )
        raise_for_limit_like_response(
            url=ROBOTS_URL,
            status_code=response.status_code,
            headers=response.headers,
            body=response.text,
        )
        response.raise_for_status()
    except VLRGGRateLimitError as exc:
        return PreflightResult(False, "robots_rate_limit", {"error": str(exc)})
    except requests.RequestException as exc:
        return PreflightResult(False, "robots_request_failed", {"error": str(exc)})

    text = response.text
    allowed_checks = {path: robots_allows(text, path) for path in ROBOTS_ALLOWED_PATHS}
    blocked_checks = {path: not robots_allows(text, path) for path in ROBOTS_BLOCKED_PATHS}
    conflicts = [
        path for path, allowed in allowed_checks.items()
        if path in {"/events", "/event/", "/player/", "/team/"} and not allowed
    ]
    if conflicts:
        return PreflightResult(
            False,
            "robots_policy_conflict",
            {
                "conflicts": conflicts,
                "allowed_path_checks": allowed_checks,
                "blocked_path_checks": blocked_checks,
            },
        )
    return PreflightResult(
        True,
        "robots_ok",
        {
            "robots_url": ROBOTS_URL,
            "content_sha256": hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest(),
            "allowed_path_checks": allowed_checks,
            "blocked_path_checks": blocked_checks,
        },
    )


def check_api_health(api_base_url: str, timeout_seconds: float = 5.0) -> PreflightResult:
    base = api_base_url.rstrip("/")
    attempts: list[dict[str, Any]] = []
    for path in ("/v2/health", "/health"):
        url = f"{base}{path}"
        try:
            response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout_seconds)
            detail: dict[str, Any] = {
                "url": url,
                "status_code": response.status_code,
                "text": response.text[:500],
            }
            attempts.append(detail)
            if response.status_code < 500 and response.status_code != 404:
                return PreflightResult(True, "api_health_ok", {"attempts": attempts})
        except requests.exceptions.ConnectionError as exc:
            attempts.append({"url": url, "error": f"connection_error: {exc}"})
        except requests.exceptions.Timeout:
            attempts.append({"url": url, "error": "timeout"})
        except requests.RequestException as exc:
            attempts.append({"url": url, "error": str(exc)})
    return PreflightResult(False, "api_health_failed", {"attempts": attempts})


def write_json_atomic(path: Path, payload: Any) -> None:
    ensure_parent(path)
    tmp_path = path.with_name(f".{path.name}.{os.getpid()}.{time.monotonic_ns()}.tmp")
    tmp_path.write_text(json_dumps(payload), encoding="utf-8")
    os.replace(tmp_path, path)


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    ensure_parent(path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json_dumps(payload) + "\n")


def stop_reason_from_files(state_dir: Path) -> str | None:
    user_stop = state_dir / "STOP"
    if user_stop.exists():
        return "user_stop_file"
    internal_stop = state_dir / "INTERNAL_STOP"
    if internal_stop.exists():
        try:
            payload = json.loads(internal_stop.read_text(encoding="utf-8"))
            return clean_id(payload.get("reason")) or "internal_stop_file"
        except Exception:
            return "internal_stop_file"
    return None


def write_internal_stop(state_dir: Path, reason: str, detail: dict[str, Any] | None = None) -> None:
    write_json_atomic(
        state_dir / "INTERNAL_STOP",
        {"reason": reason, "detail": detail or {}, "stopped_at": utc_now()},
    )


def fetch_job_payload(client: VLRGGClient, job: Job) -> dict[str, Any]:
    if job.source == "match_details":
        result = client.fetch_match_details(job.job_key)
    elif job.source == "events":
        result = client.fetch_event_detail(job.job_key)
    elif job.source == "teams":
        result = client.fetch_team(job.job_key)
    elif job.source == "players":
        result = client.fetch_player(job.job_key, timespan="all")
    else:
        raise ValueError(f"unsupported source: {job.source}")
    if result is None:
        raise RuntimeError(f"{job.source} returned no payload for {job.job_key}")
    return result


def worker_main(config: dict[str, Any], worker_index: int, preferred_source: str | None) -> None:
    args = argparse.Namespace(**config)
    worker_id = f"worker_{worker_index}"
    store = QueueStore(Path(args.state_dir) / "queue.sqlite")
    client = VLRGGClient(
        cache_dir=str(Path(args.state_dir) / "api_cache"),
        base_url=args.api_base_url,
        rate_limit_per_second=1.0 / max(float(args.per_worker_min_request_interval_seconds), 0.001),
    )
    last_request_at = 0.0
    consecutive_failures = 0
    jobs_seen = 0
    store.update_worker_status(worker_id=worker_id, status="idle")
    while True:
        reason = stop_reason_from_files(Path(args.state_dir))
        if reason:
            store.update_worker_status(worker_id=worker_id, status=f"stopped:{reason}")
            return
        backlog = store.backlog_counts()
        source_order = source_order_for_worker(
            sources=list(args.sources),
            preferred_source=preferred_source,
            backlog=backlog,
        )
        job = store.claim_job(
            worker_id=worker_id,
            source_order=source_order,
            stale_after_seconds=float(args.claim_stale_after_seconds),
        )
        if job is None:
            store.update_worker_status(worker_id=worker_id, status="idle")
            if not args.continuous:
                return
            time.sleep(float(args.worker_idle_sleep_seconds))
            continue

        jobs_seen += 1
        store.update_worker_status(
            worker_id=worker_id,
            status="running",
            source=job.source,
            job_key=job.job_key,
        )
        try:
            elapsed = time.monotonic() - last_request_at
            worker_wait = max(float(args.per_worker_min_request_interval_seconds) - elapsed, 0.0)
            if worker_wait > 0:
                time.sleep(worker_wait)
            global_wait = store.reserve_request_slot(
                scope="global_api",
                min_interval_seconds=float(args.global_min_request_interval_seconds),
            )
            last_request_at = time.monotonic()
            payload = fetch_job_payload(client, job)
            store.complete_job(
                job=job,
                worker_id=worker_id,
                result_payload={
                    SOURCE_PAYLOAD_IDS[job.source]: job.job_key,
                    "source": job.source,
                    "job_key": job.job_key,
                    "payload": payload,
                    "fetched_at": utc_now(),
                    "worker_id": worker_id,
                    "global_wait_seconds": round(global_wait, 3),
                },
            )
            store.update_worker_status(
                worker_id=worker_id,
                status="completed_job",
                source=job.source,
                job_key=job.job_key,
                completed_delta=1,
            )
            consecutive_failures = 0
        except VLRGGRateLimitError as exc:
            error = f"rate_limit: {exc}"
            store.fail_job(
                job=job,
                worker_id=worker_id,
                error=error,
                max_attempts=int(args.max_attempts),
                retry_backoff_seconds=float(args.retry_backoff_seconds),
                max_retry_backoff_seconds=float(args.max_retry_backoff_seconds),
            )
            write_internal_stop(Path(args.state_dir), "rate_limit", {"worker_id": worker_id, "error": error})
            return
        except Exception as exc:
            consecutive_failures += 1
            error = f"{type(exc).__name__}: {exc}"
            status = store.fail_job(
                job=job,
                worker_id=worker_id,
                error=error,
                max_attempts=int(args.max_attempts),
                retry_backoff_seconds=float(args.retry_backoff_seconds),
                max_retry_backoff_seconds=float(args.max_retry_backoff_seconds),
            )
            if (
                consecutive_failures >= int(args.max_consecutive_worker_failures)
                or status == "error"
            ):
                write_internal_stop(
                    Path(args.state_dir),
                    "repeated_worker_failure",
                    {"worker_id": worker_id, "source": job.source, "job_key": job.job_key, "error": error},
                )
                return
        if int(args.max_jobs_per_worker) > 0 and jobs_seen >= int(args.max_jobs_per_worker):
            store.update_worker_status(worker_id=worker_id, status="max_jobs_reached")
            return


def csv_escape_row(row: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in row.items():
        if isinstance(value, (dict, list)):
            result[key] = json_dumps(value)
        elif value is None:
            result[key] = ""
        else:
            result[key] = str(value)
    return result


def write_source_csvs(store: QueueStore, output_dir: Path, sources: list[str]) -> dict[str, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    row_counts: dict[str, int] = {}
    for source in sources:
        rows = store.result_rows(source)
        filename = SOURCE_CSV_FILES[source]
        path = output_dir / filename
        fieldnames = [
            SOURCE_PAYLOAD_IDS[source],
            "source",
            "job_key",
            "fetched_at",
            "worker_id",
            "raw_sha256",
            "raw_json",
        ]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                payload = json.loads(row["payload_json"] or "{}")
                writer.writerow(
                    csv_escape_row(
                        {
                            SOURCE_PAYLOAD_IDS[source]: payload.get(SOURCE_PAYLOAD_IDS[source], row["job_key"]),
                            "source": source,
                            "job_key": row["job_key"],
                            "fetched_at": row["fetched_at"],
                            "worker_id": row["worker_id"],
                            "raw_sha256": row["raw_sha256"],
                            "raw_json": payload.get("payload", payload),
                        }
                    )
                )
        row_counts[filename] = len(rows)
    return row_counts


def write_row_counts_csv(path: Path, row_counts: dict[str, int]) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["table", "rows"])
        writer.writeheader()
        for table, rows in sorted(row_counts.items()):
            writer.writerow({"table": table, "rows": rows})


def write_worker_health_csv(path: Path, workers: list[dict[str, Any]]) -> None:
    ensure_parent(path)
    fieldnames = [
        "worker_id",
        "pid",
        "status",
        "source",
        "job_key",
        "jobs_completed",
        "jobs_failed",
        "last_error",
        "last_seen",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for worker in workers:
            writer.writerow({key: worker.get(key, "") for key in fieldnames})


def write_optional_png(reports_dir: Path, row_counts: dict[str, int]) -> None:
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except Exception:
        return
    if not row_counts:
        return
    labels = list(row_counts.keys())
    values = [row_counts[label] for label in labels]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(labels, values)
    ax.set_ylabel("rows")
    ax.set_title("VLR.gg auto collection rows")
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    fig.savefig(reports_dir / "row_counts_by_table.png")
    plt.close(fig)


def write_worker_status_json(
    *,
    store: QueueStore,
    path: Path,
    run_id: str,
    stop_reason: str | None,
) -> dict[str, Any]:
    payload = {
        "run_id": run_id,
        "updated_at": utc_now(),
        "stop_reason": stop_reason,
        "queue": store.counts_by_source_status(),
        "results": store.result_counts(),
        "workers": store.worker_rows(),
    }
    write_json_atomic(path, payload)
    return payload


def write_overview(
    *,
    path: Path,
    run_id: str,
    args: argparse.Namespace,
    plan_sha256: str | None,
    queue_counts: dict[str, dict[str, int]],
    row_counts: dict[str, int],
    stop_reason: str | None,
    preflight: dict[str, Any],
) -> None:
    ensure_parent(path)
    lines = [
        f"# VLR.gg Auto Collection Overview",
        "",
        f"- run_id: `{run_id}`",
        f"- generated_at: `{utc_now()}`",
        f"- canonical_plan: `{args.plan_path}`",
        f"- canonical_plan_sha256: `{plan_sha256 or 'missing'}`",
        f"- state_dir: `{args.state_dir}`",
        f"- queue: `{Path(args.state_dir) / 'queue.sqlite'}`",
        f"- output: `{args.output}`",
        f"- reports: `{args.reports}`",
        f"- workers: `{args.workers}`",
        f"- sources: `{', '.join(args.sources)}`",
        f"- continuous: `{bool(args.continuous)}`",
        f"- stop_reason: `{stop_reason or 'none'}`",
        "",
        "## Preflight",
        "",
    ]
    for key, value in preflight.items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Queue", ""])
    for source, counts in sorted(queue_counts.items()):
        detail = ", ".join(f"{status}={count}" for status, count in sorted(counts.items()))
        lines.append(f"- {source}: {detail}")
    lines.extend(["", "## Row Counts", ""])
    for table, rows in sorted(row_counts.items()):
        lines.append(f"- {table}: {rows}")
    lines.extend(
        [
            "",
            "## Stop Conditions",
            "",
            "- Local API health failure stops before worker launch or during health checks.",
            "- VLR.gg robots/policy conflict stops before launch.",
            "- Rate-limit detection writes an internal stop marker and stops workers.",
            "- Repeated timeout/error retries use exponential backoff and stop after the configured failure threshold.",
            "- Creating `STOP` in the state directory requests graceful shutdown.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_reports(
    *,
    store: QueueStore,
    args: argparse.Namespace,
    plan_sha256: str | None,
    stop_reason: str | None,
    preflight: dict[str, Any],
) -> None:
    reports_dir = Path(args.reports)
    output_dir = Path(args.output)
    reports_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    row_counts = write_source_csvs(store, output_dir, list(args.sources))
    workers = store.worker_rows()
    write_row_counts_csv(reports_dir / "row_counts_by_table.csv", row_counts)
    write_worker_health_csv(reports_dir / "worker_health_summary.csv", workers)
    write_worker_status_json(
        store=store,
        path=Path(args.state_dir) / "worker_status.json",
        run_id=args.run_id,
        stop_reason=stop_reason,
    )
    write_json_atomic(
        reports_dir / "collection_summary.json",
        {
            "run_id": args.run_id,
            "generated_at": utc_now(),
            "stop_reason": stop_reason,
            "queue": store.counts_by_source_status(),
            "rows": row_counts,
            "workers": workers,
            "plan_sha256": plan_sha256,
        },
    )
    write_overview(
        path=reports_dir / "collection_overview.md",
        run_id=args.run_id,
        args=args,
        plan_sha256=plan_sha256,
        queue_counts=store.counts_by_source_status(),
        row_counts=row_counts,
        stop_reason=stop_reason,
        preflight=preflight,
    )
    write_optional_png(reports_dir, row_counts)


def health_log_event(
    *,
    store: QueueStore,
    args: argparse.Namespace,
    api_result: PreflightResult | None,
    stop_reason: str | None,
) -> dict[str, Any]:
    event = {
        "timestamp": utc_now(),
        "run_id": args.run_id,
        "api_health": api_result.ok if api_result is not None else None,
        "api_reason": api_result.reason if api_result is not None else None,
        "api_detail": api_result.detail if api_result is not None else {},
        "stop_reason": stop_reason,
        "queue": store.counts_by_source_status(),
        "results": store.result_counts(),
    }
    append_jsonl(Path(args.reports) / "health_checks.jsonl", event)
    return event


def process_is_alive(process: mp.Process) -> bool:
    return process.is_alive() and process.exitcode is None


def start_worker(
    *,
    config: dict[str, Any],
    worker_index: int,
    preferred_source: str | None,
) -> mp.Process:
    process = mp.Process(
        target=worker_main,
        args=(config, worker_index, preferred_source),
        name=f"vlrgg_auto_worker_{worker_index}",
    )
    process.start()
    return process


def run_workers(args: argparse.Namespace, store: QueueStore) -> str | None:
    config = vars(args).copy()
    preferred = preferred_sources_for_workers(list(args.sources), int(args.workers))
    processes: dict[int, mp.Process] = {
        index: start_worker(config=config, worker_index=index, preferred_source=preferred[index])
        for index in range(int(args.workers))
    }
    last_health_at = 0.0
    cycles = 0
    stop_reason: str | None = None
    try:
        while True:
            stop_reason = stop_reason_from_files(Path(args.state_dir))
            if stop_reason:
                break

            now = unix_now()
            if now - last_health_at >= float(args.health_interval_seconds):
                api_result = check_api_health(
                    args.api_base_url,
                    timeout_seconds=float(args.api_health_timeout_seconds),
                )
                health_log_event(store=store, args=args, api_result=api_result, stop_reason=None)
                write_worker_status_json(
                    store=store,
                    path=Path(args.state_dir) / "worker_status.json",
                    run_id=args.run_id,
                    stop_reason=None,
                )
                last_health_at = now
                if not api_result.ok:
                    write_internal_stop(Path(args.state_dir), "api_health_failed", api_result.detail)
                    stop_reason = "api_health_failed"
                    break

            if not store.has_active_jobs():
                cycles += 1
                write_reports(
                    store=store,
                    args=args,
                    plan_sha256=getattr(args, "plan_sha256", None),
                    stop_reason=None,
                    preflight=getattr(args, "preflight", {}),
                )
                if not args.continuous:
                    stop_reason = None
                    break
                if int(args.max_cycles) > 0 and cycles >= int(args.max_cycles):
                    stop_reason = "max_cycles_reached"
                    break
                inserted = seed_queue(args, store)
                if sum(inserted.values()) == 0:
                    time.sleep(float(args.empty_cycle_sleep_seconds))
                else:
                    cycles = 0

            for index, process in list(processes.items()):
                if process.exitcode is not None and stop_reason_from_files(Path(args.state_dir)) is None:
                    if args.continuous or store.has_active_jobs():
                        processes[index] = start_worker(
                            config=config,
                            worker_index=index,
                            preferred_source=preferred[index],
                        )
            time.sleep(float(args.coordinator_tick_seconds))
    finally:
        for process in processes.values():
            process.join(timeout=float(args.worker_shutdown_grace_seconds))
        for process in processes.values():
            if process_is_alive(process):
                process.terminate()
        for process in processes.values():
            process.join(timeout=2)
    return stop_reason


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run VLR.gg auto collection with local SQLite-claimed workers.")
    parser.add_argument("--run-id", default=f"auto_{datetime.now().strftime('%Y%m%d_%H%M')}")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--api-base-url", default=DEFAULT_API_BASE_URL)
    parser.add_argument("--sources", nargs="+", choices=DEFAULT_SOURCES, default=list(DEFAULT_SOURCES))
    parser.add_argument("--continuous", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Seed queue and write reports without API/robots preflight or workers.")
    parser.add_argument("--skip-robots-check", action="store_true", help="Skip robots preflight for local dry verification only.")
    parser.add_argument("--health-interval-seconds", type=float, default=180.0)
    parser.add_argument("--global-min-request-interval-seconds", type=float, default=2.0)
    parser.add_argument("--per-worker-min-request-interval-seconds", type=float, default=4.0)
    parser.add_argument("--empty-cycle-sleep-seconds", type=float, default=600.0)
    parser.add_argument("--worker-idle-sleep-seconds", type=float, default=5.0)
    parser.add_argument("--coordinator-tick-seconds", type=float, default=2.0)
    parser.add_argument("--worker-shutdown-grace-seconds", type=float, default=10.0)
    parser.add_argument("--claim-stale-after-seconds", type=float, default=1800.0)
    parser.add_argument("--max-attempts", type=int, default=5)
    parser.add_argument("--retry-backoff-seconds", type=float, default=60.0)
    parser.add_argument("--max-retry-backoff-seconds", type=float, default=3600.0)
    parser.add_argument("--max-consecutive-worker-failures", type=int, default=3)
    parser.add_argument("--max-jobs-per-worker", type=int, default=0)
    parser.add_argument("--max-cycles", type=int, default=0)
    parser.add_argument("--api-health-timeout-seconds", type=float, default=5.0)
    parser.add_argument("--max-seed-jobs-per-source", type=int, default=0)
    parser.add_argument("--output", default="")
    parser.add_argument("--reports", default="")
    parser.add_argument("--state-dir", default="")
    parser.add_argument("--plan-path", default=str(CANONICAL_PLAN_PATH))
    parser.add_argument("--match-candidates-file", default="data/processed/vlrgg_match_candidates.csv")
    parser.add_argument("--event-candidates-file", default="data/processed/vlrgg_event_candidates.csv")
    parser.add_argument("--team-candidates-file", default="data/processed/vlrgg_team_candidates.csv")
    parser.add_argument("--player-candidates-file", default="data/processed/vlrgg_player_candidates.csv")
    parser.add_argument(
        "--report-file",
        action="append",
        default=None,
        help="Existing summary JSON used for queue seeding. Can be repeated.",
    )
    return parser


def normalize_args(args: argparse.Namespace) -> argparse.Namespace:
    if int(args.workers) < 1:
        raise ValueError("--workers must be >= 1")
    args.sources = ordered_sources(list(args.sources))
    if args.report_file is None:
        args.report_file = ["reports/vlrgg_collection_backfill_summary.json"]
    if not args.output:
        args.output = f"data/processed/vlrgg_auto/{args.run_id}"
    if not args.reports:
        args.reports = f"reports/vlrgg_auto/{args.run_id}"
    if not args.state_dir:
        args.state_dir = f".omx/state/vlrgg_auto/{args.run_id}"
    return args


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = normalize_args(parser.parse_args(argv))
    state_dir = Path(args.state_dir)
    reports_dir = Path(args.reports)
    output_dir = Path(args.output)
    state_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    store = QueueStore(state_dir / "queue.sqlite")

    plan_path = Path(args.plan_path)
    plan_sha = sha256_file(plan_path) if plan_path.exists() else None
    args.plan_sha256 = plan_sha
    store.set_metadata(
        "run",
        {
            "run_id": args.run_id,
            "created_at": utc_now(),
            "plan_path": args.plan_path,
            "plan_sha256": plan_sha,
            "output": args.output,
            "reports": args.reports,
            "state_dir": args.state_dir,
        },
    )

    inserted = seed_queue(args, store)
    preflight: dict[str, Any] = {
        "plan_sha256": plan_sha or "missing",
        "seeded": inserted,
        "dry_run": bool(args.dry_run),
    }
    args.preflight = preflight

    if args.dry_run:
        health_log_event(store=store, args=args, api_result=None, stop_reason="dry_run")
        write_reports(
            store=store,
            args=args,
            plan_sha256=plan_sha,
            stop_reason="dry_run",
            preflight=preflight,
        )
        return 0

    api_result = check_api_health(
        args.api_base_url,
        timeout_seconds=float(args.api_health_timeout_seconds),
    )
    preflight["api_health"] = api_result.reason
    health_log_event(store=store, args=args, api_result=api_result, stop_reason=None)
    if not api_result.ok:
        write_reports(
            store=store,
            args=args,
            plan_sha256=plan_sha,
            stop_reason=api_result.reason,
            preflight=preflight,
        )
        return 2

    if args.skip_robots_check:
        preflight["robots"] = "skipped"
    else:
        robots_result = check_robots_policy(timeout_seconds=15)
        preflight["robots"] = robots_result.reason
        if not robots_result.ok:
            health_log_event(store=store, args=args, api_result=None, stop_reason=robots_result.reason)
            write_reports(
                store=store,
                args=args,
                plan_sha256=plan_sha,
                stop_reason=robots_result.reason,
                preflight=preflight,
            )
            return 3

    stop_reason = run_workers(args, store)
    health_log_event(store=store, args=args, api_result=None, stop_reason=stop_reason)
    write_reports(
        store=store,
        args=args,
        plan_sha256=plan_sha,
        stop_reason=stop_reason,
        preflight=preflight,
    )
    return 0 if stop_reason in (None, "max_cycles_reached", "user_stop_file") else 4


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
