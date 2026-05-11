"""ml/hypothesis_test.py — 도메인 가설 통계 검증 모듈 (US-005)."""
from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd
from scipy import stats

HYPOTHESIS_LIST = [
    {
        "id": "H-01",
        "description": "팀A의 ACS가 팀B보다 높으면 팀A 승률이 높다",
        "feature": "diff_avg_acs",
        "direction": "positive",
    },
    {
        "id": "H-02",
        "description": "팀A의 K/D 비율이 팀B보다 높으면 팀A 승률이 높다",
        "feature": "diff_avg_kd",
        "direction": "positive",
    },
    {
        "id": "H-03",
        "description": "팀A의 역대 H2H 승률이 팀B보다 높으면 실제로도 더 많이 이긴다",
        "feature": "diff_h2h_wr",
        "direction": "positive",
    },
    {
        "id": "H-04",
        "description": "시즌 전체 승률이 높은 팀이 경기에서도 더 많이 이긴다",
        "feature": "diff_team_wr",
        "direction": "positive",
    },
    {
        "id": "H-05",
        "description": "연승 중인 팀A(a_win_streak 양수)가 연패 팀보다 승률이 높다",
        "feature": "a_win_streak",
        "direction": "positive",
    },
    {
        "id": "H-06",
        "description": "공격 유리 맵에서 공격 측(atk_side_advantage × is_attacker_a)이 승률 높다",
        "feature": None,
        "direction": "positive",
        "interaction": ("atk_side_advantage", "is_attacker_a"),
    },
    {
        "id": "H-07",
        "description": "척후대(Initiator) 2명 이상 보유 팀A가 그렇지 않은 경우보다 승률이 높다",
        "feature": "a_double_initiator",
        "direction": "positive",
    },
    {
        "id": "H-08",
        "description": "Controller를 보유한 팀A(a_controller >= 1)가 없는 경우보다 승률이 높다",
        "feature": "a_controller",
        "direction": "positive",
    },
    {
        "id": "H-09",
        "description": "팀A의 맵 역사적 승률이 팀B보다 높으면 실제 승률도 높다",
        "feature": "diff_map_wr",
        "direction": "positive",
    },
    {
        "id": "H-10",
        "description": "팀A의 ADR이 팀B보다 높으면 팀A 승률이 높다",
        "feature": "diff_avg_adr",
        "direction": "positive",
    },
    {
        "id": "H-11",
        "description": "팀A의 KAST가 팀B보다 높으면 팀A 승률이 높다",
        "feature": "diff_avg_kast",
        "direction": "positive",
    },
    {
        "id": "H-12",
        "description": "공격 측 어드밴티지가 높은 맵일수록 공격팀 승률과 상관이 있다",
        "feature": "atk_side_advantage",
        "direction": "any",
    },
]


def _point_biserial(feature_vals: pd.Series, labels: pd.Series) -> tuple[float, float]:
    mask = feature_vals.notna() & labels.notna()
    if mask.sum() < 10:
        return float("nan"), float("nan")
    r, p = stats.pointbiserialr(feature_vals[mask], labels[mask])
    return float(r), float(p)


def test_hypotheses(df: pd.DataFrame) -> list[dict]:
    """도메인 가설을 데이터로 검증하여 결과 리스트를 반환.

    Args:
        df: feature 컬럼과 'label' 컬럼을 포함한 DataFrame

    Returns:
        각 가설별 {id, description, test, test_stat, p_value, direction, supported} dict 리스트
    """
    results: list[dict] = []

    for hyp in HYPOTHESIS_LIST:
        hid = hyp["id"]
        desc = hyp["description"]
        direction = hyp.get("direction", "any")

        if hyp.get("interaction"):
            f1, f2 = hyp["interaction"]
            if f1 not in df.columns or f2 not in df.columns or "label" not in df.columns:
                results.append({"id": hid, "description": desc, "status": "missing_columns"})
                continue
            feature_vals = df[f1] * df[f2]
        else:
            feature = hyp.get("feature")
            if feature not in df.columns or "label" not in df.columns:
                results.append({"id": hid, "description": desc, "status": "missing_columns"})
                continue
            feature_vals = df[feature]

        r, p = _point_biserial(feature_vals, df["label"])
        if math.isnan(r):
            results.append({"id": hid, "description": desc, "status": "insufficient_data"})
            continue

        if direction == "positive":
            supported = bool(p < 0.05 and r > 0)
        elif direction == "negative":
            supported = bool(p < 0.05 and r < 0)
        else:
            supported = bool(p < 0.05)

        results.append({
            "id": hid,
            "description": desc,
            "test": "point_biserial",
            "test_stat": round(r, 4),
            "p_value": round(p, 4),
            "direction": direction,
            "supported": supported,
        })

    return results


def report_hypotheses(df: pd.DataFrame, output_path: str) -> None:
    """가설 검증 결과를 JSON 파일로 저장.

    Args:
        df: feature 컬럼과 'label' 컬럼을 포함한 DataFrame
        output_path: 저장할 JSON 파일 경로
    """
    results = test_hypotheses(df)
    supported = sum(1 for r in results if r.get("supported"))
    output = {
        "n_hypotheses": len(results),
        "n_supported": supported,
        "n_rows": len(df),
        "results": results,
    }
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
