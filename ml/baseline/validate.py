import argparse
import json
import os

import joblib
import numpy as np
from sklearn.metrics import accuracy_score, roc_auc_score

from ml.baseline.preprocess import load_split, build_xy


def validate(input_dir: str = "data/processed", models_dir: str = "models/baseline") -> None:
    pipe = joblib.load(os.path.join(models_dir, "model.joblib"))

    df_train = load_split("train", base=input_dir)
    X_tr, y_tr, _ = build_xy(df_train)
    df_test = load_split("test", base=input_dir)
    X_te, y_te, _ = build_xy(df_test)

    majority = int(y_tr.mode()[0])
    majority_acc = float((y_te == majority).mean())

    train_acc = float(accuracy_score(y_tr, pipe.predict(X_tr)))
    test_acc = float(accuracy_score(y_te, pipe.predict(X_te)))
    test_auc = float(roc_auc_score(y_te, pipe.predict_proba(X_te)[:, 1]))
    gap = train_acc - test_acc

    feature_names = list(X_tr.columns)
    importances = pipe.feature_importances_
    top_idx = np.argsort(importances)[::-1][:20]

    result = {
        "majority_baseline_acc": majority_acc,
        "model_train_acc": train_acc,
        "model_test_acc": test_acc,
        "model_test_auc": test_auc,
        "train_test_gap": gap,
        "overfit_warning": gap > 0.05,
        "model_vs_majority_delta": test_acc - majority_acc,
        "top_features": [{"feature": feature_names[i], "importance": float(importances[i])} for i in top_idx],
    }

    os.makedirs(os.path.join("reports", "baseline"), exist_ok=True)
    out_path = os.path.join("reports", "baseline", "validation.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Majority baseline acc : {majority_acc:.4f}")
    print(f"Model test acc        : {test_acc:.4f}  (+{result['model_vs_majority_delta']:+.4f} vs majority)")
    print(f"Train-test gap        : {gap:.4f}  {'⚠ OVERFIT' if result['overfit_warning'] else '✓ OK'}")
    print(f"Validation → {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/processed")
    parser.add_argument("--models", default="models/baseline")
    args = parser.parse_args()
    validate(args.input, args.models)
