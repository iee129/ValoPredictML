> ⚠️ **범위 외**: Next.js 미사용. UI는 Streamlit 로컬 도구로 대체. 본문은 참고용으로 보존된다.

# 01. API 클라이언트 (api.js)

---

## 위치

`src/lib/api.js`

---

## 기본 설정

```js
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
```

| 환경 | 값 |
|---|---|
| 로컬 개발 | `http://localhost:8000` |
| Vercel 프로덕션 | `NEXT_PUBLIC_API_URL` 환경변수 |

---

## 공통 fetch 래퍼

```js
async function apiFetch(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const errorText = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${errorText}`);
  }

  return res.json();
}
```

---

## 함수별 명세

### `predictWinRate(params)`

**요청:**
```js
export async function predictWinRate({ teamA, teamB, map }) {
  return apiFetch('/predict', {
    method: 'POST',
    body: JSON.stringify({
      team_a: teamA,    // string[] — 요원 이름 5개
      team_b: teamB,    // string[] — 요원 이름 5개
      map: map,         // string   — 맵 이름
    }),
  });
}
```

**응답 타입:**
```json
{
  "win_rate_a": 0.62,
  "win_rate_b": 0.38,
  "confidence": 0.78,
  "features": [
    { "name": "팀 조합 다양성", "importance": 0.34 },
    { "name": "공격/수비 밸런스", "importance": 0.28 }
  ]
}
```

---

### `fetchAgents()`

**요청:**
```js
export async function fetchAgents() {
  return apiFetch('/agents');
}
```

**응답 타입:**
```json
[
  { "name": "Jett",  "role": "Duelist" },
  { "name": "Sage",  "role": "Sentinel" },
  ...
]
```

---

### `fetchMaps()`

**요청:**
```js
export async function fetchMaps() {
  return apiFetch('/maps');
}
```

**응답 타입:**
```json
["Ascent", "Bind", "Breeze", "Fracture", "Haven", "Icebox", "Lotus", "Pearl", "Split", "Sunset"]
```

---

### `fetchHistory(params)`

**요청:**
```js
export async function fetchHistory({
  page = 1,
  pageSize = 20,
  map = '',
  startDate = '',
  endDate = '',
} = {}) {
  const params = new URLSearchParams({ page, page_size: pageSize });
  if (map)       params.append('map', map);
  if (startDate) params.append('start_date', startDate);
  if (endDate)   params.append('end_date', endDate);

  return apiFetch(`/history?${params}`);
}
```

**응답 타입 (두 형태 모두 지원):**

형태 1 — 페이지네이션 포함:
```json
{
  "items": [ { ... }, ... ],
  "total": 150
}
```

형태 2 — 배열 직접:
```json
[ { ... }, ... ]
```

클라이언트에서:
```js
setItems(data.items ?? data);
setTotal(data.total ?? data.length);
```

---

### `fetchAnalytics()`

**요청:**
```js
export async function fetchAnalytics() {
  return apiFetch('/analytics');
}
```

**응답 타입:**
```json
{
  "total_predictions": 1245,
  "avg_confidence": 0.72,
  "map_stats": [
    {
      "map": "Ascent",
      "attack_win_rate": 0.54,
      "defense_win_rate": 0.46,
      "total_games": 312
    }
  ],
  "top_agents": [
    { "name": "Jett", "role": "Duelist", "count": 892 },
    { "name": "Sage", "role": "Sentinel", "count": 756 }
  ]
}
```

---

## 에러 처리

api.js는 에러를 throw만 함. 처리는 호출자(page.js)에서:

```js
// page.js
try {
  const data = await fetchAnalytics();
  setData(data);
} catch (e) {
  setError(e.message || '서버에 연결할 수 없습니다.');
}
```
