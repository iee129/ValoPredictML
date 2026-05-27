"""v10 모델 추론.

  python -m src.predict_v10 predict_input_example.json

state : artifacts/prior_state_v10.joblib
모델  : artifacts/models/{lgbm,xgb,rf}_v10_model.joblib
"""
from __future__ import annotations

import json
import sys
from itertools import combinations

import joblib
import numpy as np
import pandas as pd

from config import ARTIFACTS_DIR, ENSEMBLE_WEIGHTS_V10, MODELS_DIR
from src.features import META_COLS, _map_one_hot, _slot_features, _sort_team_players
from src.role_combo import get_priors, roles_from_side
from src.taxonomy import AGENT_ROLES, MAP_LIST, normalize_map

_STATE_PATH         = ARTIFACTS_DIR / "prior_state_v10.joblib"
_FEATURE_NAMES_PATH = MODELS_DIR    / "feature_names_v10.json"

_state         = None
_lgbm          = None
_xgb           = None
_rf            = None
_feature_names = None


def _load():
    global _state, _lgbm, _xgb, _rf, _feature_names
    if _state is None:
        _state = joblib.load(_STATE_PATH)
        _lgbm  = joblib.load(MODELS_DIR / "lgbm_v10_model.joblib")
        _xgb   = joblib.load(MODELS_DIR / "xgb_v10_model.joblib")
        _rf    = joblib.load(MODELS_DIR / "rf_v10_model.joblib")
        with open(_FEATURE_NAMES_PATH) as f:
            _feature_names = json.load(f)


def _build_name_lookup(player_hist: dict) -> dict[str, str]:
    return {k.lower(): k for k in player_hist if isinstance(k, str)}


def _player_stats(player_hist: dict, name: str, name_lookup: dict) -> dict:
    canonical = name_lookup.get(name.lower(), name)
    dq = player_hist.get(canonical)
    keys = ["kd", "kast", "adr", "acs", "apr", "fkpr", "fdpr", "clutch_pr"]
    if not dq:
        return {f"prior_{k}": np.nan for k in keys}
    return {
        f"prior_{k}": float(np.mean([d[k] for d in dq if k in d]))
        if any(k in d for d in dq) else np.nan
        for k in keys
    }


def _make_side_df(
    players: list[dict],
    player_hist: dict,
    name_lookup: dict,
    co_play_counts: dict,
) -> tuple[pd.DataFrame, float, list[str]]:
    cold = []
    rows = []
    for p in players:
        name  = p["player"]
        agent = p["agent"].lower() if isinstance(p["agent"], str) else ""
        role  = AGENT_ROLES.get(agent, "unknown")
        stats = _player_stats(player_hist, name, name_lookup)
        if name_lookup.get(name.lower(), name) not in player_hist:
            cold.append(name)
        row = {"player": name, "agent": agent, "role": role}
        row.update(stats)
        rows.append(row)

    df = pd.DataFrame(rows)
    player_names = [p["player"] for p in players]
    co_play_sum = float(sum(
        co_play_counts.get(tuple(sorted([p1, p2])), 0)
        for p1, p2 in combinations(player_names, 2)
    ))
    return df, co_play_sum, cold


def predict_one_v10(input_dict: dict) -> dict:
    """
    input_dict = {
        "map": str,
        "team_a": [{"player": str, "agent": str}, ...],  # 5명
        "team_b": [{"player": str, "agent": str}, ...],  # 5명
    }
    """
    _load()

    player_hist      = _state["player_hist"]
    co_play_counts   = _state.get("co_play_counts", {})
    role_combo_state = _state["role_combo_state"]
    name_lookup      = _build_name_lookup(player_hist)

    map_name       = input_dict["map"]
    map_norm       = normalize_map(map_name) or map_name.lower()
    map_recognized = map_norm in MAP_LIST

    side_a_df, copa, cold_a = _make_side_df(
        input_dict["team_a"], player_hist, name_lookup, co_play_counts)
    side_b_df, copb, cold_b = _make_side_df(
        input_dict["team_b"], player_hist, name_lookup, co_play_counts)

    side_a_sorted = _sort_team_players(side_a_df).head(5)
    side_b_sorted = _sort_team_players(side_b_df).head(5)

    a_roles  = roles_from_side(side_a_df)
    b_roles  = roles_from_side(side_b_df)
    rc_feats = get_priors(role_combo_state, map_norm, a_roles, b_roles)

    row = {}
    for i in range(5):
        row.update(_slot_features(side_a_sorted.iloc[i], "a", i))
        row.update(_slot_features(side_b_sorted.iloc[i], "b", i))
    row["a_team_co_play_sum"] = copa
    row["b_team_co_play_sum"] = copb
    row["d_team_co_play_sum"] = copa - copb
    row.update(_map_one_hot(map_norm))
    row.update(rc_feats)

    X = pd.DataFrame([row])
    X = X.drop(columns=[c for c in META_COLS if c in X.columns], errors="ignore")
    X = X.reindex(columns=_feature_names, fill_value=np.nan)

    w      = ENSEMBLE_WEIGHTS_V10
    p_lgbm = float(_lgbm.predict_proba(X)[0, 1])
    p_xgb  = float(_xgb.predict_proba(X)[0, 1])
    p_rf   = float(_rf.predict_proba(X)[0, 1])
    p_ens  = w["lgbm"] * p_lgbm + w["xgb"] * p_xgb + w["rf"] * p_rf

    return {
        "p_ensemble":     p_ens,
        "p_lgbm":         p_lgbm,
        "p_xgb":          p_xgb,
        "p_rf":           p_rf,
        "weights":        w,
        "cold_team_a":    cold_a,
        "cold_team_b":    cold_b,
        "map_recognized": map_recognized,
    }


# ───────── CLI ─────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python -m src.predict_v10 <input.json>")
        sys.exit(1)

    with open(sys.argv[1], encoding="utf-8") as f:
        inp = json.load(f)

    result = predict_one_v10(inp)

    team_a_names = [p["player"] for p in inp["team_a"]]
    team_b_names = [p["player"] for p in inp["team_b"]]

    print(f"\n{'='*50}")
    print(f"맵: {inp['map']}  (인식: {result['map_recognized']})")
    print(f"{'='*50}")
    print(f"Team A ({', '.join(team_a_names)})")
    print(f"  승리 확률: {result['p_ensemble']*100:.1f}%")
    print(f"    LGBM={result['p_lgbm']*100:.1f}%  XGB={result['p_xgb']*100:.1f}%  RF={result['p_rf']*100:.1f}%")
    print(f"Team B ({', '.join(team_b_names)})")
    print(f"  승리 확률: {(1-result['p_ensemble'])*100:.1f}%")
    if result["cold_team_a"]:
        print(f"  [경고] Team A 미등록 선수: {result['cold_team_a']}")
    if result["cold_team_b"]:
        print(f"  [경고] Team B 미등록 선수: {result['cold_team_b']}")
    print(f"{'='*50}\n")
