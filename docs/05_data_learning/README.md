# 05_data_learning — 모델 학습

ML 모델 전략, 학습, 앙상블, 성능 비교, 한계 해석을 다루는 문서 모음. 최종 보고서에서는 **baseline 설정 → 알고리즘 선택 → 하이퍼파라미터 고정 + 가중치 grid search → 성능 비교 → 한계 해석** 순서로 이 장을 사용한다. 상세 색인은 [data_learning.md](data_learning.md) 참조.

## 모델 전략

이 프로젝트는 두 모델을 함께 다룬다.

- **베이스라인: LR + DT soft voting** — 선형 모델(로지스틱 회귀)과 단일 결정 트리를 0.50/0.50 동일 가중으로 soft voting. 랜덤 Train 80% / Test 20% 분할. 개선의 기준선을 세우는 용도.
- **심화(메인): RF + XGBoost + LightGBM soft voting** — 세 모델의 예측 확률을 가중 평균(RF 2.0 : XGB 3.0 : LGBM 0.1)하여 최종 승률 산출. 시간순 year-block 분할(train 2020–2025 / test 2026), 91,458개 맵 단위 승패 샘플.

| 모델 | 선정 이유 |
|------|----------|
| Random Forest | 여러 결정 트리를 독립적으로 학습 후 평균 — 안정적, 과적합 저항 |
| XGBoost | 이전 트리의 오차를 보정하며 반복 학습 — tabular 데이터에 강함 |
| LightGBM | XGBoost와 동일 방식, 학습 속도·메모리 효율 우수 |

앙상블을 선택한 이유: 모델마다 잘 잡는 패턴이 다르다. 한 모델이 놓친 패턴을 다른 모델이 보완하므로, 단일 모델 대비 예측 분산이 줄어 더 안정적이다. (앙상블 Test AUC 0.7010은 단일 최고 LGBM 0.7015와 실질 동률이며, 이점은 정확도 상회가 아니라 분산 감소·안정성이다.)

**검증 전략**

- 베이스라인: `train + val` 내에서 `match_key` 단위 5-fold GroupKFold로 LR/DT 하이퍼파라미터를 고르고, test holdout으로 최종 평가.
- 심화: RF/XGB/LGBM은 코드 고정 하이퍼파라미터를 사용하고, soft voting 가중치만 검증 split 기준 grid search로 결정한다. test(2026)는 최종 평가에만 사용. ★ Optuna는 현재 적용하지 않는다(향후 계획).

---

## 모델 성능 (완료)

| 모델 | 피처 | 분할 | Test AUC | Test Acc | Test F1 |
|---|---:|---|---:|---:|---:|
| Baseline LR+DT soft voting | 421 | random 80/20 | 0.5943 | 0.5667 | 0.6072 |
| Advanced RF+XGB+LGBM soft voting | 179 | chrono (train 2020–2025 / test 2026, 맵 단위 승패 샘플) | **0.7010** | **0.6454** | **0.6478** |

- 베이스라인 수치는 강의 산출물(PDF) 기준이다(앙상블 AUC 0.5943; 개별 lr 0.6000 / dt 0.5556, majority 대비 +0.0649, baseline_random AUC 0.4864).
- 심화 수치는 현행 구현 코드(`reports/advanced/metrics.json`) 기준이다(개별 Test RF 0.6965 / XGB 0.7007 / LGBM 0.7015, `final_verdict=신뢰 가능`).
- 베이스라인은 랜덤 분할, 심화는 시간순 분할을 사용한다. 분할 방식이 다르므로 두 AUC를 1:1로 직접 비교하지 않는다.

## 서브디렉토리 목록

| 디렉토리 | 내용 |
|---------|------|
| [01_model_strategy/](01_model_strategy/) | 모델 비교, 선정 근거, 앙상블 설계 |
| [02_baseline_models/](02_baseline_models/) | LR+DT soft voting 베이스라인 및 성능 기준 |
| [03_advanced_models/](03_advanced_models/) | 시간순 심화 모델, 지표 상승 원인 분석 |
| [03_xgboost/](03_xgboost/) | XGBoost 알고리즘, 하이퍼파라미터, 학습 구현 |
| [04_lightgbm/](04_lightgbm/) | LightGBM 알고리즘, 하이퍼파라미터, 학습 구현 |
| [05_optimization/](05_optimization/) | 하이퍼파라미터 최적화 — 현행 고정값 + 가중치 grid search, Optuna는 향후 계획 |
