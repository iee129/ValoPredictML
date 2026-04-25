# 03. CSS Modules 전략

---

## 기본 원칙

```
JSX → className={styles.xxx}
CSS Module → @apply [tailwind utilities]
             또는 var(--color-*)
             직접 CSS 속성
```

**JSX 파일에 Tailwind 클래스 직접 사용 금지.**

---

## `.module.css` 파일 필수 구조

```css
/* 1. 반드시 첫 줄 */
@reference "tailwindcss";

/* 2. 클래스 정의 */
.wrapper {
  @apply flex flex-col gap-4;
  background: var(--color-valo-panel);
}
```

---

## @apply 패턴

### 레이아웃

```css
/* 수직 스택 */
.stack { @apply flex flex-col gap-4; }

/* 수평 배치 */
.row { @apply flex items-center gap-2; }

/* 그리드 */
.grid { @apply grid gap-4; }
```

### 타이포그래피

```css
/* 제목 */
.heading { @apply text-2xl font-black tracking-wide; }

/* 소제목 */
.subheading { @apply text-lg font-bold; }

/* 본문 */
.body { @apply text-sm; }

/* 보조 */
.muted {
  @apply text-sm;
  color: var(--color-valo-muted);
}
```

### 카드

```css
.card {
  @apply rounded-lg p-5;
  background: var(--color-valo-panel);
  border: 1px solid var(--color-valo-border);
}
```

### 버튼

```css
.btn {
  @apply px-6 py-2.5 rounded font-bold text-sm cursor-pointer transition-all;
  background: var(--color-valo-red);
  color: white;
}
.btn:hover {
  filter: brightness(1.1);
  transform: translateY(-1px);
}
.btn:disabled {
  @apply opacity-40 cursor-not-allowed;
  transform: none;
}
```

---

## 조건부 className 패턴

### 방법 1: 삼항 연산자 (단순 on/off)

```jsx
<Link className={pathname === link.href ? styles.linkActive : styles.link}>
```

### 방법 2: 배열 + join (복수 조건)

```jsx
<div className={[
  styles.card,
  selected ? styles.selected : '',
  disabled ? styles.disabled : '',
].join(' ')}>
```

### 방법 3: classnames 라이브러리 (미사용)

이 프로젝트에서는 `classnames`/`clsx` 라이브러리를 사용하지 않음.
조건이 복잡해지면 배열 join 방식 사용.

---

## 파일 당 클래스 네이밍 규칙

- **camelCase** 사용: `styles.cardTitle`, `styles.btnPrimary`
- 컴포넌트 최상위 래퍼: `styles.wrapper` 또는 `styles.container`
- 상태 변형: 기본 클래스명 + 상태 (`styles.tab`, `styles.tabActive`)
- BEM 불필요: CSS Modules가 자동으로 스코프 격리

### 예시

```css
/* AgentCard.module.css */
@reference "tailwindcss";

.wrapper { ... }        /* 최상위 */
.image { ... }          /* 이미지 */
.name { ... }           /* 이름 */
.roleDot { ... }        /* 역할 도트 */
.selected { ... }       /* 선택 상태 */
.disabled { ... }       /* 비활성 상태 */
```

---

## CSS 변수 vs @apply 선택 기준

| 상황 | 사용 |
|---|---|
| 색상 | `var(--color-*)` |
| 레이아웃, 간격 | `@apply` (Tailwind spacing, flex) |
| 텍스트 크기/굵기 | `@apply` (Tailwind typography) |
| 애니메이션 | 직접 CSS `@keyframes` |
| 테두리 radius | `@apply rounded-*` |
| 그림자 | `@apply shadow-*` |

---

## 절대 하지 말 것

```jsx
{/* ❌ JSX에 Tailwind 유틸리티 직접 사용 */}
<div className="flex items-center bg-red-500 px-4">
```

```css
/* ❌ @reference 없이 @apply 사용 */
.myClass {
  @apply flex;  /* 빌드 에러 */
}
```

```css
/* ❌ 인라인 스타일로 테마 무시 */
<div style={{ backgroundColor: '#ff4655' }}>
/* → var(--color-valo-red) 사용 */
```
