# 02. 파일/폴더 역할 상세

각 파일과 폴더의 역할을 상세히 설명한다.

---

## `src/app/` — 라우팅 레이어

### `layout.js`

```
역할: 모든 페이지에 공통 적용되는 최상위 레이아웃
포함: Navbar, PageWrapper, HTML meta 설정
```

- `<html>`, `<body>` 태그를 포함하는 루트 레이아웃
- `Navbar`를 렌더링하고, `children`을 `PageWrapper`로 감쌈
- Next.js의 `metadata` 객체로 페이지 제목/설명 설정
- `globals.css`를 여기서 import → 전체 앱에 전역 스타일 적용

### `globals.css`

```
역할: Tailwind CSS v4 설정 + 전역 스타일
포함: @import "tailwindcss", @theme 블록, body/기본 스타일
```

- `@theme {}` 블록에 발로란트 브랜드 CSS 변수 20개+ 정의
- `body`에 배경색(`--color-valo-bg`) 및 텍스트 색상(`--color-valo-text`) 적용
- 공통 유틸리티 클래스 정의: `.valo-panel`, `.valo-title`, `.valo-divider`, `.role-dot-*`

### `page.js` (홈)

```
역할: 프로젝트 소개 + 예측 진입점 + 최근 예측 미리보기
상태: recentPredictions, stats
API: GET /history?limit=3, GET /analytics
```

### `predict/page.js`

```
역할: 승률 예측 메인 페이지 (가장 복잡한 페이지)
상태: selectedMap, teamA[], teamB[], result, loading, error
API: GET /maps, GET /agents, POST /predict
```

교차 팀 필터링 로직 포함:
```js
agents.filter(a => !allSelected.includes(a.name) || teamX.includes(a.name))
```

### `history/page.js`

```
역할: 과거 예측 기록 조회 (필터 + 페이지네이션)
상태: page, mapFilter, items, total
API: GET /history?limit=10&offset=N&map=X
```

### `analytics/page.js`

```
역할: 전체 예측 데이터 통계 시각화
상태: data (단순 API 응답)
API: GET /analytics
```

---

## `src/components/` — 컴포넌트 레이어

### `layout/Navbar.js`

```
역할: 상단 네비게이션 바
props: 없음 (usePathname으로 현재 경로 자체 감지)
```

- `usePathname()` 훅으로 현재 활성 링크 강조
- 4개 링크: 홈 / 승률 예측 / 통계 분석 / 예측 기록
- 모바일에서는 아이콘만 표시 (텍스트 숨김) 대응

### `layout/PageWrapper.js`

```
역할: 콘텐츠 영역 공통 래퍼
props: children
```

- `max-width` + 좌우 `padding` 적용
- 반응형: 모바일 16px, 데스크톱 24px padding

### `predict/AgentPicker.js`

```
역할: 요원 선택 그리드 (역할군 탭 포함)
props: agents, selectedTeam, teamLabel, onAgentSelect, onAgentRemove, allSelected
```

- `RoleFilter` 탭으로 역할군 필터링
- 이미 5명 선택 시 미선택 요원 disabled
- 반대 팀이 선택한 요원도 disabled (allSelected prop으로 전달)

### `predict/AgentCard.js`

```
역할: 개별 요원 카드 (이미지 + 이름 + 역할군 색상)
props: agent, selected, disabled, onClick
```

- `getAgentIconUrl(agent.name)`으로 valorant-api.com 이미지 로드
- selected 시 빨간 테두리 + 체크 오버레이
- disabled 시 어둡게 처리

### `predict/MapSelector.js`

```
역할: 맵 선택 드롭다운
props: maps, selected, onChange
```

### `predict/RoleFilter.js`

```
역할: 역할군 탭 필터 (전체/타격대/척후병/전략가/감시자)
props: active, onChange
```

### `predict/TeamSlot.js`

```
역할: 선택된 팀 요원 슬롯 5개 미리보기
props: agents, selected, label
```

- 선택된 요원은 아이콘, 미선택 슬롯은 빈 원형 표시

### `predict/PredictButton.js`

```
역할: 예측하기 버튼 (로딩 애니메이션 포함)
props: onClick, disabled, loading
```

### `result/WinRateGauge.js`

```
역할: 팀 승률을 원형 게이지로 표시
props: winProbability (0~1), teamLabel
```

- Recharts `RadialBarChart` 사용
- 60%+ 녹색, 40~60% 노란색, 40%- 회색

### `result/ConfidenceBadge.js`

```
역할: 예측 신뢰도 배지 (high/medium/low)
props: confidence ("high" | "medium" | "low")
```

### `result/RoleRadarChart.js`

```
역할: 팀 A vs 팀 B 역할군 구성 레이더 차트
props: teamA (역할군 카운트 객체), teamB (역할군 카운트 객체)
```

- Recharts `RadarChart` 사용
- 4개 축: Duelist, Initiator, Controller, Sentinel

### `result/FeatureImportanceBar.js`

```
역할: 예측에 영향을 준 피처 상위 5개 수평 바 차트
props: data (Array<{feature, importance}>)
```

### `history/HistoryTable.js`

```
역할: 예측 기록 테이블
props: items (예측 기록 배열)
```

- 컬럼: 날짜 | 맵 | 팀 A | 팀 B | 승률 | 신뢰도

### `history/HistoryFilter.js`

```
역할: 맵 필터 드롭다운
props: maps, selected, onChange
```

### `history/Pagination.js`

```
역할: 페이지네이션 버튼
props: page, total, limit, onChange
```

### `ui/LoadingSpinner.js`

```
역할: 로딩 중 표시 스피너
props: 없음
```

### `ui/ErrorMessage.js`

```
역할: 에러 메시지 표시 박스
props: message
```

### `ui/StatCard.js`

```
역할: 통계 수치 카드 (숫자 + 레이블 + 선택적 부제목)
props: label, value, sub
```

---

## `src/lib/` — 유틸리티 레이어

### `api.js`

```
역할: FastAPI 백엔드 통신 함수 전체 모음
export: predictWinRate, fetchAgents, fetchMaps, fetchHistory, fetchAnalytics
```

환경변수 `NEXT_PUBLIC_API_URL`로 베이스 URL 설정.  
→ 상세: [08_api_integration/01_api_client.md](../08_api_integration/01_api_client.md)

### `agentImage.js`

```
역할: 요원 이름 → valorant-api.com UUID → 이미지 URL 변환
export: getAgentIconUrl, ROLE_COLORS, ROLE_LABELS_KR
```

⚠️ Harbor, Gekko UUID는 플레이스홀더 — 실제 UUID로 교체 필요  
→ 상세: [05_state_and_data/03_lib_modules.md](../05_state_and_data/03_lib_modules.md)

---

## 설정 파일

### `next.config.mjs`

```js
export default {
  reactCompiler: true,        // React 19 Compiler 활성화 (자동 메모이제이션)
  images: {
    remotePatterns: [{
      protocol: 'https',
      hostname: 'media.valorant-api.com',
      pathname: '/agents/**',
    }],
  },
};
```

### `vercel.json`

```json
{
  "framework": "nextjs",
  "regions": ["icn1"],         // 서울 리전
  "env": {
    "NEXT_PUBLIC_API_URL": "http://localhost:8000"
  }
}
```

### `jsconfig.json`

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]       // @/components/... 절대 경로 import 가능
    }
  }
}
```
