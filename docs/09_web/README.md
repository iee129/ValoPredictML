# 09. 웹 대시보드 — 문서 인덱스

ValoPredictML 웹 프론트엔드(Next.js 16 + Tailwind CSS v4)에 관한 모든 설계 및 구현 문서.

> **화면 레이아웃 설계** → [`docs/11_ui_design/`](../11_ui_design/)  
> **백엔드 API 설계** → [`docs/03_architecture/`](../03_architecture/)

---

## 폴더 구조

```
docs/09_web/
├── README.md                          ← 지금 이 파일
├── 01_overview/
│   ├── 01_tech_stack.md               기술 스택 및 선택 이유
│   ├── 02_architecture.md             프론트엔드 아키텍처 다이어그램
│   └── 03_design_decisions.md         주요 설계 결정 사항
├── 02_project_structure/
│   ├── 01_directory_tree.md           전체 디렉터리 트리 (실제 파일 기반)
│   ├── 02_file_roles.md               각 파일/폴더의 역할 상세
│   └── 03_conventions.md              명명 규칙, import 별칭, 코드 컨벤션
├── 03_pages/
│   ├── 01_app_router.md               Next.js App Router 개요
│   ├── 02_page_home.md                / 메인 페이지
│   ├── 03_page_predict.md             /predict 승률 예측 페이지
│   ├── 04_page_history.md             /history 예측 기록 페이지
│   └── 05_page_analytics.md           /analytics 통계 분석 페이지
├── 04_components/
│   ├── 01_component_tree.md           전체 컴포넌트 트리 + 의존 관계
│   ├── 02_layout_components.md        Navbar, PageWrapper
│   ├── 03_predict_components.md       AgentPicker, AgentCard, MapSelector, RoleFilter, TeamSlot, PredictButton
│   ├── 04_result_components.md        WinRateGauge, ConfidenceBadge, RoleRadarChart, FeatureImportanceBar
│   ├── 05_history_components.md       HistoryTable, HistoryFilter, Pagination
│   ├── 06_analytics_components.md     Analytics 도메인 컴포넌트 + 커스텀 바 차트
│   └── 07_ui_components.md            LoadingSpinner, ErrorMessage, StatCard
├── 05_state_and_data/
│   ├── 01_state_strategy.md           상태 관리 전략
│   ├── 02_data_flow.md                데이터 흐름 다이어그램
│   └── 03_lib_modules.md              src/lib/ 모듈 상세 (api.js, agentImage.js)
├── 06_styling/
│   ├── 01_tailwind_v4_setup.md        Tailwind CSS v4 설정
│   ├── 02_valo_theme.md               발로란트 테마 CSS 변수 전체
│   ├── 03_css_modules_strategy.md     CSS 모듈 전략 (@reference 규칙)
│   └── 04_responsive_design.md        반응형 브레이크포인트 전략
├── 07_visualization/
│   ├── 01_recharts_usage.md           Recharts 컴포넌트 사용 가이드
│   └── 02_custom_css_charts.md        커스텀 CSS 바 차트 구현
├── 08_api_integration/
│   ├── 01_api_client.md               api.js 함수 전체 명세
│   ├── 02_fastapi_endpoints.md        FastAPI 엔드포인트 명세 (프론트 관점)
│   └── 03_error_handling.md           에러 처리 전략
└── 09_deployment/
    ├── 01_vercel_config.md            vercel.json 상세 설명
    ├── 02_env_vars.md                 환경변수 목록 및 관리
    └── 03_cicd.md                     GitHub Actions CI/CD 파이프라인
```

---

## 빠른 탐색

| 목적 | 문서 |
|---|---|
| "어떤 기술을 쓰나?" | [01_overview/01_tech_stack.md](01_overview/01_tech_stack.md) |
| "전체 구조가 어떻게 생겼나?" | [02_project_structure/01_directory_tree.md](02_project_structure/01_directory_tree.md) |
| "예측 페이지 로직이 궁금하다" | [03_pages/03_page_predict.md](03_pages/03_page_predict.md) |
| "이 컴포넌트가 뭘 하나?" | [04_components/01_component_tree.md](04_components/01_component_tree.md) |
| "상태는 어떻게 관리하나?" | [05_state_and_data/01_state_strategy.md](05_state_and_data/01_state_strategy.md) |
| "Tailwind v4 설정 방법?" | [06_styling/01_tailwind_v4_setup.md](06_styling/01_tailwind_v4_setup.md) |
| "CSS 변수가 뭐가 있나?" | [06_styling/02_valo_theme.md](06_styling/02_valo_theme.md) |
| "Recharts 어떻게 쓰나?" | [07_visualization/01_recharts_usage.md](07_visualization/01_recharts_usage.md) |
| "FastAPI와 어떻게 통신하나?" | [08_api_integration/01_api_client.md](08_api_integration/01_api_client.md) |
| "Vercel 배포 방법?" | [09_deployment/01_vercel_config.md](09_deployment/01_vercel_config.md) |

---

## 관련 문서

- **화면 레이아웃 설계** (와이어프레임 수준): [`docs/11_ui_design/`](../11_ui_design/)
- **전체 시스템 아키텍처**: [`docs/03_architecture/`](../03_architecture/)
- **TODO 목록**: [`docs/08_todo_list/`](../08_todo_list/)
