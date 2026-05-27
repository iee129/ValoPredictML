"""vct_dataset 6년치 CSV 통합 로더.

읽기 전용. 어떤 파일도 수정하지 않는다.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from config import VCT_DATASET_ROOT, YEARS

MATCH_KEY_COLS = ["Tournament", "Stage", "Match Type", "Match Name"]


def _year_dir(year: int) -> Path:
    return VCT_DATASET_ROOT / f"vct_{year}"


def load_overview(years: list[int] | None = None) -> pd.DataFrame:
    """6년치 overview.csv concat. row = (매치, 맵, 선수)."""
    years = years or YEARS
    dfs = []
    for y in years:
        path = _year_dir(y) / "matches" / "overview.csv"
        if not path.exists():
            print(f"[data_load] missing {path}, skip", file=sys.stderr)
            continue
        df = pd.read_csv(path, low_memory=False)
        df["year"] = y
        dfs.append(df)
    if not dfs:
        raise FileNotFoundError("no overview.csv found")
    out = pd.concat(dfs, ignore_index=True)
    print(f"[data_load] overview: {len(out):,} rows from {len(dfs)} years",
          file=sys.stderr)
    return out


def load_maps_scores(years: list[int] | None = None) -> pd.DataFrame:
    """6년치 maps_scores.csv concat. row = (매치, 맵)."""
    years = years or YEARS
    dfs = []
    for y in years:
        path = _year_dir(y) / "matches" / "maps_scores.csv"
        if not path.exists():
            print(f"[data_load] missing {path}, skip", file=sys.stderr)
            continue
        df = pd.read_csv(path, low_memory=False)
        df["year"] = y
        dfs.append(df)
    if not dfs:
        raise FileNotFoundError("no maps_scores.csv found")
    out = pd.concat(dfs, ignore_index=True)
    print(f"[data_load] maps_scores: {len(out):,} rows from {len(dfs)} years",
          file=sys.stderr)
    return out


def _build_player_name_map(df: pd.DataFrame) -> dict[str, str]:
    """연도순으로 정렬 후, 소문자 기준으로 가장 최근에 쓰인 표기를 canonical로 반환.

    예: f0rsakeN(2022) → f0rsaken(2024) 이면 f0rsaken 이 정규 표기.
    """
    name_map: dict[str, str] = {}
    for name in df.sort_values("year")["Player"].dropna():
        name_map[str(name).lower()] = str(name)
    return name_map


def filter_overview_per_player_map(overview: pd.DataFrame) -> pd.DataFrame:
    """overview에서 (선수, 맵) 단위 1행만 남긴다.

    - Side == "both" 만 사용 (attack/defend는 같은 stat의 사이드 분할이라 중복)
    - Map == "All Maps" 는 토너먼트 집계라 (매치, 맵) 키와 안 맞음 — drop
    - Map NaN drop
    - Player 이름: 소문자 기준으로 가장 최근 표기로 정규화
    """
    n0 = len(overview)
    df = overview[overview["Side"] == "both"].copy()
    df = df[df["Map"].notna()]
    df = df[df["Map"] != "All Maps"]
    name_map = _build_player_name_map(df)
    df["Player"] = df["Player"].map(lambda x: name_map.get(str(x).lower(), x))
    print(f"[data_load] overview filtered to per-(player, map): "
          f"{n0:,} -> {len(df):,} rows", file=sys.stderr)
    return df


def load_match_ids() -> pd.DataFrame:
    """all_ids/all_matches_games_ids.csv 로드. (매치, 맵) → Match ID + Game ID."""
    path = VCT_DATASET_ROOT / "all_ids" / "all_matches_games_ids.csv"
    df = pd.read_csv(path, low_memory=False)
    print(f"[data_load] match_ids: {len(df):,} rows", file=sys.stderr)
    return df


def attach_ids_to_maps_scores(
    maps_scores: pd.DataFrame, match_ids: pd.DataFrame
) -> pd.DataFrame:
    """maps_scores에 Match ID + Game ID 부착. 결합 키 = (Tournament, Stage, Match Type, Match Name, Map)."""
    keys = MATCH_KEY_COLS + ["Map"]
    needed = keys + ["Match ID", "Game ID"]
    rhs = match_ids[needed].drop_duplicates(keys)
    merged = maps_scores.merge(rhs, on=keys, how="left")
    n_missing = merged["Match ID"].isna().sum()
    if n_missing:
        print(f"[data_load] WARN maps_scores rows without Match ID: {n_missing}",
              file=sys.stderr)
    return merged


def attach_ids_to_overview(
    overview: pd.DataFrame, match_ids: pd.DataFrame
) -> pd.DataFrame:
    """overview에 Match ID + Game ID 부착. (매치, 맵) 키."""
    keys = MATCH_KEY_COLS + ["Map"]
    needed = keys + ["Match ID", "Game ID"]
    rhs = match_ids[needed].drop_duplicates(keys)
    merged = overview.merge(rhs, on=keys, how="left")
    n_missing = merged["Match ID"].isna().sum()
    if n_missing:
        print(f"[data_load] WARN overview rows without Match ID: {n_missing}",
              file=sys.stderr)
    return merged


def load_kills_stats(years: list[int] | None = None) -> pd.DataFrame:
    """6년치 kills_stats.csv concat. row = (매치, 맵, 선수). 1v1~1v5 컬럼 보유."""
    years = years or YEARS
    dfs = []
    for y in years:
        path = _year_dir(y) / "matches" / "kills_stats.csv"
        if not path.exists():
            print(f"[data_load] missing {path}, skip", file=sys.stderr)
            continue
        df = pd.read_csv(path, low_memory=False)
        df["year"] = y
        dfs.append(df)
    if not dfs:
        raise FileNotFoundError("no kills_stats.csv found")
    out = pd.concat(dfs, ignore_index=True)
    print(f"[data_load] kills_stats: {len(out):,} rows from {len(dfs)} years",
          file=sys.stderr)
    return out


def filter_kills_stats_per_player_map(kills_stats: pd.DataFrame) -> pd.DataFrame:
    """kills_stats에서 (선수, 맵) 단위 1행만 남긴다.

    - Map == "All Maps" drop
    - Map NaN drop
    - Player 이름: 소문자 기준으로 가장 최근 표기로 정규화
    """
    n0 = len(kills_stats)
    df = kills_stats[kills_stats["Map"].notna()].copy()
    df = df[df["Map"] != "All Maps"]
    name_map = _build_player_name_map(df)
    df["Player"] = df["Player"].map(lambda x: name_map.get(str(x).lower(), x))
    print(f"[data_load] kills_stats filtered: "
          f"{n0:,} -> {len(df):,} rows", file=sys.stderr)
    return df


def rounds_per_map_lookup(maps_scores: pd.DataFrame,
                          match_ids: pd.DataFrame) -> dict:
    """(Match ID, Map) → 총 라운드 수.

    총 라운드 = Team A Score + Team B Score + OT (있으면).
    """
    ms = attach_ids_to_maps_scores(maps_scores, match_ids)
    ms = ms.dropna(subset=["Match ID", "Team A Score", "Team B Score"])
    a = ms["Team A Score"].fillna(0).astype(int)
    b = ms["Team B Score"].fillna(0).astype(int)
    ot_a = pd.to_numeric(ms.get("Team A Overtime Score"), errors="coerce").fillna(0).astype(int)
    ot_b = pd.to_numeric(ms.get("Team B Overtime Score"), errors="coerce").fillna(0).astype(int)
    total_rounds = a + b + ot_a + ot_b
    lookup = {}
    for mid, mp, r in zip(ms["Match ID"].astype(int),
                          ms["Map"], total_rounds):
        lookup[(mid, str(mp))] = int(r)
    return lookup


def clutch_lookup(kills_stats_with_ids: pd.DataFrame) -> dict:
    """(Match ID, Map, Player) → 클러치 승리 수 (1v1+1v2+1v3+1v4+1v5).

    kills_stats는 이미 attach_ids_to_overview류 join 끝났다고 가정.
    """
    df = kills_stats_with_ids.copy()
    for c in ["1v1", "1v2", "1v3", "1v4", "1v5"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df["clutch_wins"] = df["1v1"] + df["1v2"] + df["1v3"] + df["1v4"] + df["1v5"]
    df = df.dropna(subset=["Match ID"])
    df["Match ID"] = df["Match ID"].astype(int)
    lookup = {}
    for mid, mp, pl, cw in zip(df["Match ID"], df["Map"], df["Player"],
                                df["clutch_wins"].astype(int)):
        lookup[(int(mid), str(mp), str(pl))] = int(cw)
    return lookup


def attach_ids_to_kills_stats(kills_stats: pd.DataFrame,
                              match_ids: pd.DataFrame) -> pd.DataFrame:
    """kills_stats에 Match ID + Game ID 부착. (매치, 맵) 키."""
    keys = MATCH_KEY_COLS + ["Map"]
    needed = keys + ["Match ID", "Game ID"]
    rhs = match_ids[needed].drop_duplicates(keys)
    merged = kills_stats.merge(rhs, on=keys, how="left")
    n_missing = merged["Match ID"].isna().sum()
    if n_missing:
        print(f"[data_load] WARN kills_stats rows without Match ID: {n_missing}",
              file=sys.stderr)
    return merged


def load_player_ids() -> pd.DataFrame:
    """all_ids/all_players_ids.csv."""
    path = VCT_DATASET_ROOT / "all_ids" / "all_players_ids.csv"
    return pd.read_csv(path)


def load_team_ids() -> pd.DataFrame:
    """all_ids/all_teams_ids.csv."""
    path = VCT_DATASET_ROOT / "all_ids" / "all_teams_ids.csv"
    return pd.read_csv(path)


if __name__ == "__main__":
    mi = load_match_ids()
    ov = load_overview()
    ms = load_maps_scores()
    ov = filter_overview_per_player_map(ov)
    ov2 = attach_ids_to_overview(ov, mi)
    ms2 = attach_ids_to_maps_scores(ms, mi)
    print("overview rows with Match ID:",
          ov2["Match ID"].notna().sum(), "/", len(ov2))
    print("maps_scores rows with Match ID:",
          ms2["Match ID"].notna().sum(), "/", len(ms2))
    print("\noverview sample:")
    print(ov2[["year", "Match ID", "Game ID", "Map", "Player", "Team",
               "Agents", "Rating", "Average Combat Score"]].head(3))
    print("\nmaps_scores sample:")
    print(ms2[["year", "Match ID", "Map", "Team A", "Team A Score",
               "Team B", "Team B Score"]].head(3))
