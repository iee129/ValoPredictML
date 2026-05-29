# 03. LightGBM 완전한 학습 구현

마지막 업데이트: 2026-05-04

## 개요

LightGBM의 완전한 학습 코드를 Native API와 sklearn API 두 가지 방식으로 제공한다. callbacks, early_stopping, 로깅, 평가를 포함한다.
LightGBM은 RF + XGBoost + LightGBM 앙상블 구성원 중 하나다. 스케일링 불필요. 현재 활성 파이프라인은 `sample_weight` 미사용(균등 학습)이며, 아래 함수의 `sample_weight` 인자는 옵션(None이면 균등 가중)이다.

---

## 1. sklearn API 학습 구현

### 1.1 기본 학습 함수

```python
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from pathlib import Path
from datetime import datetime
import logging
import json

logger = logging.getLogger("lightgbm_trainer")


def train_lightgbm(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    sample_weight: pd.Series = None,
    params: dict = None,
    model_dir: str = "models"
) -> tuple[lgb.LGBMClassifier, dict]:
    """
    LightGBM 완전한 학습 함수 (sklearn API).

    Args:
        X_train: 학습 피처 DataFrame (N_train, 43)
        y_train: 학습 레이블 (0: 패, 1: 승)
        X_val: 검증 피처 DataFrame
        y_val: 검증 레이블
        sample_weight: 샘플 가중치 (time_weight × source_weight). None이면 균등 가중치.
        params: 하이퍼파라미터 딕셔너리
        model_dir: 모델 저장 경로

    Returns:
        model: 학습된 LGBMClassifier
        training_info: 학습 메타데이터 딕셔너리
    """
    if params is None:
        params = get_default_lgbm_params()

    logger.info("LightGBM 학습 시작")
    logger.info(f"학습 데이터: {X_train.shape}, 검증 데이터: {X_val.shape}")
    logger.info(f"레이블 분포: {y_train.value_counts().to_dict()}")

    model = lgb.LGBMClassifier(**params)

    start_time = datetime.now()
    model.fit(
        X_train, y_train,
        sample_weight=sample_weight,
        eval_set=[(X_val, y_val)],
        eval_names=["val"],
        eval_metric="binary_logloss",
        callbacks=[
            lgb.early_stopping(stopping_rounds=50, verbose=True),
            lgb.log_evaluation(period=100),   # 100 라운드마다 출력
        ]
    )
    train_duration = (datetime.now() - start_time).total_seconds()

    # 최적 반복 횟수
    best_iteration = model.best_iteration_
    best_score = model.best_score_["val"]["binary_logloss"]

    # 검증 평가
    y_pred = model.predict(X_val)
    y_prob = model.predict_proba(X_val)[:, 1]

    metrics = {
        "val_accuracy": accuracy_score(y_val, y_pred),
        "val_f1": f1_score(y_val, y_pred, average="binary"),
        "val_roc_auc": roc_auc_score(y_val, y_prob),
        "best_iteration": best_iteration,
        "best_val_logloss": best_score,
        "train_duration_seconds": train_duration,
    }

    logger.info(f"학습 완료 - {train_duration:.1f}초")
    logger.info(f"최적 트리 수: {best_iteration}")
    logger.info(f"검증 성능: ACC={metrics['val_accuracy']:.4f}, "
                f"AUC={metrics['val_roc_auc']:.4f}")

    # 모델 저장
    Path(model_dir).mkdir(parents=True, exist_ok=True)
    model_path = f"{model_dir}/lgbm_model.txt"
    model.booster_.save_model(model_path)
    logger.info(f"모델 저장: {model_path}")

    training_info = {
        "model_type": "LGBMClassifier",
        "timestamp": datetime.now().isoformat(),
        "params": params,
        "metrics": metrics,
        "model_path": model_path,
        "feature_names": list(X_train.columns),
        "n_train": len(X_train),
        "n_val": len(X_val),
        "lightgbm_version": lgb.__version__,
    }

    return model, training_info
```

---

## 2. 기본 파라미터 설정

```python
def get_default_lgbm_params() -> dict:
    """
    ValoPredictML 기본 LightGBM 파라미터.
    """
    return {
        # 핵심 구조 (가장 중요)
        "num_leaves": 31,
        "min_child_samples": 20,
        "max_depth": -1,

        # 학습
        "n_estimators": 2000,     # Early Stopping으로 실제 수 결정
        "learning_rate": 0.05,

        # 서브샘플링
        "subsample": 0.8,
        "subsample_freq": 1,      # 매 트리마다 bagging
        "colsample_bytree": 0.8,

        # 정규화
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
        "min_split_gain": 0.0,

        # 효율화 (ValoPredictML 최적화)
        "max_bin": 63,            # 역할군 카운트 0~5 → 63 bin 충분

        # 분류 설정
        "objective": "binary",
        "metric": "binary_logloss",

        # 시스템
        "n_jobs": -1,
        "random_state": 42,
        "verbose": -1,             # 경고 억제
    }
```

---

## 3. Callbacks 상세 설명

### 3.1 사용 가능한 Callbacks 목록

```python
import lightgbm as lgb

# 1. Early Stopping
early_stop_cb = lgb.early_stopping(
    stopping_rounds=50,    # 50라운드 개선 없으면 중단
    first_metric_only=True, # 첫 번째 지표만 기준으로 사용
    verbose=True           # 중단 시 메시지 출력
)

# 2. 로그 출력
log_eval_cb = lgb.log_evaluation(
    period=100,   # 100라운드마다 로그 출력
                   # period=0이면 출력 없음
)

# 3. 커스텀 콜백 (학습 진행 기록)
def custom_callback(period=50):
    """
    커스텀 콜백: 지정 라운드마다 지표 기록.
    """
    history = {"iteration": [], "val_logloss": [], "val_auc": []}

    def callback(env):
        if env.iteration % period == 0:
            # env.evaluation_result_list: [(eval_name, metric, value, is_higher_better), ...]
            for eval_name, metric_name, value, _ in env.evaluation_result_list:
                key = f"{eval_name}_{metric_name}"
                if key not in history:
                    history[key] = []
                history[key].append(value)
            history["iteration"].append(env.iteration)
            logger.info(f"Iter {env.iteration}: {dict(zip([r[1] for r in env.evaluation_result_list], [r[2] for r in env.evaluation_result_list]))}")

    callback.order = 0
    return callback, history
```

### 3.2 다중 평가 지표 설정

```python
model = lgb.LGBMClassifier(
    n_estimators=2000,
    metric=["binary_logloss", "auc"],  # 두 지표 동시 추적
    learning_rate=0.05,
    verbose=-1,
)

model.fit(
    X_train, y_train,
    eval_set=[(X_train, y_train), (X_val, y_val)],
    eval_names=["train", "val"],
    eval_metric=["binary_logloss", "auc"],
    callbacks=[
        lgb.early_stopping(50, first_metric_only=True),  # logloss 기준
        lgb.log_evaluation(100),
    ]
)

# 결과 확인
print("학습 logloss 히스토리:", model.evals_result_["train"]["binary_logloss"][-5:])
print("검증 logloss 히스토리:", model.evals_result_["val"]["binary_logloss"][-5:])
print("검증 AUC 히스토리:", model.evals_result_["val"]["auc"][-5:])
```

---

## 4. Native API 학습 (고급)

```python
def train_lightgbm_native(
    X_train, y_train, X_val, y_val, params
) -> lgb.Booster:
    """
    LightGBM Native API를 사용한 학습.
    sklearn API보다 더 세밀한 제어 가능.
    """
    dtrain = lgb.Dataset(
        X_train, label=y_train,
        feature_name=list(X_train.columns),
        categorical_feature=[],  # 범주형 피처 (map_encoded는 수치형으로 처리)
        free_raw_data=False      # 메모리 절약
    )
    dval = lgb.Dataset(
        X_val, label=y_val,
        reference=dtrain,        # 학습 데이터와 같은 bin 기준 사용
        free_raw_data=False
    )

    native_params = {
        "objective": "binary",
        "metric": ["binary_logloss", "auc"],
        "num_leaves": params.get("num_leaves", 31),
        "min_child_samples": params.get("min_child_samples", 20),
        "learning_rate": params.get("learning_rate", 0.05),
        "subsample": params.get("subsample", 0.8),
        "subsample_freq": 1,
        "colsample_bytree": params.get("colsample_bytree", 0.8),
        "reg_alpha": params.get("reg_alpha", 0.1),
        "reg_lambda": params.get("reg_lambda", 1.0),
        "max_bin": params.get("max_bin", 63),
        "verbose": -1,
        "seed": 42,
    }

    callbacks = [
        lgb.early_stopping(stopping_rounds=50),
        lgb.log_evaluation(period=100),
    ]

    booster = lgb.train(
        native_params,
        dtrain,
        num_boost_round=2000,
        valid_sets=[dtrain, dval],
        valid_names=["train", "val"],
        callbacks=callbacks,
    )

    print(f"최적 트리 수: {booster.best_iteration}")
    print(f"최적 val AUC: {booster.best_score['val']['auc']:.4f}")

    return booster
```

---

## 5. K-Fold 교차 검증

```python
from sklearn.model_selection import GroupKFold

def train_lightgbm_cv(X, y, params, df, n_splits=5):
    """
    Group K-Fold (K=5) 교차 검증으로 LightGBM 안정적 성능 추정.
    match_key 단위로 폴드를 분할해 같은 경기가 train/val에 동시에 들어가지 않게 한다.
    train.csv를 5개 폴드로 분할해 각 폴드를 한 번씩 검증에 사용한다.
    test.csv는 K-Fold와 완전히 분리되어 최종 평가 1회에만 사용한다.
    """
    gkf = GroupKFold(n_splits=n_splits)
    fold_metrics = []

    for fold_idx, (train_idx, val_idx) in enumerate(gkf.split(X, y, groups=df["match_key"])):
        X_tr, X_vl = X.iloc[train_idx], X.iloc[val_idx]
        y_tr, y_vl = y.iloc[train_idx], y.iloc[val_idx]

        model = lgb.LGBMClassifier(**params)
        model.fit(
            X_tr, y_tr,
            eval_set=[(X_vl, y_vl)],
            callbacks=[
                lgb.early_stopping(50, verbose=False),
                lgb.log_evaluation(0),  # 출력 억제
            ]
        )

        y_pred = model.predict(X_vl)
        y_prob = model.predict_proba(X_vl)[:, 1]

        fold_result = {
            "fold": fold_idx + 1,
            "best_iteration": model.best_iteration_,
            "accuracy": accuracy_score(y_vl, y_pred),
            "f1": f1_score(y_vl, y_pred),
            "roc_auc": roc_auc_score(y_vl, y_prob),
        }
        fold_metrics.append(fold_result)

        logger.info(f"Fold {fold_idx+1}/{n_splits}: "
                    f"ACC={fold_result['accuracy']:.4f}, "
                    f"AUC={fold_result['roc_auc']:.4f}, "
                    f"iter={fold_result['best_iteration']}")

    df = pd.DataFrame(fold_metrics)
    summary = {
        "accuracy_mean": df["accuracy"].mean(),
        "accuracy_std": df["accuracy"].std(),
        "roc_auc_mean": df["roc_auc"].mean(),
        "roc_auc_std": df["roc_auc"].std(),
        "f1_mean": df["f1"].mean(),
        "f1_std": df["f1"].std(),
        "avg_best_iteration": df["best_iteration"].mean(),
    }

    print(f"\n{n_splits}-Fold CV 결과 (LightGBM):")
    print(f"  Accuracy:  {summary['accuracy_mean']:.4f} ± {summary['accuracy_std']:.4f}")
    print(f"  ROC-AUC:   {summary['roc_auc_mean']:.4f} ± {summary['roc_auc_std']:.4f}")
    print(f"  F1:        {summary['f1_mean']:.4f} ± {summary['f1_std']:.4f}")
    print(f"  평균 트리 수: {summary['avg_best_iteration']:.0f}")

    return summary, df
```

---

## 6. 학습 곡선 시각화

```python
import matplotlib.pyplot as plt

def plot_lgbm_learning_curves(model: lgb.LGBMClassifier):
    """
    LightGBM 학습/검증 손실 곡선 시각화.
    """
    evals = model.evals_result_

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # logloss
    if "binary_logloss" in list(evals.values())[0]:
        for ax, metric in zip(axes, ["binary_logloss", "auc"]):
            for set_name, result in evals.items():
                if metric in result:
                    label = "학습" if set_name == "train" else "검증"
                    color = "steelblue" if set_name == "train" else "darkorange"
                    ax.plot(result[metric], label=f"{label} {metric}", color=color)

            best_iter = model.best_iteration_
            ax.axvline(x=best_iter, color="red", linestyle="--",
                       label=f"Early Stop (iter={best_iter})")
            ax.set_xlabel("부스팅 라운드")
            ax.set_ylabel(metric)
            ax.set_title(f"LightGBM {metric} 학습 곡선")
            ax.legend()
            ax.grid(True, alpha=0.3)

    plt.suptitle("LightGBM 학습 곡선", fontsize=14)
    plt.tight_layout()
    plt.savefig("reports/figures/lgbm_learning_curve.png", dpi=150)
    plt.show()
```

---

## 7. 피처 중요도 추출

```python
def get_lgbm_feature_importance(model: lgb.LGBMClassifier,
                                  feature_names: list[str]) -> pd.DataFrame:
    """
    LightGBM 피처 중요도 추출 (gain 기준).
    """
    booster = model.booster_

    importance_gain = booster.feature_importance(importance_type="gain")
    importance_split = booster.feature_importance(importance_type="split")

    df = pd.DataFrame({
        "feature": feature_names,
        "gain": importance_gain,
        "split": importance_split,
        "gain_normalized": importance_gain / importance_gain.sum(),
        "split_normalized": importance_split / importance_split.sum(),
    }).sort_values("gain", ascending=False)

    print("LightGBM 피처 중요도 (Gain 기준 상위 10):")
    print(df.head(10)[["feature", "gain_normalized", "split_normalized"]].to_string(index=False))

    return df
```

---

## 8. XGBoost vs LightGBM 성능 비교

```python
def compare_xgb_lgbm(xgb_metrics: dict, lgbm_metrics: dict) -> pd.DataFrame:
    """
    XGBoost와 LightGBM 성능 및 효율성 비교.
    """
    comparison = pd.DataFrame({
        "지표": ["Accuracy", "ROC-AUC", "F1-Score",
                "학습 시간(초)", "최적 트리 수"],
        "XGBoost": [
            xgb_metrics["val_accuracy"],
            xgb_metrics["val_roc_auc"],
            xgb_metrics["val_f1"],
            xgb_metrics["train_duration_seconds"],
            xgb_metrics["best_iteration"],
        ],
        "LightGBM": [
            lgbm_metrics["val_accuracy"],
            lgbm_metrics["val_roc_auc"],
            lgbm_metrics["val_f1"],
            lgbm_metrics["train_duration_seconds"],
            lgbm_metrics["best_iteration"],
        ],
    })

    comparison["우위"] = comparison.apply(
        lambda row: "XGBoost" if (
            row["지표"] not in ["학습 시간(초)"] and row["XGBoost"] > row["LightGBM"]
        ) or (
            row["지표"] == "학습 시간(초)" and row["XGBoost"] < row["LightGBM"]
        ) else "LightGBM",
        axis=1
    )

    print("\nXGBoost vs LightGBM 비교:")
    print(comparison.to_string(index=False))

    speed_ratio = xgb_metrics["train_duration_seconds"] / lgbm_metrics["train_duration_seconds"]
    print(f"\nLightGBM 속도 우위: {speed_ratio:.1f}배 빠름")

    return comparison
```

---

## 9. 메타데이터 저장

```python
def save_lgbm_metadata(training_info: dict, summary: dict,
                        output_path: str = "models/lgbm_metadata.json"):
    """
    LightGBM 학습 메타데이터 저장.
    """
    metadata = {
        **training_info,
        "cv_summary": summary,
        "lightgbm_version": lgb.__version__,
    }

    with open(output_path, "w") as f:
        json.dump(metadata, f, indent=2, default=str)

    print(f"메타데이터 저장: {output_path}")
    return metadata
```
