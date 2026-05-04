> ⚠️ **범위 외**: Next.js 미사용. UI는 Streamlit 로컬 도구로 대체. 본문은 참고용으로 보존된다.

# 01. Tailwind CSS v4 설정

---

## Tailwind CSS v4의 핵심 변화

v3에서 v4로 업그레이드되면서 설정 방식이 완전히 바뀌었다.

| 항목 | v3 | v4 |
|---|---|---|
| 설정 파일 | `tailwind.config.js` | `globals.css` 내 `@theme {}` |
| 커스텀 색상 | `theme.extend.colors` | CSS 변수 (`--color-*`) |
| 플러그인 설치 | `npm i -D tailwindcss` | `npm i tailwindcss@next` |
| PostCSS 설정 | 별도 파일 | 자동 |
| CSS Modules 참조 | 불필요 | `@reference "tailwindcss";` 필수 |

---

## `globals.css` 구조

```css
/* 1. Tailwind 임포트 */
@import "tailwindcss";

/* 2. 커스텀 테마 변수 */
@theme {
  /* 여기서 CSS 변수를 정의하면 Tailwind 유틸리티 클래스 자동 생성 */
  --color-valo-red: #ff4655;
  --color-valo-bg:  #0f1923;
  /* ... */
}

/* 3. 전역 기본 스타일 */
:root {
  background-color: var(--color-valo-bg);
  color: var(--color-valo-text);
}

body {
  font-family: 'Noto Sans KR', sans-serif;
}
```

---

## `@reference "tailwindcss";` 규칙

**모든 `.module.css` 파일의 첫 줄에 필수.**

```css
/* 올바른 예 */
@reference "tailwindcss";   ← 반드시 첫 줄

.myClass {
  @apply flex items-center;
}
```

```css
/* 틀린 예 — 빌드 에러 발생 */
.myClass {
  @apply flex items-center;  ← @reference 없으면 unknown utility 에러
}
```

### 왜 필요한가?

- `.module.css`는 격리된 스코프에서 처리됨
- Tailwind의 유틸리티 정의를 해당 파일에서 참조하겠다는 선언
- `globals.css`에서 `@import "tailwindcss"`가 있어도 모듈 파일은 별도 선언 필요

---

## `@theme {}` 블록으로 Tailwind 유틸리티 자동 생성

`globals.css`의 `@theme`에 CSS 변수를 정의하면:

```css
@theme {
  --color-valo-red: #ff4655;
}
```

자동으로 이런 유틸리티 클래스가 생성됨:
- `text-valo-red`
- `bg-valo-red`
- `border-valo-red`
- `ring-valo-red`

JSX에서 직접 사용 가능:
```jsx
<span className="text-valo-red">...</span>
```

> 하지만 이 프로젝트에서는 JSX에 유틸리티 직접 사용 금지 (→ CSS Modules만 사용).
> CSS 변수를 `var()` 형태로 `.module.css`에서만 참조.

---

## `next.config.mjs` Tailwind 관련 설정

```js
// next.config.mjs
/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    reactCompiler: true,
  },
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'media.valorant-api.com',
      },
    ],
  },
};

export default nextConfig;
```

Tailwind v4는 별도 PostCSS 플러그인 설정 없이 Next.js와 통합.
