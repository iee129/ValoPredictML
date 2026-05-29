> ⚠️ **범위 외**: Next.js 미사용. UI는 Streamlit 로컬 도구로 대체. 본문은 참고용으로 보존된다.

# 05. history 도메인 컴포넌트

`/history` 페이지에서 예측 기록 조회 UI를 담당하는 컴포넌트 3개.

---

## HistoryTable

**파일:** `HistoryTable.js` + `HistoryTable.module.css`

### 역할

예측 기록 목록을 테이블 형태로 렌더링.

### Props

| prop | 타입 | 설명 |
|---|---|---|
| `items` | Array | 예측 기록 배열 |

### 각 아이템 구조

```json
{
  "id": 1,
  "map": "Ascent",
  "team_a": ["Jett", "Sage", "Omen", "Fade", "Killjoy"],
  "team_b": ["Phoenix", "Skye", "Viper", "Breach", "Cypher"],
  "win_rate_a": 0.62,
  "win_rate_b": 0.38,
  "confidence": 0.78,
  "created_at": "2024-01-15T12:30:00"
}
```

### 테이블 컬럼

| 컬럼 | 표시 내용 |
|---|---|
| 날짜 | `created_at` (한국 시간 포맷) |
| 맵 | 맵 이름 |
| 팀 A | 요원 이름 5개 (`, ` 구분) |
| 팀 B | 요원 이름 5개 |
| 팀 A 승률 | `{%}` 포맷 + 색상 강조 |
| 팀 B 승률 | `{%}` 포맷 |
| 신뢰도 | HIGH/MEDIUM/LOW 배지 스타일 |

### 날짜 포맷

```js
const formatDate = (iso) =>
  new Date(iso).toLocaleString('ko-KR', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit'
  });
```

### 요원 목록 표시

`team_a.join(', ')` — 단순 텍스트. 이미지 없음 (공간 절약).

### 상태별 비주얼 스펙

```css
/* HistoryTable.module.css */
@reference "tailwindcss";

.table {
  @apply w-full text-sm;
  color: var(--color-valo-text);
}

.thead th {
  @apply py-2 px-3 text-left font-semibold uppercase tracking-wider text-xs;
  color: var(--color-valo-muted);
  border-bottom: 1px solid var(--color-valo-border);
}

.row {
  @apply border-b transition-colors duration-100;
  border-color: var(--color-valo-border);
}
.row:hover {
  background: var(--color-valo-panel-alt);
}

/* 팀 A 승률 강조 */
.winRateHigh { color: var(--color-valo-red); font-weight: 700; }
.winRateLow  { color: var(--color-valo-muted); }
```

| 요소 | 상태 | 토큰 |
|---|---|---|
| `.row` | 기본 | 배경 없음 (페이지 배경 투과) |
| `.row` | hover | `var(--color-valo-panel-alt)` |
| 팀 A 승률 우세 | 텍스트 | `var(--color-valo-red)` |
| 팀 A 승률 열세 | 텍스트 | `var(--color-valo-muted)` |

---

## HistoryFilter

**파일:** `HistoryFilter.js` + `HistoryFilter.module.css`

### 역할

기록 조회 필터 UI. 맵과 날짜 범위 선택.

### Props

| prop | 타입 | 설명 |
|---|---|---|
| `maps` | string[] | 맵 목록 |
| `filters` | `{ map, startDate, endDate }` | 현재 필터 값 |
| `onChange` | fn(filters) | 필터 변경 콜백 |
| `onReset` | fn() | 필터 초기화 콜백 |

### 필터 초기화 로직

```js
// history/page.js
const handleReset = () => {
  setFilters({ map: '', startDate: '', endDate: '' });
  setPage(1);
};
```

### UI 구성

```
[맵 선택 ▼]  [시작 날짜 📅]  [종료 날짜 📅]  [초기화 버튼]
```

### 상태별 비주얼 스펙

```css
/* HistoryFilter.module.css */
.select, .dateInput {
  @apply px-3 py-1.5 rounded text-sm transition-colors duration-150;
  background: var(--color-valo-panel-alt);
  color: var(--color-valo-text);
  border: 1px solid var(--color-valo-border);
}
.select:focus, .dateInput:focus {
  outline: none;
  border-color: var(--color-valo-red);
}

.resetBtn {
  @apply px-3 py-1.5 rounded text-sm transition-colors duration-150;
  background: var(--color-valo-panel-alt);
  color: var(--color-valo-muted);
  border: 1px solid var(--color-valo-border);
}
.resetBtn:hover {
  border-color: var(--color-valo-red);
  color: var(--color-valo-text);
}
```

| 요소 | 상태 | 토큰 |
|---|---|---|
| 입력 필드 | 기본 | background `var(--color-valo-panel-alt)`, border `var(--color-valo-border)` |
| 입력 필드 | focus | border `var(--color-valo-red)` |
| 초기화 버튼 | 기본 | color `var(--color-valo-muted)` |
| 초기화 버튼 | hover | border `var(--color-valo-red)`, color `var(--color-valo-text)` |

---

## Pagination

**파일:** `Pagination.js` + `Pagination.module.css`

### 역할

페이지네이션 UI. 이전/다음 + 페이지 번호 버튼.

### Props

| prop | 타입 | 설명 |
|---|---|---|
| `page` | number | 현재 페이지 (1-based) |
| `total` | number | 전체 아이템 수 |
| `pageSize` | number | 페이지당 아이템 수 |
| `onChange` | fn(page) | 페이지 변경 콜백 |

### 총 페이지 계산

```js
const totalPages = Math.ceil(total / pageSize);
```

### 표시할 페이지 번호 범위

현재 페이지 기준 ±2 (최대 5개 버튼):
```js
const range = (from, to) =>
  Array.from({ length: to - from + 1 }, (_, i) => from + i);

const start = Math.max(1, page - 2);
const end   = Math.min(totalPages, page + 2);
const pages = range(start, end);
```

### 버튼 렌더링

```jsx
<div className={styles.pagination}>
  <button onClick={() => onChange(page - 1)} disabled={page === 1}>
    ← 이전
  </button>
  {pages.map(p => (
    <button
      key={p}
      onClick={() => onChange(p)}
      className={p === page ? styles.pageActive : styles.page}
    >
      {p}
    </button>
  ))}
  <button onClick={() => onChange(page + 1)} disabled={page === totalPages}>
    다음 →
  </button>
</div>
```

### CSS

```css
.page {
  @apply px-3 py-1 rounded transition-colors duration-150;
  background: var(--color-valo-panel-alt);
  color: var(--color-valo-muted);
  border: 1px solid var(--color-valo-border);
}
.page:hover {
  border-color: var(--color-valo-red);
  color: var(--color-valo-text);
}

.pageActive {
  @apply px-3 py-1 rounded font-bold;
  background: var(--color-valo-red);
  color: var(--color-valo-text);
}
.pageActive:hover {
  background: var(--color-valo-red-hover);
}
```
