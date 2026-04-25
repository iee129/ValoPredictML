# 04. 프론트엔드 파일 상세 (`valo_predict_system/`)

## 1. 폴더 전체 구조

```
valo_predict_system/
├── src/
│   └── app/
│       ├── layout.js                   # 루트 레이아웃 (공통 Navbar, 폰트)
│       ├── globals.css                 # 전역 CSS + Tailwind 설정
│       ├── page.js                     # "/" 홈 대시보드
│       ├── predict/
│       │   ├── page.js                 # "/predict" 승률 예측 페이지
│       │   └── predict.module.css
│       ├── analytics/
│       │   ├── page.js                 # "/analytics" 통계 분석 페이지
│       │   └── analytics.module.css
│       ├── history/
│       │   ├── page.js                 # "/history" 예측 기록 페이지
│       │   └── history.module.css
│       └── components/
│           ├── layout/
│           │   ├── Navbar.js
│           │   └── navbar.module.css
│           ├── predict/
│           │   ├── AgentCard.js        # 요원 카드 (선택/해제)
│           │   ├── AgentPicker.js      # 요원 선택 그리드 + 역할 필터
│           │   ├── TeamSlot.js         # 선택된 5명 미리보기
│           │   ├── MapSelector.js      # 맵 드롭다운
│           │   └── [각각].module.css
│           └── result/
│               ├── WinRateGauge.js     # 승률 게이지 (RadialBarChart)
│               ├── ConfidenceBadge.js  # 신뢰도 배지
│               ├── RoleRadarChart.js   # 역할군 레이더 차트
│               ├── FeatureImportanceBar.js # 피처 중요도 바 차트
│               └── [각각].module.css
├── public/
│   └── agents/                         # 요원 아이콘 이미지 (PNG)
├── src/lib/
│   └── api.js                          # FastAPI 호출 클라이언트
├── package.json
├── next.config.mjs
├── postcss.config.mjs
└── .env.local                          # NEXT_PUBLIC_API_URL (git 제외)
```

---

## 2. App Router 라우팅 구조

```
/                    → src/app/page.js              # 홈 대시보드
/predict             → src/app/predict/page.js       # 승률 예측
/analytics           → src/app/analytics/page.js     # 통계 분석
/history             → src/app/history/page.js        # 예측 기록
```

---

## 3. 파일별 역할 상세

### 3.1 `src/app/layout.js` — 루트 레이아웃

```javascript
// src/app/layout.js
import { Inter } from 'next/font/google';
import Navbar from './components/layout/Navbar';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata = {
  title: 'ValoPredictML',
  description: 'Valorant 팀 조합 승률 예측 시스템',
};

export default function RootLayout({ children }) {
  return (
    <html lang="ko">
      <body className={inter.className}>
        <Navbar />
        <main>{children}</main>
      </body>
    </html>
  );
}
```

**책임:**
- 공통 HTML 구조 (html, body 태그)
- Navbar 렌더링
- 폰트 설정 (Inter)
- 전역 메타데이터

---

### 3.2 `src/app/globals.css` — 전역 CSS

```css
@import "tailwindcss";

:root {
  --valo-red: #FF4655;
  --valo-dark: #0F1923;
  --valo-gray: #1F2937;
  --valo-light-gray: #374151;
  --valo-accent: #FF6B35;
  --valo-white: #ECE8E1;
  --valo-teal: #00C4CC;
}

* {
  box-sizing: border-box;
}

body {
  background-color: var(--valo-dark);
  color: var(--valo-white);
}
```

---

### 3.3 `src/lib/api.js` — API 클라이언트

```javascript
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function predictWinRate(map, teamA, teamB) {
  const res = await fetch(`${BASE_URL}/api/v1/predict`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ map, team_a: teamA, team_b: teamB }),
  });
  if (!res.ok) throw new Error(`Prediction failed: ${res.status}`);
  return res.json();
}

export async function getAgents() {
  const res = await fetch(`${BASE_URL}/api/v1/agents`);
  if (!res.ok) throw new Error('Failed to fetch agents');
  return res.json();
}

export async function getMaps() {
  const res = await fetch(`${BASE_URL}/api/v1/maps`);
  if (!res.ok) throw new Error('Failed to fetch maps');
  return res.json();
}

export async function getHistory(page = 1, limit = 20) {
  const res = await fetch(`${BASE_URL}/api/v1/history?page=${page}&limit=${limit}`);
  if (!res.ok) throw new Error('Failed to fetch history');
  return res.json();
}
```

---

### 3.4 컴포넌트 역할 요약

#### `predict/` 컴포넌트

| 컴포넌트 | 역할 | 주요 props |
|---|---|---|
| `AgentCard` | 요원 1개 카드. 클릭 시 선택/해제 | `agent`, `isSelected`, `onClick` |
| `AgentPicker` | 역할 필터 + 요원 그리드. 팀 A/B 구분 | `team`, `selectedAgents`, `onSelect` |
| `TeamSlot` | 선택된 5명 요원 미리보기 슬롯 | `team`, `agents` |
| `MapSelector` | 맵 드롭다운 선택 | `maps`, `selectedMap`, `onChange` |

#### `result/` 컴포넌트

| 컴포넌트 | 역할 | 사용 라이브러리 |
|---|---|---|
| `WinRateGauge` | 팀 A 승률 원형 게이지 | Recharts `RadialBarChart` |
| `ConfidenceBadge` | 신뢰도 뱃지 (High/Medium/Low) | — |
| `RoleRadarChart` | 양 팀 역할군 분포 레이더 차트 | Recharts `RadarChart` |
| `FeatureImportanceBar` | 피처 중요도 수평 바 차트 | Recharts `BarChart` |

---

### 3.5 CSS 모듈 규칙

Tailwind CSS v4 사용 시 모든 스타일은 `.module.css`에서 `@apply`로 작성:

```css
/* components/predict/AgentCard.module.css */
@reference "tailwindcss";

.card {
  @apply relative cursor-pointer rounded-lg p-2 border-2
         border-transparent transition-all duration-200;
}

.selected {
  @apply border-[var(--valo-red)] bg-[var(--valo-red)]/10;
}
```

JSX에서 직접 Tailwind 클래스 사용 금지:
```javascript
// ❌ 금지
<div className="bg-red-500 rounded-lg p-4">

// ✅ 올바른 방법
import styles from './agentCard.module.css';
<div className={styles.card}>
```

---

## 4. 페이지별 기능

| 페이지 | URL | 기능 |
|---|---|---|
| 홈 | `/` | 프로젝트 소개, 최근 예측 카드 3개, 빠른 예측 시작 버튼 |
| 예측 | `/predict` | 맵 선택 → 양 팀 요원 선택 → 실시간 승률 + 역할군 차트 |
| 통계 | `/analytics` | 맵별/역할군별 승률 통계, 트렌드 차트 |
| 기록 | `/history` | PostgreSQL 저장된 예측 이력 테이블, 필터링 |

---

## 5. 관련 문서

| 문서 | 내용 |
|---|---|
| [../09_web/](../09_web/) | Next.js 대시보드 전체 설계 상세 |
| [../11_ui_design/](../11_ui_design/) | UI 디자인 가이드, 컬러 시스템 |
| [05_config_and_env.md](05_config_and_env.md) | `.env.local` 설정, 환경변수 목록 |
