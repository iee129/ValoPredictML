# 02. 시연 런북

처음부터 끝까지 모델 시연을 띄우는 순서. 산출물은 모두 로컬(`.gitignore`)이므로 학습 파이프라인을 먼저 돌려야 한다.

---

## 0. 사전 조건

```bash
cd ValoPredictML
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 0-1. PostgreSQL DB 활성화 (선택)

예측 히스토리(`/history`)를 사용하려면 PostgreSQL을 먼저 기동한다. 히스토리가 불필요하면 이 단계를 건너뛰어도 된다(예측·리플레이·모델 근거 기능에 영향 없음).

Docker Desktop 또는 Docker Compose CLI가 설치돼 있어야 한다.

```bash
# postgres 컨테이너만 기동 (앱은 별도 실행)
docker compose up -d postgres
```

`docker-compose.yml`은 `postgres:18-alpine`과 named volume을 쓴다. 로컬에 이미 PostgreSQL이 떠 있는 경우를 피하려고 호스트 포트는 `5433`으로 열어 둔다.

백엔드 실행 전 `VALO_DATABASE_URL` 환경변수를 설정한다:

```bash
export VALO_DATABASE_URL=postgresql+psycopg2://valopred:valopred_secret@127.0.0.1:5433/valopredictml
```

`init_store()`가 앱 시작 시 `prediction_history` 테이블을 자동 생성한다. 환경변수 없이 실행하면 `/history`만 503을 반환하고 나머지는 정상 동작한다.

---

## 1. 데이터 · 모델 산출물 생성

```bash
# (1) Kaggle 데이터 다운로드 (~/.kaggle/kaggle.json 필요)
python -m data.dataload

# (2) Kaggle raw → data/processed/{matches,players}.csv
#     ※ 이 변환 스크립트는 gitignore된 scripts/에 있을 수 있음(저장소 미포함).
#       없으면 팀에 요청하거나 해당 단계 재현 필요.

# (3) baseline reference artifact 생성 → reports/baseline/, models/baseline/meta.json
python -m ml.baseline.reference

# (4) advanced 시간순 피처 생성 → data/processed/advanced/
python -m features.chrono_preprocess --include-vlrgg

# (5) advanced 앙상블 학습/평가/검증
python -m ml.advanced.ensemble
python -m ml.advanced.evaluate
python -m ml.advanced.validate

# (6) 인사이트 사전 집계 (요원-맵 적합도 N, 메타 조합 K) → reports/insights/*.json
python -m insights.build_insights --input data/processed --output reports/insights
```

생성 확인:
```
models/advanced/ensemble.joblib, meta.json
reports/advanced/metrics.json, validation.json
reports/baseline/metrics.json, validation.json
data/processed/matches.csv, players.csv
data/processed/advanced/test.csv
```

> 빠른 점검: `uvicorn api.main:app`으로 FastAPI를 띄우고 `/health`·`/predict`가 응답하면, 동일 산출물을 쓰는 추론 로직(`src/inference/predict.py`)이 정상이다.

---

## 2. 백엔드 기동

```bash
# 저장소 루트에서 (api/ 패키지는 docs/08_web/02_backend_fastapi 기준 구현)
export VALO_DATABASE_URL=postgresql+psycopg2://valopred:valopred_secret@127.0.0.1:5433/valopredictml
uvicorn api.main:app --reload --port 8000
```

검증:
```bash
curl http://localhost:8000/health         # {"status":"ok","n_features":179,...}
curl http://localhost:8000/model          # AUC/verdict
curl "http://localhost:8000/replay/matches?limit=5"
```

Swagger로 단독 데모도 가능: `http://localhost:8000/docs`.

---

## 3. 프론트 기동

```bash
cd web
echo "VALO_INTERNAL_API_URL=http://127.0.0.1:8000" > .env.local
npm install
npm run dev      # http://localhost:3000
```

---

## 4. 시연 시나리오 (권장 순서)

| 순서 | 페이지 | 목적 | 콜드스타트 |
|------|--------|------|------------|
| 1 | `/model` | 신뢰도 먼저 — 179피처·test AUC·신뢰 가능 verdict | 없음 |
| 2 | `/replay` | 실제 경기 예측 vs 결과(적중 배지) | 없음 |
| 3 | `/` | 임의 5v5 라인업으로 라이브 예측 + 히스토리 저장 | 첫 호출만 |
| 4 | `/history` | PostgreSQL에 저장된 예측 결과 재조회 | 없음 |

> `/predict` 첫 호출 콜드스타트를 숨기려면: 백엔드 `lifespan`에서 더미 라인업 1회 예측으로 캐시 워밍(→ [../02_backend_fastapi/02_model_serving.md](../02_backend_fastapi/02_model_serving.md) §2). 또는 시연 직전 `/predict`를 한 번 호출해 둔다.

> 가독성: 브라우저 전체화면(F11) + 100% 줌 + 1280×800↑ 권장. 한 화면 대시보드·색 규약은 [../07_styling/02_layout_demo_dashboard.md](../07_styling/02_layout_demo_dashboard.md), 시연 전 점검은 [../08_testing/01_test_strategy.md](../08_testing/01_test_strategy.md) §3 체크리스트.

---

## 5. 트러블슈팅

| 증상 | 원인 | 대응 |
|------|------|------|
| `/health` 503 | 모델/데이터 산출물 부재 | §1 재실행 |
| `/predict` 422 | 슬롯/중복/화이트리스트 위반 | `detail` 메시지(한국어) 확인 |
| `/predict` 첫 호출 느림 | 이전연도 이력 캐시 구축 | 워밍업 또는 replay 우선 |
| `/history` 503 | PostgreSQL 미기동 또는 `VALO_DATABASE_URL` 누락 | `docker compose up -d postgres`, 환경변수 확인 |
| CORS 에러 | origin 불일치 | 백엔드 `allow_origins`에 `:3000` 추가 |
| 프론트가 빈 옵션 | `VALO_INTERNAL_API_URL` 오설정 | `web/.env.local` 확인 후 재시작 |
| `n_features` 불일치 | 모델/계약 버전 불일치 | advanced 재학습(`ml.advanced.ensemble`) |

참고: Docker Compose는 서비스와 볼륨을 파일로 정의하는 도구이고, 공식 Postgres 이미지는 `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`로 초기 사용자와 DB를 만든다. 실제 배포에서는 같은 앱 코드에서 `VALO_DATABASE_URL`만 원격 PostgreSQL 주소로 바꾸면 된다.

---

## 6. 관련 문서

- 실행/CORS → [../02_backend_fastapi/05_run_and_cors.md](../02_backend_fastapi/05_run_and_cors.md)
- 데이터 계약 → [01_data_contract.md](01_data_contract.md)
- 전체 ML 파이프라인 → 루트 `CLAUDE.md`, `README.md`
