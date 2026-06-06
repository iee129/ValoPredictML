"""inference.predict 얇은 래퍼 + 캐시. docs/08_web/02_backend_fastapi/02_model_serving.md."""
from __future__ import annotations

import logging
from functools import lru_cache

import pandas as pd

from inference.predict import (
    DEFAULT_ADVANCED_DIR,
    available_options,
    load_model,
    map_label,
    predict_custom_lineup,
)

logger = logging.getLogger(__name__)


def warmup() -> None:
    """콜드스타트 비용을 startup에서 흡수(실패해도 서버는 뜬다)."""
    try:
        load_model()
    except Exception as exc:
        logger.warning("model warmup skipped: %s", exc)
    try:
        options = options_bundle()
    except Exception as exc:
        logger.warning("options warmup skipped: %s", exc)
        return

    try:
        maps = list(options.get("maps") or [])
        years = list(options.get("years") or [])
        players = list(options.get("players") or [])
        agents = list(dict.fromkeys(options.get("agents") or []))
        if not maps or not years or len(players) < 10 or len(agents) < 10:
            logger.warning(
                "predict warmup skipped: insufficient options "
                "(maps=%d, years=%d, players=%d, agents=%d)",
                len(maps), len(years), len(players), len(agents),
            )
            return
        team_a = [
            {"player": player, "agent": agent}
            for player, agent in zip(players[:5], agents[:5])
        ]
        team_b = [
            {"player": player, "agent": agent}
            for player, agent in zip(players[5:10], agents[5:10])
        ]
        predict_custom_lineup(
            map_name=maps[0],
            cutoff_year=int(years[-1]),
            team_a_slots=team_a,
            team_b_slots=team_b,
        )
    except Exception as exc:
        logger.warning("predict warmup skipped: %s", exc)


@lru_cache(maxsize=1)
def options_bundle() -> dict:
    """available_options() 결과 캐시 (maps/agents/players/years/replay_matches)."""
    return available_options()


def _clean(value, fallback: str = "") -> str:
    """NaN/None/빈값을 fallback으로. (date 결측이 'nan' 문자열로 새는 것 방지)"""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return fallback
    text = str(value).strip()
    return text if text and text.lower() != "nan" else fallback


def _label_to_winner(value) -> tuple[int | None, str | None]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None, None
    try:
        label = int(value)
    except (TypeError, ValueError):
        return None, None
    if label not in (0, 1):
        return None, None
    return label, "A" if label == 1 else "B"


@lru_cache(maxsize=1)
def _replay_index() -> tuple:
    """test.csv 전체 경기 메타(검색용). 모델 추론 없음. 프로세스당 1회만 로드해 캐시."""
    test = pd.read_csv(DEFAULT_ADVANCED_DIR / "test.csv", low_memory=False)
    rows: list[dict] = []
    for row in test.itertuples(index=False):
        match_key = _clean(getattr(row, "match_key", ""))
        date = _clean(getattr(row, "date", ""))
        map_name = _clean(getattr(row, "map", ""))
        team_a = _clean(getattr(row, "team_a", ""), "Team A")
        team_b = _clean(getattr(row, "team_b", ""), "Team B")
        actual_label, actual_winner = _label_to_winner(getattr(row, "label", None))
        rows.append({
            "match_key": match_key,
            "label": f"{date} | {map_label(map_name)} | {team_a} vs {team_b} | {match_key}",
            "date": date,
            "map": map_name,
            "team_a": team_a,
            "team_b": team_b,
            "actual_label": actual_label,
            "actual_winner": actual_winner,
            # 검색용 소문자 건초더미(팀/맵/날짜/키) — 응답에는 포함하지 않음
            "_haystack": f"{team_a} {team_b} {map_name} {date} {match_key}".lower(),
        })
    return tuple(rows)   # lru_cache는 해시 가능한 반환값 필요 → tuple


def replay_query(q: str = "", limit: int = 200) -> tuple[list, int]:
    """전체 test 경기에서 q(팀/맵/날짜/키, 공백=AND)로 필터. (상위 limit 항목, 전체 일치 수) 반환.

    q가 비면 전체를 대상으로 하되 상위 limit만 돌려준다(프런트는 빈 검색을 숨김 처리).
    """
    index = _replay_index()
    needle = (q or "").strip().lower()
    if needle:
        terms = needle.split()
        matched = [r for r in index if all(t in r["_haystack"] for t in terms)]
    else:
        matched = list(index)
    total = len(matched)
    items = [
        {k: v for k, v in r.items() if k != "_haystack"}
        for r in matched[: max(0, limit)]
    ]
    return items, total
