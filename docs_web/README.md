# docs_web — FastAPI + Next.js 16 (TypeScript) 시연 문서

이 문서 세트는 **학습된 ML 모델을 FastAPI로 서빙하고, Next.js 16 (TypeScript) 프론트엔드와 연동해 UI로 시연**하는 것을 목적으로 한다. 모든 계약(엔드포인트·스키마·타입)은 저장소의 **실제 모델 코드**(`app/predict.py`, `ml/baseline/preprocess.py`, `ml/agent_roles.py`)에서 역으로 도출했다.

> `docs/09_web`와의 관계: `docs/09_web`는 과거에 작성됐다가 "범위 외(Streamlit으로 대체)"로 폐기 선언된 문서다. 본 `docs_web`는 그것을 대체하지 않고 **별개로** 존재하며, 실제 모델 계약과 TypeScript 목표에 맞춰 새로 작성됐다. 무엇이 어떻게 달라졌는지는 [05_appendix/01_diff_from_09_web.md](05_appendix/01_diff_from_09_web.md) 참조.

---

## 한눈에 보는 아키텍처

```
┌─────────────────────────────┐      ┌──────────────────────────────┐      ┌───────────────────────────┐
│  Next.js 16 (TypeScript)    │      │       FastAPI 백엔드         │      │   학습 산출물 (로컬)       │
│  App Router + React 19      │ HTTP │  app/predict.py 재사용       │ load │  models/advanced/          │
│  /predict 시연 페이지       │─────▶│  /predict /options /replay   │─────▶│   ensemble.joblib (125F)   │
│  lib/api.ts (타입 안전)     │ JSON │  /model /agents /maps        │      │  data/processed/...        │
└─────────────────────────────┘      └──────────────────────────────┘      │  reports/adv_kaggle_only/  │
                                                                            └───────────────────────────┘
```

FastAPI는 모델 로직을 새로 구현하지 않는다. `app/predict.py`의 `predict_custom_lineup`·`predict_replay_match`·`available_options`·`load_model`·`load_reports`를 그대로 호출하고, 결과 `PredictionResult`를 JSON으로 직렬화할 뿐이다.

---

## 문서 인덱스

| 폴더 | 문서 | 내용 |
|------|------|------|
| **01_overview** | [01_goal_and_scope.md](01_overview/01_goal_and_scope.md) | 시연 목적, 포함/제외 범위 |
| | [02_architecture.md](01_overview/02_architecture.md) | 3계층 아키텍처, 요청 흐름 |
| | [03_tech_stack.md](01_overview/03_tech_stack.md) | Next.js 16 / TS / FastAPI 버전·선택 이유 |
| **02_backend_fastapi** | [01_app_structure.md](02_backend_fastapi/01_app_structure.md) | `valo_web_backend/` 패키지 구조 |
| | [02_model_serving.md](02_backend_fastapi/02_model_serving.md) | `app/predict.py` 재사용, 캐싱, 콜드스타트 |
| | [03_endpoints.md](02_backend_fastapi/03_endpoints.md) | 엔드포인트 명세(실제 계약 기반) |
| | [04_schemas.md](02_backend_fastapi/04_schemas.md) | Pydantic 스키마 ↔ `PredictionResult` 매핑 |
| | [05_run_and_cors.md](02_backend_fastapi/05_run_and_cors.md) | uvicorn 실행, CORS, 환경변수 |
| **03_frontend_nextjs** | [01_setup_and_structure.md](03_frontend_nextjs/01_setup_and_structure.md) | create-next-app(TS), 디렉터리 |
| | [02_types_and_api_client.md](03_frontend_nextjs/02_types_and_api_client.md) | `types/api.ts`, `lib/api.ts` |
| | [03_predict_page.md](03_frontend_nextjs/03_predict_page.md) | 예측 페이지(선수+요원 입력) |
| | [04_pages_and_components.md](03_frontend_nextjs/04_pages_and_components.md) | replay·model 페이지, 컴포넌트 |
| **04_integration** | [01_data_contract.md](04_integration/01_data_contract.md) | 프론트↔백 데이터 계약 SSOT |
| | [02_demo_runbook.md](04_integration/02_demo_runbook.md) | 시연 실행 순서(런북) |
| **06_insights** | [00_overview.md](06_insights/00_overview.md) | 부가 인사이트 6종 개요 + 범위 외(D) |
| | [01_agent_map_fit.md](06_insights/01_agent_map_fit.md) | 요원-맵 적합도 ✓/△/✗ (N) |
| | [02_comp_match.md](06_insights/02_comp_match.md) | 메타 조합 매칭률 % (K) |
| | [03_balance_warning.md](06_insights/03_balance_warning.md) | 구성 결함 알림 (G) |
| | [04_nl_explanation.md](06_insights/04_nl_explanation.md) | 자연어 승부 근거 (C) |
| | [05_precompute_and_data.md](06_insights/05_precompute_and_data.md) | 사전 집계 빌더(`ml/insights/`) |
| **07_styling** | [00_design_principles.md](07_styling/00_design_principles.md) | 가독성·한눈에 원칙(시연용) |
| | [01_valorant_theme.md](07_styling/01_valorant_theme.md) | 발로란트 테마 토큰(색·타이포) |
| | [02_layout_demo_dashboard.md](07_styling/02_layout_demo_dashboard.md) | 한 화면 대시보드 레이아웃 |
| | [03_component_visual_specs.md](07_styling/03_component_visual_specs.md) | 컴포넌트 시각·props 명세 |
| **08_testing** | [01_test_strategy.md](08_testing/01_test_strategy.md) | 테스트 전략 + 시연 체크리스트 |
| **05_appendix** | [01_diff_from_09_web.md](05_appendix/01_diff_from_09_web.md) | 09_web 대비 정정 내역 |

---

## 핵심 계약 요약 (전체 문서의 기준점)

**입력** — `POST /predict`
```json
{
  "map": "Ascent",
  "cutoff_year": 2026,
  "team_a": [{ "player": "TenZ", "agent": "Jett" }, "...총 5쌍"],
  "team_b": [{ "player": "aspas", "agent": "Reyna" }, "...총 5쌍"]
}
```

**출력** — `PredictionResult` 직렬화 (필드 원본: `app/predict.py`)
```json
{
  "predicted_winner": "A",
  "team_a": { "name": "팀 A", "win_probability": 0.62 },
  "team_b": { "name": "팀 B", "win_probability": 0.38 },
  "confidence": 0.24,
  "role_counts": { "team_a": { "duelist": 2 }, "team_b": { "duelist": 1 } },
  "top_features": [
    { "feature": "a_prior_kd_mean", "value": 1.05, "importance": 0.03, "contribution": 0.032 }
  ],
  "model": { "contract": "advanced", "n_features": 125 }
}
```

**불변 사실** (`ml/`에서 확정):
- 요원 **29종** (`AGENT_ROLE_MAP`), 맵 **13종** (`MAP_ORDER`)
- 모델 입력 피처 **정확히 125개** (`FEATURE_COLS_ADVANCED`, import 시 어서션)
- 학습/평가 소스는 `kaggle_*`만 (`SOURCE_CONTRACT`)
