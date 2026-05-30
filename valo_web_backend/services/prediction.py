"""app.predict 얇은 래퍼 + 캐시. docs_web/02_backend_fastapi/02_model_serving.md."""
from __future__ import annotations

from functools import lru_cache

import pandas as pd

from app.predict import (
    DEFAULT_ADVANCED_DIR,
    available_options,
    load_model,
    map_label,
)


def warmup() -> None:
    """콜드스타트 비용을 startup에서 흡수(실패해도 서버는 뜬다)."""
    try:
        load_model()
    except Exception:
        pass
    try:
        options_bundle()
    except Exception:
        pass


@lru_cache(maxsize=1)
def options_bundle() -> dict:
    """available_options() 결과 캐시 (maps/agents/players/years/replay_matches)."""
    return available_options()


@lru_cache(maxsize=8)
def replay_list(limit: int = 200) -> tuple:
    """test.csv에서 다시보기 후보 경기 목록(메타 포함). 모델 추론 없음."""
    test = pd.read_csv(DEFAULT_ADVANCED_DIR / "test.csv", low_memory=False)
    rows: list[dict] = []
    for row in test.head(limit).itertuples(index=False):
        match_key = str(getattr(row, "match_key"))
        date = str(getattr(row, "date", "") or "")
        map_name = str(getattr(row, "map", "") or "")
        team_a = str(getattr(row, "team_a", "Team A") or "Team A")
        team_b = str(getattr(row, "team_b", "Team B") or "Team B")
        rows.append({
            "match_key": match_key,
            "label": f"{date} | {map_label(map_name)} | {team_a} vs {team_b} | {match_key}",
            "date": date,
            "map": map_name,
            "team_a": team_a,
            "team_b": team_b,
        })
    return tuple(rows)   # lru_cache는 해시 가능한 반환값 필요 → tuple
