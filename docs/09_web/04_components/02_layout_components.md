> ⚠️ **범위 외**: Next.js 미사용. UI는 Streamlit 로컬 도구로 대체. 본문은 참고용으로 보존된다.

# 02. 레이아웃 컴포넌트

---

## Navbar

**파일:** `src/components/layout/Navbar.js` + `Navbar.module.css`

### 역할

- 모든 페이지 상단에 고정 표시
- 4개 링크 네비게이션 (홈 / 승률 예측 / 통계 분석 / 예측 기록)
- 현재 페이지 링크 강조 표시

### Props

없음. 자체적으로 `usePathname()`으로 현재 경로를 감지.

### 네비게이션 링크 구성

```js
const NAV_LINKS = [
  { href: '/',          label: '홈',       icon: '🏠' },
  { href: '/predict',   label: '승률 예측', icon: '⚔️' },
  { href: '/analytics', label: '통계 분석', icon: '📊' },
  { href: '/history',   label: '예측 기록', icon: '📋' },
];
```

### 구현 패턴

```js
'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import styles from './Navbar.module.css';

export default function Navbar() {
  const pathname = usePathname();

  return (
    <nav className={styles.nav}>
      <div className={styles.brand}>
        <Link href="/" className={styles.logo}>ValoPredictML</Link>
      </div>
      <div className={styles.links}>
        {NAV_LINKS.map(link => (
          <Link
            key={link.href}
            href={link.href}
            className={pathname === link.href ? styles.linkActive : styles.link}
          >
            {link.label}
          </Link>
        ))}
      </div>
    </nav>
  );
}
```

### CSS 클래스

```css
/* Navbar.module.css */
@reference "tailwindcss";

.nav {
  @apply flex items-center justify-between px-6 py-4 sticky top-0 z-50;
  background-color: var(--color-valo-panel);
  border-bottom: 1px solid var(--color-valo-border);
}

.brand { ... }

.logo {
  @apply text-xl font-black tracking-widest;
  color: var(--color-valo-red);
}

.links {
  @apply flex gap-6;
}

.link {
  @apply text-sm font-medium transition-colors;
  color: var(--color-valo-muted);
}
.link:hover {
  color: var(--color-valo-text);
}

.linkActive {
  @apply text-sm font-bold;
  color: var(--color-valo-red);
  border-bottom: 2px solid var(--color-valo-red);
}
```

### 반응형 동작

| 뷰포트 | 동작 |
|---|---|
| 데스크톱 | 로고 + 텍스트 링크 4개 |
| 모바일 | 로고 + 아이콘만 표시 (텍스트 숨김) |

---

## PageWrapper

**파일:** `src/components/layout/PageWrapper.js` + `PageWrapper.module.css`

### 역할

- 모든 페이지 콘텐츠의 공통 래퍼
- 최대 너비 제한 + 자동 중앙 정렬
- 좌우/상하 여백 통일

### Props

| prop | 타입 | 설명 |
|---|---|---|
| `children` | ReactNode | 페이지 콘텐츠 |

### 구현

```js
import styles from './PageWrapper.module.css';

export default function PageWrapper({ children }) {
  return (
    <main className={styles.wrapper}>
      {children}
    </main>
  );
}
```

### CSS

```css
/* PageWrapper.module.css */
@reference "tailwindcss";

.wrapper {
  @apply max-w-7xl mx-auto px-4 py-8;
  /* 모바일: px-4 (16px) */
  /* 데스크톱: 자동 중앙 정렬 + max-w-7xl (1280px) */
}

@media (min-width: 640px) {
  .wrapper {
    @apply px-6;
  }
}
```

### `app/layout.js`에서의 사용

```js
// app/layout.js
import Navbar from '@/components/layout/Navbar';
import PageWrapper from '@/components/layout/PageWrapper';

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
