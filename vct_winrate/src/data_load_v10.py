"""VCT + VCL Challengers 통합 데이터 로더 (v10).

VCL 데이터는 컬럼 구조가 VCT와 완전히 동일하므로 concat 후 합성 Match ID 부여.

VCL 합성 Match ID: 1_000_000 + index  (VCT 최대 ~626,550 → 충분한 offset)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from src.data_load import (
    MATCH_KEY_COLS,
    load_kills_stats,
    load_maps_scores,
    load_match_ids,
    load_overview,
)

# ───────── VCL 경로 ─────────
_HERE = Path(__file__).resolve().parent          # vct_winrate/src/
VCL_DATASET_ROOT = (
    _HERE.parent.parent                          # 기계학습 프로젝트 모듈 팀플/
    / "more dataset"
    / "ryanluong1__valorant-challengers-league-data"
)
VCL_YEARS = [2023, 2024]


def _vcl_dir(year: int) -> Path:
    return VCL_DATASET_ROOT / f"vcl_{year}"


# ───────── 합성 Match ID 생성 (연도별 시간순 보존) ─────────

def _build_vcl_match_ids(
    vcl_maps_scores: pd.DataFrame,
    vct_match_ids: pd.DataFrame,
) -> pd.DataFrame:
    """VCL maps_scores 유니크 키 → 합성 Match ID DataFrame.

    각 VCL 연도의 ID 는 **같은 연도 VCT max Match ID + 1** 부터 시작.
    → priors.py 의 match_id ASC 정렬 시 VCT-VCL 이 시간순으로 올바르게 섞임.

    반환 컬럼: Tournament, Stage, Match Type, Match Name, Map, Match ID, Game ID, year
    """
    keys = MATCH_KEY_COLS + ["Map"]
    unique = (
        vcl_maps_scores[keys + ["year"]]
        .drop_duplicates(keys)
        .reset_index(drop=True)
    )

    # VCT 연도별 max ID (각 VCL 연도의 시작점)
    vct_year_max = vct_match_ids.groupby("Year")["Match ID"].max().to_dict()
    vct_year_min = vct_match_ids.groupby("Year")["Match ID"].min().to_dict()

    parts = []
    for y, grp in unique.groupby("year", sort=True):
        start = int(vct_year_max.get(y, 0)) + 1
        grp = grp.copy()
        grp["Match ID"] = list(range(start, start + len(grp)))
        parts.append(grp)
        end = start + len(grp) - 1
        # 다음 연도 VCT 와 충돌 없는지 확인
        next_min = vct_year_min.get(y + 1)
        warn = ""
        if next_min is not None and end >= next_min:
            warn = f"  ⚠️ VCT {y+1} min={next_min:,} 와 충돌"
        print(
            f"[data_load_v10] VCL {y}: ID {start:,} ~ {end:,} "
            f"(VCT {y} max={vct_year_max.get(y, 0):,}){warn}",
            file=sys.stderr,
        )

    result = pd.concat(parts, ignore_index=True)
    result["Match ID"] = result["Match ID"].astype(int)
    result["Game ID"]  = result["Match ID"]
    return result


# ───────── 통합 로더 ─────────

def load_overview_v10() -> pd.DataFrame:
    """VCT 6년치 + VCL 2023/2024 overview 통합."""
    vct = load_overview()

    vcl_dfs = []
    for y in VCL_YEARS:
        path = _vcl_dir(y) / "matches" / "overview.csv"
        if not path.exists():
            print(f"[data_load_v10] missing {path}, skip", file=sys.stderr)
            continue
        df = pd.read_csv(path, low_memory=False)
        df["year"] = y
        vcl_dfs.append(df)
        print(f"[data_load_v10] vcl_{y} overview: {len(df):,} rows", file=sys.stderr)

    out = pd.concat([vct] + vcl_dfs, ignore_index=True) if vcl_dfs else vct
    print(f"[data_load_v10] overview 합계: {len(out):,} rows", file=sys.stderr)
    return out


def load_maps_scores_v10() -> pd.DataFrame:
    """VCT 6년치 + VCL 2023/2024 maps_scores 통합."""
    vct = load_maps_scores()

    vcl_dfs = []
    for y in VCL_YEARS:
        path = _vcl_dir(y) / "matches" / "maps_scores.csv"
        if not path.exists():
            print(f"[data_load_v10] missing {path}, skip", file=sys.stderr)
            continue
        df = pd.read_csv(path, low_memory=False)
        df["year"] = y
        vcl_dfs.append(df)
        print(f"[data_load_v10] vcl_{y} maps_scores: {len(df):,} rows", file=sys.stderr)

    out = pd.concat([vct] + vcl_dfs, ignore_index=True) if vcl_dfs else vct
    print(f"[data_load_v10] maps_scores 합계: {len(out):,} rows", file=sys.stderr)
    return out


def load_kills_stats_v10() -> pd.DataFrame:
    """VCT 6년치 + VCL 2023/2024 kills_stats 통합."""
    vct = load_kills_stats()

    vcl_dfs = []
    for y in VCL_YEARS:
        path = _vcl_dir(y) / "matches" / "kills_stats.csv"
        if not path.exists():
            print(f"[data_load_v10] missing {path}, skip", file=sys.stderr)
            continue
        df = pd.read_csv(path, low_memory=False)
        df["year"] = y
        vcl_dfs.append(df)
        print(f"[data_load_v10] vcl_{y} kills_stats: {len(df):,} rows", file=sys.stderr)

    out = pd.concat([vct] + vcl_dfs, ignore_index=True) if vcl_dfs else vct
    print(f"[data_load_v10] kills_stats 합계: {len(out):,} rows", file=sys.stderr)
    return out


def load_match_ids_v10() -> pd.DataFrame:
    """VCT match_ids + VCL 합성 IDs 통합.

    내부적으로 VCL maps_scores를 로드해 합성 ID를 생성하므로 인자 불필요.
    반환 컬럼: Tournament, Stage, Match Type, Match Name, Map, Match ID, Game ID
    """
    vct_ids = load_match_ids()
    common  = ["Tournament", "Stage", "Match Type", "Match Name", "Map", "Match ID", "Game ID"]

    vcl_ms_dfs = []
    for y in VCL_YEARS:
        path = _vcl_dir(y) / "matches" / "maps_scores.csv"
        if path.exists():
            df = pd.read_csv(path, low_memory=False)
            df["year"] = y
            vcl_ms_dfs.append(df)

    if not vcl_ms_dfs:
        return vct_ids[common]

    vcl_ms  = pd.concat(vcl_ms_dfs, ignore_index=True)
    vcl_ids = _build_vcl_match_ids(vcl_ms, vct_ids)

    out = pd.concat([vct_ids[common], vcl_ids[common]], ignore_index=True)
    print(
        f"[data_load_v10] match_ids: VCT {len(vct_ids):,} + VCL {len(vcl_ids):,} = {len(out):,}",
        file=sys.stderr,
    )
    return out


# ───────── 필터 (VCT+VCL 통합용) ─────────

def filter_overview_per_player_map_v10(overview: pd.DataFrame) -> pd.DataFrame:
    """(선수, 맵) 단위 필터 — Side=='both', Map 유효, 이름 정규화."""
    n0 = len(overview)
    df = overview[overview["Side"] == "both"].copy()
    df = df[df["Map"].notna() & (df["Map"] != "All Maps")]

    # 연도순 최신 표기를 canonical로
    name_map: dict[str, str] = {}
    for name in df.sort_values("year")["Player"].dropna():
        name_map[str(name).lower()] = str(name)
    df["Player"] = df["Player"].map(lambda x: name_map.get(str(x).lower(), x))

    print(
        f"[data_load_v10] overview 필터: {n0:,} → {len(df):,} rows",
        file=sys.stderr,
    )
    return df


def filter_kills_stats_per_player_map_v10(kills_stats: pd.DataFrame) -> pd.DataFrame:
    """(선수, 맵) 단위 kills_stats 필터 — Map 유효, 이름 정규화."""
    n0 = len(kills_stats)
    df = kills_stats[kills_stats["Map"].notna() & (kills_stats["Map"] != "All Maps")].copy()

    name_map: dict[str, str] = {}
    for name in df.sort_values("year")["Player"].dropna():
        name_map[str(name).lower()] = str(name)
    df["Player"] = df["Player"].map(lambda x: name_map.get(str(x).lower(), x))

    print(
        f"[data_load_v10] kills_stats 필터: {n0:,} → {len(df):,} rows",
        file=sys.stderr,
    )
    return df
