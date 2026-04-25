# 04. GET /history 엔드포인트 완전 스펙

## 1. 기본 정보

| 항목 | 내용 |
|------|------|
| 메서드 | GET |
| 경로 | /history |
| 인증 | 없음 |
| 데이터 소스 | PostgreSQL predictions 테이블 |
| 목표 응답시간 | ≤ 100ms |

---

## 2. 요청 파라미터

| 파라미터 | 타입 | 기본값 | 설명 | 유효 범위 |
|---------|------|--------|------|----------|
| limit | integer | 20 | 한 번에 반환할 최대 건수 | 1 ~ 100 |
| offset | integer | 0 | 건너뛸 레코드 수 (페이지네이션) | 0 이상 |
| map | string | 없음 (전체) | 특정 맵 필터링 | VALID_MAPS 내 값 |

### 2.1 요청 예시

```bash
# 기본 조회 (최신 20건)
curl "http://localhost:8000/history"

# 페이지네이션 (2페이지, 페이지당 10건)
curl "http://localhost:8000/history?limit=10&offset=10"

# 맵 필터링
curl "http://localhost:8000/history?map=Ascent"

# 필터 + 페이지네이션 조합
curl "http://localhost:8000/history?map=Ascent&limit=5&offset=0"
```

---

## 3. 응답 스키마 (HTTP 200)

### 3.1 데이터 있는 경우

```json
{
  "total": 142,
  "limit": 20,
  "offset": 0,
  "items": [
    {
      "id": 142,
      "created_at": "2024-01-15T18:30:00+00:00",
      "map": "Ascent",
      "team_a_agents": ["Jett", "Sova", "Viper", "Killjoy", "Skye"],
      "team_b_agents": ["Reyna", "Breach", "Omen", "Cypher", "Fade"],
      "win_probability": 0.673,
      "confidence": "medium"
    },
    {
      "id": 141,
      "created_at": "2024-01-15T17:45:00+00:00",
      "map": "Bind",
      "team_a_agents": ["Neon", "Breach", "Viper", "Sage", "Cypher"],
      "team_b_agents": ["Jett", "Sova", "Omen", "Killjoy", "Skye"],
      "win_probability": 0.421,
      "confidence": "low"
    }
  ]
}
```

### 3.2 데이터 없는 경우

```json
{
  "total": 0,
  "limit": 20,
  "offset": 0,
  "items": []
}
```

### 3.3 맵 필터링 결과

```json
{
  "total": 38,
  "limit": 20,
  "offset": 0,
  "items": [
    {
      "id": 142,
      "created_at": "2024-01-15T18:30:00+00:00",
      "map": "Ascent",
      "team_a_agents": ["Jett", "Sova", "Viper", "Killjoy", "Skye"],
      "team_b_agents": ["Reyna", "Breach", "Omen", "Cypher", "Fade"],
      "win_probability": 0.673,
      "confidence": "medium"
    }
  ]
}
```

---

## 4. 응답 필드 정의

| 필드 | 타입 | 설명 |
|------|------|------|
| total | integer | 필터 조건 기준 전체 레코드 수 |
| limit | integer | 요청한 limit 값 (echo) |
| offset | integer | 요청한 offset 값 (echo) |
| items | array | 현재 페이지 예측 기록 목록 |
| items[].id | integer | 예측 고유 ID (자동 증가) |
| items[].created_at | string | ISO 8601 형식 생성 시각 (UTC+0) |
| items[].map | string | 예측에 사용된 맵 |
| items[].team_a_agents | array[string] | 팀 A 요원 목록 (5명) |
| items[].team_b_agents | array[string] | 팀 B 요원 목록 (5명) |
| items[].win_probability | float | 팀 A 승리 확률 (0.0~1.0) |
| items[].confidence | string | 신뢰도 등급 ("high"/"medium"/"low") |

---

## 5. 페이지네이션 동작 방식

```
전체 142건, limit=20, offset=0 → items 20건 (id 142~123)
전체 142건, limit=20, offset=20 → items 20건 (id 122~103)
전체 142건, limit=20, offset=140 → items 2건 (id 2~1)
전체 142건, limit=20, offset=200 → items 0건 (빈 배열)
```

### 페이지 번호 계산 (프론트엔드)

```typescript
// 현재 페이지 (0-indexed)
const currentPage = Math.floor(offset / limit);

// 전체 페이지 수
const totalPages = Math.ceil(total / limit);

// 다음 페이지 offset
const nextOffset = offset + limit < total ? offset + limit : null;

// 이전 페이지 offset
const prevOffset = offset > 0 ? Math.max(0, offset - limit) : null;
```

---

## 6. 백엔드 구현 코드

### 6.1 라우터

```python
# backend/routers/history.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from schemas.history import HistoryResponse
from models.prediction import Prediction

router = APIRouter()

@router.get("/history", response_model=HistoryResponse)
async def get_history(
    limit: int = Query(default=20, ge=1, le=100, description="반환할 최대 건수"),
    offset: int = Query(default=0, ge=0, description="건너뛸 레코드 수"),
    map: str | None = Query(default=None, description="맵 필터 (선택)"),
    db: Session = Depends(get_db),
):
    """예측 기록을 최신순으로 반환합니다."""
    query = db.query(Prediction).order_by(Prediction.id.desc())

    if map is not None:
        query = query.filter(Prediction.map == map)

    total = query.count()
    items = query.offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": item.id,
                "created_at": item.created_at.isoformat(),
                "map": item.map,
                "team_a_agents": item.team_a_agents,
                "team_b_agents": item.team_b_agents,
                "win_probability": item.win_probability,
                "confidence": item.confidence,
            }
            for item in items
        ]
    }
```

### 6.2 ORM 모델

```python
# backend/models/prediction.py
from sqlalchemy import Column, Integer, String, Float, DateTime, ARRAY
from sqlalchemy.sql import func
from database import Base

class Prediction(Base):
    __tablename__ = "predictions"

    id              = Column(Integer, primary_key=True, index=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    map             = Column(String(50), nullable=False, index=True)
    team_a_agents   = Column(ARRAY(String), nullable=False)
    team_b_agents   = Column(ARRAY(String), nullable=False)
    win_probability = Column(Float, nullable=False)
    confidence      = Column(String(10), nullable=False)
```

### 6.3 Pydantic 스키마

```python
# backend/schemas/history.py
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class HistoryItem(BaseModel):
    id: int
    created_at: str
    map: str
    team_a_agents: List[str]
    team_b_agents: List[str]
    win_probability: float
    confidence: str

class HistoryResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[HistoryItem]
```

---

## 7. DB 인덱스 설계

```sql
-- 최신순 조회 성능 (기본 정렬)
CREATE INDEX idx_predictions_id_desc ON predictions (id DESC);

-- 맵 필터링 성능
CREATE INDEX idx_predictions_map ON predictions (map);

-- 맵 필터 + 최신순 조합
CREATE INDEX idx_predictions_map_id ON predictions (map, id DESC);

-- 생성일 기준 조회 (향후 날짜 필터 추가 시)
CREATE INDEX idx_predictions_created_at ON predictions (created_at DESC);
```

---

## 8. 테스트 케이스

```python
# tests/integration/test_history_endpoint.py
import pytest

def test_history_empty_returns_200(client):
    response = client.get("/history")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []

def test_history_after_predict_returns_record(client):
    # 예측 수행 → DB에 저장됨
    client.post("/predict", json={
        "map": "Ascent",
        "team_a": ["Jett","Sova","Viper","Killjoy","Skye"],
        "team_b": ["Reyna","Breach","Omen","Cypher","Fade"],
    })
    data = client.get("/history").json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["map"] == "Ascent"
    assert item["team_a_agents"] == ["Jett","Sova","Viper","Killjoy","Skye"]

def test_history_pagination_limit(client, db_session):
    # 15건 삽입
    for i in range(15):
        client.post("/predict", json={
            "map": "Ascent",
            "team_a": ["Jett","Sova","Viper","Killjoy","Skye"],
            "team_b": ["Reyna","Breach","Omen","Cypher","Fade"],
        })
    data = client.get("/history?limit=5").json()
    assert data["total"] == 15
    assert len(data["items"]) == 5

def test_history_pagination_offset(client, db_session):
    for i in range(10):
        client.post("/predict", json={
            "map": "Bind",
            "team_a": ["Jett","Sova","Viper","Killjoy","Skye"],
            "team_b": ["Reyna","Breach","Omen","Cypher","Fade"],
        })
    page1 = client.get("/history?limit=5&offset=0").json()
    page2 = client.get("/history?limit=5&offset=5").json()
    ids_p1 = {i["id"] for i in page1["items"]}
    ids_p2 = {i["id"] for i in page2["items"]}
    assert len(ids_p1 & ids_p2) == 0  # 겹치는 ID 없음

def test_history_map_filter(client, db_session):
    # Ascent 3건, Bind 2건 삽입
    for m, count in [("Ascent", 3), ("Bind", 2)]:
        for _ in range(count):
            client.post("/predict", json={
                "map": m,
                "team_a": ["Jett","Sova","Viper","Killjoy","Skye"],
                "team_b": ["Reyna","Breach","Omen","Cypher","Fade"],
            })
    data = client.get("/history?map=Ascent").json()
    assert data["total"] == 3
    assert all(item["map"] == "Ascent" for item in data["items"])

def test_history_offset_exceeds_total_returns_empty(client, db_session):
    client.post("/predict", json={
        "map": "Ascent",
        "team_a": ["Jett","Sova","Viper","Killjoy","Skye"],
        "team_b": ["Reyna","Breach","Omen","Cypher","Fade"],
    })
    data = client.get("/history?offset=99999").json()
    assert data["total"] == 1
    assert data["items"] == []

def test_history_returns_newest_first(client, db_session):
    for m in ["Ascent", "Bind", "Haven"]:
        client.post("/predict", json={
            "map": m,
            "team_a": ["Jett","Sova","Viper","Killjoy","Skye"],
            "team_b": ["Reyna","Breach","Omen","Cypher","Fade"],
        })
    items = client.get("/history").json()["items"]
    # ID가 내림차순 (최신 → 오래된 순)
    ids = [i["id"] for i in items]
    assert ids == sorted(ids, reverse=True)
```

---

## 9. curl 테스트 명령어

```bash
# 기본 조회
curl "http://localhost:8000/history" | python3 -m json.tool

# limit 지정
curl "http://localhost:8000/history?limit=5"

# 2페이지 (0-indexed, limit=10)
curl "http://localhost:8000/history?limit=10&offset=10"

# Ascent 맵만 필터링
curl "http://localhost:8000/history?map=Ascent"

# Ascent 맵, 최신 3건
curl "http://localhost:8000/history?map=Ascent&limit=3&offset=0"

# total 수만 확인
curl -s "http://localhost:8000/history" | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'총 {d[\"total\"]}건')"
```
