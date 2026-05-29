# 02. 추가 피처 설계

마지막 업데이트: 2026-05-04

> 본 문서는 추후 확장 가능한 피처 후보를 기록한다. 현재 구현 피처 수: baseline 178개 / advanced 125개 (초기 설계 기준선 43개와 다름).
> Team_Shared_Exp는 visualize25 데이터셋 보류로 미구현 — 추가 시 44개.

## 1. 목표

초기 설계 기준선 15개 피처 (참고용) 기준 피처 확장 계획. 실제 파이프라인은 baseline 178피처 / advanced 125피처 구현 완료.

| 피처 그룹 | 현재 | 목표 | 기대 효과 |
|---------|------|------|---------|
| 역할군 카운트 | 8개 | 8개 (유지) | - |
| Diff | 4개 | 4개 (유지) | - |
| 맵 | 1개 | 13개 | +1~2%p |
| 이진 피처 | 2개 | 6개 | +0.5%p |
| **요원 원-핫** | 0개 | 54개 | **+3~5%p** |
| 맵×역할군 상호작용 | 0개 | 24개 | +1~2%p |
| 패치/메타 | 0개 | 2개 | +1%p |
| 조합 품질 | 0개 | 4개 | +0.5%p |
| **총계** | **초기 설계 기준선 15개** | **~115개** | **+6~11%p** |

---

## 2. 요원 원-핫 인코딩 (54개, 가장 중요)

```python
from typing import Optional

ALL_AGENTS_SORTED = sorted([
    "Astra", "Breach", "Brimstone", "Chamber", "Clove", "Cypher",
    "Deadlock", "Fade", "Gekko", "Harbor", "ISO", "Jett", "KAY/O",
    "Killjoy", "Lotus", "Neon", "Omen", "Phoenix", "Raze", "Reyna",
    "Sage", "Skye", "Sova", "Tejo", "Viper", "Vyse", "Waylay", "Yoru",
])
# 실제 요원 27종 (Lotus 제외, 맵명과 혼동 주의)

PLAYABLE_AGENTS_SORTED = sorted([
    "Astra", "Breach", "Brimstone", "Chamber", "Clove", "Cypher",
    "Deadlock", "Fade", "Gekko", "Harbor", "ISO", "Jett", "KAY/O",
    "Killjoy", "Neon", "Omen", "Phoenix", "Raze", "Reyna",
    "Sage", "Skye", "Sova", "Tejo", "Viper", "Vyse", "Waylay", "Yoru",
])  # 27종

def add_agent_onehot_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    team_a_agents / team_b_agents → 요원별 원-핫 인코딩
    총 54개 피처 추가 (27 × 2팀)
    """
    for team_prefix, agents_col in [("a", "team_a_agents"), ("b", "team_b_agents")]:
        agents_list = df[agents_col].apply(
            lambda x: [a.strip() for a in str(x).split(",")]
        )
        for agent in PLAYABLE_AGENTS_SORTED:
            col_name = f"{team_prefix}_{agent.lower().replace('/', '_').replace(' ', '_')}"
            df[col_name] = agents_list.apply(lambda agents: int(agent in agents))
    
    return df

# 생성 피처 예시:
# a_jett, a_sova, a_viper, a_omen, a_killjoy (팀 A 요원 여부)
# b_jett, b_sova, b_viper, b_omen, b_killjoy (팀 B 요원 여부)
```

---

## 3. 맵 원-핫 인코딩 (12개)

```python
VALID_MAPS = [
    "Ascent", "Bind", "Breeze", "Drift", "Fracture", "Haven",
    "Icebox", "Lotus", "Pearl", "Split", "Sunset", "Abyss",
]

def add_map_onehot_features(df: pd.DataFrame) -> pd.DataFrame:
    """맵 이름 → 원-핫 인코딩 (LabelEncoding 대체 또는 병행)"""
    for map_name in VALID_MAPS:
        col_name = f"map_{map_name.lower()}"
        df[col_name] = (df["map"] == map_name).astype(int)
    return df
```

---

## 4. 맵 × 역할군 상호작용 피처 (24개)

```python
# 가장 정보가 많은 맵 × 역할군 조합만 선택 (24개)
# = 맵 12개 × 2팀 × 역할군 중 Controller만 (Controller이 맵에 따라 가장 중요)

MAP_ROLE_INTERACTIONS = [
    ("controller", "Ascent"), ("controller", "Bind"), ("controller", "Breeze"),
    ("controller", "Fracture"), ("controller", "Haven"), ("controller", "Icebox"),
    ("controller", "Lotus"), ("controller", "Pearl"), ("controller", "Split"),
    ("controller", "Sunset"), ("controller", "Abyss"), ("controller", "Drift"),
]

def add_map_role_interaction_features(df: pd.DataFrame) -> pd.DataFrame:
    """맵 × 역할군 상호작용 이진 피처"""
    for role, map_name in MAP_ROLE_INTERACTIONS:
        is_map = (df["map"] == map_name).astype(int)
        df[f"map_{map_name.lower()}_has_{role}_a"] = is_map * (df[f"a_{role}"] >= 1).astype(int)
        df[f"map_{map_name.lower()}_has_{role}_b"] = is_map * (df[f"b_{role}"] >= 1).astype(int)
    return df
```

---

## 5. 패치 버전 피처 (2개)

```python
import numpy as np

def add_patch_features(df: pd.DataFrame) -> pd.DataFrame:
    """패치 버전 수치화 + 주요 메타 변화 이진 피처"""
    
    def patch_to_float(version: str) -> float:
        try:
            clean = version.replace("release-", "").replace("Release-", "")
            parts = clean.split(".")
            return float(f"{parts[0]}.{int(parts[1]):02d}")
        except:
            return 0.0
    
    if "game_version" in df.columns:
        df["patch_version"] = df["game_version"].apply(patch_to_float)
        # Clove 출시 이후 여부 (EP 8.02 = 8.02)
        df["is_clove_era"] = (df["patch_version"] >= 8.02).astype(int)
    else:
        df["patch_version"] = 0.0
        df["is_clove_era"] = 0
    
    return df
```

---

## 6. 조합 품질 피처 (4개)

```python
def add_composition_quality_features(df: pd.DataFrame) -> pd.DataFrame:
    """팀 조합 품질 관련 파생 피처"""
    
    # 1. 조합 다양성 (섀넌 엔트로피)
    def entropy(counts: list[int]) -> float:
        total = sum(counts)
        if total == 0:
            return 0.0
        probs = [c/total for c in counts if c > 0]
        return -sum(p * np.log2(p) for p in probs)
    
    df["comp_entropy_a"] = df[["a_duelist","a_initiator","a_controller","a_sentinel"]].apply(
        lambda row: entropy(row.values.tolist()), axis=1
    )
    df["comp_entropy_b"] = df[["b_duelist","b_initiator","b_controller","b_sentinel"]].apply(
        lambda row: entropy(row.values.tolist()), axis=1
    )
    
    # 2. 균형 조합 여부 (각 역할군 1~2개씩)
    def is_balanced(d, i, c, s) -> int:
        return int(all(1 <= x <= 2 for x in [d, i, c, s]))
    
    df["balanced_comp_a"] = df.apply(
        lambda row: is_balanced(row.a_duelist, row.a_initiator, row.a_controller, row.a_sentinel),
        axis=1
    )
    df["balanced_comp_b"] = df.apply(
        lambda row: is_balanced(row.b_duelist, row.b_initiator, row.b_controller, row.b_sentinel),
        axis=1
    )
    
    return df
```

---

## 7. 추가 이진 피처 (4개 추가)

```python
def add_extended_binary_features(df: pd.DataFrame) -> pd.DataFrame:
    """현재 2개에서 6개로 확장"""
    # 이미 있음
    # has_controller_a, has_controller_b
    
    # 더블 Controller 여부
    df["double_controller_a"] = (df["a_controller"] >= 2).astype(int)
    df["double_controller_b"] = (df["b_controller"] >= 2).astype(int)
    
    # Controller 없음
    df["no_controller_a"] = (df["a_controller"] == 0).astype(int)
    df["no_controller_b"] = (df["b_controller"] == 0).astype(int)
    
    return df
```

---

## 8. 전체 확장 파이프라인

```python
def build_extended_features(df_match: pd.DataFrame) -> pd.DataFrame:
    """확장 피처 파이프라인 (30+ 피처)"""
    df = df_match.copy()
    
    # 초기 설계 기준선 15개 피처 (실제 구현은 178/125피처 — 참고용 스펙)
    df = add_agent_onehot_features(df)        # +54
    df = add_map_onehot_features(df)          # +12
    df = add_map_role_interaction_features(df) # +24
    df = add_patch_features(df)               # +2
    df = add_composition_quality_features(df) # +4
    df = add_extended_binary_features(df)     # +4
    
    total = 15 + 54 + 12 + 24 + 2 + 4 + 4
    print(f"[INFO] 총 피처: {total}개")  # 115개
    
    return df
```
