# 05. 데이터 학습 전략

마지막 업데이트: 2026-06-04

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

이 프로젝트는 두 모델을 함께 사용한다.

**① 베이스라인: LR + DT soft voting**

- 로지스틱 회귀(선형)와 단일 결정 트리를 0.50/0.50 동일 가중으로 soft voting
- 랜덤 Train 80% / Test 20% 분할 (강의 산출물 PDF 기준)
- 피처 421개. 개선의 기준선을 세우는 용도

**② 심화(메인): RF + XGBoost + LightGBM soft voting**

- 세 모델의 예측 확률을 **가중 평균**(RF 2.0 : XGB 3.0 : LGBM 0.1)하여 최종 예측
- 시간순 year-block 분할 (train 2020–2025 / test 2026), 피처 179개, 91,458개 맵 단위 승패 샘플
- 딥러닝(PyTorch/TensorFlow) 금지 — 트리 기반 모델 전용

```python
# 심화 앙상블 예측 예시 (가중 soft voting, RF 2.0 : XGB 3.0 : LGBM 0.1)
w_rf, w_xgb, w_lgbm = 2.0, 3.0, 0.1
rf_prob = rf_model.predict_proba(X)[:, 1]
xgb_prob = xgb_model.predict_proba(X)[:, 1]
lgbm_prob = lgbm_model.predict_proba(X)[:, 1]
ensemble_prob = (w_rf*rf_prob + w_xgb*xgb_prob + w_lgbm*lgbm_prob) / (w_rf + w_xgb + w_lgbm)
predictions = (ensemble_prob >= 0.5).astype(int)
```

---

## 2. Baseline 모델 (LR + DT soft voting)

학습 시작 전 Baseline을 먼저 구축하여 개선의 기준을 세웁니다. **강의 산출물(PDF) 기준 베이스라인은 로지스틱 회귀(LR)와 결정 트리(DT)의 soft voting**이며, 랜덤 80/20 분할을 사용한다.

```python
# Baseline: LR + DT soft voting (0.50/0.50)
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.ensemble import VotingClassifier
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

def train_baseline(X_train, y_train, X_test, y_test):
    lr = Pipeline([
        ("scaler", StandardScaler()),
        ("lr", LogisticRegression(max_iter=1000, random_state=42)),
    ])
    dt = DecisionTreeClassifier(random_state=42)

    voting = VotingClassifier(
        estimators=[("lr", lr), ("dt", dt)],
        voting="soft",
        weights=[0.5, 0.5],   # 동일 가중 soft voting
    )
    voting.fit(X_train, y_train)
    return evaluate_model(voting, X_test, y_test)

def evaluate_model(model, X, y):
    y_pred = model.predict(X)
    y_prob = model.predict_proba(X)[:, 1]
    return {
        "accuracy": accuracy_score(y, y_pred),
        "f1": f1_score(y, y_pred, average="binary"),
        "roc_auc": roc_auc_score(y, y_prob),
    }
```

**Baseline 성능 (PDF 기준, 랜덤 80/20):**

| 모델 | AUC | Acc | F1 |
|------|----:|----:|---:|
| Logistic Regression 단독 | 0.6000 | 0.5821 | 0.6216 |
| Decision Tree 단독 | 0.5556 | 0.5483 | 0.5860 |
| **LR+DT soft voting (앙상블)** | **0.5943** | **0.5667** | **0.6072** |
| baseline_random (랜덤 추측) | 0.4864 | — | — |

앙상블은 majority 클래스 분류 대비 +0.0649 향상. 베이스라인은 LR과 DT만으로 구성된다 — Random Forest는 베이스라인이 아니라 **심화 앙상블 구성원**이다(아래 3장 이후).

---

## 3. XGBoost 학습

### 3.1 기본 설정

```python
import xgboost as xgb
from sklearn.metrics import accuracy_score

def train_xgboost(X_train, y_train, X_val, y_val, params: dict = None) -> xgb.XGBClassifier:
    # 현재 심화 코드 고정값 (Optuna 미사용)
    default_params = {
        "n_estimators": 500,
        "max_depth": 4,
        "learning_rate": 0.03,
        "subsample": 0.8,
        "colsample_bytree": 0.7,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
        "min_child_weight": 10,
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
    # 현재 심화 코드 고정값 (Optuna 미사용)
    default_params = {
        "n_estimators": 1000,
        "num_leaves": 63,
        "max_depth": -1,  # -1 = 무제한 (num_leaves로 제어)
        "learning_rate": 0.02,
        "subsample": 0.8,
        "subsample_freq": 1,
        "colsample_bytree": 0.7,
        "min_child_samples": 40,  # 리프 노드 최소 샘플 수
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

## 5. 하이퍼파라미터 결정 방식

### 5.0 현재 방식 — 고정값 + 가중치 grid search (Optuna 미사용)

> ★ **현재 심화 모델은 Optuna를 사용하지 않는다.** RF/XGB/LightGBM은 아래 코드 고정 하이퍼파라미터를 그대로 쓰고, soft voting 가중치만 2025 검증 split 기준 grid search로 고른다. 이 절(5.1~5.2)에 나오는 Optuna 코드는 **향후 계획(자동 HPO 도입 시)** 참고용이며, 현행 산출물의 성능 수치와는 무관하다.

현재 코드 고정 하이퍼파라미터:

| 모델 | 고정 하이퍼파라미터 |
|------|-------------------|
| Random Forest | `n_estimators=500`, `max_depth=12`, `min_samples_leaf=20` |
| XGBoost | `n_estimators=500`, `max_depth=4`, `learning_rate=0.03`, `subsample=0.8`, `colsample_bytree=0.7`, `min_child_weight=10`, `reg_alpha=0.1`, `reg_lambda=1.0` |
| LightGBM | `n_estimators=1000`, `num_leaves=63`, `learning_rate=0.02`, `min_child_samples=40`, `subsample=0.8`, `colsample_bytree=0.7` |
| soft voting 가중치 | RF 2.0 : XGB 3.0 : LGBM 0.1 (2025 검증 split grid search로 선택, val AUC 0.6682) |

### 5.1 (향후 계획) Optuna 탐색 공간 정의

```python
# (향후 계획) ml/optimize.py — 현재 파이프라인에는 적용되지 않음
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

### 5.2 (향후 계획) 최적화 실행 설정

| 설정 | 값 | 설명 |
|---|---|---|
| `n_trials` | 50 (예정) | 탐색 횟수 (TPESampler, 모델별 50 trials) |
| CV | GroupKFold (K=5) | match_key 단위 분할, train+val 내에서만 |
| Sampler | TPE | Tree-structured Parzen Estimator |
| Pruner | MedianPruner | 성능 낮은 trial 조기 종료 |

> 위 표는 자동 HPO 도입 시의 계획이다. 현행 산출물은 5.0의 고정 하이퍼파라미터 + 가중치 grid search로 생성됐다.

---

## 6. 성능 평가

### 6.0 실제 모델 성능 결과 (현행 — 시간순 split)

심화 모델은 시간순 year-block 분할(train 2020–2025 / test 2026)로 평가한다. 행 단위는 BO 시리즈 수가 아니라 맵 단위 승패 샘플이다. 출처: `reports/advanced/metrics.json`.

| 모델 | Test AUC | Test Acc | Test F1 |
|------|---------:|---------:|--------:|
| Random Forest | 0.6965 | — | — |
| XGBoost | 0.7007 | — | — |
| LightGBM | 0.7015 | — | — |
| **앙상블 (가중 Soft Voting)** | **0.7010** | **0.6454** | **0.6478** |

- 데이터 분할: 시간순 (train 2020–2025 = 75,405 / test 2026 = 16,053, 맵 단위 승패 샘플)
- 가중치 선택용 val(2025) AUC: 0.6682 (RF 2.0 : XGB 3.0 : LGBM 0.1)
- `final_verdict`: `신뢰 가능`
- 베이스라인(LR+DT soft voting, 랜덤 80/20)은 PDF 기준 AUC 0.5943 / Acc 0.5667 / F1 0.6072. 분할 방식이 다르므로 두 AUC를 직접 비교하지 않는다.

### 6.1 교차 검증 코드 (참고)

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

def save_models(xgb_model, lgbm_model, metrics: dict):
    """학습된 모델과 메타데이터 저장"""
    import os
    os.makedirs("models/advanced", exist_ok=True)
    
    joblib.dump(xgb_model, "models/advanced/xgb.joblib")
    joblib.dump(lgbm_model, "models/advanced/lgbm.joblib")
    # label encoder는 파이프라인 내부에서 처리하므로 별도 저장 불필요
    
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
        "ensemble_weights": {"rf": 2.0, "xgb": 3.0, "lgbm": 0.1},  # 가중 soft voting
    }
    
    with open("models/advanced/meta.json", "w") as f:
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
# 재학습 실행 (현행 — Optuna 미사용, 고정 하이퍼파라미터 + 가중치 grid search)
python -m features.chrono_preprocess --include-vlrgg  # 새 데이터 포함 시간순 재전처리
python -m ml.advanced.ensemble    # 가중 Soft Voting 앙상블 재학습 (RF 2.0 : XGB 3.0 : LGBM 0.1)
python -m ml.advanced.evaluate    # 성능 검증 → reports/advanced/metrics.json
python -m ml.advanced.validate    # 누수/지표 검증 → reports/advanced/validation.json
```
