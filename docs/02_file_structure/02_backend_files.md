# 02. 백엔드 파일 상세

마지막 업데이트: 2026-05-04

> **범위 외 (out of scope)**: 이 프로젝트는 FastAPI 백엔드를 사용하지 않습니다. 본 프로젝트는 **Streamlit 로컬 도구**이며 별도의 REST API 서버가 없습니다.
>
> 아래 내용은 **PostgreSQL 예측 기록 저장 후보** 관련 설명입니다. PostgreSQL + SQLAlchemy는 미구현 상태이며, 구현 시 Streamlit 앱에서 직접 SQLAlchemy를 통해 접근합니다.

---

## 1. 데이터베이스 연결 구조 (후보, 미구현)

```
app/streamlit_app.py
    ↓ SQLAlchemy 직접 호출
database.py          # DB 세션 관리
    ↓
PostgreSQL (로컬)    # predictions 테이블
```

FastAPI 라우터, Pydantic 스키마, uvicorn은 이 프로젝트에서 사용하지 않습니다.

---

## 2. 데이터베이스 관련 파일 (후보, 미구현)

### 2.1 `database.py` — PostgreSQL 세션 관리

```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:@localhost:5432/valo_predict"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**책임:**
- SQLAlchemy 엔진 및 세션 팩토리 생성
- `.env`의 `DATABASE_URL` 환경변수 로드
- 연결 풀링 관리

---

### 2.2 `db/models.py` — ORM 모델

```python
from sqlalchemy import Column, BigInteger, String, Float
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMPTZ
from sqlalchemy.sql import func
from database import Base

class Prediction(Base):
    __tablename__ = "predictions"

    id               = Column(BigInteger, primary_key=True, autoincrement=True)
    created_at       = Column(TIMESTAMPTZ, server_default=func.now(), nullable=False)
    map              = Column(String(50), nullable=False, index=True)
    team_a_agents    = Column(JSONB, nullable=False)
    team_b_agents    = Column(JSONB, nullable=False)
    team_a_roles     = Column(JSONB, nullable=False)
    team_b_roles     = Column(JSONB, nullable=False)
    win_probability  = Column(Float, nullable=False)
    confidence       = Column(Float, nullable=False)
    feature_importance = Column(JSONB)
```

---

## 3. 환경변수 설정

```env
# .env (루트)
DATABASE_URL=postgresql+psycopg2://postgres:password@localhost:5432/valo_predict
MODEL_PATH=./models
```

---

## 4. 관련 문서

| 문서 | 내용 |
|------|------|
| [../03_architecture/03_database_schema.md](../03_architecture/03_database_schema.md) | PostgreSQL 스키마 DDL |
| [04_frontend_files.md](04_frontend_files.md) | Streamlit UI 파일 구조 |
| [05_config_and_env.md](05_config_and_env.md) | 환경변수 전체 목록 |
