from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from app.feature_builder import PlayerInput, build_features, feature_source_status
import app.feature_builder as feature_builder
from app.insights import (
    describe_feature_changes,
    enrich_top_factors,
    load_vlr_evidence,
    split_factor_insights,
)


_DEFAULT_STATS = {
    "avg_acs": 200.0,
    "avg_kd": 1.0,
    "avg_kast": 0.70,
    "avg_adr": 130.0,
    "avg_hs": 0.25,
    "avg_fk": 2.0,
    "avg_fd": 2.0,
    "avg_assists": 5.0,
}


class AppInsightTests(unittest.TestCase):
    def setUp(self) -> None:
        self._old_combo = feature_builder._combo
        feature_builder._combo = {
            "wr": {
                "Jett|Ascent": 0.60,
                "Phoenix|Ascent": 0.55,
                "Raze|Ascent": 0.52,
                "Sova|Ascent": 0.51,
                "Omen|Ascent": 0.49,
                "Killjoy|Ascent": 0.48,
            },
            "pr": {},
            "exp": {},
        }

    def tearDown(self) -> None:
        feature_builder._combo = self._old_combo

    def test_feature_builder_fills_map_wr_features_from_combo_stats(self) -> None:
        team_a = [
            PlayerInput("", "Jett"),
            PlayerInput("", "Phoenix"),
            PlayerInput("", "Sova"),
            PlayerInput("", "Omen"),
            PlayerInput("", "Killjoy"),
        ]
        team_b = [
            PlayerInput("", "Raze"),
            PlayerInput("", "Sova"),
            PlayerInput("", "Omen"),
            PlayerInput("", "Killjoy"),
            PlayerInput("", "Cypher"),
        ]
        player_stats = {"": _DEFAULT_STATS}

        features = build_features(team_a, team_b, "Ascent", True, player_stats=player_stats)

        self.assertAlmostEqual(features.at[0, "a_map_wr_mean"], (0.60 + 0.55 + 0.51 + 0.49 + 0.48) / 5)
        self.assertAlmostEqual(features.at[0, "b_map_wr_mean"], (0.52 + 0.51 + 0.49 + 0.48 + 0.50) / 5)
        self.assertAlmostEqual(
            features.at[0, "diff_map_wr"],
            features.at[0, "a_map_wr_mean"] - features.at[0, "b_map_wr_mean"],
        )

        status = feature_source_status(team_a, team_b, "Ascent")
        self.assertEqual(status["agent_map_stats"]["matched"], 9)
        self.assertTrue(status["agent_map_stats"]["neutral_used"])
        self.assertIn("Cypher|Ascent", status["agent_map_stats"]["missing"])

    def test_top_factors_become_korean_insight_lists(self) -> None:
        features = pd.DataFrame([{"diff_avg_kast": 0.04, "b_fk_fd_ratio": 1.35}])
        top = enrich_top_factors(
            [
                {"feature": "diff_avg_kast", "value": 0.08},
                {"feature": "b_fk_fd_ratio", "value": -0.05},
            ],
            features,
        )

        favorable, risks = split_factor_insights(top)

        self.assertIn("Team A의 평균 KAST", favorable[0])
        self.assertIn("Team B 선제 교전 지표", risks[0])
        self.assertIn("낮추는", risks[0])

    def test_feature_change_reasons_rank_changed_features(self) -> None:
        before = pd.DataFrame([{"a_map_wr_mean": 0.50, "a_avg_agent_exp": 1.0}])
        after = pd.DataFrame([{"a_map_wr_mean": 0.57, "a_avg_agent_exp": 4.0}])

        reasons = describe_feature_changes(before, after, {"a_map_wr_mean": 0.1}, limit=2)

        self.assertEqual(len(reasons), 2)
        self.assertIn("Team A 맵별 요원 승률", reasons[0])
        self.assertIn("상승", " ".join(reasons))

    def test_load_vlr_evidence_uses_reports_without_model_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            reports = Path(tmp)
            (reports / "vlrgg_ingestion_summary.json").write_text(
                json.dumps({
                    "generated_at": "2026-05-11T00:00:00Z",
                    "rows": {
                        "vlrgg_agent_map_stats": 10,
                        "vlrgg_team_map_stats": 4,
                        "vlrgg_pipeline_matches": 3,
                    },
                    "sources": {"vlrgg_direct_html": 5},
                }),
                encoding="utf-8",
            )
            (reports / "vlrgg_pipeline_readiness.json").write_text(
                json.dumps({"ready_for_pipeline": True, "accepted_rows": 3}),
                encoding="utf-8",
            )

            evidence = load_vlr_evidence(reports)

        self.assertIsNotNone(evidence)
        assert evidence is not None
        self.assertEqual(evidence["total_rows"], 17)
        self.assertEqual(evidence["pipeline_matches"], 3)
        self.assertTrue(evidence["pipeline_ready"])


if __name__ == "__main__":
    unittest.main()
