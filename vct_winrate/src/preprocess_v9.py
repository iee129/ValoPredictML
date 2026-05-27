"""v9 전처리: 시간순 80/20 분할 + LightGBM+SVM+RF.

  python -m src.preprocess_v9

산출:
  artifacts/processed/all_v9.csv
  artifacts/processed/train_v9.csv
  artifacts/processed/test_v9.csv
  artifacts/prior_state_v9.joblib
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
    filter_kills_stats_per_player_map,
    filter_overview_per_player_map,
    load_kills_stats,
    load_match_ids,
    load_maps_scores,
    load_overview,
    rounds_per_map_lookup,
)
from src.features_main import assemble_features_v4
from src.labels import build_labels
from src.priors import compute_priors
from src.splits_v9 import split_proportional

ALL_CSV_V9   = PROCESSED_DIR / "all_v9.csv"
TRAIN_CSV_V9 = PROCESSED_DIR / "train_v9.csv"
TEST_CSV_V9  = PROCESSED_DIR / "test_v9.csv"
PRIOR_STATE_V9_PATH = ARTIFACTS_DIR / "prior_state_v9.joblib"


def _ensure_dirs():
    for d in (ARTIFACTS_DIR, PROCESSED_DIR, MODELS_DIR, REPORTS_DIR):
        Path(d).mkdir(parents=True, exist_ok=True)


def main():
    _ensure_dirs()

    print("[preprocess_v9] step 1/6: load CSVs", file=sys.stderr)
    overview    = load_overview()
    match_ids   = load_match_ids()
    maps_scores = load_maps_scores()
    kills_stats = load_kills_stats()

    print("[preprocess_v9] step 2/6: filter + attach Match IDs", file=sys.stderr)
    overview    = attach_ids_to_overview(
        filter_overview_per_player_map(overview), match_ids)
    kills_stats = attach_ids_to_kills_stats(
        filter_kills_stats_per_player_map(kills_stats), match_ids)

    print("[preprocess_v9] step 3/6: build labels + lookups", file=sys.stderr)
    labels   = build_labels(maps_scores, match_ids)
    rounds   = rounds_per_map_lookup(maps_scores, match_ids)
    clutches = build_clutch_lookup(kills_stats)

    print("[preprocess_v9] step 4/6: leak-safe priors + co-play", file=sys.stderr)
    priors_df, state = compute_priors(overview, labels, rounds, clutches)

    print("[preprocess_v9] step 5/6: slot features + role_combo prior", file=sys.stderr)
    feat, combo_state = assemble_features_v4(priors_df)

    print("[preprocess_v9] step 6/6: 비율 분할(80/20) + save", file=sys.stderr)
    train_df, test_df = split_proportional(feat)

    feat.to_csv(ALL_CSV_V9, index=False)
    print(f"  all_v9.csv: {len(feat):,} rows × {len(feat.columns)} cols", file=sys.stderr)
    train_df.to_csv(TRAIN_CSV_V9, index=False)
    test_df.to_csv(TEST_CSV_V9, index=False)
    print(f"  train: {len(train_df):,} | test: {len(test_df):,}", file=sys.stderr)

    state_v9 = dict(state)
    state_v9["role_combo_state"] = combo_state
    joblib.dump(state_v9, PRIOR_STATE_V9_PATH)
    print(f"  prior_state_v9: {PRIOR_STATE_V9_PATH}", file=sys.stderr)

    print("\n[preprocess_v9] === sanity ===", file=sys.stderr)
    print(f"label balance (train): A wins = {train_df['winner'].mean():.3f}", file=sys.stderr)
    print(f"label balance (test):  A wins = {test_df['winner'].mean():.3f}", file=sys.stderr)
    print(f"year range (train): {train_df['year'].min()}~{train_df['year'].max()}", file=sys.stderr)
    print(f"year range (test):  {test_df['year'].min()}~{test_df['year'].max()}", file=sys.stderr)


if __name__ == "__main__":
    main()
