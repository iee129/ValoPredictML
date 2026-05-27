"""Previous-year baseline feature builder.

The baseline input contract is intentionally the same shape as the future UI:
map + five player-agent pairs for team A + five player-agent pairs for team B.
Every numeric player signal is a previous-year aggregate. If a match belongs to
2024, only player history from years before 2024 is available to the model.
Player prior metrics are smoothed toward the matching previous-year league
average, and short year windows are also exposed for the last one and two years.

Usage:
    python -m ml.baseline.preprocess
"""
from __future__ import annotations

import argparse
import re
from collections import defaultdict
from dataclasses import dataclass, field
from itertools import combinations, groupby
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.ensemble import VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from ml.valorant import (
    AGENTS_SORTED,
    MAP_ORDER,
    ROLES,
    _agent_col_key,
    compute_rounds,
    normalize_agent,
    normalize_map,
)

HISTORY_STATS = ["kd", "kast", "adr", "apr", "fkpr", "fdpr", "clutch"]
PLAYER_PRIOR_BASES = ["prior_games"] + [f"prior_{stat}" for stat in HISTORY_STATS]
PRIOR_WINDOW_YEARS = {
    "all": None,
}
PLAYER_PRIOR_BASES_BY_SCOPE = {
    "all": PLAYER_PRIOR_BASES,
}
ALL_PLAYER_PRIOR_BASES = list(PLAYER_PRIOR_BASES)
PLAYER_PRIOR_SMOOTHING_GAMES = 5.0

MAP_COLS = [f"map_{m.lower()}" for m in MAP_ORDER]
ROLE_COUNT_COLS = [
    col
    for role in ROLES
    for col in (f"a_role_{role}_count", f"b_role_{role}_count", f"diff_role_{role}_count")
]
MODELED_AGENT_KEYS = [agent for agent in AGENTS_SORTED if agent != "miks"]
AGENT_COUNT_COLS = [
    col
    for agent in MODELED_AGENT_KEYS
    for col in (
        f"a_agent_{agent}_count",
        f"b_agent_{agent}_count",
        f"diff_agent_{agent}_count",
    )
]
PLAYER_PRIOR_COLS = [
    col
    for base in ALL_PLAYER_PRIOR_BASES
    for col in (f"a_{base}_mean", f"b_{base}_mean", f"diff_{base}_mean")
]
SYNERGY_COLS = ["a_synergy_mean", "b_synergy_mean", "diff_synergy_mean"]
MAP_AGENT_COLS = [
    col
    for stat in HISTORY_STATS
    for col in (f"a_map_agent_{stat}_mean", f"b_map_agent_{stat}_mean", f"diff_map_agent_{stat}_mean")
]
PLAYER_AGENT_COLS = [
    col
    for stat in HISTORY_STATS
    for col in (f"a_player_agent_{stat}_mean", f"b_player_agent_{stat}_mean", f"diff_player_agent_{stat}_mean")
]
FEATURE_ENGINEERING_CONFIG = {
    "player_prior_smoothing_games": PLAYER_PRIOR_SMOOTHING_GAMES,
    "prior_windows": {
        "prior": "all years before the current match year",
    },
    "same_year_history": "excluded",
}
SOURCE_CONTRACT = {
    "allowed_source_prefixes": ["kaggle_"],
    "excluded_source_prefixes": ["vlrgg_"],
    "description": "Active baseline uses Kaggle sources only; VLR.gg rows are excluded before feature construction.",
}

INPUT_CONTRACT = {
    "map": "one selected map",
    "team_a": "five player-agent pairs",
    "team_b": "five player-agent pairs",
    "team_names": "not required by runtime feature construction",
}
FEATURE_CONTRACT = (
    "map one-hot, role counts, 28-agent one-hot/counts, previous-year player prior "
    "smoothed mean aggregates, previous-year synergy, map×agent smoothed mean aggregates, "
    "and player×agent smoothed mean aggregates; same match and same year stats are excluded"
)
FORBIDDEN_FEATURE_TERMS = [
    "score",
    "winner",
    "result",
    "round",
    "acs",
    "kills",
    "deaths",
    "assists",
    "hs",
    "team_a",
    "team_b",
    "h2h",
    "prior_wr",
    "map_wr",
    "recent5_wr",
    "atk_side",
    "is_attacker",
    "a_p1_",
    "a_p2_",
    "a_p3_",
    "a_p4_",
    "a_p5_",
    "b_p1_",
    "b_p2_",
    "b_p3_",
    "b_p4_",
    "b_p5_",
]
FORBIDDEN_FEATURE_PATTERNS = [
    re.compile(pattern)
    for pattern in (
        r"(^|_)score(_|$)",
        r"winner|result|round",
        r"(^|_)(acs|kills|deaths|assists|hs)($|_)",
        r"(^|_)team_[ab]($|_)",
        r"h2h|prior_wr|map_wr|recent5_wr",
        r"map_prior|agent_prior|recent5",
        r"atk_side|is_attacker",
        r"^[ab]_p[1-5]_",
    )
]

FEATURE_COLS = (
    MAP_COLS
    + ROLE_COUNT_COLS
    + AGENT_COUNT_COLS
    + PLAYER_PRIOR_COLS
    + SYNERGY_COLS
    + MAP_AGENT_COLS
    + PLAYER_AGENT_COLS
)

EXPECTED_FEATURE_COUNT = 178
if len(FEATURE_COLS) != EXPECTED_FEATURE_COUNT:
    raise RuntimeError(
        f"Approved baseline contract requires {EXPECTED_FEATURE_COUNT} features, "
        f"got {len(FEATURE_COLS)}"
    )

# Advanced contract: 125 features, no diff columns, 29 agents (Miks 포함)
MODELED_AGENT_KEYS_ADVANCED: list[str] = list(AGENTS_SORTED)  # 29 agents
ROLE_COUNT_COLS_ADV = [
    col
    for role in ROLES
    for col in (f"a_role_{role}_count", f"b_role_{role}_count")
]
AGENT_COUNT_COLS_ADV = [
    col
    for agent in MODELED_AGENT_KEYS_ADVANCED
    for col in (f"a_agent_{agent}_count", f"b_agent_{agent}_count")
]
PLAYER_PRIOR_COLS_ADV = [
    col
    for base in ALL_PLAYER_PRIOR_BASES
    for col in (f"a_{base}_mean", f"b_{base}_mean")
]
SYNERGY_COLS_ADV = ["a_synergy_mean", "b_synergy_mean"]
MAP_AGENT_COLS_ADV = [
    col
    for stat in HISTORY_STATS
    for col in (f"a_map_agent_{stat}_mean", f"b_map_agent_{stat}_mean")
]
PLAYER_AGENT_COLS_ADV = [
    col
    for stat in HISTORY_STATS
    for col in (f"a_player_agent_{stat}_mean", f"b_player_agent_{stat}_mean")
]
FEATURE_COLS_ADVANCED: list[str] = (
    MAP_COLS
    + ROLE_COUNT_COLS_ADV
    + AGENT_COUNT_COLS_ADV
    + PLAYER_PRIOR_COLS_ADV
    + SYNERGY_COLS_ADV
    + MAP_AGENT_COLS_ADV
    + PLAYER_AGENT_COLS_ADV
)
EXPECTED_FEATURE_COUNT_ADVANCED = 125
if len(FEATURE_COLS_ADVANCED) != EXPECTED_FEATURE_COUNT_ADVANCED:
    raise RuntimeError(
        f"Advanced contract requires {EXPECTED_FEATURE_COUNT_ADVANCED} features, "
        f"got {len(FEATURE_COLS_ADVANCED)}"
    )
FEATURE_CONTRACT_ADVANCED = (
    "map one-hot, role counts a/b (no diff), 29-agent one-hot/counts a/b (includes miks), "
    "previous-year player prior smoothed mean aggregates a/b, synergy a/b, "
    "map×agent smoothed mean aggregates a/b, player×agent smoothed mean aggregates a/b; "
    "diff features excluded; same year stats excluded"
)

META_COLS = [
    "match_key",
    "dedup_key",
    "date",
    "year",
    "event",
    "map",
    "team_a",
    "team_b",
    "source",
    "provenance",
    "split",
]


@dataclass
class RunningStats:
    games: int = 0
    sums: dict[str, float] = field(default_factory=lambda: defaultdict(float))

    def add(self, values: dict[str, float]) -> None:
        self.games += 1
        clean = {stat: float(values.get(stat, 0.0)) for stat in HISTORY_STATS}
        for stat, value in clean.items():
            self.sums[stat] += value

    def avg(self, stat: str) -> float:
        if self.games == 0:
            return 0.0
        return float(self.sums.get(stat, 0.0) / self.games)

    def merge(self, other: "RunningStats") -> None:
        self.games += other.games
        for stat, value in other.sums.items():
            self.sums[stat] += float(value)

    def smoothed_avg(self, stat: str, global_history: "RunningStats") -> float:
        """Shrink low-sample player means toward the prior-window league mean."""
        if self.games == 0:
            return 0.0
        global_avg = global_history.avg(stat)
        numerator = self.sums.get(stat, 0.0) + PLAYER_PRIOR_SMOOTHING_GAMES * global_avg
        denominator = self.games + PLAYER_PRIOR_SMOOTHING_GAMES
        return float(numerator / denominator)


@dataclass(frozen=True)
class PlayerInput:
    player_key: str
    agent_key: str | None
    role: str | None
    stats: dict[str, float]


@dataclass(frozen=True)
class MatchInput:
    match_key: str
    year: int | None
    map_name: str | None
    sides: dict[str, list[PlayerInput]]


# Existing train/evaluate/validate interface.
def load_split(name: str, base: str = "data/processed") -> pd.DataFrame:
    return pd.read_csv(f"{base}/{name}.csv", low_memory=False)


def build_xy(df: pd.DataFrame, feature_contract: str = "baseline"):
    """Return model X, label y, and match_key groups in canonical feature order."""
    feature_cols = FEATURE_COLS_ADVANCED if feature_contract == "advanced" else FEATURE_COLS
    columns = {}
    for col in feature_cols:
        if col in df.columns:
            columns[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0).to_numpy()
        else:
            columns[col] = np.zeros(len(df), dtype=float)
    X = pd.DataFrame(columns, index=df.index)
    y = df["label"].astype(int)
    groups = df["match_key"].astype(str)
    return X.astype(float), y, groups


def make_pipeline() -> VotingClassifier:
    lr = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000, C=1.0, random_state=42)),
        ]
    )
    dt = DecisionTreeClassifier(max_depth=8, min_samples_leaf=50, random_state=42)
    return VotingClassifier(
        estimators=[("lr", lr), ("dt", dt)],
        voting="soft",
        n_jobs=1,
    )


def find_forbidden_feature_names(feature_names: Iterable[str]) -> list[str]:
    offenders: list[str] = []
    for name in feature_names:
        lower = str(name).lower()
        if any(pattern.search(lower) for pattern in FORBIDDEN_FEATURE_PATTERNS):
            offenders.append(str(name))
    return offenders


def _load_matches(processed_dir: str) -> pd.DataFrame:
    df = pd.read_csv(f"{processed_dir}/matches.csv", low_memory=False)
    df["match_key"] = df["match_key"].astype(str)
    return df


def _load_players(processed_dir: str) -> pd.DataFrame:
    df = pd.read_csv(f"{processed_dir}/players.csv", low_memory=False)
    df["match_key"] = df["match_key"].astype(str)
    return df


def _is_allowed_source(source: object) -> bool:
    text = "" if source is None or pd.isna(source) else str(source)
    return any(
        text.startswith(prefix)
        for prefix in SOURCE_CONTRACT["allowed_source_prefixes"]
    )


def _filter_allowed_sources(
    matches: pd.DataFrame,
    players: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Apply the active baseline source contract before feature construction."""
    if "source" not in matches.columns:
        return matches, players, {"enabled": False, "reason": "matches has no source column"}

    match_mask = matches["source"].map(_is_allowed_source)
    filtered_matches = matches[match_mask].copy()
    allowed_match_keys = set(filtered_matches["match_key"].astype(str))

    if "source" in players.columns:
        player_mask = (
            players["match_key"].astype(str).isin(allowed_match_keys)
            & players["source"].map(_is_allowed_source)
        )
    else:
        player_mask = players["match_key"].astype(str).isin(allowed_match_keys)
    filtered_players = players[player_mask].copy()

    summary = {
        "enabled": True,
        "allowed_source_prefixes": SOURCE_CONTRACT["allowed_source_prefixes"],
        "excluded_source_prefixes": SOURCE_CONTRACT["excluded_source_prefixes"],
        "matches_before": int(len(matches)),
        "matches_after": int(len(filtered_matches)),
        "players_before": int(len(players)),
        "players_after": int(len(filtered_players)),
        "excluded_match_sources": {
            str(source): int(count)
            for source, count in matches.loc[~match_mask, "source"].value_counts().items()
        },
    }
    return filtered_matches, filtered_players, summary


def _year_from_row(row: object) -> int | None:
    raw_year = getattr(row, "year", None)
    parsed_year = pd.to_numeric(raw_year, errors="coerce")
    if not pd.isna(parsed_year):
        return int(parsed_year)
    raw_date = getattr(row, "date", None)
    parsed_date = pd.to_datetime(raw_date, errors="coerce")
    if not pd.isna(parsed_date):
        return int(parsed_date.year)
    return None


def _load_split_membership(
    processed_dir: str,
    fallback_keys: set[str] | None = None,
) -> dict[str, set[str]]:
    """Use existing train/val/test match_key membership, or make a stable fallback."""
    result: dict[str, set[str]] = {}
    total = 0
    for split in ("train", "val", "test"):
        path = Path(processed_dir) / f"{split}.csv"
        if path.exists():
            try:
                df = pd.read_csv(path, usecols=["match_key"], low_memory=False)
                result[split] = set(df["match_key"].astype(str))
            except (pd.errors.EmptyDataError, ValueError):
                result[split] = set()
        else:
            result[split] = set()
        total += len(result[split])

    if total == 0 and fallback_keys:
        keys = np.array(sorted(fallback_keys))
        rng = np.random.default_rng(42)
        rng.shuffle(keys)
        n = len(keys)
        n_train = int(n * 0.70)
        n_val = int(n * 0.15)
        result = {
            "train": set(keys[:n_train].tolist()),
            "val": set(keys[n_train : n_train + n_val].tolist()),
            "test": set(keys[n_train + n_val :].tolist()),
        }
        print(
            "  [warn] existing split membership is empty; "
            f"created 70/15/15 random split (seed=42, {n:,} match_keys)"
        )
    return result


def _clean_key(raw: object) -> str:
    if raw is None or pd.isna(raw):
        return ""
    text = str(raw).strip()
    if not text or text.lower() == "nan":
        return ""
    return text.casefold()


def _normalize_role(agent: object, raw_role: object) -> str | None:
    normalized_agent = normalize_agent(str(agent)) if not pd.isna(agent) else None
    if normalized_agent:
        role = normalize_agent(normalized_agent)
        if role:
            from ml.valorant import AGENT_ROLE_MAP

            mapped = AGENT_ROLE_MAP.get(normalized_agent, "").lower()
            return mapped if mapped in ROLES else None
    if raw_role is None or pd.isna(raw_role):
        return None
    role_lower = str(raw_role).strip().lower()
    return role_lower if role_lower in ROLES else None


def _normalize_agent_key(raw: object) -> str | None:
    if raw is None or pd.isna(raw):
        return None
    normalized = normalize_agent(str(raw))
    if not normalized:
        return None
    return _agent_col_key(normalized)


def _enrich_player_stats(matches: pd.DataFrame, players: pd.DataFrame) -> pd.DataFrame:
    """Join rounds and derive per-round stats that become usable in later years."""
    match_rounds = matches[["match_key", "score_a", "score_b"]].copy()
    match_rounds["rounds"] = compute_rounds(
        pd.to_numeric(match_rounds["score_a"], errors="coerce"),
        pd.to_numeric(match_rounds["score_b"], errors="coerce"),
    )
    p = players.merge(match_rounds[["match_key", "rounds"]], on="match_key", how="left")
    safe_rounds = pd.to_numeric(p["rounds"], errors="coerce").replace(0, np.nan)
    p["apr"] = pd.to_numeric(p.get("assists"), errors="coerce") / safe_rounds
    p["fkpr"] = pd.to_numeric(p.get("fk"), errors="coerce") / safe_rounds
    p["fdpr"] = pd.to_numeric(p.get("fd"), errors="coerce") / safe_rounds
    for stat in HISTORY_STATS:
        if stat not in p.columns:
            p[stat] = 0.0
        p[stat] = pd.to_numeric(p[stat], errors="coerce").fillna(0.0)
    return p


def _build_match_inputs(matches: pd.DataFrame, players: pd.DataFrame) -> dict[str, MatchInput]:
    p = players[players["side"].isin(["a", "b"])].copy()
    p["player_slot"] = pd.to_numeric(p.get("player_slot"), errors="coerce").fillna(99)
    p = p.sort_values(["match_key", "side", "player_slot", "player"])

    sides_by_match: dict[str, dict[str, list[PlayerInput]]] = defaultdict(
        lambda: {"a": [], "b": []}
    )
    for row in p.itertuples(index=False):
        player_key = _clean_key(getattr(row, "player", ""))
        if not player_key:
            continue
        agent_key = _normalize_agent_key(getattr(row, "agent", None))
        role = _normalize_role(getattr(row, "agent", None), getattr(row, "role", None))
        stats = {stat: float(getattr(row, stat, 0.0) or 0.0) for stat in HISTORY_STATS}
        side = str(getattr(row, "side"))
        if len(sides_by_match[str(row.match_key)][side]) < 5:
            sides_by_match[str(row.match_key)][side].append(
                PlayerInput(player_key=player_key, agent_key=agent_key, role=role, stats=stats)
            )

    match_inputs: dict[str, MatchInput] = {}
    for row in matches.itertuples(index=False):
        match_key = str(row.match_key)
        sides = sides_by_match.get(match_key, {"a": [], "b": []})
        if len(sides["a"]) != 5 or len(sides["b"]) != 5:
            continue
        raw_map = getattr(row, "map", None)
        match_inputs[match_key] = MatchInput(
            match_key=match_key,
            year=_year_from_row(row),
            map_name=normalize_map(str(raw_map)) if not pd.isna(raw_map) else None,
            sides=sides,
        )
    return match_inputs


def _map_features(match_input: MatchInput) -> dict[str, float]:
    return {
        col: float(match_input.map_name == col.removeprefix("map_").title())
        for col in MAP_COLS
    }


def _composition_features(
    match_input: MatchInput,
    agent_keys: list[str] | None = None,
    include_diff: bool = True,
) -> dict[str, float]:
    if agent_keys is None:
        agent_keys = MODELED_AGENT_KEYS
    features: dict[str, float] = {}
    for role in ROLES:
        a_count = sum(1 for player in match_input.sides["a"] if player.role == role)
        b_count = sum(1 for player in match_input.sides["b"] if player.role == role)
        features[f"a_role_{role}_count"] = float(a_count)
        features[f"b_role_{role}_count"] = float(b_count)
        if include_diff:
            features[f"diff_role_{role}_count"] = float(a_count - b_count)

    for agent in agent_keys:
        a_count = sum(1 for player in match_input.sides["a"] if player.agent_key == agent)
        b_count = sum(1 for player in match_input.sides["b"] if player.agent_key == agent)
        features[f"a_agent_{agent}_count"] = float(a_count)
        features[f"b_agent_{agent}_count"] = float(b_count)
        if include_diff:
            features[f"diff_agent_{agent}_count"] = float(a_count - b_count)
    return features


def _history_features_for_player(
    player: PlayerInput,
    player_histories: dict[str, dict[str, RunningStats]],
    global_histories: dict[str, RunningStats],
) -> dict[str, float]:
    features: dict[str, float] = {}
    for scope in PRIOR_WINDOW_YEARS:
        prefix = "" if scope == "all" else f"{scope}_"
        hist = player_histories[scope].get(player.player_key)
        global_history = global_histories[scope]
        features[f"{prefix}prior_games"] = float(hist.games if hist else 0)
        for stat in HISTORY_STATS:
            features[f"{prefix}prior_{stat}"] = (
                hist.smoothed_avg(stat, global_history) if hist else 0.0
            )
    return features


def _aggregate_side_features(
    side: str,
    bases: list[str],
    player_values: list[dict[str, float]],
) -> dict[str, float]:
    features: dict[str, float] = {}
    for base in bases:
        values = np.array([float(row.get(base, 0.0)) for row in player_values], dtype=float)
        if len(values) == 0:
            values = np.array([0.0], dtype=float)
        features[f"{side}_{base}_mean"] = float(np.mean(values))
    return features


def _aggregate_team_history(
    match_input: MatchInput,
    player_histories: dict[str, dict[str, RunningStats]],
    global_histories: dict[str, RunningStats],
    include_diff: bool = True,
) -> dict[str, float]:
    by_side: dict[str, list[dict[str, float]]] = {"a": [], "b": []}
    for side in ("a", "b"):
        by_side[side] = [
            _history_features_for_player(
                player,
                player_histories,
                global_histories,
            )
            for player in match_input.sides[side]
        ]

    features: dict[str, float] = {}
    a_features = _aggregate_side_features("a", ALL_PLAYER_PRIOR_BASES, by_side["a"])
    b_features = _aggregate_side_features("b", ALL_PLAYER_PRIOR_BASES, by_side["b"])
    features.update(a_features)
    features.update(b_features)
    if include_diff:
        for base in ALL_PLAYER_PRIOR_BASES:
            features[f"diff_{base}_mean"] = features[f"a_{base}_mean"] - features[f"b_{base}_mean"]
    return features


def _synergy_features(
    match_input: MatchInput,
    pair_history: dict[tuple[str, str], int],
    include_diff: bool = True,
) -> dict[str, float]:
    def side_mean(side: str) -> float:
        players = sorted({player.player_key for player in match_input.sides[side]})
        if len(players) < 2:
            return 0.0
        counts = [
            pair_history[(left, right)]
            for left, right in combinations(players, 2)
        ]
        return float(np.mean(counts)) if counts else 0.0

    a_mean = side_mean("a")
    b_mean = side_mean("b")
    result = {"a_synergy_mean": a_mean, "b_synergy_mean": b_mean}
    if include_diff:
        result["diff_synergy_mean"] = a_mean - b_mean
    return result


def _combine_keyed_histories(
    keyed_history_by_year: dict[int, dict[tuple[str, str], "RunningStats"]],
    years: Iterable[int],
) -> dict[tuple[str, str], "RunningStats"]:
    combined: dict[tuple[str, str], RunningStats] = defaultdict(RunningStats)
    for year in years:
        for key, stats in keyed_history_by_year.get(year, {}).items():
            combined[key].merge(stats)
    return combined


def _map_agent_features(
    match_input: MatchInput,
    map_agent_histories: dict[tuple[str, str], RunningStats],
    global_history: RunningStats,
    include_diff: bool = True,
) -> dict[str, float]:
    features: dict[str, float] = {}
    map_name = match_input.map_name or ""
    for side in ("a", "b"):
        side_vals: list[dict[str, float]] = []
        for player in match_input.sides[side]:
            if not player.agent_key or not map_name:
                side_vals.append({stat: 0.0 for stat in HISTORY_STATS})
                continue
            hist = map_agent_histories.get((player.agent_key, map_name))
            side_vals.append({
                stat: hist.smoothed_avg(stat, global_history) if hist else 0.0
                for stat in HISTORY_STATS
            })
        for stat in HISTORY_STATS:
            vals = [row[stat] for row in side_vals]
            features[f"{side}_map_agent_{stat}_mean"] = float(np.mean(vals)) if vals else 0.0
    if include_diff:
        for stat in HISTORY_STATS:
            features[f"diff_map_agent_{stat}_mean"] = (
                features[f"a_map_agent_{stat}_mean"] - features[f"b_map_agent_{stat}_mean"]
            )
    return features


def _player_agent_features(
    match_input: MatchInput,
    player_agent_histories: dict[tuple[str, str], RunningStats],
    global_history: RunningStats,
    include_diff: bool = True,
) -> dict[str, float]:
    features: dict[str, float] = {}
    for side in ("a", "b"):
        side_vals: list[dict[str, float]] = []
        for player in match_input.sides[side]:
            if not player.agent_key:
                side_vals.append({stat: 0.0 for stat in HISTORY_STATS})
                continue
            hist = player_agent_histories.get((player.player_key, player.agent_key))
            side_vals.append({
                stat: hist.smoothed_avg(stat, global_history) if hist else 0.0
                for stat in HISTORY_STATS
            })
        for stat in HISTORY_STATS:
            vals = [row[stat] for row in side_vals]
            features[f"{side}_player_agent_{stat}_mean"] = float(np.mean(vals)) if vals else 0.0
    if include_diff:
        for stat in HISTORY_STATS:
            features[f"diff_player_agent_{stat}_mean"] = (
                features[f"a_player_agent_{stat}_mean"] - features[f"b_player_agent_{stat}_mean"]
            )
    return features


def _build_feature_row(
    match_input: MatchInput,
    player_histories: dict[str, dict[str, RunningStats]],
    global_histories: dict[str, RunningStats],
    pair_history: dict[tuple[str, str], int],
    map_agent_histories: dict[tuple[str, str], RunningStats],
    player_agent_histories: dict[tuple[str, str], RunningStats],
    agent_keys: list[str] | None = None,
    include_diff: bool = True,
) -> dict[str, float | str]:
    row: dict[str, float | str] = {"match_key": match_input.match_key}
    row.update(_map_features(match_input))
    row.update(_composition_features(match_input, agent_keys=agent_keys, include_diff=include_diff))
    row.update(_aggregate_team_history(match_input, player_histories, global_histories, include_diff=include_diff))
    row.update(_synergy_features(match_input, pair_history, include_diff=include_diff))
    row.update(_map_agent_features(match_input, map_agent_histories, global_histories["all"], include_diff=include_diff))
    row.update(_player_agent_features(match_input, player_agent_histories, global_histories["all"], include_diff=include_diff))
    return row


def _update_history_for_matches(
    match_inputs: Iterable[MatchInput],
    player_history_by_year: dict[int, dict[str, RunningStats]],
    global_history_by_year: dict[int, RunningStats],
    pair_history: dict[tuple[str, str], int],
    map_agent_history_by_year: dict[int, dict[tuple[str, str], RunningStats]],
    player_agent_history_by_year: dict[int, dict[tuple[str, str], RunningStats]],
) -> None:
    for match_input in match_inputs:
        if match_input.year is None:
            continue
        year = int(match_input.year)
        for side in ("a", "b"):
            side_players = match_input.sides[side]
            for player in side_players:
                player_history_by_year[year][player.player_key].add(player.stats)
                global_history_by_year[year].add(player.stats)

            unique_players = sorted({player.player_key for player in side_players})
            for left, right in combinations(unique_players, 2):
                pair_history[(left, right)] += 1

        # map×agent and player×agent tracking
        for side in ("a", "b"):
            for player in match_input.sides[side]:
                if player.agent_key and match_input.map_name:
                    map_agent_history_by_year[year][(player.agent_key, match_input.map_name)].add(player.stats)
                if player.agent_key:
                    player_agent_history_by_year[year][(player.player_key, player.agent_key)].add(player.stats)


def _history_years(current_year: int, window_years: int | None, known_years: Iterable[int]) -> list[int]:
    previous_years = [year for year in known_years if year < current_year]
    if window_years is None:
        return sorted(previous_years)
    lower = current_year - window_years
    return sorted(year for year in previous_years if lower <= year)


def _combine_player_histories(
    player_history_by_year: dict[int, dict[str, RunningStats]],
    years: Iterable[int],
) -> dict[str, RunningStats]:
    combined: dict[str, RunningStats] = defaultdict(RunningStats)
    for year in years:
        for player_key, stats in player_history_by_year.get(year, {}).items():
            combined[player_key].merge(stats)
    return combined


def _combine_global_history(
    global_history_by_year: dict[int, RunningStats],
    years: Iterable[int],
) -> RunningStats:
    combined = RunningStats()
    for year in years:
        combined.merge(global_history_by_year.get(year, RunningStats()))
    return combined


def _prior_histories_for_year(
    current_year: int,
    player_history_by_year: dict[int, dict[str, RunningStats]],
    global_history_by_year: dict[int, RunningStats],
) -> tuple[dict[str, dict[str, RunningStats]], dict[str, RunningStats]]:
    known_years = player_history_by_year.keys()
    player_histories: dict[str, dict[str, RunningStats]] = {}
    global_histories: dict[str, RunningStats] = {}
    for scope, window_years in PRIOR_WINDOW_YEARS.items():
        years = _history_years(current_year, window_years, known_years)
        player_histories[scope] = _combine_player_histories(player_history_by_year, years)
        global_histories[scope] = _combine_global_history(global_history_by_year, years)
    return player_histories, global_histories


def _empty_prior_histories() -> tuple[dict[str, dict[str, RunningStats]], dict[str, RunningStats]]:
    return (
        {scope: defaultdict(RunningStats) for scope in PRIOR_WINDOW_YEARS},
        {scope: RunningStats() for scope in PRIOR_WINDOW_YEARS},
    )


def _build_previous_year_features(
    match_inputs: dict[str, MatchInput],
    feature_cols: list[str] | None = None,
    agent_keys: list[str] | None = None,
    include_diff: bool = True,
) -> pd.DataFrame:
    if feature_cols is None:
        feature_cols = FEATURE_COLS
    known_year = [row for row in match_inputs.values() if row.year is not None]
    missing_year = [row for row in match_inputs.values() if row.year is None]
    known_year.sort(key=lambda row: (row.year, row.match_key))
    missing_year.sort(key=lambda row: row.match_key)

    player_history_by_year: dict[int, dict[str, RunningStats]] = defaultdict(
        lambda: defaultdict(RunningStats)
    )
    global_history_by_year: dict[int, RunningStats] = defaultdict(RunningStats)
    pair_history: dict[tuple[str, str], int] = defaultdict(int)
    map_agent_history_by_year: dict[int, dict[tuple[str, str], RunningStats]] = defaultdict(
        lambda: defaultdict(RunningStats)
    )
    player_agent_history_by_year: dict[int, dict[tuple[str, str], RunningStats]] = defaultdict(
        lambda: defaultdict(RunningStats)
    )

    feature_rows: list[dict[str, float | str]] = []
    for year, same_year_iter in groupby(known_year, key=lambda row: row.year):
        same_year_matches = list(same_year_iter)
        player_histories, global_histories = _prior_histories_for_year(
            int(year),
            player_history_by_year,
            global_history_by_year,
        )
        years_for_all = _history_years(int(year), None, player_history_by_year.keys())
        map_agent_histories = _combine_keyed_histories(map_agent_history_by_year, years_for_all)
        player_agent_histories = _combine_keyed_histories(player_agent_history_by_year, years_for_all)
        for match_input in same_year_matches:
            feature_rows.append(
                _build_feature_row(
                    match_input,
                    player_histories,
                    global_histories,
                    pair_history,
                    map_agent_histories,
                    player_agent_histories,
                    agent_keys=agent_keys,
                    include_diff=include_diff,
                )
            )
        _update_history_for_matches(
            same_year_matches,
            player_history_by_year,
            global_history_by_year,
            pair_history,
            map_agent_history_by_year,
            player_agent_history_by_year,
        )

    empty_player_histories, empty_global_histories = _empty_prior_histories()
    empty_pair_history: dict[tuple[str, str], int] = defaultdict(int)
    empty_map_agent: dict[tuple[str, str], RunningStats] = defaultdict(RunningStats)
    empty_player_agent: dict[tuple[str, str], RunningStats] = defaultdict(RunningStats)
    for match_input in missing_year:
        feature_rows.append(
            _build_feature_row(
                match_input,
                empty_player_histories,
                empty_global_histories,
                empty_pair_history,
                empty_map_agent,
                empty_player_agent,
                agent_keys=agent_keys,
                include_diff=include_diff,
            )
        )

    features = pd.DataFrame(feature_rows)
    for col in feature_cols:
        if col not in features.columns:
            features[col] = 0.0
    return features[["match_key"] + feature_cols]


def previous_year_global_earliest_audit(processed_dir: str = "data/processed") -> dict:
    """Verify that the global earliest valid year has no history-derived values."""
    matches = _load_matches(processed_dir)
    players = _load_players(processed_dir)
    matches, players, source_summary = _filter_allowed_sources(matches, players)
    enriched_players = _enrich_player_stats(matches, players)
    match_inputs = _build_match_inputs(matches, enriched_players)
    known_year = [row for row in match_inputs.values() if row.year is not None]
    if not known_year:
        return {
            "status": "WARN",
            "reason": "no valid year 5v5 matches available for previous-year audit",
            "max_abs_history_value": None,
        }
    earliest = min(row.year for row in known_year if row.year is not None)
    earliest_inputs = {
        row.match_key: row
        for row in known_year
        if row.year == earliest
    }
    features = _build_previous_year_features(earliest_inputs)
    history_cols = [
        col
        for col in FEATURE_COLS
        if "prior" in col or "synergy" in col
    ]
    max_abs = float(features[history_cols].abs().to_numpy().max()) if history_cols else 0.0
    return {
        "status": "PASS" if max_abs <= 1e-9 else "FAIL",
        "earliest_year": int(earliest),
        "rows_checked": int(len(features)),
        "max_abs_history_value": max_abs,
        "scope": "global_valid_5v5_raw_inputs",
        "source_filter": source_summary,
    }


def build_features(
    processed_dir: str = "data/processed",
    feature_contract: str = "baseline",
) -> pd.DataFrame:
    """Return previous-year features plus metadata and split."""
    if feature_contract == "advanced":
        feature_cols = FEATURE_COLS_ADVANCED
        agent_keys = MODELED_AGENT_KEYS_ADVANCED
        include_diff = False
    else:
        feature_cols = FEATURE_COLS
        agent_keys = MODELED_AGENT_KEYS
        include_diff = True

    matches = _load_matches(processed_dir)
    players = _load_players(processed_dir)
    matches, players, source_summary = _filter_allowed_sources(matches, players)
    print(
        f"  matches={len(matches):,}, players={len(players):,}, "
        f"players match_keys={players['match_key'].nunique():,}"
    )
    if source_summary.get("enabled"):
        print(
            "  source_filter="
            f"{source_summary['allowed_source_prefixes']}, "
            f"excluded_matches={source_summary['matches_before'] - source_summary['matches_after']:,}, "
            f"excluded_player_rows={source_summary['players_before'] - source_summary['players_after']:,}"
        )

    enriched_players = _enrich_player_stats(matches, players)
    match_inputs = _build_match_inputs(matches, enriched_players)
    feature_frame = _build_previous_year_features(
        match_inputs,
        feature_cols=feature_cols,
        agent_keys=agent_keys,
        include_diff=include_diff,
    )
    print(
        f"  valid 5v5 match_keys={len(match_inputs):,}, "
        f"feature_rows={len(feature_frame):,}, feature_cols={len(feature_cols):,}"
    )

    meta_cols = [
        c
        for c in (
            "match_key",
            "dedup_key",
            "date",
            "year",
            "event",
            "map",
            "team_a",
            "team_b",
            "label",
            "source",
            "provenance",
        )
        if c in matches.columns
    ]
    out = matches[meta_cols].copy()
    out["match_key"] = out["match_key"].astype(str)
    out = out.merge(feature_frame, on="match_key", how="inner")

    splits = _load_split_membership(
        processed_dir,
        fallback_keys=set(out["match_key"].tolist()),
    )

    def assign_split(match_key: str) -> str:
        for split in ("train", "val", "test"):
            if match_key in splits[split]:
                return split
        return "unknown"

    out["split"] = out["match_key"].map(assign_split)
    out = out[out["split"] != "unknown"].copy()

    for col in feature_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)

    forbidden = find_forbidden_feature_names(feature_cols)
    if forbidden:
        raise RuntimeError(f"Forbidden features detected: {forbidden}")
    return out


def save_splits(
    out: pd.DataFrame,
    processed_dir: str = "data/processed",
    output_dir: str | None = None,
) -> None:
    target = output_dir if output_dir else processed_dir
    Path(target).mkdir(parents=True, exist_ok=True)
    for split in ("train", "val", "test"):
        sub = out[out["split"] == split].copy()
        path = Path(target) / f"{split}.csv"
        sub.to_csv(path, index=False)
        print(f"  {split}: {len(sub):,} rows, {len(sub.columns)} columns -> {path}")


def run_preprocess(
    feature_contract: str = "baseline",
    processed_dir: str = "data/processed",
    output_dir: str | None = None,
) -> None:
    """전처리 실행. feature_contract='advanced'이면 data/processed/adv_kaggle_only/에 저장."""
    if output_dir is None:
        output_dir = (
            "data/processed/adv_kaggle_only" if feature_contract == "advanced" else processed_dir
        )
    print(f"Building {feature_contract} features from {processed_dir}/ ...")
    out = build_features(processed_dir, feature_contract=feature_contract)
    print(f"Total: {len(out):,} rows, {len(out.columns)} columns")
    save_splits(out, processed_dir=processed_dir, output_dir=output_dir)
    feature_cols = FEATURE_COLS_ADVANCED if feature_contract == "advanced" else FEATURE_COLS
    for split in ("train", "val", "test"):
        df = load_split(split, base=output_dir)
        X, y, groups = build_xy(df, feature_contract=feature_contract)
        print(
            f"  {split}: X={X.shape}, y={y.shape}, "
            f"matches={groups.nunique():,}, label_rate={y.mean():.3f}"
        )


def main(processed_dir: str = "data/processed", feature_contract: str = "baseline") -> None:
    run_preprocess(
        feature_contract=feature_contract,
        processed_dir=processed_dir,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/processed")
    parser.add_argument("--feature-contract", default="baseline", choices=["baseline", "advanced"])
    args = parser.parse_args()
    main(args.input, args.feature_contract)
