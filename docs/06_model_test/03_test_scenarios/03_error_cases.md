> ⚠️ **범위 외**: FastAPI 미사용. 본 프로젝트는 Streamlit 로컬 도구이며 API 엔드포인트 테스트는 적용되지 않는다. 본문은 참고용으로 보존된다.

# 03. 에러 케이스 테스트 시나리오

## 개요

HTTP 422 / 500 / 503 / 404 각 상황별 에러 케이스와 curl 명령어, 기대 응답을 정의합니다.

---

## 1. HTTP 422 — Unprocessable Entity (입력 검증 실패)

Pydantic이 요청 본문을 검증하여 실패할 때 반환됩니다.

### TC-ERR-422-001: 유효하지 않은 맵

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"map":"InvalidMap","team_a":["Jett","Sova","Viper","Killjoy","Skye"],"team_b":["Reyna","Breach","Omen","Cypher","Fade"]}'
```

**기대 응답**
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "map"],
      "msg": "Value error, 알 수 없는 맵: 'InvalidMap'. 유효한 맵: ['Abyss', 'Ascent', 'Bind', 'Breeze', 'Fracture', 'Haven', 'Icebox', 'Lotus', 'Pearl', 'Split', 'Sunset']",
      "input": "InvalidMap",
      "url": "https://errors.pydantic.dev/2.x/v/value_error"
    }
  ]
}
```

---

### TC-ERR-422-002: 팀 인원 부족

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"map":"Ascent","team_a":["Jett","Sova"],"team_b":["Reyna","Breach","Omen","Cypher","Fade"]}'
```

**기대 응답**
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "team_a"],
      "msg": "Value error, 팀 구성은 정확히 5명이어야 합니다. (입력: 2명)",
      "input": ["Jett", "Sova"]
    }
  ]
}
```

---

### TC-ERR-422-003: 중복 요원 (팀 간)

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"map":"Ascent","team_a":["Jett","Sova","Viper","Killjoy","Skye"],"team_b":["Jett","Breach","Omen","Cypher","Fade"]}'
```

**기대 응답**
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "team_b"],
      "msg": "Value error, 중복 요원이 있습니다: ['Jett']",
      "input": ["Jett", "Breach", "Omen", "Cypher", "Fade"]
    }
  ]
}
```

---

### TC-ERR-422-004: 필수 필드 누락

```bash
# map 필드 누락
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"team_a":["Jett","Sova","Viper","Killjoy","Skye"],"team_b":["Reyna","Breach","Omen","Cypher","Fade"]}'
```

**기대 응답**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "map"],
      "msg": "Field required",
      "input": {
        "team_a": ["Jett", "Sova", "Viper", "Killjoy", "Skye"],
        "team_b": ["Reyna", "Breach", "Omen", "Cypher", "Fade"]
      }
    }
  ]
}
```

---

### TC-ERR-422-005: 타입 오류 (map에 숫자)

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"map":123,"team_a":["Jett","Sova","Viper","Killjoy","Skye"],"team_b":["Reyna","Breach","Omen","Cypher","Fade"]}'
```

**기대 응답**
```json
{
  "detail": [
    {
      "type": "string_type",
      "loc": ["body", "map"],
      "msg": "Input should be a valid string",
      "input": 123
    }
  ]
}
```

---

### TC-ERR-422-006: 빈 요청 본문

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{}'
```

**기대 응답** (모든 필수 필드 누락)
```json
{
  "detail": [
    {"type": "missing", "loc": ["body", "map"], "msg": "Field required", "input": {}},
    {"type": "missing", "loc": ["body", "team_a"], "msg": "Field required", "input": {}},
    {"type": "missing", "loc": ["body", "team_b"], "msg": "Field required", "input": {}}
  ]
}
```

---

### TC-ERR-422-007: /history limit 범위 초과

```bash
# limit=0 (최솟값 1 미만)
curl "http://localhost:8000/history?limit=0"

# limit=101 (최댓값 100 초과)
curl "http://localhost:8000/history?limit=101"

# offset=-1 (음수)
curl "http://localhost:8000/history?offset=-1"
```

**기대 응답 (limit=0)**
```json
{
  "detail": [
    {
      "type": "greater_than_equal",
      "loc": ["query", "limit"],
      "msg": "Input should be greater than or equal to 1",
      "input": "0"
    }
  ]
}
```

---

## 2. HTTP 500 — Internal Server Error (서버 내부 오류)

### TC-ERR-500-001: 모델 파일 없음

모델 파일이 삭제되거나 경로가 잘못된 상태에서 예측 요청 시 발생합니다.

```bash
# 테스트 방법: MODEL_PATH를 존재하지 않는 경로로 설정 후 서버 재시작
MODEL_PATH=/nonexistent/path uvicorn main:app --port 8000

curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"map":"Ascent","team_a":["Jett","Sova","Viper","Killjoy","Skye"],"team_b":["Reyna","Breach","Omen","Cypher","Fade"]}'
```

**기대 응답**
```json
{
  "detail": "예측 오류: [Errno 2] No such file or directory: '/nonexistent/path/xgboost_model.joblib'"
}
```

**pytest 재현**
```python
def test_predict_500_when_model_missing(client):
    with patch("backend.services.prediction_service.PredictionService.predict") as mock:
        mock.side_effect = FileNotFoundError("모델 파일을 찾을 수 없습니다.")
        response = client.post("/predict", json={
            "map": "Ascent",
            "team_a": ["Jett","Sova","Viper","Killjoy","Skye"],
            "team_b": ["Reyna","Breach","Omen","Cypher","Fade"],
        })
    assert response.status_code == 500
    assert "모델 파일" in response.json()["detail"]
```

---

### TC-ERR-500-002: 예측 중 런타임 오류

```python
def test_predict_500_on_runtime_error(client):
    with patch("backend.services.prediction_service.PredictionService.predict") as mock:
        mock.side_effect = RuntimeError("피처 변환 실패")
        response = client.post("/predict", json={
            "map": "Ascent",
            "team_a": ["Jett","Sova","Viper","Killjoy","Skye"],
            "team_b": ["Reyna","Breach","Omen","Cypher","Fade"],
        })
    assert response.status_code == 500
```

---

### TC-ERR-500-003: DB 연결 실패 시 /history

```python
def test_history_500_when_db_unavailable(client):
    with patch("backend.routers.history.get_db") as mock_db:
        mock_db.side_effect = Exception("DB 연결 끊김")
        response = client.get("/history")
    assert response.status_code in [500, 503]
```

---

## 3. HTTP 503 — Service Unavailable (서비스 이용 불가)

### TC-ERR-503-001: 서버 초기화 중 요청

서버가 모델을 아직 로드하는 중에 예측 요청이 들어오는 시나리오입니다.

```python
# backend/routers/predict.py 에 초기화 체크 추가 시
@router.post("/predict", response_model=PredictResponse)
async def predict_win_rate(request: PredictRequest):
    if not service.is_loaded():
        raise HTTPException(
            status_code=503,
            detail="서비스 초기화 중입니다. 잠시 후 다시 시도하세요."
        )
    ...
```

**기대 응답**
```json
{
  "detail": "서비스 초기화 중입니다. 잠시 후 다시 시도하세요."
}
```

**pytest 재현**
```python
def test_predict_503_when_model_not_initialized(client):
    with patch("backend.routers.predict.service.is_loaded", return_value=False):
        response = client.post("/predict", json={
            "map": "Ascent",
            "team_a": ["Jett","Sova","Viper","Killjoy","Skye"],
            "team_b": ["Reyna","Breach","Omen","Cypher","Fade"],
        })
    assert response.status_code == 503
    assert "초기화" in response.json()["detail"]
```

---

### TC-ERR-503-002: /health — DB 연결 실패

```bash
# DB 중단 상태에서 /health 호출
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health
# 기대: 503
```

**기대 응답**
```json
{
  "status": "error",
  "model_loaded": true,
  "model_version": "1.0.0",
  "trained_at": "2024-01-10T12:00:00",
  "db_connected": false,
  "uptime_seconds": 120,
  "timestamp": "2024-01-15T18:30:00+00:00"
}
```

---

## 4. HTTP 404 — Not Found

### TC-ERR-404-001: 존재하지 않는 엔드포인트

```bash
curl -v http://localhost:8000/predict2
curl -v http://localhost:8000/api/predict
curl -v http://localhost:8000/
```

**기대 응답**
```json
{"detail": "Not Found"}
```

---

### TC-ERR-404-002: 잘못된 메서드

```bash
# GET으로 /predict 호출
curl http://localhost:8000/predict

# DELETE로 /predict 호출
curl -X DELETE http://localhost:8000/predict
```

**기대 응답 (405)**
```json
{"detail": "Method Not Allowed"}
```

---

## 5. 에러 응답 표준 구조 검증

모든 에러 응답이 일관된 형식인지 확인합니다.

```python
# tests/test_error_format.py
import pytest

ERROR_CASES = [
    # (method, url, payload, expected_status)
    ("POST", "/predict", {"map":"BAD","team_a":["Jett","Sova","Viper","Killjoy","Skye"],"team_b":["Reyna","Breach","Omen","Cypher","Fade"]}, 422),
    ("POST", "/predict", {"map":"Ascent","team_a":["Jett"],"team_b":["Reyna","Breach","Omen","Cypher","Fade"]}, 422),
    ("GET", "/nonexistent", None, 404),
]

@pytest.mark.parametrize("method,url,payload,expected_status", ERROR_CASES)
def test_error_response_has_detail_field(client, method, url, payload, expected_status):
    if method == "POST":
        response = client.post(url, json=payload)
    else:
        response = client.get(url)
    assert response.status_code == expected_status
    data = response.json()
    assert "detail" in data, f"'detail' 필드 없음: {data}"
```

---

## 6. 에러 코드 빠른 참조표

| HTTP 상태 | 상황 | 에러 필드 | 클라이언트 대응 |
|-----------|------|----------|--------------|
| 422 | 유효하지 않은 맵 | detail[].loc=["body","map"] | 맵 드롭다운에서 재선택 안내 |
| 422 | 팀 인원 오류 | detail[].loc=["body","team_a/b"] | 정확히 5명 선택 안내 |
| 422 | 중복 요원 | detail[].loc=["body","team_b"] | 중복 요원 해제 안내 |
| 422 | 필드 누락 | detail[].type="missing" | 필수 항목 입력 안내 |
| 500 | 모델 로드 실패 | detail=string | "잠시 후 다시 시도" 표시 |
| 500 | 예측 내부 오류 | detail=string | 오류 신고 링크 표시 |
| 503 | 서버 초기화 중 | detail=string | 자동 재시도 (3초 후) |
| 503 | DB 연결 실패 | detail=string | "서비스 점검 중" 표시 |
| 404 | 없는 엔드포인트 | detail="Not Found" | 클라이언트 버그 의심 |
| 405 | 잘못된 메서드 | detail="Method Not Allowed" | 클라이언트 버그 의심 |
