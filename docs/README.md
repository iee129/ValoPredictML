# ValoPredictML 문서 정본

이 `docs/` 디렉토리는 기말 발표와 보고서의 기준 문서다. 최종 채점 시연 경로는 **웹 스택(FastAPI `src/api` + Next.js `web`)**이다. 과거 Streamlit 앱(`app/main.py`)은 폐기됐고, 추론 로직만 `src/inference/predict.py`로 보존됐다.

> **모든 수치의 단일 출처**: [`final/deliverables/00_수치_단일진실표.md`](../final/deliverables/00_수치_단일진실표.md) (동결 git hash: 33b7576 / 2026-06-02). 이 파일과 아래 표의 수치가 충돌할 경우 SSOT가 진실이다.

## 공개 계약

| 항목 | 정본 |
|---|---|
| 사용자 입력 | 맵 1개 + 팀A 선수 5명/요원 5명 + 팀B 선수 5명/요원 5명 |
| 제외 입력 | 팀명, 외부 API 호출, 클라우드 배포 설정 |
| Baseline | LR+DT soft voting, 랜덤 80/20 split, 421 features, Test AUC 0.5943 / Acc 0.5667 / F1 0.6072, verdict 신뢰 가능 |
| Advanced | RF+XGB+LGBM soft voting, 시간순 split, 179 features, Test AUC 0.7010 / Acc 0.6454 / F1 0.6478, verdict 신뢰 가능 |
| 시간순 일반화 | Advanced active Test AUC 0.7010 |
| 시연 앱 | `uvicorn api.main:app` + `cd web && npm run dev` |
| 근거 산출물 | `models/advanced/meta.json`, `reports/advanced/validation.json`, `reports/advanced/metrics.json`, `reports/baseline/metrics.json` |

## 평가기준 추적표

| PPTX 기준 | 평가 항목 | 정본 문서 | 증거 산출물 |
|---|---|---|---|
| Slide 5 | 최종 산출물 범위 | [01_overview/01_project_summary.md](01_overview/01_project_summary.md), [02_file_structure/01_directory_overview.md](02_file_structure/01_directory_overview.md) | `src/api/`, `web/`, `models/advanced/meta.json` |
| Slide 10 | 데이터 확보 | [07_data/README.md](07_data/README.md), [04_data_processing/02_data_collection.md](04_data_processing/02_data_collection.md) | `data/raw/kaggle/`, `reports/preprocess/` |
| Slide 11 | 전처리 / EDA | [04_data_processing/README.md](04_data_processing/README.md), [04_data_processing/06_feature_engineering.md](04_data_processing/06_feature_engineering.md), [07_data/09_data_quality/01_quality_metrics.md](07_data/09_data_quality/01_quality_metrics.md) | `reports/baseline/metrics.json`, `reports/advanced/validation.json` |
| Slide 13 | Baseline 모델 | [05_data_learning/02_baseline_models/03_baseline_evaluation.md](05_data_learning/02_baseline_models/03_baseline_evaluation.md), [06_model_test/07_model_evaluation/01_random_baseline.md](06_model_test/07_model_evaluation/01_random_baseline.md) | `reports/baseline/metrics.json`, `reports/baseline/validation.json` |
| Slide 14 | 알고리즘 선택 | [05_data_learning/01_model_strategy/01_model_comparison.md](05_data_learning/01_model_strategy/01_model_comparison.md), [05_data_learning/01_model_strategy/02_selection_rationale.md](05_data_learning/01_model_strategy/02_selection_rationale.md) | `reports/advanced/metrics.json` |
| Slide 14 | 튜닝 | [05_data_learning/05_optimization/01_optuna_setup.md](05_data_learning/05_optimization/01_optuna_setup.md), [05_data_learning/01_model_strategy/03_ensemble_design.md](05_data_learning/01_model_strategy/03_ensemble_design.md) | `reports/advanced/metrics.json`, `models/advanced/meta.json` |
| Slide 15 | 성능 비교 | [06_model_test/verification_summary.md](06_model_test/verification_summary.md), [06_model_test/07_model_evaluation/00_overview.md](06_model_test/07_model_evaluation/00_overview.md), [06_model_test/07_model_evaluation/05_cross_model_comparison.md](06_model_test/07_model_evaluation/05_cross_model_comparison.md) | `reports/baseline/metrics.json`, `reports/advanced/metrics.json` |
| Slide 17 | 모델 시각화 / 인사이트 | [05_data_learning/03_advanced_models/02_advanced_metric_analysis.md](05_data_learning/03_advanced_models/02_advanced_metric_analysis.md), [06_model_test/ml_concept_validation.md](06_model_test/ml_concept_validation.md) | `reports/advanced/metrics.json` |
| Slide 19 | 애플리케이션 | [08_web/07_styling/02_layout_demo_dashboard.md](08_web/07_styling/02_layout_demo_dashboard.md), [03_architecture/02_request_flow.md](03_architecture/02_request_flow.md) | `src/api/`, `web/`, `src/inference/predict.py` |

## 보고서 흐름

1. 목표와 입력 계약: [01_overview](01_overview/)
2. 데이터 확보와 품질: [07_data](07_data/)
3. 전처리와 피처 생성: [04_data_processing](04_data_processing/)
4. 모델 선택과 학습: [05_data_learning](05_data_learning/)
5. 평가와 한계 해석: [06_model_test/07_model_evaluation](06_model_test/07_model_evaluation/)
6. 앱 시연: [08_web/07_styling](08_web/07_styling/)

## 참고 / 확장 문서

| 경로 | 상태 |
|---|---|
| [06_model_test/01_test_strategy](06_model_test/01_test_strategy/) ~ [06_model_test/06_ui_testing](06_model_test/06_ui_testing/) | FastAPI 기반 테스트 설계. 현재 웹 스택 demo path의 참고 자료로 보존한다. |
| [08_web](08_web/) | Next.js/FastAPI 웹 설계(SSOT). 현재 demo path 구현(`src/api`/`web`)의 근거다. |
| [03_architecture/04_api_design.md](03_architecture/04_api_design.md) | API 설계. 현재 평가는 웹 스택(FastAPI `src/api` + Next.js `web`) 기준이다. (클라우드 배포는 범위 외) |
