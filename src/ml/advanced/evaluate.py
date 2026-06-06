"""Evaluate the active advanced models on train/test splits.

Usage:
    python -m ml.advanced.evaluate \
        --input data/processed/advanced \
        --models models/advanced \
        --reports reports/advanced
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, roc_auc_score

from features.preprocess import FEATURE_COLS_ADVANCED, build_xy, compute_adv_impute_means

DEFAULT_INPUT_DIR = "data/processed/advanced"
DEFAULT_MODELS_DIR = "models/advanced"
DEFAULT_REPORTS_DIR = "reports/advanced"


def _metrics(y_true: pd.Series, probs: np.ndarray) -> dict[str, Any]:
    preds = (probs >= 0.5).astype(int)
    return {
        "auc": float(roc_auc_score(y_true, probs)),
        "acc": float(accuracy_score(y_true, preds)),
        "f1": float(f1_score(y_true, preds)),
        "confusion_matrix": confusion_matrix(y_true, preds).tolist(),
    }


def _load_baseline_metrics() -> dict[str, Any] | None:
    candidates = [
        ("baseline", Path("reports/baseline/metrics.json")),
    ]
    for source, path in candidates:
        if not path.exists():
            continue
        with open(path) as f:
            payload = json.load(f)
        return {
            "baseline_source": source,
            "baseline_metrics_path": str(path),
            "baseline_test_auc": float(payload.get("test_auc", 0.0)),
            "baseline_test_acc": float(payload.get("test_acc", 0.0)),
            "baseline_test_f1": float(payload.get("test_f1", 0.0)),
        }
    return None


def _feature_importances(model: Any, n_features: int) -> np.ndarray:
    if hasattr(model, "feature_importances_"):
        values = np.asarray(model.feature_importances_, dtype=float)
        if len(values) != n_features:
            return np.zeros(n_features, dtype=float)
        total = float(np.nansum(np.abs(values)))
        return values / total if total > 0 else np.zeros(n_features, dtype=float)

    if hasattr(model, "estimators_"):
        weights = getattr(model, "weights", None) or [1.0] * len(model.estimators_)
        combined = np.zeros(n_features, dtype=float)
        total_weight = 0.0
        for estimator, weight in zip(model.estimators_, weights):
            values = _feature_importances(estimator, n_features)
            if values.any():
                combined += float(weight) * values
                total_weight += float(weight)
        return combined / total_weight if total_weight else combined

    return np.zeros(n_features, dtype=float)


def _top_features(model: Any, feature_names: list[str], limit: int = 20) -> list[dict[str, Any]]:
    importances = _feature_importances(model, len(feature_names))
    order = np.argsort(importances)[::-1][:limit]
    return [
        {"feature": feature_names[i], "importance": float(importances[i])}
        for i in order
        if importances[i] > 0
    ]


def _update_meta(models_dir: Path, patch: dict[str, Any]) -> None:
    meta_path = models_dir / "meta.json"
    if not meta_path.exists():
        return
    with open(meta_path) as f:
        meta = json.load(f)
    meta.update(patch)
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)


def evaluate(
    input_dir: str = DEFAULT_INPUT_DIR,
    models_dir: str = DEFAULT_MODELS_DIR,
    reports_dir: str = DEFAULT_REPORTS_DIR,
) -> dict[str, Any]:
    inp = Path(input_dir)
    mdl = Path(models_dir)
    rpt = Path(reports_dir)
    rpt.mkdir(parents=True, exist_ok=True)

    frames = {
        split: pd.read_csv(inp / f"{split}.csv", low_memory=False)
        for split in ("train", "test")
    }
    processed_dir = str(inp.parent)
    impute_means = compute_adv_impute_means(frames["train"])
    xy = {
        split: build_xy(
            frame,
            feature_contract="advanced",
            processed_dir=processed_dir,
            impute_means=impute_means,
        )
        for split, frame in frames.items()
    }
    feature_names = list(xy["train"][0].columns)
    if feature_names != FEATURE_COLS_ADVANCED:
        raise RuntimeError("Advanced feature order does not match FEATURE_COLS_ADVANCED")

    model_names = ["rf", "xgb", "lgbm", "ensemble"]
    models = {name: joblib.load(mdl / f"{name}.joblib") for name in model_names}
    for name, model in models.items():
        n_features = getattr(model, "n_features_in_", None)
        if n_features != len(feature_names):
            raise RuntimeError(
                f"{name}.joblib expects {n_features} features; "
                f"advanced contract has {len(feature_names)}"
            )

    all_metrics: dict[str, Any] = {}
    print(f"Data: train={xy['train'][0].shape} test={xy['test'][0].shape}")

    for name, model in models.items():
        model_metrics: dict[str, Any] = {}
        for split in ("train", "test"):
            X, y, _ = xy[split]
            probs = model.predict_proba(X)[:, 1]
            model_metrics[split] = _metrics(y, probs)
        all_metrics[name] = model_metrics
        print(
            f"{name:10s} "
            f"train_auc={model_metrics['train']['auc']:.4f} "
            f"test_auc={model_metrics['test']['auc']:.4f}"
        )

    ensemble_test = all_metrics["ensemble"]["test"]
    ensemble_train = all_metrics["ensemble"]["train"]
    baseline = _load_baseline_metrics()
    baseline_comparison = None
    if baseline:
        baseline_comparison = {
            **baseline,
            "advanced_test_auc": ensemble_test["auc"],
            "advanced_test_acc": ensemble_test["acc"],
            "advanced_test_f1": ensemble_test["f1"],
            "delta_test_auc": float(ensemble_test["auc"] - baseline["baseline_test_auc"]),
        }
        print(
            "\nEnsemble test AUC="
            f"{ensemble_test['auc']:.4f} {baseline['baseline_source']}={baseline['baseline_test_auc']:.4f} "
            f"delta={baseline_comparison['delta_test_auc']:+.4f}"
        )

    train_test_gaps = {
        name: float(metrics["train"]["auc"] - metrics["test"]["auc"])
        for name, metrics in all_metrics.items()
    }
    single_model_test_auc = {
        name: float(all_metrics[name]["test"]["auc"])
        for name in ("rf", "xgb", "lgbm")
    }
    best_single_model = max(single_model_test_auc, key=single_model_test_auc.get)
    ensemble_diagnostics = {
        "train_test_auc_gap": train_test_gaps["ensemble"],
        "single_model_test_auc": single_model_test_auc,
        "best_single_model": best_single_model,
        "best_single_test_auc": single_model_test_auc[best_single_model],
        "delta_vs_rf_test_auc": float(ensemble_test["auc"] - all_metrics["rf"]["test"]["auc"]),
        "delta_vs_best_single_test_auc": float(
            ensemble_test["auc"] - single_model_test_auc[best_single_model]
        ),
    }

    metrics: dict[str, Any] = {
        "feature_contract": "advanced",
        "feature_count": len(feature_names),
        "feature_names": feature_names,
        "train_rows": int(len(frames["train"])),
        "modeling_rows": int(len(frames["train"])),
        "test_rows": int(len(frames["test"])),
        "models": all_metrics,
        "train_test_auc_gap": train_test_gaps,
        "ensemble_diagnostics": ensemble_diagnostics,
        "rf": all_metrics["rf"],
        "xgb": all_metrics["xgb"],
        "lgbm": all_metrics["lgbm"],
        "ensemble": all_metrics["ensemble"],
        "train_auc": ensemble_train["auc"],
        "test_auc": ensemble_test["auc"],
        "test_acc": ensemble_test["acc"],
        "test_f1": ensemble_test["f1"],
        "confusion_matrix": ensemble_test["confusion_matrix"],
        "baseline_comparison": baseline_comparison,
        "top_features": {
            name: _top_features(model, feature_names)
            for name, model in models.items()
        },
    }

    metrics_path = rpt / "metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"\nSaved metrics: {metrics_path}")

    _update_meta(
        mdl,
        {
            "metrics": {
                "reports_dir": str(rpt),
                "test_auc": ensemble_test["auc"],
                "test_acc": ensemble_test["acc"],
                "test_f1": ensemble_test["f1"],
                "baseline_comparison": baseline_comparison,
            }
        },
    )
    return metrics


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=DEFAULT_INPUT_DIR)
    ap.add_argument("--models", default=DEFAULT_MODELS_DIR)
    ap.add_argument("--reports", default=DEFAULT_REPORTS_DIR)
    args = ap.parse_args()
    evaluate(args.input, args.models, args.reports)
