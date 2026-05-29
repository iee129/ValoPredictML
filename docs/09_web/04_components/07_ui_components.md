> ⚠️ **범위 외**: Next.js 미사용. UI는 Streamlit 로컬 도구로 대체. 본문은 참고용으로 보존된다.

# 07. UI 공용 컴포넌트

`src/components/ui/` — 모든 페이지에서 재사용되는 범용 컴포넌트 3개.

---

## LoadingSpinner

**파일:** `LoadingSpinner.js` + `LoadingSpinner.module.css`

### 역할

데이터 페칭 중 로딩 상태 표시.

### Props

없음. 모든 로딩 상태에서 동일하게 사용.

### 구현

```jsx
export default function LoadingSpinner() {
  return (
    <div className={styles.wrapper}>
      <div className={styles.spinner} />
      <span className={styles.text}>로딩 중...</span>
    </div>
  );
}
```

### CSS (CSS-only 스피너)

```css
@reference "tailwindcss";

.wrapper {
  @apply flex flex-col items-center justify-center py-16 gap-3;
}

.spinner {
  @apply w-10 h-10 rounded-full border-4;
  border-color: var(--color-valo-border);
  border-top-color: var(--color-valo-red);
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.text {
  @apply text-sm;
  color: var(--color-valo-muted);
}
```

### 사용 위치

- `analytics/page.js` → 데이터 로딩 중
- `history/page.js` → 목록 로딩 중

---

## ErrorMessage

**파일:** `ErrorMessage.js` + `ErrorMessage.module.css`

### 역할

API 에러 또는 유효성 검사 실패 메시지 표시.

### Props

| prop | 타입 | 설명 |
|---|---|---|
| `message` | string | 표시할 에러 메시지 |

### 구현

```jsx
export default function ErrorMessage({ message }) {
  if (!message) return null;

  return (
    <div className={styles.error} role="alert">
      <span className={styles.icon}>⚠️</span>
      <span className={styles.text}>{message}</span>
    </div>
  );
}
```

### CSS

```css
@reference "tailwindcss";

.error {
  @apply flex items-center gap-2 px-4 py-3 rounded;
  background: var(--color-valo-red-dim);
  border: 1px solid rgba(255, 70, 85, 0.3);
  color: var(--color-valo-red);
}
```

### 사용 위치

- `predict/page.js` → 팀 미완성 시, API 에러 시
- `analytics/page.js` → API 에러 시

---

## StatCard

**파일:** `StatCard.js` + `StatCard.module.css`

### 역할

단일 통계 수치 + 레이블을 카드 형태로 표시. 여러 통계를 그리드로 나열할 때 사용.

### Props

| prop | 타입 | 설명 |
|---|---|---|
| `label` | string | 통계 이름 (e.g. `"총 예측 횟수"`) |
| `value` | string \| number | 표시할 값 (e.g. `1245`, `"62.3%"`) |
| `unit` | string? | 단위 (e.g. `"회"`, `"%"`) |
| `icon` | string? | 이모지 아이콘 (e.g. `"🎯"`) |

### 구현

```jsx
export default function StatCard({ label, value, unit, icon }) {
  return (
    <div className={styles.card}>
      {icon && <span className={styles.icon}>{icon}</span>}
      <div className={styles.content}>
        <span className={styles.value}>
          {value}{unit && <span className={styles.unit}>{unit}</span>}
        </span>
        <span className={styles.label}>{label}</span>
      </div>
    </div>
  );
}
```

### CSS

```css
@reference "tailwindcss";

.card {
  @apply flex items-center gap-4 p-5 rounded-lg transition-colors duration-150;
  background: var(--color-valo-panel);
  border: 1px solid var(--color-valo-border);
}
.card:hover {
  border-color: var(--color-valo-red);
}

.icon {
  @apply text-3xl;
}

.value {
  @apply text-2xl font-black;
  color: var(--color-valo-text);
}

.unit {
  @apply text-sm font-normal ml-1;
  color: var(--color-valo-muted);
}

.label {
  @apply text-sm mt-0.5;
  color: var(--color-valo-muted);
}
```

### 사용 위치

- `home/page.js` → `StatCard × 3` (총 예측, 평균 신뢰도, 인기 요원)
- `analytics/page.js` → `StatCard × 4` (예측 횟수, 평균 승률, 맵 수, 요원 수)

### StatCard 그리드 레이아웃 (page.js에서)

```jsx
<div className={styles.statsGrid}>
  <StatCard label="총 예측 횟수" value={stats.total}  icon="🎯" unit="회" />
  <StatCard label="평균 신뢰도"  value={stats.avgConf} icon="📊" unit="%" />
  <StatCard label="분석 맵 수"   value={stats.maps}   icon="🗺️" />
</div>
```

```css
.statsGrid {
  @apply grid gap-4;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
}
```
