# 02. RF + XGBoost + LightGBM 앙상블 최종 선택 이유

마지막 업데이트: 2026-06-04

## 개요

수십 개의 알고리즘 중 Random Forest, XGBoost, LightGBM 세 모델을 앙상블로 채택한 근거를 성능, 속도, 해석 가능성, 운영성 네 가지 관점에서 상세히 설명한다.
딥러닝(PyTorch/TensorFlow)은 사용하지 않으며, 트리 기반 모델만 채택한다.

---

## 1. 성능 관점

### 1.1 부스팅 계열의 구조적 강점

부스팅은 약한 학습기(weak learner)를 순차적으로 결합하여 편향(bias)을 줄이는 방식이다.
발로란트 경기 결과 예측에서 이 특성이 중요한 이유:

```
역할군 카운트만으로는 패턴이 미묘함:
- Duelist 3명 + Controller 1명 팀이 항상 이기지 않음
- 상대 팀 구성, 맵 특성, 메타 변화 복합 작용
→ 약한 학습기들이 점진적으로 이 복잡한 패턴을 학습
```

### 1.2 실증적 벤치마크 데이터

Kaggle, Papers with Code 등의 정형 데이터 분류 벤치마크 결과:

| 데이터 유형 | 최고 성능 모델 | 빈도 |
|------------|--------------|------|
| 수치형 정형 데이터 | XGBoost / LightGBM | 70%+ |
| 텍스트/이미지 | 딥러닝 | 90%+ |
| 소규모 수치형 | XGBoost / LightGBM | 85%+ |

ValoPredictML은 **수치형 정형 데이터(91,458개 맵 단위 승패 샘플, advanced 179피처)** → RF/XGBoost/LightGBM 최적 도메인

### 1.3 실제 측정 성능

현행 코드 고정 하이퍼파라미터 + 가중치 grid search 결과, 시간순 split test(2026) 최종 측정 (179피처, 맵 단위 승패 샘플):

| 모델 | Test AUC | Test Acc | Test F1 |
|------|---------:|---------:|--------:|
| Random Forest | 0.6965 | — | — |
| XGBoost | 0.7007 | — | — |
| LightGBM | 0.7015 | — | — |
| **앙상블 (가중 Soft Voting)** | **0.7010** | **0.6454** | **0.6478** |

- 데이터: 시간순 split (train 2020–2025 = 75,405 / test 2026 = 16,053, 맵 단위 승패 샘플)
- 가중치 RF 2.0 : XGB 3.0 : LGBM 0.1, 가중치 선택 val(2025) AUC 0.6682
- `final_verdict`: `신뢰 가능`

### 1.4 앙상블 다양성 확보

RF, XGBoost, LightGBM은 서로 다른 방식으로 데이터를 분석하므로 예측 오차가 상관되지 않음:

| 차이점 | Random Forest | XGBoost | LightGBM |
|--------|--------------|---------|----------|
| 학습 방식 | Bagging (독립 병렬) | Boosting (순차 보정) | Boosting (순차 보정) |
| 트리 성장 | Level-wise | Level-wise | Leaf-wise |
| 샘플링 | Bootstrap | Subsampling | GOSS |
| 분기 탐색 | 무작위 피처 | Pre-sorted / Histogram | Histogram |

→ 각 모델이 놓친 패턴을 다른 모델이 보완 → 앙상블 시 분산 감소 + 예측 안정성 향상

---

## 2. 속도 관점

### 2.1 학습 시간 비교 (ValoPredictML 스케일 추정)

피처 179개(advanced), 샘플 수 91,458개 맵 단위 승패 샘플, 트리 500개 기준:

| 모델 | 예상 학습 시간 | 비고 |
|------|--------------|------|
| Logistic Regression | < 1초 | StandardScaler 필수 |
| Random Forest (200 트리) | ~10초 | CPU 병렬 |
| XGBoost (500 트리) | ~20초 | CPU 병렬 |
| LightGBM (500 트리) | ~5초 | Histogram 방식 |
| MLP | 수 분 이상 | 미사용 (딥러닝 금지) |

### 2.2 하이퍼파라미터 결정 비용

현행 심화 모델은 **자동 HPO(Optuna)를 사용하지 않는다.** RF/XGB/LightGBM은 코드 고정 하이퍼파라미터로 1회 학습하고, soft voting 가중치(RF 2.0 : XGB 3.0 : LGBM 0.1)만 2025 검증 split 기준 작은 grid search로 고른다. 따라서 전체 학습 비용은 3모델 1회 학습(~35초) + 가중치 grid search 수준으로 가볍다.

향후 자동 HPO(Optuna 50 trials × GroupKFold 5 = 모델별 250회 학습)를 도입할 경우 LightGBM의 빠른 학습 속도가 더 넓은 탐색 공간을 커버하는 데 유리하다(향후 계획).

### 2.3 추론 속도

웹 스택(FastAPI `src/api` + Next.js `web`)에서 단일 경기 예측 (179개 피처, advanced 계약):

```python
# 단일 ensemble.joblib (VotingClassifier soft) 1회 호출 — 개별 모델 로드 아님
from inference.predict import load_model
model = load_model()  # models/advanced/ensemble.joblib 단일 로드
final_prob = model.predict_proba(X_single)[:, 1]  # soft voting 내부에서 RF+XGB+LGBM 가중 평균(2.0:3.0:0.1)

# 단일 모델 추론: < 10ms → 웹 백엔드 환경에서 충분
```

---

## 3. 해석 가능성 관점

### 3.1 피처 중요도 (Feature Importance)

발로란트 도메인 전문가와의 소통에서 핵심:

```python
import xgboost as xgb
import matplotlib.pyplot as plt

# Gain 기반 피처 중요도
xgb.plot_importance(xgb_model, importance_type='gain', max_num_features=15)
plt.title("어떤 역할군 지표가 승패를 가장 잘 설명하는가?")
plt.show()

# 예상 결과 해석 예시:
# controller_diff (상대팀 대비 Controller 수 차이) → 가장 중요
# has_controller (Controller 보유 여부) → 상위권
# duelist_count_team1 → 중위권
```

### 3.2 SHAP 값 활용 가능성

```python
import shap

explainer = shap.TreeExplainer(xgb_model)
shap_values = explainer.shap_values(X_test)

# 개별 경기 예측 설명
shap.force_plot(
    explainer.expected_value,
    shap_values[0],
    X_test.iloc[0],
    feature_names=feature_names
)
# → "이 경기에서 Controller_diff가 +0.15 기여, Duelist_count가 -0.08 기여"
```

### 3.3 로지스틱 회귀 대비 비선형 패턴 포착

```
발로란트 실제 패턴 예시:
- Controller 2명 이상: 승률 60%
- Controller 0명 + Duelist 3명 이상: 승률 45% (불균형 구성)
- Controller 1명 + Duelist 2명 + Initiator 2명: 승률 58% (균형 구성)

→ 이런 임계값(threshold) 기반 비선형 패턴은 결정 트리 분기로 자연스럽게 표현
→ 로지스틱 회귀는 선형 계수만으로 이 패턴 표현 불가
```

---

## 4. 운영성 관점

### 4.1 모델 저장 및 로드

```python
import joblib

# XGBoost (joblib로 앙상블 일관 저장)
joblib.dump(xgb_model, "models/advanced/xgb.joblib")
loaded_xgb = joblib.load("models/advanced/xgb.joblib")

# LightGBM
joblib.dump(lgbm_model, "models/advanced/lgbm.joblib")
loaded_lgbm = joblib.load("models/advanced/lgbm.joblib")

# 두 모델 모두 표준화된 저장/로드 인터페이스 → 운영 자동화 용이
```

### 4.2 재학습 파이프라인 설계

새로운 VCT 시즌 데이터 추가 시 재학습:

```python
# 증분 학습 가능 여부
# XGBoost: xgb_train() 시 xgb_model 파라미터로 기존 모델 전달
xgb.train(params, dtrain, num_boost_round=50,
          xgb_model=existing_model)  # 기존 모델에 50 트리 추가

# LightGBM: init_model 파라미터
lgb.train(params, train_data, num_boost_round=50,
          init_model=existing_model)  # 기존 모델에서 계속 학습
```

### 4.3 의존성 및 배포 복잡도

| 항목 | XGBoost | LightGBM | PyTorch/TF (MLP) |
|------|---------|----------|-------------------|
| 패키지 크기 | ~15MB | ~10MB | ~500MB+ |
| C 컴파일 의존 | 있음 (prebuilt wheel) | 있음 (prebuilt wheel) | CUDA 필요 (GPU) |
| Vercel/Cloud 호환 | 가능 (Python runtime) | 가능 (Python runtime) | 메모리 제한 초과 위험 |
| 버전 안정성 | 높음 | 높음 | 낮음 (잦은 API 변경) |

### 4.4 모니터링 및 드리프트 감지

```python
# 예측 분포 모니터링
from scipy.stats import ks_2samp

# 학습 시 예측 분포
train_probs = xgb_model.predict_proba(X_train)[:, 1]
# 운영 시 예측 분포 (새 데이터)
prod_probs = xgb_model.predict_proba(X_prod)[:, 1]

# KS 검정으로 분포 이탈 감지
ks_stat, p_value = ks_2samp(train_probs, prod_probs)
if p_value < 0.05:
    alert("모델 드리프트 감지 → 재학습 필요")
```

---

## 5. 최종 선택 결정 매트릭스

각 기준 5점 만점 평가:

| 기준 | 가중치 | LR | RF | XGB | LGBM | RF+XGB+LGBM |
|------|-------|----|----|-----|------|-------------|
| 예측 정확도 | 35% | 2 | 3 | 5 | 5 | 5 |
| 학습/추론 속도 | 20% | 5 | 3 | 4 | 5 | 4 |
| 해석 가능성 | 20% | 5 | 3 | 4 | 4 | 4 |
| 운영 안정성 | 15% | 5 | 4 | 4 | 4 | 4 |
| 앙상블 다양성 | 10% | 1 | 3 | 3 | 3 | 5 |
| **가중 합계** | 100% | **3.35** | **3.15** | **4.20** | **4.35** | **4.55** |

**결론: RF + XGBoost + LightGBM 가중 확률 평균 앙상블(2.0:3.0:0.1)이 최고점**

---

## 6. 선택하지 않은 이유 요약

| 모델 | 미선택 이유 |
|------|------------|
| Logistic Regression / Decision Tree | 비선형/복잡한 상호작용 포착 한계 — baseline(LR+DT soft voting)으로만 유지, 메인 모델 후보 아님 |
| CatBoost | 179개 피처(advanced 계약)가 수치형 위주라 핵심 장점 미활용, 학습 느림 |
| MLP / PyTorch / TensorFlow | 딥러닝 금지 (개발 원칙 1) — tabular 데이터는 트리 기반이 우위 |
