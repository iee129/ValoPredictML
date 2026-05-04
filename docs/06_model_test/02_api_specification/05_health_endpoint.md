> ⚠️ **범위 외**: FastAPI 미사용. 본 프로젝트는 Streamlit 로컬 도구이며 API 엔드포인트 테스트는 적용되지 않는다. 본문은 참고용으로 보존된다.

# 05. GET /health 엔드포인트 완전 스펙

## 1. 기본 정보

| 항목 | 내용 |
|------|------|
| 메서드 | GET |
| 경로 | /health |
| 인증 | 없음 |
| 목적 | 서버 상태, 모델 로드 여부, DB 연결 확인 |
| 목표 응답시간 | ≤ 50ms |
| 모니터링 활용 | Uptime Robot, Render Health Check, Vercel Cron |

---

## 2. 요청

```bash
curl http://localhost:8000/health
```

---

## 3. 응답 스키마

### 3.1 정상 상태 (HTTP 200 — 모든 컴포넌트 정상)

```json
{
  "status": "ok",
  "model_loaded": true,
  "model_version": "1.0.0",
  "trained_at": "2024-01-10T12:00:00",
  "db_connected": true,
  "uptime_seconds": 3600,
  "timestamp": "2024-01-15T18:30:00+00:00"
}
```

### 3.2 부분 이상 (HTTP 200 — 서비스는 동작하나 모델 미로드)

```json
{
  "status": "degraded",
  "model_loaded": false,
  "model_version": null,
  "trained_at": null,
  "db_connected": true,
  "uptime_seconds": 15,
  "timestamp": "2024-01-15T18:30:00+00:00"
}
```

### 3.3 심각한 이상 (HTTP 503 — DB 연결 실패)

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

## 4. 응답 필드 정의

| 필드 | 타입 | 설명 |
|------|------|------|
| status | string | 전체 상태: "ok" / "degraded" / "error" |
| model_loaded | boolean | ML 모델 파일 로드 성공 여부 |
| model_version | string \| null | 모델 버전 (미로드 시 null) |
| trained_at | string \| null | 모델 학습 시각 ISO 8601 (미로드 시 null) |
| db_connected | boolean | PostgreSQL 연결 성공 여부 |
| uptime_seconds | integer | 서버 기동 후 경과 시간 (초) |
| timestamp | string | 응답 생성 시각 ISO 8601 (UTC) |

### status 값 결정 로직

```python
def determine_status(model_loaded: bool, db_connected: bool) -> str:
    if model_loaded and db_connected:
        return "ok"
    elif not model_loaded and db_connected:
        return "degraded"   # 예측 불가, 나머지 기능은 정상
    else:
        return "error"      # DB 연결 실패 = 심각
```

---

## 5. 백엔드 구현 코드

```python
# backend/routers/health.py
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
from services.prediction_service import PredictionService
from database import engine
import time

router = APIRouter()
_start_time = time.time()

@router.get("/health")
async def health_check():
    """서버 상태, 모델 로드 여부, DB 연결을 종합 확인합니다."""
    svc = PredictionService()
    model_loaded = svc.is_loaded()
    model_version = svc.get_version() if model_loaded else None
    trained_at = svc.get_trained_at() if model_loaded else None

    # DB 연결 확인
    db_connected = False
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        db_connected = True
    except Exception:
        db_connected = False

    status = determine_status(model_loaded, db_connected)
    uptime_seconds = int(time.time() - _start_time)

    body = {
        "status": status,
        "model_loaded": model_loaded,
        "model_version": model_version,
        "trained_at": trained_at,
        "db_connected": db_connected,
        "uptime_seconds": uptime_seconds,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    http_status = 503 if status == "error" else 200
    return JSONResponse(content=body, status_code=http_status)


def determine_status(model_loaded: bool, db_connected: bool) -> str:
    if model_loaded and db_connected:
        return "ok"
    elif not model_loaded and db_connected:
        return "degraded"
    else:
        return "error"
```

---

## 6. 모니터링 활용법

### 6.1 Render Health Check 설정

Render 대시보드에서:

```
Health Check Path: /health
Health Check Timeout: 10s
```

Render는 `/health`가 2xx를 반환하면 정상, 그 외는 재시작합니다.

### 6.2 Uptime Robot 설정

```
Monitor Type: HTTP(s)
URL: https://your-api.onrender.com/health
Monitoring Interval: 5 minutes
Alert When: Status code != 200
Keyword: "status":"ok"  (키워드 모니터링)
```

### 6.3 GitHub Actions Smoke Test

```yaml
# .github/workflows/smoke-test.yml
- name: Health Check
  run: |
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" ${{ secrets.PROD_API_URL }}/health)
    if [ "$STATUS" != "200" ]; then
      echo "Health check failed: HTTP $STATUS"
      exit 1
    fi
    echo "Health check passed"
```

### 6.4 로컬 모니터링 스크립트

```bash
#!/bin/bash
# scripts/watch_health.sh
URL="${1:-http://localhost:8000}/health"
INTERVAL="${2:-10}"

echo "=== Health Monitor: $URL (${INTERVAL}초 간격) ==="
while true; do
    TIMESTAMP=$(date '+%H:%M:%S')
    RESPONSE=$(curl -s "$URL")
    STATUS=$(echo "$RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null)
    MODEL=$(echo "$RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin).get('model_loaded','?'))" 2>/dev/null)
    DB=$(echo "$RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin).get('db_connected','?'))" 2>/dev/null)
    echo "[$TIMESTAMP] status=$STATUS | model=$MODEL | db=$DB"
    sleep "$INTERVAL"
done
```

---

## 7. 테스트 케이스

```python
# tests/integration/test_health_endpoint.py
import pytest
from unittest.mock import patch, MagicMock

def test_health_returns_200_when_all_ok(client):
    """모델 로드 + DB 연결 정상 시 200 반환."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["model_loaded"] is True
    assert data["db_connected"] is True

def test_health_has_required_fields(client):
    data = client.get("/health").json()
    required = ["status","model_loaded","model_version","trained_at",
                "db_connected","uptime_seconds","timestamp"]
    for field in required:
        assert field in data, f"필드 누락: {field}"

def test_health_status_degraded_when_model_not_loaded(client):
    with patch("backend.routers.health.PredictionService") as mock_svc:
        instance = mock_svc.return_value
        instance.is_loaded.return_value = False
        instance.get_version.return_value = None
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["model_loaded"] is False

def test_health_status_error_when_db_fails(client):
    with patch("backend.routers.health.engine") as mock_engine:
        mock_engine.connect.side_effect = Exception("DB 연결 실패")
        response = client.get("/health")
    assert response.status_code == 503
    assert response.json()["status"] == "error"
    assert response.json()["db_connected"] is False

def test_health_timestamp_is_valid_iso8601(client):
    from datetime import datetime
    data = client.get("/health").json()
    # ISO 8601 파싱 시도
    datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))

def test_health_uptime_is_non_negative(client):
    data = client.get("/health").json()
    assert data["uptime_seconds"] >= 0

@pytest.mark.performance
def test_health_response_time(client):
    import time
    start = time.perf_counter()
    client.get("/health")
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms < 50, f"응답시간 초과: {elapsed_ms:.1f}ms"
```

---

## 8. curl 테스트 명령어

```bash
# 기본 상태 확인
curl http://localhost:8000/health | python3 -m json.tool

# 상태값만 추출
curl -s http://localhost:8000/health | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['status'])"

# HTTP 상태코드 확인
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health

# 프로덕션 확인
curl -s https://your-api.onrender.com/health | python3 -m json.tool

# 지속 모니터링 (10초마다)
watch -n 10 "curl -s http://localhost:8000/health | python3 -m json.tool"
```
