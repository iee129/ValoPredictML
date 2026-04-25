# 06. 피처 엔지니어링

## 1. 피처 설계 철학

- **도메인 지식 기반**: 발로란트의 역할군 메타(Controller 필수 등)를 반영
- **단순성**: 요원 원핫인코딩 (28개) 대신 역할군 카운트 (4개) 사용
  → 데이터 희소성 문제 해결, 신규 요원 추가 시 재학습 불필요
- **대칭성**: 팀 A/B 각각 동일한 피처 구조로 비교 가능하게 설계

---

## 2. 15개 피처 상세

### 2.1 역할군 카운트 (8개)

각 팀에서 4개 역할군(Duelist, Initiator, Controller, Sentinel)의 요원 수.

```python
ROLES = ["Duelist", "Initiator", "Controller", "Sentinel"]

def get_role_counts(agents: list[str]) -> dict[str, int]:
    counts = {role: 0 for role in ROLES}
    for agent in agents:
        role = AGENT_ROLE_MAP.get(agent, "Unknown")
        if role in counts:
            counts[role] += 1
    return counts
```

| 피처명 | 범위 | 예시 |
|---|---|---|
| `team_a_duelist_count` | 0~5 | 2 |
| `team_a_initiator_count` | 0~5 | 1 |
| `team_a_controller_count` | 0~5 | 1 |
| `team_a_sentinel_count` | 0~5 | 1 |
| `team_b_duelist_count` | 0~5 | 1 |
| `team_b_initiator_count` | 0~5 | 2 |
| `team_b_controller_count` | 0~5 | 1 |
| `team_b_sentinel_count` | 0~5 | 1 |

### 2.2 역할군 차이 (diff) 피처 (4개)

두 팀 간 역할군 구성의 차이. 양수 = 팀 A가 더 많음.

```python
for role in ROLES:
    features[f"{role.lower()}_diff"] = (
        a_counts[role] - b_counts[role]
    )
```

| 피처명 | 범위 | 해석 |
|---|---|---|
| `duelist_diff` | -5 ~ +5 | +2 = 팀 A Duelist 2명 더 많음 |
| `initiator_diff` | -5 ~ +5 | — |
| `controller_diff` | -5 ~ +5 | — |
| `sentinel_diff` | -5 ~ +5 | — |

### 2.3 Controller 보유 여부 (2개)

Controller가 없는 팀은 스모크 능력 부재로 불리한 경우가 많다.

```python
features["team_a_has_controller"] = int(a_counts["Controller"] >= 1)
features["team_b_has_controller"] = int(b_counts["Controller"] >= 1)
```

| 피처명 | 범위 | 해석 |
|---|---|---|
| `team_a_has_controller` | 0 or 1 | 1 = 팀 A에 Controller 있음 |
| `team_b_has_controller` | 0 or 1 | — |

### 2.4 맵 인코딩 (1개)

맵에 따라 최적 역할군 구성이 달라지므로 맵 정보를 피처로 포함.

```python
from sklearn.preprocessing import LabelEncoder
import joblib

le = LabelEncoder()
le.fit(["Ascent", "Bind", "Fracture", "Haven", "Lotus", "Pearl", "Split", "Sunset", "Abyss"])
joblib.dump(le, "models/label_encoder_map.joblib")

features["map_encoded"] = le.transform([map_name])[0]
```

| 피처명 | 범위 | 인코딩 |
|---|---|---|
| `map_encoded` | 0~8 | Abyss=0, Ascent=1, ..., Sunset=8 (알파벳 순) |

---

## 3. 전체 피처 생성 함수

```python
import pandas as pd
import numpy as np
from backend.ml.agent_roles import AGENT_ROLE_MAP

ROLES = ["Duelist", "Initiator", "Controller", "Sentinel"]
FEATURE_COLS = [
    "team_a_duelist_count", "team_a_initiator_count",
    "team_a_controller_count", "team_a_sentinel_count",
    "team_b_duelist_count", "team_b_initiator_count",
    "team_b_controller_count", "team_b_sentinel_count",
    "duelist_diff", "initiator_diff", "controller_diff", "sentinel_diff",
    "team_a_has_controller", "team_b_has_controller",
    "map_encoded",
]

def create_features(
    team_a: list[str],
    team_b: list[str],
    map_name: str,
    le_map
) -> pd.Series:
    a_counts = get_role_counts(team_a)
    b_counts = get_role_counts(team_b)

    features = {}
    for role in ROLES:
        role_lower = role.lower()
        features[f"team_a_{role_lower}_count"] = a_counts[role]
        features[f"team_b_{role_lower}_count"] = b_counts[role]
        features[f"{role_lower}_diff"] = a_counts[role] - b_counts[role]

    features["team_a_has_controller"] = int(a_counts["Controller"] >= 1)
    features["team_b_has_controller"] = int(b_counts["Controller"] >= 1)
    features["map_encoded"] = le_map.transform([map_name])[0]

    return pd.Series(features)

def create_features_batch(df: pd.DataFrame, le_map) -> pd.DataFrame:
    """경기 단위 DataFrame에서 일괄 피처 생성"""
    feature_rows = df.apply(
        lambda row: create_features(row["team_a"], row["team_b"], row["map_name"], le_map),
        axis=1
    )
    return pd.concat([df[["match_id", "label"]], feature_rows], axis=1)
```

---

## 4. 피처 중요도 사전 예상

도메인 지식 기반 예상 중요도 순위:

1. `controller_diff` — 스모크/유틸리티 격차
2. `team_a_has_controller` — Controller 유무
3. `map_encoded` — 맵별 메타 차이
4. `duelist_diff` — 공격력 격차
5. `initiator_diff` — 정보력/돌파력 격차

실제 XGBoost feature_importances로 검증 예정.

---

## 5. 관련 문서

| 문서 | 내용 |
|---|---|
| [07_split_and_validation.md](07_split_and_validation.md) | 피처 완성 후 데이터 분할 |
| [../05_data_learning/01_model_strategy.md](../05_data_learning/01_model_strategy.md) | 모델이 이 피처를 사용하는 방식 |
