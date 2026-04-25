# 01. Optuna 설치 및 Study 설정

## 개요

Optuna는 자동 하이퍼파라미터 최적화(HPO) 프레임워크다. ValoPredictML에서 XGBoost와 LightGBM의 하이퍼파라미터를 베이지안 최적화로 탐색한다. 이 문서는 Optuna 설치부터 전체 최적화 실행까지 완전한 코드를 제공한다.

---

## 1. 설치

```bash
# 기본 설치
pip install optuna

# 시각화 도구 포함
pip install optuna optuna-dashboard plotly

# requirements.txt에 추가
echo "optuna>=3.0.0" >> requirements.txt
echo "optuna-dashboard>=0.9.0" >> requirements.txt

# 설치 확인
python -c "import optuna; print(optuna.__version__)"
```

---

## 2. Optuna 기본 개념

```
핵심 개념:
- Study: 최적화 세션 (여러 Trial의 컨테이너)
- Trial: 단일 하이퍼파라미터 조합 평가
- Objective: 최적화할 목적 함수 (AUC 최대화)
- Sampler: 탐색 전략 (TPE, CmaEs, Grid 등)
- Pruner: 유망하지 않은 Trial 조기 중단

워크플로우:
1. Study 생성 (direction="maximize" 또는 "minimize")
2. Objective 함수 정의 (trial → score 반환)
3. study.optimize() 실행 (n_trials 만큼 반복)
4. 최적 파라미터 추출
```

---

## 3. 기본 Study 생성

### 3.1 인메모리 Study (간단한 실험)

```python
import optuna
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score
import xgboost as xgb
import lightgbm as lgb
import logging

# Optuna 로그 레벨 설정
optuna.logging.set_verbosity(optuna.logging.WARNING)

# 인메모리 Study 생성
study = optuna.create_study(
    study_name="valorant_xgb_optimization",
    direction="maximize",         # AUC 최대화
    sampler=optuna.samplers.TPESampler(
        seed=42,
        n_startup_trials=20      # 처음 20 trials는 랜덤 탐색
    ),
    pruner=optuna.pruners.MedianPruner(
        n_startup_trials=5,      # 처음 5 trials는 Pruning 안 함
        n_warmup_steps=10,       # 각 Trial에서 10 라운드 후 Pruning 판단
    )
)
```

### 3.2 영구 저장 Study (PostgreSQL)

```python
# Vercel Postgres에 Study 결과 저장
import os

DATABASE_URL = os.environ.get("POSTGRES_URL")
# postgresql://user:password@host:5432/dbname 형식

study = optuna.create_study(
    study_name="valorant_xgb_v1",
    direction="maximize",
    storage=f"postgresql+psycopg2://{DATABASE_URL.replace('postgresql://', '')}",
    load_if_exists=True,         # 기존 Study 있으면 이어서 최적화
    sampler=optuna.samplers.TPESampler(seed=42),
)

print(f"Study: {study.study_name}")
print(f"기존 완료 Trials: {len(study.trials)}")
```

### 3.3 SQLite 저장 Study (로컬 개발)

```python
# 로컬 파일 DB (개발 환경)
study = optuna.create_study(
    study_name="valorant_xgb_local",
    direction="maximize",
    storage="sqlite:///optuna_studies.db",
    load_if_exists=True,
    sampler=optuna.samplers.TPESampler(seed=42),
)
```

---

## 4. XGBoost Objective 함수

```python
def xgb_objective(trial, X, y, n_splits=5):
    """
    XGBoost 하이퍼파라미터 최적화 목적 함수.

    Args:
        trial: Optuna Trial 객체
        X: 전체 피처 DataFrame
        y: 전체 레이블 Series
        n_splits: CV fold 수 (속도 위해 5, 최종 평가는 10)

    Returns:
        float: 평균 ROC-AUC (최대화 목표)
    """
    # 하이퍼파라미터 제안
    params = {
        "max_depth": trial.suggest_int("max_depth", 3, 10),
        "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
        "gamma": trial.suggest_float("gamma", 0.0, 1.0),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "n_estimators": trial.suggest_int("n_estimators", 200, 2000),
        "subsample": trial.suggest_float("subsample", 0.5, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
        "reg_alpha": trial.suggest_float("reg_alpha", 0.0, 1.0),
        "reg_lambda": trial.suggest_float("reg_lambda", 0.1, 10.0, log=True),
        # 고정 파라미터
        "use_label_encoder": False,
        "eval_metric": "logloss",
        "early_stopping_rounds": 50,
        "random_state": 42,
        "n_jobs": -1,
        "verbosity": 0,
    }

    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    auc_scores = []

    for fold_idx, (train_idx, val_idx) in enumerate(skf.split(X, y)):
        X_tr, X_vl = X.iloc[train_idx], X.iloc[val_idx]
        y_tr, y_vl = y.iloc[train_idx], y.iloc[val_idx]

        model = xgb.XGBClassifier(**params)
        model.fit(
            X_tr, y_tr,
            eval_set=[(X_vl, y_vl)],
            verbose=False
        )

        y_prob = model.predict_proba(X_vl)[:, 1]
        fold_auc = roc_auc_score(y_vl, y_prob)
        auc_scores.append(fold_auc)

        # Pruning 보고 (중간 결과 → 유망하지 않으면 조기 중단)
        trial.report(fold_auc, step=fold_idx)
        if trial.should_prune():
            raise optuna.exceptions.TrialPruned()

    return np.mean(auc_scores)
```

---

## 5. LightGBM Objective 함수

```python
def lgbm_objective(trial, X, y, n_splits=5):
    """
    LightGBM 하이퍼파라미터 최적화 목적 함수.
    """
    params = {
        "num_leaves": trial.suggest_int("num_leaves", 15, 127),
        "min_child_samples": trial.suggest_int("min_child_samples", 10, 100),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "n_estimators": trial.suggest_int("n_estimators", 200, 2000),
        "subsample": trial.suggest_float("subsample", 0.5, 1.0),
        "subsample_freq": 1,
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
        "reg_alpha": trial.suggest_float("reg_alpha", 0.0, 1.0),
        "reg_lambda": trial.suggest_float("reg_lambda", 0.0, 10.0, log=True),
        "min_split_gain": trial.suggest_float("min_split_gain", 0.0, 1.0),
        "max_bin": 63,  # ValoPredictML 고정
        "objective": "binary",
        "metric": "binary_logloss",
        "random_state": 42,
        "n_jobs": -1,
        "verbose": -1,
    }

    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    auc_scores = []

    for fold_idx, (train_idx, val_idx) in enumerate(skf.split(X, y)):
        X_tr, X_vl = X.iloc[train_idx], X.iloc[val_idx]
        y_tr, y_vl = y.iloc[train_idx], y.iloc[val_idx]

        model = lgb.LGBMClassifier(**params)
        model.fit(
            X_tr, y_tr,
            eval_set=[(X_vl, y_vl)],
            callbacks=[
                lgb.early_stopping(50, verbose=False),
                lgb.log_evaluation(0),
            ]
        )

        y_prob = model.predict_proba(X_vl)[:, 1]
        fold_auc = roc_auc_score(y_vl, y_prob)
        auc_scores.append(fold_auc)

        trial.report(fold_auc, step=fold_idx)
        if trial.should_prune():
            raise optuna.exceptions.TrialPruned()

    return np.mean(auc_scores)
```

---

## 6. 최적화 실행 전체 코드

```python
def run_optimization(X, y, model_type="xgb", n_trials=100, n_splits=5):
    """
    XGBoost 또는 LightGBM 하이퍼파라미터 최적화 실행.

    Args:
        X: 피처 DataFrame
        y: 레이블 Series
        model_type: "xgb" 또는 "lgbm"
        n_trials: Optuna Trial 수
        n_splits: CV fold 수

    Returns:
        study: 완료된 Optuna Study
        best_params: 최적 하이퍼파라미터
    """
    print(f"\n{'='*60}")
    print(f"{model_type.upper()} 하이퍼파라미터 최적화 시작")
    print(f"  n_trials: {n_trials}")
    print(f"  CV folds: {n_splits}")
    print(f"  목표: ROC-AUC 최대화")
    print(f"{'='*60}")

    # Study 생성
    study = optuna.create_study(
        study_name=f"valorant_{model_type}_v1",
        direction="maximize",
        sampler=optuna.samplers.TPESampler(seed=42, n_startup_trials=20),
        pruner=optuna.pruners.MedianPruner(n_startup_trials=5, n_warmup_steps=3),
    )

    # Objective 함수 선택
    if model_type == "xgb":
        objective_fn = lambda trial: xgb_objective(trial, X, y, n_splits)
    elif model_type == "lgbm":
        objective_fn = lambda trial: lgbm_objective(trial, X, y, n_splits)
    else:
        raise ValueError(f"지원하지 않는 모델 유형: {model_type}")

    # 최적화 실행
    from datetime import datetime
    start = datetime.now()

    study.optimize(
        objective_fn,
        n_trials=n_trials,
        timeout=3600,              # 최대 1시간
        n_jobs=1,                  # 병렬 실행 (1: 순차, -1: CPU 전체)
        gc_after_trial=True,       # 메모리 관리
        show_progress_bar=True,
    )

    duration = (datetime.now() - start).total_seconds() / 60

    # 결과 출력
    print(f"\n최적화 완료! ({duration:.1f}분)")
    print(f"완료된 Trials: {len([t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE])}")
    print(f"Pruned Trials: {len([t for t in study.trials if t.state == optuna.trial.TrialState.PRUNED])}")
    print(f"\n최적 ROC-AUC: {study.best_value:.4f}")
    print(f"\n최적 파라미터:")
    for k, v in study.best_params.items():
        print(f"  {k}: {v}")

    # 결과 저장
    import json
    result = {
        "model_type": model_type,
        "best_value": study.best_value,
        "best_params": study.best_params,
        "n_trials": n_trials,
        "n_splits": n_splits,
        "duration_minutes": duration,
    }
    with open(f"results/{model_type}_optuna_result.json", "w") as f:
        json.dump(result, f, indent=2)

    return study, study.best_params
```

---

## 7. 실행 예시

```python
if __name__ == "__main__":
    from sklearn.model_selection import train_test_split

    # 데이터 로드 (실제 경로로 변경)
    df = pd.read_csv("data/processed/valorant_features.csv")
    feature_cols = [
        "duelist_team1", "initiator_team1", "controller_team1", "sentinel_team1",
        "duelist_team2", "initiator_team2", "controller_team2", "sentinel_team2",
        "duelist_diff", "initiator_diff", "controller_diff", "sentinel_diff",
        "has_controller_team1", "has_controller_team2", "map_encoded"
    ]
    X = df[feature_cols]
    y = df["team1_win"]

    # XGBoost 최적화
    xgb_study, xgb_best = run_optimization(X, y, model_type="xgb", n_trials=100)

    # LightGBM 최적화
    lgbm_study, lgbm_best = run_optimization(X, y, model_type="lgbm", n_trials=100)

    print("\n두 모델 최적화 완료!")
    print(f"XGBoost 최적 AUC: {xgb_study.best_value:.4f}")
    print(f"LightGBM 최적 AUC: {lgbm_study.best_value:.4f}")
```
