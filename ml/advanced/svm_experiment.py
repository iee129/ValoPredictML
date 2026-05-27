"""Run a non-promoting SVM experiment for the advanced ensemble.

This script does not overwrite the active advanced model. It trains a calibrated
linear SVM sidecar and compares it with the current RF/XGB/LGBM ensemble on the
same advanced 125-feature contract.

Usage:
    python -m ml.advanced.svm_experiment \
        --input data/processed/adv_kaggle_only \
        --models models/advanced \
        --output models/advanced_svm_experiment \
        --reports reports/advanced_svm_experiment
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC

from ml.baseline.preprocess import FEATURE_COLS_ADVANCED, build_xy

DEFAULT_INPUT_DIR = "data/processed/adv_kaggle_only"
DEFAULT_MODELS_DIR = "models/advanced"
DEFAULT_OUTPUT_DIR = "models/advanced_svm_experiment"
DEFAULT_REPORTS_DIR = "reports/advanced_svm_experiment"


def _read_split(input_dir: Path, split: str) -> tuple[pd.DataFrame, pd.Series]:
    frame = pd.read_csv(input_dir / f"{split}.csv", low_memory=False)
    X, y, _ = build_xy(frame, feature_contract="advanced")
    if list(X.columns) != FEATURE_COLS_ADVANCED:
        raise RuntimeError("Advanced feature order does not match FEATURE_COLS_ADVANCED")
    return X, y


def _metrics(y_true: pd.Series, probs: np.ndarray) -> dict[str, Any]:
    preds = (probs >= 0.5).astype(int)
    return {
        "auc": float(roc_auc_score(y_true, probs)),
        "acc": float(accuracy_score(y_true, preds)),
        "f1": float(f1_score(y_true, preds)),
        "confusion_matrix": confusion_matrix(y_true, preds).tolist(),
    }


def _weight_sweep(
    y_true: pd.Series,
    current_probs: np.ndarray,
    svm_probs: np.ndarray,
) -> dict[str, Any]:
    rows = []
    for weight in np.linspace(0.0, 1.0, 21):
        probs = (1.0 - weight) * current_probs + weight * svm_probs
        rows.append(
            {
                "svm_weight": round(float(weight), 2),
                **_metrics(y_true, probs),
            }
        )
    return {
        "rows": rows,
        "best_auc": max(rows, key=lambda row: row["auc"]),
        "best_acc": max(rows, key=lambda row: row["acc"]),
        "best_f1": max(rows, key=lambda row: row["f1"]),
    }


def make_calibrated_linear_svm(
    c_value: float,
    max_iter: int,
    calibration_cv: int,
) -> CalibratedClassifierCV:
    base = make_pipeline(
        StandardScaler(),
        LinearSVC(
            C=float(c_value),
            class_weight="balanced",
            dual="auto",
            max_iter=int(max_iter),
            random_state=42,
        ),
    )
    return CalibratedClassifierCV(
        estimator=base,
        method="sigmoid",
        cv=int(calibration_cv),
        n_jobs=-1,
    )


def _load_current_models(models_dir: Path) -> dict[str, Any]:
    names = ["rf", "xgb", "lgbm", "ensemble"]
    models = {name: joblib.load(models_dir / f"{name}.joblib") for name in names}
    for name, model in models.items():
        n_features = getattr(model, "n_features_in_", None)
        if n_features != len(FEATURE_COLS_ADVANCED):
            raise RuntimeError(
                f"{name}.joblib expects {n_features} features; "
                f"advanced contract has {len(FEATURE_COLS_ADVANCED)}"
            )
    return models


def run_experiment(
    input_dir: str = DEFAULT_INPUT_DIR,
    models_dir: str = DEFAULT_MODELS_DIR,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    reports_dir: str = DEFAULT_REPORTS_DIR,
    c_value: float = 0.5,
    max_iter: int = 10000,
    calibration_cv: int = 3,
) -> dict[str, Any]:
    inp = Path(input_dir)
    mdl = Path(models_dir)
    out = Path(output_dir)
    rpt = Path(reports_dir)
    out.mkdir(parents=True, exist_ok=True)
    rpt.mkdir(parents=True, exist_ok=True)

    X_train, y_train = _read_split(inp, "train")
    X_val, y_val = _read_split(inp, "val")
    X_test, y_test = _read_split(inp, "test")
    X_fit = pd.concat([X_train, X_val], ignore_index=True)
    y_fit = pd.concat([y_train, y_val], ignore_index=True)

    current = _load_current_models(mdl)

    print(
        "Training calibrated linear SVM on "
        f"{X_fit.shape[0]:,} rows x {X_fit.shape[1]} features"
    )
    svm = make_calibrated_linear_svm(c_value, max_iter, calibration_cv)
    svm.fit(X_fit, y_fit)

    svm_path = out / "linear_svm_calibrated.joblib"
    joblib.dump(svm, svm_path)
    print(f"Saved SVM sidecar: {svm_path}")

    splits = {
        "train": (X_train, y_train),
        "val": (X_val, y_val),
        "test": (X_test, y_test),
    }

    results: dict[str, dict[str, Any]] = {
        "current_ensemble": {},
        "svm": {},
        "rf_xgb_lgbm_plus_svm_equal": {},
        "rf_lgbm_svm_replace_xgb_equal": {},
        "rf_lgbm_without_xgb_equal": {},
    }
    test_weight_sweep: dict[str, Any] | None = None
    for split, (X, y) in splits.items():
        rf_probs = current["rf"].predict_proba(X)[:, 1]
        xgb_probs = current["xgb"].predict_proba(X)[:, 1]
        lgbm_probs = current["lgbm"].predict_proba(X)[:, 1]
        current_probs = current["ensemble"].predict_proba(X)[:, 1]
        svm_probs = svm.predict_proba(X)[:, 1]
        plus_svm_probs = (rf_probs + xgb_probs + lgbm_probs + svm_probs) / 4.0
        replace_xgb_probs = (rf_probs + lgbm_probs + svm_probs) / 3.0
        no_xgb_probs = (rf_probs + lgbm_probs) / 2.0

        results["current_ensemble"][split] = _metrics(y, current_probs)
        results["svm"][split] = _metrics(y, svm_probs)
        results["rf_xgb_lgbm_plus_svm_equal"][split] = _metrics(y, plus_svm_probs)
        results["rf_lgbm_svm_replace_xgb_equal"][split] = _metrics(y, replace_xgb_probs)
        results["rf_lgbm_without_xgb_equal"][split] = _metrics(y, no_xgb_probs)
        if split == "test":
            test_weight_sweep = _weight_sweep(y, current_probs, svm_probs)

    current_test = results["current_ensemble"]["test"]
    plus_test = results["rf_xgb_lgbm_plus_svm_equal"]["test"]
    replace_test = results["rf_lgbm_svm_replace_xgb_equal"]["test"]
    no_xgb_test = results["rf_lgbm_without_xgb_equal"]["test"]
    svm_test = results["svm"]["test"]

    payload: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "experiment": "advanced_linear_svm_sidecar_equal_soft_vote",
        "feature_contract": "advanced",
        "feature_count": len(FEATURE_COLS_ADVANCED),
        "input_dir": str(inp),
        "active_models_dir": str(mdl),
        "output_dir": str(out),
        "reports_dir": str(rpt),
        "row_counts": {
            "train": int(len(X_train)),
            "val": int(len(X_val)),
            "fit_train_plus_val": int(len(X_fit)),
            "test": int(len(X_test)),
        },
        "svm": {
            "model": "StandardScaler + LinearSVC + sigmoid calibration",
            "c_value": float(c_value),
            "class_weight": "balanced",
            "max_iter": int(max_iter),
            "calibration_cv": int(calibration_cv),
            "artifact": str(svm_path),
        },
        "results": results,
        "summary": {
            "current_ensemble_test_auc": current_test["auc"],
            "current_ensemble_test_acc": current_test["acc"],
            "current_ensemble_test_f1": current_test["f1"],
            "svm_test_auc": svm_test["auc"],
            "svm_test_acc": svm_test["acc"],
            "svm_test_f1": svm_test["f1"],
            "plus_svm_equal_test_auc": plus_test["auc"],
            "plus_svm_equal_test_acc": plus_test["acc"],
            "plus_svm_equal_test_f1": plus_test["f1"],
            "replace_xgb_equal_test_auc": replace_test["auc"],
            "replace_xgb_equal_test_acc": replace_test["acc"],
            "replace_xgb_equal_test_f1": replace_test["f1"],
            "rf_lgbm_without_xgb_test_auc": no_xgb_test["auc"],
            "rf_lgbm_without_xgb_test_acc": no_xgb_test["acc"],
            "rf_lgbm_without_xgb_test_f1": no_xgb_test["f1"],
            "delta_auc_vs_current": float(plus_test["auc"] - current_test["auc"]),
            "delta_acc_vs_current": float(plus_test["acc"] - current_test["acc"]),
            "delta_f1_vs_current": float(plus_test["f1"] - current_test["f1"]),
            "replace_xgb_delta_auc_vs_current": float(replace_test["auc"] - current_test["auc"]),
            "replace_xgb_delta_acc_vs_current": float(replace_test["acc"] - current_test["acc"]),
            "replace_xgb_delta_f1_vs_current": float(replace_test["f1"] - current_test["f1"]),
        },
        "test_weight_sweep_against_current_ensemble": test_weight_sweep,
        "promotion_recommendation": (
            "reject"
            if max(plus_test["auc"], replace_test["auc"]) <= current_test["auc"]
            else "candidate"
        ),
    }

    metrics_path = rpt / "metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(payload, f, indent=2)
    if test_weight_sweep is not None:
        sweep_path = rpt / "weight_sweep.json"
        with open(sweep_path, "w") as f:
            json.dump(test_weight_sweep, f, indent=2)

    print("\n=== SVM EXPERIMENT TEST SUMMARY ===")
    print(
        "current ensemble: "
        f"auc={current_test['auc']:.4f} "
        f"acc={current_test['acc']:.4f} "
        f"f1={current_test['f1']:.4f}"
    )
    print(
        "svm standalone:  "
        f"auc={svm_test['auc']:.4f} "
        f"acc={svm_test['acc']:.4f} "
        f"f1={svm_test['f1']:.4f}"
    )
    print(
        "+ svm equal:     "
        f"auc={plus_test['auc']:.4f} "
        f"acc={plus_test['acc']:.4f} "
        f"f1={plus_test['f1']:.4f} "
        f"delta_auc={payload['summary']['delta_auc_vs_current']:+.4f}"
    )
    print(
        "xgb -> svm:      "
        f"auc={replace_test['auc']:.4f} "
        f"acc={replace_test['acc']:.4f} "
        f"f1={replace_test['f1']:.4f} "
        f"delta_auc={payload['summary']['replace_xgb_delta_auc_vs_current']:+.4f}"
    )
    print(
        "rf+lgbm only:    "
        f"auc={no_xgb_test['auc']:.4f} "
        f"acc={no_xgb_test['acc']:.4f} "
        f"f1={no_xgb_test['f1']:.4f}"
    )
    if test_weight_sweep is not None:
        best_auc = test_weight_sweep["best_auc"]
        print(
            "best test sweep: "
            f"svm_weight={best_auc['svm_weight']:.2f} "
            f"auc={best_auc['auc']:.4f}"
        )
    print(f"\nSaved metrics: {metrics_path}")
    return payload


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=DEFAULT_INPUT_DIR)
    ap.add_argument("--models", default=DEFAULT_MODELS_DIR)
    ap.add_argument("--output", default=DEFAULT_OUTPUT_DIR)
    ap.add_argument("--reports", default=DEFAULT_REPORTS_DIR)
    ap.add_argument("--c-value", type=float, default=0.5)
    ap.add_argument("--max-iter", type=int, default=10000)
    ap.add_argument("--calibration-cv", type=int, default=3)
    args = ap.parse_args()
    run_experiment(
        input_dir=args.input,
        models_dir=args.models,
        output_dir=args.output,
        reports_dir=args.reports,
        c_value=args.c_value,
        max_iter=args.max_iter,
        calibration_cv=args.calibration_cv,
    )
