import argparse
import json
import os

import joblib
import numpy as np
from sklearn.base import clone
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, roc_auc_score
from sklearn.model_selection import GroupKFold

from ml.baseline.preprocess import build_xy, load_split
from ml.baseline.train import MODELING_SPLITS, TEST_SPLIT, load_modeling_data


def _cv_for_groups(groups):
    n_splits = min(5, int(groups.nunique()))
    if n_splits < 2:
        raise ValueError("At least two match_key groups are required for GroupKFold")
    return GroupKFold(n_splits=n_splits)


def evaluate(input_dir: str = "data/processed", models_dir: str = "models/baseline") -> None:
    pipe = joblib.load(os.path.join(models_dir, "model.joblib"))

    df_modeling = load_modeling_data(input_dir)
    X_tr, y_tr, groups_tr = build_xy(df_modeling)

    gkf = _cv_for_groups(groups_tr)
    cv_aucs, cv_accs, cv_f1s = [], [], []
    for tr_idx, va_idx in gkf.split(X_tr, y_tr, groups=groups_tr):
        fold_pipe = clone(pipe)
        fold_pipe.fit(X_tr.iloc[tr_idx], y_tr.iloc[tr_idx])
        y_va = y_tr.iloc[va_idx]
        y_va_pred = fold_pipe.predict(X_tr.iloc[va_idx])
        y_va_prob = fold_pipe.predict_proba(X_tr.iloc[va_idx])[:, 1]
        cv_aucs.append(roc_auc_score(y_va, y_va_prob))
        cv_accs.append(accuracy_score(y_va, y_va_pred))
        cv_f1s.append(f1_score(y_va, y_va_pred))

    df_test = load_split(TEST_SPLIT, base=input_dir)
    X_te, y_te, _ = build_xy(df_test)
    y_pred = pipe.predict(X_te)
    y_prob = pipe.predict_proba(X_te)[:, 1]

    metrics = {
        "cv_auc": float(np.mean(cv_aucs)),
        "cv_acc": float(np.mean(cv_accs)),
        "cv_f1": float(np.mean(cv_f1s)),
        "cv_auc_std": float(np.std(cv_aucs)),
        "n_features": int(X_tr.shape[1]),
        "modeling_splits": MODELING_SPLITS,
        "test_split": TEST_SPLIT,
        "n_modeling_rows": int(X_tr.shape[0]),
        "n_train_rows": int(X_tr.shape[0]),
        "n_test_rows": int(X_te.shape[0]),
        "test_auc": float(roc_auc_score(y_te, y_prob)),
        "test_acc": float(accuracy_score(y_te, y_pred)),
        "test_f1": float(f1_score(y_te, y_pred)),
        "confusion_matrix": confusion_matrix(y_te, y_pred).tolist(),
    }

    os.makedirs(os.path.join("reports", "baseline"), exist_ok=True)
    out_path = os.path.join("reports", "baseline", "metrics.json")
    with open(out_path, "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"CV   AUC={metrics['cv_auc']:.4f} ± {metrics['cv_auc_std']:.4f}  "
          f"Acc={metrics['cv_acc']:.4f}  F1={metrics['cv_f1']:.4f}")
    print(f"Test AUC={metrics['test_auc']:.4f}  "
          f"Acc={metrics['test_acc']:.4f}  F1={metrics['test_f1']:.4f}")
    print(f"Metrics → {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/processed")
    parser.add_argument("--models", default="models/baseline")
    args = parser.parse_args()
    evaluate(args.input, args.models)
