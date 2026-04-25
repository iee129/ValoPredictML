# 04. 컬럼 정의 및 피처 카탈로그

## 1. 현재 피처 15개 상세 정의

| # | 컬럼명 | 피처 유형 | 범위 | 중요도 | 설명 |
|---|--------|---------|------|--------|------|
| 1 | `a_duelist` | 범주형/수치 | 0~5 | 높음 | 팀 A 듀얼리스트 수 |
| 2 | `a_initiator` | 범주형/수치 | 0~5 | 높음 | 팀 A 이니시에이터 수 |
| 3 | `a_controller` | 범주형/수치 | 0~5 | 매우 높음 | 팀 A 컨트롤러 수 (스모크) |
| 4 | `a_sentinel` | 범주형/수치 | 0~5 | 보통 | 팀 A 센티넬 수 |
| 5 | `b_duelist` | 범주형/수치 | 0~5 | 높음 | 팀 B 듀얼리스트 수 |
| 6 | `b_initiator` | 범주형/수치 | 0~5 | 높음 | 팀 B 이니시에이터 수 |
| 7 | `b_controller` | 범주형/수치 | 0~5 | 매우 높음 | 팀 B 컨트롤러 수 |
| 8 | `b_sentinel` | 범주형/수치 | 0~5 | 보통 | 팀 B 센티넬 수 |
| 9 | `duelist_diff` | diff | -5~5 | 보통 | a_duelist - b_duelist |
| 10 | `initiator_diff` | diff | -5~5 | 보통 | a_initiator - b_initiator |
| 11 | `controller_diff` | diff | -5~5 | 높음 | a_controller - b_controller |
| 12 | `sentinel_diff` | diff | -5~5 | 낮음 | a_sentinel - b_sentinel |
| 13 | `map_encoded` | 범주형 | 0~11 | 매우 높음 | 맵 이름 LabelEncoded |
| 14 | `has_controller_a` | 이진 | 0 or 1 | 높음 | 팀 A에 Controller ≥1 |
| 15 | `has_controller_b` | 이진 | 0 or 1 | 높음 | 팀 B에 Controller ≥1 |

---

## 2. 추가 예정 피처 (Phase 2 목표: 30+ 피처)

### 2.1 요원 원-핫 인코딩 (27종 × 2팀 = 54개)

```python
# 각 요원의 존재 여부를 이진 피처로 표현
# 예: a_jett, a_sova, a_viper, b_jett, b_sova, ...
# 기대 효과: +3~5%p 정확도 향상

ALL_AGENTS = list(AGENT_ROLE_MAP.keys())  # 27종

def add_agent_onehot(df: pd.DataFrame) -> pd.DataFrame:
    for agent in ALL_AGENTS:
        normalized = agent.lower().replace("/", "_").replace(" ", "_")
        df[f"a_{normalized}"] = df["team_a_agents"].apply(
            lambda x: 1 if agent in str(x).split(",") else 0
        )
        df[f"b_{normalized}"] = df["team_b_agents"].apply(
            lambda x: 1 if agent in str(x).split(",") else 0
        )
    return df
```

### 2.2 맵 × 역할군 상호작용 피처 (48개)

```python
# 맵별 역할군 중요도가 다름 → 상호작용 피처
# 예: map_controller_a = map_encoded × a_controller (수치적 상호작용)
# 또는 map_ascent_a_controller = map이 Ascent AND 팀 A controller ≥1

def add_map_role_interactions(df: pd.DataFrame) -> pd.DataFrame:
    """맵 × 역할군 이진 상호작용 피처"""
    for map_name in VALID_MAPS:
        map_flag = (df["map"] == map_name).astype(int)
        for role in ["duelist", "initiator", "controller", "sentinel"]:
            df[f"map_{map_name.lower()}_a_{role}"] = map_flag * df[f"a_{role}"]
            df[f"map_{map_name.lower()}_b_{role}"] = map_flag * df[f"b_{role}"]
    return df
```

### 2.3 패치 버전 피처 (1개)

```python
# 패치 버전 숫자화
# "release-08.02.00.xxx" → 8.02
def patch_to_float(game_version: str) -> float:
    try:
        parts = game_version.replace("release-", "").split(".")
        return float(f"{parts[0]}.{parts[1]}")
    except:
        return 0.0

# df["patch_version"] = df["game_version"].apply(patch_to_float)
```

### 2.4 조합 다양성 피처 (2개)

```python
# 역할군 다양성 점수 (섀넌 엔트로피)
import numpy as np

def composition_entropy(role_counts: list[int]) -> float:
    """조합 다양성 = 섀넌 엔트로피 (균형 잡힌 조합 = 높은 점수)"""
    total = sum(role_counts)
    if total == 0:
        return 0.0
    probs = [c / total for c in role_counts if c > 0]
    return -sum(p * np.log2(p) for p in probs)

# df["comp_entropy_a"] = df[["a_duelist","a_initiator","a_controller","a_sentinel"]].apply(
#     lambda row: composition_entropy(row.values), axis=1
# )
```

---

## 3. 피처 우선순위 로드맵

| 단계 | 추가 피처 | 피처 수 증가 | 기대 정확도 향상 |
|------|---------|----------|--------------|
| 현재 | 기본 역할군 카운트 + diff + 맵 | 15개 | 기준선 (~67-72%) |
| Phase 1 | 요원 원-핫 인코딩 | +54개 (총 69개) | +3~5%p |
| Phase 2 | 맵×역할군 상호작용 | +48개 (총 117개) | +1~2%p |
| Phase 3 | 패치 버전 + 다양성 | +3개 (총 120개) | +1~2%p |
| **목표** | | **~120개 피처** | **~80%+** |

---

## 4. 피처 선택 (Feature Selection)

과적합 방지를 위해 120개 피처에서 30~50개 선택:

```python
from sklearn.feature_selection import SelectKBest, f_classif
from xgboost import XGBClassifier
import numpy as np

def select_features_xgb(X: pd.DataFrame, y: pd.Series, top_k: int = 30) -> list[str]:
    """XGBoost 피처 중요도 기반 상위 k개 선택"""
    model = XGBClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)
    
    importance = pd.Series(model.feature_importances_, index=X.columns)
    top_features = importance.nlargest(top_k).index.tolist()
    
    print(f"[INFO] 선택된 피처 ({top_k}개):")
    for feat in top_features:
        print(f"  {feat}: {importance[feat]:.4f}")
    
    return top_features
```

---

## 5. 피처 변환 파이프라인

```python
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

def build_feature_pipeline(feature_cols: list[str]) -> Pipeline:
    """피처 변환 파이프라인"""
    return Pipeline([
        # 역할군 카운트 피처는 스케일링 불필요 (트리 기반 모델)
        # 원-핫 피처는 이미 0/1 → 스케일링 선택적
        ("passthrough", "passthrough"),
    ])
    # XGBoost/LightGBM은 스케일링 불필요
    # 신경망 추가 시 StandardScaler 적용
```
