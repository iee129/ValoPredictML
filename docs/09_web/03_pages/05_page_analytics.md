> ⚠️ **범위 외**: Next.js 미사용. UI는 Streamlit 로컬 도구로 대체. 본문은 참고용으로 보존된다.

# 05. 통계 분석 페이지 (`/analytics`)

**파일:** `src/app/analytics/page.js` + `src/app/analytics/page.module.css`

---

## 목적

- 전체 예측 데이터 기반 통계 집계 표시
- 맵별 평균 승률
- 가장 많이 선택된 요원 Top 10
- 주요 수치 요약 카드

---

## UI 구조

```
┌──────────────────────────────────────────────────────────────┐
│                         Navbar                               │
├──────────────────────────────────────────────────────────────┤
│  통계 분석                                                    │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │총 예측 수 │  │평균 승률  │  │평균 신뢰도│  │최다 선택맵│   │
│  │ 1,234   │  │  54.2%  │  │  72.4%  │  │  Ascent │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  맵별 평균 승률                    인기 요원 Top 10           │
│  ┌────────────────────────┐       ┌──────────────────────┐  │
│  │ Ascent ████████ 56%   │       │ Jett   ████████ 156  │  │
│  │ Bind   ██████   52%   │       │ Sage   ███████  142  │  │
│  │ Haven  █████    49%   │       │ Sova   ██████   138  │  │
│  │ ...                   │       │ ...                  │  │
│  └────────────────────────┘       └──────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

---

## 상태 변수

```js
const [data, setData] = useState(null);    // fetchAnalytics() 전체 응답
const [loading, setLoading] = useState(true);
const [error, setError] = useState(null);
```

단순한 상태 구조. 필터/페이지네이션 없음.

---

## 데이터 페칭

```js
useEffect(() => {
  const load = async () => {
    try {
      const result = await fetchAnalytics();
      setData(result);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };
  load();
}, []);  // 마운트 시 1회만 실행
```

---

## API 응답 구조

```json
{
  "total_predictions": 1234,
  "avg_win_probability": 0.542,
  "avg_confidence": 72.4,
  "map_count": 8,
  "most_common_map": "Ascent",
  "map_stats": [
    { "map": "Ascent", "avg_win_rate": 0.56, "count": 234 },
    { "map": "Bind", "avg_win_rate": 0.52, "count": 198 },
    ...
  ],
  "top_agents": [
    { "name": "Jett", "role": "Duelist", "count": 156 },
    { "name": "Sage", "role": "Sentinel", "count": 142 },
    ...
  ]
}
```

---

## StatCard 렌더링

```jsx
<div className={styles.statsGrid}>
  <StatCard label="총 예측 수" value={data.total_predictions.toLocaleString()} />
  <StatCard label="평균 승률" value={`${(data.avg_win_probability * 100).toFixed(1)}%`} />
  <StatCard label="평균 신뢰도" value={`${data.avg_confidence.toFixed(1)}%`} />
  <StatCard label="최다 선택 맵" value={data.most_common_map} />
</div>
```

---

## 맵별 승률 바 차트 (커스텀 CSS)

Recharts 미사용. 순수 CSS `width` 비율로 구현.

```jsx
{data.map_stats.map(stat => {
  const maxRate = Math.max(...data.map_stats.map(s => s.avg_win_rate));
  const barWidth = (stat.avg_win_rate / maxRate) * 100 + '%';
  return (
    <div key={stat.map} className={styles.barRow}>
      <span className={styles.barLabel}>{stat.map}</span>
      <div className={styles.barTrack}>
        <div className={styles.barFill} style={{ width: barWidth }} />
      </div>
      <span className={styles.barValue}>
        {(stat.avg_win_rate * 100).toFixed(1)}%
      </span>
    </div>
  );
})}
```

---

## 인기 요원 차트 (커스텀 CSS)

```jsx
{(() => {
  const maxCount = data.top_agents[0]?.count ?? 1;
  return data.top_agents.map(agent => (
    <div key={agent.name} className={styles.barRow}>
      <span className={styles.barLabel}>{agent.name}</span>
      <div className={styles.barTrack}>
        <div
          className={styles.barFill}
          style={{ width: (agent.count / maxCount) * 100 + '%' }}
        />
      </div>
      <span className={styles.barValue}>{agent.count}</span>
    </div>
  ));
})()}
```

---

## 2열 레이아웃

```css
/* page.module.css */
.chartsGrid {
  @apply grid grid-cols-1 lg:grid-cols-2 gap-8;
}
```

---

## 에러/로딩 처리

```jsx
if (loading) return <LoadingSpinner />;
if (error) return <ErrorMessage message={error} />;
if (!data) return null;
```

---

## 비주얼 스펙

### 배경 레이아웃

| 영역 | 토큰 | 비고 |
|------|------|------|
| 페이지 전체 | `var(--color-valo-bg)` | 순수 블랙 |
| StatCard (×4) | `var(--color-valo-panel)` | 1px `var(--color-valo-border)` 테두리 |
| 바 차트 패널 (×2) | `var(--color-valo-panel)` | 2열 그리드 각 패널 |

---

### 페이지 헤더 타이포그래피

```css
/* page.module.css */
.pageTitle {
  font-family: 'Bebas Neue', sans-serif;
  font-size: clamp(2rem, 5vw, 3.5rem);
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--color-valo-text);
  border-left: 3px solid var(--color-valo-red);
  padding-left: 0.75rem;
}
```

---

### clip-path 적용 지점

| 컴포넌트 | clip-path 사용 이유 |
|----------|---------------------|
| StatCard ×4 | 수치 강조 카드 — 택티컬 각진 형태, 위계 시각화 |
| 바 차트 패널 헤더 | 섹션 제목 영역 시각적 분리 |

```css
/* StatCard — 우상단 8px 잘림 */
.statCard {
  clip-path: polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%);
  background: var(--color-valo-panel);
  border: 1px solid var(--color-valo-border);
  padding: 1.25rem 1.5rem;
}
.statValue {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 2.25rem;
  color: var(--color-valo-red);
}
.statLabel {
  font-family: Pretendard, sans-serif;
  font-size: 0.75rem;
  color: var(--color-valo-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
```

---

### 레드 강조 포인트 + 바 차트 스타일

| 요소 | 강조 방식 | 토큰 |
|------|-----------|------|
| StatCard 수치 | 텍스트 강조색 | `--color-valo-red` |
| 차트 섹션 헤더 | 좌측 3px 세로 강조 바 | `--color-valo-red` |
| 맵별 승률 바 fill | 레드 그라디언트 | `--color-valo-red` → `--color-valo-red-end` |
| 인기 요원 바 fill | 레드 그라디언트 | `--color-valo-red` → `--color-valo-red-end` |

```css
/* 차트 섹션 헤더 */
.chartTitle {
  border-left: 3px solid var(--color-valo-red);
  padding-left: 0.75rem;
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1.3rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--color-valo-text);
}

/* 바 트랙 (배경) */
.barTrack {
  background: var(--color-valo-border);
  border-radius: 2px;
  flex: 1;
  height: 6px;
}

/* 바 fill — 레드 그라디언트 */
.barFill {
  background: linear-gradient(
    90deg,
    var(--color-valo-red)     0%,
    var(--color-valo-red-end) 100%
  );
  height: 100%;
  border-radius: 2px;
  transition: width 0.4s ease;
}

/* 바 레이블 / 수치 */
.barLabel {
  font-family: Pretendard, sans-serif;
  font-size: 0.875rem;
  color: var(--color-valo-text);
  min-width: 80px;
}
.barValue {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 0.9rem;
  color: var(--color-valo-muted);
  letter-spacing: 0.03em;
}
```

---

## API 명세

| 메서드 | URL | 역할 |
|---|---|---|
| `GET` | `/analytics` | 전체 통계 집계 데이터 |

→ 자세한 API 구조: [08_api_integration/02_fastapi_endpoints.md](../08_api_integration/02_fastapi_endpoints.md)

---

## 관련 문서

- 커스텀 CSS 바 차트 상세: [07_visualization/02_custom_css_charts.md](../07_visualization/02_custom_css_charts.md)
