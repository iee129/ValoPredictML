> ⚠️ **범위 외**: FastAPI 미사용. 본 프로젝트는 Streamlit 로컬 도구이며 API 엔드포인트 테스트는 적용되지 않는다. 본문은 참고용으로 보존된다.

# 01. POST /predict 엔드포인트 완전 스펙

## 1. 기본 정보

| 항목 | 내용 |
|------|------|
| 메서드 | POST |
| 경로 | /predict |
| Content-Type | application/json |
| 인증 | 없음 (공개 API) |
| 목표 응답시간 | ≤ 200ms |
| 응답 캐싱 | 없음 (매 요청 새로 예측) |

---

## 2. 요청 스키마 (Request)

### 2.1 JSON 구조

```json
{
  "map": "Ascent",
  "team_a": ["Jett", "Sova", "Viper", "Killjoy", "Skye"],
  "team_b": ["Reyna", "Breach", "Omen", "Cypher", "Fade"]
}
```

### 2.2 필드 정의

| 필드 | 타입 | 필수 | 설명 | 유효성 규칙 |
|------|------|------|------|------------|
| map | string | 필수 | 경기 맵 이름 | VALID_MAPS 목록 내 값 |
| team_a | array[string] | 필수 | 팀 A 요원 목록 | 정확히 5명, 중복 불가 |
| team_b | array[string] | 필수 | 팀 B 요원 목록 | 정확히 5명, team_a와 중복 불가 |

### 2.3 유효한 맵 목록 (VALID_MAPS)

```python
VALID_MAPS = {
    "Bind", "Haven", "Split", "Ascent", "Icebox",
    "Breeze", "Fracture", "Pearl", "Lotus", "Sunset", "Abyss"
}
```

### 2.4 Pydantic 스키마 전체 코드

```python
# backend/schemas/predict.py
from pydantic import BaseModel, field_validator
from typing import List

VALID_MAPS = {
    "Bind", "Haven", "Split", "Ascent", "Icebox",
    "Breeze", "Fracture", "Pearl", "Lotus", "Sunset", "Abyss"
}

class PredictRequest(BaseModel):
    map: str
    team_a: List[str]
    team_b: List[str]

    @field_validator("map")
    @classmethod
    def validate_map(cls, v: str) -> str:
        if v not in VALID_MAPS:
            raise ValueError(
                f"알 수 없는 맵: '{v}'. 유효한 맵: {sorted(VALID_MAPS)}"
            )
        return v

    @field_validator("team_a", "team_b")
    @classmethod
    def validate_team_size(cls, v: List[str]) -> List[str]:
        if len(v) != 5:
            raise ValueError(
                f"팀 구성은 정확히 5명이어야 합니다. (입력: {len(v)}명)"
            )
        return v

    @field_validator("team_b")
    @classmethod
    def validate_no_duplicate_agents(cls, v: List[str], info) -> List[str]:
        team_a = info.data.get("team_a", [])
        all_agents = team_a + v
        if len(set(all_agents)) != len(all_agents):
            duplicates = list({a for a in all_agents if all_agents.count(a) > 1})
            raise ValueError(f"중복 요원이 있습니다: {duplicates}")
        return v

    model_config = {"json_schema_extra": {
        "example": {
            "map": "Ascent",
            "team_a": ["Jett", "Sova", "Viper", "Killjoy", "Skye"],
            "team_b": ["Reyna", "Breach", "Omen", "Cypher", "Fade"]
        }
    }}
```

---

## 3. 응답 스키마 (Response)

### 3.1 성공 응답 (HTTP 200)

```json
{
  "win_probability": 0.673,
  "lose_probability": 0.327,
  "confidence": "medium",
  "team_a_role_counts": {
    "duelist": 1,
    "initiator": 2,
    "controller": 1,
    "sentinel": 1,
    "unknown": 0
  },
  "team_b_role_counts": {
    "duelist": 1,
    "initiator": 2,
    "controller": 1,
    "sentinel": 1,
    "unknown": 0
  },
  "feature_importance": {
    "team_a_controller": 0.142,
    "team_b_duelist": 0.138,
    "map_encoded": 0.121,
    "controller_diff": 0.115,
    "team_a_initiator": 0.098
  },
  "map": "Ascent",
  "model_version": "1.0.0"
}
```

### 3.2 응답 필드 정의

| 필드 | 타입 | 설명 | 범위 |
|------|------|------|------|
| win_probability | float | 팀 A 승리 확률 | 0.0 ~ 1.0 |
| lose_probability | float | 팀 A 패배 확률 (= 1 - win_probability) | 0.0 ~ 1.0 |
| confidence | string | 예측 신뢰도 등급 | "high" / "medium" / "low" |
| team_a_role_counts | object | 팀 A 역할군 인원수 | 각 필드 0~5 |
| team_b_role_counts | object | 팀 B 역할군 인원수 | 각 필드 0~5 |
| feature_importance | object | 상위 5개 피처 중요도 (XGBoost 기준) | 값 합계 ≤ 1.0 |
| map | string | 예측에 사용된 맵 이름 | VALID_MAPS 내 값 |
| model_version | string | 사용된 모델 버전 | semver |

### 3.3 confidence 계산 기준

```python
def calculate_confidence(prob: float) -> str:
    """예측 확률의 극단성 기반 신뢰도 분류."""
    distance = abs(prob - 0.5)
    if distance >= 0.2:    # 70% 이상 or 30% 이하
        return "high"
    elif distance >= 0.1:  # 60~70% 또는 30~40%
        return "medium"
    else:                  # 40~60% (불확실)
        return "low"

# 예시
# prob=0.73 → distance=0.23 → "high"
# prob=0.62 → distance=0.12 → "medium"
# prob=0.53 → distance=0.03 → "low"
```

### 3.4 RoleCounts 구조

```python
class RoleCounts(BaseModel):
    duelist: int      # 타격대 (Jett, Reyna, Neon, Yoru, Phoenix, Iso, Deadlock 중 Duelist)
    initiator: int    # 척후대 (Sova, Breach, Skye, Fade, Gekko, KAY/O)
    controller: int   # 전략가 (Viper, Omen, Brimstone, Astra, Harbor, Clove)
    sentinel: int     # 감시자 (Killjoy, Cypher, Sage, Chamber, Deadlock)
    unknown: int = 0  # 매핑에 없는 신규/미지원 요원
```

---

## 4. 에러 응답

### 4.1 422 Unprocessable Entity — 입력 검증 실패

**잘못된 맵 이름**

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "map": "Icebox2",
    "team_a": ["Jett","Sova","Viper","Killjoy","Skye"],
    "team_b": ["Reyna","Breach","Omen","Cypher","Fade"]
  }'
```

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "map"],
      "msg": "Value error, 알 수 없는 맵: 'Icebox2'. 유효한 맵: ['Abyss', 'Ascent', ...]",
      "input": "Icebox2"
    }
  ]
}
```

**팀 인원 불일치**

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "map": "Ascent",
    "team_a": ["Jett","Sova","Viper","Killjoy"],
    "team_b": ["Reyna","Breach","Omen","Cypher","Fade"]
  }'
```

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "team_a"],
      "msg": "Value error, 팀 구성은 정확히 5명이어야 합니다. (입력: 4명)",
      "input": ["Jett","Sova","Viper","Killjoy"]
    }
  ]
}
```

**중복 요원**

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "map": "Ascent",
    "team_a": ["Jett","Sova","Viper","Killjoy","Skye"],
    "team_b": ["Jett","Breach","Omen","Cypher","Fade"]
  }'
```

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "team_b"],
      "msg": "Value error, 중복 요원이 있습니다: ['Jett']",
      "input": ["Jett","Breach","Omen","Cypher","Fade"]
    }
  ]
}
```

### 4.2 500 Internal Server Error — 서버 오류

```json
{
  "detail": "예측 오류: 모델 파일을 찾을 수 없습니다."
}
```

### 4.3 503 Service Unavailable — 서버 초기화 중

```json
{
  "detail": "서비스 초기화 중입니다. 잠시 후 다시 시도하세요."
}
```

---

## 5. curl 테스트 명령어 모음

### 5.1 정상 요청

```bash
# 기본 정상 요청
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "map": "Ascent",
    "team_a": ["Jett", "Sova", "Viper", "Killjoy", "Skye"],
    "team_b": ["Reyna", "Breach", "Omen", "Cypher", "Fade"]
  }' | python3 -m json.tool

# 응답시간 포함 측정
curl -s -o /dev/null -w "HTTP %{http_code} | %{time_total}s\n" \
  -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"map":"Bind","team_a":["Neon","Breach","Viper","Sage","Cypher"],"team_b":["Jett","Sova","Omen","Killjoy","Skye"]}'

# 다양한 맵 테스트
for MAP in Ascent Bind Haven Split Icebox Breeze Fracture Pearl Lotus Sunset Abyss; do
  echo -n "[$MAP] "
  curl -s -o /dev/null -w "HTTP %{http_code} | %{time_total}s\n" \
    -X POST http://localhost:8000/predict \
    -H "Content-Type: application/json" \
    -d "{\"map\":\"$MAP\",\"team_a\":[\"Jett\",\"Sova\",\"Viper\",\"Killjoy\",\"Skye\"],\"team_b\":[\"Reyna\",\"Breach\",\"Omen\",\"Cypher\",\"Fade\"]}"
done
```

### 5.2 에러 케이스 curl

```bash
# 잘못된 맵 → 422
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"map":"INVALID","team_a":["Jett","Sova","Viper","Killjoy","Skye"],"team_b":["Reyna","Breach","Omen","Cypher","Fade"]}'

# 인원 부족 → 422
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"map":"Ascent","team_a":["Jett","Sova"],"team_b":["Reyna","Breach","Omen","Cypher","Fade"]}'

# 중복 요원 → 422
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"map":"Ascent","team_a":["Jett","Jett","Viper","Killjoy","Skye"],"team_b":["Reyna","Breach","Omen","Cypher","Fade"]}'

# 빈 배열 → 422
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"map":"Ascent","team_a":[],"team_b":[]}'

# 필드 누락 → 422
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"map":"Ascent"}'
```

---

## 6. Swagger UI 활용

FastAPI 자동 생성 문서에서 직접 테스트 가능합니다.

```
http://localhost:8000/docs       → Swagger UI (Try it out 버튼)
http://localhost:8000/redoc      → ReDoc (읽기 전용)
http://localhost:8000/openapi.json → OpenAPI 스펙 JSON
```

---

## 7. 예측 결과 해석 가이드

| win_probability | confidence | 해석 |
|-----------------|-----------|------|
| 0.70 ~ 1.00 | high | 팀 A가 강하게 유리한 조합 |
| 0.60 ~ 0.70 | medium | 팀 A가 다소 유리 |
| 0.40 ~ 0.60 | low | 비슷한 수준, 불확실 |
| 0.30 ~ 0.40 | medium | 팀 B가 다소 유리 |
| 0.00 ~ 0.30 | high | 팀 B가 강하게 유리한 조합 |

---

## 8. DB 저장 동작

POST /predict 호출 시 예측 결과는 PostgreSQL `predictions` 테이블에 자동 저장됩니다.

```sql
-- predictions 테이블 구조
CREATE TABLE predictions (
    id          SERIAL PRIMARY KEY,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    map         VARCHAR(50) NOT NULL,
    team_a_agents TEXT[] NOT NULL,   -- ["Jett","Sova","Viper","Killjoy","Skye"]
    team_b_agents TEXT[] NOT NULL,
    win_probability FLOAT NOT NULL,
    confidence  VARCHAR(10) NOT NULL
);
```
