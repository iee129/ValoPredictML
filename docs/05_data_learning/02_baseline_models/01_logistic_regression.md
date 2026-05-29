# 01. Logistic Regression 베이스라인 구현

마지막 업데이트: 2026-05-26

## 개요

현재 baseline은 `ml/baseline/` 경로를 그대로 사용한다. 모델 파일도 `models/baseline/model.joblib`, 메타데이터도 `models/baseline/meta.json`에 덮어쓴다.

입력 계약은 UI와 같다.

```
맵 1개
팀 A 선수 5명 + 요원 5명
팀 B 선수 5명 + 요원 5명
```

팀명 기반 prior나 현재 경기 스코어/스탯은 모델 피처에 넣지 않는다. 선수 성능 피처는 현재 경기 연도보다 이전 연도의 기록만 사용한다.

활성 baseline은 Kaggle source만 사용한다. `vlrgg_*` source는 raw table에 남아 있어도 `data/processed/train.csv`, `test.csv` 생성 전에 제외한다.

세부 피처 명세: [../../04_data_processing/06_feature_engineering.md](../../04_data_processing/06_feature_engineering.md)

## 모델

학습기는 LR + DT soft voting이다.

| 구성 | 설정 |
|---|---|
| Logistic Regression | `StandardScaler` + `LogisticRegression(solver="liblinear")` |
| LR 튜닝 | `C in [0.01, 0.1, 1.0, 10.0]`, `l1_ratio in [0.0, 1.0]` |
| Decision Tree 튜닝 | `max_depth in [4, 6, 8, 10]`, `min_samples_leaf in [20, 50, 100]` |
| 선택 기준 | `train + val`에서 5-fold `GroupKFold` by `match_key`, ROC-AUC |
| 최종 모델 | `train + val` 전체로 fit한 `VotingClassifier(voting="soft")` |
| 최종 평가 | `test` holdout |

## 실행

```bash
python -m ml.baseline.preprocess
python -m ml.baseline.train
python -m ml.baseline.evaluate
python -m ml.baseline.validate
```

## 현재 산출물

| 파일 | 내용 |
|---|---|
| `data/processed/train.csv` | previous-year 178피처 baseline modeling split |
| `data/processed/test.csv` | previous-year 178피처 final holdout split |
| `models/baseline/model.joblib` | LR+DT soft-voting 모델 |
| `models/baseline/meta.json` | 입력 계약, 피처 목록, 튜닝 결과, trust verdict |
| `reports/baseline/metrics.json` | CV/test 성능 |
| `reports/baseline/validation.json` | 분리 검증 및 신뢰도 확인 결과 |

## 현재 성능

`reports/baseline/metrics.json` 기준:

| 지표 | 값 |
|---|---:|
| Feature count | 178 |
| Train rows | 53,427 |
| Test rows | 13,357 |
| CV ROC-AUC | 0.6599 ± 0.0016 |
| Test ROC-AUC | 0.6587 |
| Test Accuracy | 0.6290 |
| Test F1 | 0.7231 |

`reports/baseline/validation.json` 기준:

| Gate | 값 |
|---|---|
| Final verdict | `PASS_TRUSTED_PREMATCH_BASELINE` |
| Forbidden feature count | `0` |
| Split overlap count | `0` |
| Same-year exclusion check | `PASS` |
| Permutation top feature | `diff_prior_kd_mean` (Δauc=+0.0259)

## 해석

이 baseline은 높은 숫자를 만들기 위해 현재 경기의 선수 스탯을 쓰지 않는다. Test AUC 0.6587은 UI 입력으로 재현 가능한 pre-match 피처만 사용한다는 점에서 신뢰 가능한 기준선이다.

## 데이터 소스별 성능 비교 계획

| 실험 | source | 상태 |
|------|--------|------|
| Kaggle-only | `kaggle_*` only | 진행 중 (178피처 재학습) |
| Kaggle + VLR.gg | `kaggle_*` + `vlrgg_*` | VLR.gg 스크래핑 완료 후 예정 |

두 실험의 CV/Test AUC를 비교해 VLR.gg 데이터 추가가 성능에 미치는 효과를 측정한다. source contract는 `ml/baseline/preprocess.py`의 `SOURCE_CONTRACT`에서 제어한다.
