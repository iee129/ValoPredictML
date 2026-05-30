"""인사이트(요원-맵 적합도 N, 메타 조합 K) — 사전 집계 JSON 로드.

docs_web/06_insights/01·02·05. 모델 추론과 무관(콜드스타트 없음).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from ml.agent_roles import AGENT_ROLE_MAP
from ml.valorant import normalize_agent, normalize_map

REPO_ROOT = Path(__file__).resolve().parents[2]
INSIGHTS_DIR = REPO_ROOT / "reports" / "insights"
RULES_PATH = Path(__file__).resolve().parents[1] / "data" / "agent_map_rules.json"

ROLES = ("duelist", "initiator", "controller", "sentinel")
ROLES_KO = ("타격대", "척후대", "전략가", "감시자")


@lru_cache(maxsize=1)
def _fit_data() -> dict:
    p = INSIGHTS_DIR / "agent_map_fit.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


@lru_cache(maxsize=1)
def _meta_data() -> dict:
    p = INSIGHTS_DIR / "meta_comps.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


@lru_cache(maxsize=1)
def _rules() -> dict:
    return json.loads(RULES_PATH.read_text(encoding="utf-8")) if RULES_PATH.exists() else {}


def _rule_verdict(mp: str, agent: str, role: str) -> str:
    rules = _rules()
    m = rules.get(mp, {})
    if agent in m.get("key_picks", []):
        return "fit"
    if agent in m.get("weak", []):
        return "weak"
    if mp in rules.get("_agent_strong_maps", {}).get(agent, []):
        return "fit"
    return "ok"


# ── 요원-맵 적합도 (N) ─────────────────────────────────
def agent_map_fit(map_name: str) -> dict:
    mp = normalize_map(map_name) or map_name
    data = _fit_data().get(mp)
    present = {a["name"]: a for a in data["agents"]} if data else {}

    agents_out: list[dict] = []
    for agent in sorted(AGENT_ROLE_MAP):
        role = AGENT_ROLE_MAP[agent].lower()
        a = present.get(agent)
        if a is not None:
            if a.get("source") == "rule":   # 저표본 → 룰 판정으로 보정
                a = {**a, "verdict": _rule_verdict(mp, agent, role)}
            agents_out.append(a)
        else:                               # 데이터 없음 → 룰 fallback
            agents_out.append({
                "name": agent, "role": role,
                "verdict": _rule_verdict(mp, agent, role),
                "pick_rate": None, "win_rate": None, "sample": 0, "source": "rule",
            })
    return {"map": mp, "agents": agents_out}


# ── 메타 조합 매칭률 (K) ───────────────────────────────
def _role_vec(agents: list[str]) -> tuple[int, int, int, int]:
    c = {r: 0 for r in ROLES}
    for raw in agents:
        n = normalize_agent(raw)
        role = AGENT_ROLE_MAP.get(n, "").lower() if n else ""
        if role in c:
            c[role] += 1
    return tuple(c[r] for r in ROLES)  # type: ignore[return-value]


def _similarity(u, v) -> float:
    l1 = sum(abs(a - b) for a, b in zip(u, v))   # 0..10
    return 1.0 - l1 / 10.0


def _message(u, v, share: float) -> str:
    parts = []
    for i, r in enumerate(ROLES_KO):
        d = u[i] - v[i]
        if d > 0:
            parts.append(f"{r} {d} 많음")
        elif d < 0:
            parts.append(f"{r} {-d} 적음")
    head = "최다 승리 조합과 일치" if not parts else "메타 대비 " + ", ".join(parts)
    return f"{head} (해당 메타 승리비중 {share * 100:.0f}%)"


def comp_match(map_name: str, agents: list[str]) -> dict:
    mp = normalize_map(map_name) or map_name
    u = _role_vec(agents)
    user_comp = dict(zip(ROLES, u))
    meta = _meta_data().get(mp)
    if not meta or not meta.get("top"):
        return {
            "map": mp, "match_pct": 0.0, "weighted_pct": 0.0,
            "user_comp": user_comp, "nearest_comp": user_comp,
            "nearest_win_share": 0.0,
            "message": "이 맵의 메타 조합 데이터가 부족합니다.",
        }
    tops = meta["top"]
    nearest = max(tops, key=lambda t: _similarity(u, tuple(t["comp"])))
    weighted = sum(_similarity(u, tuple(t["comp"])) * t["win_share"] for t in tops)
    near_vec = tuple(nearest["comp"])
    return {
        "map": mp,
        "match_pct": round(_similarity(u, near_vec) * 100, 1),
        "weighted_pct": round(weighted * 100, 1),
        "user_comp": user_comp,
        "nearest_comp": dict(zip(ROLES, near_vec)),
        "nearest_win_share": nearest["win_share"],
        "message": _message(u, near_vec, nearest["win_share"]),
    }
