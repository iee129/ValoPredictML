# 01. XGBoost 알고리즘 심층 분석

마지막 업데이트: 2026-06-04

## 개요

XGBoost(eXtreme Gradient Boosting)의 내부 동작 원리를 수식과 함께 상세히 설명한다. Gradient Boosting의 이론적 배경부터 XGBoost 고유의 최적화 기법까지 다룬다.
ValoPredictML에서 XGBoost는 RF + XGBoost + LightGBM 가중 soft voting 앙상블의 구성원 중 하나다(가중치 RF 2.0 : XGB 3.0 : LGBM 0.1).

---

## 1. Gradient Boosting 이론

### 1.1 기본 아이디어

약한 학습기(weak learner, 얕은 결정 트리)를 순차적으로 결합하여 강한 학습기(strong learner)를 만든다.

```
F_M(x) = Σ_{m=0}^{M} η * f_m(x)

- F_0(x): 초기 예측 (보통 log-odds 또는 평균)
- f_m(x): m번째 트리
- η: 학습률 (shrinkage)
- M: 전체 트리 수
```

### 1.2 순차적 학습

```
1단계: F_0(x) = argmin_γ Σ L(y_i, γ)
       (이진 분류: F_0 = log(p/(1-p)) where p = mean(y))

2단계: for m = 1 to M:
          r_im = -[∂L(y_i, F(x_i))/∂F(x_i)]_{F=F_{m-1}}  # 음의 그래디언트 (pseudo-residuals)
          f_m = fit_tree(X, r)                               # 잔차에 트리 피팅
          F_m(x) = F_{m-1}(x) + η * f_m(x)
```

---

## 2. XGBoost 핵심 혁신

### 2.1 2차 테일러 근사

기존 Gradient Boosting은 1차 미분(gradient)만 사용하지만, XGBoost는 2차 미분(Hessian)도 활용:

```
L^(t) = Σ L(y_i, ŷ_i^(t-1) + f_t(x_i))

테일러 2차 근사:
L^(t) ≈ Σ [L(y_i, ŷ_i^(t-1)) + g_i * f_t(x_i) + (1/2) * h_i * f_t(x_i)^2] + Ω(f_t)

여기서:
g_i = ∂L(y_i, ŷ^(t-1)) / ∂ŷ^(t-1)    (1차 미분, gradient)
h_i = ∂²L(y_i, ŷ^(t-1)) / ∂(ŷ^(t-1))²  (2차 미분, hessian)
```

**이진 분류(Log Loss)에서의 g, h:**
```
p_i = σ(ŷ_i) = 1 / (1 + exp(-ŷ_i))    (현재 예측 확률)
g_i = p_i - y_i                          (예측확률 - 실제레이블)
h_i = p_i * (1 - p_i)                   (예측 분산)
```

### 2.2 정규화 항 Ω

```
Ω(f) = γT + (1/2) λ ||w||²

- T: 트리의 리프 노드 수
- w_j: j번째 리프의 점수(weight)
- γ: 리프 하나 추가 시 최소 손실 감소 요구량 (트리 복잡도 페널티)
- λ: L2 정규화 (리프 점수 크기 제한)
```

### 2.3 최적 리프 점수 도출

정수 L(t)를 리프 j에 속한 샘플 집합 I_j로 분해:

```
L^(t) = Σ_j [w_j * Σ_{i∈I_j} g_i + (1/2)(Σ_{i∈I_j} h_i + λ) * w_j²] + γT

w_j*로 미분하여 0:
∂L^(t)/∂w_j = Σ_{i∈I_j} g_i + (Σ_{i∈I_j} h_i + λ) * w_j = 0

→ 최적 리프 점수:
w_j* = -(G_j) / (H_j + λ)

여기서:
G_j = Σ_{i∈I_j} g_i    (리프 j의 gradient 합)
H_j = Σ_{i∈I_j} h_i    (리프 j의 hessian 합)
```

**최적 목적 함수 값:**
```
L^(t)* = -(1/2) Σ_j [G_j² / (H_j + λ)] + γT
```

### 2.4 분기 이득(Gain) 계산

좌우 자식 리프(L, R)로 분기 시 이득:

```
Gain = (1/2) * [G_L²/(H_L+λ) + G_R²/(H_R+λ) - (G_L+G_R)²/(H_L+H_R+λ)] - γ

분기 조건:
- Gain > 0: 분기하면 목적 함수 개선 → 분기 실행
- Gain ≤ 0: 분기해도 개선 없음 → 가지치기
```

---

## 3. 트리 분기 알고리즘

### 3.1 Exact Greedy Algorithm

```
for each feature f:
    sorted_values = sort(X[:, f])
    for each candidate split s in sorted_values:
        G_L = Σ g_i (x_i_f < s)
        H_L = Σ h_i (x_i_f < s)
        G_R = G_total - G_L
        H_R = H_total - H_L
        Gain = G_L²/(H_L+λ) + G_R²/(H_R+λ) - G_total²/(H_total+λ) - γ
        if Gain > best_gain:
            best_gain = Gain
            best_split = (f, s)

복잡도: O(d * N * log N)  → d: 피처수, N: 샘플수
```

### 3.2 Approximate Algorithm (히스토그램)

```
for each feature f:
    quantiles = compute_quantiles(X[:, f], n_bins)  # 분위수로 후보 분기점 요약
    for each candidate split s in quantiles:
        compute Gain

복잡도: O(d * b)  → b: bin 수 (보통 256)
→ 대규모 데이터에서 Exact보다 빠르고 성능 유사
```

---

## 4. 추가 최적화 기법

### 4.1 Shrinkage (학습률)

```
ŷ_i^(t) = ŷ_i^(t-1) + η * f_t(x_i)    (η: 학습률, 보통 0.01~0.3)

- η가 작을수록: 더 많은 트리 필요, 과적합 저항성 증가
- η가 클수록: 학습 빠름, 과적합 위험
```

### 4.2 Column Subsampling (피처 서브샘플링)

```
colsample_bytree: 트리당 무작위 피처 비율 선택 (기본: 1.0)
colsample_bylevel: 분기 깊이당 피처 선택
colsample_bynode: 각 분기점마다 피처 선택

→ Random Forest와 유사한 다양성 확보
→ 과적합 방지 + 학습 속도 향상
```

### 4.3 Row Subsampling (샘플 서브샘플링)

```
subsample: 트리당 무작위 샘플 비율 (기본: 1.0, 권장: 0.7~0.9)

→ Stochastic Gradient Boosting
→ 각 트리가 약간 다른 데이터로 학습 → 분산 감소
```

### 4.4 결측값 처리 (Sparsity-Aware)

```
XGBoost가 결측값을 처리하는 방법:
1. 결측 샘플을 좌측 또는 우측 자식으로 기본 할당
2. 두 방향 모두 시도하여 이득이 큰 방향 선택
3. 이 "default direction"을 트리에 저장

ValoPredictML에서는 map_encoded의 결측 가능성 처리에 활용
```

### 4.5 Level-wise vs Depth-wise 성장

```
XGBoost: Level-wise (깊이 우선, BFS)
- max_depth 파라미터로 제어
- 균형 트리 구조
- 과적합 예측 가능

LightGBM: Leaf-wise (손실 우선)
- num_leaves 파라미터로 제어
- 비균형 트리, 더 낮은 오차 가능
- 과적합 위험 높음 (min_child_samples로 제어)
```

---

## 5. 병렬 처리 구조

### 5.1 피처 수준 병렬화

```
for each feature f (parallel):
    compute_gain_for_all_splits(f)

→ 각 피처의 최적 분기점을 동시 계산
→ CPU 코어 수에 비례한 속도 향상
→ nthread 파라미터로 제어
```

### 5.2 블록(Block) 구조

```
데이터를 CSC(Compressed Sparse Column) 형태로 저장:
- 피처별로 미리 정렬된 인덱스
- 분기점 탐색 시 재정렬 불필요
- 캐시 효율적 접근
```

---

## 6. ValoPredictML에서의 알고리즘 적용

### 6.1 피처별 g, h 계산 예시

```python
import numpy as np

def compute_gradients_logistic(y_true, y_pred_logit):
    """
    이진 분류 Log Loss에서 gradient와 hessian 계산.

    Args:
        y_true: 실제 레이블 (0 또는 1)
        y_pred_logit: 로짓 예측값 (F(x))

    Returns:
        g: gradient (p - y)
        h: hessian (p(1-p))
    """
    p = 1 / (1 + np.exp(-y_pred_logit))  # 시그모이드
    g = p - y_true
    h = p * (1 - p)
    return g, h

# 예시: controller_diff=2, duelist_diff=1인 팀 (승리 가능성 높음)
y_true = np.array([1])          # 실제: 승리
y_pred_logit = np.array([0.3])  # 현재 예측 로짓 (낮음, 아직 잘 못 예측)

g, h = compute_gradients_logistic(y_true, y_pred_logit)
print(f"p = {1/(1+np.exp(-0.3)):.4f}")  # 0.574
print(f"g = {g[0]:.4f}")               # 0.574 - 1 = -0.426 (음수: 예측 높여야 함)
print(f"h = {h[0]:.4f}")               # 0.574 * 0.426 = 0.245
```

### 6.2 최적 분기점 탐색 시뮬레이션

```python
def simulate_best_split(X_feature, g, h, lambda_reg=1.0, gamma=0.0):
    """
    단일 피처에서 최적 분기점 탐색 시뮬레이션.
    발로란트 controller_diff 피처에 적용 예시.
    """
    G_total = g.sum()
    H_total = h.sum()
    base_score = G_total**2 / (H_total + lambda_reg)

    sorted_idx = np.argsort(X_feature)
    best_gain = -np.inf
    best_split = None

    G_L, H_L = 0.0, 0.0
    for idx in sorted_idx:
        G_L += g[idx]
        H_L += h[idx]
        G_R = G_total - G_L
        H_R = H_total - H_L

        gain = 0.5 * (G_L**2/(H_L+lambda_reg) +
                      G_R**2/(H_R+lambda_reg) -
                      base_score) - gamma

        if gain > best_gain:
            best_gain = gain
            best_split = X_feature[idx]

    print(f"최적 분기점: {best_split}, 이득: {best_gain:.4f}")
    return best_split, best_gain
```

---

## 7. 알고리즘 복잡도 요약

| 단계 | 복잡도 | 비고 |
|------|--------|------|
| 전처리 (정렬) | O(d × N log N) | 1회만 수행 (블록 구조) |
| 트리 1개 학습 | O(d × N) | 히스토그램 방식 |
| 전체 학습 | O(T × d × N) | T: 트리 수 |
| 추론 (1개) | O(T × max_depth) | 매우 빠름 |
| 메모리 | O(N × d) | 블록 저장 |

ValoPredictML (N~75K train 행, d=179 (advanced 계약), T=500 (XGB n_estimators 고정값), max_depth=4 (XGB 고정값)):
- 전처리: 75000 × 179 × log(75000) ≈ 135M 연산
- 전체 학습: 500 × 179 × 75000 ≈ 6.7B 연산 → 약 20초
- 추론: 500 × 4 = 2,000 연산 → < 1ms

> 하이퍼파라미터는 코드 고정값이다(Optuna 미사용). XGB: `n_estimators=500`, `max_depth=4`, `learning_rate=0.03`.
