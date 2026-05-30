# 01. 요원-맵 적합도 (슬롯 ✓ / △ / ✗) — 차별점 N

각 슬롯에서 고른 요원이 그 맵에 어울리는지 배지로 표시한다. 맵을 고르는 순간 29종 요원 각각의 판정을 받아, 셀렉트/슬롯에 ✓(적합)·△(보통)·✗(비추천)을 띄운다.

---

## 1. 데이터 소스 — 2단 (데이터 우선, 룰 fallback)

### (a) 데이터 기반 (1순위)

`data/processed/matches.csv`에서 맵별 요원 픽률·승률을 집계한다. 사용 컬럼: `map`, `agents_a`, `agents_b`, `label`(1=team_a 승), `source`(kaggle_ 필터).

```
각 매치 m (source startswith kaggle_):
  map = m.map
  win_side  = agents_a if m.label==1 else agents_b
  lose_side = agents_b if m.label==1 else agents_a
  for agent in win_side:  stat[map][agent].games += 1; .wins += 1
  for agent in lose_side: stat[map][agent].games += 1
맵별 총 매치수 = matches_on_map
pick_rate[map][agent] = stat.games / (2 * matches_on_map)   # 양 팀 합 기준
win_rate[map][agent]  = stat.wins / stat.games
```

> `agents_a`/`agents_b`는 `"Jett|Sova|..."` 형태(파이프 구분). `ml/valorant.py`의 `normalize_agent`로 정규화 후 집계.

### (b) 도메인 룰 fallback (표본 부족 시)

신규/저표본 요원(Miks·Veto·Waylay 등)은 맵 데이터가 적다. 이때 `docs/10_valorant`의 산문을 룩업 테이블로 인코딩해 사용:
- `agents.md` 각 요원 카드 **"강한 맵"** (예: `Jett → Haven, Split, Ascent, Fracture`)
- `maps.md` 각 맵 카드 **"키 픽"** / **"약한 요원"** (예: `Ascent 약한 요원: Brimstone, Phoenix`)

→ `valo_web_backend/data/agent_map_rules.json` (손수 1회 인코딩):
```json
{
  "Ascent": { "key_picks": ["Omen","Sova","Killjoy","Jett","KAY/O"],
              "weak": ["Brimstone","Phoenix"] },
  "_agent_strong_maps": { "Jett": ["Haven","Split","Ascent","Fracture"] }
}
```

---

## 2. 판정 규칙

표본이 충분하면 데이터, 아니면 룰:

```python
P_HI, P_LO, N_MIN = 0.12, 0.03, 20   # 튜닝 상수

def verdict(map, agent, data, rules):
    s = data.get((map, agent))
    if s and s.games >= N_MIN:                 # 데이터 기반
        if s.pick_rate >= P_HI: return "fit"   # ✓
        if s.pick_rate <  P_LO: return "weak"  # ✗
        return "ok"                            # △
    # 룰 fallback
    if agent in rules[map]["key_picks"]:        return "fit"
    if agent in rules[map]["weak"]:             return "weak"
    if map in rules["_agent_strong_maps"].get(agent, []): return "fit"
    return "ok"
```

| 배지 | verdict | 의미 |
|:---:|---------|------|
| ✓ | `fit` | 이 맵에서 자주·잘 쓰임 (또는 룰상 키픽/강한맵) |
| △ | `ok` | 무난 / 표본 부족 |
| ✗ | `weak` | 이 맵에서 드물게 쓰임 (또는 룰상 약한 요원) |

---

## 3. 엔드포인트 — `GET /agent-map-fit?map=Ascent`

오프라인 빌드된 `reports/insights/agent_map_fit.json`을 로드해 응답(콜드스타트 없음).

### Response
```json
{
  "map": "Ascent",
  "agents": [
    { "name": "Omen",  "role": "controller", "verdict": "fit",  "pick_rate": 0.71, "win_rate": 0.52, "sample": 1840, "source": "data" },
    { "name": "Jett",  "role": "duelist",    "verdict": "fit",  "pick_rate": 0.40, "win_rate": 0.50, "sample": 1020, "source": "data" },
    { "name": "Brimstone","role":"controller","verdict":"weak", "pick_rate": 0.02, "win_rate": 0.47, "sample": 60,   "source": "data" },
    { "name": "Miks",  "role": "controller", "verdict": "ok",   "pick_rate": null, "win_rate": null, "sample": 3,    "source": "rule" }
  ]
}
```

스키마(`valo_web_backend/schemas.py`):
```python
class AgentFit(BaseModel):
    name: str; role: str
    verdict: Literal["fit","ok","weak"]
    pick_rate: float | None; win_rate: float | None
    sample: int; source: Literal["data","rule"]

class AgentMapFitResponse(BaseModel):
    map: str
    agents: list[AgentFit]
```

빌드 잡은 [05_precompute_and_data.md](05_precompute_and_data.md).

---

## 4. 프론트 표시 (TypeScript)

```ts
// 맵 선택 시 1회 호출 → Map<agentName, verdict>
const fit = await getAgentMapFit(map);            // GET /agent-map-fit?map=
const fitByAgent = new Map(fit.agents.map(a => [a.name, a]));

const BADGE = { fit: "✓", ok: "△", weak: "✗" } as const;
const TONE  = { fit: "green", ok: "gray", weak: "red" } as const;

// 요원 셀렉트 옵션 라벨: "Jett ✓"  / 슬롯에 채워지면 슬롯 우상단 배지
```

타입:
```ts
export interface AgentFit {
  name: string; role: Role;
  verdict: "fit" | "ok" | "weak";
  pick_rate: number | null; win_rate: number | null;
  sample: number; source: "data" | "rule";
}
export interface AgentMapFitResponse { map: string; agents: AgentFit[] }
```

UX: 맵을 바꾸면 배지 전부 갱신. 슬롯에 ✗ 요원이 들어가면 슬롯 테두리를 경고색으로, 툴팁에 "이 맵에서 픽률 N%(표본 M)" 노출.

---

## 5. 한계·주의

- 픽률/승률은 **과거 프로 메타**(2021–2024 Kaggle) 기준 → 최신 패치 메타와 다를 수 있음(맵 로테이션·신요원).
- `win_rate`는 표본 적을 때 흔들리므로 **배지는 pick_rate 기준**, win_rate는 툴팁 보조 지표로만.
- 신규 요원은 거의 룰 fallback → `source: "rule"`을 UI에 표기해 출처를 투명하게.

---

## 6. 관련 문서

- 사전 집계 빌더 → [05_precompute_and_data.md](05_precompute_and_data.md)
- 메타 조합 매칭률 → [02_comp_match.md](02_comp_match.md)
