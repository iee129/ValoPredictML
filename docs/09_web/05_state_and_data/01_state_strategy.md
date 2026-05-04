> ⚠️ **범위 외**: Next.js 미사용. UI는 Streamlit 로컬 도구로 대체. 본문은 참고용으로 보존된다.

# 01. 상태 관리 전략

---

## 전략 요약

ValoPredictML 프론트엔드는 **외부 상태 관리 라이브러리를 사용하지 않는다.**

- Redux, Zustand, Recoil, Context API — **모두 미사용**
- 모든 상태는 각 `page.js`에서 `useState`로 관리
- 컴포넌트 간 상태 공유는 **props 전달**로만

---

## 이 전략을 선택한 이유

### 1. 앱 규모에 적합

| 항목 | 이 앱 | Redux 필요한 앱 |
|---|---|---|
| 페이지 수 | 4개 | 10개 이상 |
| 전역 상태 | 없음 | 인증, 장바구니, 테마 |
| 페이지 간 공유 데이터 | 없음 | 있음 |
| 상태 복잡도 | 단순 | 복잡 |

→ 전역 상태 저장소가 **필요 없는** 앱이다.

### 2. 각 페이지가 독립적

- `/predict` 상태(팀 선택)가 `/history`에 영향을 주지 않음
- 페이지 이동 시 상태 초기화 → 자연스럽게 예측 결과가 사라짐

### 3. 번들 크기 / 복잡도 감소

- Zustand ~20KB, Redux Toolkit ~80KB 절약
- 코드가 간단하고 예측 가능

---

## 페이지별 상태 목록

### `/` (HomePage)

```js
const [stats, setStats] = useState(null);
const [recentPredictions, setRecentPredictions] = useState([]);
const [loading, setLoading] = useState(true);
```

### `/predict` (PredictPage)

```js
const [agents, setAgents]   = useState([]);     // 전체 요원 목록
const [maps, setMaps]       = useState([]);     // 전체 맵 목록
const [selectedMap, setSelectedMap]   = useState('');
const [teamA, setTeamA]     = useState([]);     // 팀 A 선택된 요원 이름[]
const [teamB, setTeamB]     = useState([]);     // 팀 B 선택된 요원 이름[]
const [result, setResult]   = useState(null);   // 예측 결과
const [loading, setLoading] = useState(false);
const [error, setError]     = useState('');
```

### `/history` (HistoryPage)

```js
const [items, setItems]     = useState([]);
const [total, setTotal]     = useState(0);
const [page, setPage]       = useState(1);
const [maps, setMaps]       = useState([]);
const [filters, setFilters] = useState({ map: '', startDate: '', endDate: '' });
const [loading, setLoading] = useState(true);
const PAGE_SIZE = 20;
```

### `/analytics` (AnalyticsPage)

```js
const [data, setData]       = useState(null);
const [loading, setLoading] = useState(true);
const [error, setError]     = useState('');
```

---

## 상태 업데이트 패턴

### 요원 선택 (교차 팀 필터링)

```js
const handleSelectA = (agentName) => {
  if (teamA.includes(agentName)) {
    setTeamA(prev => prev.filter(n => n !== agentName));
  } else if (teamA.length < 5 && !teamB.includes(agentName)) {
    setTeamA(prev => [...prev, agentName]);
  }
};
```

같은 요원을 양 팀에서 선택하는 것 방지:
- `AgentPicker`로 전달되는 `agents`는 이미 상대 팀 필터링 완료
- `availableForA = agents.filter(a => !teamB.includes(a.name))`

### 페이지 변경 시 상태 초기화

```js
// history/page.js
const handleFilterChange = (newFilters) => {
  setFilters(newFilters);
  setPage(1); // 필터 변경 시 첫 페이지로
};
```

---

## 상태 흐름 원칙

```
page.js (상태 소유자)
    ↓ props
컴포넌트 (상태 없음, UI만)
    ↓ 콜백
page.js (상태 업데이트)
```

- **단방향 데이터 흐름** 유지
- 컴포넌트는 상태를 직접 변경하지 않음
- 모든 `setX` 함수는 page.js가 소유
