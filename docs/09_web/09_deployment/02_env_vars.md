> ⚠️ **범위 외**: Next.js 미사용. UI는 Streamlit 로컬 도구로 대체. 본문은 참고용으로 보존된다.

# 02. 환경변수

---

## 환경변수 목록

| 변수명 | 필수 | 설명 |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | ✅ | FastAPI 서버 URL |

---

## `NEXT_PUBLIC_API_URL`

### 값 예시

| 환경 | 값 |
|---|---|
| 로컬 개발 | `http://localhost:8000` |
| 프로덕션 | `https://api.your-domain.com` |
| 스테이징 | `https://staging-api.your-domain.com` |

### 기본값 폴백

```js
// api.js
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
```

환경변수가 없으면 `http://localhost:8000` 사용.

### `NEXT_PUBLIC_` 접두사의 의미

- 이 접두사가 있는 변수는 **브라우저 번들에 포함됨**
- 클라이언트 사이드 JavaScript에서 접근 가능
- 접두사 없는 변수 (`API_SECRET` 등)는 서버 사이드에서만 접근 가능

---

## 로컬 개발 설정

**`.env.local` 파일** (git에 커밋하지 않음):

```bash
# valo_predict_system/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

`.gitignore`에 `.env.local` 포함 확인:
```
# .gitignore
.env.local
.env*.local
```

---

## Vercel 환경변수 설정

### 방법 1: Vercel 대시보드

1. [vercel.com](https://vercel.com) → 프로젝트 선택
2. Settings → Environment Variables
3. `NEXT_PUBLIC_API_URL` 추가
4. Scope: `Production`, `Preview`, `Development` 선택

### 방법 2: Vercel CLI

```bash
vercel env add NEXT_PUBLIC_API_URL production
# 값 입력: https://api.your-domain.com
```

### 방법 3: vercel.json (권장하지 않음)

```json
{
  "env": {
    "NEXT_PUBLIC_API_URL": "https://api.your-domain.com"
  }
}
```

> ⚠️ API 키 같은 민감한 값은 vercel.json에 절대 넣지 말 것.
> 현재 `NEXT_PUBLIC_API_URL`은 공개 URL이므로 큰 문제 없음.

---

## 환경별 값 관리

```
.env.local          → 로컬 개발 전용 (git 제외)
Vercel Dashboard
  ├── Production   → 실제 서비스
  ├── Preview      → PR 미리보기
  └── Development  → vercel dev
```

---

## 배포 후 확인

환경변수가 올바르게 설정됐는지 확인:

```bash
# Vercel CLI로 확인
vercel env ls
```

또는 브라우저 콘솔:
```js
// 브라우저 개발자 도구 콘솔
console.log(process.env.NEXT_PUBLIC_API_URL);
// → "https://api.your-domain.com"
```
