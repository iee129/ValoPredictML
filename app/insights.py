from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


_RATE_FEATURE_TOKENS = (
    "kast",
    "hs",
    "wr",
    "rate",
    "advantage",
)

_FEATURE_LABELS: dict[str, str] = {
    "diff_avg_acs": "평균 ACS 차이",
    "diff_avg_kd": "평균 K/D 차이",
    "diff_avg_kast": "평균 KAST 차이",
    "diff_avg_adr": "평균 ADR 차이",
    "diff_avg_hs": "평균 헤드샷 비율 차이",
    "diff_map_wr": "맵별 요원 승률 차이",
    "diff_h2h_wr": "상대 전적 승률 차이",
    "diff_team_wr": "팀 전체 승률 차이",
    "a_avg_acs": "Team A 평균 ACS",
    "b_avg_acs": "Team B 평균 ACS",
    "a_avg_kd": "Team A 평균 K/D",
    "b_avg_kd": "Team B 평균 K/D",
    "a_avg_kast": "Team A 평균 KAST",
    "b_avg_kast": "Team B 평균 KAST",
    "a_avg_adr": "Team A 평균 ADR",
    "b_avg_adr": "Team B 평균 ADR",
    "a_avg_hs": "Team A 평균 헤드샷 비율",
    "b_avg_hs": "Team B 평균 헤드샷 비율",
    "a_fk_fd_ratio": "Team A 선제 교전 지표",
    "b_fk_fd_ratio": "Team B 선제 교전 지표",
    "a_avg_assists": "Team A 평균 어시스트",
    "b_avg_assists": "Team B 평균 어시스트",
    "a_kast_std": "Team A KAST 편차",
    "b_kast_std": "Team B KAST 편차",
    "a_avg_agent_map_wr": "Team A 요원-맵 평균 승률",
    "b_avg_agent_map_wr": "Team B 요원-맵 평균 승률",
    "a_avg_agent_pick_rate": "Team A 요원-맵 픽률",
    "b_avg_agent_pick_rate": "Team B 요원-맵 픽률",
    "a_avg_agent_exp": "Team A 선수-요원 경험",
    "b_avg_agent_exp": "Team B 선수-요원 경험",
    "a_map_wr_mean": "Team A 맵별 요원 승률",
    "b_map_wr_mean": "Team B 맵별 요원 승률",
    "a_duelist": "Team A 타격대 수",
    "b_duelist": "Team B 타격대 수",
    "a_initiator": "Team A 척후대 수",
    "b_initiator": "Team B 척후대 수",
    "a_controller": "Team A 전략가 수",
    "b_controller": "Team B 전략가 수",
    "a_sentinel": "Team A 감시자 수",
    "b_sentinel": "Team B 감시자 수",
    "diff_duelist": "타격대 수 차이",
    "diff_initiator": "척후대 수 차이",
    "diff_controller": "전략가 수 차이",
    "diff_sentinel": "감시자 수 차이",
    "a_double_initiator": "Team A 2척후 조합",
    "b_double_initiator": "Team B 2척후 조합",
    "atk_side_advantage": "맵 공격 유리도",
    "is_attacker_a": "Team A 선공 여부",
    "map_encoded": "맵 인코딩",
    "a_team_wr": "Team A 전체 승률",
    "b_team_wr": "Team B 전체 승률",
    "a_team_recent_wr": "Team A 최근 승률",
    "b_team_recent_wr": "Team B 최근 승률",
    "a_win_streak": "Team A 연승/연패",
    "b_win_streak": "Team B 연승/연패",
    "a_h2h_wr": "Team A 상대 전적 승률",
    "b_h2h_wr": "Team B 상대 전적 승률",
}

_DELTA_SCALES: dict[str, float] = {
    "acs": 20.0,
    "adr": 10.0,
    "kd": 0.15,
    "kast": 0.03,
    "hs": 0.03,
    "fk_fd_ratio": 0.25,
    "assists": 1.0,
    "wr": 0.03,
    "rate": 0.05,
    "exp": 3.0,
}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _feature_label(feature: str) -> str:
    return _FEATURE_LABELS.get(feature, feature)


def _feature_value(features: pd.DataFrame, feature: str) -> float | None:
    if feature not in features.columns or features.empty:
        return None
    try:
        return float(features.iloc[0][feature])
    except (TypeError, ValueError):
        return None


def _format_value(feature: str, value: float | None) -> str:
    if value is None:
        return "값 없음"
    if any(token in feature for token in _RATE_FEATURE_TOKENS) and abs(value) <= 2:
        return f"{value * 100:.1f}%"
    if abs(value - round(value)) < 1e-9 and abs(value) < 20:
        return f"{int(round(value))}"
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _impact_word(shap_value: float) -> str:
    return "높이는" if shap_value >= 0 else "낮추는"


def _describe_diff_factor(feature: str, shap_value: float, feature_value: float | None) -> str:
    label = _feature_label(feature).replace(" 차이", "")
    if feature_value is None or abs(feature_value) < 1e-9:
        state = f"{label}가 거의 같고"
    elif feature_value > 0:
        state = f"Team A의 {label}가 더 높고"
    else:
        state = f"Team B의 {label}가 더 높고"
    return f"{state}, 모델은 이를 Team A 승률을 {_impact_word(shap_value)} 요인으로 봤습니다."


def describe_factor(feature: str, shap_value: float, feature_value: float | None = None) -> str:
    if feature.startswith("diff_"):
        return _describe_diff_factor(feature, shap_value, feature_value)

    label = _feature_label(feature)
    value_text = _format_value(feature, feature_value)
    if feature.startswith("a_"):
        return f"{label}({value_text})가 Team A 승률을 {_impact_word(shap_value)} 요인으로 작용했습니다."
    if feature.startswith("b_"):
        return f"{label}({value_text})가 Team A 승률을 {_impact_word(shap_value)} 요인으로 작용했습니다."
    return f"{label}({value_text})가 Team A 승률을 {_impact_word(shap_value)} 요인으로 해석됐습니다."


def enrich_top_factors(top_factors: list[dict], features: pd.DataFrame) -> list[dict]:
    enriched: list[dict] = []
    for factor in top_factors:
        feature = str(factor.get("feature", ""))
        if not feature:
            continue
        shap_value = float(factor.get("value", 0.0))
        feature_value = _feature_value(features, feature)
        enriched.append({
            "feature": feature,
            "label": _feature_label(feature),
            "value": shap_value,
            "feature_value": feature_value,
            "feature_value_display": _format_value(feature, feature_value),
            "description": describe_factor(feature, shap_value, feature_value),
        })
    return enriched


def split_factor_insights(enriched_factors: list[dict], limit: int = 3) -> tuple[list[str], list[str]]:
    favorable = [f["description"] for f in enriched_factors if float(f.get("value", 0.0)) >= 0][:limit]
    risks = [f["description"] for f in enriched_factors if float(f.get("value", 0.0)) < 0][:limit]
    return favorable, risks


def _delta_scale(feature: str) -> float:
    for token, scale in _DELTA_SCALES.items():
        if token in feature:
            return scale
    return 1.0


def describe_feature_changes(
    before: pd.DataFrame,
    after: pd.DataFrame,
    shap_values: dict[str, float] | None = None,
    limit: int = 3,
) -> list[str]:
    if before.empty or after.empty:
        return []

    rows: list[tuple[float, str]] = []
    shap_values = shap_values or {}
    for feature in before.columns:
        try:
            before_value = float(before.iloc[0][feature])
            after_value = float(after.iloc[0][feature])
        except (TypeError, ValueError):
            continue

        delta = after_value - before_value
        if abs(delta) < 1e-9:
            continue

        normalized_delta = abs(delta) / _delta_scale(feature)
        shap_weight = 1.0 + min(abs(float(shap_values.get(feature, 0.0))) * 10.0, 3.0)
        score = normalized_delta * shap_weight
        direction = "상승" if delta > 0 else "하락"
        sentence = (
            f"{_feature_label(feature)}가 {_format_value(feature, before_value)}에서 "
            f"{_format_value(feature, after_value)}로 {direction}했습니다."
        )
        rows.append((score, sentence))

    rows.sort(key=lambda item: item[0], reverse=True)
    return [sentence for _, sentence in rows[:limit]]


def load_vlr_evidence(
    reports_dir: Path = Path("reports"),
) -> dict[str, Any] | None:
    summary_path = reports_dir / "vlrgg_ingestion_summary.json"
    if not summary_path.exists():
        return None

    summary = _read_json(summary_path)
    rows = summary.get("rows", {})
    if not isinstance(rows, dict):
        rows = {}

    readiness_path = reports_dir / "vlrgg_pipeline_readiness.json"
    readiness = _read_json(readiness_path) if readiness_path.exists() else {}
    numeric_rows = [int(v) for v in rows.values() if isinstance(v, (int, float))]

    return {
        "summary_path": str(summary_path),
        "readiness_path": str(readiness_path) if readiness_path.exists() else "",
        "generated_at": summary.get("generated_at", ""),
        "total_rows": sum(numeric_rows),
        "rows": rows,
        "sources": summary.get("sources", {}),
        "retrieval_methods": summary.get("retrieval_methods", {}),
        "pipeline_ready": bool(readiness.get("ready_for_pipeline", False)),
        "pipeline_matches": int(readiness.get("accepted_rows", rows.get("vlrgg_pipeline_matches", 0) or 0)),
    }
