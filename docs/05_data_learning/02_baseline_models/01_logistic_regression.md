# 01. Logistic Regression 베이스라인 구현

## 개요

로지스틱 회귀는 ValoPredictML의 첫 번째 베이스라인 모델이다. 선형 결정 경계의 한계를 명확히 하고, 이후 트리 기반 모델과의 성능 차이를 정량적으로 측정하기 위해 사용한다.

---

## 1. 이론 배경

### 1.1 모델 수식

```
P(팀1 승리 | x) = σ(w^T x + b)

σ(z) = 1 / (1 + e^(-z))    # 시그모이드 함수

w^T x = w₁*duelist_team1 + w₂*initiator_team1 + ... + w₁₅*map_encoded
```

### 1.2 손실 함수

이진 교차 엔트로피(Binary Cross-Entropy):

```
L(w, b) = -1/N * Σᵢ [yᵢ log(p̂ᵢ) + (1-yᵢ) log(1-p̂ᵢ)]
```

### 1.3 L2 정규화 (Ridge)

```
L_reg(w) = L(w) + (λ/2) * ||w||²

→ 과적합 방지, 모든 피처 계수 보존 (L1과 달리 계수가 0이 되지 않음)
```

sklearn `LogisticRegression`의 `C` 파라미터: C = 1/λ (클수록 정규화 약함)

---

## 2. 완전한 구현 코드

### 2.1 기본 학습 및 평가

```python
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, f1_score, roc_auc_score,
    classification_report, confusion_matrix
)
from sklearn.pipeline import Pipeline
import logging

logger = logging.getLogger(__name__)


def train_logistic_regression(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    C: float = 1.0,
    max_iter: int = 1000,
    random_state: int = 42
) -> tuple[Pipeline, dict]:
    """
    로지스틱 회귀 베이스라인 학습.

    Args:
        X_train: 학습 피처 (N_train, 15)
        y_train: 학습 레이블 (0: 패, 1: 승)
        X_val: 검증 피처
        y_val: 검증 레이블
        C: 역 정규화 강도 (클수록 정규화 약함)
        max_iter: 최대 반복 횟수
        random_state: 재현성 시드

    Returns:
        pipeline: 학습된 파이프라인 (Scaler + LR)
        metrics: 평가 지표 딕셔너리
    """
    # StandardScaler 필수: LR은 피처 스케일에 민감
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("lr", LogisticRegression(
            C=C,
            penalty="l2",
            solver="lbfgs",
            max_iter=max_iter,
            random_state=random_state
        ))
    ])

    pipeline.fit(X_train, y_train)

    # 검증 평가
    y_pred = pipeline.predict(X_val)
    y_prob = pipeline.predict_proba(X_val)[:, 1]

    metrics = {
        "model": "LogisticRegression",
        "C": C,
        "val_accuracy": accuracy_score(y_val, y_pred),
        "val_f1": f1_score(y_val, y_pred, average="binary"),
        "val_roc_auc": roc_auc_score(y_val, y_prob),
    }

    logger.info(f"LR 학습 완료: {metrics}")
    return pipeline, metrics
```

### 2.2 C 파라미터 그리드 서치

```python
from sklearn.model_selection import GridSearchCV, StratifiedKFold

def tune_logistic_regression(X_train, y_train):
    """
    로지스틱 회귀 C 파라미터 최적화.
    """
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("lr", LogisticRegression(
            penalty="l2",
            solver="lbfgs",
            max_iter=1000,
            random_state=42
        ))
    ])

    param_grid = {
        "lr__C": [0.001, 0.01, 0.1, 1.0, 10.0, 100.0]
    }

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    grid_search = GridSearchCV(
        pipeline,
        param_grid,
        cv=cv,
        scoring="roc_auc",
        n_jobs=-1,
        verbose=1
    )

    grid_search.fit(X_train, y_train)

    print(f"최적 C: {grid_search.best_params_['lr__C']}")
    print(f"최적 CV AUC: {grid_search.best_score_:.4f}")

    return grid_search.best_estimator_
```

### 2.3 전체 베이스라인 평가 함수

```python
def evaluate_baseline_lr(pipeline, X_test, y_test, feature_names):
    """
    로지스틱 회귀 최종 평가 및 계수 분석.
    """
    y_pred = pipeline.predict(X_test)
    y_prob = pipeline.predict_proba(X_test)[:, 1]

    print("=" * 50)
    print("Logistic Regression 베이스라인 평가")
    print("=" * 50)
    print(f"Accuracy:  {accuracy_score(y_test, y_pred):.4f}")
    print(f"F1-Score:  {f1_score(y_test, y_pred):.4f}")
    print(f"ROC-AUC:   {roc_auc_score(y_test, y_prob):.4f}")
    print()
    print("분류 리포트:")
    print(classification_report(y_test, y_pred, target_names=["패", "승"]))

    print("혼동 행렬:")
    cm = confusion_matrix(y_test, y_pred)
    print(f"  TN={cm[0,0]}, FP={cm[0,1]}")
    print(f"  FN={cm[1,0]}, TP={cm[1,1]}")

    # 계수 분석
    analyze_lr_coefficients(pipeline, feature_names)

    return {
        "accuracy": accuracy_score(y_test, y_pred),
        "f1": f1_score(y_test, y_pred),
        "roc_auc": roc_auc_score(y_test, y_prob)
    }
```

---

## 3. 계수(Coefficient) 해석

### 3.1 계수 추출 및 시각화

```python
import matplotlib.pyplot as plt

def analyze_lr_coefficients(pipeline, feature_names):
    """
    로지스틱 회귀 계수를 발로란트 도메인 관점에서 해석.
    """
    lr = pipeline.named_steps["lr"]
    scaler = pipeline.named_steps["scaler"]

    # 원본 스케일로 계수 복원
    # 표준화: x' = (x - μ) / σ → w'_i = w_i * σ_i
    coefficients = lr.coef_[0] / scaler.scale_
    intercept = lr.intercept_[0]

    coef_df = pd.DataFrame({
        "feature": feature_names,
        "coefficient": coefficients,
        "abs_coefficient": np.abs(coefficients),
        "direction": ["긍정 (승리 기여)" if c > 0 else "부정 (패배 기여)"
                      for c in coefficients]
    }).sort_values("abs_coefficient", ascending=False)

    print("\n계수 해석 (원본 스케일):")
    print(coef_df.to_string(index=False))
    print(f"\n절편: {intercept:.4f}")

    # 오즈비 (Odds Ratio)
    coef_df["odds_ratio"] = np.exp(coefficients)
    print("\n오즈비 해석 (1.0 기준, >1: 승리 기여, <1: 패배 기여):")
    print(coef_df[["feature", "odds_ratio"]].to_string(index=False))

    # 시각화
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = ["steelblue" if c > 0 else "salmon" for c in coef_df["coefficient"]]
    ax.barh(coef_df["feature"], coef_df["coefficient"], color=colors)
    ax.axvline(x=0, color="black", linewidth=0.8)
    ax.set_xlabel("계수 값 (양수: 승리 기여, 음수: 패배 기여)")
    ax.set_title("Logistic Regression 피처 계수")
    plt.tight_layout()
    plt.savefig("reports/figures/lr_coefficients.png", dpi=150)
    plt.show()

    return coef_df
```

### 3.2 발로란트 도메인 계수 해석 예시

ValoPredictML 피처 15개에 대한 예상 계수 방향:

| 피처 | 예상 계수 방향 | 해석 |
|------|--------------|------|
| `controller_diff` | + (양수) | Controller 수 차이가 클수록 승리 기여 |
| `has_controller_team1` | + (양수) | Controller 보유 시 승리 확률 상승 |
| `initiator_diff` | + (양수) | Initiator 수 우위가 승리에 기여 |
| `duelist_count_team1` | ± (약함) | Duelist 수만으로는 승패 설명 어려움 |
| `sentinel_diff` | + (약함) | Sentinel 차이의 영향은 맵에 따라 다름 |
| `map_encoded` | ± (맵별 상이) | 특정 맵에서 특정 구성 유리 |

**오즈비 해석 예시:**
```
controller_diff의 오즈비 = 1.45
→ Controller 수 차이가 1 증가할 때, 승리 오즈가 1.45배 증가
→ 승률이 약 31% 상승 (p=0.5 기준)
```

### 3.3 선형 모델의 한계 명시

```python
# 비선형 상호작용 예시 (LR이 포착 못하는 패턴)
"""
발로란트 실제 패턴:
- Duelist 3명 AND Controller 0명 → 매우 불리 (45% 승률)
- Duelist 3명 AND Controller 1명 → 약간 불리 (48% 승률)
- Duelist 2명 AND Controller 2명 → 유리 (55% 승률)

로지스틱 회귀의 예측:
- Duelist 계수 × 3 + Controller 계수 × 0 = 선형 합산
- Controller 0명의 패널티를 단순 선형으로만 표현
- "Duelist 과다 + Controller 부재"의 상호작용 효과 미포착
"""

# XGBoost는 이 패턴을 트리 분기로 포착:
# if duelist >= 3:
#     if controller == 0: → 낮은 승리 확률 (0.42)
#     else: → 중간 승리 확률 (0.51)
# else:
#     if controller >= 2: → 높은 승리 확률 (0.58)
```

---

## 4. 발로란트 도메인 특화 분석

### 4.1 역할군별 승리 기여도

```python
def valorant_role_impact_analysis(pipeline, X_test, y_test, feature_names):
    """
    발로란트 역할군별 승리 기여도 분석.
    """
    lr = pipeline.named_steps["lr"]
    coefficients = dict(zip(feature_names, lr.coef_[0]))

    # 역할군 그룹별 평균 기여도
    role_groups = {
        "Duelist": [f for f in feature_names if "duelist" in f],
        "Initiator": [f for f in feature_names if "initiator" in f],
        "Controller": [f for f in feature_names if "controller" in f],
        "Sentinel": [f for f in feature_names if "sentinel" in f],
    }

    print("\n역할군별 평균 계수 (승리 기여도):")
    for role, features in role_groups.items():
        avg_coef = np.mean([coefficients.get(f, 0) for f in features])
        print(f"  {role}: {avg_coef:+.4f}")

    # 가장 영향력 큰 역할군 차이(diff) 피처
    diff_features = [f for f in feature_names if "diff" in f]
    print("\n역할군 차이(diff) 피처 중요도:")
    for f in diff_features:
        print(f"  {f}: {coefficients.get(f, 0):+.4f}")
```

### 4.2 맵별 계수 효과

```python
def map_specific_lr_analysis(pipeline, X_test, feature_names):
    """
    맵 인코딩 값에 따른 모델 예측 변화 분석.
    """
    # map_encoded의 계수
    map_coef = pipeline.named_steps["lr"].coef_[0][
        feature_names.index("map_encoded")
    ]

    # 발로란트 맵 목록
    maps = {
        0: "Ascent", 1: "Bind", 2: "Haven", 3: "Icebox",
        4: "Breeze", 5: "Fracture", 6: "Pearl", 7: "Lotus"
    }

    print(f"\nmap_encoded 계수: {map_coef:+.4f}")
    print("(계수가 선형이므로 맵 간 균일한 변화량 가정 - LR의 한계)")
    print("→ 실제로는 맵별로 비선형적 구성 유불리 존재")
    print("→ XGBoost는 트리 분기로 맵별 비선형 패턴 포착 가능")
```

---

## 5. 베이스라인 성능 기록

학습 후 결과를 표준 형식으로 기록:

```python
import json
from datetime import datetime

def save_baseline_results(metrics: dict, filepath: str = "results/baseline_lr.json"):
    """
    베이스라인 결과를 JSON으로 저장.
    """
    result = {
        "model": "LogisticRegression",
        "timestamp": datetime.now().isoformat(),
        "metrics": metrics,
        "target": {
            "accuracy": 0.80,
            "roc_auc": 0.82
        },
        "gap_to_target": {
            "accuracy": round(0.80 - metrics["accuracy"], 4),
            "roc_auc": round(0.82 - metrics["roc_auc"], 4)
        }
    }

    with open(filepath, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n결과 저장: {filepath}")
    print(f"목표 대비 정확도 갭: {result['gap_to_target']['accuracy']:+.4f}")
    print(f"목표 대비 AUC 갭:   {result['gap_to_target']['roc_auc']:+.4f}")
```

---

## 6. 예상 성능 및 결론

| 지표 | 예상 성능 | 목표 | 갭 |
|------|---------|------|-----|
| Accuracy | ~0.72 | ≥ 0.80 | -0.08 |
| ROC-AUC | ~0.74 | ≥ 0.82 | -0.08 |
| F1-Score | ~0.70 | - | - |
| 학습 시간 | < 1초 | - | - |

**결론**: 로지스틱 회귀는 목표에 ~8% 미달하지만, 이것이 XGBoost/LightGBM이 채워야 할 성능 갭을 정량화한다. 비선형 패턴 포착 능력이 핵심 차이.

다음 단계: `02_random_forest.md`에서 RF 베이스라인 구축 후 성능 비교.
