# 05. 환경 설정 및 설정 파일

마지막 업데이트: 2026-05-04

## 1. `.env` — 환경변수 (루트)

```env
# =====================
# Kaggle 인증
# =====================
# ~/.kaggle/kaggle.json 으로 관리 (이 파일에 직접 기재 금지)

# =====================
# PostgreSQL (후보, 미구현)
# =====================
DATABASE_URL=postgresql+psycopg2://postgres:your_password@localhost:5432/valo_predict

# ==========
# ML 설정
# ==========
MODEL_PATH=./models
```

**규칙:**
- 이 파일은 절대 Git에 커밋하지 않음 (`.gitignore`에 포함)
- Kaggle API Key는 `~/.kaggle/kaggle.json`에 위치 (리포 외부)
- `.env.example` 파일을 별도로 유지하여 키 구조만 공유

---

## 2. 전체 환경변수 목록

| 변수명 | 필수 | 기본값 | 설명 |
|--------|------|--------|------|
| `DATABASE_URL` | 선택 | — | PostgreSQL 연결 문자열 (후보, 미구현) |
| `MODEL_PATH` | 선택 | `./models` | 모델 파일 디렉토리 |

**명시적으로 제외된 환경변수:**

| 변수명 | 이유 |
|--------|------|
| `NEXT_PUBLIC_API_URL` | Next.js 미사용 |
| `POSTGRES_URL` (Vercel) | Vercel 배포 없음 |
| `HENRIK_API_KEY` | 외부 API 미사용 |

---

## 3. `.gitignore` — Git 제외 목록

```gitignore
# Python 가상환경
.venv/
__pycache__/
*.pyc
*.pyo
*.pyd
*.egg-info/
dist/
build/

# 환경변수 (시크릿)
.env
.env.local
.env.*.local

# 데이터 파일 (용량 및 보안)
data/raw/
data/processed/
reports/

# 학습된 모델 (용량)
models/*.joblib

# Kaggle 인증 (절대 커밋 금지)
*.kaggle*

# 임시 파일
.DS_Store
Thumbs.db
*.log

# Jupyter
.ipynb_checkpoints/

# IDE
.vscode/
.idea/
*.swp
```

---

## 4. 파일 명명 규칙

### Python

| 대상 | 규칙 | 예시 |
|------|------|------|
| 모듈 파일 | `snake_case.py` | `data_pipeline.py`, `agent_roles.py` |
| 클래스 | `PascalCase` | `PredictionService` |
| 함수 | `snake_case()` | `normalize_agent()`, `count_roles()` |
| 상수 | `SCREAMING_SNAKE_CASE` | `AGENT_ROLE_MAP`, `MAP_ORDER` |
| 개인 변수 | `_snake_case` | `_model_loaded` |

### 데이터 파일

| 대상 | 규칙 | 예시 |
|------|------|------|
| CSV 파일 | `snake_case.csv` | `matches_clean.csv`, `train.csv` |
| 모델 파일 | `{model_name}_model.joblib` | `rf_model.joblib`, `xgboost_model.joblib` |
| 메타데이터 | `model_metadata.json` | `model_metadata.json` |
| 리포트 | `{name}_summary.json` | `preprocess_summary.json` |

---

## 5. Kaggle 인증 설정

```bash
# 1. ~/.kaggle/kaggle.json 생성
mkdir -p ~/.kaggle
# kaggle.json 파일 내용:
# {"username": "your_username", "key": "your_api_key"}
chmod 600 ~/.kaggle/kaggle.json

# 2. 데이터 다운로드
python dataload.py
```

---

## 6. PostgreSQL 로컬 설치 가이드 (후보, 미구현)

```bash
# macOS (Homebrew)
brew install postgresql@18
brew services start postgresql@18

# DB 생성
psql -U postgres -c "CREATE DATABASE valo_predict;"
```

---

## 7. 관련 문서

| 문서 | 내용 |
|------|------|
| [01_directory_overview.md](01_directory_overview.md) | 전체 폴더 구조 |
| [../03_architecture/03_database_schema.md](../03_architecture/03_database_schema.md) | PostgreSQL DDL |
