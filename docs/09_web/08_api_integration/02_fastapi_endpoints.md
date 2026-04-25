# 02. FastAPI 엔드포인트 명세

---

## 서버 정보

| 항목 | 값 |
|---|---|
| 프레임워크 | FastAPI |
| 기본 포트 | 8000 |
| 문서 | `http://localhost:8000/docs` (Swagger UI) |
| 인증 | 없음 (공개 API) |

---

## 엔드포인트 목록

| 메서드 | 경로 | 설명 |
|---|---|---|
| POST | `/predict` | 팀 조합 기반 승률 예측 |
| GET  | `/agents` | 사용 가능한 요원 목록 |
| GET  | `/maps` | 사용 가능한 맵 목록 |
| GET  | `/history` | 예측 기록 조회 (페이지네이션) |
| GET  | `/analytics` | 통계 집계 데이터 |

---

## POST /predict

### Request Body

```json
{
  "team_a": ["Jett", "Sage", "Omen", "Fade", "Killjoy"],
  "team_b": ["Phoenix", "Skye", "Viper", "Breach", "Cypher"],
  "map": "Ascent"
}
```

| 필드 | 타입 | 설명 |
|---|---|---|
| `team_a` | string[5] | 팀 A 요원 이름 (반드시 5개) |
| `team_b` | string[5] | 팀 B 요원 이름 (반드시 5개) |
| `map` | string | 맵 이름 |

### Response

```json
{
  "win_rate_a": 0.62,
  "win_rate_b": 0.38,
  "confidence": 0.78,
  "features": [
    { "name": "팀 조합 다양성", "importance": 0.34 },
    { "name": "공격/수비 밸런스", "importance": 0.28 },
    { "name": "맵 메타 적합도", "importance": 0.22 },
    { "name": "역할군 커버리지", "importance": 0.16 }
  ]
}
```

---

## GET /agents

### Response

```json
[
  { "name": "Jett",     "role": "Duelist" },
  { "name": "Phoenix",  "role": "Duelist" },
  { "name": "Sage",     "role": "Sentinel" },
  { "name": "Sova",     "role": "Initiator" },
  { "name": "Viper",    "role": "Controller" },
  ...
]
```

---

## GET /maps

### Response

```json
["Ascent", "Bind", "Breeze", "Fracture", "Haven", "Icebox", "Lotus", "Pearl", "Split", "Sunset"]
```

---

## GET /history

### Query Parameters

| 파라미터 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| `page` | int | 1 | 페이지 번호 |
| `page_size` | int | 20 | 페이지당 항목 수 |
| `map` | string | - | 맵 필터 |
| `start_date` | string | - | 시작 날짜 (ISO 8601) |
| `end_date` | string | - | 종료 날짜 (ISO 8601) |

### Response

```json
{
  "items": [
    {
      "id": 1,
      "map": "Ascent",
      "team_a": ["Jett", "Sage", "Omen", "Fade", "Killjoy"],
      "team_b": ["Phoenix", "Skye", "Viper", "Breach", "Cypher"],
      "win_rate_a": 0.62,
      "win_rate_b": 0.38,
      "confidence": 0.78,
      "created_at": "2024-01-15T12:30:00"
    }
  ],
  "total": 150
}
```

---

## GET /analytics

### Response

```json
{
  "total_predictions": 1245,
  "avg_confidence": 0.72,
  "map_stats": [
    {
      "map": "Ascent",
      "attack_win_rate": 0.54,
      "defense_win_rate": 0.46,
      "total_games": 312
    }
  ],
  "top_agents": [
    { "name": "Jett",    "role": "Duelist",    "count": 892 },
    { "name": "Sage",    "role": "Sentinel",   "count": 756 },
    { "name": "Killjoy", "role": "Sentinel",   "count": 643 },
    { "name": "Omen",    "role": "Controller", "count": 601 },
    { "name": "Fade",    "role": "Initiator",  "count": 589 }
  ]
}
```

---

## CORS 설정

프론트엔드(Vercel)와 백엔드(별도 서버) 도메인이 다르므로 CORS 필요:

```python
# FastAPI main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://your-app.vercel.app",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)
```
