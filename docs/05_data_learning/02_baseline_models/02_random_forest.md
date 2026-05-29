# 02. Random Forest 구현

마지막 업데이트: 2026-05-04

## 개요

Random Forest는 **앙상블 메인 모델 중 하나**다. RF + XGBoost + LightGBM 세 모델의 예측 확률을 단순 평균하여 최종 승률을 산출한다. 또한 로지스틱 회귀(선형)보다 높은 성능의 비교 기준선(Baseline+)으로도 활용한다. 스케일링 불필요 — 트리 기반 모델은 피처 스케일에 무관하다.

---

## 1. 이론 배경 요약

```
Random Forest = Bagging + Feature Randomization + 다수결 투표

핵심 파라미터:
- n_estimators (T): 트리 수
- max_features (m): 분기 시 고려할 피처 수 (보통 sqrt(d) = sqrt(125) ≈ 11 (advanced 계약))
- max_depth: 각 트리 최대 깊이 (None = 완전 성장)
- min_samples_split: 분기 최소 샘플 수
- min_samples_leaf: 리프 최소 샘플 수
```

---

## 2. 완전한 구현 코드

### 2.1 기본 Random Forest 학습

```python
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, f1_score, roc_auc_score,
    classification_report, confusion_matrix
)
from sklearn.model_selection import StratifiedKFold
import logging

logger = logging.getLogger(__name__)


def train_random_forest(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    n_estimators: int = 200,
    max_depth: int = None,
    min_samples_split: int = 5,
    min_samples_leaf: int = 2,
    max_features: str = "sqrt",
    random_state: int = 42
) -> tuple[RandomForestClassifier, dict]:
    """
    Random Forest 베이스라인 학습.

    Args:
        X_train: 학습 피처 (N_train, 125)  # advanced 계약
        y_train: 학습 레이블
        X_val: 검증 피처
        y_val: 검증 레이블
        n_estimators: 트리 수 (200이면 OOB 오차 안정)
        max_depth: 최대 깊이 (None=완전 성장, 과적합 주의)
        min_samples_split: 분기 최소 샘플 수 (과적합 방지)
        min_samples_leaf: 리프 최소 샘플 수 (과적합 방지)
        max_features: 분기 시 피처 수 ("sqrt"=sqrt(d), "log2"=log2(d))
        random_state: 재현성 시드

    Returns:
        rf: 학습된 Random Forest 모델
        metrics: 평가 지표 딕셔너리
    """
    rf = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        min_samples_split=min_samples_split,
        min_samples_leaf=min_samples_leaf,
        max_features=max_features,
        oob_score=True,         # OOB 에러 계산 (추가 검증 비용 없음)
        class_weight="balanced", # 클래스 불균형 자동 처리
        n_jobs=-1,              # 모든 CPU 코어 사용
        random_state=random_state,
        verbose=0
    )

    rf.fit(X_train, y_train)

    # OOB 점수 (학습 데이터 내 검증, 추가 비용 없음)
    oob_accuracy = rf.oob_score_
    logger.info(f"OOB Accuracy: {oob_accuracy:.4f}")

    # 검증 세트 평가
    y_pred = rf.predict(X_val)
    y_prob = rf.predict_proba(X_val)[:, 1]

    metrics = {
        "model": "RandomForest",
        "n_estimators": n_estimators,
        "oob_accuracy": oob_accuracy,
        "val_accuracy": accuracy_score(y_val, y_pred),
        "val_f1": f1_score(y_val, y_pred, average="binary"),
        "val_roc_auc": roc_auc_score(y_val, y_prob),
    }

    logger.info(f"RF 학습 완료: {metrics}")
    return rf, metrics
```

### 2.2 OOB 에러로 n_estimators 선택

```python
import matplotlib.pyplot as plt

def plot_oob_error_curve(X_train, y_train, max_trees=500, step=20):
    """
    트리 수에 따른 OOB 에러 수렴 곡선.
    OOB 에러가 수렴하는 지점이 최적 n_estimators.
    """
    oob_errors = []
    n_trees_range = range(10, max_trees + 1, step)

    for n_trees in n_trees_range:
        rf = RandomForestClassifier(
            n_estimators=n_trees,
            oob_score=True,
            max_features="sqrt",
            min_samples_leaf=2,
            n_jobs=-1,
            random_state=42
        )
        rf.fit(X_train, y_train)
        oob_errors.append(1 - rf.oob_score_)
        print(f"  n_trees={n_trees:3d}: OOB Error = {oob_errors[-1]:.4f}")

    # 수렴 지점 찾기
    diffs = np.diff(oob_errors)
    convergence_idx = np.argmax(np.abs(diffs) < 0.001)
    optimal_n = list(n_trees_range)[convergence_idx]

    plt.figure(figsize=(10, 5))
    plt.plot(n_trees_range, oob_errors, "b-o", markersize=4)
    plt.axvline(x=optimal_n, color="red", linestyle="--",
                label=f"수렴 지점: n={optimal_n}")
    plt.xlabel("트리 수 (n_estimators)")
    plt.ylabel("OOB 에러율")
    plt.title("Random Forest OOB 에러 수렴 곡선")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("reports/figures/rf_oob_error.png", dpi=150)
    plt.show()

    print(f"\n권장 n_estimators: {optimal_n}")
    return optimal_n
```

### 2.3 하이퍼파라미터 최적화 (RandomizedSearchCV)

```python
from sklearn.model_selection import RandomizedSearchCV

def tune_random_forest(X_train, y_train, n_iter=50):
    """
    RandomizedSearchCV로 RF 하이퍼파라미터 최적화.
    GridSearch보다 빠르고 넓은 탐색 공간 커버.
    """
    param_distributions = {
        "n_estimators": [100, 200, 300, 500],
        "max_depth": [None, 5, 10, 15, 20],
        "min_samples_split": [2, 5, 10, 20],
        "min_samples_leaf": [1, 2, 4, 8],
        "max_features": ["sqrt", "log2", 0.5],
        "bootstrap": [True, False]
    }

    rf_base = RandomForestClassifier(
        oob_score=False,  # RandomizedSearchCV에서는 CV 사용
        n_jobs=-1,
        random_state=42
    )

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    search = RandomizedSearchCV(
        rf_base,
        param_distributions,
        n_iter=n_iter,
        cv=cv,
        scoring="roc_auc",
        n_jobs=-1,
        random_state=42,
        verbose=1
    )

    search.fit(X_train, y_train)

    print(f"\n최적 파라미터:")
    for k, v in search.best_params_.items():
        print(f"  {k}: {v}")
    print(f"최적 CV AUC: {search.best_score_:.4f}")

    return search.best_estimator_
```

---

## 3. OOB 에러 분석

### 3.1 OOB 에러의 원리

```
Bootstrap 샘플링 시 각 샘플이 선택되지 않을 확률:
P(미선택) = (1 - 1/N)^N → e^(-1) ≈ 0.368 (36.8%)

→ 평균적으로 전체 데이터의 36.8%가 각 트리의 OOB 샘플
→ 각 샘플에 대해 그 샘플을 OOB로 사용한 트리들의 평균 예측
→ 별도 검증 세트 없이 일반화 성능 추정 가능
```

### 3.2 OOB vs CV 비교

```python
from sklearn.model_selection import cross_val_score

rf = RandomForestClassifier(n_estimators=200, oob_score=True,
                             n_jobs=-1, random_state=42)
rf.fit(X_train, y_train)

# OOB 정확도
oob_acc = rf.oob_score_

# 5-Fold CV 정확도
cv_scores = cross_val_score(rf, X_train, y_train, cv=5, scoring="accuracy")

print(f"OOB Accuracy:    {oob_acc:.4f}")
print(f"5-Fold CV Mean:  {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
# 두 값이 비슷하면 OOB 추정이 신뢰할 수 있음
```

---

## 4. 피처 중요도

### 4.1 MDI (Mean Decrease Impurity)

```python
def analyze_rf_feature_importance(rf, feature_names, importance_type="mdi"):
    """
    Random Forest 피처 중요도 분석.

    importance_type:
        "mdi": Mean Decrease Impurity (기본값, 빠름, 편향 있음)
        "permutation": Permutation Importance (느림, 편향 없음)
    """
    if importance_type == "mdi":
        importances = rf.feature_importances_
        std = np.std([tree.feature_importances_
                      for tree in rf.estimators_], axis=0)

        importance_df = pd.DataFrame({
            "feature": feature_names,
            "importance": importances,
            "std": std
        }).sort_values("importance", ascending=False)

        print("\nMDI 피처 중요도 (상위 10):")
        print(importance_df.head(10).to_string(index=False))

        # 시각화
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.barh(importance_df["feature"],
                importance_df["importance"],
                xerr=importance_df["std"],
                color="forestgreen", alpha=0.8)
        ax.set_xlabel("중요도 (Gini Impurity 감소량)")
        ax.set_title("Random Forest 피처 중요도 (MDI)")
        plt.tight_layout()
        plt.savefig("reports/figures/rf_feature_importance_mdi.png", dpi=150)
        plt.show()

    elif importance_type == "permutation":
        from sklearn.inspection import permutation_importance

        result = permutation_importance(
            rf, X_val, y_val,
            n_repeats=30,
            random_state=42,
            n_jobs=-1
        )

        importance_df = pd.DataFrame({
            "feature": feature_names,
            "importance_mean": result.importances_mean,
            "importance_std": result.importances_std
        }).sort_values("importance_mean", ascending=False)

        print("\nPermutation 피처 중요도 (상위 10):")
        print(importance_df.head(10).to_string(index=False))

    return importance_df
```

### 4.2 발로란트 도메인 해석

예상 피처 중요도 순위 (MDI 기준):

| 순위 | 피처 | 예상 중요도 | 해석 |
|------|------|------------|------|
| 1 | `controller_diff` | 0.18 | Controller 수 차이가 승패 결정적 영향 |
| 2 | `has_controller_team1` | 0.14 | Controller 존재 여부 핵심 |
| 3 | `initiator_diff` | 0.12 | Initiator 우위가 팀 파이트 이점 |
| 4 | `map_encoded` | 0.11 | 맵에 따른 구성 유불리 |
| 5 | `duelist_diff` | 0.09 | Duelist 수 차이 |
| 6-15 | 나머지 피처 | 0.05~ | 개별 카운트보다 차이 피처가 중요 |

---

## 5. 학습 곡선 분석

```python
from sklearn.model_selection import learning_curve

def plot_learning_curve(rf, X, y):
    """
    학습 데이터 크기에 따른 성능 변화 → 데이터 수집 전략 수립.
    """
    train_sizes, train_scores, val_scores = learning_curve(
        rf, X, y,
        cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
        train_sizes=np.linspace(0.1, 1.0, 10),
        scoring="roc_auc",
        n_jobs=-1
    )

    train_mean = train_scores.mean(axis=1)
    train_std = train_scores.std(axis=1)
    val_mean = val_scores.mean(axis=1)
    val_std = val_scores.std(axis=1)

    plt.figure(figsize=(10, 6))
    plt.plot(train_sizes, train_mean, "o-", color="blue", label="학습 점수")
    plt.fill_between(train_sizes,
                     train_mean - train_std,
                     train_mean + train_std, alpha=0.1, color="blue")
    plt.plot(train_sizes, val_mean, "o-", color="orange", label="검증 점수")
    plt.fill_between(train_sizes,
                     val_mean - val_std,
                     val_mean + val_std, alpha=0.1, color="orange")
    plt.axhline(y=0.82, color="red", linestyle="--", label="미달성 목표 AUC=0.82 (참고용)")
    plt.xlabel("학습 데이터 수")
    plt.ylabel("ROC-AUC")
    plt.title("Random Forest 학습 곡선")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("reports/figures/rf_learning_curve.png", dpi=150)
    plt.show()

    # 데이터 수집 권고 (0.82는 미달성 aspiration 목표 — 현재 최고 0.7570)
    if val_mean[-1] < 0.82:
        gap = val_mean[-2:]
        slope = (gap[1] - gap[0]) / (train_sizes[-1] - train_sizes[-2])
        needed_data = train_sizes[-1] + (0.82 - val_mean[-1]) / slope
        print(f"\n추가 데이터 수집 권고: 미달성 목표(0.82) 기준")
        print(f"  현재 AUC: {val_mean[-1]:.4f}")
        print(f"  추정 필요 샘플 수: ~{int(needed_data)}")
```

---

## 6. 실측 성능

adv_kaggle_only 실측 결과 (80/20 분할, train 53,427 / test 13,357, 125피처):

| 지표 | Logistic Regression | **Random Forest** | RF+XGB+LGBM 앙상블 |
|------|--------------------|--------------------|-------------------|
| Test ROC-AUC | — | **0.7013** | **0.7570** |
| Test Accuracy | — | — | **0.6958** |
| Test F1-Score | — | — | **0.7649** |
| 학습 시간 | < 1초 | **~10초** | ~35초 (3모델 합산) |
| OOB 검증 | 없음 | **있음 (무료)** | 없음 |

**결론**: Random Forest(Test AUC 0.7013)는 LR보다 높은 성능, 비선형 패턴 포착 능력 있음.
앙상블(RF + XGBoost + LightGBM) 구성원으로 피처 중요도 검증 1단계(`feature_importances_`)에도 활용.
평가 지표: Accuracy, ROC-AUC, F1 (reports/adv_kaggle_only/metrics.json).

## 향후 목표(미달성)

- 목표 AUC: 0.82 이상 (2026-05 기준 최고 앙상블 AUC 0.7570으로 미달성)
- 목표 Accuracy: 0.80 이상 (현재 최고 0.6958으로 미달성)
