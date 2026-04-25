# 05. 환경 설정 및 설정 파일

## 1. `.env` — 백엔드 환경변수 (루트)

```env
# =====================
# PostgreSQL (로컬 개발)
# =====================
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password_here
DB_NAME=valo_predict

# ==================================
# Vercel Postgres (프로덕션 배포 시)
# ==================================
# Vercel 대시보드에서 자동 제공되는 값
POSTGRES_URL=postgresql://user:pw@host.vercel-storage.com:5432/verceldb
POSTGRES_HOST=your-host.vercel-storage.com
POSTGRES_USER=default
POSTGRES_PASSWORD=your_password
POSTGRES_DATABASE=verceldb

# =========
# API Keys
# =========
HENRIK_API_KEY=your_henrik_api_key  # https://app.henrikdev.xyz에서 발급

# ==========
# ML 설정
# ==========
MODEL_PATH=./models
```

**규칙:**
- 이 파일은 절대 Git에 커밋하지 않음 (`.gitignore`에 포함)
- `.env.example` 파일을 별도로 유지하여 키 구조만 공유

---

## 2. `valo_predict_system/.env.local` — 프론트엔드 환경변수

```env
# FastAPI 백엔드 서버 URL
NEXT_PUBLIC_API_URL=http://localhost:8000

# Vercel 배포 시:
# NEXT_PUBLIC_API_URL=https://your-backend-server.com
```

**규칙:**
- `NEXT_PUBLIC_` 접두사: 브라우저에서 접근 가능 (클라이언트 사이드)
- API Key, DB 정보 등 민감한 정보는 절대 `NEXT_PUBLIC_`으로 노출 금지
- Vercel 배포 시 Vercel 대시보드 "Environment Variables" 섹션에서 등록

---

## 3. `.gitignore` — Git 제외 목록

```gitignore
# Python 가상환경
.venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.egg-info/
dist/
build/

# 환경변수 (시크릿)
.env
.env.local
.env.*.local
riot.txt

# 데이터 파일 (용량 및 보안)
data/raw/
data/processed/
data/external/

# 학습된 모델 (용량)
models/*.joblib

# 임시 파일
.DS_Store
Thumbs.db
*.log

# Jupyter
.ipynb_checkpoints/

# Node.js
node_modules/
.next/
out/

# IDE
.vscode/
.idea/
*.swp
```

---

## 4. 전체 환경변수 목록

### 4.1 백엔드 (`.env`)

| 변수명 | 필수 | 기본값 | 설명 |
|---|---|---|---|
| `DB_HOST` | 선택 | `localhost` | PostgreSQL 호스트 |
| `DB_PORT` | 선택 | `5432` | PostgreSQL 포트 |
| `DB_USER` | 선택 | `postgres` | PostgreSQL 사용자 |
| `DB_PASSWORD` | ✅ | — | PostgreSQL 비밀번호 |
| `DB_NAME` | 선택 | `valo_predict` | 데이터베이스 이름 |
| `POSTGRES_URL` | 선택 | — | Vercel Postgres 연결 문자열 (프로덕션 우선) |
| `POSTGRES_HOST` | 선택 | — | Vercel Postgres 호스트 |
| `POSTGRES_USER` | 선택 | — | Vercel Postgres 사용자 |
| `POSTGRES_PASSWORD` | 선택 | — | Vercel Postgres 비밀번호 |
| `POSTGRES_DATABASE` | 선택 | — | Vercel Postgres DB 이름 |
| `HENRIK_API_KEY` | ✅ | — | HenrikDev API 인증 키 |
| `MODEL_PATH` | 선택 | `./models` | 모델 파일 디렉토리 |

> `POSTGRES_URL`이 있으면 `DB_HOST` 등 분리 변수를 무시하고 `POSTGRES_URL` 우선 사용

### 4.2 프론트엔드 (`.env.local`)

| 변수명 | 필수 | 기본값 | 설명 |
|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | ✅ | `http://localhost:8000` | FastAPI 서버 URL |

---

## 5. 파일 명명 규칙

### Python

| 대상 | 규칙 | 예시 |
|---|---|---|
| 모듈 파일 | `snake_case.py` | `feature_engineering.py` |
| 클래스 | `PascalCase` | `PredictionService` |
| 함수 | `snake_case()` | `get_role_counts()` |
| 상수 | `SCREAMING_SNAKE_CASE` | `AGENT_ROLE_MAP` |
| 개인 변수 | `_snake_case` | `_model_loaded` |

### JavaScript / Next.js

| 대상 | 규칙 | 예시 |
|---|---|---|
| 컴포넌트 파일 | `PascalCase.js` | `AgentPicker.js` |
| 유틸 파일 | `camelCase.js` | `api.js`, `formatters.js` |
| CSS 모듈 | `camelCase.module.css` | `agentPicker.module.css` |
| 페이지 | `page.js` (App Router) | `predict/page.js` |
| 환경변수 | `SCREAMING_SNAKE_CASE` | `NEXT_PUBLIC_API_URL` |

### 데이터 파일

| 대상 | 규칙 | 예시 |
|---|---|---|
| CSV 파일 | `snake_case.csv` | `features.csv`, `train.csv` |
| 모델 파일 | `{model_name}_model.joblib` | `xgboost_model.joblib` |
| 메타데이터 | `{name}_metadata.json` | `model_metadata.json` |
| 리포트 | `{name}_report.json` | `training_report.json` |

---

## 6. `next.config.mjs` 설정

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'media.valorant-api.com',  // 공식 요원 이미지
      },
    ],
  },
  async headers() {
    return [
      {
        source: '/api/:path*',
        headers: [
          { key: 'Access-Control-Allow-Origin', value: '*' },
        ],
      },
    ];
  },
};

export default nextConfig;
```

---

## 7. `postcss.config.mjs` 설정

```javascript
const config = {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};

export default config;
```

---

## 8. PostgreSQL 로컬 설치 가이드 (개발 환경)

```bash
# macOS (Homebrew)
brew install postgresql@18
brew services start postgresql@18

# DB 생성
psql -U postgres -c "CREATE DATABASE valo_predict;"

# 테이블 초기화
psql -U postgres -d valo_predict -f backend/db/init.sql
```

---

## 9. 관련 문서

| 문서 | 내용 |
|---|---|
| [01_directory_overview.md](01_directory_overview.md) | 전체 폴더 구조 |
| [../03_architecture/05_deployment_architecture.md](../03_architecture/05_deployment_architecture.md) | Vercel 배포 환경변수 설정 |
| [../03_architecture/03_database_schema.md](../03_architecture/03_database_schema.md) | PostgreSQL DDL 및 init.sql |
