# 03. XGBoost 완전한 학습 구현

마지막 업데이트: 2026-05-04

## 개요

Early Stopping, 로깅, 평가 세트, 콜백을 포함한 XGBoost의 완전한 학습 구현 코드를 제공한다.
XGBoost는 RF + XGBoost + LightGBM 앙상블 구성원 중 하나다.
트리 기반이라 스케일링 불필요. 현재 활성 파이프라인은 `sample_weight` 미사용(균등 학습)이며, 하이퍼파라미터는 `ml/advanced/optimize.py`(Optuna)를 따른다.

---

## 1. 기본 학습 파이프라인

```python
import xgboost as xgb
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
import logging
import json
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("xgboost_trainer")


def train_xgboost(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    params: dict = None,
    model_dir: str = "models"
) -> tuple[xgb.XGBClassifier, dict]:
    """
    XGBoost 완전한 학습 함수.

    Args:
        X_train: 학습 피처 DataFrame (N_train, 125)  # advanced 계약
        y_train: 학습 레이블 (0: 패, 1: 승)
        X_val: 검증 피처 DataFrame (N_val, 125)  # advanced 계약
        y_val: 검증 레이블
        params: 하이퍼파라미터 딕셔너리 (None이면 기본값 사용)
        model_dir: 모델 저장 경로

    Returns:
        model: 학습된 XGBClassifier
        training_info: 학습 메타데이터 딕셔너리
    """
    if params is None:
        params = get_default_xgb_params()

    logger.info(f"XGBoost 학습 시작")
    logger.info(f"학습 데이터: {X_train.shape}, 검증 데이터: {X_val.shape}")
    logger.info(f"레이블 분포 - 학습: {y_train.value_counts().to_dict()}")
    logger.info(f"파라미터: {params}")

    # 클래스 불균형 계산
    neg_count = (y_train == 0).sum()
    pos_count = (y_train == 1).sum()
    if "scale_pos_weight" not in params:
        params["scale_pos_weight"] = neg_count / pos_count
        logger.info(f"scale_pos_weight 자동 설정: {params['scale_pos_weight']:.3f}")

    model = xgb.XGBClassifier(**params)

    start_time = datetime.now()
    model.fit(
        X_train, y_train,
        eval_set=[(X_train, y_train), (X_val, y_val)],
        eval_names=["train", "val"],
        verbose=50  # 50 라운드마다 로그 출력
    )
    train_duration = (datetime.now() - start_time).total_seconds()

    # 평가
    best_iteration = model.best_iteration
    y_pred = model.predict(X_val)
    y_prob = model.predict_proba(X_val)[:, 1]

    metrics = {
        "val_accuracy": accuracy_score(y_val, y_pred),
        "val_f1": f1_score(y_val, y_pred, average="binary"),
        "val_roc_auc": roc_auc_score(y_val, y_prob),
        "best_iteration": best_iteration,
        "train_duration_seconds": train_duration,
    }

    logger.info(f"학습 완료 - {train_duration:.1f}초")
    logger.info(f"최적 트리 수: {best_iteration}")
    logger.info(f"검증 성능: ACC={metrics['val_accuracy']:.4f}, "
                f"AUC={metrics['val_roc_auc']:.4f}")

    # 모델 저장
    Path(model_dir).mkdir(parents=True, exist_ok=True)
    model_path = f"{model_dir}/xgb_model.json"
    model.save_model(model_path)
    logger.info(f"모델 저장: {model_path}")

    training_info = {
        "model_type": "XGBClassifier",
        "timestamp": datetime.now().isoformat(),
        "params": params,
        "metrics": metrics,
        "model_path": model_path,
        "feature_names": list(X_train.columns),
        "n_train": len(X_train),
        "n_val": len(X_val),
    }

    return model, training_info
```

---

## 2. 기본 파라미터 설정

```python
def get_default_xgb_params() -> dict:
    """
    ValoPredictML 기본 XGBoost 파라미터.
    """
    return {
        # 트리 구조
        "max_depth": 6,
        "min_child_weight": 3,
        "gamma": 0.0,

        # 부스팅
        "n_estimators": 1000,
        "learning_rate": 0.1,
        "early_stopping_rounds": 50,

        # 서브샘플링
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "colsample_bylevel": 1.0,

        # 정규화
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,

        # 분류 설정
        "objective": "binary:logistic",
        "eval_metric": "logloss",
        "use_label_encoder": False,

        # 시스템
        "n_jobs": -1,
        "random_state": 42,
        "verbosity": 0,
    }
```

---

## 3. Early Stopping 상세 구현

### 3.1 Early Stopping 동작 원리

```python
"""
Early Stopping 작동 방식:
1. eval_set에 검증 데이터 지정
2. 매 라운드마다 검증 지표 계산
3. best_score 갱신 없이 early_stopping_rounds 연속 진행 시 중단
4. model.best_iteration에 최적 트리 수 저장

예시:
라운드 100: val_logloss = 0.580 ← best
라운드 150: val_logloss = 0.585 (개선 없음, 50라운드 카운트)
라운드 151: val_logloss = 0.582 ← 새 best! 카운트 초기화
라운드 201: val_logloss = 0.589 (50라운드 카운트)
...
라운드 251: val_logloss = 0.591 ← 중단! best_iteration=151
"""

# eval_metric 선택 (높을수록 좋은 지표는 XGBoost가 자동 판단)
# "logloss": 낮을수록 좋음 → minimize
# "auc": 높을수록 좋음 → maximize
# "error": 낮을수록 좋음 → minimize (1 - accuracy)

model = xgb.XGBClassifier(
    n_estimators=2000,
    early_stopping_rounds=100,
    eval_metric="logloss",  # 검증 기준
    random_state=42
)

model.fit(
    X_train, y_train,
    eval_set=[(X_val, y_val)],
    verbose=False  # 로그 출력 억제
)

print(f"최적 트리 수: {model.best_iteration}")
print(f"최적 val logloss: {model.best_score:.6f}")
```

### 3.2 eval_set 다중 지정

```python
model.fit(
    X_train, y_train,
    eval_set=[
        (X_train, y_train),  # 학습 세트 (과적합 모니터링)
        (X_val, y_val),      # 검증 세트 (Early Stopping 기준)
    ],
    verbose=100  # 100 라운드마다 출력
)

# 학습 곡선 추출
evals_result = model.evals_result()
train_logloss = evals_result["validation_0"]["logloss"]
val_logloss = evals_result["validation_1"]["logloss"]
```

---

## 4. 학습 곡선 시각화

```python
import matplotlib.pyplot as plt

def plot_xgb_learning_curves(model, title="XGBoost 학습 곡선"):
    """
    XGBoost 학습/검증 손실 곡선 시각화.
    과적합 여부 및 Early Stopping 지점 확인.
    """
    evals_result = model.evals_result()

    # eval_set 이름 추출
    eval_keys = list(evals_result.keys())
    metric = list(evals_result[eval_keys[0]].keys())[0]

    fig, ax = plt.subplots(figsize=(12, 5))

    for i, key in enumerate(eval_keys):
        values = evals_result[key][metric]
        label = "학습" if i == 0 else "검증"
        color = "steelblue" if i == 0 else "darkorange"
        ax.plot(values, label=f"{label} {metric}", color=color)

    # Best iteration 표시
    best_iter = model.best_iteration
    ax.axvline(x=best_iter, color="red", linestyle="--",
               label=f"Early Stopping (iter={best_iter})")

    ax.set_xlabel("부스팅 라운드")
    ax.set_ylabel(metric)
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("reports/figures/xgb_learning_curve.png", dpi=150)
    plt.show()

    # 과적합 진단
    train_final = evals_result[eval_keys[0]][metric][-1]
    val_best = model.best_score
    gap = abs(val_best - train_final)
    print(f"\n과적합 진단:")
    print(f"  학습 {metric}: {train_final:.4f}")
    print(f"  검증 {metric}: {val_best:.4f}")
    print(f"  갭: {gap:.4f} {'← 과적합 주의' if gap > 0.05 else '← 정상'}")
```

---

## 5. K-Fold 교차 검증 학습

```python
from sklearn.model_selection import GroupKFold

def train_xgboost_cv(X, y, params, df, n_splits=5):
    """
    Group K-Fold (K=5) 교차 검증으로 XGBoost 안정적 성능 추정.
    match_key 단위로 폴드를 분할해 같은 경기가 train/val에 동시에 들어가지 않게 한다.
    train을 5조각으로 나눠 각 조각을 한 번씩 검증셋으로 사용 → 5번 Accuracy 평균.
    test.csv는 이 함수와 완전 분리 — 최종 평가 1회만 사용.
    """
    gkf = GroupKFold(n_splits=n_splits)
    fold_metrics = []

    for fold_idx, (train_idx, val_idx) in enumerate(gkf.split(X, y, groups=df["match_key"])):
        X_tr, X_vl = X.iloc[train_idx], X.iloc[val_idx]
        y_tr, y_vl = y.iloc[train_idx], y.iloc[val_idx]

        model = xgb.XGBClassifier(**params)
        model.fit(
            X_tr, y_tr,
            eval_set=[(X_vl, y_vl)],
            verbose=False
        )

        y_pred = model.predict(X_vl)
        y_prob = model.predict_proba(X_vl)[:, 1]

        fold_result = {
            "fold": fold_idx + 1,
            "best_iteration": model.best_iteration,
            "accuracy": accuracy_score(y_vl, y_pred),
            "f1": f1_score(y_vl, y_pred),
            "roc_auc": roc_auc_score(y_vl, y_prob),
        }
        fold_metrics.append(fold_result)

        logger.info(f"Fold {fold_idx+1}/{n_splits}: "
                    f"ACC={fold_result['accuracy']:.4f}, "
                    f"AUC={fold_result['roc_auc']:.4f}")

    # 집계
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

    print(f"\n{n_splits}-Fold CV 결과 (평가 지표: Accuracy, ROC-AUC, F1):")
    print(f"  Accuracy:  {summary['accuracy_mean']:.4f} ± {summary['accuracy_std']:.4f}")
    print(f"  ROC-AUC:   {summary['roc_auc_mean']:.4f} ± {summary['roc_auc_std']:.4f}")
    print(f"  F1:        {summary['f1_mean']:.4f} ± {summary['f1_std']:.4f}")
    print(f"  평균 트리 수: {summary['avg_best_iteration']:.0f}")

    return summary, df
```

---

## 6. 로깅 및 모니터링

```python
import logging
from typing import Optional

class XGBoostTrainingLogger:
    """
    XGBoost 학습 진행 상황 로깅 클래스.
    """

    def __init__(self, log_file: Optional[str] = "logs/xgb_training.log"):
        self.logger = logging.getLogger("XGBoostTrainer")
        self.logger.setLevel(logging.INFO)

        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # 파일 핸들러
        if log_file:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def log_training_start(self, params: dict, data_shape: tuple):
        self.logger.info("=" * 60)
        self.logger.info("XGBoost 학습 시작")
        self.logger.info(f"데이터 형태: {data_shape}")
        self.logger.info(f"파라미터: {json.dumps(params, indent=2)}")

    def log_fold_result(self, fold: int, metrics: dict):
        self.logger.info(
            f"Fold {fold}: ACC={metrics['accuracy']:.4f}, "
            f"AUC={metrics['roc_auc']:.4f}, "
            f"F1={metrics['f1']:.4f}, "
            f"best_iter={metrics['best_iteration']}"
        )

    def log_final_result(self, summary: dict):
        self.logger.info("=" * 60)
        self.logger.info("최종 결과:")
        self.logger.info(
            f"  Accuracy:  {summary['accuracy_mean']:.4f} ± {summary['accuracy_std']:.4f}"
        )
        self.logger.info(
            f"  ROC-AUC:   {summary['roc_auc_mean']:.4f} ± {summary['roc_auc_std']:.4f}"
        )
        # 0.80/0.82는 미달성 aspiration 목표 — 현재 False (XGB AUC 0.7641 / 앙상블 Acc 0.6958)
        goal_met = (summary['accuracy_mean'] >= 0.80 and
                    summary['roc_auc_mean'] >= 0.82)
        self.logger.info(f"  aspiration 목표(Acc≥0.80, AUC≥0.82) 달성: {'예' if goal_met else '아니오 (현재 미달성)'}")
```

---

## 7. 메타데이터 저장

```python
def save_training_metadata(training_info: dict, summary: dict,
                            output_path: str = "models/xgb_metadata.json"):
    """
    학습 메타데이터를 JSON으로 저장.
    재현성과 버전 관리를 위함.
    """
    metadata = {
        **training_info,
        "cv_summary": summary,
        "xgboost_version": xgb.__version__,
        # 아래 goals는 미달성 aspiration — 실측: XGB Test AUC 0.7641 / 앙상블 Acc 0.6958
        "goals": {"accuracy": 0.80, "roc_auc": 0.82},
        "achieved": {"roc_auc": 0.7641},  # XGB 실측 Test AUC (adv_kaggle_only)
        "goals_achieved": {
            "accuracy": summary["accuracy_mean"] >= 0.80,  # 현재 False (실측 0.6958)
            "roc_auc": summary["roc_auc_mean"] >= 0.82,    # 현재 False (실측 0.7641)
        }
    }

    with open(output_path, "w") as f:
        json.dump(metadata, f, indent=2, default=str)

    print(f"메타데이터 저장: {output_path}")
    return metadata
```
