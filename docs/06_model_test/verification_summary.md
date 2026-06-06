# 검증 결과 종합 요약 — ValoPredictML

기반: `src/ml/baseline/`·`src/ml/advanced/`의 evaluate/validate 산출물.
본 프로젝트는 베이스라인 1개(랜덤 holdout) + 심화 1개(시간순 holdout), 총 2개 모델을 비교한다.
활성 심화 모델은 시간순 split 산출물인 `reports/advanced/`, `models/advanced/`, `data/processed/advanced/`를 사용한다.

---

## 1. 2모델 성과지표 스냅샷

| 모델 | 분할 | 피처 | Test AUC | Test Acc | Test F1 |
|---|---|---:|---:|---:|---:|
| 베이스라인 (LR+DT) | 랜덤 80/20 | 421 | 0.5943 | 0.5667 | 0.6072 |
| **심화 (RF+XGB+LGBM)** | **시간순 (train 2020–2025 / test 2026)** | **179** | **0.7010** | **0.6454** | **0.6478** |

코드: baseline `src/ml/baseline/{train,evaluate,validate}.py`, advanced `src/ml/advanced/{ensemble,evaluate,validate,feature_importance}.py`.
베이스라인 수치는 발표자료(PDF) 보고값, 심화 수치는 `reports/advanced/metrics.json`·`validation.json`을 정본으로 한다.

## 2. 베이스라인 개별 모델 (랜덤 holdout, 421피처)

| 모델 | ROC-AUC | Accuracy | F1 |
|------|--------:|---------:|---:|
| LR | 0.6000 | 0.5821 | 0.6216 |
| DT | 0.5556 | 0.5483 | 0.5860 |
| **앙상블 (soft voting 0.50/0.50)** | **0.5943** | **0.5667** | **0.6072** |

majority 기준선 대비 앙상블 정확도는 +0.0649 향상이다.

## 3. 심화 개별 모델 (시간순 Test, 179피처)

| 모델 | ROC-AUC |
|------|--------:|
| RF | 0.6965 |
| XGBoost | 0.7007 |
| LightGBM | 0.7015 |
| **Ensemble (Soft Voting 2.0:3.0:0.1)** | **0.7010** |

심화는 `reports/advanced/metrics.json`과 `reports/advanced/validation.json`의 test 지표를 정본으로 사용한다.
앙상블의 Test 종합 지표는 AUC 0.7010 / Acc 0.6454 / F1 0.6478이다.

## 4. 분할·과적합 관찰

- 베이스라인은 `match_key`(경기) 단위 랜덤 80/20으로 분할해, 같은 경기에서 나온 여러 맵 행이 train·test에 동시에 들어가지 않는다.
- 심화는 연도 블록 시간순(train 2020–2025 / test 2026)으로 분할해, 학습 이후 시즌으로 일반화를 점검한다. 행 단위는 BO 시리즈 수가 아니라 맵 단위 승패 샘플이며, `split_overlap_count=0`이다.
- 결과 이후 정보(스코어·라운드·킬·데스·승률 등) 용어는 정규식(`find_forbidden_feature_names`)으로 입력 피처에서 제외하고, 선수 prior는 이전 연도까지만 집계한다.
- 심화 검증 verdict는 `신뢰 가능`(`feature_count=179`, `test AUC ≥ 0.70`)이다.

## 5. 피처 영향도 (`reports/advanced/`)

`src/ml/advanced/feature_importance.py`의 출력은 `reports/advanced/`를 따른다. 진짜 SHAP이 아니라 트리 모델의 `feature_importances_`와 `importance × value` 휴리스틱으로 산출한다.

## 결론

앱과 발표 근거는 시간순 심화 모델(179피처, Test AUC 0.7010)을 대표 모델로 사용한다. 베이스라인(랜덤 80/20, 421피처, Test AUC 0.5943)은 비교 기준점으로 남긴다. 두 수치는 분할·모델 축이 모두 달라 같은 잣대의 우열이 아니다. 활성 산출물·검증·UI 경로는 `advanced` 디렉터리 3종으로 고정한다.
