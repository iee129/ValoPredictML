# 05. 배포 아키텍처

## 1. 전체 배포 구조

```
GitHub Repository
        │
        │ git push
        ↓
┌───────────────────────────────────────────────────────────┐
│                      Vercel                               │
│                                                           │
│  ┌──────────────────────────────────────────────────┐    │
│  │             Next.js 16 앱                         │    │
│  │  (자동 빌드 · 자동 배포 · Edge CDN)               │    │
│  │  https://valo-predict.vercel.app                 │    │
│  └──────────────────────────────────────────────────┘    │
│                         │                                  │
│  ┌──────────────────────────────────────────────────┐    │
│  │         Vercel Postgres (PostgreSQL 18)          │    │
│  │  Connection Pool · TLS 자동 적용                  │    │
│  │  환경변수: POSTGRES_URL 자동 주입                 │    │
│  └──────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────┘
                          │
                          │ HTTPS (CORS 허용)
                          │
┌─────────────────────────────────────────────────────────┐
│              FastAPI 백엔드 서버                          │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  uvicorn backend.main:app --host 0.0.0.0 --port 8000│
│  │  (로컬 또는 클라우드 VM)                           │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  - XGBoost, LightGBM 모델 메모리 로드                  │
│  - PostgreSQL 연결 (Vercel Postgres로 직접 연결)        │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Vercel 배포 설정

### 2.1 프로젝트 구조 지정

Vercel은 `valo_predict_system/` 폴더를 루트로 인식해야 한다.

```json
// vercel.json (리포지토리 루트)
{
  "buildCommand": "cd valo_predict_system && npm run build",
  "outputDirectory": "valo_predict_system/.next",
  "framework": "nextjs",
  "installCommand": "cd valo_predict_system && npm install"
}
```

### 2.2 환경변수 설정 (Vercel Dashboard)

| 변수명 | 범위 | 설명 |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Production, Preview | FastAPI 서버 URL |
| `POSTGRES_URL` | Production | Vercel Postgres 연결 문자열 (자동 주입) |
| `POSTGRES_HOST` | Production | (자동 주입) |
| `POSTGRES_USER` | Production | (자동 주입) |
| `POSTGRES_PASSWORD` | Production | (자동 주입) |
| `POSTGRES_DATABASE` | Production | (자동 주입) |

**Vercel Postgres 추가 방법:**
1. Vercel 대시보드 → Storage → Create Database
2. PostgreSQL 선택 → 리전 선택 (ap-northeast-1 권장)
3. 프로젝트에 연결 → 환경변수 자동 주입

---

## 3. FastAPI 백엔드 서버 배포

FastAPI는 직접 서버에서 실행해야 한다. (Vercel은 Python 서버 미지원)

### 3.1 로컬 개발 실행

```bash
cd /path/to/ValoPredictML
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 3.2 프로덕션 배포 옵션

#### 옵션 A: Railway (권장, 무료 티어 있음)

```bash
# railway.toml
[build]
builder = "nixpacks"
buildCommand = "pip install -r requirements.txt"

[deploy]
startCommand = "uvicorn backend.main:app --host 0.0.0.0 --port $PORT"
```

#### 옵션 B: Fly.io

```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

#### 옵션 C: VPS (Ubuntu)

```bash
# Nginx + Gunicorn
sudo apt install nginx
pip install gunicorn
gunicorn backend.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

---

## 4. 환경별 설정 비교

| 항목 | 로컬 개발 | Vercel (프로덕션) |
|---|---|---|
| 프론트엔드 | `http://localhost:3000` | `https://valo-predict.vercel.app` |
| API URL | `http://localhost:8000` | `https://api.your-domain.com` |
| PostgreSQL | 로컬 PostgreSQL 18 | Vercel Postgres |
| DB 연결 | 환경변수 분리 변수 | `POSTGRES_URL` |
| 모델 경로 | `./models/` | 서버의 절대 경로 |

---

## 5. CI/CD 파이프라인

```
개발자 로컬
    │ git push origin main
    ↓
GitHub Repository
    ├──→ Vercel (자동 감지, 자동 배포)
    │       ├── `cd valo_predict_system && npm run build`
    │       ├── Edge 네트워크에 배포
    │       └── Preview URL 생성 (PR 브랜치)
    └──→ (선택) GitHub Actions → 백엔드 서버 배포
```

---

## 6. 보안 설정

### 6.1 CORS
```python
# 허용 오리진만 화이트리스트
allow_origins=[
    "http://localhost:3000",
    "https://*.vercel.app",
    "https://valo-predict.vercel.app",
]
```

### 6.2 환경변수 보안
- `.env` 파일은 `.gitignore`에 등록
- Vercel 환경변수는 암호화되어 저장
- `NEXT_PUBLIC_` 접두사는 클라이언트에 노출되므로 민감 정보 금지

### 6.3 PostgreSQL TLS
- Vercel Postgres는 TLS 강제 적용
- 로컬 개발 시 `sslmode=prefer`

---

## 7. 관련 문서

| 문서 | 내용 |
|---|---|
| [../02_file_structure/05_config_and_env.md](../02_file_structure/05_config_and_env.md) | 환경변수 전체 목록 |
| [03_database_schema.md](03_database_schema.md) | PostgreSQL DDL |
| [../06_model_test/05_local_development.md](../06_model_test/05_local_development.md) | 로컬 개발 실행 가이드 |
