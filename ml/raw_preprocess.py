"""Raw-only preprocessing helpers used by the repository tests and docs.

This module keeps raw VLR detail JSON conversion separate from the active
baseline model contract. It writes small, inspectable CSV artifacts under the
caller-provided output directory and never reads from processed data as input.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Iterable

import pandas as pd


class RawInputError(ValueError):
    pass


FORBIDDEN_FEATURE_TERMS = ("acs", "kd", "kast", "adr", "score", "round", "economy", "clutch")
MATCH_FIELDS = [
    "match_key",
    "dedup_key",
    "source",
    "source_priority",
    "date",
    "date_raw",
    "date_quality",
    "event",
    "map",
    "team_a",
    "team_b",
    "score_a",
    "score_b",
    "label",
    "agents_a",
    "agents_b",
    "provenance",
]
PLAYER_FIELDS = [
    "match_key",
    "dedup_key",
    "side",
    "team",
    "player_slot",
    "player",
    "agent",
    "acs",
    "kills",
    "deaths",
    "assists",
    "kast",
    "adr",
    "hs_pct",
    "fk",
    "fd",
    "source",
    "provenance",
]


def assert_raw_input_root(path: Path | str) -> Path:
    resolved = Path(path).resolve()
    if "processed" in {part.lower() for part in resolved.parts}:
        raise RawInputError(f"Refusing to use processed path as raw input: {resolved}")
    return resolved


def _sha1(text: str, length: int = 24) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:length]


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _parse_int(value: object, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _normalize_date(raw: str) -> tuple[str, str]:
    text = _clean_text(raw)
    if re.match(r"^\d{4}-\d{2}-\d{2}$", text):
        return text, "iso"
    if re.search(
        r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+\d{1,2}\b",
        text,
        flags=re.IGNORECASE,
    ):
        return "", "partial"
    parsed = pd.to_datetime(text, errors="coerce", utc=True)
    if pd.notna(parsed):
        return str(parsed.date()), "partial"
    return "", "missing"


def canonical_dedup_key(row: dict) -> str:
    """Return a stable key when the same map is represented with team order flipped."""
    teams = []
    for side in ("a", "b"):
        team = _clean_text(row.get(f"team_{side}"))
        score = _parse_int(row.get(f"score_{side}"))
        players = row.get(f"players_{side}") or []
        agents = sorted(_clean_text(player.get("agent")) for player in players if player.get("agent"))
        teams.append({"team": team, "score": score, "agents": agents})
    teams = sorted(teams, key=lambda item: (item["team"].lower(), "|".join(item["agents"])))
    payload = {
        "date": _clean_text(row.get("date") or row.get("date_raw")),
        "event": _clean_text(row.get("event")),
        "map": _clean_text(row.get("map")),
        "teams": teams,
    }
    return _sha1(json.dumps(payload, sort_keys=True, ensure_ascii=False), 24)


def validate_match_candidate(row: dict) -> tuple[dict | None, str | None, dict]:
    score_a = _parse_int(row.get("score_a"))
    score_b = _parse_int(row.get("score_b"))
    if score_a == score_b:
        return None, "draw_map", {}

    for side in ("a", "b"):
        players = row.get(f"players_{side}") or []
        agents = [_clean_text(player.get("agent")).lower() for player in players if player.get("agent")]
        if len(agents) != len(set(agents)):
            return None, "duplicate_agent_in_team", {"side": side}
        if len(players) != 5:
            return None, "invalid_player_count", {"side": side, "count": len(players)}

    clean = dict(row)
    clean["label"] = 1 if score_a > score_b else 0
    clean["dedup_key"] = canonical_dedup_key(row)
    return clean, None, {}


def forbidden_feature_columns(frame: pd.DataFrame) -> list[str]:
    offenders = []
    for column in frame.columns:
        lower = column.lower()
        if column == "source":
            continue
        if any(term in lower for term in FORBIDDEN_FEATURE_TERMS):
            offenders.append(column)
    return offenders


def _iter_detail_files(input_dir: Path) -> Iterable[Path]:
    root = input_dir / "vlrgg" / "collection_runs"
    if not root.exists():
        return []
    return sorted(root.rglob("*.json"))


def _extract_segments(payload: dict) -> list[dict]:
    data = payload.get("data") or {}
    if isinstance(data, dict) and isinstance(data.get("data"), dict):
        data = data["data"]
    segments = data.get("segments") if isinstance(data, dict) else None
    return segments if isinstance(segments, list) else []


def _players_for_side(raw_players: list[dict], match_key: str, dedup_key: str, side: str, team: str, source: str) -> list[dict]:
    rows = []
    for idx, player in enumerate(raw_players[:5], start=1):
        rows.append(
            {
                "match_key": match_key,
                "dedup_key": dedup_key,
                "side": side,
                "team": team,
                "player_slot": idx,
                "player": _clean_text(player.get("name") or player.get("player")),
                "agent": _clean_text(player.get("agent")),
                "acs": _clean_text(player.get("acs")),
                "kills": _clean_text(player.get("kills")),
                "deaths": _clean_text(player.get("deaths")),
                "assists": _clean_text(player.get("assists")),
                "kast": _clean_text(player.get("kast")),
                "adr": _clean_text(player.get("adr")),
                "hs_pct": _clean_text(player.get("hs_pct") or player.get("hs")),
                "fk": _clean_text(player.get("fk")),
                "fd": _clean_text(player.get("fd")),
                "source": source,
                "provenance": source,
            }
        )
    return rows


def _candidate_from_map(segment: dict, map_row: dict, source: str) -> dict:
    match_id = _clean_text(segment.get("match_id"))
    map_name = _clean_text(map_row.get("map_name") or map_row.get("map"))
    teams = segment.get("teams") or [{}, {}]
    team_a = _clean_text(teams[0].get("name") if len(teams) > 0 else "team1")
    team_b = _clean_text(teams[1].get("name") if len(teams) > 1 else "team2")
    score = map_row.get("score") or {}
    score_a = _parse_int(score.get("team1"))
    score_b = _parse_int(score.get("team2"))
    players = map_row.get("players") or {}
    players_a = players.get("team1") or []
    players_b = players.get("team2") or []
    date_raw = _clean_text(segment.get("date"))
    date, date_quality = _normalize_date(date_raw)
    event = _clean_text((segment.get("event") or {}).get("name") if isinstance(segment.get("event"), dict) else segment.get("event"))
    match_key = _sha1(f"{source}|{match_id}|{map_name}", 16)
    return {
        "match_key": match_key,
        "source": "raw_vlrgg_detail",
        "source_priority": 1,
        "date": date,
        "date_raw": date_raw,
        "date_quality": date_quality,
        "event": event,
        "map": map_name,
        "team_a": team_a,
        "team_b": team_b,
        "score_a": score_a,
        "score_b": score_b,
        "players_a": [
            {"player": _clean_text(player.get("name") or player.get("player")), "agent": _clean_text(player.get("agent"))}
            for player in players_a[:5]
        ],
        "players_b": [
            {"player": _clean_text(player.get("name") or player.get("player")), "agent": _clean_text(player.get("agent"))}
            for player in players_b[:5]
        ],
        "_raw_players_a": players_a,
        "_raw_players_b": players_b,
        "_source_file": source,
    }


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = sorted({key for row in rows for key in row.keys()}) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def _lineup_features(matches: list[dict]) -> list[dict]:
    rows = []
    for row in matches:
        rows.append(
            {
                "match_key": row["match_key"],
                "date": row["date"],
                "date_quality": row["date_quality"],
                "map": row["map"],
                "a_players": 5,
                "b_players": 5,
                "a_agents": len(row["agents_a"].split("|")),
                "b_agents": len(row["agents_b"].split("|")),
                "label": row["label"],
                "source": row["source"],
            }
        )
    return rows


def _static_features(matches: list[dict]) -> list[dict]:
    rows = []
    team_history: dict[str, list[int]] = {}
    for row in sorted(matches, key=lambda item: (item["date"], item["match_key"])):
        if row["date_quality"] != "iso":
            continue
        a_hist = team_history.get(row["team_a"], [])
        b_hist = team_history.get(row["team_b"], [])
        rows.append(
            {
                "match_key": row["match_key"],
                "date": row["date"],
                "date_quality": row["date_quality"],
                "map": row["map"],
                "a_team_prior_games": len(a_hist),
                "a_team_prior_wr": (sum(a_hist) / len(a_hist)) if a_hist else 0.0,
                "b_team_prior_games": len(b_hist),
                "b_team_prior_wr": (sum(b_hist) / len(b_hist)) if b_hist else 0.0,
                "label": row["label"],
                "source": row["source"],
            }
        )
        team_history.setdefault(row["team_a"], []).append(int(row["label"] == 1))
        team_history.setdefault(row["team_b"], []).append(int(row["label"] == 0))
    return rows


def run_raw_preprocess(
    input_dir: Path | str,
    output_dir: Path | str,
    reports_dir: Path | str,
    smoke_limit: int = 0,
    run_model_check: bool = False,
) -> dict:
    raw_root = assert_raw_input_root(input_dir)
    output_root = Path(output_dir)
    reports_root = Path(reports_dir)
    detail_files = list(_iter_detail_files(raw_root))
    if smoke_limit:
        detail_files = detail_files[:smoke_limit]

    matches: list[dict] = []
    players: list[dict] = []
    rejects: list[dict] = []
    for path in detail_files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        for segment in _extract_segments(payload):
            for map_row in segment.get("maps") or []:
                candidate = _candidate_from_map(segment, map_row, str(path))
                clean, reason, detail = validate_match_candidate(candidate)
                if clean is None:
                    rejects.append({"source_file": str(path), "reason": reason, **detail})
                    continue
                raw_players_a = clean.pop("_raw_players_a")
                raw_players_b = clean.pop("_raw_players_b")
                source_file = clean.pop("_source_file")
                clean["agents_a"] = "|".join(player["agent"] for player in clean.pop("players_a"))
                clean["agents_b"] = "|".join(player["agent"] for player in clean.pop("players_b"))
                clean["provenance"] = source_file
                matches.append({key: clean.get(key, "") for key in MATCH_FIELDS})
                players.extend(_players_for_side(raw_players_a, clean["match_key"], clean["dedup_key"], "a", clean["team_a"], source_file))
                players.extend(_players_for_side(raw_players_b, clean["match_key"], clean["dedup_key"], "b", clean["team_b"], source_file))

    teams = sorted({row["team_a"] for row in matches} | {row["team_b"] for row in matches})
    lineup = _lineup_features(matches)
    static = _static_features(matches)

    _write_csv(output_root / "files.csv", [{"path": str(path)} for path in detail_files])
    _write_csv(output_root / "schemas.csv", [{"name": "matches"}, {"name": "players"}])
    _write_csv(output_root / "sources.csv", [{"source": "raw_vlrgg_detail", "rows": len(matches)}])
    _write_csv(output_root / "matches.csv", matches, MATCH_FIELDS)
    _write_csv(output_root / "players.csv", players, PLAYER_FIELDS)
    _write_csv(output_root / "teams.csv", [{"team": team} for team in teams])
    _write_csv(output_root / "rejects.csv", rejects)
    _write_csv(output_root / "features_lineup.csv", lineup)
    _write_csv(output_root / "features_static.csv", static)
    _write_csv(output_root / "train.csv", static[: max(1, len(static) - 2)] if static else [])
    _write_csv(output_root / "val.csv", static[max(1, len(static) - 2) : max(1, len(static) - 1)] if static else [])
    _write_csv(output_root / "test.csv", static[max(1, len(static) - 1) :] if static else [])

    reports_root.mkdir(parents=True, exist_ok=True)
    _write_csv(
        reports_root / "comparison.csv",
        [
            {"dataset": "features_lineup", "rows": len(lineup)},
            {"dataset": "features_static", "rows": len(static)},
        ],
    )
    (reports_root / "decision.md").write_text(
        "# Raw Preprocess Decision\n\nReport-only raw preprocess artifacts generated.\n",
        encoding="utf-8",
    )

    return {
        "accepted_rows": len(matches),
        "static_rows": len(static),
        "rejected_rows": len(rejects),
        "run_model_check": bool(run_model_check),
        "forbidden_lineup_feature_columns": forbidden_feature_columns(pd.DataFrame(lineup)),
        "forbidden_static_feature_columns": forbidden_feature_columns(pd.DataFrame(static)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--reports", required=True)
    parser.add_argument("--smoke-limit", type=int, default=0)
    args = parser.parse_args()
    summary = run_raw_preprocess(args.input, args.output, args.reports, smoke_limit=args.smoke_limit)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
