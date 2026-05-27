"""v9 모델 평가: v7 분할 테스트셋 + LightGBM.

  python -m src.evaluate_v9

산출:
  artifacts/reports/eval_summary_v9.json
"""
from __future__ import annotations

import json
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, roc_auc_score

from config import ENSEMBLE_WEIGHTS_V9, MODELS_DIR, PROCESSED_DIR, REPORTS_DIR
from src.features import META_COLS

TEST_CSV_V9 = PROCESSED_DIR / "test_v9.csv"


def _load_xy(csv_path):
    df = pd.read_csv(csv_path)
    y = df["winner"].astype(int).values
    X = df.drop(columns=[c for c in META_COLS if c in df.columns])
    return X, y


def _metrics(name, y_true, proba):
    if proba is None:
        pred = np.ones_like(y_true)
        auc  = float("nan")
    else:
        pred = (proba >= 0.5).astype(int)
        auc  = float(roc_auc_score(y_true, proba))
    acc = float(accuracy_score(y_true, pred))
    f1  = float(f1_score(y_true, pred))
    tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
    return {"name": name, "roc_auc": auc, "accuracy": acc, "f1": f1,
            "tp": int(tp), "tn": int(tn), "fp": int(fp), "fn": int(fn)}


def _print_table(rows):
    header = (f"{'model':<18} | {'ROC-AUC':>7} | {'Acc':>6} | {'F1':>6} | "
              f"{'TP':>4} {'TN':>4} {'FP':>4} {'FN':>4}")
    print("\n" + header, file=sys.stderr)
    print("-" * len(header), file=sys.stderr)
    for r in rows:
        auc_s = "  nan " if np.isnan(r["roc_auc"]) else f"{r['roc_auc']:.4f}"
        print(f"{r['name']:<18} | {auc_s:>7} | {r['accuracy']:.4f} | {r['f1']:.4f} | "
              f"{r['tp']:>4} {r['tn']:>4} {r['fp']:>4} {r['fn']:>4}", file=sys.stderr)


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    print("[eval_v9] loading test_v9.csv", file=sys.stderr)
    X_test, y_test = _load_xy(TEST_CSV_V9)
    print(f"[eval_v9] X_test {X_test.shape}  A승률(test)={np.mean(y_test):.3f}",
          file=sys.stderr)

    print("[eval_v9] loading v9 models ...", file=sys.stderr)
    lgbm = joblib.load(MODELS_DIR / "lgbm_v9_model.joblib")
    xgb  = joblib.load(MODELS_DIR / "xgb_v9_model.joblib")
    svm  = joblib.load(MODELS_DIR / "svm_v9_model.joblib")
    rf   = joblib.load(MODELS_DIR / "rf_v9_model.joblib")

    proba_lgbm = lgbm.predict_proba(X_test)[:, 1]
    proba_xgb  = xgb.predict_proba(X_test)[:, 1]
    proba_svm  = svm.predict_proba(X_test)[:, 1]
    proba_rf   = rf.predict_proba(X_test)[:, 1]
    w = ENSEMBLE_WEIGHTS_V9
    proba_ens = (w["lgbm"] * proba_lgbm + w["xgb"] * proba_xgb
                 + w["svm"] * proba_svm + w["rf"] * proba_rf)

    rows = [
        _metrics("lgbm", y_test, proba_lgbm),
        _metrics("xgb",  y_test, proba_xgb),
        _metrics("svm",  y_test, proba_svm),
        _metrics("rf",   y_test, proba_rf),
        _metrics(
            f"ensemble({w['lgbm']:.2f}/{w['xgb']:.2f}/{w['svm']:.2f}/{w['rf']:.2f})",
            y_test, proba_ens,
        ),
    ]

    baseline_majority = _metrics("baseline_majority", y_test, None)
    rng = np.random.default_rng(42)
    baseline_random   = _metrics("baseline_random", y_test, rng.random(len(y_test)))

    _print_table(rows + [baseline_majority, baseline_random])

    best  = max(rows, key=lambda r: r["roc_auc"])
    delta = best["accuracy"] - baseline_majority["accuracy"]
    print(f"\n[eval_v9] best = {best['name']} "
          f"(Acc={best['accuracy']:.4f}, ROC-AUC={best['roc_auc']:.4f})", file=sys.stderr)
    print(f"[eval_v9] majority 대비 +{delta:.4f}", file=sys.stderr)

    summary = {
        "n_test": int(len(y_test)),
        "test_a_win_rate": float(np.mean(y_test)),
        "ensemble_weights": w,
        "models": {r["name"]: {k: r[k] for k in r if k != "name"} for r in rows},
        "baselines": {
            "majority_A_always": {k: baseline_majority[k]
                                  for k in baseline_majority if k != "name"},
            "random_coin_seed42": {k: baseline_random[k]
                                   for k in baseline_random if k != "name"},
        },
        "best_model_vs_majority_accuracy_delta": delta,
    }
    out_path = REPORTS_DIR / "eval_summary_v9.json"
    with open(out_path, "w") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"[eval_v9] saved {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
