# 03. 예상 성능 및 정확도 가설

마지막 업데이트: 2026-05-04

> 본 프로젝트의 데이터 소스는 Kaggle 7개(2.3GB)로 확정.
> 외부 소스 없이 달성 가능한 현실적 성능 범위를 정의한다.

## 1. 예상 성능 범위

| 지표 | 초기 추정 (43피처 기준) | 실측 (구현 완료) |
|------|------|------|
| Accuracy (랜덤 분할) | 58~65% (추정) | baseline 0.6290 / advanced 0.6958 |
| Accuracy (시간 분할) | 55~62% (추정) | advanced 시간순 0.6182 |
| ROC-AUC | 0.62~0.68 (추정) | baseline 0.6587 / advanced 0.7570 |

> 실측치가 초기 43피처 기반 추정치를 상회함. 위 초기 추정은 파이프라인 완성 전 낙관적 선행연구 외삽치.

---

## 2. 요인별 정확도 기여 추정

```
요인                    기여도 추정     누적 정확도
─────────────────────────────────────────────────
기준선 (무작위)          50%            50%
맵 피처                  +8~10%p       58~60%
역할군 카운트 피처        +7~10%p       65~70%
대규모 데이터 (50K+)     +5~8%p        70~78%
요원 원-핫 인코딩         +3~5%p        73~83%
피처 선택 최적화          +1~2%p        74~85%
앙상블 모델 (XGB+LGBM)   +1~2%p        75~85%
하이퍼파라미터 튜닝       +0.5~1%p      76~86%
─────────────────────────────────────────────────
최종 목표 (미달성)                      80~84% (미달성 — 2026-05 기준 최고 Acc 0.6958, AUC 0.7570)
```

---

## 3. 데이터 크기 vs 정확도 관계

Valorant 승률 예측 관련 선행 연구 및 유사 게임(CS:GO, LoL) 연구 기반 추정:

```python
import numpy as np
import matplotlib.pyplot as plt

DATA_ACCURACY_CURVE = {
    2_000:   0.65,
    5_000:   0.68,
    10_000:  0.71,
    20_000:  0.74,
    30_000:  0.76,
    50_000:  0.79,
    80_000:  0.81,
    100_000: 0.83,
    200_000: 0.84,  # 수확 체감 시작
}
# 아래 수치는 초기 낙관적 추정 — 실측: 53K행 125피처 기준 Acc 0.6958·AUC 0.7570
# 기준: 43개 피처(초기 설계), RF + XGBoost + LightGBM 앙상블

DATA_ACCURACY_CURVE_EXTENDED = {
    # 피처 확장(요원 원-핫 포함) 시
    50_000:  0.82,
    80_000:  0.84,
    100_000: 0.85,
}

def estimate_accuracy(n_matches: int, extended_features: bool = False) -> float:
    """데이터 크기 기반 정확도 추정"""
    curve = DATA_ACCURACY_CURVE_EXTENDED if extended_features else DATA_ACCURACY_CURVE
    
    # 가장 가까운 두 포인트 보간
    keys = sorted(curve.keys())
    for i, k in enumerate(keys):
        if k >= n_matches:
            if i == 0:
                return curve[k]
            prev_k = keys[i-1]
            ratio = (n_matches - prev_k) / (k - prev_k)
            return curve[prev_k] + ratio * (curve[k] - curve[prev_k])
    return curve[keys[-1]]

# 사용 예시
print(f"10,000 경기 예상 정확도: {estimate_accuracy(10000):.1%}")
print(f"50,000 경기 예상 정확도: {estimate_accuracy(50000):.1%}")
print(f"50,000 경기 + 피처 확장: {estimate_accuracy(50000, extended_features=True):.1%}")
```

---

## 4. 과적합 방지 요구사항

80%+ 정확도를 **과적합 없이** 달성하기 위한 조건:

```python
OVERFITTING_THRESHOLDS = {
    "train_val_acc_diff": 0.03,   # 훈련 vs 검증 정확도 차이 최대 3%p
    "cv_std": 0.02,               # 교차 검증 표준편차 최대 2%p
    "feature_count_max": 50,      # 최대 피처 수 (전체 115개 중 선택)
    "min_train_size": 20_000,     # 최소 훈련 데이터 크기
}

def check_overfitting(
    train_acc: float,
    val_acc: float,
    cv_scores: list[float],
) -> bool:
    """과적합 여부 판단"""
    diff = train_acc - val_acc
    cv_std = np.std(cv_scores)
    
    is_overfitting = (
        diff > OVERFITTING_THRESHOLDS["train_val_acc_diff"]
        or cv_std > OVERFITTING_THRESHOLDS["cv_std"]
    )
    
    print(f"[과적합 검사]")
    print(f"  Train: {train_acc:.3f}, Val: {val_acc:.3f}, 차이: {diff:.3f}")
    print(f"  CV 평균: {np.mean(cv_scores):.3f} ± {cv_std:.3f}")
    print(f"  결과: {'⚠️ 과적합 의심' if is_overfitting else '✅ 정상'}")
    
    return is_overfitting
```

---

## 5. 모델별 기대 성능

| 모델 | 50K 경기 (추정) | 100K 경기 (추정) | 과적합 위험 |
|------|---------|---------|---------|
| XGBoost | 79-81% | 81-83% | 보통 |
| LightGBM | 78-80% | 80-82% | 낮음 |
| **XGB+LGBM 앙상블** | **80-82%** | **82-84%** | **낮음** |
| RandomForest | 76-78% | 78-80% | 낮음 |
| 신경망(MLP) | 77-80% | 79-82% | 높음 |
| 로지스틱 회귀 | 72-75% | 74-77% | 매우 낮음 |

> **실측**: RF+XGB+LGBM 앙상블 53K행·125피처 기준 Acc 0.6958·AUC 0.7570 (80%+ 미달성)

---

## 6. 검증 프로토콜

```python
from sklearn.model_selection import StratifiedKFold, cross_validate
from xgboost import XGBClassifier
import lightgbm as lgb
from sklearn.ensemble import VotingClassifier

def validate_80_target(
    X: pd.DataFrame,
    y: pd.Series,
    n_splits: int = 5,
) -> dict:
    """80% 목표 달성 여부 검증 프로토콜"""
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    
    xgb = XGBClassifier(n_estimators=500, max_depth=6, learning_rate=0.05,
                         subsample=0.8, colsample_bytree=0.8, random_state=42)
    lgbm = lgb.LGBMClassifier(n_estimators=500, num_leaves=31, learning_rate=0.05,
                               random_state=42)
    
    ensemble = VotingClassifier(
        estimators=[("xgb", xgb), ("lgbm", lgbm)],
        voting="soft",
        weights=[1, 1],
    )
    
    results = cross_validate(
        ensemble, X, y,
        cv=cv,
        scoring=["accuracy", "roc_auc"],
        return_train_score=True,
    )
    
    summary = {
        "cv_accuracy_mean": results["test_accuracy"].mean(),
        "cv_accuracy_std": results["test_accuracy"].std(),
        "cv_roc_auc_mean": results["test_roc_auc"].mean(),
        "train_accuracy_mean": results["train_accuracy"].mean(),
        "target_met": results["test_accuracy"].mean() >= 0.80,
    }
    
    print("=== 80% 목표 달성 검증 ===")
    print(f"CV 정확도: {summary['cv_accuracy_mean']:.3f} ± {summary['cv_accuracy_std']:.3f}")
    print(f"ROC AUC:  {summary['cv_roc_auc_mean']:.3f}")
    print(f"목표 달성: {'✅ YES' if summary['target_met'] else '❌ NO (미달)'}")
    
    return summary
```

---

## 7. 단계별 달성 체크리스트

```
[x] 53,427행 + baseline 178피처 + LR+DT → Acc 0.6290·AUC 0.6587 달성
[x] 53,427행 + advanced 125피처 + RF/XGB/LGBM → Acc 0.6958·AUC 0.7570 달성
[ ] 50,000 경기 + 요원 원-핫 → 80-82%  ← 목표 (미달성)
[ ] 100,000 경기 + 전체 피처 선택 → 82-84%  ← 이상적 (미달성)
```

## 향후 목표(미달성)

아래 수치는 현재 미달성 상태의 장기 목표이며, 추가 데이터·피처 확장 시 재평가 필요.

- 목표 Accuracy: 80~84% (현재 최고: 0.6958)
- 목표 ROC-AUC: 0.82+ (현재 최고: 0.7570)
- 달성 조건: 요원 원-핫 피처 + 대용량 데이터(50K+ 경기) 필요 추정
