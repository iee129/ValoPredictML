"""Prediction helpers for the Streamlit app.

The app serves the Kaggle-only advanced model. Runtime inputs stay at the user
level: map, five players, and five agents per side.
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from itertools import groupby
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from ml.agent_roles import AGENT_ROLE_MAP
from ml.baseline.preprocess import (
    FEATURE_COLS_ADVANCED,
    HISTORY_STATS,
    MODELED_AGENT_KEYS_ADVANCED,
    ROLES,
    MatchInput,
    PlayerInput,
    RunningStats,
    _build_feature_row,
    _build_match_inputs,
    _clean_key,
    _combine_keyed_histories,
    _enrich_player_stats,
    _filter_allowed_sources,
    _history_years,
    _load_matches,
    _load_players,
    _normalize_agent_key,
    _normalize_role,
    _prior_histories_for_year,
    _update_history_for_matches,
    build_xy,
)
from ml.valorant import MAP_ORDER, normalize_agent, normalize_map

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROCESSED_DIR = REPO_ROOT / "data" / "processed"
DEFAULT_ADVANCED_DIR = DEFAULT_PROCESSED_DIR / "adv_kaggle_only"
DEFAULT_MODELS_DIR = REPO_ROOT / "models" / "advanced"
DEFAULT_REPORTS_DIR = REPO_ROOT / "reports" / "adv_kaggle_only"

ROLE_LABELS = {
    "duelist": "타격대",
    "initiator": "척후대",
    "controller": "전략가",
    "sentinel": "감시자",
}
MAP_LABELS = {
    "Ascent": "어센트",
    "Bind": "바인드",
    "Haven": "헤이븐",
    "Split": "스플릿",
    "Icebox": "아이스박스",
    "Breeze": "브리즈",
    "Fracture": "프랙처",
    "Pearl": "펄",
    "Lotus": "로터스",
    "Sunset": "선셋",
    "Abyss": "어비스",
    "Drift": "드리프트",
    "Corrode": "코로드",
}
AGENT_LABELS = {
    "Astra": "아스트라",
    "Breach": "브리치",
    "Brimstone": "브림스톤",
    "Chamber": "체임버",
    "Clove": "클로브",
    "Cypher": "사이퍼",
    "Deadlock": "데드록",
    "Fade": "페이드",
    "Gekko": "게코",
    "Harbor": "하버",
    "ISO": "아이소",
    "Jett": "제트",
    "KAY/O": "케이/오",
    "Killjoy": "킬조이",
    "Miks": "믹스",
    "Neon": "네온",
    "Omen": "오멘",
    "Phoenix": "피닉스",
    "Raze": "레이즈",
    "Reyna": "레이나",
    "Sage": "세이지",
    "Skye": "스카이",
    "Sova": "소바",
    "Tejo": "테호",
    "Veto": "베토",
    "Viper": "바이퍼",
    "Vyse": "바이스",
    "Waylay": "웨이레이",
    "Yoru": "요루",
}
STAT_LABELS = {
    "games": "경기 수",
    "kd": "K/D",
    "kast": "KAST",
    "adr": "평균 피해량",
    "apr": "라운드당 어시스트",
    "fkpr": "라운드당 첫 킬",
    "fdpr": "라운드당 첫 데스",
    "clutch": "클러치",
}
VALIDATION_LABELS = {
    "PASS_TRUSTED_KAGGLE_ONLY_ADVANCED": "통과 - Kaggle 전용 고급 모델",
    "FAIL": "실패",
}


@dataclass(frozen=True)
class PredictionResult:
    team_a_win_probability: float
    team_b_win_probability: float
    confidence: float
    predicted_label: int
    top_features: list[dict[str, Any]]
    role_counts: dict[str, dict[str, float]]
    model_metadata: dict[str, Any]
    report_metadata: dict[str, Any]
    match_key: str | None = None
    map_name: str | None = None
    team_a: str = "Team A"
    team_b: str = "Team B"
    actual_label: int | None = None
    source: str | None = None
    feature_values: dict[str, float] | None = None


def map_label(map_name: str | None) -> str:
    if not map_name:
        return "-"
    return f"{MAP_LABELS.get(map_name, map_name)} ({map_name})"


def agent_label(agent_name: str | None) -> str:
    if not agent_name:
        return "-"
    return f"{AGENT_LABELS.get(agent_name, agent_name)} ({agent_name})"


def role_label(role: str) -> str:
    return ROLE_LABELS.get(role, role)


def verdict_label(verdict: str | None) -> str:
    if not verdict:
        return "-"
    return VALIDATION_LABELS.get(verdict, verdict)


def feature_label(feature: str) -> str:
    if feature.startswith("map_"):
        raw = feature.removeprefix("map_").title()
        return f"맵: {MAP_LABELS.get(raw, raw)}"

    side = ""
    rest = feature
    if feature.startswith("a_"):
        side = "A팀 "
        rest = feature[2:]
    elif feature.startswith("b_"):
        side = "B팀 "
        rest = feature[2:]

    if rest.startswith("role_") and rest.endswith("_count"):
        role = rest.removeprefix("role_").removesuffix("_count")
        return f"{side}{role_label(role)} 수"

    if rest.startswith("agent_") and rest.endswith("_count"):
        agent_key = rest.removeprefix("agent_").removesuffix("_count")
        agent = next(
            (name for name in AGENT_ROLE_MAP if _normalize_agent_key(name) == agent_key),
            agent_key,
        )
        return f"{side}{AGENT_LABELS.get(agent, agent)} 픽 수"

    if rest.startswith("prior_") and rest.endswith("_mean"):
        stat = rest.removeprefix("prior_").removesuffix("_mean")
        return f"{side}이전 연도 선수 평균 {STAT_LABELS.get(stat, stat)}"

    if rest == "synergy_mean":
        return f"{side}선수 동료 경험 평균"

    if rest.startswith("map_agent_") and rest.endswith("_mean"):
        stat = rest.removeprefix("map_agent_").removesuffix("_mean")
        return f"{side}맵-요원 이전 평균 {STAT_LABELS.get(stat, stat)}"

    if rest.startswith("player_agent_") and rest.endswith("_mean"):
        stat = rest.removeprefix("player_agent_").removesuffix("_mean")
        return f"{side}선수-요원 이전 평균 {STAT_LABELS.get(stat, stat)}"

    return feature


def _as_path(path: str | Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


@lru_cache(maxsize=4)
def load_model(models_dir: str | Path = DEFAULT_MODELS_DIR) -> tuple[Any, dict[str, Any]]:
    models_path = _as_path(models_dir)
    model = joblib.load(models_path / "ensemble.joblib")
    meta = _read_json(models_path / "meta.json")
    expected = len(FEATURE_COLS_ADVANCED)
    actual = getattr(model, "n_features_in_", None)
    if actual != expected:
        raise ValueError(f"advanced model expects {actual} features, contract has {expected}")
    return model, meta


@lru_cache(maxsize=4)
def load_reports(reports_dir: str | Path = DEFAULT_REPORTS_DIR) -> dict[str, Any]:
    reports_path = _as_path(reports_dir)
    return {
        "metrics": _read_json(reports_path / "metrics.json"),
        "validation": _read_json(reports_path / "validation.json"),
    }


def _history_dir(processed_dir: str | Path) -> Path:
    path = _as_path(processed_dir)
    if (path / "players.csv").exists() and (path / "matches.csv").exists():
        return path
    if path.name == "adv_kaggle_only" and (path.parent / "players.csv").exists():
        return path.parent
    return DEFAULT_PROCESSED_DIR


def _advanced_dir(processed_dir: str | Path) -> Path:
    path = _as_path(processed_dir)
    if (path / "test.csv").exists() and path.name == "adv_kaggle_only":
        return path
    candidate = path / "adv_kaggle_only"
    if (candidate / "test.csv").exists():
        return candidate
    return DEFAULT_ADVANCED_DIR


def _display_agents() -> list[str]:
    return sorted(AGENT_ROLE_MAP)


def _display_players(players: pd.DataFrame) -> list[str]:
    kaggle = players[players["source"].astype(str).str.startswith("kaggle_")].copy()
    counts = kaggle["player"].dropna().astype(str).str.strip()
    counts = counts[counts.ne("")]
    ordered = counts.value_counts().sort_values(ascending=False)
    return ordered.index.tolist()


def _replay_options(advanced_dir: Path, limit: int = 500) -> list[dict[str, str]]:
    test = pd.read_csv(advanced_dir / "test.csv", low_memory=False)
    rows: list[dict[str, str]] = []
    for row in test.head(limit).itertuples(index=False):
        match_key = str(getattr(row, "match_key"))
        date = str(getattr(row, "date", ""))
        map_name = str(getattr(row, "map", ""))
        team_a = str(getattr(row, "team_a", "Team A"))
        team_b = str(getattr(row, "team_b", "Team B"))
        rows.append(
            {
                "match_key": match_key,
                "label": f"{date} | {map_label(map_name)} | {team_a} vs {team_b} | {match_key}",
            }
        )
    return rows


def available_options(processed_dir: str | Path = DEFAULT_PROCESSED_DIR) -> dict[str, Any]:
    history_path = _history_dir(processed_dir)
    advanced_path = _advanced_dir(processed_dir)
    matches = pd.read_csv(history_path / "matches.csv", low_memory=False)
    players = pd.read_csv(history_path / "players.csv", low_memory=False)

    maps = [
        map_name
        for map_name in MAP_ORDER
        if map_name in set(matches["map"].dropna().astype(str))
    ]
    years = sorted(
        int(year)
        for year in pd.to_numeric(matches.get("year"), errors="coerce").dropna().unique()
        if 2000 <= int(year) <= 2099
    )
    if years:
        years.append(max(years) + 1)

    return {
        "maps": maps or MAP_ORDER,
        "agents": _display_agents(),
        "players": _display_players(players),
        "years": years,
        "replay_matches": _replay_options(advanced_path),
    }


@lru_cache(maxsize=2)
def _historical_match_inputs(processed_dir: str | Path = DEFAULT_PROCESSED_DIR) -> dict[str, MatchInput]:
    history_path = _history_dir(processed_dir)
    matches = _load_matches(str(history_path))
    players = _load_players(str(history_path))
    matches, players, _ = _filter_allowed_sources(matches, players)
    enriched_players = _enrich_player_stats(matches, players)
    return _build_match_inputs(matches, enriched_players)


@lru_cache(maxsize=8)
def _history_state_before_year(
    processed_dir: str | Path,
    cutoff_year: int,
) -> tuple[
    dict[str, dict[str, RunningStats]],
    dict[str, RunningStats],
    dict[tuple[str, str], int],
    dict[tuple[str, str], RunningStats],
    dict[tuple[str, str], RunningStats],
]:
    historical = [
        row
        for row in _historical_match_inputs(processed_dir).values()
        if row.year is not None and int(row.year) < int(cutoff_year)
    ]
    historical.sort(key=lambda row: (int(row.year or 0), row.match_key))

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

    for _, same_year_iter in groupby(historical, key=lambda row: row.year):
        _update_history_for_matches(
            list(same_year_iter),
            player_history_by_year,
            global_history_by_year,
            pair_history,
            map_agent_history_by_year,
            player_agent_history_by_year,
        )

    player_histories, global_histories = _prior_histories_for_year(
        int(cutoff_year),
        player_history_by_year,
        global_history_by_year,
    )
    years_for_all = _history_years(int(cutoff_year), None, player_history_by_year.keys())
    map_agent_histories = _combine_keyed_histories(map_agent_history_by_year, years_for_all)
    player_agent_histories = _combine_keyed_histories(player_agent_history_by_year, years_for_all)
    return (
        player_histories,
        global_histories,
        pair_history,
        map_agent_histories,
        player_agent_histories,
    )


def _slot_to_player_input(slot: dict[str, str]) -> PlayerInput:
    player = _clean_key(slot.get("player", ""))
    agent = normalize_agent(slot.get("agent", ""))
    if not player:
        raise ValueError("선수 10명을 모두 선택해야 합니다.")
    if not agent:
        raise ValueError(f"알 수 없는 요원입니다: {slot.get('agent', '')}")
    agent_key = _normalize_agent_key(agent)
    role = _normalize_role(agent, AGENT_ROLE_MAP.get(agent))
    return PlayerInput(
        player_key=player,
        agent_key=agent_key,
        role=role,
        stats={stat: 0.0 for stat in HISTORY_STATS},
    )


def _validate_slots(team_a_slots: list[dict[str, str]], team_b_slots: list[dict[str, str]]) -> None:
    if len(team_a_slots) != 5 or len(team_b_slots) != 5:
        raise ValueError("각 팀은 선수-요원 슬롯이 정확히 5개여야 합니다.")

    player_keys = [_clean_key(slot.get("player", "")) for slot in team_a_slots + team_b_slots]
    if len(set(player_keys)) != len(player_keys):
        raise ValueError("10개 슬롯 안에서 같은 선수를 중복 선택할 수 없습니다.")

    for side_name, slots in (("A팀", team_a_slots), ("B팀", team_b_slots)):
        agents = []
        for slot in slots:
            agent = normalize_agent(slot.get("agent", ""))
            if agent:
                agents.append(agent)
        if len(set(agents)) != len(agents):
            raise ValueError(f"{side_name} 안에서 같은 요원을 중복 선택할 수 없습니다.")


def _custom_feature_frame(
    map_name: str,
    cutoff_year: int,
    team_a_slots: list[dict[str, str]],
    team_b_slots: list[dict[str, str]],
    processed_dir: str | Path = DEFAULT_PROCESSED_DIR,
) -> pd.DataFrame:
    _validate_slots(team_a_slots, team_b_slots)
    normalized_map = normalize_map(map_name)
    if normalized_map is None:
        raise ValueError(f"알 수 없는 맵입니다: {map_name}")

    custom = MatchInput(
        match_key="custom_lineup",
        year=int(cutoff_year),
        map_name=normalized_map,
        sides={
            "a": [_slot_to_player_input(slot) for slot in team_a_slots],
            "b": [_slot_to_player_input(slot) for slot in team_b_slots],
        },
    )

    (
        player_histories,
        global_histories,
        pair_history,
        map_agent_histories,
        player_agent_histories,
    ) = _history_state_before_year(
        processed_dir,
        int(cutoff_year),
    )

    row = _build_feature_row(
        custom,
        player_histories,
        global_histories,
        pair_history,
        map_agent_histories,
        player_agent_histories,
        agent_keys=MODELED_AGENT_KEYS_ADVANCED,
        include_diff=False,
    )
    frame = pd.DataFrame([row])
    for col in FEATURE_COLS_ADVANCED:
        if col not in frame.columns:
            frame[col] = 0.0
        frame[col] = pd.to_numeric(frame[col], errors="coerce").fillna(0.0)
    return frame[FEATURE_COLS_ADVANCED].astype(float)


def _combined_importances(model: Any, n_features: int) -> np.ndarray:
    if hasattr(model, "feature_importances_"):
        values = np.asarray(model.feature_importances_, dtype=float)
        return values if len(values) == n_features else np.zeros(n_features, dtype=float)
    if hasattr(model, "estimators_"):
        weights = getattr(model, "weights", None) or [1.0] * len(model.estimators_)
        total = np.zeros(n_features, dtype=float)
        weight_sum = 0.0
        for estimator, weight in zip(model.estimators_, weights):
            values = _combined_importances(estimator, n_features)
            if values.any():
                total += float(weight) * values
                weight_sum += float(weight)
        return total / weight_sum if weight_sum else total
    return np.zeros(n_features, dtype=float)


def _top_features(model: Any, X: pd.DataFrame, limit: int = 8) -> list[dict[str, Any]]:
    importances = _combined_importances(model, X.shape[1])
    values = X.iloc[0].to_numpy(dtype=float)
    contributions = importances * values
    if np.abs(contributions).sum() > 0:
        order = np.argsort(np.abs(contributions))[::-1]
    else:
        order = np.argsort(importances)[::-1]
    result = []
    for idx in order[:limit]:
        result.append(
            {
                "feature": X.columns[idx],
                "value": float(values[idx]),
                "importance": float(importances[idx]),
                "contribution": float(contributions[idx]),
            }
        )
    return result


def global_feature_importance(
    models_dir: str | Path = DEFAULT_MODELS_DIR,
    limit: int = 20,
) -> list[dict[str, Any]]:
    model, _ = load_model(models_dir)
    importances = _combined_importances(model, len(FEATURE_COLS_ADVANCED))
    order = np.argsort(importances)[::-1][:limit]
    return [
        {"feature": FEATURE_COLS_ADVANCED[idx], "importance": float(importances[idx])}
        for idx in order
    ]


def _role_counts_from_features(X: pd.DataFrame) -> dict[str, dict[str, float]]:
    row = X.iloc[0]
    return {
        "A팀": {role_label(role): float(row.get(f"a_role_{role}_count", 0.0)) for role in ROLES},
        "B팀": {role_label(role): float(row.get(f"b_role_{role}_count", 0.0)) for role in ROLES},
    }


def _result_from_features(
    X: pd.DataFrame,
    match_key: str | None = None,
    map_name: str | None = None,
    team_a: str = "A팀",
    team_b: str = "B팀",
    actual_label: int | None = None,
    source: str | None = None,
    models_dir: str | Path = DEFAULT_MODELS_DIR,
    reports_dir: str | Path = DEFAULT_REPORTS_DIR,
) -> PredictionResult:
    model, meta = load_model(models_dir)
    reports = load_reports(reports_dir)
    prob_a = float(model.predict_proba(X[FEATURE_COLS_ADVANCED])[:, 1][0])
    return PredictionResult(
        team_a_win_probability=prob_a,
        team_b_win_probability=1.0 - prob_a,
        confidence=float(abs(prob_a - 0.5) * 2.0),
        predicted_label=int(prob_a >= 0.5),
        top_features=_top_features(model, X[FEATURE_COLS_ADVANCED]),
        role_counts=_role_counts_from_features(X),
        model_metadata=meta,
        report_metadata=reports,
        match_key=match_key,
        map_name=map_name,
        team_a=team_a,
        team_b=team_b,
        actual_label=actual_label,
        source=source,
        feature_values={col: float(X.iloc[0][col]) for col in FEATURE_COLS_ADVANCED},
    )


def predict_custom_lineup(
    map_name: str,
    cutoff_year: int,
    team_a_slots: list[dict[str, str]],
    team_b_slots: list[dict[str, str]],
    processed_dir: str | Path = DEFAULT_PROCESSED_DIR,
    models_dir: str | Path = DEFAULT_MODELS_DIR,
    reports_dir: str | Path = DEFAULT_REPORTS_DIR,
) -> PredictionResult:
    X = _custom_feature_frame(
        map_name=map_name,
        cutoff_year=int(cutoff_year),
        team_a_slots=team_a_slots,
        team_b_slots=team_b_slots,
        processed_dir=processed_dir,
    )
    return _result_from_features(
        X,
        map_name=normalize_map(map_name),
        models_dir=models_dir,
        reports_dir=reports_dir,
    )


def predict_replay_match(
    match_key: str,
    processed_dir: str | Path = DEFAULT_ADVANCED_DIR,
    models_dir: str | Path = DEFAULT_MODELS_DIR,
    reports_dir: str | Path = DEFAULT_REPORTS_DIR,
) -> PredictionResult:
    advanced_path = _advanced_dir(processed_dir)
    test = pd.read_csv(advanced_path / "test.csv", low_memory=False)
    row = test[test["match_key"].astype(str) == str(match_key)]
    if row.empty:
        raise ValueError(f"테스트 split에서 경기 키를 찾지 못했습니다: {match_key}")
    X, y, _ = build_xy(row, feature_contract="advanced")
    data = row.iloc[0]
    return _result_from_features(
        X,
        match_key=str(data.get("match_key")),
        map_name=str(data.get("map")),
        team_a=str(data.get("team_a", "Team A")),
        team_b=str(data.get("team_b", "Team B")),
        actual_label=int(y.iloc[0]),
        source=str(data.get("source")) if "source" in row.columns else None,
        models_dir=models_dir,
        reports_dir=reports_dir,
    )
