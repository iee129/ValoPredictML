# 02. 기술 스택 상세

마지막 업데이트: 2026-05-05

## 1. 전체 스택 한눈에 보기

```
┌─────────────────────────────────────────────────────────────────┐
│                       ValoPredictML 스택                         │
│                                                                   │
│  [데이터 수집]        [ML 파이프라인]         [웹 스택]           │
│  Kaggle kagglehub  → pandas + NumPy    →  FastAPI (src/api)     │
│  data/raw/kaggle/    scikit-learn           Next.js 16 (web)     │
│                       XGBoost + LightGBM    React 19 + Tailwind  │
│                       Random Forest                               │
│                                                                   │
│  [데이터 저장]                                                     │
│  PostgreSQL + SQLAlchemy (예측 기록, 선택적 — DB 없어도 동작)    │
└─────────────────────────────────────────────────────────────────┘
```

> 초기엔 Streamlit 로컬 앱으로 시연했으나 폐기됐고, 추론 로직만 `src/inference/predict.py`로 보존된다. 현행 시연은 FastAPI(`src/api`) + Next.js(`web`) 웹 스택이다. 클라우드 배포는 평가 범위 밖이다.

---

## 2. 백엔드 / ML 스택

### 2.1 Python 3.14.4

- **역할:** 전체 ML 파이프라인 및 FastAPI 백엔드
- **선택 이유:** ML 생태계(scikit-learn, XGBoost, pandas)의 표준 언어
- **주요 사용처:** `src/`(domain·data·features·ml·insights·inference·api)

### 2.2 pandas 2.x

- **역할:** 데이터 로드, 변환, 집계
- **주요 사용처:**
  - CSV 멀티파일 로드 및 concat
  - 경기 단위 집계 (`groupby`)
  - 결측값 처리 (`fillna`, `dropna`)

### 2.3 NumPy

- **역할:** 수치 연산, 배열 처리
- **주요 사용처:** 피처 벡터 생성, 가중치 계산

### 2.4 Random Forest (scikit-learn)

- **역할:** 앙상블 구성 모델 1
- **선택 이유:** 여러 결정 트리를 독립적으로 학습한 후 다수결로 예측 — 안정적인 baseline
- **앙상블 방식:** 세 모델 예측 확률 평균

### 2.5 XGBoost 2.x

- **역할:** 앙상블 구성 모델 2
- **선택 이유:**
  - 이전 트리의 오차를 다음 트리가 보정하며 반복 학습 — tabular 데이터에 강함
  - Early Stopping으로 과적합 자동 방지
  - 피처 중요도 내장
- **핵심 파라미터:** `n_estimators`, `max_depth`, `learning_rate`, `subsample`, `colsample_bytree`

### 2.6 LightGBM 4.x

- **역할:** 앙상블 구성 모델 3
- **선택 이유:**
  - XGBoost와 같은 방식이나 학습 속도가 빠르고 메모리 효율이 높음 (Leaf-wise 분기, 히스토그램 기반)
  - 다양한 피처 상호작용 포착
- **핵심 파라미터:** `num_leaves`, `min_child_samples`, `feature_fraction`, `bagging_fraction`

### 2.7 앙상블 작동 방식

```
RF 예측      → 팀 A 승률 0.62
XGBoost 예측 → 팀 A 승률 0.58
LightGBM 예측 → 팀 A 승률 0.65

최종 승률 = (0.62 + 0.58 + 0.65) / 3 = 0.617
```

### 2.8 scikit-learn 1.5+

- **역할:** 전처리, K-Fold 교차검증, 평가 지표
- **주요 사용 모듈:**
  - `GroupShuffleSplit`: match_key 단위로 같은 경기가 train/test에 겹치지 않도록 분할
  - `LabelEncoder`: 맵 이름 인코딩
  - `classification_report`, `roc_auc_score`: 평가
  - `RandomForestClassifier`: 앙상블 구성

### 2.9 웹 스택 (FastAPI + Next.js)

- **역할:** 모델 서빙 백엔드(FastAPI `src/api`) + 시연 프런트엔드(Next.js 16 `web`)
- **선택 이유:** 추론 로직(`src/inference/predict.py`)을 그대로 import해 동일 예측을 웹으로 서빙
- **시각화:** React 컴포넌트 + Tailwind v4
- **진입점:** `uvicorn api.main:app`(백엔드) / `web` Next.js(프런트). 구 Streamlit 앱은 폐기됨.

### 2.10 PostgreSQL + SQLAlchemy (구현됨, 선택적)

- **역할:** 예측 기록 자동 저장 (`prediction_history` 테이블)
- **선택 이유:**
  - SQLAlchemy Core로 Raw SQL 없이 Python 코드로 DB 조작
  - `JSONB` 타입(request_json, response_json)으로 JSON 인덱싱 가능
- **연결:** SQLAlchemy + psycopg2-binary (`postgresql+psycopg2://`)
- **테이블:** `prediction_history` (예측 기록)
- **환경변수:** `VALO_DATABASE_URL` 또는 `DATABASE_URL` (미설정 시 히스토리 비활성, 예측은 정상 동작)
- **docker-compose:** postgres:18-alpine, db=valopredictml, user=valopred, port=5433:5432
- **graceful 처리:** DB 장애 발생 시 경고 로그 후 계속 동작 — 예측 실패 야기하지 않음

### 2.11 피처 중요도 (현재 사용 중)

- **역할:** 피처별 예측 기여도 산출
- **현재 방식:** 트리 모델의 `feature_importances_` + `importance × value` 휴리스틱으로 자연어 근거를 만든다. 진짜 SHAP 분석은 아니다.
- **향후 계획:** SHAP TreeExplainer 기반 정밀 기여도 분석은 향후 확장 후보다.

### 2.12 하이퍼파라미터 (현재 사용 중)

- **현재 방식:** RF/XGBoost/LightGBM은 코드에 고정한 파라미터로 학습한다. **Optuna 자동 튜닝은 현재 사용하지 않는다.**
- **향후 계획:** Optuna 기반 HPO(TPESampler, ROC-AUC 최적화)는 향후 확장 후보다.

### 2.13 joblib

- **역할:** 학습된 모델 직렬화/역직렬화
- **사용법:**
  ```python
  import joblib
  joblib.dump(model, "models/advanced/rf.joblib")   # 저장
  model = joblib.load("models/advanced/rf.joblib")  # 로드
  ```

### 2.12 kagglehub

- **역할:** Kaggle 데이터셋 다운로드 자동화 (구현 완료)
- **사용법:**
  ```python
  import kagglehub
  path = kagglehub.dataset_download("ryanluong1/valorant-champion-tour-2021-2023-data")
  ```
- **인증:** `~/.kaggle/kaggle.json` 필요

---

## 3. 의존성 파일

### 3.1 Python (`requirements.txt`) — 현재

현재 `requirements.txt`는 데이터 수집·전처리·ML 학습 레이어용입니다.

```
# 데이터 수집
kagglehub
pandas>=2.0.0
numpy>=1.26.0

# ML 파이프라인 (현재 사용 중)
scikit-learn>=1.5.0
xgboost>=2.0.0
lightgbm>=4.0.0
joblib>=1.3.0

# 향후 확장 후보 (현재 활성 모델에서는 미사용)
shap
optuna

# 웹 백엔드 레이어 (현재 사용 중)
fastapi
uvicorn
pydantic

# DB 레이어 (예측 기록 저장, 선택적 — VALO_DATABASE_URL 설정 시 활성)
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
```

> 프런트엔드(Next.js 16 `web`)는 npm 의존성으로 별도 관리한다(`web/package.json`).

---

## 4. 명시적으로 제외된 기술

| 기술 | 이유 |
|------|------|
| Vercel / 클라우드 배포 | 로컬 실행 시연 — 클라우드 배포는 평가 범위 밖 |
| Streamlit | 폐기됨 — 웹 스택(FastAPI + Next.js)으로 전환, 추론 로직만 `src/inference/predict.py`로 보존 |
| HenrikDev API | 외부 API 미사용 — Kaggle 5개 데이터셋 + VLR.gg 수집 스냅샷 사용 |
| PyTorch / TensorFlow | 딥러닝 금지 — Tree-based ML만 사용 |

---

## 5. 관련 문서

| 문서 | 내용 |
|------|------|
| [01_project_summary.md](01_project_summary.md) | 프로젝트 소개 및 핵심 아이디어 |
| [03_design_principles.md](03_design_principles.md) | 설계 원칙 |
| [../03_architecture/06_ml_pipeline_architecture.md](../03_architecture/06_ml_pipeline_architecture.md) | ML 파이프라인 아키텍처 |
