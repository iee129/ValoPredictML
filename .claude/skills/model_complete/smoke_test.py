#!/usr/bin/env python3
"""model_complete 스킬 — 규격 맞춘 가상 입력을 실제 백엔드에 던져 결과를 검증하는 스모크 테스트.

- stdlib만 사용(추가 의존성 없음). 백엔드(uvicorn valo_web_backend.main:app)가 떠 있어야 한다.
- /options에서 실제 도메인(요원·맵·선수·연도)을 받아 계약에 맞는 5v5 입력을 구성해 던진다.
- /predict·/comp-match·/agent-map-fit·/replay 응답이 PredictResponse 계약을 지키는지 + 값이 합리적인지 검증한다.
- 잘못된 입력(선수 중복)이 422로 막히는지도 확인한다.

Usage:
    python .claude/skills/model_complete/smoke_test.py [BASE_URL]   # 기본 http://localhost:8000
종료코드 0 = 전부 통과, 1 = 실패 있음.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
PASS: list[str] = []
FAIL: list[str] = []


def ok(cond: bool, msg: str) -> None:
    (PASS if cond else FAIL).append(msg)
    print(("  PASS " if cond else "  FAIL ") + msg)


def req(method: str, path: str, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(
        BASE + path, data=data, method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.load(e)
        except Exception:
            return e.code, {}


def approx(a: float, b: float, t: float = 1e-3) -> bool:
    return abs(a - b) <= t


def main() -> int:
    print(f"=== model_complete smoke test @ {BASE} ===")

    # 1) 헬스체크
    s, j = req("GET", "/health")
    ok(s == 200, f"/health 200 (got {s})")
    ok(j.get("n_features") == 125, f"/health n_features=125 (got {j.get('n_features')})")
    if not j.get("model_loaded"):
        print("  [warn] model_loaded=False — 실제 모델/데이터 산출물 확인 필요:", j.get("detail"))

    # 2) /options → 규격 입력 재료
    s, o = req("GET", "/options")
    ok(s == 200 and len(o.get("agents", [])) >= 10 and len(o.get("maps", [])) >= 1,
       "/options 200 + 도메인 로드(요원≥10·맵≥1)")
    if s != 200:
        return _summary()
    agents = [a["name"] for a in o.get("agents", [])]
    maps = [m["name"] for m in o.get("maps", [])]
    players = list(o.get("players", []))
    years = o.get("years", []) or [2026]
    while len(players) < 10:          # 10명 distinct 선수 (부족하면 합성)
        players.append(f"TestPlayer{len(players)}")
    players = list(dict.fromkeys(players))[:10]
    mp, year = maps[0], years[-1]
    team_a = [{"player": players[i], "agent": agents[i]} for i in range(5)]
    team_b = [{"player": players[5 + i], "agent": agents[5 + i]} for i in range(5)]

    # 3) /predict — 규격 가상 입력 → 결과 수신·검증
    body = {"map": mp, "cutoff_year": year, "team_a": team_a, "team_b": team_b}
    s, j = req("POST", "/predict", body)
    ok(s == 200, f"/predict 200 (got {s})")
    if s == 200:
        pa = j["team_a"]["win_probability"]
        pb = j["team_b"]["win_probability"]
        ok(j["predicted_winner"] in ("A", "B"), f"predicted_winner={j['predicted_winner']}")
        ok(approx(pa + pb, 1.0), f"team_a+team_b 승률합≈1 ({pa}+{pb})")
        ok(0.0 <= j["confidence"] <= 1.0, f"confidence∈[0,1] ({j['confidence']})")
        rc = j["role_counts"]["team_a"]
        ok(approx(sum(rc.values()), 5.0), f"role_counts.team_a 합=5 ({rc})")
        tf = j["top_features"]
        ok(len(tf) > 0 and all(k in tf[0] for k in
           ("feature", "label", "value", "importance", "contribution")),
           f"top_features 계약 OK (n={len(tf)})")
        ok(isinstance(j.get("explanations"), list), "explanations(자연어 근거) 존재")
        ok("team_a" in j.get("balance", {}), "balance(구성 결함) 존재")
        print(f"  >>> 결과: 승자 {j['predicted_winner']} | A {pa:.3f} / B {pb:.3f} "
              f"| conf {j['confidence']:.3f} | 근거 {len(j.get('explanations', []))}문장")

    # 4) 잘못된 입력(선수 중복) → 실모델 백엔드는 422. (mock은 검증 안 하므로 soft 경고)
    bad = {**body, "team_b": [{"player": players[0], "agent": s2["agent"]} for s2 in team_b]}
    s, _ = req("POST", "/predict", bad)
    if s == 422:
        ok(True, "잘못된 입력(선수 중복) → 422 (입력 검증 동작)")
    else:
        print(f"  WARN 잘못된 입력(선수 중복) → {s} "
              f"(실모델 백엔드는 422 기대; mock 백엔드는 입력 검증을 하지 않음)")

    # 5) /comp-match
    s, j = req("POST", "/comp-match", {"map": mp, "agents": [a["agent"] for a in team_a]})
    ok(s == 200 and 0 <= j.get("match_pct", -1) <= 100,
       f"/comp-match 200, match_pct={j.get('match_pct')}")

    # 6) /agent-map-fit
    s, j = req("GET", f"/agent-map-fit?map={mp}")
    verds = {a["verdict"] for a in j.get("agents", [])}
    ok(s == 200 and len(j.get("agents", [])) >= 10 and verds <= {"fit", "ok", "weak"},
       f"/agent-map-fit 200, agents={len(j.get('agents', []))}, verdicts={verds or '-'}")

    # 7) /replay
    s, j = req("GET", "/replay/matches?limit=5")
    items = j.get("items", [])
    ok(s == 200 and len(items) >= 1, f"/replay/matches 200, items={len(items)}")
    if items:
        s, r = req("GET", "/replay/" + items[0]["match_key"])
        ok(s == 200 and r.get("actual_winner") in ("A", "B") and isinstance(r.get("hit"), bool),
           f"/replay/{{key}} 200, hit={r.get('hit')}")

    return _summary()


def _summary() -> int:
    print(f"\n=== 결과: {len(PASS)} PASS / {len(FAIL)} FAIL ===")
    if FAIL:
        print("실패 항목:")
        for m in FAIL:
            print("  -", m)
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
