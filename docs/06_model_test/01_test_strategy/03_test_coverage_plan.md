# 03. 테스트 커버리지 계획

## 1. 커버리지 목표

| 레이어 | 목표 커버리지 | 측정 방법 |
|--------|-------------|-----------|
| 전체 백엔드 | 80% 이상 | pytest-cov |
| 라우터 (routers/) | 90% 이상 | 엔드포인트 직접 호출 |
| 서비스 (services/) | 85% 이상 | 단위 + 통합 테스트 |
| 스키마 (schemas/) | 95% 이상 | 유효성 검사 케이스 망라 |
| DB 모델 (models/) | 70% 이상 | ORM CRUD 테스트 |
| 유틸리티 (utils/) | 80% 이상 | 단위 테스트 |

---

## 2. 테스트 매트릭스

### 2.1 POST /predict

| TC ID | 분류 | 시나리오 | 입력 | 기대 상태코드 | 우선순위 |
|-------|------|----------|------|-------------|---------|
| TC-P-001 | 정상 | 균형 잡힌 조합, Ascent | 각 역할 1명씩 | 200 | P0 |
| TC-P-002 | 정상 | 전략가 중심 팀 | Controller 3명 | 200 | P1 |
| TC-P-003 | 정상 | 모든 맵 순환 | 11개 맵 순서대로 | 200 | P1 |
| TC-P-004 | 엣지 | 중복 요원 | team_a[0]==team_b[0] | 422 | P0 |
| TC-P-005 | 엣지 | 팀 인원 부족 | team_a에 4명 | 422 | P0 |
| TC-P-006 | 엣지 | 팀 인원 초과 | team_a에 6명 | 422 | P0 |
| TC-P-007 | 엣지 | 유효하지 않은 맵 | "Icebox2" | 422 | P0 |
| TC-P-008 | 엣지 | 빈 팀 배열 | team_a=[] | 422 | P0 |
| TC-P-009 | 엣지 | 알 수 없는 요원 이름 | "UnknownAgent" | 200 (unknown 처리) | P1 |
| TC-P-010 | 에러 | 모델 미로드 | 정상 요청, 모델 없음 | 500 | P0 |
| TC-P-011 | 성능 | 응답시간 | 정상 요청 10회 | 200, 각 ≤200ms | P0 |

### 2.2 GET /agents

| TC ID | 분류 | 시나리오 | 기대 상태코드 | 우선순위 |
|-------|------|----------|-------------|---------|
| TC-A-001 | 정상 | 전체 요원 목록 반환 | 200 | P0 |
| TC-A-002 | 정상 | 역할군 분류 정확성 | 200, roles 키 포함 | P1 |
| TC-A-003 | 정상 | 요원 수 27명 이상 | 200, agents.length >= 27 | P1 |

### 2.3 GET /maps

| TC ID | 분류 | 시나리오 | 기대 상태코드 | 우선순위 |
|-------|------|----------|-------------|---------|
| TC-M-001 | 정상 | 전체 맵 목록 반환 | 200 | P0 |
| TC-M-002 | 정상 | 맵 수 11개 | 200, maps.length == 11 | P1 |

### 2.4 GET /history

| TC ID | 분류 | 시나리오 | 파라미터 | 기대 상태코드 | 우선순위 |
|-------|------|----------|---------|-------------|---------|
| TC-H-001 | 정상 | 기본 조회 (데이터 없음) | - | 200, total=0 | P0 |
| TC-H-002 | 정상 | 기본 조회 (데이터 있음) | - | 200, total>0 | P0 |
| TC-H-003 | 정상 | 페이지네이션 | limit=5&offset=0 | 200, items.length<=5 | P1 |
| TC-H-004 | 정상 | 맵 필터링 | map=Ascent | 200, 모든 item.map==Ascent | P1 |
| TC-H-005 | 엣지 | limit=0 | limit=0 | 200 또는 422 | P2 |
| TC-H-006 | 엣지 | offset 초과 | offset=99999 | 200, items=[] | P2 |
| TC-H-007 | 엣지 | 유효하지 않은 맵 필터 | map=InvalidMap | 200, items=[] 또는 422 | P2 |

### 2.5 GET /health

| TC ID | 분류 | 시나리오 | 기대 결과 | 우선순위 |
|-------|------|----------|---------|---------|
| TC-HE-001 | 정상 | 모델 로드 완료 상태 | status=ok, model_loaded=true | P0 |
| TC-HE-002 | 엣지 | 모델 미로드 상태 | status=ok, model_loaded=false | P1 |

---

## 3. 우선순위 정의

| 우선순위 | 설명 | 실패 시 대응 |
|---------|------|------------|
| **P0** | 블로커 — 반드시 통과해야 배포 가능 | 즉시 핫픽스, 배포 차단 |
| **P1** | 주요 — 기능 정확성에 직접 영향 | 당일 수정 목표 |
| **P2** | 부가 — 엣지 케이스, UX 개선 영역 | 다음 스프린트 처리 |

---

## 4. 커버리지 측정 설정

### 4.1 pyproject.toml 설정

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --strict-markers"
markers = [
    "unit: 단위 테스트",
    "integration: 통합 테스트",
    "e2e: E2E 테스트",
    "slow: 1초 이상 소요",
    "performance: 성능 테스트",
]

[tool.coverage.run]
source = ["backend"]
omit = [
    "backend/tests/*",
    "backend/migrations/*",
    "backend/main.py",          # 진입점은 통합 테스트로 커버
]

[tool.coverage.report]
fail_under = 80
show_missing = true
exclude_lines = [
    "pragma: no cover",
    "if __name__ == .__main__.:",
    "raise NotImplementedError",
]
```

### 4.2 커버리지 실행 및 리포트

```bash
# 커버리지 측정 + HTML 리포트 생성
pytest tests/ --cov=backend --cov-report=html --cov-report=term-missing

# HTML 리포트 확인
open htmlcov/index.html

# 커버리지 미달 시 CI 실패
pytest tests/ --cov=backend --cov-fail-under=80
```

### 4.3 커버리지 제외 규칙

```python
# 의도적으로 커버리지에서 제외하는 코드
def _debug_print_features(features):  # pragma: no cover
    """개발용 디버그 출력 — 프로덕션 비활성."""
    print(features)

class AbstractBaseService:
    def predict(self):
        raise NotImplementedError  # pragma: no cover
```

---

## 5. 테스트 파일 구조

```
tests/
├── conftest.py                    # 공통 fixture
├── fixtures/
│   ├── models/                    # 목(mock) 모델 파일
│   │   ├── xgboost_model.joblib
│   │   ├── lgbm_model.joblib
│   │   ├── label_encoder_map.joblib
│   │   └── model_metadata.json
│   └── sample_requests.json       # 재사용 요청 데이터
├── unit/
│   ├── test_schemas.py            # Pydantic 스키마 검증
│   ├── test_feature_engineer.py   # 피처 엔지니어링
│   ├── test_confidence.py         # 신뢰도 계산
│   └── test_role_counts.py        # 역할군 집계
├── integration/
│   ├── test_predict_endpoint.py   # POST /predict
│   ├── test_agents_endpoint.py    # GET /agents
│   ├── test_maps_endpoint.py      # GET /maps
│   ├── test_history_endpoint.py   # GET /history
│   └── test_health_endpoint.py    # GET /health
├── performance/
│   ├── test_response_time.py      # 응답시간 검증
│   └── k6_scripts/
│       └── load_test.js           # k6 부하 테스트
└── e2e/
    └── test_predict_flow.py       # Playwright E2E
```

---

## 6. 커버리지 추이 목표 (스프린트별)

| 스프린트 | 목표 커버리지 | 주요 추가 테스트 |
|---------|-------------|----------------|
| Sprint 1 | 50% | 스키마 검증, /health, /agents, /maps |
| Sprint 2 | 70% | POST /predict 정상/에러 케이스 |
| Sprint 3 | 80% | /history 페이지네이션, 성능 테스트 |
| Sprint 4 | 85% | 엣지 케이스, E2E 추가 |
| 안정화 | 85% 유지 | 회귀 방지 테스트 |

---

## 7. 커버리지 예외 승인 절차

80% 미만인 모듈이 있을 경우 아래 절차를 따릅니다.

1. 해당 모듈에 `# coverage-exception` 주석과 사유 기재
2. PR description에 미달 사유 및 보완 계획 명시
3. 팀 리뷰어 승인 후 병합 허용
4. 다음 스프린트 내 보완 이슈 생성 필수

```python
# backend/utils/legacy_encoder.py
# coverage-exception: 레거시 호환성 코드, 점진적 제거 예정 (Issue #42)
```
