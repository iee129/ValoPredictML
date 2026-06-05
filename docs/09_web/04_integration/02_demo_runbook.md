# 02. 시연 런북

처음부터 끝까지 모델 시연을 띄우는 순서. 산출물은 모두 로컬(`.gitignore`)이므로 학습 파이프라인을 먼저 돌려야 한다.

---

## 0. 사전 조건

```bash
cd ValoPredictML
source .venv/bin/activate
pip install -r requirements.txt
pip install "fastapi>=0.115.0" "uvicorn[standard]>=0.30.0"
```

---

## 1. 데이터 · 모델 산출물 생성

```bash
# (1) Kaggle 데이터 다운로드 (~/.kaggle/kaggle.json 필요)
python dataload.py

# (2) Kaggle raw → data/processed/{matches,players}.csv
#     ※ 이 변환 스크립트는 gitignore된 scripts/에 있을 수 있음(저장소 미포함).
#       없으면 팀에 요청하거나 해당 단계 재현 필요.

# (3) advanced 피처 생성 → data/processed/adv_kaggle_only/
python -m ml.baseline.preprocess --feature-contract advanced

# (4) advanced 앙상블 학습/평가/검증
python -m ml.advanced.ensemble  --input data/processed/adv_kaggle_only --output models/advanced --reports reports/adv_kaggle_only
python -m ml.advanced.evaluate  --input data/processed/adv_kaggle_only --models models/advanced --reports reports/adv_kaggle_only
python -m ml.advanced.validate  --reports reports/adv_kaggle_only --models models/advanced

# (5) 인사이트 사전 집계 (요원-맵 적합도 N, 메타 조합 K) → reports/insights/*.json
python -m ml.insights.build_insights --input data/processed --output reports/insights
```

생성 확인:
```
models/advanced/ensemble.joblib, meta.json
reports/adv_kaggle_only/metrics.json, validation.json
data/processed/matches.csv, players.csv
data/processed/adv_kaggle_only/test.csv
```

> 빠른 점검: `python -m streamlit run app/main.py`로 기존 Streamlit 앱이 예측되면, 동일 산출물을 쓰는 FastAPI도 동작한다.

---

## 2. 백엔드 기동

```bash
# 저장소 루트에서 (api/ 패키지는 docs_web/02_backend_fastapi 기준 구현)
uvicorn valo_web_backend.main:app --reload --port 8000
```

검증:
```bash
curl http://localhost:8000/health         # {"status":"ok","n_features":125,...}
curl http://localhost:8000/model          # AUC/verdict
curl "http://localhost:8000/replay/matches?limit=5"
```

Swagger로 단독 데모도 가능: `http://localhost:8000/docs`.

---

## 3. 프론트 기동

```bash
cd valo_web_frontend
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm install
npm run dev      # http://localhost:3000
```

---

## 4. 시연 시나리오 (권장 순서)

| 순서 | 페이지 | 목적 | 콜드스타트 |
|------|--------|------|------------|
| 1 | `/model` | 신뢰도 먼저 — 125피처·test AUC·PASS verdict | 없음 |
| 2 | `/replay` | 실제 경기 예측 vs 결과(적중 배지) | 없음 |
| 3 | `/predict` | 임의 5v5 라인업으로 라이브 예측 | 첫 호출만 |

> `/predict` 첫 호출 콜드스타트를 숨기려면: 백엔드 `lifespan`에서 더미 라인업 1회 예측으로 캐시 워밍(→ [../02_backend_fastapi/02_model_serving.md](../02_backend_fastapi/02_model_serving.md) §2). 또는 시연 직전 `/predict`를 한 번 호출해 둔다.

> 가독성: 브라우저 전체화면(F11) + 100% 줌 + 1280×800↑ 권장. 한 화면 대시보드·색 규약은 [../07_styling/02_layout_demo_dashboard.md](../07_styling/02_layout_demo_dashboard.md), 시연 전 점검은 [../08_testing/01_test_strategy.md](../08_testing/01_test_strategy.md) §3 체크리스트.

---

## 5. 트러블슈팅

| 증상 | 원인 | 대응 |
|------|------|------|
| `/health` 503 | 모델/데이터 산출물 부재 | §1 재실행 |
| `/predict` 422 | 슬롯/중복/화이트리스트 위반 | `detail` 메시지(한국어) 확인 |
| `/predict` 첫 호출 느림 | 이전연도 이력 캐시 구축 | 워밍업 또는 replay 우선 |
| CORS 에러 | origin 불일치 | 백엔드 `allow_origins`에 `:3000` 추가 |
| 프론트가 빈 옵션 | `NEXT_PUBLIC_API_URL` 오설정 | `.env.local` 확인 후 재시작 |
| `n_features` 불일치 | 모델/계약 버전 불일치 | advanced 재학습(`ml.advanced.ensemble`) |

---

## 6. 관련 문서

- 실행/CORS → [../02_backend_fastapi/05_run_and_cors.md](../02_backend_fastapi/05_run_and_cors.md)
- 데이터 계약 → [01_data_contract.md](01_data_contract.md)
- 전체 ML 파이프라인 → 루트 `CLAUDE.md`, `README.md`
