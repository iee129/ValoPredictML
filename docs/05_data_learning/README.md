# 05_data_learning — 모델 학습

ML 모델 전략, 학습, 앙상블, 최적화를 다루는 문서 모음. 상세 색인은 [data_learning.md](data_learning.md) 참조.

## 모델 전략

**메인 모델: RF + XGBoost + LightGBM 앙상블**

세 모델의 예측 확률을 평균하여 최종 승률을 산출한다.

| 모델 | 선정 이유 |
|------|----------|
| Random Forest | 여러 결정 트리를 독립적으로 학습 후 다수결 예측 — 안정적인 baseline |
| XGBoost | 이전 트리의 오차를 보정하며 반복 학습 — tabular 데이터에 강함 |
| LightGBM | XGBoost와 동일 방식, 학습 속도·메모리 효율 우수 |

앙상블을 선택한 이유: 모델마다 잘 잡는 패턴이 다르다. 한 모델이 놓친 패턴을 다른 모델이 보완하므로, 단일 모델 대비 예측이 더 안정적이고 정확하다.

**GroupKFold 교차 검증 (K=5)**

train 데이터를 5조각으로 나누고 각 조각을 순서대로 검증셋으로 사용하여 5번 평가 → 평균. `match_key` 단위로 그룹을 설정하여 같은 경기의 행이 train/val에 동시에 들어가는 데이터 누수를 차단한다. test.csv는 K-Fold와 완전히 분리 유지 — 최종 평가에만 한 번 사용.

---

## 모델 성능 (완료)

| 모델 | K-Fold AUC | Test AUC |
|------|-----------|---------|
| Random Forest | 0.9449 | 0.9378 |
| XGBoost | 0.9343 | 0.9281 |
| LightGBM | 0.9353 | 0.9292 |
| **Ensemble** | **0.9414** | **0.9355** |

## 서브디렉토리 목록

| 디렉토리 | 내용 |
|---------|------|
| [01_model_strategy/](01_model_strategy/) | 모델 비교, 선정 근거, 앙상블 설계 |
| [02_baseline_models/](02_baseline_models/) | Logistic Regression, Random Forest 베이스라인 |
| [03_xgboost/](03_xgboost/) | XGBoost 알고리즘, 하이퍼파라미터, 학습 구현 |
| [04_lightgbm/](04_lightgbm/) | LightGBM 알고리즘, 하이퍼파라미터, 학습 구현 |
| [05_optimization/](05_optimization/) | Optuna HPO 설정 및 GroupKFold 최적화 |
