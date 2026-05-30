"""PredictionResult → 응답 dict 변환 + 자연어 근거(C)·구성 결함(G) 파생.

docs_web/02_backend_fastapi/04_schemas.md, 06_insights/03·04 기준.
"""
from __future__ import annotations

from typing import Any

from app.predict import ROLE_LABELS, feature_label  # 기존 라벨 매핑 재사용

ROLES = ("duelist", "initiator", "controller", "sentinel")
# {"타격대":"duelist", ...} — app.predict.ROLE_LABELS(영문→한국어)의 역매핑
ROLE_KO_TO_KEY = {ko: en for en, ko in ROLE_LABELS.items()}
ROLES_KO = ("타격대", "척후대", "전략가", "감시자")


# ── 역할 카운트: 한국어 키 → canonical 키 ──────────────
def _role_counts(side: dict) -> dict[str, float]:
    out = {r: 0.0 for r in ROLES}
    for k, v in (side or {}).items():
        key = ROLE_KO_TO_KEY.get(k, str(k).lower())
        if key in out:
            out[key] = float(v)
    return out


# ── 구성 결함 (G) ─────────────────────────────────────
def balance_warnings(rc: dict[str, float]) -> list[dict]:
    c = {r: rc.get(r, 0.0) for r in ROLES}
    out: list[dict] = []
    if c["controller"] == 0:
        out.append({"code": "no_controller", "severity": "high",
                    "message": "전략가 부재 — 스모크로 시야 차단·지역 통제가 약합니다."})
    if c["sentinel"] >= 3:
        out.append({"code": "too_many_sentinel", "severity": "high",
                    "message": "감시자 과다 — 진입력이 부족해 공격 라운드가 어렵습니다."})
    if c["duelist"] == 0:
        out.append({"code": "no_duelist", "severity": "medium",
                    "message": "타격대 부재 — 진입·킬 창출 주체가 없습니다."})
    if c["initiator"] == 0:
        out.append({"code": "no_initiator", "severity": "medium",
                    "message": "척후대 부재 — 정보 수집·진입 보조가 약합니다."})
    if c["duelist"] >= 4:
        out.append({"code": "too_many_duelist", "severity": "low",
                    "message": "타격대 과다 — 유틸·지역 통제가 부족합니다."})
    return out


# ── 자연어 근거 (C) ───────────────────────────────────
_TEMPLATES = [
    ("prior_games",  "직전 연도 경험",        lambda d: f"평균 대비 {abs(d):.0f}경기"),
    ("prior_kd",     "선수 평균 K/D",         lambda d: f"{abs(d):.2f}"),
    ("prior_adr",    "라운드당 피해량(ADR)",  lambda d: f"{abs(d):.1f}"),
    ("prior_kast",   "KAST(라운드 기여율)",   lambda d: f"{abs(d) * 100:.0f}%p"),
    ("synergy",      "팀 동반 출전 경험(호흡)", lambda d: ""),
    ("map_agent",    "이 맵에서의 요원 숙련도", lambda d: ""),
    ("player_agent", "선수-요원 조합 경험",    lambda d: ""),
]


def _base_of(feature: str) -> str:          # "a_prior_kd_mean" → "prior_kd"
    f = feature[2:] if feature[:2] in ("a_", "b_") else feature
    return f[:-5] if f.endswith("_mean") else f


def _delta(fv: dict, base: str) -> float:
    return float(fv.get(f"a_{base}_mean", 0.0)) - float(fv.get(f"b_{base}_mean", 0.0))


def _sentence_for(feature: str, fv: dict) -> dict | None:
    base = _base_of(feature)
    for key, noun, fmt in _TEMPLATES:
        if key in base:
            d = _delta(fv, base)
            if abs(d) < 1e-9:
                return None
            side = "팀 A" if d > 0 else "팀 B"
            tail = fmt(d)
            text = f"{side} 우위: {noun}" + (f"가 {tail} 우세" if tail else "이 더 많음")
            return {"feature": feature, "text": text, "magnitude": abs(d)}
    return None


def explanations(result: Any) -> list[dict]:
    fv = result.feature_values or {}
    out: list[dict] = []
    seen_bases: set[str] = set()

    # 대표 문장: 직전연도 경험(prior_games)
    dg = _delta(fv, "prior_games")
    if abs(dg) >= 1:
        side = "팀 A" if dg > 0 else "팀 B"
        out.append({"feature": "prior_games",
                    "text": f"{side} 우세 요인: 직전 연도 경험이 평균 대비 {abs(dg):.0f}경기 많음",
                    "magnitude": abs(dg)})
        seen_bases.add("prior_games")

    # top_features 기반 추가 (패밀리 중복 제외)
    for f in result.top_features:
        base = _base_of(f["feature"])
        if any(base.startswith(b) for b in seen_bases):
            continue
        s = _sentence_for(f["feature"], fv)
        if s:
            out.append(s)
            seen_bases.add(base)
        if len(out) >= 4:
            break
    return out


# ── 메인 직렬화 ───────────────────────────────────────
def serialize_prediction(r: Any) -> dict:
    rc_a = _role_counts(r.role_counts.get("A팀", {}))
    rc_b = _role_counts(r.role_counts.get("B팀", {}))
    return {
        "map": r.map_name,
        "cutoff_year": None,
        "predicted_winner": "A" if r.predicted_label == 1 else "B",
        "predicted_label": int(r.predicted_label),
        "confidence": float(r.confidence),
        "team_a": {"name": r.team_a, "win_probability": float(r.team_a_win_probability)},
        "team_b": {"name": r.team_b, "win_probability": float(r.team_b_win_probability)},
        "role_counts": {"team_a": rc_a, "team_b": rc_b},
        "top_features": [{**f, "label": feature_label(f["feature"])} for f in r.top_features],
        "model": {
            "contract": r.model_metadata.get("feature_contract", "advanced"),
            "n_features": r.model_metadata.get("n_features", 125),
        },
        "explanations": explanations(r),
        "balance": {"team_a": balance_warnings(rc_a), "team_b": balance_warnings(rc_b)},
        "match_key": r.match_key,
        "actual_label": r.actual_label,
        "actual_winner": (None if r.actual_label is None
                          else ("A" if r.actual_label == 1 else "B")),
        "hit": (None if r.actual_label is None
                else bool(r.predicted_label == r.actual_label)),
    }
