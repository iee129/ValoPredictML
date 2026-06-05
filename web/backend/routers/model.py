"""GET /health, GET /model — 모델 상태·근거."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re
from typing import Any

import numpy as np
import pandas as pd
from fastapi import APIRouter

from app.predict import (
    DEFAULT_ADVANCED_DIR,
    feature_label,
    global_feature_importance,
    load_model,
    load_reports,
)
from ml.baseline.preprocess import FEATURE_COLS_ADVANCED, ROLES, build_xy
from ml.valorant import AGENT_ROLE_MAP, _agent_col_key, normalize_agent
from web.backend.deps import to_http

router = APIRouter()

_AGENT_COUNT_RE = re.compile(r"^[ab]_agent_(?P<agent>.+)_count$")
_AGENT_KEY_TO_NAME = {_agent_col_key(agent): agent for agent in AGENT_ROLE_MAP}
_FEATURE_GROUP_LABELS = {
    "player_prior": "선수 이전 성과",
    "player_agent": "선수×요원 숙련",
    "map_agent": "맵×요원 적합도",
    "comp_role": "조합·역할 균형",
    "team_history": "팀 이력",
    "roster_history": "로스터 연속성",
    "history_reliability": "히스토리 신뢰도",
    "map_context": "맵 컨텍스트",
    "other": "기타",
}
_MIDTERM_BASELINE_AUC = 0.5943
_MIDTERM_BASELINE_ACC = 0.5667
_MIDTERM_BASELINE_F1 = 0.6072
_MIDTERM_BASELINE_FEATURES = 421


@router.get("/health")
def health() -> dict:
    try:
        model, _ = load_model()
        n = getattr(model, "n_features_in_", None)
        ok = n == len(FEATURE_COLS_ADVANCED)
        return {"status": "ok" if ok else "degraded",
                "model_loaded": bool(ok), "n_features": n, "contract": "advanced"}
    except Exception as exc:   # 산출물 부재 등 — 서버는 살아있고 상태만 보고
        return {"status": "unavailable", "model_loaded": False,
                "n_features": None, "contract": "advanced", "detail": str(exc)}


def _clean_metrics(raw: dict[str, Any]) -> dict[str, Any]:
    metrics = dict(raw)
    advanced_auc = raw.get("test_auc")
    metrics["baseline_auc"] = _MIDTERM_BASELINE_AUC
    metrics["baseline_acc"] = _MIDTERM_BASELINE_ACC
    metrics["baseline_f1"] = _MIDTERM_BASELINE_F1
    metrics["baseline_features"] = _MIDTERM_BASELINE_FEATURES
    metrics["baseline_comparison"] = {
        "baseline_features": _MIDTERM_BASELINE_FEATURES,
        "baseline_test_auc": _MIDTERM_BASELINE_AUC,
        "baseline_test_acc": _MIDTERM_BASELINE_ACC,
        "baseline_test_f1": _MIDTERM_BASELINE_F1,
        "advanced_test_auc": advanced_auc,
        "advanced_test_acc": raw.get("test_acc"),
        "advanced_test_f1": raw.get("test_f1"),
        "delta_test_auc": (
            float(advanced_auc) - _MIDTERM_BASELINE_AUC
            if advanced_auc is not None
            else None
        ),
    }
    return metrics


def _per_model_metrics(raw: dict[str, Any]) -> list[dict[str, Any]]:
    models = raw.get("models") or {}
    names = [
        ("rf", "RF"),
        ("xgb", "XGBoost"),
        ("lgbm", "LightGBM"),
        ("ensemble", "Ensemble"),
    ]
    out: list[dict[str, Any]] = []
    for key, name in names:
        item = models.get(key) or raw.get(key) or {}
        train = item.get("train") or {}
        test = item.get("test") or {}
        if not train and not test:
            continue
        out.append(
            {
                "name": name,
                "train_auc": train.get("auc"),
                "test_auc": test.get("auc"),
                "acc": test.get("acc"),
                "f1": test.get("f1"),
                "confusion_matrix": test.get("confusion_matrix"),
            }
        )
    return out


def _model_eval(raw: dict[str, Any]) -> dict[str, Any]:
    test_auc = raw.get("test_auc")
    train_auc = raw.get("train_auc")
    out: dict[str, Any] = {
        "primary_auc": test_auc,
        "primary_label": "Test AUC",
        "note": "현재 웹 표시는 advanced train/test 맵 단위 승패 샘플 기준입니다.",
    }
    if train_auc is not None:
        out["secondary_auc"] = train_auc
        out["secondary_label"] = "Train AUC"
    return out


def _validation_summary(validation: dict[str, Any]) -> list[dict[str, Any]]:
    test_auc_check = validation.get("test_auc_check") or {}
    return [
        {
            "key": "forbidden_feature_count",
            "label": "금지 피처",
            "value": str(validation.get("forbidden_feature_count", "-")),
            "passed": validation.get("forbidden_feature_count") == 0,
        },
        {
            "key": "split_overlap_count",
            "label": "split 중복",
            "value": str(validation.get("split_overlap_count", "-")),
            "passed": validation.get("split_overlap_count") == 0,
        },
        {
            "key": "same_year_exclusion_check",
            "label": "동일연도 제외",
            "value": str(validation.get("same_year_exclusion_check", "-")),
            "passed": validation.get("same_year_exclusion_check") == "정상",
        },
        {
            "key": "source_prefix_check",
            "label": "소스 계약",
            "value": str(validation.get("source_prefix_check", "-")),
            "passed": validation.get("source_prefix_check") == "정상",
        },
        {
            "key": "test_auc_check",
            "label": "Test AUC 게이트",
            "value": (
                f"{float(test_auc_check.get('value')):.3f}"
                if test_auc_check.get("value") is not None
                else "-"
            ),
            "passed": bool(test_auc_check.get("passed")),
        },
        {
            "key": "final_verdict",
            "label": "최종 판정",
            "value": str(validation.get("final_verdict", "-")),
            "passed": validation.get("final_verdict") == "신뢰 가능",
        },
    ]


def _finite_float_list(values: np.ndarray) -> list[float]:
    return [float(v) for v in values if np.isfinite(v)]


@lru_cache(maxsize=1)
def _test_predictions() -> dict[str, np.ndarray] | None:
    try:
        model, _ = load_model()
        test = pd.read_csv(DEFAULT_ADVANCED_DIR / "test.csv", low_memory=False)
        X, y, _ = build_xy(test, feature_contract="advanced")
        scores = model.predict_proba(X[FEATURE_COLS_ADVANCED])[:, 1]
        labels = np.asarray(y, dtype=int)
        preds = (scores >= 0.5).astype(int)
        confidence = np.maximum(scores, 1.0 - scores)
        return {
            "scores": scores.astype(float),
            "labels": labels,
            "preds": preds,
            "confidence": confidence.astype(float),
            "correct": preds == labels,
        }
    except Exception:
        return None


@lru_cache(maxsize=1)
def _roc_points() -> dict[str, list[float]] | None:
    try:
        from sklearn.metrics import roc_curve

        preds = _test_predictions()
        if not preds:
            return None
        scores = preds["scores"]
        labels = preds["labels"]
        fpr, tpr, _ = roc_curve(labels, scores)
        if len(fpr) > 260:
            idx = np.unique(np.linspace(0, len(fpr) - 1, 260, dtype=int))
            fpr = fpr[idx]
            tpr = tpr[idx]
        return {"fpr": _finite_float_list(fpr), "tpr": _finite_float_list(tpr)}
    except Exception:
        return None


def _feature_group_key(feature: str) -> str:
    core = feature
    for prefix in ("diff_", "a_", "b_"):
        if core.startswith(prefix):
            core = core.removeprefix(prefix)
            break

    if core.startswith("player_agent_"):
        return "player_agent"
    if core.startswith("map_agent_") or core.startswith("agent_map_fit"):
        return "map_agent"
    if (
        core.startswith("prior_")
        or core in {"max_prior_kd", "std_prior_kd"}
        or core in {"known_player_ratio", "low_sample_player_ratio"}
    ):
        return "player_prior"
    if core.startswith("team_"):
        return "team_history"
    if core.startswith("roster_"):
        return "roster_history"
    if (
        core.startswith("comp_")
        or core == "synergy_mean"
        or core == "role_balance"
        or core in {"has_controller", "has_initiator", "double_duelist"}
    ):
        return "comp_role"
    if "history" in core or core.endswith("_known_ratio"):
        return "history_reliability"
    if feature.startswith("map_") or core == "map_atk_adv":
        return "map_context"
    return "other"


@lru_cache(maxsize=1)
def _feature_group_importance() -> list[dict[str, Any]]:
    try:
        rows = global_feature_importance(limit=len(FEATURE_COLS_ADVANCED))
    except Exception:
        return []

    groups: dict[str, dict[str, Any]] = {}
    total = 0.0
    for row in rows:
        feature = str(row.get("feature", ""))
        importance = float(row.get("importance") or 0.0)
        if not feature or not np.isfinite(importance):
            continue
        importance = max(0.0, importance)
        total += importance
        key = _feature_group_key(feature)
        group = groups.setdefault(
            key,
            {
                "group": key,
                "label": _FEATURE_GROUP_LABELS.get(key, key),
                "importance": 0.0,
                "top_features": [],
            },
        )
        group["importance"] += importance
        if importance > 0:
            group["top_features"].append(
                {
                    "feature": feature,
                    "importance": importance,
                    "label": feature_label(feature),
                }
            )

    if total <= 0:
        return []

    result: list[dict[str, Any]] = []
    for group in groups.values():
        top_features = sorted(
            group["top_features"],
            key=lambda item: item["importance"],
            reverse=True,
        )[:3]
        result.append(
            {
                "group": group["group"],
                "label": group["label"],
                "importance": float(group["importance"]),
                "share": float(group["importance"] / total),
                "top_features": top_features,
            }
        )
    return sorted(result, key=lambda item: item["importance"], reverse=True)


@lru_cache(maxsize=1)
def _confidence_bins() -> list[dict[str, Any]]:
    preds = _test_predictions()
    if not preds:
        return []

    confidence = preds["confidence"].astype(float)
    correct = preds["correct"].astype(bool)
    bins = [
        (0.50, 0.60),
        (0.60, 0.70),
        (0.70, 0.80),
        (0.80, 0.90),
        (0.90, 1.00),
    ]
    rows: list[dict[str, Any]] = []
    for lower, upper in bins:
        if upper >= 1.0:
            mask = (confidence >= lower) & (confidence <= upper)
        else:
            mask = (confidence >= lower) & (confidence < upper)
        count = int(mask.sum())
        if count <= 0:
            continue
        rows.append(
            {
                "bin": f"{int(lower * 100)}-{int(upper * 100)}%",
                "lower": lower,
                "upper": upper,
                "count": count,
                "accuracy": float(correct[mask].mean()),
                "avg_confidence": float(confidence[mask].mean()),
            }
        )
    return rows


def _read_split_frame(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    header = pd.read_csv(path, nrows=0).columns
    agent_cols = [
        col
        for col in header
        if _AGENT_COUNT_RE.match(str(col))
    ]
    usecols = [
        col
        for col in (
            ["match_key", "label", "map", "year"]
            + [f"a_role_{r}_count" for r in ROLES]
            + [f"b_role_{r}_count" for r in ROLES]
            + agent_cols
        )
        if col in header
    ]
    return pd.read_csv(path, usecols=usecols, low_memory=False)


def _agent_display_name(agent_key: str) -> str:
    return _AGENT_KEY_TO_NAME.get(agent_key, agent_key.replace("_", " ").title())


def _numeric_column(group: pd.DataFrame, col: str) -> pd.Series:
    if col not in group.columns:
        return pd.Series(0.0, index=group.index)
    return pd.to_numeric(group[col], errors="coerce").fillna(0.0)


def _agent_meta_from_players(split_df: pd.DataFrame) -> list[dict[str, Any]]:
    if not {"match_key", "year", "label"}.issubset(split_df.columns):
        return []

    players_path = DEFAULT_ADVANCED_DIR.parent / "players.csv"
    if not players_path.exists():
        return []

    player_header = pd.read_csv(players_path, nrows=0).columns
    if not {"match_key", "side", "agent"}.issubset(player_header):
        return []

    matches = split_df[["match_key", "year", "label"]].dropna().copy()
    matches["match_key"] = matches["match_key"].astype(str)
    matches["year"] = pd.to_numeric(matches["year"], errors="coerce")
    matches["label"] = pd.to_numeric(matches["label"], errors="coerce")
    matches = matches.dropna(subset=["year", "label"]).drop_duplicates("match_key")
    if matches.empty:
        return []

    players = pd.read_csv(
        players_path,
        usecols=["match_key", "side", "agent"],
        low_memory=False,
    ).dropna(subset=["match_key", "side", "agent"])
    if players.empty:
        return []

    players["match_key"] = players["match_key"].astype(str)
    players["side"] = players["side"].astype(str).str.strip().str.lower()
    players = players[players["side"].isin(["a", "b"])]
    players["agent"] = players["agent"].map(lambda raw: normalize_agent(str(raw)))
    players = players.dropna(subset=["agent"])
    if players.empty:
        return []

    merged = players.merge(matches, on="match_key", how="inner")
    if merged.empty:
        return []

    labels = merged["label"].astype(int)
    merged["won"] = (
        (merged["side"].eq("a") & labels.eq(1))
        | (merged["side"].eq("b") & labels.eq(0))
    ).astype(float)

    rows: list[dict[str, Any]] = []
    for year, year_group in merged.groupby("year"):
        denom = float(matches.loc[matches["year"].eq(year), "match_key"].nunique() * 10)
        if denom <= 0:
            continue
        for agent, group in year_group.groupby("agent"):
            sample = len(group)
            if sample <= 0:
                continue
            rows.append(
                {
                    "year": int(year),
                    "agent": str(agent),
                    "agent_key": _agent_col_key(str(agent)),
                    "pick_rate": float(sample / denom),
                    "win_rate": float(group["won"].mean()),
                    "sample": int(sample),
                }
            )
    return rows


@lru_cache(maxsize=1)
def _eda_summary() -> dict[str, Any]:
    frames = [
        frame
        for frame in (
            _read_split_frame(DEFAULT_ADVANCED_DIR / "train.csv"),
            _read_split_frame(DEFAULT_ADVANCED_DIR / "test.csv"),
        )
        if frame is not None and not frame.empty
    ]
    if not frames:
        return {}
    df = pd.concat(frames, ignore_index=True)
    out: dict[str, Any] = {
        "sample_unit": "map_win_loss",
        "sample_unit_label": "맵 단위 승패 샘플",
        "sample_unit_note": "모델 학습·평가 기준은 맵별 승패 샘플입니다.",
    }

    if "label" in df.columns:
        counts = df["label"].dropna().astype(int).value_counts().sort_index()
        out["target_dist"] = [
            {"label": int(label), "count": int(count)}
            for label, count in counts.items()
        ]

    if "map" in df.columns:
        map_counts = df["map"].dropna().astype(str).value_counts()
        out["map_counts"] = [
            {"map": str(map_name), "count": int(count)}
            for map_name, count in map_counts.items()
        ]

    role_cols = [
        col
        for col in [f"{side}_role_{role}_count" for side in ("a", "b") for role in ROLES]
        if col in df.columns
    ]
    if "year" in df.columns and role_cols:
        role_rows: list[dict[str, Any]] = []
        tmp = df.copy()
        tmp["year"] = pd.to_numeric(tmp["year"], errors="coerce")
        for year, group in tmp.dropna(subset=["year"]).groupby("year"):
            denom = float(len(group) * 10) or 1.0
            for role in ROLES:
                cols = [
                    col
                    for col in (f"a_role_{role}_count", f"b_role_{role}_count")
                    if col in group.columns
                ]
                if not cols:
                    continue
                role_rows.append(
                    {
                        "year": int(year),
                        "role": role,
                        "pick_rate": float(group[cols].sum().sum() / denom),
                    }
                )
        if role_rows:
            out["role_meta_by_year"] = role_rows

    player_agent_rows = _agent_meta_from_players(df)
    if player_agent_rows:
        out["agent_meta_by_year"] = player_agent_rows

    agent_keys = sorted(
        {
            match.group("agent")
            for col in df.columns
            if (match := _AGENT_COUNT_RE.match(str(col)))
        }
    )
    if "agent_meta_by_year" not in out and "year" in df.columns and "label" in df.columns and agent_keys:
        agent_rows: list[dict[str, Any]] = []
        tmp = df.copy()
        tmp["year"] = pd.to_numeric(tmp["year"], errors="coerce")
        tmp["label"] = pd.to_numeric(tmp["label"], errors="coerce")
        for year, group in tmp.dropna(subset=["year", "label"]).groupby("year"):
            denom = float(len(group) * 10) or 1.0
            labels = group["label"].astype(int)
            a_won = labels.eq(1).astype(float)
            b_won = labels.eq(0).astype(float)
            for agent_key in agent_keys:
                a_col = f"a_agent_{agent_key}_count"
                b_col = f"b_agent_{agent_key}_count"
                if a_col not in group.columns and b_col not in group.columns:
                    continue
                a_count = _numeric_column(group, a_col)
                b_count = _numeric_column(group, b_col)
                sample = float(a_count.sum() + b_count.sum())
                if sample <= 0:
                    continue
                wins = float((a_count * a_won).sum() + (b_count * b_won).sum())
                agent_rows.append(
                    {
                        "year": int(year),
                        "agent": _agent_display_name(agent_key),
                        "agent_key": agent_key,
                        "pick_rate": float(sample / denom),
                        "win_rate": float(wins / sample),
                        "sample": int(sample),
                    }
                )
        if agent_rows:
            out["agent_meta_by_year"] = agent_rows

    return out


@router.get("/model")
def model_info() -> dict:
    try:
        model, meta = load_model()
        reports = load_reports()
        gi = global_feature_importance(limit=20)
    except (FileNotFoundError, ValueError) as exc:
        raise to_http(exc)

    # n_features는 실제 모델 객체에서 읽어 literal fallback 없음
    n_features = getattr(model, "n_features_in_", meta.get("n_features"))

    metrics_raw = reports.get("metrics", {})
    validation = reports.get("validation", {})
    base = {
        "algorithm": meta.get("algorithm", "RF+XGB+LGBM_soft_voting"),
        "contract": meta.get("feature_contract", "advanced"),
        "n_features": n_features,
        "metrics": _clean_metrics(metrics_raw),
        "validation": validation,
        "validation_summary": _validation_summary(validation),
        "global_importance": gi,
        "eval": _model_eval(metrics_raw),
        "models": _per_model_metrics(metrics_raw),
    }

    roc = _roc_points()
    if roc:
        base["roc"] = roc

    eda = _eda_summary()
    if eda:
        base["eda"] = eda

    feature_groups = _feature_group_importance()
    if feature_groups:
        base["feature_groups"] = feature_groups

    confidence_bins = _confidence_bins()
    if confidence_bins:
        base["confidence_bins"] = confidence_bins

    return base
