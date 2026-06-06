import argparse
import json
import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.metrics import accuracy_score, roc_auc_score

from features.preprocess import (
    FEATURE_CONTRACT,
    FEATURE_ENGINEERING_CONFIG,
    FORBIDDEN_FEATURE_TERMS,
    INPUT_CONTRACT,
    SOURCE_CONTRACT,
    build_xy,
    find_forbidden_feature_names,
    load_split,
    previous_year_global_earliest_audit,
)
from ml.baseline.train import MODELING_SPLITS, TEST_SPLIT, load_modeling_data


def _load_all_splits(input_dir: str) -> dict[str, pd.DataFrame]:
    return {split: load_split(split, base=input_dir) for split in ("train", "test")}


def _split_overlap_count(splits: dict[str, pd.DataFrame]) -> int:
    keys = {name: set(df["match_key"].astype(str)) for name, df in splits.items()}
    return int(len(keys["train"] & keys["test"]))


def _label_shuffle_auc(y_true: pd.Series, y_prob: np.ndarray) -> dict:
    rng = np.random.default_rng(42)
    shuffled = np.array(y_true, dtype=int).copy()
    rng.shuffle(shuffled)
    auc = float(roc_auc_score(shuffled, y_prob))
    status = "정상" if 0.48 <= auc <= 0.52 else "주의"
    return {"status": status, "auc": auc, "expected_range": [0.48, 0.52]}


def _single_feature_auc_scan(X: pd.DataFrame, y: pd.Series) -> dict:
    best = {"feature": None, "auc": 0.5, "directionless_auc": 0.5}
    for col in X.columns:
        values = X[col].to_numpy(dtype=float)
        if np.nanmax(values) == np.nanmin(values):
            continue
        auc = float(roc_auc_score(y, values))
        directionless = max(auc, 1.0 - auc)
        if directionless > best["directionless_auc"]:
            best = {
                "feature": col,
                "auc": auc,
                "directionless_auc": directionless,
            }
    if best["directionless_auc"] > 0.95:
        status = "문제"
    elif best["directionless_auc"] > 0.85:
        status = "주의"
    else:
        status = "정상"
    return {"status": status, **best}


def _dt_importances(pipe, feature_names: list[str]) -> list[dict]:
    dt = pipe.named_estimators_["dt"]
    importances = dt.feature_importances_
    top_idx = np.argsort(importances)[::-1][:20]
    return [
        {"feature": feature_names[i], "importance": float(importances[i])}
        for i in top_idx
        if i < len(feature_names)
    ]


def _permutation_importances(
    pipe,
    X: pd.DataFrame,
    y: pd.Series,
    feature_names: list[str],
    n_repeats: int = 10,
) -> list[dict]:
    """Test 데이터에서 피처별 AUC 감소량(permutation importance) 측정.

    impurity-based importance의 first-split 편향과 다중공선성 흡수 영향을 받지 않는다.
    """
    result = permutation_importance(
        pipe,
        X,
        y,
        scoring="roc_auc",
        n_repeats=n_repeats,
        random_state=42,
        n_jobs=-1,
    )
    top_idx = np.argsort(result.importances_mean)[::-1][:20]
    return [
        {
            "feature": feature_names[i],
            "auc_drop_mean": float(result.importances_mean[i]),
            "auc_drop_std": float(result.importances_std[i]),
        }
        for i in top_idx
        if i < len(feature_names)
    ]


def _update_meta(models_dir: str, validation: dict) -> None:
    meta_path = Path(models_dir) / "meta.json"
    if meta_path.exists():
        with open(meta_path) as f:
            meta = json.load(f)
    else:
        meta = {}
    meta.update(
        {
            "input_contract": INPUT_CONTRACT,
            "feature_contract": FEATURE_CONTRACT,
            "feature_engineering_config": FEATURE_ENGINEERING_CONFIG,
            "modeling_splits": MODELING_SPLITS,
            "test_split": TEST_SPLIT,
            "split_protocol": "tune with GroupKFold on train (80%), final fit on train, final evaluation on test (20%)",
            "source_contract": SOURCE_CONTRACT,
            "forbidden_feature_terms": FORBIDDEN_FEATURE_TERMS,
            "feature_names": validation["feature_names"],
            "separation_checks": validation["separation_checks"],
            "final_verdict": validation["final_verdict"],
        }
    )
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)


def validate(
    input_dir: str = "data/processed",
    models_dir: str = "models/baseline",
    reports_dir: str = os.path.join("reports", "baseline"),
) -> None:
    model_path = os.path.join(models_dir, "model.joblib")
    if not os.path.exists(model_path):
        from ml.baseline.reference import REFERENCE_BASELINE, materialize

        paths = materialize(reports_dir=reports_dir, models_dir=models_dir)
        print("Baseline model joblib not found; using midterm PDF reference baseline.")
        print(
            "Reference AUC={test_auc:.4f} Acc={test_acc:.4f} F1={test_f1:.4f} "
            "features={feature_count}".format(**REFERENCE_BASELINE)
        )
        print(f"Metrics    -> {paths['metrics']}")
        print(f"Validation -> {paths['validation']}")
        print(f"Meta       -> {paths['meta']}")
        return

    pipe = joblib.load(model_path)

    splits = _load_all_splits(input_dir)
    df_modeling = load_modeling_data(input_dir)
    X_tr, y_tr, _ = build_xy(df_modeling)
    df_test = splits[TEST_SPLIT]
    X_te, y_te, _ = build_xy(df_test)

    majority = int(y_tr.mode()[0])
    majority_acc = float((y_te == majority).mean())

    train_acc = float(accuracy_score(y_tr, pipe.predict(X_tr)))
    test_acc = float(accuracy_score(y_te, pipe.predict(X_te)))
    test_prob = pipe.predict_proba(X_te)[:, 1]
    test_auc = float(roc_auc_score(y_te, test_prob))
    gap = train_acc - test_acc

    feature_names = list(X_tr.columns)
    forbidden_features = find_forbidden_feature_names(feature_names)
    split_overlap = _split_overlap_count(splits)
    same_year_check = previous_year_global_earliest_audit(input_dir)
    label_shuffle = _label_shuffle_auc(y_te, test_prob)
    single_feature = _single_feature_auc_scan(X_te, y_te)

    separation_checks = {
        "forbidden_features": "정상" if not forbidden_features else "문제",
        "same_match_separation": same_year_check["status"],
        "same_year_history_exclusion": same_year_check["status"],
        "split_overlap": "정상" if split_overlap == 0 else "문제",
        "label_shuffle_auc": label_shuffle["status"],
        "single_feature_auc": single_feature["status"],
    }
    hard_fail = (
        bool(forbidden_features)
        or same_year_check["status"] == "문제"
        or split_overlap != 0
        or single_feature["status"] == "문제"
    )
    final_verdict = (
        "신뢰 가능"
        if not hard_fail
        else "신뢰 불가"
    )

    result = {
        "input_contract": INPUT_CONTRACT,
        "feature_contract": FEATURE_CONTRACT,
        "feature_engineering_config": FEATURE_ENGINEERING_CONFIG,
        "modeling_splits": MODELING_SPLITS,
        "test_split": TEST_SPLIT,
        "split_protocol": "tune with GroupKFold on train+val, final fit on train+val, final evaluation on test",
        "source_contract": SOURCE_CONTRACT,
        "forbidden_feature_terms": FORBIDDEN_FEATURE_TERMS,
        "feature_names": feature_names,
        "forbidden_feature_count": len(forbidden_features),
        "forbidden_features": forbidden_features,
        "separation_checks": separation_checks,
        "same_match_separation_check": same_year_check,
        "same_year_history_exclusion_check": same_year_check,
        "split_overlap_count": split_overlap,
        "label_shuffle_auc": label_shuffle,
        "single_feature_auc_scan": single_feature,
        "majority_baseline_acc": majority_acc,
        "model_train_acc": train_acc,
        "model_test_acc": test_acc,
        "model_test_auc": test_auc,
        "train_test_gap": gap,
        "overfit_warning": gap > 0.05,
        "model_vs_majority_delta": test_acc - majority_acc,
        "top_features": _dt_importances(pipe, feature_names),
        "permutation_top_features": _permutation_importances(
            pipe, X_te, y_te, feature_names
        ),
        "final_verdict": final_verdict,
    }

    os.makedirs(reports_dir, exist_ok=True)
    out_path = os.path.join(reports_dir, "validation.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    _update_meta(models_dir, result)

    print(f"Majority baseline acc : {majority_acc:.4f}")
    print(f"Model test acc        : {test_acc:.4f}  ({result['model_vs_majority_delta']:+.4f} vs majority)")
    print(f"Model test AUC        : {test_auc:.4f}")
    print(f"Forbidden features    : {len(forbidden_features)}")
    print(f"Split overlap         : {split_overlap}")
    print(f"최종 판정              : {final_verdict}")
    perm_top = result["permutation_top_features"]
    if perm_top:
        first = perm_top[0]
        print(
            f"Permutation top1      : {first['feature']} "
            f"(Δauc={first['auc_drop_mean']:+.4f} ± {first['auc_drop_std']:.4f})"
        )
    print(f"Validation -> {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/processed")
    parser.add_argument("--models", default="models/baseline")
    parser.add_argument("--reports", default=os.path.join("reports", "baseline"))
    args = parser.parse_args()
    validate(args.input, args.models, args.reports)
