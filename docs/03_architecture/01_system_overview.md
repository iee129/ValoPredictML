# 01. 시스템 전체 개요

마지막 업데이트: 2026-05-04

## 1. 시스템 구조

ValoPredictML은 **ML 파이프라인 → FastAPI 백엔드 → Next.js 프런트엔드** 의 3계층 웹 구조로 설계되었다. (초기엔 Streamlit 로컬 UI 2계층이었으나 폐기됐고, 추론 로직만 `src/inference/predict.py`로 보존된다.)

> 클라우드 배포는 평가 범위 밖이다 — 로컬에서 FastAPI + Next.js를 실행해 시연한다.

```
┌─────────────────────────────────────────────────────────────┐
│                     UI 레이어                                │
│                                                             │
│   ┌──────────────────────────────────────────────────┐     │
│   │         Next.js 16 (web/, 로컬 실행)             │     │
│   │   - 선수/요원 조합 입력                           │     │
│   │   - 예측 결과 + 영향도 시각화 (React/Tailwind)    │     │
│   │   - Next Route Handler(/api) → FastAPI 프록시     │     │
│   └──────────────────────────────────────────────────┘     │
│                    HTTP (/api)                                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  백엔드 레이어 (FastAPI src/api)             │
│   src/inference/predict.py import → 예측 호출 + 직렬화        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    모델 레이어                                │
│                                                             │
│   ┌──────────────────────────────────────────────────┐     │
│   │   Feature Builder (src/domain/valorant.py 참조)           │     │
│   │   RF / XGBoost / LightGBM (앙상블)               │     │
│   │   SHAP / feature importance                      │     │
│   │   models/*.joblib (로컬 파일)                    │     │
│   └──────────────────────────────────────────────────┘     │
│                    SQLAlchemy Core (선택적)                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   데이터 레이어                               │
│                                                             │
│   ┌─────────────────┐     ┌──────────────────────────┐    │
│   │  PostgreSQL      │     │  ML Pipeline (로컬 실행) │    │
│   │  prediction_     │     │  Kaggle → 전처리 → 학습  │    │
│   │  history 테이블  │     │  data/ → models/ 저장    │    │
│   │  (선택적, grace) │     │                          │    │
│   └─────────────────┘     └──────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 계층별 책임

### UI 레이어 (Next.js `web`)
- 맵, 선수 5명 + 요원 5명 (팀당) 입력 UI 제공
- Next Route Handler(`/api`)를 통해 FastAPI 백엔드로 예측 요청
- 예측 결과 시각화 (React/Tailwind)
- 경기 다시보기, 모델 근거 화면

### 백엔드 레이어 (FastAPI `src/api`)
- `src/inference/predict.py`를 import해 예측 호출 후 결과를 JSON 직렬화
- 라우터: `predict`/`replay`/`options`/`model`/`insights`

### 모델 레이어
- 피처 벡터 생성 (baseline 421개 / advanced 179개)
- RF + XGBoost + LightGBM Soft Voting 앙상블 (가중치 2.0:3.0:0.1)
- 예측 결과 PostgreSQL 자동 저장 (`prediction_history`, 선택적 — DB 장애 시 예측 실패 없음)
- 예측 기록 조회 (`GET /history`)

### 데이터 레이어
- **Kaggle 원천 데이터**: `data/raw/kaggle/` (2.3GB, 5개 데이터셋)
- **ML Pipeline**: 오프라인 전처리 + 학습, joblib 저장
- **PostgreSQL**: `prediction_history` 테이블 (구현됨, 선택적 — `VALO_DATABASE_URL` 미설정 시 비활성)

---

## 3. 기술 스택 요약

| 계층 | 기술 | 버전 | 역할 |
|------|------|------|------|
| UI | Next.js / React | 16 / 19 | 시연 프런트엔드 (`web`) |
| UI | Tailwind | v4 | 스타일 |
| 백엔드 | FastAPI / uvicorn | 최신 | 모델 서빙 (`src/api`) |
| 언어 | Python | 3.14.4 | 전체 |
| 데이터 처리 | pandas | 2.x | 전처리 |
| 데이터 처리 | NumPy | 최신 | 수치 연산 |
| ML | Random Forest | scikit-learn 1.5+ | 앙상블 구성 |
| ML | XGBoost | 2.x | 앙상블 구성 |
| ML | LightGBM | 4.x | 앙상블 구성 |
| 설명 | feature_importances_ / 순열 중요도 | — | 예측 근거 (SHAP 미구현) |
| 모델 저장 | joblib | 최신 | 직렬화 |
| DB | PostgreSQL + SQLAlchemy Core | 구현됨(선택적) | 예측 기록 (`prediction_history`, `VALO_DATABASE_URL` 설정 시 활성) |

**범위 외**: Vercel/클라우드 배포, HenrikDev API, 딥러닝 프레임워크

---

## 4. 데이터 흐름

```
[Kaggle 데이터셋 5개] (data/raw/kaggle/, 2.3GB)
        ↓ src/data/raw_preprocess.py
  파싱 → 정규화 → 품질 검사 → dedup → 분할
        ↓ src/features/preprocess.py (baseline 421피처, 랜덤80:20) / src/features/chrono_preprocess.py (advanced 179피처, 시간순)
  data/processed/train.csv, test.csv
  data/processed/advanced/train.csv, test.csv
        ↓ src/ml/baseline/train.py (LR+DT soft voting) / src/ml/advanced/ensemble.py (RF+XGB+LGBM w=2.0:3.0:0.1)
  baseline: GroupKFold n=5 / advanced: 시간순 split
        ↓ src/ml/baseline/evaluate.py + src/ml/advanced/evaluate.py
  Baseline Test AUC=0.5943, Advanced Ensemble Test AUC=0.7010
        ↓ src/ml/baseline/validate.py / src/ml/advanced/validate.py
  models/baseline/model.joblib, models/advanced/ensemble.joblib (서빙용)
        ↓ web (Next.js) → src/api (FastAPI) → src/inference/predict.py
  사용자 입력 → 피처 빌드 → 앙상블 예측 → 승률 출력
        ↓ (선택적, graceful)
  PostgreSQL prediction_history 테이블 (VALO_DATABASE_URL 설정 시 자동 저장)
```

---

## 5. 현재 구현 상태

| 컴포넌트 | 상태 |
|----------|------|
| 데이터 수집 (`src/data/dataload.py`) | 완료 |
| raw 정제 (`src/data/raw_preprocess.py`) | 완료 |
| 전처리 파이프라인 (`src/features/preprocess.py`) | 완료 |
| 모델 학습 (`src/ml/baseline/train.py` / `src/ml/advanced/ensemble.py`) | 완료 (Baseline AUC=0.5943(랜덤) / Advanced Ensemble AUC=0.7010(시간순)) |
| 모델 평가 (`src/ml/baseline/evaluate.py` / `src/ml/advanced/evaluate.py`) | 완료 |
| SHAP 분석 (`src/ml/advanced/shap_analysis.py`) | 미구현 (현재 feature_importances_/휴리스틱 사용) |
| 메트릭 검증 (`src/ml/baseline/validate.py` / `src/ml/advanced/validate.py`) | 완료 |
| 추론 로직 (`src/inference/predict.py`) | 완료 (구 Streamlit `app/main.py` 폐기) |
| 웹 스택 (FastAPI `src/api` + Next.js `web`) | 완료 |
| PostgreSQL 예측 기록 (`prediction_history`) | 구현됨 (선택적 — `VALO_DATABASE_URL` 설정 시 활성, graceful) |

---

## 6. 관련 문서

| 문서 | 내용 |
|------|------|
| [02_request_flow.md](02_request_flow.md) | 예측 요청 흐름 단계별 상세 |
| [04_api_design.md](04_api_design.md) | API 설계 (HTTP 계약 SSOT는 `docs/08_web`) |
| [06_ml_pipeline_architecture.md](06_ml_pipeline_architecture.md) | ML 파이프라인 상세 다이어그램 |
