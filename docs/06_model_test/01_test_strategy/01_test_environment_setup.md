# 01. 테스트 환경 구성

## 1. 개요

ValoPredictML 프로젝트의 테스트는 세 가지 환경에서 수행됩니다.

| 환경 | 목적 | 실행 주체 |
|------|------|-----------|
| 로컬 (Local) | 개발 중 빠른 피드백, 단위/통합 테스트 | 개발자 |
| CI (GitHub Actions) | PR 머지 전 자동 검증, 회귀 방지 | 자동화 |
| 프로덕션 (Vercel + Render/Railway) | 실제 배포 후 smoke test | 배포 후 검증 |

---

## 2. 로컬 테스트 환경 구성

### 2.1 필수 도구 목록

| 도구 | 버전 | 용도 |
|------|------|------|
| Python | 3.11+ | FastAPI 백엔드 실행 |
| Node.js | 20 LTS | Next.js 16 프론트엔드 실행 |
| PostgreSQL | 18 | 로컬 DB (또는 Docker) |
| curl | 최신 | API 수동 테스트 |
| k6 | 0.49+ | 부하 테스트 |
| pytest | 8.x | Python 단위/통합 테스트 |
| httpx | 0.27+ | FastAPI TestClient용 비동기 HTTP |
| Docker | 24+ | PostgreSQL 컨테이너 실행 (선택) |

### 2.2 Python 가상환경 설정

```bash
# 프로젝트 루트에서
python -m venv .venv
source .venv/bin/activate          # macOS/Linux
# .venv\Scripts\activate           # Windows

# 의존성 설치
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 테스트 전용 의존성
```

`requirements-dev.txt` 예시:
```
pytest==8.2.0
pytest-asyncio==0.23.6
httpx==0.27.0
pytest-cov==5.0.0
factory-boy==3.3.0
faker==25.0.0
```

### 2.3 PostgreSQL 로컬 설정

**방법 A: Docker Compose 사용 (권장)**

```yaml
# docker-compose.yml
version: "3.9"
services:
  postgres:
    image: postgres:18-alpine
    environment:
      POSTGRES_USER: valopred
      POSTGRES_PASSWORD: valopred_secret
      POSTGRES_DB: valopredml
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

```bash
docker compose up -d postgres
```

**방법 B: 로컬 PostgreSQL 직접 설치**

```bash
# macOS (Homebrew)
brew install postgresql@18
brew services start postgresql@18

# DB 및 사용자 생성
psql postgres -c "CREATE USER valopred WITH PASSWORD 'valopred_secret';"
psql postgres -c "CREATE DATABASE valopredml OWNER valopred;"
```

### 2.4 환경변수 설정

```bash
cp .env.example .env
```

`.env` 파일 내용:
```
# Database
DATABASE_URL=postgresql://valopred:valopred_secret@localhost:5432/valopredml

# Model
MODEL_PATH=./models
MODEL_VERSION=1.0.0

# API
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000,https://*.vercel.app

# Logging
LOG_LEVEL=INFO
```

### 2.5 FastAPI 서버 실행

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 서버 기동 확인
curl http://localhost:8000/health
# 기대 응답: {"status":"ok","model_loaded":true,"model_version":"1.0.0"}
```

### 2.6 Next.js 프론트엔드 실행

```bash
cd frontend
npm install
cp .env.local.example .env.local
# .env.local: NEXT_PUBLIC_API_URL=http://localhost:8000

npm run dev
# http://localhost:3000 에서 확인
```

---

## 3. CI 환경 구성 (GitHub Actions)

### 3.1 워크플로우 파일

```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  backend-test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:18-alpine
        env:
          POSTGRES_USER: valopred
          POSTGRES_PASSWORD: valopred_secret
          POSTGRES_DB: valopredml_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run pytest
        env:
          DATABASE_URL: postgresql://valopred:valopred_secret@localhost:5432/valopredml_test
          MODEL_PATH: ./tests/fixtures/models
        run: |
          pytest tests/ -v --cov=backend --cov-report=xml --cov-fail-under=80

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml

  frontend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: cd frontend && npm ci
      - run: cd frontend && npm run lint
      - run: cd frontend && npm run build
```

### 3.2 테스트용 모델 픽스처

CI 환경에서는 실제 학습된 모델 대신 경량 목(mock) 모델을 사용합니다.

```python
# tests/fixtures/create_mock_models.py
import joblib
import json
import numpy as np
from sklearn.dummy import DummyClassifier
from pathlib import Path

def create_mock_models(output_dir: str = "tests/fixtures/models"):
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # 더미 분류기 (항상 0.5 확률 반환)
    dummy = DummyClassifier(strategy="prior")
    dummy.fit([[0]*15], [1])
    dummy.classes_ = np.array([0, 1])
    dummy.class_prior_ = np.array([0.5, 0.5])

    joblib.dump(dummy, f"{output_dir}/xgboost_model.joblib")
    joblib.dump(dummy, f"{output_dir}/lgbm_model.joblib")

    # LabelEncoder 픽스처
    from sklearn.preprocessing import LabelEncoder
    le = LabelEncoder()
    le.fit(["Ascent", "Bind", "Haven", "Split", "Icebox",
            "Breeze", "Fracture", "Pearl", "Lotus", "Sunset", "Abyss"])
    joblib.dump(le, f"{output_dir}/label_encoder_map.joblib")

    # 메타데이터
    metadata = {
        "model_version": "test-1.0.0",
        "trained_at": "2024-01-01T00:00:00",
        "features": [
            "map_encoded", "team_a_duelist", "team_a_initiator",
            "team_a_controller", "team_a_sentinel",
            "team_b_duelist", "team_b_initiator",
            "team_b_controller", "team_b_sentinel",
            "duelist_diff", "initiator_diff", "controller_diff",
            "sentinel_diff", "team_a_unknown", "team_b_unknown"
        ]
    }
    with open(f"{output_dir}/model_metadata.json", "w") as f:
        json.dump(metadata, f)

    print(f"Mock models created in {output_dir}")

if __name__ == "__main__":
    create_mock_models()
```

---

## 4. 프로덕션 Smoke Test

배포 완료 후 핵심 엔드포인트만 빠르게 검증합니다.

```bash
#!/bin/bash
# scripts/smoke_test.sh
BASE_URL="${PROD_API_URL:-https://your-api.onrender.com}"

echo "=== Smoke Test: $BASE_URL ==="

# 1. Health Check
echo -n "[1] GET /health ... "
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health")
[ "$STATUS" = "200" ] && echo "OK ($STATUS)" || echo "FAIL ($STATUS)"

# 2. Agents
echo -n "[2] GET /agents ... "
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/agents")
[ "$STATUS" = "200" ] && echo "OK ($STATUS)" || echo "FAIL ($STATUS)"

# 3. Maps
echo -n "[3] GET /maps ... "
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/maps")
[ "$STATUS" = "200" ] && echo "OK ($STATUS)" || echo "FAIL ($STATUS)"

# 4. Predict (정상 케이스)
echo -n "[4] POST /predict (정상) ... "
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/predict" \
  -H "Content-Type: application/json" \
  -d '{"map":"Ascent","team_a":["Jett","Sova","Viper","Killjoy","Skye"],"team_b":["Reyna","Breach","Omen","Cypher","Fade"]}')
STATUS=$(echo "$RESPONSE" | tail -1)
[ "$STATUS" = "200" ] && echo "OK ($STATUS)" || echo "FAIL ($STATUS)"

# 5. Predict (에러 케이스 - 422 기대)
echo -n "[5] POST /predict (잘못된 맵 → 422) ... "
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/predict" \
  -H "Content-Type: application/json" \
  -d '{"map":"InvalidMap","team_a":["Jett","Sova","Viper","Killjoy","Skye"],"team_b":["Reyna","Breach","Omen","Cypher","Fade"]}')
[ "$STATUS" = "422" ] && echo "OK ($STATUS)" || echo "FAIL ($STATUS)"

echo "=== Smoke Test 완료 ==="
```

```bash
chmod +x scripts/smoke_test.sh
PROD_API_URL=https://your-api.onrender.com ./scripts/smoke_test.sh
```

---

## 5. 환경별 설정 요약

| 항목 | 로컬 | CI | 프로덕션 |
|------|------|----|----------|
| DB | Docker/로컬 PG | GitHub Services PG | Vercel Postgres |
| 모델 | 실제 모델 파일 | 목(mock) 모델 | 실제 모델 파일 |
| CORS | localhost:3000 | 불필요 | vercel.app 도메인 |
| 로그 레벨 | DEBUG | INFO | WARNING |
| 응답시간 목표 | ≤ 200ms | 측정 안 함 | ≤ 200ms |
| 테스트 DB | valopredml | valopredml_test | 별도 스키마 격리 |
