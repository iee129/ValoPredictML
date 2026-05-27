"""Train the Kaggle-only advanced RF/XGB/LGBM soft-voting ensemble.

Usage:
    python -m ml.advanced.ensemble \
        --input data/processed/adv_kaggle_only \
        --output models/advanced \
        --reports reports/adv_kaggle_only
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from xgboost import XGBClassifier

from ml.baseline.preprocess import (
    FEATURE_COLS_ADVANCED,
    SOURCE_CONTRACT,
    build_xy,
)

DEFAULT_INPUT_DIR = "data/processed/adv_kaggle_only"
DEFAULT_OUTPUT_DIR = "models/advanced"
DEFAULT_REPORTS_DIR = "reports/adv_kaggle_only"


def _read_best_params(reports_dir: Path, model_name: str) -> dict[str, Any]:
    path = reports_dir / f"{model_name}_best_params.json"
    if not path.exists():
        return {}
    with open(path) as f:
        payload = json.load(f)
    return dict(payload.get("best_params", {}))


def make_rf(params: dict[str, Any] | None = None) -> RandomForestClassifier:
    cfg: dict[str, Any] = {
        "n_estimators": 500,
        "max_depth": 12,
        "min_samples_leaf": 20,
        "n_jobs": -1,
        "random_state": 42,
    }
    cfg.update(params or {})
    cfg["n_estimators"] = int(cfg["n_estimators"])
    if cfg.get("max_depth") is not None:
        cfg["max_depth"] = int(cfg["max_depth"])
    cfg["min_samples_leaf"] = int(cfg["min_samples_leaf"])
    return RandomForestClassifier(**cfg)


def make_xgb(params: dict[str, Any] | None = None) -> XGBClassifier:
    cfg: dict[str, Any] = {
        "n_estimators": 500,
        "max_depth": 4,
        "learning_rate": 0.03,
        "subsample": 0.8,
        "colsample_bytree": 0.7,
        "min_child_weight": 10,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
        "random_state": 42,
        "n_jobs": -1,
        "verbosity": 0,
        "eval_metric": "logloss",
    }
    cfg.update(params or {})
    cfg["n_estimators"] = int(cfg["n_estimators"])
    cfg["max_depth"] = int(cfg["max_depth"])
    return XGBClassifier(**cfg)


def make_lgbm(params: dict[str, Any] | None = None) -> LGBMClassifier:
    cfg: dict[str, Any] = {
        "n_estimators": 1000,
        "num_leaves": 63,
        "learning_rate": 0.02,
        "min_child_samples": 40,
        "subsample": 0.8,
        "colsample_bytree": 0.7,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
        "random_state": 42,
        "n_jobs": -1,
        "verbosity": -1,
    }
    cfg.update(params or {})
    cfg["n_estimators"] = int(cfg["n_estimators"])
    cfg["num_leaves"] = int(cfg["num_leaves"])
    cfg["min_child_samples"] = int(cfg["min_child_samples"])
    return LGBMClassifier(**cfg)


def _assert_kaggle_only(df: pd.DataFrame, split_name: str) -> None:
    if "source" not in df.columns:
        raise ValueError(f"{split_name}.csv has no source column")
    bad = df.loc[~df["source"].astype(str).str.startswith("kaggle_"), "source"].unique()
    if len(bad):
        preview = ", ".join(map(str, bad[:5]))
        raise ValueError(f"{split_name}.csv contains non-Kaggle sources: {preview}")


def _load_training_frame(input_dir: Path, include_val: bool) -> tuple[pd.DataFrame, dict[str, int]]:
    train_df = pd.read_csv(input_dir / "train.csv", low_memory=False)
    _assert_kaggle_only(train_df, "train")
    row_counts = {"train": int(len(train_df))}
    if include_val:
        val_df = pd.read_csv(input_dir / "val.csv", low_memory=False)
        _assert_kaggle_only(val_df, "val")
        row_counts["val"] = int(len(val_df))
        train_df = pd.concat([train_df, val_df], ignore_index=True)
    return train_df, row_counts


def train_ensemble(
    input_dir: str = DEFAULT_INPUT_DIR,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    reports_dir: str = DEFAULT_REPORTS_DIR,
    include_val: bool = True,
) -> dict[str, Any]:
    inp = Path(input_dir)
    out = Path(output_dir)
    rpt = Path(reports_dir)
    out.mkdir(parents=True, exist_ok=True)

    train_df, row_counts = _load_training_frame(inp, include_val=include_val)
    X, y, _ = build_xy(train_df, feature_contract="advanced")
    feature_names = list(X.columns)
    if feature_names != FEATURE_COLS_ADVANCED:
        raise RuntimeError("Advanced feature order does not match FEATURE_COLS_ADVANCED")
    if X.shape[1] != 125:
        raise RuntimeError(f"Advanced model expects 125 features, got {X.shape[1]}")

    params = {
        "rf": _read_best_params(rpt, "rf"),
        "xgb": _read_best_params(rpt, "xgb"),
        "lgbm": _read_best_params(rpt, "lgbm"),
    }

    print(f"Training advanced ensemble on {X.shape[0]:,} rows x {X.shape[1]} features")
    print(f"  input={inp}")
    print(f"  params source={rpt}")

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
    ensemble.fit(X, y)

    for name, estimator in ensemble.named_estimators_.items():
        path = out / f"{name}.joblib"
        joblib.dump(estimator, path)
        print(f"  saved {name}: {path}")

    ensemble_path = out / "ensemble.joblib"
    joblib.dump(ensemble, ensemble_path)
    print(f"  saved ensemble: {ensemble_path}")

    meta: dict[str, Any] = {
        "algorithm": "RF+XGB+LGBM_soft_voting",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "feature_contract": "advanced",
        "n_features": int(X.shape[1]),
        "feature_names": feature_names,
        "source_contract": {
            "allowed_source_prefixes": SOURCE_CONTRACT["allowed_source_prefixes"],
            "excluded_source_prefixes": SOURCE_CONTRACT["excluded_source_prefixes"],
            "active_rule": "all training/evaluation rows must have source starting with kaggle_",
        },
        "data": {
            "input_dir": str(inp),
            "modeling_splits": ["train", "val"] if include_val else ["train"],
            "row_counts": row_counts,
            "trained_rows": int(len(train_df)),
        },
        "models": {
            "rf": params["rf"],
            "xgb": params["xgb"],
            "lgbm": params["lgbm"],
        },
        "ensemble": {
            "voting": "soft",
            "weights": [1, 1, 1],
            "members": ["rf", "xgb", "lgbm"],
        },
        "trained_on_val": include_val,
        "artifacts": {
            "rf": str(out / "rf.joblib"),
            "xgb": str(out / "xgb.joblib"),
            "lgbm": str(out / "lgbm.joblib"),
            "ensemble": str(ensemble_path),
            "meta": str(out / "meta.json"),
        },
    }
    meta_path = out / "meta.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"  saved meta: {meta_path}")
    return meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=DEFAULT_INPUT_DIR)
    ap.add_argument("--output", default=DEFAULT_OUTPUT_DIR)
    ap.add_argument("--reports", default=DEFAULT_REPORTS_DIR)
    ap.add_argument("--no-val", action="store_true", help="exclude val split from final fit")
    args = ap.parse_args()
    train_ensemble(
        input_dir=args.input,
        output_dir=args.output,
        reports_dir=args.reports,
        include_val=not args.no_val,
    )
