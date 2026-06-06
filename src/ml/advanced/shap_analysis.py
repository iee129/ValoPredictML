# DEPRECATED: 2026-06-02 — SHAP을 피처 중요도로 전환함.
# 이 파일 대신 src/ml/advanced/feature_importance.py를 사용할 것.
# 하단 코드는 참조용으로만 보존됨.

"""SHAP TreeExplainer analysis for the advanced RF/XGB/LGBM models.

Trains each model with its Optuna-tuned best params, computes SHAP values on a
test sample, and writes model-level explanations:

    reports/advanced/figures/shap_summary_{rf,xgb,lgbm}.png
    reports/advanced/shap_importance.json   (mean|SHAP| top features)

This is read-only with respect to the promoted ensemble: it re-fits sidecar
copies from the same best params and never overwrites models/advanced/*.joblib.

Usage:
    python -m ml.advanced.shap_analysis --sample-size 5000
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
# SHAP 라이브러리 제거됨. feature_importance.py 참조.
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier

from features.preprocess import FEATURE_COLS_ADVANCED, build_xy, load_split

DEFAULT_INPUT_DIR = "data/processed/advanced"
DEFAULT_REPORTS_DIR = "reports/advanced"
MODELING_SPLITS = ["train"]
TEST_SPLIT = "test"
RANDOM_STATE = 42
DEFAULT_SAMPLE_SIZE = 5000
TOP_FEATURES = 20


def _read_best_params(reports_dir: Path, name: str) -> dict[str, Any]:
    path = reports_dir / f"{name}_best_params.json"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found; run `python -m ml.advanced.optimize` first"
        )
    with open(path) as f:
        return dict(json.load(f).get("best_params", {}))


def _build_model(name: str, params: dict[str, Any]) -> Any:
    if name == "rf":
        return RandomForestClassifier(**params, random_state=RANDOM_STATE, n_jobs=-1)
    if name == "xgb":
        return XGBClassifier(
            **params, eval_metric="logloss", random_state=RANDOM_STATE, n_jobs=-1
        )
    if name == "lgbm":
        return LGBMClassifier(**params, random_state=RANDOM_STATE, n_jobs=-1, verbose=-1)
    raise ValueError(f"Unknown model {name!r}")


def _positive_class_shap(shap_values: Any) -> np.ndarray:
    """Normalize SHAP output to a 2D (n_samples, n_features) positive-class array."""
    if isinstance(shap_values, list) and len(shap_values) == 2:
        return np.asarray(shap_values[1])
    if hasattr(shap_values, "values"):
        values = np.asarray(shap_values.values)
        return values[:, :, 1] if values.ndim == 3 else values
    values = np.asarray(shap_values)
    return values[:, :, 1] if values.ndim == 3 else values


def _load_xy(input_dir: str, splits: list[str]) -> tuple[pd.DataFrame, pd.Series]:
    frames = [load_split(split, base=input_dir) for split in splits]
    df = pd.concat(frames, ignore_index=True)
    X, y, _ = build_xy(df, feature_contract="advanced")
    if list(X.columns) != FEATURE_COLS_ADVANCED:
        raise RuntimeError("Advanced feature order does not match FEATURE_COLS_ADVANCED")
    return X, y


def run_shap(
    input_dir: str = DEFAULT_INPUT_DIR,
    reports_dir: str = DEFAULT_REPORTS_DIR,
    sample_size: int = DEFAULT_SAMPLE_SIZE,
) -> dict[str, Any]:
    rpt = Path(reports_dir)
    figures_dir = rpt / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    X_train, y_train = _load_xy(input_dir, MODELING_SPLITS)
    X_test, _ = _load_xy(input_dir, [TEST_SPLIT])
    sample = X_test.sample(min(sample_size, len(X_test)), random_state=RANDOM_STATE)
    print(f"Train rows={len(X_train):,}, SHAP sample={len(sample):,}")

    importance: dict[str, Any] = {
        "feature_contract": "advanced",
        "feature_count": len(FEATURE_COLS_ADVANCED),
        "sample_size": int(len(sample)),
        "models": {},
    }

    for name in ("rf", "xgb", "lgbm"):
        params = _read_best_params(rpt, name)
        print(f"Fitting {name} with tuned params ...")
        model = _build_model(name, params)
        model.fit(X_train, y_train)

        print(f"Computing SHAP for {name} ...")
        explainer = shap.TreeExplainer(model)
        sv = _positive_class_shap(explainer.shap_values(sample))

        shap.summary_plot(sv, sample, show=False, max_display=TOP_FEATURES)
        out_path = figures_dir / f"shap_summary_{name}.png"
        plt.savefig(out_path, dpi=120, bbox_inches="tight")
        plt.close("all")
        print(f"  saved -> {out_path}")

        mean_abs = np.abs(sv).mean(axis=0)
        order = np.argsort(mean_abs)[::-1][:TOP_FEATURES]
        importance["models"][name] = [
            {"feature": FEATURE_COLS_ADVANCED[i], "mean_abs_shap": float(mean_abs[i])}
            for i in order
        ]

    importance_path = rpt / "shap_importance.json"
    with open(importance_path, "w") as f:
        json.dump(importance, f, indent=2)
    print(f"Saved SHAP importance -> {importance_path}")
    return importance


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=DEFAULT_INPUT_DIR)
    ap.add_argument("--reports", default=DEFAULT_REPORTS_DIR)
    ap.add_argument("--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE)
    args = ap.parse_args()
    run_shap(
        input_dir=args.input,
        reports_dir=args.reports,
        sample_size=args.sample_size,
    )
