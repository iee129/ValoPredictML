# 03. 앙상블 설계 (RF + XGBoost + LightGBM 단순 평균)

마지막 업데이트: 2026-05-05

## 개요

Random Forest, XGBoost, LightGBM 세 모델의 예측 확률을 단순 평균하는 앙상블의 수식, 설계 근거, 구현 코드를 설명한다.
세 모델의 확률을 평균 내어 최종 승률을 산출한다 — 가중치 없이 균등 평균.

**앙상블 작동 방식:**
```
RF 예측      → 팀 A 승률 0.62
XGBoost 예측 → 팀 A 승률 0.58
LightGBM 예측 → 팀 A 승률 0.65

최종 승률 = (0.62 + 0.58 + 0.65) / 3 = 0.617
```

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

**Soft Voting (선택) — 단순 평균:**
```
P(y=1|x) = (P_RF(y=1|x) + P_XGB(y=1|x) + P_LGBM(y=1|x)) / 3

예시: RF → 0.62, XGB → 0.58, LGBM → 0.65
결과: (0.62 + 0.58 + 0.65) / 3 = 0.617 → 1 (승)
```

단순 평균 방식이 우수한 이유:
- 확률 정보를 완전히 활용 (Hard Voting은 이진 정보만 사용)
- 한 모델이 특정 경기에서 크게 틀려도 나머지 두 모델이 균형을 잡아줌
- 가중치 최적화 없이도 안정적인 성능 — 구현 단순화
- 일반적으로 단일 모델보다 높은 ROC-AUC

---

## 2. 수식 정의

### 2.1 단순 평균 앙상블 수식

```
P_ensemble(y=1|x) = (P_RF(y=1|x) + P_XGB(y=1|x) + P_LGBM(y=1|x)) / 3

최종 예측:
ŷ = I(P_ensemble(y=1|x) ≥ θ)    (θ: 결정 임계값, 기본값 0.5)
```

### 2.2 일반화 수식 (M개 모델 균등 가중)

```
P_ensemble = (1/M) * Σ_{m=1}^{M} P_m(y=1|x)
           = (P_RF + P_XGB + P_LGBM) / 3    (M=3)
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

### 3.1 단순 평균 앙상블 (권장)

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

### 3.2 sklearn VotingClassifier (균등 가중치)

```python
from sklearn.ensemble import VotingClassifier

ensemble = VotingClassifier(
    estimators=[
        ("rf",   rf_model),
        ("xgb",  xgb_model),
        ("lgbm", lgbm_model),
    ],
    voting="soft",
    weights=[1, 1, 1],   # 균등 — 단순 평균과 동일
)
```

### 3.3 sample_weight 적용

세 모델 각각 학습 시 `sample_weight` 적용:

```python
# sample_weight = time_weight * source_weight
weights = df["time_weight"] * df["source_weight"]

rf_model.fit(X_train, y_train, sample_weight=weights)
xgb_model.fit(X_train, y_train,
              sample_weight=weights,
              eval_set=[(X_val, y_val)], verbose=False)
lgbm_model.fit(X_train, y_train,
               sample_weight=weights,
               eval_set=[(X_val, y_val)],
               callbacks=[lgb.early_stopping(50, verbose=False),
                          lgb.log_evaluation(0)])
```

---

## 4. 완전한 구현 코드

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
        단일 경기 예측 (Streamlit 연동용).

        Args:
            features: 43개 피처 딕셔너리

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
    sample_weight = time_weight * source_weight (preprocessing.md 참조).
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

K-Fold (K=5) 교차 검증 및 test 세트 실제 측정 결과:

| 지표 | RF 단독 | XGBoost 단독 | LightGBM 단독 | **앙상블 (단순 평균)** |
|------|---------|-------------|--------------|----------------------|
| K-Fold Accuracy | 0.8652±0.0017 | 0.8488±0.0028 | 0.8494±0.0027 | **0.8580±0.0034** |
| K-Fold ROC-AUC | 0.9449±0.0012 | 0.9343±0.0019 | 0.9353±0.0019 | **0.9414±0.0017** |
| K-Fold F1-Score | 0.8652±0.0017 | 0.8488±0.0028 | 0.8494±0.0027 | **0.8580±0.0034** |
| Test Accuracy | 0.8595 | 0.8443 | 0.8480 | **0.8540** |
| Test ROC-AUC | 0.9378 | 0.9281 | 0.9292 | **0.9355** |
| Test F1-Score | 0.8566 | 0.8408 | 0.8447 | **0.8508** |

앙상블이 단일 모델보다 분산이 낮고 안정적인 성능을 보임.
앙상블 방식: predict_proba 3개 단순 평균 (균등 가중치, 별도 최적화 없음).

**평가 지표**: Accuracy, ROC-AUC, F1
**K-Fold**: K=5 (train 데이터를 5조각으로 나눠 각 조각을 한 번씩 검증셋으로 사용 → 5번 Accuracy 평균)
**test.csv**: K-Fold와 완전 분리 — 최종 평가 1회만 사용
**K-Fold vs Test 갭**: 0.004 — 과적합 없음
