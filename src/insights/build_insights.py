"""Precompute insight aggregations for the insight panel and feature engineering.

Reads data/processed/matches.csv and players.csv to produce:
  - agent_map_fit.json  : {map: {agent: win_rate}}
  - meta_comps.json     : {map: [{comp, win_rate, count}]}

players.csv has: match_key, side (a/b), agent, role, ...
matches.csv has: match_key, map, team_a, team_b, label (1 = team_a wins)

Usage:
    python -m insights.build_insights --input data/processed --output reports/insights
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def _load_data(input_dir: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    base = Path(input_dir)
    matches = pd.read_csv(base / "matches.csv", low_memory=False)
    players = pd.read_csv(base / "players.csv", low_memory=False)
    matches["match_key"] = matches["match_key"].astype(str)
    players["match_key"] = players["match_key"].astype(str)
    return matches, players


def _title(val: object) -> str:
    return str(val).strip().title() if pd.notna(val) else ""


def _build_match_info(matches: pd.DataFrame) -> dict[str, tuple[str, int]]:
    """Return {match_key: (map_title, label)} for rows with valid map+label."""
    info: dict[str, tuple[str, int]] = {}
    for _, row in matches.dropna(subset=["label", "map"]).iterrows():
        map_name = _title(row["map"])
        if map_name:
            info[str(row["match_key"])] = (map_name, int(row["label"]))
    return info


def _side_won(side: str, label: int) -> int | None:
    """Return 1 if this side won, 0 if lost, None if side is unknown."""
    s = side.strip().lower()
    if s == "a":
        return int(label == 1)
    if s == "b":
        return int(label == 0)
    return None


def build_agent_map_fit(matches: pd.DataFrame, players: pd.DataFrame) -> dict:
    """Compute agent win rates per map: {map: {agent: win_rate}}.

    label == 1 → side a wins; label == 0 → side b wins.
    """
    if not {"label", "map"}.issubset(matches.columns):
        return {}
    if not {"agent", "side"}.issubset(players.columns):
        return {}

    match_info = _build_match_info(matches)
    records = []
    for _, row in players.dropna(subset=["agent", "side"]).iterrows():
        mk = str(row["match_key"])
        if mk not in match_info:
            continue
        map_name, label = match_info[mk]
        agent = _title(row["agent"])
        if not agent:
            continue
        won = _side_won(str(row["side"]), label)
        if won is None:
            continue
        records.append({"map": map_name, "agent": agent, "won": won})

    if not records:
        return {}

    df = pd.DataFrame(records)
    result: dict[str, dict[str, float]] = {}
    for (map_name, agent), grp in df.groupby(["map", "agent"]):
        if len(grp) < 10:
            continue
        result.setdefault(str(map_name), {})[str(agent)] = round(float(grp["won"].mean()), 4)
    return result


def build_meta_comps(
    matches: pd.DataFrame, players: pd.DataFrame, top_k: int = 10
) -> dict:
    """Compute top compositions per map: {map: [{comp, win_rate, count}]}."""
    if not {"label", "map"}.issubset(matches.columns):
        return {}
    if not {"agent", "side"}.issubset(players.columns):
        return {}

    match_info = _build_match_info(matches)
    pdf = players.dropna(subset=["agent", "side"]).copy()
    pdf["agent"] = pdf["agent"].map(_title)
    pdf = pdf[pdf["agent"] != ""]

    comp_rows = []
    for (mk, side), grp in pdf.groupby(["match_key", "side"]):
        mk_str = str(mk)
        if mk_str not in match_info:
            continue
        map_name, label = match_info[mk_str]
        agents = sorted(grp["agent"].unique())
        if len(agents) < 5:
            continue
        won = _side_won(str(side), label)
        if won is None:
            continue
        comp_rows.append({"map": map_name, "comp": "|".join(agents[:5]), "won": won})

    if not comp_rows:
        return {}

    df = pd.DataFrame(comp_rows)
    result: dict[str, list[dict]] = {}
    for (map_name, comp), grp in df.groupby(["map", "comp"]):
        count = len(grp)
        if count < 5:
            continue
        result.setdefault(str(map_name), []).append({
            "comp": str(comp),
            "win_rate": round(float(grp["won"].mean()), 4),
            "count": count,
        })

    for map_name in result:
        result[map_name] = sorted(result[map_name], key=lambda x: -x["win_rate"])[:top_k]
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Build insight aggregations")
    parser.add_argument("--input", default="data/processed")
    parser.add_argument("--output", default="reports/insights")
    args = parser.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    print(f"Loading data from {args.input} ...")
    matches, players = _load_data(args.input)
    print(f"  matches={len(matches):,}, players={len(players):,}")

    print("Building agent_map_fit ...")
    agent_map_fit = build_agent_map_fit(matches, players)
    n_entries = sum(len(v) for v in agent_map_fit.values())
    print(f"  {len(agent_map_fit)} maps, {n_entries} (map, agent) entries")
    (out / "agent_map_fit.json").write_text(json.dumps(agent_map_fit, indent=2, ensure_ascii=False))

    print("Building meta_comps ...")
    meta_comps = build_meta_comps(matches, players)
    print(f"  {len(meta_comps)} maps")
    (out / "meta_comps.json").write_text(json.dumps(meta_comps, indent=2, ensure_ascii=False))

    print(f"Done → {out}/")


if __name__ == "__main__":
    main()
