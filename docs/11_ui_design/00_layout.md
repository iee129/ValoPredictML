# 00. 공통 레이아웃 설계

> **적용 범위:** 전체 4개 화면 공통  
> **파일:** `src/app/layout.js`, `src/app/globals.css`, `src/components/layout/`

---

## 1. 전체 페이지 구조

```
┌─────────────────────────────────────────────────────────────────┐
│ <html lang="ko">                                                │
│  <body>                                                         │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ <Navbar />                          position: sticky top  │  │
│  │  ┌─────────────────┐  ┌──────────────────────────────┐   │  │
│  │  │ VALO PredictML  │  │  홈  승률 예측  통계 분석  기록│   │  │
│  │  └─────────────────┘  └──────────────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ <main>                                                    │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │ <PageWrapper>                                       │  │  │
│  │  │  max-w-6xl  mx-auto  px-4 py-8                     │  │  │
│  │  │  ┌─────────────────────────────────────────────┐   │  │  │
│  │  │  │  페이지별 콘텐츠                              │   │  │  │
│  │  │  └─────────────────────────────────────────────┘   │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
│  </body>                                                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 컴포넌트 트리

```
RootLayout (src/app/layout.js)          [Server Component]
├── Navbar (src/components/layout/Navbar.js)   [Client Component]
└── <main>
    └── PageWrapper (src/components/layout/PageWrapper.js)  [Server Component]
        └── {children}  ← 각 페이지 컴포넌트
```

---

## 3. 컴포넌트 명세

### 3-1. RootLayout

| 항목 | 내용 |
|------|------|
| 파일 | `src/app/layout.js` |
| 타입 | Server Component |
| CSS | `src/app/layout.module.css` |
| 역할 | `globals.css` 임포트, `<html>`, `<body>` 구성 |

**CSS 클래스:**
```
.root   → background-color: --color-valo-bg; min-height: 100vh
.main   → flex: 1; padding-top: Navbar 높이(56px)
```

### 3-2. Navbar

| 항목 | 내용 |
|------|------|
| 파일 | `src/components/layout/Navbar.js` |
| 타입 | Client Component (`'use client'`) |
| CSS | `src/components/layout/Navbar.module.css` |
| 역할 | 브랜드 로고 + 네비게이션 링크, 현재 경로 하이라이트 |

**Props:** 없음 (내부적으로 `usePathname()` 사용)

**상태:**
```
pathname = usePathname()  → 현재 경로 → linkActive CSS 클래스 적용 여부 결정
```

**네비게이션 링크:**
| href | label |
|------|-------|
| `/` | 홈 |
| `/predict` | 승률 예측 |
| `/analytics` | 통계 분석 |
| `/history` | 예측 기록 |

**CSS 클래스:**
```
.nav         → sticky top-0, height: 56px, background: --color-valo-panel, z-index: 50
.logo        → flex items-center gap-1
.logoAccent  → color: --color-valo-red, font-weight: 900
.logoText    → color: --color-valo-text
.links       → flex gap-6
.link        → text-sm font-medium, color: --color-valo-muted
.linkActive  → color: --color-valo-red, border-bottom: 2px solid --color-valo-red
```

**인터랙션:**
- 링크 hover → color: --color-valo-text
- 현재 경로와 `href` 일치 → `.linkActive` 적용 (밑줄 + 빨간 색상)

### 3-3. PageWrapper

| 항목 | 내용 |
|------|------|
| 파일 | `src/components/layout/PageWrapper.js` |
| 타입 | Server Component |
| CSS | `src/components/layout/PageWrapper.module.css` |
| 역할 | 콘텐츠 최대 너비 제한 + 수평 중앙 정렬 + 상하 패딩 |

**CSS 클래스:**
```
.wrap  → max-width: 72rem (max-w-6xl), margin: 0 auto, padding: 2rem 1rem
```

---

## 4. 글로벌 CSS 변수 (`globals.css`)

### 4-1. 색상 변수 (`@theme` 블록)

| 변수 | 값 | 용도 |
|------|----|------|
| `--color-valo-red` | `#ff4655` | 브랜드 강조색, CTA, 활성 상태 |
| `--color-valo-red-dark` | `#cc3344` | 버튼 hover 상태 |
| `--color-valo-bg` | `#0f1923` | 전체 배경색 |
| `--color-valo-panel` | `#1a2332` | 카드/패널 배경 |
| `--color-valo-panel-alt` | `#1e2a3a` | hover 상태 패널, 테이블 헤더 |
| `--color-valo-border` | `#2a3a4a` | 테두리, 구분선, 빈 슬롯 |
| `--color-valo-text` | `#ece8e1` | 기본 본문 텍스트 |
| `--color-valo-muted` | `#8899aa` | 보조 텍스트, 라벨, 비활성 |
| `--color-role-duelist` | `#ff4655` | 타격대 역할 색상 |
| `--color-role-initiator` | `#00bcd4` | 척후병 역할 색상 |
| `--color-role-controller` | `#4caf50` | 전략가 역할 색상 |
| `--color-role-sentinel` | `#ff9800` | 감시자 역할 색상 |
| `--color-confidence-high` | `#4caf50` | 신뢰도 높음 (≥75%) |
| `--color-confidence-medium` | `#ff9800` | 신뢰도 보통 (55~75%) |
| `--color-confidence-low` | `#9e9e9e` | 신뢰도 낮음 (<55%) |

### 4-2. 전역 유틸 클래스

| 클래스 | 스타일 | 용도 |
|--------|--------|------|
| `.valo-panel` | panel 배경 + border + rounded-xl | 기본 카드 |
| `.valo-panel-alt` | panel-alt 배경 + border + rounded-xl | 강조 카드 |
| `.valo-title` | text-sm font-bold uppercase tracking-widest + muted | 섹션 레이블 |
| `.valo-divider` | border-t + border-color: valo-border | 구분선 |
| `.role-dot-duelist` | background-color: role-duelist | 역할 도트 |
| `.role-dot-initiator` | background-color: role-initiator | 역할 도트 |
| `.role-dot-controller` | background-color: role-controller | 역할 도트 |
| `.role-dot-sentinel` | background-color: role-sentinel | 역할 도트 |

### 4-3. 스크롤바 스타일

```css
::-webkit-scrollbar       → width: 6px
::-webkit-scrollbar-track → background: --color-valo-panel
::-webkit-scrollbar-thumb → background: --color-valo-border, border-radius: 3px
::-webkit-scrollbar-thumb:hover → background: --color-valo-muted
```

---

## 5. 공용 UI 컴포넌트

### StatCard

| 항목 | 내용 |
|------|------|
| 파일 | `src/components/ui/StatCard.js` |
| 타입 | Server Component |
| Props | `title: string`, `value: string\|number`, `desc: string` |

**레이아웃:**
```
┌──────────────────────┐
│ title (muted, small) │
│ value (large, bold)  │
│ desc (muted, tiny)   │
└──────────────────────┘
```

### LoadingSpinner

| 항목 | 내용 |
|------|------|
| 파일 | `src/components/ui/LoadingSpinner.js` |
| 역할 | 데이터 로딩 중 전체 영역 대체 표시 |
| 시각 | 중앙 정렬 원형 스피너, --color-valo-red 색상 |

### ErrorMessage

| 항목 | 내용 |
|------|------|
| 파일 | `src/components/ui/ErrorMessage.js` |
| Props | `message: string`, `onClose?: () => void` |
| 역할 | API 에러 발생 시 인라인 에러 배너 표시 |
| 시각 | 빨간 배경 배너, X 닫기 버튼 |

---

## 6. 반응형 기준

| 브레이크포인트 | 너비 | 레이아웃 변화 |
|----------------|------|---------------|
| Mobile | < 768px | Navbar 링크 → 아이콘/숨김 고려, PageWrapper padding 축소 |
| Tablet | 768px~1024px | 대부분 1컬럼 그리드 |
| Desktop | > 1024px | 기본 2컬럼 그리드, max-w-6xl 제한 |

> Navbar는 현재 모바일 대응 미구현. 향후 햄버거 메뉴 추가 가능.

---

## 7. 폰트

| 폰트 | 적용 방식 | 용도 |
|------|-----------|------|
| DM Sans | system fallback | 기본 본문 폰트 |
| Inter | system fallback | DM Sans 없을 때 |
| system-ui | CSS 기본 | 최종 fallback |

> Google Fonts 연동 시 `layout.js`에 `next/font/google`으로 DM Sans, Rajdhani 추가 권장.
