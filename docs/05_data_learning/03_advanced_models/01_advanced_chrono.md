# 01. 시간순 active 심화 모델

마지막 업데이트: 2026-06-04

## 개요

활성 advanced 모델은 시간순 split을 사용한다. 랜덤 holdout 산출물은 더 이상 활성 경로가 아니며, 앱과 검증 스크립트는 아래 세 경로를 기준으로 동작한다.

| 구분 | 경로 |
|---|---|
| 피처 split | `data/processed/advanced/{train,test}.csv` |
| 모델 | `models/advanced/{rf,xgb,lgbm,ensemble,meta}.joblib` |
| 리포트 | `reports/advanced/{metrics,validation,split_metadata}.json` |

입력 계약은 런타임 UI와 같다.

```text
맵 1개
팀 A 선수 5명 + 요원 5명
팀 B 선수 5명 + 요원 5명
```

## 피처 계약

`advanced` 계약은 179개 피처이며 `ml.baseline.preprocess.FEATURE_COLS_ADVANCED`가 단일 진실 공급원이다. 모델 파일과 `meta.json`도 같은 179피처를 선언해야 한다.

## 현재 성능

출처: `reports/advanced/metrics.json`, `reports/advanced/validation.json`, `models/advanced/meta.json`.

| 지표 | 값 |
|---|---:|
| Feature count | 179 |
| Sample unit | 맵 단위 승패 샘플(BO 시리즈 수 아님) |
| Train rows | 75,405 |
| Test rows | 16,053 |
| Train years | 2020-2025 |
| Test years | 2026 |
| Test ROC-AUC | 0.7010 |
| Test Accuracy | 0.6454 |
| Test F1 | 0.6478 |
| 개별 모델 Test AUC | RF 0.6965 / XGB 0.7007 / LGBM 0.7015 |
| soft voting 가중치 | RF 2.0 : XGB 3.0 : LGBM 0.1 |
| 가중치 선택 val AUC | 0.6682 |

`final_verdict`: `신뢰 가능`. 베이스라인(LR+DT soft voting, 랜덤 80/20, PDF)은 AUC 0.5943이며 분할 방식이 달라 직접 비교하지 않는다.

## 실행

```bash
python -m features.chrono_preprocess --include-vlrgg
python -m ml.advanced.ensemble    # 가중 soft voting (RF 2.0 : XGB 3.0 : LGBM 0.1), 고정 하이퍼파라미터 (Optuna 미사용)
python -m ml.advanced.evaluate
python -m ml.advanced.validate
```

## Stale Artifact 방지 규칙

- `models/advanced/*.joblib`의 `n_features_in_`는 반드시 179여야 한다.
- `models/advanced/meta.json`의 `feature_names`는 `ml.baseline.preprocess.FEATURE_COLS_ADVANCED` 순서와 같아야 한다.
- `reports/advanced/validation.json`은 split overlap 0, forbidden feature 0, source prefix 정상, active 시간순 AUC 기준 통과를 만족해야 한다.
- UI는 `models/advanced/`, `reports/advanced/`, `data/processed/advanced/test.csv`, `data/processed/{matches,players}.csv`에서 옵션과 근거를 읽는다.
