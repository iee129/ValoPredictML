"""v10 전처리: VCT + VCL Challengers 통합 + 시간순 80/20 분할.

  python -m src.preprocess_v10

산출:
  artifacts/processed/all_v10.csv
  artifacts/processed/train_v10.csv
  artifacts/processed/test_v10.csv
  artifacts/prior_state_v10.joblib
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib

from config import ARTIFACTS_DIR, MODELS_DIR, PROCESSED_DIR, REPORTS_DIR
from src.data_load import (
    attach_ids_to_kills_stats,
    attach_ids_to_overview,
    clutch_lookup as build_clutch_lookup,
    rounds_per_map_lookup,
)
from src.data_load_v10 import (
    filter_kills_stats_per_player_map_v10,
    filter_overview_per_player_map_v10,
    load_kills_stats_v10,
    load_maps_scores_v10,
    load_match_ids_v10,
    load_overview_v10,
)
from src.features_main import assemble_features_v4
from src.labels import build_labels
from src.priors import compute_priors
from src.splits_v9 import split_proportional

ALL_CSV_V10        = PROCESSED_DIR / "all_v10.csv"
TRAIN_CSV_V10      = PROCESSED_DIR / "train_v10.csv"
TEST_CSV_V10       = PROCESSED_DIR / "test_v10.csv"
PRIOR_STATE_V10    = ARTIFACTS_DIR / "prior_state_v10.joblib"


def _ensure_dirs():
    for d in (ARTIFACTS_DIR, PROCESSED_DIR, MODELS_DIR, REPORTS_DIR):
        Path(d).mkdir(parents=True, exist_ok=True)


def main():
    _ensure_dirs()

    print("[preprocess_v10] step 1/6: CSVs 로드 (VCT + VCL)", file=sys.stderr)
    overview    = load_overview_v10()
    maps_scores = load_maps_scores_v10()
    kills_stats = load_kills_stats_v10()

    print("[preprocess_v10] step 2/6: Match ID 부여 (VCT 원본 + VCL 합성)", file=sys.stderr)
    match_ids   = load_match_ids_v10()
    overview    = attach_ids_to_overview(
        filter_overview_per_player_map_v10(overview), match_ids)
    kills_stats = attach_ids_to_kills_stats(
        filter_kills_stats_per_player_map_v10(kills_stats), match_ids)

    print("[preprocess_v10] step 3/6: 레이블 + 룩업 구성", file=sys.stderr)
    labels   = build_labels(maps_scores, match_ids)
    rounds   = rounds_per_map_lookup(maps_scores, match_ids)
    clutches = build_clutch_lookup(kills_stats)

    print("[preprocess_v10] step 4/6: leak-safe prior + co-play", file=sys.stderr)
    priors_df, state = compute_priors(overview, labels, rounds, clutches)

    print("[preprocess_v10] step 5/6: 슬롯 피처 + role_combo prior", file=sys.stderr)
    feat, combo_state = assemble_features_v4(priors_df)

    print("[preprocess_v10] step 6/6: 80/20 시간순 분할 + 저장", file=sys.stderr)
    train_df, test_df = split_proportional(feat)

    feat.to_csv(ALL_CSV_V10, index=False)
    print(f"  all_v10.csv  : {len(feat):,} rows × {len(feat.columns)} cols", file=sys.stderr)
    train_df.to_csv(TRAIN_CSV_V10, index=False)
    test_df.to_csv(TEST_CSV_V10, index=False)
    print(f"  train: {len(train_df):,} | test: {len(test_df):,}", file=sys.stderr)

    state_v10 = dict(state)
    state_v10["role_combo_state"] = combo_state
    joblib.dump(state_v10, PRIOR_STATE_V10)
    print(f"  prior_state_v10: {PRIOR_STATE_V10}", file=sys.stderr)

    print("\n[preprocess_v10] === sanity ===", file=sys.stderr)
    print(f"label balance  train: A wins = {train_df['winner'].mean():.3f}", file=sys.stderr)
    print(f"label balance  test : A wins = {test_df['winner'].mean():.3f}", file=sys.stderr)
    print(f"year range     train: {train_df['year'].min()}~{train_df['year'].max()}", file=sys.stderr)
    print(f"year range     test : {test_df['year'].min()}~{test_df['year'].max()}", file=sys.stderr)


if __name__ == "__main__":
    main()
