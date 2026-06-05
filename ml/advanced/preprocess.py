"""Unified ingest pipeline: Kaggle + VLR.gg raw data → data/processed/

Output:
    data/processed/matches.csv   -- map-level matches (model training table)
    data/processed/players.csv   -- player × map (lineup + prior source)
    data/processed/comps.csv     -- team × map compositions (EDA/insights)
    data/processed/maps.csv      -- team × map round stats (EDA, not model features)

Usage:
    python -m ml.advanced.preprocess [--kaggle data/raw/kaggle] [--vlrgg data/raw/vlrgg/match]
                                     [--output data/processed] [--reports reports]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ml.agent_roles import AGENT_ROLE_MAP, MAP_ORDER, TEAM_NAME_ALIASES
from ml.valorant import normalize_agent, normalize_map

# ──────────────────────────── constants ─────────────────────────────────────

VALID_MAPS: set[str] = set(MAP_ORDER)

YEAR_RE = re.compile(r"(20[12][0-9])")
PATCH_RE = re.compile(r"Patch\s+(\d+)\.\d+", re.I)
# VALORANT patch major → calendar year (boundaries confirmed from patch release dates)
PATCH_TO_YEAR: dict[int, int] = {
    1: 2020, 2: 2021, 3: 2021, 4: 2022, 5: 2022,
    6: 2023, 7: 2023, 8: 2024, 9: 2024,
    10: 2025, 11: 2025, 12: 2026, 13: 2026,
}

MATCHES_COLS = [
    "match_key", "dedup_key", "source", "date", "year", "event",
    "map", "team_a", "team_b", "score_a", "score_b", "label",
    "agents_a", "agents_b", "provenance",
]
PLAYERS_COLS = [
    "match_key", "dedup_key", "side", "player_slot", "player", "agent", "role",
    "kd", "kast", "adr", "clutch", "assists", "fk", "fd",
    "acs", "kills", "deaths", "hs",
    "source", "provenance",
]
COMPS_COLS = [
    "match_key", "team_side", "map", "agents", "comp_key",
    "duelist_count", "initiator_count", "controller_count", "sentinel_count",
]
MAPS_COLS = [
    "match_key", "team_side", "map", "side_first_half",
    "atk_rounds", "def_rounds", "ot_rounds", "score", "source",
]

# ──────────────────────────── helpers ───────────────────────────────────────

def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="replace")).hexdigest()


def make_match_key(source: str, raw_id: str, map_norm: str) -> str:
    return _sha1(f"{source}|{raw_id}|{map_norm}")[:16]


def make_dedup_key(
    year: int | None,
    team_a: str,
    team_b: str,
    map_norm: str,
    score_lo: float = 0.0,
    score_hi: float = 0.0,
) -> str:
    # v2: no label (catches cross-source label conflicts); case-folded teams; sorted scores preserve true rematches.
    y = int(year) if year else 0
    ta = norm_team(team_a).lower().strip()
    tb = norm_team(team_b).lower().strip()
    sl = int(min(score_lo, score_hi))
    sh = int(max(score_lo, score_hi))
    return _sha1(f"{y}|{ta}|{tb}|{map_norm}|{sl}|{sh}")[:24]


def norm_team(name: str) -> str:
    if not name:
        return name
    s = name.strip()
    return TEAM_NAME_ALIASES.get(s.lower(), s)


def norm_kast(v: Any) -> float:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return float("nan")
    try:
        f = float(str(v).strip().rstrip("%"))
        return f / 100.0 if f > 1.0 else f
    except (ValueError, TypeError):
        return float("nan")


def norm_hs(v: Any) -> float:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return float("nan")
    try:
        f = float(str(v).strip().rstrip("%"))
        return f / 100.0 if f > 1.0 else f
    except (ValueError, TypeError):
        return float("nan")


def norm_kd(kills: Any, deaths: Any) -> float:
    try:
        k = float(kills or 0)
        d = max(float(deaths or 0), 1.0)
        return k / d
    except (ValueError, TypeError):
        return 0.0


def _to_float(v: Any, fallback: float = float("nan")) -> float:
    """Convert a raw CSV value to float; return fallback on None/empty/nan."""
    if v is None:
        return fallback
    s = str(v).strip()
    if not s or s.lower() == "nan":
        return fallback
    try:
        return float(s)
    except (ValueError, TypeError):
        return fallback


def _extract_year_from_text(event: str | None, date_str: str | None) -> tuple[int | None, str]:
    """Try event name first (YEAR_RE), then date/patch string."""
    for text in (event, date_str):
        if not text:
            continue
        m = YEAR_RE.search(str(text))
        if m:
            return int(m.group(1)), "event"
    if date_str:
        m2 = PATCH_RE.search(str(date_str))
        if m2:
            major = int(m2.group(1))
            y = PATCH_TO_YEAR.get(major)
            if y:
                return y, "patch"
    return None, "unknown"


def _agents_from_pipe(agents_str: str) -> list[str]:
    """Parse '|'-separated agents, normalise each, return sorted list."""
    if not agents_str or not isinstance(agents_str, str):
        return []
    result = []
    for part in agents_str.split("|"):
        a = normalize_agent(part.strip())
        if a:
            result.append(a)
    return result


def _role_counts(agents: list[str]) -> dict[str, int]:
    counts = {"Duelist": 0, "Initiator": 0, "Controller": 0, "Sentinel": 0}
    for a in agents:
        role = AGENT_ROLE_MAP.get(a)
        if role in counts:
            counts[role] += 1
    return counts


def _build_comp_row(match_key: str, team_side: str, map_norm: str, agents: list[str]) -> dict:
    rc = _role_counts(agents)
    sorted_agents = sorted(agents)
    return {
        "match_key": match_key,
        "team_side": team_side,
        "map": map_norm,
        "agents": "|".join(sorted_agents),
        "comp_key": "|".join(sorted_agents),
        "duelist_count": rc["Duelist"],
        "initiator_count": rc["Initiator"],
        "controller_count": rc["Controller"],
        "sentinel_count": rc["Sentinel"],
    }


def _make_match_row(
    match_key: str, dedup_key: str, source: str,
    date: str, year: int | None, event: str,
    map_norm: str, team_a: str, team_b: str,
    score_a: float, score_b: float, label: int,
    agents_a: list[str], agents_b: list[str], provenance: str,
) -> dict:
    return {
        "match_key": match_key, "dedup_key": dedup_key, "source": source,
        "date": date, "year": year, "event": event, "map": map_norm,
        "team_a": team_a, "team_b": team_b,
        "score_a": score_a, "score_b": score_b, "label": label,
        "agents_a": "|".join(agents_a), "agents_b": "|".join(agents_b),
        "provenance": provenance,
    }


def _make_player_row(
    match_key: str, dedup_key: str, side: str, slot: int, player: str,
    agent: str, kills: Any, deaths: Any, assists: Any,
    kast: Any, adr: Any, hs: Any, fk: Any, fd: Any, acs: Any,
    source: str, provenance: str,
) -> dict:
    role = AGENT_ROLE_MAP.get(agent, "")
    return {
        "match_key": match_key, "dedup_key": dedup_key,
        "side": side, "player_slot": slot,
        "player": player, "agent": agent, "role": role.lower() if role else "",
        "kd": norm_kd(kills, deaths),
        "kast": norm_kast(kast),
        "adr": _to_float(adr),
        "clutch": float("nan"),
        "assists": _to_float(assists, 0.0),
        "fk": _to_float(fk, 0.0),
        "fd": _to_float(fd, 0.0),
        "acs": _to_float(acs),
        "kills": _to_float(kills, 0.0),
        "deaths": _to_float(deaths, 0.0),
        "hs": norm_hs(hs),
        "source": source, "provenance": provenance,
    }


# ─────────────────────── Kaggle: ryanluong loader ───────────────────────────

def _load_ryanluong_dir(
    year_dir: Path,
    source: str,
    folder_year: int,
    match_rows: list,
    player_rows: list,
    comp_rows: list,
) -> None:
    """Load one ryanluong-format dataset directory (VCT or VCL year folder)."""
    maps_scores_path = year_dir / "matches" / "maps_scores.csv"
    overview_path = year_dir / "matches" / "overview.csv"
    if not maps_scores_path.exists() or not overview_path.exists():
        return

    try:
        scores_df = pd.read_csv(maps_scores_path, low_memory=False)
        overview_df = pd.read_csv(overview_path, low_memory=False)
    except Exception as e:
        print(f"    Warning: could not read {year_dir.name}: {e}")
        return

    # Filter overview to 'both' side only (removes per-side duplicates)
    if "Side" in overview_df.columns:
        overview_df = overview_df[overview_df["Side"].str.lower() == "both"]

    # Build player lookup: (Match Name, Map, Team) → list of player dicts
    player_lookup: dict[tuple, list] = {}
    for _, row in overview_df.iterrows():
        mn = str(row.get("Match Name", "")).strip()
        mp = normalize_map(str(row.get("Map", "")))
        tm = norm_team(str(row.get("Team", "")).strip())
        pl = str(row.get("Player", "")).strip()
        ag = normalize_agent(str(row.get("Agents", "")))
        if not mn or not mp or not tm or not ag:
            continue
        key = (mn, mp, tm)
        if key not in player_lookup:
            player_lookup[key] = []
        # Stats
        kast_raw = row.get("Kill, Assist, Trade, Survive %") or row.get("KAST%") or row.get("kast")
        player_lookup[key].append({
            "player": pl, "agent": ag,
            "kills": row.get("Kills") or row.get("K"),
            "deaths": row.get("Deaths") or row.get("D"),
            "assists": row.get("Assists") or row.get("A"),
            "kast": kast_raw,
            "adr": row.get("Average Damage Per Round") or row.get("ADR"),
            "hs": row.get("Headshot %") or row.get("HS%"),
            "fk": row.get("First Kills") or row.get("FK"),
            "fd": row.get("First Deaths") or row.get("FD"),
            "acs": row.get("Average Combat Score") or row.get("ACS"),
        })

    # Extract year from tournament column or fall back to folder year
    # Process map score rows
    for _, row in scores_df.iterrows():
        match_name = str(row.get("Match Name", "")).strip()
        map_raw = str(row.get("Map", "")).strip()
        map_norm = normalize_map(map_raw)
        if not map_norm or not match_name:
            continue

        team_a_raw = norm_team(str(row.get("Team A", "")).strip())
        team_b_raw = norm_team(str(row.get("Team B", "")).strip())
        if not team_a_raw or not team_b_raw:
            continue

        try:
            score_a = float(row.get("Team A Score", 0) or 0)
            score_b = float(row.get("Team B Score", 0) or 0)
        except (ValueError, TypeError):
            continue

        if score_a == score_b:
            continue  # no draws in Valorant

        label = 1 if score_a > score_b else 0

        # Sort teams alphabetically for canonical ordering
        if team_a_raw <= team_b_raw:
            ta, tb, sa, sb, lbl = team_a_raw, team_b_raw, score_a, score_b, label
        else:
            ta, tb, sa, sb, lbl = team_b_raw, team_a_raw, score_b, score_a, 1 - label

        # Year from tournament name
        tournament = str(row.get("Tournament", "")).strip()
        year_val, _ = _extract_year_from_text(tournament, None)
        if not year_val:
            year_val = folder_year

        event = tournament
        raw_id = f"{match_name}|{map_norm}"
        prov = f"{source}/{year_dir.name}/{match_name}"
        mkey = make_match_key(source, raw_id, map_norm)
        dkey = make_dedup_key(year_val, ta, tb, map_norm, sa, sb)

        # Get agents from player lookup
        agents_a = [p["agent"] for p in player_lookup.get((match_name, map_norm, ta), [])]
        agents_b = [p["agent"] for p in player_lookup.get((match_name, map_norm, tb), [])]

        # Only include if we have exactly 5 agents per team
        if len(agents_a) != 5 or len(agents_b) != 5:
            # Try original ordering in case team norm changed
            agents_a_orig = [p["agent"] for p in player_lookup.get((match_name, map_norm, team_a_raw), [])]
            agents_b_orig = [p["agent"] for p in player_lookup.get((match_name, map_norm, team_b_raw), [])]
            if ta == team_a_raw:
                agents_a, agents_b = agents_a_orig, agents_b_orig
            else:
                agents_a, agents_b = agents_b_orig, agents_a_orig

        if len(agents_a) != 5 or len(agents_b) != 5:
            continue  # 5v5 gate

        match_rows.append(_make_match_row(
            mkey, dkey, source, "", year_val, event,
            map_norm, ta, tb, sa, sb, lbl,
            agents_a, agents_b, prov,
        ))
        comp_rows.append(_build_comp_row(mkey, "a", map_norm, agents_a))
        comp_rows.append(_build_comp_row(mkey, "b", map_norm, agents_b))

        # Players
        for side, team_name in (("a", ta), ("b", tb)):
            pdata = player_lookup.get((match_name, map_norm, team_name), [])
            for slot, pd_row in enumerate(sorted(pdata, key=lambda x: x["player"]), 1):
                if slot > 5:
                    break
                player_rows.append(_make_player_row(
                    mkey, dkey, side, slot, pd_row["player"], pd_row["agent"],
                    pd_row["kills"], pd_row["deaths"], pd_row["assists"],
                    pd_row["kast"], pd_row["adr"], pd_row["hs"],
                    pd_row["fk"], pd_row["fd"], pd_row["acs"],
                    source, prov,
                ))


def load_ryanluong(kaggle_root: Path, match_rows: list, player_rows: list, comp_rows: list) -> None:
    """Load all ryanluong VCT (2021-2026) and VCL (2023-2024) data."""
    # VCT: vct_2021_2023 root
    vct_root = kaggle_root / "vct_2021_2023"
    if vct_root.exists():
        for year_dir in sorted(vct_root.iterdir()):
            if not year_dir.is_dir() or not year_dir.name.startswith("vct_"):
                continue
            try:
                folder_year = int(year_dir.name.split("_")[-1])
            except ValueError:
                continue
            print(f"  Loading VCT/{year_dir.name}...")
            _load_ryanluong_dir(year_dir, "kaggle_ryanluong_vct", folder_year, match_rows, player_rows, comp_rows)

    # VCL
    vcl_root = kaggle_root / "ryanluong1__valorant-challengers-league-data"
    if vcl_root.exists():
        for year_dir in sorted(vcl_root.iterdir()):
            if not year_dir.is_dir() or not year_dir.name.startswith("vcl_"):
                continue
            try:
                folder_year = int(year_dir.name.split("_")[-1])
            except ValueError:
                continue
            print(f"  Loading VCL/{year_dir.name}...")
            _load_ryanluong_dir(year_dir, "kaggle_ryanluong_vcl", folder_year, match_rows, player_rows, comp_rows)


# ───────────────────────── Kaggle: qualidea loader ──────────────────────────

def load_qualidea(kaggle_root: Path, match_rows: list, player_rows: list, comp_rows: list) -> None:
    """Load qualidea1217 flat CSV dataset."""
    path = kaggle_root / "qualidea1217__valorant-pro-matches-since-april-2021" / "data-since-april-2021.csv"
    if not path.exists():
        print("  qualidea: file not found, skipping")
        return
    print("  Loading qualidea...")
    try:
        df = pd.read_csv(path, low_memory=False, encoding="latin-1")
    except Exception as e:
        print(f"  qualidea: error reading {e}")
        return

    source = "kaggle_qualidea"
    # Group by (match-datetime, map, team1, team2) to get match-level rows
    # Each group has 10 players (5 per team)
    group_cols = ["match-datetime", "map", "team1", "team2"]
    for gc in group_cols:
        if gc not in df.columns:
            print(f"  qualidea: missing column {gc}, skipping")
            return

    # Rename for easier access
    df = df.copy()
    df["team1"] = df["team1"].apply(norm_team)
    df["team2"] = df["team2"].apply(norm_team)

    # Extract match-level score: take first row per group for scores
    for (dt, map_raw, t1, t2), grp in df.groupby(["match-datetime", "map", "team1", "team2"]):
        map_norm = normalize_map(str(map_raw))
        if not map_norm:
            continue

        # Score from columns
        try:
            first = grp.iloc[0]
            score1 = float(first.get("team1-score", 0) or 0)
            score2 = float(first.get("team2-score", 0) or 0)
        except (ValueError, TypeError):
            continue
        if score1 == score2:
            continue

        # Year from match-datetime "2023/4/16 10:00"
        year_val = None
        dt_str = str(dt)
        m = YEAR_RE.search(dt_str)
        if m:
            year_val = int(m.group(1))
        if not year_val:
            continue

        label = 1 if score1 > score2 else 0
        # Canonical sort
        if t1 <= t2:
            ta, tb, sa, sb, lbl = t1, t2, score1, score2, label
        else:
            ta, tb, sa, sb, lbl = t2, t1, score2, score1, 1 - label

        raw_id = f"{dt}|{t1}|{t2}|{map_norm}"
        prov = f"{source}/{dt}/{map_norm}"
        mkey = make_match_key(source, raw_id, map_norm)
        dkey = make_dedup_key(year_val, ta, tb, map_norm, sa, sb)

        # Players per team
        agents_a, agents_b = [], []
        pa_rows, pb_rows = [], []
        for _, prow in grp.iterrows():
            team_name = norm_team(str(prow.get("player-team", "")).strip())
            agent = normalize_agent(str(prow.get("agent", "")))
            if not agent:
                continue
            pl_name = str(prow.get("player-name", "")).strip()
            pdict = {
                "player": pl_name, "agent": agent,
                "kills": prow.get("k"), "deaths": prow.get("d"),
                "assists": prow.get("a"),
                "kast": prow.get("kast"),
                "adr": prow.get("adr"), "hs": prow.get("hs"),
                "fk": prow.get("fk"), "fd": prow.get("fd"),
                "acs": prow.get("acs"),
            }
            if team_name == ta:
                agents_a.append(agent)
                pa_rows.append(pdict)
            elif team_name == tb:
                agents_b.append(agent)
                pb_rows.append(pdict)

        if len(agents_a) != 5 or len(agents_b) != 5:
            continue  # 5v5 gate

        match_rows.append(_make_match_row(
            mkey, dkey, source, dt_str, year_val, "",
            map_norm, ta, tb, sa, sb, lbl,
            agents_a, agents_b, prov,
        ))
        comp_rows.append(_build_comp_row(mkey, "a", map_norm, agents_a))
        comp_rows.append(_build_comp_row(mkey, "b", map_norm, agents_b))

        for side, plist in (("a", pa_rows), ("b", pb_rows)):
            for slot, pd_row in enumerate(sorted(plist, key=lambda x: x["player"]), 1):
                player_rows.append(_make_player_row(
                    mkey, dkey, side, slot, pd_row["player"], pd_row["agent"],
                    pd_row["kills"], pd_row["deaths"], pd_row["assists"],
                    pd_row["kast"], pd_row["adr"], pd_row["hs"],
                    pd_row["fk"], pd_row["fd"], pd_row["acs"],
                    source, prov,
                ))


# ─────────────────────── Kaggle: ediashtarevin loader ───────────────────────

def load_ediashtarevin(kaggle_root: Path, match_rows: list, player_rows: list, comp_rows: list) -> None:
    """Load ediashtarevin VCT Champions 2023 player stats."""
    path = kaggle_root / "ediashtarevin__vct-champions-2023-stats" / "player_stats.csv"
    if not path.exists():
        print("  ediashtarevin: file not found, skipping")
        return
    print("  Loading ediashtarevin...")
    try:
        df = pd.read_csv(path, low_memory=False)
    except Exception as e:
        print(f"  ediashtarevin: error {e}")
        return

    source = "kaggle_ediashtarevin"
    year_val = 2023

    df["team"] = df["team"].apply(norm_team)
    df["opponent"] = df["opponent"].apply(norm_team)

    for (mid, gid, map_raw, team1), grp1 in df.groupby(["match_id", "game_id", "map", "team"]):
        map_norm = normalize_map(str(map_raw))
        if not map_norm or len(grp1) == 0:
            continue
        first1 = grp1.iloc[0]
        opp = norm_team(str(first1.get("opponent", "")).strip())
        # Get the other team's group
        grp2 = df[(df["match_id"] == mid) & (df["game_id"] == gid) &
                  (df["map"] == map_raw) & (df["team"] == opp)]
        if len(grp2) == 0:
            continue

        try:
            s1 = float(first1.get("score_team", 0) or 0)
            s2 = float(first1.get("score_opp", 0) or 0)
        except (ValueError, TypeError):
            continue
        if s1 == s2:
            continue

        label = 1 if s1 > s2 else 0
        t1, t2 = str(team1), opp
        if t1 <= t2:
            ta, tb, sa, sb, lbl = t1, t2, s1, s2, label
        else:
            ta, tb, sa, sb, lbl = t2, t1, s2, s1, 1 - label

        raw_id = f"{mid}|{gid}|{map_norm}"
        prov = f"{source}/match_{mid}/game_{gid}/{map_norm}"
        mkey = make_match_key(source, raw_id, map_norm)
        dkey = make_dedup_key(year_val, ta, tb, map_norm, sa, sb)

        grp_a = grp1 if t1 == ta else grp2
        grp_b = grp2 if t1 == ta else grp1
        agents_a, agents_b = [], []
        pa_rows, pb_rows = [], []
        for side_rows, agents_list, plist in ((grp_a, agents_a, pa_rows), (grp_b, agents_b, pb_rows)):
            for _, prow in side_rows.iterrows():
                agent = normalize_agent(str(prow.get("agent", "")))
                if not agent:
                    continue
                agents_list.append(agent)
                plist.append({
                    "player": str(prow.get("player", "")).strip(), "agent": agent,
                    "kills": prow.get("kill"), "deaths": prow.get("death"),
                    "assists": prow.get("assist"),
                    "kast": prow.get("kast%"),
                    "adr": prow.get("adr"),
                    "hs": prow.get("hs%"),
                    "fk": prow.get("fk"), "fd": prow.get("fd"),
                    "acs": prow.get("acs"),
                })

        if len(agents_a) != 5 or len(agents_b) != 5:
            continue

        match_rows.append(_make_match_row(
            mkey, dkey, source, "", year_val, "VCT Champions 2023",
            map_norm, ta, tb, sa, sb, lbl,
            agents_a, agents_b, prov,
        ))
        comp_rows.append(_build_comp_row(mkey, "a", map_norm, agents_a))
        comp_rows.append(_build_comp_row(mkey, "b", map_norm, agents_b))

        for side, plist in (("a", pa_rows), ("b", pb_rows)):
            for slot, pd_row in enumerate(sorted(plist, key=lambda x: x["player"]), 1):
                player_rows.append(_make_player_row(
                    mkey, dkey, side, slot, pd_row["player"], pd_row["agent"],
                    pd_row["kills"], pd_row["deaths"], pd_row["assists"],
                    pd_row["kast"], pd_row["adr"], pd_row["hs"],
                    pd_row["fk"], pd_row["fd"], pd_row["acs"],
                    source, prov,
                ))


# ─────────────────────── Kaggle: piyush loader ──────────────────────────────

def load_piyush(kaggle_root: Path, match_rows: list, player_rows: list, comp_rows: list) -> None:
    """Load piyush86kumar VCT Champions 2024 stats."""
    base = kaggle_root / "piyush86kumar__valorant-champions-2024"
    ps_path = base / "detailed_matches_player_stats.csv"
    maps_path = base / "detailed_matches_maps.csv"
    if not ps_path.exists():
        print("  piyush: player_stats not found, skipping")
        return
    print("  Loading piyush...")
    try:
        ps_df = pd.read_csv(ps_path, low_memory=False)
        maps_df = pd.read_csv(maps_path, low_memory=False) if maps_path.exists() else None
    except Exception as e:
        print(f"  piyush: error {e}")
        return

    source = "kaggle_piyush"

    # Filter map-level rows
    ps_map = ps_df[ps_df["stat_type"].str.strip().str.lower() == "map"].copy()
    if ps_map.empty:
        return

    ps_map["team1"] = ps_map["team1"].apply(norm_team)
    ps_map["team2"] = ps_map["team2"].apply(norm_team)
    ps_map["player_team"] = ps_map["player_team"].apply(norm_team)
    ps_map["map_winner"] = ps_map["map_winner"].apply(norm_team)

    # Build score lookup from maps_df
    score_lookup: dict[tuple, tuple[float, float]] = {}
    if maps_df is not None:
        for _, row in maps_df.iterrows():
            mid = row["match_id"]
            mn = str(row.get("map_name", "")).strip()
            score_str = str(row.get("score", ""))
            parts = [x.strip() for x in score_str.split("-")]
            if len(parts) == 2:
                try:
                    score_lookup[(mid, mn)] = (float(parts[0]), float(parts[1]))
                except ValueError:
                    pass

    # Group by (match_id, map_name)
    for (mid, map_raw), grp in ps_map.groupby(["match_id", "map_name"]):
        map_norm = normalize_map(str(map_raw))
        if not map_norm or grp.empty:
            continue

        first = grp.iloc[0]
        t1 = norm_team(str(first.get("team1", "")).strip())
        t2 = norm_team(str(first.get("team2", "")).strip())
        winner = norm_team(str(first.get("map_winner", "")).strip())

        if not winner or not t1 or not t2:
            continue

        # Get score
        raw_score = score_lookup.get((mid, str(map_raw)))
        if raw_score:
            s1_raw, s2_raw = raw_score
            # score is in team1-team2 order (verified from data)
            sa_t1, sb_t2 = s1_raw, s2_raw
        else:
            # fallback: winner gets higher, loser gets lower
            sa_t1 = 13.0 if winner == t1 else 5.0
            sb_t2 = 5.0 if winner == t1 else 13.0

        label_t1 = 1 if winner == t1 else 0

        # Canonical sort
        if t1 <= t2:
            ta, tb, sa, sb, lbl = t1, t2, sa_t1, sb_t2, label_t1
        else:
            ta, tb, sa, sb, lbl = t2, t1, sb_t2, sa_t1, 1 - label_t1

        year_val = None
        date_str = str(first.get("match_date", "")).strip()
        m = YEAR_RE.search(date_str)
        if m:
            year_val = int(m.group(1))
        if not year_val:
            year_val = 2024

        event = str(first.get("event_name", "")).strip()
        raw_id = f"{mid}|{map_norm}"
        prov = f"{source}/match_{mid}/{map_norm}"
        mkey = make_match_key(source, raw_id, map_norm)
        dkey = make_dedup_key(year_val, ta, tb, map_norm, sa, sb)

        agents_a, agents_b = [], []
        pa_rows, pb_rows = [], []
        for _, prow in grp.iterrows():
            pt = norm_team(str(prow.get("player_team", "")).strip())
            agent = normalize_agent(str(prow.get("agent", "")))
            if not agent:
                continue
            pl_name = str(prow.get("player_name", "")).strip()
            pd_dict = {
                "player": pl_name, "agent": agent,
                "kills": prow.get("k"), "deaths": prow.get("d"),
                "assists": prow.get("a"),
                "kast": prow.get("kast"),
                "adr": prow.get("adr"),
                "hs": prow.get("hs_percent"),
                "fk": prow.get("fk"), "fd": prow.get("fd"),
                "acs": prow.get("acs"),
            }
            if pt == ta:
                agents_a.append(agent)
                pa_rows.append(pd_dict)
            elif pt == tb:
                agents_b.append(agent)
                pb_rows.append(pd_dict)

        if len(agents_a) != 5 or len(agents_b) != 5:
            continue

        match_rows.append(_make_match_row(
            mkey, dkey, source, date_str, year_val, event,
            map_norm, ta, tb, sa, sb, lbl,
            agents_a, agents_b, prov,
        ))
        comp_rows.append(_build_comp_row(mkey, "a", map_norm, agents_a))
        comp_rows.append(_build_comp_row(mkey, "b", map_norm, agents_b))

        for side, plist in (("a", pa_rows), ("b", pb_rows)):
            for slot, pd_row in enumerate(sorted(plist, key=lambda x: x["player"]), 1):
                player_rows.append(_make_player_row(
                    mkey, dkey, side, slot, pd_row["player"], pd_row["agent"],
                    pd_row["kills"], pd_row["deaths"], pd_row["assists"],
                    pd_row["kast"], pd_row["adr"], pd_row["hs"],
                    pd_row["fk"], pd_row["fd"], pd_row["acs"],
                    source, prov,
                ))


# ─────────────────────────── VLR.gg builder ─────────────────────────────────

def load_vlrgg(
    vlrgg_root: Path,
    match_rows: list,
    player_rows: list,
    comp_rows: list,
    map_aux_rows: list,
) -> dict[str, Any]:
    """Build vlrgg training rows from maps.csv + players.csv + details.csv."""
    maps_path = vlrgg_root / "maps.csv"
    players_path = vlrgg_root / "players.csv"
    details_path = vlrgg_root / "details.csv"
    matches_path = vlrgg_root / "matches.csv"

    if not maps_path.exists():
        print("  vlrgg: maps.csv not found, skipping")
        return {"year_event": 0, "year_patch": 0, "year_unknown": 0, "usable_games": 0}

    print("  vlrgg: building match_id→year lookup...")
    mid_year: dict[str, tuple[int, str]] = {}

    if details_path.exists():
        det = pd.read_csv(details_path, low_memory=False)
        for _, row in det.iterrows():
            mid = str(int(float(row["match_id"])))
            y, src = _extract_year_from_text(row.get("event"), row.get("date"))
            if y:
                mid_year[mid] = (y, src)

    if matches_path.exists():
        vmatch = pd.read_csv(matches_path, low_memory=False)
        for _, row in vmatch.iterrows():
            mid = str(int(float(row["match_id"])))
            if mid not in mid_year:
                y, src = _extract_year_from_text(row.get("event"), None)
                if y:
                    mid_year[mid] = (y, src)

    print(f"  vlrgg: {len(mid_year)} match_ids with year; loading maps.csv ({maps_path})")
    maps_df = pd.read_csv(maps_path, low_memory=False)
    maps_df["match_id_str"] = maps_df["match_id"].apply(lambda x: str(int(float(x))))
    maps_df["year_info"] = maps_df["match_id_str"].map(mid_year)

    # Filter: has year, valid map, valid game_id (not in {0,1,2,3,4})
    maps_df = maps_df[maps_df["year_info"].notna()].copy()
    maps_df["year"] = maps_df["year_info"].apply(lambda x: x[0])
    maps_df["year_src"] = maps_df["year_info"].apply(lambda x: x[1])
    maps_df = maps_df[maps_df["map"].isin(VALID_MAPS)]
    bad_game_ids = {"0", "1", "2", "3", "4"}
    maps_df = maps_df[~maps_df["game_id"].astype(str).isin(bad_game_ids)]
    maps_df["agent_count"] = maps_df["agents"].fillna("").apply(
        lambda s: len([x for x in s.split("|") if x.strip()])
    )

    year_src_counts = {"event": 0, "patch": 0, "unknown": 0}
    for v in maps_df["year_src"]:
        year_src_counts[v] = year_src_counts.get(v, 0) + 1

    # Group by game_id: must have exactly 2 rows (one per team), 5 agents, map_winner
    usable_games = 0
    print(f"  vlrgg: grouping {maps_df['game_id'].nunique()} game_ids...")

    if players_path.exists():
        print("  vlrgg: loading players.csv...")
        pl_df = pd.read_csv(players_path, low_memory=False)
        player_lookup: dict[tuple, list] = {}
        for _, row in pl_df.iterrows():
            gid = str(row["game_id"])
            team = norm_team(str(row.get("team", "")).strip())
            key = (gid, team)
            if key not in player_lookup:
                player_lookup[key] = []
            player_lookup[key].append(row)
    else:
        player_lookup = {}

    source = "vlrgg_api_detail"
    for game_id, grp in maps_df.groupby("game_id"):
        if len(grp) != 2:
            continue

        rows = list(grp.itertuples())
        r0, r1 = rows[0], rows[1]

        # Both must have map_winner set and match
        w0 = str(getattr(r0, "map_winner", "") or "").strip()
        w1 = str(getattr(r1, "map_winner", "") or "").strip()
        if not w0 or not w1:
            continue

        # Agents: each team must have 5
        if getattr(r0, "agent_count", 0) < 5 or getattr(r1, "agent_count", 0) < 5:
            continue

        map_norm = normalize_map(str(r0.map))
        if not map_norm:
            continue

        year_val = int(r0.year)
        match_id_str = str(r0.match_id_str)
        event = ""  # event text not stored in maps.csv

        t0 = norm_team(str(r0.team).strip())
        t1 = norm_team(str(r1.team).strip())
        winner = norm_team(w0)

        # Score: use score column, fallback to comparing with map_winner
        try:
            s0 = float(r0.score or 0)
            s1 = float(r1.score or 0)
        except (ValueError, TypeError):
            s0, s1 = (13.0, 5.0) if winner == t0 else (5.0, 13.0)

        if s0 == s1:
            # fallback to map_winner
            s0, s1 = (13.0, 5.0) if winner == t0 else (5.0, 13.0)

        label_t0 = 1 if s0 > s1 else 0
        # Canonical sort
        if t0 <= t1:
            ta, tb, sa, sb, lbl = t0, t1, s0, s1, label_t0
        else:
            ta, tb, sa, sb, lbl = t1, t0, s1, s0, 1 - label_t0

        agents_ta = _agents_from_pipe(str(r0.agents if t0 == ta else r1.agents))
        agents_tb = _agents_from_pipe(str(r1.agents if t1 == tb else r0.agents))

        if len(agents_ta) != 5 or len(agents_tb) != 5:
            continue

        game_id_str = str(game_id)
        raw_id = f"{match_id_str}|{game_id_str}"
        prov = f"{source}/match_{match_id_str}/game_{game_id_str}"
        mkey = make_match_key(source, raw_id, map_norm)
        dkey = make_dedup_key(year_val, ta, tb, map_norm, sa, sb)

        match_rows.append(_make_match_row(
            mkey, dkey, source, "", year_val, event,
            map_norm, ta, tb, sa, sb, lbl,
            agents_ta, agents_tb, prov,
        ))
        comp_rows.append(_build_comp_row(mkey, "a", map_norm, agents_ta))
        comp_rows.append(_build_comp_row(mkey, "b", map_norm, agents_tb))

        # Maps auxiliary row (side details)
        r_a = r0 if t0 == ta else r1
        r_b = r1 if t0 == ta else r0
        for r_side, side_label in ((r_a, "a"), (r_b, "b")):
            map_aux_rows.append({
                "match_key": mkey, "team_side": side_label, "map": map_norm,
                "side_first_half": getattr(r_side, "side_first_half", ""),
                "atk_rounds": getattr(r_side, "atk_rounds", None),
                "def_rounds": getattr(r_side, "def_rounds", None),
                "ot_rounds": getattr(r_side, "ot_rounds", None),
                "score": getattr(r_side, "score", None),
                "source": source,
            })

        # Players
        for side, team_name in (("a", ta), ("b", tb)):
            pdata = player_lookup.get((game_id_str, team_name), [])
            for slot, prow in enumerate(sorted(pdata, key=lambda x: str(x.get("player", "")))[:5], 1):
                agent = normalize_agent(str(prow.get("agent", "")))
                if not agent:
                    continue
                player_rows.append(_make_player_row(
                    mkey, dkey, side, slot,
                    str(prow.get("player", "")).strip(), agent,
                    prow.get("kills"), prow.get("deaths"), prow.get("assists"),
                    prow.get("kast"),
                    prow.get("adr"),
                    prow.get("hs_pct"),
                    prow.get("fb"),   # fb → fk
                    prow.get("fd"),
                    prow.get("acs"),
                    source, prov,
                ))

        usable_games += 1

    return {
        "year_event": year_src_counts.get("event", 0) // 2,
        "year_patch": year_src_counts.get("patch", 0) // 2,
        "year_unknown_dropped": year_src_counts.get("unknown", 0) // 2,
        "usable_games": usable_games,
    }


# ──────────────────────────── orchestrator ──────────────────────────────────

def main(
    kaggle_root: str = "data/raw/kaggle",
    vlrgg_root: str = "data/raw/vlrgg/match",
    output_dir: str = "data/processed",
    reports_dir: str = "reports",
) -> None:
    kaggle_path = Path(kaggle_root)
    vlrgg_path = Path(vlrgg_root)
    out = Path(output_dir)
    rpt = Path(reports_dir)
    out.mkdir(parents=True, exist_ok=True)
    rpt.mkdir(parents=True, exist_ok=True)

    match_rows: list[dict] = []
    player_rows: list[dict] = []
    comp_rows: list[dict] = []
    map_aux_rows: list[dict] = []

    print("=== KAGGLE: ryanluong ===")
    load_ryanluong(kaggle_path, match_rows, player_rows, comp_rows)
    print(f"  → {len(match_rows)} match rows so far")

    print("\n=== KAGGLE: qualidea ===")
    load_qualidea(kaggle_path, match_rows, player_rows, comp_rows)
    print(f"  → {len(match_rows)} match rows so far")

    print("\n=== KAGGLE: ediashtarevin ===")
    load_ediashtarevin(kaggle_path, match_rows, player_rows, comp_rows)
    print(f"  → {len(match_rows)} match rows so far")

    print("\n=== KAGGLE: piyush ===")
    load_piyush(kaggle_path, match_rows, player_rows, comp_rows)
    print(f"  → {len(match_rows)} match rows so far")

    print("\n=== VLR.gg ===")
    vlrgg_stats = load_vlrgg(vlrgg_path, match_rows, player_rows, comp_rows, map_aux_rows)
    print(f"  vlrgg usable games: {vlrgg_stats['usable_games']}")
    print(f"  → {len(match_rows)} total match rows")

    # ── Build DataFrames ──────────────────────────────────────────────
    print("\n=== Building DataFrames ===")
    matches_df = pd.DataFrame(match_rows, columns=MATCHES_COLS)
    players_df = pd.DataFrame(player_rows, columns=PLAYERS_COLS)
    comps_df = pd.DataFrame(comp_rows, columns=COMPS_COLS)
    maps_aux_df = pd.DataFrame(map_aux_rows, columns=MAPS_COLS)

    print(f"Raw: {len(matches_df)} matches, {len(players_df)} player rows")

    # ── kd clipping: cap extreme KD ratios (kills 20-27, deaths 0-1) at 10.0 ──
    kd_clipped_count = int((players_df["kd"] > 10.0).sum())
    players_df["kd"] = players_df["kd"].clip(upper=10.0)
    print(f"kd clipping: clipped {kd_clipped_count} player rows (kd > 10 → 10.0)")

    # ── Source-level match_key dedup ──────────────────────────────────
    before_dedup1 = len(matches_df)
    matches_df = matches_df.drop_duplicates(subset="match_key", keep="first").reset_index(drop=True)
    intra_dedup = before_dedup1 - len(matches_df)
    print(f"Intra-source dedup: removed {intra_dedup} rows")

    # ── Cross-source dedup_key dedup (kaggle preferred over vlrgg) ────
    # Sort: kaggle rows first (lower source_priority)
    matches_df["_is_kaggle"] = matches_df["source"].str.startswith("kaggle_").astype(int)
    matches_df = matches_df.sort_values("_is_kaggle", ascending=False)  # kaggle=1 first
    before_dedup2 = len(matches_df)
    matches_df = matches_df.drop_duplicates(subset="dedup_key", keep="first").reset_index(drop=True)
    cross_dedup = before_dedup2 - len(matches_df)
    matches_df = matches_df.drop(columns="_is_kaggle")
    print(f"Cross-source dedup: removed {cross_dedup} rows")

    # ── Score=0 filter: remove forfeit/no-play matches (score 0 on either side) ──
    zero_score_mask = (matches_df["score_a"].fillna(-1) == 0) | (matches_df["score_b"].fillna(-1) == 0)
    zero_score_dropped = int(zero_score_mask.sum())
    matches_df = matches_df[~zero_score_mask].reset_index(drop=True)
    print(f"Score=0 filter: dropped {zero_score_dropped} forfeit/zero-score matches")

    # ── 5v5 enforcement: match_key must have side a=5 and b=5 in players ──
    # Filter players to only match_keys in matches
    valid_keys = set(matches_df["match_key"])
    players_df = players_df[players_df["match_key"].isin(valid_keys)].copy()

    side_counts = (
        players_df.groupby(["match_key", "side"]).size().reset_index(name="cnt")
        .pivot_table(index="match_key", columns="side", values="cnt", fill_value=0)
        .reset_index()
    )
    if "a" in side_counts.columns and "b" in side_counts.columns:
        good_keys = set(side_counts[
            (side_counts["a"] == 5) & (side_counts["b"] == 5)
        ]["match_key"])
    else:
        good_keys = set()

    drop_5v5 = len(matches_df[~matches_df["match_key"].isin(good_keys)])
    matches_df = matches_df[matches_df["match_key"].isin(good_keys)].reset_index(drop=True)
    players_df = players_df[players_df["match_key"].isin(good_keys)].reset_index(drop=True)
    print(f"5v5 gate: dropped {drop_5v5} matches without exact 5+5 players")
    print(f"Final: {len(matches_df)} matches, {len(players_df)} player rows")

    # Source counts
    source_counts: dict[str, int] = matches_df["source"].value_counts().to_dict()
    year_counts: dict[str, int] = matches_df["year"].astype(str).value_counts().sort_index().to_dict()

    # ── Write outputs ─────────────────────────────────────────────────
    matches_out = out / "matches.csv"
    players_out = out / "players.csv"
    comps_out = out / "comps.csv"
    maps_out = out / "maps.csv"

    matches_df.to_csv(matches_out, index=False)
    players_df.to_csv(players_out, index=False)

    # comps: filter to valid match_keys
    final_keys = set(matches_df["match_key"])
    comps_df = comps_df[comps_df["match_key"].isin(final_keys)].reset_index(drop=True)
    comps_df.to_csv(comps_out, index=False)

    maps_aux_df_out = maps_aux_df[maps_aux_df["match_key"].isin(final_keys)].reset_index(drop=True)
    maps_aux_df_out.to_csv(maps_out, index=False)

    print(f"\n→ {matches_out}")
    print(f"→ {players_out}")
    print(f"→ {comps_out}")
    print(f"→ {maps_out}")

    # ── Ingest summary ────────────────────────────────────────────────
    summary = {
        "dedup_key_version": "v2_score_based",
        "total_matches": int(len(matches_df)),
        "total_players": int(len(players_df)),
        "intra_source_dedup_removed": int(intra_dedup),
        "cross_source_dedup_removed": int(cross_dedup),
        "zero_score_dropped": zero_score_dropped,
        "kd_clipped_count": kd_clipped_count,
        "five_v_five_dropped": int(drop_5v5),
        "by_source": {k: int(v) for k, v in source_counts.items()},
        "by_year": {k: int(v) for k, v in year_counts.items()},
        "vlrgg_year_coverage": {
            "year_from_event": int(vlrgg_stats.get("year_event", 0)),
            "year_from_patch": int(vlrgg_stats.get("year_patch", 0)),
            "year_unknown_dropped": int(vlrgg_stats.get("year_unknown_dropped", 0)),
            "usable_games": int(vlrgg_stats.get("usable_games", 0)),
        },
        "unknown_map_or_agent_note": "rows with unrecognized map or <5 agents dropped by 5v5 gate",
    }
    summary_path = rpt / "ingest_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"→ {summary_path}")

    # ── Data quality report ───────────────────────────────────────────────
    deaths_zero_count = int((players_df["deaths"] == 0).sum())
    kast_null_by_source: dict[str, float] = {}
    if "source" in players_df.columns and "kast" in players_df.columns:
        for src, grp in players_df.groupby("source"):
            kast_null_by_source[str(src)] = round(float(grp["kast"].isna().mean() * 100), 2)
    dq_report = {
        "total_matches_before": int(before_dedup1),
        "total_matches_after": int(len(matches_df)),
        "zero_score_dropped": zero_score_dropped,
        "kd_clipped_count": kd_clipped_count,
        "deaths_zero_count": deaths_zero_count,
        "kast_null_pct_by_source": kast_null_by_source,
        "note_kast_nan": (
            "kast NaN rows propagate through RunningStats.sums; "
            "XGBoost/LightGBM handle NaN natively via learned split direction. "
            "No imputation applied (intentional)."
        ),
    }
    dq_path = rpt / "data_quality_report.json"
    with open(dq_path, "w") as f:
        json.dump(dq_report, f, indent=2)
    print(f"→ {dq_path}")

    print("\n=== Summary ===")
    for src, cnt in sorted(source_counts.items()):
        print(f"  {src}: {cnt}")
    print(f"  Total: {len(matches_df)} matches")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaggle", default="data/raw/kaggle")
    ap.add_argument("--vlrgg", default="data/raw/vlrgg/match")
    ap.add_argument("--output", default="data/processed")
    ap.add_argument("--reports", default="reports")
    args = ap.parse_args()
    main(args.kaggle, args.vlrgg, args.output, args.reports)
