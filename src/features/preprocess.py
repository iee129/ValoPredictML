"""Previous-year baseline feature builder.

The baseline input contract is intentionally the same shape as the future UI:
map + five player-agent pairs for team A + five player-agent pairs for team B.
Every numeric player signal is a previous-year aggregate. If a match belongs to
2024, only player history from years before 2024 is available to the model.
Player prior metrics are smoothed toward the matching previous-year league
average, and short year windows are also exposed for the last one and two years.

Usage:
    python -m features.preprocess
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict, deque
from dataclasses import dataclass, field
from itertools import combinations, groupby
from pathlib import Path
from typing import Iterable, Deque

import numpy as np
import pandas as pd
from sklearn.ensemble import VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from domain.agent_roles import ATK_ADV_MAP
from domain.valorant import (
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
    "allowed_source_prefixes": ["kaggle_", "vlrgg_"],
    "excluded_source_prefixes": [],
    "description": "Active baseline uses Kaggle and VLR.gg sources; both prefixes are allowed.",
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

# Advanced contract v4: 179 features
# Redesign: removed agent count 42 + role count 8 + team_priorform 3 (serve skew)
# Added: role archetype 6 + comp_meta_wr 3 + team_dist(max/std kd) 6
# Added: history reliability/coverage 21 so the model can distinguish strong
# historical priors from cold-start or low-sample priors.
RARE_AGENTS: list[str] = [
    "veto", "waylay", "clove", "iso", "deadlock", "vyse", "tejo", "harbor",
]
HISTORY_STATS_NO_CLUTCH: list[str] = [s for s in HISTORY_STATS if s != "clutch"]
_ADV_MA_STAT_COLS: list[str] = (
    [f"a_map_agent_{s}_mean" for s in HISTORY_STATS]
    + [f"b_map_agent_{s}_mean" for s in HISTORY_STATS]
)
_ADV_PA_STAT_COLS: list[str] = (
    [f"a_player_agent_{s}_mean" for s in HISTORY_STATS]
    + [f"b_player_agent_{s}_mean" for s in HISTORY_STATS]
)

# Maps without Drift (deathmatch-only)
_MAP_COLS_ADV = [f"map_{m.lower()}" for m in MAP_ORDER if m.lower() != "drift"]

# Internal-use only: agent/role count cols are computed by _build_feature_row and
# used by _apply_advanced_transforms (agent_map_fit, role_balance, comp_meta_wr),
# but are NOT included in FEATURE_COLS_ADVANCED (replaced by dense archetypes).
ROLE_COUNT_COLS_ADV = [
    col
    for role in ROLES
    for col in (f"a_role_{role}_count", f"b_role_{role}_count")
]

# Non-rare, non-miks agents + other bucket
_MODELED_AGENT_KEYS_ADV = [
    a for a in AGENTS_SORTED if a != "miks" and a not in RARE_AGENTS
]
MODELED_AGENT_KEYS_ADVANCED = _MODELED_AGENT_KEYS_ADV  # public alias used by predict.py
AGENT_COUNT_COLS_ADV = (
    [
        col
        for agent in _MODELED_AGENT_KEYS_ADV
        for col in (f"a_agent_{agent}_count", f"b_agent_{agent}_count")
    ]
    + ["a_agent_other_count", "b_agent_other_count"]
)

# Prior stats without clutch + diff (21 features)
_PRIOR_BASES_NO_CLUTCH = [b for b in ALL_PLAYER_PRIOR_BASES if "clutch" not in b]
PLAYER_PRIOR_COLS_ADV = [
    col
    for base in _PRIOR_BASES_NO_CLUTCH
    for col in (f"a_{base}_mean", f"b_{base}_mean", f"diff_{base}_mean")
]

SYNERGY_COLS_ADV = ["a_synergy_mean", "b_synergy_mean", "diff_synergy_mean"]

MAP_AGENT_COLS_ADV = [
    col
    for stat in HISTORY_STATS_NO_CLUTCH
    for col in (
        f"a_map_agent_{stat}_mean",
        f"b_map_agent_{stat}_mean",
        f"diff_map_agent_{stat}_mean",
    )
]
PLAYER_AGENT_COLS_ADV = [
    col
    for stat in HISTORY_STATS_NO_CLUTCH
    for col in (
        f"a_player_agent_{stat}_mean",
        f"b_player_agent_{stat}_mean",
        f"diff_player_agent_{stat}_mean",
    )
]

# NEW: dense role archetype signals (6) — replaces sparse role+agent count 50 cols
ROLE_ARCHETYPE_COLS_ADV = [
    "a_has_controller", "b_has_controller",
    "a_has_initiator", "b_has_initiator",
    "a_double_duelist", "b_double_duelist",
]

# NEW: meta composition win rate a/b/diff (3)
COMP_META_COLS_ADV = ["a_comp_meta_wr", "b_comp_meta_wr", "diff_comp_meta_wr"]

# NEW: team skill distribution max/std kd a/b/diff (6)
TEAM_DIST_COLS_ADV = [
    "a_max_prior_kd", "b_max_prior_kd", "diff_max_prior_kd",
    "a_std_prior_kd", "b_std_prior_kd", "diff_std_prior_kd",
]
HISTORY_RELIABILITY_BASES_ADV = [
    "known_player_ratio",
    "low_sample_player_ratio",
    "map_agent_games_mean",
    "map_agent_known_ratio",
    "player_agent_games_mean",
    "player_agent_known_ratio",
    "history_coverage_mean",
]
HISTORY_RELIABILITY_COLS_ADV = [
    col
    for base in HISTORY_RELIABILITY_BASES_ADV
    for col in (f"a_{base}", f"b_{base}", f"diff_{base}")
]
TEAM_CONTEXT_BASES_ADV = [
    "team_games",
    "team_success",
    "team_margin_mean",
    "team_map_games",
    "team_map_success",
    "team_map_margin_mean",
    "team_event_games",
    "team_event_success",
]
TEAM_CONTEXT_COLS_ADV = [
    col
    for base in TEAM_CONTEXT_BASES_ADV
    for col in (f"a_{base}", f"b_{base}", f"diff_{base}")
]
TEAM_FORM_BASES_ADV = [
    "team_form5_success",
    "team_form5_margin_mean",
    "team_form10_success",
    "team_form10_margin_mean",
]
TEAM_FORM_COLS_ADV = [
    col
    for base in TEAM_FORM_BASES_ADV
    for col in (f"a_{base}", f"b_{base}", f"diff_{base}")
]
ROSTER_CONTEXT_BASES_ADV = [
    "roster_pair_games_mean",
    "roster_pair_known_ratio",
    "roster_prev_overlap_ratio",
]
ROSTER_CONTEXT_COLS_ADV = [
    col
    for base in ROSTER_CONTEXT_BASES_ADV
    for col in (f"a_{base}", f"b_{base}", f"diff_{base}")
]
COMP_CONTEXT_BASES_ADV = [
    "comp_games",
    "comp_success",
    "comp_low_sample_ratio",
]
COMP_CONTEXT_COLS_ADV = [
    col
    for base in COMP_CONTEXT_BASES_ADV
    for col in (f"a_{base}", f"b_{base}", f"diff_{base}")
]
RELIABILITY_INTERACTION_BASES_ADV = [
    "prior_kd_x_history_coverage",
    "player_agent_kd_x_known_ratio",
    "agent_map_fit_x_known_ratio",
]
RELIABILITY_INTERACTION_COLS_ADV = [
    col
    for base in RELIABILITY_INTERACTION_BASES_ADV
    for col in (f"a_{base}", f"b_{base}", f"diff_{base}")
]

FEATURE_COLS_ADVANCED: list[str] = (
    _MAP_COLS_ADV                    # 12: map one-hot (no drift)
    + PLAYER_PRIOR_COLS_ADV          # 21: player prior a/b/diff (no clutch)
    + SYNERGY_COLS_ADV               # 3:  synergy a/b/diff
    + MAP_AGENT_COLS_ADV             # 18: map×agent (no clutch) a/b/diff
    + PLAYER_AGENT_COLS_ADV          # 18: player×agent (no clutch) a/b/diff
    + ["map_agent_history_missing", "player_agent_history_missing"]  # 2: cold-start flags
    + ["map_atk_adv"]                # 1:  map attack advantage
    + ["a_agent_map_fit_sum", "b_agent_map_fit_sum", "diff_agent_map_fit"]  # 3
    + ["a_role_balance", "b_role_balance"]  # 2: role diversity entropy
    + ROLE_ARCHETYPE_COLS_ADV        # 6:  dense archetype signals
    + COMP_META_COLS_ADV             # 3:  meta composition win rate
    + TEAM_DIST_COLS_ADV             # 6:  team skill distribution
    + HISTORY_RELIABILITY_COLS_ADV   # 21: history sample size / coverage reliability
    + TEAM_CONTEXT_COLS_ADV          # 24: team, team×map, team×event prior context
    + TEAM_FORM_COLS_ADV             # 12: last-5/last-10 historical team form
    + ROSTER_CONTEXT_COLS_ADV        # 9:  roster pair history and previous roster overlap
    + COMP_CONTEXT_COLS_ADV          # 9:  map composition sample size / success reliability
    + RELIABILITY_INTERACTION_COLS_ADV  # 9: performance × reliability interaction terms
    # Removed from v1 (133): role count 8, agent count 42, team_priorform 3 (serve skew)
)
EXPECTED_FEATURE_COUNT_ADVANCED = 179
if len(FEATURE_COLS_ADVANCED) != EXPECTED_FEATURE_COUNT_ADVANCED:
    raise RuntimeError(
        f"Advanced contract requires {EXPECTED_FEATURE_COUNT_ADVANCED} features, "
        f"got {len(FEATURE_COLS_ADVANCED)}"
    )
FEATURE_CONTRACT_ADVANCED = (
    "map one-hot (no drift), player prior (no clutch) a/b/diff, synergy a/b/diff, "
    "map×agent (no clutch) a/b/diff, player×agent (no clutch) a/b/diff, "
    "cold-start missing flags, map atk advantage, agent-map fit sum a/b/diff, "
    "role diversity entropy a/b, role archetype (has_controller/initiator/double_duelist) a/b, "
    "meta composition win rate a/b/diff, team skill distribution (max/std kd) a/b/diff; "
    "history reliability coverage (known player, low-sample, map-agent and player-agent coverage) a/b/diff; "
    "strict-before team context, team form, roster continuity, comp sample reliability, "
    "and performance×reliability interactions; team_priorform removed (serve skew); same year stats excluded"
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

def _build_comp_meta_lookup(insights_dir: str) -> dict[tuple[str, str], float]:
    """(map_title, sorted_agent_key_string) → meta win rate from reports/insights/meta_comps.json."""
    path = Path(insights_dir) / "meta_comps.json"
    if not path.exists():
        return {}
    data: dict = json.loads(path.read_text())
    lookup: dict[tuple[str, str], float] = {}
    for map_name, comps in data.items():
        for entry in comps:
            agents_title = str(entry.get("comp", "")).split("|")
            # convert title-case agent names back to column keys for lookup consistency
            agents_key = sorted(_agent_col_key(a) for a in agents_title if a.strip())
            comp_key = "|".join(agents_key)
            lookup[(str(map_name).title(), comp_key)] = float(entry.get("win_rate", 0.5))
    return lookup


def _build_agent_map_fit_lookup(insights_dir: str) -> dict[tuple[str, str], float]:
    """(map_title, agent_col_key) → win_rate. Empty dict if file missing."""
    path = Path(insights_dir) / "agent_map_fit.json"
    if not path.exists():
        return {}
    data: dict = json.loads(path.read_text())
    lookup: dict[tuple[str, str], float] = {}
    for map_name, agents in data.items():
        for agent_title, score in agents.items():
            lookup[(str(map_name).title(), _agent_col_key(agent_title))] = float(score)
    return lookup


def compute_adv_impute_means(df: pd.DataFrame) -> dict[str, float]:
    """Compute per-column nonzero means for cold-start imputation.

    Must be called on the TRAINING split only. Pass the result to subsequent
    build_xy / _apply_advanced_transforms calls for test/val splits.
    """
    all_cols = [c for c in _ADV_MA_STAT_COLS + _ADV_PA_STAT_COLS if c in df.columns]
    means: dict[str, float] = {}
    for col in all_cols:
        nonzero = df.loc[df[col] != 0.0, col]
        means[col] = float(nonzero.mean()) if len(nonzero) > 0 else 0.0
    return means


def _apply_advanced_transforms(
    df: pd.DataFrame,
    team_priorform_lookup: dict | None = None,  # deprecated, no longer used (serve skew removed)
    impute_means: dict[str, float] | None = None,
    agent_map_fit_lookup: dict[tuple[str, str], float] | None = None,
    comp_meta_lookup: dict[tuple[str, str], float] | None = None,
) -> pd.DataFrame:
    """Apply all advanced v2 transforms to a pre-loaded feature DataFrame."""
    df = df.copy()

    # diff cols for non-clutch prior bases
    for base in _PRIOR_BASES_NO_CLUTCH:
        a_col, b_col = f"a_{base}_mean", f"b_{base}_mean"
        a_vals = pd.to_numeric(df.get(a_col, 0.0), errors="coerce").fillna(0.0)
        b_vals = pd.to_numeric(df.get(b_col, 0.0), errors="coerce").fillna(0.0)
        df[f"diff_{base}_mean"] = a_vals - b_vals

    # diff synergy
    df["diff_synergy_mean"] = (
        pd.to_numeric(df.get("a_synergy_mean", 0.0), errors="coerce").fillna(0.0)
        - pd.to_numeric(df.get("b_synergy_mean", 0.0), errors="coerce").fillna(0.0)
    )

    # diff map_agent / player_agent (no clutch)
    for stat in HISTORY_STATS_NO_CLUTCH:
        for prefix in ("map_agent", "player_agent"):
            a_col, b_col = f"a_{prefix}_{stat}_mean", f"b_{prefix}_{stat}_mean"
            a_v = pd.to_numeric(df.get(a_col, 0.0), errors="coerce").fillna(0.0)
            b_v = pd.to_numeric(df.get(b_col, 0.0), errors="coerce").fillna(0.0)
            df[f"diff_{prefix}_{stat}_mean"] = a_v - b_v

    # rare agent clustering (still computed for agent_map_fit_sum internal use)
    rare_a = [f"a_agent_{a}_count" for a in RARE_AGENTS if f"a_agent_{a}_count" in df.columns]
    rare_b = [f"b_agent_{a}_count" for a in RARE_AGENTS if f"b_agent_{a}_count" in df.columns]
    df["a_agent_other_count"] = df[rare_a].sum(axis=1).astype(float) if rare_a else 0.0
    df["b_agent_other_count"] = df[rare_b].sum(axis=1).astype(float) if rare_b else 0.0

    # cold-start missing flags
    ma_present = [c for c in _ADV_MA_STAT_COLS if c in df.columns]
    pa_present = [c for c in _ADV_PA_STAT_COLS if c in df.columns]
    df["map_agent_history_missing"] = (
        (df[ma_present] == 0.0).all(axis=1).astype(int) if ma_present else 0
    )
    df["player_agent_history_missing"] = (
        (df[pa_present] == 0.0).all(axis=1).astype(int) if pa_present else 0
    )

    # impute_means must be from the training split to avoid test leakage
    if impute_means:
        for col in ma_present + pa_present:
            zero_mask = df[col] == 0.0
            if zero_mask.any() and col in impute_means:
                df.loc[zero_mask, col] = impute_means[col]

    # map attack advantage (from ATK_ADV_MAP constant)
    if "map" in df.columns:
        df["map_atk_adv"] = [
            float(ATK_ADV_MAP.get(str(m).title(), 0.0)) if pd.notna(m) else 0.0
            for m in df["map"]
        ]
    else:
        df["map_atk_adv"] = 0.0

    # agent-map fit sum (historical win-rate prior per agent×map, uses internal agent count cols)
    if agent_map_fit_lookup and "map" in df.columns:
        map_titles = df["map"].map(lambda m: str(m).title() if pd.notna(m) else "")
        a_fit = np.zeros(len(df), dtype=float)
        b_fit = np.zeros(len(df), dtype=float)
        for agent in MODELED_AGENT_KEYS_ADVANCED:
            a_counts = pd.to_numeric(df.get(f"a_agent_{agent}_count", 0), errors="coerce").fillna(0.0).to_numpy()
            b_counts = pd.to_numeric(df.get(f"b_agent_{agent}_count", 0), errors="coerce").fillna(0.0).to_numpy()
            scores = np.fromiter(
                (agent_map_fit_lookup.get((m, agent), 0.5) for m in map_titles),
                dtype=float, count=len(df),
            )
            a_fit += a_counts * scores
            b_fit += b_counts * scores
        df["a_agent_map_fit_sum"] = a_fit
        df["b_agent_map_fit_sum"] = b_fit
        df["diff_agent_map_fit"] = a_fit - b_fit
    else:
        df["a_agent_map_fit_sum"] = 0.5
        df["b_agent_map_fit_sum"] = 0.5
        df["diff_agent_map_fit"] = 0.0

    # role balance entropy (0 = imbalanced, ~1 = perfectly spread across 4 roles)
    role_list = ["duelist", "initiator", "controller", "sentinel"]
    for side in ("a", "b"):
        counts = np.zeros((len(df), len(role_list)), dtype=float)
        for i, role in enumerate(role_list):
            col = f"{side}_role_{role}_count"
            if col in df.columns:
                counts[:, i] = pd.to_numeric(df[col], errors="coerce").fillna(0.0).to_numpy()
        totals = counts.sum(axis=1, keepdims=True)
        totals_safe = np.where(totals == 0, 1.0, totals)
        probs = counts / totals_safe
        with np.errstate(divide="ignore", invalid="ignore"):
            entropy = -(probs * np.log2(np.where(probs > 0, probs, 1.0))).sum(axis=1)
        df[f"{side}_role_balance"] = np.where(totals.squeeze() > 0, entropy / 2.0, 0.0)

    # role archetype features (dense signals replacing sparse agent/role count 50 cols)
    for side in ("a", "b"):
        duelist_arr = pd.to_numeric(df.get(f"{side}_role_duelist_count", 0), errors="coerce").fillna(0).to_numpy()
        controller_arr = pd.to_numeric(df.get(f"{side}_role_controller_count", 0), errors="coerce").fillna(0).to_numpy()
        initiator_arr = pd.to_numeric(df.get(f"{side}_role_initiator_count", 0), errors="coerce").fillna(0).to_numpy()
        df[f"{side}_has_controller"] = (controller_arr > 0).astype(float)
        df[f"{side}_has_initiator"] = (initiator_arr > 0).astype(float)
        df[f"{side}_double_duelist"] = (duelist_arr >= 2).astype(float)

    # meta composition win rate (from insights/meta_comps.json, uses internal agent count cols)
    if comp_meta_lookup and "map" in df.columns:
        map_titles_list = [str(m).title() if pd.notna(m) else "" for m in df["map"]]
        agent_presence: dict[tuple[str, str], np.ndarray] = {}
        for side in ("a", "b"):
            for agent in MODELED_AGENT_KEYS_ADVANCED:
                col = f"{side}_agent_{agent}_count"
                agent_presence[(side, agent)] = (
                    pd.to_numeric(df[col], errors="coerce").fillna(0).to_numpy()
                    if col in df.columns else np.zeros(len(df))
                )
        for side in ("a", "b"):
            meta_wrs = []
            for i in range(len(df)):
                agents = sorted(
                    agent for agent in MODELED_AGENT_KEYS_ADVANCED
                    if agent_presence[(side, agent)][i] > 0
                )
                comp_key = "|".join(agents)
                meta_wrs.append(comp_meta_lookup.get((map_titles_list[i], comp_key), 0.5))
            df[f"{side}_comp_meta_wr"] = meta_wrs
        df["diff_comp_meta_wr"] = (
            df["a_comp_meta_wr"].astype(float) - df["b_comp_meta_wr"].astype(float)
        )
    else:
        df["a_comp_meta_wr"] = 0.5
        df["b_comp_meta_wr"] = 0.5
        df["diff_comp_meta_wr"] = 0.0

    for base in (
        TEAM_CONTEXT_BASES_ADV
        + TEAM_FORM_BASES_ADV
        + ROSTER_CONTEXT_BASES_ADV
        + COMP_CONTEXT_BASES_ADV
    ):
        a_col, b_col = f"a_{base}", f"b_{base}"
        a_v = pd.to_numeric(df.get(a_col, 0.0), errors="coerce").fillna(0.0)
        b_v = pd.to_numeric(df.get(b_col, 0.0), errors="coerce").fillna(0.0)
        df[f"diff_{base}"] = a_v - b_v

    for side in ("a", "b"):
        prior_kd = pd.to_numeric(df.get(f"{side}_prior_kd_mean", 0.0), errors="coerce").fillna(0.0)
        coverage = pd.to_numeric(df.get(f"{side}_history_coverage_mean", 0.0), errors="coerce").fillna(0.0)
        pa_kd = pd.to_numeric(df.get(f"{side}_player_agent_kd_mean", 0.0), errors="coerce").fillna(0.0)
        pa_known = pd.to_numeric(df.get(f"{side}_player_agent_known_ratio", 0.0), errors="coerce").fillna(0.0)
        fit_sum = pd.to_numeric(df.get(f"{side}_agent_map_fit_sum", 0.0), errors="coerce").fillna(0.0)
        ma_known = pd.to_numeric(df.get(f"{side}_map_agent_known_ratio", 0.0), errors="coerce").fillna(0.0)
        df[f"{side}_prior_kd_x_history_coverage"] = prior_kd * coverage
        df[f"{side}_player_agent_kd_x_known_ratio"] = pa_kd * pa_known
        df[f"{side}_agent_map_fit_x_known_ratio"] = fit_sum * ma_known

    for base in RELIABILITY_INTERACTION_BASES_ADV:
        df[f"diff_{base}"] = (
            pd.to_numeric(df.get(f"a_{base}", 0.0), errors="coerce").fillna(0.0)
            - pd.to_numeric(df.get(f"b_{base}", 0.0), errors="coerce").fillna(0.0)
        )

    return df


@dataclass
class RunningStats:
    games: int = 0
    sums: dict[str, float] = field(default_factory=lambda: defaultdict(float))

    def add(self, values: dict[str, float]) -> None:
        self.games += 1
        # NaN values (e.g. kast from sources that don't collect it) propagate through sums;
        # tree-based models (XGB/LGBM) handle NaN natively via learned split direction.
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


@dataclass
class OutcomeStats:
    games: int = 0
    successes: float = 0.0
    margin_sum: float = 0.0

    def add(self, success: float, margin: float) -> None:
        self.games += 1
        self.successes += float(success)
        self.margin_sum += float(margin)

    def merge(self, other: "OutcomeStats") -> None:
        self.games += other.games
        self.successes += other.successes
        self.margin_sum += other.margin_sum

    def success_rate(self) -> float:
        return float(self.successes / self.games) if self.games else 0.5

    def margin_mean(self) -> float:
        return float(self.margin_sum / self.games) if self.games else 0.0


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
    team_keys: dict[str, str]
    event_key: str
    label: int | None
    margin_a: float
    sides: dict[str, list[PlayerInput]]


# Existing train/evaluate/validate interface.
def load_split(name: str, base: str = "data/processed") -> pd.DataFrame:
    return pd.read_csv(f"{base}/{name}.csv", low_memory=False)


def build_xy(
    df: pd.DataFrame,
    feature_contract: str = "baseline",
    processed_dir: str = "data/processed",
    impute_means: dict[str, float] | None = None,
    insights_dir: str = "reports/insights",
):
    """Return model X, label y, and match_key groups in canonical feature order.

    For the advanced contract, pass impute_means computed from the training split
    to avoid test-data leakage in cold-start mean imputation.
    Use compute_adv_impute_means(train_df) to obtain these means.
    """
    if feature_contract == "advanced":
        fit_lookup = _build_agent_map_fit_lookup(insights_dir)
        comp_meta_lookup = _build_comp_meta_lookup(insights_dir)
        df = _apply_advanced_transforms(df, None, impute_means, fit_lookup, comp_meta_lookup)
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


def _is_allowed_source(source: object, extra_prefixes: list[str] | None = None) -> bool:
    text = "" if source is None or pd.isna(source) else str(source)
    prefixes = SOURCE_CONTRACT["allowed_source_prefixes"] + (extra_prefixes or [])
    return any(text.startswith(p) for p in prefixes)


def _filter_allowed_sources(
    matches: pd.DataFrame,
    players: pd.DataFrame,
    include_vlrgg: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Apply the active baseline source contract before feature construction.

    Args:
        include_vlrgg: if True, adds "vlrgg_" to allowed prefixes (런 한정 오버라이드).
                       기본값은 False — kaggle-only 레인 불변.
    """
    if "source" not in matches.columns:
        return matches, players, {"enabled": False, "reason": "matches has no source column"}

    extra = ["vlrgg_"] if include_vlrgg else []
    effective_prefixes = list(dict.fromkeys(SOURCE_CONTRACT["allowed_source_prefixes"] + extra))
    match_mask = matches["source"].map(lambda s: _is_allowed_source(s, extra))
    filtered_matches = matches[match_mask].copy()
    allowed_match_keys = set(filtered_matches["match_key"].astype(str))

    if "source" in players.columns:
        player_mask = (
            players["match_key"].astype(str).isin(allowed_match_keys)
            & players["source"].map(lambda s: _is_allowed_source(s, extra))
        )
    else:
        player_mask = players["match_key"].astype(str).isin(allowed_match_keys)
    filtered_players = players[player_mask].copy()

    summary = {
        "enabled": True,
        "allowed_source_prefixes": effective_prefixes,
        "include_vlrgg": include_vlrgg,
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
    """Use existing train/test match_key membership, or make a stable 80/20 fallback."""
    result: dict[str, set[str]] = {}
    total = 0
    for split in ("train", "test"):
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
        n_train = int(n * 0.80)
        result = {
            "train": set(keys[:n_train].tolist()),
            "test": set(keys[n_train:].tolist()),
        }
        print(
            "  [warn] existing split membership is empty; "
            f"created 80/20 random split (seed=42, {n:,} match_keys)"
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
            from domain.valorant import AGENT_ROLE_MAP

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
        raw_label = pd.to_numeric(getattr(row, "label", None), errors="coerce")
        label = int(raw_label) if not pd.isna(raw_label) else None
        score_a = pd.to_numeric(getattr(row, "score_a", None), errors="coerce")
        score_b = pd.to_numeric(getattr(row, "score_b", None), errors="coerce")
        margin_a = float(score_a - score_b) if not pd.isna(score_a) and not pd.isna(score_b) else 0.0
        match_inputs[match_key] = MatchInput(
            match_key=match_key,
            year=_year_from_row(row),
            map_name=normalize_map(str(raw_map)) if not pd.isna(raw_map) else None,
            team_keys={
                "a": _clean_key(getattr(row, "team_a", "")),
                "b": _clean_key(getattr(row, "team_b", "")),
            },
            event_key=_clean_key(getattr(row, "event", "")),
            label=label,
            margin_a=margin_a,
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


def _combine_outcome_histories(
    history_by_year: dict[int, dict[tuple | str, OutcomeStats]],
    years: Iterable[int],
) -> dict[tuple | str, OutcomeStats]:
    combined: dict[tuple | str, OutcomeStats] = defaultdict(OutcomeStats)
    for year in years:
        for key, stats in history_by_year.get(year, {}).items():
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


def _team_skill_dist_features(
    match_input: MatchInput,
    player_histories: dict[str, dict[str, RunningStats]],
    global_histories: dict[str, RunningStats],
) -> dict[str, float]:
    """Compute max/std of prior kd per side — captures skill spread within team."""
    hist_all = player_histories.get("all", {})
    global_all = global_histories.get("all", RunningStats())
    features: dict[str, float] = {}
    for side in ("a", "b"):
        kd_vals = []
        for p in match_input.sides[side]:
            hist = hist_all.get(p.player_key)
            kd_vals.append(hist.smoothed_avg("kd", global_all) if hist else 0.0)
        arr = np.array(kd_vals, dtype=float)
        features[f"{side}_max_prior_kd"] = float(np.max(arr)) if len(arr) > 0 else 0.0
        features[f"{side}_std_prior_kd"] = float(np.std(arr)) if len(arr) > 0 else 0.0
    features["diff_max_prior_kd"] = features["a_max_prior_kd"] - features["b_max_prior_kd"]
    features["diff_std_prior_kd"] = features["a_std_prior_kd"] - features["b_std_prior_kd"]
    return features


def _history_reliability_features(
    match_input: MatchInput,
    player_histories: dict[str, dict[str, RunningStats]],
    map_agent_histories: dict[tuple[str, str], RunningStats],
    player_agent_histories: dict[tuple[str, str], RunningStats],
) -> dict[str, float]:
    """Expose sample-size/coverage signals for history-derived advanced priors."""
    hist_all = player_histories.get("all", {})
    map_name = match_input.map_name or ""
    features: dict[str, float] = {}

    for side in ("a", "b"):
        prior_games: list[float] = []
        map_agent_games: list[float] = []
        player_agent_games: list[float] = []

        for player in match_input.sides[side]:
            player_hist = hist_all.get(player.player_key)
            prior_games.append(float(player_hist.games if player_hist else 0))

            ma_games = 0.0
            if player.agent_key and map_name:
                ma_hist = map_agent_histories.get((player.agent_key, map_name))
                ma_games = float(ma_hist.games if ma_hist else 0)
            map_agent_games.append(ma_games)

            pa_games = 0.0
            if player.agent_key:
                pa_hist = player_agent_histories.get((player.player_key, player.agent_key))
                pa_games = float(pa_hist.games if pa_hist else 0)
            player_agent_games.append(pa_games)

        prior_arr = np.array(prior_games or [0.0], dtype=float)
        map_agent_arr = np.array(map_agent_games or [0.0], dtype=float)
        player_agent_arr = np.array(player_agent_games or [0.0], dtype=float)

        known_player_ratio = float(np.mean(prior_arr > 0.0))
        map_agent_known_ratio = float(np.mean(map_agent_arr > 0.0))
        player_agent_known_ratio = float(np.mean(player_agent_arr > 0.0))

        features[f"{side}_known_player_ratio"] = known_player_ratio
        features[f"{side}_low_sample_player_ratio"] = float(
            np.mean(prior_arr < PLAYER_PRIOR_SMOOTHING_GAMES)
        )
        features[f"{side}_map_agent_games_mean"] = float(np.mean(map_agent_arr))
        features[f"{side}_map_agent_known_ratio"] = map_agent_known_ratio
        features[f"{side}_player_agent_games_mean"] = float(np.mean(player_agent_arr))
        features[f"{side}_player_agent_known_ratio"] = player_agent_known_ratio
        features[f"{side}_history_coverage_mean"] = float(
            np.mean([known_player_ratio, map_agent_known_ratio, player_agent_known_ratio])
        )

    for base in HISTORY_RELIABILITY_BASES_ADV:
        features[f"diff_{base}"] = features[f"a_{base}"] - features[f"b_{base}"]
    return features


def _outcome_features(stats: OutcomeStats | None) -> tuple[float, float, float]:
    if stats is None or stats.games == 0:
        return 0.0, 0.5, 0.0
    return float(stats.games), stats.success_rate(), stats.margin_mean()


def _team_context_features(
    match_input: MatchInput,
    team_histories: dict[str, OutcomeStats],
    team_map_histories: dict[tuple[str, str], OutcomeStats],
    team_event_histories: dict[tuple[str, str], OutcomeStats],
) -> dict[str, float]:
    features: dict[str, float] = {}
    map_name = match_input.map_name or ""
    event_key = match_input.event_key or ""
    for side in ("a", "b"):
        team_key = match_input.team_keys.get(side, "")
        games, success, margin = _outcome_features(team_histories.get(team_key))
        features[f"{side}_team_games"] = games
        features[f"{side}_team_success"] = success
        features[f"{side}_team_margin_mean"] = margin

        map_games, map_success, map_margin = _outcome_features(
            team_map_histories.get((team_key, map_name))
        )
        features[f"{side}_team_map_games"] = map_games
        features[f"{side}_team_map_success"] = map_success
        features[f"{side}_team_map_margin_mean"] = map_margin

        event_games, event_success, _ = _outcome_features(
            team_event_histories.get((team_key, event_key))
        )
        features[f"{side}_team_event_games"] = event_games
        features[f"{side}_team_event_success"] = event_success

    for base in TEAM_CONTEXT_BASES_ADV:
        features[f"diff_{base}"] = features[f"a_{base}"] - features[f"b_{base}"]
    return features


def _recent_window(values: Deque[tuple[float, float]], size: int) -> tuple[float, float]:
    if not values:
        return 0.5, 0.0
    rows = list(values)[-size:]
    successes = [row[0] for row in rows]
    margins = [row[1] for row in rows]
    return float(np.mean(successes)), float(np.mean(margins))


def _team_form_features(
    match_input: MatchInput,
    team_recent_history: dict[str, Deque[tuple[float, float]]],
) -> dict[str, float]:
    features: dict[str, float] = {}
    for side in ("a", "b"):
        team_key = match_input.team_keys.get(side, "")
        values = team_recent_history.get(team_key, deque(maxlen=10))
        form5_success, form5_margin = _recent_window(values, 5)
        form10_success, form10_margin = _recent_window(values, 10)
        features[f"{side}_team_form5_success"] = form5_success
        features[f"{side}_team_form5_margin_mean"] = form5_margin
        features[f"{side}_team_form10_success"] = form10_success
        features[f"{side}_team_form10_margin_mean"] = form10_margin

    for base in TEAM_FORM_BASES_ADV:
        features[f"diff_{base}"] = features[f"a_{base}"] - features[f"b_{base}"]
    return features


def _side_player_keys(match_input: MatchInput, side: str) -> list[str]:
    return sorted({player.player_key for player in match_input.sides[side] if player.player_key})


def _roster_context_features(
    match_input: MatchInput,
    team_pair_history: dict[tuple[str, str, str], int],
    last_roster_by_team: dict[str, set[str]],
) -> dict[str, float]:
    features: dict[str, float] = {}
    for side in ("a", "b"):
        team_key = match_input.team_keys.get(side, "")
        players = _side_player_keys(match_input, side)
        pair_counts = [
            float(team_pair_history[(team_key, left, right)])
            for left, right in combinations(players, 2)
        ]
        features[f"{side}_roster_pair_games_mean"] = (
            float(np.mean(pair_counts)) if pair_counts else 0.0
        )
        features[f"{side}_roster_pair_known_ratio"] = (
            float(np.mean(np.array(pair_counts, dtype=float) > 0.0)) if pair_counts else 0.0
        )
        previous = last_roster_by_team.get(team_key, set())
        features[f"{side}_roster_prev_overlap_ratio"] = (
            float(len(set(players) & previous) / max(len(players), 1)) if previous else 0.0
        )

    for base in ROSTER_CONTEXT_BASES_ADV:
        features[f"diff_{base}"] = features[f"a_{base}"] - features[f"b_{base}"]
    return features


def _side_comp_key(match_input: MatchInput, side: str) -> str:
    agents = sorted(
        player.agent_key
        for player in match_input.sides[side]
        if player.agent_key
    )
    return "|".join(agents)


def _comp_context_features(
    match_input: MatchInput,
    comp_histories: dict[tuple[str, str], OutcomeStats],
) -> dict[str, float]:
    features: dict[str, float] = {}
    map_name = match_input.map_name or ""
    for side in ("a", "b"):
        comp_key = _side_comp_key(match_input, side)
        stats = comp_histories.get((map_name, comp_key))
        games, success, _ = _outcome_features(stats)
        features[f"{side}_comp_games"] = games
        features[f"{side}_comp_success"] = success
        features[f"{side}_comp_low_sample_ratio"] = float(games < PLAYER_PRIOR_SMOOTHING_GAMES)

    for base in COMP_CONTEXT_BASES_ADV:
        features[f"diff_{base}"] = features[f"a_{base}"] - features[f"b_{base}"]
    return features


def _build_feature_row(
    match_input: MatchInput,
    player_histories: dict[str, dict[str, RunningStats]],
    global_histories: dict[str, RunningStats],
    pair_history: dict[tuple[str, str], int],
    map_agent_histories: dict[tuple[str, str], RunningStats],
    player_agent_histories: dict[tuple[str, str], RunningStats],
    team_histories: dict[str, OutcomeStats] | None = None,
    team_map_histories: dict[tuple[str, str], OutcomeStats] | None = None,
    team_event_histories: dict[tuple[str, str], OutcomeStats] | None = None,
    team_recent_history: dict[str, Deque[tuple[float, float]]] | None = None,
    team_pair_history: dict[tuple[str, str, str], int] | None = None,
    last_roster_by_team: dict[str, set[str]] | None = None,
    comp_histories: dict[tuple[str, str], OutcomeStats] | None = None,
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
    row.update(_team_skill_dist_features(match_input, player_histories, global_histories))
    row.update(_history_reliability_features(match_input, player_histories, map_agent_histories, player_agent_histories))
    row.update(_team_context_features(match_input, team_histories or {}, team_map_histories or {}, team_event_histories or {}))
    row.update(_team_form_features(match_input, team_recent_history or {}))
    row.update(_roster_context_features(match_input, team_pair_history or defaultdict(int), last_roster_by_team or {}))
    row.update(_comp_context_features(match_input, comp_histories or {}))
    return row


def _update_history_for_matches(
    match_inputs: Iterable[MatchInput],
    player_history_by_year: dict[int, dict[str, RunningStats]],
    global_history_by_year: dict[int, RunningStats],
    pair_history: dict[tuple[str, str], int],
    map_agent_history_by_year: dict[int, dict[tuple[str, str], RunningStats]],
    player_agent_history_by_year: dict[int, dict[tuple[str, str], RunningStats]],
    team_history_by_year: dict[int, dict[str, OutcomeStats]] | None = None,
    team_map_history_by_year: dict[int, dict[tuple[str, str], OutcomeStats]] | None = None,
    team_event_history_by_year: dict[int, dict[tuple[str, str], OutcomeStats]] | None = None,
    team_recent_history: dict[str, Deque[tuple[float, float]]] | None = None,
    team_pair_history: dict[tuple[str, str, str], int] | None = None,
    last_roster_by_team: dict[str, set[str]] | None = None,
    comp_history_by_year: dict[int, dict[tuple[str, str], OutcomeStats]] | None = None,
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
                team_key = match_input.team_keys.get(side, "")
                if team_key and team_pair_history is not None:
                    team_pair_history[(team_key, left, right)] += 1
            team_key = match_input.team_keys.get(side, "")
            if team_key and last_roster_by_team is not None:
                last_roster_by_team[team_key] = set(unique_players)

        # map×agent and player×agent tracking
        for side in ("a", "b"):
            for player in match_input.sides[side]:
                if player.agent_key and match_input.map_name:
                    map_agent_history_by_year[year][(player.agent_key, match_input.map_name)].add(player.stats)
                if player.agent_key:
                    player_agent_history_by_year[year][(player.player_key, player.agent_key)].add(player.stats)

        if match_input.label is None:
            continue
        for side in ("a", "b"):
            team_key = match_input.team_keys.get(side, "")
            if not team_key:
                continue
            success = float(match_input.label == 1) if side == "a" else float(match_input.label == 0)
            margin = float(match_input.margin_a if side == "a" else -match_input.margin_a)
            if team_history_by_year is not None:
                team_history_by_year[year][team_key].add(success, margin)
            if team_map_history_by_year is not None and match_input.map_name:
                team_map_history_by_year[year][(team_key, match_input.map_name)].add(success, margin)
            if team_event_history_by_year is not None and match_input.event_key:
                team_event_history_by_year[year][(team_key, match_input.event_key)].add(success, margin)
            if team_recent_history is not None:
                team_recent_history[team_key].append((success, margin))
            if comp_history_by_year is not None and match_input.map_name:
                comp_key = _side_comp_key(match_input, side)
                if comp_key:
                    comp_history_by_year[year][(match_input.map_name, comp_key)].add(success, margin)


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
    team_history_by_year: dict[int, dict[str, OutcomeStats]] = defaultdict(
        lambda: defaultdict(OutcomeStats)
    )
    team_map_history_by_year: dict[int, dict[tuple[str, str], OutcomeStats]] = defaultdict(
        lambda: defaultdict(OutcomeStats)
    )
    team_event_history_by_year: dict[int, dict[tuple[str, str], OutcomeStats]] = defaultdict(
        lambda: defaultdict(OutcomeStats)
    )
    comp_history_by_year: dict[int, dict[tuple[str, str], OutcomeStats]] = defaultdict(
        lambda: defaultdict(OutcomeStats)
    )
    team_recent_history: dict[str, Deque[tuple[float, float]]] = defaultdict(
        lambda: deque(maxlen=10)
    )
    team_pair_history: dict[tuple[str, str, str], int] = defaultdict(int)
    last_roster_by_team: dict[str, set[str]] = {}

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
        team_histories = _combine_outcome_histories(team_history_by_year, years_for_all)
        team_map_histories = _combine_outcome_histories(team_map_history_by_year, years_for_all)
        team_event_histories = _combine_outcome_histories(team_event_history_by_year, years_for_all)
        comp_histories = _combine_outcome_histories(comp_history_by_year, years_for_all)
        for match_input in same_year_matches:
            feature_rows.append(
                _build_feature_row(
                    match_input,
                    player_histories,
                    global_histories,
                    pair_history,
                    map_agent_histories,
                    player_agent_histories,
                    team_histories=team_histories,
                    team_map_histories=team_map_histories,
                    team_event_histories=team_event_histories,
                    team_recent_history=team_recent_history,
                    team_pair_history=team_pair_history,
                    last_roster_by_team=last_roster_by_team,
                    comp_histories=comp_histories,
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
            team_history_by_year,
            team_map_history_by_year,
            team_event_history_by_year,
            team_recent_history,
            team_pair_history,
            last_roster_by_team,
            comp_history_by_year,
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
    return features  # return ALL computed columns; build_xy handles final selection


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
            "status": "주의",
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
        "status": "정상" if max_abs <= 1e-9 else "문제",
        "earliest_year": int(earliest),
        "rows_checked": int(len(features)),
        "max_abs_history_value": max_abs,
        "scope": "global_valid_5v5_raw_inputs",
        "source_filter": source_summary,
    }


def build_features(
    processed_dir: str = "data/processed",
    feature_contract: str = "baseline",
    include_vlrgg: bool = False,
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
    matches, players, source_summary = _filter_allowed_sources(matches, players, include_vlrgg=include_vlrgg)
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
        for split in ("train", "test"):
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
    for split in ("train", "test"):
        sub = out[out["split"] == split].copy()
        path = Path(target) / f"{split}.csv"
        sub.to_csv(path, index=False)
        print(f"  {split}: {len(sub):,} rows, {len(sub.columns)} columns -> {path}")


def run_preprocess(
    feature_contract: str = "baseline",
    processed_dir: str = "data/processed",
    output_dir: str | None = None,
    include_vlrgg: bool = False,
) -> None:
    """전처리 실행.

    Args:
        include_vlrgg: True이면 vlrgg_ 소스도 포함 (기본 False = kaggle-only 불변).
    """
    if output_dir is None:
        if feature_contract == "advanced":
            raise ValueError(
                "Active advanced preprocessing uses chronological split. "
                "Run `python -m features.chrono_preprocess --include-vlrgg` "
                "or pass --output explicitly for a non-active experiment."
            )
        output_dir = processed_dir
    print(f"Building {feature_contract} features from {processed_dir}/ ...")
    if include_vlrgg:
        print("  [include_vlrgg=True] vlrgg_ 소스도 포함합니다")
    out = build_features(processed_dir, feature_contract=feature_contract, include_vlrgg=include_vlrgg)
    print(f"Total: {len(out):,} rows, {len(out.columns)} columns")
    save_splits(out, processed_dir=processed_dir, output_dir=output_dir)
    feature_cols = FEATURE_COLS_ADVANCED if feature_contract == "advanced" else FEATURE_COLS
    for split in ("train", "test"):
        df = load_split(split, base=output_dir)
        X, y, groups = build_xy(df, feature_contract=feature_contract)
        print(
            f"  {split}: X={X.shape}, y={y.shape}, "
            f"matches={groups.nunique():,}, label_rate={y.mean():.3f}"
        )


def main(processed_dir: str = "data/processed", feature_contract: str = "baseline", include_vlrgg: bool = False) -> None:
    run_preprocess(
        feature_contract=feature_contract,
        processed_dir=processed_dir,
        include_vlrgg=include_vlrgg,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/processed")
    parser.add_argument(
        "--output",
        default=None,
        help=(
            "피처 CSV 저장 디렉터리 "
            "(기본: baseline→input; advanced는 시간순 active lane 보호를 위해 --output 필요)"
        ),
    )
    parser.add_argument("--feature-contract", default="baseline", choices=["baseline", "advanced"])
    parser.add_argument("--include-vlrgg", action="store_true", default=False,
                        help="vlrgg_ 소스도 학습 포함 (런 한정, 기본=kaggle-only)")
    args = parser.parse_args()
    run_preprocess(
        feature_contract=args.feature_contract,
        processed_dir=args.input,
        output_dir=args.output,
        include_vlrgg=args.include_vlrgg,
    )
