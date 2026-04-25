# 02. 기술 스택 상세

## 1. 전체 스택 한눈에 보기

```
┌─────────────────────────────────────────────────────────────────┐
│                       ValoPredictML 스택                         │
│                                                                   │
│  [데이터 수집]        [ML 파이프라인]         [서빙]               │
│  Kaggle kagglehub  → pandas + scikit  →  FastAPI (Python)       │
│  HenrikDev API v4    XGBoost + LightGBM   PostgreSQL 18          │
│                       Optuna                                      │
│                                                                   │
│  [프론트엔드]                          [배포]                      │
│  Next.js 16 (App Router)              Vercel (프론트)             │
│  React 19, Tailwind v4                VPS/로컬 (백엔드)           │
│  Recharts 2.x                                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 백엔드 / ML 스택

### 2.1 Python 3.14+

- **역할:** 전체 ML 파이프라인 및 FastAPI 백엔드
- **선택 이유:** ML 생태계(scikit-learn, XGBoost, pandas)의 표준 언어
- **주요 사용처:** `ml/`, `backend/`

### 2.2 FastAPI 0.115+

- **역할:** ML 모델을 REST API로 서빙
- **선택 이유:**
  - Pydantic 기반 자동 타입 검증
  - Swagger UI 자동 생성 (`/docs`)
  - 비동기(async) 지원으로 고성능
  - uvicorn으로 경량 운영
- **주요 엔드포인트:** `POST /predict`, `GET /history`, `GET /agents`, `GET /maps`

### 2.3 XGBoost 2.x

- **역할:** 메인 분류 모델
- **선택 이유:**
  - 구조화 데이터(테이블형) 분류에서 최상위 성능
  - Early Stopping으로 과적합 자동 방지
  - 피처 중요도 내장
- **앙상블 가중치:** 60%
- **핵심 파라미터:** `n_estimators`, `max_depth`, `learning_rate`, `subsample`, `colsample_bytree`

### 2.4 LightGBM 4.x

- **역할:** 앙상블 서브 모델
- **선택 이유:**
  - XGBoost 대비 빠른 학습 속도 (Leaf-wise 분기)
  - 메모리 효율적 (히스토그램 기반)
  - 다양한 피처 상호작용 포착
- **앙상블 가중치:** 40%
- **핵심 파라미터:** `num_leaves`, `min_child_samples`, `feature_fraction`, `bagging_fraction`

### 2.5 scikit-learn 1.5+

- **역할:** 전처리, K-Fold 교차검증, 평가 지표
- **주요 사용 모듈:**
  - `StratifiedKFold`: 클래스 비율 유지 K-Fold
  - `LabelEncoder`: 맵 이름 인코딩
  - `classification_report`, `roc_auc_score`: 평가
  - `LogisticRegression`, `RandomForestClassifier`: 베이스라인

### 2.6 Optuna 3.x

- **역할:** 하이퍼파라미터 자동 최적화
- **선택 이유:**
  - TPE(Tree-structured Parzen Estimator) Sampler로 효율적 탐색
  - Pruner로 조기 종료 (불필요한 trial 방지)
  - 탐색 과정 시각화 지원
- **탐색 공간:** `max_depth`, `n_estimators`, `learning_rate`, `subsample`, `num_leaves` 등

### 2.7 pandas 2.x

- **역할:** 데이터 로드, 변환, 집계
- **주요 사용처:**
  - CSV 멀티파일 로드 및 concat
  - 경기 단위 집계 (`groupby`)
  - 결측값 처리 (`fillna`, `dropna`)

### 2.8 PostgreSQL 18.x

- **역할:** 예측 로그 및 경기 데이터 캐시 저장
- **선택 이유:**
  - Vercel Postgres 네이티브 지원
  - `JSONB` 타입으로 JSON 인덱싱 가능 (MySQL JSON 대비 우수)
  - `TIMESTAMPTZ`로 시간대 정보 보존
  - `BIGSERIAL`로 자동 증가 ID 관리
  - `CHECK` 제약으로 데이터 무결성 강화
- **연결:** SQLAlchemy + psycopg2 (`postgresql+psycopg2://`)
- **테이블:** `predictions`, `match_cache`

### 2.9 SQLAlchemy 2.x

- **역할:** Python ORM (Object-Relational Mapping)
- **선택 이유:**
  - Raw SQL 없이 Python 코드로 DB 조작 (SQL Injection 방지)
  - 세션 관리 자동화
  - 마이그레이션 도구(Alembic)와 연동 용이

### 2.10 joblib

- **역할:** 학습된 모델 직렬화/역직렬화
- **사용법:**
  ```python
  import joblib
  joblib.dump(model, "models/xgboost_model.joblib")  # 저장
  model = joblib.load("models/xgboost_model.joblib")  # 로드
  ```

### 2.11 kagglehub

- **역할:** Kaggle 데이터셋 다운로드 자동화
- **사용법:**
  ```python
  import kagglehub
  path = kagglehub.dataset_download("ryanluong1/valorant-champion-tour-2021-2023-data")
  ```
- **인증:** `~/.kaggle/kaggle.json` 필요

---

## 3. 프론트엔드 스택

### 3.1 Next.js 16.2.4

- **역할:** React 기반 풀스택 프레임워크
- **선택 이유:**
  - App Router로 파일 기반 라우팅 (코드 구조 명확)
  - Server Components + Client Components 혼용 가능
  - Vercel 네이티브 지원 (자동 최적화 배포)
  - Image 최적화, 자동 코드 분할
- **라우팅 구조:**
  - `/` — 홈 대시보드
  - `/predict` — 승률 예측
  - `/analytics` — 통계 분석
  - `/history` — 예측 기록

### 3.2 React 19.2.4

- **역할:** UI 컴포넌트 라이브러리
- **주요 사용 패턴:**
  - `useState`: 요원 선택 상태 관리
  - `useEffect`: 컴포넌트 마운트 시 데이터 페칭
  - `Suspense`: 로딩 상태 처리

### 3.3 Tailwind CSS 4.x

- **역할:** 유틸리티 기반 스타일링
- **선택 이유:**
  - CSS 파일 없이 HTML에 직접 스타일 적용
  - 발로란트 브랜드 컬러 커스터마이징 용이
  - 반응형 레이아웃 빠른 구현 (`sm:`, `md:`, `lg:`)
- **규칙:** JSX에 직접 Tailwind 유틸리티 금지 → `.module.css`에서 `@apply`만 사용
- **커스텀 색상:**
  ```css
  /* globals.css */
  --valo-red: #FF4655
  --valo-dark: #0F1923
  --valo-gray: #1F2937
  --valo-accent: #FF6B35
  ```

### 3.4 SWR 2.x

- **역할:** API 데이터 페칭 및 캐싱
- **선택 이유:**
  - stale-while-revalidate 전략으로 UX 향상
  - 자동 재시도, 에러 처리 내장
  - 뮤테이션으로 예측 요청 후 즉시 UI 갱신

### 3.5 Recharts 2.x

- **역할:** 데이터 시각화 차트
- **사용 차트:**
  - `RadialBarChart`: 승률 게이지 (WinRateGauge)
  - `RadarChart`: 역할군 분포 비교 (RoleRadarChart)
  - `BarChart`: 피처 중요도 (FeatureImportanceBar)
  - `LineChart`: 통계 트렌드 (AnalyticsPage)

---

## 4. 배포 / 인프라 스택

### 4.1 Vercel

- **역할:** Next.js 프론트엔드 배포
- **선택 이유:**
  - Next.js 공식 권장 배포 플랫폼
  - GitHub 연동 자동 배포 (push → 자동 빌드)
  - Vercel Postgres 통합 (PostgreSQL 18 호스팅)
  - 전 세계 CDN 자동 적용
- **환경변수:** Vercel 대시보드에서 관리 (`NEXT_PUBLIC_API_URL`, `POSTGRES_URL` 등)

### 4.2 uvicorn

- **역할:** FastAPI ASGI 서버
- **실행 방법:**
  ```bash
  python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
  ```

---

## 5. 의존성 파일

### 5.1 Python (`requirements.txt`)

```
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
python-dotenv>=1.0.0
pydantic>=2.0.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
xgboost>=2.0.0
lightgbm>=4.0.0
scikit-learn>=1.5.0
optuna>=3.0.0
pandas>=2.0.0
numpy>=1.26.0
joblib>=1.3.0
kagglehub
requests>=2.31.0
```

### 5.2 Node.js (`valo_predict_system/package.json` 주요 의존성)

```json
{
  "dependencies": {
    "next": "16.2.4",
    "react": "19.2.4",
    "react-dom": "19.2.4",
    "recharts": "^2.0.0",
    "swr": "^2.0.0"
  },
  "devDependencies": {
    "@tailwindcss/postcss": "^4.0.0",
    "tailwindcss": "^4.0.0"
  }
}
```

---

## 6. 관련 문서

| 문서 | 내용 |
|---|---|
| [01_project_summary.md](01_project_summary.md) | 프로젝트 소개 및 핵심 아이디어 |
| [03_design_principles.md](03_design_principles.md) | 설계 원칙 |
| [../03_architecture/03_database_schema.md](../03_architecture/03_database_schema.md) | PostgreSQL 스키마 완전 정의 |
| [../05_data_learning/01_model_strategy.md](../05_data_learning/01_model_strategy.md) | 모델 비교표 및 채택 이유 |
