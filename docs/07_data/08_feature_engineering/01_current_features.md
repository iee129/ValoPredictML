# 01. 현재 피처 엔지니어링 (15개)

## 1. 현재 피처 파이프라인 전체 흐름

```
원본 경기 데이터
    │ (플레이어 단위 행)
    ▼
집계 (match_level_aggregation)
    │ (경기 단위 행)
    ▼
역할군 카운트 피처 (8개)
    │
    ▼
Diff 피처 (4개)
    │
    ▼
맵 인코딩 (1개)
    │
    ▼
이진 피처 (2개)
    │
    ▼
최종 피처 벡터 (15개)
```

---

## 2. 피처 생성 코드 (현재 구현)

### 2.1 경기 단위 집계

```python
import pandas as pd
from typing import Optional

AGENT_ROLE_MAP = {
    "Jett": "Duelist", "Reyna": "Duelist", "Phoenix": "Duelist",
    "Raze": "Duelist", "Yoru": "Duelist", "Neon": "Duelist",
    "ISO": "Duelist", "Waylay": "Duelist",
    "Sova": "Initiator", "Breach": "Initiator", "Skye": "Initiator",
    "KAY/O": "Initiator", "Fade": "Initiator", "Gekko": "Initiator",
    "Tejo": "Initiator",
    "Viper": "Controller", "Omen": "Controller", "Brimstone": "Controller",
    "Astra": "Controller", "Harbor": "Controller", "Clove": "Controller",
    "Killjoy": "Sentinel", "Cypher": "Sentinel", "Sage": "Sentinel",
    "Chamber": "Sentinel", "Deadlock": "Sentinel", "Vyse": "Sentinel",
}

def aggregate_to_match_level(df_player: pd.DataFrame) -> pd.DataFrame:
    """
    플레이어 단위 DataFrame → 경기 단위 DataFrame 집계
    
    입력 컬럼 필수: match_id, map, team_a, team_b, team (선수 소속), agent, winner
    """
    records = []
    
    for match_id, group in df_player.groupby("match_id"):
        maps = group["map"].unique()
        for map_name in maps:
            map_group = group[group["map"] == map_name]
            
            team_a = map_group["team_a"].iloc[0]
            team_b = map_group["team_b"].iloc[0]
            
            team_a_agents = map_group[map_group["team"] == team_a]["agent"].tolist()
            team_b_agents = map_group[map_group["team"] == team_b]["agent"].tolist()
            
            winner = map_group["winner"].iloc[0]
            label = 1 if winner == team_a else 0
            
            records.append({
                "match_id": f"{match_id}_{map_name}",
                "map": map_name,
                "team_a": team_a,
                "team_b": team_b,
                "team_a_agents": ",".join(team_a_agents),
                "team_b_agents": ",".join(team_b_agents),
                "label": label,
            })
    
    return pd.DataFrame(records)
```

### 2.2 역할군 카운트 피처 (8개)

```python
def add_role_count_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    team_a_agents, team_b_agents 컬럼 → 역할군 카운트 8개 피처
    """
    for prefix, agents_col in [("a", "team_a_agents"), ("b", "team_b_agents")]:
        for role in ["duelist", "initiator", "controller", "sentinel"]:
            df[f"{prefix}_{role}"] = df[agents_col].apply(
                lambda x: sum(1 for a in str(x).split(",")
                              if AGENT_ROLE_MAP.get(a.strip(), "").lower() == role)
            )
    return df
```

### 2.3 Diff 피처 (4개)

```python
def add_diff_features(df: pd.DataFrame) -> pd.DataFrame:
    """역할군 카운트 → diff 피처 4개 추가"""
    for role in ["duelist", "initiator", "controller", "sentinel"]:
        df[f"{role}_diff"] = df[f"a_{role}"] - df[f"b_{role}"]
    return df
```

### 2.4 맵 인코딩 (1개)

```python
from sklearn.preprocessing import LabelEncoder

VALID_MAPS = [
    "Ascent", "Bind", "Breeze", "Drift", "Fracture", "Haven",
    "Icebox", "Lotus", "Pearl", "Split", "Sunset", "Abyss",
]

def add_map_encoding(df: pd.DataFrame) -> tuple[pd.DataFrame, LabelEncoder]:
    """맵 이름 → 정수 인코딩"""
    le = LabelEncoder()
    le.fit(VALID_MAPS)
    
    df["map_encoded"] = df["map"].apply(
        lambda x: le.transform([x])[0] if x in VALID_MAPS else -1
    )
    # 인코딩 실패(맵 미인식) 행 제거
    df = df[df["map_encoded"] >= 0].reset_index(drop=True)
    return df, le
```

### 2.5 이진 피처 (2개)

```python
def add_binary_features(df: pd.DataFrame) -> pd.DataFrame:
    """Controller 보유 여부 이진 피처"""
    df["has_controller_a"] = (df["a_controller"] >= 1).astype(int)
    df["has_controller_b"] = (df["b_controller"] >= 1).astype(int)
    return df
```

---

## 3. 전체 파이프라인 실행

```python
def build_features(df_player: pd.DataFrame) -> tuple[pd.DataFrame, LabelEncoder]:
    """전체 피처 엔지니어링 파이프라인"""
    print("[STEP 1] 경기 단위 집계...")
    df = aggregate_to_match_level(df_player)
    
    print("[STEP 2] 역할군 카운트 피처...")
    df = add_role_count_features(df)
    
    print("[STEP 3] Diff 피처...")
    df = add_diff_features(df)
    
    print("[STEP 4] 맵 인코딩...")
    df, le = add_map_encoding(df)
    
    print("[STEP 5] 이진 피처...")
    df = add_binary_features(df)
    
    print(f"[INFO] 최종 데이터: {len(df)} 경기, 15개 피처")
    return df, le

FEATURE_COLUMNS = [
    "a_duelist", "a_initiator", "a_controller", "a_sentinel",
    "b_duelist", "b_initiator", "b_controller", "b_sentinel",
    "duelist_diff", "initiator_diff", "controller_diff", "sentinel_diff",
    "map_encoded",
    "has_controller_a", "has_controller_b",
]
```

---

## 4. 피처 분포 검증

```python
import matplotlib.pyplot as plt

def check_feature_distributions(df: pd.DataFrame):
    """피처별 분포 통계 출력"""
    print("\n=== 피처 분포 ===")
    print(df[FEATURE_COLUMNS].describe())
    
    print("\n=== 레이블 분포 ===")
    print(df["label"].value_counts(normalize=True))
    
    print("\n=== 맵 분포 ===")
    print(df["map"].value_counts())
    
    print("\n=== 역할군 카운트 (팀 A) ===")
    print(df[["a_duelist", "a_initiator", "a_controller", "a_sentinel"]].mean())
```

---

## 5. 알려진 피처 한계

| 한계 | 영향 | 해결 방법 |
|------|------|---------|
| 같은 역할군 카운트라도 요원이 다름 | 피처가 너무 거칠음 | 요원 원-핫 인코딩 (08-02) |
| 맵 인코딩이 순서 없는 LabelEncoding | 트리 기반 모델에서 OK, 선형 모델에서 문제 | OneHotEncoding 또는 유지 |
| Controller 보유 이진은 수 고려 안 함 | 2 Controller vs 1 Controller 구분 안 됨 | controller_diff로 보완됨 |
| 데이터 크기 (~2,000경기) 부족 | 일반화 어려움 | 데이터 수집 확장 |
