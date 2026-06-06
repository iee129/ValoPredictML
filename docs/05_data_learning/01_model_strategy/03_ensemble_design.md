# 03. 앙상블 설계 (RF + XGBoost + LightGBM 가중 soft voting)

마지막 업데이트: 2026-06-04

## 개요

Random Forest, XGBoost, LightGBM 세 모델의 예측 확률을 **가중 평균**하는 soft voting 앙상블의 수식, 설계 근거, 구현 코드를 설명한다.
현행 코드는 가중치 **RF 2.0 : XGB 3.0 : LGBM 0.1**을 사용하며, 이 가중치는 2025 검증 split 기준 grid search로 선택됐다(val AUC 0.6682).

**앙상블 작동 방식 (가중 평균):**
```
RF 예측      → 팀 A 승률 0.62  (가중치 2.0)
XGBoost 예측 → 팀 A 승률 0.58  (가중치 3.0)
LightGBM 예측 → 팀 A 승률 0.65 (가중치 0.1)

최종 승률 = (2.0*0.62 + 3.0*0.58 + 0.1*0.65) / (2.0 + 3.0 + 0.1) ≈ 0.599
```

> 참고: 균등 가중(1:1:1) 단순 평균은 설계 기준선이며, 현행 활성 앙상블은 위 가중치를 사용한다.

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

- M: 모델 수 (여기서 M=3 — RF, XGBoost, LightGBM)
- 모델들의 예측이 상관관계가 낮을수록 (Covariance 작을수록)
- 앙상블 분산이 개별 모델 분산보다 작아짐
```

### 1.2 Hard Voting vs Soft Voting

**Hard Voting:**
```
ŷ = argmax Σ I(ŷ_m = c)    (다수결)

예시: RF → 1, XGB → 0, LGBM → 1
결과: 2:1 → 1 (승) — 확률 정보 손실
```

**Soft Voting (선택) — 가중 평균:**
```
P(y=1|x) = (w_RF*P_RF + w_XGB*P_XGB + w_LGBM*P_LGBM) / (w_RF + w_XGB + w_LGBM)
         (w_RF=2.0, w_XGB=3.0, w_LGBM=0.1)

예시: RF → 0.62, XGB → 0.58, LGBM → 0.65
결과: (2.0*0.62 + 3.0*0.58 + 0.1*0.65) / 5.1 ≈ 0.599 → 1 (승)
```

Soft Voting 방식이 우수한 이유:
- 확률 정보를 완전히 활용 (Hard Voting은 이진 정보만 사용)
- 한 모델이 특정 경기에서 크게 틀려도 나머지 모델이 균형을 잡아줌
- 가중치는 검증 split 기준 grid search로 고정 — 구현은 단순하게 유지
- 일반적으로 단일 모델보다 높은 ROC-AUC

---

## 2. 수식 정의

### 2.1 가중 평균 앙상블 수식 (현행)

```
P_ensemble(y=1|x) = Σ_m w_m * P_m(y=1|x) / Σ_m w_m
                  = (2.0*P_RF + 3.0*P_XGB + 0.1*P_LGBM) / 5.1

최종 예측:
ŷ = I(P_ensemble(y=1|x) ≥ θ)    (θ: 결정 임계값, 기본값 0.5)
```

### 2.2 일반화 수식 (M개 모델 가중)

```
P_ensemble = Σ_{m=1}^{M} w_m * P_m(y=1|x) / Σ_{m=1}^{M} w_m
           = (w_RF*P_RF + w_XGB*P_XGB + w_LGBM*P_LGBM) / (w_RF+w_XGB+w_LGBM)    (M=3)

균등 가중(w=1,1,1)이면 단순 평균과 같다. 현행은 w=(2.0, 3.0, 0.1).
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

## 3. 앙상블 구현

### 3.1 단순 평균 앙상블 (설계 기준선 예시)

> 아래는 균등 가중(1:1:1) 단순 평균 예시다. 현행 활성 구현은 §3.2의 가중 soft voting(`weights=[2.0, 3.0, 0.1]`)을 사용한다.

```python
import numpy as np
from sklearn.metrics import accuracy_score, roc_auc_score, f1_score

def ensemble_predict_proba(rf_model, xgb_model, lgbm_model, X):
    """RF + XGBoost + LightGBM 단순 평균 앙상블 예측 확률."""
    rf_prob   = rf_model.predict_proba(X)[:, 1]
    xgb_prob  = xgb_model.predict_proba(X)[:, 1]
    lgbm_prob = lgbm_model.predict_proba(X)[:, 1]
    return (rf_prob + xgb_prob + lgbm_prob) / 3

def ensemble_evaluate(rf_model, xgb_model, lgbm_model, X, y):
    """앙상블 평가 지표 계산."""
    probs = ensemble_predict_proba(rf_model, xgb_model, lgbm_model, X)
    preds = (probs >= 0.5).astype(int)
    return {
        "accuracy": accuracy_score(y, preds),
        "roc_auc":  roc_auc_score(y, probs),
        "f1":       f1_score(y, preds, average="binary"),
    }
```

### 3.2 sklearn VotingClassifier (현행 가중치)

```python
from sklearn.ensemble import VotingClassifier

ensemble = VotingClassifier(
    estimators=[
        ("rf",   rf_model),
        ("xgb",  xgb_model),
        ("lgbm", lgbm_model),
    ],
    voting="soft",
    weights=[2.0, 3.0, 0.1],   # 현행 가중치 (RF:XGB:LGBM), 2025 val grid search 선택
)
```

### 3.3 가중치 선택 방식

현재 활성 앙상블(`src/ml/advanced/ensemble.py`)은 RF/XGB/LGBM을 코드 고정 하이퍼파라미터로 학습한 뒤, soft voting 가중치를 **2025 검증 split 기준 grid search**로 선택한다(선택된 가중치 RF 2.0 : XGB 3.0 : LGBM 0.1, val AUC 0.6682). 개별 모델 학습은 `sample_weight` 없이 균등하다.

```python
# src/ml/advanced/ensemble.py — 가중 soft voting (grid search로 선택된 weights)
ensemble = VotingClassifier(
    estimators=[("rf", make_rf(...)), ("xgb", make_xgb(...)), ("lgbm", make_lgbm(...))],
    voting="soft", weights=[2.0, 3.0, 0.1],
)
ensemble.fit(X, y)
```

---

## 4. 구현 (설계 예시)

> 아래는 앙상블의 설계 예시다(SimpleAverageEnsemble는 균등 평균 예시 클래스). **실제 활성 구현은 `src/ml/advanced/ensemble.py`의 `VotingClassifier(voting="soft", weights=[2.0, 3.0, 0.1])`** 이며, RF/XGB/LightGBM 하이퍼파라미터는 코드 고정값을 따른다(Optuna 미사용). 아래 하드코딩 값은 예시일 뿐 현행 고정값과 다를 수 있다.

### 4.1 EnsemblePredictor 클래스

```python
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, roc_auc_score, f1_score
import logging

logger = logging.getLogger(__name__)


class SimpleAverageEnsemble:
    """
    RF + XGBoost + LightGBM 단순 확률 평균 앙상블 예측기.

    Attributes:
        rf_model:   학습된 Random Forest 모델
        xgb_model:  학습된 XGBoost 모델
        lgbm_model: 학습된 LightGBM 모델
        threshold:  이진 분류 임계값 (기본 0.5)
    """

    def __init__(self, rf_model, xgb_model, lgbm_model, threshold: float = 0.5):
        assert 0 < threshold < 1, "임계값은 (0, 1) 범위여야 합니다"
        self.rf_model   = rf_model
        self.xgb_model  = xgb_model
        self.lgbm_model = lgbm_model
        self.threshold  = threshold

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        앙상블 예측 확률 반환 (단순 평균).

        Returns:
            shape (N, 2) 배열 [[P(패), P(승)], ...]
        """
        rf_prob   = self.rf_model.predict_proba(X)[:, 1]
        xgb_prob  = self.xgb_model.predict_proba(X)[:, 1]
        lgbm_prob = self.lgbm_model.predict_proba(X)[:, 1]
        ensemble_prob = (rf_prob + xgb_prob + lgbm_prob) / 3
        return np.column_stack([1 - ensemble_prob, ensemble_prob])

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """이진 예측 반환 (0: 패, 1: 승)."""
        probs = self.predict_proba(X)[:, 1]
        return (probs >= self.threshold).astype(int)

    def evaluate(self, X: pd.DataFrame, y: np.ndarray) -> dict:
        """Accuracy, ROC-AUC, F1 계산."""
        probs = self.predict_proba(X)[:, 1]
        preds = self.predict(X)
        metrics = {
            "accuracy": accuracy_score(y, preds),
            "roc_auc":  roc_auc_score(y, probs),
            "f1":       f1_score(y, preds, average="binary"),
        }
        logger.info(f"Ensemble 평가: {metrics}")
        return metrics

    def predict_single(self, features: dict) -> dict:
        """
        단일 경기 예측 (웹 스택 연동용).

        Args:
            features: 179개 피처 딕셔너리 (advanced 계약)

        Returns:
            {"win_probability": 0.617, "prediction": 1, "confidence": "high"}
        """
        X = pd.DataFrame([features])
        prob = self.predict_proba(X)[0, 1]
        pred = int(prob >= self.threshold)
        confidence = (
            "high"   if abs(prob - 0.5) > 0.2 else
            "medium" if abs(prob - 0.5) > 0.1 else
            "low"
        )
        return {
            "win_probability": round(float(prob), 4),
            "prediction":      pred,
            "confidence":      confidence,
        }
```

### 4.2 앙상블 학습 및 평가 파이프라인

```python
def build_ensemble(X_train, y_train, X_val, y_val, X_test, y_test,
                   sample_weight=None):
    """
    RF + XGBoost + LightGBM 앙상블 구축 파이프라인.
    sample_weight 인자는 옵션이며 현재 활성 파이프라인(src/ml/advanced/ensemble.py)은 미사용(균등 학습).
    """
    import xgboost as xgb
    import lightgbm as lgb
    from sklearn.ensemble import RandomForestClassifier

    # 1. 개별 모델 학습
    rf_model = RandomForestClassifier(
        n_estimators=200,
        max_features="sqrt",
        class_weight="balanced",
        n_jobs=-1,
        random_state=42,
    )
    rf_model.fit(X_train, y_train, sample_weight=sample_weight)

    xgb_model = xgb.XGBClassifier(
        n_estimators=1000,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        eval_metric="logloss",
        early_stopping_rounds=50,
        random_state=42,
        n_jobs=-1,
    )
    xgb_model.fit(X_train, y_train,
                  sample_weight=sample_weight,
                  eval_set=[(X_val, y_val)],
                  verbose=False)

    lgbm_model = lgb.LGBMClassifier(
        n_estimators=2000,
        num_leaves=31,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )
    lgbm_model.fit(X_train, y_train,
                   sample_weight=sample_weight,
                   eval_set=[(X_val, y_val)],
                   callbacks=[lgb.early_stopping(50, verbose=False),
                               lgb.log_evaluation(0)])

    # 2. 앙상블 생성 (단순 평균)
    ensemble = SimpleAverageEnsemble(rf_model, xgb_model, lgbm_model)

    # 3. test.csv 최종 평가 (1회만)
    test_metrics = ensemble.evaluate(X_test, y_test)
    print(f"\n최종 앙상블 성능 (test.csv):")
    print(f"  Accuracy: {test_metrics['accuracy']:.4f}")
    print(f"  ROC-AUC:  {test_metrics['roc_auc']:.4f}")
    print(f"  F1:       {test_metrics['f1']:.4f}")

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

## 6. 앙상블 성능 (구현 완료)

현행 코드 고정 하이퍼파라미터 + 가중치 grid search, 시간순 split test(2026) 실제 측정 (179피처, 맵 단위 승패 샘플):

| 지표 | RF 단독 | XGBoost 단독 | LightGBM 단독 | **앙상블 (가중 Soft Voting)** |
|------|--------:|------------:|-------------:|----------------------------:|
| Test ROC-AUC | 0.6965 | 0.7007 | 0.7015 | **0.7010** |
| Test Accuracy | — | — | — | **0.6454** |
| Test F1-Score | — | — | — | **0.6478** |

앙상블이 단일 모델 대비 안정적인 성능을 보임(개별 최고 LGBM 0.7015와 근접하되 분산을 줄임).
앙상블 방식: `src/ml/advanced/ensemble.py` 가중 Soft Voting (RF 2.0 : XGB 3.0 : LGBM 0.1, 2025 val grid search 선택, val AUC 0.6682).
HPO: 자동 HPO(Optuna) 미사용 — 코드 고정 하이퍼파라미터 사용(향후 계획).

**데이터**: 시간순 split (train 2020–2025 = 75,405 / test 2026 = 16,053, 맵 단위 승패 샘플)
**피처**: 179개 (`data/processed/advanced/`)
**`final_verdict`**: `신뢰 가능`
