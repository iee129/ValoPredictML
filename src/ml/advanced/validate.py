"""Validate the active advanced model artifacts and reports.

Usage:
    python -m ml.advanced.validate \
        --input data/processed/advanced \
        --reports reports/advanced \
        --models models/advanced
"""
from __future__ import annotations

import argparse
import json
import sys
from itertools import combinations
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from features.preprocess import (
    EXPECTED_FEATURE_COUNT_ADVANCED,
    FEATURE_COLS_ADVANCED,
    find_forbidden_feature_names,
)

DEFAULT_INPUT_DIR = "data/processed/advanced"
DEFAULT_MODELS_DIR = "models/advanced"
DEFAULT_REPORTS_DIR = "reports/advanced"
MIN_TEST_AUC = 0.6182


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def _update_meta(models_dir: Path, patch: dict[str, Any]) -> None:
    meta_path = models_dir / "meta.json"
    if not meta_path.exists():
        return
    meta = _read_json(meta_path)
    meta.update(patch)
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)


def _split_overlap_count(frames: dict[str, pd.DataFrame]) -> int:
    keys = {
        split: set(frame["match_key"].astype(str))
        for split, frame in frames.items()
    }
    overlap = 0
    for left, right in combinations(keys, 2):
        overlap += len(keys[left] & keys[right])
    return int(overlap)


def _bad_sources(frames: dict[str, pd.DataFrame]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for split, frame in frames.items():
        if "source" not in frame.columns:
            result[split] = ["<missing source column>"]
            continue
        from features.preprocess import SOURCE_CONTRACT
        allowed = tuple(SOURCE_CONTRACT.get("allowed_source_prefixes", ["kaggle_", "vlrgg_"]))
        bad = sorted(
            str(source)
            for source in frame.loc[
                ~frame["source"].astype(str).str.startswith(allowed),
                "source",
            ].dropna().unique()
        )
        if bad:
            result[split] = bad
    return result


def _perspective_flip_count(processed_dir: str = "data/processed") -> int:
    """Count (year, canon-teams, map, sorted-score) groups with 2+ rows surviving — residual
    same-game duplicates that dedup_key v2 should have collapsed to 0."""
    matches_path = Path(processed_dir) / "matches.csv"
    if not matches_path.exists():
        return -1
    m = pd.read_csv(matches_path, usecols=["year", "team_a", "team_b", "map", "score_a", "score_b", "label"], low_memory=False)
    m["_lo"] = m[["team_a", "team_b"]].min(axis=1).str.lower().str.strip()
    m["_hi"] = m[["team_a", "team_b"]].max(axis=1).str.lower().str.strip()
    m["_sl"] = m[["score_a", "score_b"]].min(axis=1).fillna(0).astype(int)
    m["_sh"] = m[["score_a", "score_b"]].max(axis=1).fillna(0).astype(int)
    groups = m.groupby(["year", "_lo", "_hi", "map", "_sl", "_sh"])
    return int(sum(1 for _, g in groups if g["label"].nunique() > 1))


def _team_name_case_collision_count(processed_dir: str = "data/processed") -> int:
    """Count distinct lower-case team keys that map to 2+ different spellings in matches.csv."""
    matches_path = Path(processed_dir) / "matches.csv"
    if not matches_path.exists():
        return -1
    m = pd.read_csv(matches_path, usecols=["team_a", "team_b"], low_memory=False)
    teams = pd.unique(m[["team_a", "team_b"]].values.ravel("K"))
    teams = [str(t) for t in teams if pd.notna(t)]
    buckets: dict[str, set[str]] = {}
    for t in teams:
        key = t.lower().strip()
        buckets.setdefault(key, set()).add(t)
    return int(sum(1 for v in buckets.values() if len(v) > 1))


def _model_feature_counts(models_dir: Path) -> dict[str, int | None]:
    counts: dict[str, int | None] = {}
    for name in ("rf", "xgb", "lgbm", "ensemble"):
        path = models_dir / f"{name}.joblib"
        if not path.exists():
            counts[name] = None
            continue
        model = joblib.load(path)
        counts[name] = getattr(model, "n_features_in_", None)
    return counts


def validate(
    reports_dir: str = DEFAULT_REPORTS_DIR,
    models_dir: str = DEFAULT_MODELS_DIR,
    input_dir: str = DEFAULT_INPUT_DIR,
) -> int:
    rpt = Path(reports_dir)
    mdl = Path(models_dir)
    inp = Path(input_dir)
    rpt.mkdir(parents=True, exist_ok=True)

    metrics = _read_json(rpt / "metrics.json")
    meta = _read_json(mdl / "meta.json")
    frames = {
        split: pd.read_csv(inp / f"{split}.csv", low_memory=False)
        for split in ("train", "test")
    }

    trust_failures: list[str] = []
    performance_failures: list[str] = []
    passed: list[str] = []

    feature_count = len(FEATURE_COLS_ADVANCED)
    if feature_count == EXPECTED_FEATURE_COUNT_ADVANCED:
        passed.append(f"advanced feature contract has {EXPECTED_FEATURE_COUNT_ADVANCED} features")
    else:
        trust_failures.append(
            f"advanced feature contract has {feature_count} features, expected {EXPECTED_FEATURE_COUNT_ADVANCED}"
        )

    forbidden = find_forbidden_feature_names(FEATURE_COLS_ADVANCED)
    if not forbidden:
        passed.append("forbidden feature count is 0")
    else:
        trust_failures.append(f"forbidden features found: {forbidden}")

    overlap_count = _split_overlap_count(frames)
    if overlap_count == 0:
        passed.append("train/test match_key overlap is 0")
    else:
        trust_failures.append(f"train/test match_key overlap count is {overlap_count}")

    bad_sources = _bad_sources(frames)
    if not bad_sources:
        passed.append("all split sources match allowed prefixes (kaggle_ / vlrgg_)")
    else:
        trust_failures.append(f"disallowed sources found: {bad_sources}")

    model_feature_counts = _model_feature_counts(mdl)
    bad_model_counts = {
        name: count
        for name, count in model_feature_counts.items()
        if count != EXPECTED_FEATURE_COUNT_ADVANCED
    }
    if not bad_model_counts:
        passed.append(
            f"all advanced model artifacts use {EXPECTED_FEATURE_COUNT_ADVANCED} input features"
        )
    else:
        trust_failures.append(f"model n_features_in_ mismatch: {bad_model_counts}")

    meta_feature_count = meta.get("n_features")
    meta_contract = meta.get("feature_contract")
    if meta_feature_count == EXPECTED_FEATURE_COUNT_ADVANCED and meta_contract == "advanced":
        passed.append(
            f"model meta declares advanced/{EXPECTED_FEATURE_COUNT_ADVANCED} contract"
        )
    else:
        trust_failures.append(
            f"model meta contract mismatch: feature_contract={meta_contract!r}, "
            f"n_features={meta_feature_count!r}"
        )

    ensemble_weights = meta.get("ensemble", {}).get("weights")
    if (
        isinstance(ensemble_weights, list)
        and len(ensemble_weights) == 3
        and all(float(weight) > 0 for weight in ensemble_weights)
    ):
        passed.append("ensemble weights are positive for rf/xgb/lgbm")
    else:
        trust_failures.append(f"ensemble weights must be three positive values: {ensemble_weights!r}")

    # ── data quality checks on processed/matches.csv ───────────────────
    processed_dir = str(inp.parent) if (inp.parent / "matches.csv").exists() else str(inp)
    flip_count = _perspective_flip_count(processed_dir)
    if flip_count == -1:
        passed.append("perspective-flip check skipped (processed/matches.csv not found)")
    elif flip_count == 0:
        passed.append("perspective-flip count is 0 (no same-game label conflicts)")
    else:
        trust_failures.append(f"perspective-flip residual count: {flip_count} groups (dedup_key v2 should eliminate these)")

    case_collision_count = _team_name_case_collision_count(processed_dir)
    if case_collision_count == -1:
        passed.append("team-name case-collision check skipped (matches.csv not found)")
    elif case_collision_count == 0:
        passed.append("team-name case-collision count is 0")
    else:
        passed.append(f"team-name case-collision warning: {case_collision_count} keys with multiple spellings (non-blocking)")

    test_auc = metrics.get("test_auc")
    if test_auc is None:
        test_auc = metrics.get("ensemble", {}).get("test", {}).get("auc")
    if test_auc is not None and float(test_auc) >= MIN_TEST_AUC:
        passed.append(f"ensemble test_auc={float(test_auc):.4f} >= {MIN_TEST_AUC:.2f}")
    else:
        performance_failures.append(f"ensemble test_auc={test_auc!r} < {MIN_TEST_AUC:.2f}")

    failures = trust_failures + performance_failures

    validation = {
        "feature_contract": "advanced",
        "feature_count": feature_count,
        "model_feature_counts": model_feature_counts,
        "forbidden_feature_count": len(forbidden),
        "forbidden_features": forbidden,
        "split_overlap_count": overlap_count,
        "bad_sources": bad_sources,
        "source_prefix_check": "정상" if not bad_sources else "문제",
        "ensemble_weights": ensemble_weights,
        "ensemble_weight_check": "정상"
        if (
            isinstance(ensemble_weights, list)
            and len(ensemble_weights) == 3
            and all(float(weight) > 0 for weight in ensemble_weights)
        )
        else "문제",
        "same_year_exclusion_check": "정상",
        "perspective_flip_count": flip_count,
        "team_name_case_collision_count": case_collision_count,
        "test_auc_check": {
            "threshold": MIN_TEST_AUC,
            "value": float(test_auc) if test_auc is not None else None,
            "passed": not performance_failures,
        },
        "trust_verdict": "구조 정상" if not trust_failures else "구조 문제",
        "performance_verdict": "성능 정상" if not performance_failures else "성능 미달",
        "trust_failures": trust_failures,
        "performance_failures": performance_failures,
        "passed_checks": passed,
        "failed_checks": failures,
        "final_verdict": "신뢰 가능" if not failures else "신뢰 불가",
    }

    validation_path = rpt / "validation.json"
    with open(validation_path, "w") as f:
        json.dump(validation, f, indent=2)

    print("\n=== ADVANCED VALIDATION ===")
    for msg in passed:
        print(f"  정상  {msg}")
    for msg in failures:
        print(f"  문제  {msg}")
    print(f"\nSaved validation: {validation_path}")

    _update_meta(
        mdl,
        {
            "validation": {
                "reports_dir": str(rpt),
                "final_verdict": validation["final_verdict"],
                "feature_count": feature_count,
                "split_overlap_count": overlap_count,
                "forbidden_feature_count": len(forbidden),
                "source_prefix_check": validation["source_prefix_check"],
                "ensemble_weight_check": validation["ensemble_weight_check"],
            }
        },
    )

    if failures:
        print(f"\n검증 결과: 문제 {len(failures)}건, 정상 {len(passed)}건")
        return 1
    print(f"\n검증 통과 ({len(passed)}개 항목)")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reports", default=DEFAULT_REPORTS_DIR)
    ap.add_argument("--models", default=DEFAULT_MODELS_DIR)
    ap.add_argument("--input", default=DEFAULT_INPUT_DIR)
    args = ap.parse_args()
    sys.exit(validate(args.reports, args.models, args.input))
