# 02. LightGBM 하이퍼파라미터 상세 가이드

마지막 업데이트: 2026-05-04

## 개요

LightGBM의 핵심 하이퍼파라미터를 XGBoost와 대응 관계로 비교하며 설명한다. num_leaves와 min_child_samples가 LightGBM에서 가장 중요한 두 파라미터임을 강조한다.
LightGBM은 RF + XGBoost + LightGBM 앙상블 구성원 중 하나다. 스케일링 불필요.

---

## 1. LightGBM vs XGBoost 파라미터 대응표

| XGBoost | LightGBM | 역할 |
|---------|----------|------|
| `max_depth` | `num_leaves` + `max_depth` | 트리 복잡도 |
| `min_child_weight` | `min_child_samples` | 리프 최소 샘플 |
| `gamma` | `min_split_gain` | 분기 임계값 |
| `n_estimators` | `n_estimators` | 트리 수 |
| `learning_rate` | `learning_rate` | 학습률 |
| `subsample` | `subsample` (또는 `bagging_fraction`) | 행 서브샘플링 |
| `colsample_bytree` | `colsample_bytree` (또는 `feature_fraction`) | 열 서브샘플링 |
| `reg_alpha` | `reg_alpha` (또는 `lambda_l1`) | L1 정규화 |
| `reg_lambda` | `reg_lambda` (또는 `lambda_l2`) | L2 정규화 |
| `scale_pos_weight` | `is_unbalance` 또는 `scale_pos_weight` | 클래스 불균형 |

---

## 2. 핵심 파라미터 상세

### 2.1 num_leaves (★★★★★ 가장 중요)

```
역할: 트리당 최대 리프 노드 수 (Leaf-wise 성장의 핵심 제어)
기본값: 31
권장 범위: 20 ~ 300

XGBoost max_depth와의 관계:
num_leaves ≤ 2^(max_depth - 1)
max_depth=5 → max_leaves = 2^4 = 16 (보수적)
max_depth=6 → max_leaves = 2^5 = 32 (기본 31 이유)
max_depth=8 → max_leaves = 2^7 = 128

주의: num_leaves 높이면 과적합 위험 → min_child_samples와 함께 조정
```

| num_leaves | 모델 복잡도 | 사용 시기 |
|-----------|-----------|---------|
| 15~20 | 낮음 | 소규모 데이터 (<2000) |
| 31 (기본) | 중간 | **ValoPredictML 시작점** |
| 63~127 | 높음 | 대규모 데이터, 복잡한 패턴 |
| 255+ | 매우 높음 | 과적합 위험 |

```python
# ValoPredictML Optuna 탐색 범위
num_leaves = trial.suggest_int("num_leaves", 15, 127)
```

### 2.2 min_child_samples (★★★★★ 두 번째로 중요)

```
역할: 리프 노드를 만들기 위한 최소 샘플 수
기본값: 20
권장 범위: 5 ~ 100
별칭: min_data_in_leaf

ValoPredictML (N=5000):
min_child_samples=20: 리프 최소 20샘플 → 전체의 0.4%
min_child_samples=50: 리프 최소 50샘플 → 전체의 1%

규칙: min_child_samples ≥ N * 0.005 (경험칙)
     N=5000 → min_child_samples ≥ 25 권장
```

| 값 | 효과 |
|----|------|
| < 10 | 과적합 위험 |
| 20 (기본) | ValoPredictML 시작점 |
| 30~50 | 안정적 과적합 방지 |
| > 100 | 과소적합 위험 |

### 2.3 max_depth

```
역할: 트리 최대 깊이 (-1: 제한 없음)
기본값: -1 (제한 없음)
권장: num_leaves와 함께 사용

LightGBM은 num_leaves로 주로 제어하지만,
max_depth를 추가 설정하면 극단적 깊이 방지

권장: max_depth = -1 (num_leaves로만 제어) 또는
      max_depth = ceil(log2(num_leaves)) + 1
```

---

## 3. 학습 파라미터

### 3.1 learning_rate

```
역할: 각 트리 기여도 축소
기본값: 0.1
권장 범위: 0.01 ~ 0.3

Early Stopping과 함께 사용:
- lr=0.1, n_estimators=1000, early_stopping=50 → 빠른 수렴
- lr=0.05, n_estimators=2000 → 더 안정적
```

### 3.2 n_estimators (Early Stopping과 함께)

```python
lgb_model = lgb.LGBMClassifier(
    n_estimators=2000,  # 최대값 (Early Stopping이 결정)
    learning_rate=0.05,
)

lgb_model.fit(
    X_train, y_train,
    eval_set=[(X_val, y_val)],
    callbacks=[
        lgb.early_stopping(stopping_rounds=50),  # 50라운드 개선 없으면 중단
        lgb.log_evaluation(period=100),           # 100라운드마다 로그
    ]
)

print(f"실제 사용 트리 수: {lgb_model.best_iteration_}")
```

---

## 4. 서브샘플링 파라미터

### 4.1 subsample / bagging_fraction

```
역할: 트리당 학습 샘플 비율
기본값: 1.0 (sklearn API), 또는 bagging_fraction=1.0
권장 범위: 0.5 ~ 1.0

주의: subsample < 1.0 사용 시 bagging_freq도 설정 필요
```

```python
# sklearn API (subsample 사용)
lgb_model = lgb.LGBMClassifier(
    subsample=0.8,
    subsample_freq=1,  # 매 트리마다 샘플링 (bagging_freq 대응)
)

# Native API (bagging_fraction 사용)
params = {
    "bagging_fraction": 0.8,
    "bagging_freq": 1,  # 0이면 bagging 비활성화
}
```

### 4.2 colsample_bytree / feature_fraction

```
역할: 트리당 사용할 피처 비율
기본값: 1.0
권장 범위: 0.5 ~ 1.0

ValoPredictML (d=15):
feature_fraction=0.8 → 12개 피처 사용
feature_fraction=0.6 → 9개 피처 사용
```

---

## 5. 정규화 파라미터

### 5.1 reg_alpha (L1) / lambda_l1

```
기본값: 0.0
권장 범위: 0.0 ~ 1.0
```

### 5.2 reg_lambda (L2) / lambda_l2

```
기본값: 0.0  (LightGBM 기본값 주의: XGBoost는 1.0)
권장 범위: 0.0 ~ 10.0
```

### 5.3 min_split_gain / min_gain_to_split

```
역할: 분기 시 최소 이득 (XGBoost gamma 대응)
기본값: 0.0
권장 범위: 0.0 ~ 1.0
```

---

## 6. 특수 파라미터

### 6.1 max_bin

```
역할: 연속형 피처를 나눌 최대 bin 수
기본값: 255
권장: ValoPredictML에서 63 또는 127

ValoPredictML 적용:
- 역할군 카운트 값 범위: 0~5 (6가지 값)
- 255 bin은 낭비: 6가지 값을 255 bin으로 나눠봐야 의미없음
- 63 bin 충분: 메모리 절감 + 속도 향상 + 정규화 효과
```

```python
# 피처별 유니크 값 확인 후 max_bin 결정
for feat in feature_names:
    n_unique = X_train[feat].nunique()
    print(f"{feat}: {n_unique}개 유니크 값")

# 결과 예시:
# duelist_team1: 6개 (0,1,2,3,4,5)
# map_encoded: 8개 (0~7)
# has_controller_team1: 2개 (0,1)
# → max_bin=63이면 모든 피처의 유니크 값보다 크므로 충분
```

### 6.2 path_smooth

```
역할: 리프 점수를 부모 방향으로 평활화 (Path Smoothing)
기본값: 0.0
권장 범위: 0.0 ~ 1.0

높은 값: 예측 안정성 증가, 극단값 감소
소규모 데이터에서 유용
```

### 6.3 extra_trees

```
역할: True이면 Extremely Randomized Trees 방식 사용
       분기점을 최적이 아닌 무작위로 선택 → 더 빠름, 과적합 방지
기본값: False
```

---

## 7. 전체 파라미터 표

| 파라미터 | 기본값 | ValoPredictML 권장 | Optuna 탐색 범위 | 우선순위 |
|---------|--------|-------------------|-----------------|---------|
| `num_leaves` | 31 | 20~63 | [15, 127] (int) | ★★★★★ |
| `min_child_samples` | 20 | 20~50 | [10, 100] (int) | ★★★★★ |
| `learning_rate` | 0.1 | 0.05~0.1 | [0.01, 0.3] (log) | ★★★★☆ |
| `n_estimators` | 100 | 500~2000+ES | [200, 2000] (int) | ★★★★☆ |
| `subsample` | 1.0 | 0.7~0.9 | [0.5, 1.0] (float) | ★★★☆☆ |
| `colsample_bytree` | 1.0 | 0.7~0.9 | [0.5, 1.0] (float) | ★★★☆☆ |
| `reg_alpha` | 0.0 | 0.0~0.5 | [0.0, 1.0] (float) | ★★★☆☆ |
| `reg_lambda` | 0.0 | 0.1~3.0 | [0.0, 10.0] (log) | ★★★☆☆ |
| `max_bin` | 255 | 63 | 고정 (63) | ★★☆☆☆ |
| `min_split_gain` | 0.0 | 0.0~0.5 | [0.0, 1.0] (float) | ★★☆☆☆ |
| `max_depth` | -1 | -1 | 고정 (-1) | ★☆☆☆☆ |

---

## 8. 클래스 불균형 처리

```python
# 방법 1: is_unbalance (자동 가중치)
lgb_model = lgb.LGBMClassifier(
    is_unbalance=True,  # 자동으로 neg/pos 비율에 맞게 가중치 설정
)

# 방법 2: scale_pos_weight (수동 설정, XGBoost와 동일)
neg_count = (y_train == 0).sum()
pos_count = (y_train == 1).sum()
scale_pos_weight = neg_count / pos_count

lgb_model = lgb.LGBMClassifier(
    scale_pos_weight=scale_pos_weight,
)

# 방법 3: class_weight (sklearn API)
lgb_model = lgb.LGBMClassifier(
    class_weight="balanced",
)

# ValoPredictML: VCT 데이터에서 팀1/팀2 승률이 50:50이면 불필요
# 데이터 수집 방식에 따라 편향 가능 → 확인 후 결정
```

---

## 9. 빠른 시작 설정

### 9.1 기본 설정 (탐색 시작점)

```python
lgbm_params_starter = {
    # 핵심 구조
    "num_leaves": 31,
    "min_child_samples": 20,
    "max_depth": -1,

    # 학습
    "n_estimators": 1000,
    "learning_rate": 0.05,

    # 서브샘플링
    "subsample": 0.8,
    "subsample_freq": 1,
    "colsample_bytree": 0.8,

    # 정규화
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "min_split_gain": 0.0,

    # 효율화
    "max_bin": 63,
    "verbose": -1,

    # 분류
    "objective": "binary",
    "metric": "binary_logloss",

    # 시스템
    "n_jobs": -1,
    "random_state": 42,
}
```

### 9.2 Optuna 최적화 후 기대 파라미터

```python
expected_optimal_lgbm = {
    "num_leaves": 45,         # 31보다 약간 높게 (더 복잡한 패턴)
    "min_child_samples": 35,  # 20보다 높게 (과적합 방지)
    "learning_rate": 0.06,
    "n_estimators": 780,      # Early Stopping으로 결정
    "subsample": 0.78,
    "colsample_bytree": 0.72,
    "reg_alpha": 0.22,
    "reg_lambda": 0.85,
    "min_split_gain": 0.08,
}
```
