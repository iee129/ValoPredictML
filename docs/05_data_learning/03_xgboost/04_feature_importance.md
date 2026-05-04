# 04. XGBoost 피처 중요도 분석

마지막 업데이트: 2026-05-04

## 개요

XGBoost가 제공하는 세 가지 피처 중요도(gain, weight, cover)의 차이와 발로란트 도메인 관점에서의 해석, 시각화 코드를 제공한다.

**피처 중요도 검증 순서** (정전 기준):
1. RF `feature_importances_` — 훈련 직후 무료. 빠른 전체 윤곽.
2. XGBoost gain/cover — RF와 비교해 일관성 확인.
3. Permutation importance — 피처를 섞었을 때 성능 하락량. 신뢰도 높음.
4. Ablation study — 카테고리 단위(역할군만 / 스탯만 / 시너지만) 제거 실험.

---

## 1. 세 가지 피처 중요도 종류

### 1.1 Gain (이득) - 권장

```
정의: 피처가 분기에 사용된 모든 트리에서 발생시킨 평균 손실 감소량

Gain(f) = Σ_{트리 t, 피처 f를 사용한 분기} Gain_split(t, f) / Count(f가 사용된 분기 수)

특성:
- 실제 예측력을 가장 잘 반영
- 피처가 얼마나 정보량이 큰지 측정
- 권장되는 기본 피처 중요도
```

### 1.2 Weight (빈도) - 분기 횟수

```
정의: 피처가 전체 트리에서 분기점으로 사용된 횟수

Weight(f) = Σ_{트리 t} Count(피처 f를 사용한 분기)

특성:
- 해석이 직관적 (몇 번 사용됐는가)
- 하지만 연속형 피처가 과대평가되는 경향
- 범주 수가 많은 피처에 불리
- ValoPredictML에서는 Gain 대비 신뢰도 낮음
```

### 1.3 Cover (커버리지)

```
정의: 피처가 분기에 사용될 때 영향받은 샘플들의 평균 hessian 합

Cover(f) = Σ_{피처 f를 사용한 분기} (H_L + H_R) / Count(분기 수)

특성:
- 피처가 얼마나 많은 샘플에 영향을 미치는지 측정
- h = p(1-p)이므로 예측 불확실성이 높은 샘플에 더 큰 가중치
```

---

## 2. 피처 중요도 추출 코드

### 2.1 세 가지 중요도 동시 추출

```python
import xgboost as xgb
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def extract_all_feature_importances(
    model: xgb.XGBClassifier,
    feature_names: list[str]
) -> pd.DataFrame:
    """
    XGBoost의 세 가지 피처 중요도를 모두 추출하여 비교.

    Args:
        model: 학습된 XGBClassifier
        feature_names: 피처 이름 목록

    Returns:
        DataFrame: 세 가지 중요도 값과 순위
    """
    booster = model.get_booster()

    # 세 가지 방식 추출
    gain_scores = booster.get_score(importance_type="gain")
    weight_scores = booster.get_score(importance_type="weight")
    cover_scores = booster.get_score(importance_type="cover")

    # 모든 피처 포함 (사용 안 된 피처는 0)
    importance_data = []
    for feat in feature_names:
        importance_data.append({
            "feature": feat,
            "gain": gain_scores.get(feat, 0.0),
            "weight": weight_scores.get(feat, 0),
            "cover": cover_scores.get(feat, 0.0),
        })

    df = pd.DataFrame(importance_data)

    # 정규화 (0~1 범위)
    for col in ["gain", "weight", "cover"]:
        total = df[col].sum()
        df[f"{col}_normalized"] = df[col] / total if total > 0 else 0

    # 순위
    for col in ["gain", "weight", "cover"]:
        df[f"{col}_rank"] = df[col].rank(ascending=False).astype(int)

    return df.sort_values("gain", ascending=False).reset_index(drop=True)


# 사용 예시
feature_names = [
    # 역할군 카운트 (12)
    "a_duelist", "a_initiator", "a_controller", "a_sentinel",
    "b_duelist", "b_initiator", "b_controller", "b_sentinel",
    "diff_duelist", "diff_initiator", "diff_controller", "diff_sentinel",
    # 역할군 파생 (4)
    "has_controller_a", "has_controller_b",
    "is_double_duelist_a", "is_double_duelist_b",
    # 선수 스탯 (12), 시너지 (6), 요원 조합 (6), 맵 (3) ...
    # 전체 43개 피처 목록은 preprocessing.md 7장 참조
]

importance_df = extract_all_feature_importances(xgb_model, feature_names)
print(importance_df[["feature", "gain_normalized", "weight_normalized", "cover_normalized"]])
```

### 2.2 sklearn API를 통한 간단 추출

```python
# feature_importances_ 속성 (기본: gain)
importances = xgb_model.feature_importances_

importance_df_simple = pd.DataFrame({
    "feature": feature_names,
    "importance": importances
}).sort_values("importance", ascending=False)

print(importance_df_simple.to_string(index=False))
```

---

## 3. 시각화 코드

### 3.1 단일 중요도 막대 차트

```python
def plot_feature_importance(
    importance_df: pd.DataFrame,
    importance_type: str = "gain",
    top_n: int = 15,
    title: str = None
):
    """
    피처 중요도 막대 차트.

    Args:
        importance_df: extract_all_feature_importances() 반환값
        importance_type: "gain", "weight", "cover" 중 하나
        top_n: 상위 몇 개 표시
        title: 차트 제목
    """
    col = f"{importance_type}_normalized"
    plot_df = importance_df.nlargest(top_n, col)

    # 발로란트 역할군별 색상
    role_colors = {
        "duelist": "#FF6B6B",    # 빨강
        "initiator": "#4ECDC4",  # 청록
        "controller": "#45B7D1", # 파랑
        "sentinel": "#96CEB4",   # 초록
        "map": "#FFEAA7",        # 노랑
        "has_": "#DDA0DD",       # 보라
        "diff": "#FFB347",       # 오렌지
    }

    def get_color(feature_name):
        for key, color in role_colors.items():
            if key in feature_name:
                return color
        return "#808080"

    colors = [get_color(f) for f in plot_df["feature"]]

    fig, ax = plt.subplots(figsize=(10, 7))
    bars = ax.barh(
        range(len(plot_df)),
        plot_df[col],
        color=colors,
        edgecolor="white",
        linewidth=0.5
    )
    ax.set_yticks(range(len(plot_df)))
    ax.set_yticklabels(plot_df["feature"])
    ax.invert_yaxis()

    # 값 레이블
    for i, (bar, val) in enumerate(zip(bars, plot_df[col])):
        ax.text(bar.get_width() + 0.001, bar.get_y() + bar.get_height()/2,
                f"{val:.4f}", va="center", fontsize=9)

    ax.set_xlabel(f"정규화된 {importance_type.capitalize()} 중요도")
    ax.set_title(title or f"XGBoost 피처 중요도 ({importance_type})")

    # 범례
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#FFB347", label="차이(diff) 피처"),
        Patch(facecolor="#FF6B6B", label="Duelist"),
        Patch(facecolor="#4ECDC4", label="Initiator"),
        Patch(facecolor="#45B7D1", label="Controller"),
        Patch(facecolor="#96CEB4", label="Sentinel"),
        Patch(facecolor="#DDA0DD", label="has_ 피처"),
        Patch(facecolor="#FFEAA7", label="맵"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", fontsize=8)
    ax.grid(True, axis="x", alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"reports/figures/xgb_importance_{importance_type}.png", dpi=150)
    plt.show()
```

### 3.2 세 가지 중요도 비교 차트

```python
def plot_importance_comparison(importance_df: pd.DataFrame, top_n: int = 10):
    """
    gain, weight, cover 세 가지 중요도를 나란히 비교.
    """
    top_features = importance_df.head(top_n)["feature"].tolist()
    compare_df = importance_df[importance_df["feature"].isin(top_features)].copy()
    compare_df = compare_df.set_index("feature").loc[top_features]

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    for ax, col, title, color in zip(
        axes,
        ["gain_normalized", "weight_normalized", "cover_normalized"],
        ["Gain (이득)", "Weight (사용 횟수)", "Cover (커버리지)"],
        ["steelblue", "darkorange", "forestgreen"]
    ):
        bars = ax.barh(range(len(compare_df)), compare_df[col], color=color, alpha=0.8)
        ax.set_yticks(range(len(compare_df)))
        ax.set_yticklabels(compare_df.index, fontsize=9)
        ax.invert_yaxis()
        ax.set_title(title, fontweight="bold")
        ax.set_xlabel("정규화 중요도")
        ax.grid(True, axis="x", alpha=0.3)

        for bar, val in zip(bars, compare_df[col]):
            ax.text(bar.get_width() + 0.001, bar.get_y() + bar.get_height()/2,
                    f"{val:.3f}", va="center", fontsize=8)

    plt.suptitle("XGBoost 피처 중요도 비교 (Top 10)", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig("reports/figures/xgb_importance_comparison.png", dpi=150)
    plt.show()
```

### 3.3 SHAP 값 시각화

```python
def plot_shap_values(model, X_test, feature_names, max_samples=500):
    """
    SHAP 값을 사용한 고급 피처 중요도 시각화.

    SHAP vs XGBoost 내장 중요도 차이:
    - SHAP: 게임 이론 기반, 공정한 기여도 분배
    - XGBoost gain: 트리 분기 이득 기반
    - SHAP가 더 신뢰할 수 있는 피처 중요도 제공
    """
    try:
        import shap
    except ImportError:
        print("pip install shap 실행 후 다시 시도하세요")
        return

    # 샘플 제한 (속도)
    if len(X_test) > max_samples:
        X_sample = X_test.sample(max_samples, random_state=42)
    else:
        X_sample = X_test

    # SHAP 계산
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_sample)

    # 1. Summary Plot (전체 중요도)
    plt.figure(figsize=(10, 7))
    shap.summary_plot(
        shap_values, X_sample,
        feature_names=feature_names,
        plot_type="bar",
        show=False
    )
    plt.title("SHAP 피처 중요도 (전체 평균)")
    plt.tight_layout()
    plt.savefig("reports/figures/shap_summary_bar.png", dpi=150)
    plt.show()

    # 2. Beeswarm Plot (방향과 크기 동시 확인)
    plt.figure(figsize=(10, 7))
    shap.summary_plot(
        shap_values, X_sample,
        feature_names=feature_names,
        show=False
    )
    plt.title("SHAP 값 분포 (양수: 승리 기여, 음수: 패배 기여)")
    plt.tight_layout()
    plt.savefig("reports/figures/shap_beeswarm.png", dpi=150)
    plt.show()

    # 3. 개별 예측 설명 (Force Plot)
    print("\n단일 경기 예측 설명 (첫 번째 샘플):")
    shap.force_plot(
        explainer.expected_value,
        shap_values[0],
        X_sample.iloc[0],
        feature_names=feature_names,
        matplotlib=True
    )
    plt.savefig("reports/figures/shap_force_single.png", dpi=150)
    plt.show()
```

---

## 4. 발로란트 도메인 해석

### 4.1 예상 피처 중요도 결과 해석

```
예상 Gain 중요도 순위 (ValoPredictML 기준):

1. controller_diff (0.22): 
   Controller 수 차이가 경기 결과에 가장 결정적
   → 발로란트에서 스모크(연막) 활용이 핵심 전략

2. has_controller_team1 (0.15):
   Controller 보유 여부 (0/1) 자체가 중요
   → Controller 없는 팀의 불리함이 극명

3. initiator_diff (0.13):
   정보 수집 능력 차이 (Sova, Fade 등)
   → 적 위치 파악 → 파이트 주도권

4. map_encoded (0.11):
   맵에 따라 구성 중요도 달라짐
   → Bind: Controller 더 중요 / Breeze: Initiator 더 중요

5. duelist_diff (0.09):
   Duelist 수 차이 (덜 중요)
   → 단순히 Duelist 많다고 이기지 않음
```

### 4.2 피처 중요도 기반 인사이트 도출

```python
def generate_valorant_insights(importance_df: pd.DataFrame) -> list[str]:
    """
    피처 중요도를 발로란트 전략적 인사이트로 변환.
    """
    insights = []
    top_feature = importance_df.iloc[0]["feature"]
    top_importance = importance_df.iloc[0]["gain_normalized"]

    if "controller" in top_feature:
        insights.append(
            f"Controller 관련 피처({top_feature})가 가장 중요 ({top_importance:.1%}) → "
            f"팀 구성 시 Controller 우선 확보 권장"
        )

    diff_features = importance_df[importance_df["feature"].str.contains("diff")]
    count_features = importance_df[~importance_df["feature"].str.contains("diff|has_|map")]

    if diff_features["gain_normalized"].mean() > count_features["gain_normalized"].mean():
        insights.append(
            "차이(diff) 피처가 개별 카운트보다 중요 → 절대적 역할군 수보다 상대 팀 대비 우위가 핵심"
        )

    map_importance = importance_df[importance_df["feature"] == "map_encoded"]["gain_normalized"].values
    if len(map_importance) > 0 and map_importance[0] > 0.08:
        insights.append(
            f"맵 중요도: {map_importance[0]:.1%} → 맵별 최적 구성 데이터 추가 수집 권장"
        )

    return insights
```

---

## 5. 피처 중요도 기반 피처 선택

```python
def select_features_by_importance(
    model: xgb.XGBClassifier,
    feature_names: list[str],
    threshold: float = 0.01
) -> list[str]:
    """
    중요도 임계값 이하 피처 제거.
    ValoPredictML: 43개 피처가 이미 선별되어 있어 제거 최소화.
    """
    importance_df = extract_all_feature_importances(model, feature_names)

    selected = importance_df[
        importance_df["gain_normalized"] >= threshold
    ]["feature"].tolist()

    removed = [f for f in feature_names if f not in selected]

    print(f"선택된 피처 ({len(selected)}개): {selected}")
    print(f"제거된 피처 ({len(removed)}개): {removed}")
    print("\n주의: ValoPredictML은 43개 피처가 도메인 지식으로 선별됨.")
    print("중요도 낮은 피처도 제거 전 도메인 전문가 검토 필요.")
    print("Ablation study(카테고리 단위 제거)로 최종 확인 권장.")

    return selected
```
