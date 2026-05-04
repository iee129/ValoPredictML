> ⚠️ **범위 외**: FastAPI 미사용. 본 프로젝트는 Streamlit 로컬 도구이며 API 엔드포인트 테스트는 적용되지 않는다. 본문은 참고용으로 보존된다.

# 03. 데이터베이스 성능 테스트

## 1. 목표

| 쿼리 유형 | 목표 실행시간 | 측정 방법 |
|---------|------------|---------|
| INSERT (예측 저장) | < 10ms | EXPLAIN ANALYZE |
| SELECT 기본 조회 | < 20ms | EXPLAIN ANALYZE |
| SELECT 맵 필터 + 정렬 | < 30ms | EXPLAIN ANALYZE |
| SELECT COUNT(*) | < 10ms | EXPLAIN ANALYZE |
| SELECT 100건 페이지네이션 | < 50ms | EXPLAIN ANALYZE |

---

## 2. predictions 테이블 구조 및 인덱스

```sql
-- 테이블 생성
CREATE TABLE predictions (
    id              SERIAL PRIMARY KEY,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    map             VARCHAR(50) NOT NULL,
    team_a_agents   TEXT[] NOT NULL,
    team_b_agents   TEXT[] NOT NULL,
    win_probability FLOAT NOT NULL,
    confidence      VARCHAR(10) NOT NULL
);

-- 인덱스 1: 최신순 조회 (기본 정렬)
CREATE INDEX idx_predictions_id_desc
    ON predictions (id DESC);

-- 인덱스 2: 맵 필터링
CREATE INDEX idx_predictions_map
    ON predictions (map);

-- 인덱스 3: 맵 필터 + 최신순 복합 인덱스
CREATE INDEX idx_predictions_map_id
    ON predictions (map, id DESC);

-- 인덱스 4: 날짜 기반 조회 (향후 확장용)
CREATE INDEX idx_predictions_created_at
    ON predictions (created_at DESC);
```

---

## 3. EXPLAIN ANALYZE로 쿼리 성능 측정

### 3.1 기본 최신 20건 조회

```sql
EXPLAIN ANALYZE
SELECT id, created_at, map, team_a_agents, team_b_agents, win_probability, confidence
FROM predictions
ORDER BY id DESC
LIMIT 20 OFFSET 0;
```

**인덱스 전 (예상 플랜)**
```
Seq Scan on predictions  (cost=0.00..185.00 rows=10000 width=180)
  Sort  (cost=185.00..210.00 rows=10000)
Planning Time: 0.5ms
Execution Time: 45.2ms   ← 느림
```

**인덱스 후 (예상 플랜)**
```
Index Scan using idx_predictions_id_desc on predictions
  (cost=0.42..8.53 rows=20 width=180)
Planning Time: 0.3ms
Execution Time: 0.8ms    ← 빠름
```

---

### 3.2 맵 필터링 조회

```sql
EXPLAIN ANALYZE
SELECT id, created_at, map, team_a_agents, team_b_agents, win_probability, confidence
FROM predictions
WHERE map = 'Ascent'
ORDER BY id DESC
LIMIT 20 OFFSET 0;
```

**복합 인덱스 적용 후 (예상)**
```
Index Scan using idx_predictions_map_id on predictions
  (cost=0.42..4.21 rows=12 width=180)
  Index Cond: (map = 'Ascent')
Planning Time: 0.2ms
Execution Time: 0.5ms
```

---

### 3.3 COUNT(*) 쿼리

```sql
-- 전체 건수
EXPLAIN ANALYZE
SELECT COUNT(*) FROM predictions;

-- 맵 필터 건수
EXPLAIN ANALYZE
SELECT COUNT(*) FROM predictions WHERE map = 'Ascent';
```

---

### 3.4 INSERT 성능

```sql
EXPLAIN ANALYZE
INSERT INTO predictions (map, team_a_agents, team_b_agents, win_probability, confidence)
VALUES (
    'Ascent',
    ARRAY['Jett','Sova','Viper','Killjoy','Skye'],
    ARRAY['Reyna','Breach','Omen','Cypher','Fade'],
    0.673,
    'medium'
)
RETURNING id;
```

---

## 4. 인덱스 효과 측정 스크립트

```sql
-- 인덱스 사용 현황 확인
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan AS scans,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched
FROM pg_stat_user_indexes
WHERE tablename = 'predictions'
ORDER BY idx_scan DESC;
```

```sql
-- 테이블 통계
SELECT
    n_live_tup AS live_rows,
    n_dead_tup AS dead_rows,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
WHERE relname = 'predictions';
```

---

## 5. 대용량 데이터 삽입 및 성능 측정

### 5.1 테스트 데이터 생성

```python
# scripts/seed_test_data.py
"""대용량 테스트 데이터를 predictions 테이블에 삽입합니다."""
import os
import random
import psycopg2
from datetime import datetime, timedelta

MAPS = ["Ascent","Bind","Haven","Split","Icebox","Breeze","Fracture","Pearl","Lotus","Sunset","Abyss"]
AGENTS = [
    "Jett","Reyna","Neon","Yoru","Phoenix","Iso","Waylay",
    "Sova","Breach","Skye","Fade","Gekko","KAY/O","Tejo",
    "Viper","Omen","Brimstone","Astra","Harbor","Clove",
    "Killjoy","Cypher","Sage","Chamber","Deadlock","Vyse",
]

def generate_teams():
    selected = random.sample(AGENTS, 10)
    return selected[:5], selected[5:]

def seed(n: int = 10000):
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()

    print(f"Seeding {n} records...")
    batch = []
    for i in range(n):
        map_name = random.choice(MAPS)
        team_a, team_b = generate_teams()
        win_prob = round(random.uniform(0.3, 0.7), 4)
        confidence = "high" if abs(win_prob-0.5) >= 0.2 else ("medium" if abs(win_prob-0.5) >= 0.1 else "low")
        created_at = datetime.now() - timedelta(days=random.randint(0, 365))

        batch.append((map_name, team_a, team_b, win_prob, confidence, created_at))

        if len(batch) == 1000:
            cur.executemany(
                "INSERT INTO predictions (map, team_a_agents, team_b_agents, win_probability, confidence, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                batch
            )
            conn.commit()
            batch = []
            print(f"  {i+1}/{n} 완료")

    if batch:
        cur.executemany(
            "INSERT INTO predictions (map, team_a_agents, team_b_agents, win_probability, confidence, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            batch
        )
        conn.commit()

    cur.close()
    conn.close()
    print(f"Seeding 완료: {n}건")

if __name__ == "__main__":
    seed(10000)
```

```bash
DATABASE_URL=postgresql://valopred:secret@localhost:5432/valopredml_test \
  python scripts/seed_test_data.py
```

---

### 5.2 대용량 쿼리 성능 비교

```bash
#!/bin/bash
# scripts/db_benchmark.sh

PG_CMD="psql $DATABASE_URL -c"

echo "=== DB 성능 벤치마크 ==="

# 현재 레코드 수
TOTAL=$($PG_CMD "SELECT COUNT(*) FROM predictions;" -t | xargs)
echo "현재 레코드 수: $TOTAL건"

echo ""
echo "--- 쿼리 실행 시간 ---"

# 1. 전체 COUNT
echo -n "[1] COUNT(*): "
$PG_CMD "EXPLAIN ANALYZE SELECT COUNT(*) FROM predictions;" 2>&1 \
  | grep "Execution Time" | awk '{print $3, $4}'

# 2. 최신 20건
echo -n "[2] 최신 20건 SELECT: "
$PG_CMD "EXPLAIN ANALYZE SELECT * FROM predictions ORDER BY id DESC LIMIT 20;" 2>&1 \
  | grep "Execution Time" | awk '{print $3, $4}'

# 3. 맵 필터 COUNT
echo -n "[3] Ascent COUNT: "
$PG_CMD "EXPLAIN ANALYZE SELECT COUNT(*) FROM predictions WHERE map='Ascent';" 2>&1 \
  | grep "Execution Time" | awk '{print $3, $4}'

# 4. 맵 필터 + 정렬
echo -n "[4] Ascent 최신 20건: "
$PG_CMD "EXPLAIN ANALYZE SELECT * FROM predictions WHERE map='Ascent' ORDER BY id DESC LIMIT 20;" 2>&1 \
  | grep "Execution Time" | awk '{print $3, $4}'

# 5. INSERT
echo -n "[5] INSERT 1건: "
$PG_CMD "EXPLAIN ANALYZE INSERT INTO predictions (map,team_a_agents,team_b_agents,win_probability,confidence) VALUES ('Ascent','{Jett,Sova}','{Reyna,Breach}',0.5,'low') RETURNING id;" 2>&1 \
  | grep "Execution Time" | awk '{print $3, $4}'
```

---

## 6. SQLAlchemy 쿼리 최적화

### 6.1 N+1 문제 방지

```python
# 나쁜 예: N+1 쿼리
predictions = db.query(Prediction).all()
for p in predictions:
    print(p.map)  # 각 접근마다 쿼리 발생 (관계 있을 경우)

# 좋은 예: 필요한 컬럼만 선택
predictions = db.query(
    Prediction.id,
    Prediction.map,
    Prediction.win_probability,
    Prediction.confidence,
    Prediction.created_at,
).order_by(Prediction.id.desc()).limit(20).all()
```

### 6.2 커넥션 풀 설정

```python
# backend/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
import os

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(
    DATABASE_URL,
    pool_size=10,          # 기본 커넥션 수
    max_overflow=20,       # 추가 허용 커넥션
    pool_pre_ping=True,    # 연결 유효성 사전 확인
    pool_recycle=3600,     # 1시간마다 커넥션 재생성
    connect_args={
        "connect_timeout": 10,
        "application_name": "valopredml",
    }
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

## 7. 인덱스 적용 전후 성능 비교표

10,000건 기준 예상 측정값:

| 쿼리 | 인덱스 없음 | 인덱스 적용 | 개선율 |
|------|-----------|-----------|-------|
| SELECT 최신 20건 | 45ms | 0.8ms | 98% |
| SELECT WHERE map=X | 30ms | 0.5ms | 98% |
| SELECT COUNT(*) | 8ms | 2ms | 75% |
| SELECT COUNT(*) WHERE map=X | 15ms | 1ms | 93% |
| INSERT 1건 | 2ms | 3ms | -50% (인덱스 유지 비용) |

> INSERT 성능이 소폭 저하되지만, 읽기 패턴이 훨씬 많으므로 허용 가능합니다.

---

## 8. Vercel Postgres 특이사항

Vercel Postgres (Neon 기반) 사용 시 추가 고려사항:

```python
# Neon 서버리스 — 커넥션 풀링 필수
# DATABASE_URL에 ?sslmode=require 포함 필요

DATABASE_URL = os.environ["POSTGRES_URL"]  # Vercel 환경변수 이름

# pgbouncer 모드 사용 (Neon 권장)
engine = create_engine(
    DATABASE_URL + "?options=endpoint%3D" + os.environ.get("PGHOST", ""),
    pool_size=1,        # 서버리스: 최소 풀
    max_overflow=0,
    pool_pre_ping=True,
)
```

```bash
# Vercel Postgres 쿼리 로그 확인
vercel env pull .env.local
psql $POSTGRES_URL -c "SELECT * FROM predictions LIMIT 5;"
```
