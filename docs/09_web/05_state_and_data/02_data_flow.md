# 02. 데이터 흐름

---

## 전체 데이터 흐름 다이어그램

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Server                        │
│  /predict  /agents  /maps  /history  /analytics         │
└─────────────────────────┬───────────────────────────────┘
                          │ HTTP (JSON)
                          ▼
┌─────────────────────────────────────────────────────────┐
│              src/lib/api.js                             │
│  predictWinRate()  fetchAgents()  fetchMaps()           │
│  fetchHistory()    fetchAnalytics()                     │
└───────┬─────────────┬─────────────┬────────────┬────────┘
        │             │             │            │
        ▼             ▼             ▼            ▼
┌───────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ predict/  │  │ history/ │  │analytics/│  │   /      │
│  page.js  │  │  page.js │  │  page.js │  │ page.js  │
│           │  │          │  │          │  │          │
│ useState  │  │ useState │  │ useState │  │ useState │
└─────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
      │ props       │ props        │ props        │ props
      ▼             ▼              ▼              ▼
┌──────────────────────────────────────────────────────┐
│                  Components                          │
│  AgentPicker  HistoryTable  StatCard  ...            │
└──────────────────────────────────────────────────────┘
```

---

## 페이지별 데이터 페칭 패턴

### 초기화 페칭 (useEffect + async/await)

```js
useEffect(() => {
  const load = async () => {
    try {
      setLoading(true);
      const [agents, maps] = await Promise.all([
        fetchAgents(),
        fetchMaps(),
      ]);
      setAgents(agents);
      setMaps(maps);
    } catch (e) {
      setError('데이터를 불러오지 못했습니다.');
    } finally {
      setLoading(false);
    }
  };
  load();
}, []);
```

- `Promise.all` → 병렬 페칭으로 초기 로딩 시간 단축
- `finally` → 성공/실패 무관하게 로딩 해제

### 필터/페이지 변경에 따른 재페칭

```js
useEffect(() => {
  const load = async () => {
    setLoading(true);
    const data = await fetchHistory({
      page,
      pageSize: PAGE_SIZE,
      ...filters,
    });
    setItems(data.items ?? data);
    setTotal(data.total ?? data.length);
    setLoading(false);
  };
  load();
}, [page, filters]); // 의존성: page, filters
```

---

## 데이터 변환 레이어

API 응답 → 컴포넌트 props 사이에 변환이 필요한 경우:

### agentImage.js — 요원 이름 → 이미지 URL

```
요원 이름 (string)
    ↓ agentImage.js
UUID (string, 하드코딩 매핑)
    ↓
https://media.valorant-api.com/agents/{uuid}/displayicon.png
```

### 날짜 포맷 변환

```
ISO 8601 (from API) → toLocaleString('ko-KR')
"2024-01-15T12:30:00" → "2024. 01. 15. 오후 12:30"
```

### 승률 표시 변환

```
float (from API) → 퍼센트 문자열
0.62 → "62%"
(winRate * 100).toFixed(0) + '%'
```

### 신뢰도 레벨 변환

```
float (from API) → 레벨 문자열
0.78 → 'HIGH'
0.61 → 'MEDIUM'
0.42 → 'LOW'
```

---

## 에러 처리 흐름

```
fetchX()
  ├─ 성공 → setState(data)
  └─ 실패 → setError(message)
              └─ ErrorMessage 컴포넌트 렌더링
```

- `api.js`에서 throw 된 에러를 page.js의 try/catch가 받음
- 에러 메시지는 `setError()`로 저장
- `<ErrorMessage message={error} />`로 표시

---

## valorant-api.com 외부 의존성

요원 이미지만 외부 CDN 사용:
- `next.config.mjs`의 `images.remotePatterns`에 도메인 등록 필요
- FastAPI 서버는 이미지를 반환하지 않음 → 클라이언트에서 직접 URL 조합
