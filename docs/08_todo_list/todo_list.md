# 08. 전체 작업 Todo List

> 각 항목에는 **우선순위**, **참조 문서**, **구현 파일 경로**가 명시되어 있습니다.  
> 의존 관계가 있는 작업은 선행 작업 완료 후 진행하세요.

---

## 우선순위 기준

| 레벨 | 의미 |
|---|---|
| 🔴 Critical | 이것 없이는 다음 단계 불가 |
| 🟠 High | 핵심 기능, 조기 완료 권장 |
| 🟡 Medium | 품질/완성도 향상 |
| 🟢 Low | 부가 기능, 나중에 작업 가능 |

---

## Phase 0 — 환경 설정

| # | 작업 | 우선순위 | 참조 문서 | 구현 파일 |
|---|---|---|---|---|
| 0-1 | Python 가상환경 생성 (`python -m venv .venv`) | 🔴 Critical | `02_file_structure` | `.venv/` |
| 0-2 | `requirements.txt` 작성 (XGBoost, LightGBM, FastAPI, Optuna 등) | 🔴 Critical | `05_data_learning`, `06_model_test` | `requirements.txt` |
| 0-3 | `pip install -r requirements.txt` 실행 | 🔴 Critical | — | — |
| 0-4 | `.env` 파일 생성 (Kaggle API Key, DB 접속 정보, Riot API Key) | 🔴 Critical | `02_file_structure` | `.env`, `.env.example` |
| 0-5 | `kaggle.json` 설정 (`~/.kaggle/kaggle.json`) | 🔴 Critical | `07_data` | `~/.kaggle/kaggle.json` |
| 0-6 | PostgreSQL 데이터베이스 생성 및 테이블 초기화 | 🟠 High | `03_architecture` | `backend/db/init.sql` |
| 0-7 | Next.js 의존성 설치 (`cd valo_predict_system && npm install`) | 🟠 High | `09_web` | `valo_predict_system/package.json` |

---

## Phase 1 — 데이터 수집

| # | 작업 | 우선순위 | 참조 문서 | 구현 파일 |
|---|---|---|---|---|
| 1-1 | `dataload.py` 실행하여 Kaggle VCT 데이터셋 다운로드 | 🔴 Critical | `07_data` | `dataload.py` |
| 1-2 | 다운로드된 CSV 파일 구조 확인 (컬럼명, 행 수, 결측값) | 🔴 Critical | `07_data` | — (분석 작업) |
| 1-3 | HenrikDev API 키 발급 및 `.env`에 등록 | 🟠 High | `07_data` | `.env` |
| 1-4 | HenrikDev API 수집 스크립트 작성 (`collect_matches.py`) | 🟠 High | `07_data`, `04_data_processing` | `ml/collect_matches.py` |
| 1-5 | 수집된 원본 데이터를 `data/raw/` 디렉토리에 저장 | 🟠 High | `02_file_structure` | `data/raw/` |

**Phase 1 완료 기준:** `data/raw/` 에 최소 5,000건 이상의 매치 데이터 확보

---

## Phase 2 — 데이터 전처리

| # | 작업 | 우선순위 | 참조 문서 | 구현 파일 |
|---|---|---|---|---|
| 2-1 | 요원→역할군 매핑 딕셔너리 작성 (`AGENT_ROLE_MAP`) | 🔴 Critical | `07_data` | `ml/agent_roles.py` |
| 2-2 | 원본 데이터 로드 및 컬럼 표준화 함수 구현 | 🔴 Critical | `04_data_processing` | `ml/data_pipeline.py` |
| 2-3 | 중복 매치 제거 로직 구현 | 🔴 Critical | `04_data_processing` | `ml/data_pipeline.py` |
| 2-4 | 결측값 처리 로직 구현 (Unknown 처리, 행 제거 기준) | 🔴 Critical | `04_data_processing` | `ml/data_pipeline.py` |
| 2-5 | 플레이어 단위 → 매치 단위 집계 함수 구현 (`aggregate_to_match_level`) | 🔴 Critical | `04_data_processing` | `ml/data_pipeline.py` |
| 2-6 | 피처 엔지니어링 구현 (역할군 카운트, 차이 피처, 전략가 유무) | 🔴 Critical | `04_data_processing` | `ml/feature_engineer.py` |
| 2-7 | 맵 이름 Label Encoding 구현 및 저장 | 🔴 Critical | `04_data_processing` | `ml/feature_engineer.py`, `models/label_encoder_map.joblib` |
| 2-8 | Stratified K-Fold용 데이터 분할 (70/15/15) | 🟠 High | `04_data_processing` | `ml/data_pipeline.py` |
| 2-9 | 전처리된 데이터를 `data/processed/` 에 저장 | 🟠 High | `02_file_structure` | `data/processed/` |
| 2-10 | 데이터 검증 체크리스트 실행 (클래스 불균형 확인, 피처 분포 시각화) | 🟡 Medium | `04_data_processing` | `ml/validate_data.py` |

**Phase 2 완료 기준:** 15개 피처가 포함된 정제된 DataFrame이 `data/processed/train.csv` 에 저장됨

---

## Phase 3 — 모델 학습

| # | 작업 | 우선순위 | 참조 문서 | 구현 파일 |
|---|---|---|---|---|
| 3-1 | XGBoost 베이스라인 모델 학습 (기본 파라미터) | 🔴 Critical | `05_data_learning` | `ml/train.py` |
| 3-2 | LightGBM 베이스라인 모델 학습 (기본 파라미터) | 🔴 Critical | `05_data_learning` | `ml/train.py` |
| 3-3 | Optuna 하이퍼파라미터 탐색 구현 (XGBoost) | 🔴 Critical | `05_data_learning` | `ml/optimize.py` |
| 3-4 | Optuna 하이퍼파라미터 탐색 구현 (LightGBM) | 🔴 Critical | `05_data_learning` | `ml/optimize.py` |
| 3-5 | Stratified K-Fold (k=10) 교차검증 구현 | 🔴 Critical | `05_data_learning` | `ml/evaluate.py` |
| 3-6 | XGBoost + LightGBM Soft Voting 앙상블 구현 (60:40 가중치) | 🔴 Critical | `05_data_learning` | `ml/train.py` |
| 3-7 | 과적합 감지 로직 구현 (Train-Val 갭 ≤ 3pp 검사) | 🟠 High | `05_data_learning` | `ml/evaluate.py` |
| 3-8 | 최종 모델 저장 (`joblib` 직렬화) | 🔴 Critical | `05_data_learning` | `models/xgboost_model.joblib`, `models/lgbm_model.joblib` |
| 3-9 | 모델 메타데이터 저장 (`model_metadata.json`) | 🟠 High | `06_model_test` | `models/model_metadata.json` |
| 3-10 | 피처 중요도 시각화 및 저장 | 🟡 Medium | `05_data_learning` | `reports/feature_importance.png` |
| 3-11 | 학습 결과 리포트 생성 (정확도, F1, ROC-AUC 기록) | 🟡 Medium | `05_data_learning` | `reports/training_report.json` |

**Phase 3 완료 기준:**
- 검증 정확도 ≥ 80%
- F1 Score ≥ 0.78
- ROC-AUC ≥ 0.82
- Train-Val 갭 ≤ 3pp

---

## Phase 4 — FastAPI 백엔드 구축

| # | 작업 | 우선순위 | 참조 문서 | 구현 파일 |
|---|---|---|---|---|
| 4-1 | FastAPI 프로젝트 디렉토리 구조 생성 | 🔴 Critical | `02_file_structure`, `03_architecture` | `backend/` |
| 4-2 | `POST /predict` 엔드포인트 구현 | 🔴 Critical | `06_model_test` | `backend/routers/predict.py` |
| 4-3 | Pydantic 요청/응답 스키마 구현 (`PredictRequest`, `PredictResponse`) | 🔴 Critical | `06_model_test` | `backend/schemas/predict.py` |
| 4-4 | `PredictionService` 싱글톤 구현 (모델 로드 + 추론 로직) | 🔴 Critical | `06_model_test` | `backend/services/prediction_service.py` |
| 4-5 | `GET /agents` 엔드포인트 구현 | 🟠 High | `06_model_test`, `07_data` | `backend/routers/agents.py` |
| 4-6 | `GET /maps` 엔드포인트 구현 | 🟠 High | `06_model_test`, `07_data` | `backend/routers/maps.py` |
| 4-7 | `GET /history` 엔드포인트 구현 (PostgreSQL 조회) | 🟠 High | `06_model_test`, `03_architecture` | `backend/routers/history.py` |
| 4-8 | `GET /health` 엔드포인트 구현 | 🟡 Medium | `06_model_test` | `backend/main.py` |
| 4-9 | CORS 미들웨어 설정 (Vercel 도메인 + localhost 허용) | 🔴 Critical | `03_architecture`, `09_web` | `backend/main.py` |
| 4-10 | PostgreSQL DB 연결 및 예측 기록 저장 로직 구현 | 🟠 High | `03_architecture` | `backend/db/database.py`, `backend/db/models.py` |
| 4-11 | 에러 핸들러 등록 (422, 500, 503) | 🟠 High | `06_model_test` | `backend/main.py` |
| 4-12 | `uvicorn` 실행 확인 (`python -m uvicorn backend.main:app --reload`) | 🔴 Critical | `06_model_test` | — |
| 4-13 | Swagger UI (`/docs`) 접속 및 엔드포인트 동작 확인 | 🟠 High | `06_model_test` | — (검증 작업) |
| 4-14 | 응답시간 검증 (모든 예측 요청 ≤ 200ms) | 🟡 Medium | `06_model_test` | — |

**Phase 4 완료 기준:** `curl` 또는 Swagger UI에서 `/predict` 호출 시 정상 JSON 응답 반환

---

## Phase 5 — Next.js 프론트엔드 구축

| # | 작업 | 우선순위 | 참조 문서 | 구현 파일 |
|---|---|---|---|---|
| 5-1 | `NEXT_PUBLIC_API_URL` 환경변수 설정 (`.env.local`) | 🔴 Critical | `09_web` | `valo_predict_system/.env.local` |
| 5-2 | Tailwind CSS v4 발로란트 커스텀 컬러 테마 설정 | 🟠 High | `09_web` | `valo_predict_system/src/app/globals.css` |
| 5-3 | `src/lib/api.js` API 클라이언트 모듈 구현 | 🔴 Critical | `09_web` | `valo_predict_system/src/lib/api.js` |
| 5-4 | 공통 레이아웃 `layout.js` + `Navbar.js` 구현 | 🟠 High | `09_web` | `valo_predict_system/src/app/layout.js`, `src/components/layout/Navbar.js` |
| 5-5 | `MapSelector.js` 컴포넌트 구현 | 🔴 Critical | `09_web` | `src/components/predict/MapSelector.js` |
| 5-6 | `AgentCard.js` 컴포넌트 구현 (클릭 선택/해제, 선택 상태 표시) | 🔴 Critical | `09_web` | `src/components/predict/AgentCard.js` |
| 5-7 | `AgentPicker.js` 컴포넌트 구현 (역할 필터 + 그리드) | 🔴 Critical | `09_web` | `src/components/predict/AgentPicker.js` |
| 5-8 | `TeamSlot.js` 컴포넌트 구현 (선택된 5명 미리보기) | 🟠 High | `09_web` | `src/components/predict/TeamSlot.js` |
| 5-9 | `WinRateGauge.js` 구현 (Recharts RadialBarChart) | 🔴 Critical | `09_web` | `src/components/result/WinRateGauge.js` |
| 5-10 | `ConfidenceBadge.js` 구현 (high/medium/low 배지) | 🟠 High | `09_web` | `src/components/result/ConfidenceBadge.js` |
| 5-11 | `RoleRadarChart.js` 구현 (팀 A vs 팀 B 역할군 레이더) | 🟠 High | `09_web` | `src/components/result/RoleRadarChart.js` |
| 5-12 | `FeatureImportanceBar.js` 구현 (수평 바 차트) | 🟡 Medium | `09_web` | `src/components/result/FeatureImportanceBar.js` |
| 5-13 | `/predict` 페이지 전체 구현 (상태 관리 + API 연동) | 🔴 Critical | `09_web` | `src/app/predict/page.js` |
| 5-14 | `/` 메인 홈 페이지 구현 (소개 + 최근 예측 카드) | 🟠 High | `09_web` | `src/app/page.js` |
| 5-15 | `/history` 예측 기록 페이지 구현 (테이블 + 필터) | 🟡 Medium | `09_web` | `src/app/history/page.js` |
| 5-16 | `/analytics` 통계 분석 페이지 구현 | 🟢 Low | `09_web` | `src/app/analytics/page.js` |
| 5-17 | `next.config.js` 설정 (이미지 도메인, headers) | 🟠 High | `09_web` | `valo_predict_system/next.config.js` |
| 5-18 | `npm run dev` 실행 후 전체 UI 동작 확인 | 🔴 Critical | `09_web` | — |
| 5-19 | 반응형 레이아웃 검증 (모바일/태블릿/데스크톱) | 🟡 Medium | `09_web` | — |

**Phase 5 완료 기준:** `http://localhost:3000/predict` 에서 요원 선택 → 예측 → 결과 화면까지 정상 동작

---

## Phase 6 — 테스트 및 검증

| # | 작업 | 우선순위 | 참조 문서 | 구현 파일 |
|---|---|---|---|---|
| 6-1 | 정상 케이스 테스트 (균형 조합, 불균형 조합) | 🔴 Critical | `06_model_test` | — |
| 6-2 | 에러 케이스 테스트 (중복 요원, 잘못된 맵, 인원 초과) | 🔴 Critical | `06_model_test` | — |
| 6-3 | 신규/미지원 요원 입력 시 Unknown 처리 동작 확인 | 🟠 High | `06_model_test`, `07_data` | `ml/agent_roles.py` |
| 6-4 | 예측 응답시간 10회 측정 (모두 200ms 이내 확인) | 🟠 High | `06_model_test` | — |
| 6-5 | 맵별 예측 결과가 서로 다른지 확인 (맵 피처 효과 검증) | 🟡 Medium | `06_model_test` | — |
| 6-6 | PostgreSQL 예측 기록 저장 및 `/history` 조회 확인 | 🟠 High | `03_architecture`, `06_model_test` | — |
| 6-7 | FastAPI 재시작 시 모델 재로드 정상 동작 확인 | 🟡 Medium | `06_model_test` | — |

---

## Phase 7 — Vercel 배포

| # | 작업 | 우선순위 | 참조 문서 | 구현 파일 |
|---|---|---|---|---|
| 7-1 | `vercel.json` 작성 | 🔴 Critical | `09_web` | `valo_predict_system/vercel.json` |
| 7-2 | Vercel CLI 설치 및 프로젝트 연동 (`vercel link`) | 🔴 Critical | `09_web` | — |
| 7-3 | Vercel 대시보드에서 `NEXT_PUBLIC_API_URL` 환경변수 등록 | 🔴 Critical | `09_web` | — |
| 7-4 | 프로덕션 빌드 확인 (`npm run build`) | 🔴 Critical | `09_web` | — |
| 7-5 | `vercel --prod` 배포 실행 | 🔴 Critical | `09_web` | — |
| 7-6 | 배포된 URL에서 `/predict` 동작 확인 | 🔴 Critical | `09_web` | — |
| 7-7 | FastAPI 서버 외부 접근 가능하도록 포트 오픈 또는 VPS 배포 | 🟠 High | `03_architecture` | — |
| 7-8 | GitHub Actions CI/CD 파이프라인 구성 (선택) | 🟢 Low | `09_web` | `.github/workflows/deploy.yml` |

**Phase 7 완료 기준:** Vercel 배포 URL에서 외부 네트워크로 전체 기능 정상 동작

---

## 작업 순서 요약 (의존 관계)

```
Phase 0 (환경 설정)
  ↓
Phase 1 (데이터 수집)
  ↓
Phase 2 (전처리)         ← ml/agent_roles.py 먼저 완성
  ↓
Phase 3 (모델 학습)      ← data/processed/ 있어야 가능
  ↓
Phase 4 (FastAPI)        ← models/ 저장 완료 후 진행
  ↓
Phase 5 (Next.js)        ← FastAPI /predict 동작 확인 후 진행
  ↓
Phase 6 (테스트)         ← Phase 4+5 모두 완료 후
  ↓
Phase 7 (배포)           ← Phase 6 통과 후
```

---

## 전체 작업 수 요약

| Phase | 작업 수 | Critical | High | Medium | Low |
|---|---|---|---|---|---|
| 0 환경 설정 | 7 | 5 | 2 | 0 | 0 |
| 1 데이터 수집 | 5 | 1 | 4 | 0 | 0 |
| 2 전처리 | 10 | 6 | 3 | 1 | 0 |
| 3 모델 학습 | 11 | 5 | 3 | 3 | 0 |
| 4 FastAPI | 14 | 6 | 6 | 2 | 0 |
| 5 Next.js | 19 | 8 | 7 | 3 | 1 |
| 6 테스트 | 7 | 2 | 4 | 2 | 0 |
| 7 배포 | 8 | 6 | 1 | 0 | 1 |
| **합계** | **81** | **39** | **30** | **11** | **2** |
