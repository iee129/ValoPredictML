from __future__ import annotations

import argparse
import csv
import fcntl
import json
import multiprocessing as mp
from pathlib import Path
import sqlite3
import sys
import time
from datetime import datetime, timezone
from typing import Any

import requests


DEFAULT_API_BASE = "http://127.0.0.1:3001"
DEFAULT_DB = ".omx/state/vlrgg_worker.db"
DEFAULT_OUTPUT = "data/raw/vlrgg"
DEFAULT_WORKERS = 4
DEFAULT_INTERVAL = 2.0
DETAILS_RELPATH = "match/details.csv"
CSV_FIELDS = [
    "match_id", "event", "date", "status",
    "teams_json", "maps_json", "raw_json",
    "source", "source_url", "retrieval_method",
    "fetched_at", "cache_hit", "parser_version", "source_hash",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = _connect(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            match_id TEXT PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'pending',
            claimed_by TEXT,
            claimed_at REAL,
            done_at TEXT,
            error TEXT,
            retries INTEGER NOT NULL DEFAULT 0
        );
    """)
    try:
        conn.execute("ALTER TABLE jobs ADD COLUMN retries INTEGER NOT NULL DEFAULT 0")
        conn.commit()
    except Exception:
        pass
    conn.close()


def _ids_from_csv(csv_path: Path) -> set[str]:
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return set()
    ids: set[str] = set()
    with csv_path.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            mid = (row.get("match_id") or "").strip()
            if mid:
                ids.add(mid)
    return ids


def seed(
    db_path: Path,
    candidates_path: Path,
    output_dir: Path,
    skip_csvs: list[Path],
) -> tuple[int, int]:
    done: set[str] = _ids_from_csv(output_dir / DETAILS_RELPATH)
    for p in skip_csvs:
        done |= _ids_from_csv(p)

    to_insert: list[str] = []
    skipped = 0
    with candidates_path.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            mid = (row.get("match_id") or row.get("candidate_id") or "").strip()
            if not mid:
                continue
            if mid in done or (row.get("status") or "").strip() == "detail_complete":
                skipped += 1
                continue
            to_insert.append(mid)

    conn = _connect(db_path)
    inserted = 0
    for mid in to_insert:
        cur = conn.execute("INSERT OR IGNORE INTO jobs(match_id) VALUES(?)", (mid,))
        inserted += cur.rowcount
    conn.commit()
    conn.close()
    return inserted, skipped


def claim_job(db_path: Path, worker_id: str) -> str | None:
    conn = _connect(db_path)
    try:
        conn.execute("BEGIN EXCLUSIVE")
        row = conn.execute(
            "SELECT match_id FROM jobs WHERE status='pending' ORDER BY rowid LIMIT 1"
        ).fetchone()
        if row is None:
            conn.execute("ROLLBACK")
            return None
        mid = row["match_id"]
        conn.execute(
            "UPDATE jobs SET status='claimed', claimed_by=?, claimed_at=? WHERE match_id=?",
            (worker_id, time.time(), mid),
        )
        conn.execute("COMMIT")
        return mid
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()


def mark_status(db_path: Path, match_id: str, status: str, error: str = "") -> None:
    conn = _connect(db_path)
    conn.execute(
        "UPDATE jobs SET status=?, done_at=?, error=? WHERE match_id=?",
        (status, utc_now(), error[:500], match_id),
    )
    conn.commit()
    conn.close()


def mark_retry_or_no_data(db_path: Path, match_id: str, error: str, max_retries: int = 5) -> None:
    conn = _connect(db_path)
    row = conn.execute("SELECT retries FROM jobs WHERE match_id=?", (match_id,)).fetchone()
    retries = (row["retries"] if row else 0) + 1
    if retries >= max_retries:
        conn.execute(
            "UPDATE jobs SET status='no_data', done_at=?, error=?, retries=? WHERE match_id=?",
            (utc_now(), error[:500], retries, match_id),
        )
    else:
        conn.execute(
            "UPDATE jobs SET status='pending', claimed_by=NULL, claimed_at=NULL, retries=?, error=? WHERE match_id=?",
            (retries, error[:500], match_id),
        )
    conn.commit()
    conn.close()


def mark_retry_or_failed(db_path: Path, match_id: str, error: str, max_retries: int = 5) -> None:
    conn = _connect(db_path)
    row = conn.execute("SELECT retries FROM jobs WHERE match_id=?", (match_id,)).fetchone()
    retries = (row["retries"] if row else 0) + 1
    if retries >= max_retries:
        conn.execute(
            "UPDATE jobs SET status='failed', done_at=?, error=?, retries=? WHERE match_id=?",
            (utc_now(), error[:500], retries, match_id),
        )
    else:
        conn.execute(
            "UPDATE jobs SET status='pending', claimed_by=NULL, claimed_at=NULL, retries=?, error=? WHERE match_id=?",
            (retries, error[:500], match_id),
        )
    conn.commit()
    conn.close()


def reset_claimed(db_path: Path) -> int:
    conn = _connect(db_path)
    cur = conn.execute(
        "UPDATE jobs SET status='pending', claimed_by=NULL, claimed_at=NULL WHERE status='claimed'"
    )
    n = cur.rowcount
    conn.commit()
    conn.close()
    return n


def reset_failed(db_path: Path) -> int:
    conn = _connect(db_path)
    cur = conn.execute(
        "UPDATE jobs SET status='pending', claimed_by=NULL, claimed_at=NULL, error=NULL WHERE status='failed'"
    )
    n = cur.rowcount
    conn.commit()
    conn.close()
    return n


def status_counts(db_path: Path) -> dict[str, int]:
    conn = _connect(db_path)
    rows = conn.execute("SELECT status, COUNT(*) AS n FROM jobs GROUP BY status").fetchall()
    conn.close()
    return {r["status"]: r["n"] for r in rows}


def ensure_csv_header(csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        with csv_path.open("w", encoding="utf-8", newline="") as f:
            csv.DictWriter(f, fieldnames=CSV_FIELDS).writeheader()


def append_csv_row(csv_path: Path, row: dict[str, str]) -> None:
    with csv_path.open("a", encoding="utf-8", newline="") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            csv.DictWriter(f, fieldnames=CSV_FIELDS).writerow(row)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def _parse_event(event_field: Any) -> str:
    if isinstance(event_field, dict):
        return str(event_field.get("name") or event_field.get("id") or "")
    return str(event_field or "")


def _has_scores(maps: list[Any]) -> bool:
    for m in maps:
        if not isinstance(m, dict):
            continue
        score = m.get("score") or {}
        if isinstance(score, dict):
            if int(score.get("team1") or 0) + int(score.get("team2") or 0) > 0:
                return True
    return False


def fetch_segment(api_base: str, match_id: str) -> dict[str, Any]:
    url = f"{api_base.rstrip('/')}/v2/match/details"
    resp = requests.get(url, params={"match_id": match_id}, timeout=10.0)
    resp.raise_for_status()
    return resp.json()["data"]["segments"][0]


def worker_loop(
    db_path: str,
    csv_path: str,
    api_base: str,
    interval: float,
    worker_idx: int,
) -> None:
    db = Path(db_path)
    csv_p = Path(csv_path)
    wid = f"w{worker_idx}"
    backoff = float(interval)

    while True:
        mid = claim_job(db, wid)
        if mid is None:
            return

        time.sleep(backoff)

        try:
            seg = fetch_segment(api_base, mid)
            maps = seg.get("maps") or []
            teams = seg.get("teams") or []

            if not _has_scores(maps):
                mark_status(db, mid, "no_data")
                backoff = max(float(interval), backoff * 0.9)
                continue

            append_csv_row(csv_p, {
                "match_id": mid,
                "event": _parse_event(seg.get("event")),
                "date": str(seg.get("date") or ""),
                "status": str(seg.get("status") or ""),
                "teams_json": json.dumps(teams, ensure_ascii=False),
                "maps_json": json.dumps(maps, ensure_ascii=False),
                "raw_json": json.dumps(seg, ensure_ascii=False),
                "source": "vlrgg_api_detail",
                "source_url": f"https://www.vlr.gg/{mid}",
                "retrieval_method": "api_match_detail",
                "fetched_at": utc_now(),
                "cache_hit": "False",
                "parser_version": "worker_v2",
                "source_hash": "",
            })
            mark_status(db, mid, "done")
            backoff = max(float(interval), backoff * 0.9)

        except requests.exceptions.HTTPError as exc:
            code = exc.response.status_code if exc.response is not None else 0
            if code == 404:
                mark_status(db, mid, "no_data", f"HTTP {code}")
                backoff = max(float(interval), backoff * 0.9)
            elif code in (502, 503):
                mark_retry_or_no_data(db, mid, f"HTTP {code}")
                backoff = min(backoff * 1.5, 30.0)
            else:
                mark_status(db, mid, "failed", f"HTTP {code}: {exc}"[:200])
                backoff = min(backoff * 1.5, 30.0)

        except requests.exceptions.Timeout:
            mark_retry_or_failed(db, mid, "timeout")
            backoff = min(backoff * 1.5, 30.0)

        except Exception as exc:
            mark_status(db, mid, "failed", f"{type(exc).__name__}: {exc}"[:200])
            backoff = min(backoff * 1.5, 30.0)


def _print_status(db_path: Path) -> None:
    c = status_counts(db_path)
    total = sum(c.values())
    print(
        f"total={total} pending={c.get('pending', 0)} claimed={c.get('claimed', 0)} "
        f"done={c.get('done', 0)} no_data={c.get('no_data', 0)} failed={c.get('failed', 0)}"
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="VLR.gg match detail parallel worker")
    p.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    p.add_argument("--interval", type=float, default=DEFAULT_INTERVAL,
                   help="seconds between requests per worker (default: 2.0)")
    p.add_argument("--api-base", default=DEFAULT_API_BASE)
    p.add_argument("--output", default=DEFAULT_OUTPUT)
    p.add_argument("--db", default=DEFAULT_DB)
    p.add_argument("--candidates", default="data/processed/vlrgg/vlrgg_match_candidates.csv")
    p.add_argument("--skip-csv", action="append", default=None,
                   help="additional CSV with match_id column to treat as already done")
    p.add_argument("--reset", action="store_true",
                   help="reset stuck claimed jobs back to pending before running")
    p.add_argument("--reset-failed", action="store_true",
                   help="reset failed jobs back to pending before running")
    p.add_argument("--status", action="store_true",
                   help="print queue status and exit")
    p.add_argument("--seed-only", action="store_true",
                   help="seed queue and exit without running workers")
    args = p.parse_args(argv)

    db_path = Path(args.db)
    output_dir = Path(args.output)
    csv_path = output_dir / DETAILS_RELPATH

    init_db(db_path)

    if args.reset:
        n = reset_claimed(db_path)
        print(f"reset {n} claimed → pending")

    if args.reset_failed:
        n = reset_failed(db_path)
        print(f"reset {n} failed → pending")

    if args.status:
        _print_status(db_path)
        return 0

    skip_csvs: list[Path] = [Path(s) for s in (args.skip_csv or [])]

    inserted, skipped = seed(db_path, Path(args.candidates), output_dir, skip_csvs)
    print(f"seed: inserted={inserted} already_done={skipped}")
    _print_status(db_path)

    if args.seed_only:
        return 0

    if status_counts(db_path).get("pending", 0) == 0:
        print("no pending jobs")
        return 0

    ensure_csv_header(csv_path)
    print(f"output: {csv_path}")
    print(f"starting {args.workers} workers, interval={args.interval}s")

    procs = [
        mp.Process(
            target=worker_loop,
            args=(str(db_path), str(csv_path), args.api_base, args.interval, i),
            name=f"vlrgg_worker_{i}",
            daemon=True,
        )
        for i in range(args.workers)
    ]
    for proc in procs:
        proc.start()

    try:
        while any(proc.is_alive() for proc in procs):
            time.sleep(15)
            _print_status(db_path)
    except KeyboardInterrupt:
        print("\ninterrupted — workers will finish current job then stop")

    for proc in procs:
        proc.join(timeout=30)
        if proc.is_alive():
            proc.terminate()

    print("done")
    _print_status(db_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
