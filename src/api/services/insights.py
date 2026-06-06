"""인사이트(요원-맵 적합도 N, 메타 조합 K) — 사전 집계 JSON 로드.

docs/08_web/06_insights/01·02·05. 모델 추론과 무관(콜드스타트 없음).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from domain.agent_roles import AGENT_ROLE_MAP
from domain.valorant import normalize_agent, normalize_map

REPO_ROOT = Path(__file__).resolve().parents[3]  # src/api/services/insights.py → repo root
INSIGHTS_DIR = REPO_ROOT / "reports" / "insights"
RULES_PATH = Path(__file__).resolve().parents[1] / "data" / "agent_map_rules.json"  # src/api/data/

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


def _data_verdict(win_rate: float) -> str:
    if win_rate >= 0.52:
        return "fit"
    if win_rate <= 0.48:
        return "weak"
    return "ok"


def _normalized_map_or_raise(map_name: str) -> str:
    mp = normalize_map(map_name)
    if mp is None:
        raise ValueError(f"알 수 없는 맵입니다: {map_name}")
    return mp


def _normalized_agents_or_raise(agents: list[str]) -> list[str]:
    normalized: list[str] = []
    for raw in agents:
        agent = normalize_agent(raw)
        if agent is None:
            raise ValueError(f"알 수 없는 요원입니다: {raw}")
        normalized.append(agent)
    return normalized


# ── 요원-맵 적합도 (N) ─────────────────────────────────
def agent_map_fit(map_name: str) -> dict:
    mp = _normalized_map_or_raise(map_name)
    raw_data = _fit_data().get(mp) or {}
    data = {
        normalized: win_rate
        for raw_agent, win_rate in raw_data.items()
        if (normalized := normalize_agent(str(raw_agent))) is not None
    }

    agents_out: list[dict] = []
    for agent in sorted(AGENT_ROLE_MAP):
        role = AGENT_ROLE_MAP[agent].lower()
        win_rate = data.get(agent)
        if win_rate is None:
            agents_out.append({
                "name": agent, "role": role,
                "verdict": _rule_verdict(mp, agent, role),
                "pick_rate": None, "win_rate": None, "sample": 0, "source": "rule",
            })
        else:
            wr = float(win_rate)
            agents_out.append({
                "name": agent, "role": role,
                "verdict": _data_verdict(wr),
                "pick_rate": None, "win_rate": wr, "sample": 0, "source": "data",
            })
    return {"map": mp, "agents": agents_out}


# ── 메타 조합 매칭률 (K) ───────────────────────────────
def _role_vec(agents: list[str]) -> tuple[int, int, int, int]:
    c = {r: 0 for r in ROLES}
    for raw in agents:
        role = AGENT_ROLE_MAP.get(raw, "").lower()
        if role in c:
            c[role] += 1
    return tuple(c[r] for r in ROLES)  # type: ignore[return-value]


def _comp_role_vec(comp: str) -> tuple[int, int, int, int]:
    agents = _normalized_agents_or_raise([part for part in str(comp).split("|") if part])
    return _role_vec(agents)


def _similarity(u, v) -> float:
    l1 = sum(abs(a - b) for a, b in zip(u, v))   # 0..10
    return 1.0 - l1 / 10.0


def _message(u, v, win_rate: float) -> str:
    parts = []
    for i, r in enumerate(ROLES_KO):
        d = u[i] - v[i]
        if d > 0:
            parts.append(f"{r} {d} 많음")
        elif d < 0:
            parts.append(f"{r} {-d} 적음")
    head = "최다 승리 조합과 일치" if not parts else "메타 대비 " + ", ".join(parts)
    return f"{head} (가장 가까운 조합 승률 {win_rate * 100:.0f}%)"


def comp_match(map_name: str, agents: list[str]) -> dict:
    mp = _normalized_map_or_raise(map_name)
    normalized_agents = _normalized_agents_or_raise(agents)
    u = _role_vec(normalized_agents)
    user_comp = dict(zip(ROLES, u))
    meta = _meta_data().get(mp) or []
    if not meta:
        return {
            "map": mp, "match_pct": 0.0, "weighted_pct": 0.0,
            "user_comp": user_comp, "nearest_comp": user_comp,
            "nearest_win_share": 0.0,
            "message": "이 맵의 메타 조합 데이터가 부족합니다.",
        }
    candidates = []
    for item in meta:
        near_vec = _comp_role_vec(str(item.get("comp", "")))
        count = int(item.get("count", 0) or 0)
        win_rate = float(item.get("win_rate", 0.0) or 0.0)
        candidates.append({
            "vec": near_vec,
            "similarity": _similarity(u, near_vec),
            "count": max(0, count),
            "win_rate": win_rate,
        })
    nearest = max(candidates, key=lambda item: (item["similarity"], item["count"], item["win_rate"]))
    total_count = sum(item["count"] for item in candidates)
    weighted = (
        sum(item["similarity"] * item["count"] for item in candidates) / total_count
        if total_count > 0
        else 0.0
    )
    near_vec = tuple(nearest["vec"])
    return {
        "map": mp,
        "match_pct": round(_similarity(u, near_vec) * 100, 1),
        "weighted_pct": round(weighted * 100, 1),
        "user_comp": user_comp,
        "nearest_comp": dict(zip(ROLES, near_vec)),
        "nearest_win_share": nearest["win_rate"],
        "message": _message(u, near_vec, nearest["win_rate"]),
    }
