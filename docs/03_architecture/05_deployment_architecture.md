# 05. 배포 아키텍처

마지막 업데이트: 2026-05-04

> **범위 외 (out of scope)**: 이 프로젝트는 클라우드 배포를 사용하지 않습니다. Vercel, Railway, Fly.io, Docker, Nginx, GitHub Actions CI/CD, FastAPI 서버 배포는 이 프로젝트의 범위 밖입니다. 본 프로젝트는 **Streamlit 로컬 도구**로 로컬 머신에서만 실행됩니다.

---

## 1. 실행 환경

```
로컬 머신
    │
    ├── Python 3.14.4 가상환경 (.venv)
    ├── data/raw/kaggle/       ← Kaggle 데이터셋 (2.3GB, git 제외)
    ├── data/processed/        ← 전처리 결과물 (git 제외)
    ├── models/                ← 학습된 모델 (git 제외)
    └── app/main.py            ← Streamlit UI 진입점 (구현 완료)
```

---

## 2. 로컬 실행 방법

### 2.1 환경 설정

```bash
# 가상환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows

# 의존성 설치
pip install -r requirements.txt
```

### 2.2 데이터 수집 (구현 완료)

```bash
# Kaggle 인증 필요: ~/.kaggle/kaggle.json
python dataload.py
```

### 2.3 전처리 파이프라인 실행 (구현 완료)

```bash
# raw 정제
python -m ml.raw_preprocess

# baseline 전처리
python -m ml.baseline.preprocess

# advanced 전처리
python -m ml.baseline.preprocess --feature-contract advanced
```

### 2.4 모델 학습 (구현 완료)

```bash
# baseline
python -m ml.baseline.train --input data/processed --output models/baseline

# advanced (Optuna HPO + 앙상블)
python -m ml.advanced.optimize
python -m ml.advanced.ensemble
```

### 2.5 Streamlit UI 실행 (구현 완료)

```bash
streamlit run app/main.py
# 브라우저에서 http://localhost:8501 접속
```

---

## 3. 환경별 설정

| 항목 | 로컬 개발 |
|------|-----------|
| UI | `http://localhost:8501` (Streamlit) |
| DB | 로컬 PostgreSQL (후보, 미구현) |
| 모델 경로 | `./models/` |
| 데이터 경로 | `./data/raw/kaggle/` |

---

## 4. 의존성 설치 단계

Phase별 추가 의존성:

| Phase | 추가 패키지 | 상태 |
|-------|------------|------|
| 1 | `kagglehub`, `pandas`, `numpy` | 완료 |
| 2-3 | `scikit-learn` | 완료 |
| 4 | `xgboost`, `lightgbm`, `shap`, `joblib` | 완료 |
| 5 | `streamlit`, `plotly` | 완료 |
| DB 후보 | `sqlalchemy`, `psycopg2-binary` | 미구현 (후보) |

---

## 5. 관련 문서

| 문서 | 내용 |
|------|------|
| [../02_file_structure/05_config_and_env.md](../02_file_structure/05_config_and_env.md) | 환경변수 전체 목록 |
| [03_database_schema.md](03_database_schema.md) | PostgreSQL DDL |
| [01_system_overview.md](01_system_overview.md) | 시스템 아키텍처 전체 |
