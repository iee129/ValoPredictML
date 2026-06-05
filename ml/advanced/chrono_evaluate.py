"""Train and evaluate advanced ensemble on the active chronological split.

Trains RF+XGB+LGB on data/processed/advanced/train.csv,
evaluates on data/processed/advanced/test.csv,
saves results to reports/advanced/metrics.json.

Usage:
    python -m ml.advanced.chrono_evaluate
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from xgboost import XGBClassifier

from ml.baseline.preprocess import (
    EXPECTED_FEATURE_COUNT_ADVANCED,
    FEATURE_COLS_ADVANCED,
    build_xy,
    compute_adv_impute_means,
)
from ml.advanced.ensemble import _read_best_params, make_rf, make_xgb, make_lgbm

DEFAULT_INPUT_DIR = "data/processed/advanced"
DEFAULT_REPORTS_DIR = "reports/advanced"


def _metrics(y_true: pd.Series, probs: np.ndarray) -> dict[str, Any]:
    preds = (probs >= 0.5).astype(int)
    return {
        "auc": float(roc_auc_score(y_true, probs)),
        "acc": float(accuracy_score(y_true, preds)),
        "f1": float(f1_score(y_true, preds)),
    }


def chrono_evaluate(
    input_dir: str = DEFAULT_INPUT_DIR,
    reports_dir: str = DEFAULT_REPORTS_DIR,
    params_dir: str = DEFAULT_REPORTS_DIR,
) -> dict[str, Any]:
    inp = Path(input_dir)
    rpt = Path(reports_dir)
    rpt.mkdir(parents=True, exist_ok=True)

    processed_dir = str(inp.parent)  # data/processed

    train_df = pd.read_csv(inp / "train.csv", low_memory=False)
    test_df = pd.read_csv(inp / "test.csv", low_memory=False)

    impute_means = compute_adv_impute_means(train_df)
    X_tr, y_tr, _ = build_xy(
        train_df, feature_contract="advanced",
        processed_dir=processed_dir, impute_means=impute_means,
    )
    X_te, y_te, _ = build_xy(
        test_df, feature_contract="advanced",
        processed_dir=processed_dir, impute_means=impute_means,
    )

    print(f"Chrono train: {X_tr.shape}, test: {X_te.shape}")

    params = {
        "rf": _read_best_params(Path(params_dir), "rf"),
        "xgb": _read_best_params(Path(params_dir), "xgb"),
        "lgbm": _read_best_params(Path(params_dir), "lgbm"),
    }

    ensemble = VotingClassifier(
        estimators=[
            ("rf", make_rf(params["rf"])),
            ("xgb", make_xgb(params["xgb"])),
            ("lgbm", make_lgbm(params["lgbm"])),
        ],
        voting="soft",
        weights=[1, 1, 1],
        n_jobs=1,
    )
    ensemble.fit(X_tr, y_tr)

    probs = ensemble.predict_proba(X_te)[:, 1]
    test_metrics = _metrics(y_te, probs)
    print(f"Chrono test AUC={test_metrics['auc']:.4f}")

    result = {
        "feature_contract": "advanced",
        "feature_count": len(FEATURE_COLS_ADVANCED),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "split": {"train_rows": int(len(X_tr)), "test_rows": int(len(X_te))},
        "train_years": sorted(int(y) for y in train_df["year"].dropna().unique()),
        "test_years": sorted(int(y) for y in test_df["year"].dropna().unique()),
        "test_auc": test_metrics["auc"],
        "test_acc": test_metrics["acc"],
        "test_f1": test_metrics["f1"],
    }

    out = rpt / "metrics.json"
    with open(out, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Saved → {out}")

    auc_gate = result["test_auc"] >= 0.6182
    val = {
        "feature_contract": "advanced",
        "feature_count": len(FEATURE_COLS_ADVANCED),
        "created_at": result["created_at"],
        "checks": {
            "feature_count_matches_contract": (
                len(FEATURE_COLS_ADVANCED) == EXPECTED_FEATURE_COUNT_ADVANCED
            ),
            "chrono_auc_gte_0618": auc_gate,
        },
        "final_verdict": (
            "PASS" if auc_gate and len(FEATURE_COLS_ADVANCED) == EXPECTED_FEATURE_COUNT_ADVANCED else "FAIL"
        ),
        "test_auc": result["test_auc"],
    }
    val_out = rpt / "validation.json"
    with open(val_out, "w") as f:
        json.dump(val, f, indent=2)
    print(f"Saved → {val_out}  verdict={val['final_verdict']}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=DEFAULT_INPUT_DIR)
    parser.add_argument("--reports", default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--params", default=DEFAULT_REPORTS_DIR)
    args = parser.parse_args()
    chrono_evaluate(args.input, args.reports, args.params)


if __name__ == "__main__":
    main()
