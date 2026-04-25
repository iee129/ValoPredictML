# 03. 에러 처리 전략

---

## 에러 분류

| 유형 | 예시 | 처리 방법 |
|---|---|---|
| 네트워크 오류 | 서버 다운, 연결 거부 | `ErrorMessage` 표시 |
| API 에러 (4xx/5xx) | 유효성 실패, 서버 에러 | `ErrorMessage` 표시 |
| 유효성 검사 | 팀 미완성 | `PredictButton` disabled |
| 데이터 없음 | 빈 기록 목록 | 빈 상태 UI |

---

## 레이어별 에러 처리

### 레이어 1: api.js (throw)

```js
async function apiFetch(path, options = {}) {
  const res = await fetch(...);

  if (!res.ok) {
    const errorText = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${errorText}`);
  }

  return res.json();
}
```

- API 오류를 Error 객체로 throw
- 구체적인 상태 코드 포함

### 레이어 2: page.js (catch + setState)

```js
try {
  setLoading(true);
  setError('');                      // 이전 에러 초기화
  const data = await fetchAnalytics();
  setData(data);
} catch (e) {
  setError(e.message || '서버에 연결할 수 없습니다.');
} finally {
  setLoading(false);
}
```

### 레이어 3: 컴포넌트 (표시)

```jsx
{error && <ErrorMessage message={error} />}
{loading && <LoadingSpinner />}
{data && <AnalyticsContent data={data} />}
```

---

## 예측 페이지 유효성 검사

UI 레벨 유효성 검사 (API 호출 전):

```js
const handlePredict = async () => {
  if (teamA.length !== 5) {
    setError('팀 A에 요원 5명을 선택해주세요.');
    return;
  }
  if (teamB.length !== 5) {
    setError('팀 B에 요원 5명을 선택해주세요.');
    return;
  }
  if (!selectedMap) {
    setError('맵을 선택해주세요.');
    return;
  }
  // API 호출
};
```

버튼 비활성화로 중복 방지:
```jsx
<PredictButton
  disabled={loading || teamA.length !== 5 || teamB.length !== 5 || !selectedMap}
/>
```

---

## 에러 상태 자동 초기화

새로운 요청 시작 시 이전 에러 제거:

```js
// 요청 시작 시
setError('');

// 필터 변경 시
const handleFilterChange = (newFilters) => {
  setFilters(newFilters);
  setError('');  // 필터 변경하면 에러 초기화
};
```

---

## 빈 데이터 처리

```jsx
// 기록 없을 때
{items.length === 0 && !loading && (
  <div className={styles.emptyState}>
    <span>📋</span>
    <p>예측 기록이 없습니다.</p>
  </div>
)}
```

---

## 에러 메시지 문구 가이드

| 상황 | 표시 문구 |
|---|---|
| 서버 연결 실패 | "서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요." |
| 요원 부족 | "팀 A에 요원 5명을 선택해주세요." |
| 맵 미선택 | "맵을 선택해주세요." |
| 알 수 없는 오류 | "오류가 발생했습니다. 다시 시도해주세요." |
| API 400 | 응답 메시지 그대로 표시 |
