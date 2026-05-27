"""베이스라인 LR + DT 튜닝 학습.

LR: C ∈ {0.01, 0.1, 1.0, 10}, l1_ratio ∈ {0.0, 1.0}
DT: max_depth ∈ {4, 6, 8, 10}, min_samples_leaf ∈ {20, 50, 100}
선택 기준: 5-fold GroupKFold by match_key의 mean ROC-AUC.

사용:
    python -m ml.baseline.train --input data/processed --output models/baseline
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import date

import joblib
import pandas as pd
from sklearn.ensemble import VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from ml.baseline.preprocess import (
    FEATURE_COLS,
    FEATURE_CONTRACT,
    FEATURE_ENGINEERING_CONFIG,
    FORBIDDEN_FEATURE_TERMS,
    INPUT_CONTRACT,
    SOURCE_CONTRACT,
    build_xy,
    find_forbidden_feature_names,
    load_split,
)


MODELING_SPLITS = ["train", "val"]
TEST_SPLIT = "test"


def load_modeling_data(input_dir: str):
    frames = [load_split(split, base=input_dir) for split in MODELING_SPLITS]
    return pd.concat(frames, ignore_index=True)


def _cv_for_groups(groups):
    n_splits = min(5, int(groups.nunique()))
    if n_splits < 2:
        raise ValueError("At least two match_key groups are required for GroupKFold")
    return GroupKFold(n_splits=n_splits)


def _tune_lr(X, y, groups):
    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(
            max_iter=2000, random_state=42, solver="liblinear",
        )),
    ])
    grid = {
        "clf__C": [0.01, 0.1, 1.0, 10.0],
        "clf__l1_ratio": [0.0, 1.0],
    }
    cv = _cv_for_groups(groups)
    gs = GridSearchCV(
        pipe, grid, cv=cv, scoring="roc_auc",
        n_jobs=-1, verbose=0, refit=True,
    )
    gs.fit(X, y, groups=groups)
    return gs


def _tune_dt(X, y, groups):
    dt = DecisionTreeClassifier(random_state=42)
    grid = {
        "max_depth": [4, 6, 8, 10],
        "min_samples_leaf": [20, 50, 100],
    }
    cv = _cv_for_groups(groups)
    gs = GridSearchCV(
        dt, grid, cv=cv, scoring="roc_auc",
        n_jobs=-1, verbose=0, refit=True,
    )
    gs.fit(X, y, groups=groups)
    return gs


def train(input_dir: str = "data/processed", output_dir: str = "models/baseline") -> None:
    df = load_modeling_data(input_dir)
    X, y, groups = build_xy(df)
    print(
        f"Train+val: X={X.shape}, y={y.shape}, "
        f"matches={groups.nunique():,}"
    )

    print("Tuning LR ...")
    lr_gs = _tune_lr(X, y, groups)
    print(f"  best LR : {lr_gs.best_params_}  CV AUC={lr_gs.best_score_:.4f}")

    print("Tuning DT ...")
    dt_gs = _tune_dt(X, y, groups)
    print(f"  best DT : {dt_gs.best_params_}  CV AUC={dt_gs.best_score_:.4f}")

    final = VotingClassifier(
        estimators=[("lr", lr_gs.best_estimator_), ("dt", dt_gs.best_estimator_)],
        voting="soft",
        n_jobs=1,
    )
    final.fit(X, y)

    os.makedirs(output_dir, exist_ok=True)
    joblib.dump(final, os.path.join(output_dir, "model.joblib"))

    meta = {
        "algorithm": "LR+DT_soft_voting (tuned)",
        "n_features": int(X.shape[1]),
        "n_rows": int(X.shape[0]),
        "date": str(date.today()),
        "modeling_splits": MODELING_SPLITS,
        "test_split": TEST_SPLIT,
        "split_protocol": "tune with GroupKFold on train+val, final fit on train+val, final evaluation on test",
        "source_contract": SOURCE_CONTRACT,
        "input_contract": INPUT_CONTRACT,
        "feature_contract": FEATURE_CONTRACT,
        "feature_engineering_config": FEATURE_ENGINEERING_CONFIG,
        "forbidden_feature_terms": FORBIDDEN_FEATURE_TERMS,
        "forbidden_feature_count": len(find_forbidden_feature_names(FEATURE_COLS)),
        "feature_names": list(X.columns),
        "leakage_gate_status": "PENDING_VALIDATE_STEP",
        "final_verdict": "PENDING_VALIDATE_STEP",
        "best_lr": {
            **{k.replace("clf__", ""): v for k, v in lr_gs.best_params_.items()},
            "cv_auc": float(lr_gs.best_score_),
        },
        "best_dt": {
            **dt_gs.best_params_,
            "cv_auc": float(dt_gs.best_score_),
        },
    }
    with open(os.path.join(output_dir, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
    print(f"Saved → {output_dir}/model.joblib")
    print(f"Meta  → {output_dir}/meta.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/processed")
    parser.add_argument("--output", default="models/baseline")
    args = parser.parse_args()
    train(args.input, args.output)
