# 04. XGBoost 피처 중요도 분석

마지막 업데이트: 2026-06-04

## 개요

XGBoost가 제공하는 세 가지 피처 중요도(gain, weight, cover)의 차이와 발로란트 도메인 관점에서의 해석, 시각화 코드를 제공한다.

> ★ 현행 프로젝트의 피처 중요도와 자연어 근거는 **`feature_importances_` + importance×value 휴리스틱**을 사용한다(진짜 SHAP 아님). 아래 SHAP 코드(§3.3)는 향후 도입 시 참고용 예시이며, 현재 활성 파이프라인에는 적용되지 않는다.

**피처 중요도 검증 순서** (권장):
1. RF/XGB `feature_importances_` — 훈련 직후 무료. 빠른 전체 윤곽. (현행 활성)
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
    # 전체 179개 피처 목록은 preprocessing.md 7장 참조 (advanced 계약)
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

### 3.3 SHAP 값 시각화 (향후 계획 — 현행 미적용)

> 아래는 향후 도입 시 참고용 예시다. **현행 프로젝트는 진짜 SHAP을 쓰지 않고 `feature_importances_` + importance×value 휴리스틱으로 근거를 만든다.**

```python
def plot_shap_values(model, X_test, feature_names, max_samples=500):
    """
    SHAP 값을 사용한 고급 피처 중요도 시각화 (향후 계획).

    SHAP vs XGBoost 내장 중요도 차이:
    - SHAP: 게임 이론 기반, 공정한 기여도 분배
    - XGBoost gain: 트리 분기 이득 기반
    - SHAP가 더 신뢰할 수 있는 피처 중요도를 제공하지만 계산 비용이 크다.
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

### 4.1 실측 앙상블 피처 중요도 상위 11위

> 출처: `reports/advanced/metrics.json` → `top_features.ensemble` / SSOT `final/deliverables/00_수치_단일진실표.md`
> **앙상블 `feature_importances_` 기준 (SHAP 아님).** RF+XGB+LGBM 가중 soft voting 앙상블 모델의 평균 `feature_importances_` 상위값이다.

| 순위 | 피처명 | 중요도 | 설명 |
|---|---|---:|---|
| 1 | `diff_prior_kd_mean` | 0.1559 | 이전 연도 평균 K/D 비율 팀 간 차이 — **주 신호** |
| 2 | `diff_prior_kd_x_history_coverage` | 0.0804 | K/D × 히스토리 신뢰도 가중 차이 |
| 3 | `diff_prior_games_mean` | 0.0690 | 이전 연도 평균 출전 경기 수 팀 간 차이 |
| 4 | `diff_max_prior_kd` | 0.0295 | 팀 내 최고 K/D 선수 팀 간 차이 |
| 5 | `diff_player_agent_games_mean` | 0.0211 | 선수×요원 조합 히스토리 경험 팀 간 차이 |
| 6 | `diff_low_sample_player_ratio` | 0.0200 | 저표본 선수 비율 팀 간 차이 |
| 7 | `diff_prior_fkpr_mean` | 0.0192 | 이전 연도 평균 FKPR 팀 간 차이 |
| 8 | `diff_prior_adr_mean` | 0.0172 | 이전 연도 평균 ADR 팀 간 차이 |
| 9 | `diff_history_coverage_mean` | 0.0116 | 히스토리 커버리지 평균 팀 간 차이 |
| 10 | `diff_player_agent_kd_mean` | 0.0113 | 선수×요원 조합 K/D 팀 간 차이 |
| **11** | **`diff_agent_map_fit`** | **0.0095** | **요원-맵 적합도 팀 간 차이 — 보조 신호** |

**실측 결과가 시사하는 인사이트**:
- 역할군 카운트(Controller 수 차이 등) 기반의 구성 신호보다 **선수 개인 누적 역량 격차가 훨씬 강력한 예측 신호**임이 확인됐다.
- `diff_agent_map_fit`(요원-맵 적합도)은 11위(0.0095)로, 전략적 구성 지식이 모델에 반영되긴 하나 보조 수준이다.
- 상위권(`diff_prior_kd_x_history_coverage`, `diff_low_sample_player_ratio`)의 "신뢰도" 피처 존재는 선수 히스토리가 부족한 경우 예측 품질이 낮아짐을 모델이 인식한다는 의미다.

### 4.2 피처 중요도 기반 인사이트 도출 (범용 프레임워크)

> **주의**: 아래 코드는 임의의 중요도 DataFrame에 적용 가능한 범용 프레임워크 예시다. 실측 1위는 `diff_prior_kd_mean`(`"controller"`가 아님)이므로, `if "controller" in top_feature` 분기는 현재 모델에서 발동되지 않는다. 실측 인사이트는 §4.1을 참조.

```python
def generate_valorant_insights(importance_df: pd.DataFrame) -> list[str]:
    """
    피처 중요도를 발로란트 전략적 인사이트로 변환 (범용).
    실측 앙상블 기준 인사이트는 docs/05_data_learning/03_advanced_models/02_advanced_metric_analysis.md 참조.
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
    ValoPredictML: 179개 피처(advanced 계약)가 이미 선별되어 있어 제거 최소화.
    """
    importance_df = extract_all_feature_importances(model, feature_names)

    selected = importance_df[
        importance_df["gain_normalized"] >= threshold
    ]["feature"].tolist()

    removed = [f for f in feature_names if f not in selected]

    print(f"선택된 피처 ({len(selected)}개): {selected}")
    print(f"제거된 피처 ({len(removed)}개): {removed}")
    print("\n주의: ValoPredictML은 179개 피처(advanced 계약)가 도메인 지식으로 선별됨.")
    print("중요도 낮은 피처도 제거 전 도메인 전문가 검토 필요.")
    print("Ablation study(카테고리 단위 제거)로 최종 확인 권장.")

    return selected
```
