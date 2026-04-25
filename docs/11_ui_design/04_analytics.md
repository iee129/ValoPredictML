# 04. 분석 대시보드 화면 설계 (`/analytics`)

> **URL:** `/analytics`  
> **파일:** `src/app/analytics/page.js` + `src/app/analytics/page.module.css`  
> **렌더링:** CSR (Client-Side Rendering) — `'use client'`, 마운트 시 단일 API 호출

---

## 1. 화면 목적

모든 예측 기록을 집계한 통계를 시각화한다. 에이전트 사용 빈도, 맵별 예측 횟수, 전체 예측 건수, 평균 승률 등을 한눈에 파악할 수 있는 대시보드.

---

## 2. 전체 레이아웃 다이어그램

### 2-1. 로딩 중

```
┌─────────────────────────────────────────────────────────────────┐
│ Navbar                                                          │
├─────────────────────────────────────────────────────────────────┤
│ PageWrapper                                                     │
│                                                                 │
│                    [LoadingSpinner]                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2-2. 로드 완료

```
┌─────────────────────────────────────────────────────────────────┐
│ Navbar                                                          │
├─────────────────────────────────────────────────────────────────┤
│ PageWrapper                                                     │
│                                                                 │
│  h1  "분석 대시보드"                                            │
│                                                                 │
│  ┌── StatCard Grid (auto-fit, min 180px) ───────────────────┐  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌───────┐ ┌────────┐  │  │
│  │  │ 총 예측 횟수  │ │  평균 승률  │ │자주 쓴│ │많이 예측│  │  │
│  │  │    1,234     │ │    52%      │ │에이전트│ │  맵    │  │  │
│  │  └──────────────┘ └──────────────┘ └───────┘ └────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌── charts 2열 ─────────────────────────────────────────────┐  │
│  │  ┌── chartCard (좌) ──────────────────────────────────┐   │  │
│  │  │  에이전트 사용 빈도 Top 10                           │   │  │
│  │  │  ┌ Jett    ████████████████████████████████ 234 ┐  │   │  │
│  │  │  │ Phoenix ████████████████████           189 │  │   │  │
│  │  │  │ ...     ...                                │  │   │  │
│  │  │  └─────────────────────────────────────────────┘  │   │  │
│  │  └────────────────────────────────────────────────────┘   │  │
│  │  ┌── chartCard (우) ──────────────────────────────────┐   │  │
│  │  │  맵별 예측 횟수                                      │   │  │
│  │  │  ┌ Ascent  ██████████████████████████████ 320  ┐  │   │  │
│  │  │  │ Bind    ████████████████████           270  │  │   │  │
│  │  │  │ Icebox  ████████████████               245  │  │   │  │
│  │  │  │ ...     ...                                 │  │   │  │
│  │  │  └─────────────────────────────────────────────┘  │   │  │
│  │  └────────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 컴포넌트 트리

```
AnalyticsPage (page.js)                        [Client Component]
├── [loading] → PageWrapper > LoadingSpinner
├── [error]   → PageWrapper > ErrorMessage
└── [데이터 있음]
    └── PageWrapper
        ├── h1.pageTitle
        ├── div.grid (StatCard × 4)
        │   ├── StatCard  (총 예측 횟수)
        │   ├── StatCard  (평균 승률)
        │   ├── StatCard  (가장 많이 쓴 에이전트)
        │   └── StatCard  (가장 많이 예측한 맵)
        └── div.charts (2-col grid)
            ├── div.chartCard  (에이전트 빈도)
            │   ├── p.chartTitle
            │   └── div.barRow × 10
            │       ├── span.barLabel  에이전트명
            │       ├── div.barTrack
            │       │   └── div.barFill  (width: % 동적)
            │       └── span.barValue  횟수
            └── div.chartCard  (맵별 횟수)
                ├── p.chartTitle
                └── div.barRow × N
                    ├── span.barLabel  맵명
                    ├── div.barTrack
                    │   └── div.barFill  (width: % 동적)
                    └── span.barValue  횟수
```

---

## 4. 컴포넌트 명세

### 4-1. StatCard 요약 그리드

| StatCard | title | value | desc |
|----------|-------|-------|------|
| 1 | 총 예측 횟수 | `data.total_predictions` | 누적 예측 기록 |
| 2 | 평균 승률 | `round(data.avg_win_probability * 100)%` | 팀 A 기준 |
| 3 | 가장 많이 쓴 에이전트 | `topAgents[0].name` | `{count}회` |
| 4 | 가장 많이 예측한 맵 | `topMaps[0].map` | `{count}회` |

**그리드:**
```css
.grid {
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}
```

### 4-2. 가로 바차트 (커스텀)

Recharts 없이 순수 CSS로 구현된 커스텀 바차트.

**바 너비 계산:**
```js
maxAgentCount = topAgents[0]?.count ?? 1
barWidth = (agent.count / maxAgentCount) * 100 + '%'
```
→ 가장 많은 에이전트/맵을 100%로 하여 상대적 비율로 표현

**레이아웃:**
```
.chartCard  → p-5 rounded-xl, background: panel, border: valo-border
.chartTitle → text-sm font-bold, color: valo-text, mb-4
.barRow     → flex items-center gap-3, mb-2
.barLabel   → text-xs w-20 text-right shrink-0, color: muted
.barTrack   → flex-1 h-2 rounded-full, background: valo-border
.barFill    → h-full rounded-full, background: valo-red, transition: width
.barValue   → text-xs w-10 shrink-0, color: muted
```

**에이전트 차트:** 상위 10개 (`topAgents.slice(0, 10)`)  
**맵 차트:** 전체 맵 목록 (`topMaps` 전체)

---

## 5. 상태 흐름

```
[초기화]
loading = true, error = null, data = null

[마운트]
useEffect([]) → fetchAnalytics()
  성공: setData(res)
  실패: setError(e.message)
  finally: setLoading(false)

[렌더 분기]
loading === true  → <PageWrapper><LoadingSpinner /></PageWrapper>
error !== null    → <PageWrapper><ErrorMessage message={error} /></PageWrapper>
data !== null     → 실제 대시보드 렌더

데이터 파생:
  topAgents = data?.top_agents ?? []
  topMaps   = data?.map_stats ?? []
  maxAgentCount = topAgents[0]?.count ?? 1  ← 바 너비 기준값
  maxMapCount   = topMaps[0]?.count ?? 1
```

---

## 6. 인터랙션 정의

| 사용자 액션 | 반응 |
|-------------|------|
| 페이지 진입 | API 호출 → 로딩 스피너 표시 |
| 로드 완료 | 스피너 → 대시보드 렌더링 |
| API 실패 | 스피너 → ErrorMessage 표시 |

> 이 화면은 사용자 인터랙션이 없는 순수 읽기 전용 대시보드.  
> 향후 날짜 범위 필터, 새로고침 버튼 추가 가능.

---

## 7. CSS 변수 사용 목록

| 변수 | 사용 위치 |
|------|----------|
| `--color-valo-red` | 바차트 `.barFill` 배경색 |
| `--color-valo-panel` | chartCard 배경 |
| `--color-valo-border` | chartCard 테두리, `.barTrack` 배경 (트랙 색상) |
| `--color-valo-text` | `.chartTitle`, StatCard value |
| `--color-valo-muted` | `.barLabel`, `.barValue`, StatCard title/desc |

---

## 8. 반응형 처리

| 요소 | 데스크탑 (>768px) | 모바일 (<768px) |
|------|-------------------|----------------|
| StatCard 그리드 | 4열 (auto-fit) | 1~2열 (minmax 180px) |
| `.charts` | 2컬럼 (1fr 1fr) | 1컬럼 |

```css
@media (max-width: 768px) {
  .charts {
    grid-template-columns: 1fr;
  }
}
```

---

## 9. API 연동

**엔드포인트:** `GET /analytics`

**응답:**
```json
{
  "total_predictions": 1234,
  "avg_win_probability": 0.52,
  "top_agents": [
    { "name": "Jett", "count": 234 },
    { "name": "Phoenix", "count": 189 },
    ...
  ],
  "map_stats": [
    { "map": "Ascent", "count": 320 },
    { "map": "Bind", "count": 270 },
    ...
  ]
}
```

**Null 방어:**
```js
topAgents[0]?.name ?? '-'
topAgents[0] ? `${topAgents[0].count}회` : ''
```
→ 데이터가 없는 초기 상태에서도 UI 깨지지 않음

---

## 10. 향후 개선 아이디어

| 기능 | 설명 |
|------|------|
| 날짜 범위 필터 | 특정 기간의 통계만 조회 |
| 역할군별 분포 차트 | 전체 에이전트 선택 중 각 역할군 비율 파이차트 |
| 승률 분포 히스토그램 | 예측 결과 승률 구간별 빈도 |
| 새로고침 버튼 | 수동으로 데이터 갱신 |
| 에이전트 클릭 → 상세 | 특정 에이전트 포함 기록 필터링 |
