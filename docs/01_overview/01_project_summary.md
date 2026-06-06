# 01. 프로젝트 소개 및 핵심 아이디어

마지막 업데이트: 2026-06-05

## 1. ValoPredictML이란?

**ValoPredictML**은 Valorant 경기의 **맵 + 5v5 라인업**을 입력받아 팀 A의 승리 확률을 예측하는 머신러닝 기반 **웹 분석 도구**다(FastAPI `src/api` + Next.js `web`). 초기엔 Streamlit 로컬 앱으로 시연했으나 폐기됐고, 추론 로직만 `src/inference/predict.py`로 보존된다.

최종 발표와 채점 시연의 기준은 웹 스택(`uvicorn api.main:app` + `web` Next.js)이며, 입력은 다음 21개 항목으로 고정한다.

| 구분 | 입력 |
|---|---|
| 맵 | 1개 |
| 팀 A | 선수 5명 + 요원 5명 |
| 팀 B | 선수 5명 + 요원 5명 |

팀명, 외부 API 호출, 클라우드 배포는 최종 평가 범위 밖이다. 모델은 사용자가 입력한 선수·요원·맵에서 이전 연도 기반 피처를 생성해 예측한다.

## 2. 문제 정의

Valorant는 픽 단계에서 요원 조합, 맵 적합도, 선수-요원 숙련도가 승패에 영향을 준다. 하지만 사용자는 현재 라인업이 어느 정도 유리한지 정량적으로 확인하기 어렵다.

이 프로젝트의 질문은 하나다.

> 지금 선택한 맵에서 양 팀 5명 라인업이 맞붙으면 팀 A가 이길 가능성은 얼마인가?

## 3. 데이터와 피처 전략

학습 데이터는 Kaggle 5개 데이터셋과 VLR.gg 수집 데이터를 통합해 사용한다. 모델 학습·평가의 행 단위는 BO 시리즈 전체 경기가 아니라 **맵 단위 승패 샘플**이다. 현재 advanced 산출물은 train 75,405개 + test 16,053개, 총 **91,458개 맵 단위 승패 샘플**을 사용한다.

| 축 | 정본 |
|---|---|
| 데이터 소스 | `source`가 `kaggle_` 또는 `vlrgg_`로 시작하는 맵 단위 승패 행 |
| 분할 | Baseline은 랜덤 80/20 holdout, Advanced는 시간순 year-block split |
| 누수 방지 | 같은 경기 overlap 0, 금지 피처 0, 이전 연도 prior만 사용 |
| 런타임 입력 재현성 | 맵 + 선수/요원 5명씩으로 생성 가능한 피처만 사용 |

### Baseline 421 Features

Baseline은 LR+DT soft voting(0.50/0.50)이며, 랜덤 80/20 split으로 학습하고 421개 피처를 쓴다.

| 카테고리 | 수 | 설명 |
|---|---:|---|
| 슬롯 선수 피처 | 400 | 10슬롯 × (PRIOR 통계 8 + 요원 ONE-HOT 27 + 역할군 ONE-HOT 5) |
| 맵 원핫 | 12 | 매치 컨텍스트 |
| 팀 합동출전 | 3 | 매치 컨텍스트 |
| 역할 조합 PRIOR | 6 | 매치 컨텍스트 |
| **합계** | **421** | 슬롯 선수 400 + 매치 컨텍스트 21 |

누수 방지는 시간순 누적 평균(LEAK-SAFE)으로 처리한다. 선수별 stat은 최근 20경기 평균을 쓰며, 결측 신인은 전체 중앙값, stat 누락은 누락 제외 평균, 클러치는 0으로 대체한다.

### Advanced 179 Features

Advanced는 RF+XGBoost+LightGBM soft voting이며, 179개 피처를 쓴다. 정본 목록은 `features.preprocess.FEATURE_COLS_ADVANCED`와 `models/advanced/meta.json`의 `feature_names`다.

주요 카테고리는 맵 원핫, 역할군·요원 count, 선수 prior, synergy, 맵×요원, 선수×요원, 팀 form, composition meta, cold-start flag다. 세부 열 목록은 재학습 때 달라질 수 있으므로 문서 표가 아니라 `meta.json`의 `feature_names`를 기준으로 확인한다.

## 4. 모델 성능

두 모델은 서로 다른 분할로 평가한다. Baseline은 랜덤 80/20 holdout, Advanced는 시간순 year-block split(train 2020–2025 / test 2026)이다.

| 모델 | 분할 | 피처 | Test AUC | Test Acc | Test F1 |
|---|---|---:|---:|---:|---:|
| Baseline LR+DT | 랜덤 80/20 | 421 | 0.5943 | 0.5667 | 0.6072 |
| Advanced RF+XGB+LGBM | 시간순 2026 | 179 | **0.7010** | **0.6454** | **0.6478** |

해석 기준:

- 최종 시연 웹 스택은 시간순 split로 검증한 `models/advanced/ensemble.joblib`를 사용한다.
- Advanced 개별 모델 Test AUC는 RF 0.6965 / XGB 0.7007 / LGBM 0.7015이며 soft voting 앙상블이 0.7010이다.
- Baseline(랜덤 80/20)과 Advanced(시간순)는 분할 방식이 달라 직접 비교가 아니라 분할 차이를 명시해 해석한다.

근거 산출물:

| 산출물 | 역할 |
|---|---|
| `reports/baseline/metrics.json` | baseline 421 features, 랜덤 80/20 holdout 성능 |
| `models/advanced/meta.json` | advanced 179 features, 모델/성능/validation 메타 |
| `reports/advanced/validation.json` | feature count, split overlap, source prefix, artifact feature count 검증 |
| `reports/advanced/metrics.json` | 시간순 holdout 성능 |

## 5. 애플리케이션

웹 스택은 FastAPI 백엔드와 Next.js 프런트엔드로 실행한다.

```bash
uvicorn api.main:app --reload --port 8000   # 백엔드
cd web && npm run dev                        # 프런트 (http://localhost:3000)
```

주요 화면:

| 화면 | 역할 |
|---|---|
| 커스텀 라인업 예측 | 맵과 양 팀 선수/요원을 직접 입력해 승률 계산 |
| 경기 다시보기 | test split의 실제 경기로 예측과 실제 결과 비교 |
| 모델 상태 | feature count, 지표, validation verdict 확인 |

## 6. 관련 문서

| 문서 | 내용 |
|---|---|
| [../04_data_processing/06_feature_engineering.md](../04_data_processing/06_feature_engineering.md) | baseline/advanced 피처 계약 |
| [../05_data_learning/03_advanced_models/01_advanced_chrono.md](../05_data_learning/03_advanced_models/01_advanced_chrono.md) | 활성 advanced 모델 정리 |
| [../05_data_learning/03_advanced_models/02_advanced_metric_analysis.md](../05_data_learning/03_advanced_models/02_advanced_metric_analysis.md) | 랜덤 holdout과 시간순 holdout 해석 |
| [../06_model_test/verification_summary.md](../06_model_test/verification_summary.md) | 2모델 성능 종합 (Baseline 랜덤 80/20 vs Advanced 시간순) |
| [../08_web/README.md](../08_web/README.md) | 웹 스택 설계 (FastAPI + Next.js, SSOT) |
