# 01. 시스템 전체 개요

## 1. 3계층 아키텍처

ValoPredictML은 **ML 파이프라인 → FastAPI 백엔드 → Next.js 프론트엔드** 의 3계층 구조로 설계되었다.

```
┌─────────────────────────────────────────────────────────────┐
│                     클라이언트 레이어                          │
│                                                             │
│   ┌──────────────────────────────────────────────────┐     │
│   │         Next.js 16 (Vercel 배포)                 │     │
│   │   /predict  /analytics  /history  /           │     │
│   │   Recharts · Tailwind CSS v4 · CSS Modules     │     │
│   └──────────────────────────────────────────────────┘     │
│                         ↕ HTTPS / REST API                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    애플리케이션 레이어                         │
│                                                             │
│   ┌──────────────────────────────────────────────────┐     │
│   │         FastAPI 0.115+ (Python 3.11+)            │     │
│   │   POST /predict    GET /history                  │     │
│   │   GET /agents      GET /maps                     │     │
│   │   XGBoost + LightGBM 앙상블 예측                │     │
│   └──────────────────────────────────────────────────┘     │
│                         ↕ SQLAlchemy ORM                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     데이터 레이어                              │
│                                                             │
│   ┌─────────────────┐     ┌──────────────────────────┐    │
│   │  PostgreSQL 18  │     │  ML Pipeline (로컬 실행)  │    │
│   │  Vercel Postgres│     │  Kaggle → 전처리 → 학습  │    │
│   │  predictions 표 │     │  data/ → models/ 저장    │    │
│   └─────────────────┘     └──────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 계층별 책임

### 클라이언트 레이어 (Next.js)
- 요원 선택 UI 제공
- FastAPI REST API 호출
- 예측 결과 시각화 (Recharts)
- Vercel에 자동 배포

### 애플리케이션 레이어 (FastAPI)
- HTTP 요청 검증 (Pydantic)
- 피처 엔지니어링 (요청 시 실시간)
- XGBoost + LightGBM Soft Voting 앙상블
- 예측 결과 PostgreSQL 저장
- 예측 기록 조회

### 데이터 레이어
- **PostgreSQL 18**: 예측 기록, 캐시 저장
- **ML Pipeline**: 오프라인 학습, joblib 저장

---

## 3. 기술 스택 요약

| 계층 | 기술 | 버전 | 역할 |
|---|---|---|---|
| 프론트엔드 | Next.js | 16.2.4 | 웹 UI |
| 프론트엔드 | React | 19.2.4 | UI 컴포넌트 |
| 프론트엔드 | Tailwind CSS | v4 | 스타일링 |
| 프론트엔드 | Recharts | 2.x | 차트 시각화 |
| 백엔드 | FastAPI | 0.115+ | REST API |
| 백엔드 | Python | 3.11+ | 서버 언어 |
| 백엔드 | SQLAlchemy | 2.x | ORM |
| DB | PostgreSQL | 18.x | 예측 기록 |
| ML | XGBoost | 2.x | 분류 모델 |
| ML | LightGBM | 4.x | 분류 모델 |
| ML | Optuna | 3.x | 하이퍼파라미터 최적화 |
| 배포 | Vercel | — | Next.js 호스팅 |
| 패키지 | kagglehub | 최신 | 데이터 다운로드 |

---

## 4. 데이터 흐름 요약

```
[Kaggle 데이터셋]
        ↓ (kagglehub 다운로드)
  data/raw/*.csv
        ↓ (ml/data_pipeline.py)
  data/processed/train.csv, val.csv, test.csv
        ↓ (ml/optimize.py → ml/train.py)
  models/xgboost_model.joblib + lgbm_model.joblib
        ↓ (백엔드 시작 시 로드)
  FastAPI PredictionService
        ↓ (POST /api/v1/predict)
  Soft Voting → 승률 계산
        ↓ (PostgreSQL INSERT)
  predictions 테이블
        ↓ (GET /api/v1/history)
  Next.js 대시보드 시각화
```

---

## 5. 비기능 요구사항

| 항목 | 목표 | 전략 |
|---|---|---|
| 예측 정확도 | ≥ 80% Accuracy | Soft Voting 앙상블, Optuna 최적화 |
| 과적합 방지 | Train-Val 갭 < 3% | Early Stopping, 10-Fold CV |
| API 응답 시간 | < 200ms | 모델 싱글톤, 피처 연산 최소화 |
| 프론트엔드 배포 | Vercel 자동 배포 | GitHub 연동 |
| 데이터 무결성 | 중복 예측 기록 방지 | PostgreSQL UNIQUE 제약 |

---

## 6. 관련 문서

| 문서 | 내용 |
|---|---|
| [02_request_flow.md](02_request_flow.md) | 예측 요청 흐름 단계별 상세 |
| [03_database_schema.md](03_database_schema.md) | PostgreSQL 스키마 DDL |
| [04_api_design.md](04_api_design.md) | REST API 엔드포인트 스펙 |
| [05_deployment_architecture.md](05_deployment_architecture.md) | Vercel + 백엔드 배포 구조 |
| [06_ml_pipeline_architecture.md](06_ml_pipeline_architecture.md) | ML 파이프라인 상세 다이어그램 |
