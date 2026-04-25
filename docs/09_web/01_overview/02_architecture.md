# 02. 프론트엔드 아키텍처

## 전체 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────┐
│                    사용자 브라우저                            │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                  Next.js App Router                   │  │
│  │                                                       │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │  │
│  │  │  layout.js   │  │   globals    │  │  Navbar    │  │  │
│  │  │ (공통 래퍼)   │  │    .css      │  │ PageWrapper│  │  │
│  │  └──────┬───────┘  └──────────────┘  └────────────┘  │  │
│  │         │                                             │  │
│  │  ┌──────┴──────────────────────────────────────────┐  │  │
│  │  │                  페이지 레이어                    │  │  │
│  │  │  page.js  predict/  history/  analytics/        │  │  │
│  │  └──────┬──────────────────────────────────────────┘  │  │
│  │         │                                             │  │
│  │  ┌──────┴──────────────────────────────────────────┐  │  │
│  │  │               컴포넌트 레이어                     │  │  │
│  │  │  predict/  result/  history/  analytics/  ui/   │  │  │
│  │  └──────┬──────────────────────────────────────────┘  │  │
│  │         │                                             │  │
│  │  ┌──────┴──────────────────────────────────────────┐  │  │
│  │  │                    lib 레이어                    │  │  │
│  │  │          api.js          agentImage.js           │  │  │
│  │  └──────┬──────────────────────────────────────────┘  │  │
│  └─────────┼─────────────────────────────────────────────┘  │
└────────────┼────────────────────────────────────────────────┘
             │ HTTP (fetch / NEXT_PUBLIC_API_URL)
             ▼
┌─────────────────────────────┐
│      FastAPI 백엔드          │
│  POST /predict              │
│  GET  /agents               │
│  GET  /maps                 │
│  GET  /history              │
│  GET  /analytics            │
└─────────────────────────────┘
             │
             ▼
┌─────────────────────────────┐
│     ML 모델 (scikit-learn)   │
│  RandomForest / XGBoost     │
│  win_probability 반환        │
└─────────────────────────────┘
```

---

## 레이어별 역할

### 1. App Router 레이어 (`src/app/`)

Next.js의 파일 시스템 기반 라우팅. 각 폴더가 URL 경로에 1:1 매핑된다.

```
src/app/
├── layout.js         → 공통 레이아웃 (Navbar, 배경색, 폰트)
├── globals.css       → Tailwind @theme, 전역 CSS 변수, body 스타일
├── page.js           → / 홈
├── predict/page.js   → /predict
├── history/page.js   → /history
└── analytics/page.js → /analytics
```

모든 페이지는 `'use client'` 지시어를 사용하는 클라이언트 컴포넌트.  
(예측 결과를 실시간으로 표시해야 하므로 서버 컴포넌트 불가)

---

### 2. 컴포넌트 레이어 (`src/components/`)

도메인별로 5개 폴더로 구성. 각 컴포넌트는 `.js` + `.module.css` 쌍으로 존재.

```
src/components/
├── layout/     → 레이아웃 (Navbar, PageWrapper)
├── predict/    → 예측 입력 UI (AgentPicker, TeamSlot 등)
├── result/     → 예측 결과 시각화 (차트, 배지)
├── history/    → 기록 조회 UI (테이블, 필터, 페이지네이션)
└── ui/         → 공통 UI (로딩, 에러, StatCard)
```

**설계 원칙:**
- 컴포넌트는 순수 표현(presentation) 위주 — 비즈니스 로직은 page.js에
- props로 데이터를 받아 렌더링만 담당
- 상태를 내부에 갖는 경우는 UI 상태(탭 선택, 토글)에만 한정

---

### 3. lib 레이어 (`src/lib/`)

재사용 가능한 유틸리티 모듈.

| 파일 | 역할 |
|---|---|
| `api.js` | FastAPI 통신 함수 모음 (`predictWinRate`, `fetchAgents`, ...) |
| `agentImage.js` | 요원 이름 → UUID → 이미지 URL 변환, 역할군 색상/레이블 맵 |

---

### 4. 스타일 레이어

```
globals.css          → @theme 블록 (CSS 변수 정의), body 기본 스타일
*.module.css         → 컴포넌트별 격리된 CSS (@reference + @apply)
```

Tailwind 유틸리티는 JSX에 직접 쓰지 않고 `.module.css`에서 `@apply`로만 사용.

---

## 클라이언트-서버 데이터 흐름

```
사용자 액션
    │
    ▼
page.js (useState, event handler)
    │ api.js 함수 호출
    ▼
src/lib/api.js
    │ fetch(NEXT_PUBLIC_API_URL + "/endpoint")
    ▼
FastAPI 서버
    │ JSON 응답
    ▼
api.js → page.js (setState)
    │ props 전달
    ▼
컴포넌트 (re-render)
```

---

## 빌드 결과

```
Route (app)                   Size     First Load JS
┌ ○ /                         2.1 kB   105 kB
├ ○ /analytics                3.4 kB   110 kB
├ ○ /history                  4.2 kB   108 kB
└ ○ /predict                  8.7 kB   142 kB

○  (Static)  prerendered as static content
```

`/predict`가 가장 큰 이유: Recharts(RadialBar, Radar) 번들이 포함되기 때문.

---

## 관련 문서

- 상세 컴포넌트 구조 → [04_components/01_component_tree.md](../04_components/01_component_tree.md)
- 데이터 흐름 상세 → [05_state_and_data/02_data_flow.md](../05_state_and_data/02_data_flow.md)
