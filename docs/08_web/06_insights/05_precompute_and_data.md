# 05. 사전 집계 빌더 · 데이터 요건

요원-맵 적합도(N)와 메타 조합(K)은 `data/processed/matches.csv`를 1회 집계한 JSON에서 읽는다. 그 빌더를 정의한다. 모델 추론과 무관하므로 API는 JSON만 로드(콜드스타트 없음).

---

## 1. 입력 데이터 — `data/processed/matches.csv`

모델과 동일 소스 계약(`kaggle_*`). 사용 컬럼:

| 컬럼 | 용도 |
|------|------|
| `map` | 맵 키 (`normalize_map`) |
| `agents_a` / `agents_b` | `"Jett|Sova|..."` 파이프 구분 5요원 |
| `label` | 1 = `team_a` 승, 0 = `team_b` 승 |
| `source` | `kaggle_` 시작 행만 사용 |

> `agents_a`/`agents_b`는 `src/data/ingest.py`의 `_parse_agents`와 동일하게 파싱(`normalize_agent` + `_agent_col_key`). 역할은 `AGENT_ROLE_MAP`.

---

## 2. 빌더 — `src/insights/build_insights.py` (신규)

> `src/insights/`에 두면 `src/`처럼 커밋 가능 영역이다(`.gitignore` 허용목록). 산출 JSON은 `reports/insights/`(로컬 전용)로 나간다.

```python
"""인사이트 사전 집계: matches.csv → reports/insights/*.json

Usage:
    python -m insights.build_insights --input data/processed --output reports/insights
"""
from __future__ import annotations
import argparse, json
from collections import defaultdict
from pathlib import Path
import pandas as pd
from ml.valorant import AGENTS_SORTED, MAP_ORDER, normalize_agent, normalize_map
from ml.agent_roles import AGENT_ROLE_MAP

ROLES = ("duelist", "initiator", "controller", "sentinel")

def _agents(cell: str) -> list[str]:
    if not isinstance(cell, str): return []
    out = []
    for p in cell.split("|"):
        n = normalize_agent(p.strip())
        if n: out.append(n)
    return out

def _role_vec(agents: list[str]) -> tuple[int,int,int,int]:
    c = {r: 0 for r in ROLES}
    for a in agents:
        role = AGENT_ROLE_MAP.get(a, "").lower()
        if role in c: c[role] += 1
    return tuple(c[r] for r in ROLES)

def build(input_dir: str, output_dir: str) -> None:
    df = pd.read_csv(f"{input_dir}/matches.csv", low_memory=False)
    df = df[df["source"].astype(str).str.startswith("kaggle_")]

    am_games = defaultdict(int); am_wins = defaultdict(int); map_matches = defaultdict(int)
    comp = defaultdict(lambda: defaultdict(int))

    for row in df.itertuples(index=False):
        mp = normalize_map(str(getattr(row, "map", "")))
        if not mp: continue
        label = int(getattr(row, "label"))
        a, b = _agents(row.agents_a), _agents(row.agents_b)
        win, lose = (a, b) if label == 1 else (b, a)
        map_matches[mp] += 1
        for ag in win:  am_games[(mp,ag)] += 1; am_wins[(mp,ag)] += 1
        for ag in lose: am_games[(mp,ag)] += 1
        comp[mp][_role_vec(win)] += 1

    # (1) agent_map_fit.json
    P_HI, P_LO, N_MIN = 0.12, 0.03, 20
    fit = {}
    for mp in MAP_ORDER:
        if map_matches[mp] == 0: continue
        agents = []
        for ag in sorted({a for (m,a) in am_games if m == mp}):
            g = am_games[(mp,ag)]; w = am_wins[(mp,ag)]
            pr = g / (2 * map_matches[mp]); wr = w / g if g else 0.0
            if g >= N_MIN:
                v = "fit" if pr >= P_HI else ("weak" if pr < P_LO else "ok")
                src = "data"
            else:
                v, src = "ok", "rule"      # 룰 fallback은 API에서 agent_map_rules.json과 병합
            agents.append({"name": ag, "role": AGENT_ROLE_MAP.get(ag,"").lower(),
                           "verdict": v, "pick_rate": round(pr,4), "win_rate": round(wr,4),
                           "sample": g, "source": src})
        fit[mp] = {"map_matches": map_matches[mp], "agents": agents}

    # (2) meta_comps.json
    metas = {}
    for mp, dist in comp.items():
        total = sum(dist.values())
        top = sorted(dist.items(), key=lambda kv: -kv[1])[:5]
        metas[mp] = {"total_wins": total,
                     "top": [{"comp": list(k), "win_share": round(v/total,4)} for k,v in top]}

    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    (out/"agent_map_fit.json").write_text(json.dumps(fit, ensure_ascii=False, indent=2))
    (out/"meta_comps.json").write_text(json.dumps(metas, ensure_ascii=False, indent=2))
    print(f"maps={len(fit)}  meta_maps={len(metas)} → {out}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/processed")
    ap.add_argument("--output", default="reports/insights")
    a = ap.parse_args()
    build(a.input, a.output)
```

실행:
```bash
python -m insights.build_insights --input data/processed --output reports/insights
```

---

## 3. 산출물

| 파일 | 소비 엔드포인트 |
|------|------------------|
| `reports/insights/agent_map_fit.json` | `GET /agent-map-fit` ([01](01_agent_map_fit.md)) |
| `reports/insights/meta_comps.json` | `POST /comp-match` ([02](02_comp_match.md)) |
| `src/api/data/agent_map_rules.json` (손수 인코딩, 커밋) | `/agent-map-fit` 룰 fallback 병합 |

`src/api/data/agent_map_rules.json`은 `docs/09_valorant/{agents,maps}.md`의 "강한 맵 / 키 픽 / 약한 요원"을 사람이 1회 구조화한다(데이터로 안 잡히는 신규 요원 대비).

---

## 4. API 로딩

```python
# src/api/services/insights.py
import json
from functools import lru_cache
from pathlib import Path

BASE = Path("reports/insights")

@lru_cache(maxsize=1)
def agent_map_fit() -> dict:
    return json.loads((BASE/"agent_map_fit.json").read_text(encoding="utf-8"))

@lru_cache(maxsize=1)
def meta_comps() -> dict:
    return json.loads((BASE/"meta_comps.json").read_text(encoding="utf-8"))
```

서버 startup(`lifespan`)에서 두 JSON을 워밍해 두면 첫 요청도 즉시.

---

## 5. 재생성 시점

- `matches.csv`가 갱신될 때(데이터 추가/재전처리) 빌더 재실행.
- 모델 재학습과는 독립 — 인사이트만 다시 만들면 됨.
- 데모 런북에 한 줄 추가: 모델 학습 후 `python -m insights.build_insights` 실행 → [../04_integration/02_demo_runbook.md](../04_integration/02_demo_runbook.md).

---

## 6. 데이터 부족 시 동작

| 상황 | 처리 |
|------|------|
| `matches.csv` 없음 | 빌더 실패 → 런북 §1(데이터 생성) 선행. API는 인사이트 엔드포인트 503 |
| 특정 맵 표본 0 | 해당 맵 키 생략 → `/agent-map-fit`은 룰 fallback만, `/comp-match`는 "데이터 부족" |
| 신규 요원 저표본 | `source:"rule"`로 표시 |

---

## 7. 관련 문서

- 요원-맵 적합도 → [01_agent_map_fit.md](01_agent_map_fit.md)
- 메타 조합 → [02_comp_match.md](02_comp_match.md)
- 데이터 계약 → [../04_integration/01_data_contract.md](../04_integration/01_data_contract.md)
