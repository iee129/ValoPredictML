# ② 랜덤순 심화

분할축 **랜덤 holdout** × 모델축 **심화**. 전체 기간의 경기를 무작위로 나눠 평가한, 트리 앙상블 구성의 모델이다.

출처: `reports/adv_kaggle_only/metrics.json`, `reports/adv_kaggle_only/shap_importance.json`, `models/advanced/meta.json`.

## 1. 모델 정의

RandomForest(RF)·XGBoost(XGB)·LightGBM(LGBM)을 soft voting으로 묶은 심화 앙상블을, `match_key` 단위
무작위 80/20 holdout으로 평가한 구성이다. 125개 피처를 사용하며, 베이스라인(①)과 같은 분할 축에서 모델 계열만 바꾼 짝이다.

## 2. 데이터 분할

- **방식**: `match_key` 단위 무작위 80/20 분할(`data/processed/adv_kaggle_only/`). 같은 경기의 맵 행은 한쪽에만 들어간다.
- **튜닝**: 별도 검증셋 없이 train 내부 GroupKFold(group=`match_key`)로 각 모델을 튜닝한 뒤 holdout test로 평가한다.
- **행 수**: train 53,427 / test 13,357 (①과 동일 분할 기반).
- **소스**: Kaggle 소스(`kaggle_*`)만 사용한다. 같은 경기·같은 해 통계는 제외하고 선수 prior는 이전 연도까지만 집계한다.

## 3. 모델 구성

- **알고리즘**: RF + XGB + LGBM soft voting (확률 단순 평균, 가중 1:1:1).
- **피처**: 125개 — 맵 원-핫, 역할군·요원 카운트, 선수 prior, synergy, map×agent·player×agent 집계.
  심화 계약은 `a_*`·`b_*`를 분리하며 `diff_*`를 두지 않는다.
- **하이퍼파라미터 탐색**: Optuna `TPESampler(seed=42)`로 각 모델 50 trial. study는
  `reports/adv_kaggle_only/optuna_studies/*.db`에 저장된다.
  - RF: `n_estimators=89`, `max_depth=10`, `min_samples_leaf=5` (Optuna CV AUC 0.6901)
  - XGB: `n_estimators=242`, `max_depth=10`, `learning_rate=0.099` (Optuna CV AUC 0.7465)
  - LGBM: `n_estimators=192`, `max_depth=8`, `learning_rate=0.179`, `num_leaves=60` (Optuna CV AUC 0.7139)

## 4. 성능 지표

| 모델 | Train AUC | Test AUC | Test Acc | Test F1 |
|------|----------:|---------:|---------:|--------:|
| RF | 0.8051 | 0.7013 | — | — |
| XGB | 0.9741 | 0.7641 | — | — |
| LGBM | 0.9052 | 0.7332 | — | — |
| **Ensemble** | 0.9550 | **0.7570** | **0.6958** | **0.7649** |

- **혼동행렬** (ensemble test, 행=실제 / 열=예측): `[[2684, 3073], [990, 6610]]`
- 랜덤순 베이스라인(①, Test AUC 0.6587) 대비 ensemble Test AUC 차이는 +0.0982.
- ensemble의 train·test AUC 차이는 0.198(개별 모델은 RF 0.104, XGB 0.210, LGBM 0.172).

## 5. 의미 해석

②도 ①과 같은 랜덤 holdout이다. 전 기간에서 무작위로 떼어낸 경기를 맞히는 정도를 보며, train과 test가
같은 시기·소스를 공유한다.
- **SHAP 피처 영향도** (`shap_importance.json`, TreeExplainer, sample 5,000): RF 기준 상위는
  `b_prior_games_mean`, `b_prior_kd_mean`, `a_prior_games_mean`, `a_prior_kd_mean`, `a_prior_adr_mean`로,
  **선수의 이전 연도 출전 경험·교전 성과(prior)** 계열이 상위를 차지한다.
- **permutation 피처 영향도** (ensemble): `b_prior_games_mean`, `a_prior_apr_mean`, `a_synergy_mean`,
  `a_prior_kd_mean`, `a_prior_kast_mean` 순으로, SHAP과 마찬가지로 선수 prior·synergy 계열이 상위다.
- **train–test 차이**: train AUC가 0.955로 test 0.757보다 높다. 트리 앙상블은 train 분포를 깊게 적합하며,
  같은 기간 분포의 holdout test에서 그 신호의 상당 부분이 재현된다.
- 베이스라인(①)과 달리 트리 분기로 피처 간 비선형 상호작용을 학습한다.

## 6. 산출물 경로

| 종류 | 경로 |
|------|------|
| 지표(개별·앙상블·혼동행렬·top_features) | `reports/adv_kaggle_only/metrics.json` |
| SHAP 피처 영향도 | `reports/adv_kaggle_only/shap_importance.json` |
| Optuna study | `reports/adv_kaggle_only/optuna_studies/*.db`, `{rf,xgb,lgbm}_best_params.json` |
| 모델 메타 | `models/advanced/meta.json` |
| 모델 파일 | `models/advanced/{rf,xgb,lgbm,ensemble}.joblib` |
| 그림(ROC·혼동행렬·SHAP summary 등) | `reports/adv_kaggle_only/figures/` |
