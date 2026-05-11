from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from ml.vlrgg_worker_auto_collect import (
    QueueStore,
    main,
    preferred_sources_for_workers,
    source_order_for_worker,
)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class VLRGGAutoCollectTests(unittest.TestCase):
    def test_sqlite_claim_allows_only_one_worker_per_job(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = QueueStore(Path(tmp) / "queue.sqlite")
            inserted = store.upsert_job("match_details", "101", {"match_id": "101"})
            duplicate_inserted = store.upsert_job("match_details", "101", {"match_id": "101"})

            first = store.claim_job(
                worker_id="worker_0",
                source_order=["match_details"],
                stale_after_seconds=60,
            )
            second = store.claim_job(
                worker_id="worker_1",
                source_order=["match_details"],
                stale_after_seconds=60,
            )

            self.assertTrue(inserted)
            self.assertFalse(duplicate_inserted)
            self.assertIsNotNone(first)
            self.assertIsNone(second)
            self.assertEqual(store.counts_by_source_status()["match_details"]["in_progress"], 1)

    def test_retry_backoff_prevents_immediate_reclaim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = QueueStore(Path(tmp) / "queue.sqlite")
            store.upsert_job("events", "201", {"event_id": "201"})
            job = store.claim_job(
                worker_id="worker_0",
                source_order=["events"],
                stale_after_seconds=60,
            )

            assert job is not None
            status = store.fail_job(
                job=job,
                worker_id="worker_0",
                error="timeout",
                max_attempts=5,
                retry_backoff_seconds=100,
                max_retry_backoff_seconds=100,
            )
            reclaimed = store.claim_job(
                worker_id="worker_1",
                source_order=["events"],
                stale_after_seconds=60,
            )

            self.assertEqual(status, "retry")
            self.assertIsNone(reclaimed)
            self.assertEqual(store.counts_by_source_status()["events"]["retry"], 1)

    def test_worker_assignment_prefers_sources_then_largest_backlog(self) -> None:
        preferred = preferred_sources_for_workers(["match_details", "events", "teams"], 4)
        order = source_order_for_worker(
            sources=["match_details", "events", "teams"],
            preferred_source=None,
            backlog={"match_details": 1, "events": 2, "teams": 8},
        )

        self.assertEqual(preferred, ["match_details", "events", "teams", None])
        self.assertEqual(order[0], "teams")
        self.assertEqual(set(order), {"match_details", "events", "teams"})

    def test_dry_run_seeds_queue_and_writes_reports_without_workers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            match_csv = root / "vlrgg_match_candidates.csv"
            event_csv = root / "vlrgg_event_candidates.csv"
            plan = root / "vlrgg_worker_auto_collection.md"
            plan.write_text("# plan\n", encoding="utf-8")
            write_csv(
                match_csv,
                ["candidate_type", "candidate_id", "match_id"],
                [
                    {"candidate_type": "match", "candidate_id": "101", "match_id": "101"},
                    {"candidate_type": "match", "candidate_id": "102", "match_id": "102"},
                    {"candidate_type": "event", "candidate_id": "999", "match_id": ""},
                ],
            )
            write_csv(
                event_csv,
                ["candidate_id", "event_id"],
                [{"candidate_id": "201", "event_id": "201"}],
            )

            exit_code = main(
                [
                    "--run-id",
                    "test_auto",
                    "--dry-run",
                    "--sources",
                    "match_details",
                    "events",
                    "--match-candidates-file",
                    str(match_csv),
                    "--event-candidates-file",
                    str(event_csv),
                    "--report-file",
                    str(root / "missing_report.json"),
                    "--output",
                    str(root / "out"),
                    "--reports",
                    str(root / "reports"),
                    "--state-dir",
                    str(root / "state"),
                    "--plan-path",
                    str(plan),
                ]
            )

            summary = json.loads((root / "reports" / "collection_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(exit_code, 0)
            self.assertEqual(summary["stop_reason"], "dry_run")
            self.assertEqual(summary["queue"]["match_details"]["pending"], 2)
            self.assertEqual(summary["queue"]["events"]["pending"], 1)
            self.assertTrue((root / "state" / "queue.sqlite").exists())
            self.assertTrue((root / "reports" / "collection_overview.md").exists())

    def test_local_api_down_exits_before_worker_launch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            match_csv = root / "vlrgg_match_candidates.csv"
            plan = root / "vlrgg_worker_auto_collection.md"
            plan.write_text("# plan\n", encoding="utf-8")
            write_csv(
                match_csv,
                ["candidate_type", "candidate_id", "match_id"],
                [{"candidate_type": "match", "candidate_id": "101", "match_id": "101"}],
            )

            exit_code = main(
                [
                    "--run-id",
                    "api_down",
                    "--sources",
                    "match_details",
                    "--match-candidates-file",
                    str(match_csv),
                    "--report-file",
                    str(root / "missing_report.json"),
                    "--output",
                    str(root / "out"),
                    "--reports",
                    str(root / "reports"),
                    "--state-dir",
                    str(root / "state"),
                    "--plan-path",
                    str(plan),
                    "--api-base-url",
                    "http://127.0.0.1:1",
                    "--api-health-timeout-seconds",
                    "0.05",
                    "--skip-robots-check",
                ]
            )

            summary = json.loads((root / "reports" / "collection_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(exit_code, 2)
            self.assertEqual(summary["stop_reason"], "api_health_failed")
            self.assertEqual(summary["workers"], [])


if __name__ == "__main__":
    unittest.main()
