# 02. 기술 스택 상세

마지막 업데이트: 2026-05-05

## 1. 전체 스택 한눈에 보기

```
┌─────────────────────────────────────────────────────────────────┐
│                       ValoPredictML 스택                         │
│                                                                   │
│  [데이터 수집]        [ML 파이프라인]         [UI]                │
│  Kaggle kagglehub  → pandas + NumPy    →  Streamlit (Python)    │
│  data/raw/kaggle/    scikit-learn           Plotly (시각화 후보)  │
│                       XGBoost + LightGBM                         │
│                       Random Forest                               │
│                                                                   │
│  [데이터 저장 (후보)]                                              │
│  PostgreSQL + SQLAlchemy (예측 기록, 미구현)                      │
└─────────────────────────────────────────────────────────────────┘
```

**범위 외 (out of scope)**: FastAPI, Next.js, React, Vercel/클라우드 배포는 이 프로젝트에서 사용하지 않습니다. 본 프로젝트는 Streamlit 로컬 도구입니다.

---

## 2. 백엔드 / ML 스택

### 2.1 Python 3.14.4

- **역할:** 전체 ML 파이프라인 및 Streamlit 앱
- **선택 이유:** ML 생태계(scikit-learn, XGBoost, pandas)의 표준 언어
- **주요 사용처:** `ml/`, `app/`

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

### 2.9 Streamlit

- **역할:** 로컬 분석 UI
- **선택 이유:** Python만으로 대화형 웹 UI 구현 가능 — 별도 프론트엔드 불필요
- **시각화:** Streamlit 컴포넌트 + Plotly (후보)
- **진입점:** `app/main.py` (구현 완료)

### 2.10 PostgreSQL + SQLAlchemy (후보, 미구현)

- **역할:** 예측 기록 저장 후보
- **선택 이유:**
  - SQLAlchemy ORM으로 Raw SQL 없이 Python 코드로 DB 조작
  - `JSONB` 타입으로 JSON 인덱싱 가능
- **연결:** SQLAlchemy + psycopg2 (`postgresql+psycopg2://`)
- **테이블:** `predictions` (예측 기록)

### 2.11 SHAP

- **역할:** 피처별 예측 기여도 계산 (TreeExplainer 사용)
- **사용처:** `ml/advanced/shap_analysis.py` — 앙상블 모델 SHAP 값 산출 및 시각화 (TreeExplainer, 구현 완료)

### 2.12 Optuna

- **역할:** 하이퍼파라미터 자동 최적화 (HPO)
- **사용처:** `ml/advanced/optimize.py` — RF/XGBoost/LightGBM 각 모델의 파라미터 탐색 (TPESampler 50 trials, 구현 완료)
- **방식:** Optuna Study (`direction="maximize"`, ROC-AUC 최적화)

### 2.13 joblib

- **역할:** 학습된 모델 직렬화/역직렬화
- **사용법:**
  ```python
  import joblib
  joblib.dump(model, "models/rf_model.joblib")   # 저장
  model = joblib.load("models/rf_model.joblib")  # 로드
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
shap
optuna
joblib>=1.3.0

# UI 레이어 (현재 사용 중)
streamlit>=1.35.0

# 후보 DB 레이어 (현재 미사용 — PostgreSQL/SQLite 범위 외)
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
```

---

## 4. 명시적으로 제외된 기술

| 기술 | 이유 |
|------|------|
| FastAPI / uvicorn | 외부 API 서빙 불필요 — Streamlit 로컬 도구 |
| Next.js / React | 프론트엔드 프레임워크 불필요 |
| Vercel / 클라우드 배포 | 로컬 실행 도구 — 배포 없음 |
| HenrikDev API | 외부 API 미사용 — Kaggle 데이터셋만 사용 |
| PyTorch / TensorFlow | 딥러닝 금지 — Tree-based ML만 사용 |

---

## 5. 관련 문서

| 문서 | 내용 |
|------|------|
| [01_project_summary.md](01_project_summary.md) | 프로젝트 소개 및 핵심 아이디어 |
| [03_design_principles.md](03_design_principles.md) | 설계 원칙 |
| [../03_architecture/03_database_schema.md](../03_architecture/03_database_schema.md) | PostgreSQL 스키마 정의 |
| [../03_architecture/06_ml_pipeline_architecture.md](../03_architecture/06_ml_pipeline_architecture.md) | ML 파이프라인 아키텍처 |
