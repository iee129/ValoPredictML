> ⚠️ 참고/확장 설계: 현재 시연은 웹 스택(FastAPI `src/api` + Next.js `web`) 기준이다. 이 문서의 테스트 설계는 참고용으로 보존한다.

> ⚠️ **참고용**: 본 프로젝트는 웹 스택(FastAPI `src/api` + Next.js `web`)으로 서빙한다. 본문의 상세 테스트 설계는 참고용으로 보존된다.

# 01. main.py 완전 구현 코드

## 1. 파일 위치 및 역할

```
backend/
└── main.py   ← FastAPI 애플리케이션 진입점
```

`main.py`는 FastAPI 인스턴스 생성, 미들웨어 등록, 라우터 포함, 시작/종료 이벤트를 담당합니다.

---

## 2. 완전 구현 코드

```python
# backend/main.py
"""
ValoPredictML FastAPI 애플리케이션 진입점.

실행:
    uvicorn main:app --reload --port 8000
    gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
"""

import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from database import engine, Base
from routers import predict, agents, maps, history, health

# ── 로깅 설정 ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Lifespan (시작/종료 이벤트) ────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작 및 종료 시 실행되는 lifespan 핸들러."""
    # 시작
    logger.info("서버 시작 중...")

    # DB 테이블 생성 (없는 경우)
    Base.metadata.create_all(bind=engine)
    logger.info("DB 테이블 확인 완료")

    # 모델 사전 로드 (싱글톤 초기화)
    try:
        from services.prediction_service import PredictionService
        svc = PredictionService()
        logger.info(f"모델 로드 완료: v{svc.get_version()}")
    except Exception as e:
        logger.warning(f"모델 로드 실패 (예측 불가 상태로 시작): {e}")

    yield

    # 종료
    logger.info("서버 종료 중...")


# ── FastAPI 인스턴스 ────────────────────────────────────────────────────────
app = FastAPI(
    title="ValoPredictML API",
    version="1.0.0",
    description=(
        "발로란트 팀 조합 승률 예측 API. "
        "RF + XGBoost + LightGBM 가중 Soft Voting (2.0:3.0:0.1) 앙상블 모델 기반."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# ── CORS 미들웨어 ───────────────────────────────────────────────────────────
CORS_ORIGINS = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:3000,https://*.vercel.app"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Accept"],
    max_age=3600,
)


# ── 요청 로깅 미들웨어 ──────────────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """모든 요청의 메서드, 경로, 응답시간을 로깅합니다."""
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000

    logger.info(
        f"{request.method} {request.url.path} "
        f"→ {response.status_code} [{elapsed_ms:.1f}ms]"
    )

    # 응답 헤더에 처리 시간 추가
    response.headers["X-Process-Time"] = f"{elapsed_ms:.1f}ms"
    return response


# ── 전역 예외 핸들러 ────────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """처리되지 않은 예외를 500으로 변환합니다."""
    logger.error(f"처리되지 않은 예외: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "내부 서버 오류가 발생했습니다. 잠시 후 다시 시도하세요."},
    )


# ── 라우터 등록 ─────────────────────────────────────────────────────────────
app.include_router(predict.router, tags=["prediction"])
app.include_router(agents.router, tags=["agents"])
app.include_router(maps.router, tags=["maps"])
app.include_router(history.router, tags=["history"])
app.include_router(health.router, tags=["health"])


# ── 루트 엔드포인트 ─────────────────────────────────────────────────────────
@app.get("/", tags=["root"])
async def root():
    """API 루트 — 사용 가능한 엔드포인트 안내."""
    return {
        "name": "ValoPredictML API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "predict": "POST /predict",
            "agents":  "GET /agents",
            "maps":    "GET /maps",
            "history": "GET /history",
            "health":  "GET /health",
        },
    }
```

---

## 3. 환경 변수 목록

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `VALO_DATABASE_URL` | — | PostgreSQL 연결 문자열 (선택적 — 미설정 시 히스토리 비활성, 예측은 정상 동작) |
| `DATABASE_URL` | — | PostgreSQL 연결 문자열 대체값 (`VALO_DATABASE_URL` 없을 때 참조) |
| `MODEL_PATH` | `./models` | ML 모델 파일 디렉토리 |
| `CORS_ORIGINS` | `http://localhost:3000,...` | 허용 CORS Origin (쉼표 구분) |
| `LOG_LEVEL` | `INFO` | 로그 레벨 (DEBUG/INFO/WARNING/ERROR) |
| `API_HOST` | `0.0.0.0` | 바인딩 호스트 |
| `API_PORT` | `8000` | 바인딩 포트 |

---

## 4. 디렉토리 전체 구조

```
backend/
├── main.py                    ← 진입점
├── database.py                ← SQLAlchemy 엔진, 세션, Base
├── models/
│   └── prediction.py          ← ORM 모델
├── schemas/
│   ├── predict.py             ← PredictRequest, PredictResponse
│   ├── agents.py              ← AgentsResponse
│   ├── maps.py                ← MapsResponse
│   └── history.py             ← HistoryResponse
├── routers/
│   ├── predict.py             ← POST /predict
│   ├── agents.py              ← GET /agents
│   ├── maps.py                ← GET /maps
│   ├── history.py             ← GET /history
│   └── health.py              ← GET /health
├── services/
│   └── prediction_service.py  ← 싱글톤 예측 서비스
├── ml/
│   ├── feature_engineer.py    ← 피처 변환
│   └── agent_roles.py         ← 요원→역할 매핑
├── data/
│   ├── agent_data.py          ← AGENTS, ROLES 딕셔너리
│   └── map_data.py            ← MAPS 딕셔너리
└── models_files/              ← joblib 모델 파일들
    ├── xgboost_model.joblib
    ├── lgbm_model.joblib
    ├── label_encoder_map.joblib
    └── model_metadata.json
```

---

## 5. database.py 전체 코드

```python
# backend/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://valopred:valopred_secret@localhost:5432/valopredml"
)

# Vercel Postgres (Neon) sslmode 처리
if "sslmode" not in DATABASE_URL and "vercel" in DATABASE_URL.lower():
    DATABASE_URL += "?sslmode=require"

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI 의존성 주입용 DB 세션 제공."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

## 6. 실행 방법

```bash
# 개발 환경 (자동 재시작)
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 프로덕션 환경
gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 30 \
  --access-logfile - \
  --error-logfile -

# Docker
docker build -t valopredml-api .
docker run -p 8000:8000 \
  -e DATABASE_URL=$DATABASE_URL \
  -e MODEL_PATH=/app/models \
  valopredml-api
```

---

## 7. 기동 확인

```bash
# 헬스 체크
curl http://localhost:8000/health

# Swagger UI
open http://localhost:8000/docs

# 루트 응답
curl http://localhost:8000/
```

**기대 응답 (/)**
```json
{
  "name": "ValoPredictML API",
  "version": "1.0.0",
  "docs": "/docs",
  "endpoints": {
    "predict": "POST /predict",
    "agents":  "GET /agents",
    "maps":    "GET /maps",
    "history": "GET /history",
    "health":  "GET /health"
  }
}
```
