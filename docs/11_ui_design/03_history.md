# 03. 예측 기록 화면 설계 (`/history`)

> **URL:** `/history`  
> **파일:** `src/app/history/page.js` + `src/app/history/page.module.css`  
> **렌더링:** CSR (Client-Side Rendering) — `'use client'`, API 호출, 맵 필터 + 페이지네이션

---

## 1. 화면 목적

과거에 수행된 승률 예측 결과를 테이블 형태로 조회한다. 맵별 필터링과 페이지네이션을 제공하여 많은 기록을 효율적으로 탐색할 수 있다.

---

## 2. 전체 레이아웃 다이어그램

```
┌─────────────────────────────────────────────────────────────────┐
│ Navbar                                                          │
├─────────────────────────────────────────────────────────────────┤
│ PageWrapper                                                     │
│                                                                 │
│  h1  "예측 기록"                                                │
│                                                                 │
│  ┌── toolbar ────────────────────────────────────────────────┐  │
│  │  맵 필터:  [드롭다운 ▼]                                   │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌── tableSection ───────────────────────────────────────────┐  │
│  │  [ErrorMessage? — 오류 시만]                               │  │
│  │                                                           │  │
│  │  [LoadingSpinner? — 로딩 중]                               │  │
│  │                                                           │  │
│  │  ┌── HistoryTable ───────────────────────────────────┐   │  │
│  │  │  ┌────────┬──────────┬──────────┬────────┬──────┐  │   │  │
│  │  │  │  맵    │  팀 A    │  팀 B    │ 팀A승률 │시각  │  │   │  │
│  │  │  ├────────┼──────────┼──────────┼────────┼──────┤  │   │  │
│  │  │  │ Ascent │ Jett외4 │Phoenix외4│  67%   │ ...  │  │   │  │
│  │  │  │ Bind   │ ...     │  ...     │  45%   │ ...  │  │   │  │
│  │  │  │  ...   │  ...    │  ...     │  ...   │ ...  │  │   │  │
│  │  │  └────────┴──────────┴──────────┴────────┴──────┘  │   │  │
│  │  └───────────────────────────────────────────────────┘   │  │
│  │                                                           │  │
│  │  ┌── Pagination ──────────────────────────────────────┐  │  │
│  │  │          ← 이전   1 / 3 페이지   다음 →            │  │  │
│  │  └───────────────────────────────────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 컴포넌트 트리

```
HistoryPage (page.js)                          [Client Component]
├── PageWrapper
├── h1.pageTitle
├── div.toolbar
│   └── HistoryFilter
│       ├── span.label  "맵 필터:"
│       └── select.select  (전체 + 맵 목록)
└── div.tableSection
    ├── ErrorMessage?                          ← error 상태 시
    ├── LoadingSpinner?                        ← loading 시
    ├── HistoryTable                           ← !loading 시
    │   ├── (비어있을 때) div.empty
    │   └── (데이터 있을 때)
    │       ├── div.tableWrap
    │       │   └── table.table
    │       │       ├── thead.thead
    │       │       │   └── tr > th × 5 (맵/팀A/팀B/승률/시각)
    │       │       └── tbody.tbody
    │       │           └── tr × N
    │       │               ├── td  맵 이름
    │       │               ├── td  팀A 에이전트 태그들
    │       │               ├── td  팀B 에이전트 태그들
    │       │               ├── td  팀A 승률 % (색상 분기)
    │       │               └── td  예측 시각
    └── Pagination
        ├── button.btn  "← 이전"
        ├── span.info  "N / M 페이지"
        └── button.btn  "다음 →"
```

---

## 4. 컴포넌트 명세

### 4-1. HistoryFilter

| 항목 | 내용 |
|------|------|
| 파일 | `src/components/history/HistoryFilter.js` |
| Props | `maps: string[]`, `mapFilter: string`, `onMapChange: (v: string) => void` |

**레이아웃:**
```
.wrap   → flex items-center gap-2
.label  → text-xs font-semibold, color: muted
.select → px-3 py-1.5 rounded-lg text-sm, background: panel, border: valo-border
```

**드롭다운 옵션:** `전체` (value="") + 각 맵 이름

| 상태 | 스타일 |
|------|--------|
| 기본 | border: valo-border |
| focus | border-color: valo-red, outline: none |

### 4-2. HistoryTable

| 항목 | 내용 |
|------|------|
| 파일 | `src/components/history/HistoryTable.js` |
| Props | `items: PredictionRecord[]` |

**PredictionRecord 타입:**
```
{
  id?: string,
  map: string,
  team_a: string[],
  team_b: string[],
  win_probability: number,  // 0~1
  created_at?: string       // ISO 날짜 문자열
}
```

**빈 상태:** `items.length === 0` → 중앙 정렬 안내 문구 표시
```
┌────────────────────────────────────┐
│        예측 기록이 없습니다.         │
└────────────────────────────────────┘
```

**테이블 스타일:**
```
.tableWrap  → overflow-x-auto rounded-xl, border: 1px solid valo-border
.table      → width: 100%, border-collapse: collapse
.thead th   → text-xs uppercase tracking-wider, color: muted, background: panel-alt
              border-bottom: 1px solid valo-border, padding: 12px 16px
.tbody tr   → border-bottom: 1px solid valo-border
.tbody tr:hover → background: panel-alt
.tbody td   → padding: 12px 16px, color: valo-text
```

**승률 색상 분기:**
| 팀A 승률 | CSS 클래스 | 색상 |
|----------|-----------|------|
| ≥ 60% | `.probHigh` | `--color-confidence-high` (초록) |
| 40~60% | `.probMed` | `#f59e0b` (노랑) |
| < 40% | `.probLow` | `#ef4444` (빨강) |

**에이전트 태그:**
```
.agents   → flex flex-wrap gap-1, max-width: 18rem
.agentTag → text-xs px-1.5 py-0.5 rounded, background: valo-border, color: muted
```

**예측 시각 표시:**
```js
new Date(item.created_at).toLocaleString('ko-KR')
// 예: 2026. 4. 25. 오후 7:00:00
```

### 4-3. Pagination

| 항목 | 내용 |
|------|------|
| 파일 | `src/components/history/Pagination.js` |
| Props | `page: number`, `total: number`, `pageSize: number`, `onPage: (n: number) => void` |

**계산:**
```js
totalPages = Math.max(1, Math.ceil(total / pageSize))
```

**버튼 상태:**
| 버튼 | 비활성 조건 |
|------|------------|
| ← 이전 | `page <= 1` |
| 다음 → | `page >= totalPages` |

**레이아웃:**
```
.wrap  → flex items-center gap-2 justify-center
.btn   → px-3 py-1.5 rounded-lg text-sm
.info  → text-xs, color: muted
```

---

## 5. 상태 흐름

```
[초기화]
useEffect([]) → fetchMaps() → setMaps

[데이터 로드]
useEffect([page, mapFilter])
  → setLoading(true)
  → fetchHistory({ limit: 10, offset: (page-1)*10, map: mapFilter||undefined })
  → 성공: setItems(data.items ?? data), setTotal(data.total ?? items.length)
  → 실패: setError(e.message)
  → setLoading(false)

[필터 변경]
HistoryFilter.onMapChange(v)
  → setMapFilter(v) + setPage(1)   ← 페이지 1로 리셋
  → useEffect 재트리거

[페이지 변경]
Pagination.onPage(n)
  → setPage(n)
  → useEffect 재트리거

상태 요약:
  maps: string[]      ← 필터 드롭다운용
  mapFilter: string   ← 선택된 맵 (""=전체)
  page: number        ← 현재 페이지 (1-indexed)
  items: []           ← 현재 페이지 데이터
  total: number       ← 전체 레코드 수 (페이지네이션용)
  loading: bool
  error: string|null
```

---

## 6. 인터랙션 정의

| 사용자 액션 | 상태 변화 | UI 반응 |
|-------------|-----------|---------|
| 맵 필터 선택 | `mapFilter` 변경, `page` → 1 | 테이블 재로드, 스피너 표시 |
| 이전 버튼 클릭 | `page` 감소 | 테이블 재로드 |
| 다음 버튼 클릭 | `page` 증가 | 테이블 재로드 |
| 데이터 로딩 중 | `loading: true` | HistoryTable 대신 LoadingSpinner |
| 로드 완료 | `loading: false` | HistoryTable 표시 |
| API 오류 | `error` 설정 | ErrorMessage 배너 |
| 기록 없음 | `items.length === 0` | "예측 기록이 없습니다." 메시지 |

---

## 7. CSS 변수 사용 목록

| 변수 | 사용 위치 |
|------|----------|
| `--color-valo-red` | HistoryFilter select focus border |
| `--color-valo-panel` | 테이블 배경, 필터 select 배경 |
| `--color-valo-panel-alt` | 테이블 헤더 배경, 행 hover |
| `--color-valo-border` | 테이블 래퍼 테두리, 행 구분선, agentTag 배경 |
| `--color-valo-text` | 테이블 셀 기본 텍스트 |
| `--color-valo-muted` | 테이블 헤더 텍스트, agentTag 텍스트, Pagination info |
| `--color-confidence-high` | 승률 ≥60% 텍스트 |

---

## 8. 반응형 처리

| 요소 | 데스크탑 | 모바일 |
|------|---------|--------|
| 테이블 | 고정 컬럼 배치 | `overflow-x-auto` → 가로 스크롤 |
| 에이전트 태그 | max-w-xs로 줄바꿈 | 동일 |
| Pagination | 중앙 정렬 가로 배치 | 동일 |

> 테이블은 `overflow-x-auto` 처리로 모바일에서 가로 스크롤을 통해 전체 내용 접근 가능.

---

## 9. API 연동

**엔드포인트:** `GET /history?limit=10&offset=0&map=Ascent`

**응답 (페이지네이션 포함):**
```json
{
  "items": [
    {
      "id": "uuid",
      "map": "Ascent",
      "team_a": ["Jett", "Omen", "Sova", "Killjoy", "Skye"],
      "team_b": ["Phoenix", "Viper", "Fade", "Sage", "Chamber"],
      "win_probability": 0.67,
      "created_at": "2026-04-25T10:00:00Z"
    }
  ],
  "total": 25
}
```

**응답 (단순 배열 fallback):**
```json
[{ ... }, { ... }]
```
> `data.items ?? data` 처리로 두 형태 모두 지원
