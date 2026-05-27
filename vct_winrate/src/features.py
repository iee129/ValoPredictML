"""per-(match, map, player) prior → per-(match, map) 슬롯 기반 피처.

옵션 B 슬롯 배정 (사용자 합의):
  팀 5명을 (역할 우선순위, prior_acs desc) 정렬 → 슬롯 1~5
  역할 우선순위: duelist(0) → initiator(1) → controller(2) → sentinel(3) → unknown(4)
  슬롯 라벨(개념적): 1선엔트리, 2선엔트리, 척후, 전략, 감시

슬롯 단위 피처 (× 5 슬롯 × 2 팀):
  - prior stat 8개: kd, kast, adr, acs, apr, fkpr, fdpr, clutch_pr
  - 요원 one-hot: 27개 (taxonomy.AGENT_ROLES 키 순)
  - 역할 one-hot: 5개 (duelist/initiator/controller/sentinel/unknown)

팀 단위 피처:
  - team_co_play_sum (priors.py에서 계산)

매치 단위 피처:
  - 맵 one-hot (12개)

레이블:
  - winner (1=A 승, 0=B 승)
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from src.taxonomy import AGENT_ROLES, MAP_LIST, POSITIONS, ROLES, agent_position

# 슬롯 정렬 우선순위 (5 포지션: duelist1/duelist2/initiator/controller/sentinel)
_POSITION_PRIORITY = {pos: i for i, pos in enumerate(POSITIONS)}
SLOT_LABELS = list(POSITIONS)  # duelist1, duelist2, initiator, controller, sentinel

# one-hot 카테고리
_AGENT_KEYS = sorted(AGENT_ROLES.keys())  # 27개 고정 순
_ROLE_KEYS = list(ROLES)                  # 5 (first_duelist, second_duelist, initiator, controller, sentinel)

STAT_COLS = ["prior_kd", "prior_kast", "prior_adr", "prior_acs",
             "prior_apr", "prior_fkpr", "prior_fdpr", "prior_clutch_pr"]


def _sort_team_players(side_df: pd.DataFrame) -> pd.DataFrame:
    """포지션(5종: entry1/entry2/initiator/controller/sentinel) 우선순위 + prior_acs 내림차순."""
    df = side_df.copy()
    df["__position"] = df["agent"].apply(agent_position)
    df["__pos_prio"] = df["__position"].map(_POSITION_PRIORITY).fillna(5)
    # NaN ACS는 -inf 취급해서 같은 포지션 내에선 뒤로
    df["__sort_acs"] = df["prior_acs"].fillna(-np.inf)
    df = df.sort_values(
        ["__pos_prio", "__sort_acs"], ascending=[True, False]
    ).reset_index(drop=True)
    return df.drop(columns=["__position", "__pos_prio", "__sort_acs"])


def _slot_features(slot_row, side_prefix: str, slot_idx: int) -> dict:
    """한 슬롯의 stat + 요원 one-hot + 역할 one-hot → dict."""
    out = {}
    slot_name = SLOT_LABELS[slot_idx]
    prefix = f"{side_prefix}_s{slot_idx + 1}_{slot_name}"

    if slot_row is None:
        out[f"{prefix}_player"] = None
        for s in STAT_COLS:
            out[f"{prefix}_{s}"] = np.nan
        for a in _AGENT_KEYS:
            out[f"{prefix}_agent_{a}"] = 0
        for r in _ROLE_KEYS:
            out[f"{prefix}_role_{r}"] = 0
        return out

    # 선수 이름 (메타, 학습 시 drop)
    out[f"{prefix}_player"] = slot_row["player"]

    # stat
    for s in STAT_COLS:
        out[f"{prefix}_{s}"] = slot_row[s]

    # 요원 one-hot
    agent = slot_row["agent"]
    for a in _AGENT_KEYS:
        out[f"{prefix}_agent_{a}"] = int(agent == a) if isinstance(agent, str) else 0

    # 역할 one-hot (4종). 미인식 요원이면 4개 다 0.
    role = slot_row["role"]
    for r in _ROLE_KEYS:
        out[f"{prefix}_role_{r}"] = int(role == r) if isinstance(role, str) else 0

    return out


def _map_one_hot(map_name: str) -> dict:
    return {f"map_is_{m}": int(map_name == m) for m in MAP_LIST}


def assemble_features(priors_df: pd.DataFrame) -> pd.DataFrame:
    """priors → per-(match, map) feature row. 5v5 아닌 그룹은 drop."""
    out_rows = []
    n_skipped_not_5v5 = 0
    for (mid, mp), grp in priors_df.groupby(["match_id", "map"], sort=False):
        side_a = grp[grp["is_team_a"] == 1]
        side_b = grp[grp["is_team_a"] == 0]
        if len(side_a) < 5 or len(side_b) < 5:
            n_skipped_not_5v5 += 1
            continue

        side_a_sorted = _sort_team_players(side_a).head(5)
        side_b_sorted = _sort_team_players(side_b).head(5)

        # year는 split.py가 분할에 사용. 저장 직전 preprocess.py가 drop함.
        # winner는 레이블.
        row = {
            "year": int(grp["year"].iloc[0]),
            "winner": int(grp["winner"].iloc[0]),
        }

        # 슬롯 피처 (5슬롯 × 2팀)
        for i in range(5):
            row.update(_slot_features(side_a_sorted.iloc[i], "a", i))
            row.update(_slot_features(side_b_sorted.iloc[i], "b", i))

        # 팀 단위 동반출전 (priors가 5명 모두에게 emit한 같은 값)
        row["a_team_co_play_sum"] = int(side_a.iloc[0]["team_co_play_sum"])
        row["b_team_co_play_sum"] = int(side_b.iloc[0]["team_co_play_sum"])
        row["d_team_co_play_sum"] = (
            row["a_team_co_play_sum"] - row["b_team_co_play_sum"])

        # 맵 one-hot
        row.update(_map_one_hot(mp))

        out_rows.append(row)

    df = pd.DataFrame(out_rows)
    print(f"[features] assembled {len(df):,} (match, map) rows "
          f"× {len(df.columns)} cols "
          f"(skipped {n_skipped_not_5v5} non-5v5 groups)", file=sys.stderr)
    return df


# 메타 컬럼 — CSV 검사용. 학습 시엔 X에서 모두 drop.
#   winner: 레이블
#   year:   연도 (분할/검사용)
#   *_player: 슬롯별 선수 이름 10개
META_COLS = ["winner", "year"] + [
    f"{side}_s{i + 1}_{label}_player"
    for side in ["a", "b"]
    for i, label in enumerate(SLOT_LABELS)
]


def feature_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c not in META_COLS]


if __name__ == "__main__":
    from src.data_load import (
        attach_ids_to_kills_stats,
        attach_ids_to_overview,
        clutch_lookup as build_clutch_lookup,
        filter_kills_stats_per_player_map,
        filter_overview_per_player_map,
        load_kills_stats,
        load_match_ids,
        load_maps_scores,
        load_overview,
        rounds_per_map_lookup,
    )
    from src.labels import build_labels
    from src.priors import compute_priors

    ov = load_overview()
    mi = load_match_ids()
    ms = load_maps_scores()
    ks = load_kills_stats()

    ov_filt = attach_ids_to_overview(filter_overview_per_player_map(ov), mi)
    ks_filt = attach_ids_to_kills_stats(filter_kills_stats_per_player_map(ks), mi)
    labels = build_labels(ms, mi)
    rounds = rounds_per_map_lookup(ms, mi)
    clutches = build_clutch_lookup(ks_filt)

    priors_df, state = compute_priors(ov_filt, labels, rounds, clutches)
    feat = assemble_features(priors_df)

    print(f"\nshape: {feat.shape}")
    print(f"feature cols: {len(feature_columns(feat))}")
    print("\n샘플 row:")
    print(feat.iloc[0][["match_id", "map", "winner", "team_a", "team_b",
                        "a_s1_entry1_prior_kd", "a_s1_entry1_prior_acs",
                        "a_s3_scout_prior_kd",
                        "a_team_co_play_sum", "b_team_co_play_sum"]])
    print("\nyear 분포:")
    print(feat["year"].value_counts().sort_index())
