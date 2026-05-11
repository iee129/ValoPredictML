from __future__ import annotations

import json
import tempfile
import unittest
from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from bs4 import BeautifulSoup

from ml.collect_local_research import build_outputs
from ml.collect_vlrgg import (
    EVENT_AGENT_USAGE_COLUMNS,
    EVENT_DETAIL_COLUMNS,
    EVENT_PLAYER_STATS_COLUMNS,
    PLAYER_AGENT_USAGE_COLUMNS,
    PLAYER_PROFILE_COLUMNS,
    PLAYER_RECENT_MATCH_COLUMNS,
    PROVENANCE_FIELDS,
    CollectionStageError,
    CollectionState,
    apply_backfill_shard_isolation,
    _guard_duplicate_overlap,
    _load_stage_output_ids,
    _run_stage_with_resume,
    _require_match_detail_rows,
    _read_stage_frames,
    _event_detail_frames_from_api,
    _api_match_request_windows,
    _candidate_ids_for_backfill,
    _merge_source_output_dirs,
    _stable_backfill_shard,
    _vlrgg_upstream_slot,
    build_match_candidates,
    build_api_match_detail_artifacts,
    build_match_detail_frames,
    build_vlrgg_pipeline_matches,
    expand_player_profiles_to_stage,
    fetch_api_match_to_cache,
    fetch_api_match_detail_to_stage,
    load_api_cache,
    run_backfill_plan,
    run_merge_shard_outputs,
    validate_provenance,
    write_expanded_outputs,
    write_player_profile_outputs,
)
from ml.data_pipeline import parse_vlrgg_pipeline_matches
from ml.research_validation import REQUIRED_FACT_FIELDS, build_report_facts
from ml.vlrgg_rate_limit import VLRGGRateLimitError, parse_retry_after_seconds
from ml.vlrgg_client import VLRGGClient
from ml.vlrgg_scraper import (
    DIRECT_HTML_ALLOWED_PATH_PREFIXES,
    assert_vlrgg_path_allowed,
    scrape_event_agent_usage,
    scrape_event_player_stats,
)


class VLRGGOfflineTests(unittest.TestCase):
    def test_v2_cache_only_stats_uses_no_network(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            (cache / "_stats_region_na_timespan_30.json").write_text(
                json.dumps({
                    "data": {
                        "status": 200,
                        "segments": [{
                            "player": "p1",
                            "org": "ORG",
                            "agents": ["jett"],
                            "rounds_played": "10",
                        }],
                    }
                }),
                encoding="utf-8",
            )
            client = VLRGGClient(cache_dir=str(cache), cache_only=True)
            rows = client.fetch_stats("na", "30")
            self.assertEqual(rows[0]["player"], "p1")
            self.assertTrue(client.last_cache_hit)
            self.assertEqual(client.request_count, 0)

    def test_v2_cache_file_parses_through_loader(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            (cache / "_v2_stats_region_kr_timespan_all.json").write_text(
                json.dumps({
                    "status": "success",
                    "data": {
                        "status": 200,
                        "segments": [{
                            "player": "p2",
                            "org": "ORG",
                            "agents": ["sova"],
                            "rounds_played": "12",
                            "rating": "1.10",
                        }],
                    },
                }),
                encoding="utf-8",
            )
            _, players = load_api_cache(cache, "http://127.0.0.1:3001", "2026-05-10T00:00:00Z")
            self.assertEqual(len(players), 1)
            self.assertEqual(players.iloc[0]["region"], "kr")
            self.assertEqual(players.iloc[0]["retrieval_method"], "api_cache")

    def test_v2_event_matches_cache_uses_no_network(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            (cache / "_v2_events_matches_event_id_2095.json").write_text(
                json.dumps({
                    "status": "success",
                    "data": {
                        "matches": [{
                            "match_id": "595657",
                            "teams": [{"name": "A"}, {"name": "B"}],
                        }]
                    },
                }),
                encoding="utf-8",
            )
            client = VLRGGClient(cache_dir=str(cache), cache_only=True)
            rows = client.fetch_event_matches("2095")
            self.assertEqual(rows[0]["match_id"], "595657")
            self.assertEqual(client.request_count, 0)

    def test_v2_deep_endpoint_wrappers_use_cache_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            fixtures = {
                "_v2_match_details_match_id_595657.json": {"status": "success", "data": {"match_id": "595657", "maps": []}},
                "_v2_event_2124.json": {"status": "success", "data": {"segments": {"event": {"name": "Event A"}}}},
                "_v2_player_id_9_timespan_all.json": {"status": "success", "data": {"info": {"name": "TenZ"}}},
                "_v2_player_matches_id_9_page_1.json": {"status": "success", "data": {"matches": [{"match_id": "1"}]}},
                "_v2_team_id_2.json": {"status": "success", "data": {"info": {"name": "Sentinels"}}},
                "_v2_team_matches_id_2_page_1.json": {"status": "success", "data": {"matches": [{"match_id": "2"}]}},
                "_v2_team_transactions_id_2.json": {"status": "success", "data": {"transactions": [{"player": "p1"}]}},
            }
            for filename, payload in fixtures.items():
                (cache / filename).write_text(json.dumps(payload), encoding="utf-8")

            client = VLRGGClient(cache_dir=str(cache), cache_only=True)

            self.assertEqual(client.fetch_match_details("595657")["match_id"], "595657")
            self.assertEqual(client.fetch_event_detail("2124")["event"]["name"], "Event A")
            self.assertEqual(client.fetch_player("9", timespan="all")["info"]["name"], "TenZ")
            self.assertEqual(client.fetch_player_matches("9")[0]["match_id"], "1")
            self.assertEqual(client.fetch_team("2")["info"]["name"], "Sentinels")
            self.assertEqual(client.fetch_team_matches("2")[0]["match_id"], "2")
            self.assertEqual(client.fetch_team_transactions("2")[0]["player"], "p1")
            self.assertEqual(client.request_count, 0)

    def test_v2_match_details_status_segments_wrapper_uses_first_segment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            (cache / "_v2_match_details_match_id_595657.json").write_text(
                json.dumps({
                    "status": "success",
                    "data": {
                        "status": 200,
                        "segments": [{
                            "match_id": "595657",
                            "teams": [{"name": "A"}, {"name": "B"}],
                            "maps": [{"map_name": "Haven", "players": {"team1": [], "team2": []}}],
                        }],
                    },
                }),
                encoding="utf-8",
            )
            client = VLRGGClient(cache_dir=str(cache), cache_only=True)

            detail = client.fetch_match_details("595657")

            self.assertIsNotNone(detail)
            self.assertEqual(detail["match_id"], "595657")
            self.assertIn("maps", detail)
            self.assertEqual(client.request_count, 0)

    def test_v2_match_listing_supports_page_range_cache_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            (cache / "_v2_match_from_page_2_num_pages_3_q_results_to_page_4.json").write_text(
                json.dumps({
                    "status": "success",
                    "data": {"segments": [{"match_page": "/111/a-vs-b"}]},
                }),
                encoding="utf-8",
            )
            client = VLRGGClient(cache_dir=str(cache), cache_only=True)
            rows = client.fetch_match("results", num_pages=3, from_page=2, to_page=4)
            self.assertEqual(rows[0]["match_page"], "/111/a-vs-b")
            self.assertEqual(client.request_count, 0)

    def test_api_match_request_windows_split_at_api_limit(self) -> None:
        args = Namespace(api_from_page=0, api_to_page=0, api_match_window_size=20)

        windows = _api_match_request_windows(args, "results", 45)

        self.assertEqual(windows, [
            {"q": "results", "num_pages": 20, "from_page": 1, "to_page": 20},
            {"q": "results", "num_pages": 20, "from_page": 21, "to_page": 40},
            {"q": "results", "num_pages": 5, "from_page": 41, "to_page": 45},
        ])
        self.assertEqual(_api_match_request_windows(args, "live_score", 45), [{"q": "live_score", "num_pages": 1}])

    def test_api_match_cache_fetch_splits_large_page_requests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            fixtures = {
                "_v2_match_from_page_1_num_pages_20_q_results_to_page_20.json": "/101/a-vs-b",
                "_v2_match_from_page_21_num_pages_20_q_results_to_page_40.json": "/102/c-vs-d",
                "_v2_match_from_page_41_num_pages_5_q_results_to_page_45.json": "/103/e-vs-f",
            }
            for filename, match_page in fixtures.items():
                (cache / filename).write_text(
                    json.dumps({"status": "success", "data": {"segments": [{"match_page": match_page}]}}),
                    encoding="utf-8",
                )
            args = Namespace(
                rate_limit=1.0,
                cache_dir=cache,
                api_base_url="http://127.0.0.1:3001",
                api_from_page=0,
                api_to_page=0,
                api_match_window_size=20,
            )

            result = fetch_api_match_to_cache(args, "results", 45)

            self.assertEqual(result["rows"], 3)
            self.assertEqual(result["network_requests"], 0)
            self.assertEqual(len(result["windows"]), 3)

    def test_api_match_cache_extracts_match_id_from_match_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            (cache / "_v2_match_num_pages_1_q_results.json").write_text(
                json.dumps({
                    "status": "success",
                    "data": {
                        "status": 200,
                        "segments": [{
                            "team1": "Alpha",
                            "team2": "Beta",
                            "score1": "2",
                            "score2": "1",
                            "match_page": "/314642/alpha-vs-beta-test-event",
                            "tournament_name": "Test Event",
                        }],
                    },
                }),
                encoding="utf-8",
            )
            matches, _ = load_api_cache(cache, "http://127.0.0.1:3001", "2026-05-10T00:00:00Z")
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches.iloc[0]["match_id"], "314642")
            self.assertEqual(matches.iloc[0]["label"], 1)

    def test_missing_provenance_fails(self) -> None:
        df = pd.DataFrame([{"source": "vlrgg"}])
        with self.assertRaises(ValueError):
            validate_provenance(df, "bad")

    def test_complete_provenance_passes(self) -> None:
        df = pd.DataFrame([{field: "x" for field in PROVENANCE_FIELDS}])
        df["cache_hit"] = True
        validate_provenance(df, "good")

    def test_disallowed_direct_paths_blocked(self) -> None:
        for path in ["/search/auto?q=x", "https://www.vlr.gg/rr/test"]:
            with self.assertRaises(ValueError):
                assert_vlrgg_path_allowed(path)
        assert_vlrgg_path_allowed("https://www.vlr.gg/matches/results?page=1")
        assert_vlrgg_path_allowed("https://www.vlr.gg/event/stats/2489/?series_id=all", allowed_prefixes=DIRECT_HTML_ALLOWED_PATH_PREFIXES)
        assert_vlrgg_path_allowed("https://www.vlr.gg/event/agents/2489/?series_id=all", allowed_prefixes=DIRECT_HTML_ALLOWED_PATH_PREFIXES)
        with self.assertRaises(ValueError):
            assert_vlrgg_path_allowed("/stats", allowed_prefixes=DIRECT_HTML_ALLOWED_PATH_PREFIXES)

    def test_event_player_stats_parser_reads_static_table(self) -> None:
        html = """
        <table>
          <thead><tr>
            <th>Player</th><th>Agents</th><th>Rnd</th><th>R2.0</th><th>ACS</th>
            <th>K:D</th><th>KAST</th><th>ADR</th><th>KPR</th><th>APR</th>
            <th>FKPR</th><th>FDPR</th><th>HS%</th><th>CL%</th>
          </tr></thead>
          <tbody><tr>
            <td><a href="/player/9/test-player">test player</a> TST</td>
            <td><img alt="Jett" src="/img/vlr/game/agents/jett.png"></td>
            <td>54</td><td>1.20</td><td>240.5</td><td>1.30</td><td>77%</td>
            <td>152.0</td><td>0.82</td><td>0.30</td><td>0.11</td><td>0.08</td>
            <td>28%</td><td>19%</td>
          </tr></tbody>
        </table>
        """
        with patch("ml.vlrgg_scraper._get", return_value=BeautifulSoup(html, "html.parser")):
            rows = scrape_event_player_stats("2489", delay=0)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["player"], "test player")
        self.assertEqual(rows[0]["team"], "TST")
        self.assertEqual(rows[0]["agent"], "Jett")
        self.assertEqual(rows[0]["rounds_played"], 54)

    def test_event_agent_usage_parser_reads_static_table(self) -> None:
        html = """
        <table>
          <thead><tr>
            <th>Map</th><th>#</th><th>ATK WIN</th><th>DEF WIN</th>
            <th><img alt="Jett" src="/img/vlr/game/agents/jett.png"></th>
            <th><img alt="Sova" src="/img/vlr/game/agents/sova.png"></th>
          </tr></thead>
          <tbody><tr>
            <td>A Ascent</td><td>10</td><td>52%</td><td>48%</td>
            <td>7 (70%)</td><td>3 (30%)</td>
          </tr></tbody>
        </table>
        """
        with patch("ml.vlrgg_scraper._get", return_value=BeautifulSoup(html, "html.parser")):
            rows = scrape_event_agent_usage("2489", delay=0)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["map"], "Ascent")
        self.assertEqual(rows[0]["agent"], "Jett")
        self.assertEqual(rows[0]["use_count"], 7)
        self.assertEqual(rows[0]["use_rate"], 70.0)

    def test_retry_after_parsing_supports_seconds_and_http_dates(self) -> None:
        now = datetime(2026, 5, 10, 3, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(parse_retry_after_seconds("12", now=now), 12.0)
        self.assertEqual(
            parse_retry_after_seconds("Sun, 10 May 2026 03:00:30 GMT", now=now),
            30.0,
        )
        self.assertIsNone(parse_retry_after_seconds("not-a-date", now=now))

    def test_stage_rate_limit_degrades_after_three_retries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = CollectionState(Path(tmp) / "vlrgg_state.json", reset=True)
            args = Namespace(
                restart=False,
                max_rate_limit_wait_seconds=0,
                retry_backoff_seconds=0,
            )

            def always_limited() -> dict:
                raise VLRGGRateLimitError(
                    "limited",
                    url="https://www.vlr.gg/matches/results",
                    status_code=429,
                    retry_after="1",
                )

            result = _run_stage_with_resume(
                args=args,
                state=state,
                name="direct_html_page_1",
                cursor={"path": "/matches/results", "page": 1},
                fn=always_limited,
            )

            self.assertEqual(result["status"], "degraded")
            self.assertEqual(state.stage("direct_html_page_1")["attempts"], 3)
            self.assertEqual(len(state.data["rate_limit_events"]), 3)

    def test_upstream_slot_writes_shared_lock_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "vlrgg_upstream.lock"
            args = Namespace(
                disable_upstream_lock=False,
                upstream_lock_file=lock_path,
                upstream_lock_min_interval_seconds=0,
                rate_limit=1000.0,
            )

            with _vlrgg_upstream_slot(args, stage_name="match_detail_101"):
                pass

            metadata = json.loads(lock_path.read_text(encoding="utf-8"))
            self.assertEqual(metadata["stage"], "match_detail_101")
            self.assertEqual(metadata["min_interval_seconds"], 0.001)
            self.assertIn("pid", metadata)

    def test_completed_stage_clears_stale_failure_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = CollectionState(Path(tmp) / "vlrgg_state.json", reset=True)
            state.mark_stage(
                "match_detail_101",
                "degraded",
                failure_reason="temporary timeout",
                next_retry_at="2026-05-11T00:00:00Z",
            )

            state.mark_stage("match_detail_101", "completed", rows=12, network_requests=1)

            row = state.stage("match_detail_101")
            self.assertEqual(row["status"], "completed")
            self.assertNotIn("failure_reason", row)
            self.assertNotIn("next_retry_at", row)

    def test_empty_match_detail_rows_are_not_successful(self) -> None:
        with self.assertRaises(CollectionStageError) as ctx:
            _require_match_detail_rows(
                match_id="667825",
                maps=pd.DataFrame(),
                players=pd.DataFrame(),
                source_label="direct HTML fallback",
                requests_made=2,
            )

        self.assertIn("direct HTML fallback", str(ctx.exception))
        self.assertEqual(ctx.exception.requests_made, 2)

    def test_empty_match_detail_completion_is_retried(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = CollectionState(Path(tmp) / "vlrgg_state.json", reset=True)
            state.mark_stage(
                "match_detail_667825",
                "completed",
                attempts=1,
                rows=0,
                network_requests=1,
                details={
                    "map_rows": 0,
                    "player_rows": 0,
                    "composition_rows": 0,
                    "used_direct_html_fallback": True,
                },
            )
            args = Namespace(
                restart=False,
                max_rate_limit_wait_seconds=0,
                retry_backoff_seconds=0,
            )
            calls = {"count": 0}

            def recovered_detail() -> dict:
                calls["count"] += 1
                return {"rows": 12, "network_requests": 1, "map_rows": 2, "player_rows": 10}

            result = _run_stage_with_resume(
                args=args,
                state=state,
                name="match_detail_667825",
                cursor={"match_id": "667825", "mode": "backfill_plan"},
                fn=recovered_detail,
            )

            self.assertEqual(calls["count"], 1)
            self.assertFalse(result.get("skipped"))
            self.assertEqual(state.stage("match_detail_667825")["rows"], 12)

    def test_backfill_stops_after_degraded_match_detail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidates_file = root / "candidates.csv"
            pd.DataFrame([
                {
                    "candidate_type": "match",
                    "candidate_id": "101",
                    "match_id": "101",
                    "status": "pending_detail",
                    "priority": 5,
                },
                {
                    "candidate_type": "match",
                    "candidate_id": "102",
                    "match_id": "102",
                    "status": "pending_detail",
                    "priority": 5,
                },
            ]).to_csv(candidates_file, index=False)
            args = Namespace(
                restart=False,
                max_rate_limit_wait_seconds=0,
                retry_backoff_seconds=0,
                max_requests_per_session=20,
                detail_limit=0,
                event_limit=0,
                team_limit=0,
                standing_years="",
                rate_limit=1000.0,
                backfill_shard_count=1,
                backfill_shard_index=0,
                backfill_candidates_file=str(candidates_file),
                api_base_url="http://127.0.0.1:3001",
                cache_dir=root / "cache",
                output=root / "processed",
                reports=root / "reports",
                state_file=root / "state.json",
                stage_output_dir=root / "stage",
            )

            with (
                patch("ml.collect_vlrgg.fetch_robots_policy", return_value={
                    "rows": 1,
                    "network_requests": 0,
                    "direct_html_allowed_live": True,
                }),
                patch("ml.collect_vlrgg.api_base_available", return_value=(True, "ok", 0)),
                patch(
                    "ml.collect_vlrgg.fetch_api_match_detail_to_stage",
                    side_effect=CollectionStageError("api unavailable", requests_made=0),
                ),
                patch("ml.vlrgg_scraper.scrape_match_detail", return_value=[]),
            ):
                run_backfill_plan(args)

            state_data = json.loads(Path(args.state_file).read_text(encoding="utf-8"))
            self.assertEqual(state_data["stages"]["backfill_match_detail_stop"]["status"], "degraded")
            stopped_match_id = state_data["stages"]["backfill_match_detail_stop"]["cursor"]["match_id"]
            self.assertIn(stopped_match_id, {"101", "102"})
            self.assertEqual(state_data["stages"][f"match_detail_{stopped_match_id}"]["status"], "degraded")
            remaining_match_id = ({"101", "102"} - {stopped_match_id}).pop()
            self.assertNotIn(f"match_detail_{remaining_match_id}", state_data["stages"])

    def test_backfill_api_only_can_skip_robots_and_direct_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidates_file = root / "candidates.csv"
            pd.DataFrame([{
                "candidate_type": "match",
                "candidate_id": "101",
                "match_id": "101",
                "status": "pending_detail",
                "priority": 5,
            }]).to_csv(candidates_file, index=False)
            args = Namespace(
                restart=False,
                max_rate_limit_wait_seconds=0,
                retry_backoff_seconds=0,
                max_requests_per_session=5,
                detail_limit=1,
                event_limit=0,
                team_limit=0,
                standing_years="",
                rate_limit=1000.0,
                backfill_shard_count=1,
                backfill_shard_index=0,
                backfill_candidates_file=str(candidates_file),
                skip_robots_check=True,
                disable_direct_html_fallback=True,
                disable_upstream_lock=True,
                upstream_lock_file=root / "upstream.lock",
                upstream_lock_min_interval_seconds=0,
                api_base_url="https://vlrggapi.vercel.app",
                cache_dir=root / "cache",
                output=root / "processed",
                reports=root / "reports",
                state_file=root / "state.json",
                stage_output_dir=root / "stage",
            )

            with (
                patch("ml.collect_vlrgg.fetch_robots_policy", side_effect=AssertionError("robots check should be skipped")),
                patch("ml.collect_vlrgg.api_base_available", return_value=(True, "ok", 0)),
                patch("ml.collect_vlrgg.fetch_api_match_detail_to_stage", return_value={
                    "rows": 12,
                    "network_requests": 1,
                    "map_rows": 2,
                    "player_rows": 10,
                }),
                patch("ml.vlrgg_scraper.scrape_match_detail", side_effect=AssertionError("direct fallback should be disabled")),
            ):
                run_backfill_plan(args)

            state_data = json.loads(Path(args.state_file).read_text(encoding="utf-8"))
            self.assertEqual(state_data["stages"]["robots_txt"]["status"], "completed")
            self.assertTrue(state_data["stages"]["robots_txt"]["skipped"])
            self.assertEqual(state_data["stages"]["backfill_direct_html_available"]["status"], "completed")
            self.assertTrue(state_data["stages"]["backfill_direct_html_available"]["skipped"])
            self.assertEqual(state_data["stages"]["match_detail_101"]["status"], "completed")
            self.assertNotIn("backfill_match_detail_stop", state_data["stages"])

    def test_backfill_shards_partition_match_ids(self) -> None:
        candidates = pd.DataFrame([
            {
                "candidate_type": "match",
                "candidate_id": str(match_id),
                "match_id": str(match_id),
                "status": "pending_detail",
                "priority": 5,
                "date": f"2026-05-{match_id:02d}",
            }
            for match_id in range(1, 25)
        ])

        parts = [
            set(_candidate_ids_for_backfill(
                candidates,
                limit=0,
                request_budget=100,
                shard_count=4,
                shard_index=idx,
            ))
            for idx in range(4)
        ]
        expected = {str(match_id) for match_id in range(1, 25)}

        self.assertEqual(set().union(*parts), expected)
        for left in range(4):
            for right in range(left + 1, 4):
                self.assertFalse(parts[left] & parts[right])
        self.assertEqual(_stable_backfill_shard("595657", 4), _stable_backfill_shard("595657", 4))

    def test_parallel_backfill_shard_paths_are_isolated_by_default(self) -> None:
        args = Namespace(
            backfill_shard_count=4,
            backfill_shard_index=3,
            cache_dir="data/raw/vlrgg_cache",
            output="data/processed",
            reports="reports",
            state_file=".omx/state/vlrgg_collection_state.json",
            stage_output_dir=".omx/state/vlrgg_collection_outputs",
        )

        apply_backfill_shard_isolation(args)

        self.assertEqual(str(args.cache_dir), "data/raw/vlrgg_cache_shards/shard_3")
        self.assertEqual(str(args.output), "data/processed/vlrgg_shards/shard_3")
        self.assertEqual(str(args.reports), "reports/vlrgg_shards/shard_3")
        self.assertEqual(str(args.state_file), ".omx/state/vlrgg_shards/shard_3_state.json")
        self.assertEqual(str(args.stage_output_dir), ".omx/state/vlrgg_shards/shard_3_outputs")

    def test_parallel_backfill_keeps_existing_shard_paths(self) -> None:
        args = Namespace(
            backfill_shard_count=4,
            backfill_shard_index=2,
            cache_dir="custom/cache/shard_2",
            output="custom/output/shard_2",
            reports="custom/reports/shard_2",
            state_file="custom/state/shard_2_state.json",
            stage_output_dir="custom/state/shard_2_outputs",
        )

        apply_backfill_shard_isolation(args)

        self.assertEqual(str(args.cache_dir), "custom/cache/shard_2")
        self.assertEqual(str(args.output), "custom/output/shard_2")
        self.assertEqual(str(args.reports), "custom/reports/shard_2")
        self.assertEqual(str(args.state_file), "custom/state/shard_2_state.json")
        self.assertEqual(str(args.stage_output_dir), "custom/state/shard_2_outputs")

    def test_duplicate_exclude_index_reads_stage_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stage = Path(tmp) / "stage"
            nested = stage / "run_20260511"
            nested.mkdir(parents=True)
            (stage / "match_detail_maps_101.json").write_text(
                json.dumps([{"match_id": "101"}]),
                encoding="utf-8",
            )
            (stage / "event_matches_202_page_1.json").write_text(
                json.dumps([{"event_id": "202"}]),
                encoding="utf-8",
            )
            (nested / "team_profile_direct_303.json").write_text(
                json.dumps([{"team_id": "303"}]),
                encoding="utf-8",
            )

            index = _load_stage_output_ids([stage])

            self.assertIn("101", index["match_id"])
            self.assertIn("202", index["event_id"])
            self.assertIn("303", index["team_id"])

    def test_duplicate_overlap_guard_filters_at_or_below_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = Namespace(
                duplicate_overlap_threshold=0.05,
                exclude_stage_output_dirs=[root / "prior"],
            )
            state = CollectionState(root / "state.json", reset=True)

            zero_overlap = _guard_duplicate_overlap(
                args=args,
                state=state,
                stage_name="duplicate_overlap_zero",
                id_key="match_id",
                candidate_ids=["1", "2", "3"],
                exclude_ids={"9"},
            )
            at_threshold = _guard_duplicate_overlap(
                args=args,
                state=state,
                stage_name="duplicate_overlap_at_threshold",
                id_key="match_id",
                candidate_ids=[str(value) for value in range(1, 21)],
                exclude_ids={"1"},
            )

            self.assertEqual(zero_overlap, ["1", "2", "3"])
            self.assertNotIn("1", at_threshold)
            self.assertEqual(len(at_threshold), 19)
            stage = state.stage("duplicate_overlap_at_threshold")
            self.assertEqual(stage["status"], "completed")
            self.assertEqual(stage["network_requests"], 0)
            self.assertEqual(stage["details"]["overlap_ratio"], 0.05)
            self.assertEqual(stage["details"]["remaining_count"], 19)

    def test_duplicate_overlap_guard_fails_above_threshold_before_requests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = Namespace(
                duplicate_overlap_threshold=0.05,
                exclude_stage_output_dirs=[root / "prior"],
            )
            state = CollectionState(root / "state.json", reset=True)

            with self.assertRaises(CollectionStageError):
                _guard_duplicate_overlap(
                    args=args,
                    state=state,
                    stage_name="duplicate_overlap_match_detail",
                    id_key="match_id",
                    candidate_ids=[str(value) for value in range(1, 11)],
                    exclude_ids={"1"},
                )

            stage = state.stage("duplicate_overlap_match_detail")
            self.assertEqual(stage["status"], "failed")
            self.assertEqual(stage["network_requests"], 0)
            self.assertEqual(state.data["cumulative_requests"], 0)
            self.assertIn("exceeds threshold", state.data["failure_reason"])

    def test_merge_shard_outputs_defaults_to_standard_shard_dirs(self) -> None:
        args = Namespace(
            output="data/processed",
            shard_output_dirs=[],
            no_merge_existing_output=True,
            backfill_shard_count=4,
            backfill_shard_index=0,
        )

        self.assertEqual(
            [str(path) for path in _merge_source_output_dirs(args)],
            [
                "data/processed/vlrgg_shards/shard_0",
                "data/processed/vlrgg_shards/shard_1",
                "data/processed/vlrgg_shards/shard_2",
                "data/processed/vlrgg_shards/shard_3",
            ],
        )

    def test_merge_shard_outputs_rebuilds_pipeline_and_candidates(self) -> None:
        agents_a = ["jett", "sova", "omen", "killjoy", "gekko"]
        agents_b = ["raze", "fade", "viper", "cypher", "breach"]

        def players(prefix: str, agents: list[str]) -> list[dict]:
            return [
                {
                    "player": f"{prefix}{idx}",
                    "agent": agent,
                    "rating": 1.0,
                    "acs": 200 + idx,
                    "kills": 15 + idx,
                    "deaths": 10,
                    "assists": idx,
                    "kast": 75,
                    "adr": 130 + idx,
                    "hs_pct": 25,
                    "fb": 1,
                    "fd": 0,
                    "atk_kills": 8,
                    "def_kills": 7,
                    "atk_deaths": 5,
                    "def_deaths": 5,
                }
                for idx, agent in enumerate(agents, start=1)
            ]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            final_output = root / "processed"
            final_reports = root / "reports"
            shard_output = root / "shard_0"
            final_output.mkdir()
            final_reports.mkdir()
            shard_output.mkdir()

            event_matches = pd.DataFrame([{
                "event_id": "e1",
                "event": "Test Event",
                "match_id": "123",
                "team_a": "Alpha",
                "team_b": "Beta",
                "score_a": 13,
                "score_b": 9,
                "date": "2026-05-10",
                **{field: "x" for field in PROVENANCE_FIELDS if field != "cache_hit"},
                "cache_hit": True,
            }])
            event_matches.to_csv(final_output / "vlrgg_event_matches.csv", index=False)
            pd.DataFrame([{
                "candidate_type": "match",
                "candidate_id": "123",
                "match_id": "123",
                "status": "pending_detail",
                "priority": 5,
            }]).to_csv(final_output / "vlrgg_match_candidates.csv", index=False)

            details = [{
                "match_id": "123",
                "game_id": "456",
                "map": "ascent",
                "team_a": "Alpha",
                "team_b": "Beta",
                "first_atk": "Alpha",
                "atk_rounds_a": 7,
                "def_rounds_a": 6,
                "ot_rounds_a": 0,
                "atk_rounds_b": 5,
                "def_rounds_b": 4,
                "ot_rounds_b": 0,
                "agents_a": agents_a,
                "agents_b": agents_b,
                "players_a": players("a", agents_a),
                "players_b": players("b", agents_b),
            }]
            maps, match_players, comps = build_match_detail_frames(details, "2026-05-10T00:00:00Z")
            maps.to_csv(shard_output / "vlrgg_match_maps.csv", index=False)
            match_players.to_csv(shard_output / "vlrgg_match_players.csv", index=False)
            comps.to_csv(shard_output / "vlrgg_compositions.csv", index=False)

            args = Namespace(
                output=final_output,
                reports=final_reports,
                shard_output_dirs=[str(shard_output)],
                no_merge_existing_output=False,
                state_file=str(root / "merge_state.json"),
                stage_output_dir=str(root / "merge_stage"),
                backfill_shard_count=1,
                backfill_shard_index=0,
            )

            run_merge_shard_outputs(args)

            pipeline = pd.read_csv(final_output / "vlrgg_pipeline_matches.csv")
            candidates = pd.read_csv(final_output / "vlrgg_match_candidates.csv")
            self.assertEqual(len(pipeline), 1)
            self.assertEqual(candidates.iloc[0]["status"], "detail_complete")

    def test_report_facts_include_doc_update_provenance(self) -> None:
        vlr_players = pd.DataFrame([{
            "agent": "Sova",
            "source_url": "http://127.0.0.1:3001/v2/stats?region=kr&timespan=all",
            "retrieval_method": "api_cache",
        }])
        vlr_matches = pd.DataFrame([{
            "source_url": "https://www.vlr.gg/1/test",
            "retrieval_method": "kaggle_cache",
        }])
        coverage = {
            "sources": {
                "processed_model_contract": {
                    "rows": 10,
                    "path": "data/processed/matches_clean.csv",
                    "active_feature_count": 57,
                }
            }
        }
        ingestion = {
            "generated_at": "2026-05-10T00:00:00Z",
            "mode": "from_cache_only",
            "network_requests": 0,
            "retrieval_methods": {"api_cache": 1},
            "robots_url": "https://www.vlr.gg/robots.txt",
            "allowed_paths": ["/matches/results"],
            "blocked_paths": ["/search/auto", "/rr/"],
        }
        comparisons = {
            "shared_agents": ["Sova"],
            "vlr_only_agents": [],
            "top_vlr_agents": [{"agent": "Sova", "rows": 1}],
        }

        facts = build_report_facts(
            coverage,
            ingestion,
            comparisons,
            [],
            [],
            vlr_matches,
            vlr_players,
        )

        self.assertTrue(facts)
        for fact in facts:
            self.assertTrue(set(REQUIRED_FACT_FIELDS).issubset(fact))
            self.assertTrue(fact["dataset_id"])
            self.assertTrue(fact["source_url"])
            self.assertTrue(fact["doc_targets"])

    def test_match_detail_frames_include_maps_players_and_compositions(self) -> None:
        details = [{
            "match_id": "123",
            "game_id": "456",
            "map": "ascent",
            "team_a": "Alpha",
            "team_b": "Beta",
            "first_atk": "Alpha",
            "atk_rounds_a": 7,
            "def_rounds_a": 6,
            "ot_rounds_a": 0,
            "atk_rounds_b": 5,
            "def_rounds_b": 4,
            "ot_rounds_b": 0,
            "agents_a": ["jett", "sova", "omen", "killjoy", "gekko"],
            "agents_b": ["raze", "fade", "viper", "cypher", "breach"],
            "players_a": [{
                "player": "p1",
                "agent": "jett",
                "rating": 1.2,
                "acs": 250,
                "kills": 20,
                "deaths": 10,
                "assists": 5,
                "kast": 80,
                "adr": 150,
                "hs_pct": 30,
                "fb": 3,
                "fd": 1,
                "atk_kills": 11,
                "def_kills": 9,
                "atk_deaths": 5,
                "def_deaths": 5,
            }],
            "players_b": [],
        }]

        maps, players, comps = build_match_detail_frames(details, "2026-05-10T00:00:00Z")

        self.assertEqual(len(maps), 2)
        self.assertEqual(len(players), 1)
        self.assertEqual(len(comps), 2)
        self.assertEqual(maps.iloc[0]["map"], "Ascent")
        self.assertEqual(players.iloc[0]["agent"], "Jett")
        self.assertEqual(comps.iloc[0]["comp_key"], "Gekko|Jett|Killjoy|Omen|Sova")
        self.assertEqual(comps.iloc[0]["duelist_count"], 1)
        for df_name, df in [("maps", maps), ("players", players), ("comps", comps)]:
            validate_provenance(df, df_name)

    def test_complete_match_detail_becomes_pipeline_match(self) -> None:
        agents_a = ["jett", "sova", "omen", "killjoy", "gekko"]
        agents_b = ["raze", "fade", "viper", "cypher", "breach"]

        def players(prefix: str, agents: list[str]) -> list[dict]:
            return [
                {
                    "player": f"{prefix}{idx}",
                    "agent": agent,
                    "rating": 1.0,
                    "acs": 200 + idx,
                    "kills": 15 + idx,
                    "deaths": 10,
                    "assists": idx,
                    "kast": 75,
                    "adr": 130 + idx,
                    "hs_pct": 25,
                    "fb": 1,
                    "fd": 0,
                    "atk_kills": 8,
                    "def_kills": 7,
                    "atk_deaths": 5,
                    "def_deaths": 5,
                }
                for idx, agent in enumerate(agents, start=1)
            ]

        details = [{
            "match_id": "123",
            "game_id": "456",
            "map": "ascent",
            "team_a": "Alpha",
            "team_b": "Beta",
            "first_atk": "Alpha",
            "atk_rounds_a": 7,
            "def_rounds_a": 6,
            "ot_rounds_a": 0,
            "atk_rounds_b": 5,
            "def_rounds_b": 4,
            "ot_rounds_b": 0,
            "agents_a": agents_a,
            "agents_b": agents_b,
            "players_a": players("a", agents_a),
            "players_b": players("b", agents_b),
        }]
        maps, match_players, _ = build_match_detail_frames(details, "2026-05-10T00:00:00Z")
        event_matches = pd.DataFrame([{
            "match_id": "123",
            "event": "Test Event",
            "date": "2026-05-10",
        }])

        pipeline, rejected = build_vlrgg_pipeline_matches(maps, match_players, event_matches)

        self.assertEqual(len(pipeline), 1)
        self.assertEqual(len(rejected), 0)
        self.assertEqual(pipeline.iloc[0]["source"], "vlrgg_direct_detail")
        self.assertEqual(pipeline.iloc[0]["map"], "Ascent")
        self.assertEqual(pipeline.iloc[0]["label"], 1)

        candidates = build_match_candidates(
            matches_df=pd.DataFrame([{"match_id": "123", "source": "vlrgg_direct_html"}]),
            event_matches_df=event_matches,
            standings_df=pd.DataFrame(),
            maps_df=maps,
            players_df=match_players,
            event_candidates_df=pd.DataFrame(),
            discovered_at="2026-05-10T00:00:00Z",
        )
        self.assertEqual(candidates.iloc[0]["status"], "detail_complete")

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "vlrgg_pipeline_matches.csv"
            pipeline.to_csv(path, index=False)
            rows = parse_vlrgg_pipeline_matches(path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["source"], "vlrgg_direct_detail")
            self.assertEqual(len(rows[0]["players_a"]), 5)

    def test_api_match_detail_artifacts_feed_pipeline_contract(self) -> None:
        agents_a = ["jett", "sova", "omen", "killjoy", "gekko"]
        agents_b = ["raze", "fade", "viper", "cypher", "breach"]

        def players(prefix: str, agents: list[str]) -> list[dict]:
            return [
                {
                    "name": f"{prefix}{idx}",
                    "agent": agent,
                    "rating": "1.0",
                    "acs": str(200 + idx),
                    "kills": str(15 + idx),
                    "deaths": "10",
                    "assists": str(idx),
                    "kast": "75%",
                    "adr": str(130 + idx),
                    "hs_pct": "25%",
                    "fk": "1",
                    "fd": "0",
                }
                for idx, agent in enumerate(agents, start=1)
            ]

        detail = {
            "match_id": "595657",
            "event": {"name": "Test Event", "series": "Grand Final"},
            "map_vetos": "Alpha pick Ascent; Beta ban Bind",
            "date": "2026-05-10",
            "status": "completed",
            "teams": [{"id": "1", "name": "Alpha", "score": 1}, {"id": "2", "name": "Beta", "score": 0}],
            "maps": [{
                "map_name": "Ascent",
                "score": {"team1": {"total": 13, "ct": 6, "t": 7}, "team2": {"total": 9, "ct": 5, "t": 4}},
                "players": {"team1": players("a", agents_a), "team2": players("b", agents_b)},
                "rounds": [{"round_num": 1, "winner": "team1", "side": "t"}],
            }],
            "performance": {"kill_matrix": [{"player": "a1", "kills_vs": {"b1": "5"}}]},
            "economy": [{"Team": "Alpha", "Pistol": "50%", "Eco": "33%", "Full": "72%"}],
        }

        maps, match_players, comps, raw, rounds, economy, kill_matrix, vetoes = build_api_match_detail_artifacts(
            detail,
            fetched_at="2026-05-10T00:00:00Z",
            source_url="http://127.0.0.1:3001/v2/match/details?match_id=595657",
            cache_hit=True,
        )
        event_matches = pd.DataFrame([{"match_id": "595657", "event": "Test Event", "date": "2026-05-10"}])
        pipeline, rejected = build_vlrgg_pipeline_matches(maps, match_players, event_matches)

        self.assertEqual(len(pipeline), 1)
        self.assertEqual(len(rejected), 0)
        self.assertEqual(pipeline.iloc[0]["source"], "vlrgg_direct_detail")
        self.assertEqual(pipeline.iloc[0]["retrieval_method"], "api_match_detail_cache")
        self.assertEqual(len(raw), 1)
        self.assertEqual(len(rounds), 1)
        self.assertEqual(len(economy), 1)
        self.assertEqual(len(kill_matrix), 1)
        self.assertEqual(len(vetoes), 2)
        for df_name, df in [("maps", maps), ("players", match_players), ("comps", comps), ("raw", raw)]:
            validate_provenance(df, df_name)

    def test_api_match_detail_skips_forfeit_with_no_played_maps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            detail = {
                "match_id": "646401",
                "event": {"name": "Project Queens 2026: Split 2"},
                "date": "Tuesday, March 31 2:00 AM KST",
                "status": "forfeited by INDIGO",
                "teams": [{"name": "Royal Legion GC"}, {"name": "INDIGO"}],
                "maps": [],
            }

            class FakeClient:
                request_count = 1
                last_cache_hit = False

                def __init__(self, **kwargs):
                    pass

                def fetch_match_details(self, match_id: str):
                    self.request_count = 1
                    return detail

            args = Namespace(
                rate_limit=1000.0,
                cache_dir=root / "cache",
                api_base_url="http://127.0.0.1:3001",
                api_available=True,
                stage_output_dir=root / "stage",
            )

            with patch("ml.collect_vlrgg.VLRGGClient", FakeClient):
                result = fetch_api_match_detail_to_stage(args, "646401", "2026-05-11T00:00:00Z")

            self.assertTrue(result["skipped_no_played_maps"])
            self.assertEqual(result["map_rows"], 0)
            self.assertEqual(result["player_rows"], 0)
            self.assertEqual(result["raw_rows"], 1)
            self.assertEqual(result["network_requests"], 1)
            raw_rows = json.loads((root / "stage" / "match_details_raw_646401.json").read_text(encoding="utf-8"))
            self.assertEqual(raw_rows[0]["status"], "forfeited by INDIGO")

    def test_api_event_detail_extracts_team_and_player_candidates(self) -> None:
        detail = {
            "event": {"name": "Event A", "series": "Series", "dates": "May 2026", "prize": "$1"},
            "bracket": {"format": "double_elim"},
            "prize_distribution": [{"place": "1st", "prize": "$1"}],
            "points": {"championship_points": 3},
            "teams": [{
                "id": "120",
                "name": "Alpha",
                "region": "United States",
                "players": [{"id": "9", "name": "p1", "flag": "mod-us"}],
            }],
        }

        event_df, team_df, player_df = _event_detail_frames_from_api(
            "2124",
            detail,
            fetched_at="2026-05-10T00:00:00Z",
            source_url="http://127.0.0.1:3001/v2/event/2124",
            cache_hit=False,
        )

        self.assertEqual(event_df.iloc[0]["event"], "Event A")
        self.assertTrue(set(EVENT_DETAIL_COLUMNS).issubset(event_df.columns))
        self.assertIn("double_elim", event_df.iloc[0]["bracket_json"])
        self.assertIn("championship_points", event_df.iloc[0]["points_json"])
        self.assertEqual(team_df.iloc[0]["team_id"], "120")
        self.assertEqual(team_df.iloc[0]["status"], "profile_pending")
        self.assertEqual(player_df.iloc[0]["player_id"], "9")
        self.assertEqual(player_df.iloc[0]["status"], "profile_pending")

    def test_expanded_outputs_include_event_intel_header_only_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = Namespace(
                output=root / "output",
                reports=root / "reports",
                stage_output_dir=root / "stage",
                state_file=root / "state.json",
                cache_dir=root / "cache",
                api_base_url="http://127.0.0.1:3001",
                detail_limit=0,
                event_limit=20,
                team_limit=0,
                standing_years="2024,2025,2026",
            )
            state = CollectionState(args.state_file, reset=True)

            write_expanded_outputs(
                pd.DataFrame(),
                pd.DataFrame(),
                pd.DataFrame(),
                pd.DataFrame(),
                pd.DataFrame(),
                pd.DataFrame(),
                args,
                "2026-05-10T00:00:00Z",
                state,
            )

            expected = {
                "vlrgg_event_matches.csv": None,
                "vlrgg_standings.csv": None,
                "vlrgg_event_details.csv": EVENT_DETAIL_COLUMNS,
                "vlrgg_event_player_stats.csv": EVENT_PLAYER_STATS_COLUMNS,
                "vlrgg_event_agent_usage.csv": EVENT_AGENT_USAGE_COLUMNS,
            }
            for filename, expected_columns in expected.items():
                path = args.output / filename
                self.assertTrue(path.exists(), filename)
                df = pd.read_csv(path)
                self.assertTrue(set(PROVENANCE_FIELDS).issubset(df.columns))
                if expected_columns is not None:
                    self.assertEqual(list(df.columns), expected_columns)

            summary = json.loads((args.reports / "vlrgg_ingestion_summary.json").read_text(encoding="utf-8"))
            coverage = json.loads((args.reports / "data_source_coverage.json").read_text(encoding="utf-8"))
            for dataset in [
                "vlrgg_event_matches",
                "vlrgg_standings",
                "vlrgg_event_details",
                "vlrgg_event_player_stats",
                "vlrgg_event_agent_usage",
            ]:
                self.assertIn(dataset, summary["rows"])
                self.assertIn(dataset, coverage["sources"])
                self.assertEqual(summary["rows"][dataset], 0)

    def test_read_stage_frames_prefers_current_root_over_nested_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stage = root / "stage"
            stale = stage / "run_20260511_stale"
            stage.mkdir()
            stale.mkdir()
            (stale / "event_player_stats_1.json").write_text(
                json.dumps([{"event_id": "stale"}]),
                encoding="utf-8",
            )
            (stage / "event_player_stats_1.json").write_text(
                json.dumps([{"event_id": "current"}]),
                encoding="utf-8",
            )

            frames = _read_stage_frames(Namespace(stage_output_dir=stage), "event_player_stats_")

            self.assertEqual(len(frames), 1)
            self.assertEqual(frames[0].iloc[0]["event_id"], "current")

    def test_player_profile_plan_outputs_profiles_usage_and_recent_matches_from_cache(self) -> None:
        def profile_payload(timespan: str) -> dict:
            return {
                "status": "success",
                "data": {
                    "info": {
                        "name": "TenZ",
                        "real_name": "Tyson Ngo",
                        "country": "Canada",
                        "twitter": "@TenZOfficial",
                    },
                    "current_teams": [{"id": "2", "name": "Sentinels"}],
                    "past_teams": [{"id": "188", "name": "Cloud9"}],
                    "agent_stats": [{
                        "agent": "jett",
                        "use_count": "4",
                        "rounds_played": "92",
                        "rating": "1.24",
                        "acs": "255",
                        "kd": "1.35",
                        "adr": "162",
                        "hs_pct": "28%",
                    }],
                    "event_placements": [{"event": "Masters", "placement": "1st"}],
                    "total_winnings": "$100,000",
                    "timespan": timespan,
                },
            }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cache = root / "cache"
            output = root / "output"
            reports = root / "reports"
            stage = root / "stage"
            cache.mkdir()
            for timespan in ["30d", "60d", "90d", "all"]:
                (cache / f"_v2_player_id_9_timespan_{timespan}.json").write_text(
                    json.dumps(profile_payload(timespan)),
                    encoding="utf-8",
                )
            (cache / "_v2_player_matches_id_9_page_1.json").write_text(
                json.dumps({
                    "status": "success",
                    "data": {
                        "matches": [{
                            "match_id": "595657",
                            "event": "Masters Toronto",
                            "date": "2026-05-01",
                            "round_info": "Grand Final",
                            "teams": [
                                {"name": "Sentinels", "score": "13"},
                                {"name": "G2 Esports", "score": "9"},
                            ],
                            "map": "ascent",
                        }]
                    },
                }),
                encoding="utf-8",
            )
            (cache / "_v2_player_matches_id_9_page_2.json").write_text(
                json.dumps({
                    "status": "success",
                    "data": {"matches": [{"match_id": "should_not_be_loaded"}]},
                }),
                encoding="utf-8",
            )

            args = Namespace(
                rate_limit=1.0,
                cache_dir=cache,
                output=output,
                reports=reports,
                state_file=root / "state.json",
                stage_output_dir=stage,
                api_base_url="http://127.0.0.1:3001",
                api_available=False,
                player_limit=0,
                player_profile_timespans=["30d", "60d", "90d", "all"],
                player_match_pages=1,
                event_limit=20,
                event_pages=5,
            )
            candidates = pd.DataFrame([{
                "player_id": "9",
                "player": "TenZ",
                "priority": 25,
            }])

            result = expand_player_profiles_to_stage(args, candidates, "2026-05-10T00:00:00Z", 3000)
            profiles, usage, recent = write_player_profile_outputs(
                args,
                "2026-05-10T00:00:00Z",
                state=None,
                session_network_requests=result["network_requests"],
                stopped_reason=result["stopped_reason"],
            )

            self.assertEqual(result["network_requests"], 0)
            self.assertEqual(len(profiles), 1)
            self.assertEqual(len(usage), 4)
            self.assertEqual(len(recent), 1)
            self.assertTrue(set(PLAYER_PROFILE_COLUMNS).issubset(profiles.columns))
            self.assertTrue(set(PLAYER_AGENT_USAGE_COLUMNS).issubset(usage.columns))
            self.assertTrue(set(PLAYER_RECENT_MATCH_COLUMNS).issubset(recent.columns))
            self.assertEqual(set(usage["timespan"]), {"30d", "60d", "90d", "all"})
            self.assertEqual(recent.iloc[0]["match_id"], "595657")
            self.assertNotIn("should_not_be_loaded", set(recent["match_id"]))
            self.assertIn("twitter", json.loads(profiles.iloc[0]["social_handles_json"]))
            for df_name, df in [("profiles", profiles), ("usage", usage), ("recent", recent)]:
                validate_provenance(df, df_name)

            summary = json.loads((reports / "vlrgg_player_collection_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["rows"]["vlrgg_player_profiles"], 1)
            self.assertEqual(summary["rows"]["vlrgg_player_agent_usage"], 4)
            self.assertEqual(summary["rows"]["vlrgg_player_recent_matches"], 1)
            self.assertEqual(summary["stopped_reason"], "completed")

    def test_local_research_normalizer_outputs_expected_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ds = root / "kierru__valorant-vct-champions-2025-dataset"
            ds.mkdir(parents=True)
            (ds / "pick_ban.csv").write_text(
                "match_id,event_name,team,pb_phase,map\n1,Event A,Alpha,pick,ascent\n",
                encoding="utf-8",
            )
            (ds / "economy.csv").write_text(
                "match_id,game_id,team_id,team_pistol_win,team_eco_round,team_eco_win,"
                "team_semieco_round,team_semieco_win,team_semibuy_round,team_semibuy_win,"
                "team_fullbuy_round,team_fullbuy_win,event_name\n"
                "1,2,3,1,4,2,1,0,5,3,10,7,Event A\n",
                encoding="utf-8",
            )
            (ds / "counter_kill.csv").write_text(
                "match_id,game_id,player,team_id,2k,3k,4k,5k,1v1,1v2,1v3,1v4,1v5,"
                "econ_rating,plant,defuse,event_name\n"
                "1,2,p1,3,1,0,0,0,1,0,0,0,0,80,1,0,Event A\n",
                encoding="utf-8",
            )
            (ds / "1v1.csv").write_text(
                "match_id,game_id,type,event_name,player,opponent,kills,deaths,team_id\n"
                "1,2,all,Event A,p1,p2,2,1,3\n",
                encoding="utf-8",
            )
            piyush = root / "piyush86kumar__valorant-champions-2024"
            piyush.mkdir()
            (piyush / "detailed_matches_player_stats.csv").write_text(
                "match_id,event_name,event_stage,match_date,team1,team2,score_overall,"
                "player_name,player_id,player_team,stat_type,agent,rating,acs,k,d,a,"
                "kd_diff,kast,adr,hs_percent,fk,fd,fk_fd_diff,map_name,map_winner\n"
                "1,Event B,Final,2025-01-01,A,B,2 - 0,p1,11,A,map,sova,1.1,220,18,12,6,6,80%,140,25%,2,1,1,bind,A\n",
                encoding="utf-8",
            )

            outputs, inventory = build_outputs(root)

            self.assertEqual(len(outputs["research_pick_ban"]), 1)
            self.assertEqual(len(outputs["research_economy"]), 1)
            self.assertEqual(len(outputs["research_clutch_counter"]), 2)
            self.assertEqual(len(outputs["research_player_map_stats"]), 1)
            self.assertEqual(outputs["research_pick_ban"].iloc[0]["map"], "Ascent")
            self.assertEqual(outputs["research_player_map_stats"].iloc[0]["agent"], "Sova")
            self.assertEqual(inventory["network_requests"], 0)


if __name__ == "__main__":
    unittest.main()
