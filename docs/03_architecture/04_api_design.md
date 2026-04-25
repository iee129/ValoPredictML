# 04. REST API 설계

## 1. API 전체 엔드포인트 목록

| Method | 경로 | 설명 | 인증 |
|---|---|---|---|
| `POST` | `/api/v1/predict` | 팀 조합 승률 예측 | 없음 |
| `GET` | `/api/v1/agents` | 요원 목록 및 역할군 조회 | 없음 |
| `GET` | `/api/v1/maps` | 맵 목록 조회 | 없음 |
| `GET` | `/api/v1/history` | 예측 기록 조회 (페이징) | 없음 |
| `GET` | `/health` | 헬스 체크 | 없음 |

---

## 2. `POST /api/v1/predict` — 승률 예측

### 2.1 요청

```json
{
  "map": "Ascent",
  "team_a": ["Jett", "Viper", "Sova", "Killjoy", "Omen"],
  "team_b": ["Reyna", "Brimstone", "Fade", "Cypher", "Skye"]
}
```

**요청 스키마 (`PredictRequest`):**

| 필드 | 타입 | 필수 | 제약 |
|---|---|---|---|
| `map` | `string` | ✅ | 허용 맵 9개 중 하나 |
| `team_a` | `string[]` | ✅ | 정확히 5개, 유효한 요원 이름 |
| `team_b` | `string[]` | ✅ | 정확히 5개, 유효한 요원 이름 |

### 2.2 응답 (200 OK)

```json
{
  "team_a_win_probability": 0.673,
  "team_b_win_probability": 0.327,
  "confidence": 0.346,
  "confidence_level": "High",
  "team_a_roles": {
    "duelist": 1,
    "initiator": 1,
    "controller": 2,
    "sentinel": 1
  },
  "team_b_roles": {
    "duelist": 1,
    "initiator": 2,
    "controller": 1,
    "sentinel": 1
  },
  "feature_importance": [
    { "feature": "controller_diff", "importance": 0.23 },
    { "feature": "team_a_has_controller", "importance": 0.18 },
    { "feature": "map_encoded", "importance": 0.15 },
    { "feature": "duelist_diff", "importance": 0.12 },
    { "feature": "team_b_has_controller", "importance": 0.11 }
  ]
}
```

**응답 스키마 (`PredictResponse`):**

| 필드 | 타입 | 설명 |
|---|---|---|
| `team_a_win_probability` | `float` | 0.0~1.0, 팀 A 승리 확률 |
| `team_b_win_probability` | `float` | `1 - team_a_win_probability` |
| `confidence` | `float` | 0.0~1.0, 예측 신뢰도 |
| `confidence_level` | `string` | `"High"` / `"Medium"` / `"Low"` |
| `team_a_roles` | `object` | 팀 A 역할군 카운트 |
| `team_b_roles` | `object` | 팀 B 역할군 카운트 |
| `feature_importance` | `array` | 상위 5개 피처 중요도 |

### 2.3 에러 응답

```json
// 422 Unprocessable Entity (유효하지 않은 입력)
{
  "detail": [
    {
      "loc": ["body", "map"],
      "msg": "Invalid map. Must be one of ['Ascent', ...]",
      "type": "value_error"
    }
  ]
}

// 400 Bad Request (알 수 없는 요원)
{
  "error": "invalid_agent",
  "message": "Unknown agent: 'UnknownAgent'. Valid agents: [...]"
}

// 503 Service Unavailable (모델 로드 실패)
{
  "error": "model_unavailable",
  "message": "Prediction model is not loaded"
}
```

---

## 3. `GET /api/v1/agents` — 요원 목록

### 3.1 응답 (200 OK)

```json
{
  "agents": [
    { "name": "Jett", "role": "Duelist", "icon_url": "/agents/jett.png" },
    { "name": "Viper", "role": "Controller", "icon_url": "/agents/viper.png" },
    { "name": "Sova", "role": "Initiator", "icon_url": "/agents/sova.png" },
    { "name": "Killjoy", "role": "Sentinel", "icon_url": "/agents/killjoy.png" }
  ],
  "roles": ["Duelist", "Initiator", "Controller", "Sentinel"],
  "total": 28
}
```

---

## 4. `GET /api/v1/maps` — 맵 목록

### 4.1 응답 (200 OK)

```json
{
  "maps": [
    { "name": "Ascent", "image_url": "/maps/ascent.png" },
    { "name": "Bind",   "image_url": "/maps/bind.png" },
    { "name": "Haven",  "image_url": "/maps/haven.png" },
    { "name": "Split",  "image_url": "/maps/split.png" },
    { "name": "Fracture","image_url": "/maps/fracture.png" },
    { "name": "Pearl",  "image_url": "/maps/pearl.png" },
    { "name": "Lotus",  "image_url": "/maps/lotus.png" },
    { "name": "Sunset", "image_url": "/maps/sunset.png" },
    { "name": "Abyss",  "image_url": "/maps/abyss.png" }
  ]
}
```

---

## 5. `GET /api/v1/history` — 예측 기록

### 5.1 쿼리 파라미터

| 파라미터 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| `page` | `int` | `1` | 페이지 번호 |
| `limit` | `int` | `20` | 페이지 당 항목 수 (최대 100) |
| `map` | `string` | — | 특정 맵 필터 |

### 5.2 응답 (200 OK)

```json
{
  "items": [
    {
      "id": 42,
      "created_at": "2025-01-15T09:30:00Z",
      "map": "Ascent",
      "team_a_agents": ["Jett", "Viper", "Sova", "Killjoy", "Omen"],
      "team_b_agents": ["Reyna", "Brimstone", "Fade", "Cypher", "Skye"],
      "win_probability": 0.673,
      "confidence_level": "High"
    }
  ],
  "total": 150,
  "page": 1,
  "limit": 20,
  "has_next": true
}
```

---

## 6. API 설계 원칙

### 6.1 버전 관리
- URL에 `/api/v1/` 접두사 포함
- 하위 호환성 유지 (기존 엔드포인트 제거 전 v2 병행 운영)

### 6.2 CORS 정책

```python
allow_origins=[
    "http://localhost:3000",           # 로컬 개발
    "https://*.vercel.app",            # Vercel 프리뷰
    "https://valo-predict.vercel.app", # 프로덕션
]
```

### 6.3 에러 형식

모든 에러 응답은 동일한 구조 사용:
```json
{
  "error": "error_code",
  "message": "사람이 읽을 수 있는 설명",
  "detail": {}  // 선택: 추가 디버그 정보
}
```

### 6.4 HTTP 상태 코드

| 코드 | 사용 경우 |
|---|---|
| 200 | 성공 |
| 400 | 잘못된 요청 (비즈니스 로직 검증 실패) |
| 422 | 요청 형식 검증 실패 (Pydantic) |
| 500 | 서버 내부 오류 |
| 503 | 모델 미로드 등 서비스 불가 상태 |

---

## 7. Swagger UI 접근

```
로컬:       http://localhost:8000/docs
ReDoc:      http://localhost:8000/redoc
OpenAPI:    http://localhost:8000/openapi.json
```

---

## 8. 관련 문서

| 문서 | 내용 |
|---|---|
| [02_request_flow.md](02_request_flow.md) | 예측 요청 처리 흐름 |
| [../06_model_test/02_api_specification.md](../06_model_test/02_api_specification.md) | 테스트 케이스 포함 상세 스펙 |
| [../06_model_test/06_error_handling.md](../06_model_test/06_error_handling.md) | 에러 코드 전체 목록 |
