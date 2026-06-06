# 06. 예측 히스토리 & PostgreSQL DB

## 1. 설계 원칙 — Graceful 선택적 DB

DB(`VALO_DATABASE_URL`) 환경변수가 없으면 `HistoryUnavailable` 예외가 발생하고, 라우터가 503을 반환한다. **예측 자체(`/predict`)는 DB 유무와 무관하게 항상 동작한다.** DB는 "예측 결과를 저장하고 나중에 조회하는" 선택적 기능이다.

---

## 2. 테이블 스키마 (`prediction_history`)

SQLAlchemy Core 사용(ORM 아님). `init_store()` 호출 시 테이블이 없으면 자동 생성(`CREATE TABLE IF NOT EXISTS`).

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | TEXT PRIMARY KEY | UUID v4 (저장 시 생성) |
| `created_at` | DATETIME(timezone=True) | 저장 시각, 인덱스 있음 |
| `map` | TEXT | 예측에 사용한 맵명, 인덱스 있음 |
| `cutoff_year` | INTEGER | 기준 연도, 인덱스 있음 |
| `predicted_winner` | TEXT | `"A"` 또는 `"B"` |
| `confidence` | FLOAT | 확신도 (`abs(prob_a - 0.5) * 2`) |
| `team_a_name` | TEXT | 팀 A 식별자 (커스텀="A팀") |
| `team_b_name` | TEXT | 팀 B 식별자 |
| `team_a_win_probability` | FLOAT | 팀 A 승률 |
| `team_b_win_probability` | FLOAT | 팀 B 승률 (`= 1 - team_a`) |
| `request_json` | JSONB | 원본 예측 요청 전체 |
| `response_json` | JSONB | 원본 예측 응답 전체 |

---

## 3. 환경변수

| 변수 | 우선순위 | 예시 |
|------|---------|------|
| `VALO_DATABASE_URL` | 1순위 | `postgresql+psycopg2://valopred:valopred_secret@127.0.0.1:5433/valopredictml` |
| `DATABASE_URL` | 2순위(fallback) | 동일 형식 |

URL은 내부에서 `postgresql+psycopg2://`로 정규화한다(`postgres://`도 수용).

---

## 4. Docker Compose 설정 (`docker-compose.yml`)

```yaml
services:
  postgres:
    image: postgres:18-alpine
    environment:
      POSTGRES_USER: valopred
      POSTGRES_PASSWORD: valopred_secret
      POSTGRES_DB: valopredictml
    ports:
      - "5433:5432"    # 로컬 5432 충돌 방지
    volumes:
      - pg_data:/var/lib/postgresql/data

volumes:
  pg_data:
```

호스트 포트 `5433`을 쓰는 이유: 로컬에 이미 PostgreSQL이 떠 있는 경우 포트 충돌을 막기 위해.

---

## 5. 엔진 초기화 (`src/api/services/history.py`)

```python
@lru_cache(maxsize=1)
def engine() -> Engine | None:
    url = database_url()   # VALO_DATABASE_URL → DATABASE_URL 순서로 읽고 정규화
    if not url:
        return None        # URL 없으면 None 반환 (예외 아님)
    return create_engine(url, pool_pre_ping=True, future=True)

def _require_engine() -> Engine:
    eng = engine()
    if eng is None:
        raise HistoryUnavailable("VALO_DATABASE_URL 또는 DATABASE_URL을 설정하세요.")
    return eng

def init_store() -> bool:
    eng = engine()
    if eng is None:
        logger.info("prediction history skipped: database URL is not configured")
        return False
    metadata.create_all(eng)   # CREATE TABLE IF NOT EXISTS
    return True
```

`engine()`은 URL 미설정 시 예외 대신 `None`을 반환한다. 예외(`HistoryUnavailable`)는 실제 DB 호출이 필요한 `_require_engine()`에서 발생한다. `init_store()`는 `None`을 확인해 조용히 비활성화한다.

---

## 6. `save_prediction()` 흐름

```
POST /predict
  → predict_custom_lineup() → PredictionResult
  → serialize_prediction()  → response_dict
  → save_prediction(req, response_dict)
      ├─ engine() 호출 (lru_cache — 첫 호출만 연결)
      ├─ history_id = str(uuid4())  # 함수 내부에서 생성
      ├─ INSERT INTO prediction_history VALUES (...)
      └─ DB 미설정/오류 시 → 로깅 후 무시 (예측 응답에 영향 없음)
  → PredictResponse 반환 (history_id, created_at 필드 포함 또는 None)
```

`/predict` 응답의 `history_id`·`created_at`은 DB 저장에 성공하면 값이, 실패(DB 미설정 포함)하면 `null`이 된다.

---

## 7. 엔드포인트

### `GET /history?limit=50&offset=0`

- `limit`: 1~200 (범위 초과 시 clamp)
- `offset`: 0 이상
- 응답: `HistoryListResponse`
- DB 미설정 → 503

### `GET /history/{history_id}`

- `history_id`: UUID 문자열
- 없는 ID → 404
- DB 미설정 → 503

---

## 8. 에러 코드 정리

| 상황 | HTTP | 원인 |
|------|------|------|
| DB 환경변수 미설정 | 503 | `HistoryUnavailable` |
| DB 서버 다운 | 503 | 연결 실패 → `HistoryUnavailable` |
| 없는 `history_id` | 404 | 조회 결과 없음 |
| `limit` 초과 | — | 서버가 1~200으로 clamp (에러 없음) |

---

## 9. 관련 문서

- 엔드포인트 전체 목록 → [03_endpoints.md](03_endpoints.md)
- 스키마(HistoryItem 등) → [04_schemas.md](04_schemas.md)
- 실행·환경변수 → [05_run_and_cors.md](05_run_and_cors.md)
- 시연 런북 → [../04_integration/02_demo_runbook.md](../04_integration/02_demo_runbook.md)
