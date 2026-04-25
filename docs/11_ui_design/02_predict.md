# 02. 승률 예측 화면 설계 (`/predict`)

> **URL:** `/predict`  
> **파일:** `src/app/predict/page.js` + `src/app/predict/page.module.css`  
> **렌더링:** CSR (Client-Side Rendering) — `'use client'`, 동적 API 호출

---

## 1. 화면 목적

팀 A / 팀 B의 에이전트 구성(각 5명)과 맵을 선택한 뒤, FastAPI 백엔드에 예측을 요청하고 결과(승률 게이지, 신뢰도 배지, 역할군 레이더 차트, 피처 중요도 바차트)를 시각적으로 보여준다.

---

## 2. 전체 레이아웃 다이어그램

### 2-1. 입력 단계 (결과 없음)

```
┌─────────────────────────────────────────────────────────────────┐
│ Navbar                                                          │
├─────────────────────────────────────────────────────────────────┤
│ PageWrapper                                                     │
│                                                                 │
│  h1  "승률 예측"                                                │
│  [ErrorMessage — 오류 시만 표시]                                │
│                                                                 │
│  ┌── 2컬럼 layout ─────────────────────────────────────────┐   │
│  │  ┌── leftPanel ──────────────┐ ┌── rightPanel ────────┐ │   │
│  │  │ ┌── MapSelector Panel ─┐  │ │ ┌── AgentPicker B ─┐ │ │   │
│  │  │ │  맵  [드롭다운]       │  │ │ │  팀 B  0/5       │ │ │   │
│  │  │ └───────────────────────┘  │ │ │  [역할 필터 탭]   │ │ │   │
│  │  │                            │ │ │  [에이전트 그리드] │ │ │   │
│  │  │ ┌── AgentPicker A ──────┐  │ │ └──────────────────┘ │ │   │
│  │  │ │  팀 A  0/5            │  │ └──────────────────────┘ │   │
│  │  │ │  [역할 필터 탭]        │  │                          │   │
│  │  │ │  [에이전트 카드 그리드] │  │                          │   │
│  │  │ └───────────────────────┘  │                          │   │
│  │  └────────────────────────────┘                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌── TeamSlot 2열 ──────────────────────────────────────────┐   │
│  │  ┌─────────────────────────┐ ┌────────────────────────┐  │   │
│  │  │ 팀 A 선택 현황           │ │ 팀 B 선택 현황          │  │   │
│  │  │ [□][□][□][□][□]         │ │ [□][□][□][□][□]         │  │   │
│  │  └─────────────────────────┘ └────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌── PredictButton ─────────────────────────────────────────┐   │
│  │          [ 승률 예측하기 ]  (비활성: 회색)                │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 2-2. 결과 단계 (예측 완료 후 스크롤 아래)

```
│  ┌── resultSection ─────────────────────────────────────────┐   │
│  │  ┌── resultHeader ─────────────────────────────────────┐ │   │
│  │  │  "예측 결과"             [신뢰도 높음 🟢]           │ │   │
│  │  └─────────────────────────────────────────────────────┘ │   │
│  │                                                           │   │
│  │  ┌── WinRateGauge (중앙 정렬) ──────────────────────────┐ │   │
│  │  │          팀 A 예측 승률                               │ │   │
│  │  │    ╭──────────────────╮                              │ │   │
│  │  │   ╱    67%  (big)      ╲                             │ │   │
│  │  │  ╱  RadialBarChart      ╲                            │ │   │
│  │  │   ╲                    ╱                             │ │   │
│  │  │    ╰──────────────────╯                              │ │   │
│  │  │         팀 B 예측 승률: 33%                           │ │   │
│  │  └──────────────────────────────────────────────────────┘ │   │
│  │                                                           │   │
│  │  ┌── resultCharts 2열 ──────────────────────────────────┐ │   │
│  │  │  ┌── RoleRadarChart ──────┐ ┌── FeatureImportanceBar┐ │   │
│  │  │  │  팀 역할군 비교         │ │  피처 중요도 Top 8     │ │   │
│  │  │  │  RadarChart            │ │  BarChart (horizontal) │ │   │
│  │  │  └───────────────────────┘ └───────────────────────┘ │   │
│  │  └──────────────────────────────────────────────────────┘ │   │
│  └───────────────────────────────────────────────────────────┘   │
```

---

## 3. 컴포넌트 트리

```
PredictPage (page.js)                              [Client Component]
├── PageWrapper
├── h1.pageTitle
├── ErrorMessage?                                  ← error 상태 시만 렌더
├── div.layout (2-col grid)
│   ├── div.leftPanel
│   │   ├── div.section  (MapSelector 래퍼)
│   │   │   ├── p.sectionLabel  "맵"
│   │   │   └── MapSelector
│   │   │       └── select.select
│   │   └── AgentPicker (팀 A)
│   │       ├── div.section
│   │       │   ├── div.header (팀 A | 0/5)
│   │       │   ├── RoleFilter
│   │       │   │   └── button.btn × 5 (전체/타격대/척후병/전략가/감시자)
│   │       │   └── div.grid
│   │       │       └── AgentCard × N
│   │       │           ├── div.imgWrap > Image
│   │       │           ├── span.name
│   │       │           ├── span.roleDot
│   │       │           └── span.checkMark?  ← selected 시만
│   └── div.rightPanel
│       └── AgentPicker (팀 B)  ← 구조 동일
├── div.teamSlots (2-col grid)
│   ├── TeamSlot (팀 A)
│   │   └── div.slot × 5
│   │       ├── div.slotImg > Image?
│   │       └── span.slotName
│   └── TeamSlot (팀 B)
├── PredictButton
│   └── button.btn  (loading 시 스피너)
└── div.resultSection?                            ← result 상태 시만 렌더
    ├── div.resultHeader
    │   ├── h2.resultTitle
    │   └── ConfidenceBadge
    ├── WinRateGauge
    │   └── RadialBarChart (recharts)
    └── div.resultCharts (2-col grid)
        ├── RoleRadarChart
        │   └── RadarChart (recharts)
        └── FeatureImportanceBar
            └── BarChart (recharts, layout="vertical")
```

---

## 4. 컴포넌트 명세

### 4-1. MapSelector

| 항목 | 내용 |
|------|------|
| 파일 | `src/components/predict/MapSelector.js` |
| Props | `maps: string[]`, `value: string`, `onChange: (v: string) => void` |

**레이아웃:**
```
.wrap   → flex flex-col gap-2
.label  → text-xs font-bold uppercase tracking-widest, color: muted
.select → px-3 py-2 rounded-lg, background: panel, border: valo-border
```

### 4-2. RoleFilter

| 항목 | 내용 |
|------|------|
| 파일 | `src/components/predict/RoleFilter.js` |
| Props | `active: string`, `onChange: (role: string) => void` |
| 내부 상태 | 없음 (외부 상태를 props로 수신) |

**버튼 탭 목록:** `전체`, `타격대`, `척후병`, `전략가`, `감시자`

| 상태 | CSS 클래스 | 스타일 |
|------|-----------|--------|
| 기본 | `.btn` | background: panel, border: valo-border, color: muted |
| hover | `.btn:hover` | border-color: muted, color: text |
| 활성 | `.active` | border-color: red, color: red, background: red/8% |

### 4-3. AgentCard

| 항목 | 내용 |
|------|------|
| 파일 | `src/components/predict/AgentCard.js` |
| Props | `agent: {name, role}`, `selected: bool`, `disabled: bool`, `onClick: () => void` |

**상태별 시각:**
| 상태 | 스타일 |
|------|--------|
| 기본 | border: valo-border, background: valo-panel |
| hover | border: muted, background: panel-alt |
| selected | border: valo-red, background: red/8%, ✓ 체크마크 표시 |
| disabled | opacity: 30%, cursor: not-allowed |

**역할 도트:** 에이전트 하단에 2px 원형 도트, 역할별 색상 적용

**에이전트 이미지:** `media.valorant-api.com` UUID 기반 이미지 (Next.js `Image` 컴포넌트)

### 4-4. AgentPicker

| 항목 | 내용 |
|------|------|
| 파일 | `src/components/predict/AgentPicker.js` |
| Props | `agents`, `selectedTeam`, `teamLabel`, `onAgentSelect`, `onAgentRemove` |
| 내부 상태 | `activeRole: string` (기본값: '전체') |

**선택 제한 로직:**
- `selectedTeam.length >= 5` → 미선택 에이전트에 `disabled` 적용
- 이미 선택된 에이전트 클릭 → `onAgentRemove` 호출
- 상대팀에서 선택된 에이전트는 상위 페이지에서 필터링 후 전달

**에이전트 그리드:**
```
grid-template-columns: repeat(auto-fill, minmax(64px, 1fr))
gap: 0.5rem
```

### 4-5. TeamSlot

| 항목 | 내용 |
|------|------|
| 파일 | `src/components/predict/TeamSlot.js` |
| Props | `selected: string[]`, `label: string` |

**슬롯 렌더링 (항상 5개):**
- 선택됨: 에이전트 이미지 + 이름
- 비어있음: 점선 테두리 + `+` 아이콘

### 4-6. PredictButton

| 항목 | 내용 |
|------|------|
| 파일 | `src/components/predict/PredictButton.js` |
| Props | `onClick`, `loading: bool`, `disabled: bool` |

| 상태 | 시각 |
|------|------|
| 기본 | 빨간 배경, 흰 텍스트 "승률 예측하기" |
| hover | 배경 약간 어두워짐 + 1px 위로 상승 + 그림자 |
| loading | 회전 스피너 + "예측 중..." |
| disabled | 40% opacity, no hover 효과 |

### 4-7. WinRateGauge

| 항목 | 내용 |
|------|------|
| 파일 | `src/components/result/WinRateGauge.js` |
| Props | `probability: number` (0~1) |
| 차트 | Recharts `RadialBarChart` (180×180px) |

**색상 분기:**
| 범위 | 색상 |
|------|------|
| ≥ 60% | `--color-confidence-high` (초록) |
| 40~60% | `#f59e0b` (노랑) |
| < 40% | `#ef4444` (빨강) |

**텍스트 오버레이:** SVG `<text>` 태그로 차트 중앙에 퍼센트 값 표시

### 4-8. ConfidenceBadge

| 항목 | 내용 |
|------|------|
| 파일 | `src/components/result/ConfidenceBadge.js` |
| Props | `confidence: number` (0~1) |

**레벨 분기:**
| confidence | 레벨 | 표시 | 색상 |
|-----------|------|------|------|
| ≥ 0.75 | high | 신뢰도 높음 | 초록 |
| 0.55~0.75 | medium | 신뢰도 보통 | 주황 |
| < 0.55 | low | 신뢰도 낮음 | 빨강 |

### 4-9. RoleRadarChart

| 항목 | 내용 |
|------|------|
| 파일 | `src/components/result/RoleRadarChart.js` |
| Props | `roleCountsA: number[]`, `roleCountsB: number[]` (각 4개: 타격대/척후병/전략가/감시자 순) |
| 차트 | Recharts `RadarChart`, 260px 높이, `ResponsiveContainer` |

**데이터 구조:**
```js
[
  { role: '타격대', A: n, B: n },
  { role: '척후병', A: n, B: n },
  { role: '전략가', A: n, B: n },
  { role: '감시자', A: n, B: n },
]
```

**색상:** 팀 A = `--color-valo-red`, 팀 B = `--color-role-initiator` (청록)

### 4-10. FeatureImportanceBar

| 항목 | 내용 |
|------|------|
| 파일 | `src/components/result/FeatureImportanceBar.js` |
| Props | `featureImportance: {feature: string, importance: number}[]` |
| 차트 | Recharts `BarChart` (layout="vertical"), 상위 8개, 220px 높이 |

**색상:** 1위 피처 = `--color-valo-red`, 나머지 = `--color-valo-muted`

---

## 5. 상태 흐름

```
[초기화]
useEffect() → fetchMaps() + fetchAgents() (병렬)
           → setMaps / setSelectedMap(maps[0]) / setAgents

[에이전트 선택]
AgentPicker.onAgentSelect(name) → setTeamA/setTeamB (append)
AgentPicker.onAgentRemove(name) → setTeamA/setTeamB (filter out)

상대팀 필터링:
  agents.filter(a => !allSelected.includes(a.name) || teamX.includes(a.name))
  → 상대팀 선택 에이전트는 AgentPicker에서 아예 숨김

[예측 실행]
PredictButton.onClick → handlePredict()
  setLoading(true) → predictWinRate({map, team_a, team_b})
    성공: setResult(res)
    실패: setError(e.message)
  setLoading(false)

[버튼 활성 조건]
canPredict = selectedMap && teamA.length === 5 && teamB.length === 5

[결과 렌더]
result !== null → resultSection 표시
  result.win_probability → WinRateGauge
  result.confidence → ConfidenceBadge
  result.role_counts.team_a/b → RoleRadarChart
  result.feature_importance → FeatureImportanceBar
```

---

## 6. 인터랙션 정의

| 사용자 액션 | 상태 변화 | UI 반응 |
|-------------|-----------|---------|
| 맵 드롭다운 선택 | `selectedMap` 변경 | 드롭다운 표시값 변경 |
| 역할 필터 탭 클릭 | `activeRole` 변경 | 해당 역할 에이전트만 그리드에 표시 |
| 에이전트 카드 클릭 (미선택) | `teamA/B` 배열에 추가 | 카드 selected 스타일, TeamSlot 업데이트, 카운터 증가 |
| 에이전트 카드 클릭 (선택됨) | `teamA/B`에서 제거 | 카드 기본 스타일로 복귀 |
| 5명 선택 완료 | — | 나머지 에이전트 disabled (반투명) |
| 예측 버튼 클릭 | `loading: true` | 버튼 스피너 + "예측 중..." |
| 예측 완료 | `result` 설정 | resultSection 등장, 차트 렌더링 |
| 예측 실패 | `error` 설정 | 상단 빨간 ErrorMessage 배너 |
| ErrorMessage X 클릭 | `error: null` | 배너 사라짐 |

---

## 7. CSS 변수 사용 목록

| 변수 | 사용 위치 |
|------|----------|
| `--color-valo-red` | PredictButton 배경, AgentCard selected border, WinRateGauge (60%↑), RoleRadarChart 팀A |
| `--color-valo-red-dark` | PredictButton hover 배경 |
| `--color-valo-panel` | 모든 카드/패널 배경 |
| `--color-valo-panel-alt` | AgentCard hover, resultSection 내부 |
| `--color-valo-border` | 모든 테두리, TeamSlot 빈 슬롯, RadarChart PolarGrid |
| `--color-valo-text` | 페이지 타이틀, AgentCard 이름 |
| `--color-valo-muted` | 라벨들, RoleFilter 기본, FeatureImportanceBar 나머지 바 |
| `--color-role-initiator` | RoleRadarChart 팀B 색상 |
| `--color-confidence-high` | WinRateGauge 60%↑, ConfidenceBadge high |

---

## 8. 반응형 처리

| 요소 | 데스크탑 (>768px) | 모바일 (<768px) |
|------|-------------------|----------------|
| `.layout` (AgentPicker 영역) | 2컬럼 | 1컬럼 |
| `.resultCharts` | 2컬럼 | 1컬럼 |
| `.teamSlots` | 2컬럼 | 1컬럼 |
| AgentCard 그리드 | `minmax(64px)` auto-fill | 동일 (좁아지면 자동 축소) |

```css
@media (max-width: 768px) {
  .layout, .resultCharts, .teamSlots {
    grid-template-columns: 1fr;
  }
}
```

---

## 9. API 연동

**엔드포인트:** `POST /predict`  
**요청:**
```json
{
  "map": "Ascent",
  "team_a": ["Jett", "Omen", "Sova", "Killjoy", "Skye"],
  "team_b": ["Phoenix", "Viper", "Fade", "Sage", "Chamber"]
}
```
**응답:**
```json
{
  "win_probability": 0.67,
  "confidence": 0.81,
  "role_counts": {
    "team_a": [1, 1, 1, 1],
    "team_b": [1, 1, 1, 1]
  },
  "feature_importance": [
    { "feature": "duelist_diff", "importance": 0.142 },
    ...
  ]
}
```
