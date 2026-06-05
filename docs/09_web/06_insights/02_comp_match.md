# 02. 메타 조합 매칭률 % — 차별점 K

사용자가 짠 5인 구성이 "이 맵에서 자주 통하는 조합"과 얼마나 비슷한지 %로 보여준다.

---

## 1. 조합의 표현 — 역할 구성 벡터

요원 5개 집합(agent-set)은 너무 희소(조합 폭발)하다. 안정적인 단위는 **역할 구성 벡터** `(duelist, initiator, controller, sentinel)`이며 합은 항상 5. 예:

```
[Jett, Sova, Omen, Killjoy, KAY/O] → (1, 2, 1, 1)   # 타1 척2 전1 감1
```

역할 매핑은 `ml/agent_roles.py`의 `AGENT_ROLE_MAP` (29종 → 4역할). 보조로 agent-set Jaccard(키픽 대비)도 곁들일 수 있다(§4).

---

## 2. 메타 조합 마이닝 (오프라인)

`data/processed/matches.csv`에서 **승리한 쪽의 역할 구성**을 맵별로 집계:

```
for m in matches (kaggle_):
  win_agents = agents_a if m.label==1 else agents_b
  comp = role_vector(win_agents)            # (d,i,c,s)
  meta[m.map][comp] += 1
맵별 정규화 → 각 comp의 win_share = count / sum(counts)
top-K(예: 5) 저장
```

→ `reports/insights/meta_comps.json`:
```json
{
  "Ascent": {
    "total_wins": 1920,
    "top": [
      { "comp": [1,2,1,1], "win_share": 0.34 },
      { "comp": [2,1,1,1], "win_share": 0.21 },
      { "comp": [1,1,2,1], "win_share": 0.12 }
    ]
  }
}
```

빌드 잡 상세 → [05_precompute_and_data.md](05_precompute_and_data.md).

---

## 3. 매칭률 계산

역할 벡터는 합이 5로 같으므로 L1 거리로 유사도를 정의한다. 한 칸 교체(한 역할 −1, 다른 역할 +1)는 L1=2. 완전히 다른 극단은 L1=10.

```python
def similarity(u, v):                  # u, v: (d,i,c,s), 합=5
    l1 = sum(abs(a-b) for a, b in zip(u, v))   # 0..10
    return 1.0 - l1 / 10.0                      # 1.0(동일) .. 0.0

def match_pct(map, agents, meta):
    u = role_vector(agents)
    tops = meta[map]["top"]
    # 가장 가까운 메타 + win_share 가중 평균을 함께 제공
    nearest = max(tops, key=lambda t: similarity(u, tuple(t["comp"])))
    weighted = sum(similarity(u, tuple(t["comp"])) * t["win_share"] for t in tops)
    return {
        "match_pct": round(similarity(u, tuple(nearest["comp"])) * 100, 1),
        "weighted_pct": round(weighted * 100, 1),
        "nearest_comp": nearest["comp"],
        "nearest_win_share": nearest["win_share"],
        "user_comp": list(u),
    }
```

- `match_pct`: 가장 가까운 상위 메타와의 유사도 (대표 숫자, UI 강조)
- `weighted_pct`: 상위 메타 분포 전체에 대한 가중 유사도 (해석 보조)

예: 사용자 `(2,1,1,1)`, 최근접 메타 `(1,2,1,1)` → L1=2 → **80% 일치**, 메시지 "이 맵 승리 조합 1위(승리의 34%)와 한 자리 차이".

---

## 4. (보조) agent-set 신호

역할이 같아도 요원이 다를 수 있다. `maps.md` "키 픽 5"와의 Jaccard를 보조 표시 가능:
```
jaccard = |user_agents ∩ key_picks| / |user_agents ∪ key_picks|
```
"키 픽 5명 중 3명 포함" 같은 부가 문구로만 쓰고, 대표 % 는 역할 벡터 기반을 유지(데이터 견고).

---

## 5. 엔드포인트 — `POST /comp-match`

한 팀씩 평가(프론트가 A·B 각각 호출). 입력은 요원 5개면 충분(선수 불필요 — 모델과 무관).

### Request
```json
{ "map": "Ascent", "agents": ["Jett","Reyna","Omen","Killjoy","Sova"] }
```

### Response
```json
{
  "map": "Ascent",
  "match_pct": 80.0,
  "weighted_pct": 63.4,
  "user_comp": { "duelist": 2, "initiator": 1, "controller": 1, "sentinel": 1 },
  "nearest_comp": { "duelist": 1, "initiator": 2, "controller": 1, "sentinel": 1 },
  "nearest_win_share": 0.34,
  "message": "이 맵 승리 조합 1위(승리의 34%)와 역할 한 자리 차이 — 척후대 1↔타격대 1"
}
```

스키마:
```python
class CompMatchRequest(BaseModel):
    map: str
    agents: conlist(str, min_length=5, max_length=5)

class CompMatchResponse(BaseModel):
    map: str
    match_pct: float; weighted_pct: float
    user_comp: RoleCounts; nearest_comp: RoleCounts
    nearest_win_share: float
    message: str
```

> 콜드스타트 없음(`meta_comps.json`만 로드). 슬롯이 5개 다 차면 디바운스(예: 400ms) 후 호출.

---

## 6. 프론트 표시

```ts
const r = await compMatch(map, teamAagents);   // 5개 다 찼을 때
// <MetaMatchBar pct={r.match_pct} message={r.message} />
```
- 큰 숫자 `match_pct%` + 진행 바
- `message`로 무엇이 다른지 한 줄 설명
- `weighted_pct`는 작게 보조 표기

타입:
```ts
export interface CompMatchResponse {
  map: string; match_pct: number; weighted_pct: number;
  user_comp: RoleCounts; nearest_comp: RoleCounts;
  nearest_win_share: number; message: string;
}
```

---

## 7. 한계

- "통하는 조합" = 과거 승리 빈도지 인과가 아님(강팀이 특정 구성을 많이 써서 생긴 편향 가능).
- 맵 표본이 적은 비활성 맵(Drift 등)은 `top`이 빈약 → `total_wins`가 임계 미만이면 "데이터 부족" 표기 권장.

---

## 8. 관련 문서

- 사전 집계 빌더 → [05_precompute_and_data.md](05_precompute_and_data.md)
- 구성 결함 알림 → [03_balance_warning.md](03_balance_warning.md)
