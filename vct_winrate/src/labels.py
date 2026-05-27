"""(매치, 맵) 단위 레이블 추출.

각 (Match ID, Map) row → A팀 승리 여부.
"""
from __future__ import annotations

import sys

import pandas as pd

from src.data_load import (
    attach_ids_to_maps_scores,
    load_maps_scores,
    load_match_ids,
)
from src.taxonomy import normalize_map, normalize_team


def build_labels(
    maps_scores: pd.DataFrame, match_ids: pd.DataFrame
) -> pd.DataFrame:
    """maps_scores → (match_id, map, team_a, team_b, score_a, score_b, winner, year).

    - Match ID NaN row drop
    - 점수 NaN row drop
    - 동점(드물지만) drop
    """
    df = attach_ids_to_maps_scores(maps_scores, match_ids)
    n0 = len(df)

    df = df.dropna(subset=["Match ID", "Team A Score", "Team B Score",
                           "Team A", "Team B", "Map"])
    df["Team A Score"] = df["Team A Score"].astype(int)
    df["Team B Score"] = df["Team B Score"].astype(int)
    df["Match ID"] = df["Match ID"].astype(int)

    # 동점 drop
    tie_mask = df["Team A Score"] == df["Team B Score"]
    if tie_mask.any():
        print(f"[labels] dropping {tie_mask.sum()} tied rows", file=sys.stderr)
    df = df[~tie_mask]

    out = pd.DataFrame({
        "match_id": df["Match ID"].values,
        "map": [normalize_map(m) or str(m).strip().lower() for m in df["Map"]],
        "map_raw": df["Map"].values,
        "team_a": [normalize_team(t) for t in df["Team A"]],
        "team_b": [normalize_team(t) for t in df["Team B"]],
        "score_a": df["Team A Score"].values,
        "score_b": df["Team B Score"].values,
        "winner": (df["Team A Score"].values > df["Team B Score"].values).astype(int),
        "year": df["year"].values,
        "tournament": df["Tournament"].values,
        "stage": df["Stage"].values,
        "match_type": df["Match Type"].values,
        "match_name": df["Match Name"].values,
    })

    # (match_id, map) 중복 dedup — 소스 CSV에 가끔 있음
    pre_dedup = len(out)
    out = out.drop_duplicates(subset=["match_id", "map"], keep="first")
    if pre_dedup != len(out):
        print(f"[labels] dedup duplicates: {pre_dedup - len(out)}",
              file=sys.stderr)

    # 시간순 정렬
    out = out.sort_values(["match_id", "map"]).reset_index(drop=True)

    print(f"[labels] built {len(out):,} labeled rows "
          f"(dropped {n0 - len(out):,})", file=sys.stderr)
    print(f"[labels] label balance: A wins = {out['winner'].mean():.3f}",
          file=sys.stderr)
    return out


if __name__ == "__main__":
    ms = load_maps_scores()
    mi = load_match_ids()
    labels = build_labels(ms, mi)
    print("\nlabels head:")
    print(labels[["match_id", "map", "team_a", "team_b",
                  "score_a", "score_b", "winner", "year"]].head(8))
    print("\nyear distribution:")
    print(labels["year"].value_counts().sort_index())
    print("\nmap distribution (top 12):")
    print(labels["map"].value_counts().head(12))
