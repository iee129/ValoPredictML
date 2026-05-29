# ④ 시간순 심화

분할축 **시간순 holdout** × 모델축 **심화**. 과거 연도로 학습해 이후 연도를 평가한, 트리 앙상블 구성의 모델이다.

출처: `reports/adv_kaggle_chrono/metrics.json`, `reports/adv_kaggle_chrono/split_metadata.json`, `models/advanced_chrono/meta.json`.

## 1. 모델 정의

②와 같은 RF + XGB + LGBM soft voting 심화 앙상블(125피처)을, ③과 같은 연도 블록 시간순 holdout으로
평가한 구성이다. 4모델 중 분할 축(시간순)과 모델 축(심화)을 모두 적용한 짝이다.

## 2. 데이터 분할

- **방식**: 연도 블록 분할 — train 2021–2023, test 2024–2026 (③과 동일 분할 기반, `data/processed/adv_kaggle_chrono/`).
- **행 수**: train 53,897 / test 12,887.
- **라벨 평균**: train 0.5802 / test 0.5220.
- **소스 구성**: train은 qualidea·vct·challengers 중심, test는 challengers·piyush2025·vct 중심으로 train에 없던
  소스(`piyush2024`, `piyush2025`)가 등장한다(상세는 [03_chrono_baseline.md](./03_chrono_baseline.md) §2와 동일).
- **소스 계열**: Kaggle 소스(`kaggle_*`)만 사용한다.

## 3. 모델 구성

- **알고리즘**: RF + XGB + LGBM soft voting (②와 동일 계열, 125피처, `a_*`/`b_*` 분리).
- **하이퍼파라미터 탐색**: Optuna로 이 분할에 대해 독립 탐색 — RF `n_estimators=83`, `max_depth=10` /
  XGB `n_estimators=290`, `max_depth=10`, `learning_rate=0.171` / LGBM `n_estimators=193`, `max_depth=7`,
  `learning_rate=0.236`.

## 4. 성능 지표

| 모델 | Train AUC | Test AUC | Test Acc | Test F1 |
|------|----------:|---------:|---------:|--------:|
| RF | 0.8056 | 0.6319 | — | — |
| XGB | 0.9741 | 0.6031 | — | — |
| LGBM | 0.9025 | 0.6032 | — | — |
| **Ensemble** | 0.9617 | **0.6182** | **0.5885** | **0.6539** |

- **혼동행렬** (ensemble test, 행=실제 / 열=예측): `[[2575, 3585], [1718, 5009]]`
- ensemble의 train·test AUC 차이는 0.344(개별 모델은 RF 0.174, XGB 0.371, LGBM 0.299).
- 다른 모델과의 직접 비교(랜덤순 심화 ②, 시간순 베이스라인 ③ 대비)는 [05_cross_model_comparison.md](./05_cross_model_comparison.md)에서 다룬다.

## 5. 의미 해석

④는 ③과 같은 시간순 구성이다. 2021–2023으로 학습한 심화 앙상블이 2024–2026 경기를 맞히는 정도를 보며,
③과 같은 분포 차이(라벨 비율·소스 구성) 위에서 측정된다.
- **피처 영향도** (permutation, ensemble): `b_prior_games_mean`, `b_prior_fdpr_mean`, `a_prior_games_mean`,
  `b_synergy_mean`, `a_prior_fdpr_mean` 순으로, ②(랜덤순 심화)와 같은 선수 prior·synergy 계열이 상위다.
- **train–test 차이**: train AUC 0.962로 test 0.618보다 높다. 같은 심화 앙상블을 랜덤 분할로 본 ②의
  train–test 차이(0.198)와 비교하면, 시간순 분할에서는 그 차이가 0.344으로 더 크다 — train 기간에 적합된
  신호가 이후 기간 test에 재현되는 비율이 같은 기간 holdout일 때와 다르다.
- 상위 피처 계열은 ②와 같으나, 측정 대상 기간(미래 시즌)이 다르다는 점이 두 구성의 차이다.

## 6. 산출물 경로

| 종류 | 경로 |
|------|------|
| 지표(개별·앙상블·혼동행렬·top_features) | `reports/adv_kaggle_chrono/metrics.json` |
| 분할 메타(연도·소스·라벨 분포) | `reports/adv_kaggle_chrono/split_metadata.json` |
| Optuna study | `reports/adv_kaggle_chrono/optuna_studies/*.db`, `{rf,xgb,lgbm}_best_params.json` |
| 모델 메타 | `models/advanced_chrono/meta.json` |
| 모델 파일 | `models/advanced_chrono/{rf,xgb,lgbm,ensemble}.joblib` |
