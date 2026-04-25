# 03. PostgreSQL 데이터베이스 스키마

## 1. 테이블 구조 개요

```
PostgreSQL 18 (Vercel Postgres 또는 로컬)
│
├── predictions          ← 예측 요청 기록
└── match_cache          ← HenrikDev API 경기 캐시 (선택)
```

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
    confidence         DOUBLE PRECISION NOT NULL,
    confidence_level   VARCHAR(10)  NOT NULL
                       CHECK (confidence_level IN ('High', 'Medium', 'Low')),
    feature_importance JSONB
);

-- 인덱스
CREATE INDEX idx_predictions_created_at ON predictions (created_at DESC);
CREATE INDEX idx_predictions_map        ON predictions (map);
CREATE INDEX idx_predictions_agents     ON predictions USING GIN (team_a_agents);
```

### 2.2 컬럼 설명

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | BIGSERIAL | PK, 자동 증가 |
| `created_at` | TIMESTAMPTZ | 예측 생성 시각 (UTC) |
| `map` | VARCHAR(50) | 맵 이름 ("Ascent" 등) |
| `team_a_agents` | JSONB | 팀 A 요원 목록 `["Jett", "Viper", ...]` |
| `team_b_agents` | JSONB | 팀 B 요원 목록 |
| `team_a_roles` | JSONB | 팀 A 역할군 카운트 `{"duelist": 2, ...}` |
| `team_b_roles` | JSONB | 팀 B 역할군 카운트 |
| `win_probability` | DOUBLE PRECISION | 팀 A 승리 확률 (0.0~1.0) |
| `confidence` | DOUBLE PRECISION | 예측 신뢰도 (0.0~1.0) |
| `confidence_level` | VARCHAR(10) | High / Medium / Low |
| `feature_importance` | JSONB | 피처 중요도 `[{"feature": "...", "value": 0.23}, ...]` |

### 2.3 데이터 예시

```json
{
  "id": 1,
  "created_at": "2025-01-15T09:30:00Z",
  "map": "Ascent",
  "team_a_agents": ["Jett", "Viper", "Sova", "Killjoy", "Omen"],
  "team_b_agents": ["Reyna", "Brimstone", "Fade", "Cypher", "Skye"],
  "team_a_roles": {"duelist": 1, "controller": 2, "initiator": 1, "sentinel": 1},
  "team_b_roles": {"duelist": 1, "controller": 1, "initiator": 2, "sentinel": 1},
  "win_probability": 0.673,
  "confidence": 0.85,
  "confidence_level": "High",
  "feature_importance": [
    {"feature": "controller_diff", "value": 0.23},
    {"feature": "team_a_has_controller", "value": 0.18},
    {"feature": "map_encoded", "value": 0.15}
  ]
}
```

---

## 3. `match_cache` 테이블 (선택)

HenrikDev API로 수집한 실제 경기 데이터를 임시 저장.

### 3.1 DDL

```sql
CREATE TABLE match_cache (
    id           BIGSERIAL PRIMARY KEY,
    match_id     VARCHAR(100) NOT NULL UNIQUE,
    fetched_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    match_status VARCHAR(20)  NOT NULL DEFAULT 'pending'
                 CHECK (match_status IN ('pending', 'processed', 'failed')),
    raw_data     JSONB        NOT NULL,
    processed    BOOLEAN      NOT NULL DEFAULT FALSE
);

CREATE INDEX idx_match_cache_match_id    ON match_cache (match_id);
CREATE INDEX idx_match_cache_status      ON match_cache (match_status);
CREATE INDEX idx_match_cache_fetched_at  ON match_cache (fetched_at DESC);
```

### 3.2 컬럼 설명

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `match_id` | VARCHAR(100) | HenrikDev API 매치 ID (UNIQUE) |
| `match_status` | VARCHAR(20) | pending / processed / failed |
| `raw_data` | JSONB | API 응답 원본 JSON |
| `processed` | BOOLEAN | `ml/data_pipeline.py`에서 처리 여부 |

---

## 4. SQLAlchemy ORM 모델

```python
# backend/db/models.py
from sqlalchemy import Column, BigInteger, String, Float, Boolean, Index
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMPTZ
from sqlalchemy.sql import func
from backend.database import Base

class Prediction(Base):
    __tablename__ = "predictions"

    id               = Column(BigInteger, primary_key=True, autoincrement=True)
    created_at       = Column(TIMESTAMPTZ, server_default=func.now(), nullable=False)
    map              = Column(String(50),  nullable=False, index=True)
    team_a_agents    = Column(JSONB, nullable=False)
    team_b_agents    = Column(JSONB, nullable=False)
    team_a_roles     = Column(JSONB, nullable=False)
    team_b_roles     = Column(JSONB, nullable=False)
    win_probability  = Column(Float, nullable=False)
    confidence       = Column(Float, nullable=False)
    confidence_level = Column(String(10), nullable=False)
    feature_importance = Column(JSONB)

    __table_args__ = (
        Index("idx_predictions_created_at", "created_at"),
    )


class MatchCache(Base):
    __tablename__ = "match_cache"

    id           = Column(BigInteger, primary_key=True, autoincrement=True)
    match_id     = Column(String(100), unique=True, nullable=False, index=True)
    fetched_at   = Column(TIMESTAMPTZ, server_default=func.now(), nullable=False)
    match_status = Column(String(20), nullable=False, default="pending")
    raw_data     = Column(JSONB, nullable=False)
    processed    = Column(Boolean, nullable=False, default=False)
```

---

## 5. 초기화 SQL (`backend/db/init.sql`)

```sql
-- ValoPredictML DB 초기화
-- 실행: psql -U postgres -d valo_predict -f backend/db/init.sql

CREATE TABLE IF NOT EXISTS predictions (
    id                 BIGSERIAL PRIMARY KEY,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    map                VARCHAR(50)  NOT NULL,
    team_a_agents      JSONB        NOT NULL,
    team_b_agents      JSONB        NOT NULL,
    team_a_roles       JSONB        NOT NULL,
    team_b_roles       JSONB        NOT NULL,
    win_probability    DOUBLE PRECISION NOT NULL,
    confidence         DOUBLE PRECISION NOT NULL,
    confidence_level   VARCHAR(10)  NOT NULL
                       CHECK (confidence_level IN ('High', 'Medium', 'Low')),
    feature_importance JSONB
);

CREATE TABLE IF NOT EXISTS match_cache (
    id           BIGSERIAL PRIMARY KEY,
    match_id     VARCHAR(100) NOT NULL UNIQUE,
    fetched_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    match_status VARCHAR(20)  NOT NULL DEFAULT 'pending'
                 CHECK (match_status IN ('pending', 'processed', 'failed')),
    raw_data     JSONB        NOT NULL,
    processed    BOOLEAN      NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_predictions_created_at ON predictions (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_map        ON predictions (map);
CREATE INDEX IF NOT EXISTS idx_match_cache_match_id   ON match_cache (match_id);
CREATE INDEX IF NOT EXISTS idx_match_cache_status     ON match_cache (match_status);
```

---

## 6. 마이그레이션 전략

### 로컬 → Vercel Postgres 마이그레이션

```bash
# 1. 로컬 데이터 덤프
pg_dump -U postgres -d valo_predict --data-only -t predictions > predictions_backup.sql

# 2. Vercel Postgres에 스키마 생성
psql $POSTGRES_URL -f backend/db/init.sql

# 3. 데이터 복원 (선택)
psql $POSTGRES_URL -f predictions_backup.sql
```

---

## 7. 관련 문서

| 문서 | 내용 |
|---|---|
| [../02_file_structure/02_backend_files.md](../02_file_structure/02_backend_files.md) | database.py, models.py 코드 상세 |
| [05_deployment_architecture.md](05_deployment_architecture.md) | Vercel Postgres 연결 설정 |
