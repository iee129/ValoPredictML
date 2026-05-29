# 검증 결과 종합 요약 — ValoPredictML

기반: `ml/baseline/`·`ml/advanced/`의 evaluate/validate 산출물.
4모델(분할 × 계열) 산출물: `reports/{baseline, adv_kaggle_only, baseline_chrono, adv_kaggle_chrono}/`.
각 모델 단독·교차 분석은 [`07_model_evaluation/`](./07_model_evaluation/00_overview.md)에 정리한다.

---

## 1. 4모델 성과지표 스냅샷

| # | 모델 | 분할 | 피처 | CV AUC | Test AUC | Test Acc | Test F1 |
|---|------|------|-----:|-------:|---------:|---------:|--------:|
| ① | 랜덤순 베이스라인 (LR+DT) | match_key 랜덤 80/20 | 178 | 0.6599±0.0016 | 0.6587 | 0.6290 | 0.7231 |
| ② | 랜덤순 심화 (RF+XGB+LGBM) | match_key 랜덤 80/20 | 125 | — | 0.7570 | 0.6958 | 0.7649 |
| ③ | 시간순 베이스라인 (LR+DT) | 연도 블록 ≤2023/≥2024 | 178 | 0.6684±0.0103 | 0.6124 | 0.5795 | 0.6226 |
| ④ | 시간순 심화 (RF+XGB+LGBM) | 연도 블록 ≤2023/≥2024 | 125 | — | 0.6182 | 0.5885 | 0.6539 |

코드: baseline `ml/baseline/{train,evaluate,validate}.py`, advanced `ml/advanced/{optimize,ensemble,evaluate,validate,shap_analysis}.py`.

## 2. 랜덤순 심화 개별 모델 (Test, 125피처)

| 모델 | ROC-AUC | Accuracy | F1 |
|------|--------:|---------:|---:|
| RF | 0.7013 | — | — |
| XGBoost | 0.7641 | — | — |
| LightGBM | 0.7332 | — | — |
| **Ensemble (Soft Voting)** | **0.7570** | **0.6958** | **0.7649** |

시간순 심화 개별 모델은 RF 0.6319 / XGB 0.6031 / LGBM 0.6032 / Ensemble 0.6182 (`reports/adv_kaggle_chrono/metrics.json`).

## 3. 다수 클래스 대비 (랜덤 holdout)

| 기준선 | Accuracy |
|--------|---------:|
| 무작위 | 0.5000 |
| 다수 클래스 (label=1) | 0.5690 |
| 랜덤순 베이스라인 (①) | 0.6290 |
| 랜덤순 심화 (②) | 0.6958 |

다수 클래스 정확도 0.5690 대비, 랜덤순 베이스라인은 +6.0%p, 랜덤순 심화는 +12.7%p다.

## 4. 분할·과적합 관찰

- 네 모델 모두 `match_key`(경기) 단위로 분할해, 같은 경기에서 나온 여러 맵 행이 train·test에 동시에 들어가지 않는다.
- 결과 이후 정보(스코어·라운드·킬·데스·승률 등) 용어는 정규식(`find_forbidden_feature_names`)으로 입력 피처에서 제외하고, 선수 prior는 이전 연도까지만 집계한다.
- 심화 앙상블의 train·test AUC 차이는 랜덤 holdout 0.198, 시간순 holdout 0.344이다(상세 [`07_model_evaluation/05_cross_model_comparison.md`](./07_model_evaluation/05_cross_model_comparison.md)).

## 5. SHAP 피처 영향도 (`reports/adv_kaggle_only/shap_importance.json`)

`ml/advanced/shap_analysis.py`가 TreeExplainer로 RF/XGB/LGBM summary와 mean|SHAP|를 산출한다(sample 5,000).
세 모델 공통으로 상위는 **선수의 이전 연도 prior**(`b_prior_games_mean`, `a_prior_games_mean`, `a_prior_kd_mean`,
`a_prior_adr_mean`, `b_prior_adr_mean` 등) — 이전 시즌 출전 경험과 교전 성과(KD/ADR) 누적이 예측에 크게 기여한다.

## 결론

네 모델은 동일한 Kaggle 소스 데이터와 동일한 피처 계약(베이스라인 178 / 심화 125)을 공유하며, **분할 축**(랜덤 / 시간순)과
**모델 축**(베이스라인 / 심화)만 바꿔 측정한 결과다. 랜덤 holdout과 시간순 holdout은 서로 다른 대상을 측정하므로(전 기간
보류 경기 / 학습 이후 기간 경기), 두 분할의 수치는 같은 척도의 우열이 아니라 다른 측정 맥락의 값이다. 분할별·계열별 차이의
의미와 배경은 [`07_model_evaluation/05_cross_model_comparison.md`](./07_model_evaluation/05_cross_model_comparison.md)와
[`../05_data_learning/03_advanced_models/02_advanced_metric_analysis.md`](../05_data_learning/03_advanced_models/02_advanced_metric_analysis.md)에 정리한다.
