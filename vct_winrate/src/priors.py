"""leak-safe 누적 prior 계산 (★ 전처리의 핵심).

stat 셋 (사용자 스펙):
  - kd       : Kills / max(Deaths, 1)
  - kast     : Kill/Assist/Trade/Survive %
  - adr      : Average Damage Per Round
  - acs      : Average Combat Score
  - apr      : Assists Per Round (= Assists / rounds_this_map)
  - fkpr     : First Kills Per Round
  - fdpr     : First Deaths Per Round
  - clutch_pr: 클러치 승리 / 라운드 (kills_stats.csv 1v1~1v5 합 / rounds)

추가 추적:
  - 동반 출전 횟수: 같은 팀에서 같은 (매치, 맵)에 함께 출전한 누적 횟수
                   (5명 팀 = 10 페어). 팀 단위 합계 emit.

알고리즘 (priors v1과 동일한 leak-safe 시간 순회):
  1. overview를 (Match ID ASC, Map) 정렬
  2. (match_id, map) 그룹 단위 순회
  3. 각 그룹: 현재 state로 prior 계산 → 그룹 처리 후 state 업데이트
"""
from __future__ import annotations

import sys
from collections import defaultdict, deque
from itertools import combinations

import numpy as np
import pandas as pd

from config import PLAYER_RECENT_N
from src.taxonomy import agent_role, normalize_agent, normalize_map, normalize_team

STAT_KEYS = ("kd", "kast", "adr", "acs", "apr", "fkpr", "fdpr", "clutch_pr")


# ───────── 파싱 헬퍼 ─────────
def _to_float(x) -> float:
    if x is None:
        return np.nan
    if isinstance(x, float) and np.isnan(x):
        return np.nan
    if isinstance(x, str):
        s = x.strip().rstrip("%")
        if not s:
            return np.nan
        try:
            return float(s)
        except ValueError:
            return np.nan
    try:
        return float(x)
    except (TypeError, ValueError):
        return np.nan


def _to_percent(x) -> float:
    """'73%' → 0.73."""
    v = _to_float(x)
    if np.isnan(v):
        return np.nan
    return v / 100.0 if v > 1.5 else v


def _mean_of(dq: deque, key: str) -> float:
    if not dq:
        return np.nan
    vals = [d[key] for d in dq if not np.isnan(d[key])]
    return float(np.mean(vals)) if vals else np.nan


def _safe_div(num, den) -> float:
    if den is None or den == 0 or (isinstance(den, float) and np.isnan(den)):
        return np.nan
    return num / den


# ───────── overview 정규화 + raw stat 계산 ─────────
def _normalize_overview(ov: pd.DataFrame,
                        rounds_lookup: dict,
                        clutch_lookup: dict) -> pd.DataFrame:
    df = ov.rename(columns={
        "Match ID": "match_id",
        "Map": "map_raw",
        "Player": "player",
        "Team": "team_raw",
        "Agents": "agent_raw",
        "Rating": "rating",
        "Average Combat Score": "acs",
        "Kill, Assist, Trade, Survive %": "kast_str",
        "Average Damage Per Round": "adr",
        "Kills": "kills",
        "Deaths": "deaths",
        "Assists": "assists",
        "First Kills": "first_kills",
        "First Deaths": "first_deaths",
    }).copy()

    df["acs"] = df["acs"].apply(_to_float)
    df["adr"] = df["adr"].apply(_to_float)
    df["kills"] = df["kills"].apply(_to_float)
    df["deaths"] = df["deaths"].apply(_to_float)
    df["assists"] = df["assists"].apply(_to_float)
    df["first_kills"] = df["first_kills"].apply(_to_float)
    df["first_deaths"] = df["first_deaths"].apply(_to_float)
    df["kast"] = df["kast_str"].apply(_to_percent)

    df["match_id"] = df["match_id"].astype(int)
    df["map"] = df["map_raw"].apply(
        lambda m: normalize_map(m) or str(m).strip().lower())
    df["team"] = df["team_raw"].apply(normalize_team)
    df["agent"] = df["agent_raw"].apply(normalize_agent)
    df["role"] = df["agent"].apply(lambda a: agent_role(a) if a else None)

    # KD ratio
    df["kd"] = df.apply(
        lambda r: _safe_div(r["kills"], max(r["deaths"], 1.0))
        if not np.isnan(r["kills"]) and not np.isnan(r["deaths"])
        else np.nan, axis=1)

    # rounds 조회 — raw map 이름 그대로 사용 (rounds_lookup의 key는 raw)
    df["rounds"] = df.apply(
        lambda r: rounds_lookup.get((r["match_id"], r["map_raw"]), np.nan),
        axis=1)

    df["apr"] = df.apply(
        lambda r: _safe_div(r["assists"], r["rounds"]), axis=1)
    df["fkpr"] = df.apply(
        lambda r: _safe_div(r["first_kills"], r["rounds"]), axis=1)
    df["fdpr"] = df.apply(
        lambda r: _safe_div(r["first_deaths"], r["rounds"]), axis=1)

    # clutch_pr: 클러치 승리 / 라운드
    df["clutch_wins"] = df.apply(
        lambda r: clutch_lookup.get((r["match_id"], r["map_raw"], r["player"]), 0),
        axis=1)
    df["clutch_pr"] = df.apply(
        lambda r: _safe_div(r["clutch_wins"], r["rounds"]), axis=1)

    return df.sort_values(["match_id", "map"]).reset_index(drop=True)


# ───────── 메인 ─────────
def compute_priors(overview: pd.DataFrame,
                   labels: pd.DataFrame,
                   rounds_lookup: dict,
                   clutch_lookup: dict) -> tuple[pd.DataFrame, dict]:
    """
    Returns:
      - per-(match, map, player) prior DataFrame
      - state snapshot dict (inference용)
    """
    ov = _normalize_overview(overview, rounds_lookup, clutch_lookup)

    # labels lookup: (match_id, map) → (team_a, team_b, winner)
    labels = labels.copy()
    labels["match_id"] = labels["match_id"].astype(int)
    label_lookup: dict[tuple, tuple] = {}
    for r in labels.itertuples(index=False):
        label_lookup[(r.match_id, r.map)] = (r.team_a, r.team_b, int(r.winner))

    # state
    player_hist: dict[str, deque] = defaultdict(
        lambda: deque(maxlen=PLAYER_RECENT_N))
    player_total_count: dict[str, int] = defaultdict(int)
    co_play_counts: dict[frozenset, int] = defaultdict(int)

    out_rows: list[dict] = []
    skipped_no_label = 0

    for (mid, mp), grp in ov.groupby(["match_id", "map"], sort=False):
        key = (int(mid), mp)
        if key not in label_lookup:
            skipped_no_label += 1
            continue
        team_a, team_b, y = label_lookup[key]
        if team_a is None or team_b is None:
            skipped_no_label += 1
            continue

        # 팀 단위 동반출전 합 계산 (이 그룹의 prior 시점)
        def _players_of(team_name):
            players = grp.loc[grp["team"] == team_name, "player"].dropna().tolist()
            return sorted({p for p in players if isinstance(p, str) and p})
        side_a_players = _players_of(team_a)
        side_b_players = _players_of(team_b)
        copa = sum(co_play_counts[frozenset({p1, p2})]
                   for p1, p2 in combinations(side_a_players, 2))
        copb = sum(co_play_counts[frozenset({p1, p2})]
                   for p1, p2 in combinations(side_b_players, 2))

        # row-level prior emit
        for r in grp.itertuples(index=False):
            is_team_a = (r.team == team_a)
            out_rows.append({
                "match_id": int(mid),
                "map": mp,
                "year": int(r.year),
                "winner": y,
                "player": r.player,
                "team": r.team,
                "agent": r.agent,
                "role": r.role,
                "is_team_a": int(is_team_a),
                # 8 stat priors
                "prior_kd":        _mean_of(player_hist[r.player], "kd"),
                "prior_kast":      _mean_of(player_hist[r.player], "kast"),
                "prior_adr":       _mean_of(player_hist[r.player], "adr"),
                "prior_acs":       _mean_of(player_hist[r.player], "acs"),
                "prior_apr":       _mean_of(player_hist[r.player], "apr"),
                "prior_fkpr":      _mean_of(player_hist[r.player], "fkpr"),
                "prior_fdpr":      _mean_of(player_hist[r.player], "fdpr"),
                "prior_clutch_pr": _mean_of(player_hist[r.player], "clutch_pr"),
                "prior_count":     player_total_count[r.player],
                # 팀 단위 동반출전 합 (5명 모두 같은 값)
                "team_co_play_sum": copa if is_team_a else copb,
            })

        # state 업데이트
        for r in grp.itertuples(index=False):
            stats = {
                "kd": r.kd, "kast": r.kast, "adr": r.adr, "acs": r.acs,
                "apr": r.apr, "fkpr": r.fkpr, "fdpr": r.fdpr,
                "clutch_pr": r.clutch_pr,
            }
            player_hist[r.player].append(stats)
            player_total_count[r.player] += 1

        # 동반출전 카운트: 같은 팀 페어들 +1
        for p1, p2 in combinations(side_a_players, 2):
            co_play_counts[frozenset({p1, p2})] += 1
        for p1, p2 in combinations(side_b_players, 2):
            co_play_counts[frozenset({p1, p2})] += 1

    print(f"[priors] emitted {len(out_rows):,} rows, "
          f"skipped no-label {skipped_no_label}",
          file=sys.stderr)

    state = {
        "player_hist": dict(player_hist),
        "player_total_count": dict(player_total_count),
        "co_play_counts": {tuple(sorted(k)): v for k, v in co_play_counts.items()},
    }
    return pd.DataFrame(out_rows), state


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

    print("loading...", file=sys.stderr)
    ov = load_overview()
    mi = load_match_ids()
    ms = load_maps_scores()
    ks = load_kills_stats()

    ov_filt = attach_ids_to_overview(filter_overview_per_player_map(ov), mi)
    ks_filt = attach_ids_to_kills_stats(filter_kills_stats_per_player_map(ks), mi)
    labels = build_labels(ms, mi)

    print("building lookups...", file=sys.stderr)
    rounds = rounds_per_map_lookup(ms, mi)
    clutches = build_clutch_lookup(ks_filt)
    print(f"rounds entries: {len(rounds):,}, clutch entries: {len(clutches):,}",
          file=sys.stderr)

    priors_df, state = compute_priors(ov_filt, labels, rounds, clutches)
    print(f"\npriors shape: {priors_df.shape}")
    print("\ncolumns:", list(priors_df.columns))
    print("\nlast row (with history):")
    print(priors_df.iloc[-1])
    print("\nprior NaN ratios:")
    cols = [c for c in priors_df.columns if c.startswith("prior_")]
    print(priors_df[cols].isna().mean().round(3))
    print("\nco-play sum sample (last 5 groups):")
    print(priors_df.groupby(["match_id", "map"], sort=False).tail(1)[
        ["match_id", "map", "team", "team_co_play_sum"]].tail(10))
