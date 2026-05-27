"""v9 모델 학습: v7 분할 데이터 + LightGBM+XGBoost+SVM+RF (4-모델 앙상블).

  python -m src.train_v9

산출:
  artifacts/models/lgbm_v9_model.joblib
  artifacts/models/xgb_v9_model.joblib
  artifacts/models/svm_v9_model.joblib
  artifacts/models/rf_v9_model.joblib
  artifacts/models/feature_names_v9.json
  artifacts/models/train_summary_v9.json
"""
from __future__ import annotations

import json
import sys

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC
from xgboost import XGBClassifier

from config import (
    LGBM_PARAMS,
    MODELS_DIR,
    PROCESSED_DIR,
    RF_PARAMS,
    SVM_CALIBRATION_CV,
    SVM_PARAMS,
    XGB_PARAMS,
)
from src.features import META_COLS

TRAIN_CSV_V9 = PROCESSED_DIR / "train_v9.csv"


def _load_xy(csv_path):
    df = pd.read_csv(csv_path)
    y = df["winner"].astype(int).values
    X = df.drop(columns=[c for c in META_COLS if c in df.columns])
    return X, y


def main():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    print("[train_v9] loading train_v9.csv", file=sys.stderr)
    X_train, y_train = _load_xy(TRAIN_CSV_V9)
    print(f"[train_v9] X_train {X_train.shape}", file=sys.stderr)
    print(f"[train_v9] train winner balance: {np.mean(y_train):.3f}", file=sys.stderr)

    feature_names = list(X_train.columns)
    summary = {
        "n_train": int(len(X_train)),
        "n_features": len(feature_names),
        "train_a_win_rate": float(np.mean(y_train)),
        "models": {},
    }

    print("[train_v9] fitting LightGBM ...", file=sys.stderr)
    lgbm = LGBMClassifier(**LGBM_PARAMS)
    lgbm.fit(X_train, y_train)
    joblib.dump(lgbm, MODELS_DIR / "lgbm_v9_model.joblib")

    print("[train_v9] fitting XGBoost ...", file=sys.stderr)
    xgb = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("xgb",     XGBClassifier(**XGB_PARAMS)),
    ])
    xgb.fit(X_train, y_train)
    joblib.dump(xgb, MODELS_DIR / "xgb_v9_model.joblib")

    print(f"[train_v9] fitting SVM (LinearSVC + CalibratedCV cv={SVM_CALIBRATION_CV}) ...",
          file=sys.stderr)
    svm = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler",  StandardScaler()),
        ("svm",     CalibratedClassifierCV(
            estimator=LinearSVC(**SVM_PARAMS),
            cv=SVM_CALIBRATION_CV,
        )),
    ])
    svm.fit(X_train, y_train)
    joblib.dump(svm, MODELS_DIR / "svm_v9_model.joblib")

    print("[train_v9] fitting RandomForest ...", file=sys.stderr)
    rf = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("rf",      RandomForestClassifier(**RF_PARAMS)),
    ])
    rf.fit(X_train, y_train)
    joblib.dump(rf, MODELS_DIR / "rf_v9_model.joblib")

    with open(MODELS_DIR / "feature_names_v9.json", "w") as f:
        json.dump(feature_names, f, ensure_ascii=False, indent=2)
    with open(MODELS_DIR / "train_summary_v9.json", "w") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"[train_v9] saved models into {MODELS_DIR}", file=sys.stderr)


if __name__ == "__main__":
    main()
