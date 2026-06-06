"""Optuna hyperparameter optimization for the advanced RF/XGB/LGBM models.

This reproduces the best-params artifacts the soft-voting ensemble consumes:

    reports/advanced/{rf,xgb,lgbm}_best_params.json
    reports/advanced/optuna_studies/chrono_val_{year}/{rf,xgb,lgbm}_study.db

The objective is a train-internal chronological holdout: years before
``--val-year`` train the candidate, and ``--val-year`` scores ROC-AUC. The
official 2026 test split is never used by Optuna.

Usage:
    python -m ml.advanced.optimize --models rf xgb lgbm --n-trials 50
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

import optuna
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from xgboost import XGBClassifier

from features.preprocess import (
    FEATURE_COLS_ADVANCED,
    build_xy,
    compute_adv_impute_means,
    load_split,
)

DEFAULT_INPUT_DIR = "data/processed/advanced"
DEFAULT_REPORTS_DIR = "reports/advanced"
MODELING_SPLITS = ["train"]
RANDOM_STATE = 42
DEFAULT_N_TRIALS = 50
DEFAULT_VAL_YEAR = 2025


def _rf_factory(trial: optuna.Trial) -> RandomForestClassifier:
    return RandomForestClassifier(
        n_estimators=trial.suggest_int("n_estimators", 60, 260),
        max_depth=trial.suggest_int("max_depth", 5, 12),
        min_samples_leaf=trial.suggest_int("min_samples_leaf", 10, 150),
        min_samples_split=trial.suggest_int("min_samples_split", 20, 220),
        max_features=trial.suggest_float("max_features", 0.25, 0.75),
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )


def _xgb_factory(trial: optuna.Trial) -> XGBClassifier:
    return XGBClassifier(
        n_estimators=trial.suggest_int("n_estimators", 120, 900),
        max_depth=trial.suggest_int("max_depth", 2, 6),
        learning_rate=trial.suggest_float("learning_rate", 0.005, 0.08, log=True),
        subsample=trial.suggest_float("subsample", 0.65, 0.95),
        colsample_bytree=trial.suggest_float("colsample_bytree", 0.50, 0.90),
        min_child_weight=trial.suggest_int("min_child_weight", 8, 100),
        gamma=trial.suggest_float("gamma", 0.0, 6.0),
        reg_alpha=trial.suggest_float("reg_alpha", 1e-4, 5.0, log=True),
        reg_lambda=trial.suggest_float("reg_lambda", 1.0, 30.0, log=True),
        max_delta_step=trial.suggest_int("max_delta_step", 0, 5),
        tree_method="hist",
        eval_metric="logloss",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )


def _lgbm_factory(trial: optuna.Trial) -> LGBMClassifier:
    return LGBMClassifier(
        n_estimators=trial.suggest_int("n_estimators", 120, 900),
        max_depth=trial.suggest_int("max_depth", 3, 8),
        learning_rate=trial.suggest_float("learning_rate", 0.005, 0.08, log=True),
        num_leaves=trial.suggest_int("num_leaves", 8, 64),
        subsample=trial.suggest_float("subsample", 0.65, 0.95),
        subsample_freq=1,
        colsample_bytree=trial.suggest_float("colsample_bytree", 0.50, 0.90),
        min_child_samples=trial.suggest_int("min_child_samples", 40, 300),
        reg_alpha=trial.suggest_float("reg_alpha", 1e-4, 5.0, log=True),
        reg_lambda=trial.suggest_float("reg_lambda", 1.0, 30.0, log=True),
        min_split_gain=trial.suggest_float("min_split_gain", 0.0, 1.0),
        random_state=RANDOM_STATE,
        n_jobs=-1,
        verbose=-1,
    )


MODEL_CONFIG: dict[str, dict[str, Any]] = {
    "rf": {"factory": _rf_factory},
    "xgb": {"factory": _xgb_factory},
    "lgbm": {"factory": _lgbm_factory},
}


def _load_modeling_data(input_dir: str) -> pd.DataFrame:
    frames = [load_split(split, base=input_dir) for split in MODELING_SPLITS]
    return pd.concat(frames, ignore_index=True)


def _chrono_train_val_frames(
    df: pd.DataFrame,
    val_year: int,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    if "year" not in df.columns:
        raise ValueError("train.csv must include a year column for chronological tuning")

    years = pd.to_numeric(df["year"], errors="coerce")
    fit_mask = years < val_year
    val_mask = years == val_year
    fit_df = df.loc[fit_mask].copy()
    val_df = df.loc[val_mask].copy()
    if fit_df.empty or val_df.empty:
        raise ValueError(
            f"Cannot build chronological holdout for val_year={val_year}: "
            f"fit_rows={len(fit_df)}, val_rows={len(val_df)}"
        )

    overlap = set(fit_df["match_key"].astype(str)) & set(val_df["match_key"].astype(str))
    if overlap:
        raise ValueError(f"Chronological holdout has {len(overlap)} match_key overlaps")

    fit_years = pd.to_numeric(fit_df["year"], errors="coerce")
    val_years = pd.to_numeric(val_df["year"], errors="coerce")
    metadata = {
        "selection_method": "chrono_holdout",
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
    return fit_df, val_df, metadata


def _build_chrono_xy(
    fit_df: pd.DataFrame,
    val_df: pd.DataFrame,
    processed_dir: str,
) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
    impute_means = compute_adv_impute_means(fit_df)
    X_fit, y_fit, _ = build_xy(
        fit_df,
        feature_contract="advanced",
        processed_dir=processed_dir,
        impute_means=impute_means,
    )
    X_val, y_val, _ = build_xy(
        val_df,
        feature_contract="advanced",
        processed_dir=processed_dir,
        impute_means=impute_means,
    )
    if list(X_fit.columns) != FEATURE_COLS_ADVANCED:
        raise RuntimeError("Advanced feature order does not match FEATURE_COLS_ADVANCED")
    if list(X_val.columns) != FEATURE_COLS_ADVANCED:
        raise RuntimeError("Validation feature order does not match FEATURE_COLS_ADVANCED")
    return X_fit, y_fit, X_val, y_val


def _make_objective(
    factory: Callable[[optuna.Trial], Any],
    X_fit: pd.DataFrame,
    y_fit: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
) -> Callable[[optuna.Trial], float]:
    def objective(trial: optuna.Trial) -> float:
        model = factory(trial)
        model.fit(X_fit, y_fit)
        prob = model.predict_proba(X_val)[:, 1]
        return float(roc_auc_score(y_val, prob))

    return objective


def _run_study(
    objective: Callable[[optuna.Trial], float],
    study_name: str,
    storage_path: Path,
    n_trials: int,
) -> optuna.Study:
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    study = optuna.create_study(
        study_name=study_name,
        direction="maximize",
        storage=f"sqlite:///{storage_path}",
        load_if_exists=True,
        sampler=optuna.samplers.TPESampler(seed=RANDOM_STATE),
    )
    remaining = n_trials - len(study.trials)
    if remaining > 0:
        optuna.logging.set_verbosity(optuna.logging.WARNING)
        study.optimize(objective, n_trials=remaining)
    return study


def _save_best_params(study: optuna.Study, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "best_params": study.best_params,
        "best_value": study.best_value,
        "n_trials": len(study.trials),
    }
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"  saved best params -> {path} (best_value={study.best_value:.4f})")


def optimize(
    models: list[str],
    n_trials: int = DEFAULT_N_TRIALS,
    input_dir: str = DEFAULT_INPUT_DIR,
    reports_dir: str = DEFAULT_REPORTS_DIR,
    val_year: int = DEFAULT_VAL_YEAR,
) -> dict[str, dict[str, Any]]:
    rpt = Path(reports_dir)
    studies_dir = rpt / "optuna_studies" / f"chrono_val_{val_year}"

    df = _load_modeling_data(input_dir)
    fit_df, val_df, validation = _chrono_train_val_frames(df, val_year)
    X_fit, y_fit, X_val, y_val = _build_chrono_xy(
        fit_df,
        val_df,
        processed_dir=str(Path(input_dir).parent),
    )
    print(
        "Data: "
        f"fit={X_fit.shape} years={validation['fit_year_min']}-{validation['fit_year_max']} "
        f"val={X_val.shape} year={validation['val_year']} "
        f"fit_label_rate={y_fit.mean():.3f} val_label_rate={y_val.mean():.3f}"
    )

    results: dict[str, dict[str, Any]] = {}
    for name in models:
        if name not in MODEL_CONFIG:
            raise ValueError(f"Unknown model {name!r}; choose from {list(MODEL_CONFIG)}")
        config = MODEL_CONFIG[name]
        print(f"Tuning {name} (chrono val_year={val_year}, n_trials={n_trials}) ...")
        objective = _make_objective(config["factory"], X_fit, y_fit, X_val, y_val)
        study = _run_study(
            objective,
            study_name=f"{name}_chrono_val_{val_year}_study",
            storage_path=studies_dir / f"{name}_study.db",
            n_trials=n_trials,
        )
        path = rpt / f"{name}_best_params.json"
        _save_best_params(study, path)
        with open(path) as f:
            payload = json.load(f)
        payload.update(
            {
                "selection_method": "chrono_holdout",
                "validation": validation,
            }
        )
        with open(path, "w") as f:
            json.dump(payload, f, indent=2)
        results[name] = {
            "best_params": study.best_params,
            "best_value": study.best_value,
            "validation": validation,
        }
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["rf", "xgb", "lgbm"], choices=["rf", "xgb", "lgbm"])
    ap.add_argument("--n-trials", type=int, default=DEFAULT_N_TRIALS)
    ap.add_argument("--input", default=DEFAULT_INPUT_DIR)
    ap.add_argument("--reports", default=DEFAULT_REPORTS_DIR)
    ap.add_argument("--val-year", type=int, default=DEFAULT_VAL_YEAR)
    args = ap.parse_args()
    optimize(
        models=args.models,
        n_trials=args.n_trials,
        input_dir=args.input,
        reports_dir=args.reports,
        val_year=args.val_year,
    )
