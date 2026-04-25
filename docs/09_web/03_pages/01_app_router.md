# 01. Next.js App Router 개요

---

## App Router란?

Next.js 13부터 도입된 파일 시스템 기반 라우팅 방식.  
`src/app/` 폴더 구조가 URL 경로에 1:1로 매핑된다.

```
src/app/
├── layout.js        → 공통 레이아웃 (모든 페이지에 적용)
├── page.js          → / (루트 경로)
├── predict/
│   └── page.js      → /predict
├── history/
│   └── page.js      → /history
└── analytics/
    └── page.js      → /analytics
```

---

## 핵심 파일 규칙

| 파일명 | 역할 |
|---|---|
| `page.js` | URL에 해당하는 페이지 UI |
| `layout.js` | 자식 페이지들을 감싸는 레이아웃 (중첩 가능) |
| `loading.js` | 페이지 로딩 중 표시 (사용 안 함, 컴포넌트 레벨 로딩 사용) |
| `error.js` | 에러 바운더리 (사용 안 함) |
| `not-found.js` | 404 페이지 (미구현) |

---

## 클라이언트 컴포넌트 (`'use client'`)

App Router의 기본값은 서버 컴포넌트(Server Component).  
하지만 ValoPredictML의 모든 페이지는 `'use client'` 지시어를 사용한다.

**이유:**
- `useState`, `useEffect` 같은 React 훅 사용 필요
- 요원 선택, 예측 버튼 클릭 등 사용자 인터랙션 처리 필요
- FastAPI와의 실시간 통신 (`fetch`) 필요

```js
// src/app/predict/page.js
'use client';   // ← 반드시 첫 줄

import { useState, useEffect } from 'react';
// ...
```

---

## `layout.js` — 공통 레이아웃

```js
// src/app/layout.js
import './globals.css';
import Navbar from '@/components/layout/Navbar';
import PageWrapper from '@/components/layout/PageWrapper';

export const metadata = {
  title: 'ValoPredictML',
  description: '발로란트 팀 조합 기반 승률 예측 시스템',
};

export default function RootLayout({ children }) {
  return (
    <html lang="ko">
      <body>
        <Navbar />
        <PageWrapper>{children}</PageWrapper>
      </body>
    </html>
  );
}
```

**`metadata` 객체:** App Router의 정적 메타데이터 API. 서버 컴포넌트(layout.js)에서만 사용 가능.

---

## 라우팅 구조

```
URL           파일                     컴포넌트
──────────────────────────────────────────────────
/             src/app/page.js          HomePage
/predict      src/app/predict/page.js  PredictPage
/history      src/app/history/page.js  HistoryPage
/analytics    src/app/analytics/page.js AnalyticsPage
```

네비게이션은 `<Link>` 컴포넌트 사용 (Navbar 내):
```js
import Link from 'next/link';
<Link href="/predict">승률 예측</Link>
```

---

## `usePathname()` — 현재 경로 감지

Navbar에서 현재 활성 링크를 강조하기 위해 사용:

```js
// src/components/layout/Navbar.js
'use client';
import { usePathname } from 'next/navigation';

export default function Navbar() {
  const pathname = usePathname();
  
  return (
    <nav>
      {NAV_LINKS.map(link => (
        <Link
          key={link.href}
          href={link.href}
          className={pathname === link.href ? styles.linkActive : styles.link}
        >
          {link.label}
        </Link>
      ))}
    </nav>
  );
}
```

---

## 이미지 최적화 (`next/image`)

요원 이미지는 `<Image>` 컴포넌트로 렌더링:

```js
import Image from 'next/image';

<Image
  src={getAgentIconUrl(agent.name)}
  alt={agent.name}
  width={64}
  height={64}
/>
```

`next.config.mjs`에서 외부 도메인 허용 설정 필수:
```js
images: {
  remotePatterns: [{
    protocol: 'https',
    hostname: 'media.valorant-api.com',
  }]
}
```

---

## 빌드 출력 형태

```
Route (app)         Size     Type
/                   2.1 kB   ○ Static (빌드 시 HTML 생성)
/analytics          3.4 kB   ○ Static
/history            4.2 kB   ○ Static
/predict            8.7 kB   ○ Static
```

모든 페이지가 Static으로 빌드됨.  
실제 데이터는 클라이언트에서 FastAPI로 직접 fetch.
