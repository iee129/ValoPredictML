"""역할 조합 (map, role_combo, side) → leak-safe 누적 승률 + 빈도 prior.

추가 피처 6개:
  a_role_combo_map_winrate  — 팀 A 역할조합의 이 맵에서 A측으로 출전 시 누적 승률
  a_role_combo_map_count    — 팀 A 역할조합의 이 맵에서 누적 등장 횟수
  b_role_combo_map_winrate  — 팀 B 역할조합의 이 맵에서 B측으로 출전 시 누적 승률
  b_role_combo_map_count    — 팀 B 역할조합의 이 맵에서 누적 등장 횟수
  d_role_combo_map_winrate  — a_winrate - b_winrate
  d_role_combo_map_count    — a_count  - b_count

"3감시 이력 없음 = 비메타 = 약한 조합" 신호를 자연스럽게 학습:
  - 첫 등장 조합은 winrate=NaN, count=0 → Imputer가 median으로 채움
  - 자주 쓰인 메타 조합일수록 count가 크고 winrate가 안정적으로 수렴
"""
from __future__ import annotations

_ALPHA = 5  # 베이지안 스무딩 강도. count=0 → 0.5, count↑ → 실제 winrate 수렴


def new_state() -> dict:
    """(map, role_combo_tuple, side) → {"wins": int, "count": int}"""
    return {}


def get_priors(
    state: dict,
    map_name: str,
    a_roles: tuple,
    b_roles: tuple,
) -> dict:
    """현재 prior 6개 반환 (이 매치 처리 전 값).

    smoothed_winrate = (wins + α×0.5) / (count + α)
    count=0이면 0.5, count가 클수록 실제 winrate에 수렴. NaN 없음.
    """
    key_a = (map_name, a_roles, "a")
    key_b = (map_name, b_roles, "b")

    d_a = state.get(key_a, {"wins": 0, "count": 0})
    d_b = state.get(key_b, {"wins": 0, "count": 0})

    a_wr = (d_a["wins"] + _ALPHA * 0.5) / (d_a["count"] + _ALPHA)
    b_wr = (d_b["wins"] + _ALPHA * 0.5) / (d_b["count"] + _ALPHA)
    a_cnt = float(d_a["count"])
    b_cnt = float(d_b["count"])

    return {
        "a_role_combo_map_winrate": a_wr,
        "a_role_combo_map_count": a_cnt,
        "b_role_combo_map_winrate": b_wr,
        "b_role_combo_map_count": b_cnt,
        "d_role_combo_map_winrate": a_wr - b_wr,
        "d_role_combo_map_count": a_cnt - b_cnt,
    }


def update_state(
    state: dict,
    map_name: str,
    a_roles: tuple,
    b_roles: tuple,
    winner: int,
) -> None:
    """이 매치 결과로 state 업데이트. winner=1: A승, 0: B승."""
    key_a = (map_name, a_roles, "a")
    key_b = (map_name, b_roles, "b")

    if key_a not in state:
        state[key_a] = {"wins": 0, "count": 0}
    if key_b not in state:
        state[key_b] = {"wins": 0, "count": 0}

    state[key_a]["count"] += 1
    state[key_a]["wins"] += int(winner == 1)
    state[key_b]["count"] += 1
    state[key_b]["wins"] += int(winner == 0)


def roles_from_side(side_df) -> tuple:
    """팀 DataFrame의 role 컬럼 → sorted tuple."""
    return tuple(sorted(str(r) for r in side_df["role"].fillna("unknown")))
