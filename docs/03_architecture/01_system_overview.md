# 01. 시스템 전체 개요

마지막 업데이트: 2026-05-04

## 1. 시스템 구조

ValoPredictML은 **ML 파이프라인 → Streamlit 로컬 UI** 의 단순 2계층 구조로 설계되었다.

**범위 외 (out of scope)**: FastAPI, Next.js, React, Vercel/클라우드 배포는 이 프로젝트에서 사용하지 않는다. REST API 서버 없이 Streamlit이 모델을 직접 호출한다.

```
┌─────────────────────────────────────────────────────────────┐
│                     UI 레이어                                │
│                                                             │
│   ┌──────────────────────────────────────────────────┐     │
│   │         Streamlit (로컬 실행)                     │     │
│   │   app/streamlit_app.py                           │     │
│   │   - 선수/요원 조합 입력                           │     │
│   │   - 예측 결과 + 영향도 시각화 (Plotly)            │     │
│   │   - 교체 시뮬레이션                               │     │
│   └──────────────────────────────────────────────────┘     │
│                    Python 함수 호출                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    모델 레이어                                │
│                                                             │
│   ┌──────────────────────────────────────────────────┐     │
│   │   Feature Builder (ml/agent_roles.py 참조)       │     │
│   │   RF / XGBoost / LightGBM (앙상블)               │     │
│   │   SHAP / feature importance                      │     │
│   │   models/*.joblib (로컬 파일)                    │     │
│   └──────────────────────────────────────────────────┘     │
│                    SQLAlchemy (후보)                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   데이터 레이어                               │
│                                                             │
│   ┌─────────────────┐     ┌──────────────────────────┐    │
│   │  PostgreSQL      │     │  ML Pipeline (로컬 실행) │    │
│   │  predictions 표  │     │  Kaggle → 전처리 → 학습  │    │
│   │  (후보, 미구현)  │     │  data/ → models/ 저장    │    │
│   └─────────────────┘     └──────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 계층별 책임

### UI 레이어 (Streamlit)
- 맵, 선수 5명 + 요원 5명 (팀당) 입력 UI 제공
- Python 함수 직접 호출로 예측 실행 (API 서버 없음)
- 예측 결과 시각화 (Plotly)
- 교체 시뮬레이션, 최적 조합 탐색

### 모델 레이어
- 피처 벡터 생성 (43개)
- RF + XGBoost + LightGBM Soft Voting 앙상블 (확률 평균)
- 예측 결과 PostgreSQL 저장 (후보)
- 예측 기록 조회 (후보)

### 데이터 레이어
- **Kaggle 원천 데이터**: `data/raw/kaggle/` (2.3GB, 7개 데이터셋)
- **ML Pipeline**: 오프라인 전처리 + 학습, joblib 저장
- **PostgreSQL**: 예측 기록 저장 후보 (미구현)

---

## 3. 기술 스택 요약

| 계층 | 기술 | 버전 | 역할 |
|------|------|------|------|
| UI | Streamlit | 최신 | 로컬 분석 도구 |
| UI | Plotly | 최신 | 시각화 (후보) |
| 언어 | Python | 3.14.4 | 전체 |
| 데이터 처리 | pandas | 2.x | 전처리 |
| 데이터 처리 | NumPy | 최신 | 수치 연산 |
| ML | Random Forest | scikit-learn 1.5+ | 앙상블 구성 |
| ML | XGBoost | 2.x | 앙상블 구성 |
| ML | LightGBM | 4.x | 앙상블 구성 |
| 설명 | SHAP / feature importance | — | 예측 근거 |
| 모델 저장 | joblib | 최신 | 직렬화 |
| DB | PostgreSQL + SQLAlchemy | 후보 | 예측 기록 (미구현) |

**범위 외**: FastAPI, uvicorn, Next.js, React, Tailwind, Recharts, Vercel, Optuna, HenrikDev API

---

## 4. 데이터 흐름

```
[Kaggle 데이터셋 7개] (data/raw/kaggle/, 2.3GB)
        ↓ ml/data_pipeline.py (구현 예정)
  파싱 → 정규화 → 품질 게이트 → dedup → 분할
        ↓
  data/processed/train.csv, val.csv, test.csv
        ↓ ml/train_model.py (구현 예정)
  RF + XGBoost + LightGBM 학습 (K-Fold K=5)
        ↓
  models/*.joblib
        ↓ app/streamlit_app.py (구현 예정)
  사용자 입력 → 피처 빌드 → 앙상블 예측 → 승률 출력
        ↓ (후보)
  PostgreSQL predictions 테이블
```

---

## 5. 현재 구현 상태

| 컴포넌트 | 상태 |
|----------|------|
| 데이터 수집 (`dataload.py`) | 완료 |
| 전처리 파이프라인 (`ml/data_pipeline.py`) | 미구현 |
| 모델 학습 (`ml/train_model.py`) | 미구현 |
| Streamlit UI (`app/streamlit_app.py`) | 미구현 |
| PostgreSQL 예측 기록 | 미구현 (후보) |

---

## 6. 관련 문서

| 문서 | 내용 |
|------|------|
| [02_request_flow.md](02_request_flow.md) | 예측 요청 흐름 단계별 상세 |
| [03_database_schema.md](03_database_schema.md) | PostgreSQL 스키마 DDL |
| [04_api_design.md](04_api_design.md) | 범위 외 (out of scope) 참조 |
| [05_deployment_architecture.md](05_deployment_architecture.md) | 범위 외 (out of scope) 참조 |
| [06_ml_pipeline_architecture.md](06_ml_pipeline_architecture.md) | ML 파이프라인 상세 다이어그램 |
