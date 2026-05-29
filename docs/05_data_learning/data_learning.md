# 05. 데이터 학습 전략

마지막 업데이트: 2026-05-05

## 1. 모델 선택 전략

### 1.1 모델 비교표

| 모델 | 장점 | 단점 | 역할 |
|---|---|---|---|
| **Logistic Regression** | 빠름, 해석 쉬움 | 복잡한 패턴 학습 불가 | Baseline 비교용 |
| **Random Forest** | 과적합 강함, 안정적 | 메모리 사용 많음 | 앙상블 메인 |
| **XGBoost** | 높은 정확도, 빠름 | 하이퍼파라미터 많음 | 앙상블 메인 |
| **LightGBM** | 매우 빠름, 메모리 효율 | 소규모 데이터에서 불안정 | 앙상블 메인 |
| **CatBoost** | 범주형 처리 내장 | 느린 학습 | 미사용 |
| **MLP (Neural Net)** | 복잡한 패턴 학습 | 딥러닝 금지 (트리 모델 전용) | 미사용 |

### 1.2 채택 모델

**RF + XGBoost + LightGBM 단순 평균 앙상블**

- 이유: 세 모델의 다양성을 합쳐 개별 모델보다 안정적인 성능
- 단순 평균: 각 모델의 확률값을 동일 가중치로 평균 → 최종 예측
- 딥러닝(PyTorch/TensorFlow) 금지 — 트리 기반 모델 전용

```python
# 앙상블 예측 예시
rf_prob = rf_model.predict_proba(X)[:, 1]
xgb_prob = xgb_model.predict_proba(X)[:, 1]
lgbm_prob = lgbm_model.predict_proba(X)[:, 1]
ensemble_prob = (rf_prob + xgb_prob + lgbm_prob) / 3
predictions = (ensemble_prob >= 0.5).astype(int)
```

---

## 2. Baseline 모델

학습 시작 전 Baseline을 먼저 구축하여 개선의 기준을 세웁니다.

```python
# ml/train.py - Baseline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

def train_baseline(X_train, y_train, X_val, y_val):
    results = {}
    
    # Dummy (랜덤 추측 수준)
    dummy_acc = max(y_train.mean(), 1 - y_train.mean())
    results["Dummy"] = {"val_accuracy": dummy_acc}
    
    # Logistic Regression
    lr = LogisticRegression(max_iter=1000, random_state=42)
    lr.fit(X_train, y_train)
    results["LogReg"] = evaluate_model(lr, X_val, y_val)
    
    # Random Forest
    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    rf.fit(X_train, y_train)
    results["RandomForest"] = evaluate_model(rf, X_val, y_val)
    
    for name, metrics in results.items():
        print(f"{name:20s} | Acc: {metrics['val_accuracy']:.4f}")
    
    return results

def evaluate_model(model, X, y):
    y_pred = model.predict(X)
    y_prob = model.predict_proba(X)[:, 1]
    return {
        "val_accuracy": accuracy_score(y, y_pred),
        "val_f1": f1_score(y, y_pred, average="macro"),
        "val_roc_auc": roc_auc_score(y, y_prob),
    }
```

**Baseline 역할:** Logistic Regression — 하한선 확인용 (메인 모델 후보 아님). StandardScaler 필요. Random Forest — 앙상블 메인 모델 중 하나.

---

## 3. XGBoost 학습

### 3.1 기본 설정

```python
import xgboost as xgb
from sklearn.metrics import accuracy_score

def train_xgboost(X_train, y_train, X_val, y_val, params: dict = None) -> xgb.XGBClassifier:
    default_params = {
        "n_estimators": 500,
        "max_depth": 5,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
        "min_child_weight": 5,
        "gamma": 0.1,
        "objective": "binary:logistic",
        "eval_metric": "logloss",
        "random_state": 42,
        "tree_method": "hist",  # 빠른 학습
    }
    
    if params:
        default_params.update(params)
    
    model = xgb.XGBClassifier(**default_params)
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        early_stopping_rounds=50,  # 50 라운드 개선 없으면 조기 종료
        verbose=100,
    )
    
    val_acc = accuracy_score(y_val, model.predict(X_val))
    print(f"[XGBoost] Val Accuracy: {val_acc:.4f}, Best iteration: {model.best_iteration}")
    return model
```

### 3.2 주요 하이퍼파라미터 설명

| 파라미터 | 역할 | 과적합 방지 |
|---|---|---|
| `max_depth` | 트리 최대 깊이 | 낮을수록 단순 모델 (3~6 권장) |
| `subsample` | 각 트리에 사용할 샘플 비율 | 0.7~0.9 (1.0이면 과적합 위험) |
| `colsample_bytree` | 각 트리에 사용할 피처 비율 | 0.7~0.9 |
| `learning_rate` | 학습률 | 낮을수록 안정적 (0.01~0.1) |
| `reg_alpha` | L1 정규화 | 피처 희소화 |
| `reg_lambda` | L2 정규화 | 가중치 크기 제한 |
| `min_child_weight` | 리프 노드 최소 가중치 합 | 높을수록 일반화 |
| `early_stopping_rounds` | 조기 종료 기준 라운드 | 과적합 자동 방지 |

---

## 4. LightGBM 학습

```python
import lightgbm as lgb

def train_lightgbm(X_train, y_train, X_val, y_val, params: dict = None) -> lgb.LGBMClassifier:
    default_params = {
        "n_estimators": 500,
        "num_leaves": 31,
        "max_depth": -1,  # -1 = 무제한 (num_leaves로 제어)
        "learning_rate": 0.05,
        "subsample": 0.8,
        "subsample_freq": 1,
        "colsample_bytree": 0.8,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
        "min_child_samples": 20,  # 리프 노드 최소 샘플 수
        "objective": "binary",
        "metric": "binary_logloss",
        "random_state": 42,
        "verbose": -1,
    }
    
    if params:
        default_params.update(params)
    
    model = lgb.LGBMClassifier(**default_params)
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        callbacks=[lgb.early_stopping(50), lgb.log_evaluation(100)],
    )
    
    val_acc = accuracy_score(y_val, model.predict(X_val))
    print(f"[LightGBM] Val Accuracy: {val_acc:.4f}, Best iteration: {model.best_iteration_}")
    return model
```

---

## 5. Optuna 하이퍼파라미터 최적화

### 5.1 탐색 공간 정의

```python
# ml/optimize.py
import optuna
from sklearn.model_selection import StratifiedKFold, cross_val_score
import xgboost as xgb
import lightgbm as lgb
import numpy as np

def xgb_objective(trial, X, y):
    params = {
        "n_estimators": trial.suggest_int("n_estimators", 100, 1000),
        "max_depth": trial.suggest_int("max_depth", 3, 8),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
        "reg_alpha": trial.suggest_float("reg_alpha", 1e-5, 10.0, log=True),
        "reg_lambda": trial.suggest_float("reg_lambda", 1e-5, 10.0, log=True),
        "min_child_weight": trial.suggest_int("min_child_weight", 1, 20),
        "gamma": trial.suggest_float("gamma", 0, 1.0),
        "objective": "binary:logistic",
        "random_state": 42,
        "tree_method": "hist",
    }
    
    model = xgb.XGBClassifier(**params)
    
    # Stratified K-Fold (5겹) 교차검증으로 평가
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scores = cross_val_score(model, X, y, cv=skf, scoring="accuracy", n_jobs=-1)
    
    return scores.mean()

def lgbm_objective(trial, X, y):
    params = {
        "n_estimators": trial.suggest_int("n_estimators", 100, 1000),
        "num_leaves": trial.suggest_int("num_leaves", 20, 100),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "subsample_freq": 1,
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
        "reg_alpha": trial.suggest_float("reg_alpha", 1e-5, 10.0, log=True),
        "reg_lambda": trial.suggest_float("reg_lambda", 1e-5, 10.0, log=True),
        "min_child_samples": trial.suggest_int("min_child_samples", 5, 50),
        "objective": "binary",
        "random_state": 42,
        "verbose": -1,
    }
    
    model = lgb.LGBMClassifier(**params)
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scores = cross_val_score(model, X, y, cv=skf, scoring="accuracy", n_jobs=-1)
    
    return scores.mean()

def run_optimization(X_train, y_train, n_trials: int = 50):  # DEFAULT_N_TRIALS=50
    """Optuna 최적화 실행"""
    print("[Optuna] XGBoost 최적화 시작...")
    xgb_study = optuna.create_study(direction="maximize")
    xgb_study.optimize(
        lambda trial: xgb_objective(trial, X_train, y_train),
        n_trials=n_trials, show_progress_bar=True
    )
    
    print("[Optuna] LightGBM 최적화 시작...")
    lgbm_study = optuna.create_study(direction="maximize")
    lgbm_study.optimize(
        lambda trial: lgbm_objective(trial, X_train, y_train),
        n_trials=n_trials, show_progress_bar=True
    )
    
    print(f"[XGBoost] 최적 파라미터: {xgb_study.best_params}")
    print(f"[LightGBM] 최적 파라미터: {lgbm_study.best_params}")
    
    return xgb_study.best_params, lgbm_study.best_params
```

### 5.2 최적화 실행 설정

| 설정 | 값 | 설명 |
|---|---|---|
| `n_trials` | 50 | 탐색 횟수 (TPESampler, 모델별 50 trials) |
| CV | GroupKFold (K=5) | match_key 단위 분할, train+val 내에서만 |
| Sampler | TPE | Tree-structured Parzen Estimator |
| Pruner | MedianPruner | 성능 낮은 trial 조기 종료 |

---

## 6. Stratified K-Fold (K=5) 교차검증

### 6.0 실제 모델 성능 결과

K-Fold (K=5) 교차검증 결과 및 test 세트 최종 평가:

| 모델 | Optuna CV best AUC | Test Acc | Test F1 | Test AUC |
|------|-------------------|---------|--------|---------|
| Random Forest | 0.6901 | — | — | 0.7013 |
| XGBoost | 0.7465 | — | — | 0.7641 |
| LightGBM | 0.7139 | — | — | 0.7332 |
| **앙상블 (Soft Voting)** | — | **0.6958** | **0.7649** | **0.7570** |

- 데이터 분할: 80/20 (train 53,427 / test 13,357, 별도 검증셋 없이 train 내부 GroupKFold로 튜닝)
- Optuna TPESampler 50 trials per model
- verdict: `PASS_TRUSTED_KAGGLE_ONLY_ADVANCED`

### 6.1 최종 성능 평가 (5-Fold)

```python
# ml/evaluate.py
from sklearn.model_selection import GroupKFold
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
import numpy as np

def kfold_evaluate(model, X, y, df, n_splits: int = 5) -> dict:
    """Group K-Fold (K=5) 교차검증으로 최종 성능 평가.
    match_key 단위로 폴드를 분할해 같은 경기가 train/val에 동시에 들어가지 않게 한다.
    train.csv를 5개 폴드로 분할하며, test.csv는 최종 평가 1회에만 사용한다.
    """
    gkf = GroupKFold(n_splits=n_splits)
    
    acc_scores, f1_scores, auc_scores = [], [], []
    
    for fold, (train_idx, val_idx) in enumerate(gkf.split(X, y, groups=df["match_key"]), 1):
        X_fold_train, X_fold_val = X.iloc[train_idx], X.iloc[val_idx]
        y_fold_train, y_fold_val = y.iloc[train_idx], y.iloc[val_idx]
        
        model.fit(X_fold_train, y_fold_train)
        y_pred = model.predict(X_fold_val)
        y_prob = model.predict_proba(X_fold_val)[:, 1]
        
        acc = accuracy_score(y_fold_val, y_pred)
        f1 = f1_score(y_fold_val, y_pred, average="macro")
        auc = roc_auc_score(y_fold_val, y_prob)
        
        acc_scores.append(acc)
        f1_scores.append(f1)
        auc_scores.append(auc)
        
        print(f"Fold {fold:2d} | Acc: {acc:.4f} | F1: {f1:.4f} | AUC: {auc:.4f}")
    
    results = {
        "accuracy_mean": np.mean(acc_scores),
        "accuracy_std": np.std(acc_scores),
        "f1_mean": np.mean(f1_scores),
        "f1_std": np.std(f1_scores),
        "roc_auc_mean": np.mean(auc_scores),
        "roc_auc_std": np.std(auc_scores),
    }
    
    print(f"\n[결과] Accuracy: {results['accuracy_mean']:.4f} ± {results['accuracy_std']:.4f}")
    print(f"[결과] F1-Score: {results['f1_mean']:.4f} ± {results['f1_std']:.4f}")
    print(f"[결과] ROC-AUC: {results['roc_auc_mean']:.4f} ± {results['roc_auc_std']:.4f}")
    
    return results
```

---

## 7. 과적합 방지 전략

### 7.1 판단 기준

```python
def check_overfitting(train_acc: float, val_acc: float, threshold: float = 0.03) -> bool:
    gap = train_acc - val_acc
    if gap > threshold:
        print(f"[경고] 과적합 감지! Train: {train_acc:.4f}, Val: {val_acc:.4f}, Gap: {gap:.4f}")
        return True
    return False
```

### 7.2 과적합 발생 시 대응 방법

| 상황 | 조치 |
|---|---|
| Train-Val 격차 > 3%p | `max_depth` 1 감소, `subsample` 0.1 감소 |
| Val Loss 증가 | `early_stopping_rounds` 30으로 감소 |
| 피처 중요도 편중 | 중요도 하위 3개 피처 제거 후 재학습 |
| 전체적으로 낮은 성능 | 데이터 추가 수집 (HenrikDev API) |

---

## 8. 모델 저장 및 메타데이터

```python
# ml/train.py - 최종 모델 저장
import joblib, json
from datetime import datetime

def save_models(xgb_model, lgbm_model, le_map, metrics: dict):
    """학습된 모델과 메타데이터 저장"""
    import os
    os.makedirs("models", exist_ok=True)
    
    joblib.dump(xgb_model, "models/xgboost_model.joblib")
    joblib.dump(lgbm_model, "models/lgbm_model.joblib")
    joblib.dump(le_map, "models/label_encoder_map.joblib")
    
    metadata = {
        "trained_at": datetime.now().isoformat(),
        "python_version": "3.14",
        "features": FEATURE_COLUMNS,
        "feature_count": len(FEATURE_COLUMNS),
        "train_samples": metrics.get("train_samples"),
        "val_accuracy": metrics.get("val_accuracy"),
        "test_accuracy": metrics.get("test_accuracy"),
        "kfold_accuracy_mean": metrics.get("kfold_accuracy_mean"),
        "kfold_accuracy_std": metrics.get("kfold_accuracy_std"),
        "kfold_f1_mean": metrics.get("kfold_f1_mean"),
        "kfold_roc_auc_mean": metrics.get("kfold_roc_auc_mean"),
        "xgb_params": xgb_model.get_params(),
        "lgbm_params": lgbm_model.get_params(),
        "ensemble_weights": {"rf": 1/3, "xgb": 1/3, "lgbm": 1/3},  # 단순 평균
    }
    
    with open("models/model_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    
    print("[INFO] 모델 저장 완료 ✅")
```

---

## 9. 성능 검증 체크리스트

학습 완료 후 아래 항목을 확인한다.

| 확인 항목 | 점검 방법 |
|---|---|
| K-Fold (K=5) 지표 안정성 | Accuracy / ROC-AUC / F1 평균 및 표준편차 확인 |
| Train-Val 격차 | > 3%p이면 정규화 강화 |
| test.csv 분리 | K-Fold 중 test.csv 미사용 확인 |
| 클래스 불균형 | 팀1/팀2 승률 50:50 여부 확인 |
| 피처 중요도 | RF importances → XGB gain → Permutation → Ablation 순으로 검증 |

---

## 10. 재학습 조건

| 조건 | 주기 |
|---|---|
| 신규 패치로 요원 추가됨 | 패치 후 즉시 |
| HenrikDev 신규 데이터 1,000경기 이상 | 월 1회 |
| 성능 저하 (Accuracy < 0.75 신고) | 즉시 |
| 새 맵 추가 | 충분한 데이터 수집 후 |

```bash
# 재학습 실행
python -m ml.advanced.preprocess  # 새 데이터 포함 재전처리
python -m ml.advanced.optimize    # Optuna HPO 재탐색 (TPESampler 50 trials)
python -m ml.advanced.ensemble    # Soft Voting 앙상블 재학습
python -m ml.advanced.evaluate    # 성능 검증
python -m ml.advanced.validate    # 지표 검증
```
