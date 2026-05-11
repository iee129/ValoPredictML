from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from ml.vlrgg_client import VLRGGClient

_DEFAULT_STANDING_YEARS = list(range(2021, 2027))  # 2021-2026


def _default_client() -> "VLRGGClient":
    from ml.vlrgg_client import VLRGGClient
    return VLRGGClient(cache_dir=os.getenv("VLRGG_CACHE_DIR", "data/raw/vlrgg_cache"))


def load_vlrgg_stats(
    regions: list[str] | None = None,
    timespan: str = "30",
    client: "VLRGGClient | None" = None,
) -> pd.DataFrame:
    """여러 지역의 선수 통계를 DataFrame으로 로드합니다.

    Args:
        regions: 수집할 지역 목록. None이면 주요 5개 지역 ('na','eu','ap','la','kr').
        timespan: '30', '60', '90', 'all'

    Returns:
        컬럼: region, player, org, agents, rounds_played, rating,
              average_combat_score, kill_deaths, headshot_percentage 등
    """
    if regions is None:
        regions = ["na", "eu", "ap", "la", "kr"]
    c = client or _default_client()

    rows: list[dict] = []
    for region in regions:
        data = c.fetch_stats(region, timespan)
        if data:
            for row in data:
                rows.append({"region": region, **row})

    return pd.DataFrame(rows)


def load_vlrgg_events(
    q: str = "completed",
    pages: int = 1,
    client: "VLRGGClient | None" = None,
) -> pd.DataFrame:
    """완료/예정 이벤트 목록을 DataFrame으로 로드합니다.

    Returns:
        컬럼: title, status, prize, dates, region, url_path, event_id
    """
    from ml.vlrgg_client import VLRGGClient

    c = client or _default_client()
    rows: list[dict] = []

    for page in range(1, pages + 1):
        data = c.fetch_events(q=q, page=page)
        if not data:
            break
        for row in data:
            event_id = VLRGGClient.extract_event_id(row.get("url_path", ""))
            rows.append({**row, "event_id": event_id})

    return pd.DataFrame(rows)


def load_vlrgg_season_data(
    regions: list[str] | None = None,
    timespans: list[str] | None = None,
    client: "VLRGGClient | None" = None,
) -> pd.DataFrame:
    """여러 지역 × 기간 조합의 선수 통계를 통합 DataFrame으로 반환합니다.

    Args:
        regions: 지역 목록. None이면 ('na','eu','ap').
        timespans: 기간 목록. None이면 ('30', '90', 'all').

    Returns:
        region, timespan, player, ... 컬럼 포함 통합 DataFrame
    """
    if regions is None:
        regions = ["na", "eu", "ap"]
    if timespans is None:
        timespans = ["30", "90", "all"]

    c = client or _default_client()
    frames: list[pd.DataFrame] = []

    for timespan in timespans:
        df = load_vlrgg_stats(regions=regions, timespan=timespan, client=c)
        if not df.empty:
            df["timespan"] = timespan
            frames.append(df)

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def load_vlrgg_standings(
    years: list[int] | None = None,
) -> pd.DataFrame:
    """VCT 연도별 팀 스탠딩을 수집해 DataFrame으로 반환합니다.

    Args:
        years: 수집할 연도 목록. None이면 2021-2026.

    Returns:
        컬럼: year, region, rank, team, team_id, points, country
    """
    from ml.vlrgg_scraper import scrape_standings

    if years is None:
        years = _DEFAULT_STANDING_YEARS

    rows: list[dict] = []
    for year in years:
        rows.extend(scrape_standings(year))

    return pd.DataFrame(rows)


def load_vlrgg_match_details(
    match_ids: list[int | str],
) -> pd.DataFrame:
    """매치 상세 페이지에서 게임별 agent pick을 수집합니다.

    Args:
        match_ids: VLR.gg 매치 ID 목록

    Returns:
        컬럼: match_id, game_id, map, team_a, team_b, agents_a (list), agents_b (list)
    """
    from ml.vlrgg_scraper import scrape_match_detail

    rows: list[dict] = []
    for mid in match_ids:
        rows.extend(scrape_match_detail(mid))

    return pd.DataFrame(rows)


def load_vlrgg_event_matches(
    event_id: int | str,
    pages: int = 1,
) -> pd.DataFrame:
    """이벤트별 매치 목록을 수집해 DataFrame으로 반환합니다.

    Args:
        event_id: VLR.gg 이벤트 ID
        pages: 수집할 페이지 수 (기본 1)

    Returns:
        컬럼: event_id, match_id, team_a, team_b, score_a, score_b, date
    """
    from ml.vlrgg_scraper import scrape_event_matches

    rows: list[dict] = []
    for page in range(1, pages + 1):
        batch = scrape_event_matches(event_id, page)
        if not batch:
            break
        rows.extend(batch)

    return pd.DataFrame(rows)


def load_vlrgg_team_stats(
    team_ids: list[int | str],
) -> pd.DataFrame:
    """팀별 맵 통계를 수집해 DataFrame으로 반환합니다.

    Args:
        team_ids: VLR.gg 팀 ID 목록

    Returns:
        컬럼: team_id, map, games, win_rate, wins, losses,
              atk_first, def_first, atk_rwin_pct, atk_rw, atk_rl,
              def_rwin_pct, def_rw, def_rl
    """
    from ml.vlrgg_scraper import scrape_team_stats

    rows: list[dict] = []
    for tid in team_ids:
        rows.extend(scrape_team_stats(tid))

    return pd.DataFrame(rows)


def load_vlrgg_research_outputs(processed_dir: str | Path = "data/processed") -> dict[str, pd.DataFrame]:
    """Load generated VLR research artifacts without touching the network."""
    root = Path(processed_dir)
    files = {
        "matches": root / "vlrgg_matches.csv",
        "player_stats": root / "vlrgg_player_stats.csv",
        "agent_map_stats": root / "vlrgg_agent_map_stats.csv",
    }
    return {
        name: pd.read_csv(path, low_memory=False) if path.exists() else pd.DataFrame()
        for name, path in files.items()
    }


# 하위 호환 — US-003 초기 골격 시그니처 유지
def load_vlrgg_event_stats(
    event_id: int | str,
    event_slug: str,
    client: "VLRGGClient | None" = None,
) -> dict:
    """단일 이벤트 stats. /stats API는 이벤트별 필터를 미지원 — region/timespan 기반 사용 권장."""
    raise NotImplementedError(
        "vlrggapi는 이벤트 ID별 stats를 미지원. "
        "load_vlrgg_stats(region, timespan) 또는 load_vlrgg_events()를 사용하세요."
    )
