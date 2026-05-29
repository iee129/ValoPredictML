# 4모델 평가 개요

이 폴더는 ValoPredictML의 승률 예측 모델을 **분할 방식 × 모델 계열**의 2×2 = 4가지 구성으로
개별·교차 기록한다. 각 문서는 성능의 좋고 나쁨을 판정하지 않고, 각 구성이 **무엇을 어떻게 측정한
결과인지**를 산출물 수치 그대로 정리한다.

모든 수치의 단일 출처는 각 실험의 `reports/*/metrics.json`, `split_metadata.json`,
`models/*/meta.json`이다.

## 2×2 구성

|                | 베이스라인 (LR+DT, 178피처) | 심화 (RF+XGB+LGBM, 125피처) |
|----------------|------------------------------|------------------------------|
| **랜덤 holdout** | ① 랜덤순 베이스라인 — Test AUC 0.6587 | ② 랜덤순 심화 — Test AUC 0.7570 |
| **시간순 holdout** | ③ 시간순 베이스라인 — Test AUC 0.6124 | ④ 시간순 심화 — Test AUC 0.6182 |

## 4모델 지표 요약

| # | 모델 | 분할 | 피처 | CV AUC | Test AUC | Test Acc | Test F1 |
|---|------|------|-----:|-------:|---------:|---------:|--------:|
| ① | 랜덤순 베이스라인 | match_key 랜덤 80/20 | 178 | 0.6599±0.0016 | 0.6587 | 0.6290 | 0.7231 |
| ② | 랜덤순 심화 | match_key 랜덤 80/20 | 125 | — | 0.7570 | 0.6958 | 0.7649 |
| ③ | 시간순 베이스라인 | 연도 블록 (≤2023 / ≥2024) | 178 | 0.6684±0.0103 | 0.6124 | 0.5795 | 0.6226 |
| ④ | 시간순 심화 | 연도 블록 (≤2023 / ≥2024) | 125 | — | 0.6182 | 0.5885 | 0.6539 |

> 심화 모델의 CV AUC는 단일 값으로 저장되지 않는다(튜닝을 train 내부 GroupKFold로 수행하고
> 최종 비교는 holdout test 기준). 개별 모델(RF/XGB/LGBM)·confusion matrix 등 상세는 각 모델 문서를 본다.

## 두 개의 평가 축

### 분할 축 — 랜덤 holdout vs 시간순 holdout

- **랜덤 holdout**: 전체 기간(2021–2026)의 경기를 `match_key` 단위로 무작위 80/20 분할한다. 같은 경기에서
  나온 여러 맵 행은 한쪽에만 들어간다. train과 test가 **같은 시기·소스 분포를 공유**한다.
- **시간순 holdout**: 2021–2023 경기로 학습하고 2024–2026 경기로 평가한다. train 연도가 test 연도보다
  모두 앞선 **과거→미래 구성**이며, test에는 train에 없던 시기·소스가 등장한다(자세한 분포는 ③④ 문서).

두 축은 서로 다른 질문에 답한다. 랜덤 holdout은 "같은 기간 분포 안에서 보류한 경기를 맞히는 정도",
시간순 holdout은 "과거로 학습해 이후 시즌을 맞히는 정도"를 본다.

### 모델 축 — 베이스라인 vs 심화

- **베이스라인 (178피처)**: 로지스틱 회귀(LR)와 얕은 결정트리(DT)의 soft voting. `diff_*`(양 팀 차이) 피처 포함.
- **심화 (125피처)**: RF·XGBoost·LightGBM의 soft voting. Optuna로 각 모델을 개별 튜닝. `a_*`/`b_*` 분리 피처.

두 계열은 모두 Kaggle 소스만(`kaggle_*`) 사용하고, 같은 경기·같은 해 통계를 입력에서 제외한 prematch 입력으로
재현되도록 구성된다.

## 문서 안내

| 문서 | 내용 |
|------|------|
| [00_overview.md](./00_overview.md) | 이 문서 — 4모델 정의·축·지표 개요 |
| [01_random_baseline.md](./01_random_baseline.md) | ① 랜덤순 베이스라인 단독 분석 |
| [02_random_advanced.md](./02_random_advanced.md) | ② 랜덤순 심화 단독 분석 |
| [03_chrono_baseline.md](./03_chrono_baseline.md) | ③ 시간순 베이스라인 단독 분석 |
| [04_chrono_advanced.md](./04_chrono_advanced.md) | ④ 시간순 심화 단독 분석 |
| [05_cross_model_comparison.md](./05_cross_model_comparison.md) | 4모델 교차 비교 |

## 관련 문서

- 심화 모델 지표의 분할별 차이에 대한 원인 분석: [`../../05_data_learning/03_advanced_models/02_advanced_metric_analysis.md`](../../05_data_learning/03_advanced_models/02_advanced_metric_analysis.md)
- 베이스라인 모델 설계: [`../../05_data_learning/02_baseline_models/`](../../05_data_learning/02_baseline_models/)
- 심화 앙상블 설계: [`../../05_data_learning/03_advanced_models/`](../../05_data_learning/03_advanced_models/)
