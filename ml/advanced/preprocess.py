"""
Advanced preprocess: matches.csv → feature matrix → train/val/test.csv

Usage:
    python -m ml.advanced.preprocess [--input data/processed] [--output data/processed]
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd

from ml.valorant import (
    AGENTS_SORTED, MAP_ORDER, ROLES,
    _AGENT_KEY_TO_ROLE, _agent_col_key,
    agent_feature_columns, map_feature_columns, role_feature_columns,
    normalize_agent, normalize_map,
)

META_COLS = [
    "match_key", "dedup_key",
    "event", "map", "team_a", "team_b", "source", "provenance", "split",
]

_YEAR_RE = re.compile(r"(20\d{2})")

_DROP_COLS = ["score_a", "score_b", "source_priority", "agents_a", "agents_b",
              "date", "date_raw", "date_quality", "strict_before_cutoff"]


def extract_year(df: pd.DataFrame) -> pd.Series:
    """Use explicit year when available, then fall back to event/provenance text."""
    def _find(s) -> float:
        if not s or not isinstance(s, str):
            return float("nan")
        m = _YEAR_RE.search(s)
        return float(m.group(1)) if m else float("nan")

    years = pd.Series(np.nan, index=df.index, dtype="float64")
    if "year" in df.columns:
        years = pd.to_numeric(df["year"], errors="coerce")
        years = years.where(years.between(2000, 2099))
    if "event" in df.columns:
        years = years.combine_first(df["event"].apply(_find))
    if "provenance" in df.columns:
        prov_years = df["provenance"].apply(_find)
        years = years.combine_first(prov_years)
    return years.fillna(0).astype(int)


def _parse_agents(s: str | None) -> list[str]:
    if not s or not isinstance(s, str):
        return []
    keys = []
    for part in s.split("|"):
        part = part.strip()
        if not part:
            continue
        norm = normalize_agent(part)
        if norm:
            keys.append(_agent_col_key(norm))
    return keys


def dedup_matches(df: pd.DataFrame) -> pd.DataFrame:
    """Keep one row per dedup_key, prefer lowest source_priority (higher quality)."""
    if "dedup_key" not in df.columns:
        return df.reset_index(drop=True)
    before = len(df)
    out = (
        df.sort_values("source_priority", ascending=True)
        .drop_duplicates(subset="dedup_key", keep="first")
        .reset_index(drop=True)
    )
    print(f"  dedup: {before} → {len(out)} rows ({before - len(out)} removed)")
    return out


def build_agent_onehot(df: pd.DataFrame) -> pd.DataFrame:
    """a_<agent>, b_<agent>, diff_<agent> — 87 cols (29 × 3)."""
    key_to_idx = {k: i for i, k in enumerate(AGENTS_SORTED)}
    n = len(df)
    m = len(AGENTS_SORTED)
    a_mat = np.zeros((n, m), dtype=np.int8)
    b_mat = np.zeros((n, m), dtype=np.int8)

    for i, (_, row) in enumerate(df.iterrows()):
        for key in _parse_agents(row.get("agents_a")):
            j = key_to_idx.get(key)
            if j is not None:
                a_mat[i, j] = 1
        for key in _parse_agents(row.get("agents_b")):
            j = key_to_idx.get(key)
            if j is not None:
                b_mat[i, j] = 1

    diff_mat = (a_mat - b_mat).astype(np.int8)
    a_cols = [f"a_{a}" for a in AGENTS_SORTED]
    b_cols = [f"b_{a}" for a in AGENTS_SORTED]
    diff_cols = [f"diff_{a}" for a in AGENTS_SORTED]
    return pd.DataFrame(
        np.concatenate([a_mat, b_mat, diff_mat], axis=1),
        columns=a_cols + b_cols + diff_cols,
        index=df.index,
    )


def build_role_counts(df: pd.DataFrame) -> pd.DataFrame:
    """a_<role>, b_<role>, diff_<role> — 12 cols (4 × 3)."""
    role_to_idx = {r: i for i, r in enumerate(ROLES)}
    n, nr = len(df), len(ROLES)
    a_mat = np.zeros((n, nr), dtype=np.int8)
    b_mat = np.zeros((n, nr), dtype=np.int8)

    for i, (_, row) in enumerate(df.iterrows()):
        for key in _parse_agents(row.get("agents_a")):
            role = _AGENT_KEY_TO_ROLE.get(key)
            if role is not None:
                j = role_to_idx.get(role)
                if j is not None:
                    a_mat[i, j] += 1
        for key in _parse_agents(row.get("agents_b")):
            role = _AGENT_KEY_TO_ROLE.get(key)
            if role is not None:
                j = role_to_idx.get(role)
                if j is not None:
                    b_mat[i, j] += 1

    diff_mat = (a_mat - b_mat).astype(np.int8)
    a_cols = [f"a_{r}" for r in ROLES]
    b_cols = [f"b_{r}" for r in ROLES]
    diff_cols = [f"diff_{r}" for r in ROLES]
    return pd.DataFrame(
        np.concatenate([a_mat, b_mat, diff_mat], axis=1),
        columns=a_cols + b_cols + diff_cols,
        index=df.index,
    )


def build_map_onehot(df: pd.DataFrame) -> pd.DataFrame:
    """map_<name> binary columns — 13 cols."""
    normalized = df["map"].apply(lambda m: normalize_map(str(m)) if pd.notna(m) else None)
    result: dict[str, np.ndarray] = {}
    for col, map_name in zip(map_feature_columns(), MAP_ORDER):
        result[col] = (normalized == map_name).astype(np.int8).values
    return pd.DataFrame(result, index=df.index)


def build_team_prior_wr(df: pd.DataFrame) -> pd.DataFrame:
    """Expanding team win rate — strict before current row in date order.

    Columns: a_prior_wr, b_prior_wr, diff_prior_wr  (NaN = no prior games)
    """
    n = len(df)
    a_wr = np.full(n, np.nan)
    b_wr = np.full(n, np.nan)

    # argsort returns positions sorted by date; df must have 0-based int index
    date_order = df["year"].argsort().values

    wins: dict[str, int] = {}
    games: dict[str, int] = {}

    for pos in date_order:
        row = df.iloc[pos]
        ta, tb = str(row["team_a"]), str(row["team_b"])
        ga, gb = games.get(ta, 0), games.get(tb, 0)
        if ga > 0:
            a_wr[pos] = wins.get(ta, 0) / ga
        if gb > 0:
            b_wr[pos] = wins.get(tb, 0) / gb
        wins[ta] = wins.get(ta, 0) + int(row["label"])
        games[ta] = ga + 1
        wins[tb] = wins.get(tb, 0) + int(1 - int(row["label"]))
        games[tb] = gb + 1

    diff_wr = np.where(np.isnan(a_wr) | np.isnan(b_wr), np.nan, a_wr - b_wr)
    return pd.DataFrame(
        {"a_prior_wr": a_wr, "b_prior_wr": b_wr, "diff_prior_wr": diff_wr},
        index=df.index,
    )


def build_map_team_wr(df: pd.DataFrame) -> pd.DataFrame:
    """Team win rate on the specific map being played (strict-before-date order)."""
    n = len(df)
    a_arr = np.full(n, np.nan)
    b_arr = np.full(n, np.nan)
    date_order = df["year"].argsort().values

    wins: dict[tuple, int] = {}
    games: dict[tuple, int] = {}

    for pos in date_order:
        row = df.iloc[pos]
        ta, tb = str(row["team_a"]), str(row["team_b"])
        m = str(row["map"])
        ka, kb = (ta, m), (tb, m)
        ga, gb = games.get(ka, 0), games.get(kb, 0)
        if ga > 0:
            a_arr[pos] = wins.get(ka, 0) / ga
        if gb > 0:
            b_arr[pos] = wins.get(kb, 0) / gb
        wins[ka] = wins.get(ka, 0) + int(row["label"])
        games[ka] = ga + 1
        wins[kb] = wins.get(kb, 0) + int(1 - int(row["label"]))
        games[kb] = gb + 1

    diff = np.where(np.isnan(a_arr) | np.isnan(b_arr), np.nan, a_arr - b_arr)
    return pd.DataFrame(
        {"a_map_wr": a_arr, "b_map_wr": b_arr, "diff_map_wr": diff},
        index=df.index,
    )


def build_recent_form(df: pd.DataFrame, windows: tuple[int, ...] = (5, 10)) -> pd.DataFrame:
    """Win rate in last N games per team — one set of 3 cols per window."""
    n = len(df)
    date_order = df["year"].argsort().values

    from collections import deque
    cols: dict[str, np.ndarray] = {}
    for w in windows:
        a_arr = np.full(n, np.nan)
        b_arr = np.full(n, np.nan)
        history: dict[str, deque] = {}

        for pos in date_order:
            row = df.iloc[pos]
            ta, tb = str(row["team_a"]), str(row["team_b"])
            ha = history.setdefault(ta, deque(maxlen=w))
            hb = history.setdefault(tb, deque(maxlen=w))
            if ha:
                a_arr[pos] = sum(ha) / len(ha)
            if hb:
                b_arr[pos] = sum(hb) / len(hb)
            ha.append(int(row["label"]))
            hb.append(int(1 - int(row["label"])))

        diff = np.where(np.isnan(a_arr) | np.isnan(b_arr), np.nan, a_arr - b_arr)
        cols[f"a_recent{w}_wr"] = a_arr
        cols[f"b_recent{w}_wr"] = b_arr
        cols[f"diff_recent{w}_wr"] = diff

    return pd.DataFrame(cols, index=df.index)


def build_h2h_wr(df: pd.DataFrame) -> pd.DataFrame:
    """Team A's historical win rate against team B (strict-before-date order).

    Uses a canonical pair key (alphabetical) so A-vs-B and B-vs-A rows are
    counted together, and the win rate is always from team_a's perspective.

    Columns: h2h_wr (NaN = no prior H2H), h2h_count (# prior H2H games).
    """
    n = len(df)
    h2h = np.full(n, np.nan)
    h2h_count = np.zeros(n, dtype=np.int32)
    date_order = df["year"].argsort().values

    pair_wins: dict[tuple, int] = {}
    pair_games: dict[tuple, int] = {}

    for pos in date_order:
        row = df.iloc[pos]
        ta, tb = str(row["team_a"]), str(row["team_b"])
        label = int(row["label"])

        ta_is_first = ta <= tb
        key = (ta, tb) if ta_is_first else (tb, ta)

        g = pair_games.get(key, 0)
        if g > 0:
            w = pair_wins.get(key, 0)
            h2h[pos] = (w / g) if ta_is_first else ((g - w) / g)
            h2h_count[pos] = g

        first_won = label if ta_is_first else 1 - label
        pair_wins[key] = pair_wins.get(key, 0) + first_won
        pair_games[key] = g + 1

    return pd.DataFrame(
        {"h2h_wr": h2h, "h2h_count": h2h_count.astype(float)},
        index=df.index,
    )


def split_data(df: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    """Assign 'split' column (train 70 / val 15 / test 15) by match_key."""
    keys = df["match_key"].unique()
    rng = np.random.default_rng(seed)
    shuffled = rng.permutation(keys)
    n = len(shuffled)
    n_train = int(n * 0.70)
    n_val = int(n * 0.15)
    train_keys = set(shuffled[:n_train])
    val_keys = set(shuffled[n_train : n_train + n_val])
    df = df.copy()
    df["split"] = df["match_key"].map(
        lambda k: "train" if k in train_keys else ("val" if k in val_keys else "test")
    )
    return df


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Combine all feature blocks with original metadata columns."""
    print(f"  agent one-hot ({len(AGENTS_SORTED)} × 3 = {len(AGENTS_SORTED)*3} cols)...")
    agent_df = build_agent_onehot(df)
    print(f"  role counts ({len(ROLES)} × 3 = {len(ROLES)*3} cols)...")
    role_df = build_role_counts(df)
    print(f"  map one-hot ({len(MAP_ORDER)} cols)...")
    map_df = build_map_onehot(df)
    print("  team prior win rates...")
    wr_df = build_team_prior_wr(df)
    print("  map-specific team win rates...")
    map_wr_df = build_map_team_wr(df)
    print("  recent form (last 5 / 10 games)...")
    form_df = build_recent_form(df)
    print("  head-to-head win rate...")
    h2h_df = build_h2h_wr(df)
    return pd.concat([df, agent_df, role_df, map_df, wr_df, map_wr_df, form_df, h2h_df], axis=1)


def main(input_dir: str = "data/processed", output_dir: str = "data/processed") -> None:
    inp, out = Path(input_dir), Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    csv_name = "vct_matches.csv" if (inp / "vct_matches.csv").exists() else "matches.csv"
    print(f"Loading {csv_name}...")
    matches = pd.read_csv(inp / csv_name, low_memory=False)
    print(f"  {len(matches)} rows, {len(matches.columns)} cols")

    print("Deduplicating...")
    matches = dedup_matches(matches)

    print("Filtering...")
    matches = matches.dropna(subset=["label"]).copy()
    matches["label"] = matches["label"].astype(int)
    matches = matches.reset_index(drop=True)
    print(f"  {len(matches)} rows after label filter")

    print("Extracting year from event/provenance...")
    matches["year"] = extract_year(matches)
    year_known = (matches["year"] > 0).sum()
    print(f"  year known: {year_known}/{len(matches)} rows "
          f"({year_known / len(matches) * 100:.1f}%)")

    print("Building features...")
    feat = build_features(matches)

    print("Splitting train/val/test...")
    feat = split_data(feat)

    # Handle win-rate NaN: add unknown flag, fill with 0.5
    wr_cols = [c for c in feat.columns if "_wr" in c and not c.endswith("_unknown")]
    for col in wr_cols:
        feat[f"{col}_unknown"] = feat[col].isna().astype(np.int8)
    feat[wr_cols] = feat[wr_cols].fillna(0.5)

    # Drop leaky/raw columns not needed as features
    feat = feat.drop(columns=[c for c in _DROP_COLS if c in feat.columns])
    feat = feat.fillna(0)

    # Validate no match_key overlap
    sets = {s: set(feat[feat["split"] == s]["match_key"]) for s in ("train", "val", "test")}
    assert not (sets["train"] & sets["val"]), "train/val match_key overlap"
    assert not (sets["train"] & sets["test"]), "train/test match_key overlap"
    assert not (sets["val"] & sets["test"]), "val/test match_key overlap"

    feat_cols = [c for c in feat.columns if c not in META_COLS + ["label"]]
    print(f"\n=== Split summary ===")
    print(f"  Total cols: {len(feat.columns)}  Feature cols: {len(feat_cols)}")
    for s in ("train", "val", "test"):
        sub = feat[feat["split"] == s]
        print(f"  {s}: {len(sub)} rows, label_mean={sub['label'].mean():.3f}")
    print("  match_key overlap: PASSED")

    for s in ("train", "val", "test"):
        sub = feat[feat["split"] == s].copy()
        path = out / f"{s}.csv"
        sub.to_csv(path, index=False)
        print(f"  → {path}  ({len(sub)} rows)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/processed")
    ap.add_argument("--output", default="data/processed")
    args = ap.parse_args()
    main(args.input, args.output)
