"""features.py + 역할 조합 prior 6개 피처 (role_combo.py).

기존 assemble_features 무수정 원칙. 이 모듈은 assemble_features_v4 만 export.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from src.features import (
    META_COLS,
    _map_one_hot,
    _slot_features,
    _sort_team_players,
)
from src.role_combo import get_priors, new_state, roles_from_side, update_state

META_COLS_V4 = META_COLS  # 학습 시 drop 목록 동일


def assemble_features_v4(priors_df: pd.DataFrame):
    """priors → (feat_df, role_combo_state).

    feat_df : v1 피처 415개 + role_combo 6개 = 421개
    role_combo_state : predict_v4 inference 에서 재사용 가능한 누적 상태 dict
    """
    combo_state = new_state()
    out_rows = []
    n_skipped = 0

    for (mid, mp), grp in priors_df.groupby(["match_id", "map"], sort=False):
        side_a = grp[grp["is_team_a"] == 1]
        side_b = grp[grp["is_team_a"] == 0]
        if len(side_a) < 5 or len(side_b) < 5:
            n_skipped += 1
            continue

        side_a_sorted = _sort_team_players(side_a).head(5)
        side_b_sorted = _sort_team_players(side_b).head(5)
        winner = int(grp["winner"].iloc[0])

        # 역할 조합 prior (이 매치 이전 누적값)
        a_roles = roles_from_side(side_a)
        b_roles = roles_from_side(side_b)
        rc_feats = get_priors(combo_state, mp, a_roles, b_roles)

        row = {
            "year": int(grp["year"].iloc[0]),
            "winner": winner,
        }

        for i in range(5):
            row.update(_slot_features(side_a_sorted.iloc[i], "a", i))
            row.update(_slot_features(side_b_sorted.iloc[i], "b", i))

        row["a_team_co_play_sum"] = int(side_a.iloc[0]["team_co_play_sum"])
        row["b_team_co_play_sum"] = int(side_b.iloc[0]["team_co_play_sum"])
        row["d_team_co_play_sum"] = row["a_team_co_play_sum"] - row["b_team_co_play_sum"]
        row.update(_map_one_hot(mp))
        row.update(rc_feats)

        # 이 매치 결과 반영
        update_state(combo_state, mp, a_roles, b_roles, winner)

        out_rows.append(row)

    df = pd.DataFrame(out_rows)
    print(
        f"[features_v4] assembled {len(df):,} rows × {len(df.columns)} cols "
        f"(skipped {n_skipped} non-5v5)",
        file=sys.stderr,
    )
    return df, combo_state
