# 03. Soft Voting 앙상블 설계

## 개요

XGBoost와 LightGBM의 예측 확률을 가중 평균하는 Soft Voting 앙상블의 수식, 가중치 결정 방법, 완전한 구현 코드를 설명한다.

---

## 1. 앙상블 이론적 배경

### 1.1 편향-분산 트레이드오프

단일 모델의 예측 오차:
```
E[(y - ŷ)^2] = Bias^2 + Variance + Irreducible Noise
```

앙상블의 효과:
```
Variance(ensemble) = (1/M^2) * Σ Variance(m) + (M-1)/M * Covariance(m, m')

- M: 모델 수 (여기서 M=2)
- 모델들의 예측이 상관관계가 낮을수록 (Covariance 작을수록)
- 앙상블 분산이 개별 모델 분산보다 작아짐
```

### 1.2 Hard Voting vs Soft Voting

**Hard Voting:**
```
ŷ = argmax Σ I(ŷ_m = c)    (다수결)

예시: XGB → 1 (승), LGBM → 0 (패)
결과: 동점 → 불확실한 처리
```

**Soft Voting (선택):**
```
P(y=1|x) = Σ w_m * P_m(y=1|x)    (확률 가중 평균)

예시: XGB → 0.65, LGBM → 0.58
가중치: w_XGB=0.6, w_LGBM=0.4
결과: 0.6*0.65 + 0.4*0.58 = 0.622 → 1 (승)
```

Soft Voting이 우수한 이유:
- 확률 정보를 완전히 활용 (Hard Voting은 이진 정보만 사용)
- 더 세밀한 불확실성 표현
- 일반적으로 더 나은 ROC-AUC

---

## 2. 수식 정의

### 2.1 기본 Soft Voting 수식

```
P_ensemble(y=1|x) = w₁ * P_XGB(y=1|x) + w₂ * P_LGBM(y=1|x)

제약 조건:
- w₁ + w₂ = 1
- w₁, w₂ ∈ [0, 1]

최종 예측:
ŷ = I(P_ensemble(y=1|x) ≥ θ)    (θ: 결정 임계값, 기본값 0.5)
```

### 2.2 일반화 수식 (M개 모델)

```
P_ensemble = Σ_{m=1}^{M} w_m * P_m(y=1|x)
           = w_XGB * P_XGB + w_LGBM * P_LGBM    (M=2)
```

### 2.3 확률 캘리브레이션 고려

각 모델의 확률 출력이 잘 보정(calibrated)되어 있는지 확인:

```python
from sklearn.calibration import calibration_curve
import matplotlib.pyplot as plt

fig, ax = plt.subplots(1, 2, figsize=(12, 5))

for model, name, axis in [(xgb_model, "XGBoost", ax[0]),
                           (lgbm_model, "LightGBM", ax[1])]:
    prob_true, prob_pred = calibration_curve(
        y_test,
        model.predict_proba(X_test)[:, 1],
        n_bins=10
    )
    axis.plot(prob_pred, prob_true, 's-', label=name)
    axis.plot([0, 1], [0, 1], 'k--', label='Perfect calibration')
    axis.set_xlabel("Mean predicted probability")
    axis.set_ylabel("Fraction of positives")
    axis.legend()

# 대각선에 가까울수록 잘 보정된 확률
```

---

## 3. 가중치 결정 방법

### 3.1 방법 1: Optuna 기반 가중치 최적화 (권장)

```python
import optuna
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score
import numpy as np

def objective_weights(trial, X, y, xgb_model, lgbm_model):
    """앙상블 가중치를 최적화하는 Optuna objective."""

    w_xgb = trial.suggest_float("w_xgb", 0.3, 0.8)
    w_lgbm = 1.0 - w_xgb

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    auc_scores = []

    for fold_idx, (train_idx, val_idx) in enumerate(skf.split(X, y)):
        X_val_fold = X.iloc[val_idx]
        y_val_fold = y.iloc[val_idx]

        xgb_probs = xgb_model.predict_proba(X_val_fold)[:, 1]
        lgbm_probs = lgbm_model.predict_proba(X_val_fold)[:, 1]

        ensemble_probs = w_xgb * xgb_probs + w_lgbm * lgbm_probs
        auc = roc_auc_score(y_val_fold, ensemble_probs)
        auc_scores.append(auc)

    return np.mean(auc_scores)

# 최적화 실행
study = optuna.create_study(direction="maximize")
study.optimize(
    lambda trial: objective_weights(trial, X_val, y_val, xgb_model, lgbm_model),
    n_trials=100
)

best_w_xgb = study.best_params["w_xgb"]
best_w_lgbm = 1.0 - best_w_xgb
print(f"최적 가중치: XGBoost={best_w_xgb:.3f}, LightGBM={best_w_lgbm:.3f}")
```

### 3.2 방법 2: 검증 성능 기반 비례 가중치

```python
from sklearn.metrics import roc_auc_score

# 각 모델의 검증 AUC
xgb_auc = roc_auc_score(y_val, xgb_model.predict_proba(X_val)[:, 1])
lgbm_auc = roc_auc_score(y_val, lgbm_model.predict_proba(X_val)[:, 1])

# AUC에 비례한 가중치
total_auc = xgb_auc + lgbm_auc
w_xgb = xgb_auc / total_auc
w_lgbm = lgbm_auc / total_auc

print(f"AUC 기반 가중치: XGBoost={w_xgb:.3f}, LightGBM={w_lgbm:.3f}")
```

### 3.3 방법 3: sklearn VotingClassifier (기본값 동일 가중치)

```python
from sklearn.ensemble import VotingClassifier

# 동일 가중치 (w=0.5, 0.5)
ensemble_equal = VotingClassifier(
    estimators=[("xgb", xgb_model), ("lgbm", lgbm_model)],
    voting="soft",
    weights=[1, 1]
)

# 사전 정의 가중치
ensemble_weighted = VotingClassifier(
    estimators=[("xgb", xgb_model), ("lgbm", lgbm_model)],
    voting="soft",
    weights=[6, 4]  # XGB 60%, LGBM 40%
)
```

### 3.4 가중치 결정 가이드라인

| 상황 | 권장 가중치 (XGB:LGBM) |
|------|----------------------|
| 두 모델 성능 비슷 | 50:50 |
| XGB AUC > LGBM AUC by 0.01+ | 60:40 |
| XGB AUC > LGBM AUC by 0.02+ | 70:30 |
| 데이터 매우 소규모 (<2000) | 50:50 (LGBM 과적합 위험) |
| Optuna 최적화 후 | 최적값 사용 |

---

## 4. 완전한 구현 코드

### 4.1 EnsemblePredictor 클래스

```python
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, roc_auc_score, f1_score
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class SoftVotingEnsemble:
    """
    XGBoost + LightGBM Soft Voting 앙상블 예측기.

    Attributes:
        xgb_model: 학습된 XGBoost 모델
        lgbm_model: 학습된 LightGBM 모델
        w_xgb: XGBoost 가중치
        w_lgbm: LightGBM 가중치
        threshold: 이진 분류 임계값
    """

    def __init__(
        self,
        xgb_model,
        lgbm_model,
        w_xgb: float = 0.6,
        w_lgbm: float = 0.4,
        threshold: float = 0.5
    ):
        assert abs(w_xgb + w_lgbm - 1.0) < 1e-6, "가중치 합이 1이어야 합니다"
        assert 0 < threshold < 1, "임계값은 (0, 1) 범위여야 합니다"

        self.xgb_model = xgb_model
        self.lgbm_model = lgbm_model
        self.w_xgb = w_xgb
        self.w_lgbm = w_lgbm
        self.threshold = threshold

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        앙상블 예측 확률 반환.

        Returns:
            shape (N, 2) 배열 [[P(패), P(승)], ...]
        """
        xgb_probs = self.xgb_model.predict_proba(X)[:, 1]
        lgbm_probs = self.lgbm_model.predict_proba(X)[:, 1]

        ensemble_probs = self.w_xgb * xgb_probs + self.w_lgbm * lgbm_probs

        # (N, 2) 형태로 반환
        return np.column_stack([1 - ensemble_probs, ensemble_probs])

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        이진 예측 반환 (0: 패, 1: 승).
        """
        probs = self.predict_proba(X)[:, 1]
        return (probs >= self.threshold).astype(int)

    def evaluate(self, X: pd.DataFrame, y: np.ndarray) -> dict:
        """
        전체 평가 지표 계산.
        """
        probs = self.predict_proba(X)[:, 1]
        preds = self.predict(X)

        metrics = {
            "accuracy": accuracy_score(y, preds),
            "f1_score": f1_score(y, preds, average="binary"),
            "roc_auc": roc_auc_score(y, probs),
            "xgb_weight": self.w_xgb,
            "lgbm_weight": self.w_lgbm,
            "threshold": self.threshold
        }

        logger.info(f"Ensemble 평가: {metrics}")
        return metrics

    def predict_single(self, features: dict) -> dict:
        """
        단일 경기 예측 (FastAPI 연동용).

        Args:
            features: {"duelist_team1": 2, "controller_team1": 1, ...}

        Returns:
            {"win_probability": 0.65, "prediction": 1, "confidence": "high"}
        """
        X = pd.DataFrame([features])
        prob = self.predict_proba(X)[0, 1]
        pred = int(prob >= self.threshold)

        confidence = "high" if abs(prob - 0.5) > 0.2 else "medium" if abs(prob - 0.5) > 0.1 else "low"

        return {
            "win_probability": round(float(prob), 4),
            "prediction": pred,
            "confidence": confidence,
            "xgb_contribution": round(float(self.w_xgb * self.xgb_model.predict_proba(X)[0, 1]), 4),
            "lgbm_contribution": round(float(self.w_lgbm * self.lgbm_model.predict_proba(X)[0, 1]), 4)
        }
```

### 4.2 앙상블 학습 및 평가 파이프라인

```python
def build_ensemble(X_train, y_train, X_val, y_val, X_test, y_test):
    """
    전체 앙상블 구축 파이프라인.
    """
    import xgboost as xgb
    import lightgbm as lgb

    # 1. 개별 모델 학습
    xgb_model = xgb.XGBClassifier(
        n_estimators=500,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        use_label_encoder=False,
        eval_metric="logloss",
        early_stopping_rounds=50,
        random_state=42
    )
    xgb_model.fit(X_train, y_train,
                  eval_set=[(X_val, y_val)],
                  verbose=False)

    lgbm_model = lgb.LGBMClassifier(
        n_estimators=500,
        num_leaves=31,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42
    )
    lgbm_model.fit(X_train, y_train,
                   eval_set=[(X_val, y_val)],
                   callbacks=[lgb.early_stopping(50), lgb.log_evaluation(0)])

    # 2. 가중치 최적화 (검증 세트 기준)
    xgb_auc = roc_auc_score(y_val, xgb_model.predict_proba(X_val)[:, 1])
    lgbm_auc = roc_auc_score(y_val, lgbm_model.predict_proba(X_val)[:, 1])
    total = xgb_auc + lgbm_auc
    w_xgb, w_lgbm = xgb_auc / total, lgbm_auc / total

    print(f"개별 모델 AUC: XGB={xgb_auc:.4f}, LGBM={lgbm_auc:.4f}")
    print(f"자동 가중치: XGB={w_xgb:.3f}, LGBM={w_lgbm:.3f}")

    # 3. 앙상블 생성
    ensemble = SoftVotingEnsemble(xgb_model, lgbm_model, w_xgb, w_lgbm)

    # 4. 테스트 평가
    test_metrics = ensemble.evaluate(X_test, y_test)
    print(f"\n최종 앙상블 성능:")
    print(f"  Accuracy:  {test_metrics['accuracy']:.4f} (목표: ≥ 0.80)")
    print(f"  ROC-AUC:   {test_metrics['roc_auc']:.4f} (목표: ≥ 0.82)")
    print(f"  F1-Score:  {test_metrics['f1_score']:.4f}")

    return ensemble, test_metrics
```

---

## 5. 결정 임계값 최적화

기본 임계값 0.5가 최적이 아닐 수 있음:

```python
import numpy as np
from sklearn.metrics import f1_score

def find_optimal_threshold(y_true, y_probs, metric="f1"):
    """
    F1 또는 정확도를 최대화하는 최적 임계값 탐색.
    """
    thresholds = np.arange(0.3, 0.7, 0.01)
    best_threshold = 0.5
    best_score = 0.0

    for thresh in thresholds:
        preds = (y_probs >= thresh).astype(int)
        if metric == "f1":
            score = f1_score(y_true, preds)
        else:
            score = accuracy_score(y_true, preds)

        if score > best_score:
            best_score = score
            best_threshold = thresh

    print(f"최적 임계값: {best_threshold:.2f} ({metric}={best_score:.4f})")
    return best_threshold

# 사용
ensemble_probs = ensemble.predict_proba(X_val)[:, 1]
optimal_threshold = find_optimal_threshold(y_val, ensemble_probs)
ensemble.threshold = optimal_threshold
```

---

## 6. 앙상블 성능 기대값

Optuna 최적화 및 10-Fold CV 기준 예상 성능:

| 지표 | XGBoost 단독 | LightGBM 단독 | **앙상블** | 목표 |
|------|-------------|--------------|-----------|------|
| Accuracy | 0.79 | 0.78 | **0.81** | ≥ 0.80 |
| ROC-AUC | 0.82 | 0.81 | **0.84** | ≥ 0.82 |
| F1-Score | 0.78 | 0.77 | **0.80** | - |
| 표준편차 | ±0.03 | ±0.04 | **±0.02** | 낮을수록 좋음 |

앙상블이 단일 모델보다 분산이 낮고(±0.02) 안정적인 성능을 보임.
