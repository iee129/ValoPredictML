> ⚠️ **범위 외**: FastAPI 미사용. 본 프로젝트는 Streamlit 로컬 도구이며 API 엔드포인트 테스트는 적용되지 않는다. 본문은 참고용으로 보존된다.

# 02. GET /agents 엔드포인트 완전 스펙

## 1. 기본 정보

| 항목 | 내용 |
|------|------|
| 메서드 | GET |
| 경로 | /agents |
| 인증 | 없음 |
| 응답 캐싱 | 권장 (정적 데이터) |
| 목표 응답시간 | ≤ 50ms |

---

## 2. 요청

쿼리 파라미터 없음. 단순 GET 요청입니다.

```bash
curl http://localhost:8000/agents
```

---

## 3. 응답 스키마 (HTTP 200)

```json
{
  "agents": [
    {"name": "Jett",      "role": "Duelist",    "role_kr": "타격대"},
    {"name": "Reyna",     "role": "Duelist",    "role_kr": "타격대"},
    {"name": "Neon",      "role": "Duelist",    "role_kr": "타격대"},
    {"name": "Yoru",      "role": "Duelist",    "role_kr": "타격대"},
    {"name": "Phoenix",   "role": "Duelist",    "role_kr": "타격대"},
    {"name": "Iso",       "role": "Duelist",    "role_kr": "타격대"},
    {"name": "Waylay",    "role": "Duelist",    "role_kr": "타격대"},
    {"name": "Sova",      "role": "Initiator",  "role_kr": "척후대"},
    {"name": "Breach",    "role": "Initiator",  "role_kr": "척후대"},
    {"name": "Skye",      "role": "Initiator",  "role_kr": "척후대"},
    {"name": "Fade",      "role": "Initiator",  "role_kr": "척후대"},
    {"name": "Gekko",     "role": "Initiator",  "role_kr": "척후대"},
    {"name": "KAY/O",     "role": "Initiator",  "role_kr": "척후대"},
    {"name": "Tejo",      "role": "Initiator",  "role_kr": "척후대"},
    {"name": "Viper",     "role": "Controller", "role_kr": "전략가"},
    {"name": "Omen",      "role": "Controller", "role_kr": "전략가"},
    {"name": "Brimstone", "role": "Controller", "role_kr": "전략가"},
    {"name": "Astra",     "role": "Controller", "role_kr": "전략가"},
    {"name": "Harbor",    "role": "Controller", "role_kr": "전략가"},
    {"name": "Clove",     "role": "Controller", "role_kr": "전략가"},
    {"name": "Killjoy",   "role": "Sentinel",   "role_kr": "감시자"},
    {"name": "Cypher",    "role": "Sentinel",   "role_kr": "감시자"},
    {"name": "Sage",      "role": "Sentinel",   "role_kr": "감시자"},
    {"name": "Chamber",   "role": "Sentinel",   "role_kr": "감시자"},
    {"name": "Deadlock",  "role": "Sentinel",   "role_kr": "감시자"},
    {"name": "Vyse",      "role": "Sentinel",   "role_kr": "감시자"},
    {"name": "Omen",      "role": "Controller", "role_kr": "전략가"}
  ],
  "roles": {
    "Duelist": {
      "name_kr": "타격대",
      "description": "돌파구를 만드는 공격형 역할",
      "count": 7
    },
    "Initiator": {
      "name_kr": "척후대",
      "description": "정보 수집 및 진입 지원 역할",
      "count": 7
    },
    "Controller": {
      "name_kr": "전략가",
      "description": "스모크와 구역 통제 역할",
      "count": 6
    },
    "Sentinel": {
      "name_kr": "감시자",
      "description": "수비 및 팀 지원 역할",
      "count": 6
    }
  },
  "total": 26
}
```

---

## 4. 응답 필드 정의

| 필드 | 타입 | 설명 |
|------|------|------|
| agents | array | 전체 요원 목록 |
| agents[].name | string | 요원 이름 (영어, POST /predict에서 사용) |
| agents[].role | string | 역할군 영어 이름 |
| agents[].role_kr | string | 역할군 한국어 이름 |
| roles | object | 역할군별 메타데이터 |
| roles[role].name_kr | string | 역할군 한국어 이름 |
| roles[role].description | string | 역할군 설명 |
| roles[role].count | integer | 해당 역할군 요원 수 |
| total | integer | 전체 요원 수 |

---

## 5. 백엔드 구현 코드

```python
# backend/routers/agents.py
from fastapi import APIRouter
from schemas.agents import AgentsResponse
from data.agent_data import AGENTS, ROLES

router = APIRouter()

@router.get("/agents", response_model=AgentsResponse)
async def get_agents():
    """발로란트 전체 요원 목록과 역할군 정보를 반환합니다."""
    return {
        "agents": [
            {
                "name": name,
                "role": info["role"],
                "role_kr": ROLES[info["role"]]["name_kr"]
            }
            for name, info in AGENTS.items()
        ],
        "roles": {
            role: {
                "name_kr": data["name_kr"],
                "description": data["description"],
                "count": sum(1 for a in AGENTS.values() if a["role"] == role)
            }
            for role, data in ROLES.items()
        },
        "total": len(AGENTS)
    }
```

```python
# backend/data/agent_data.py
AGENTS = {
    "Jett":      {"role": "Duelist"},
    "Reyna":     {"role": "Duelist"},
    "Neon":      {"role": "Duelist"},
    "Yoru":      {"role": "Duelist"},
    "Phoenix":   {"role": "Duelist"},
    "Iso":       {"role": "Duelist"},
    "Waylay":    {"role": "Duelist"},
    "Sova":      {"role": "Initiator"},
    "Breach":    {"role": "Initiator"},
    "Skye":      {"role": "Initiator"},
    "Fade":      {"role": "Initiator"},
    "Gekko":     {"role": "Initiator"},
    "KAY/O":     {"role": "Initiator"},
    "Tejo":      {"role": "Initiator"},
    "Viper":     {"role": "Controller"},
    "Omen":      {"role": "Controller"},
    "Brimstone": {"role": "Controller"},
    "Astra":     {"role": "Controller"},
    "Harbor":    {"role": "Controller"},
    "Clove":     {"role": "Controller"},
    "Killjoy":   {"role": "Sentinel"},
    "Cypher":    {"role": "Sentinel"},
    "Sage":      {"role": "Sentinel"},
    "Chamber":   {"role": "Sentinel"},
    "Deadlock":  {"role": "Sentinel"},
    "Vyse":      {"role": "Sentinel"},
}

ROLES = {
    "Duelist":    {"name_kr": "타격대",   "description": "돌파구를 만드는 공격형 역할"},
    "Initiator":  {"name_kr": "척후대",   "description": "정보 수집 및 진입 지원 역할"},
    "Controller": {"name_kr": "전략가",   "description": "스모크와 구역 통제 역할"},
    "Sentinel":   {"name_kr": "감시자",   "description": "수비 및 팀 지원 역할"},
}
```

---

## 6. 프론트엔드 활용 방식

```typescript
// frontend/lib/api.ts
export interface Agent {
  name: string;
  role: string;
  role_kr: string;
}

export interface AgentsResponse {
  agents: Agent[];
  roles: Record<string, { name_kr: string; description: string; count: number }>;
  total: number;
}

export async function fetchAgents(): Promise<AgentsResponse> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/agents`);
  if (!res.ok) throw new Error("요원 목록 로드 실패");
  return res.json();
}
```

```typescript
// 역할군별 그룹핑 (UI 렌더링용)
function groupByRole(agents: Agent[]) {
  return agents.reduce((acc, agent) => {
    const role = agent.role;
    if (!acc[role]) acc[role] = [];
    acc[role].push(agent);
    return acc;
  }, {} as Record<string, Agent[]>);
}
```

---

## 7. 테스트 케이스

```python
# tests/integration/test_agents_endpoint.py
import pytest

def test_get_agents_returns_200(client):
    response = client.get("/agents")
    assert response.status_code == 200

def test_get_agents_has_required_fields(client):
    data = client.get("/agents").json()
    assert "agents" in data
    assert "roles" in data
    assert "total" in data

def test_get_agents_each_agent_has_name_and_role(client):
    agents = client.get("/agents").json()["agents"]
    for agent in agents:
        assert "name" in agent
        assert "role" in agent
        assert "role_kr" in agent
        assert agent["role"] in ["Duelist", "Initiator", "Controller", "Sentinel"]

def test_get_agents_total_matches_list_length(client):
    data = client.get("/agents").json()
    assert data["total"] == len(data["agents"])

def test_get_agents_roles_has_four_categories(client):
    roles = client.get("/agents").json()["roles"]
    assert set(roles.keys()) == {"Duelist", "Initiator", "Controller", "Sentinel"}

@pytest.mark.performance
def test_get_agents_response_time(client):
    import time
    start = time.perf_counter()
    client.get("/agents")
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms < 50, f"응답시간 초과: {elapsed_ms:.1f}ms (목표: 50ms)"
```

---

## 8. 응답 캐싱 권장 설정

요원 목록은 정적 데이터이므로 HTTP 캐시 헤더를 적용할 수 있습니다.

```python
from fastapi import APIRouter
from fastapi.responses import JSONResponse

@router.get("/agents")
async def get_agents():
    data = {...}  # 위 구현과 동일
    response = JSONResponse(content=data)
    response.headers["Cache-Control"] = "public, max-age=3600"  # 1시간 캐시
    return response
```
