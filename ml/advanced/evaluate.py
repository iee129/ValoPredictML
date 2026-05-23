"""
Evaluate advanced models on train/val/test splits.

Usage:
    python -m ml.advanced.evaluate [--input data/processed] [--models models/advanced] [--reports reports/advanced]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, confusion_matrix, f1_score, roc_auc_score,
)

from ml.baseline.preprocess import build_xy

BASELINE_TEST_AUC = 0.6678


def _metrics(y_true, probs) -> dict:
    preds = (probs >= 0.5).astype(int)
    return {
        "auc": float(roc_auc_score(y_true, probs)),
        "acc": float(accuracy_score(y_true, preds)),
        "f1": float(f1_score(y_true, preds)),
        "confusion_matrix": confusion_matrix(y_true, preds).tolist(),
    }


def evaluate(
    input_dir: str = "data/processed",
    models_dir: str = "models/advanced",
    reports_dir: str = "reports/advanced",
) -> dict:
    inp, mdl, rpt = Path(input_dir), Path(models_dir), Path(reports_dir)
    rpt.mkdir(parents=True, exist_ok=True)

    train_df = pd.read_csv(inp / "train.csv", low_memory=False)
    val_df = pd.read_csv(inp / "val.csv", low_memory=False)
    test_df = pd.read_csv(inp / "test.csv", low_memory=False)
    X_train, y_train, _ = build_xy(train_df)
    X_val, y_val, _ = build_xy(val_df)
    X_test, y_test, _ = build_xy(test_df)
    print(f"Data: train={X_train.shape} val={X_val.shape} test={X_test.shape}")

    model_names = ["rf", "xgb", "lgbm", "ensemble"]
    models = {name: joblib.load(mdl / f"{name}.joblib") for name in model_names}

    all_metrics: dict = {}

    for name, model in models.items():
        train_probs = model.predict_proba(X_train)[:, 1]
        val_probs = model.predict_proba(X_val)[:, 1]
        test_probs = model.predict_proba(X_test)[:, 1]

        m = {
            "train": _metrics(y_train, train_probs),
            "val": _metrics(y_val, val_probs),
            "test": _metrics(y_test, test_probs),
        }
        all_metrics[name] = m
        print(
            f"{name:10s}  "
            f"train_auc={m['train']['auc']:.4f}  "
            f"val_auc={m['val']['auc']:.4f}  "
            f"test_auc={m['test']['auc']:.4f}"
        )

    ens_test_auc = all_metrics["ensemble"]["test"]["auc"]
    delta = ens_test_auc - BASELINE_TEST_AUC
    print(f"\nEnsemble test AUC={ens_test_auc:.4f}  baseline={BASELINE_TEST_AUC:.4f}  delta={delta:+.4f}")
    all_metrics["baseline_comparison"] = {
        "baseline_test_auc": BASELINE_TEST_AUC,
        "ensemble_test_auc": ens_test_auc,
        "delta": float(delta),
    }

    # Feature importance top-20
    print("\n=== Top-20 feature importance ===")
    feature_names = list(X_train.columns)
    for name in ["rf", "xgb", "lgbm"]:
        importances = models[name].feature_importances_
        top_idx = np.argsort(importances)[::-1][:20]
        print(f"\n{name}:")
        for i in top_idx:
            print(f"  {feature_names[i]}: {importances[i]:.4f}")
        all_metrics[f"{name}_top20"] = [
            {"feature": feature_names[i], "importance": float(importances[i])}
            for i in top_idx
        ]

    metrics_path = rpt / "metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(all_metrics, f, indent=2)
    print(f"\nSaved → {metrics_path}")

    return all_metrics


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/processed")
    ap.add_argument("--models", default="models/advanced")
    ap.add_argument("--reports", default="reports/advanced")
    args = ap.parse_args()
    evaluate(args.input, args.models, args.reports)
