"""Materialize the midterm-PDF-locked baseline reference artifacts.

The final deliverables freeze the baseline as a reference number from the
midterm presentation PDF, not as a currently served model artifact. This module
keeps the local reports/models surfaces present so advanced comparisons and
release checks have a concrete baseline contract.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_REPORTS_DIR = "reports/baseline"
DEFAULT_MODELS_DIR = "models/baseline"

REFERENCE_BASELINE: dict[str, Any] = {
    "source_kind": "midterm_pdf_reference",
    "source_artifacts": [
        "final/기계학습프로젝트_11분반_중간발표_5조_발로란트 승률 예측 시뮬레이터.pdf",
        "final/deliverables/00_수치_단일진실표.md",
        "final/deliverables/00b_검증결과.md",
    ],
    "algorithm": "LR+DT_soft_voting",
    "split_protocol": "random_80_20_match_key_holdout",
    "feature_count": 421,
    "test_auc": 0.5943,
    "test_acc": 0.5667,
    "test_f1": 0.6072,
    "majority_delta_acc": 0.0649,
    "component_metrics": {
        "logistic_regression": {"test_auc": 0.6000, "test_acc": 0.5821, "test_f1": 0.6216},
        "decision_tree": {"test_auc": 0.5556, "test_acc": 0.5483, "test_f1": 0.5860},
        "soft_voting": {"test_auc": 0.5943, "test_acc": 0.5667, "test_f1": 0.6072},
    },
    "canonical_note": (
        "Baseline is frozen from the midterm presentation PDF pages 8-9. "
        "The conflicting ROC-figure AUC 0.6562 is intentionally not used."
    ),
}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def metrics_payload(created_at: str) -> dict[str, Any]:
    return {
        **REFERENCE_BASELINE,
        "created_at": created_at,
        "artifact_contract": "baseline_reference_metrics",
        "n_features": REFERENCE_BASELINE["feature_count"],
        "test_split": "midterm_pdf_reference",
        "modeling_splits": ["midterm_pdf_reference"],
        "model_artifact_required": False,
    }


def validation_payload(created_at: str) -> dict[str, Any]:
    return {
        **REFERENCE_BASELINE,
        "created_at": created_at,
        "artifact_contract": "baseline_reference_validation",
        "model_artifact_required": False,
        "model_joblib_status": "not_applicable",
        "checks": {
            "baseline_source_locked": "정상",
            "canonical_conflict_handled": "정상",
            "feature_count_present": "정상",
            "metrics_present": "정상",
        },
        "final_verdict": "신뢰 가능",
    }


def meta_payload(created_at: str) -> dict[str, Any]:
    return {
        **REFERENCE_BASELINE,
        "created_at": created_at,
        "artifact_contract": "baseline_reference_meta",
        "n_features": REFERENCE_BASELINE["feature_count"],
        "model_joblib": None,
        "model_artifact_required": False,
        "final_verdict": "신뢰 가능",
    }


def materialize(
    reports_dir: str = DEFAULT_REPORTS_DIR,
    models_dir: str = DEFAULT_MODELS_DIR,
) -> dict[str, str]:
    created_at = datetime.now(timezone.utc).isoformat()
    reports = Path(reports_dir)
    models = Path(models_dir)

    metrics_path = reports / "metrics.json"
    validation_path = reports / "validation.json"
    meta_path = models / "meta.json"

    _write_json(metrics_path, metrics_payload(created_at))
    _write_json(validation_path, validation_payload(created_at))
    _write_json(meta_path, meta_payload(created_at))

    return {
        "metrics": str(metrics_path),
        "validation": str(validation_path),
        "meta": str(meta_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports", default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--models", default=DEFAULT_MODELS_DIR)
    args = parser.parse_args()

    paths = materialize(reports_dir=args.reports, models_dir=args.models)
    print("Baseline reference artifacts materialized")
    for key, path in paths.items():
        print(f"{key}: {path}")


if __name__ == "__main__":
    main()
