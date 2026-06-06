# 2모델 평가 개요

이 폴더는 ValoPredictML의 승률 예측 모델 평가를 기록한다. 본 프로젝트는 **베이스라인 1개 + 심화 1개**, 총 2개 모델을 비교한다. 두 모델은 분할 방식과 알고리즘이 서로 다르다.

- **베이스라인**: LR+DT soft voting, 421피처, **랜덤 80/20 holdout**, Test AUC 0.5943.
- **심화**: RF+XGB+LGBM soft voting, 179피처, **시간순 holdout**(train 2020–2025 / test 2026), 91,458개 맵 단위 승패 샘플, Test AUC 0.7010.

심화 모델 성능 수치의 단일 출처는 `reports/advanced/metrics.json`이고, 검증은 `reports/advanced/validation.json`·`models/advanced/meta.json`을 따른다. 베이스라인 수치는 발표자료(PDF) 보고값을 기준으로 한다.

## 2모델 구성

| | 분할 | 피처 | 알고리즘 | Test AUC | Test Acc | Test F1 |
|---|---|---:|---|---:|---:|---:|
| **베이스라인** | 랜덤 80/20 | 421 | LR+DT soft voting (0.50/0.50) | 0.5943 | 0.5667 | 0.6072 |
| **심화** | 시간순 (train 2020–2025 / test 2026) | 179 | RF+XGB+LGBM soft voting (2.0:3.0:0.1) | 0.7010 | 0.6454 | 0.6478 |

## 두 모델의 차이

### 분할 — 랜덤 holdout(베이스) vs 시간순 holdout(심화)

- **베이스라인은 랜덤 holdout**: 전체 기간의 경기를 `match_key` 단위로 무작위 80/20 분할한다. train과 test가 **같은 시기·소스 분포를 공유**한다. "같은 기간 분포 안에서 보류한 경기를 맞히는 정도"를 본다.
- **심화는 시간순 holdout**: 2020–2025 맵 단위 승패 샘플로 학습하고 2026 샘플로 평가한다. train 연도가 test 연도보다 모두 앞선 **과거→미래** 구성이다. "과거로 학습해 이후 시즌을 맞히는 정도"를 본다.

두 분할은 서로 다른 질문에 답한다. 따라서 0.5943과 0.7010은 같은 잣대의 우열이 아니라 서로 다른 평가 상황에서 잰 값이다.

### 모델 — 베이스라인 vs 심화

- **베이스라인 (421피처)**: 로지스틱 회귀(LR)와 얕은 결정트리(DT)의 soft voting(0.50/0.50). 선수 슬롯 피처 400 + 컨텍스트 21로 구성.
- **심화 (179피처)**: RF·XGBoost·LightGBM의 soft voting(2.0:3.0:0.1). 트리 분기로 비선형 상호작용을 학습한다. Optuna는 사용하지 않고, 피처 중요도는 `feature_importances_`/휴리스틱(진짜 SHAP 아님)으로 산출한다. 요원 29종 / 맵 13종.

## 문서 안내

| 문서 | 내용 |
|------|------|
| [00_overview.md](./00_overview.md) | 이 문서 — 2모델 정의·차이·지표 개요 |
| [01_random_baseline.md](./01_random_baseline.md) | 베이스라인 (랜덤 holdout, 421피처, 0.5943) 단독 분석 |
| [04_chrono_advanced.md](./04_chrono_advanced.md) | 심화 (시간순 holdout, 179피처, 0.7010) 단독 분석 |
| [05_cross_model_comparison.md](./05_cross_model_comparison.md) | 2모델 비교 |

## 관련 문서

- 베이스라인 모델 설계: [`../../05_data_learning/02_baseline_models/`](../../05_data_learning/02_baseline_models/)
- 심화 앙상블 설계: [`../../05_data_learning/03_advanced_models/`](../../05_data_learning/03_advanced_models/)
- 심화 모델 지표 분석: [`../../05_data_learning/03_advanced_models/02_advanced_metric_analysis.md`](../../05_data_learning/03_advanced_models/02_advanced_metric_analysis.md)
