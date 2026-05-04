> ⚠️ **범위 외**: Next.js 미사용. UI는 Streamlit 로컬 도구로 대체. 본문은 참고용으로 보존된다.

# 03. 주요 설계 결정 사항

프로젝트 초기에 내린 핵심 설계 결정들과 그 이유를 기록한다.

---

## 결정 1: TypeScript 미사용

**결정:** JavaScript만 사용 (`.js`, `.jsx` 확장자)

**이유:**
- ML 모델의 API 응답 구조가 개발 중에 자주 변경될 가능성 → 타입 정의 비용 증가
- 프로토타입 단계에서 빠른 반복 개발 우선
- Next.js + Tailwind CSS v4의 타입 지원이 아직 성숙하지 않은 부분 존재

**트레이드오프:**
- 런타임 타입 에러 위험 증가
- IDE 자동완성 지원 약화

**마이그레이션 전략 (향후):**
```
1. jsconfig.json → tsconfig.json 변환
2. src/types/api.d.ts 생성 (API 응답 타입)
3. 컴포넌트 .js → .tsx 순차 전환
```

---

## 결정 2: CSS Modules + Tailwind @apply 방식

**결정:** JSX에 Tailwind 유틸리티 클래스 직접 사용 금지 → `.module.css`에서 `@apply`만 사용

**이유:**
- 스타일 코드와 마크업 코드 명확히 분리 (가독성)
- 클래스명이 길어져 JSX가 지저분해지는 문제 방지
- `.module.css`에서 CSS 변수와 `@apply`를 함께 쓸 수 있어 유연성 증가
- 향후 스타일 변경 시 JS 파일 수정 없이 CSS 파일만 수정 가능

**패턴 예시:**
```css
/* AgentCard.module.css */
@reference "tailwindcss";

.card {
  @apply relative cursor-pointer rounded-lg overflow-hidden transition-all duration-200;
  border: 1px solid var(--color-valo-border);
}

.card:hover {
  @apply scale-105;
  border-color: var(--color-valo-red);
}
```

```jsx
/* AgentCard.js */
import styles from './AgentCard.module.css';
<div className={styles.card}>...</div>  // ✅
<div className="relative cursor-pointer ...">...</div>  // ❌
```

**중요 규칙:** `.module.css` 첫 줄에 `@reference "tailwindcss";` 필수  
→ 없으면 빌드 에러: `Cannot apply unknown utility class 'X'`

---

## 결정 3: 전역 상태 관리 라이브러리 미사용

**결정:** Redux, Zustand, Jotai 등 사용 안 함 → `useState`만으로 상태 관리

**이유:**
- 각 페이지가 독립적으로 동작 (페이지 간 공유 상태 없음)
- 예측 결과는 `/predict` 페이지 내에서만 사용
- 상태 구조가 단순함: `[map, teamA, teamB, result, loading, error]`

**페이지별 상태 목록:**
| 페이지 | 상태 변수 |
|---|---|
| `/predict` | `selectedMap`, `teamA`, `teamB`, `result`, `loading`, `error` |
| `/history` | `page`, `mapFilter`, `items`, `total` |
| `/analytics` | `data` (단순 fetch 결과) |
| `/` | `recentPredictions` (StatCard용) |

---

## 결정 4: 요원 이미지 = valorant-api.com 외부 URL

**결정:** 요원 이미지를 프로젝트에 포함하지 않고 `https://media.valorant-api.com/agents/{uuid}/displayicon.png` 사용

**이유:**
- 23명 요원 이미지를 직접 호스팅하면 저장소 용량 증가
- valorant-api.com은 공개 API, CORS 허용, 안정적 CDN
- `next/image`의 `remotePatterns` 설정으로 자동 최적화

**설정 (`next.config.mjs`):**
```js
images: {
  remotePatterns: [{
    protocol: 'https',
    hostname: 'media.valorant-api.com',
    pathname: '/agents/**',
  }]
}
```

**주의:** Harbor, Gekko UUID가 플레이스홀더 → 실제 UUID로 교체 필요  
→ 상세: [05_state_and_data/03_lib_modules.md](../05_state_and_data/03_lib_modules.md)

---

## 결정 5: Analytics 바 차트 = Recharts 미사용

**결정:** Analytics 페이지의 `TopAgents` 차트는 Recharts 대신 순수 CSS `width: %` 방식 구현

**이유:**
- Recharts BarChart를 위해 `'use client'` 전환 시 번들 크기 증가
- 단순 horizontal bar (count/maxCount × 100%)는 CSS로 충분히 표현 가능
- 로딩 속도 개선

**구현 원리:**
```js
const maxCount = topAgents[0]?.count ?? 1;
// 각 바의 너비 = (agent.count / maxCount) * 100 + '%'
```

---

## 결정 6: App Router (Server Components 기본값)

**결정:** Next.js Pages Router 대신 App Router 사용

**이유:**
- Next.js 13 이후 공식 권장 방식
- `layout.js`로 공통 레이아웃 중첩 구조 표현 용이
- 향후 RSC(React Server Components) 활용 가능성 열어둠

**현재 모든 페이지는 `'use client'`:**  
실시간 인터랙션(요원 선택, 예측 버튼)이 있어 서버 컴포넌트 사용 불가.  
향후 정적 콘텐츠(발로란트 가이드, 맵 정보)는 서버 컴포넌트로 분리 가능.

---

## 결정 7: Vercel 배포 (단일 플랫폼)

**결정:** 프론트엔드(Next.js)를 Vercel에 배포

**이유:**
- Next.js + Vercel 조합은 빌드/배포 설정이 가장 단순
- `vercel.json`의 `rewrites`로 CORS 없이 FastAPI 프록시 가능
- Preview URL로 PR 단위 테스트 가능

**FastAPI 백엔드는 Vercel 외부 (별도 서버):**  
Vercel은 Python 런타임을 장기 실행 프로세스로 지원하지 않음.
