# 06. 모델 테스트 문서 인덱스

이 디렉토리는 두 묶음으로 구성된다.

- **2모델 평가·검증** (현행): 루트 ML 문서 3개와 [`07_model_evaluation/`](./07_model_evaluation/00_overview.md) —
  베이스라인 1개(랜덤 holdout) + 심화 1개(시간순 holdout) 2개 모델의 평가 기록.
- **FastAPI API 테스트 설계** (참고 보존): `01_test_strategy/`~`06_ui_testing/`.
  현재 시연 demo path는 웹 스택(FastAPI `src/api` + Next.js `web`)이며, 이 하위 문서들은 그 테스트 설계의 참고 자료다.

---

## 폴더 구조

```
docs/06_model_test/
├── README.md                            ← 이 파일
├── model_test.md                        ← FastAPI 스펙 (참고) + §8 평가 문서 참조
├── ml_concept_validation.md             ← ML 개념 검증 (GroupKFold·앙상블·중요도·알고리즘 선택)
├── project_differentiation.md           ← 프로젝트 차별점 + 2모델 성능표
├── verification_summary.md              ← 2모델 성과지표 종합
├── 07_model_evaluation/                 ← 2모델 개별·비교 평가
│   ├── 00_overview.md                   ← 2모델 정의 · 분할/모델 축 차이
│   ├── 01_random_baseline.md            ← 베이스라인 (랜덤 holdout, 421피처, Test AUC 0.5943)
│   ├── 04_chrono_advanced.md            ← 심화 (시간순 holdout, 179피처, Test AUC 0.7010)
│   └── 05_cross_model_comparison.md     ← 2모델 비교
├── 01_test_strategy/                    ← FastAPI 테스트 설계 (참고)
├── 02_api_specification/                ← FastAPI 테스트 설계 (참고)
├── 03_test_scenarios/                   ← FastAPI 테스트 설계 (참고)
├── 04_performance_testing/              ← FastAPI 테스트 설계 (참고)
├── 05_fastapi_implementation/           ← FastAPI 테스트 설계 (참고)
└── 06_ui_testing/                       ← FastAPI 테스트 설계 (참고)
```

## 2모델 한눈 보기

| 모델 | 분할 | 피처 | Test AUC |
|---|---|---:|---:|
| 베이스라인 (LR+DT) | 랜덤 80/20 | 421 | 0.5943 |
| 심화 (RF+XGB+LGBM) | 시간순 (train 2020–2025 / test 2026, 맵 단위 승패 샘플) | 179 | 0.7010 |

> 베이스(랜덤 80/20)와 심화(시간순)는 분할·모델 축이 모두 다르므로 두 수치는 같은 잣대의 우열이 아니다.

상세는 [`07_model_evaluation/00_overview.md`](./07_model_evaluation/00_overview.md).
