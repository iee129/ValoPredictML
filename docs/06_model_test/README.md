# 06. 모델 테스트 문서 인덱스

이 디렉토리는 두 묶음으로 구성된다.

- **4모델 평가·검증** (현행): 루트 ML 문서 3개와 [`07_model_evaluation/`](./07_model_evaluation/00_overview.md) —
  분할(랜덤 / 시간순) × 계열(베이스라인 / 심화) 2×2 = 4가지 모델의 평가 기록.
- **FastAPI API 테스트 설계** (범위 외, 참고 보존): `01_test_strategy/`~`06_ui_testing/`.
  본 프로젝트의 실제 구현은 Streamlit 로컬 도구이므로 이 하위 문서들은 적용되지 않는다.

---

## 폴더 구조

```
docs/06_model_test/
├── README.md                            ← 이 파일
├── model_test.md                        ← FastAPI 스펙 (범위 외) + §8 평가 문서 참조
├── ml_concept_validation.md             ← ML 개념 검증 (GroupKFold·앙상블·SHAP·알고리즘 선택)
├── project_differentiation.md           ← 프로젝트 차별점 + 4모델 성능표
├── verification_summary.md              ← 4모델 성과지표 종합
├── 07_model_evaluation/                 ← 4모델 개별·교차 평가
│   ├── 00_overview.md                   ← 2×2 매트릭스 · 평가 축
│   ├── 01_random_baseline.md            ← ① 랜덤순 베이스라인 (Test AUC 0.6587)
│   ├── 02_random_advanced.md            ← ② 랜덤순 심화 (Test AUC 0.7570)
│   ├── 03_chrono_baseline.md            ← ③ 시간순 베이스라인 (Test AUC 0.6124)
│   ├── 04_chrono_advanced.md            ← ④ 시간순 심화 (Test AUC 0.6182)
│   └── 05_cross_model_comparison.md     ← 4모델 교차 비교
├── 01_test_strategy/                    ← FastAPI (범위 외)
├── 02_api_specification/                ← FastAPI (범위 외)
├── 03_test_scenarios/                   ← FastAPI (범위 외)
├── 04_performance_testing/              ← FastAPI (범위 외)
├── 05_fastapi_implementation/           ← FastAPI (범위 외)
└── 06_ui_testing/                       ← FastAPI (범위 외)
```

## 4모델 한눈 보기

| | 베이스라인 (178) | 심화 (125) |
|---|---|---|
| 랜덤 holdout | ① Test AUC 0.6587 | ② Test AUC 0.7570 |
| 시간순 holdout | ③ Test AUC 0.6124 | ④ Test AUC 0.6182 |

상세는 [`07_model_evaluation/00_overview.md`](./07_model_evaluation/00_overview.md).
