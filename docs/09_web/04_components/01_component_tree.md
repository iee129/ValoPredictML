# 01. 전체 컴포넌트 트리

---

## 컴포넌트 계층 구조

```
RootLayout (app/layout.js)
├── Navbar
└── PageWrapper
    │
    ├── [/] HomePage
    │   ├── StatCard × 3
    │   └── PredictionCard × N (인라인)
    │
    ├── [/predict] PredictPage
    │   ├── MapSelector
    │   ├── TeamSlot (팀 A)
    │   ├── TeamSlot (팀 B)
    │   ├── AgentPicker (팀 A 선택용)
    │   │   ├── RoleFilter
    │   │   └── AgentCard × N
    │   ├── AgentPicker (팀 B 선택용)
    │   │   ├── RoleFilter
    │   │   └── AgentCard × N
    │   ├── PredictButton
    │   ├── ErrorMessage (조건부)
    │   └── [결과 영역, result != null]
    │       ├── WinRateGauge (팀 A)
    │       ├── WinRateGauge (팀 B)
    │       ├── ConfidenceBadge
    │       ├── RoleRadarChart
    │       └── FeatureImportanceBar
    │
    ├── [/history] HistoryPage
    │   ├── HistoryFilter
    │   ├── LoadingSpinner (조건부)
    │   ├── HistoryTable
    │   └── Pagination
    │
    └── [/analytics] AnalyticsPage
        ├── LoadingSpinner (조건부)
        ├── ErrorMessage (조건부)
        ├── StatCard × 4
        └── [data != null]
            ├── 맵별 승률 바 차트 (인라인 렌더링)
            └── 인기 요원 차트 (인라인 렌더링)
```

---

## 컴포넌트 의존 관계 표

| 컴포넌트 | 사용하는 컴포넌트 | 사용하는 lib |
|---|---|---|
| `AgentPicker` | `RoleFilter`, `AgentCard` | - |
| `AgentCard` | - | `agentImage.js` |
| `TeamSlot` | - | `agentImage.js` |
| `WinRateGauge` | - | Recharts |
| `RoleRadarChart` | - | Recharts |
| `FeatureImportanceBar` | - | - |
| `HistoryTable` | - | - |
| `Pagination` | - | - |
| `HistoryFilter` | - | - |
| `StatCard` | - | - |
| `LoadingSpinner` | - | - |
| `ErrorMessage` | - | - |
| `Navbar` | - | `next/navigation` |
| `PageWrapper` | - | - |

---

## 컴포넌트 분류

### Presentational (표현 전용)
상태 없이 props만 받아 렌더링:

- `AgentCard` — 요원 카드 (selected/disabled 상태는 props)
- `TeamSlot` — 팀 슬롯 미리보기
- `ConfidenceBadge` — 신뢰도 배지
- `FeatureImportanceBar` — 피처 중요도
- `StatCard` — 통계 카드
- `ErrorMessage` — 에러 메시지
- `LoadingSpinner` — 로딩 스피너
- `HistoryTable` — 기록 테이블
- `Pagination` — 페이지네이션
- `PageWrapper` — 페이지 래퍼

### Stateful (내부 상태 보유)
자체 UI 상태(탭, 현재 경로 등)를 관리:

- `AgentPicker` — `activeRole` 탭 상태
- `RoleFilter` — 선택된 역할군 탭 (부모에서 제어)
- `Navbar` — `usePathname()`으로 현재 경로

### Container (데이터 페칭 + 상태 관리)
모든 page.js 파일:

- `HomePage`, `PredictPage`, `HistoryPage`, `AnalyticsPage`

---

## 폴더 별 컴포넌트 목록

### `src/components/layout/` (2개)

| 컴포넌트 | 파일 쌍 |
|---|---|
| Navbar | `Navbar.js` + `Navbar.module.css` |
| PageWrapper | `PageWrapper.js` + `PageWrapper.module.css` |

### `src/components/predict/` (6개)

| 컴포넌트 | 파일 쌍 |
|---|---|
| AgentCard | `AgentCard.js` + `AgentCard.module.css` |
| AgentPicker | `AgentPicker.js` + `AgentPicker.module.css` |
| MapSelector | `MapSelector.js` + `MapSelector.module.css` |
| PredictButton | `PredictButton.js` + `PredictButton.module.css` |
| RoleFilter | `RoleFilter.js` + `RoleFilter.module.css` |
| TeamSlot | `TeamSlot.js` + `TeamSlot.module.css` |

### `src/components/result/` (4개)

| 컴포넌트 | 파일 쌍 |
|---|---|
| ConfidenceBadge | `ConfidenceBadge.js` + `ConfidenceBadge.module.css` |
| FeatureImportanceBar | `FeatureImportanceBar.js` + `FeatureImportanceBar.module.css` |
| RoleRadarChart | `RoleRadarChart.js` + `RoleRadarChart.module.css` |
| WinRateGauge | `WinRateGauge.js` + `WinRateGauge.module.css` |

### `src/components/history/` (3개)

| 컴포넌트 | 파일 쌍 |
|---|---|
| HistoryFilter | `HistoryFilter.js` + `HistoryFilter.module.css` |
| HistoryTable | `HistoryTable.js` + `HistoryTable.module.css` |
| Pagination | `Pagination.js` + `Pagination.module.css` |

### `src/components/ui/` (3개)

| 컴포넌트 | 파일 쌍 |
|---|---|
| ErrorMessage | `ErrorMessage.js` + `ErrorMessage.module.css` |
| LoadingSpinner | `LoadingSpinner.js` + `LoadingSpinner.module.css` |
| StatCard | `StatCard.js` + `StatCard.module.css` |

---

## 컴포넌트 추가 시 규칙

1. 도메인 폴더에 위치 (`predict/`, `result/`, `history/`, `ui/`)
2. `.js` + `.module.css` 쌍으로 생성
3. `@reference "tailwindcss";`를 `.module.css` 첫 줄에 추가
4. default export 사용
5. props는 구조 분해 할당으로 선언
