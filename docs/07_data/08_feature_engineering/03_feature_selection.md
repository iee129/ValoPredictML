# 03. 피처 선택 전략

## 1. 문제 정의

115개 피처 → **30~50개 선택**으로 과적합 방지 및 모델 성능 최적화.

| 상황 | 피처 수 | 예상 정확도 | 과적합 위험 |
|------|---------|----------|---------|
| 현재 (기준) | 15 | ~67-72% | 낮음 |
| 전체 사용 | 115 | ~75-80% | 높음 |
| **선택 후 (목표)** | **30~50** | **80-84%** | **낮음** |

---

## 2. 피처 중요도 분석

### 2.1 XGBoost 피처 중요도

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from xgboost import XGBClassifier

def analyze_feature_importance_xgb(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    top_k: int = 40
) -> pd.Series:
    """XGBoost 기반 피처 중요도 분석"""
    model = XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
    )
    model.fit(X_train, y_train)
    
    importance = pd.Series(
        model.feature_importances_,
        index=X_train.columns
    ).sort_values(ascending=False)
    
    print(f"상위 {top_k}개 피처:")
    print(importance.head(top_k))
    
    return importance
```

### 2.2 LightGBM 피처 중요도

```python
import lightgbm as lgb

def analyze_feature_importance_lgb(
    X_train: pd.DataFrame,
    y_train: pd.Series,
) -> pd.Series:
    """LightGBM 기반 피처 중요도 분석"""
    model = lgb.LGBMClassifier(
        n_estimators=300,
        num_leaves=31,
        learning_rate=0.1,
        random_state=42,
    )
    model.fit(X_train, y_train)
    
    importance = pd.Series(
        model.feature_importances_,
        index=X_train.columns
    ).sort_values(ascending=False)
    
    return importance
```

### 2.3 앙상블 중요도 (두 모델 평균)

```python
def ensemble_importance(
    xgb_imp: pd.Series,
    lgb_imp: pd.Series,
    top_k: int = 40,
) -> list[str]:
    """XGBoost + LightGBM 중요도 평균으로 최종 피처 선택"""
    # 0~1로 정규화
    xgb_norm = (xgb_imp - xgb_imp.min()) / (xgb_imp.max() - xgb_imp.min())
    lgb_norm = (lgb_imp - lgb_imp.min()) / (lgb_imp.max() - lgb_imp.min())
    
    # 공통 피처만 평균
    common_features = xgb_norm.index.intersection(lgb_norm.index)
    avg_importance = (xgb_norm[common_features] + lgb_norm[common_features]) / 2
    
    top_features = avg_importance.nlargest(top_k).index.tolist()
    print(f"[INFO] 앙상블 기준 상위 {top_k}개 피처 선택")
    return top_features
```

---

## 3. SHAP 값 기반 분석

```python
import shap

def analyze_shap_values(
    model: XGBClassifier,
    X_test: pd.DataFrame,
    sample_size: int = 500,
) -> None:
    """SHAP 값으로 피처 영향력 시각화"""
    X_sample = X_test.sample(min(sample_size, len(X_test)), random_state=42)
    
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_sample)
    
    # 전체 피처 중요도
    shap.summary_plot(shap_values, X_sample, plot_type="bar", max_display=30)
    
    # 상세 분포
    shap.summary_plot(shap_values, X_sample, max_display=20)
```

---

## 4. Recursive Feature Elimination (RFE)

```python
from sklearn.feature_selection import RFECV
from sklearn.model_selection import StratifiedKFold

def rfe_feature_selection(
    X: pd.DataFrame,
    y: pd.Series,
    min_features: int = 20,
    max_features: int = 50,
) -> list[str]:
    """RFECV로 최적 피처 수 자동 탐색"""
    from xgboost import XGBClassifier
    
    base_model = XGBClassifier(n_estimators=100, random_state=42)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    
    rfe = RFECV(
        estimator=base_model,
        step=5,
        cv=cv,
        scoring="accuracy",
        min_features_to_select=min_features,
        n_jobs=-1,
    )
    rfe.fit(X, y)
    
    selected = X.columns[rfe.support_].tolist()
    print(f"[RFE] 선택된 피처 수: {len(selected)}")
    print(f"[RFE] 최적 CV 정확도: {rfe.cv_results_['mean_test_score'].max():.4f}")
    
    return selected
```

---

## 5. 피처 상관관계 분석

```python
def remove_correlated_features(
    df: pd.DataFrame,
    features: list[str],
    threshold: float = 0.95,
) -> list[str]:
    """상관계수 > threshold인 피처 쌍에서 하나 제거"""
    corr_matrix = df[features].corr().abs()
    upper = corr_matrix.where(
        np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
    )
    
    to_drop = [col for col in upper.columns if any(upper[col] > threshold)]
    remaining = [f for f in features if f not in to_drop]
    
    print(f"[INFO] 상관관계로 제거: {len(to_drop)}개")
    print(f"[INFO] 남은 피처: {len(remaining)}개")
    
    return remaining
```

---

## 6. 최종 피처 선택 파이프라인

```python
def select_final_features(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    target_count: int = 40,
) -> list[str]:
    """단계별 피처 선택 파이프라인"""
    
    print("=== Step 1: 상관관계 기반 1차 제거 ===")
    all_features = X_train.columns.tolist()
    features = remove_correlated_features(X_train, all_features, threshold=0.95)
    
    print("\n=== Step 2: 앙상블 피처 중요도 ===")
    xgb_imp = analyze_feature_importance_xgb(X_train[features], y_train)
    lgb_imp = analyze_feature_importance_lgb(X_train[features], y_train)
    top_features = ensemble_importance(xgb_imp, lgb_imp, top_k=target_count * 2)
    
    print("\n=== Step 3: RFE 최종 선택 ===")
    final_features = rfe_feature_selection(
        X_train[top_features], y_train,
        min_features=int(target_count * 0.7),
        max_features=target_count,
    )
    
    # 검증
    print("\n=== Step 4: 검증셋 성능 확인 ===")
    from xgboost import XGBClassifier
    model = XGBClassifier(n_estimators=300, random_state=42)
    model.fit(X_train[final_features], y_train)
    val_acc = model.score(X_val[final_features], y_val)
    print(f"[결과] 검증 정확도: {val_acc:.4f}")
    
    return final_features
```

---

## 7. 예상 결과

기존 논문 및 유사 프로젝트 기반 추정:

| 피처 그룹 추가 순서 | 정확도 추정 |
|----------------|---------|
| 기본 15개 (현재) | 67~72% |
| + 요원 원-핫 54개 | 73~77% |
| + 맵 원-핫/상호작용 | 75~79% |
| + 조합 품질 피처 | 76~80% |
| + 피처 선택 최적화 | **80~84%** |

---

## 8. 주요 유지 피처 (예상 Top 15)

기존 경험 및 Valorant 게임 지식 기반:

1. `map_encoded` / `map_ascent`, `map_bind`, ... (맵 영향력 가장 큼)
2. `a_controller`, `b_controller` (스모크 필수성)
3. `controller_diff` (컨트롤러 차이)
4. `has_controller_a`, `has_controller_b` (스모크 유무)
5. 맵별 강한 요원 원-핫 (e.g., `a_viper` on Breeze, Icebox)
6. `comp_entropy_a`, `comp_entropy_b` (조합 균형)
7. `a_initiator`, `b_initiator` (정보 수집 역할)
