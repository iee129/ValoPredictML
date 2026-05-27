"""v10 모델 학습: VCT+VCL 통합 데이터 + LightGBM+XGBoost+RF.

  python -m src.train_v10

산출:
  artifacts/models/lgbm_v10_model.joblib
  artifacts/models/xgb_v10_model.joblib
  artifacts/models/rf_v10_model.joblib
  artifacts/models/feature_names_v10.json
  artifacts/models/train_summary_v10.json
"""
from __future__ import annotations

import json
import sys

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from config import LGBM_PARAMS, MODELS_DIR, PROCESSED_DIR, RF_PARAMS, XGB_PARAMS
from src.features import META_COLS

TRAIN_CSV_V10 = PROCESSED_DIR / "train_v10.csv"


def _load_xy(csv_path):
    df = pd.read_csv(csv_path)
    y  = df["winner"].astype(int).values
    X  = df.drop(columns=[c for c in META_COLS if c in df.columns])
    return X, y


def main():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    print("[train_v10] loading train_v10.csv", file=sys.stderr)
    X_train, y_train = _load_xy(TRAIN_CSV_V10)
    print(f"[train_v10] X_train {X_train.shape}", file=sys.stderr)
    print(f"[train_v10] train winner balance: {np.mean(y_train):.3f}", file=sys.stderr)

    feature_names = list(X_train.columns)
    summary = {
        "n_train": int(len(X_train)),
        "n_features": len(feature_names),
        "train_a_win_rate": float(np.mean(y_train)),
        "models": {},
    }

    print("[train_v10] fitting LightGBM ...", file=sys.stderr)
    lgbm = LGBMClassifier(**LGBM_PARAMS)
    lgbm.fit(X_train, y_train)
    joblib.dump(lgbm, MODELS_DIR / "lgbm_v10_model.joblib")
    print("[train_v10] LightGBM 저장 완료", file=sys.stderr)

    print("[train_v10] fitting XGBoost ...", file=sys.stderr)
    xgb = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("xgb",     XGBClassifier(**XGB_PARAMS)),
    ])
    xgb.fit(X_train, y_train)
    joblib.dump(xgb, MODELS_DIR / "xgb_v10_model.joblib")
    print("[train_v10] XGBoost 저장 완료", file=sys.stderr)

    print("[train_v10] fitting RandomForest ...", file=sys.stderr)
    rf = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("rf",      RandomForestClassifier(**RF_PARAMS)),
    ])
    rf.fit(X_train, y_train)
    joblib.dump(rf, MODELS_DIR / "rf_v10_model.joblib")
    print("[train_v10] RF 저장 완료", file=sys.stderr)

    with open(MODELS_DIR / "feature_names_v10.json", "w") as f:
        json.dump(feature_names, f, ensure_ascii=False, indent=2)
    with open(MODELS_DIR / "train_summary_v10.json", "w") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"[train_v10] 모든 모델 저장 완료 → {MODELS_DIR}", file=sys.stderr)


if __name__ == "__main__":
    main()
