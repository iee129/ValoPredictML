"""
Train RF + XGBoost + LightGBM soft-voting ensemble.

Usage:
    python -m ml.advanced.ensemble [--input data/processed] [--output models/advanced]
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from xgboost import XGBClassifier

from ml.baseline.preprocess import build_xy


def make_rf() -> RandomForestClassifier:
    return RandomForestClassifier(
        n_estimators=500, max_depth=12, min_samples_leaf=20,
        n_jobs=-1, random_state=42,
    )


def make_xgb() -> XGBClassifier:
    return XGBClassifier(
        n_estimators=500, max_depth=4, learning_rate=0.03,
        subsample=0.8, colsample_bytree=0.7, min_child_weight=10,
        reg_alpha=0.1, reg_lambda=1.0,
        random_state=42, n_jobs=-1, verbosity=0, eval_metric="logloss",
    )


def make_lgbm() -> LGBMClassifier:
    return LGBMClassifier(
        n_estimators=1000, num_leaves=63, learning_rate=0.02,
        min_child_samples=40, subsample=0.8, colsample_bytree=0.7,
        reg_alpha=0.1, reg_lambda=1.0,
        random_state=42, n_jobs=-1, verbosity=-1,
    )


def train_ensemble(
    input_dir: str = "data/processed",
    output_dir: str = "models/advanced",
    include_val: bool = True,
) -> None:
    inp, out = Path(input_dir), Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    print("Loading train.csv...")
    train_df = pd.read_csv(inp / "train.csv", low_memory=False)
    if include_val:
        print("Loading val.csv (adding to training)...")
        val_df = pd.read_csv(inp / "val.csv", low_memory=False)
        train_df = pd.concat([train_df, val_df], ignore_index=True)
        print(f"  Combined train+val: {len(train_df)} rows")
    X, y, _ = build_xy(train_df)
    print(f"  X={X.shape}, label distribution: {dict(y.value_counts())}")

    # Train individual models (RF kept for analysis only)
    print("Training RF (individual, not in ensemble)...")
    rf = make_rf()
    rf.fit(X, y)
    joblib.dump(rf, out / "rf.joblib")
    print(f"  Saved rf → {out}/rf.joblib")

    print("Training XGB + LGBM soft-voting ensemble...")
    ensemble = VotingClassifier(
        estimators=[("xgb", make_xgb()), ("lgbm", make_lgbm())],
        voting="soft",
        weights=[1, 1],
        n_jobs=1,
    )
    ensemble.fit(X, y)

    for name, model in zip(["xgb", "lgbm"], ensemble.estimators_):
        path = out / f"{name}.joblib"
        joblib.dump(model, path)
        print(f"  Saved {name} → {path}")

    ens_path = out / "ensemble.joblib"
    joblib.dump(ensemble, ens_path)
    print(f"  Saved ensemble → {ens_path}")

    meta = {
        "algorithm": "XGB+LGBM_soft_voting",
        "date": str(date.today()),
        "n_rows": int(len(train_df)),
        "n_features": int(X.shape[1]),
        "models": {
            "rf": {"n_estimators": 500, "max_depth": 12, "min_samples_leaf": 20,
                   "note": "individual only, not in ensemble"},
            "xgb": {"n_estimators": 500, "max_depth": 4, "learning_rate": 0.03,
                    "subsample": 0.8, "colsample_bytree": 0.7},
            "lgbm": {"n_estimators": 1000, "num_leaves": 63, "learning_rate": 0.02,
                     "min_child_samples": 40, "reg_alpha": 0.1, "reg_lambda": 1.0},
        },
        "ensemble": {"voting": "soft", "weights": [1, 1], "members": ["xgb", "lgbm"]},
        "trained_on_val": include_val,
    }
    meta_path = out / "meta.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"  Saved meta → {meta_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/processed")
    ap.add_argument("--output", default="models/advanced")
    ap.add_argument("--no-val", action="store_true", help="exclude val set from training")
    args = ap.parse_args()
    train_ensemble(args.input, args.output, include_val=not args.no_val)
