# 01. 모델 비교 상세 분석

마지막 업데이트: 2026-05-05

## 개요

ValoPredictML에서 팀 구성(역할군 조합)으로 경기 결과를 예측하기 위해 여러 머신러닝 알고리즘을 체계적으로 비교한다.
이 문서는 각 알고리즘의 수식, 시간/공간 복잡도, 장단점을 상세히 설명한다.
딥러닝(PyTorch/TensorFlow)은 사용하지 않으며, 트리 기반 모델만 채택한다.

---

## 1. Logistic Regression (로지스틱 회귀)

### 1.1 알고리즘 원리

이진 분류 문제에서 사건 발생 확률을 로지스틱 함수(시그모이드)로 모델링한다.

```
P(y=1 | x) = σ(w^T x + b) = 1 / (1 + exp(-(w^T x + b)))
```

**손실 함수 (Binary Cross-Entropy):**
```
L(w) = -1/N * Σ [y_i * log(p_i) + (1 - y_i) * log(1 - p_i)]
```

**정규화 포함 목적 함수:**
```
L_reg(w) = L(w) + λ * ||w||^2   (L2 / Ridge)
L_reg(w) = L(w) + λ * ||w||_1   (L1 / Lasso)
```

### 1.2 복잡도

| 항목 | 복잡도 |
|------|--------|
| 학습 시간 | O(N * d * iter) |
| 추론 시간 | O(d) |
| 메모리 | O(d) |
| N: 샘플 수, d: 피처 수, iter: 반복 횟수 | |

### 1.3 ValoPredictML 적용 시 특성

- **피처 수 d = 43**: 역할군 카운트·파생, 선수 스탯, 시너지, 요원 조합, 맵 피처 전체 (상세 내역은 `preprocessing.md` 7장 참조)
- 선형 결정 경계 → 역할군 조합의 비선형 시너지 효과 포착 불가
- 계수 w를 통해 "Duelist 수가 1 늘면 승률 몇 % 변하는지" 직접 해석 가능
- **메인 모델 후보 아님** — baseline 비교용으로만 사용. StandardScaler 필수.

### 1.4 장단점

| 구분 | 내용 |
|------|------|
| 장점 | 학습/추론 빠름, 계수 해석 직관적, 과적합 위험 낮음 |
| 단점 | 비선형 관계 포착 불가, 역할군 간 상호작용 반영 안 됨 |
| ValoPredictML 역할 | Baseline 비교용 (메인 모델 아님) |

---

## 2. Random Forest (랜덤 포레스트)

### 2.1 알고리즘 원리

**Bagging (Bootstrap Aggregating)** + **Feature Randomization**을 결합한 앙상블 기법.

**학습 과정:**
```
for t = 1 to T:
    D_t = bootstrap_sample(D)          # 복원 추출
    F_t = random_subset(features, m)   # sqrt(d) 개 피처 무작위 선택
    tree_t = fit_decision_tree(D_t, F_t)

final_pred = majority_vote([tree_1(x), ..., tree_T(x)])   # 분류
```

**불순도 측정 (Gini Impurity):**
```
Gini(t) = 1 - Σ p(c|t)^2
```

**정보 이득 (Information Gain):**
```
IG(t, f) = Gini(t) - Σ (|t_i| / |t|) * Gini(t_i)
```

### 2.2 OOB(Out-of-Bag) 에러

Bootstrap 샘플에 포함되지 않은 약 37%의 샘플로 검증 → 별도 validation set 없이 일반화 성능 추정 가능.

```python
from sklearn.ensemble import RandomForestClassifier

rf = RandomForestClassifier(n_estimators=100, oob_score=True, random_state=42)
rf.fit(X_train, y_train)
print(f"OOB Score: {rf.oob_score_:.4f}")
```

### 2.3 복잡도

| 항목 | 복잡도 |
|------|--------|
| 학습 시간 | O(T * N * log(N) * sqrt(d)) |
| 추론 시간 | O(T * log(N)) |
| 메모리 | O(T * N) |

### 2.4 장단점

| 구분 | 내용 |
|------|------|
| 장점 | 과적합 저항성, 피처 중요도 제공, 이상값 강건, 병렬 학습 |
| 단점 | 메모리 사용 많음, 단일 트리보다 해석 어려움, 부스팅보다 정확도 낮을 수 있음 |
| ValoPredictML 역할 | Baseline+ (향상된 기준선) / 앙상블 메인 모델 중 하나 |

---

## 3. XGBoost (eXtreme Gradient Boosting)

### 3.1 알고리즘 원리

**Gradient Boosting**의 최적화 구현. 잔차(Residual)가 아닌 **그래디언트**를 피팅.

**목적 함수:**
```
L(φ) = Σ l(y_i, ŷ_i) + Σ Ω(f_k)
```

**정규화 항:**
```
Ω(f) = γT + (1/2)λ||w||^2
```
- T: 리프 노드 수 (트리 복잡도 제어)
- λ: 가중치 L2 정규화
- γ: 리프 추가 페널티

**2차 테일러 근사:**
```
L^(t) ≈ Σ [g_i * f_t(x_i) + (1/2) * h_i * f_t(x_i)^2] + Ω(f_t)
```
- g_i = ∂l(y_i, ŷ^(t-1)) / ∂ŷ^(t-1)  (1차 미분, gradient)
- h_i = ∂²l(y_i, ŷ^(t-1)) / ∂(ŷ^(t-1))²  (2차 미분, hessian)

**최적 리프 점수:**
```
w_j* = -G_j / (H_j + λ)
```

**분기 이득:**
```
Gain = (1/2) * [G_L² / (H_L + λ) + G_R² / (H_R + λ) - (G_L + G_R)² / (H_L + H_R + λ)] - γ
```

### 3.2 복잡도

| 항목 | 복잡도 |
|------|--------|
| 학습 시간 | O(T * d * N * log(N)) |
| 추론 시간 | O(T * max_depth) |
| 메모리 | O(N * d) |

### 3.3 장단점

| 구분 | 내용 |
|------|------|
| 장점 | 높은 예측 정확도, 정규화 내장, 결측값 처리, 병렬 처리, Early Stopping |
| 단점 | 하이퍼파라미터 많음, 학습 데이터 적을 때 과적합 가능 |
| ValoPredictML 역할 | 앙상블 메인 모델 (RF + XGBoost + LightGBM 확률 평균) |

---

## 4. LightGBM (Light Gradient Boosting Machine)

### 4.1 알고리즘 원리

XGBoost 대비 두 가지 핵심 혁신:

**GOSS (Gradient-based One-Side Sampling):**
```
그래디언트 큰 샘플 100% 유지
그래디언트 작은 샘플 → 상위 a% 유지, 나머지 b% 랜덤 샘플링
가중치 보정: 작은 그래디언트 샘플에 (1-a)/b 곱하여 편향 제거
```

**EFB (Exclusive Feature Bundling):**
```
상호 배타적인 피처들(동시에 0이 아닌 경우 드문)을 묶어 하나의 피처로 처리
그래프 컬러링 문제로 모델링 → 피처 수 감소
```

**Leaf-wise 성장 (vs Level-wise):**
```
Level-wise: 같은 깊이의 모든 리프 분기 → 균형 트리
Leaf-wise: 손실 감소가 가장 큰 리프만 분기 → 비균형 트리, 더 낮은 오차
```

### 4.2 복잡도

| 항목 | 복잡도 |
|------|--------|
| 학습 시간 | O(T * d' * b) — d' << d (EFB), b: bin 수 |
| 추론 시간 | O(T * max_depth) |
| 메모리 | O(N * d') |

### 4.3 장단점

| 구분 | 내용 |
|------|------|
| 장점 | XGBoost 대비 5-10배 빠른 학습, 메모리 효율적, 카테고리 피처 지원 |
| 단점 | 소규모 데이터에서 불안정, Leaf-wise로 인한 과적합 위험 |
| ValoPredictML 역할 | 앙상블 메인 모델 (RF + XGBoost + LightGBM 확률 평균) |

---

## 5. CatBoost

### 5.1 알고리즘 원리

**Ordered Boosting**: 학습 순서에 따른 타겟 리키지(Target Leakage) 방지

**카테고리 피처 처리:**
```
TS(category) = (sum_of_target_in_category + prior) / (count_in_category + 1)
```
- Ordered TS: 현재 샘플 이전의 데이터만 사용하여 통계 계산 → 편향 방지

### 5.2 ValoPredictML 적합성

- map_encoded: 이미 Label Encoding 처리됨 → CatBoost 고유 기능 활용도 낮음
- 나머지 피처 모두 수치형 → CatBoost의 핵심 강점 미활용
- 학습 속도 느려 프로토타입 단계에서 비효율

### 5.3 장단점

| 구분 | 내용 |
|------|------|
| 장점 | 범주형 피처 자동 처리, 타겟 리키지 방지, 파라미터 조정 최소화 |
| 단점 | 학습 느림, 수치형만 있으면 XGBoost/LightGBM 대비 이점 없음 |
| ValoPredictML 역할 | 선택적 (범주형 피처 확장 시 고려) |

---

## 6. MLP (Multi-Layer Perceptron, 신경망)

### 6.1 알고리즘 원리

**순전파 (Forward Propagation):**
```
h^(1) = σ(W^(1) x + b^(1))
h^(l) = σ(W^(l) h^(l-1) + b^(l))
ŷ = softmax(W^(L) h^(L-1) + b^(L))
```

**역전파 (Backpropagation):**
```
∂L/∂W^(l) = ∂L/∂h^(l) * (∂h^(l)/∂W^(l))
```

**일반적인 활성화 함수:**
```
ReLU(x) = max(0, x)
Sigmoid(x) = 1 / (1 + e^(-x))
Tanh(x) = (e^x - e^(-x)) / (e^x + e^(-x))
```

### 6.2 ValoPredictML 적합성

- 데이터 크기: VCT 2021-2023 경기 수 ~수천 건 → 신경망에는 상대적으로 소규모
- 피처 수 d = 43 → 신경망의 복잡한 표현 능력 과잉
- Dropout, Batch Normalization 등 추가 튜닝 비용 대비 효과 불명확

### 6.3 장단점

| 구분 | 내용 |
|------|------|
| 장점 | 복잡한 비선형 패턴, 피처 자동 추출 잠재력 |
| 단점 | 소규모 데이터에서 과적합, 학습 불안정, 해석 어려움, 추론 느림 |
| ValoPredictML 역할 | 선택적 (데이터 10만+ 확보 시 재고려) |

---

## 7. 모델 비교 종합표

### 7.1 실제 측정 성능 (K-Fold K=5 기준)

| 모델 | K-Fold AUC | K-Fold Acc | Test AUC | Test Acc | ValoPredictML 역할 |
|------|-----------|-----------|---------|---------|-------------------|
| Random Forest | **0.9449**±0.0012 | 0.8652±0.0017 | 0.9378 | 0.8595 | **앙상블 메인** |
| XGBoost | 0.9343±0.0019 | 0.8488±0.0028 | 0.9281 | 0.8443 | **앙상블 메인** |
| LightGBM | 0.9353±0.0019 | 0.8494±0.0027 | 0.9292 | 0.8480 | **앙상블 메인** |
| **앙상블 (단순 평균)** | **0.9414**±0.0017 | 0.8580±0.0034 | 0.9355 | 0.8540 | **최종 모델** |

RF OOB Score: 0.8713. 다수 클래스 baseline 56.9% 대비 앙상블 +29.13%p 개선.

### 7.2 모델 특성 비교

| 모델 | 예측 정확도 | 학습 속도 | 해석 가능성 | 메모리 | 과적합 저항 | ValoPredictML 역할 |
|------|------------|----------|------------|--------|------------|-------------------|
| Logistic Regression | ★★☆☆☆ | ★★★★★ | ★★★★★ | ★★★★★ | ★★★★☆ | Baseline 비교용 (메인 아님) |
| Random Forest | ★★★★☆ | ★★★☆☆ | ★★★☆☆ | ★★☆☆☆ | ★★★★★ | **앙상블 메인** |
| XGBoost | ★★★★★ | ★★★★☆ | ★★★★☆ | ★★★☆☆ | ★★★★☆ | **앙상블 메인** |
| LightGBM | ★★★★★ | ★★★★★ | ★★★★☆ | ★★★★☆ | ★★★☆☆ | **앙상블 메인** |
| CatBoost | ★★★★☆ | ★★★☆☆ | ★★★☆☆ | ★★★☆☆ | ★★★★☆ | 선택적 |
| MLP | ★★★☆☆ | ★★★☆☆ | ★☆☆☆☆ | ★★★☆☆ | ★★☆☆☆ | 미사용 (딥러닝 금지) |

---

## 8. 결론

ValoPredictML의 피처 구조(43개 피처, 수치형 위주)와 데이터 규모(VCT 2021~2026, 약 80~100K 맵 행)를 고려할 때:

1. **RF + XGBoost + LightGBM 앙상블**: 세 모델의 예측 확률을 단순 평균 → 최종 승률 산출
2. **딥러닝(MLP, PyTorch, TensorFlow) 미사용**: tabular 데이터는 트리 기반 모델이 우위
3. **Logistic Regression**: 메인 모델 후보 아님 — baseline 성능 하한선 설정 용도만
4. **평가 지표**: Accuracy, ROC-AUC, F1 / K-Fold (K=5) 교차 검증으로 일반화 성능 확인

상세 선택 근거는 `02_selection_rationale.md`, 앙상블 설계는 `03_ensemble_design.md` 참조.
