# 01. 홈 화면 설계 (`/`)

> **URL:** `/`  
> **파일:** `src/app/page.js` + `src/app/page.module.css`  
> **렌더링:** SSG (Static Site Generation) — `metadata` export 포함, 동적 데이터 없음

---

## 1. 화면 목적

ValoPredictML 진입점. 시스템 주요 지표를 요약하고, 각 기능 페이지로 빠르게 이동할 수 있는 내비게이션 허브 역할을 한다.

---

## 2. 전체 레이아웃 다이어그램

```
┌─────────────────────────────────────────────────────────────────┐
│ Navbar (공통)                                                   │
├─────────────────────────────────────────────────────────────────┤
│ PageWrapper (max-w-6xl, mx-auto, py-8 px-4)                     │
│                                                                 │
│  ┌── Hero Section ──────────────────────────────────────────┐  │
│  │  VALOPREDIC_TML  ← 타이틀 (VALO = red accent)           │  │
│  │  발로란트 5v5 팀 구성 승률 예측 시스템 ...   ← 서브타이틀 │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌── StatCard Grid (auto-fit, min 200px) ───────────────────┐  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────┐ ┌───────┐  │  │
│  │  │ 모델 정확도 │ │ 지원 맵     │ │에이전트 │ │피처 수│  │  │
│  │  │   ≥80%     │ │   9개       │ │  24명   │ │ 15개  │  │  │
│  │  └─────────────┘ └─────────────┘ └─────────┘ └───────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌── Quick Links Section ────────────────────────────────────┐  │
│  │  빠른 시작  ← 섹션 타이틀                                 │  │
│  │  ┌─────────────────┐ ┌──────────────────┐ ┌────────────┐ │  │
│  │  │ 🎯 승률 예측     │ │ 📋 예측 기록     │ │ 📊 분석    │ │  │
│  │  │ /predict 링크    │ │ /history 링크    │ │ /analytics │ │  │
│  │  └─────────────────┘ └──────────────────┘ └────────────┘ │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 컴포넌트 트리

```
HomePage (page.js)                           [Server Component]
├── PageWrapper
├── div.hero
│   ├── h1.title
│   │   ├── span.titleAccent  "VALO"
│   │   ├── "PREDICT"
│   │   └── span.titleAccent  "ML"
│   └── p.subtitle
├── div.grid                                 ← StatCard × 4
│   ├── StatCard  (모델 정확도)
│   ├── StatCard  (지원 맵)
│   ├── StatCard  (에이전트 수)
│   └── StatCard  (분석 피처)
└── div.section
    ├── h2.sectionTitle  "빠른 시작"
    └── div.quickLinks                       ← Link × 3
        ├── Link(/predict) → div.quickLink
        │   ├── span.quickLinkIcon  🎯
        │   ├── span.quickLinkLabel  승률 예측
        │   └── span.quickLinkDesc
        ├── Link(/history) → div.quickLink
        │   ├── span.quickLinkIcon  📋
        │   ├── span.quickLinkLabel  예측 기록
        │   └── span.quickLinkDesc
        └── Link(/analytics) → div.quickLink
            ├── span.quickLinkIcon  📊
            ├── span.quickLinkLabel  분석 대시보드
            └── span.quickLinkDesc
```

---

## 4. 컴포넌트 명세

### 4-1. Hero Section

| 요소 | CSS 클래스 | 스타일 |
|------|-----------|--------|
| 전체 래퍼 | `.hero` | `flex flex-col gap-2 mb-8` |
| 메인 타이틀 | `.title` | `text-3xl font-black`, `--color-valo-text` |
| 빨간 강조 | `.titleAccent` | `color: --color-valo-red` |
| 서브타이틀 | `.subtitle` | `text-sm`, `color: --color-valo-muted` |

**콘텐츠:**
- 타이틀: `VALOPREDIC**TML**` → VALO와 ML에만 빨간색 적용
- 서브타이틀: `발로란트 5v5 팀 구성 승률 예측 시스템 — XGBoost + LightGBM 앙상블 모델`

### 4-2. StatCard 그리드

| 요소 | CSS 클래스 | 스타일 |
|------|-----------|--------|
| 그리드 래퍼 | `.grid` | `grid gap-4`, `grid-template-columns: repeat(auto-fit, minmax(200px, 1fr))` |

**카드 데이터:**
| title | value | desc |
|-------|-------|------|
| 모델 정확도 | ≥80% | XGBoost + LightGBM 앙상블 |
| 지원 맵 | 9개 | Ascent, Bind, Haven 외 |
| 에이전트 수 | 24명 | 전 역할군 커버 |
| 분석 피처 | 15개 | 역할 분포 · 맵 인코딩 포함 |

**StatCard 내부 레이아웃:**
```
┌────────────────────────────────┐
│ title (muted, uppercase, xs)   │
│ value (2xl~3xl, bold, white)   │
│ desc (xs, muted)               │
└────────────────────────────────┘
  border: 1px solid --valo-border
  background: --color-valo-panel
  padding: 1.25rem
  border-radius: 0.75rem
```

### 4-3. Quick Links 섹션

| 요소 | CSS 클래스 | 스타일 |
|------|-----------|--------|
| 섹션 래퍼 | `.section` | `mt-8 flex flex-col gap-4` |
| 섹션 타이틀 | `.sectionTitle` | `text-lg font-bold`, `--color-valo-text` |
| 링크 그리드 | `.quickLinks` | `grid gap-3`, `grid-template-columns: repeat(auto-fit, minmax(160px, 1fr))` |
| 링크 카드 | `.quickLink` | `flex flex-col gap-1 p-4 rounded-xl` |

**quickLink 인터랙션:**
- 기본: `background: --color-valo-panel`, `border: 1px solid --color-valo-border`
- hover: `border-color: --color-valo-red`, `background: --color-valo-panel-alt`
- `text-decoration: none` (Link 기본값 오버라이드)

---

## 5. 상태 흐름

```
HomePage는 순수 정적 컴포넌트 — 클라이언트 상태 없음

빌드 시 pre-render → HTML 즉시 서빙
API 호출 없음 / useEffect 없음 / useState 없음
```

---

## 6. 인터랙션 정의

| 사용자 액션 | 반응 |
|-------------|------|
| QuickLink hover | 카드 border 색상 변경 (muted → red), 배경 밝아짐 |
| 승률 예측 클릭 | `/predict`로 Next.js 클라이언트 라우팅 |
| 예측 기록 클릭 | `/history`로 이동 |
| 분석 대시보드 클릭 | `/analytics`로 이동 |

---

## 7. CSS 변수 사용 목록

| 변수 | 사용 위치 |
|------|----------|
| `--color-valo-red` | `.titleAccent` 텍스트 색상, quickLink hover border |
| `--color-valo-bg` | body 배경 (globals.css) |
| `--color-valo-panel` | StatCard, quickLink 배경 |
| `--color-valo-panel-alt` | quickLink hover 배경 |
| `--color-valo-border` | StatCard, quickLink 테두리 |
| `--color-valo-text` | `.title`, `.sectionTitle` 텍스트 |
| `--color-valo-muted` | `.subtitle`, StatCard desc |

---

## 8. 반응형 처리

| 화면 너비 | StatCard 그리드 | QuickLinks 그리드 |
|-----------|----------------|-------------------|
| > 1024px | 4열 (auto-fit) | 3열 |
| 768~1024px | 2열 | 2~3열 |
| < 768px | 1~2열 (minmax 200px) | 1~2열 (minmax 160px) |

> `auto-fit` + `minmax` 방식으로 별도 미디어쿼리 없이 자동 반응형 처리됨.

---

## 9. 메타데이터

```js
export const metadata = {
  title: 'ValoPredictML — 홈'
};
```
