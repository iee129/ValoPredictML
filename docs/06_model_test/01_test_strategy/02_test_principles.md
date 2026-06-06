> ⚠️ 참고/확장 설계: 현재 시연은 웹 스택(FastAPI `src/api` + Next.js `web`) 기준이다. 이 문서의 테스트 설계는 참고용으로 보존한다.

> ⚠️ **참고용**: 본 프로젝트는 웹 스택(FastAPI `src/api` + Next.js `web`)으로 서빙한다. 본문의 상세 테스트 설계는 참고용으로 보존된다.

# 02. 테스트 설계 원칙

## 1. 핵심 원칙 개요

ValoPredictML의 테스트는 아래 세 가지 핵심 원칙을 기반으로 설계합니다.

| 원칙 | 설명 | 위반 시 문제 |
|------|------|-------------|
| 독립성 (Independence) | 각 테스트는 다른 테스트에 의존하지 않음 | 실행 순서에 따라 결과가 달라짐 |
| 재현성 (Reproducibility) | 동일 입력에 항상 동일 결과 | 간헐적 실패로 신뢰도 저하 |
| 완전성 (Completeness) | 정상/엣지/에러 케이스 모두 포함 | 숨겨진 버그 미탐지 |

---

## 2. 독립성 (Independence)

### 2.1 원칙 정의

각 테스트 케이스는 다른 테스트의 실행 여부나 순서에 무관하게 동일하게 동작해야 합니다.

### 2.2 실천 방법

**DB 상태 격리 — pytest fixture로 트랜잭션 롤백**

```python
# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base, get_db
from backend.main import app
from fastapi.testclient import TestClient

TEST_DATABASE_URL = "postgresql://valopred:valopred_secret@localhost:5432/valopredml_test"

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """각 테스트마다 트랜잭션을 시작하고 종료 시 롤백."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db_session):
    """DB 세션이 격리된 TestClient."""
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

**모델 의존성 격리 — Mock 사용**

```python
# tests/test_predict.py
from unittest.mock import patch, MagicMock

def test_predict_uses_model_result(client):
    """PredictionService를 Mock으로 교체하여 모델 의존성 제거."""
    mock_result = {
        "win_probability": 0.65,
        "lose_probability": 0.35,
        "confidence": "medium",
        "team_a_role_counts": {"duelist":1,"initiator":2,"controller":1,"sentinel":1,"unknown":0},
        "team_b_role_counts": {"duelist":1,"initiator":2,"controller":1,"sentinel":1,"unknown":0},
        "feature_importance": {"map_encoded": 0.2},
        "map": "Ascent",
        "model_version": "1.0.0",
    }

    with patch("backend.routers.predict.service.predict", return_value=mock_result):
        response = client.post("/predict", json={
            "map": "Ascent",
            "team_a": ["Jett","Sova","Viper","Killjoy","Skye"],
            "team_b": ["Reyna","Breach","Omen","Cypher","Fade"],
        })

    assert response.status_code == 200
    assert response.json()["win_probability"] == 0.65
```

### 2.3 안티패턴 — 피해야 할 사례

```python
# 나쁜 예: 전역 상태에 의존
predictions_count = 0

def test_first():
    global predictions_count
    predictions_count += 1

def test_second():
    # test_first가 먼저 실행돼야 통과
    assert predictions_count == 1  # 실행 순서 의존!

# 좋은 예: 각 테스트가 자체 상태 관리
def test_second_correct(db_session):
    # db_session fixture가 매번 초기화됨
    count = db_session.query(Prediction).count()
    assert count == 0  # 항상 깨끗한 상태에서 시작
```

---

## 3. 재현성 (Reproducibility)

### 3.1 원칙 정의

동일한 입력에 대해 언제 어디서 실행해도 동일한 결과를 보장합니다.

### 3.2 비결정적 요소 제어

**시간 고정**

```python
# tests/test_history.py
from unittest.mock import patch
from datetime import datetime, timezone

FIXED_TIME = datetime(2024, 1, 15, 18, 30, 0, tzinfo=timezone.utc)

def test_prediction_timestamp(client):
    with patch("backend.services.prediction_service.datetime") as mock_dt:
        mock_dt.now.return_value = FIXED_TIME
        mock_dt.utcnow.return_value = FIXED_TIME

        response = client.post("/predict", json={...})

    # created_at이 고정된 시간인지 확인
    history = client.get("/history?limit=1").json()
    assert history["items"][0]["created_at"] == "2024-01-15T18:30:00+00:00"
```

**난수 시드 고정**

```python
import numpy as np

@pytest.fixture(autouse=True)
def fix_random_seed():
    """모든 테스트에서 난수 시드를 고정."""
    np.random.seed(42)
    yield
```

**외부 API 차단**

```python
# conftest.py - Riot API 등 외부 호출 차단
@pytest.fixture(autouse=True)
def no_external_calls(monkeypatch):
    """테스트 중 실제 외부 HTTP 호출 방지."""
    import httpx
    def mock_get(*args, **kwargs):
        raise RuntimeError("외부 HTTP 호출은 테스트에서 금지됩니다. Mock을 사용하세요.")
    monkeypatch.setattr(httpx, "get", mock_get)
```

### 3.3 환경 변수 통제

```python
# conftest.py
import os

@pytest.fixture(autouse=True)
def set_test_env():
    """테스트 전용 환경 변수를 강제 설정."""
    original = dict(os.environ)
    os.environ.update({
        "DATABASE_URL": "postgresql://valopred:secret@localhost:5432/valopredml_test",
        "MODEL_PATH": "./tests/fixtures/models",
        "LOG_LEVEL": "ERROR",  # 테스트 중 로그 최소화
    })
    yield
    os.environ.clear()
    os.environ.update(original)
```

---

## 4. 완전성 (Completeness)

### 4.1 테스트 피라미드

```
         /\
        /  \   E2E 테스트 (소수)
       /    \  브라우저 시뮬레이션
      /------\
     /        \ 통합 테스트 (중간)
    /          \ API 엔드포인트 전체 흐름
   /------------\
  /              \ 단위 테스트 (다수)
 /                \ 함수, 클래스, 스키마
/------------------\
```

**단위 테스트** — 전체의 70%
- Pydantic 스키마 검증 로직
- FeatureEngineer.transform() 함수
- calculate_confidence() 함수
- get_role_counts() 함수

**통합 테스트** — 전체의 25%
- POST /predict 전체 흐름 (입력 → 서비스 → DB → 응답)
- GET /history 페이지네이션 + 필터링
- DB 연결 및 ORM 동작

**E2E 테스트** — 전체의 5%
- 브라우저에서 요원 선택 → 예측 → 결과 표시
- Playwright 또는 Cypress 사용

### 4.2 각 엔드포인트별 최소 테스트 요건

| 엔드포인트 | 정상 케이스 | 엣지 케이스 | 에러 케이스 |
|-----------|------------|------------|------------|
| POST /predict | 3개 이상 | 5개 이상 | 3개 이상 |
| GET /agents | 1개 | 0개 | 1개 |
| GET /maps | 1개 | 0개 | 1개 |
| GET /history | 2개 (빈/유) | 2개 (경계값) | 1개 |
| GET /health | 1개 | 1개 (모델 미로드) | 0개 |

### 4.3 테스트 분류 태깅

```python
import pytest

# 마커 정의 (pytest.ini 또는 pyproject.toml)
# [pytest]
# markers =
#     unit: 단위 테스트
#     integration: 통합 테스트
#     e2e: E2E 테스트
#     slow: 느린 테스트 (1초 이상)
#     performance: 성능 테스트

@pytest.mark.unit
def test_confidence_high():
    assert calculate_confidence(0.75) == "high"

@pytest.mark.integration
def test_predict_saves_to_db(client, db_session):
    client.post("/predict", json={...})
    assert db_session.query(Prediction).count() == 1

@pytest.mark.slow
@pytest.mark.performance
def test_response_time_under_200ms(client):
    import time
    start = time.perf_counter()
    client.post("/predict", json={...})
    elapsed = (time.perf_counter() - start) * 1000
    assert elapsed < 200, f"응답시간 초과: {elapsed:.1f}ms"
```

### 4.4 테스트 선택 실행

```bash
# 단위 테스트만 실행 (빠름)
pytest -m unit

# 통합 테스트 제외 (느린 테스트 스킵)
pytest -m "not slow"

# 특정 파일만
pytest tests/test_predict.py -v

# 커버리지 포함
pytest --cov=backend --cov-report=html tests/
```

---

## 5. FIRST 원칙 (보조 원칙)

| 원칙 | 설명 | 적용 방법 |
|------|------|----------|
| **F**ast | 단위 테스트는 1ms 이내 | DB/네트워크 Mock 사용 |
| **I**solated | 테스트 간 상태 공유 없음 | fixture scope=function |
| **R**epeatable | 어느 환경에서도 동일 결과 | 시드 고정, 외부 차단 |
| **S**elf-validating | 자동으로 pass/fail 판정 | assert 명확히 작성 |
| **T**imely | 코드 작성과 동시에 테스트 작성 | TDD 또는 BDD 방식 |

---

## 6. 테스트 명명 규칙

```python
# 패턴: test_[기능]_[조건]_[기대결과]

# 좋은 예
def test_predict_with_valid_input_returns_probability():
def test_predict_with_duplicate_agent_returns_422():
def test_history_with_map_filter_returns_filtered_results():
def test_health_when_model_loaded_returns_ok():

# 나쁜 예
def test_1():
def test_predict():
def test_error():
```

---

## 7. 테스트 문서화 표준

각 테스트 함수에는 아래 형식의 docstring을 작성합니다.

```python
def test_predict_with_all_duelist_team_returns_low_probability(client):
    """
    시나리오: 팀 A에 타격대(Duelist)만 5명 구성 시
    입력: team_a=[Jett, Reyna, Neon, Yoru, Phoenix], team_b=균형 팀
    기대: team_a 승률이 50% 미만 (역할 불균형 패널티)
    관련: 게임 로직 검증 #TC-GL-003
    """
    response = client.post("/predict", json={
        "map": "Ascent",
        "team_a": ["Jett", "Reyna", "Neon", "Yoru", "Phoenix"],
        "team_b": ["Jett", "Sova", "Omen", "Killjoy", "Skye"],  # 의도적 중복 아님
    })
    assert response.status_code == 200
    data = response.json()
    assert data["win_probability"] < 0.5
```
