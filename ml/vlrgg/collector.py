from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
import random
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.robotparser import RobotFileParser

import pandas as pd
import requests

def _sha1(s: str, length: int) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="replace")).hexdigest()[:length]


def make_match_key(source: str, filepath: str, match_id: str, map_name: str) -> str:
    return _sha1(f"{source}|{filepath}|{match_id}|{map_name}", 16)


def make_dedup_key(
    date: str, event: str, map_name: str,
    team_a: str, team_b: str,
    agents_a: list[str], agents_b: list[str],
    score_a: int, score_b: int,
) -> str:
    canonical = "|".join([
        str(date).strip(),
        event.lower().strip(),
        map_name.lower(),
        team_a.lower(),
        team_b.lower(),
        ",".join(sorted(a.lower() for a in agents_a)),
        ",".join(sorted(a.lower() for a in agents_b)),
        str(score_a),
        str(score_b),
    ])
    return _sha1(canonical, 24)


from ml.agent_roles import (
    AGENT_ROLE_MAP,
    MAP_ORDER,
    get_role,
    normalize_agent,
    normalize_event,
    normalize_map,
    normalize_player,
    normalize_team,
)
from ml.vlrgg.client import (
    DEFAULT_API_BASE_URL,
    DEFAULT_API_VERSION,
    PLAYER_TIMESPANS,
    REGIONS,
    TIMESPANS,
    VLRGGClient,
    VLRGGRateLimitError,
    parse_retry_after_seconds,
    raise_for_limit_like_response,
)

PARSER_VERSION = "vlrgg-collector-v1"
DEFAULT_CACHE_DIR = "data/raw/vlrgg/api_cache"
DEFAULT_KAGGLE_PROXY_DIR = "data/raw/kaggle/hidious__valorant-vlrgg-results-and-stats"
DEFAULT_OUTPUT_DIR = "data/raw/vlrgg"
DEFAULT_REPORTS_DIR = "reports"
DEFAULT_STATE_FILE = ".omx/state/vlrgg_collection_state.json"
DEFAULT_STAGE_OUTPUT_DIR = ".omx/state/vlrgg_collection_outputs"
DEFAULT_BACKFILL_SHARD_CACHE_ROOT = "data/raw/vlrgg/api_cache/shards"
DEFAULT_BACKFILL_SHARD_OUTPUT_ROOT = ".omx/state/vlrgg_shards"
DEFAULT_BACKFILL_SHARD_REPORTS_ROOT = "reports/vlrgg_shards"
DEFAULT_BACKFILL_SHARD_STATE_ROOT = ".omx/state/vlrgg_shards"
DEFAULT_UPSTREAM_LOCK_FILE = ".omx/state/vlrgg_upstream.lock"
ROBOTS_URL = "https://www.vlr.gg/robots.txt"
ROBOTS_ALLOWED_PATHS = [
    "/",
    "/stats",
    "/events",
    "/event/",
    "/event/stats/",
    "/event/agents/",
    "/event/matches/",
    "/matches/results",
    "/player/",
    "/team/",
    "/team/stats/",
    "/team/transactions/",
    "/vct-2024/standings",
    "/vct-2025/standings",
    "/vct-2026/standings",
]
ROBOTS_BLOCKED_PATHS = ["/search/auto", "/rr", "/rr/"]
DIRECT_HTML_ALLOWED_PATHS = [
    "/matches/results",
    "/event/stats/",
    "/event/agents/",
    "/team/",
    "/team/stats/",
    "/team/transactions/",
]
MAX_DIRECT_HTML_PAGES = 5
DEFAULT_DIRECT_HTML_LIMIT = 100
DEFAULT_DETAIL_LIMIT = 0
DEFAULT_MAX_DETAIL_LIMIT = 5000
DEFAULT_EVENT_LIMIT = 20
DEFAULT_TEAM_LIMIT = 50
DEFAULT_PLAYER_LIMIT = 0
DEFAULT_STANDING_YEARS = "2024,2025,2026"
DEFAULT_MAX_REQUESTS_PER_SESSION = 5000
DEFAULT_API_MATCH_WINDOW_SIZE = 20
DEFAULT_DUPLICATE_OVERLAP_THRESHOLD = 0.05
DEFAULT_LONG_WAIT_SECONDS = 5 * 60 * 60
DEFAULT_RATE_LIMIT_JITTER_SECONDS = 60
MAX_CONSECUTIVE_STAGE_FAILURES = 3
PROVENANCE_FIELDS = [
    "source",
    "source_url",
    "retrieval_method",
    "fetched_at",
    "cache_hit",
    "parser_version",
    "source_hash",
]
DUPLICATE_EXCLUDE_PREFIXES: dict[str, tuple[tuple[str, str], ...]] = {
    "match_id": (
        ("match_detail_maps_", "match_id"),
        ("match_detail_players_", "match_id"),
        ("match_detail_compositions_", "match_id"),
        ("match_details_raw_", "match_id"),
        ("match_rounds_", "match_id"),
        ("match_economy_", "match_id"),
        ("match_kill_matrix_", "match_id"),
        ("match_map_vetoes_", "match_id"),
    ),
    "event_id": (
        ("event_detail_", "event_id"),
        ("event_matches_", "event_id"),
        ("event_player_stats_", "event_id"),
        ("event_agent_usage_", "event_id"),
        ("event_team_candidates_", "event_id"),
        ("event_player_candidates_", "event_id"),
    ),
    "team_id": (
        ("team_map_stats_", "team_id"),
        ("team_profile_direct_", "team_id"),
        ("team_profile_", "team_id"),
        ("team_roster_", "team_id"),
        ("team_rating_history_", "team_id"),
        ("team_matches_", "team_id"),
    ),
}
EVENT_QUERIES = ("completed", "upcoming")
MATCH_QUERIES = ("results", "upcoming", "live_score")
EVENT_CANDIDATE_COLUMNS = [
    "event_id", "event", "status", "region", "dates", "source",
    "source_url", "retrieval_method", "fetched_at", "cache_hit",
    "parser_version", "source_hash",
]
TEAM_CANDIDATE_COLUMNS = [
    "candidate_id", "team_id", "team", "region", "rank", "country",
    "record", "earnings", "status", "status_reason", "priority",
    "source", "source_url", "retrieval_method", "fetched_at",
    "cache_hit", "parser_version", "source_hash",
]
PLAYER_CANDIDATE_COLUMNS = [
    "candidate_id", "player_id", "player", "team_id", "team", "event_id",
    "event", "country", "status", "status_reason", "priority",
    "source", "source_url", "retrieval_method", "fetched_at",
    "cache_hit", "parser_version", "source_hash",
]
API_STATS_COLUMNS = [
    "player", "org", "region", "timespan", "agent", "rounds_played",
    "rating", "average_combat_score", "kill_deaths",
    "average_damage_per_round", "kills_per_round", "assists_per_round",
    "first_kills_per_round", "first_deaths_per_round",
    "headshot_percentage", "clutch_success_percentage", "map_key",
    *PROVENANCE_FIELDS,
]
API_RANKING_COLUMNS = [
    "rank", "team", "region", "country", "last_played",
    "last_played_team", "record", "earnings", *PROVENANCE_FIELDS,
]
API_NEWS_COLUMNS = [
    "title", "description", "date", "author", "url_path", *PROVENANCE_FIELDS,
]
API_MATCH_COLUMNS = [
    "match_id", "event", "date", "round_info", "team_a", "team_b",
    "score_a", "score_b", "label", "map", *PROVENANCE_FIELDS,
]
MATCH_DETAIL_RAW_COLUMNS = [
    "match_id", "event", "date", "status", "teams_json", "maps_json",
    "raw_json", *PROVENANCE_FIELDS,
]
EVENT_DETAIL_COLUMNS = [
    "event_id", "event", "series", "dates", "prize", "location",
    "bracket_json", "prize_distribution_json", "points_json",
    "team_ids_json", "player_ids_json", "raw_json", *PROVENANCE_FIELDS,
]
EVENT_PLAYER_STATS_COLUMNS = [
    "event_id", "event", "player", "team", "agent", "map_key",
    "rounds_played", "rating", "average_combat_score", "kill_deaths",
    "average_damage_per_round", "kills_per_round", "assists_per_round",
    "first_kills_per_round", "first_deaths_per_round",
    "headshot_percentage", "clutch_success_percentage", *PROVENANCE_FIELDS,
]
EVENT_AGENT_USAGE_COLUMNS = [
    "event_id", "event", "map", "agent", "use_count", "use_rate",
    "rounds_played", "win_rate", "raw_metric_json", *PROVENANCE_FIELDS,
]
TEAM_PROFILE_COLUMNS = [
    "team_id", "team", "tag", "country", "region", "rank",
    "current_rating", "record", "core_id", "roster_json",
    "rating_history_json", "event_placements_json", "total_winnings",
    "raw_json", *PROVENANCE_FIELDS,
]
TEAM_ROSTER_COLUMNS = [
    "team_id", "team", "member_type", "player_id", "player", "real_name",
    "role", "status", *PROVENANCE_FIELDS,
]
TEAM_RATING_HISTORY_COLUMNS = [
    "team_id", "team", "core_id", "sequence", "date", "opponent", "event",
    "result", "rating_delta", "rating_after", "opponent_rating", "raw_text",
    *PROVENANCE_FIELDS,
]
TEAM_MATCH_COLUMNS = [
    "team_id", "team", "match_id", "event", "date", "round_info", "opponent",
    "score_for", "score_against", "status", *PROVENANCE_FIELDS,
]
PLAYER_PROFILE_COLUMNS = [
    "player_id", "player", "real_name", "country", "current_teams_json",
    "past_teams_json", "social_handles_json", "agent_stats_json",
    "event_placements_json", "total_winnings", "raw_json",
    *PROVENANCE_FIELDS,
]
PLAYER_AGENT_USAGE_COLUMNS = [
    "player_id", "player", "timespan", "agent", "usage_count",
    "matches_played", "maps_played", "rounds_played", "rating",
    "average_combat_score", "kill_deaths", "average_damage_per_round",
    "kills", "deaths", "assists", "kills_per_round",
    "assists_per_round", "first_kills", "first_deaths",
    "first_kills_per_round", "first_deaths_per_round",
    "headshot_percentage", "clutch_success_percentage", "raw_json",
    *PROVENANCE_FIELDS,
]
PLAYER_RECENT_MATCH_COLUMNS = [
    "player_id", "player", "page", "match_id", "event", "date",
    "round_info", "team_a", "team_b", "score_a", "score_b", "label",
    "map", "raw_json", *PROVENANCE_FIELDS,
]
PLAYER_PROFILE_ROBOTS_PATHS = ["/events", "/event/", "/player/"]
ROUND_COLUMNS = [
    "match_id", "game_id", "map", "round_num", "winner", "side", "team",
    "raw_json", *PROVENANCE_FIELDS,
]
ECONOMY_COLUMNS = [
    "match_id", "team", "pistol", "eco", "semi_eco", "semi_buy", "full_buy",
    "raw_json", *PROVENANCE_FIELDS,
]
KILL_MATRIX_COLUMNS = [
    "match_id", "player", "kills_vs_json", "advanced_stats_json",
    *PROVENANCE_FIELDS,
]
MAP_VETO_COLUMNS = [
    "match_id", "sequence", "team", "action", "map", "raw_text",
    *PROVENANCE_FIELDS,
]
TEAM_TRANSACTION_COLUMNS = [
    "team_id", "team", "date", "action", "player", "position",
    *PROVENANCE_FIELDS,
]
MATCH_MAP_COLUMNS = [
    "match_id", "game_id", "map", "team", "opponent", "side_first_half",
    "atk_rounds", "def_rounds", "ot_rounds", "score", "opponent_score",
    "map_winner", "agents", *PROVENANCE_FIELDS,
]
MATCH_PLAYER_COLUMNS = [
    "match_id", "game_id", "map", "team", "opponent", "player", "agent",
    "rating", "acs", "kills", "deaths", "assists", "kast", "adr", "hs_pct",
    "fb", "fd", "atk_kills", "def_kills", "atk_deaths", "def_deaths",
    *PROVENANCE_FIELDS,
]
COMPOSITION_COLUMNS = [
    "match_id", "game_id", "map", "team", "agents", "comp_key",
    "duelist_count", "initiator_count", "controller_count", "sentinel_count",
    "unknown_role_count", *PROVENANCE_FIELDS,
]
STANDINGS_COLUMNS = [
    "year", "region", "rank", "team", "team_id", "points", "country",
    *PROVENANCE_FIELDS,
]
TEAM_MAP_COLUMNS = [
    "team_id", "team", "map", "games", "win_rate", "wins", "losses",
    "atk_first", "def_first", "atk_rwin_pct", "atk_rw", "atk_rl",
    "def_rwin_pct", "def_rw", "def_rl", *PROVENANCE_FIELDS,
]
EVENT_MATCH_COLUMNS = [
    "event_id", "event", "match_id", "team_a", "team_b", "score_a",
    "score_b", "date", *PROVENANCE_FIELDS,
]
MATCH_CANDIDATE_COLUMNS = [
    "candidate_type", "candidate_id", "match_id", "event_id", "team_id",
    "event", "team", "team_a", "team_b", "score_a", "score_b", "date",
    "source", "source_url", "retrieval_method", "status", "status_reason",
    "priority", "has_detail", "map_count", "player_count", "discovered_at",
    "fetched_at", "parser_version",
]
PIPELINE_MATCH_COLUMNS = [
    "source", "weight", "match_key", "dedup_key", "date", "event", "map",
    "team_a", "team_b", "score_a", "score_b", "agents_a", "agents_b",
    "players_a_json", "players_b_json", "atk_a", "def_a", "label",
    "match_id", "game_id", "source_url", "retrieval_method", "fetched_at",
    "cache_hit", "parser_version", "source_hash",
]
PIPELINE_REJECT_COLUMNS = [
    "match_id", "game_id", "map", "team_a", "team_b", "label",
    "reject_reason", "details",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha1_obj(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha1(raw.encode("utf-8", errors="replace")).hexdigest()


def _pct_to_float(value: Any) -> float | None:
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return None
    text = str(value).strip().replace("%", "")
    if not text:
        return None
    try:
        num = float(text)
    except ValueError:
        return None
    return num / 100.0 if num > 1.5 else num


def _num(value: Any) -> float | None:
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return None
    try:
        return float(str(value).strip().replace(",", ""))
    except ValueError:
        return None


def _int_or_none(value: Any) -> int | None:
    num = _num(value)
    return int(num) if num is not None else None


def _source_url_for_api(base_url: str, path: str, params: dict[str, Any]) -> str:
    if DEFAULT_API_VERSION and not path.startswith(f"/{DEFAULT_API_VERSION}/"):
        path = f"/{DEFAULT_API_VERSION}{path if path.startswith('/') else '/' + path}"
    query = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    return f"{base_url.rstrip('/')}{path}?{query}" if query else f"{base_url.rstrip('/')}{path}"


def _api_coverage_row(
    *,
    endpoint: str,
    params: dict[str, Any] | None,
    rows: int,
    network_requests: int,
    cache_hit: bool,
    status: str,
    source_url: str,
    error: str = "",
) -> dict[str, Any]:
    return {
        "endpoint": endpoint,
        "params": params or {},
        "rows": int(rows),
        "network_requests": int(network_requests),
        "cache_hit": bool(cache_hit),
        "status": status,
        "source_url": source_url,
        "error": error,
        "recorded_at": _utc_now(),
    }


def _extract_match_id_from_row(row: dict[str, Any]) -> str:
    explicit = _clean_id(row.get("match_id", row.get("id")))
    if explicit:
        return explicit
    return _clean_id(VLRGGClient.extract_match_id(_clean_text(row.get("match_page", row.get("url_path", row.get("url", ""))))) or "")


def _event_rows_from_api(
    rows: list[dict[str, Any]],
    *,
    q: str,
    source_url: str,
    fetched_at: str,
    cache_hit: bool,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        url_path = _clean_text(row.get("url_path", row.get("url")))
        event_id = VLRGGClient.extract_event_id(url_path) or _clean_id(row.get("event_id", row.get("id")))
        if not event_id:
            continue
        out.append(_with_provenance({
            "event_id": event_id,
            "event": _clean_text(row.get("title", row.get("event", row.get("name")))),
            "status": _clean_text(row.get("status", q)),
            "region": _clean_text(row.get("region")),
            "dates": _clean_text(row.get("dates", row.get("date"))),
        }, source="vlrgg_api", source_url=url_path or source_url,
            method="api_cache" if cache_hit else "api", fetched_at=fetched_at, cache_hit=cache_hit))
    return out


def _match_rows_from_api(
    rows: list[dict[str, Any]],
    *,
    q: str,
    source_url: str,
    fetched_at: str,
    cache_hit: bool,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        url_path = _clean_text(row.get("url_path", row.get("match_page", row.get("url"))))
        score_a = _int_or_none(row.get("score_a", row.get("score1")))
        score_b = _int_or_none(row.get("score_b", row.get("score2")))
        out.append(_with_provenance({
            "match_id": _extract_match_id_from_row(row),
            "event": _clean_text(row.get("event", row.get("match_event", row.get("tournament_name", row.get("tournament"))))),
            "date": _clean_text(row.get("date", row.get("unix_timestamp", row.get("time_completed", row.get("time_until_match"))))),
            "round_info": _clean_text(row.get("round_info", row.get("match_series", row.get("status", q)))),
            "team_a": normalize_team(_clean_text(row.get("team_a", row.get("team1")))),
            "team_b": normalize_team(_clean_text(row.get("team_b", row.get("team2")))),
            "score_a": score_a,
            "score_b": score_b,
            "label": 1 if score_a is not None and score_b is not None and score_a > score_b else (
                0 if score_a is not None and score_b is not None and score_a < score_b else None
            ),
            "map": normalize_map(_clean_text(row.get("map", row.get("current_map")))) or _clean_text(row.get("map", row.get("current_map"))),
        }, source="vlrgg_api",
            source_url=f"https://www.vlr.gg{url_path}" if url_path.startswith("/") else (url_path or source_url),
            method="api_cache" if cache_hit else "api",
            fetched_at=fetched_at,
            cache_hit=cache_hit))
    return out


def _stats_rows_from_api(
    rows: list[dict[str, Any]],
    *,
    region: str,
    timespan: str,
    source_url: str,
    fetched_at: str,
    cache_hit: bool,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        agents = row.get("agents")
        if not isinstance(agents, list):
            agents = [agents] if agents else [""]
        for agent_raw in agents:
            agent = normalize_agent(str(agent_raw)) or str(agent_raw or "").strip()
            out.append(_with_provenance({
                "player": _clean_text(row.get("player")),
                "org": _clean_text(row.get("org")),
                "region": region,
                "timespan": timespan,
                "agent": agent,
                "rounds_played": _int_or_none(row.get("rounds_played")),
                "rating": _num(row.get("rating")),
                "average_combat_score": _num(row.get("average_combat_score")),
                "kill_deaths": _num(row.get("kill_deaths")),
                "average_damage_per_round": _num(row.get("average_damage_per_round")),
                "kills_per_round": _num(row.get("kills_per_round")),
                "assists_per_round": _num(row.get("assists_per_round")),
                "first_kills_per_round": _num(row.get("first_kills_per_round")),
                "first_deaths_per_round": _num(row.get("first_deaths_per_round")),
                "headshot_percentage": _pct_to_float(row.get("headshot_percentage")),
                "clutch_success_percentage": _pct_to_float(row.get("clutch_success_percentage")),
                "map_key": "",
            }, source="vlrgg_api", source_url=source_url,
                method="api_cache" if cache_hit else "api", fetched_at=fetched_at, cache_hit=cache_hit))
    return out


def _ranking_rows_from_api(
    rows: list[dict[str, Any]],
    *,
    region: str,
    source_url: str,
    fetched_at: str,
    cache_hit: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rankings: list[dict[str, Any]] = []
    teams: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        rank = _int_or_none(row.get("rank"))
        team = normalize_team(_clean_text(row.get("team")))
        team_id = _clean_id(row.get("team_id", row.get("id")))
        if not team_id:
            for key in ("url_path", "url", "team_url", "href"):
                match = re.search(r"/team/(\d+)(?:/|$)", _clean_text(row.get(key)))
                if match:
                    team_id = match.group(1)
                    break
        ranking = _with_provenance({
            "rank": rank,
            "team": team,
            "region": region,
            "country": _clean_text(row.get("country")),
            "last_played": _clean_text(row.get("last_played")),
            "last_played_team": _clean_text(row.get("last_played_team")),
            "record": _clean_text(row.get("record")),
            "earnings": _clean_text(row.get("earnings")),
        }, source="vlrgg_api", source_url=source_url,
            method="api_cache" if cache_hit else "api", fetched_at=fetched_at, cache_hit=cache_hit)
        rankings.append(ranking)
        if team:
            candidate_id = team_id or re.sub(r"\W+", "_", team.lower()).strip("_")
            teams.append(_with_provenance({
                "candidate_id": candidate_id,
                "team_id": team_id,
                "team": team,
                "region": region,
                "rank": rank,
                "country": _clean_text(row.get("country")),
                "record": _clean_text(row.get("record")),
                "earnings": _clean_text(row.get("earnings")),
                "status": "profile_pending",
                "status_reason": "team discovered from rankings; profile not fetched yet",
                "priority": 40,
            }, source="vlrgg_api", source_url=source_url,
                method="api_cache" if cache_hit else "api", fetched_at=fetched_at, cache_hit=cache_hit))
    return rankings, teams


def _news_rows_from_api(
    rows: list[dict[str, Any]],
    *,
    source_url: str,
    fetched_at: str,
    cache_hit: bool,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        out.append(_with_provenance({
            "title": _clean_text(row.get("title")),
            "description": _clean_text(row.get("description")),
            "date": _clean_text(row.get("date")),
            "author": _clean_text(row.get("author")),
            "url_path": _clean_text(row.get("url_path", row.get("url"))),
        }, source="vlrgg_api", source_url=source_url,
            method="api_cache" if cache_hit else "api", fetched_at=fetched_at, cache_hit=cache_hit))
    return out


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, low_memory=False)


def _read_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_json_file(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _stable_backfill_shard(match_id: str, shard_count: int) -> int:
    count = int(shard_count)
    if count <= 0:
        raise ValueError("--backfill-shard-count must be >= 1")
    text = _clean_id(match_id)
    if not text:
        raise ValueError("match_id is required for shard assignment")
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()
    return int(digest, 16) % count


def _backfill_shard_settings(args: argparse.Namespace) -> tuple[int, int]:
    count = int(getattr(args, "backfill_shard_count", 1) or 1)
    index = int(getattr(args, "backfill_shard_index", 0) or 0)
    if count < 1:
        raise ValueError("--backfill-shard-count must be >= 1")
    if index < 0 or index >= count:
        raise ValueError("--backfill-shard-index must be between 0 and backfill_shard_count - 1")
    return count, index


def _backfill_shard_metadata(args: argparse.Namespace) -> dict[str, Any]:
    count, index = _backfill_shard_settings(args)
    return {
        "enabled": count > 1,
        "count": count,
        "index": index,
    }


def _shard_marker(shard_index: int) -> str:
    return f"shard_{int(shard_index)}"


def _path_mentions_shard(path: str | Path, shard_index: int) -> bool:
    marker = _shard_marker(shard_index)
    return any(marker in part for part in Path(path).parts)


def _is_default_path(path: str | Path, default: str) -> bool:
    return Path(path) == Path(default)


def _derive_shard_dir(
    path: str | Path,
    *,
    shard_index: int,
    default_path: str,
    default_shard_root: str,
) -> Path:
    current = Path(path)
    if _path_mentions_shard(current, shard_index):
        return current
    if _is_default_path(current, default_path):
        return Path(default_shard_root) / _shard_marker(shard_index)
    return current / _shard_marker(shard_index)


def _derive_shard_state_file(path: str | Path, shard_index: int) -> Path:
    current = Path(path)
    if _path_mentions_shard(current, shard_index):
        return current
    marker = _shard_marker(shard_index)
    if _is_default_path(current, DEFAULT_STATE_FILE):
        return Path(DEFAULT_BACKFILL_SHARD_STATE_ROOT) / f"{marker}_state.json"
    if current.suffix:
        return current.with_name(f"{current.stem}_{marker}{current.suffix}")
    return current / f"{marker}_state.json"


def _derive_shard_stage_output_dir(path: str | Path, shard_index: int) -> Path:
    current = Path(path)
    if _path_mentions_shard(current, shard_index):
        return current
    marker = _shard_marker(shard_index)
    if _is_default_path(current, DEFAULT_STAGE_OUTPUT_DIR):
        return Path(DEFAULT_BACKFILL_SHARD_STATE_ROOT) / f"{marker}_outputs"
    return current / f"{marker}_outputs"


def apply_backfill_shard_isolation(args: argparse.Namespace) -> None:
    """Make multi-shard backfills safe to run from concurrent sessions.

    When count > 1, every mutable path is forced under a shard-specific path
    unless the caller already supplied a path containing the shard marker.
    The candidates file remains shared/read-only by design.
    """
    shard_count, shard_index = _backfill_shard_settings(args)
    if shard_count <= 1:
        return
    args.cache_dir = _derive_shard_dir(
        getattr(args, "cache_dir", DEFAULT_CACHE_DIR),
        shard_index=shard_index,
        default_path=DEFAULT_CACHE_DIR,
        default_shard_root=DEFAULT_BACKFILL_SHARD_CACHE_ROOT,
    )
    args.output = _derive_shard_dir(
        getattr(args, "output", DEFAULT_OUTPUT_DIR),
        shard_index=shard_index,
        default_path=DEFAULT_OUTPUT_DIR,
        default_shard_root=DEFAULT_BACKFILL_SHARD_OUTPUT_ROOT,
    )
    args.reports = _derive_shard_dir(
        getattr(args, "reports", DEFAULT_REPORTS_DIR),
        shard_index=shard_index,
        default_path=DEFAULT_REPORTS_DIR,
        default_shard_root=DEFAULT_BACKFILL_SHARD_REPORTS_ROOT,
    )
    args.state_file = _derive_shard_state_file(
        getattr(args, "state_file", DEFAULT_STATE_FILE),
        shard_index,
    )
    args.stage_output_dir = _derive_shard_stage_output_dir(
        getattr(args, "stage_output_dir", DEFAULT_STAGE_OUTPUT_DIR),
        shard_index,
    )


class CollectionStageError(RuntimeError):
    def __init__(self, message: str, *, requests_made: int = 0) -> None:
        super().__init__(message)
        self.requests_made = requests_made


class CollectionState:
    def __init__(self, path: Path, *, reset: bool = False) -> None:
        self.path = path
        self.data = {} if reset else _read_json_file(path)
        if not self.data:
            self.data = {
                "created_at": _utc_now(),
                "updated_at": _utc_now(),
                "last_completed_stage": "",
                "last_cursor": {},
                "cumulative_requests": 0,
                "last_success_at": "",
                "failure_reason": "",
                "next_retry_at": "",
                "rate_limit_events": [],
                "stages": {},
            }
            self.save()

    def save(self) -> None:
        self.data["updated_at"] = _utc_now()
        _write_json_file(self.path, self.data)

    def stage(self, name: str) -> dict[str, Any]:
        return self.data.setdefault("stages", {}).setdefault(name, {})

    def add_requests(self, count: int) -> None:
        if count <= 0:
            return
        self.data["cumulative_requests"] = int(self.data.get("cumulative_requests", 0)) + int(count)

    def mark_stage(self, name: str, status: str, **fields: Any) -> None:
        row = self.stage(name)
        row.update({"status": status, "updated_at": _utc_now(), **fields})
        cursor = fields.get("cursor")
        if cursor is not None:
            self.data["last_cursor"] = cursor
        if status == "completed":
            if "failure_reason" not in fields:
                row.pop("failure_reason", None)
            if "next_retry_at" not in fields:
                row.pop("next_retry_at", None)
            self.data["last_completed_stage"] = name
            self.data["last_success_at"] = _utc_now()
            self.data["failure_reason"] = ""
            self.data["next_retry_at"] = ""
        elif status in {"waiting", "degraded", "failed"}:
            reason = str(fields.get("failure_reason", ""))
            self.data["failure_reason"] = reason
            if "next_retry_at" in fields:
                self.data["next_retry_at"] = fields["next_retry_at"]
        self.save()

    def record_rate_limit(self, stage_name: str, wait_seconds: float, exc: VLRGGRateLimitError) -> None:
        events = self.data.setdefault("rate_limit_events", [])
        events.append({
            "stage": stage_name,
            "url": exc.url,
            "status_code": exc.status_code,
            "retry_after": exc.retry_after,
            "wait_seconds": round(float(wait_seconds), 3),
            "recorded_at": _utc_now(),
        })
        self.save()


def _stage_summary(state: CollectionState) -> dict[str, Any]:
    return {
        name: {
            key: value
            for key, value in row.items()
            if key in {
                "status",
                "attempts",
                "rows",
                "network_requests",
                "failure_reason",
                "last_success_at",
                "updated_at",
                "cursor",
                "skipped",
                "details",
            }
        }
        for name, row in sorted(state.data.get("stages", {}).items())
    }


def _next_retry_at(wait_seconds: float) -> str:
    return datetime.fromtimestamp(time.time() + wait_seconds, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rate_limit_wait_seconds(args: argparse.Namespace, exc: VLRGGRateLimitError) -> float:
    retry_after = parse_retry_after_seconds(exc.retry_after)
    if retry_after is None:
        retry_after = DEFAULT_LONG_WAIT_SECONDS + random.uniform(0, DEFAULT_RATE_LIMIT_JITTER_SECONDS)
    cap = float(args.max_rate_limit_wait_seconds)
    return max(0.0, min(float(retry_after), cap))


def _upstream_lock_interval_seconds(args: argparse.Namespace) -> float:
    configured = float(getattr(args, "upstream_lock_min_interval_seconds", 0.0) or 0.0)
    if configured > 0:
        return configured
    rate = float(getattr(args, "rate_limit", 0.0) or 0.0)
    if rate <= 0:
        return 0.0
    return 1.0 / rate


@contextmanager
def _vlrgg_upstream_slot(args: argparse.Namespace, *, stage_name: str):
    """Coordinate VLR.gg upstream detail calls across parallel shard processes."""
    if bool(getattr(args, "disable_upstream_lock", False)):
        yield
        return

    lock_path = Path(getattr(args, "upstream_lock_file", DEFAULT_UPSTREAM_LOCK_FILE))
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        try:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        except ImportError:
            fcntl = None  # type: ignore[assignment]

        try:
            interval = _upstream_lock_interval_seconds(args)
            handle.seek(0)
            raw = handle.read().strip()
            try:
                metadata = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                metadata = {}
            last_started = float(metadata.get("last_started_monotonic", 0.0) or 0.0)
            wait_seconds = interval - (time.monotonic() - last_started)
            if wait_seconds > 0:
                time.sleep(wait_seconds)

            metadata = {
                "last_started_monotonic": time.monotonic(),
                "stage": stage_name,
                "pid": os.getpid(),
                "updated_at": _utc_now(),
                "min_interval_seconds": interval,
            }
            handle.seek(0)
            handle.truncate()
            handle.write(json.dumps(metadata, ensure_ascii=False))
            handle.flush()
            os.fsync(handle.fileno())
            yield
        finally:
            if "fcntl" in locals() and fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _should_retry_empty_match_detail_stage(name: str, stage: dict[str, Any]) -> bool:
    if not name.startswith("match_detail_"):
        return False
    try:
        rows = int(stage.get("rows", 0) or 0)
    except (TypeError, ValueError):
        rows = 0
    if rows > 0:
        return False
    details = stage.get("details") if isinstance(stage.get("details"), dict) else {}
    try:
        map_rows = int(details.get("map_rows", 0) or 0)
        player_rows = int(details.get("player_rows", 0) or 0)
    except (TypeError, ValueError):
        map_rows = 0
        player_rows = 0
    return bool(details.get("used_direct_html_fallback")) or (map_rows == 0 and player_rows == 0)


def _require_match_detail_rows(
    *,
    match_id: str,
    maps: pd.DataFrame,
    players: pd.DataFrame,
    source_label: str,
    requests_made: int,
) -> None:
    if maps.empty or players.empty:
        raise CollectionStageError(
            f"{source_label} did not normalize to map/player rows for match_id={match_id}",
            requests_made=requests_made,
        )


def _is_no_played_map_detail(detail: dict[str, Any]) -> bool:
    maps = _as_list(detail.get("maps"))
    if maps:
        return False
    status = _clean_text(detail.get("status")).lower()
    if not status:
        return False
    return any(token in status for token in ("forfeit", "cancelled", "canceled", "postponed", "walkover"))


def _run_stage_with_resume(
    *,
    args: argparse.Namespace,
    state: CollectionState,
    name: str,
    cursor: dict[str, Any],
    fn: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    stage = state.stage(name)
    if stage.get("status") == "completed" and not args.restart:
        if _should_retry_empty_match_detail_stage(name, stage):
            stage["attempts"] = 0
            state.mark_stage(
                name,
                "failed",
                attempts=0,
                cursor=cursor,
                failure_reason="previous match_detail completion had zero map/player rows",
            )
            stage = state.stage(name)
        else:
            state.mark_stage(name, "completed", skipped=True, cursor=cursor)
            return {"status": "completed", "skipped": True, **stage}

    if stage.get("status") == "degraded" and not args.restart and _should_retry_empty_match_detail_stage(name, stage):
        stage["attempts"] = 0
        state.mark_stage(
            name,
            "failed",
            attempts=0,
            cursor=cursor,
            failure_reason="previous match_detail degradation had zero map/player rows",
        )
        stage = state.stage(name)

    attempts = int(stage.get("attempts", 0) or 0)
    while attempts < MAX_CONSECUTIVE_STAGE_FAILURES:
        attempts += 1
        state.mark_stage(name, "running", attempts=attempts, cursor=cursor)
        try:
            result = fn()
            requests_made = int(result.get("network_requests", 0) or 0)
            state.add_requests(requests_made)
            result_status = str(result.get("status", "completed") or "completed")
            if result_status == "degraded":
                reason = str(result.get("failure_reason", "stage degraded"))
                state.mark_stage(
                    name,
                    "degraded",
                    attempts=attempts,
                    cursor=cursor,
                    rows=result.get("rows", 0),
                    network_requests=requests_made,
                    failure_reason=reason,
                    details={k: v for k, v in result.items() if k not in {"rows", "network_requests", "status", "failure_reason"}},
                )
                return {"status": "degraded", **result}
            state.mark_stage(
                name,
                "completed",
                attempts=attempts,
                cursor=cursor,
                rows=result.get("rows", 0),
                network_requests=requests_made,
                last_success_at=_utc_now(),
                details={k: v for k, v in result.items() if k not in {"rows", "network_requests"}},
            )
            return {"status": "completed", **result}
        except VLRGGRateLimitError as exc:
            state.add_requests(int(getattr(exc, "requests_made", 1) or 1))
            wait_seconds = _rate_limit_wait_seconds(args, exc)
            state.record_rate_limit(name, wait_seconds, exc)
            if attempts >= MAX_CONSECUTIVE_STAGE_FAILURES:
                reason = str(exc)
                state.mark_stage(
                    name,
                    "degraded",
                    attempts=attempts,
                    cursor=cursor,
                    failure_reason=reason,
                    network_requests=int(getattr(exc, "requests_made", 1) or 1),
                )
                return {"status": "degraded", "failure_reason": reason, "network_requests": int(getattr(exc, "requests_made", 1) or 1)}
            next_retry_at = _next_retry_at(wait_seconds)
            state.mark_stage(
                name,
                "waiting",
                attempts=attempts,
                cursor=cursor,
                failure_reason=str(exc),
                next_retry_at=next_retry_at,
            )
            time.sleep(wait_seconds)
        except Exception as exc:
            state.add_requests(int(getattr(exc, "requests_made", 0) or 0))
            reason = f"{type(exc).__name__}: {exc}"
            if attempts >= MAX_CONSECUTIVE_STAGE_FAILURES:
                state.mark_stage(
                    name,
                    "degraded",
                    attempts=attempts,
                    cursor=cursor,
                    failure_reason=reason,
                    network_requests=int(getattr(exc, "requests_made", 0) or 0),
                )
                return {
                    "status": "degraded",
                    "failure_reason": reason,
                    "network_requests": int(getattr(exc, "requests_made", 0) or 0),
                }
            state.mark_stage(name, "failed", attempts=attempts, cursor=cursor, failure_reason=reason)
            time.sleep(float(args.retry_backoff_seconds))

    reason = state.stage(name).get("failure_reason", "stage failed")
    state.mark_stage(name, "degraded", attempts=attempts, cursor=cursor, failure_reason=reason)
    return {"status": "degraded", "failure_reason": reason, "network_requests": 0}


def _reset_stage_attempts(state: CollectionState, name: str) -> None:
    row = state.stage(name)
    if "attempts" in row:
        row.pop("attempts", None)
        state.save()


def _stage_output_path(args: argparse.Namespace, name: str) -> Path:
    safe = re.sub(r"[^\w\-]+", "_", name).strip("_")
    return Path(args.stage_output_dir) / f"{safe}.json"


def _write_stage_frame(args: argparse.Namespace, name: str, df: pd.DataFrame) -> None:
    path = _stage_output_path(args, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(df.to_json(orient="records", force_ascii=False), encoding="utf-8")


def _read_stage_frames(args: argparse.Namespace, prefix: str) -> list[pd.DataFrame]:
    root = Path(args.stage_output_dir)
    frames: list[pd.DataFrame] = []
    if not root.exists():
        return frames
    paths = sorted(root.glob(f"{prefix}*.json"))
    if not paths:
        child_dirs = sorted((path for path in root.iterdir() if path.is_dir()), key=lambda path: path.name)
        for child in reversed(child_dirs):
            paths = sorted(child.glob(f"{prefix}*.json"))
            if paths:
                break
    for path in sorted(paths):
        try:
            df = pd.read_json(path)
        except ValueError:
            continue
        if not df.empty:
            frames.append(df)
    return frames


def _with_provenance(row: dict[str, Any], *, source: str, source_url: str, method: str,
                     fetched_at: str, cache_hit: bool) -> dict[str, Any]:
    out = dict(row)
    out.update({
        "source": source,
        "source_url": source_url,
        "retrieval_method": method,
        "fetched_at": fetched_at,
        "cache_hit": bool(cache_hit),
        "parser_version": PARSER_VERSION,
    })
    out["source_hash"] = _sha1_obj({k: v for k, v in out.items() if k != "source_hash"})
    return out


def validate_provenance(df: pd.DataFrame, name: str) -> None:
    missing = [field for field in PROVENANCE_FIELDS if field not in df.columns]
    if missing:
        raise ValueError(f"{name} missing provenance fields: {missing}")
    if not df.empty:
        empty = [
            field for field in PROVENANCE_FIELDS
            if field != "cache_hit" and df[field].astype(str).str.strip().eq("").any()
        ]
        if empty:
            raise ValueError(f"{name} has empty provenance values: {empty}")


def _ensure_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=columns)
    out = df.copy()
    for column in columns:
        if column not in out.columns:
            out[column] = None
    return out[columns]


def _clean_text(value: Any) -> str:
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


def _clean_id(value: Any) -> str:
    text = _clean_text(value)
    if not text or text.lower() in {"nan", "none"}:
        return ""
    if re.fullmatch(r"\d+\.0", text):
        return text[:-2]
    return text


def _stage_dirs_from_args(args: argparse.Namespace) -> list[Path]:
    return [Path(path) for path in getattr(args, "exclude_stage_output_dirs", []) or []]


def _add_clean_id(target: set[str], value: Any) -> None:
    clean = _clean_id(value)
    if clean:
        target.add(clean)


def _stage_id_from_filename(filename: str, prefix: str) -> str:
    match = re.match(rf"^{re.escape(prefix)}(\d+)(?:_|\.json|$)", filename)
    return _clean_id(match.group(1)) if match else ""


def _load_stage_output_ids(stage_output_dirs: list[Path]) -> dict[str, set[str]]:
    index: dict[str, set[str]] = {id_key: set() for id_key in DUPLICATE_EXCLUDE_PREFIXES}
    for root in stage_output_dirs:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.json")):
            matched: tuple[str, str, str] | None = None
            for id_key, specs in DUPLICATE_EXCLUDE_PREFIXES.items():
                for prefix, column in specs:
                    if path.name.startswith(prefix):
                        matched = (id_key, prefix, column)
                        break
                if matched:
                    break
            if not matched:
                continue
            id_key, prefix, column = matched
            _add_clean_id(index[id_key], _stage_id_from_filename(path.name, prefix))
            try:
                df = pd.read_json(path)
            except ValueError:
                continue
            if column in df.columns:
                for value in df[column].tolist():
                    _add_clean_id(index[id_key], value)
    return index


def _ordered_unique_ids(ids: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in ids:
        clean = _clean_id(value)
        if clean and clean not in seen:
            seen.add(clean)
            out.append(clean)
    return out


def _guard_duplicate_overlap(
    *,
    args: argparse.Namespace,
    state: CollectionState,
    stage_name: str,
    id_key: str,
    candidate_ids: list[str],
    exclude_ids: set[str],
) -> list[str]:
    candidates = _ordered_unique_ids(candidate_ids)
    duplicate_ids = sorted(set(candidates) & set(exclude_ids), key=lambda value: (0, int(value)) if value.isdigit() else (1, value))
    candidate_count = len(candidates)
    duplicate_count = len(duplicate_ids)
    overlap_ratio = (duplicate_count / candidate_count) if candidate_count else 0.0
    threshold = max(0.0, float(getattr(args, "duplicate_overlap_threshold", DEFAULT_DUPLICATE_OVERLAP_THRESHOLD)))
    threshold = min(1.0, threshold)
    details = {
        "id_key": id_key,
        "candidate_count": int(candidate_count),
        "duplicate_count": int(duplicate_count),
        "remaining_count": int(candidate_count - duplicate_count),
        "overlap_ratio": round(float(overlap_ratio), 6),
        "threshold": round(float(threshold), 6),
        "duplicate_ids_sample": duplicate_ids[:20],
        "exclude_stage_output_dirs": [str(path) for path in _stage_dirs_from_args(args)],
    }
    cursor = {"duplicate_guard": stage_name, "id_key": id_key}
    if overlap_ratio > threshold:
        reason = (
            f"{stage_name} duplicate overlap {overlap_ratio:.2%} exceeds "
            f"threshold {threshold:.2%} ({duplicate_count}/{candidate_count})"
        )
        state.mark_stage(
            stage_name,
            "failed",
            cursor=cursor,
            rows=0,
            network_requests=0,
            failure_reason=reason,
            details=details,
        )
        raise CollectionStageError(reason, requests_made=0)
    state.mark_stage(
        stage_name,
        "completed",
        cursor=cursor,
        rows=int(candidate_count - duplicate_count),
        network_requests=0,
        skipped=bool(duplicate_count),
        details=details,
    )
    duplicate_set = set(duplicate_ids)
    return [candidate_id for candidate_id in candidates if candidate_id not in duplicate_set]


def _filter_frame_by_clean_ids(df: pd.DataFrame, column: str, keep_ids: set[str]) -> pd.DataFrame:
    if df.empty or column not in df.columns:
        return df
    out = df.copy()
    mask = out[column].map(_clean_id).isin(keep_ids)
    return out[mask].reset_index(drop=True)


def _normalize_agents(raw_agents: Any) -> list[str]:
    if isinstance(raw_agents, str):
        candidates = [part for part in re.split(r"[|,;/]", raw_agents) if part.strip()]
    elif isinstance(raw_agents, (list, tuple, set)):
        candidates = list(raw_agents)
    else:
        candidates = []
    agents: list[str] = []
    for value in candidates:
        agent = normalize_agent(str(value)) or _clean_text(value).title()
        if agent:
            agents.append(agent)
    return agents


def _agent_join(agents: list[str]) -> str:
    return "|".join(agents)


def _comp_key(agents: list[str]) -> str:
    return "|".join(sorted(agents))


def _role_counts(agents: list[str]) -> dict[str, int]:
    counts = {"Duelist": 0, "Initiator": 0, "Controller": 0, "Sentinel": 0, "Unknown": 0}
    for agent in agents:
        role = get_role(agent) or "Unknown"
        counts[role] = counts.get(role, 0) + 1
    return {
        "duelist_count": counts.get("Duelist", 0),
        "initiator_count": counts.get("Initiator", 0),
        "controller_count": counts.get("Controller", 0),
        "sentinel_count": counts.get("Sentinel", 0),
        "unknown_role_count": counts.get("Unknown", 0),
    }


def _sum_rounds(*values: Any) -> int:
    total = 0
    for value in values:
        parsed = _int_or_none(value)
        if parsed is not None:
            total += parsed
    return total


def _safe_source_url_from_match(match_id: str) -> str:
    return f"https://www.vlr.gg/{match_id}" if match_id else "https://www.vlr.gg/"


def _combine_stage_frames(args: argparse.Namespace, prefix: str, columns: list[str]) -> pd.DataFrame:
    frames = _read_stage_frames(args, prefix)
    if not frames:
        return pd.DataFrame(columns=columns)
    return _ensure_columns(pd.concat(frames, ignore_index=True), columns)


def _limit_frame(df: pd.DataFrame, limit: int) -> pd.DataFrame:
    return df if int(limit) == 0 else df.head(max(0, int(limit)))


def select_match_detail_candidates(matches_df: pd.DataFrame, limit: int) -> list[str]:
    if matches_df.empty or "match_id" not in matches_df.columns or limit < 0:
        return []
    df = matches_df.copy()
    df["match_id"] = df["match_id"].map(_clean_id)
    df = df[df["match_id"].str.fullmatch(r"\d+")]
    if df.empty:
        return []
    priority = {"vlrgg_direct_html": 0, "vlrgg_api": 1, "vlrgg_kaggle_proxy": 2}
    df["_source_priority"] = df.get("source", pd.Series("", index=df.index)).map(priority).fillna(9)
    df["_date_sort"] = pd.to_datetime(df.get("date", pd.Series("", index=df.index)), errors="coerce", utc=True)
    df = df.sort_values(["_source_priority", "_date_sort", "match_id"], ascending=[True, False, False])
    deduped = df.drop_duplicates("match_id")
    return _limit_frame(deduped, int(limit))["match_id"].tolist()


def _load_expanded_match_sources(args: argparse.Namespace, fetched_at: str) -> pd.DataFrame:
    matches_df = _read_csv(Path(args.output) / "vlrgg_matches.csv")
    if not matches_df.empty:
        return matches_df
    proxy_matches, _ = load_kaggle_proxy(Path(args.kaggle_proxy_dir), fetched_at)
    cache_matches, _ = load_api_cache(Path(args.cache_dir), args.api_base_url, fetched_at)
    frames = [df for df in [proxy_matches, cache_matches] if not df.empty]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _detail_counts(maps_df: pd.DataFrame, players_df: pd.DataFrame) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    if not maps_df.empty and "match_id" in maps_df.columns:
        for match_id, grp in maps_df.assign(match_id=maps_df["match_id"].map(_clean_id)).groupby("match_id", dropna=False):
            if not match_id:
                continue
            counts.setdefault(match_id, {})["map_count"] = int(grp.get("game_id", pd.Series(dtype=str)).nunique())
    if not players_df.empty and "match_id" in players_df.columns:
        for match_id, grp in players_df.assign(match_id=players_df["match_id"].map(_clean_id)).groupby("match_id", dropna=False):
            if not match_id:
                continue
            counts.setdefault(match_id, {})["player_count"] = int(len(grp))
    return counts


def _candidate_row(
    *,
    candidate_type: str,
    candidate_id: str,
    discovered_at: str,
    status: str = "pending_detail",
    status_reason: str = "",
    priority: int = 50,
    **fields: Any,
) -> dict[str, Any]:
    row = {column: "" for column in MATCH_CANDIDATE_COLUMNS}
    row.update(fields)
    row.update({
        "candidate_type": candidate_type,
        "candidate_id": _clean_id(candidate_id),
        "status": status,
        "status_reason": status_reason,
        "priority": int(priority),
        "discovered_at": discovered_at,
        "fetched_at": discovered_at,
        "parser_version": PARSER_VERSION,
    })
    return row


def _normalize_match_candidates(candidates_df: pd.DataFrame) -> pd.DataFrame:
    out = _ensure_columns(candidates_df, MATCH_CANDIDATE_COLUMNS).copy()
    if out.empty:
        return out
    fetched = out.get("fetched_at", pd.Series("", index=out.index)).astype(str).str.strip()
    discovered = out.get("discovered_at", pd.Series("", index=out.index)).astype(str)
    out.loc[fetched.eq(""), "fetched_at"] = discovered
    return _ensure_columns(out, MATCH_CANDIDATE_COLUMNS)


def build_match_candidates(
    *,
    matches_df: pd.DataFrame,
    event_matches_df: pd.DataFrame,
    standings_df: pd.DataFrame,
    maps_df: pd.DataFrame,
    players_df: pd.DataFrame,
    event_candidates_df: pd.DataFrame | None,
    discovered_at: str,
) -> pd.DataFrame:
    detail = _detail_counts(maps_df, players_df)
    rows: list[dict[str, Any]] = []

    def _match_status(match_id: str) -> tuple[str, str, bool, int, int]:
        info = detail.get(match_id, {})
        map_count = int(info.get("map_count", 0) or 0)
        player_count = int(info.get("player_count", 0) or 0)
        has_detail = map_count > 0 and player_count > 0
        if has_detail:
            return "detail_complete", "match detail stage output exists", True, map_count, player_count
        return "pending_detail", "match id is known but map/player detail is not complete", False, map_count, player_count

    if not matches_df.empty and "match_id" in matches_df.columns:
        for _, row in matches_df.iterrows():
            match_id = _clean_id(row.get("match_id"))
            if not match_id:
                continue
            status, reason, has_detail, map_count, player_count = _match_status(match_id)
            source = _clean_text(row.get("source"))
            source_priority = {"vlrgg_direct_html": 10, "vlrgg_api": 20, "vlrgg_kaggle_proxy": 30}.get(source, 40)
            rows.append(_candidate_row(
                candidate_type="match",
                candidate_id=match_id,
                discovered_at=discovered_at,
                match_id=match_id,
                event=_clean_text(row.get("event")),
                team_a=normalize_team(_clean_text(row.get("team_a"))),
                team_b=normalize_team(_clean_text(row.get("team_b"))),
                score_a=_int_or_none(row.get("score_a")),
                score_b=_int_or_none(row.get("score_b")),
                date=_clean_text(row.get("date")),
                source=source,
                source_url=_clean_text(row.get("source_url")),
                retrieval_method=_clean_text(row.get("retrieval_method")),
                status=status,
                status_reason=reason,
                priority=source_priority,
                has_detail=has_detail,
                map_count=map_count,
                player_count=player_count,
            ))

    if not event_matches_df.empty and "match_id" in event_matches_df.columns:
        for _, row in event_matches_df.iterrows():
            match_id = _clean_id(row.get("match_id"))
            if not match_id:
                continue
            status, reason, has_detail, map_count, player_count = _match_status(match_id)
            rows.append(_candidate_row(
                candidate_type="match",
                candidate_id=match_id,
                discovered_at=discovered_at,
                match_id=match_id,
                event_id=_clean_id(row.get("event_id")),
                event=_clean_text(row.get("event")),
                team_a=normalize_team(_clean_text(row.get("team_a"))),
                team_b=normalize_team(_clean_text(row.get("team_b"))),
                score_a=_int_or_none(row.get("score_a")),
                score_b=_int_or_none(row.get("score_b")),
                date=_clean_text(row.get("date")),
                source=_clean_text(row.get("source")),
                source_url=_clean_text(row.get("source_url")),
                retrieval_method=_clean_text(row.get("retrieval_method")),
                status=status,
                status_reason=reason,
                priority=5,
                has_detail=has_detail,
                map_count=map_count,
                player_count=player_count,
            ))

    if event_candidates_df is not None and not event_candidates_df.empty:
        for _, row in event_candidates_df.iterrows():
            event_id = _clean_id(row.get("event_id"))
            if not event_id:
                continue
            rows.append(_candidate_row(
                candidate_type="event",
                candidate_id=event_id,
                discovered_at=discovered_at,
                event_id=event_id,
                event=_clean_text(row.get("event")),
                source=_clean_text(row.get("source")),
                source_url=_clean_text(row.get("source_url", row.get("url_path"))),
                retrieval_method=_clean_text(row.get("retrieval_method")),
                status="profile_pending",
                status_reason="event can expand to event detail and match candidates",
                priority=15,
            ))

    if not standings_df.empty and "team_id" in standings_df.columns:
        for _, row in standings_df.iterrows():
            team_id = _clean_id(row.get("team_id"))
            if not team_id:
                continue
            rows.append(_candidate_row(
                candidate_type="team",
                candidate_id=team_id,
                discovered_at=discovered_at,
                team_id=team_id,
                team=normalize_team(_clean_text(row.get("team"))),
                event=_clean_text(row.get("region")),
                date=_clean_text(row.get("year")),
                source=_clean_text(row.get("source")),
                source_url=_clean_text(row.get("source_url")),
                retrieval_method=_clean_text(row.get("retrieval_method")),
                status="profile_pending",
                status_reason="team profile is useful for candidate expansion and future features",
                priority=60,
            ))

    if not rows:
        return pd.DataFrame(columns=MATCH_CANDIDATE_COLUMNS)
    df = _ensure_columns(pd.DataFrame(rows), MATCH_CANDIDATE_COLUMNS)
    sort_cols = ["priority", "date", "candidate_type", "candidate_id"]
    df = df.sort_values(sort_cols, ascending=[True, False, True, False], kind="stable")
    df = df.drop_duplicates(subset=["candidate_type", "candidate_id"], keep="first")
    return _ensure_columns(df.reset_index(drop=True), MATCH_CANDIDATE_COLUMNS)


def _filter_candidates_for_backfill_shard(
    candidates_df: pd.DataFrame,
    shard_count: int,
    shard_index: int,
) -> pd.DataFrame:
    if candidates_df.empty or int(shard_count) <= 1:
        return candidates_df
    df = candidates_df.copy()
    df["candidate_type"] = df.get("candidate_type", "").astype(str)
    df["match_id"] = df.get("match_id", "").map(_clean_id)
    match_mask = (df["candidate_type"] == "match") & df["match_id"].str.fullmatch(r"\d+", na=False)
    shard_mask = df["match_id"].map(
        lambda value: bool(value) and _stable_backfill_shard(str(value), int(shard_count)) == int(shard_index)
    )
    return _ensure_columns(df[match_mask & shard_mask].reset_index(drop=True), MATCH_CANDIDATE_COLUMNS)


def _with_detail_status_from_frames(
    candidates_df: pd.DataFrame,
    maps_df: pd.DataFrame,
    players_df: pd.DataFrame,
) -> pd.DataFrame:
    if candidates_df.empty:
        return _ensure_columns(candidates_df, MATCH_CANDIDATE_COLUMNS)
    out = _ensure_columns(candidates_df, MATCH_CANDIDATE_COLUMNS).copy()
    detail = _detail_counts(maps_df, players_df)
    if not detail:
        return out
    match_mask = out.get("candidate_type", pd.Series(dtype=str)).astype(str) == "match"
    for idx, row in out[match_mask].iterrows():
        match_id = _clean_id(row.get("match_id"))
        info = detail.get(match_id, {})
        map_count = int(info.get("map_count", 0) or 0)
        player_count = int(info.get("player_count", 0) or 0)
        out.at[idx, "map_count"] = map_count
        out.at[idx, "player_count"] = player_count
        has_detail = map_count > 0 and player_count > 0
        out.at[idx, "has_detail"] = has_detail
        if has_detail:
            out.at[idx, "status"] = "detail_complete"
            out.at[idx, "status_reason"] = "match detail stage output exists"
        elif str(out.at[idx, "status"]) == "detail_complete":
            out.at[idx, "status"] = "pending_detail"
            out.at[idx, "status_reason"] = "match id is known but map/player detail is not complete"
    return _ensure_columns(out, MATCH_CANDIDATE_COLUMNS)


def _with_detail_status_from_stage_outputs(candidates_df: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    maps_df = _combine_stage_frames(args, "match_detail_maps_", MATCH_MAP_COLUMNS)
    players_df = _combine_stage_frames(args, "match_detail_players_", MATCH_PLAYER_COLUMNS)
    return _with_detail_status_from_frames(candidates_df, maps_df, players_df)


def _candidate_ids_for_backfill(
    candidates_df: pd.DataFrame,
    limit: int,
    request_budget: int,
    *,
    shard_count: int = 1,
    shard_index: int = 0,
) -> list[str]:
    if candidates_df.empty:
        return []
    df = candidates_df.copy()
    df["candidate_type"] = df.get("candidate_type", "").astype(str)
    df["match_id"] = df.get("match_id", "").map(_clean_id)
    df = df[
        (df["candidate_type"] == "match")
        & df["match_id"].str.fullmatch(r"\d+")
        & (df.get("status", "").astype(str) != "detail_complete")
    ]
    if df.empty:
        return []
    df["_priority"] = pd.to_numeric(df.get("priority"), errors="coerce").fillna(50)
    df["_date_sort"] = pd.to_datetime(df.get("date", pd.Series("", index=df.index)), errors="coerce", utc=True)
    df = df.sort_values(["_priority", "_date_sort", "match_id"], ascending=[True, False, False])
    deduped = df.drop_duplicates("match_id")
    if int(shard_count) > 1:
        deduped = deduped[
            deduped["match_id"].map(
                lambda value: _stable_backfill_shard(str(value), int(shard_count)) == int(shard_index)
            )
        ]
    cap = int(request_budget)
    if int(limit) > 0:
        cap = min(cap, int(limit))
    if cap <= 0:
        return []
    return deduped["match_id"].head(cap).tolist()


def _json_players(players: list[dict[str, Any]]) -> str:
    return json.dumps(players, ensure_ascii=False, sort_keys=True)


def _load_json_players(value: Any) -> list[dict[str, Any]]:
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return []
    try:
        raw = json.loads(str(value))
    except json.JSONDecodeError:
        return []
    return raw if isinstance(raw, list) else []


def _pipeline_player(row: pd.Series) -> dict[str, Any]:
    kills = _num(row.get("kills")) or 0.0
    deaths = _num(row.get("deaths")) or 0.0
    return {
        "player": normalize_player(_clean_text(row.get("player"))),
        "agent": normalize_agent(_clean_text(row.get("agent"))) or _clean_text(row.get("agent")),
        "acs": _num(row.get("acs")),
        "kd": kills / max(deaths, 1.0),
        "kast": _pct_to_float(row.get("kast")),
        "adr": _num(row.get("adr")),
        "fk": _num(row.get("fb")) or 0.0,
        "fd": _num(row.get("fd")) or 0.0,
        "assists": _num(row.get("assists")) or 0.0,
        "hs": _pct_to_float(row.get("hs_pct")),
        "clutch": None,
    }


def _validate_pipeline_candidate(row: dict[str, Any]) -> tuple[bool, str, str]:
    players_a = row.get("players_a") or []
    players_b = row.get("players_b") or []
    agents_a = [p.get("agent") for p in players_a if p.get("agent")]
    agents_b = [p.get("agent") for p in players_b if p.get("agent")]
    if len(players_a) != 5 or len(players_b) != 5:
        return False, "WRONG_PLAYER_COUNT", f"a={len(players_a)} b={len(players_b)}"
    if not all(a in AGENT_ROLE_MAP for a in agents_a + agents_b):
        unknown = sorted({str(a) for a in agents_a + agents_b if a not in AGENT_ROLE_MAP})
        return False, "UNKNOWN_AGENT", ",".join(unknown)
    if row.get("map") not in MAP_ORDER:
        return False, "UNKNOWN_MAP", str(row.get("map", ""))
    if row.get("label") not in (0, 1):
        return False, "INVALID_LABEL", str(row.get("label", ""))
    if row.get("score_a") == row.get("score_b"):
        return False, "DRAW", f"{row.get('score_a')}={row.get('score_b')}"
    if len(set(agents_a)) != 5 or len(set(agents_b)) != 5:
        return False, "DUPLICATE_AGENT_IN_TEAM", ""
    for player in players_a + players_b:
        if pd.isna(player.get("acs")) or pd.isna(player.get("kd")):
            return False, "MISSING_STATS", str(player.get("player", ""))
    return True, "", ""


def build_vlrgg_pipeline_matches(
    maps_df: pd.DataFrame,
    players_df: pd.DataFrame,
    event_matches_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if maps_df.empty or players_df.empty:
        return pd.DataFrame(columns=PIPELINE_MATCH_COLUMNS), pd.DataFrame(columns=PIPELINE_REJECT_COLUMNS)

    maps = maps_df.copy()
    players = players_df.copy()
    maps["match_id"] = maps["match_id"].map(_clean_id)
    maps["game_id"] = maps["game_id"].map(_clean_id)
    players["match_id"] = players["match_id"].map(_clean_id)
    players["game_id"] = players["game_id"].map(_clean_id)
    event_lookup: dict[str, dict[str, Any]] = {}
    if not event_matches_df.empty and "match_id" in event_matches_df.columns:
        for _, row in event_matches_df.iterrows():
            match_id = _clean_id(row.get("match_id"))
            if match_id and match_id not in event_lookup:
                event_lookup[match_id] = row.to_dict()

    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for (match_id, game_id, map_raw), map_grp in maps.groupby(["match_id", "game_id", "map"], dropna=False, sort=False):
        map_name = normalize_map(_clean_text(map_raw)) or _clean_text(map_raw)
        map_grp = map_grp.drop_duplicates(subset=["team"], keep="first")
        if len(map_grp) != 2:
            rejected.append({
                "match_id": match_id,
                "game_id": game_id,
                "map": map_name,
                "team_a": "",
                "team_b": "",
                "label": "",
                "reject_reason": "WRONG_TEAM_COUNT",
                "details": f"team_rows={len(map_grp)}",
            })
            continue

        team_rows = [row for _, row in map_grp.iterrows()]
        row_a, row_b = team_rows[0], team_rows[1]
        team_a = normalize_team(_clean_text(row_a.get("team")))
        team_b = normalize_team(_clean_text(row_b.get("team")))
        score_a = _int_or_none(row_a.get("score"))
        score_b = _int_or_none(row_b.get("score"))
        label = 1 if score_a is not None and score_b is not None and score_a > score_b else (
            0 if score_a is not None and score_b is not None and score_a < score_b else None
        )
        player_grp = players[
            (players["match_id"] == match_id)
            & (players["game_id"] == game_id)
            & (players["map"].astype(str) == str(map_raw))
        ]
        players_a = [_pipeline_player(row) for _, row in player_grp[player_grp["team"].map(normalize_team) == team_a].iterrows()]
        players_b = [_pipeline_player(row) for _, row in player_grp[player_grp["team"].map(normalize_team) == team_b].iterrows()]
        agents_a = [str(p.get("agent", "")) for p in players_a]
        agents_b = [str(p.get("agent", "")) for p in players_b]
        event_row = event_lookup.get(str(match_id), {})
        event = normalize_event(_clean_text(event_row.get("event")))
        date = _clean_text(event_row.get("date"))
        source_url = _clean_text(row_a.get("source_url")) or _safe_source_url_from_match(str(match_id))
        row = {
            "source": "vlrgg_direct_detail",
            "weight": 1.1,
            "match_key": make_match_key("vlrgg_direct_detail", source_url, f"{match_id}|{game_id}", map_name),
            "dedup_key": make_dedup_key(date, event, map_name, team_a, team_b, agents_a, agents_b, score_a or 0, score_b or 0),
            "date": date,
            "event": event,
            "map": map_name,
            "team_a": team_a,
            "team_b": team_b,
            "score_a": score_a,
            "score_b": score_b,
            "agents_a": _agent_join(agents_a),
            "agents_b": _agent_join(agents_b),
            "players_a": players_a,
            "players_b": players_b,
            "atk_a": _int_or_none(row_a.get("atk_rounds")),
            "def_a": _int_or_none(row_a.get("def_rounds")),
            "label": label,
            "match_id": match_id,
            "game_id": game_id,
            "source_url": source_url,
            "retrieval_method": _clean_text(row_a.get("retrieval_method")) or "direct_html_detail",
            "fetched_at": _clean_text(row_a.get("fetched_at")),
            "cache_hit": bool(row_a.get("cache_hit", False)),
            "parser_version": PARSER_VERSION,
        }
        ok, reason, details = _validate_pipeline_candidate(row)
        if not ok:
            rejected.append({
                "match_id": match_id,
                "game_id": game_id,
                "map": map_name,
                "team_a": team_a,
                "team_b": team_b,
                "label": label,
                "reject_reason": reason,
                "details": details,
            })
            continue
        serializable = dict(row)
        serializable["players_a_json"] = _json_players(players_a)
        serializable["players_b_json"] = _json_players(players_b)
        serializable.pop("players_a", None)
        serializable.pop("players_b", None)
        serializable["source_hash"] = _sha1_obj({k: v for k, v in serializable.items() if k != "source_hash"})
        accepted.append(serializable)

    accepted_df = _ensure_columns(pd.DataFrame(accepted), PIPELINE_MATCH_COLUMNS)
    rejected_df = _ensure_columns(pd.DataFrame(rejected), PIPELINE_REJECT_COLUMNS)
    if not accepted_df.empty:
        accepted_df = accepted_df.drop_duplicates(subset=["dedup_key"], keep="last").reset_index(drop=True)
    return accepted_df, rejected_df


def write_pipeline_readiness_outputs(
    maps_df: pd.DataFrame,
    players_df: pd.DataFrame,
    event_matches_df: pd.DataFrame,
    args: argparse.Namespace,
    fetched_at: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    pipeline_df, rejected_df = build_vlrgg_pipeline_matches(maps_df, players_df, event_matches_df)
    pipeline_df.to_csv(args.output / "vlrgg_pipeline_matches.csv", index=False)
    rejected_df.to_csv(args.reports / "vlrgg_pipeline_rejected_matches.csv", index=False)

    duplicate_dedup = 0
    if not pipeline_df.empty and "dedup_key" in pipeline_df.columns:
        duplicate_dedup = int(pipeline_df["dedup_key"].duplicated().sum())
    unknown_maps = sorted({
        str(value) for value in pipeline_df.get("map", pd.Series(dtype=str)).dropna().unique()
        if str(value) not in MAP_ORDER
    })
    unknown_agents: set[str] = set()
    for column in ["players_a_json", "players_b_json"]:
        for value in pipeline_df.get(column, pd.Series(dtype=str)):
            for player in _load_json_players(value):
                agent = str(player.get("agent", ""))
                if agent and agent not in AGENT_ROLE_MAP:
                    unknown_agents.add(agent)

    readiness = {
        "generated_at": fetched_at,
        "parser_version": PARSER_VERSION,
        "source": "vlrgg_direct_detail",
        "pipeline_matches_path": str(args.output / "vlrgg_pipeline_matches.csv"),
        "rejected_matches_path": str(args.reports / "vlrgg_pipeline_rejected_matches.csv"),
        "input_rows": {
            "vlrgg_match_maps": int(len(maps_df)),
            "vlrgg_match_players": int(len(players_df)),
            "vlrgg_event_matches": int(len(event_matches_df)),
        },
        "accepted_rows": int(len(pipeline_df)),
        "rejected_rows": int(len(rejected_df)),
        "reject_reasons": rejected_df.get("reject_reason", pd.Series(dtype=str)).value_counts().to_dict(),
        "unknown_maps": unknown_maps,
        "unknown_agents": sorted(unknown_agents),
        "duplicate_dedup_keys": duplicate_dedup,
        "required_feature_contract": "existing 57 FEATURE_COLS; no schema expansion",
        "ready_for_pipeline": bool(
            len(pipeline_df) > 0
            and not unknown_maps
            and not unknown_agents
            and duplicate_dedup == 0
        ),
    }
    (args.reports / "vlrgg_pipeline_readiness.json").write_text(
        json.dumps(readiness, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return pipeline_df, rejected_df


def _load_expanded_outputs(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return (
        _ensure_columns(_read_csv(args.output / "vlrgg_match_maps.csv"), MATCH_MAP_COLUMNS),
        _ensure_columns(_read_csv(args.output / "vlrgg_match_players.csv"), MATCH_PLAYER_COLUMNS),
        _ensure_columns(_read_csv(args.output / "vlrgg_compositions.csv"), COMPOSITION_COLUMNS),
        _ensure_columns(_read_csv(args.output / "vlrgg_standings.csv"), STANDINGS_COLUMNS),
        _ensure_columns(_read_csv(args.output / "vlrgg_team_map_stats.csv"), TEAM_MAP_COLUMNS),
        _ensure_columns(_read_csv(args.output / "vlrgg_event_matches.csv"), EVENT_MATCH_COLUMNS),
    )


def _load_candidate_source_frames(args: argparse.Namespace, fetched_at: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame | None]:
    matches_df = _read_csv(args.output / "vlrgg_matches.csv")
    api_match_stage = _combine_stage_frames(args, "api_exhaustive_match_rows", API_MATCH_COLUMNS)
    api_profile_match_stage = _combine_stage_frames(args, "api_profile_match_rows_", API_MATCH_COLUMNS)
    if matches_df.empty:
        proxy_matches, _ = load_kaggle_proxy(Path(args.kaggle_proxy_dir), fetched_at)
        cache_matches, _ = load_api_cache(args.cache_dir, args.api_base_url, fetched_at)
        frames = [df for df in [proxy_matches, cache_matches, api_match_stage, api_profile_match_stage] if not df.empty]
        matches_df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    else:
        frames = [df for df in [matches_df, api_match_stage, api_profile_match_stage] if not df.empty]
        matches_df = pd.concat(frames, ignore_index=True) if frames else matches_df
    maps_df, players_df, _, standings_df, _, event_matches_df = _load_expanded_outputs(args)
    stage_event_matches_df = _combine_stage_frames(args, "event_matches_", EVENT_MATCH_COLUMNS)
    if not stage_event_matches_df.empty:
        event_matches_df = pd.concat(
            [df for df in [event_matches_df, stage_event_matches_df] if not df.empty],
            ignore_index=True,
        )
        event_matches_df = _ensure_columns(
            event_matches_df.drop_duplicates(
                subset=[col for col in ["event_id", "match_id", "team_a", "team_b"] if col in event_matches_df.columns],
                keep="last",
            ).reset_index(drop=True),
            EVENT_MATCH_COLUMNS,
        )
    event_candidates_df = _combine_stage_frames(
        args,
        "expanded_event_candidates",
        ["event_id", "event", "url_path", *PROVENANCE_FIELDS],
    )
    api_event_candidates_df = _combine_stage_frames(args, "api_event_candidates", EVENT_CANDIDATE_COLUMNS)
    if not api_event_candidates_df.empty:
        api_event_candidates_df = api_event_candidates_df.rename(columns={"dates": "date"})
        event_candidates_df = pd.concat(
            [df for df in [event_candidates_df, api_event_candidates_df] if not df.empty],
            ignore_index=True,
        )
    return matches_df, event_matches_df, standings_df, maps_df, players_df, event_candidates_df


def write_candidate_outputs(
    candidates_df: pd.DataFrame,
    args: argparse.Namespace,
    fetched_at: str,
    state: CollectionState | None = None,
    session_network_requests: int | None = None,
) -> None:
    args.output.mkdir(parents=True, exist_ok=True)
    args.reports.mkdir(parents=True, exist_ok=True)
    candidates_df = _normalize_match_candidates(candidates_df)
    candidates_df.to_csv(args.output / "vlrgg_match_candidates.csv", index=False)
    status_counts = candidates_df.get("status", pd.Series(dtype=str)).value_counts().to_dict()
    type_counts = candidates_df.get("candidate_type", pd.Series(dtype=str)).value_counts().to_dict()
    summary = {
        "generated_at": fetched_at,
        "parser_version": PARSER_VERSION,
        "candidate_rows": int(len(candidates_df)),
        "candidate_types": type_counts,
        "candidate_statuses": status_counts,
        "pending_match_details": int(
            len(candidates_df[
                (candidates_df.get("candidate_type", pd.Series(dtype=str)).astype(str) == "match")
                & (candidates_df.get("status", pd.Series(dtype=str)).astype(str) != "detail_complete")
            ])
        ) if not candidates_df.empty else 0,
        "match_candidates_path": str(args.output / "vlrgg_match_candidates.csv"),
        "collection_state_file": str(getattr(args, "state_file", "")),
        "stage_output_dir": str(getattr(args, "stage_output_dir", "")),
        "backfill_shard": _backfill_shard_metadata(args),
        "collection_stages": _stage_summary(state) if state is not None else {},
        "network_requests": int(session_network_requests) if session_network_requests is not None else (
            int(state.data.get("cumulative_requests", 0) or 0) if state is not None else 0
        ),
        "cumulative_network_requests": int(state.data.get("cumulative_requests", 0) or 0) if state is not None else 0,
        "rate_limit": {
            "waited": bool(state and state.data.get("rate_limit_events", [])),
            "events": state.data.get("rate_limit_events", []) if state is not None else [],
        },
    }
    (args.reports / "vlrgg_collection_backfill_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def write_discovery_artifacts(args: argparse.Namespace, fetched_at: str, state: CollectionState | None) -> None:
    args.output.mkdir(parents=True, exist_ok=True)
    args.reports.mkdir(parents=True, exist_ok=True)
    event_candidates = _combine_stage_frames(args, "api_event_candidates", EVENT_CANDIDATE_COLUMNS)
    team_candidates = _team_candidates_for_profile_expansion(args)
    player_candidates = _combine_stage_frames(args, "event_player_candidates_", PLAYER_CANDIDATE_COLUMNS)
    stats_rows = _combine_stage_frames(args, "api_stats_rows", API_STATS_COLUMNS)
    ranking_rows = _combine_stage_frames(args, "api_rankings_rows", API_RANKING_COLUMNS)
    news_rows = _combine_stage_frames(args, "api_news_rows", API_NEWS_COLUMNS)
    api_match_rows = _combine_stage_frames(args, "api_exhaustive_match_rows", API_MATCH_COLUMNS)
    profile_match_rows = _combine_stage_frames(args, "api_profile_match_rows_", API_MATCH_COLUMNS)
    stage_event_matches = _combine_stage_frames(args, "event_matches_", EVENT_MATCH_COLUMNS)
    event_details = _combine_stage_frames(args, "event_detail_", EVENT_DETAIL_COLUMNS)
    event_player_stats = _combine_stage_frames(args, "event_player_stats_", EVENT_PLAYER_STATS_COLUMNS)
    event_agent_usage = _combine_stage_frames(args, "event_agent_usage_", EVENT_AGENT_USAGE_COLUMNS)
    team_profiles = _dedupe_frame(_combine_stage_frames(args, "team_profile_", TEAM_PROFILE_COLUMNS), ["team_id"])
    team_roster = _dedupe_frame(
        _combine_stage_frames(args, "team_roster_", TEAM_ROSTER_COLUMNS),
        ["team_id", "player_id", "member_type", "role"],
    )
    team_rating_history = _dedupe_frame(
        _combine_stage_frames(args, "team_rating_history_", TEAM_RATING_HISTORY_COLUMNS),
        ["team_id", "core_id", "sequence", "date", "opponent", "event"],
    )
    team_matches = _dedupe_frame(
        _combine_stage_frames(args, "team_matches_", TEAM_MATCH_COLUMNS),
        ["team_id", "match_id"],
    )
    team_map_stats = _dedupe_frame(
        _combine_stage_frames(args, "team_map_stats_", TEAM_MAP_COLUMNS),
        ["team_id", "map"],
    )
    player_profiles = _combine_stage_frames(args, "player_profile_", PLAYER_PROFILE_COLUMNS)
    team_transactions = _combine_stage_frames(args, "team_transactions_", TEAM_TRANSACTION_COLUMNS)
    if not team_candidates.empty and not team_profiles.empty:
        complete_ids = set(team_profiles.get("team_id", pd.Series(dtype=str)).map(_clean_id))
        mask = team_candidates.get("team_id", pd.Series(dtype=str)).map(_clean_id).isin(complete_ids)
        team_candidates.loc[mask, "status"] = "profile_complete"
        team_candidates.loc[mask, "status_reason"] = "team profile stage output exists"
    if not player_candidates.empty and not player_profiles.empty:
        complete_ids = set(player_profiles.get("player_id", pd.Series(dtype=str)).map(_clean_id))
        mask = player_candidates.get("player_id", pd.Series(dtype=str)).map(_clean_id).isin(complete_ids)
        player_candidates.loc[mask, "status"] = "profile_complete"
        player_candidates.loc[mask, "status_reason"] = "player profile stage output exists"
    artifact_specs = [
        ("vlrgg_event_candidates", event_candidates, EVENT_CANDIDATE_COLUMNS),
        ("vlrgg_team_candidates", team_candidates, TEAM_CANDIDATE_COLUMNS),
        ("vlrgg_player_candidates", player_candidates, PLAYER_CANDIDATE_COLUMNS),
        ("vlrgg_event_details", event_details, EVENT_DETAIL_COLUMNS),
        ("vlrgg_event_player_stats", event_player_stats, EVENT_PLAYER_STATS_COLUMNS),
        ("vlrgg_event_agent_usage", event_agent_usage, EVENT_AGENT_USAGE_COLUMNS),
        ("vlrgg_team_profiles", team_profiles, TEAM_PROFILE_COLUMNS),
        ("vlrgg_team_roster", team_roster, TEAM_ROSTER_COLUMNS),
        ("vlrgg_team_rating_history", team_rating_history, TEAM_RATING_HISTORY_COLUMNS),
        ("vlrgg_team_matches", team_matches, TEAM_MATCH_COLUMNS),
        ("vlrgg_team_map_stats", team_map_stats, TEAM_MAP_COLUMNS),
        ("vlrgg_player_profiles", player_profiles, PLAYER_PROFILE_COLUMNS),
        ("vlrgg_team_transactions", team_transactions, TEAM_TRANSACTION_COLUMNS),
        ("vlrgg_api_stats", stats_rows, API_STATS_COLUMNS),
        ("vlrgg_rankings", ranking_rows, API_RANKING_COLUMNS),
        ("vlrgg_news", news_rows, API_NEWS_COLUMNS),
    ]
    if not stage_event_matches.empty or not (args.output / "vlrgg_event_matches.csv").exists():
        artifact_specs.append(("vlrgg_event_matches", stage_event_matches, EVENT_MATCH_COLUMNS))
    for name, df, columns in artifact_specs:
        out = _ensure_columns(df, columns)
        if set(PROVENANCE_FIELDS).issubset(out.columns):
            validate_provenance(out, name)
        out.to_csv(args.output / f"{name}.csv", index=False)

    coverage_path = args.reports / "vlrgg_api_coverage.json"
    coverage = _read_json_file(coverage_path)
    coverage.setdefault("generated_at", fetched_at)
    coverage.setdefault("parser_version", PARSER_VERSION)
    coverage.setdefault("api_base_url", args.api_base_url)
    coverage.setdefault("api_version", DEFAULT_API_VERSION)
    coverage["artifact_paths"] = {
        "event_candidates": str(args.output / "vlrgg_event_candidates.csv"),
        "team_candidates": str(args.output / "vlrgg_team_candidates.csv"),
        "player_candidates": str(args.output / "vlrgg_player_candidates.csv"),
        "event_details": str(args.output / "vlrgg_event_details.csv"),
        "event_player_stats": str(args.output / "vlrgg_event_player_stats.csv"),
        "event_agent_usage": str(args.output / "vlrgg_event_agent_usage.csv"),
        "team_profiles": str(args.output / "vlrgg_team_profiles.csv"),
        "team_roster": str(args.output / "vlrgg_team_roster.csv"),
        "team_rating_history": str(args.output / "vlrgg_team_rating_history.csv"),
        "team_matches": str(args.output / "vlrgg_team_matches.csv"),
        "team_map_stats": str(args.output / "vlrgg_team_map_stats.csv"),
        "player_profiles": str(args.output / "vlrgg_player_profiles.csv"),
        "team_transactions": str(args.output / "vlrgg_team_transactions.csv"),
        "api_stats": str(args.output / "vlrgg_api_stats.csv"),
        "rankings": str(args.output / "vlrgg_rankings.csv"),
        "news": str(args.output / "vlrgg_news.csv"),
        "api_match_rows_stage": str(_stage_output_path(args, "api_exhaustive_match_rows")),
    }
    coverage["rows"] = {
        **dict(coverage.get("rows", {}) if isinstance(coverage.get("rows"), dict) else {}),
        "event_candidates": int(len(event_candidates)),
        "team_candidates": int(len(team_candidates)),
        "player_candidates": int(len(player_candidates)),
        "event_details": int(len(event_details)),
        "event_player_stats": int(len(event_player_stats)),
        "event_agent_usage": int(len(event_agent_usage)),
        "team_profiles": int(len(team_profiles)),
        "team_roster": int(len(team_roster)),
        "team_rating_history": int(len(team_rating_history)),
        "team_matches": int(len(team_matches)),
        "team_map_stats": int(len(team_map_stats)),
        "player_profiles": int(len(player_profiles)),
        "team_transactions": int(len(team_transactions)),
        "stats": int(len(stats_rows)),
        "rankings": int(len(ranking_rows)),
        "news": int(len(news_rows)),
        "api_match_rows": int(len(api_match_rows)),
        "api_profile_match_rows": int(len(profile_match_rows)),
    }
    coverage["collection_stages"] = _stage_summary(state) if state is not None else {}
    coverage_path.write_text(json.dumps(coverage, indent=2, ensure_ascii=False), encoding="utf-8")

    stages = _stage_summary(state) if state is not None else {}
    team_summary = {
        "generated_at": fetched_at,
        "parser_version": PARSER_VERSION,
        "mode": "team_profile_discovery_plan",
        "artifact_paths": {
            "team_profiles": str(args.output / "vlrgg_team_profiles.csv"),
            "team_roster": str(args.output / "vlrgg_team_roster.csv"),
            "team_rating_history": str(args.output / "vlrgg_team_rating_history.csv"),
            "team_matches": str(args.output / "vlrgg_team_matches.csv"),
            "team_map_stats": str(args.output / "vlrgg_team_map_stats.csv"),
            "team_transactions": str(args.output / "vlrgg_team_transactions.csv"),
            "rankings": str(args.output / "vlrgg_rankings.csv"),
        },
        "rows": {
            "team_profiles": int(len(team_profiles)),
            "team_roster": int(len(team_roster)),
            "team_rating_history": int(len(team_rating_history)),
            "team_matches": int(len(team_matches)),
            "team_map_stats": int(len(team_map_stats)),
            "team_transactions": int(len(team_transactions)),
            "rankings": int(len(ranking_rows)),
        },
        "network_requests": int(state.data.get("cumulative_requests", 0) or 0) if state is not None else 0,
        "blocked_paths": ROBOTS_BLOCKED_PATHS,
        "direct_html_allowed_paths": DIRECT_HTML_ALLOWED_PATHS,
        "degraded_stages": [
            name for name, details in stages.items()
            if isinstance(details, dict) and details.get("status") == "degraded"
        ],
        "collection_stages": stages,
    }
    (args.reports / "vlrgg_team_profile_collection_summary.json").write_text(
        json.dumps(team_summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _build_and_write_candidates(
    args: argparse.Namespace,
    fetched_at: str,
    state: CollectionState | None = None,
    session_network_requests: int | None = None,
) -> pd.DataFrame:
    matches_df, event_matches_df, standings_df, maps_df, players_df, event_candidates_df = _load_candidate_source_frames(args, fetched_at)
    candidates_df = build_match_candidates(
        matches_df=matches_df,
        event_matches_df=event_matches_df,
        standings_df=standings_df,
        maps_df=maps_df,
        players_df=players_df,
        event_candidates_df=event_candidates_df,
        discovered_at=fetched_at,
    )
    write_candidate_outputs(candidates_df, args, fetched_at, state, session_network_requests)
    return candidates_df


def _load_and_write_backfill_candidates(
    args: argparse.Namespace,
    fetched_at: str,
    state: CollectionState | None = None,
    session_network_requests: int | None = None,
) -> pd.DataFrame:
    candidates_file = str(getattr(args, "backfill_candidates_file", "") or "").strip()
    if candidates_file:
        candidates_df = _ensure_columns(_read_csv(Path(candidates_file)), MATCH_CANDIDATE_COLUMNS)
        candidates_df = _with_detail_status_from_stage_outputs(candidates_df, args)
    else:
        matches_df, event_matches_df, standings_df, maps_df, players_df, event_candidates_df = _load_candidate_source_frames(args, fetched_at)
        candidates_df = build_match_candidates(
            matches_df=matches_df,
            event_matches_df=event_matches_df,
            standings_df=standings_df,
            maps_df=maps_df,
            players_df=players_df,
            event_candidates_df=event_candidates_df,
            discovered_at=fetched_at,
        )
    shard_count, shard_index = _backfill_shard_settings(args)
    candidates_df = _filter_candidates_for_backfill_shard(candidates_df, shard_count, shard_index)
    write_candidate_outputs(candidates_df, args, fetched_at, state, session_network_requests)
    return candidates_df


def run_discovery_plan(args: argparse.Namespace) -> None:
    fetched_at = _utc_now()
    args.cache_dir = Path(args.cache_dir)
    args.output = Path(args.output)
    args.reports = Path(args.reports)
    args.state_file = Path(args.state_file)
    args.stage_output_dir = Path(args.stage_output_dir)
    args.api_base_url = args.api_base_url.rstrip("/")
    args.allow_direct_html = True

    state = CollectionState(args.state_file, reset=args.restart)
    requests_before = int(state.data.get("cumulative_requests", 0) or 0)
    if int(args.max_requests_per_session) > 0:
        robots_args = argparse.Namespace(**vars(args))
        robots_result = _run_stage_with_resume(
            args=robots_args,
            state=state,
            name="robots_txt",
            cursor={"url": ROBOTS_URL, "mode": "discovery_plan"},
            fn=fetch_robots_policy,
        )
        robots_policy = robots_result if robots_result.get("status") == "completed" else {}
        if "allowed_path_checks" not in robots_policy and "details" in robots_result:
            robots_policy = dict(robots_result.get("details") or {})
        args.robots_policy = robots_policy
        team_direct_paths = ["/team/", "/team/stats/", "/team/transactions/"]
        allowed_checks = robots_policy.get("allowed_path_checks", {}) if isinstance(robots_policy, dict) else {}
        blocked_checks = robots_policy.get("blocked_path_checks", {}) if isinstance(robots_policy, dict) else {}
        direct_team_html_available = bool(robots_policy) and all(
            allowed_checks.get(path) is True for path in team_direct_paths
        ) and blocked_checks.get("/search/auto") is True
        if not direct_team_html_available:
            state.mark_stage(
                "direct_team_html_robots_policy",
                "degraded",
                cursor={"robots_url": ROBOTS_URL, "paths": team_direct_paths},
                rows=0,
                network_requests=0,
                failure_reason="robots.txt did not confirm direct team HTML path allowlist",
            )
        else:
            state.mark_stage(
                "direct_team_html_robots_policy",
                "completed",
                cursor={"robots_url": ROBOTS_URL, "paths": team_direct_paths},
                rows=1,
                network_requests=0,
                failure_reason="",
                details={"blocked_path_checks": blocked_checks},
            )

        def _api_health_discovery() -> dict[str, Any]:
            available, reason, requests_made = api_base_available(args.api_base_url)
            if not available:
                raise CollectionStageError(f"local vlrggapi unavailable: {reason}", requests_made=requests_made)
            return {"rows": 1, "network_requests": requests_made, "api_base_status": reason}

        api_result = _run_stage_with_resume(
            args=args,
            state=state,
            name="api_base_available",
            cursor={"api_base_url": args.api_base_url, "mode": "discovery_plan"},
            fn=_api_health_discovery,
        )
        args.api_available = api_result.get("status") == "completed"
        if args.api_available and int(args.max_requests_per_session) > 1:
            remaining_budget = max(
                0,
                int(args.max_requests_per_session)
                - (int(state.data.get("cumulative_requests", 0) or 0) - requests_before),
            )
            _run_stage_with_resume(
                args=args,
                state=state,
                name="api_exhaustive_discovery",
                cursor={"path": "/v2/*", "mode": "discovery_plan", "request_budget": remaining_budget},
                fn=lambda: fetch_api_exhaustive_to_stage(args, fetched_at, remaining_budget),
            )
            _run_stage_with_resume(
                args=args,
                state=state,
                name="expanded_event_candidates",
                cursor={"path": "/v2/events", "q": "completed", "limit": int(args.event_limit)},
                fn=lambda: fetch_event_candidates_to_stage(args, int(args.event_limit), fetched_at),
            )
            event_candidates_df = _combine_stage_frames(args, "api_event_candidates", EVENT_CANDIDATE_COLUMNS)
            if event_candidates_df.empty:
                event_candidates_df = _combine_stage_frames(
                    args,
                    "expanded_event_candidates",
                    ["event_id", "event", "url_path", *PROVENANCE_FIELDS],
                )
            remaining_budget = max(
                0,
                int(args.max_requests_per_session)
                - (int(state.data.get("cumulative_requests", 0) or 0) - requests_before),
            )
            if remaining_budget > 0:
                _run_stage_with_resume(
                    args=args,
                    state=state,
                    name="api_event_detail_expansion",
                    cursor={
                        "path": "/v2/event/{event_id}",
                        "event_limit": int(args.event_limit),
                        "request_budget": remaining_budget,
                    },
                    fn=lambda: expand_api_event_details_to_stage(args, event_candidates_df, fetched_at, remaining_budget),
                )
            remaining_budget = max(
                0,
                int(args.max_requests_per_session)
                - (int(state.data.get("cumulative_requests", 0) or 0) - requests_before),
            )
            if remaining_budget > 0:
                _run_stage_with_resume(
                    args=args,
                    state=state,
                    name="api_event_match_expansion",
                    cursor={
                        "path": "/v2/events/matches",
                        "event_limit": int(args.event_limit),
                        "request_budget": remaining_budget,
                    },
                    fn=lambda: expand_api_event_matches_to_stage(args, event_candidates_df, fetched_at, remaining_budget),
                )
            remaining_budget = max(
                0,
                int(args.max_requests_per_session)
                - (int(state.data.get("cumulative_requests", 0) or 0) - requests_before),
            )
            if remaining_budget > 0:
                _run_stage_with_resume(
                    args=args,
                    state=state,
                    name="api_profile_expansion",
                    cursor={
                        "paths": ["/v2/team", "/v2/team/matches", "/v2/team/transactions", "/v2/player", "/v2/player/matches"],
                        "team_limit": int(args.team_limit),
                        "player_limit": int(getattr(args, "player_limit", DEFAULT_PLAYER_LIMIT)),
                        "request_budget": remaining_budget,
                    },
                    fn=lambda: expand_api_profiles_to_stage(args, fetched_at, remaining_budget),
                )
            remaining_budget = max(
                0,
                int(args.max_requests_per_session)
                - (int(state.data.get("cumulative_requests", 0) or 0) - requests_before),
            )
            if direct_team_html_available and remaining_budget > 0:
                _run_stage_with_resume(
                    args=args,
                    state=state,
                    name="direct_team_profile_expansion",
                    cursor={
                        "paths": ["/team/{team_id}"],
                        "team_limit": int(args.team_limit),
                        "request_budget": remaining_budget,
                    },
                    fn=lambda: expand_direct_team_profiles_to_stage(args, fetched_at, remaining_budget),
                )
            remaining_budget = max(
                0,
                int(args.max_requests_per_session)
                - (int(state.data.get("cumulative_requests", 0) or 0) - requests_before),
            )
            if direct_team_html_available and remaining_budget > 0:
                _run_stage_with_resume(
                    args=args,
                    state=state,
                    name="direct_team_map_stats_expansion",
                    cursor={
                        "paths": ["/team/stats/{team_id}"],
                        "team_limit": int(args.team_limit),
                        "request_budget": remaining_budget,
                    },
                    fn=lambda: expand_direct_team_map_stats_to_stage(args, fetched_at, remaining_budget),
                )
    else:
        args.api_available = False
        state.mark_stage(
            "discovery_network_skipped",
            "completed",
            cursor={"max_requests_per_session": int(args.max_requests_per_session)},
            rows=0,
            network_requests=0,
            skipped=True,
        )

    session_requests = int(state.data.get("cumulative_requests", 0) or 0) - requests_before
    write_discovery_artifacts(args, fetched_at, state)
    candidates_df = _build_and_write_candidates(args, fetched_at, state, session_requests)
    maps_df, players_df, _, _, _, event_matches_df = _load_expanded_outputs(args)
    write_pipeline_readiness_outputs(maps_df, players_df, event_matches_df, args, fetched_at)
    print(
        "VLR discovery plan complete: "
        f"candidates={len(candidates_df)} "
        f"network_requests={session_requests} "
        f"state={args.state_file}"
    )


def _json_text(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False, sort_keys=True, default=str)


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _first_clean(*values: Any) -> str:
    for value in values:
        text = _clean_text(value)
        if text:
            return text
    return ""


def _first_present(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in row:
            value = row.get(key)
            if _clean_text(value):
                return value
    return None


def _json_payload(value: Any, fallback: Any) -> str:
    if value is None:
        return _json_text(fallback)
    if isinstance(value, float) and pd.isna(value):
        return _json_text(fallback)
    if isinstance(value, str) and not value.strip():
        return _json_text(fallback)
    return _json_text(value)


SOCIAL_HANDLE_KEYS = (
    "twitter", "x", "twitch", "youtube", "instagram", "facebook",
    "discord", "weibo", "bilibili",
)


def _social_platform_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _clean_text(value).lower()).strip("_")


def _extract_social_handles(profile: dict[str, Any]) -> dict[str, str]:
    info = _as_dict(profile.get("info"))
    handles: dict[str, str] = {}

    def add(platform: Any, value: Any) -> None:
        key = _social_platform_key(platform)
        text = _clean_text(value)
        if key and text:
            handles[key] = text

    for source in [profile, info]:
        for key in SOCIAL_HANDLE_KEYS:
            add(key, source.get(key))

    containers = [
        profile.get("socials"),
        profile.get("social_handles"),
        profile.get("social_links"),
        profile.get("links"),
        info.get("socials"),
        info.get("social_handles"),
        info.get("social_links"),
        info.get("links"),
    ]
    for container in containers:
        if isinstance(container, dict):
            for platform, value in container.items():
                if isinstance(value, dict):
                    add(platform, _first_present(value, "handle", "url", "href", "value", "text"))
                else:
                    add(platform, value)
        elif isinstance(container, list):
            for item in container:
                if not isinstance(item, dict):
                    continue
                platform = _first_present(item, "platform", "site", "type", "name", "label")
                value = _first_present(item, "handle", "url", "href", "value", "text")
                add(platform, value)
    return handles


def _coerce_agent_stat_rows(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [row for row in value if isinstance(row, dict)]
    if isinstance(value, dict):
        for key in ["agent_stats", "agents", "rows", "segments", "data"]:
            rows = _coerce_agent_stat_rows(value.get(key))
            if rows:
                return rows
        if any(key in value for key in ["agent", "agent_name", "name"]):
            return [value]
        rows: list[dict[str, Any]] = []
        for agent, stats in value.items():
            if isinstance(stats, dict):
                row = dict(stats)
                row.setdefault("agent", agent)
                rows.append(row)
        return rows
    return []


def _profile_agent_stats(profile: dict[str, Any]) -> list[dict[str, Any]]:
    stats = _as_dict(profile.get("stats"))
    candidates = [
        profile.get("agent_stats"),
        profile.get("agent_usage"),
        profile.get("agents"),
        stats.get("agent_stats"),
        stats.get("agent_usage"),
        stats.get("agents"),
    ]
    for candidate in candidates:
        rows = _coerce_agent_stat_rows(candidate)
        if rows:
            return rows
    return []


def _score_from_match_row(row: dict[str, Any]) -> tuple[int | None, int | None]:
    score_a = _int_or_none(_first_present(row, "score_a", "score1", "team_a_score", "team1_score"))
    score_b = _int_or_none(_first_present(row, "score_b", "score2", "team_b_score", "team2_score"))
    if score_a is not None or score_b is not None:
        return score_a, score_b
    score_text = _clean_text(_first_present(row, "score", "result", "scoreline"))
    match = re.match(r"^\s*(\d+)\s*[-:]\s*(\d+)", score_text)
    if match:
        return int(match.group(1)), int(match.group(2))
    teams = row.get("teams")
    if isinstance(teams, list) and len(teams) >= 2:
        left = teams[0] if isinstance(teams[0], dict) else {}
        right = teams[1] if isinstance(teams[1], dict) else {}
        return _int_or_none(left.get("score")), _int_or_none(right.get("score"))
    return None, None


def _teams_from_match_row(row: dict[str, Any]) -> tuple[str, str]:
    teams = row.get("teams")
    if isinstance(teams, dict):
        team1 = teams.get("team1")
        team2 = teams.get("team2")
        if isinstance(team1, dict):
            team_a = _clean_text(team1.get("name", team1.get("team")))
        else:
            team_a = _clean_text(team1)
        if isinstance(team2, dict):
            team_b = _clean_text(team2.get("name", team2.get("team")))
        else:
            team_b = _clean_text(team2)
        return normalize_team(team_a), normalize_team(team_b)
    if isinstance(teams, list):
        left = teams[0] if len(teams) > 0 and isinstance(teams[0], dict) else {}
        right = teams[1] if len(teams) > 1 and isinstance(teams[1], dict) else {}
        return (
            normalize_team(_clean_text(left.get("name", left.get("team")))),
            normalize_team(_clean_text(right.get("name", right.get("team")))),
        )
    return (
        normalize_team(_first_clean(row.get("team_a"), row.get("team1"), row.get("team"))),
        normalize_team(_first_clean(row.get("team_b"), row.get("team2"), row.get("opponent"))),
    )


def _team_name_from_slot(teams: list[Any], slot: str) -> str:
    index = 0 if slot == "team1" else 1
    if len(teams) > index and isinstance(teams[index], dict):
        return normalize_team(_clean_text(teams[index].get("name", teams[index].get("team"))))
    return ""


def _score_part(score: dict[str, Any], slot: str, *keys: str) -> int | None:
    row = _as_dict(score.get(slot))
    for key in keys:
        parsed = _int_or_none(row.get(key))
        if parsed is not None:
            return parsed
    return None


def _api_detail_players(raw_players: Any, slot: str) -> list[dict[str, Any]]:
    players = _as_dict(raw_players).get(slot, [])
    out: list[dict[str, Any]] = []
    for row in _as_list(players):
        if not isinstance(row, dict):
            continue
        out.append({
            "player": _clean_text(row.get("player", row.get("name", row.get("alias")))),
            "agent": _clean_text(row.get("agent")),
            "rating": _num(row.get("rating")),
            "acs": _num(row.get("acs")),
            "kills": _num(row.get("kills", row.get("k"))),
            "deaths": _num(row.get("deaths", row.get("d"))),
            "assists": _num(row.get("assists", row.get("a"))),
            "kast": _pct_to_float(row.get("kast")),
            "adr": _num(row.get("adr")),
            "hs_pct": _pct_to_float(row.get("hs_pct", row.get("hs"))),
            "fb": _num(row.get("fb", row.get("fk"))),
            "fd": _num(row.get("fd")),
            "atk_kills": _num(row.get("atk_kills")),
            "def_kills": _num(row.get("def_kills")),
            "atk_deaths": _num(row.get("atk_deaths")),
            "def_deaths": _num(row.get("def_deaths")),
        })
    return out


def _api_match_detail_to_direct_details(detail: dict[str, Any]) -> list[dict[str, Any]]:
    match_id = _clean_id(detail.get("match_id", detail.get("id")))
    teams = _as_list(detail.get("teams"))
    team_a = _team_name_from_slot(teams, "team1")
    team_b = _team_name_from_slot(teams, "team2")
    out: list[dict[str, Any]] = []
    for idx, game in enumerate(_as_list(detail.get("maps")), start=1):
        if not isinstance(game, dict):
            continue
        score = _as_dict(game.get("score"))
        players = _as_dict(game.get("players"))
        players_a = _api_detail_players(players, "team1")
        players_b = _api_detail_players(players, "team2")
        agents_a = [row.get("agent") for row in players_a if row.get("agent")]
        agents_b = [row.get("agent") for row in players_b if row.get("agent")]
        game_id = _clean_id(game.get("game_id", game.get("id"))) or f"{match_id}-{idx}"
        out.append({
            "match_id": match_id,
            "game_id": game_id,
            "map": _clean_text(game.get("map_name", game.get("map"))),
            "team_a": team_a,
            "team_b": team_b,
            "first_atk": team_a,
            "atk_rounds_a": _score_part(score, "team1", "t", "atk", "attack"),
            "def_rounds_a": _score_part(score, "team1", "ct", "def", "defense"),
            "ot_rounds_a": _score_part(score, "team1", "ot", "overtime"),
            "atk_rounds_b": _score_part(score, "team2", "t", "atk", "attack"),
            "def_rounds_b": _score_part(score, "team2", "ct", "def", "defense"),
            "ot_rounds_b": _score_part(score, "team2", "ot", "overtime"),
            "agents_a": agents_a,
            "agents_b": agents_b,
            "players_a": players_a,
            "players_b": players_b,
        })
    return out


def _api_match_detail_raw_frame(
    detail: dict[str, Any],
    *,
    fetched_at: str,
    source_url: str,
    cache_hit: bool,
) -> pd.DataFrame:
    event = _as_dict(detail.get("event"))
    row = _with_provenance({
        "match_id": _clean_id(detail.get("match_id", detail.get("id"))),
        "event": _clean_text(event.get("name", detail.get("event"))),
        "date": _clean_text(detail.get("date")),
        "status": _clean_text(detail.get("status")),
        "teams_json": _json_text(detail.get("teams", [])),
        "maps_json": _json_text(detail.get("maps", [])),
        "raw_json": _json_text(detail),
    }, source="vlrgg_api_detail", source_url=source_url,
        method="api_match_detail_cache" if cache_hit else "api_match_detail",
        fetched_at=fetched_at, cache_hit=cache_hit)
    return _ensure_columns(pd.DataFrame([row]), MATCH_DETAIL_RAW_COLUMNS)


def _api_match_rounds_frame(
    detail: dict[str, Any],
    *,
    fetched_at: str,
    source_url: str,
    cache_hit: bool,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    match_id = _clean_id(detail.get("match_id", detail.get("id")))
    teams = _as_list(detail.get("teams"))
    for idx, game in enumerate(_as_list(detail.get("maps")), start=1):
        if not isinstance(game, dict):
            continue
        game_id = _clean_id(game.get("game_id", game.get("id"))) or f"{match_id}-{idx}"
        map_name = normalize_map(_clean_text(game.get("map_name", game.get("map")))) or _clean_text(game.get("map_name", game.get("map")))
        for round_row in _as_list(game.get("rounds")):
            if not isinstance(round_row, dict):
                continue
            winner = _clean_text(round_row.get("winner"))
            team = _team_name_from_slot(teams, winner) if winner in {"team1", "team2"} else winner
            rows.append(_with_provenance({
                "match_id": match_id,
                "game_id": game_id,
                "map": map_name,
                "round_num": _int_or_none(round_row.get("round_num", round_row.get("round"))),
                "winner": winner,
                "side": _clean_text(round_row.get("side")),
                "team": normalize_team(team),
                "raw_json": _json_text(round_row),
            }, source="vlrgg_api_detail", source_url=source_url,
                method="api_match_detail_cache" if cache_hit else "api_match_detail",
                fetched_at=fetched_at, cache_hit=cache_hit))
    return _ensure_columns(pd.DataFrame(rows), ROUND_COLUMNS)


def _api_match_economy_frame(
    detail: dict[str, Any],
    *,
    fetched_at: str,
    source_url: str,
    cache_hit: bool,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    match_id = _clean_id(detail.get("match_id", detail.get("id")))
    for row in _as_list(detail.get("economy")):
        if not isinstance(row, dict):
            continue
        rows.append(_with_provenance({
            "match_id": match_id,
            "team": normalize_team(_clean_text(row.get("Team", row.get("team")))),
            "pistol": _pct_to_float(row.get("Pistol", row.get("pistol"))),
            "eco": _pct_to_float(row.get("Eco", row.get("eco"))),
            "semi_eco": _pct_to_float(row.get("Semi Eco", row.get("semi_eco"))),
            "semi_buy": _pct_to_float(row.get("Semi Buy", row.get("semi_buy"))),
            "full_buy": _pct_to_float(row.get("Full", row.get("full_buy", row.get("Full Buy")))),
            "raw_json": _json_text(row),
        }, source="vlrgg_api_detail", source_url=source_url,
            method="api_match_detail_cache" if cache_hit else "api_match_detail",
            fetched_at=fetched_at, cache_hit=cache_hit))
    return _ensure_columns(pd.DataFrame(rows), ECONOMY_COLUMNS)


def _api_match_kill_matrix_frame(
    detail: dict[str, Any],
    *,
    fetched_at: str,
    source_url: str,
    cache_hit: bool,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    match_id = _clean_id(detail.get("match_id", detail.get("id")))
    performance = _as_dict(detail.get("performance"))
    advanced_by_player: dict[str, dict[str, Any]] = {}
    for row in _as_list(performance.get("advanced_stats")):
        if isinstance(row, dict):
            player = _clean_text(row.get("player", row.get("name")))
            if player:
                advanced_by_player[player] = row
    for row in _as_list(performance.get("kill_matrix")):
        if not isinstance(row, dict):
            continue
        player = _clean_text(row.get("player", row.get("name")))
        rows.append(_with_provenance({
            "match_id": match_id,
            "player": normalize_player(player),
            "kills_vs_json": _json_text(row.get("kills_vs", row)),
            "advanced_stats_json": _json_text(advanced_by_player.get(player, {})),
        }, source="vlrgg_api_detail", source_url=source_url,
            method="api_match_detail_cache" if cache_hit else "api_match_detail",
            fetched_at=fetched_at, cache_hit=cache_hit))
    return _ensure_columns(pd.DataFrame(rows), KILL_MATRIX_COLUMNS)


def _api_match_map_vetoes_frame(
    detail: dict[str, Any],
    *,
    fetched_at: str,
    source_url: str,
    cache_hit: bool,
) -> pd.DataFrame:
    raw = _clean_text(detail.get("map_vetos", detail.get("map_vetoes")))
    match_id = _clean_id(detail.get("match_id", detail.get("id")))
    rows: list[dict[str, Any]] = []
    if raw:
        for idx, part in enumerate([item.strip() for item in raw.split(";") if item.strip()], start=1):
            match = re.match(r"(?P<team>.+?)\s+(?P<action>ban|pick|remove|decider|remains)\s+(?P<map>.+)$", part, re.I)
            rows.append(_with_provenance({
                "match_id": match_id,
                "sequence": idx,
                "team": normalize_team(match.group("team")) if match else "",
                "action": match.group("action").lower() if match else "",
                "map": normalize_map(match.group("map")) if match else "",
                "raw_text": part,
            }, source="vlrgg_api_detail", source_url=source_url,
                method="api_match_detail_cache" if cache_hit else "api_match_detail",
                fetched_at=fetched_at, cache_hit=cache_hit))
    return _ensure_columns(pd.DataFrame(rows), MAP_VETO_COLUMNS)


def build_api_match_detail_artifacts(
    detail: dict[str, Any],
    *,
    fetched_at: str,
    source_url: str,
    cache_hit: bool,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    direct_details = _api_match_detail_to_direct_details(detail)
    maps, players, comps = build_match_detail_frames(
        direct_details,
        fetched_at,
        source="vlrgg_api_detail",
        method="api_match_detail_cache" if cache_hit else "api_match_detail",
        cache_hit=cache_hit,
        source_url_func=lambda match_id: source_url or _safe_source_url_from_match(match_id),
    )
    return (
        maps,
        players,
        comps,
        _api_match_detail_raw_frame(detail, fetched_at=fetched_at, source_url=source_url, cache_hit=cache_hit),
        _api_match_rounds_frame(detail, fetched_at=fetched_at, source_url=source_url, cache_hit=cache_hit),
        _api_match_economy_frame(detail, fetched_at=fetched_at, source_url=source_url, cache_hit=cache_hit),
        _api_match_kill_matrix_frame(detail, fetched_at=fetched_at, source_url=source_url, cache_hit=cache_hit),
        _api_match_map_vetoes_frame(detail, fetched_at=fetched_at, source_url=source_url, cache_hit=cache_hit),
    )


def fetch_api_match_detail_to_stage(args: argparse.Namespace, match_id: str, fetched_at: str) -> dict[str, Any]:
    client = VLRGGClient(
        rate_limit_per_second=args.rate_limit,
        cache_dir=str(args.cache_dir),
        base_url=args.api_base_url,
        cache_only=not bool(getattr(args, "api_available", False)),
        api_version=DEFAULT_API_VERSION,
    )
    detail = client.fetch_match_details(match_id)
    if not detail:
        raise CollectionStageError(f"/match/details returned no data for match_id={match_id}", requests_made=client.request_count)
    source_url = _source_url_for_api(args.api_base_url, "/match/details", {"match_id": match_id})
    maps, players, comps, raw, rounds, economy, kill_matrix, map_vetoes = build_api_match_detail_artifacts(
        detail,
        fetched_at=fetched_at,
        source_url=source_url,
        cache_hit=client.last_cache_hit,
    )
    if (maps.empty or players.empty) and _is_no_played_map_detail(detail):
        _write_stage_frame(args, f"match_detail_maps_{match_id}", maps)
        _write_stage_frame(args, f"match_detail_players_{match_id}", players)
        _write_stage_frame(args, f"match_detail_compositions_{match_id}", comps)
        _write_stage_frame(args, f"match_details_raw_{match_id}", raw)
        _write_stage_frame(args, f"match_rounds_{match_id}", rounds)
        _write_stage_frame(args, f"match_economy_{match_id}", economy)
        _write_stage_frame(args, f"match_kill_matrix_{match_id}", kill_matrix)
        _write_stage_frame(args, f"match_map_vetoes_{match_id}", map_vetoes)
        return {
            "rows": int(len(raw) + len(rounds) + len(economy) + len(kill_matrix) + len(map_vetoes)),
            "network_requests": int(client.request_count),
            "map_rows": 0,
            "player_rows": 0,
            "composition_rows": int(len(comps)),
            "raw_rows": int(len(raw)),
            "round_rows": int(len(rounds)),
            "economy_rows": int(len(economy)),
            "kill_matrix_rows": int(len(kill_matrix)),
            "map_veto_rows": int(len(map_vetoes)),
            "used_api_detail": True,
            "skipped_no_played_maps": True,
            "no_played_maps_reason": _clean_text(detail.get("status")),
        }
    _require_match_detail_rows(
        match_id=match_id,
        maps=maps,
        players=players,
        source_label="/match/details",
        requests_made=client.request_count,
    )
    _write_stage_frame(args, f"match_detail_maps_{match_id}", maps)
    _write_stage_frame(args, f"match_detail_players_{match_id}", players)
    _write_stage_frame(args, f"match_detail_compositions_{match_id}", comps)
    _write_stage_frame(args, f"match_details_raw_{match_id}", raw)
    _write_stage_frame(args, f"match_rounds_{match_id}", rounds)
    _write_stage_frame(args, f"match_economy_{match_id}", economy)
    _write_stage_frame(args, f"match_kill_matrix_{match_id}", kill_matrix)
    _write_stage_frame(args, f"match_map_vetoes_{match_id}", map_vetoes)
    return {
        "rows": int(len(maps) + len(players) + len(comps) + len(raw) + len(rounds) + len(economy) + len(kill_matrix) + len(map_vetoes)),
        "network_requests": int(client.request_count),
        "map_rows": int(len(maps)),
        "player_rows": int(len(players)),
        "composition_rows": int(len(comps)),
        "raw_rows": int(len(raw)),
        "round_rows": int(len(rounds)),
        "economy_rows": int(len(economy)),
        "kill_matrix_rows": int(len(kill_matrix)),
        "map_veto_rows": int(len(map_vetoes)),
        "used_api_detail": True,
    }


def run_backfill_plan(args: argparse.Namespace) -> None:
    fetched_at = _utc_now()
    shard_count, shard_index = _backfill_shard_settings(args)
    apply_backfill_shard_isolation(args)
    args.cache_dir = Path(args.cache_dir)
    args.output = Path(args.output)
    args.reports = Path(args.reports)
    args.state_file = Path(args.state_file)
    args.stage_output_dir = Path(args.stage_output_dir)
    args.api_base_url = args.api_base_url.rstrip("/")
    direct_html_fallback_disabled = bool(getattr(args, "disable_direct_html_fallback", False))
    args.allow_direct_html = not direct_html_fallback_disabled

    state = CollectionState(args.state_file, reset=args.restart)
    requests_before = int(state.data.get("cumulative_requests", 0) or 0)
    if int(args.max_requests_per_session) <= 0:
        state.mark_stage(
            "backfill_network_skipped",
            "completed",
            cursor={"max_requests_per_session": int(args.max_requests_per_session)},
            rows=0,
            network_requests=0,
            skipped=True,
        )
    else:
        if bool(getattr(args, "skip_robots_check", False)) or direct_html_fallback_disabled:
            robots_blocked = True
            state.mark_stage(
                "robots_txt",
                "completed",
                cursor={
                    "url": ROBOTS_URL,
                    "mode": "backfill_plan",
                    "skipped": True,
                    "direct_html_fallback_disabled": direct_html_fallback_disabled,
                },
                rows=0,
                network_requests=0,
                skipped=True,
            )
            state.mark_stage(
                "backfill_direct_html_available",
                "completed",
                cursor={"robots_url": ROBOTS_URL, "disabled": True},
                rows=0,
                network_requests=0,
                skipped=True,
            )
        else:
            robots_args = argparse.Namespace(**vars(args))
            _reset_stage_attempts(state, "robots_txt")
            robots_result = _run_stage_with_resume(
                args=robots_args,
                state=state,
                name="robots_txt",
                cursor={"url": ROBOTS_URL, "mode": "backfill_plan"},
                fn=fetch_robots_policy,
            )
            robots_policy = robots_result if robots_result.get("status") == "completed" else {}
            if "direct_html_allowed_live" not in robots_policy and "details" in robots_result:
                robots_policy = dict(robots_result.get("details") or {})
            if robots_policy and robots_policy.get("direct_html_allowed_live") is False:
                state.mark_stage(
                    "backfill_direct_html_available",
                    "degraded",
                    cursor={"robots_url": ROBOTS_URL},
                    failure_reason="robots.txt does not allow direct VLR detail collection",
                    network_requests=0,
                )
                robots_blocked = True
            else:
                robots_blocked = False

        def _api_health_backfill() -> dict[str, Any]:
            available, reason, requests_made = api_base_available(args.api_base_url)
            if not available:
                raise CollectionStageError(f"local vlrggapi unavailable: {reason}", requests_made=requests_made)
            return {"rows": 1, "network_requests": requests_made, "api_base_status": reason}

        api_result = _run_stage_with_resume(
            args=args,
            state=state,
            name="api_base_available",
            cursor={"api_base_url": args.api_base_url, "mode": "backfill_plan"},
            fn=_api_health_backfill,
        )
        args.api_available = api_result.get("status") == "completed"

    robots_blocked_for_fallback = bool(locals().get("robots_blocked", False))
    if int(args.max_requests_per_session) > 0 and (
        bool(getattr(args, "api_available", False)) or not robots_blocked_for_fallback
    ):
        session_requests = int(state.data.get("cumulative_requests", 0) or 0) - requests_before
        candidates_df = _load_and_write_backfill_candidates(args, fetched_at, state, session_requests)
        request_budget = max(0, int(args.max_requests_per_session) - session_requests)
        match_ids = _candidate_ids_for_backfill(
            candidates_df,
            int(args.detail_limit),
            request_budget,
            shard_count=shard_count,
            shard_index=shard_index,
        )
        session_requests = 0
        stopped_reason = "completed"
        for match_id in match_ids:
            if session_requests >= request_budget:
                stopped_reason = "request_budget_exhausted"
                break

            def _detail_stage(match_id: str = match_id) -> dict[str, Any]:
                with _vlrgg_upstream_slot(args, stage_name=f"match_detail_{match_id}"):
                    api_requests = 0
                    if bool(getattr(args, "api_available", False)):
                        try:
                            return fetch_api_match_detail_to_stage(args, match_id, fetched_at)
                        except CollectionStageError as api_exc:
                            api_requests = int(getattr(api_exc, "requests_made", 0) or 0)
                            if robots_blocked_for_fallback:
                                raise CollectionStageError(
                                    f"API detail failed and direct HTML fallback is blocked for match_id={match_id}: {api_exc}",
                                    requests_made=api_requests,
                                ) from api_exc
                        except VLRGGRateLimitError:
                            raise

                    from ml.vlrgg_scraper import scrape_match_detail
                    details = scrape_match_detail(match_id)
                    maps, players, comps = build_match_detail_frames(details, fetched_at)
                    _require_match_detail_rows(
                        match_id=match_id,
                        maps=maps,
                        players=players,
                        source_label="direct HTML fallback",
                        requests_made=int(api_requests + 1),
                    )
                    _write_stage_frame(args, f"match_detail_maps_{match_id}", maps)
                    _write_stage_frame(args, f"match_detail_players_{match_id}", players)
                    _write_stage_frame(args, f"match_detail_compositions_{match_id}", comps)
                    return {
                        "rows": int(len(maps) + len(players) + len(comps)),
                        "network_requests": int(api_requests + 1),
                        "map_rows": int(len(maps)),
                        "player_rows": int(len(players)),
                        "composition_rows": int(len(comps)),
                        "used_api_detail": False,
                        "used_direct_html_fallback": True,
                    }

            result = _run_stage_with_resume(
                args=args,
                state=state,
                name=f"match_detail_{match_id}",
                cursor={
                    "api_path": "/v2/match/details",
                    "match_id": match_id,
                    "mode": "backfill_plan",
                    "direct_html_fallback_enabled": not direct_html_fallback_disabled,
                    **({} if direct_html_fallback_disabled else {"fallback_path": f"/{match_id}"}),
                },
                fn=_detail_stage,
            )
            if not result.get("skipped"):
                session_requests += int(result.get("network_requests", 0) or 0)
            if result.get("status") == "degraded":
                failure_reason = str(result.get("failure_reason", "match detail stage degraded"))
                if "did not normalize to map/player rows" in failure_reason:
                    continue
                stopped_reason = "degraded_match_detail"
                state.mark_stage(
                    "backfill_match_detail_stop",
                    "degraded",
                    cursor={
                        "match_id": match_id,
                        "mode": "backfill_plan",
                        "shard": _backfill_shard_metadata(args),
                    },
                    failure_reason=failure_reason,
                    network_requests=0,
                )
                break
    else:
        stopped_reason = "network_skipped_or_unavailable"

    maps_df = _combine_stage_frames(args, "match_detail_maps_", MATCH_MAP_COLUMNS)
    players_df = _combine_stage_frames(args, "match_detail_players_", MATCH_PLAYER_COLUMNS)
    comps_df = _combine_stage_frames(args, "match_detail_compositions_", COMPOSITION_COLUMNS)
    standings_df = _combine_stage_frames(args, "standings_", STANDINGS_COLUMNS)
    team_stats_df = _combine_stage_frames(args, "team_map_stats_", TEAM_MAP_COLUMNS)
    event_matches_df = _combine_stage_frames(args, "event_matches_", EVENT_MATCH_COLUMNS)
    maps_df, players_df, comps_df, standings_df, team_stats_df, event_matches_df = _dedupe_expanded_outputs(
        maps_df, players_df, comps_df, standings_df, team_stats_df, event_matches_df
    )
    write_expanded_outputs(
        maps_df,
        players_df,
        comps_df,
        standings_df,
        team_stats_df,
        event_matches_df,
        args,
        fetched_at,
        state,
    )
    session_requests = int(state.data.get("cumulative_requests", 0) or 0) - requests_before
    candidates_df = _load_and_write_backfill_candidates(args, fetched_at, state, session_requests)
    print(
        "VLR backfill plan complete: "
        f"candidates={len(candidates_df)} shard={shard_index}/{shard_count} "
        f"maps={len(maps_df)} players={len(players_df)} "
        f"stopped_reason={stopped_reason} "
        f"network_requests={session_requests} "
        f"state={args.state_file}"
    )


def _merge_source_output_dirs(args: argparse.Namespace) -> list[Path]:
    dirs: list[Path] = []
    if not bool(getattr(args, "no_merge_existing_output", False)):
        dirs.append(Path(args.output))
    dirs.extend(Path(value) for value in getattr(args, "shard_output_dirs", []) or [])
    if not getattr(args, "shard_output_dirs", None):
        shard_count, _ = _backfill_shard_settings(args)
        if shard_count > 1:
            output_root = (
                Path(DEFAULT_BACKFILL_SHARD_OUTPUT_ROOT)
                if _is_default_path(getattr(args, "output", DEFAULT_OUTPUT_DIR), DEFAULT_OUTPUT_DIR)
                else Path(args.output)
            )
            dirs.extend(output_root / _shard_marker(index) for index in range(shard_count))
    seen: set[str] = set()
    unique: list[Path] = []
    for path in dirs:
        key = str(path.expanduser().resolve())
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def _merge_csv_from_dirs(source_dirs: list[Path], filename: str, columns: list[str]) -> pd.DataFrame:
    frames = [_ensure_columns(_read_csv(root / filename), columns) for root in source_dirs]
    frames = [df for df in frames if not df.empty]
    if not frames:
        return pd.DataFrame(columns=columns)
    return _ensure_columns(pd.concat(frames, ignore_index=True), columns)


def _dedupe_frame(df: pd.DataFrame, subset: list[str]) -> pd.DataFrame:
    if df.empty:
        return df
    cols = [col for col in subset if col in df.columns]
    return df.drop_duplicates(subset=cols, keep="last").reset_index(drop=True) if cols else df.reset_index(drop=True)


def run_merge_shard_outputs(args: argparse.Namespace) -> None:
    fetched_at = _utc_now()
    args.output = Path(args.output)
    args.reports = Path(args.reports)
    args.output.mkdir(parents=True, exist_ok=True)
    args.reports.mkdir(parents=True, exist_ok=True)
    source_dirs = _merge_source_output_dirs(args)
    if not source_dirs:
        raise ValueError("--shard-output-dirs must include at least one directory, or existing output merging must be enabled")

    maps_df = _merge_csv_from_dirs(source_dirs, "vlrgg_match_maps.csv", MATCH_MAP_COLUMNS)
    players_df = _merge_csv_from_dirs(source_dirs, "vlrgg_match_players.csv", MATCH_PLAYER_COLUMNS)
    comps_df = _merge_csv_from_dirs(source_dirs, "vlrgg_compositions.csv", COMPOSITION_COLUMNS)
    standings_df = _merge_csv_from_dirs(source_dirs, "vlrgg_standings.csv", STANDINGS_COLUMNS)
    team_stats_df = _merge_csv_from_dirs(source_dirs, "vlrgg_team_map_stats.csv", TEAM_MAP_COLUMNS)
    event_matches_df = _merge_csv_from_dirs(source_dirs, "vlrgg_event_matches.csv", EVENT_MATCH_COLUMNS)
    maps_df, players_df, comps_df, standings_df, team_stats_df, event_matches_df = _dedupe_expanded_outputs(
        maps_df,
        players_df,
        comps_df,
        standings_df,
        team_stats_df,
        event_matches_df,
    )
    detail_raw_df = _dedupe_frame(
        _merge_csv_from_dirs(source_dirs, "vlrgg_match_details_raw.csv", MATCH_DETAIL_RAW_COLUMNS),
        ["match_id"],
    )
    rounds_df = _dedupe_frame(
        _merge_csv_from_dirs(source_dirs, "vlrgg_rounds.csv", ROUND_COLUMNS),
        ["match_id", "game_id", "map", "round_num", "team", "winner"],
    )
    economy_df = _dedupe_frame(
        _merge_csv_from_dirs(source_dirs, "vlrgg_economy.csv", ECONOMY_COLUMNS),
        ["match_id", "team"],
    )
    kill_matrix_df = _dedupe_frame(
        _merge_csv_from_dirs(source_dirs, "vlrgg_kill_matrix.csv", KILL_MATRIX_COLUMNS),
        ["match_id", "player"],
    )
    map_vetoes_df = _dedupe_frame(
        _merge_csv_from_dirs(source_dirs, "vlrgg_map_vetoes.csv", MAP_VETO_COLUMNS),
        ["match_id", "sequence", "team", "action", "map", "raw_text"],
    )
    team_transactions_df = _dedupe_frame(
        _merge_csv_from_dirs(source_dirs, "vlrgg_team_transactions.csv", TEAM_TRANSACTION_COLUMNS),
        ["team_id", "date", "action", "player"],
    )

    for name, df in [
        ("vlrgg_match_maps", maps_df),
        ("vlrgg_match_players", players_df),
        ("vlrgg_compositions", comps_df),
        ("vlrgg_standings", standings_df),
        ("vlrgg_team_map_stats", team_stats_df),
        ("vlrgg_event_matches", event_matches_df),
        ("vlrgg_match_details_raw", detail_raw_df),
        ("vlrgg_rounds", rounds_df),
        ("vlrgg_economy", economy_df),
        ("vlrgg_kill_matrix", kill_matrix_df),
        ("vlrgg_map_vetoes", map_vetoes_df),
        ("vlrgg_team_transactions", team_transactions_df),
    ]:
        validate_provenance(df, name)
        df.to_csv(args.output / f"{name}.csv", index=False)

    pipeline_df, pipeline_rejected_df = write_pipeline_readiness_outputs(
        maps_df,
        players_df,
        event_matches_df,
        args,
        fetched_at,
    )

    candidates_df = _merge_csv_from_dirs(source_dirs, "vlrgg_match_candidates.csv", MATCH_CANDIDATE_COLUMNS)
    candidates_df = _dedupe_frame(candidates_df, ["candidate_type", "candidate_id"])
    candidates_df = _with_detail_status_from_frames(candidates_df, maps_df, players_df)
    write_candidate_outputs(candidates_df, args, fetched_at, state=None, session_network_requests=0)

    row_counts = {
        "vlrgg_match_candidates": int(len(candidates_df)),
        "vlrgg_match_maps": int(len(maps_df)),
        "vlrgg_match_players": int(len(players_df)),
        "vlrgg_compositions": int(len(comps_df)),
        "vlrgg_standings": int(len(standings_df)),
        "vlrgg_team_map_stats": int(len(team_stats_df)),
        "vlrgg_event_matches": int(len(event_matches_df)),
        "vlrgg_match_details_raw": int(len(detail_raw_df)),
        "vlrgg_rounds": int(len(rounds_df)),
        "vlrgg_economy": int(len(economy_df)),
        "vlrgg_kill_matrix": int(len(kill_matrix_df)),
        "vlrgg_map_vetoes": int(len(map_vetoes_df)),
        "vlrgg_team_transactions": int(len(team_transactions_df)),
        "vlrgg_pipeline_matches": int(len(pipeline_df)),
        "vlrgg_pipeline_rejected_matches": int(len(pipeline_rejected_df)),
    }
    merge_summary = {
        "generated_at": fetched_at,
        "parser_version": PARSER_VERSION,
        "mode": "vlrgg_shard_merge",
        "source_output_dirs": [str(path) for path in source_dirs],
        "rows": row_counts,
    }
    _write_json_file(args.reports / "vlrgg_shard_merge_summary.json", merge_summary)

    summary_path = args.reports / "vlrgg_ingestion_summary.json"
    summary = _read_json_file(summary_path)
    summary.update({
        "generated_at": fetched_at,
        "parser_version": PARSER_VERSION,
        "mode": "vlrgg_shard_merge",
        "source_output_dirs": [str(path) for path in source_dirs],
        "rows": row_counts,
    })
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    coverage_path = args.reports / "data_source_coverage.json"
    coverage = _read_json_file(coverage_path)
    coverage.setdefault("generated_at", fetched_at)
    sources = coverage.setdefault("sources", {})
    for name, rows in row_counts.items():
        path = args.reports / f"{name}.csv" if name == "vlrgg_pipeline_rejected_matches" else args.output / f"{name}.csv"
        sources[name] = {"rows": rows, "path": str(path)}
    coverage_path.write_text(json.dumps(coverage, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        "VLR shard merge complete: "
        f"source_dirs={len(source_dirs)} maps={len(maps_df)} players={len(players_df)} "
        f"pipeline={len(pipeline_df)} output={args.output}"
    )


def build_match_detail_frames(
    details: list[dict[str, Any]],
    fetched_at: str,
    *,
    source: str = "vlrgg_direct_html",
    method: str = "direct_html_detail",
    cache_hit: bool = False,
    source_url_func: Callable[[str], str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    map_rows: list[dict[str, Any]] = []
    player_rows: list[dict[str, Any]] = []
    composition_rows: list[dict[str, Any]] = []
    for detail in details:
        match_id = _clean_id(detail.get("match_id"))
        game_id = _clean_id(detail.get("game_id"))
        map_name = normalize_map(_clean_text(detail.get("map"))) or _clean_text(detail.get("map"))
        team_a = normalize_team(_clean_text(detail.get("team_a")))
        team_b = normalize_team(_clean_text(detail.get("team_b")))
        first_atk = normalize_team(_clean_text(detail.get("first_atk")))
        source_url = source_url_func(match_id) if source_url_func else _safe_source_url_from_match(match_id)

        team_specs = [
            ("a", team_a, team_b, _normalize_agents(detail.get("agents_a")), detail.get("players_a") or []),
            ("b", team_b, team_a, _normalize_agents(detail.get("agents_b")), detail.get("players_b") or []),
        ]
        scores = {
            side: _sum_rounds(detail.get(f"atk_rounds_{side}"), detail.get(f"def_rounds_{side}"), detail.get(f"ot_rounds_{side}"))
            for side, *_ in team_specs
        }
        for side, team, opponent, agents, players in team_specs:
            other_side = "b" if side == "a" else "a"
            score = scores.get(side, 0)
            opponent_score = scores.get(other_side, 0)
            map_rows.append(_with_provenance({
                "match_id": match_id,
                "game_id": game_id,
                "map": map_name,
                "team": team,
                "opponent": opponent,
                "side_first_half": "attack" if team and first_atk and team == first_atk else "defense",
                "atk_rounds": _int_or_none(detail.get(f"atk_rounds_{side}")),
                "def_rounds": _int_or_none(detail.get(f"def_rounds_{side}")),
                "ot_rounds": _int_or_none(detail.get(f"ot_rounds_{side}")),
                "score": score,
                "opponent_score": opponent_score,
                "map_winner": team if score > opponent_score else (opponent if opponent_score > score else ""),
                "agents": _agent_join(agents),
            }, source=source, source_url=source_url, method=method,
                fetched_at=fetched_at, cache_hit=cache_hit))

            composition_rows.append(_with_provenance({
                "match_id": match_id,
                "game_id": game_id,
                "map": map_name,
                "team": team,
                "agents": _agent_join(agents),
                "comp_key": _comp_key(agents),
                **_role_counts(agents),
            }, source=source, source_url=source_url, method=method,
                fetched_at=fetched_at, cache_hit=cache_hit))

            for player in (players if isinstance(players, list) else []):
                agent = normalize_agent(_clean_text(player.get("agent"))) or _clean_text(player.get("agent"))
                player_rows.append(_with_provenance({
                    "match_id": match_id,
                    "game_id": game_id,
                    "map": map_name,
                    "team": team,
                    "opponent": opponent,
                    "player": _clean_text(player.get("player")),
                    "agent": agent,
                    "rating": _num(player.get("rating")),
                    "acs": _num(player.get("acs")),
                    "kills": _num(player.get("kills")),
                    "deaths": _num(player.get("deaths")),
                    "assists": _num(player.get("assists")),
                    "kast": _num(player.get("kast")),
                    "adr": _num(player.get("adr")),
                    "hs_pct": _pct_to_float(player.get("hs_pct")),
                    "fb": _num(player.get("fb")),
                    "fd": _num(player.get("fd")),
                    "atk_kills": _num(player.get("atk_kills")),
                    "def_kills": _num(player.get("def_kills")),
                    "atk_deaths": _num(player.get("atk_deaths")),
                    "def_deaths": _num(player.get("def_deaths")),
                }, source=source, source_url=source_url, method=method,
                    fetched_at=fetched_at, cache_hit=cache_hit))

    return (
        _ensure_columns(pd.DataFrame(map_rows), MATCH_MAP_COLUMNS),
        _ensure_columns(pd.DataFrame(player_rows), MATCH_PLAYER_COLUMNS),
        _ensure_columns(pd.DataFrame(composition_rows), COMPOSITION_COLUMNS),
    )


def _standings_frame(rows: list[dict[str, Any]], *, year: int, fetched_at: str) -> pd.DataFrame:
    source_url = f"https://www.vlr.gg/vct-{year}/standings"
    out = [
        _with_provenance({
            "year": year,
            "region": _clean_text(row.get("region")),
            "rank": _int_or_none(row.get("rank")),
            "team": normalize_team(_clean_text(row.get("team"))),
            "team_id": _clean_id(row.get("team_id")),
            "points": _int_or_none(row.get("points")),
            "country": _clean_text(row.get("country")),
        }, source="vlrgg_direct_html", source_url=source_url, method="direct_html_standings",
            fetched_at=fetched_at, cache_hit=False)
        for row in rows
    ]
    return _ensure_columns(pd.DataFrame(out), STANDINGS_COLUMNS)


def _team_map_stats_frame(rows: list[dict[str, Any]], *, team_id: str, team: str,
                          fetched_at: str) -> pd.DataFrame:
    source_url = f"https://www.vlr.gg/team/stats/{team_id}"
    out = []
    for row in rows:
        out.append(_with_provenance({
            "team_id": _clean_id(row.get("team_id") or team_id),
            "team": normalize_team(team),
            "map": normalize_map(_clean_text(row.get("map"))) or _clean_text(row.get("map")),
            "games": _int_or_none(row.get("games")),
            "win_rate": _pct_to_float(row.get("win_rate")),
            "wins": _int_or_none(row.get("wins")),
            "losses": _int_or_none(row.get("losses")),
            "atk_first": _int_or_none(row.get("atk_first")),
            "def_first": _int_or_none(row.get("def_first")),
            "atk_rwin_pct": _pct_to_float(row.get("atk_rwin_pct")),
            "atk_rw": _int_or_none(row.get("atk_rw")),
            "atk_rl": _int_or_none(row.get("atk_rl")),
            "def_rwin_pct": _pct_to_float(row.get("def_rwin_pct")),
            "def_rw": _int_or_none(row.get("def_rw")),
            "def_rl": _int_or_none(row.get("def_rl")),
        }, source="vlrgg_direct_html", source_url=source_url, method="direct_html_team_stats",
            fetched_at=fetched_at, cache_hit=False))
    return _ensure_columns(pd.DataFrame(out), TEAM_MAP_COLUMNS)


def _event_matches_frame(rows: list[dict[str, Any]], *, event_id: str, event: str,
                         fetched_at: str, page: int = 1) -> pd.DataFrame:
    source_url = f"https://www.vlr.gg/event/matches/{event_id}/?series_id=all&page={page}"
    out = []
    for row in rows:
        score_a = _int_or_none(row.get("score_a"))
        score_b = _int_or_none(row.get("score_b"))
        out.append(_with_provenance({
            "event_id": _clean_id(row.get("event_id") or event_id),
            "event": _clean_text(event),
            "match_id": _clean_id(row.get("match_id")),
            "team_a": normalize_team(_clean_text(row.get("team_a"))),
            "team_b": normalize_team(_clean_text(row.get("team_b"))),
            "score_a": score_a,
            "score_b": score_b,
            "date": _clean_text(row.get("date")),
        }, source="vlrgg_direct_html", source_url=source_url, method="direct_html_event_matches",
            fetched_at=fetched_at, cache_hit=False))
    return _ensure_columns(pd.DataFrame(out), EVENT_MATCH_COLUMNS)


def _event_player_stats_frame(
    rows: list[dict[str, Any]],
    *,
    event_id: str,
    event: str,
    fetched_at: str,
) -> pd.DataFrame:
    source_url = f"https://www.vlr.gg/event/stats/{event_id}/?series_id=all"
    out: list[dict[str, Any]] = []
    for row in rows:
        out.append(_with_provenance({
            "event_id": _clean_id(row.get("event_id") or event_id),
            "event": _clean_text(row.get("event") or event),
            "player": normalize_player(_clean_text(row.get("player"))),
            "team": normalize_team(_clean_text(row.get("team"))),
            "agent": normalize_agent(_clean_text(row.get("agent"))) or _clean_text(row.get("agent")),
            "map_key": normalize_map(_clean_text(row.get("map_key"))) or _clean_text(row.get("map_key")),
            "rounds_played": _int_or_none(row.get("rounds_played")),
            "rating": _num(row.get("rating")),
            "average_combat_score": _num(row.get("average_combat_score", row.get("acs"))),
            "kill_deaths": _num(row.get("kill_deaths", row.get("kd"))),
            "average_damage_per_round": _num(row.get("average_damage_per_round", row.get("adr"))),
            "kills_per_round": _num(row.get("kills_per_round", row.get("kpr"))),
            "assists_per_round": _num(row.get("assists_per_round", row.get("apr"))),
            "first_kills_per_round": _num(row.get("first_kills_per_round", row.get("fkpr"))),
            "first_deaths_per_round": _num(row.get("first_deaths_per_round", row.get("fdpr"))),
            "headshot_percentage": _pct_to_float(row.get("headshot_percentage")),
            "clutch_success_percentage": _pct_to_float(row.get("clutch_success_percentage")),
        }, source="vlrgg_direct_html", source_url=source_url, method="direct_html_event_player_stats",
            fetched_at=fetched_at, cache_hit=False))
    return _ensure_columns(pd.DataFrame(out), EVENT_PLAYER_STATS_COLUMNS)


def _event_agent_usage_frame(
    rows: list[dict[str, Any]],
    *,
    event_id: str,
    event: str,
    fetched_at: str,
) -> pd.DataFrame:
    source_url = f"https://www.vlr.gg/event/agents/{event_id}/?series_id=all"
    out: list[dict[str, Any]] = []
    for row in rows:
        out.append(_with_provenance({
            "event_id": _clean_id(row.get("event_id") or event_id),
            "event": _clean_text(row.get("event") or event),
            "map": normalize_map(_clean_text(row.get("map"))) or _clean_text(row.get("map")),
            "agent": normalize_agent(_clean_text(row.get("agent"))) or _clean_text(row.get("agent")),
            "use_count": _num(row.get("use_count")),
            "use_rate": _pct_to_float(row.get("use_rate")),
            "rounds_played": _int_or_none(row.get("rounds_played")),
            "win_rate": _pct_to_float(row.get("win_rate")),
            "raw_metric_json": _json_text(row.get("raw_metric", row)),
        }, source="vlrgg_direct_html", source_url=source_url, method="direct_html_event_agent_usage",
            fetched_at=fetched_at, cache_hit=False))
    return _ensure_columns(pd.DataFrame(out), EVENT_AGENT_USAGE_COLUMNS)


def parse_standing_years(value: str) -> list[int]:
    years: list[int] = []
    for part in str(value or "").split(","):
        text = part.strip()
        if not text:
            continue
        try:
            years.append(int(text))
        except ValueError:
            raise ValueError(f"invalid standing year: {text}") from None
    return years or [2024, 2025, 2026]


def _team_candidates_from_standings(standings_df: pd.DataFrame, limit: int) -> list[dict[str, str]]:
    if standings_df.empty or "team_id" not in standings_df.columns or limit < 0:
        return []
    df = standings_df.copy()
    df["team_id"] = df["team_id"].map(_clean_id)
    df = df[df["team_id"].str.fullmatch(r"\d+")]
    if df.empty:
        return []
    df["_year_sort"] = pd.to_numeric(df.get("year"), errors="coerce").fillna(0)
    df["_points_sort"] = pd.to_numeric(df.get("points"), errors="coerce").fillna(0)
    df["_rank_sort"] = pd.to_numeric(df.get("rank"), errors="coerce").fillna(9999)
    df = df.sort_values(["_year_sort", "_points_sort", "_rank_sort"], ascending=[False, False, True])
    out = []
    candidates = _limit_frame(df.drop_duplicates("team_id"), int(limit))
    for _, row in candidates.iterrows():
        out.append({"team_id": _clean_id(row.get("team_id")), "team": normalize_team(_clean_text(row.get("team")))})
    return out


def _event_candidates_from_frame(df: pd.DataFrame, limit: int) -> list[dict[str, str]]:
    if df.empty or limit < 0:
        return []
    out = []
    for _, row in _limit_frame(df, int(limit)).iterrows():
        event_id = _clean_id(row.get("event_id"))
        if not event_id:
            continue
        out.append({
            "event_id": event_id,
            "event": _clean_text(row.get("event")),
            "url_path": _clean_text(row.get("url_path")),
        })
        if int(limit) > 0 and len(out) >= limit:
            break
    return out


def fetch_event_candidates_to_stage(args: argparse.Namespace, limit: int, fetched_at: str) -> dict[str, Any]:
    client = VLRGGClient(
        rate_limit_per_second=args.rate_limit,
        cache_dir=str(args.cache_dir),
        base_url=args.api_base_url,
        cache_only=not bool(getattr(args, "api_available", False)),
        api_version=DEFAULT_API_VERSION,
    )
    rows: list[dict[str, Any]] = []
    if int(limit) == 0:
        pages = max(1, int(getattr(args, "event_pages", 5) or 5))
    else:
        pages = max(1, min(int(getattr(args, "event_pages", 5) or 5), (max(limit, 1) + 49) // 50))
    for page in range(1, pages + 1):
        events = client.fetch_events("completed", page=page) or []
        if not events:
            break
        source_url = _source_url_for_api(args.api_base_url, "/events", {"q": "completed", "page": page})
        for row in events:
            if not isinstance(row, dict):
                continue
            url_path = _clean_text(row.get("url_path", row.get("url")))
            event_id = VLRGGClient.extract_event_id(url_path) or _clean_id(row.get("event_id", row.get("id")))
            if not event_id:
                continue
            rows.append(_with_provenance({
                "event_id": event_id,
                "event": _clean_text(row.get("title", row.get("event", row.get("name")))),
                "url_path": url_path,
            }, source="vlrgg_api", source_url=url_path or source_url,
                method="api" if not client.last_cache_hit else "api_cache",
                fetched_at=fetched_at, cache_hit=client.last_cache_hit))
            if int(limit) > 0 and len(rows) >= limit:
                break
        if int(limit) > 0 and len(rows) >= limit:
            break
    df = pd.DataFrame(rows)
    _write_stage_frame(args, "expanded_event_candidates", df)
    return {"rows": int(len(df)), "network_requests": int(client.request_count)}


def expand_event_matches_to_stage(
    args: argparse.Namespace,
    event_candidates_df: pd.DataFrame,
    fetched_at: str,
    request_budget: int,
) -> dict[str, Any]:
    from ml.vlrgg_scraper import scrape_event_matches

    rows_total = 0
    requests_made = 0
    event_count = 0
    event_limit = int(getattr(args, "event_limit", DEFAULT_EVENT_LIMIT) or 0)
    max_pages = int(getattr(args, "event_match_pages", 1) or 1)
    candidates = _event_candidates_from_frame(event_candidates_df, event_limit)
    for candidate in candidates:
        if int(request_budget) > 0 and requests_made >= int(request_budget):
            break
        event_id = candidate["event_id"]
        event = candidate["event"]
        event_count += 1
        page = 1
        while True:
            if int(request_budget) > 0 and requests_made >= int(request_budget):
                break
            if max_pages > 0 and page > max_pages:
                break
            rows = scrape_event_matches(event_id, page=page)
            requests_made += 1
            frame = _event_matches_frame(rows, event_id=event_id, event=event, fetched_at=fetched_at, page=page)
            if not frame.empty:
                _write_stage_frame(args, f"event_matches_{event_id}_page_{page}", frame)
                rows_total += int(len(frame))
            if not rows:
                break
            page += 1
            if max_pages == 0 and page > 100:
                break
    return {
        "rows": int(rows_total),
        "network_requests": int(requests_made),
        "events": int(event_count),
        "event_match_pages": max_pages,
    }


def expand_event_intel_to_stage(
    args: argparse.Namespace,
    event_candidates_df: pd.DataFrame,
    fetched_at: str,
    request_budget: int,
) -> dict[str, Any]:
    from ml.vlrgg_scraper import scrape_event_agent_usage, scrape_event_player_stats

    rows_total = 0
    player_rows_total = 0
    agent_rows_total = 0
    requests_made = 0
    events_seen = 0
    degraded_events: list[dict[str, str]] = []
    event_limit = int(getattr(args, "event_limit", DEFAULT_EVENT_LIMIT) or 0)
    direct_delay = max(1.0, 1.0 / max(float(args.rate_limit), 1e-6))

    for candidate in _event_candidates_from_frame(event_candidates_df, event_limit):
        if int(request_budget) > 0 and requests_made >= int(request_budget):
            break
        event_id = candidate["event_id"]
        event = candidate["event"]
        events_seen += 1

        player_rows = scrape_event_player_stats(event_id, delay=direct_delay)
        requests_made += 1
        player_df = _event_player_stats_frame(player_rows, event_id=event_id, event=event, fetched_at=fetched_at)
        _write_stage_frame(args, f"event_player_stats_{event_id}", player_df)
        player_rows_total += int(len(player_df))
        rows_total += int(len(player_df))
        if player_df.empty:
            degraded_events.append({"event_id": event_id, "stage": "event_player_stats", "reason": "no static player stats table rows"})

        if int(request_budget) > 0 and requests_made >= int(request_budget):
            break
        agent_rows = scrape_event_agent_usage(event_id, delay=direct_delay)
        requests_made += 1
        agent_df = _event_agent_usage_frame(agent_rows, event_id=event_id, event=event, fetched_at=fetched_at)
        _write_stage_frame(args, f"event_agent_usage_{event_id}", agent_df)
        agent_rows_total += int(len(agent_df))
        rows_total += int(len(agent_df))
        if agent_df.empty:
            degraded_events.append({"event_id": event_id, "stage": "event_agent_usage", "reason": "no static agent usage table rows"})

    status = "degraded" if degraded_events and rows_total == 0 else "completed"
    result: dict[str, Any] = {
        "status": status,
        "rows": int(rows_total),
        "network_requests": int(requests_made),
        "events": int(events_seen),
        "event_player_stats_rows": int(player_rows_total),
        "event_agent_usage_rows": int(agent_rows_total),
        "degraded_events": degraded_events,
    }
    if status == "degraded":
        result["failure_reason"] = "event stats/agents pages did not expose static table rows"
    return result


def _event_matches_frame_from_api(
    rows: list[dict[str, Any]],
    *,
    event_id: str,
    event: str,
    source_url: str,
    fetched_at: str,
    cache_hit: bool,
) -> pd.DataFrame:
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        teams = _as_list(row.get("teams"))
        team_a = normalize_team(_clean_text(teams[0].get("name"))) if len(teams) > 0 and isinstance(teams[0], dict) else ""
        team_b = normalize_team(_clean_text(teams[1].get("name"))) if len(teams) > 1 and isinstance(teams[1], dict) else ""
        score_a = _int_or_none(teams[0].get("score")) if len(teams) > 0 and isinstance(teams[0], dict) else None
        score_b = _int_or_none(teams[1].get("score")) if len(teams) > 1 and isinstance(teams[1], dict) else None
        out.append(_with_provenance({
            "event_id": _clean_id(row.get("event_id") or event_id),
            "event": _clean_text(row.get("event", event)),
            "match_id": _clean_id(row.get("match_id")),
            "team_a": team_a,
            "team_b": team_b,
            "score_a": score_a,
            "score_b": score_b,
            "date": _clean_text(row.get("date")),
        }, source="vlrgg_api", source_url=source_url,
            method="api_event_matches_cache" if cache_hit else "api_event_matches",
            fetched_at=fetched_at, cache_hit=cache_hit))
    return _ensure_columns(pd.DataFrame(out), EVENT_MATCH_COLUMNS)


def _profile_match_rows_from_api(
    rows: list[dict[str, Any]],
    *,
    source_url: str,
    fetched_at: str,
    cache_hit: bool,
    source: str,
) -> pd.DataFrame:
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        teams = row.get("teams")
        if isinstance(teams, dict):
            team_a = normalize_team(_clean_text(teams.get("team1")))
            team_b = normalize_team(_clean_text(teams.get("team2")))
        elif isinstance(teams, list):
            team_a = normalize_team(_clean_text(teams[0].get("name"))) if len(teams) > 0 and isinstance(teams[0], dict) else ""
            team_b = normalize_team(_clean_text(teams[1].get("name"))) if len(teams) > 1 and isinstance(teams[1], dict) else ""
        else:
            team_a = ""
            team_b = ""
        score_text = _clean_text(row.get("score"))
        score_a = score_b = None
        m_score = re.match(r"^\s*(\d+)\s*[-:]\s*(\d+)", score_text)
        if m_score:
            score_a = int(m_score.group(1))
            score_b = int(m_score.group(2))
        out.append(_with_provenance({
            "match_id": _clean_id(row.get("match_id")),
            "event": _clean_text(row.get("event")),
            "date": _clean_text(row.get("date")),
            "round_info": _clean_text(row.get("event_series", row.get("series"))),
            "team_a": team_a,
            "team_b": team_b,
            "score_a": score_a,
            "score_b": score_b,
            "label": 1 if score_a is not None and score_b is not None and score_a > score_b else (
                0 if score_a is not None and score_b is not None and score_a < score_b else None
            ),
            "map": "",
        }, source=source, source_url=source_url,
            method="api_profile_matches_cache" if cache_hit else "api_profile_matches",
            fetched_at=fetched_at, cache_hit=cache_hit))
    return _ensure_columns(pd.DataFrame(out), API_MATCH_COLUMNS)


def _event_detail_frames_from_api(
    event_id: str,
    detail: dict[str, Any],
    *,
    fetched_at: str,
    source_url: str,
    cache_hit: bool,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    event_info = _as_dict(detail.get("event")) or _as_dict(detail.get("info"))
    event_name = _clean_text(event_info.get("name", detail.get("name")))
    teams = _as_list(detail.get("teams"))
    team_ids: list[str] = []
    player_ids: list[str] = []
    team_rows: list[dict[str, Any]] = []
    player_rows: list[dict[str, Any]] = []
    for team in teams:
        if not isinstance(team, dict):
            continue
        team_id = _clean_id(team.get("id", team.get("team_id")))
        team_name = normalize_team(_clean_text(team.get("name", team.get("team"))))
        if team_id:
            team_ids.append(team_id)
            team_rows.append(_with_provenance({
                "candidate_id": team_id,
                "team_id": team_id,
                "team": team_name,
                "region": _clean_text(team.get("region")),
                "rank": None,
                "country": _clean_text(team.get("country", team.get("region"))),
                "record": "",
                "earnings": "",
                "status": "profile_pending",
                "status_reason": "team discovered from event detail; profile not fetched yet",
                "priority": 20,
            }, source="vlrgg_api_event_detail", source_url=source_url,
                method="api_event_detail_cache" if cache_hit else "api_event_detail",
                fetched_at=fetched_at, cache_hit=cache_hit))
        for player in _as_list(team.get("players")):
            if not isinstance(player, dict):
                continue
            player_id = _clean_id(player.get("id", player.get("player_id")))
            if not player_id:
                continue
            player_ids.append(player_id)
            player_rows.append(_with_provenance({
                "candidate_id": player_id,
                "player_id": player_id,
                "player": normalize_player(_clean_text(player.get("name", player.get("alias")))),
                "team_id": team_id,
                "team": team_name,
                "event_id": event_id,
                "event": event_name,
                "country": _clean_text(player.get("flag", player.get("country"))),
                "status": "profile_pending",
                "status_reason": "player discovered from event roster; profile not fetched yet",
                "priority": 25,
            }, source="vlrgg_api_event_detail", source_url=source_url,
                method="api_event_detail_cache" if cache_hit else "api_event_detail",
                fetched_at=fetched_at, cache_hit=cache_hit))
    detail_row = _with_provenance({
        "event_id": event_id,
        "event": event_name,
        "series": _clean_text(event_info.get("series", detail.get("series"))),
        "dates": _clean_text(event_info.get("dates", detail.get("dates"))),
        "prize": _clean_text(event_info.get("prize", detail.get("prize"))),
        "location": _clean_text(event_info.get("location", detail.get("location"))),
        "bracket_json": _json_text(detail.get("bracket", detail.get("brackets", event_info.get("bracket", {})))),
        "prize_distribution_json": _json_text(detail.get(
            "prize_distribution",
            detail.get("prizeDistribution", detail.get("placements", detail.get("prizes", {}))),
        )),
        "points_json": _json_text(detail.get(
            "points",
            detail.get("point_distribution", detail.get("circuit_points", event_info.get("points", {}))),
        )),
        "team_ids_json": _json_text(sorted(set(team_ids))),
        "player_ids_json": _json_text(sorted(set(player_ids))),
        "raw_json": _json_text(detail),
    }, source="vlrgg_api_event_detail", source_url=source_url,
        method="api_event_detail_cache" if cache_hit else "api_event_detail",
        fetched_at=fetched_at, cache_hit=cache_hit)
    return (
        _ensure_columns(pd.DataFrame([detail_row]), EVENT_DETAIL_COLUMNS),
        _ensure_columns(pd.DataFrame(team_rows), TEAM_CANDIDATE_COLUMNS),
        _ensure_columns(pd.DataFrame(player_rows), PLAYER_CANDIDATE_COLUMNS),
    )


def expand_api_event_details_to_stage(
    args: argparse.Namespace,
    event_candidates_df: pd.DataFrame,
    fetched_at: str,
    request_budget: int,
) -> dict[str, Any]:
    client = VLRGGClient(
        rate_limit_per_second=args.rate_limit,
        cache_dir=str(args.cache_dir),
        base_url=args.api_base_url,
        cache_only=not bool(getattr(args, "api_available", False)),
        api_version=DEFAULT_API_VERSION,
    )
    rows_total = 0
    team_total = 0
    player_total = 0
    event_count = 0
    for candidate in _event_candidates_from_frame(event_candidates_df, int(getattr(args, "event_limit", 0) or 0)):
        if int(request_budget) > 0 and client.request_count >= int(request_budget):
            break
        event_id = candidate["event_id"]
        source_url = _source_url_for_api(args.api_base_url, f"/event/{event_id}", {})
        detail = client.fetch_event_detail(event_id)
        if not detail:
            continue
        event_count += 1
        detail_df, team_df, player_df = _event_detail_frames_from_api(
            event_id,
            detail,
            fetched_at=fetched_at,
            source_url=source_url,
            cache_hit=client.last_cache_hit,
        )
        _write_stage_frame(args, f"event_detail_{event_id}", detail_df)
        _write_stage_frame(args, f"event_team_candidates_{event_id}", team_df)
        _write_stage_frame(args, f"event_player_candidates_{event_id}", player_df)
        rows_total += int(len(detail_df))
        team_total += int(len(team_df))
        player_total += int(len(player_df))
    return {
        "rows": int(rows_total + team_total + player_total),
        "network_requests": int(client.request_count),
        "events": int(event_count),
        "event_detail_rows": int(rows_total),
        "team_candidates": int(team_total),
        "player_candidates": int(player_total),
    }


def expand_api_event_matches_to_stage(
    args: argparse.Namespace,
    event_candidates_df: pd.DataFrame,
    fetched_at: str,
    request_budget: int,
) -> dict[str, Any]:
    client = VLRGGClient(
        rate_limit_per_second=args.rate_limit,
        cache_dir=str(args.cache_dir),
        base_url=args.api_base_url,
        cache_only=not bool(getattr(args, "api_available", False)),
        api_version=DEFAULT_API_VERSION,
    )
    rows_total = 0
    event_count = 0
    for candidate in _event_candidates_from_frame(event_candidates_df, int(getattr(args, "event_limit", 0) or 0)):
        if int(request_budget) > 0 and client.request_count >= int(request_budget):
            break
        event_id = candidate["event_id"]
        event = candidate["event"]
        source_url = _source_url_for_api(args.api_base_url, "/events/matches", {"event_id": event_id})
        rows = client.fetch_event_matches(event_id) or []
        frame = _event_matches_frame_from_api(
            rows,
            event_id=event_id,
            event=event,
            source_url=source_url,
            fetched_at=fetched_at,
            cache_hit=client.last_cache_hit,
        )
        if not frame.empty:
            _write_stage_frame(args, f"event_matches_{event_id}", frame)
        rows_total += int(len(frame))
        event_count += 1
    return {
        "rows": int(rows_total),
        "network_requests": int(client.request_count),
        "events": int(event_count),
    }


def _team_profile_frame_from_api(
    team_id: str,
    profile: dict[str, Any],
    *,
    fetched_at: str,
    source_url: str,
    cache_hit: bool,
) -> pd.DataFrame:
    info = _as_dict(profile.get("info"))
    rating = _as_dict(profile.get("rating"))
    row = _with_provenance({
        "team_id": team_id,
        "team": normalize_team(_clean_text(info.get("name", profile.get("name")))),
        "tag": _clean_text(info.get("tag")),
        "country": _clean_text(info.get("country")),
        "region": _clean_text(rating.get("region")),
        "rank": _int_or_none(rating.get("rank")),
        "current_rating": _int_or_none(_first_present(rating, "rating", "current_rating", "elo")),
        "record": _first_clean(rating.get("record"), profile.get("record")),
        "core_id": _first_clean(rating.get("core_id"), rating.get("core"), profile.get("core_id")),
        "roster_json": _json_text(profile.get("roster", [])),
        "rating_history_json": _json_text(_first_present(profile, "rating_history", "ratings", "rating_history_json") or []),
        "event_placements_json": _json_text(profile.get("event_placements", [])),
        "total_winnings": _clean_text(profile.get("total_winnings")),
        "raw_json": _json_text(profile),
    }, source="vlrgg_api_team_profile", source_url=source_url,
        method="api_team_profile_cache" if cache_hit else "api_team_profile",
        fetched_at=fetched_at, cache_hit=cache_hit)
    return _ensure_columns(pd.DataFrame([row]), TEAM_PROFILE_COLUMNS)


def _player_profile_frame_from_api(
    player_id: str,
    profile: dict[str, Any],
    *,
    fetched_at: str,
    source_url: str,
    cache_hit: bool,
) -> pd.DataFrame:
    info = _as_dict(profile.get("info"))
    current_teams = _first_present(profile, "current_teams", "current_team", "team") or _first_present(info, "current_teams", "current_team", "team")
    past_teams = _first_present(profile, "past_teams", "former_teams") or _first_present(info, "past_teams", "former_teams")
    placements = _first_present(profile, "event_placements", "placements", "achievements") or _first_present(info, "event_placements", "placements", "achievements")
    agent_stats = _profile_agent_stats(profile)
    row = _with_provenance({
        "player_id": player_id,
        "player": normalize_player(_first_clean(info.get("name"), profile.get("name"), profile.get("player"))),
        "real_name": _first_clean(info.get("real_name"), info.get("realName"), profile.get("real_name"), profile.get("realName")),
        "country": _first_clean(info.get("country"), profile.get("country"), info.get("flag"), profile.get("flag")),
        "current_teams_json": _json_payload(current_teams, []),
        "past_teams_json": _json_payload(past_teams, []),
        "social_handles_json": _json_text(_extract_social_handles(profile)),
        "agent_stats_json": _json_text(agent_stats),
        "event_placements_json": _json_payload(placements, []),
        "total_winnings": _first_clean(profile.get("total_winnings"), profile.get("winnings"), profile.get("earnings"), info.get("total_winnings")),
        "raw_json": _json_text(profile),
    }, source="vlrgg_api_player_profile", source_url=source_url,
        method="api_player_profile_cache" if cache_hit else "api_player_profile",
        fetched_at=fetched_at, cache_hit=cache_hit)
    return _ensure_columns(pd.DataFrame([row]), PLAYER_PROFILE_COLUMNS)


def _player_agent_usage_frame_from_api(
    player_id: str,
    profile: dict[str, Any],
    *,
    timespan: str,
    fetched_at: str,
    source_url: str,
    cache_hit: bool,
) -> pd.DataFrame:
    info = _as_dict(profile.get("info"))
    player_name = normalize_player(_first_clean(info.get("name"), profile.get("name"), profile.get("player")))
    rows: list[dict[str, Any]] = []
    for stat in _profile_agent_stats(profile):
        agent = normalize_agent(_first_clean(
            stat.get("agent"),
            stat.get("agent_name"),
            stat.get("name"),
        )) or _first_clean(stat.get("agent"), stat.get("agent_name"), stat.get("name"))
        rows.append(_with_provenance({
            "player_id": player_id,
            "player": player_name,
            "timespan": timespan,
            "agent": agent,
            "usage_count": _int_or_none(_first_present(stat, "usage_count", "use_count", "uses", "use")),
            "matches_played": _int_or_none(_first_present(stat, "matches_played", "matches")),
            "maps_played": _int_or_none(_first_present(stat, "maps_played", "maps")),
            "rounds_played": _int_or_none(_first_present(stat, "rounds_played", "rounds", "rds")),
            "rating": _num(_first_present(stat, "rating", "rating_2")),
            "average_combat_score": _num(_first_present(stat, "average_combat_score", "acs")),
            "kill_deaths": _num(_first_present(stat, "kill_deaths", "kd", "k_d")),
            "average_damage_per_round": _num(_first_present(stat, "average_damage_per_round", "adr")),
            "kills": _num(_first_present(stat, "kills", "k")),
            "deaths": _num(_first_present(stat, "deaths", "d")),
            "assists": _num(_first_present(stat, "assists", "a")),
            "kills_per_round": _num(_first_present(stat, "kills_per_round", "kpr")),
            "assists_per_round": _num(_first_present(stat, "assists_per_round", "apr")),
            "first_kills": _num(_first_present(stat, "first_kills", "fk", "fb")),
            "first_deaths": _num(_first_present(stat, "first_deaths", "fd")),
            "first_kills_per_round": _num(_first_present(stat, "first_kills_per_round", "fkpr")),
            "first_deaths_per_round": _num(_first_present(stat, "first_deaths_per_round", "fdpr")),
            "headshot_percentage": _pct_to_float(_first_present(stat, "headshot_percentage", "hs_pct", "hs")),
            "clutch_success_percentage": _pct_to_float(_first_present(stat, "clutch_success_percentage", "clutch")),
            "raw_json": _json_text(stat),
        }, source="vlrgg_api_player_profile", source_url=source_url,
            method="api_player_profile_cache" if cache_hit else "api_player_profile",
            fetched_at=fetched_at, cache_hit=cache_hit))
    return _ensure_columns(pd.DataFrame(rows), PLAYER_AGENT_USAGE_COLUMNS)


def _player_recent_matches_frame_from_api(
    player_id: str,
    player: str,
    rows: list[dict[str, Any]],
    *,
    page: int,
    fetched_at: str,
    source_url: str,
    cache_hit: bool,
) -> pd.DataFrame:
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        team_a, team_b = _teams_from_match_row(row)
        score_a, score_b = _score_from_match_row(row)
        url_path = _clean_text(row.get("url_path", row.get("match_page", row.get("url"))))
        match_id = _clean_id(row.get("match_id", row.get("id"))) or _clean_id(VLRGGClient.extract_match_id(url_path) or "")
        out.append(_with_provenance({
            "player_id": player_id,
            "player": normalize_player(player),
            "page": int(page),
            "match_id": match_id,
            "event": _clean_text(row.get("event", row.get("tournament_name", row.get("tournament")))),
            "date": _clean_text(row.get("date", row.get("unix_timestamp", row.get("time_completed")))),
            "round_info": _clean_text(row.get("round_info", row.get("event_series", row.get("series")))),
            "team_a": team_a,
            "team_b": team_b,
            "score_a": score_a,
            "score_b": score_b,
            "label": 1 if score_a is not None and score_b is not None and score_a > score_b else (
                0 if score_a is not None and score_b is not None and score_a < score_b else None
            ),
            "map": normalize_map(_clean_text(row.get("map", row.get("current_map")))) or _clean_text(row.get("map", row.get("current_map"))),
            "raw_json": _json_text(row),
        }, source="vlrgg_api_player_matches", source_url=source_url,
            method="api_player_matches_cache" if cache_hit else "api_player_matches",
            fetched_at=fetched_at, cache_hit=cache_hit))
    return _ensure_columns(pd.DataFrame(out), PLAYER_RECENT_MATCH_COLUMNS)


def _team_transactions_frame_from_api(
    team_id: str,
    team: str,
    rows: list[dict[str, Any]],
    *,
    fetched_at: str,
    source_url: str,
    cache_hit: bool,
) -> pd.DataFrame:
    out = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        out.append(_with_provenance({
            "team_id": team_id,
            "team": normalize_team(team),
            "date": _clean_text(row.get("date")),
            "action": _clean_text(row.get("action")),
            "player": normalize_player(_clean_text(row.get("player"))),
            "position": _clean_text(row.get("position")),
        }, source="vlrgg_api_team_transactions", source_url=source_url,
            method="api_team_transactions_cache" if cache_hit else "api_team_transactions",
            fetched_at=fetched_at, cache_hit=cache_hit))
    return _ensure_columns(pd.DataFrame(out), TEAM_TRANSACTION_COLUMNS)


def _team_candidates_for_profile_expansion(args: argparse.Namespace) -> pd.DataFrame:
    frames = [
        df for df in [
            _combine_stage_frames(args, "api_team_candidates", TEAM_CANDIDATE_COLUMNS),
            _combine_stage_frames(args, "event_team_candidates_", TEAM_CANDIDATE_COLUMNS),
        ]
        if not df.empty
    ]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=TEAM_CANDIDATE_COLUMNS)


def _team_name_lookup_from_candidates(team_candidates: pd.DataFrame) -> dict[str, str]:
    lookup: dict[str, str] = {}
    if team_candidates.empty or "team_id" not in team_candidates.columns:
        return lookup
    for _, row in team_candidates.iterrows():
        team_id = _clean_id(row.get("team_id"))
        if team_id and team_id not in lookup:
            lookup[team_id] = normalize_team(_clean_text(row.get("team")))
    return lookup


def _team_profile_frames_from_direct_html(
    team_id: str,
    profile: dict[str, Any],
    *,
    fetched_at: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    source_url = f"https://www.vlr.gg/team/{team_id}"
    team = normalize_team(_first_clean(profile.get("team"), profile.get("name")))
    roster = _as_list(profile.get("roster"))
    rating_history = _as_list(profile.get("rating_history"))
    matches = _as_list(profile.get("recent_matches"))
    event_placements = _as_list(profile.get("event_placements"))
    profile_row = _with_provenance({
        "team_id": team_id,
        "team": team,
        "tag": _clean_text(profile.get("tag")),
        "country": _clean_text(profile.get("country")),
        "region": _clean_text(profile.get("region")),
        "rank": _int_or_none(profile.get("rank")),
        "current_rating": _int_or_none(profile.get("current_rating")),
        "record": _clean_text(profile.get("record")),
        "core_id": _clean_text(profile.get("core_id")),
        "roster_json": _json_text(roster),
        "rating_history_json": _json_text(rating_history),
        "event_placements_json": _json_text(event_placements),
        "total_winnings": _clean_text(profile.get("total_winnings")),
        "raw_json": _json_text(profile),
    }, source="vlrgg_direct_html", source_url=source_url,
        method="direct_html_team_profile", fetched_at=fetched_at, cache_hit=False)

    roster_rows: list[dict[str, Any]] = []
    for member in roster:
        if not isinstance(member, dict):
            continue
        roster_rows.append(_with_provenance({
            "team_id": team_id,
            "team": team,
            "member_type": _clean_text(member.get("member_type")) or "player",
            "player_id": _clean_id(member.get("player_id")),
            "player": normalize_player(_clean_text(member.get("player"))),
            "real_name": _clean_text(member.get("real_name")),
            "role": _clean_text(member.get("role")),
            "status": _clean_text(member.get("status")) or "active",
        }, source="vlrgg_direct_html", source_url=source_url,
            method="direct_html_team_roster", fetched_at=fetched_at, cache_hit=False))

    rating_rows: list[dict[str, Any]] = []
    core_id = _clean_text(profile.get("core_id"))
    for row in rating_history:
        if not isinstance(row, dict):
            continue
        rating_rows.append(_with_provenance({
            "team_id": team_id,
            "team": team,
            "core_id": core_id,
            "sequence": _int_or_none(row.get("sequence")),
            "date": _clean_text(row.get("date")),
            "opponent": normalize_team(_clean_text(row.get("opponent"))) or _clean_text(row.get("opponent")),
            "event": normalize_event(_clean_text(row.get("event"))) or _clean_text(row.get("event")),
            "result": _clean_text(row.get("result")),
            "rating_delta": _int_or_none(row.get("rating_delta")),
            "rating_after": _int_or_none(row.get("rating_after")),
            "opponent_rating": _int_or_none(row.get("opponent_rating")),
            "raw_text": _clean_text(row.get("raw_text")),
        }, source="vlrgg_direct_html", source_url=source_url,
            method="direct_html_team_rating_history", fetched_at=fetched_at, cache_hit=False))

    match_rows: list[dict[str, Any]] = []
    for row in matches:
        if not isinstance(row, dict):
            continue
        match_rows.append(_with_provenance({
            "team_id": team_id,
            "team": team,
            "match_id": _clean_id(row.get("match_id")),
            "event": normalize_event(_clean_text(row.get("event"))) or _clean_text(row.get("event")),
            "date": _clean_text(row.get("date")),
            "round_info": _clean_text(row.get("round_info")),
            "opponent": normalize_team(_clean_text(row.get("opponent"))) or _clean_text(row.get("opponent")),
            "score_for": _int_or_none(row.get("score_for")),
            "score_against": _int_or_none(row.get("score_against")),
            "status": _clean_text(row.get("status")),
        }, source="vlrgg_direct_html", source_url=source_url,
            method="direct_html_team_matches", fetched_at=fetched_at, cache_hit=False))

    return (
        _ensure_columns(pd.DataFrame([profile_row]), TEAM_PROFILE_COLUMNS),
        _ensure_columns(pd.DataFrame(roster_rows), TEAM_ROSTER_COLUMNS),
        _ensure_columns(pd.DataFrame(rating_rows), TEAM_RATING_HISTORY_COLUMNS),
        _ensure_columns(pd.DataFrame(match_rows), TEAM_MATCH_COLUMNS),
    )


def _profile_candidate_ids(df: pd.DataFrame, id_col: str, limit: int) -> list[str]:
    if df.empty or id_col not in df.columns:
        return []
    work = df.copy()
    work[id_col] = work[id_col].map(_clean_id)
    work = work[work[id_col].str.fullmatch(r"\d+")]
    if work.empty:
        return []
    if "priority" in work.columns:
        work["_priority"] = pd.to_numeric(work["priority"], errors="coerce").fillna(50)
        work = work.sort_values(["_priority", id_col], ascending=[True, True])
    out = work.drop_duplicates(id_col)[id_col].tolist()
    return out if int(limit) == 0 else out[: max(0, int(limit))]


def expand_direct_team_profiles_to_stage(
    args: argparse.Namespace,
    fetched_at: str,
    request_budget: int,
) -> dict[str, Any]:
    from ml.vlrgg_scraper import scrape_team_profile

    team_candidates = _team_candidates_for_profile_expansion(args)
    team_ids = _profile_candidate_ids(
        team_candidates,
        "team_id",
        int(getattr(args, "team_limit", DEFAULT_TEAM_LIMIT) or 0),
    )
    request_count = 0
    profile_rows = roster_rows = rating_rows = match_rows = 0
    delay = max(1.0, 1.0 / max(float(getattr(args, "rate_limit", 1.0) or 1.0), 0.000001))

    for team_id in team_ids:
        if int(request_budget) > 0 and request_count >= int(request_budget):
            break
        profile = scrape_team_profile(team_id, delay=delay)
        request_count += 1
        if not profile:
            continue
        profile_df, roster_df, rating_df, match_df = _team_profile_frames_from_direct_html(
            team_id,
            profile,
            fetched_at=fetched_at,
        )
        _write_stage_frame(args, f"team_profile_direct_{team_id}", profile_df)
        _write_stage_frame(args, f"team_roster_{team_id}", roster_df)
        _write_stage_frame(args, f"team_rating_history_{team_id}", rating_df)
        _write_stage_frame(args, f"team_matches_{team_id}", match_df)
        profile_rows += int(len(profile_df))
        roster_rows += int(len(roster_df))
        rating_rows += int(len(rating_df))
        match_rows += int(len(match_df))

    if team_ids and profile_rows == 0:
        raise CollectionStageError(
            "direct team profile parser returned 0 rows",
            requests_made=request_count,
        )
    return {
        "rows": int(profile_rows + roster_rows + rating_rows + match_rows),
        "network_requests": int(request_count),
        "team_profiles": int(profile_rows),
        "team_roster": int(roster_rows),
        "team_rating_history": int(rating_rows),
        "team_matches": int(match_rows),
    }


def expand_direct_team_map_stats_to_stage(
    args: argparse.Namespace,
    fetched_at: str,
    request_budget: int,
) -> dict[str, Any]:
    from ml.vlrgg_scraper import scrape_team_stats

    team_candidates = _team_candidates_for_profile_expansion(args)
    team_lookup = _team_name_lookup_from_candidates(team_candidates)
    team_ids = _profile_candidate_ids(
        team_candidates,
        "team_id",
        int(getattr(args, "team_limit", DEFAULT_TEAM_LIMIT) or 0),
    )
    request_count = 0
    rows_total = 0
    for team_id in team_ids:
        if int(request_budget) > 0 and request_count >= int(request_budget):
            break
        rows = scrape_team_stats(team_id)
        request_count += 1
        frame = _team_map_stats_frame(
            rows,
            team_id=team_id,
            team=team_lookup.get(team_id, ""),
            fetched_at=fetched_at,
        )
        if not frame.empty:
            _write_stage_frame(args, f"team_map_stats_{team_id}", frame)
            rows_total += int(len(frame))
    return {
        "rows": int(rows_total),
        "network_requests": int(request_count),
        "team_map_stats": int(rows_total),
    }


def expand_api_profiles_to_stage(
    args: argparse.Namespace,
    fetched_at: str,
    request_budget: int,
) -> dict[str, Any]:
    client = VLRGGClient(
        rate_limit_per_second=args.rate_limit,
        cache_dir=str(args.cache_dir),
        base_url=args.api_base_url,
        cache_only=not bool(getattr(args, "api_available", False)),
        api_version=DEFAULT_API_VERSION,
    )
    team_candidates = _team_candidates_for_profile_expansion(args)
    player_candidates = _combine_stage_frames(args, "event_player_candidates_", PLAYER_CANDIDATE_COLUMNS)

    team_profiles = team_transactions = team_match_rows = 0
    for team_id in _profile_candidate_ids(team_candidates, "team_id", int(getattr(args, "team_limit", DEFAULT_TEAM_LIMIT) or 0)):
        if int(request_budget) > 0 and client.request_count >= int(request_budget):
            break
        source_url = _source_url_for_api(args.api_base_url, "/team", {"id": team_id})
        profile = client.fetch_team(team_id)
        if profile:
            profile_df = _team_profile_frame_from_api(
                team_id,
                profile,
                fetched_at=fetched_at,
                source_url=source_url,
                cache_hit=client.last_cache_hit,
            )
            _write_stage_frame(args, f"team_profile_{team_id}", profile_df)
            team_profiles += int(len(profile_df))
        if int(request_budget) > 0 and client.request_count >= int(request_budget):
            break
        match_url = _source_url_for_api(args.api_base_url, "/team/matches", {"id": team_id, "page": 1})
        matches = client.fetch_team_matches(team_id, page=1) or []
        match_df = _profile_match_rows_from_api(
            matches,
            source_url=match_url,
            fetched_at=fetched_at,
            cache_hit=client.last_cache_hit,
            source="vlrgg_api_team_matches",
        )
        if not match_df.empty:
            _write_stage_frame(args, f"api_profile_match_rows_team_{team_id}", match_df)
            team_match_rows += int(len(match_df))
        if int(request_budget) > 0 and client.request_count >= int(request_budget):
            break
        transaction_url = _source_url_for_api(args.api_base_url, "/team/transactions", {"id": team_id})
        transactions = client.fetch_team_transactions(team_id) or []
        team_name = ""
        if not team_candidates.empty:
            rows = team_candidates[team_candidates["team_id"].map(_clean_id) == team_id]
            if not rows.empty:
                team_name = _clean_text(rows.iloc[0].get("team"))
        transaction_df = _team_transactions_frame_from_api(
            team_id,
            team_name,
            transactions,
            fetched_at=fetched_at,
            source_url=transaction_url,
            cache_hit=client.last_cache_hit,
        )
        if not transaction_df.empty:
            _write_stage_frame(args, f"team_transactions_{team_id}", transaction_df)
            team_transactions += int(len(transaction_df))

    player_profiles = player_match_rows = 0
    player_limit = int(getattr(args, "player_limit", DEFAULT_PLAYER_LIMIT) or 0)
    player_ids = _profile_candidate_ids(player_candidates, "player_id", player_limit) if player_limit > 0 else []
    for player_id in player_ids:
        if int(request_budget) > 0 and client.request_count >= int(request_budget):
            break
        source_url = _source_url_for_api(args.api_base_url, "/player", {"id": player_id, "timespan": "all"})
        profile = client.fetch_player(player_id, timespan="all")
        if profile:
            profile_df = _player_profile_frame_from_api(
                player_id,
                profile,
                fetched_at=fetched_at,
                source_url=source_url,
                cache_hit=client.last_cache_hit,
            )
            _write_stage_frame(args, f"player_profile_{player_id}", profile_df)
            player_profiles += int(len(profile_df))
        if int(request_budget) > 0 and client.request_count >= int(request_budget):
            break
        match_url = _source_url_for_api(args.api_base_url, "/player/matches", {"id": player_id, "page": 1})
        matches = client.fetch_player_matches(player_id, page=1) or []
        match_df = _profile_match_rows_from_api(
            matches,
            source_url=match_url,
            fetched_at=fetched_at,
            cache_hit=client.last_cache_hit,
            source="vlrgg_api_player_matches",
        )
        if not match_df.empty:
            _write_stage_frame(args, f"api_profile_match_rows_player_{player_id}", match_df)
            player_match_rows += int(len(match_df))

    return {
        "rows": int(team_profiles + team_transactions + team_match_rows + player_profiles + player_match_rows),
        "network_requests": int(client.request_count),
        "team_profiles": int(team_profiles),
        "team_transactions": int(team_transactions),
        "team_match_rows": int(team_match_rows),
        "player_profiles": int(player_profiles),
        "player_match_rows": int(player_match_rows),
    }


def _player_lookup_from_candidates(player_candidates: pd.DataFrame) -> dict[str, str]:
    lookup: dict[str, str] = {}
    if player_candidates.empty:
        return lookup
    for _, row in player_candidates.iterrows():
        player_id = _clean_id(row.get("player_id"))
        if not player_id or player_id in lookup:
            continue
        lookup[player_id] = normalize_player(_clean_text(row.get("player")))
    return lookup


def _client_call_with_request_context(client: VLRGGClient, fn: Callable[[], Any]) -> Any:
    try:
        return fn()
    except VLRGGRateLimitError as exc:
        exc.requests_made = max(int(getattr(exc, "requests_made", 1) or 1), int(client.request_count))
        raise


def expand_player_profiles_to_stage(
    args: argparse.Namespace,
    player_candidates: pd.DataFrame,
    fetched_at: str,
    request_budget: int,
) -> dict[str, Any]:
    client = VLRGGClient(
        rate_limit_per_second=args.rate_limit,
        cache_dir=str(args.cache_dir),
        base_url=args.api_base_url,
        cache_only=not bool(getattr(args, "api_available", False)),
        api_version=DEFAULT_API_VERSION,
    )
    timespans = list(getattr(args, "player_profile_timespans", None) or ["all"])
    match_pages = max(0, int(getattr(args, "player_match_pages", 1) or 0))
    player_lookup = _player_lookup_from_candidates(player_candidates)
    player_profiles = 0
    agent_usage_rows = 0
    recent_match_rows = 0
    players_considered = 0
    stopped_reason = "completed"

    for player_id in _profile_candidate_ids(
        player_candidates,
        "player_id",
        int(getattr(args, "player_limit", DEFAULT_PLAYER_LIMIT) or 0),
    ):
        if int(request_budget) > 0 and client.request_count >= int(request_budget):
            stopped_reason = "max_requests_reached"
            break
        players_considered += 1
        best_profile: dict[str, Any] | None = None
        best_profile_url = ""
        best_cache_hit = False
        for timespan in timespans:
            if int(request_budget) > 0 and client.request_count >= int(request_budget):
                stopped_reason = "max_requests_reached"
                break
            source_url = _source_url_for_api(args.api_base_url, "/player", {"id": player_id, "timespan": timespan})
            profile = _client_call_with_request_context(
                client,
                lambda player_id=player_id, timespan=timespan: client.fetch_player(player_id, timespan=timespan),
            )
            if not profile:
                continue
            if best_profile is None or timespan == "all":
                best_profile = profile
                best_profile_url = source_url
                best_cache_hit = client.last_cache_hit
            usage_df = _player_agent_usage_frame_from_api(
                player_id,
                profile,
                timespan=timespan,
                fetched_at=fetched_at,
                source_url=source_url,
                cache_hit=client.last_cache_hit,
            )
            if not usage_df.empty:
                _write_stage_frame(args, f"player_agent_usage_{player_id}_{timespan}", usage_df)
                agent_usage_rows += int(len(usage_df))

        if best_profile:
            profile_df = _player_profile_frame_from_api(
                player_id,
                best_profile,
                fetched_at=fetched_at,
                source_url=best_profile_url,
                cache_hit=best_cache_hit,
            )
            if (
                player_lookup.get(player_id)
                and not _clean_text(profile_df.iloc[0].get("player"))
            ):
                profile_df.loc[:, "player"] = player_lookup[player_id]
            _write_stage_frame(args, f"player_profile_{player_id}", profile_df)
            player_profiles += int(len(profile_df))

        for page in range(1, match_pages + 1):
            if int(request_budget) > 0 and client.request_count >= int(request_budget):
                stopped_reason = "max_requests_reached"
                break
            match_url = _source_url_for_api(args.api_base_url, "/player/matches", {"id": player_id, "page": page})
            matches = _client_call_with_request_context(
                client,
                lambda player_id=player_id, page=page: client.fetch_player_matches(player_id, page=page),
            ) or []
            player_name = player_lookup.get(player_id, "")
            if best_profile:
                info = _as_dict(best_profile.get("info"))
                player_name = normalize_player(_first_clean(info.get("name"), best_profile.get("name"), player_name))
            match_df = _player_recent_matches_frame_from_api(
                player_id,
                player_name,
                matches,
                page=page,
                fetched_at=fetched_at,
                source_url=match_url,
                cache_hit=client.last_cache_hit,
            )
            if not match_df.empty:
                _write_stage_frame(args, f"player_recent_matches_{player_id}_page_{page}", match_df)
                recent_match_rows += int(len(match_df))
            if not matches:
                break

    return {
        "rows": int(player_profiles + agent_usage_rows + recent_match_rows),
        "network_requests": int(client.request_count),
        "players_considered": int(players_considered),
        "player_profiles": int(player_profiles),
        "player_agent_usage_rows": int(agent_usage_rows),
        "player_recent_match_rows": int(recent_match_rows),
        "timespans": timespans,
        "player_match_pages": int(match_pages),
        "stopped_reason": stopped_reason,
    }


def _provenance_valid_row_count(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    mask = pd.Series(True, index=df.index)
    for field in PROVENANCE_FIELDS:
        if field == "cache_hit":
            continue
        mask &= df[field].astype(str).str.strip().ne("")
    return int(mask.sum())


def _dedupe_player_profile_outputs(
    profiles_df: pd.DataFrame,
    usage_df: pd.DataFrame,
    recent_matches_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    profiles_df = _dedupe_frame(_ensure_columns(profiles_df, PLAYER_PROFILE_COLUMNS), ["player_id"])
    usage_df = _dedupe_frame(
        _ensure_columns(usage_df, PLAYER_AGENT_USAGE_COLUMNS),
        ["player_id", "timespan", "agent", "raw_json"],
    )
    recent_matches_df = _dedupe_frame(
        _ensure_columns(recent_matches_df, PLAYER_RECENT_MATCH_COLUMNS),
        ["player_id", "page", "match_id", "event", "date", "team_a", "team_b"],
    )
    for df in [profiles_df, usage_df, recent_matches_df]:
        if "player_id" in df.columns:
            df["player_id"] = df["player_id"].map(_clean_id).astype(object)
    if "match_id" in recent_matches_df.columns:
        recent_matches_df["match_id"] = recent_matches_df["match_id"].map(_clean_id).astype(object)
    return profiles_df, usage_df, recent_matches_df


def write_player_profile_outputs(
    args: argparse.Namespace,
    fetched_at: str,
    state: CollectionState | None,
    session_network_requests: int,
    stopped_reason: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    args.output.mkdir(parents=True, exist_ok=True)
    args.reports.mkdir(parents=True, exist_ok=True)
    profiles_df = _combine_stage_frames(args, "player_profile_", PLAYER_PROFILE_COLUMNS)
    usage_df = _combine_stage_frames(args, "player_agent_usage_", PLAYER_AGENT_USAGE_COLUMNS)
    recent_matches_df = _combine_stage_frames(args, "player_recent_matches_", PLAYER_RECENT_MATCH_COLUMNS)
    profiles_df, usage_df, recent_matches_df = _dedupe_player_profile_outputs(
        profiles_df,
        usage_df,
        recent_matches_df,
    )
    for name, df in [
        ("vlrgg_player_profiles", profiles_df),
        ("vlrgg_player_agent_usage", usage_df),
        ("vlrgg_player_recent_matches", recent_matches_df),
    ]:
        validate_provenance(df, name)
        df.to_csv(args.output / f"{name}.csv", index=False)

    summary = {
        "generated_at": fetched_at,
        "parser_version": PARSER_VERSION,
        "mode": "player_profile_plan",
        "api_base_url": args.api_base_url,
        "api_version": DEFAULT_API_VERSION,
        "cache_dir": str(args.cache_dir),
        "collection_state_file": str(getattr(args, "state_file", "")),
        "stage_output_dir": str(getattr(args, "stage_output_dir", "")),
        "output_dir": str(args.output),
        "reports_dir": str(args.reports),
        "player_profile_timespans": list(getattr(args, "player_profile_timespans", []) or []),
        "player_match_pages": int(getattr(args, "player_match_pages", 0) or 0),
        "player_limit": int(getattr(args, "player_limit", DEFAULT_PLAYER_LIMIT) or 0),
        "event_limit": int(getattr(args, "event_limit", DEFAULT_EVENT_LIMIT) or 0),
        "event_pages": int(getattr(args, "event_pages", 0) or 0),
        "network_requests": int(session_network_requests),
        "cumulative_network_requests": int(state.data.get("cumulative_requests", 0) or 0) if state is not None else int(session_network_requests),
        "stopped_reason": stopped_reason,
        "collection_stages": _stage_summary(state) if state is not None else {},
        "rate_limit": {
            "waited": bool(state and state.data.get("rate_limit_events", [])),
            "events": state.data.get("rate_limit_events", []) if state is not None else [],
            "wait_seconds_total": round(sum(float(row.get("wait_seconds", 0) or 0) for row in state.data.get("rate_limit_events", [])), 3) if state is not None else 0.0,
        },
        "rows": {
            "vlrgg_player_profiles": int(len(profiles_df)),
            "vlrgg_player_agent_usage": int(len(usage_df)),
            "vlrgg_player_recent_matches": int(len(recent_matches_df)),
        },
        "provenance_valid_rows": {
            "vlrgg_player_profiles": _provenance_valid_row_count(profiles_df),
            "vlrgg_player_agent_usage": _provenance_valid_row_count(usage_df),
            "vlrgg_player_recent_matches": _provenance_valid_row_count(recent_matches_df),
        },
    }
    _write_json_file(args.reports / "vlrgg_player_collection_summary.json", summary)
    return profiles_df, usage_df, recent_matches_df


def _player_profile_robots_conflicts(robots_policy: dict[str, Any]) -> list[str]:
    checks = _as_dict(robots_policy.get("allowed_path_checks"))
    conflicts = []
    for path in PLAYER_PROFILE_ROBOTS_PATHS:
        if checks.get(path) is False:
            conflicts.append(path)
    return conflicts


def run_player_profile_plan(args: argparse.Namespace) -> None:
    fetched_at = _utc_now()
    args.cache_dir = Path(args.cache_dir)
    args.output = Path(args.output)
    args.reports = Path(args.reports)
    args.state_file = Path(args.state_file)
    args.stage_output_dir = Path(args.stage_output_dir)
    args.api_base_url = args.api_base_url.rstrip("/")
    args.allow_direct_html = False

    state = CollectionState(args.state_file, reset=args.restart)
    requests_before = int(state.data.get("cumulative_requests", 0) or 0)
    stopped_reason = "completed"

    if int(args.max_requests_per_session) <= 0:
        state.mark_stage(
            "player_profile_network_skipped",
            "completed",
            cursor={"max_requests_per_session": int(args.max_requests_per_session)},
            rows=0,
            network_requests=0,
            skipped=True,
        )
        stopped_reason = "max_requests_reached"
        write_player_profile_outputs(args, fetched_at, state, 0, stopped_reason)
        print(f"VLR player profile plan skipped: stopped_reason={stopped_reason} state={args.state_file}")
        return

    robots_args = argparse.Namespace(**vars(args))
    robots_args.restart = True
    _reset_stage_attempts(state, "robots_txt")
    robots_result = _run_stage_with_resume(
        args=robots_args,
        state=state,
        name="robots_txt",
        cursor={"url": ROBOTS_URL, "mode": "player_profile_plan"},
        fn=fetch_robots_policy,
    )
    robots_policy = robots_result if robots_result.get("status") == "completed" else {}
    if "allowed_path_checks" not in robots_policy and "details" in robots_result:
        robots_policy = dict(robots_result.get("details") or {})
    if not robots_policy:
        stopped_reason = "robots_check_failed"
        session_requests = int(state.data.get("cumulative_requests", 0) or 0) - requests_before
        write_player_profile_outputs(args, fetched_at, state, session_requests, stopped_reason)
        print(f"VLR player profile plan stopped: stopped_reason={stopped_reason} state={args.state_file}")
        return

    conflicts = _player_profile_robots_conflicts(robots_policy)
    if conflicts:
        stopped_reason = "robots_policy_conflict"
        state.mark_stage(
            "player_profile_robots_policy",
            "degraded",
            cursor={"robots_url": ROBOTS_URL, "paths": conflicts},
            rows=0,
            network_requests=0,
            failure_reason=f"robots.txt disallows player profile source paths: {conflicts}",
        )
        session_requests = int(state.data.get("cumulative_requests", 0) or 0) - requests_before
        write_player_profile_outputs(args, fetched_at, state, session_requests, stopped_reason)
        print(
            "VLR player profile plan stopped: "
            f"stopped_reason={stopped_reason} conflicts={conflicts} state={args.state_file}"
        )
        return

    def _api_health_player_profile() -> dict[str, Any]:
        available, reason, requests_made = api_base_available(args.api_base_url)
        if not available:
            raise CollectionStageError(f"local vlrggapi unavailable: {reason}", requests_made=requests_made)
        return {"rows": 1, "network_requests": requests_made, "api_base_status": reason}

    api_result = _run_stage_with_resume(
        args=args,
        state=state,
        name="api_base_available",
        cursor={"api_base_url": args.api_base_url, "mode": "player_profile_plan"},
        fn=_api_health_player_profile,
    )
    args.api_available = api_result.get("status") == "completed"
    if not args.api_available:
        stopped_reason = "local_api_unavailable"
        session_requests = int(state.data.get("cumulative_requests", 0) or 0) - requests_before
        write_player_profile_outputs(args, fetched_at, state, session_requests, stopped_reason)
        print(f"VLR player profile plan stopped: stopped_reason={stopped_reason} state={args.state_file}")
        return

    remaining_budget = max(
        0,
        int(args.max_requests_per_session)
        - (int(state.data.get("cumulative_requests", 0) or 0) - requests_before),
    )
    if remaining_budget <= 0:
        stopped_reason = "max_requests_reached"
        write_player_profile_outputs(args, fetched_at, state, int(args.max_requests_per_session), stopped_reason)
        print(f"VLR player profile plan stopped: stopped_reason={stopped_reason} state={args.state_file}")
        return

    _run_stage_with_resume(
        args=args,
        state=state,
        name="player_profile_event_candidates",
        cursor={"path": "/v2/events", "q": "completed", "limit": int(args.event_limit)},
        fn=lambda: fetch_event_candidates_to_stage(args, int(args.event_limit), fetched_at),
    )

    event_candidates_df = _combine_stage_frames(
        args,
        "expanded_event_candidates",
        ["event_id", "event", "url_path", *PROVENANCE_FIELDS],
    )
    remaining_budget = max(
        0,
        int(args.max_requests_per_session)
        - (int(state.data.get("cumulative_requests", 0) or 0) - requests_before),
    )
    if remaining_budget <= 0:
        stopped_reason = "max_requests_reached"
    elif event_candidates_df.empty:
        stopped_reason = "no_event_candidates"
    else:
        _run_stage_with_resume(
            args=args,
            state=state,
            name="player_profile_event_details",
            cursor={
                "path": "/v2/event/{event_id}",
                "event_limit": int(args.event_limit),
                "request_budget": remaining_budget,
            },
            fn=lambda: expand_api_event_details_to_stage(args, event_candidates_df, fetched_at, remaining_budget),
        )

    player_candidates_df = _combine_stage_frames(args, "event_player_candidates_", PLAYER_CANDIDATE_COLUMNS)
    remaining_budget = max(
        0,
        int(args.max_requests_per_session)
        - (int(state.data.get("cumulative_requests", 0) or 0) - requests_before),
    )
    profile_result: dict[str, Any] = {}
    if stopped_reason == "completed" and remaining_budget <= 0:
        stopped_reason = "max_requests_reached"
    elif stopped_reason == "completed" and player_candidates_df.empty:
        stopped_reason = "no_player_candidates"
    elif stopped_reason == "completed":
        profile_result = _run_stage_with_resume(
            args=args,
            state=state,
            name="player_profile_expansion",
            cursor={
                "paths": ["/v2/player", "/v2/player/matches"],
                "player_limit": int(args.player_limit),
                "timespans": list(args.player_profile_timespans),
                "player_match_pages": int(args.player_match_pages),
                "request_budget": remaining_budget,
            },
            fn=lambda: expand_player_profiles_to_stage(args, player_candidates_df, fetched_at, remaining_budget),
        )
        stopped_reason = _clean_text(profile_result.get("stopped_reason")) or stopped_reason
        if "details" in profile_result and isinstance(profile_result["details"], dict):
            stopped_reason = _clean_text(profile_result["details"].get("stopped_reason")) or stopped_reason

    session_requests = int(state.data.get("cumulative_requests", 0) or 0) - requests_before
    profiles_df, usage_df, recent_matches_df = write_player_profile_outputs(
        args,
        fetched_at,
        state,
        session_requests,
        stopped_reason,
    )
    print(
        "VLR player profile plan complete: "
        f"profiles={len(profiles_df)} agent_usage={len(usage_df)} "
        f"recent_matches={len(recent_matches_df)} network_requests={session_requests} "
        f"stopped_reason={stopped_reason} state={args.state_file}"
    )


def load_kaggle_proxy(proxy_dir: Path, fetched_at: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    results_path = proxy_dir / "results.csv"
    stats_path = proxy_dir / "stats.csv"
    match_rows: list[dict[str, Any]] = []
    player_rows: list[dict[str, Any]] = []

    results = _read_csv(results_path)
    for _, row in results.iterrows():
        url_path = str(row.get("match_page", "") or "")
        source_url = f"https://www.vlr.gg{url_path}" if url_path.startswith("/") else f"kaggle://{results_path}"
        match_id = ""
        if url_path.startswith("/"):
            parts = [part for part in url_path.split("/") if part]
            match_id = parts[0] if parts else ""
        score_a = _int_or_none(row.get("score1"))
        score_b = _int_or_none(row.get("score2"))
        match_rows.append(_with_provenance({
            "match_id": match_id,
            "event": str(row.get("tournament_name", "") or ""),
            "date": str(row.get("time_completed", "") or ""),
            "round_info": str(row.get("round_info", "") or ""),
            "team_a": normalize_team(str(row.get("team1", "") or "")),
            "team_b": normalize_team(str(row.get("team2", "") or "")),
            "score_a": score_a,
            "score_b": score_b,
            "label": 1 if score_a is not None and score_b is not None and score_a > score_b else (
                0 if score_a is not None and score_b is not None and score_a < score_b else None
            ),
            "map": "",
        }, source="vlrgg_kaggle_proxy", source_url=source_url,
            method="kaggle_cache", fetched_at=fetched_at, cache_hit=True))

    stats = _read_csv(stats_path)
    for _, row in stats.iterrows():
        agent = normalize_agent(str(row.get("agent", "") or "")) or str(row.get("agent", "") or "").strip()
        player_rows.append(_with_provenance({
            "player": str(row.get("player", "") or ""),
            "org": str(row.get("org", "") or ""),
            "region": str(row.get("region", "") or ""),
            "agent": agent,
            "rounds_played": _int_or_none(row.get("rds")),
            "rating": None,
            "average_combat_score": _num(row.get("average_combat_score")),
            "kill_deaths": _num(row.get("kill_deaths")),
            "average_damage_per_round": _num(row.get("average_damage_per_round")),
            "kills_per_round": _num(row.get("kills_per_round")),
            "assists_per_round": _num(row.get("assists_per_round")),
            "first_kills_per_round": _num(row.get("first_kills_per_round")),
            "first_deaths_per_round": _num(row.get("first_deaths_per_round")),
            "headshot_percentage": _pct_to_float(row.get("headshot_percentage")),
            "clutch_success_percentage": _pct_to_float(row.get("clutch_success_percentage")),
            "map_key": f"vlr_map_id_{row.get('map_id')}" if "map_id" in row else "",
        }, source="vlrgg_kaggle_proxy", source_url=f"kaggle://{stats_path}",
            method="kaggle_cache", fetched_at=fetched_at, cache_hit=True))

    return pd.DataFrame(match_rows), pd.DataFrame(player_rows)


def _iter_api_cache(cache_dir: Path) -> list[tuple[Path, dict[str, Any]]]:
    rows = []
    if not cache_dir.exists():
        return rows
    for path in sorted(cache_dir.glob("*.json")):
        try:
            rows.append((path, json.loads(path.read_text(encoding="utf-8"))))
        except Exception:
            continue
    return rows


def _normalized_cache_stem(stem: str) -> str:
    return re.sub(r"^_v2_", "_", stem)


def load_api_cache(cache_dir: Path, base_url: str, fetched_at: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    match_rows: list[dict[str, Any]] = []
    player_rows: list[dict[str, Any]] = []
    for path, raw in _iter_api_cache(cache_dir):
        segments = VLRGGClient.extract_segments(raw) or []
        name = _normalized_cache_stem(path.stem)
        if name.startswith("_stats_"):
            region = ""
            timespan = ""
            m_region = name.split("_region_", 1)
            if len(m_region) == 2:
                region = m_region[1].split("_timespan_", 1)[0]
            m_timespan = name.split("_timespan_", 1)
            if len(m_timespan) == 2:
                timespan = m_timespan[1]
            source_url = _source_url_for_api(base_url, "/stats", {"region": region, "timespan": timespan})
            for row in segments:
                agents = row.get("agents") if isinstance(row, dict) else []
                if not isinstance(agents, list):
                    agents = [agents]
                if not agents:
                    agents = [""]
                for agent_raw in agents:
                    agent = normalize_agent(str(agent_raw)) or str(agent_raw or "").strip()
                    player_rows.append(_with_provenance({
                        "player": str(row.get("player", "") or ""),
                        "org": str(row.get("org", "") or ""),
                        "region": region,
                        "timespan": timespan,
                        "agent": agent,
                        "rounds_played": _int_or_none(row.get("rounds_played")),
                        "rating": _num(row.get("rating")),
                        "average_combat_score": _num(row.get("average_combat_score")),
                        "kill_deaths": _num(row.get("kill_deaths")),
                        "average_damage_per_round": _num(row.get("average_damage_per_round")),
                        "kills_per_round": _num(row.get("kills_per_round")),
                        "assists_per_round": _num(row.get("assists_per_round")),
                        "first_kills_per_round": _num(row.get("first_kills_per_round")),
                        "first_deaths_per_round": _num(row.get("first_deaths_per_round")),
                        "headshot_percentage": _pct_to_float(row.get("headshot_percentage")),
                        "clutch_success_percentage": _pct_to_float(row.get("clutch_success_percentage")),
                        "map_key": "",
                    }, source="vlrgg_api", source_url=source_url,
                        method="api_cache", fetched_at=fetched_at, cache_hit=True))
        elif name.startswith("_match_") or name.startswith("_events_"):
            source_url = f"cache://{path}"
            for row in segments:
                if not isinstance(row, dict):
                    continue
                url_path = str(row.get("url_path", row.get("match_page", "")) or "")
                match_id = _extract_match_id_from_row(row)
                if name.startswith("_events_") and not match_id:
                    continue
                score_a = _int_or_none(row.get("score_a", row.get("score1")))
                score_b = _int_or_none(row.get("score_b", row.get("score2")))
                match_rows.append(_with_provenance({
                    "match_id": match_id,
                    "event": str(row.get("event", row.get("match_event", row.get("tournament_name", row.get("title", "")))) or ""),
                    "date": str(row.get("date", row.get("unix_timestamp", row.get("time_completed", row.get("dates", "")))) or ""),
                    "round_info": str(row.get("round_info", row.get("match_series", row.get("status", ""))) or ""),
                    "team_a": normalize_team(str(row.get("team_a", row.get("team1", "")) or "")),
                    "team_b": normalize_team(str(row.get("team_b", row.get("team2", "")) or "")),
                    "score_a": score_a,
                    "score_b": score_b,
                    "label": 1 if score_a is not None and score_b is not None and score_a > score_b else (
                        0 if score_a is not None and score_b is not None and score_a < score_b else None
                    ),
                    "map": str(row.get("map", "") or ""),
                }, source="vlrgg_api", source_url=url_path or source_url,
                    method="api_cache", fetched_at=fetched_at, cache_hit=True))
    return pd.DataFrame(match_rows), pd.DataFrame(player_rows)


def fetch_api(args: argparse.Namespace, fetched_at: str) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    client = VLRGGClient(
        rate_limit_per_second=args.rate_limit,
        cache_dir=str(args.cache_dir),
        base_url=args.api_base_url,
        cache_only=False,
        api_version=DEFAULT_API_VERSION,
    )
    player_rows: list[dict[str, Any]] = []
    match_rows: list[dict[str, Any]] = []

    for region in args.regions:
        stats = client.fetch_stats(region, args.timespan) or []
        source_url = _source_url_for_api(args.api_base_url, "/stats", {"region": region, "timespan": args.timespan})
        for row in stats:
            agents = row.get("agents") if isinstance(row, dict) else []
            if not isinstance(agents, list):
                agents = [agents]
            if not agents:
                agents = [""]
            for agent_raw in agents:
                agent = normalize_agent(str(agent_raw)) or str(agent_raw or "").strip()
                player_rows.append(_with_provenance({
                    "player": str(row.get("player", "") or ""),
                    "org": str(row.get("org", "") or ""),
                    "region": region,
                    "timespan": args.timespan,
                    "agent": agent,
                    "rounds_played": _int_or_none(row.get("rounds_played")),
                    "rating": _num(row.get("rating")),
                    "average_combat_score": _num(row.get("average_combat_score")),
                    "kill_deaths": _num(row.get("kill_deaths")),
                    "average_damage_per_round": _num(row.get("average_damage_per_round")),
                    "kills_per_round": _num(row.get("kills_per_round")),
                    "assists_per_round": _num(row.get("assists_per_round")),
                    "first_kills_per_round": _num(row.get("first_kills_per_round")),
                    "first_deaths_per_round": _num(row.get("first_deaths_per_round")),
                    "headshot_percentage": _pct_to_float(row.get("headshot_percentage")),
                    "clutch_success_percentage": _pct_to_float(row.get("clutch_success_percentage")),
                    "map_key": "",
                }, source="vlrgg_api", source_url=source_url,
                    method="api", fetched_at=fetched_at, cache_hit=client.last_cache_hit))

    for page in range(1, args.pages + 1):
        events = client.fetch_events("completed", page=page) or []
        source_url = _source_url_for_api(args.api_base_url, "/events", {"q": "completed", "page": page})
        for row in events:
            if not isinstance(row, dict):
                continue
            match_rows.append(_with_provenance({
                "match_id": "",
                "event": str(row.get("title", "") or ""),
                "date": str(row.get("dates", "") or ""),
                "round_info": str(row.get("status", "") or ""),
                "team_a": "",
                "team_b": "",
                "score_a": None,
                "score_b": None,
                "label": None,
                "map": "",
            }, source="vlrgg_api", source_url=str(row.get("url_path", "") or source_url),
                method="api", fetched_at=fetched_at, cache_hit=client.last_cache_hit))

    match_params = _api_match_params(args, "results", args.pages)
    matches = client.fetch_match(
        "results",
        num_pages=args.pages,
        from_page=match_params.get("from_page"),
        to_page=match_params.get("to_page"),
    ) or []
    match_source_url = _source_url_for_api(args.api_base_url, "/match", match_params)
    for row in matches:
        if not isinstance(row, dict):
            continue
        url_path = str(row.get("url_path", row.get("match_page", "")) or "")
        score_a = _int_or_none(row.get("score_a", row.get("score1")))
        score_b = _int_or_none(row.get("score_b", row.get("score2")))
        match_rows.append(_with_provenance({
            "match_id": _extract_match_id_from_row(row),
            "event": str(row.get("event", row.get("tournament_name", row.get("tournament", ""))) or ""),
            "date": str(row.get("date", row.get("time_completed", "")) or ""),
            "round_info": str(row.get("round_info", row.get("status", "")) or ""),
            "team_a": normalize_team(str(row.get("team_a", row.get("team1", "")) or "")),
            "team_b": normalize_team(str(row.get("team_b", row.get("team2", "")) or "")),
            "score_a": score_a,
            "score_b": score_b,
            "label": 1 if score_a is not None and score_b is not None and score_a > score_b else (
                0 if score_a is not None and score_b is not None and score_a < score_b else None
            ),
            "map": str(row.get("map", "") or ""),
        }, source="vlrgg_api",
            source_url=f"https://www.vlr.gg{url_path}" if url_path.startswith("/") else (url_path or match_source_url),
            method="api", fetched_at=fetched_at, cache_hit=client.last_cache_hit))

    return pd.DataFrame(match_rows), pd.DataFrame(player_rows), client.request_count


def fetch_direct_html(args: argparse.Namespace, fetched_at: str) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    if not args.allow_direct_html:
        raise ValueError("direct HTML fetch requires --allow-direct-html")
    if args.pages > MAX_DIRECT_HTML_PAGES:
        raise ValueError(f"direct HTML fetch is capped at {MAX_DIRECT_HTML_PAGES} pages per run")
    from ml.vlrgg_scraper import scrape_recent_results

    match_rows: list[dict[str, Any]] = []
    pages_requested = 0
    remaining = args.limit or DEFAULT_DIRECT_HTML_LIMIT
    direct_delay = max(1.0, 1.0 / max(float(args.rate_limit), 1e-6))
    for page in range(1, args.pages + 1):
        rows = scrape_recent_results(page=page, delay=direct_delay)
        pages_requested += 1
        if remaining > 0:
            rows = rows[:remaining]
            remaining -= len(rows)
        for row in rows:
            url_path = str(row.get("url_path", "") or "")
            score_a = _int_or_none(row.get("score_a"))
            score_b = _int_or_none(row.get("score_b"))
            match_rows.append(_with_provenance({
                "match_id": str(row.get("match_id", "") or ""),
                "event": str(row.get("event", "") or ""),
                "date": str(row.get("date", "") or ""),
                "round_info": str(row.get("status", "") or ""),
                "team_a": normalize_team(str(row.get("team_a", "") or "")),
                "team_b": normalize_team(str(row.get("team_b", "") or "")),
                "score_a": score_a,
                "score_b": score_b,
                "label": 1 if score_a is not None and score_b is not None and score_a > score_b else (
                    0 if score_a is not None and score_b is not None and score_a < score_b else None
                ),
                "map": "",
            }, source="vlrgg_direct_html",
                source_url=f"https://www.vlr.gg{url_path}" if url_path.startswith("/") else "https://www.vlr.gg/matches/results",
                method="direct_html", fetched_at=fetched_at, cache_hit=False))
        if remaining <= 0:
            break
    return pd.DataFrame(match_rows), pd.DataFrame(), pages_requested


def _robots_allows(text: str, path: str) -> bool:
    parser = RobotFileParser()
    parser.set_url(ROBOTS_URL)
    parser.parse(text.splitlines())
    return bool(parser.can_fetch("*", f"https://www.vlr.gg{path}"))


def fetch_robots_policy() -> dict[str, Any]:
    headers = {"User-Agent": "ValoPredicML/1.0 (academic research; non-commercial)"}
    resp = requests.get(ROBOTS_URL, headers=headers, timeout=15)
    raise_for_limit_like_response(
        url=ROBOTS_URL,
        status_code=resp.status_code,
        headers=resp.headers,
        body=resp.text,
    )
    resp.raise_for_status()
    text = resp.text
    return {
        "network_requests": 1,
        "rows": 1,
        "robots_checked_at": _utc_now(),
        "robots_url": ROBOTS_URL,
        "direct_html_allowed_live": all(_robots_allows(text, path) for path in DIRECT_HTML_ALLOWED_PATHS),
        "event_intel_direct_html_allowed_live": all(
            _robots_allows(text, path) for path in ["/event/stats/", "/event/agents/"]
        ),
        "team_profile_direct_html_allowed_live": all(
            _robots_allows(text, path) for path in ["/team/", "/team/stats/", "/team/transactions/"]
        ),
        "allowed_path_checks": {
            path: _robots_allows(text, path)
            for path in ROBOTS_ALLOWED_PATHS
        },
        "blocked_path_checks": {
            path: not _robots_allows(text, path)
            for path in ROBOTS_BLOCKED_PATHS
        },
        "content_sha1": hashlib.sha1(text.encode("utf-8", errors="replace")).hexdigest(),
    }


def api_base_available(api_base_url: str) -> tuple[bool, str, int]:
    url = api_base_url.rstrip("/")
    try:
        resp = requests.get(url, timeout=3)
    except requests.exceptions.ConnectionError as exc:
        return False, f"connection_error: {exc}", 0
    except requests.exceptions.Timeout:
        return False, "timeout", 1
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}", 0
    return resp.status_code < 500, f"status={resp.status_code}", 1


def fetch_api_stats_to_cache(args: argparse.Namespace, region: str, timespan: str) -> dict[str, Any]:
    client = VLRGGClient(
        rate_limit_per_second=args.rate_limit,
        cache_dir=str(args.cache_dir),
        base_url=args.api_base_url,
        cache_only=False,
        api_version=DEFAULT_API_VERSION,
    )
    rows = client.fetch_stats(region, timespan)
    if rows is None:
        raise CollectionStageError(f"/stats returned no data for region={region} timespan={timespan}")
    return {"rows": int(len(rows)), "network_requests": client.request_count}


def fetch_api_events_to_cache(args: argparse.Namespace, q: str, page: int) -> dict[str, Any]:
    client = VLRGGClient(
        rate_limit_per_second=args.rate_limit,
        cache_dir=str(args.cache_dir),
        base_url=args.api_base_url,
        cache_only=False,
        api_version=DEFAULT_API_VERSION,
    )
    rows = client.fetch_events(q=q, page=page)
    if rows is None:
        raise CollectionStageError(f"/events returned no data for q={q} page={page}")
    return {"rows": int(len(rows)), "network_requests": client.request_count}


def _api_match_params(args: argparse.Namespace, q: str, pages: int) -> dict[str, Any]:
    params: dict[str, Any] = {"q": q, "num_pages": pages}
    from_page = int(getattr(args, "api_from_page", 0) or 0)
    to_page = int(getattr(args, "api_to_page", 0) or 0)
    if from_page > 0:
        params["from_page"] = from_page
    if to_page > 0:
        params["to_page"] = to_page
    return params


def _api_match_window_size(args: argparse.Namespace) -> int:
    raw_size = int(getattr(args, "api_match_window_size", DEFAULT_API_MATCH_WINDOW_SIZE) or DEFAULT_API_MATCH_WINDOW_SIZE)
    return max(1, min(DEFAULT_API_MATCH_WINDOW_SIZE, raw_size))


def _api_match_request_windows(args: argparse.Namespace, q: str, pages: int) -> list[dict[str, Any]]:
    if q == "live_score":
        return [{"q": q, "num_pages": 1}]

    requested_pages = max(1, int(pages or 1))
    from_page = int(getattr(args, "api_from_page", 0) or 0)
    to_page = int(getattr(args, "api_to_page", 0) or 0)
    start_page = max(1, from_page or 1)
    end_page = max(start_page, to_page if to_page > 0 else start_page + requested_pages - 1)
    window_size = _api_match_window_size(args)

    windows: list[dict[str, Any]] = []
    for window_start in range(start_page, end_page + 1, window_size):
        window_end = min(window_start + window_size - 1, end_page)
        windows.append({
            "q": q,
            "num_pages": window_end - window_start + 1,
            "from_page": window_start,
            "to_page": window_end,
        })
    return windows


def fetch_api_match_to_cache(args: argparse.Namespace, q: str, pages: int) -> dict[str, Any]:
    client = VLRGGClient(
        rate_limit_per_second=args.rate_limit,
        cache_dir=str(args.cache_dir),
        base_url=args.api_base_url,
        cache_only=False,
        api_version=DEFAULT_API_VERSION,
    )
    total_rows = 0
    windows = _api_match_request_windows(args, q, pages)
    for params in windows:
        rows = client.fetch_match(
            q=q,
            num_pages=int(params["num_pages"]),
            from_page=params.get("from_page"),
            to_page=params.get("to_page"),
        )
        if rows is None:
            raise CollectionStageError(f"/match returned no data for params={params}")
        total_rows += int(len(rows))
    return {"rows": total_rows, "network_requests": client.request_count, "windows": windows}


def _api_match_stage_cursor(args: argparse.Namespace, q: str, pages: int) -> dict[str, Any]:
    windows = _api_match_request_windows(args, q, pages)
    return {
        "path": "/v2/match",
        "q": q,
        "requested_pages": max(1, int(pages or 1)),
        "window_size": _api_match_window_size(args),
        "window_count": len(windows),
        "windows": windows,
    }


def _has_discovery_budget(client: VLRGGClient, request_budget: int) -> bool:
    return int(request_budget) <= 0 or client.request_count < int(request_budget)


def fetch_api_exhaustive_to_stage(args: argparse.Namespace, fetched_at: str, request_budget: int) -> dict[str, Any]:
    """Fetch every public vlrggapi discovery endpoint into cache-backed stage files."""
    client = VLRGGClient(
        rate_limit_per_second=args.rate_limit,
        cache_dir=str(args.cache_dir),
        base_url=args.api_base_url,
        cache_only=not bool(getattr(args, "api_available", False)),
        api_version=DEFAULT_API_VERSION,
    )
    coverage: list[dict[str, Any]] = []
    match_rows: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    stats_rows: list[dict[str, Any]] = []
    ranking_rows: list[dict[str, Any]] = []
    team_rows: list[dict[str, Any]] = []
    news_rows: list[dict[str, Any]] = []

    def _record(endpoint: str, params: dict[str, Any] | None, rows: int, before: int, status: str = "ok", error: str = "") -> None:
        source_url = _source_url_for_api(args.api_base_url, endpoint, params or {})
        coverage.append(_api_coverage_row(
            endpoint=f"/{DEFAULT_API_VERSION}{endpoint}",
            params=params,
            rows=rows,
            network_requests=client.request_count - before,
            cache_hit=client.last_cache_hit,
            status=status,
            source_url=source_url,
            error=error,
        ))

    if _has_discovery_budget(client, request_budget):
        before = client.request_count
        try:
            health = client.fetch_health()
            rows = 1 if health else 0
            _record("/health", None, rows, before, status="ok" if health else "empty")
        except Exception as exc:
            _record("/health", None, 0, before, status="error", error=f"{type(exc).__name__}: {exc}")

    for q in EVENT_QUERIES:
        max_pages = int(getattr(args, "event_pages", 0) or 0)
        page = 1
        while _has_discovery_budget(client, request_budget):
            if max_pages > 0 and page > max_pages:
                break
            params = {"q": q, "page": page}
            before = client.request_count
            try:
                rows = client.fetch_events(q=q, page=page)
            except Exception as exc:
                _record("/events", params, 0, before, status="error", error=f"{type(exc).__name__}: {exc}")
                break
            if rows is None:
                _record("/events", params, 0, before, status="empty")
                break
            source_url = _source_url_for_api(args.api_base_url, "/events", params)
            event_rows.extend(_event_rows_from_api(rows, q=q, source_url=source_url, fetched_at=fetched_at, cache_hit=client.last_cache_hit))
            _record("/events", params, len(rows), before)
            if not rows or max_pages == 0 and len(rows) == 0:
                break
            if max_pages == 0 and len(rows) == 0:
                break
            if max_pages == 0 and len(rows) < 1:
                break
            page += 1
            if max_pages == 0 and page > 500:
                _record("/events", {"q": q, "page": page}, 0, client.request_count, status="stopped", error="page safety cap reached")
                break

    for q in MATCH_QUERIES:
        pages = max(1, int(getattr(args, "api_pages", 1) or 1))
        for params in _api_match_request_windows(args, q, pages):
            if not _has_discovery_budget(client, request_budget):
                break
            before = client.request_count
            try:
                rows = client.fetch_match(
                    q=q,
                    num_pages=int(params["num_pages"]),
                    from_page=params.get("from_page"),
                    to_page=params.get("to_page"),
                )
            except Exception as exc:
                _record("/match", params, 0, before, status="error", error=f"{type(exc).__name__}: {exc}")
                continue
            if rows is None:
                _record("/match", params, 0, before, status="empty")
                continue
            source_url = _source_url_for_api(args.api_base_url, "/match", params)
            match_rows.extend(_match_rows_from_api(rows, q=q, source_url=source_url, fetched_at=fetched_at, cache_hit=client.last_cache_hit))
            _record("/match", params, len(rows), before)

    for region in REGIONS:
        for timespan in TIMESPANS:
            if not _has_discovery_budget(client, request_budget):
                break
            params = {"region": region, "timespan": timespan}
            before = client.request_count
            try:
                rows = client.fetch_stats(region, timespan)
            except Exception as exc:
                _record("/stats", params, 0, before, status="error", error=f"{type(exc).__name__}: {exc}")
                continue
            if rows is None:
                _record("/stats", params, 0, before, status="empty")
                continue
            source_url = _source_url_for_api(args.api_base_url, "/stats", params)
            stats_rows.extend(_stats_rows_from_api(rows, region=region, timespan=timespan, source_url=source_url, fetched_at=fetched_at, cache_hit=client.last_cache_hit))
            _record("/stats", params, len(rows), before)

    for region in REGIONS:
        if not _has_discovery_budget(client, request_budget):
            break
        params = {"region": region}
        before = client.request_count
        try:
            rows = client.fetch_rankings(region)
        except Exception as exc:
            _record("/rankings", params, 0, before, status="error", error=f"{type(exc).__name__}: {exc}")
            continue
        if rows is None:
            _record("/rankings", params, 0, before, status="empty")
            continue
        source_url = _source_url_for_api(args.api_base_url, "/rankings", params)
        rankings, teams = _ranking_rows_from_api(rows, region=region, source_url=source_url, fetched_at=fetched_at, cache_hit=client.last_cache_hit)
        ranking_rows.extend(rankings)
        team_rows.extend(teams)
        _record("/rankings", params, len(rows), before)

    if _has_discovery_budget(client, request_budget):
        before = client.request_count
        try:
            rows = client.fetch_news()
        except Exception as exc:
            _record("/news", None, 0, before, status="error", error=f"{type(exc).__name__}: {exc}")
        else:
            if rows is None:
                _record("/news", None, 0, before, status="empty")
            else:
                source_url = _source_url_for_api(args.api_base_url, "/news", {})
                news_rows.extend(_news_rows_from_api(rows, source_url=source_url, fetched_at=fetched_at, cache_hit=client.last_cache_hit))
                _record("/news", None, len(rows), before)

    _write_stage_frame(args, "api_exhaustive_match_rows", _ensure_columns(pd.DataFrame(match_rows), API_MATCH_COLUMNS))
    _write_stage_frame(args, "api_event_candidates", _ensure_columns(pd.DataFrame(event_rows), EVENT_CANDIDATE_COLUMNS))
    _write_stage_frame(args, "api_team_candidates", _ensure_columns(pd.DataFrame(team_rows), TEAM_CANDIDATE_COLUMNS))
    _write_stage_frame(args, "api_stats_rows", _ensure_columns(pd.DataFrame(stats_rows), API_STATS_COLUMNS))
    _write_stage_frame(args, "api_rankings_rows", _ensure_columns(pd.DataFrame(ranking_rows), API_RANKING_COLUMNS))
    _write_stage_frame(args, "api_news_rows", _ensure_columns(pd.DataFrame(news_rows), API_NEWS_COLUMNS))
    _write_json_file(Path(args.reports) / "vlrgg_api_coverage.json", {
        "generated_at": fetched_at,
        "parser_version": PARSER_VERSION,
        "api_base_url": args.api_base_url,
        "api_version": DEFAULT_API_VERSION,
        "request_budget": int(request_budget),
        "network_requests": int(client.request_count),
        "coverage": coverage,
        "rows": {
            "match_candidates": int(len(match_rows)),
            "event_candidates": int(len(event_rows)),
            "team_candidates": int(len(team_rows)),
            "stats": int(len(stats_rows)),
            "rankings": int(len(ranking_rows)),
            "news": int(len(news_rows)),
        },
    })
    return {
        "rows": int(len(match_rows) + len(event_rows) + len(team_rows) + len(stats_rows) + len(ranking_rows) + len(news_rows)),
        "network_requests": int(client.request_count),
        "match_rows": int(len(match_rows)),
        "event_rows": int(len(event_rows)),
        "team_rows": int(len(team_rows)),
        "stats_rows": int(len(stats_rows)),
        "ranking_rows": int(len(ranking_rows)),
        "news_rows": int(len(news_rows)),
    }


def _dedupe_outputs(match_df: pd.DataFrame, player_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not match_df.empty:
        subset = [
            col for col in ["source", "source_url", "match_id", "event", "date", "team_a", "team_b", "score_a", "score_b"]
            if col in match_df.columns
        ]
        if subset:
            match_df = match_df.drop_duplicates(subset=subset, keep="last").reset_index(drop=True)
    if not player_df.empty:
        subset = [
            col for col in ["source", "source_url", "player", "org", "region", "timespan", "agent", "rounds_played"]
            if col in player_df.columns
        ]
        if subset:
            player_df = player_df.drop_duplicates(subset=subset, keep="last").reset_index(drop=True)
    return match_df, player_df


def run_collection_plan(args: argparse.Namespace) -> None:
    fetched_at = _utc_now()
    args.cache_dir = Path(args.cache_dir)
    args.output = Path(args.output)
    args.reports = Path(args.reports)
    args.state_file = Path(args.state_file)
    args.stage_output_dir = Path(args.stage_output_dir)
    args.api_base_url = args.api_base_url.rstrip("/")
    args.allow_direct_html = True

    state = CollectionState(args.state_file, reset=args.restart)

    robots_result = _run_stage_with_resume(
        args=args,
        state=state,
        name="robots_txt",
        cursor={"url": ROBOTS_URL},
        fn=fetch_robots_policy,
    )
    robots_policy = robots_result if robots_result.get("status") == "completed" else {}
    if "direct_html_allowed_live" not in robots_policy and "details" in robots_result:
        robots_policy = dict(robots_result.get("details") or {})
    if not robots_policy:
        robots_policy = dict(state.stage("robots_txt").get("details") or {})
    args.robots_policy = robots_policy
    if (
        state.stage("direct_html_page_1").get("status") == "completed"
        and not _stage_output_path(args, "direct_html_page_1").exists()
        and not args.restart
    ):
        state.mark_stage(
            "direct_html_page_1",
            "degraded",
            failure_reason="completed state existed without a direct HTML stage output file",
        )

    def _direct_page() -> dict[str, Any]:
        if robots_policy and robots_policy.get("direct_html_allowed_live") is False:
            raise CollectionStageError("robots.txt does not allow /matches/results direct HTML collection")
        direct_args = argparse.Namespace(**vars(args))
        direct_args.pages = min(int(args.direct_pages), MAX_DIRECT_HTML_PAGES)
        direct_args.limit = int(args.direct_limit)
        direct_matches, _, requests_made = fetch_direct_html(direct_args, fetched_at)
        if direct_matches.empty:
            raise CollectionStageError("direct HTML returned 0 match rows", requests_made=requests_made)
        _write_stage_frame(args, "direct_html_page_1", direct_matches)
        return {"rows": int(len(direct_matches)), "network_requests": int(requests_made)}

    _run_stage_with_resume(
        args=args,
        state=state,
        name="direct_html_page_1",
        cursor={"path": "/matches/results", "page": 1, "limit": int(args.direct_limit)},
        fn=_direct_page,
    )

    def _api_health() -> dict[str, Any]:
        available, reason, requests_made = api_base_available(args.api_base_url)
        if not available:
            raise CollectionStageError(f"local vlrggapi unavailable: {reason}", requests_made=requests_made)
        return {"rows": 1, "network_requests": requests_made, "api_base_status": reason}

    api_result = _run_stage_with_resume(
        args=args,
        state=state,
        name="api_base_available",
        cursor={"api_base_url": args.api_base_url},
        fn=_api_health,
    )
    api_available = api_result.get("status") == "completed"
    args.api_available = bool(api_available)

    if api_available:
        for region in args.regions:
            _run_stage_with_resume(
                args=args,
                state=state,
                name=f"api_stats_{region}_{args.timespan}",
                cursor={"path": "/v2/stats", "region": region, "timespan": args.timespan},
                fn=lambda region=region: fetch_api_stats_to_cache(args, region, args.timespan),
            )
        for page in range(1, int(args.api_pages) + 1):
            _run_stage_with_resume(
                args=args,
                state=state,
                name=f"api_events_completed_page_{page}",
                cursor={"path": "/v2/events", "q": "completed", "page": page},
                fn=lambda page=page: fetch_api_events_to_cache(args, "completed", page),
            )
        _run_stage_with_resume(
            args=args,
            state=state,
            name=f"api_match_results_pages_{int(args.api_pages)}",
            cursor=_api_match_stage_cursor(args, "results", int(args.api_pages)),
            fn=lambda: fetch_api_match_to_cache(args, "results", int(args.api_pages)),
        )

    proxy_matches, proxy_players = load_kaggle_proxy(Path(args.kaggle_proxy_dir), fetched_at)
    cache_matches, cache_players = load_api_cache(args.cache_dir, args.api_base_url, fetched_at)
    direct_frames = _read_stage_frames(args, "direct_html")

    match_frames = [proxy_matches, cache_matches, *direct_frames]
    player_frames = [proxy_players, cache_players]
    match_df = pd.concat([df for df in match_frames if not df.empty], ignore_index=True) if any(not df.empty for df in match_frames) else pd.DataFrame(columns=PROVENANCE_FIELDS)
    player_df = pd.concat([df for df in player_frames if not df.empty], ignore_index=True) if any(not df.empty for df in player_frames) else pd.DataFrame(columns=PROVENANCE_FIELDS)
    match_df, player_df = _dedupe_outputs(match_df, player_df)

    args.collection_stages = _stage_summary(state)
    args.rate_limit_events = state.data.get("rate_limit_events", [])
    write_outputs(match_df, player_df, args, fetched_at, int(state.data.get("cumulative_requests", 0) or 0))

    _run_stage_with_resume(
        args=args,
        state=state,
        name="research_validation",
        cursor={"output": "reports/research_validation.json"},
        fn=lambda: _run_research_validation(args),
    )
    args.collection_stages = _stage_summary(state)
    args.rate_limit_events = state.data.get("rate_limit_events", [])
    write_outputs(match_df, player_df, args, fetched_at, int(state.data.get("cumulative_requests", 0) or 0))
    _run_research_validation(args)
    print(
        "VLR collection plan complete: "
        f"matches={len(match_df)} player_stats={len(player_df)} "
        f"network_requests={state.data.get('cumulative_requests', 0)} "
        f"state={args.state_file}"
    )


def _dedupe_expanded_outputs(
    maps_df: pd.DataFrame,
    players_df: pd.DataFrame,
    comps_df: pd.DataFrame,
    standings_df: pd.DataFrame,
    team_stats_df: pd.DataFrame,
    event_matches_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    specs = [
        (maps_df, ["match_id", "game_id", "team"]),
        (players_df, ["match_id", "game_id", "team", "player", "agent"]),
        (comps_df, ["match_id", "game_id", "team"]),
        (standings_df, ["year", "region", "team_id"]),
        (team_stats_df, ["team_id", "map"]),
        (event_matches_df, ["event_id", "match_id", "team_a", "team_b"]),
    ]
    out = []
    for df, subset in specs:
        if df.empty:
            out.append(df)
            continue
        cols = [col for col in subset if col in df.columns]
        out.append(df.drop_duplicates(subset=cols, keep="last").reset_index(drop=True) if cols else df)
    return tuple(out)  # type: ignore[return-value]


def write_expanded_outputs(
    maps_df: pd.DataFrame,
    players_df: pd.DataFrame,
    comps_df: pd.DataFrame,
    standings_df: pd.DataFrame,
    team_stats_df: pd.DataFrame,
    event_matches_df: pd.DataFrame,
    args: argparse.Namespace,
    fetched_at: str,
    state: CollectionState,
) -> None:
    args.output.mkdir(parents=True, exist_ok=True)
    args.reports.mkdir(parents=True, exist_ok=True)

    maps_df = _ensure_columns(maps_df, MATCH_MAP_COLUMNS)
    players_df = _ensure_columns(players_df, MATCH_PLAYER_COLUMNS)
    comps_df = _ensure_columns(comps_df, COMPOSITION_COLUMNS)
    standings_df = _ensure_columns(standings_df, STANDINGS_COLUMNS)
    team_stats_df = _ensure_columns(team_stats_df, TEAM_MAP_COLUMNS)
    event_matches_df = _ensure_columns(event_matches_df, EVENT_MATCH_COLUMNS)
    detail_raw_df = _combine_stage_frames(args, "match_details_raw_", MATCH_DETAIL_RAW_COLUMNS)
    rounds_df = _combine_stage_frames(args, "match_rounds_", ROUND_COLUMNS)
    economy_df = _combine_stage_frames(args, "match_economy_", ECONOMY_COLUMNS)
    kill_matrix_df = _combine_stage_frames(args, "match_kill_matrix_", KILL_MATRIX_COLUMNS)
    map_vetoes_df = _combine_stage_frames(args, "match_map_vetoes_", MAP_VETO_COLUMNS)
    team_transactions_df = _combine_stage_frames(args, "team_transactions_", TEAM_TRANSACTION_COLUMNS)
    event_details_df = _combine_stage_frames(args, "event_detail_", EVENT_DETAIL_COLUMNS)
    event_player_stats_df = _combine_stage_frames(args, "event_player_stats_", EVENT_PLAYER_STATS_COLUMNS)
    event_agent_usage_df = _combine_stage_frames(args, "event_agent_usage_", EVENT_AGENT_USAGE_COLUMNS)
    for name, df in [
        ("vlrgg_match_maps", maps_df),
        ("vlrgg_match_players", players_df),
        ("vlrgg_compositions", comps_df),
        ("vlrgg_standings", standings_df),
        ("vlrgg_team_map_stats", team_stats_df),
        ("vlrgg_event_matches", event_matches_df),
        ("vlrgg_event_details", event_details_df),
        ("vlrgg_event_player_stats", event_player_stats_df),
        ("vlrgg_event_agent_usage", event_agent_usage_df),
        ("vlrgg_match_details_raw", detail_raw_df),
        ("vlrgg_rounds", rounds_df),
        ("vlrgg_economy", economy_df),
        ("vlrgg_kill_matrix", kill_matrix_df),
        ("vlrgg_map_vetoes", map_vetoes_df),
        ("vlrgg_team_transactions", team_transactions_df),
    ]:
        validate_provenance(df, name)
        df.to_csv(args.output / f"{name}.csv", index=False)

    pipeline_df, pipeline_rejected_df = write_pipeline_readiness_outputs(
        maps_df,
        players_df,
        event_matches_df,
        args,
        fetched_at,
    )

    stages = _stage_summary(state)
    degraded_stages = [
        name for name, row in stages.items()
        if row.get("status") == "degraded" and (
            name.startswith("match_detail_")
            or name.startswith("standings_")
            or name.startswith("team_map_stats_")
            or name.startswith("event_matches_")
            or name.startswith("event_player_stats_")
            or name.startswith("event_agent_usage_")
            or name.startswith("event_intel_")
            or name.startswith("api_event_detail_")
            or name.startswith("api_event_intel_")
            or name.startswith("expanded_")
        )
    ]
    row_counts = {
        "vlrgg_match_maps": int(len(maps_df)),
        "vlrgg_match_players": int(len(players_df)),
        "vlrgg_compositions": int(len(comps_df)),
        "vlrgg_standings": int(len(standings_df)),
        "vlrgg_team_map_stats": int(len(team_stats_df)),
        "vlrgg_event_matches": int(len(event_matches_df)),
        "vlrgg_event_details": int(len(event_details_df)),
        "vlrgg_event_player_stats": int(len(event_player_stats_df)),
        "vlrgg_event_agent_usage": int(len(event_agent_usage_df)),
        "vlrgg_match_details_raw": int(len(detail_raw_df)),
        "vlrgg_rounds": int(len(rounds_df)),
        "vlrgg_economy": int(len(economy_df)),
        "vlrgg_kill_matrix": int(len(kill_matrix_df)),
        "vlrgg_map_vetoes": int(len(map_vetoes_df)),
        "vlrgg_team_transactions": int(len(team_transactions_df)),
        "vlrgg_pipeline_matches": int(len(pipeline_df)),
        "vlrgg_pipeline_rejected_matches": int(len(pipeline_rejected_df)),
    }

    summary_path = args.reports / "vlrgg_ingestion_summary.json"
    summary = _read_json_file(summary_path)
    summary.update({
        "generated_at": fetched_at,
        "parser_version": PARSER_VERSION,
        "mode": "expanded_collection_plan",
        "api_base_url": args.api_base_url,
        "api_version": DEFAULT_API_VERSION,
        "cache_dir": str(args.cache_dir),
        "robots_url": ROBOTS_URL,
        "allowed_paths": ROBOTS_ALLOWED_PATHS,
        "blocked_paths": ROBOTS_BLOCKED_PATHS,
        "collection_state_file": str(args.state_file),
        "stage_output_dir": str(args.stage_output_dir),
        "collection_stages": stages,
        "rate_limit": {
            "waited": bool(state.data.get("rate_limit_events", [])),
            "events": state.data.get("rate_limit_events", []),
            "wait_seconds_total": round(sum(float(row.get("wait_seconds", 0) or 0) for row in state.data.get("rate_limit_events", [])), 3),
        },
    })
    rows = dict(summary.get("rows", {}) if isinstance(summary.get("rows"), dict) else {})
    rows.update(row_counts)
    summary["rows"] = rows
    summary["expanded_collection"] = {
        "generated_at": fetched_at,
        "detail_limit": int(args.detail_limit),
        "event_limit": int(args.event_limit),
        "team_limit": int(args.team_limit),
        "standing_years": parse_standing_years(args.standing_years),
        "rows": row_counts,
        "sources": _combined_value_counts(
            [
                maps_df, players_df, comps_df, standings_df, team_stats_df,
                event_matches_df, event_details_df, event_player_stats_df,
                event_agent_usage_df, detail_raw_df, rounds_df, economy_df,
                kill_matrix_df, map_vetoes_df, team_transactions_df,
            ],
            "source",
        ),
        "retrieval_methods": _combined_value_counts(
            [
                maps_df, players_df, comps_df, standings_df, team_stats_df,
                event_matches_df, event_details_df, event_player_stats_df,
                event_agent_usage_df, detail_raw_df, rounds_df, economy_df,
                kill_matrix_df, map_vetoes_df, team_transactions_df,
            ],
            "retrieval_method",
        ),
        "degraded_stages": degraded_stages,
    }
    summary["network_requests"] = int(state.data.get("cumulative_requests", 0) or 0)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    coverage_path = args.reports / "data_source_coverage.json"
    coverage = _read_json_file(coverage_path)
    coverage.setdefault("generated_at", fetched_at)
    sources = coverage.setdefault("sources", {})
    for name, df in [
        ("vlrgg_match_maps", maps_df),
        ("vlrgg_match_players", players_df),
        ("vlrgg_compositions", comps_df),
        ("vlrgg_standings", standings_df),
        ("vlrgg_team_map_stats", team_stats_df),
        ("vlrgg_event_matches", event_matches_df),
        ("vlrgg_event_details", event_details_df),
        ("vlrgg_event_player_stats", event_player_stats_df),
        ("vlrgg_event_agent_usage", event_agent_usage_df),
        ("vlrgg_match_details_raw", detail_raw_df),
        ("vlrgg_rounds", rounds_df),
        ("vlrgg_economy", economy_df),
        ("vlrgg_kill_matrix", kill_matrix_df),
        ("vlrgg_map_vetoes", map_vetoes_df),
        ("vlrgg_team_transactions", team_transactions_df),
        ("vlrgg_pipeline_matches", pipeline_df),
    ]:
        info: dict[str, Any] = {
            "rows": int(len(df)),
            "path": str(args.output / f"{name}.csv"),
        }
        if "source" in df.columns:
            info["sources"] = df.get("source", pd.Series(dtype=str)).value_counts().to_dict()
        if "retrieval_method" in df.columns:
            info["retrieval_methods"] = df.get("retrieval_method", pd.Series(dtype=str)).value_counts().to_dict()
        sources[name] = info
    coverage_path.write_text(json.dumps(coverage, indent=2, ensure_ascii=False), encoding="utf-8")


def run_expanded_collection_plan(args: argparse.Namespace) -> None:
    fetched_at = _utc_now()
    args.cache_dir = Path(args.cache_dir)
    args.output = Path(args.output)
    args.reports = Path(args.reports)
    args.state_file = Path(args.state_file)
    args.stage_output_dir = Path(args.stage_output_dir)
    args.api_base_url = args.api_base_url.rstrip("/")
    args.allow_direct_html = True

    state = CollectionState(args.state_file, reset=args.restart)
    requests_before = int(state.data.get("cumulative_requests", 0) or 0)
    exclude_stage_output_dirs = _stage_dirs_from_args(args)
    exclude_ids = _load_stage_output_ids(exclude_stage_output_dirs)
    match_detail_candidate_ids: list[str] | None = None
    if exclude_stage_output_dirs and int(args.detail_limit) > 0:
        matches_for_detail = _load_expanded_match_sources(args, fetched_at)
        match_detail_candidate_ids = _guard_duplicate_overlap(
            args=args,
            state=state,
            stage_name="duplicate_overlap_match_detail",
            id_key="match_id",
            candidate_ids=select_match_detail_candidates(matches_for_detail, int(args.detail_limit)),
            exclude_ids=exclude_ids.get("match_id", set()),
        )

    def _remaining_budget() -> int:
        cap = int(getattr(args, "max_requests_per_session", DEFAULT_MAX_REQUESTS_PER_SESSION) or 0)
        if cap <= 0:
            return 0
        used = int(state.data.get("cumulative_requests", 0) or 0) - requests_before
        return max(0, cap - used)

    robots_args = argparse.Namespace(**vars(args))
    robots_args.restart = True
    _reset_stage_attempts(state, "robots_txt")
    robots_result = _run_stage_with_resume(
        args=robots_args,
        state=state,
        name="robots_txt",
        cursor={"url": ROBOTS_URL, "mode": "expanded_collection_plan"},
        fn=fetch_robots_policy,
    )
    robots_policy = robots_result if robots_result.get("status") == "completed" else {}
    if "direct_html_allowed_live" not in robots_policy and "details" in robots_result:
        robots_policy = dict(robots_result.get("details") or {})
    args.robots_policy = robots_policy
    direct_vlr_available = bool(robots_policy) and robots_policy.get("direct_html_allowed_live") is not False
    if not direct_vlr_available:
        state.mark_stage(
            "expanded_direct_html_available",
            "degraded",
            cursor={"robots_url": ROBOTS_URL},
            failure_reason="robots.txt could not be verified for expanded direct VLR collection",
            network_requests=0,
        )

    def _api_health_expanded() -> dict[str, Any]:
        available, reason, requests_made = api_base_available(args.api_base_url)
        if not available:
            raise CollectionStageError(f"local vlrggapi unavailable: {reason}", requests_made=requests_made)
        return {"rows": 1, "network_requests": requests_made, "api_base_status": reason}

    api_result = _run_stage_with_resume(
        args=args,
        state=state,
        name="api_base_available",
        cursor={"api_base_url": args.api_base_url},
        fn=_api_health_expanded,
    )
    args.api_available = api_result.get("status") == "completed"

    if int(args.event_limit) > 0 and _remaining_budget() > 0:
        _run_stage_with_resume(
            args=args,
            state=state,
            name="expanded_event_candidates",
            cursor={"path": "/v2/events", "q": "completed", "limit": int(args.event_limit)},
            fn=lambda: fetch_event_candidates_to_stage(args, int(args.event_limit), fetched_at),
        )
    event_candidates_df = _combine_stage_frames(
        args,
        "expanded_event_candidates",
        ["event_id", "event", "url_path", *PROVENANCE_FIELDS],
    )
    if int(args.event_limit) > 0 and event_candidates_df.empty:
        event_candidates_df = _combine_stage_frames(args, "api_event_candidates", EVENT_CANDIDATE_COLUMNS)
    if int(args.event_limit) <= 0:
        event_candidates_df = pd.DataFrame(columns=EVENT_CANDIDATE_COLUMNS)
    elif exclude_stage_output_dirs and not event_candidates_df.empty:
        kept_event_ids = _guard_duplicate_overlap(
            args=args,
            state=state,
            stage_name="duplicate_overlap_event_expansion",
            id_key="event_id",
            candidate_ids=[candidate["event_id"] for candidate in _event_candidates_from_frame(event_candidates_df, int(args.event_limit))],
            exclude_ids=exclude_ids.get("event_id", set()),
        )
        event_candidates_df = _filter_frame_by_clean_ids(event_candidates_df, "event_id", set(kept_event_ids))

    if not event_candidates_df.empty and _remaining_budget() > 0:
        _run_stage_with_resume(
            args=args,
            state=state,
            name="api_event_detail_expansion",
            cursor={
                "path": "/v2/event/{event_id}",
                "event_limit": int(args.event_limit),
                "request_budget": _remaining_budget(),
            },
            fn=lambda: expand_api_event_details_to_stage(args, event_candidates_df, fetched_at, _remaining_budget()),
        )

    if direct_vlr_available:
        from ml.vlrgg_scraper import scrape_event_matches, scrape_match_detail, scrape_standings, scrape_team_stats

        matches_df = _load_expanded_match_sources(args, fetched_at)
        if int(args.detail_limit) > 0:
            candidate_match_ids = match_detail_candidate_ids
            if candidate_match_ids is None:
                candidate_match_ids = select_match_detail_candidates(matches_df, int(args.detail_limit))
            for match_id in candidate_match_ids:
                if _remaining_budget() <= 0:
                    break

                def _detail_stage(match_id: str = match_id) -> dict[str, Any]:
                    details = scrape_match_detail(match_id)
                    maps, players, comps = build_match_detail_frames(details, fetched_at)
                    _write_stage_frame(args, f"match_detail_maps_{match_id}", maps)
                    _write_stage_frame(args, f"match_detail_players_{match_id}", players)
                    _write_stage_frame(args, f"match_detail_compositions_{match_id}", comps)
                    return {
                        "rows": int(len(maps) + len(players) + len(comps)),
                        "network_requests": 1,
                        "map_rows": int(len(maps)),
                        "player_rows": int(len(players)),
                        "composition_rows": int(len(comps)),
                    }

                _run_stage_with_resume(
                    args=args,
                    state=state,
                    name=f"match_detail_{match_id}",
                    cursor={"path": f"/{match_id}", "match_id": match_id},
                    fn=_detail_stage,
                )

        for year in parse_standing_years(args.standing_years):
            if _remaining_budget() <= 0:
                break
            def _standings_stage(year: int = year) -> dict[str, Any]:
                df = _standings_frame(scrape_standings(year), year=year, fetched_at=fetched_at)
                _write_stage_frame(args, f"standings_{year}", df)
                return {"rows": int(len(df)), "network_requests": 1}

            _run_stage_with_resume(
                args=args,
                state=state,
                name=f"standings_{year}",
                cursor={"path": f"/vct-{year}/standings", "year": year},
                fn=_standings_stage,
            )

        standings_df_for_candidates = _combine_stage_frames(args, "standings_", STANDINGS_COLUMNS)
        if int(args.team_limit) > 0:
            team_candidates = _team_candidates_from_standings(standings_df_for_candidates, int(args.team_limit))
            if exclude_stage_output_dirs:
                kept_team_ids = set(_guard_duplicate_overlap(
                    args=args,
                    state=state,
                    stage_name="duplicate_overlap_team_map_stats",
                    id_key="team_id",
                    candidate_ids=[candidate["team_id"] for candidate in team_candidates],
                    exclude_ids=exclude_ids.get("team_id", set()),
                ))
                team_candidates = [candidate for candidate in team_candidates if candidate["team_id"] in kept_team_ids]
            for candidate in team_candidates:
                if _remaining_budget() <= 0:
                    break
                team_id = candidate["team_id"]
                team = candidate["team"]

                def _team_stage(team_id: str = team_id, team: str = team) -> dict[str, Any]:
                    df = _team_map_stats_frame(scrape_team_stats(team_id), team_id=team_id, team=team, fetched_at=fetched_at)
                    _write_stage_frame(args, f"team_map_stats_{team_id}", df)
                    return {"rows": int(len(df)), "network_requests": 1}

                _run_stage_with_resume(
                    args=args,
                    state=state,
                    name=f"team_map_stats_{team_id}",
                    cursor={"path": f"/team/stats/{team_id}", "team_id": team_id},
                    fn=_team_stage,
                )

        for candidate in _event_candidates_from_frame(event_candidates_df, int(args.event_limit)):
            if _remaining_budget() <= 0:
                break
            event_id = candidate["event_id"]
            event = candidate["event"]

            def _event_stage(event_id: str = event_id, event: str = event) -> dict[str, Any]:
                df = _event_matches_frame(scrape_event_matches(event_id, page=1), event_id=event_id, event=event, fetched_at=fetched_at)
                _write_stage_frame(args, f"event_matches_{event_id}", df)
                return {"rows": int(len(df)), "network_requests": 1}

            _run_stage_with_resume(
                args=args,
                state=state,
                name=f"event_matches_{event_id}",
                cursor={"path": f"/event/matches/{event_id}/", "page": 1},
                fn=_event_stage,
            )

    if int(args.event_limit) > 0:
        event_intel_allowed = bool(robots_policy) and robots_policy.get("event_intel_direct_html_allowed_live") is not False
        if not event_intel_allowed:
            state.mark_stage(
                "event_intel_direct_html",
                "degraded",
                cursor={"paths": ["/event/stats/{event_id}/", "/event/agents/{event_id}/"]},
                failure_reason="robots.txt could not be verified for event stats/agents direct HTML collection",
                network_requests=0,
            )
        elif not event_candidates_df.empty and _remaining_budget() > 0:
            _run_stage_with_resume(
                args=args,
                state=state,
                name="event_intel_direct_html",
                cursor={
                    "paths": ["/event/stats/{event_id}/", "/event/agents/{event_id}/"],
                    "event_limit": int(args.event_limit),
                    "request_budget": _remaining_budget(),
                },
                fn=lambda: expand_event_intel_to_stage(args, event_candidates_df, fetched_at, _remaining_budget()),
            )

    maps_df = _combine_stage_frames(args, "match_detail_maps_", MATCH_MAP_COLUMNS)
    players_df = _combine_stage_frames(args, "match_detail_players_", MATCH_PLAYER_COLUMNS)
    comps_df = _combine_stage_frames(args, "match_detail_compositions_", COMPOSITION_COLUMNS)
    standings_df = _combine_stage_frames(args, "standings_", STANDINGS_COLUMNS)
    team_stats_df = _combine_stage_frames(args, "team_map_stats_", TEAM_MAP_COLUMNS)
    event_matches_df = _combine_stage_frames(args, "event_matches_", EVENT_MATCH_COLUMNS)
    event_details_df = _combine_stage_frames(args, "event_detail_", EVENT_DETAIL_COLUMNS)
    event_player_stats_df = _combine_stage_frames(args, "event_player_stats_", EVENT_PLAYER_STATS_COLUMNS)
    event_agent_usage_df = _combine_stage_frames(args, "event_agent_usage_", EVENT_AGENT_USAGE_COLUMNS)
    maps_df, players_df, comps_df, standings_df, team_stats_df, event_matches_df = _dedupe_expanded_outputs(
        maps_df, players_df, comps_df, standings_df, team_stats_df, event_matches_df
    )
    write_expanded_outputs(
        maps_df,
        players_df,
        comps_df,
        standings_df,
        team_stats_df,
        event_matches_df,
        args,
        fetched_at,
        state,
    )
    validation_args = argparse.Namespace(**vars(args))
    validation_args.restart = True
    _reset_stage_attempts(state, "research_validation")
    _run_stage_with_resume(
        args=validation_args,
        state=state,
        name="research_validation",
        cursor={"output": "reports/research_validation.json", "mode": "expanded_collection_plan"},
        fn=lambda: _run_research_validation(args),
    )
    candidates_df = _build_and_write_candidates(args, fetched_at, state)
    print(
        "VLR expanded collection complete: "
        f"maps={len(maps_df)} players={len(players_df)} comps={len(comps_df)} "
        f"standings={len(standings_df)} team_maps={len(team_stats_df)} "
        f"event_matches={len(event_matches_df)} event_details={len(event_details_df)} "
        f"event_player_stats={len(event_player_stats_df)} event_agent_usage={len(event_agent_usage_df)} "
        f"candidates={len(candidates_df)} state={args.state_file}"
    )


def _run_research_validation(args: argparse.Namespace) -> dict[str, Any]:
    report = build_research_validation_report(Path(args.output), Path(args.reports))
    output = Path(args.research_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    facts = report.get("report_facts", [])
    return {"rows": int(len(facts)), "network_requests": 0}


def build_research_validation_report(processed_dir: Path, reports_dir: Path) -> dict[str, Any]:
    return {"report_facts": [], "skipped": "research_validation module not available"}


def build_agent_map_stats(player_df: pd.DataFrame, fetched_at: str) -> pd.DataFrame:
    if player_df.empty:
        return pd.DataFrame(columns=[
            "agent", "map_key", "region", "n_player_rows", "total_rounds",
            "avg_rating", "avg_acs", "avg_kd", "avg_adr", *PROVENANCE_FIELDS,
        ])
    rows = []
    group_cols = ["agent", "map_key", "region"]
    for keys, grp in player_df.groupby(group_cols, dropna=False):
        agent, map_key, region = keys
        source_hash = _sha1_obj(sorted(grp["source_hash"].astype(str).tolist()))
        rows.append({
            "agent": agent,
            "map_key": map_key,
            "region": region,
            "n_player_rows": int(len(grp)),
            "total_rounds": int(pd.to_numeric(grp.get("rounds_played"), errors="coerce").fillna(0).sum()),
            "avg_rating": pd.to_numeric(grp.get("rating"), errors="coerce").mean(),
            "avg_acs": pd.to_numeric(grp.get("average_combat_score"), errors="coerce").mean(),
            "avg_kd": pd.to_numeric(grp.get("kill_deaths"), errors="coerce").mean(),
            "avg_adr": pd.to_numeric(grp.get("average_damage_per_round"), errors="coerce").mean(),
            "source": "|".join(sorted(set(grp["source"].astype(str)))),
            "source_url": "|".join(sorted(set(grp["source_url"].astype(str)))[:3]),
            "retrieval_method": "aggregate",
            "fetched_at": fetched_at,
            "cache_hit": bool(grp["cache_hit"].all()),
            "parser_version": PARSER_VERSION,
            "source_hash": source_hash,
        })
    return pd.DataFrame(rows)


def _combined_value_counts(frames: list[pd.DataFrame], column: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for df in frames:
        if df.empty or column not in df.columns:
            continue
        for value, count in df[column].astype(str).value_counts().to_dict().items():
            counts[value] = counts.get(value, 0) + int(count)
    return counts


def write_outputs(match_df: pd.DataFrame, player_df: pd.DataFrame, args: argparse.Namespace,
                  fetched_at: str, network_requests: int) -> None:
    args.output.mkdir(parents=True, exist_ok=True)
    args.reports.mkdir(parents=True, exist_ok=True)

    agent_map_df = build_agent_map_stats(player_df, fetched_at)
    for name, df in [
        ("vlrgg_matches", match_df),
        ("vlrgg_player_stats", player_df),
        ("vlrgg_agent_map_stats", agent_map_df),
    ]:
        validate_provenance(df, name)

    match_df.to_csv(args.output / "vlrgg_matches.csv", index=False)
    player_df.to_csv(args.output / "vlrgg_player_stats.csv", index=False)
    agent_map_df.to_csv(args.output / "vlrgg_agent_map_stats.csv", index=False)

    robots_policy = getattr(args, "robots_policy", {}) or {}
    rate_limit_events = getattr(args, "rate_limit_events", []) or []
    summary = {
        "generated_at": fetched_at,
        "parser_version": PARSER_VERSION,
        "mode": "collection_plan" if getattr(args, "run_plan", False) else (
            "from_cache_only" if args.from_cache_only else ("fetch_" + args.source if args.fetch else "cache_plus_local")
        ),
        "api_base_url": args.api_base_url,
        "api_version": DEFAULT_API_VERSION,
        "cache_dir": str(args.cache_dir),
        "robots_checked_at": robots_policy.get("robots_checked_at", fetched_at),
        "robots_url": ROBOTS_URL,
        "allowed_paths": ROBOTS_ALLOWED_PATHS,
        "blocked_paths": ROBOTS_BLOCKED_PATHS,
        "robots_live": robots_policy,
        "direct_html_allowed": bool(args.allow_direct_html),
        "direct_html_allowed_paths": DIRECT_HTML_ALLOWED_PATHS,
        "blocked_direct_paths": ROBOTS_BLOCKED_PATHS,
        "direct_html_max_pages": MAX_DIRECT_HTML_PAGES,
        "direct_html_default_limit": DEFAULT_DIRECT_HTML_LIMIT,
        "network_requests": network_requests,
        "collection_state_file": str(getattr(args, "state_file", "")),
        "stage_output_dir": str(getattr(args, "stage_output_dir", "")),
        "collection_stages": getattr(args, "collection_stages", {}),
        "api_available": getattr(args, "api_available", None),
        "rate_limit": {
            "waited": bool(rate_limit_events),
            "events": rate_limit_events,
            "wait_seconds_total": round(sum(float(row.get("wait_seconds", 0) or 0) for row in rate_limit_events), 3),
        },
        "rows": {
            "vlrgg_matches": int(len(match_df)),
            "vlrgg_player_stats": int(len(player_df)),
            "vlrgg_agent_map_stats": int(len(agent_map_df)),
        },
        "sources": _combined_value_counts([match_df, player_df], "source"),
        "retrieval_methods": _combined_value_counts([match_df, player_df], "retrieval_method"),
        "regions": sorted(set(player_df.get("region", pd.Series(dtype=str)).dropna().astype(str))),
        "agents": sorted(set(player_df.get("agent", pd.Series(dtype=str)).dropna().astype(str))),
    }
    (args.reports / "vlrgg_ingestion_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    processed_matches = _read_csv(Path("data/processed/matches_clean.csv"))
    preprocess_summary_path = args.reports / "preprocess_summary.json"
    preprocess_summary = {}
    if preprocess_summary_path.exists():
        preprocess_summary = json.loads(preprocess_summary_path.read_text(encoding="utf-8"))
    coverage = {
        "generated_at": fetched_at,
        "sources": {
            "processed_model_contract": {
                "rows": int(len(processed_matches)),
                "path": "data/processed/matches_clean.csv",
                "active_feature_count": preprocess_summary.get("active_feature_count"),
            },
            "vlrgg_matches": {
                "rows": int(len(match_df)),
                "path": str(args.output / "vlrgg_matches.csv"),
                "sources": match_df.get("source", pd.Series(dtype=str)).value_counts().to_dict(),
            },
            "vlrgg_player_stats": {
                "rows": int(len(player_df)),
                "path": str(args.output / "vlrgg_player_stats.csv"),
                "regions": sorted(set(player_df.get("region", pd.Series(dtype=str)).dropna().astype(str))),
            },
            "vlrgg_agent_map_stats": {
                "rows": int(len(agent_map_df)),
                "path": str(args.output / "vlrgg_agent_map_stats.csv"),
            },
        },
    }
    (args.reports / "data_source_coverage.json").write_text(
        json.dumps(coverage, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def run_max_collection_plan(args: argparse.Namespace) -> None:
    """Run discovery plus pending-detail backfill under the per-session request cap."""
    if int(args.event_limit) == DEFAULT_EVENT_LIMIT:
        args.event_limit = 0
    if int(args.event_pages) == 5:
        args.event_pages = 0
    run_discovery_plan(args)
    backfill_args = argparse.Namespace(**vars(args))
    backfill_args.restart = False
    run_backfill_plan(backfill_args)


def run(args: argparse.Namespace) -> None:
    if getattr(args, "merge_shard_outputs", False):
        run_merge_shard_outputs(args)
        return
    if getattr(args, "run_player_profile_plan", False):
        run_player_profile_plan(args)
        return
    if getattr(args, "run_max_plan", False):
        run_max_collection_plan(args)
        return
    if getattr(args, "run_discovery_plan", False):
        run_discovery_plan(args)
        return
    if getattr(args, "run_backfill_plan", False):
        run_backfill_plan(args)
        return
    if getattr(args, "run_expanded_plan", False):
        run_expanded_collection_plan(args)
        return
    if getattr(args, "run_plan", False):
        run_collection_plan(args)
        return

    fetched_at = _utc_now()
    args.cache_dir = Path(args.cache_dir)
    args.output = Path(args.output)
    args.reports = Path(args.reports)
    args.api_base_url = args.api_base_url.rstrip("/")
    network_requests = 0

    match_frames: list[pd.DataFrame] = []
    player_frames: list[pd.DataFrame] = []

    proxy_matches, proxy_players = load_kaggle_proxy(Path(args.kaggle_proxy_dir), fetched_at)
    match_frames.append(proxy_matches)
    player_frames.append(proxy_players)

    cache_matches, cache_players = load_api_cache(args.cache_dir, args.api_base_url, fetched_at)
    match_frames.append(cache_matches)
    player_frames.append(cache_players)

    if args.fetch and not args.from_cache_only:
        if args.source == "api":
            api_matches, api_players, requests_made = fetch_api(args, fetched_at)
            network_requests += requests_made
            match_frames.append(api_matches)
            player_frames.append(api_players)
        elif args.source == "direct-html":
            direct_matches, direct_players, requests_made = fetch_direct_html(args, fetched_at)
            network_requests += requests_made
            match_frames.append(direct_matches)
            player_frames.append(direct_players)

    match_df = pd.concat([df for df in match_frames if not df.empty], ignore_index=True) if any(not df.empty for df in match_frames) else pd.DataFrame(columns=PROVENANCE_FIELDS)
    player_df = pd.concat([df for df in player_frames if not df.empty], ignore_index=True) if any(not df.empty for df in player_frames) else pd.DataFrame(columns=PROVENANCE_FIELDS)

    if args.limit and len(match_df) > args.limit:
        match_df = match_df.head(args.limit).copy()
    write_outputs(match_df, player_df, args, fetched_at, network_requests)
    print(
        f"VLR outputs written: matches={len(match_df)} player_stats={len(player_df)} "
        f"network_requests={network_requests}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect conservative VLR.gg research artifacts")
    parser.add_argument("--run-max-plan", action="store_true", help="Run exhaustive API discovery, event-match expansion, and capped detail backfill")
    parser.add_argument("--run-plan", action="store_true", help="Run robots -> direct HTML -> local API -> reports with resumable state")
    parser.add_argument("--run-expanded-plan", action="store_true", help="Run VLR detail/team/event expansion with resumable state")
    parser.add_argument("--run-discovery-plan", action="store_true", help="Build VLR event/match/team candidate inventory and readiness outputs")
    parser.add_argument("--run-backfill-plan", action="store_true", help="Backfill pending VLR match details into pipeline-ready rows")
    parser.add_argument("--run-player-profile-plan", action="store_true", help="Collect player profiles, per-timespan agent usage, and recent matches through the local VLR.gg API")
    parser.add_argument("--merge-shard-outputs", action="store_true", help="Merge isolated VLR backfill shard output directories into the final output/reports")
    parser.add_argument("--restart", action="store_true", help="Ignore prior collection state for --run-plan")
    parser.add_argument("--from-cache-only", action="store_true", help="Use Kaggle proxy and existing cache only")
    parser.add_argument("--fetch", action="store_true", help="Fetch missing data from the selected source")
    parser.add_argument("--source", choices=["api", "direct-html"], default="api")
    parser.add_argument("--pages", type=int, default=1)
    parser.add_argument("--direct-pages", type=int, default=1)
    parser.add_argument("--direct-limit", type=int, default=DEFAULT_DIRECT_HTML_LIMIT)
    parser.add_argument("--api-pages", type=int, default=1)
    parser.add_argument("--api-from-page", type=int, default=0)
    parser.add_argument("--api-to-page", type=int, default=0)
    parser.add_argument("--api-match-window-size", type=int, default=DEFAULT_API_MATCH_WINDOW_SIZE, help="Maximum /v2/match page window per request; local vlrggapi rejects windows above 20")
    parser.add_argument("--event-pages", type=int, default=5)
    parser.add_argument("--event-match-pages", type=int, default=1)
    parser.add_argument("--detail-limit", type=int, default=DEFAULT_DETAIL_LIMIT)
    parser.add_argument("--event-limit", type=int, default=DEFAULT_EVENT_LIMIT)
    parser.add_argument("--team-limit", type=int, default=DEFAULT_TEAM_LIMIT)
    parser.add_argument("--player-limit", type=int, default=DEFAULT_PLAYER_LIMIT)
    parser.add_argument("--player-profile-timespans", nargs="+", default=["all"], choices=list(PLAYER_TIMESPANS))
    parser.add_argument("--player-match-pages", type=int, default=1)
    parser.add_argument("--standing-years", default=DEFAULT_STANDING_YEARS)
    parser.add_argument("--regions", nargs="+", default=["na", "eu", "ap", "kr"], choices=list(REGIONS))
    parser.add_argument("--timespan", default="30", choices=list(TIMESPANS))
    parser.add_argument("--rate-limit", type=float, default=1.0)
    parser.add_argument("--max-requests-per-session", type=int, default=DEFAULT_MAX_REQUESTS_PER_SESSION)
    parser.add_argument("--retry-backoff-seconds", type=float, default=5.0)
    parser.add_argument("--max-rate-limit-wait-seconds", type=float, default=DEFAULT_LONG_WAIT_SECONDS + DEFAULT_RATE_LIMIT_JITTER_SECONDS)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--allow-direct-html", action="store_true")
    parser.add_argument("--backfill-shard-count", type=int, default=1, help="Total number of parallel backfill shards; count > 1 automatically isolates mutable shard paths")
    parser.add_argument("--backfill-shard-index", type=int, default=0, help="Zero-based shard index for this backfill worker")
    parser.add_argument("--backfill-candidates-file", default="", help="Candidate CSV to read when running an isolated shard output directory")
    parser.add_argument("--skip-robots-check", action="store_true", help="Skip direct VLR robots.txt probing for API-only backfill runs")
    parser.add_argument("--disable-direct-html-fallback", action="store_true", help="Do not use direct VLR match HTML fallback when API detail collection fails")
    parser.add_argument("--upstream-lock-file", default=DEFAULT_UPSTREAM_LOCK_FILE, help="Cross-process lock file for shared VLR.gg upstream detail calls")
    parser.add_argument("--upstream-lock-min-interval-seconds", type=float, default=0.0, help="Minimum seconds between shared VLR detail starts; defaults to 1 / --rate-limit")
    parser.add_argument("--disable-upstream-lock", action="store_true", help="Disable the shared upstream detail lock for controlled single-process debugging")
    parser.add_argument("--shard-output-dirs", nargs="+", default=[], help="Shard output directories to merge with --merge-shard-outputs")
    parser.add_argument("--no-merge-existing-output", action="store_true", help="Do not include --output as an input source when merging shard outputs")
    parser.add_argument("--exclude-stage-output-dirs", nargs="+", default=[], help="Stage output directories whose collected IDs are skipped by --run-expanded-plan")
    parser.add_argument("--duplicate-overlap-threshold", type=float, default=DEFAULT_DUPLICATE_OVERLAP_THRESHOLD, help="Fail an expanded-plan candidate batch when excluded-ID overlap is above this ratio")
    parser.add_argument("--api-base-url", default=os.getenv("VLRGG_API_BASE_URL", DEFAULT_API_BASE_URL))
    parser.add_argument("--cache-dir", default=os.getenv("VLRGG_CACHE_DIR", DEFAULT_CACHE_DIR))
    parser.add_argument("--kaggle-proxy-dir", default=DEFAULT_KAGGLE_PROXY_DIR)
    parser.add_argument("--output", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--reports", default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--state-file", default=DEFAULT_STATE_FILE)
    parser.add_argument("--stage-output-dir", default=DEFAULT_STAGE_OUTPUT_DIR)
    parser.add_argument("--research-output", default="reports/research_validation.json")
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
