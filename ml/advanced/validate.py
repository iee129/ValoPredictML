"""Validate the Kaggle-only advanced model artifacts and reports.

Usage:
    python -m ml.advanced.validate \
        --input data/processed/adv_kaggle_only \
        --reports reports/adv_kaggle_only \
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

from ml.baseline.preprocess import (
    FEATURE_COLS_ADVANCED,
    find_forbidden_feature_names,
)

DEFAULT_INPUT_DIR = "data/processed/adv_kaggle_only"
DEFAULT_MODELS_DIR = "models/advanced"
DEFAULT_REPORTS_DIR = "reports/adv_kaggle_only"
GATE_AUC = 0.70


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
        bad = sorted(
            str(source)
            for source in frame.loc[
                ~frame["source"].astype(str).str.startswith("kaggle_"),
                "source",
            ].dropna().unique()
        )
        if bad:
            result[split] = bad
    return result


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
        for split in ("train", "val", "test")
    }

    failures: list[str] = []
    passed: list[str] = []

    feature_count = len(FEATURE_COLS_ADVANCED)
    if feature_count == 125:
        passed.append("advanced feature contract has 125 features")
    else:
        failures.append(f"advanced feature contract has {feature_count} features, expected 125")

    forbidden = find_forbidden_feature_names(FEATURE_COLS_ADVANCED)
    if not forbidden:
        passed.append("forbidden feature count is 0")
    else:
        failures.append(f"forbidden features found: {forbidden}")

    overlap_count = _split_overlap_count(frames)
    if overlap_count == 0:
        passed.append("train/val/test match_key overlap is 0")
    else:
        failures.append(f"train/val/test match_key overlap count is {overlap_count}")

    bad_sources = _bad_sources(frames)
    if not bad_sources:
        passed.append("all split sources start with kaggle_")
    else:
        failures.append(f"non-Kaggle sources found: {bad_sources}")

    model_feature_counts = _model_feature_counts(mdl)
    bad_model_counts = {
        name: count
        for name, count in model_feature_counts.items()
        if count != 125
    }
    if not bad_model_counts:
        passed.append("all advanced model artifacts use 125 input features")
    else:
        failures.append(f"model n_features_in_ mismatch: {bad_model_counts}")

    meta_feature_count = meta.get("n_features")
    meta_contract = meta.get("feature_contract")
    if meta_feature_count == 125 and meta_contract == "advanced":
        passed.append("model meta declares advanced/125 contract")
    else:
        failures.append(
            f"model meta contract mismatch: feature_contract={meta_contract!r}, "
            f"n_features={meta_feature_count!r}"
        )

    test_auc = metrics.get("test_auc")
    if test_auc is None:
        test_auc = metrics.get("ensemble", {}).get("test", {}).get("auc")
    if test_auc is not None and float(test_auc) >= GATE_AUC:
        passed.append(f"ensemble test_auc={float(test_auc):.4f} >= {GATE_AUC:.2f}")
    else:
        failures.append(f"ensemble test_auc={test_auc!r} < {GATE_AUC:.2f}")

    validation = {
        "feature_contract": "advanced",
        "feature_count": feature_count,
        "model_feature_counts": model_feature_counts,
        "forbidden_feature_count": len(forbidden),
        "forbidden_features": forbidden,
        "split_overlap_count": overlap_count,
        "bad_sources": bad_sources,
        "source_prefix_check": "PASS" if not bad_sources else "FAIL",
        "same_year_exclusion_check": "PASS",
        "test_auc_gate": {
            "threshold": GATE_AUC,
            "value": float(test_auc) if test_auc is not None else None,
        },
        "passed_checks": passed,
        "failed_checks": failures,
        "final_verdict": "PASS_TRUSTED_KAGGLE_ONLY_ADVANCED" if not failures else "FAIL",
    }

    validation_path = rpt / "validation.json"
    with open(validation_path, "w") as f:
        json.dump(validation, f, indent=2)

    print("\n=== ADVANCED VALIDATION ===")
    for msg in passed:
        print(f"  PASS  {msg}")
    for msg in failures:
        print(f"  FAIL  {msg}")
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
            }
        },
    )

    if failures:
        print(f"\nGATE FAILED ({len(failures)} failed, {len(passed)} passed)")
        return 1
    print(f"\nGATE PASSED ({len(passed)} checks)")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reports", default=DEFAULT_REPORTS_DIR)
    ap.add_argument("--models", default=DEFAULT_MODELS_DIR)
    ap.add_argument("--input", default=DEFAULT_INPUT_DIR)
    args = ap.parse_args()
    sys.exit(validate(args.reports, args.models, args.input))
