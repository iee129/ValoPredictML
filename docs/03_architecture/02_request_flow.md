# 02. 예측 요청 흐름

## 1. 전체 흐름 다이어그램

```
사용자 브라우저
    │
    │  1. 맵 선택, 양 팀 요원 5명씩 선택 후 "예측" 클릭
    ↓
[Next.js Client]
    │
    │  2. POST /api/v1/predict
    │  Body: { "map": "Ascent", "team_a": [...], "team_b": [...] }
    ↓
[FastAPI Router: /routers/predict.py]
    │
    │  3. Pydantic PredictRequest 검증
    │     - map ∈ 허용된 맵 목록 (9개)
    │     - team_a, team_b 각각 정확히 5명
    │     - 요원 이름 유효성 검사
    ↓
[PredictionService.predict()]
    │
    │  4. FeatureService.transform(map, team_a, team_b) 호출
    ↓
[FeatureService]
    │
    │  5. 역할군 매핑 (agent_roles.py)
    │     - Jett → Duelist, Viper → Controller, ...
    │
    │  6. 역할군 카운트 계산 (8개 피처)
    │     - team_a_duelist_count, team_a_controller_count, ...
    │
    │  7. diff 피처 계산 (4개 피처)
    │     - duelist_diff = a_count - b_count, ...
    │
    │  8. has_controller 피처 (2개)
    │     - team_a_has_controller, team_b_has_controller
    │
    │  9. 맵 Label Encoding (1개)
    │     - "Ascent" → 0, "Bind" → 1, ...
    │
    │  반환: shape (1, 15) NumPy 배열
    ↓
[Predictor.predict_proba(X)]
    │
    │  10. xgb_model.predict_proba(X) → [p_lose, p_win]
    │  11. lgbm_model.predict_proba(X) → [p_lose, p_win]
    │
    │  12. Soft Voting 앙상블
    │      final_prob = 0.6 * xgb_prob[1] + 0.4 * lgbm_prob[1]
    │
    │  13. 신뢰도 계산
    │      confidence = |final_prob - 0.5| * 2
    ↓
[PredictionService - DB 저장]
    │
    │  14. PostgreSQL INSERT INTO predictions
    │      - map, team_a_agents, team_b_agents (JSONB)
    │      - team_a_roles, team_b_roles (JSONB)
    │      - win_probability, confidence
    │      - feature_importance (JSONB)
    ↓
[FastAPI Router 응답]
    │
    │  15. PredictResponse 직렬화
    │      {
    │        "team_a_win_probability": 0.673,
    │        "team_b_win_probability": 0.327,
    │        "confidence": 0.85,
    │        "confidence_level": "High",
    │        "team_a_roles": { "duelist": 2, ... },
    │        "team_b_roles": { "duelist": 1, ... },
    │        "feature_importance": [...]
    │      }
    ↓
[Next.js Client]
    │
    │  16. WinRateGauge 업데이트
    │  17. RoleRadarChart 렌더링
    │  18. FeatureImportanceBar 렌더링
    │  19. ConfidenceBadge 표시
    ↓
사용자 화면
```

---

## 2. 단계별 상세 설명

### 2.1 Step 3: Pydantic 검증

```python
# schemas/predict.py
from pydantic import BaseModel, validator
from typing import List

VALID_MAPS = ["Ascent", "Bind", "Haven", "Split", "Fracture", "Pearl", "Lotus", "Sunset", "Abyss"]

class PredictRequest(BaseModel):
    map: str
    team_a: List[str]
    team_b: List[str]

    @validator("map")
    def validate_map(cls, v):
        if v not in VALID_MAPS:
            raise ValueError(f"Invalid map. Must be one of {VALID_MAPS}")
        return v

    @validator("team_a", "team_b")
    def validate_team_size(cls, v):
        if len(v) != 5:
            raise ValueError("Each team must have exactly 5 agents")
        return v
```

---

### 2.2 Step 5~9: 피처 엔지니어링 (15개 피처)

| 피처 번호 | 피처명 | 설명 |
|---|---|---|
| 1 | `team_a_duelist_count` | 팀 A Duelist 수 (0~5) |
| 2 | `team_a_initiator_count` | 팀 A Initiator 수 |
| 3 | `team_a_controller_count` | 팀 A Controller 수 |
| 4 | `team_a_sentinel_count` | 팀 A Sentinel 수 |
| 5 | `team_b_duelist_count` | 팀 B Duelist 수 |
| 6 | `team_b_initiator_count` | 팀 B Initiator 수 |
| 7 | `team_b_controller_count` | 팀 B Controller 수 |
| 8 | `team_b_sentinel_count` | 팀 B Sentinel 수 |
| 9 | `duelist_diff` | A - B Duelist 차이 (-5 ~ +5) |
| 10 | `initiator_diff` | A - B Initiator 차이 |
| 11 | `controller_diff` | A - B Controller 차이 |
| 12 | `sentinel_diff` | A - B Sentinel 차이 |
| 13 | `team_a_has_controller` | A에 Controller ≥ 1 (0 or 1) |
| 14 | `team_b_has_controller` | B에 Controller ≥ 1 (0 or 1) |
| 15 | `map_encoded` | 맵 Label Encoding (0~8) |

---

### 2.3 Step 12~13: Soft Voting 앙상블

```python
def predict_proba(X: np.ndarray) -> tuple[float, float]:
    xgb_proba = xgb_model.predict_proba(X)[0][1]   # 팀 A 승리 확률
    lgbm_proba = lgbm_model.predict_proba(X)[0][1]  # 팀 A 승리 확률

    # 가중 평균 (60% XGBoost, 40% LightGBM)
    final_prob = 0.6 * xgb_proba + 0.4 * lgbm_proba

    # 신뢰도: 50% 중립 기준 거리를 0~1로 정규화
    confidence = abs(final_prob - 0.5) * 2

    return final_prob, confidence
```

**신뢰도 등급:**
| `confidence_level` | 기준 |
|---|---|
| `High` | confidence ≥ 0.6 |
| `Medium` | 0.3 ≤ confidence < 0.6 |
| `Low` | confidence < 0.3 |

---

### 2.4 Step 14: PostgreSQL 저장

```sql
INSERT INTO predictions (
    map, team_a_agents, team_b_agents,
    team_a_roles, team_b_roles,
    win_probability, confidence, feature_importance
) VALUES (
    'Ascent',
    '["Jett","Viper","Sova","Killjoy","Omen"]',
    '["Reyna","Brimstone","Fade","Cypher","Skye"]',
    '{"duelist":1,"controller":2,"initiator":1,"sentinel":1}',
    '{"duelist":1,"controller":1,"initiator":2,"sentinel":1}',
    0.673, 0.85,
    '[{"feature":"controller_diff","importance":0.23},...]'
);
```

---

## 3. 에러 처리 흐름

```
요청 → Pydantic 검증 실패 → 422 Unprocessable Entity
                              { "detail": [{ "loc": [...], "msg": "..." }] }

요청 → 모델 로드 실패      → 503 Service Unavailable
                              { "error": "model_unavailable", "message": "..." }

요청 → 요원 이름 미존재    → 400 Bad Request
                              { "error": "invalid_agent", "message": "..." }

요청 → DB 저장 실패        → 500 Internal Server Error
                              (예측 결과는 반환, 기록만 실패)
```

---

## 4. 관련 문서

| 문서 | 내용 |
|---|---|
| [04_api_design.md](04_api_design.md) | API 엔드포인트 전체 스펙 |
| [06_error_handling.md](../06_model_test/06_error_handling.md) | 에러 코드 전체 목록 |
| [../05_data_learning/05_ensemble_strategy.md](../05_data_learning/05_ensemble_strategy.md) | Soft Voting 상세 구현 |
