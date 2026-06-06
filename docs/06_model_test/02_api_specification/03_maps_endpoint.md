> ⚠️ 참고/확장 설계: 현재 시연은 웹 스택(FastAPI `src/api` + Next.js `web`) 기준이다. 이 문서의 테스트 설계는 참고용으로 보존한다.

> ⚠️ **참고용**: 본 프로젝트는 웹 스택(FastAPI `src/api` + Next.js `web`)으로 서빙한다. 본문의 상세 테스트 설계는 참고용으로 보존된다.

# 03. GET /maps 엔드포인트 완전 스펙

## 1. 기본 정보

| 항목 | 내용 |
|------|------|
| 메서드 | GET |
| 경로 | /maps |
| 인증 | 없음 |
| 응답 캐싱 | 권장 (정적 데이터) |
| 목표 응답시간 | ≤ 30ms |

---

## 2. 요청

```bash
curl http://localhost:8000/maps
```

쿼리 파라미터 없음.

---

## 3. 응답 스키마 (HTTP 200)

```json
{
  "maps": [
    {
      "name": "Ascent",
      "name_kr": "어센트",
      "region": "Italy",
      "callouts": ["A Main", "B Main", "Mid", "Catwalk", "Market"]
    },
    {
      "name": "Bind",
      "name_kr": "바인드",
      "region": "Morocco",
      "callouts": ["A Short", "B Long", "Hookah", "Showers", "Teleport"]
    },
    {
      "name": "Haven",
      "name_kr": "헤이븐",
      "region": "Bhutan",
      "callouts": ["A Long", "B Mid", "C Long", "Garage", "Courtyard"]
    },
    {
      "name": "Split",
      "name_kr": "스플릿",
      "region": "Japan",
      "callouts": ["A Main", "B Main", "Mid", "Ropes", "Vent"]
    },
    {
      "name": "Icebox",
      "name_kr": "아이스박스",
      "region": "Arctic",
      "callouts": ["A Site", "B Site", "Mid", "Tube", "Kitchen"]
    },
    {
      "name": "Breeze",
      "name_kr": "브리즈",
      "region": "Caribbean",
      "callouts": ["A Hall", "B Hall", "Mid", "Cave", "Elbow"]
    },
    {
      "name": "Fracture",
      "name_kr": "프랙처",
      "region": "Southwest USA",
      "callouts": ["A Drop", "B Arcade", "Mid", "Dish", "Tunnel"]
    },
    {
      "name": "Pearl",
      "name_kr": "펄",
      "region": "Underwater Portugal",
      "callouts": ["A Main", "B Main", "Mid", "Art", "Shops"]
    },
    {
      "name": "Lotus",
      "name_kr": "로터스",
      "region": "India",
      "callouts": ["A Main", "B Main", "C Main", "Ropes", "Waterfall"]
    },
    {
      "name": "Sunset",
      "name_kr": "선셋",
      "region": "Los Angeles",
      "callouts": ["A Main", "B Main", "Mid", "Alley", "Market"]
    },
    {
      "name": "Abyss",
      "name_kr": "어비스",
      "region": "Unknown",
      "callouts": ["A Main", "B Main", "Mid", "Pit", "Bridge"]
    }
  ],
  "total": 11
}
```

---

## 4. 간소화 응답 형식 (단순 목록)

일부 클라이언트에서는 이름만 필요한 경우:

```json
{
  "maps": ["Ascent", "Bind", "Haven", "Split", "Icebox",
           "Breeze", "Fracture", "Pearl", "Lotus", "Sunset", "Abyss"],
  "total": 11
}
```

---

## 5. 백엔드 구현 코드

```python
# backend/routers/maps.py
from fastapi import APIRouter
from schemas.maps import MapsResponse
from data.map_data import MAPS

router = APIRouter()

@router.get("/maps", response_model=MapsResponse)
async def get_maps():
    """발로란트 경쟁 맵 풀 목록을 반환합니다."""
    return {
        "maps": [
            {
                "name": name,
                "name_kr": info["name_kr"],
                "region": info["region"],
                "callouts": info["callouts"],
            }
            for name, info in MAPS.items()
        ],
        "total": len(MAPS)
    }
```

```python
# backend/data/map_data.py
MAPS = {
    "Ascent":   {"name_kr": "어센트",   "region": "Italy",                 "callouts": ["A Main","B Main","Mid","Catwalk","Market"]},
    "Bind":     {"name_kr": "바인드",   "region": "Morocco",               "callouts": ["A Short","B Long","Hookah","Showers","Teleport"]},
    "Haven":    {"name_kr": "헤이븐",   "region": "Bhutan",                "callouts": ["A Long","B Mid","C Long","Garage","Courtyard"]},
    "Split":    {"name_kr": "스플릿",   "region": "Japan",                 "callouts": ["A Main","B Main","Mid","Ropes","Vent"]},
    "Icebox":   {"name_kr": "아이스박스","region": "Arctic",               "callouts": ["A Site","B Site","Mid","Tube","Kitchen"]},
    "Breeze":   {"name_kr": "브리즈",   "region": "Caribbean",             "callouts": ["A Hall","B Hall","Mid","Cave","Elbow"]},
    "Fracture": {"name_kr": "프랙처",   "region": "Southwest USA",         "callouts": ["A Drop","B Arcade","Mid","Dish","Tunnel"]},
    "Pearl":    {"name_kr": "펄",       "region": "Underwater Portugal",   "callouts": ["A Main","B Main","Mid","Art","Shops"]},
    "Lotus":    {"name_kr": "로터스",   "region": "India",                 "callouts": ["A Main","B Main","C Main","Ropes","Waterfall"]},
    "Sunset":   {"name_kr": "선셋",     "region": "Los Angeles",           "callouts": ["A Main","B Main","Mid","Alley","Market"]},
    "Abyss":    {"name_kr": "어비스",   "region": "Unknown",               "callouts": ["A Main","B Main","Mid","Pit","Bridge"]},
}

# POST /predict 검증에서 사용하는 이름 집합
VALID_MAP_NAMES = set(MAPS.keys())
```

---

## 6. Pydantic 스키마

```python
# backend/schemas/maps.py
from pydantic import BaseModel
from typing import List

class MapInfo(BaseModel):
    name: str
    name_kr: str
    region: str
    callouts: List[str]

class MapsResponse(BaseModel):
    maps: List[MapInfo]
    total: int

    model_config = {"json_schema_extra": {
        "example": {
            "maps": [{"name":"Ascent","name_kr":"어센트","region":"Italy","callouts":["A Main","B Main"]}],
            "total": 11
        }
    }}
```

---

## 7. 테스트 케이스

```python
# tests/integration/test_maps_endpoint.py
import pytest

def test_get_maps_returns_200(client):
    response = client.get("/maps")
    assert response.status_code == 200

def test_get_maps_returns_11_maps(client):
    data = client.get("/maps").json()
    assert data["total"] == 11
    assert len(data["maps"]) == 11

def test_get_maps_includes_all_expected_maps(client):
    expected = {
        "Ascent","Bind","Haven","Split","Icebox",
        "Breeze","Fracture","Pearl","Lotus","Sunset","Abyss"
    }
    data = client.get("/maps").json()
    actual = {m["name"] for m in data["maps"]}
    assert actual == expected

def test_get_maps_each_map_has_required_fields(client):
    maps = client.get("/maps").json()["maps"]
    for m in maps:
        assert "name" in m
        assert "name_kr" in m
        assert "region" in m
        assert "callouts" in m
        assert isinstance(m["callouts"], list)
        assert len(m["callouts"]) > 0

def test_get_maps_names_match_predict_valid_maps(client):
    """GET /maps 반환 맵 이름이 POST /predict VALID_MAPS와 일치해야 함."""
    from backend.schemas.predict import VALID_MAPS
    maps_data = client.get("/maps").json()
    returned_names = {m["name"] for m in maps_data["maps"]}
    assert returned_names == VALID_MAPS

@pytest.mark.performance
def test_get_maps_response_time(client):
    import time
    start = time.perf_counter()
    client.get("/maps")
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms < 30, f"응답시간 초과: {elapsed_ms:.1f}ms (목표: 30ms)"
```

---

## 8. curl 테스트 명령어

```bash
# 기본 조회
curl http://localhost:8000/maps | python3 -m json.tool

# 맵 이름만 추출
curl -s http://localhost:8000/maps | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'총 {data[\"total\"]}개 맵:')
for m in data['maps']:
    print(f'  - {m[\"name\"]} ({m[\"name_kr\"]})')
"

# 응답시간 측정
curl -s -o /dev/null -w "응답시간: %{time_total}s\n" http://localhost:8000/maps
```

---

## 9. 프론트엔드 활용 예시

```typescript
// frontend/components/MapSelector.tsx
import { useEffect, useState } from "react";

interface MapInfo {
  name: string;
  name_kr: string;
  region: string;
  callouts: string[];
}

export function MapSelector({ onSelect }: { onSelect: (map: string) => void }) {
  const [maps, setMaps] = useState<MapInfo[]>([]);

  useEffect(() => {
    fetch(`/api/maps`)
      .then(r => r.json())
      .then(data => setMaps(data.maps));
  }, []);

  return (
    <select onChange={e => onSelect(e.target.value)}>
      <option value="">맵 선택</option>
      {maps.map(m => (
        <option key={m.name} value={m.name}>
          {m.name_kr} ({m.name})
        </option>
      ))}
    </select>
  );
}
```
