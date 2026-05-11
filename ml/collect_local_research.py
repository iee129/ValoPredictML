from __future__ import annotations

import argparse
import ast
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from ml.agent_roles import normalize_agent, normalize_event, normalize_map, normalize_player, normalize_team

PICK_BAN_COLUMNS = [
    "dataset_id", "source_path", "source_row", "match_id", "game_id", "event",
    "team", "action", "map", "ingested_at",
]
ECONOMY_COLUMNS = [
    "dataset_id", "source_path", "source_row", "match_id", "game_id", "event",
    "map", "team", "team_id", "pistol_wins", "eco_rounds", "eco_wins",
    "semieco_rounds", "semieco_wins", "semibuy_rounds", "semibuy_wins",
    "fullbuy_rounds", "fullbuy_wins", "ingested_at",
]
CLUTCH_COUNTER_COLUMNS = [
    "dataset_id", "source_path", "source_row", "match_id", "game_id", "event",
    "player", "team", "team_id", "opponent", "stat_scope", "kills", "deaths",
    "multi_kills_2k", "multi_kills_3k", "multi_kills_4k", "multi_kills_5k",
    "one_v_one", "one_v_two", "one_v_three", "one_v_four", "one_v_five",
    "econ_rating", "plants", "defuses", "ingested_at",
]
PLAYER_MAP_COLUMNS = [
    "dataset_id", "source_path", "source_row", "match_id", "game_id", "event",
    "event_stage", "match_date", "map", "map_winner", "team", "player",
    "player_id", "agent", "stat_type", "rating", "acs", "kills", "deaths",
    "assists", "kd_diff", "kast", "adr", "hs_pct", "first_kills",
    "first_deaths", "first_kill_diff", "total_utilization",
    "map_utilization", "metric_scope", "ingested_at",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _clean(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        try:
            missing = pd.isna(value)
        except (TypeError, ValueError):
            missing = False
        if isinstance(missing, bool) and missing:
            return ""
    return str(value).strip()


def _num(value: Any) -> float | None:
    text = _clean(value).replace(",", "").replace("%", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _int(value: Any) -> int | None:
    number = _num(value)
    return int(number) if number is not None else None


def _pct(value: Any) -> float | None:
    number = _num(value)
    if number is None:
        return None
    return number / 100.0 if number > 1.5 else number


def _dataset_id(path: Path, root: Path) -> str:
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path
    return rel.parts[0] if rel.parts else path.parent.name


def _source_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _read_csv(path: Path, inventory: list[dict[str, Any]], root: Path, output: str) -> pd.DataFrame:
    if not path.exists():
        inventory.append({"path": _source_path(path, root), "exists": False, "output": output})
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, low_memory=False)
    except Exception as exc:
        inventory.append({
            "path": _source_path(path, root),
            "exists": True,
            "output": output,
            "error": f"{type(exc).__name__}: {exc}",
        })
        return pd.DataFrame()
    inventory.append({
        "path": _source_path(path, root),
        "exists": True,
        "output": output,
        "rows": int(len(df)),
        "columns": list(df.columns),
    })
    return df


def _ensure_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=columns)
    out = df.copy()
    for column in columns:
        if column not in out.columns:
            out[column] = None
    return out[columns]


def _parse_buy_pair(value: Any) -> tuple[int | None, int | None]:
    text = _clean(value)
    if not text:
        return None, None
    # Handles strings like "4 (2)": attempts (wins).
    import re

    match = re.match(r"^\s*(\d+)\s*(?:\((\d+)\))?\s*$", text)
    if not match:
        return _int(text), None
    rounds = int(match.group(1))
    wins = int(match.group(2)) if match.group(2) is not None else None
    return rounds, wins


def collect_pick_ban(root: Path, inventory: list[dict[str, Any]], ingested_at: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("pick_ban.csv")):
        df = _read_csv(path, inventory, root, "research_pick_ban")
        dataset_id = _dataset_id(path, root)
        for idx, row in df.iterrows():
            rows.append({
                "dataset_id": dataset_id,
                "source_path": _source_path(path, root),
                "source_row": int(idx),
                "match_id": _clean(row.get("match_id")),
                "game_id": _clean(row.get("game_id")),
                "event": normalize_event(_clean(row.get("event_name", row.get("event")))),
                "team": normalize_team(_clean(row.get("team"))),
                "action": _clean(row.get("pb_phase", row.get("action"))).lower(),
                "map": normalize_map(_clean(row.get("map"))) or _clean(row.get("map")),
                "ingested_at": ingested_at,
            })
    return _ensure_columns(pd.DataFrame(rows), PICK_BAN_COLUMNS)


def collect_economy_csv(root: Path, inventory: list[dict[str, Any]], ingested_at: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for filename in ("economy.csv", "economy_data.csv"):
        for path in sorted(root.rglob(filename)):
            df = _read_csv(path, inventory, root, "research_economy")
            dataset_id = _dataset_id(path, root)
            for idx, row in df.iterrows():
                if filename == "economy.csv":
                    rows.append({
                        "dataset_id": dataset_id,
                        "source_path": _source_path(path, root),
                        "source_row": int(idx),
                        "match_id": _clean(row.get("match_id")),
                        "game_id": _clean(row.get("game_id")),
                        "event": normalize_event(_clean(row.get("event_name", row.get("event")))),
                        "map": normalize_map(_clean(row.get("map"))) or _clean(row.get("map")),
                        "team": normalize_team(_clean(row.get("team"))),
                        "team_id": _clean(row.get("team_id")),
                        "pistol_wins": _int(row.get("team_pistol_win")),
                        "eco_rounds": _int(row.get("team_eco_round")),
                        "eco_wins": _int(row.get("team_eco_win")),
                        "semieco_rounds": _int(row.get("team_semieco_round")),
                        "semieco_wins": _int(row.get("team_semieco_win")),
                        "semibuy_rounds": _int(row.get("team_semibuy_round")),
                        "semibuy_wins": _int(row.get("team_semibuy_win")),
                        "fullbuy_rounds": _int(row.get("team_fullbuy_round")),
                        "fullbuy_wins": _int(row.get("team_fullbuy_win")),
                        "ingested_at": ingested_at,
                    })
                else:
                    eco_rounds, eco_wins = _parse_buy_pair(row.get("Eco (won)"))
                    semieco_rounds, semieco_wins = _parse_buy_pair(row.get("Semi-eco (won)"))
                    semibuy_rounds, semibuy_wins = _parse_buy_pair(row.get("Semi-buy (won)"))
                    fullbuy_rounds, fullbuy_wins = _parse_buy_pair(row.get("Full buy(won)"))
                    rows.append({
                        "dataset_id": dataset_id,
                        "source_path": _source_path(path, root),
                        "source_row": int(idx),
                        "match_id": _clean(row.get("match_id")),
                        "game_id": _clean(row.get("game_id")),
                        "event": normalize_event(_clean(row.get("event_name", row.get("event")))),
                        "map": normalize_map(_clean(row.get("map"))) or _clean(row.get("map")),
                        "team": normalize_team(_clean(row.get("Team", row.get("team")))),
                        "team_id": _clean(row.get("team_id")),
                        "pistol_wins": _int(row.get("Pistol Won")),
                        "eco_rounds": eco_rounds,
                        "eco_wins": eco_wins,
                        "semieco_rounds": semieco_rounds,
                        "semieco_wins": semieco_wins,
                        "semibuy_rounds": semibuy_rounds,
                        "semibuy_wins": semibuy_wins,
                        "fullbuy_rounds": fullbuy_rounds,
                        "fullbuy_wins": fullbuy_wins,
                        "ingested_at": ingested_at,
                    })
    return _ensure_columns(pd.DataFrame(rows), ECONOMY_COLUMNS)


def collect_clutch_counter_csv(root: Path, inventory: list[dict[str, Any]], ingested_at: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("counter_kill.csv")):
        df = _read_csv(path, inventory, root, "research_clutch_counter")
        dataset_id = _dataset_id(path, root)
        for idx, row in df.iterrows():
            rows.append({
                "dataset_id": dataset_id,
                "source_path": _source_path(path, root),
                "source_row": int(idx),
                "match_id": _clean(row.get("match_id")),
                "game_id": _clean(row.get("game_id")),
                "event": normalize_event(_clean(row.get("event_name", row.get("event")))),
                "player": normalize_player(_clean(row.get("player"))),
                "team": normalize_team(_clean(row.get("team"))),
                "team_id": _clean(row.get("team_id")),
                "opponent": "",
                "stat_scope": "counter_kill",
                "kills": None,
                "deaths": None,
                "multi_kills_2k": _int(row.get("2k")),
                "multi_kills_3k": _int(row.get("3k")),
                "multi_kills_4k": _int(row.get("4k")),
                "multi_kills_5k": _int(row.get("5k")),
                "one_v_one": _int(row.get("1v1")),
                "one_v_two": _int(row.get("1v2")),
                "one_v_three": _int(row.get("1v3")),
                "one_v_four": _int(row.get("1v4")),
                "one_v_five": _int(row.get("1v5")),
                "econ_rating": _num(row.get("econ_rating")),
                "plants": _int(row.get("plant")),
                "defuses": _int(row.get("defuse")),
                "ingested_at": ingested_at,
            })
    for path in sorted(root.rglob("1v1.csv")):
        df = _read_csv(path, inventory, root, "research_clutch_counter")
        dataset_id = _dataset_id(path, root)
        for idx, row in df.iterrows():
            rows.append({
                "dataset_id": dataset_id,
                "source_path": _source_path(path, root),
                "source_row": int(idx),
                "match_id": _clean(row.get("match_id")),
                "game_id": _clean(row.get("game_id")),
                "event": normalize_event(_clean(row.get("event_name", row.get("event")))),
                "player": normalize_player(_clean(row.get("player"))),
                "team": normalize_team(_clean(row.get("team"))),
                "team_id": _clean(row.get("team_id")),
                "opponent": normalize_player(_clean(row.get("opponent"))),
                "stat_scope": _clean(row.get("type")) or "1v1",
                "kills": _int(row.get("kills")),
                "deaths": _int(row.get("deaths")),
                "ingested_at": ingested_at,
            })
    return _ensure_columns(pd.DataFrame(rows), CLUTCH_COUNTER_COLUMNS)


def collect_player_map_csv(root: Path, inventory: list[dict[str, Any]], ingested_at: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("detailed_matches_player_stats.csv")):
        df = _read_csv(path, inventory, root, "research_player_map_stats")
        dataset_id = _dataset_id(path, root)
        for idx, row in df.iterrows():
            rows.append({
                "dataset_id": dataset_id,
                "source_path": _source_path(path, root),
                "source_row": int(idx),
                "match_id": _clean(row.get("match_id")),
                "game_id": _clean(row.get("game_id")),
                "event": normalize_event(_clean(row.get("event_name", row.get("event")))),
                "event_stage": _clean(row.get("event_stage")),
                "match_date": _clean(row.get("match_date")),
                "map": normalize_map(_clean(row.get("map_name", row.get("map")))) or _clean(row.get("map_name", row.get("map"))),
                "map_winner": normalize_team(_clean(row.get("map_winner"))),
                "team": normalize_team(_clean(row.get("player_team", row.get("team")))),
                "player": normalize_player(_clean(row.get("player_name", row.get("player")))),
                "player_id": _clean(row.get("player_id")),
                "agent": normalize_agent(_clean(row.get("agent"))) or _clean(row.get("agent")),
                "stat_type": _clean(row.get("stat_type")),
                "rating": _num(row.get("rating")),
                "acs": _num(row.get("acs")),
                "kills": _int(row.get("k", row.get("kills"))),
                "deaths": _int(row.get("d", row.get("deaths"))),
                "assists": _int(row.get("a", row.get("assists"))),
                "kd_diff": _int(row.get("kd_diff")),
                "kast": _pct(row.get("kast")),
                "adr": _num(row.get("adr")),
                "hs_pct": _pct(row.get("hs_percent", row.get("hs_pct"))),
                "first_kills": _int(row.get("fk", row.get("first_kills"))),
                "first_deaths": _int(row.get("fd", row.get("first_deaths"))),
                "first_kill_diff": _int(row.get("fk_fd_diff", row.get("first_kill_diff"))),
                "metric_scope": "player_map",
                "ingested_at": ingested_at,
            })
    for path in sorted(root.rglob("agents_stats.csv")):
        df = _read_csv(path, inventory, root, "research_player_map_stats")
        dataset_id = _dataset_id(path, root)
        for idx, row in df.iterrows():
            agent = normalize_agent(_clean(row.get("agent_name", row.get("agent")))) or _clean(row.get("agent_name", row.get("agent")))
            raw_map_values = _clean(row.get("map_utilizations"))
            try:
                map_values = ast.literal_eval(raw_map_values) if raw_map_values else {}
            except (SyntaxError, ValueError):
                map_values = {}
            if not isinstance(map_values, dict) or not map_values:
                map_values = {"": None}
            for map_name, utilization in map_values.items():
                rows.append({
                    "dataset_id": dataset_id,
                    "source_path": _source_path(path, root),
                    "source_row": int(idx),
                    "agent": agent,
                    "map": normalize_map(_clean(map_name)) or _clean(map_name),
                    "total_utilization": _pct(row.get("total_utilization")),
                    "map_utilization": _pct(utilization),
                    "metric_scope": "agent_map_utilization",
                    "ingested_at": ingested_at,
                })
    return _ensure_columns(pd.DataFrame(rows), PLAYER_MAP_COLUMNS)


def collect_sqlite(root: Path, inventory: list[dict[str, Any]], ingested_at: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    economy_rows: list[dict[str, Any]] = []
    clutch_rows: list[dict[str, Any]] = []
    player_rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("valorant.sqlite")):
        dataset_id = _dataset_id(path, root)
        try:
            con = sqlite3.connect(path)
            games = pd.read_sql_query("select * from Games", con)
            scoreboard = pd.read_sql_query("select * from Game_Scoreboard", con)
            matches = pd.read_sql_query("select * from Matches", con)
            con.close()
        except Exception as exc:
            inventory.append({
                "path": _source_path(path, root),
                "exists": True,
                "output": "sqlite_research",
                "error": f"{type(exc).__name__}: {exc}",
            })
            continue
        inventory.append({
            "path": _source_path(path, root),
            "exists": True,
            "output": "sqlite_research",
            "tables": {
                "Games": int(len(games)),
                "Game_Scoreboard": int(len(scoreboard)),
                "Matches": int(len(matches)),
            },
        })
        match_lookup = matches.set_index("MatchID").to_dict("index") if "MatchID" in matches.columns else {}
        game_lookup = games.set_index("GameID").to_dict("index") if "GameID" in games.columns else {}
        for idx, row in games.iterrows():
            match = match_lookup.get(row.get("MatchID"), {})
            for side in ("Team1", "Team2"):
                economy_rows.append({
                    "dataset_id": dataset_id,
                    "source_path": _source_path(path, root),
                    "source_row": int(idx),
                    "match_id": _clean(row.get("MatchID")),
                    "game_id": _clean(row.get("GameID")),
                    "event": normalize_event(_clean(match.get("EventName"))),
                    "map": normalize_map(_clean(row.get("Map"))) or _clean(row.get("Map")),
                    "team": normalize_team(_clean(row.get(side))),
                    "team_id": _clean(row.get(f"{side}ID")),
                    "pistol_wins": _int(row.get(f"{side}_PistolWon")),
                    "eco_rounds": _int(row.get(f"{side}_Eco")),
                    "eco_wins": _int(row.get(f"{side}_EcoWon")),
                    "semieco_rounds": _int(row.get(f"{side}_SemiEco")),
                    "semieco_wins": _int(row.get(f"{side}_SemiEcoWon")),
                    "semibuy_rounds": _int(row.get(f"{side}_SemiBuy")),
                    "semibuy_wins": _int(row.get(f"{side}_SemiBuyWon")),
                    "fullbuy_rounds": _int(row.get(f"{side}_FullBuy")),
                    "fullbuy_wins": _int(row.get(f"{side}_FullBuyWon")),
                    "ingested_at": ingested_at,
                })
        for idx, row in scoreboard.iterrows():
            game = game_lookup.get(row.get("GameID"), {})
            match = match_lookup.get(game.get("MatchID"), {})
            common = {
                "dataset_id": dataset_id,
                "source_path": _source_path(path, root),
                "source_row": int(idx),
                "match_id": _clean(game.get("MatchID")),
                "game_id": _clean(row.get("GameID")),
                "event": normalize_event(_clean(match.get("EventName"))),
                "team": normalize_team(_clean(row.get("TeamAbbreviation"))),
                "player": normalize_player(_clean(row.get("PlayerName"))),
                "player_id": _clean(row.get("PlayerID")),
                "agent": normalize_agent(_clean(row.get("Agent"))) or _clean(row.get("Agent")),
                "ingested_at": ingested_at,
            }
            clutch_rows.append({
                **common,
                "stat_scope": "scoreboard_clutch_counter",
                "kills": _int(row.get("Kills")),
                "deaths": _int(row.get("Deaths")),
                "multi_kills_2k": _int(row.get("Num_2Ks")),
                "multi_kills_3k": _int(row.get("Num_3Ks")),
                "multi_kills_4k": _int(row.get("Num_4Ks")),
                "multi_kills_5k": _int(row.get("Num_5Ks")),
                "one_v_one": _int(row.get("OnevOne")),
                "one_v_two": _int(row.get("OnevTwo")),
                "one_v_three": _int(row.get("OnevThree")),
                "one_v_four": _int(row.get("OnevFour")),
                "one_v_five": _int(row.get("OnevFive")),
                "econ_rating": _num(row.get("Econ")),
                "plants": _int(row.get("Plants")),
                "defuses": _int(row.get("Defuses")),
            })
            player_rows.append({
                **common,
                "event_stage": _clean(match.get("EventStage")),
                "match_date": _clean(match.get("Date")),
                "map": normalize_map(_clean(game.get("Map"))) or _clean(game.get("Map")),
                "map_winner": normalize_team(_clean(game.get("Winner"))),
                "stat_type": "map",
                "acs": _num(row.get("ACS")),
                "kills": _int(row.get("Kills")),
                "deaths": _int(row.get("Deaths")),
                "assists": _int(row.get("Assists")),
                "kd_diff": _int(row.get("PlusMinus")),
                "kast": _pct(row.get("KAST_Percent")),
                "adr": _num(row.get("ADR")),
                "hs_pct": _pct(row.get("HS_Percent")),
                "first_kills": _int(row.get("FirstKills")),
                "first_deaths": _int(row.get("FirstDeaths")),
                "first_kill_diff": _int(row.get("FKFD_PlusMinus")),
                "metric_scope": "sqlite_scoreboard",
            })
    return (
        _ensure_columns(pd.DataFrame(economy_rows), ECONOMY_COLUMNS),
        _ensure_columns(pd.DataFrame(clutch_rows), CLUTCH_COUNTER_COLUMNS),
        _ensure_columns(pd.DataFrame(player_rows), PLAYER_MAP_COLUMNS),
    )


def build_outputs(input_dir: Path) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    ingested_at = _utc_now()
    inventory_rows: list[dict[str, Any]] = []
    pick_ban = collect_pick_ban(input_dir, inventory_rows, ingested_at)
    economy_csv = collect_economy_csv(input_dir, inventory_rows, ingested_at)
    clutch_csv = collect_clutch_counter_csv(input_dir, inventory_rows, ingested_at)
    player_csv = collect_player_map_csv(input_dir, inventory_rows, ingested_at)
    economy_sql, clutch_sql, player_sql = collect_sqlite(input_dir, inventory_rows, ingested_at)

    outputs = {
        "research_pick_ban": pick_ban,
        "research_economy": _ensure_columns(
            pd.concat([economy_csv, economy_sql], ignore_index=True) if not economy_csv.empty or not economy_sql.empty else pd.DataFrame(),
            ECONOMY_COLUMNS,
        ),
        "research_clutch_counter": _ensure_columns(
            pd.concat([clutch_csv, clutch_sql], ignore_index=True) if not clutch_csv.empty or not clutch_sql.empty else pd.DataFrame(),
            CLUTCH_COUNTER_COLUMNS,
        ),
        "research_player_map_stats": _ensure_columns(
            pd.concat([player_csv, player_sql], ignore_index=True) if not player_csv.empty or not player_sql.empty else pd.DataFrame(),
            PLAYER_MAP_COLUMNS,
        ),
    }
    inventory = {
        "generated_at": ingested_at,
        "input": str(input_dir),
        "outputs": {
            name: {
                "rows": int(len(df)),
                "columns": list(df.columns),
                "sources": sorted(set(df["source_path"].dropna().astype(str))) if "source_path" in df.columns and not df.empty else [],
            }
            for name, df in outputs.items()
        },
        "source_inventory": inventory_rows,
        "network_requests": 0,
    }
    return outputs, inventory


def run(args: argparse.Namespace) -> None:
    input_dir = Path(args.input)
    output_dir = Path(args.output)
    reports_dir = Path(args.reports)
    output_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    outputs, inventory = build_outputs(input_dir)
    for name, df in outputs.items():
        df.to_csv(output_dir / f"{name}.csv", index=False)
    (reports_dir / "research_source_inventory.json").write_text(
        json.dumps(inventory, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(
        "local research normalization complete: "
        + " ".join(f"{name}={len(df)}" for name, df in outputs.items())
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize local raw Valorant research datasets")
    parser.add_argument("--input", default="data/raw/kaggle")
    parser.add_argument("--output", default="data/processed")
    parser.add_argument("--reports", default="reports")
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
