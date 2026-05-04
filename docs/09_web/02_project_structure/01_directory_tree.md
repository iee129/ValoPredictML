> ⚠️ **범위 외**: Next.js 미사용. UI는 Streamlit 로컬 도구로 대체. 본문은 참고용으로 보존된다.

# 01. 전체 디렉터리 트리

실제 구현된 소스 파일 기준의 전체 디렉터리 구조.

---

## 저장소 최상위

```
ValoPredictML/
├── valo_predict_system/        ← Next.js 웹 프론트엔드 루트
├── docs/                       ← 프로젝트 문서
├── dataload.py                 ← 데이터 로드 스크립트
├── requirements.txt            ← Python 의존성
└── overview.md                 ← 프로젝트 요약
```

---

## Next.js 앱 (`valo_predict_system/`)

```
valo_predict_system/
├── package.json
├── package-lock.json
├── next.config.mjs             ← React Compiler, 이미지 remotePatterns
├── vercel.json                 ← Vercel 배포 설정
├── postcss.config.mjs          ← Tailwind CSS PostCSS 플러그인
├── jsconfig.json               ← @/ import 별칭 설정
│
└── src/
    ├── app/                    ← Next.js App Router 루트
    │   ├── layout.js           공통 레이아웃 (Navbar, body 래퍼)
    │   ├── layout.module.css
    │   ├── globals.css         Tailwind @theme, 전역 CSS 변수
    │   ├── favicon.ico
    │   │
    │   ├── page.js             / 홈 페이지
    │   ├── page.module.css
    │   │
    │   ├── predict/
    │   │   ├── page.js         /predict 승률 예측 페이지
    │   │   └── page.module.css
    │   │
    │   ├── history/
    │   │   ├── page.js         /history 예측 기록 페이지
    │   │   └── page.module.css
    │   │
    │   └── analytics/
    │       ├── page.js         /analytics 통계 분석 페이지
    │       └── page.module.css
    │
    ├── components/             ← 재사용 컴포넌트
    │   │
    │   ├── layout/
    │   │   ├── Navbar.js       상단 네비게이션 바
    │   │   ├── Navbar.module.css
    │   │   ├── PageWrapper.js  페이지 공통 래퍼 (max-width, padding)
    │   │   └── PageWrapper.module.css
    │   │
    │   ├── predict/
    │   │   ├── AgentCard.js    개별 요원 카드 (클릭으로 선택)
    │   │   ├── AgentCard.module.css
    │   │   ├── AgentPicker.js  요원 선택 그리드 (역할군 탭 포함)
    │   │   ├── AgentPicker.module.css
    │   │   ├── MapSelector.js  맵 선택 드롭다운
    │   │   ├── MapSelector.module.css
    │   │   ├── PredictButton.js 예측하기 버튼 (로딩 상태)
    │   │   ├── PredictButton.module.css
    │   │   ├── RoleFilter.js   역할군 탭 필터 (전체/타격대/척후대/전략가/감시자)
    │   │   ├── RoleFilter.module.css
    │   │   ├── TeamSlot.js     선택된 팀 요원 슬롯 미리보기
    │   │   └── TeamSlot.module.css
    │   │
    │   ├── result/
    │   │   ├── ConfidenceBadge.js     신뢰도 배지 (high/medium/low)
    │   │   ├── ConfidenceBadge.module.css
    │   │   ├── FeatureImportanceBar.js 피처 중요도 수평 바 차트
    │   │   ├── FeatureImportanceBar.module.css
    │   │   ├── RoleRadarChart.js      역할군 비교 레이더 차트 (Recharts)
    │   │   ├── RoleRadarChart.module.css
    │   │   ├── WinRateGauge.js        승률 게이지 (Recharts RadialBarChart)
    │   │   └── WinRateGauge.module.css
    │   │
    │   ├── history/
    │   │   ├── HistoryFilter.js  맵 선택 필터
    │   │   ├── HistoryFilter.module.css
    │   │   ├── HistoryTable.js   예측 기록 테이블
    │   │   ├── HistoryTable.module.css
    │   │   ├── Pagination.js     페이지네이션 컨트롤
    │   │   └── Pagination.module.css
    │   │
    │   └── ui/
    │       ├── ErrorMessage.js   에러 메시지 표시
    │       ├── ErrorMessage.module.css
    │       ├── LoadingSpinner.js 로딩 스피너
    │       ├── LoadingSpinner.module.css
    │       ├── StatCard.js       통계 카드 (숫자 + 레이블)
    │       └── StatCard.module.css
    │
    └── lib/
        ├── api.js              FastAPI 통신 함수 모음
        └── agentImage.js       요원 이름 → 이미지 URL 변환
```

---

## 파일 수 통계

| 카테고리 | JS 파일 | CSS 파일 | 합계 |
|---|---|---|---|
| pages (app/) | 4 | 4 | 8 |
| layout (app/layout.js) | 1 | 1 | 2 |
| layout 컴포넌트 | 2 | 2 | 4 |
| predict 컴포넌트 | 6 | 6 | 12 |
| result 컴포넌트 | 4 | 4 | 8 |
| history 컴포넌트 | 3 | 3 | 6 |
| ui 컴포넌트 | 3 | 3 | 6 |
| lib | 2 | - | 2 |
| globals.css | - | 1 | 1 |
| **합계** | **25** | **24** | **49** |

---

## 설정 파일 상세

| 파일 | 내용 |
|---|---|
| `next.config.mjs` | `reactCompiler: true`, `images.remotePatterns` |
| `vercel.json` | `framework: nextjs`, `region: icn1`, `NEXT_PUBLIC_API_URL` |
| `postcss.config.mjs` | `@tailwindcss/postcss` 플러그인 |
| `jsconfig.json` | `paths: { "@/*": ["./src/*"] }` |
