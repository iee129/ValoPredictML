> ⚠️ **범위 외**: Next.js 미사용. UI는 Streamlit 로컬 도구로 대체. 본문은 참고용으로 보존된다.

# 04. 기록 페이지 (`/history`)

**파일:** `src/app/history/page.js` + `src/app/history/page.module.css`

---

## 목적

- 과거 예측 기록 조회
- 맵 필터링
- 페이지네이션 (10개씩)

---

## UI 구조

```
┌──────────────────────────────────────────────────────────────┐
│                         Navbar                               │
├──────────────────────────────────────────────────────────────┤
│  예측 기록                                                    │
│                                                              │
│  맵 필터: [전체 ▼]                                           │
├──────────────────────────────────────────────────────────────┤
│  날짜       │ 맵      │ 팀 A 구성  │ 팀 B 구성  │ 승률  │ 신뢰 │
│  ─────────────────────────────────────────────────────────  │
│  2024-01-15 │ Ascent  │ Jett,Sage… │ Reyna,Vip… │ 62%  │ HIGH │
│  2024-01-14 │ Bind    │ …         │ …          │ 48%  │ MED  │
│  ...                                                         │
├──────────────────────────────────────────────────────────────┤
│           < 이전  1 / 5  다음 >                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 상태 변수

```js
const [page, setPage] = useState(1);            // 현재 페이지 (1-indexed)
const [mapFilter, setMapFilter] = useState(''); // 선택된 맵 필터 ('' = 전체)
const [items, setItems] = useState([]);         // 현재 페이지 기록 목록
const [total, setTotal] = useState(0);          // 전체 기록 수
const [maps, setMaps] = useState([]);           // 맵 목록 (필터용)
const [loading, setLoading] = useState(true);
```

---

## 데이터 페칭 로직

```js
const LIMIT = 10;

// 초기 로드: 맵 목록 가져오기
useEffect(() => {
  fetchMaps().then(data => setMaps(data.maps ?? data));
}, []);

// page 또는 mapFilter 변경 시 기록 다시 로드
useEffect(() => {
  const load = async () => {
    setLoading(true);
    try {
      const offset = (page - 1) * LIMIT;
      const data = await fetchHistory(LIMIT, offset, mapFilter || null);
      
      // API가 { items, total } 형태이거나 plain array 형태 모두 지원
      setItems(data.items ?? data);
      setTotal(data.total ?? (data.items ? data.total : data.length));
    } finally {
      setLoading(false);
    }
  };
  load();
}, [page, mapFilter]);
```

**의존성 배열 `[page, mapFilter]`:**  
- 페이지 변경 시 → 같은 맵 필터로 다음 페이지 로드
- 맵 필터 변경 시 → `page`를 1로 리셋 후 새로 로드

```js
const handleMapFilterChange = (newMap) => {
  setPage(1);        // ← 필터 변경 시 첫 페이지로 리셋
  setMapFilter(newMap);
};
```

---

## 컴포넌트 구성

```
HistoryPage
├── HistoryFilter
│   props: maps, selected, onChange
│
├── LoadingSpinner  (loading=true 시)
│
├── HistoryTable
│   props: items
│
└── Pagination
    props: page, total, limit=10, onChange=setPage
```

---

## 총 페이지 수 계산

```js
const totalPages = Math.ceil(total / LIMIT);
```

---

## API 명세

**요청:**
```
GET /history?limit=10&offset=20&map=Ascent
```

**파라미터:**
| 파라미터 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| `limit` | int | 10 | 한 페이지 항목 수 |
| `offset` | int | 0 | 건너뛸 항목 수 |
| `map` | string | null | 맵 필터 (없으면 전체) |

**응답 (두 형태 모두 지원):**
```json
// 형태 1: 페이지네이션 객체
{ "items": [...], "total": 156 }

// 형태 2: 배열 직접 반환
[{ "map": "Ascent", "win_probability": 0.62, ... }, ...]
```

**응답 항목 구조:**
```json
{
  "map": "Ascent",
  "team_a": ["Jett", "Sage", "Brimstone", "Sova", "Cypher"],
  "team_b": ["Reyna", "Viper", "Omen", "Fade", "Killjoy"],
  "win_probability": 0.623,
  "confidence": "high",
  "created_at": "2024-01-15T14:23:00Z"
}
```

---

## 승률 색상 코딩

| 승률 범위 | 색상 | CSS 변수 |
|---|---|---|
| 60% 이상 | 녹색 | `--color-confidence-high` (#4caf50) |
| 40% ~ 60% | 주황색 | `--color-confidence-medium` (#ff9800) |
| 40% 미만 | 회색 | `--color-confidence-low` (#9e9e9e) |

---

## 반응형 처리

테이블이 모바일에서 넘칠 수 있으므로:
```css
/* HistoryTable.module.css */
.tableWrapper {
  @apply overflow-x-auto;
}
```

---

## 관련 문서

- 테이블/필터/페이지네이션 컴포넌트: [04_components/05_history_components.md](../04_components/05_history_components.md)
