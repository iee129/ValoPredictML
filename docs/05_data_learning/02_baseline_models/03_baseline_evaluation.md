# 03. Baseline 성능 기준표 및 비교 방법론

마지막 업데이트: 2026-05-04

## 개요

베이스라인 모델들의 성능을 체계적으로 비교하고, 최종 앙상블 모델(RF + XGBoost + LightGBM 단순 평균)이 달성해야 할 최소 기준을 설정한다.
평가 지표: Accuracy, ROC-AUC, F1. 교차 검증: K-Fold (K=5). test.csv는 최종 평가 1회만 사용.

---

## 1. 베이스라인 성능 기준표

### 1.1 모델별 성능 비교 (K-Fold K=5 기준 예상값, 43 피처, ~80~100K 맵 행)

| 모델 | Accuracy | ROC-AUC | F1-Score | 학습 시간 | 역할 |
|------|----------|---------|---------|---------|------|
| Dummy (다수 클래스) | ~0.51 | ~0.50 | ~0.34 | < 0.01s | 하한 |
| Logistic Regression | ~0.55~0.58 | ~0.57~0.61 | ~0.54~0.57 | < 1s | Baseline (메인 아님) |
| Random Forest | ~0.60~0.63 | ~0.62~0.66 | ~0.59~0.62 | ~10s | Baseline+ / 앙상블 |
| **RF+XGB+LGBM 앙상블** | **~0.63~0.66** | **~0.66~0.69** | **~0.62~0.65** | ~35s | **메인** |

실제 수치는 전처리 완료 후 측정 — 현재 미구현.

### 1.2 성능 갭 분석

```python
baseline_results = {
    "Dummy":               {"accuracy": 0.51, "roc_auc": 0.50, "f1": 0.34},
    "LogisticRegression":  {"accuracy": 0.57, "roc_auc": 0.59, "f1": 0.56},
    "RandomForest":        {"accuracy": 0.62, "roc_auc": 0.64, "f1": 0.61},
    "RF+XGB+LGBM_Ensemble": {"accuracy": 0.65, "roc_auc": 0.67, "f1": 0.64},
}

# 갭 계산 (앙상블 대비)
target = baseline_results["RF+XGB+LGBM_Ensemble"]
for model, perf in baseline_results.items():
    if model == "RF+XGB+LGBM_Ensemble":
        continue
    gap_acc = target["accuracy"] - perf["accuracy"]
    gap_auc = target["roc_auc"] - perf["roc_auc"]
    print(f"{model:25s}: Accuracy 갭 = {gap_acc:+.2f}, AUC 갭 = {gap_auc:+.2f}")
```

---

## 2. 비교 방법론

### 2.1 통계적 유의성 검정 (McNemar's Test)

두 모델의 예측 결과가 통계적으로 유의미하게 다른지 검정:

```python
from statsmodels.stats.contingency_tables import mcnemar
import numpy as np

def mcnemar_test(y_true, pred_model1, pred_model2, model1_name, model2_name):
    """
    McNemar's test: 두 분류기의 오류 패턴이 다른지 검정.

    귀무가설: 두 모델의 오류율이 동일
    p < 0.05: 통계적으로 유의미한 차이
    """
    # 혼동 행렬 구성
    # b: 모델1 맞고 모델2 틀림
    # c: 모델1 틀리고 모델2 맞음
    b = np.sum((pred_model1 == y_true) & (pred_model2 != y_true))
    c = np.sum((pred_model1 != y_true) & (pred_model2 == y_true))

    table = [[0, b], [c, 0]]  # McNemar table
    result = mcnemar(table, exact=True)

    print(f"\nMcNemar's Test: {model1_name} vs {model2_name}")
    print(f"  b (M1 옳고 M2 틀림): {b}")
    print(f"  c (M1 틀리고 M2 옳음): {c}")
    print(f"  p-value: {result.pvalue:.4f}")
    print(f"  결론: {'유의미한 차이' if result.pvalue < 0.05 else '유의미한 차이 없음'}")

    return result
```

### 2.2 Bootstrap 신뢰구간

```python
def bootstrap_confidence_interval(y_true, y_prob, metric="roc_auc",
                                   n_bootstrap=1000, ci=0.95):
    """
    Bootstrap으로 성능 지표의 신뢰구간 계산.
    """
    from sklearn.metrics import roc_auc_score, accuracy_score
    from sklearn.utils import resample

    scores = []
    n = len(y_true)

    for _ in range(n_bootstrap):
        indices = resample(range(n), replace=True, random_state=None)
        y_true_boot = y_true[indices]
        y_prob_boot = y_prob[indices]

        if metric == "roc_auc":
            # 클래스가 하나만 있으면 스킵
            if len(np.unique(y_true_boot)) < 2:
                continue
            score = roc_auc_score(y_true_boot, y_prob_boot)
        elif metric == "accuracy":
            score = accuracy_score(y_true_boot, (y_prob_boot >= 0.5).astype(int))

        scores.append(score)

    lower = np.percentile(scores, (1 - ci) / 2 * 100)
    upper = np.percentile(scores, (1 + ci) / 2 * 100)
    mean = np.mean(scores)

    print(f"\n{metric} Bootstrap {ci*100:.0f}% 신뢰구간:")
    print(f"  Mean: {mean:.4f}")
    print(f"  [{lower:.4f}, {upper:.4f}]")

    return {"mean": mean, "lower": lower, "upper": upper}
```

### 2.3 DeLong's Test (ROC-AUC 비교)

```python
def delong_test(y_true, prob_model1, prob_model2):
    """
    DeLong's test: 두 ROC-AUC가 통계적으로 다른지 검정.
    sklearn-compatible 구현.
    """
    # 간소화 버전: Mann-Whitney U test 기반 AUC 추정
    from scipy.stats import mannwhitneyu

    pos_mask = y_true == 1
    neg_mask = y_true == 0

    pos_probs1 = prob_model1[pos_mask]
    neg_probs1 = prob_model1[neg_mask]

    pos_probs2 = prob_model2[pos_mask]
    neg_probs2 = prob_model2[neg_mask]

    # AUC 차이 검정
    diff_scores = (pos_probs1 - neg_probs1.reshape(-1, 1)).flatten() - \
                  (pos_probs2 - neg_probs2.reshape(-1, 1)).flatten()

    stat, p_value = mannwhitneyu(
        (pos_probs1 - neg_probs1.reshape(-1, 1)).flatten(),
        (pos_probs2 - neg_probs2.reshape(-1, 1)).flatten(),
        alternative="two-sided"
    )

    print(f"DeLong's Test p-value: {p_value:.4f}")
    return p_value
```

---

## 3. 표준 비교 파이프라인

### 3.1 전체 베이스라인 비교 실행

```python
import json
from datetime import datetime
from pathlib import Path

def run_baseline_comparison(X_train, y_train, X_val, y_val, X_test, y_test,
                             feature_names, output_dir="results"):
    """
    모든 베이스라인 모델을 학습하고 성능을 비교하는 전체 파이프라인.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    results = {}

    # 1. Dummy 베이스라인
    from sklearn.dummy import DummyClassifier
    dummy = DummyClassifier(strategy="most_frequent", random_state=42)
    dummy.fit(X_train, y_train)
    dummy_pred = dummy.predict(X_test)
    dummy_prob = dummy.predict_proba(X_test)[:, 1]
    results["Dummy"] = {
        "accuracy": accuracy_score(y_test, dummy_pred),
        "roc_auc": roc_auc_score(y_test, dummy_prob)
            if len(np.unique(dummy_prob)) > 1 else 0.5,
        "f1": f1_score(y_test, dummy_pred, zero_division=0)
    }
    print(f"[1/4] Dummy: ACC={results['Dummy']['accuracy']:.4f}")

    # 2. Logistic Regression
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    lr_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("lr", LogisticRegression(C=1.0, max_iter=1000, random_state=42))
    ])
    lr_pipeline.fit(X_train, y_train)
    lr_pred = lr_pipeline.predict(X_test)
    lr_prob = lr_pipeline.predict_proba(X_test)[:, 1]
    results["LogisticRegression"] = {
        "accuracy": accuracy_score(y_test, lr_pred),
        "roc_auc": roc_auc_score(y_test, lr_prob),
        "f1": f1_score(y_test, lr_pred)
    }
    print(f"[2/4] LR: ACC={results['LogisticRegression']['accuracy']:.4f}, "
          f"AUC={results['LogisticRegression']['roc_auc']:.4f}")

    # 3. Random Forest
    from sklearn.ensemble import RandomForestClassifier
    rf = RandomForestClassifier(n_estimators=200, oob_score=True,
                                 n_jobs=-1, random_state=42)
    rf.fit(X_train, y_train)
    rf_pred = rf.predict(X_test)
    rf_prob = rf.predict_proba(X_test)[:, 1]
    results["RandomForest"] = {
        "accuracy": accuracy_score(y_test, rf_pred),
        "roc_auc": roc_auc_score(y_test, rf_prob),
        "f1": f1_score(y_test, rf_pred),
        "oob_score": rf.oob_score_
    }
    print(f"[3/4] RF: ACC={results['RandomForest']['accuracy']:.4f}, "
          f"AUC={results['RandomForest']['roc_auc']:.4f}")

    # 4. 결과 저장
    comparison_report = {
        "timestamp": datetime.now().isoformat(),
        "data_info": {
            "n_train": len(X_train),
            "n_val": len(X_val),
            "n_test": len(X_test),
            "n_features": X_train.shape[1],
            "feature_names": feature_names
        },
        "results": results,
        "targets": {"accuracy": 0.80, "roc_auc": 0.82},
        "gaps_to_target": {
            model: {
                metric: round(0.80 if metric == "accuracy" else 0.82)
                         - results[model].get(metric, 0)
                for metric in ["accuracy", "roc_auc"]
            }
            for model in results
        }
    }

    output_path = f"{output_dir}/baseline_comparison.json"
    with open(output_path, "w") as f:
        json.dump(comparison_report, f, indent=2)

    print(f"\n결과 저장: {output_path}")
    return comparison_report
```

### 3.2 시각화 비교 차트

```python
import matplotlib.pyplot as plt
import numpy as np

def plot_baseline_comparison(results: dict):
    """
    베이스라인 모델 성능 비교 막대 차트.
    """
    models = list(results.keys())
    accuracy_vals = [results[m]["accuracy"] for m in models]
    auc_vals = [results[m]["roc_auc"] for m in models]
    f1_vals = [results[m]["f1"] for m in models]

    x = np.arange(len(models))
    width = 0.25

    fig, ax = plt.subplots(figsize=(12, 6))
    bars1 = ax.bar(x - width, accuracy_vals, width, label="Accuracy", color="steelblue", alpha=0.8)
    bars2 = ax.bar(x, auc_vals, width, label="ROC-AUC", color="darkorange", alpha=0.8)
    bars3 = ax.bar(x + width, f1_vals, width, label="F1-Score", color="forestgreen", alpha=0.8)

    # 목표선
    ax.axhline(y=0.80, color="blue", linestyle="--", linewidth=1.5, label="목표 Accuracy=0.80")
    ax.axhline(y=0.82, color="orange", linestyle="--", linewidth=1.5, label="목표 AUC=0.82")

    # 값 레이블
    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f"{height:.3f}",
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3), textcoords="offset points",
                        ha="center", fontsize=8)

    ax.set_xlabel("모델")
    ax.set_ylabel("성능 지표")
    ax.set_title("베이스라인 모델 성능 비교")
    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation=15)
    ax.set_ylim(0, 1.0)
    ax.legend(loc="lower right")
    ax.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()
    plt.savefig("reports/figures/baseline_comparison.png", dpi=150)
    plt.show()
```

---

## 4. 성능 판단 기준

### 4.1 베이스라인 합격 기준

| 모델 | 최소 합격 Accuracy | 최소 합격 AUC | 실패 시 조치 |
|------|------------------|-------------|------------|
| Dummy | > 0.50 | > 0.50 | 데이터 불균형 확인 |
| LR | > 0.65 | > 0.65 | 피처 스케일링 확인 |
| RF | > 0.70 | > 0.72 | n_estimators 증가 |

### 4.2 베이스라인 실패 시 점검 체크리스트

```python
BASELINE_CHECKLIST = """
베이스라인 성능 미달 시 점검 항목:

[ ] 데이터 균형 확인 (팀1 승 vs 팀2 승 비율)
    → y_train.value_counts() 로 확인
    → 70:30 이상이면 class_weight='balanced' 필수

[ ] 피처 분포 확인
    → X_train.describe() 로 이상치 확인
    → 카운트 피처가 음수인 경우 없는지 확인

[ ] 결측값 처리 확인
    → X_train.isnull().sum() 로 확인
    → has_controller_team1 피처가 올바른 값인지 확인

[ ] 레이블 인코딩 확인
    → 팀1이 항상 home_team인지, 아니면 winner_team인지 정의 일관성
    → y = 1이 팀1 승리를 의미하는지 확인

[ ] 데이터 누수 (Data Leakage) 확인
    → 경기 결과 관련 피처가 포함되지 않았는지 확인
    → map_encoded가 결과와 상관관계 높은 경우 누수 가능성 검토
"""
print(BASELINE_CHECKLIST)
```

---

## 5. 결론 및 다음 단계

베이스라인 구축 완료 후 결론:

1. **Dummy 대비 개선량**: LR > Dummy, RF > LR → 피처가 예측력 있음을 확인
2. **비선형 패턴 존재**: RF가 LR보다 높음 → 역할군 조합 간 비선형 상호작용 존재 확인
3. **앙상블 이점**: RF + XGBoost + LightGBM 단순 평균 → RF 단독보다 안정적이고 높은 성능
4. **데이터 품질 확인**: 베이스라인 성능이 예상 범위에 있으면 전처리 올바름
5. **평가 지표**: Accuracy, ROC-AUC, F1 / K-Fold (K=5) 교차 검증 / test.csv 최종 평가 1회

다음 단계: `03_xgboost/` 폴더의 XGBoost 상세 구현으로 이동.
