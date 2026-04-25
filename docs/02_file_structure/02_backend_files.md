# 02. 백엔드 파일 상세 (`backend/`)

## 1. 폴더 전체 구조

```
backend/
├── main.py                     # FastAPI 앱 진입점
├── config.py                   # 환경변수, 경로 설정
├── database.py                 # PostgreSQL 세션 관리
├── routers/
│   ├── __init__.py
│   ├── predict.py              # POST /predict
│   ├── agents.py               # GET /agents
│   ├── maps.py                 # GET /maps
│   └── history.py              # GET /history
├── schemas/
│   ├── __init__.py
│   ├── predict.py              # Pydantic 요청/응답 스키마
│   └── history.py              # 예측 기록 스키마
├── services/
│   ├── __init__.py
│   ├── prediction_service.py   # 모델 로드 및 추론 로직
│   └── feature_service.py      # 피처 변환 로직
├── db/
│   ├── __init__.py
│   ├── models.py               # SQLAlchemy ORM 모델
│   └── init.sql                # 테이블 초기화 SQL
└── ml/
    ├── __init__.py
    ├── agent_roles.py          # 요원↔역할군 매핑
    ├── feature_engineer.py     # 피처 엔지니어링 (서빙용)
    └── predictor.py            # 앙상블 예측 실행
```

---

## 2. 파일별 역할 상세

### 2.1 `main.py` — FastAPI 앱 진입점

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import predict, agents, maps, history
from backend.services.prediction_service import PredictionService

app = FastAPI(title="ValoPredictML API", version="1.0.0")

# CORS 미들웨어 등록
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://*.vercel.app",
        "https://valo-predict.vercel.app",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(predict.router, prefix="/api/v1")
app.include_router(agents.router, prefix="/api/v1")
app.include_router(maps.router, prefix="/api/v1")
app.include_router(history.router, prefix="/api/v1")

@app.on_event("startup")
async def startup():
    PredictionService.get_instance()  # 앱 시작 시 모델 로드

@app.get("/health")
def health():
    return {"status": "ok"}
```

**책임:**
- FastAPI 앱 인스턴스 생성
- CORS 미들웨어 등록
- 라우터 등록
- 앱 시작 시 모델 사전 로드

---

### 2.2 `config.py` — 환경변수 로드

```python
import os
from dotenv import load_dotenv

load_dotenv()

# PostgreSQL 연결 설정
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "valo_predict")

# Vercel Postgres (프로덕션)
POSTGRES_URL = os.getenv("POSTGRES_URL")

DATABASE_URL = (
    POSTGRES_URL
    or f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# 모델 경로
MODEL_PATH = os.getenv("MODEL_PATH", "./models")
XGB_MODEL_PATH = f"{MODEL_PATH}/xgboost_model.joblib"
LGBM_MODEL_PATH = f"{MODEL_PATH}/lgbm_model.joblib"
LABEL_ENCODER_PATH = f"{MODEL_PATH}/label_encoder_map.joblib"
```

**책임:**
- `.env` 파일 로드
- DB URL 생성 (로컬: 분리 변수, 프로덕션: `POSTGRES_URL`)
- 모델 파일 경로 설정

---

### 2.3 `database.py` — PostgreSQL 세션 관리

```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.config import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """FastAPI 의존성 주입용 DB 세션 제공"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**책임:**
- SQLAlchemy 엔진 및 세션 팩토리 생성
- FastAPI 의존성 주입 함수 (`get_db`) 제공
- 연결 풀링 관리 (`pool_pre_ping`으로 끊긴 연결 재연결)

---

### 2.4 `routers/predict.py` — 예측 라우터

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas.predict import PredictRequest, PredictResponse
from backend.services.prediction_service import PredictionService

router = APIRouter()

@router.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest, db: Session = Depends(get_db)):
    service = PredictionService.get_instance()
    return service.predict(request, db)
```

**책임:**
- HTTP POST `/api/v1/predict` 처리
- Pydantic 요청 검증 위임
- Service 호출만 담당 (비즈니스 로직 직접 구현 금지)

---

### 2.5 `services/prediction_service.py` — 예측 서비스

**책임:**
- XGBoost, LightGBM 모델 싱글톤으로 로드
- `feature_service.transform()` 호출하여 15개 피처 생성
- `predictor.predict_proba()` 호출하여 Soft Voting 앙상블
- PostgreSQL에 예측 결과 저장

---

### 2.6 `services/feature_service.py` — 피처 변환 서비스

**책임:**
- 요원 이름 → 역할군 변환
- 역할군 카운트 계산 (8개 피처)
- diff 피처 계산 (4개 피처)
- has_controller 피처 생성 (2개)
- 맵 Label Encoding (1개)
- 최종 15개 피처 벡터 반환

---

### 2.7 `db/models.py` — ORM 모델

```python
from sqlalchemy import Column, BigInteger, String, Float, DateTime
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMPTZ
from sqlalchemy.sql import func
from backend.database import Base

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(BigInteger, primary_key=True, index=True)
    created_at = Column(TIMESTAMPTZ, server_default=func.now())
    map = Column(String(50), nullable=False, index=True)
    team_a_agents = Column(JSONB, nullable=False)
    team_b_agents = Column(JSONB, nullable=False)
    team_a_roles = Column(JSONB, nullable=False)
    team_b_roles = Column(JSONB, nullable=False)
    win_probability = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    feature_importance = Column(JSONB)
```

---

### 2.8 `ml/agent_roles.py` — 요원-역할군 매핑

```python
AGENT_ROLE_MAP = {
    # Duelist
    "Jett": "Duelist", "Reyna": "Duelist", "Phoenix": "Duelist",
    "Raze": "Duelist", "Yoru": "Duelist", "Neon": "Duelist",
    "Iso": "Duelist", "Waylay": "Duelist",
    # Initiator
    "Sova": "Initiator", "Breach": "Initiator", "Skye": "Initiator",
    "KAY/O": "Initiator", "Fade": "Initiator", "Gekko": "Initiator",
    # Controller
    "Viper": "Controller", "Omen": "Controller", "Brimstone": "Controller",
    "Astra": "Controller", "Harbor": "Controller", "Clove": "Controller",
    # Sentinel
    "Killjoy": "Sentinel", "Cypher": "Sentinel", "Sage": "Sentinel",
    "Chamber": "Sentinel", "Deadlock": "Sentinel", "Vyse": "Sentinel",
}

def get_role(agent_name: str) -> str:
    return AGENT_ROLE_MAP.get(agent_name, "Unknown")
```

---

### 2.9 `ml/predictor.py` — 앙상블 예측

**책임:**
- `xgb_model.predict_proba(X)` 호출
- `lgbm_model.predict_proba(X)` 호출
- Soft Voting: `0.6 * xgb_prob + 0.4 * lgbm_prob`
- 피처 중요도 추출 및 정규화

---

## 3. 의존성 흐름 다이어그램

```
HTTP Request
    ↓
[routers/predict.py]
    ↓ (Pydantic 검증 후)
[services/prediction_service.py]
    ├──→ [services/feature_service.py] → 15개 피처 생성
    │        └──→ [ml/agent_roles.py]
    │        └──→ [ml/feature_engineer.py]
    ├──→ [ml/predictor.py] → Soft Voting 앙상블
    └──→ [database.py] → PostgreSQL INSERT
    ↓
HTTP Response
```

---

## 4. 관련 문서

| 문서 | 내용 |
|---|---|
| [../03_architecture/04_api_design.md](../03_architecture/04_api_design.md) | API 엔드포인트 전체 스펙 |
| [../03_architecture/03_database_schema.md](../03_architecture/03_database_schema.md) | PostgreSQL 스키마 DDL |
| [../06_model_test/03_fastapi_implementation.md](../06_model_test/03_fastapi_implementation.md) | FastAPI 구현 코드 상세 |
