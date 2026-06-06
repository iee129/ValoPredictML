"""Train the active advanced RF/XGB/LGBM soft-voting ensemble.

Usage:
    python -m ml.advanced.ensemble \
        --input data/processed/advanced \
        --output models/advanced \
        --reports reports/advanced
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.metrics import roc_auc_score
from xgboost import XGBClassifier

from ml.baseline.preprocess import (
    EXPECTED_FEATURE_COUNT_ADVANCED,
    FEATURE_COLS_ADVANCED,
    SOURCE_CONTRACT,
    build_xy,
    compute_adv_impute_means,
)

DEFAULT_INPUT_DIR = "data/processed/advanced"
DEFAULT_OUTPUT_DIR = "models/advanced"
DEFAULT_REPORTS_DIR = "reports/advanced"
DEFAULT_VAL_YEAR = 2025
DEFAULT_WEIGHT_GRID = (0.1, 0.2, 0.35, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0)


def _read_best_params(reports_dir: Path, model_name: str) -> dict[str, Any]:
    path = reports_dir / f"{model_name}_best_params.json"
    if not path.exists():
        return {}
    with open(path) as f:
        payload = json.load(f)
    return dict(payload.get("best_params", {}))


def _read_best_weights(reports_dir: Path) -> dict[str, Any] | None:
    path = reports_dir / "ensemble_best_weights.json"
    if not path.exists():
        return None
    with open(path) as f:
        payload = json.load(f)
    weights = payload.get("weights")
    if not isinstance(weights, list) or len(weights) != 3:
        raise ValueError(f"{path} must contain three ensemble weights")
    if any(float(weight) <= 0 for weight in weights):
        raise ValueError(f"{path} contains non-positive ensemble weights: {weights}")
    payload["weights"] = [float(weight) for weight in weights]
    return payload


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
    if "min_samples_split" in cfg:
        cfg["min_samples_split"] = int(cfg["min_samples_split"])
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
        "tree_method": "hist",
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
        "subsample_freq": 1,
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
    if "max_depth" in cfg and cfg["max_depth"] is not None:
        cfg["max_depth"] = int(cfg["max_depth"])
    return LGBMClassifier(**cfg)


def _assert_allowed_sources(df: pd.DataFrame, split_name: str) -> None:
    if "source" not in df.columns:
        raise ValueError(f"{split_name}.csv has no source column")
    allowed = tuple(SOURCE_CONTRACT.get("allowed_source_prefixes", ["kaggle_", "vlrgg_"]))
    bad = df.loc[~df["source"].astype(str).str.startswith(allowed), "source"].unique()
    if len(bad):
        preview = ", ".join(map(str, bad[:5]))
        raise ValueError(f"{split_name}.csv contains disallowed sources: {preview}")


def _load_training_frame(input_dir: Path) -> tuple[pd.DataFrame, dict[str, int]]:
    train_df = pd.read_csv(input_dir / "train.csv", low_memory=False)
    _assert_allowed_sources(train_df, "train")
    row_counts = {"train": int(len(train_df))}
    return train_df, row_counts


def _chrono_train_val_frames(
    train_df: pd.DataFrame,
    val_year: int,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    if "year" not in train_df.columns:
        raise ValueError("train.csv must include a year column for ensemble weight selection")

    years = pd.to_numeric(train_df["year"], errors="coerce")
    fit_df = train_df.loc[years < val_year].copy()
    val_df = train_df.loc[years == val_year].copy()
    if fit_df.empty or val_df.empty:
        raise ValueError(
            f"Cannot select ensemble weights for val_year={val_year}: "
            f"fit_rows={len(fit_df)}, val_rows={len(val_df)}"
        )

    overlap = set(fit_df["match_key"].astype(str)) & set(val_df["match_key"].astype(str))
    if overlap:
        raise ValueError(f"Chronological weight selection has {len(overlap)} match_key overlaps")

    fit_years = pd.to_numeric(fit_df["year"], errors="coerce")
    val_years = pd.to_numeric(val_df["year"], errors="coerce")
    return fit_df, val_df, {
        "selection_method": "chrono_holdout_weight_grid",
        "val_year": int(val_year),
        "fit_rows": int(len(fit_df)),
        "val_rows": int(len(val_df)),
        "fit_year_min": int(fit_years.min()),
        "fit_year_max": int(fit_years.max()),
        "val_year_min": int(val_years.min()),
        "val_year_max": int(val_years.max()),
        "metric": "roc_auc",
        "test_usage": "not_used",
    }


def _build_xy_with_means(
    fit_df: pd.DataFrame,
    val_df: pd.DataFrame,
    input_dir: Path,
) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
    impute_means = compute_adv_impute_means(fit_df)
    X_fit, y_fit, _ = build_xy(
        fit_df,
        feature_contract="advanced",
        processed_dir=str(input_dir.parent),
        impute_means=impute_means,
    )
    X_val, y_val, _ = build_xy(
        val_df,
        feature_contract="advanced",
        processed_dir=str(input_dir.parent),
        impute_means=impute_means,
    )
    if list(X_fit.columns) != FEATURE_COLS_ADVANCED:
        raise RuntimeError("Advanced feature order does not match FEATURE_COLS_ADVANCED")
    if list(X_val.columns) != FEATURE_COLS_ADVANCED:
        raise RuntimeError("Validation feature order does not match FEATURE_COLS_ADVANCED")
    return X_fit, y_fit, X_val, y_val


def _make_member_models(params: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "rf": make_rf(params["rf"]),
        "xgb": make_xgb(params["xgb"]),
        "lgbm": make_lgbm(params["lgbm"]),
    }


def _weight_candidates(grid: tuple[float, ...]) -> list[list[float]]:
    values = [float(value) for value in grid]
    if any(value <= 0 for value in values):
        raise ValueError(f"Weight grid must be positive: {values}")
    return [[rf, xgb, lgbm] for rf in values for xgb in values for lgbm in values]


def _select_ensemble_weights(
    train_df: pd.DataFrame,
    input_dir: Path,
    reports_dir: Path,
    params: dict[str, dict[str, Any]],
    val_year: int,
    weight_grid: tuple[float, ...] = DEFAULT_WEIGHT_GRID,
) -> dict[str, Any]:
    fit_df, val_df, validation = _chrono_train_val_frames(train_df, val_year)
    X_fit, y_fit, X_val, y_val = _build_xy_with_means(fit_df, val_df, input_dir)

    print(
        "Selecting ensemble weights "
        f"(fit_years={validation['fit_year_min']}-{validation['fit_year_max']}, "
        f"val_year={validation['val_year']}, candidates={len(weight_grid) ** 3})"
    )

    val_probs: dict[str, np.ndarray] = {}
    member_auc: dict[str, float] = {}
    for name, model in _make_member_models(params).items():
        model.fit(X_fit, y_fit)
        probs = model.predict_proba(X_val)[:, 1]
        val_probs[name] = probs
        member_auc[name] = float(roc_auc_score(y_val, probs))
        print(f"  {name:4s} val_auc={member_auc[name]:.4f}")

    best_auc = -1.0
    best_weights = [1.0, 1.0, 1.0]
    names = ["rf", "xgb", "lgbm"]
    prob_matrix = np.vstack([val_probs[name] for name in names])
    for weights in _weight_candidates(weight_grid):
        weight_arr = np.asarray(weights, dtype=float)
        probs = np.average(prob_matrix, axis=0, weights=weight_arr)
        auc = float(roc_auc_score(y_val, probs))
        if auc > best_auc:
            best_auc = auc
            best_weights = [float(value) for value in weights]

    payload: dict[str, Any] = {
        "weights": best_weights,
        "members": names,
        "selection_method": validation["selection_method"],
        "validation": validation,
        "validation_auc": best_auc,
        "member_validation_auc": member_auc,
        "weight_grid": [float(value) for value in weight_grid],
    }
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / "ensemble_best_weights.json"
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"  selected weights={best_weights} val_auc={best_auc:.4f}")
    print(f"  saved weights -> {path}")
    return payload


def train_ensemble(
    input_dir: str = DEFAULT_INPUT_DIR,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    reports_dir: str = DEFAULT_REPORTS_DIR,
    select_weights: bool = True,
    val_year: int = DEFAULT_VAL_YEAR,
) -> dict[str, Any]:
    inp = Path(input_dir)
    out = Path(output_dir)
    rpt = Path(reports_dir)
    out.mkdir(parents=True, exist_ok=True)

    train_df, row_counts = _load_training_frame(inp)
    impute_means = compute_adv_impute_means(train_df)
    X, y, _ = build_xy(
        train_df,
        feature_contract="advanced",
        processed_dir=str(inp.parent),
        impute_means=impute_means,
    )
    feature_names = list(X.columns)
    if feature_names != FEATURE_COLS_ADVANCED:
        raise RuntimeError("Advanced feature order does not match FEATURE_COLS_ADVANCED")
    if X.shape[1] != EXPECTED_FEATURE_COUNT_ADVANCED:
        raise RuntimeError(
            f"Advanced model expects {EXPECTED_FEATURE_COUNT_ADVANCED} features, got {X.shape[1]}"
        )

    params = {
        "rf": _read_best_params(rpt, "rf"),
        "xgb": _read_best_params(rpt, "xgb"),
        "lgbm": _read_best_params(rpt, "lgbm"),
    }
    weights_payload = _read_best_weights(rpt)
    if select_weights:
        weights_payload = _select_ensemble_weights(
            train_df=train_df,
            input_dir=inp,
            reports_dir=rpt,
            params=params,
            val_year=val_year,
        )
    if weights_payload is None:
        weights_payload = {
            "weights": [1.0, 1.0, 1.0],
            "members": ["rf", "xgb", "lgbm"],
            "selection_method": "default_equal_weights",
            "validation": None,
            "validation_auc": None,
        }
    weights = [float(weight) for weight in weights_payload["weights"]]

    print(f"Training advanced ensemble on {X.shape[0]:,} rows x {X.shape[1]} features")
    print(f"  input={inp}")
    print(f"  params source={rpt}")
    print(f"  ensemble weights={weights}")

    ensemble = VotingClassifier(
        estimators=[
            ("rf", make_rf(params["rf"])),
            ("xgb", make_xgb(params["xgb"])),
            ("lgbm", make_lgbm(params["lgbm"])),
        ],
        voting="soft",
        weights=weights,
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
            "active_rule": "all training/evaluation rows must match the allowed source prefixes",
        },
        "data": {
            "input_dir": str(inp),
            "modeling_splits": ["train"],
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
            "weights": weights,
            "members": ["rf", "xgb", "lgbm"],
            "weight_source": str(rpt / "ensemble_best_weights.json")
            if weights_payload.get("selection_method") != "default_equal_weights"
            else None,
            "weight_selection": {
                key: value
                for key, value in weights_payload.items()
                if key != "weights"
            },
        },
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
    ap.add_argument("--val-year", type=int, default=DEFAULT_VAL_YEAR)
    ap.add_argument(
        "--no-select-weights",
        action="store_true",
        help="Use an existing ensemble_best_weights.json or equal weights instead of selecting on the chrono holdout.",
    )
    args = ap.parse_args()
    train_ensemble(
        input_dir=args.input,
        output_dir=args.output,
        reports_dir=args.reports,
        select_weights=not args.no_select_weights,
        val_year=args.val_year,
    )
