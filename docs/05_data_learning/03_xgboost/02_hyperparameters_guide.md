# 02. XGBoost 하이퍼파라미터 상세 가이드

마지막 업데이트: 2026-06-04

## 개요

XGBoost의 모든 주요 하이퍼파라미터를 역할, 영향, 권장 범위와 함께 설명한다.
XGBoost는 RF + XGBoost + LightGBM 가중 soft voting 앙상블 구성원 중 하나다. 스케일링 불필요.

> 현행 심화 XGBoost는 **코드 고정 하이퍼파라미터**를 사용한다(Optuna 미사용): `n_estimators=500`, `max_depth=4`, `learning_rate=0.03`, `subsample=0.8`, `colsample_bytree=0.7`, `min_child_weight=10`, `reg_alpha=0.1`, `reg_lambda=1.0`. 아래 권장 범위·탐색 공간은 일반 가이드이자 향후 자동 HPO 도입 시 참고용이다.

---

## 1. 트리 구조 파라미터

### 1.1 max_depth (트리 최대 깊이)

```
역할: 각 트리의 최대 깊이 제한
기본값: 6
권장 범위: 3 ~ 10
```

| 값 | 효과 | 사용 시기 |
|----|------|---------|
| 3~4 | 단순 모델, 과적합 저항, 빠름 | **ValoPredictML 현행 (max_depth=4 고정)** |
| 5~7 | 균형 (기본값 6) | 피처 간 더 깊은 상호작용 필요 시 |
| 8~10 | 복잡한 패턴, 과적합 위험 | 피처 수 많고 데이터 클 때 |

```python
# ValoPredictML 현행: 피처 179개 (advanced 계약), train ~75K 맵 행
# max_depth=4: 얕은 트리로 과적합 억제 (현행 코드 고정값)
param_xgb = {"max_depth": 4}
```

### 1.2 min_child_weight (리프 최소 hessian 합)

```
역할: 리프 노드를 만들기 위한 최소 hessian(2차 미분) 합
기본값: 1
권장 범위: 1 ~ 10

이진 분류에서 hessian = p*(1-p) ≈ 0.25 (확률 0.5 근처)
→ min_child_weight=5: 리프에 최소 20개 샘플 필요 (5/0.25=20)
```

| 값 | 효과 |
|----|------|
| 1 (기본) | 작은 리프 허용, 과적합 위험 |
| 3~5 | 중간 수준 과적합 방지 |
| 10+ | 강한 과적합 방지, 높은 편향 위험 |

### 1.3 gamma (min_split_loss)

```
역할: 분기 시 최소 손실 감소 요구량 (= 분기 이득의 임계값)
기본값: 0
권장 범위: 0 ~ 5

Gain < gamma: 분기 안 함 → 자연스러운 가지치기
```

```python
# Gain 수식에서의 gamma 역할:
# Gain = 0.5 * [G_L²/(H_L+λ) + G_R²/(H_R+λ) - G_total²/(H_total+λ)] - gamma
# gamma=0.5: 이득이 0.5 미만이면 분기 거부
```

---

## 2. 부스팅 파라미터

### 2.1 n_estimators / num_boost_round (트리 수)

```
역할: 학습할 총 트리 수
기본값: 100
권장 범위: 100 ~ 2000 (Early Stopping과 함께)
```

```python
# Early Stopping 사용 시 n_estimators를 크게 설정
# (실제 사용 트리 수는 early_stopping_rounds에 의해 결정)
xgb_model = xgb.XGBClassifier(
    n_estimators=2000,          # 최대 2000트리
    early_stopping_rounds=50,   # 50 라운드 개선 없으면 중단
    # 실제 사용 트리 수: best_iteration_ 확인
)
```

### 2.2 learning_rate / eta (학습률)

```
역할: 각 트리 기여도 축소 (Shrinkage)
기본값: 0.3
권장 범위: 0.01 ~ 0.3
```

| 학습률 | n_estimators 권장 | 특성 |
|-------|-----------------|------|
| 0.3 | 100~300 | 빠른 학습, 과적합 위험 |
| 0.1 | 300~500 | 균형 (기본 추천) |
| 0.05 | 500~1000 | 안정적, 느림 |
| 0.01 | 1000~2000 | 매우 안정적, 매우 느림 |

```python
# 일반 규칙: learning_rate * n_estimators ≈ 상수
# lr=0.1, n=500 ≈ lr=0.05, n=1000 (비슷한 최종 성능)
```

---

## 3. 정규화 파라미터

### 3.1 reg_alpha (L1 정규화)

```
역할: 리프 점수에 L1(Lasso) 정규화 → 희소성 유도
기본값: 0
권장 범위: 0 ~ 1.0

높은 값: 일부 피처 계수를 0으로 만드는 효과
ValoPredictML: 피처 179개 (advanced 계약), L1 과도하면 정보 손실 위험
```

### 3.2 reg_lambda (L2 정규화)

```
역할: 리프 점수에 L2(Ridge) 정규화 → 가중치 크기 제한
기본값: 1
권장 범위: 0.1 ~ 10.0

수식에서: w_j* = -G_j / (H_j + lambda)
lambda 크면 → 리프 점수 작아짐 → 모델 보수적
```

---

## 4. 서브샘플링 파라미터

### 4.1 subsample (행 서브샘플링)

```
역할: 각 트리 학습 시 사용할 샘플 비율
기본값: 1.0 (전체 사용)
권장 범위: 0.5 ~ 1.0
```

| 값 | 효과 |
|----|------|
| 1.0 | 전체 데이터, 결정론적 |
| 0.8 | 권장 (약간의 무작위성) |
| 0.5 | 강한 정규화, 느린 수렴 |

### 4.2 colsample_bytree (열 서브샘플링 - 트리당)

```
역할: 트리 생성 시 사용할 피처 비율
기본값: 1.0
권장 범위: 0.5 ~ 1.0

ValoPredictML (d=179, advanced 계약): colsample_bytree=0.7 (현행) → 약 125개 피처 사용
```

### 4.3 colsample_bylevel / colsample_bynode

```
colsample_bylevel: 각 트리 깊이(level)에서 피처 비율 재샘플
colsample_bynode:  각 분기점에서 피처 비율 재샘플 (가장 세밀)

일반적으로 colsample_bytree만 사용 (단순화)
```

---

## 5. 전체 파라미터 표

| 파라미터 | 기본값 | ValoPredictML 권장 | Optuna 탐색 범위 | 영향 |
|---------|--------|-------------------|-----------------|------|
| `max_depth` | 6 | 4~8 | [3, 10] (int) | 모델 복잡도 |
| `min_child_weight` | 1 | 1~5 | [1, 10] (int) | 과적합 방지 |
| `gamma` | 0 | 0~0.5 | [0.0, 1.0] (float) | 분기 임계값 |
| `n_estimators` | 100 | 500~1000 + ES | [200, 2000] (int) | 앙상블 크기 |
| `learning_rate` | 0.3 | 0.05~0.15 | [0.01, 0.3] (log) | 학습 속도 |
| `subsample` | 1.0 | 0.7~0.9 | [0.5, 1.0] (float) | 샘플 다양성 |
| `colsample_bytree` | 1.0 | 0.7~0.9 | [0.5, 1.0] (float) | 피처 다양성 |
| `reg_alpha` | 0 | 0~0.5 | [0.0, 1.0] (float) | L1 정규화 |
| `reg_lambda` | 1 | 0.5~3.0 | [0.1, 10.0] (log) | L2 정규화 |
| `scale_pos_weight` | 1 | 자동 계산 | 고정 (불균형 보정) | 클래스 불균형 |

---

## 6. 클래스 불균형 처리

### 6.1 scale_pos_weight

```python
# 클래스 불균형이 있을 경우 (팀1 승률이 50%가 아닐 때)
neg_count = (y_train == 0).sum()
pos_count = (y_train == 1).sum()
scale_pos_weight = neg_count / pos_count

# 예: neg=3000, pos=2000 → scale_pos_weight = 1.5
print(f"scale_pos_weight: {scale_pos_weight:.2f}")

xgb_model = xgb.XGBClassifier(
    scale_pos_weight=scale_pos_weight,
    eval_metric="auc",  # 불균형 시 accuracy 대신 AUC 사용
    ...
)
```

---

## 7. 파라미터 상호작용

### 7.1 학습률 ↔ 트리 수

```
규칙: 학습률을 반으로 줄이면 트리 수를 2배로 늘림
- lr=0.1, n=500 → 최종 성능 A
- lr=0.05, n=1000 → 최종 성능 ≈ A (더 안정적)
- lr=0.01, n=5000 → 최종 성능 ≈ A (매우 안정적, 느림)
```

### 7.2 max_depth ↔ min_child_weight

```
max_depth 높음 + min_child_weight 낮음 → 과적합 위험
max_depth 낮음 + min_child_weight 높음 → 과소적합 위험
밸런스: max_depth=6, min_child_weight=3 (ValoPredictML 권장 시작점)
```

### 7.3 subsample + colsample_bytree 조합

```
과적합이 의심될 때:
- subsample: 0.8 → 0.7 (더 적은 샘플)
- colsample_bytree: 0.8 → 0.7 (더 적은 피처)
- 두 값 동시에 줄이면 학습 속도 저하 + 수렴 불안정

권장: 한 번에 하나씩 조정
```

---

## 8. 빠른 시작 설정

### 8.1 기본 설정 (탐색 시작점)

```python
xgb_params_starter = {
    "n_estimators": 1000,
    "max_depth": 6,
    "learning_rate": 0.1,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 3,
    "gamma": 0.0,
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "scale_pos_weight": 1.0,
    "use_label_encoder": False,
    "eval_metric": "logloss",
    "early_stopping_rounds": 50,
    "random_state": 42,
    "n_jobs": -1,
}
```

### 8.2 현행 심화 XGBoost 고정 하이퍼파라미터

```python
# 현행 코드 고정값 (Optuna 미사용) — reports/advanced/metrics.json 산출 기준
current_xgb_params = {
    "max_depth": 4,            # 얕은 트리로 과적합 억제
    "min_child_weight": 10,    # 리프 최소 hessian 합 (강한 정규화)
    "learning_rate": 0.03,     # 낮은 학습률 + 많은 트리
    "n_estimators": 500,
    "subsample": 0.8,
    "colsample_bytree": 0.7,
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
}
# 이 설정으로 시간순 split XGB Test AUC ≈ 0.7007
```
