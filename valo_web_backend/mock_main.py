"""임시 MOCK API — 실제 모델/데이터 없이 프론트 전체 UI를 시연하기 위한 가짜 백엔드.

계약(엔드포인트·필드명)은 실제 valo_web_backend/schemas.py 및 프론트 types/api.ts와 동일하게 맞춘다.
도메인 값(요원 29·맵 13·역할)은 ml.agent_roles에서 가져와 실제와 일치시키고, 승률·피처·근거는
입력으로부터 deterministic하게 생성한 가짜 값이다.

⚠️ 시연/검증 전용. 실제 데이터·모델이 준비되면 valo_web_backend.main 으로 교체한다.

실행: uvicorn valo_web_backend.mock_main:app --host 127.0.0.1 --port 8000
"""
from __future__ import annotations

import hashlib

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from ml.agent_roles import AGENT_ROLE_MAP, MAP_ORDER

ROLES = ("duelist", "initiator", "controller", "sentinel")
AGENTS = sorted(AGENT_ROLE_MAP)  # 29
NEW_AGENTS = {"Miks", "Veto", "Waylay"}  # 저표본 → rule 표기

MAP_KO = {
    "Ascent": "어센트", "Bind": "바인드", "Haven": "헤이븐", "Split": "스플릿",
    "Icebox": "아이스박스", "Breeze": "브리즈", "Fracture": "프랙처", "Pearl": "펄",
    "Lotus": "로터스", "Sunset": "선셋", "Abyss": "어비스", "Drift": "드리프트",
    "Corrode": "코로드",
}
PLAYERS = [
    "TenZ", "aspas", "Derke", "Less", "Demon1", "yay", "Chronicle", "Boaster",
    "f0rsakeN", "Jinggg", "ZmjjKK", "nAts", "Sacy", "pancada", "saadhak",
    "Cryocells", "johnqt", "crashies", "Marved", "zekken", "tarik", "Zellsis",
    "trent", "valyn", "Mazino", "stax", "BuZz", "MaKo", "Rb", "Sayaplayer",
]
YEARS = [2021, 2022, 2023, 2024, 2025, 2026]

# 맵별 키픽/약체 (Ascent만 도메인 정확, 나머지는 hash 스프레드)
KEY_PICKS = {
    "Ascent": {"fit": {"Omen", "Sova", "Killjoy", "Jett", "KAY/O"},
               "weak": {"Brimstone", "Phoenix"}},
}


def _h(s: str) -> float:
    return int(hashlib.sha1(s.encode("utf-8")).hexdigest(), 16) % 10_000 / 10_000.0


def _role(a: str) -> str:
    return AGENT_ROLE_MAP.get(a, "").lower()


def _role_counts(agents: list[str]) -> dict[str, int]:
    c = {r: 0 for r in ROLES}
    for a in agents:
        r = _role(a)
        if r in c:
            c[r] += 1
    return c


def _balance(rc: dict[str, int]) -> list[dict]:
    out = []
    if rc["controller"] == 0:
        out.append({"code": "no_controller", "severity": "high",
                    "message": "전략가 부재 — 스모크로 시야 차단·지역 통제가 약합니다."})
    if rc["sentinel"] >= 3:
        out.append({"code": "too_many_sentinel", "severity": "high",
                    "message": "감시자 과다 — 진입력이 부족해 공격 라운드가 어렵습니다."})
    if rc["duelist"] == 0:
        out.append({"code": "no_duelist", "severity": "medium",
                    "message": "타격대 부재 — 진입·킬 창출 주체가 없습니다."})
    if rc["initiator"] == 0:
        out.append({"code": "no_initiator", "severity": "medium",
                    "message": "척후대 부재 — 정보 수집·진입 보조가 약합니다."})
    if rc["duelist"] >= 4:
        out.append({"code": "too_many_duelist", "severity": "low",
                    "message": "타격대 과다 — 유틸·지역 통제가 부족합니다."})
    return out


app = FastAPI(title="ValoPredictML MOCK API", version="0.0.0-mock")
app.add_middleware(
    CORSMiddleware, allow_origins=["http://localhost:3000"],
    allow_methods=["GET", "POST"], allow_headers=["*"],
)


@app.get("/")
def root():
    return {"service": "ValoPredictML MOCK API", "mock": True, "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": True, "n_features": 125,
            "contract": "advanced", "mock": True}


@app.get("/model")
def model():
    feats = [
        ("a_prior_kd_mean", 0.052), ("b_prior_kd_mean", 0.048),
        ("a_synergy_mean", 0.041), ("a_map_agent_adr_mean", 0.038),
        ("a_prior_games_mean", 0.034), ("b_prior_kast_mean", 0.031),
        ("a_player_agent_kast_mean", 0.028), ("map_ascent", 0.022),
        ("a_role_controller_count", 0.019), ("b_synergy_mean", 0.017),
        ("a_prior_adr_mean", 0.015), ("b_map_agent_kd_mean", 0.013),
    ]
    return {
        "algorithm": "RF+XGB+LGBM_soft_voting (MOCK)",
        "contract": "advanced", "n_features": 125,
        "metrics": {"test_auc": 0.7570, "test_acc": 0.6958, "test_f1": 0.7649},
        "validation": {"final_verdict": "PASS_TRUSTED_KAGGLE_ONLY_ADVANCED"},
        "global_importance": [{"feature": f, "importance": v} for f, v in feats],
    }


def _agents_payload():
    return [{"name": a, "role": _role(a)} for a in AGENTS]


def _maps_payload():
    return [{"name": m, "ko": MAP_KO.get(m, m)} for m in MAP_ORDER]


@app.get("/options")
def options():
    return {"maps": _maps_payload(), "agents": _agents_payload(),
            "players": PLAYERS, "years": YEARS}


@app.get("/agents")
def agents():
    return _agents_payload()


@app.get("/maps")
def maps():
    return _maps_payload()


@app.get("/players")
def players(limit: int = 300):
    return {"players": PLAYERS[:limit], "total": len(PLAYERS)}


@app.get("/years")
def years():
    return {"years": YEARS, "default": YEARS[-1]}


@app.get("/agent-map-fit")
def agent_map_fit(map: str = Query(...)):
    rules = KEY_PICKS.get(map, {})
    out = []
    for a in AGENTS:
        if a in NEW_AGENTS:
            out.append({"name": a, "role": _role(a), "verdict": "ok",
                        "pick_rate": None, "win_rate": None, "sample": 3, "source": "rule"})
            continue
        if a in rules.get("fit", set()):
            verdict = "fit"
        elif a in rules.get("weak", set()):
            verdict = "weak"
        else:
            hh = _h(map + a)
            verdict = "fit" if hh < 0.30 else ("weak" if hh > 0.82 else "ok")
        pr = round(0.04 + _h("pr" + map + a) * 0.55, 3)
        wr = round(0.42 + _h("wr" + map + a) * 0.18, 3)
        out.append({"name": a, "role": _role(a), "verdict": verdict,
                    "pick_rate": pr, "win_rate": wr,
                    "sample": int(40 + _h("s" + map + a) * 1800), "source": "data"})
    return {"map": map, "agents": out}


def _similarity(u, v):
    return 1.0 - sum(abs(x - y) for x, y in zip(u, v)) / 10.0


@app.post("/comp-match")
def comp_match(body: dict):
    mp = body.get("map", "")
    agents = body.get("agents", [])
    rc = _role_counts(agents)
    u = tuple(rc[r] for r in ROLES)
    nearest = (1, 2, 1, 1)  # 메타 기준 구성 (mock)
    sim = _similarity(u, nearest)
    return {
        "map": mp,
        "match_pct": round(sim * 100, 1),
        "weighted_pct": round(sim * 90, 1),
        "user_comp": dict(zip(ROLES, u)),
        "nearest_comp": dict(zip(ROLES, nearest)),
        "nearest_win_share": 0.31,
        "message": ("최다 승리 조합과 일치 (해당 메타 승리비중 31%)" if u == nearest
                    else "메타 대비 역할 구성 일부 차이 (해당 메타 승리비중 31%)"),
    }


def _build_prediction(mp, a_ids, b_ids, a_agents, b_agents,
                      name_a="팀 A", name_b="팀 B", actual=None):
    rc_a = _role_counts(a_agents)
    rc_b = _role_counts(b_agents)
    raw = 0.5 + (_h(mp + "|".join(a_ids + a_agents)) - _h("|".join(b_ids + b_agents))) * 0.34
    prob_a = round(max(0.30, min(0.70, raw)), 4)
    to_a = prob_a >= 0.5
    winner = name_a if to_a else name_b
    sign = 1 if to_a else -1
    feats = [
        ("a_prior_kd_mean", "A팀 이전 연도 선수 평균 K/D", 1.08, 0.052 * sign),
        ("a_prior_games_mean", "A팀 이전 연도 선수 평균 경기 수", 42.0, 0.041 * sign),
        ("a_synergy_mean", "A팀 선수 동료 경험 평균", 3.4, 0.034 * sign),
        ("a_map_agent_adr_mean", "A팀 맵-요원 이전 평균 평균 피해량", 148.0, 0.029 * -sign),
        (f"map_{mp.lower()}", f"맵: {MAP_KO.get(mp, mp)}", 1.0, 0.018),
        ("a_player_agent_kast_mean", "A팀 선수-요원 이전 평균 KAST", 0.72, 0.015 * sign),
    ]
    top_features = [
        {"feature": f, "label": lab, "value": val,
         "importance": abs(con), "contribution": round(con, 4)}
        for f, lab, val, con in feats
    ]
    dg = int(2 + _h("g" + mp) * 8)
    kd = round(0.05 + _h("kd" + mp) * 0.18, 2)
    explanations = [
        {"feature": "prior_games",
         "text": f"{winner} 우세 요인: 직전 연도 경험이 평균 대비 {dg}경기 많음", "magnitude": float(dg)},
        {"feature": "prior_kd",
         "text": f"{winner} 우위: 선수 평균 K/D가 {kd:.2f} 우세", "magnitude": kd},
        {"feature": "synergy",
         "text": f"{winner} 우위: 팀 동반 출전 경험(호흡)이 더 많음", "magnitude": 1.0},
    ]
    resp = {
        "map": mp, "cutoff_year": None,
        "predicted_winner": "A" if to_a else "B",
        "predicted_label": 1 if to_a else 0,
        "confidence": round(abs(prob_a - 0.5) * 2, 4),
        "team_a": {"name": name_a, "win_probability": prob_a},
        "team_b": {"name": name_b, "win_probability": round(1 - prob_a, 4)},
        "role_counts": {"team_a": rc_a, "team_b": rc_b},
        "top_features": top_features,
        "model": {"contract": "advanced", "n_features": 125},
        "explanations": explanations,
        "balance": {"team_a": _balance(rc_a), "team_b": _balance(rc_b)},
        "match_key": None, "actual_label": None, "actual_winner": None, "hit": None,
    }
    if actual is not None:
        resp["actual_label"] = actual
        resp["actual_winner"] = "A" if actual == 1 else "B"
        resp["hit"] = (resp["predicted_label"] == actual)
    return resp


@app.post("/predict")
def predict(body: dict):
    mp = body.get("map", "Ascent")
    ta = body.get("team_a", [])
    tb = body.get("team_b", [])
    a_ids = [s.get("player", "") for s in ta]
    b_ids = [s.get("player", "") for s in tb]
    a_agents = [s.get("agent", "") for s in ta]
    b_agents = [s.get("agent", "") for s in tb]
    return _build_prediction(mp, a_ids, b_ids, a_agents, b_agents)


# ── 다시보기 (mock 경기) ───────────────────────────────
_REPLAY = [
    ("mk_t1_geng_ascent", "2024-08-04", "Ascent", "T1", "GenG",
     ["Jett", "Sova", "Omen", "Killjoy", "KAY/O"], ["Raze", "Fade", "Viper", "Cypher", "Skye"], 1),
    ("mk_drx_sen_bind", "2024-07-21", "Bind", "DRX", "Sentinels",
     ["Raze", "Gekko", "Brimstone", "Cypher", "Skye"], ["Jett", "Breach", "Viper", "Killjoy", "Fade"], 0),
    ("mk_prx_fnc_haven", "2024-09-01", "Haven", "Paper Rex", "FNATIC",
     ["Jett", "Sova", "Omen", "Killjoy", "Breach"], ["Raze", "Fade", "Astra", "Cypher", "KAY/O"], 1),
    ("mk_eg_nrg_split", "2024-06-15", "Split", "Evil Geniuses", "NRG",
     ["Raze", "Skye", "Omen", "Cypher", "Breach"], ["Jett", "Sova", "Viper", "Killjoy", "Gekko"], 0),
    ("mk_kru_loud_lotus", "2024-08-25", "Lotus", "KRÜ", "LOUD",
     ["Raze", "Fade", "Omen", "Killjoy", "Sova"], ["Neon", "Breach", "Viper", "Cypher", "Skye"], 1),
    ("mk_th_vit_icebox", "2024-07-07", "Icebox", "Team Heretics", "Team Vitality",
     ["Jett", "Sova", "Viper", "Killjoy", "Sage"], ["Raze", "Fade", "Harbor", "Cypher", "KAY/O"], 0),
]


@app.get("/replay/matches")
def replay_matches(limit: int = 200):
    items = []
    for mk, date, mp, ta, tb, _aa, _ba, _lab in _REPLAY[:limit]:
        items.append({"match_key": mk, "date": date, "map": mp, "team_a": ta, "team_b": tb,
                      "label": f"{date} | {MAP_KO.get(mp, mp)} ({mp}) | {ta} vs {tb} | {mk}"})
    return {"items": items, "total": len(items)}


@app.get("/replay/{match_key}")
def replay_one(match_key: str):
    from fastapi import HTTPException
    for mk, _date, mp, ta, tb, aa, ba, lab in _REPLAY:
        if mk == match_key:
            return _build_prediction(mp, [ta] * 5, [tb] * 5, aa, ba,
                                     name_a=ta, name_b=tb, actual=lab)
    raise HTTPException(status_code=404, detail=f"경기 키를 찾지 못했습니다: {match_key}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("valo_web_backend.mock_main:app", host="127.0.0.1", port=8000)
