# 03. CI/CD 파이프라인

---

## 전체 흐름

```
개발자 로컬
    ↓ git push
GitHub Repository
    ↓ GitHub Actions 트리거
    ├── 1. 린트 / 빌드 체크
    ├── 2. PR → Vercel Preview 배포
    └── 3. main 브랜치 → Vercel Production 배포
```

---

## GitHub Actions 워크플로

### `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main, dev]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: valo_predict_system

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: valo_predict_system/package-lock.json

      - name: Install dependencies
        run: npm ci

      - name: Build
        run: npm run build
        env:
          NEXT_PUBLIC_API_URL: ${{ secrets.NEXT_PUBLIC_API_URL }}
```

---

## Vercel 자동 배포

Vercel은 GitHub 연동 시 **자동으로 CI/CD 처리**:

| 이벤트 | Vercel 동작 |
|---|---|
| PR 오픈/업데이트 | Preview URL 생성 |
| PR 머지 → main | Production 배포 |
| main 직접 push | Production 배포 |

### Vercel GitHub 연동

1. [vercel.com](https://vercel.com) → New Project
2. GitHub 저장소 선택
3. Root Directory: `valo_predict_system`
4. 환경변수 설정
5. Deploy

이후 모든 push/PR에 자동 반응.

---

## 브랜치 전략

```
main    → Production 배포
dev     → 개발 통합 브랜치
feature/xxx → 기능 개발
```

### PR → main 흐름

```
feature/xxx
    ↓ PR 생성
Vercel Preview URL 자동 생성
    ↓ 리뷰 + 확인
dev 브랜치 머지
    ↓ QA 완료
main 브랜치 PR
    ↓ 머지
Vercel Production 자동 배포
```

---

## 배포 확인 방법

### 방법 1: Vercel 대시보드

- Deployments 탭에서 실시간 빌드 로그 확인
- 각 배포의 상태 (Building → Ready / Error)

### 방법 2: GitHub Checks

PR에 Vercel 체크 자동 추가:
- `vercel — Preview deployment` 체크 표시
- Preview URL 링크 포함

### 방법 3: CLI

```bash
# 현재 프로덕션 배포 상태
vercel --prod

# 배포 목록
vercel ls
```

---

## 롤백

배포 문제 발생 시:

```bash
# 이전 배포로 롤백
vercel rollback [deployment-url]
```

또는 Vercel 대시보드 → Deployments → 이전 배포 → "Promote to Production"

---

## 빌드 최적화

`next.config.mjs`에서 빌드 최적화:

```js
const nextConfig = {
  experimental: {
    reactCompiler: true,  // React 컴파일러로 자동 최적화
  },
};
```

React Compiler:
- 자동 메모이제이션 (useMemo/useCallback 수동 작성 불필요)
- 번들 크기 감소
- 런타임 성능 개선
