# 03. PostgreSQL 데이터베이스 스키마

마지막 업데이트: 2026-05-04

> PostgreSQL + SQLAlchemy는 **예측 기록 저장 후보**입니다. 현재 미구현 상태이며, 구현 시 Streamlit 앱에서 SQLAlchemy를 통해 직접 접근합니다. Vercel Postgres, FastAPI, REST API는 이 프로젝트에서 사용하지 않습니다.

## 1. 테이블 구조 개요

```
PostgreSQL (로컬)
│
└── predictions    ← 예측 요청 기록 (후보, 미구현)
```

`match_cache` 테이블은 HenrikDev API 캐시 용도였으나, 외부 API를 사용하지 않으므로 이 프로젝트에서 제외합니다.

---

## 2. `predictions` 테이블

### 2.1 DDL

```sql
CREATE TABLE predictions (
    id                 BIGSERIAL PRIMARY KEY,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    map                VARCHAR(50)  NOT NULL,
    team_a_agents      JSONB        NOT NULL,
    team_b_agents      JSONB        NOT NULL,
    team_a_roles       JSONB        NOT NULL,
    team_b_roles       JSONB        NOT NULL,
    win_probability    DOUBLE PRECISION NOT NULL,
    confidence         DOUBLE PRECISION,
    feature_importance JSONB
);

-- 인덱스
CREATE INDEX idx_predictions_created_at ON predictions (created_at DESC);
CREATE INDEX idx_predictions_map        ON predictions (map);
CREATE INDEX idx_predictions_agents     ON predictions USING GIN (team_a_agents);
```

### 2.2 컬럼 설명

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | BIGSERIAL | PK, 자동 증가 |
| `created_at` | TIMESTAMPTZ | 예측 생성 시각 (UTC) |
| `map` | VARCHAR(50) | 맵 이름 ("Ascent" 등) |
| `team_a_agents` | JSONB | 팀 A 요원 목록 `["Jett", "Viper", ...]` |
| `team_b_agents` | JSONB | 팀 B 요원 목록 |
| `team_a_roles` | JSONB | 팀 A 역할군 카운트 `{"duelist": 2, ...}` |
| `team_b_roles` | JSONB | 팀 B 역할군 카운트 |
| `win_probability` | DOUBLE PRECISION | 팀 A 승리 확률 (0.0~1.0) |
| `confidence` | DOUBLE PRECISION | 예측 신뢰도 0.0~1.0 (선택) |
| `feature_importance` | JSONB | 피처 중요도 `[{"feature": "...", "value": 0.23}, ...]` |

### 2.3 데이터 예시

```json
{
  "id": 1,
  "created_at": "2026-05-04T09:30:00Z",
  "map": "Ascent",
  "team_a_agents": ["Jett", "Viper", "Sova", "Killjoy", "Omen"],
  "team_b_agents": ["Reyna", "Brimstone", "Fade", "Cypher", "Skye"],
  "team_a_roles": {"duelist": 1, "controller": 2, "initiator": 1, "sentinel": 1},
  "team_b_roles": {"duelist": 1, "controller": 1, "initiator": 2, "sentinel": 1},
  "win_probability": 0.617,
  "confidence": null,
  "feature_importance": [
    {"feature": "diff_controller", "value": 0.21},
    {"feature": "has_controller_a", "value": 0.17},
    {"feature": "map_encoded", "value": 0.14}
  ]
}
```

---

## 3. SQLAlchemy ORM 모델

```python
# database.py (미구현 — PostgreSQL 범위 외)
from sqlalchemy import Column, BigInteger, String, Float, Index
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMPTZ
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

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
    confidence       = Column(Float)
    feature_importance = Column(JSONB)

    __table_args__ = (
        Index("idx_predictions_created_at", "created_at"),
    )
```

---

## 4. 초기화 SQL

```sql
-- 실행: psql -U postgres -d valo_predict -f db/init.sql

CREATE TABLE IF NOT EXISTS predictions (
    id                 BIGSERIAL PRIMARY KEY,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    map                VARCHAR(50)  NOT NULL,
    team_a_agents      JSONB        NOT NULL,
    team_b_agents      JSONB        NOT NULL,
    team_a_roles       JSONB        NOT NULL,
    team_b_roles       JSONB        NOT NULL,
    win_probability    DOUBLE PRECISION NOT NULL,
    confidence         DOUBLE PRECISION,
    feature_importance JSONB
);

CREATE INDEX IF NOT EXISTS idx_predictions_created_at ON predictions (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_map        ON predictions (map);
```

---

## 5. 로컬 설치 가이드

```bash
# macOS (Homebrew)
brew install postgresql@18
brew services start postgresql@18

# DB 생성
psql -U postgres -c "CREATE DATABASE valo_predict;"

# 테이블 초기화
psql -U postgres -d valo_predict -f db/init.sql
```

---

## 6. 관련 문서

| 문서 | 내용 |
|------|------|
| [../02_file_structure/02_backend_files.md](../02_file_structure/02_backend_files.md) | database.py, models.py 코드 상세 |
| [../02_file_structure/05_config_and_env.md](../02_file_structure/05_config_and_env.md) | DATABASE_URL 환경변수 설정 |
