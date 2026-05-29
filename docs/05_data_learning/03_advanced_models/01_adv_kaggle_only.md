# 01. adv_kaggle_only 심화 모델

마지막 업데이트: 2026-05-27

## 개요

`adv_kaggle_only`는 VLR.gg 데이터를 섞지 않고 `source.startswith("kaggle_")` 행만 사용하는 심화 모델이다. 입력 계약은 런타임 UI와 동일하다.

```
맵 1개
팀 A 선수 5명 + 요원 5명
팀 B 선수 5명 + 요원 5명
```

## 피처 계약

`advanced` 계약은 128개 피처이며 diff 컬럼을 제외하고 `miks`를 포함한 29개 요원 count를 사용한다.

| 카테고리 | 수 |
|---|---:|
| 맵 원핫 | 13 |
| 역할군 count a/b | 8 |
| 29명 요원 count a/b | 58 |
| 이전 연도 선수 prior 평균 a/b | 16 |
| Synergy a/b | 2 |
| 맵×요원 평균 a/b | 14 |
| 선수×요원 평균 a/b | 14 |
| **합계** | **128** |

데이터 위치: `data/processed/adv_kaggle_only/{train,val,test}.csv`

## 모델 산출물

| 파일 | 내용 |
|---|---|
| `models/advanced/rf.joblib` | Optuna best params로 학습한 RandomForest |
| `models/advanced/xgb.joblib` | Optuna best params로 학습한 XGBoost |
| `models/advanced/lgbm.joblib` | Optuna best params로 학습한 LightGBM |
| `models/advanced/ensemble.joblib` | RF + XGB + LGBM soft-voting 앙상블 |
| `models/advanced/meta.json` | 128피처 계약, feature names, split/source 계약, 성능, validation verdict |
| `reports/adv_kaggle_only/metrics.json` | 현재 모델 평가 결과 |
| `reports/adv_kaggle_only/validation.json` | 분리 검증·소스·모델 계약 확인 결과 |

## 현재 성능

| 지표 | baseline | adv_kaggle_only |
|---|---:|---:|
| Feature count | 178 | 128 |
| Train rows | 53,427 | 53,427 |
| Test rows | 13,357 | 13,357 |
| Test ROC-AUC | 0.6587 | **0.7570** (+0.0983) |
| Test Accuracy | 0.6290 | **0.6958** |
| Test F1 | 0.7231 | **0.7649** |

Validation verdict: `PASS_TRUSTED_KAGGLE_ONLY_ADVANCED`.

## 실행

```bash
python -m ml.baseline.preprocess --feature-contract advanced
python -m ml.advanced.ensemble --input data/processed/adv_kaggle_only --output models/advanced --reports reports/adv_kaggle_only
python -m ml.advanced.evaluate --input data/processed/adv_kaggle_only --models models/advanced --reports reports/adv_kaggle_only
python -m ml.advanced.validate --reports reports/adv_kaggle_only --models models/advanced
```

## Stale Artifact 방지 규칙

- `models/advanced/*.joblib`의 `n_features_in_` 는 반드시 128이어야 한다여야 한다.
- `models/advanced/meta.json`의 `feature_names`는 `ml.baseline.preprocess.FEATURE_COLS_ADVANCED` 순서와 같아야 한다.
- `reports/adv_kaggle_only/validation.json`은 split overlap 0, forbidden feature 0, 모든 source `kaggle_` prefix를 만족해야 한다.
- UI는 `models/advanced/ensemble.joblib`, `models/advanced/meta.json`, `reports/adv_kaggle_only/*.json`, `data/processed/adv_kaggle_only/test.csv`, `data/processed/{matches,players}.csv`에서만 옵션과 근거를 읽는다.
