# 02. 데이터 검증 규칙

마지막 업데이트: 2026-05-04

> 품질 검사 기준: [01_quality_metrics.md](./01_quality_metrics.md)

## 1. 검증 규칙 카탈로그

| ID | 규칙명 | 심각도 | 자동 수정 |
|----|-------|--------|---------|
| V001 | 역할군 합계 = 5 | Critical | 가능 (필터링) |
| V002 | 요원 이름 유효성 | Critical | 가능 (정규화) |
| V003 | 맵 이름 유효성 | Critical | 가능 (정규화) |
| V004 | 레이블 0/1 여부 | Critical | 가능 (필터링) |
| V005 | match_id 중복 | High | 가능 (중복 제거) |
| V006 | Diff 피처 정합성 | Medium | 가능 (재계산) |
| V007 | 레이블 균형 | Low | 불가 (데이터 수집) |
| V008 | 맵 분포 균형 | Low | 불가 (데이터 수집) |

---

## 2. 핵심 검증 구현

### V001: 역할군 합계 = 5

```python
import pandas as pd

def validate_role_sum(df: pd.DataFrame, fix: bool = True) -> tuple[pd.DataFrame, int]:
    """
    각 팀의 역할군 합계가 정확히 5여야 함.
    fix=True: 오류 행 제거 (학습 데이터 오염 방지)
    """
    role_cols_a = ["a_duelist", "a_initiator", "a_controller", "a_sentinel"]
    role_cols_b = ["b_duelist", "b_initiator", "b_controller", "b_sentinel"]
    
    sum_a = df[role_cols_a].sum(axis=1)
    sum_b = df[role_cols_b].sum(axis=1)
    
    valid_mask = (sum_a == 5) & (sum_b == 5)
    invalid_count = (~valid_mask).sum()
    
    if invalid_count > 0:
        print(f"[V001] 역할군 합계 오류: {invalid_count}행")
        if fix:
            df = df[valid_mask].reset_index(drop=True)
            print(f"[V001] 오류 행 제거 완료. 남은 행: {len(df):,}")
    
    return df, int(invalid_count)
```

### V002: 요원 이름 유효성

```python
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
VALID_AGENTS = set(AGENT_ROLE_MAP.keys())

AGENT_NAME_ALIASES = {
    "kayo": "KAY/O", "kay/o": "KAY/O", "kay_o": "KAY/O", "kayo/": "KAY/O",
    "yoru": "Yoru", "neon": "Neon", "iso": "ISO",
    "clove": "Clove", "deadlock": "Deadlock", "vyse": "Vyse",
    "tejo": "Tejo", "waylay": "Waylay",
}

def normalize_agent_name(name: str) -> str:
    """요원 이름 정규화 (대소문자 + 표기 변형 처리)"""
    if not name or pd.isna(name):
        return ""
    name = str(name).strip()
    # 이미 정확한 이름이면 그대로
    if name in VALID_AGENTS:
        return name
    # 소문자 별칭 확인
    lower = name.lower().replace("-", "/")
    if lower in AGENT_NAME_ALIASES:
        return AGENT_NAME_ALIASES[lower]
    # Title Case 시도
    title = name.title()
    if title in VALID_AGENTS:
        return title
    # KAY/O 특수 처리
    if "kay" in lower and "o" in lower:
        return "KAY/O"
    return name  # 정규화 실패 → 원본 반환

def validate_agent_names(df: pd.DataFrame, fix: bool = True) -> tuple[pd.DataFrame, set]:
    """요원 이름 유효성 검사 및 정규화"""
    unknown_agents = set()
    
    for col in ["team_a_agents", "team_b_agents"]:
        if col not in df.columns:
            continue
        
        if fix:
            df[col] = df[col].apply(
                lambda x: ",".join(
                    normalize_agent_name(a) for a in str(x).split(",")
                ) if pd.notna(x) else x
            )
        
        # 정규화 후 미인식 요원 수집
        for agents_str in df[col].dropna():
            for agent in agents_str.split(","):
                agent = agent.strip()
                if agent and agent not in VALID_AGENTS:
                    unknown_agents.add(agent)
    
    if unknown_agents:
        print(f"[V002] 미인식 요원 {len(unknown_agents)}개: {sorted(unknown_agents)}")
    
    return df, unknown_agents
```

### V003: 맵 이름 유효성

```python
VALID_MAPS = {
    "Ascent", "Bind", "Breeze", "Drift", "Fracture", "Haven",
    "Icebox", "Lotus", "Pearl", "Split", "Sunset", "Abyss",
    "Corrode",
}

MAP_ALIASES = {
    "ascent": "Ascent", "bind": "Bind", "breeze": "Breeze",
    "drift": "Drift", "fracture": "Fracture", "haven": "Haven",
    "icebox": "Icebox", "lotus": "Lotus", "pearl": "Pearl",
    "split": "Split", "sunset": "Sunset", "abyss": "Abyss",
    "corrode": "Corrode",
    # Riot API 경로 형식
    "/game/maps/ascent": "Ascent",
    "/game/maps/bonsai": "Split",
    "/game/maps/canyon": "Fracture",
    "/game/maps/foxtrot": "Bind",
    "/game/maps/triad": "Haven",
    "/game/maps/port": "Icebox",
    "/game/maps/pitt": "Pearl",
    "/game/maps/jam": "Lotus",
    "/game/maps/juliett": "Sunset",
    "/game/maps/infinity": "Abyss",
    "/game/maps/outpost": "Drift",
}

def normalize_map_name(map_name: str) -> Optional[str]:
    """맵 이름 정규화"""
    if pd.isna(map_name):
        return None
    name = str(map_name).strip()
    if name in VALID_MAPS:
        return name
    lower = name.lower()
    if lower in MAP_ALIASES:
        return MAP_ALIASES[lower]
    return None  # 정규화 실패

def validate_map_names(df: pd.DataFrame, fix: bool = True) -> tuple[pd.DataFrame, set]:
    """맵 이름 유효성 검사 및 정규화"""
    if "map" not in df.columns:
        return df, set()
    
    if fix:
        df["map"] = df["map"].apply(normalize_map_name)
        before = len(df)
        df = df.dropna(subset=["map"]).reset_index(drop=True)
        removed = before - len(df)
        if removed > 0:
            print(f"[V003] 미인식 맵으로 {removed}행 제거")
    
    invalid_maps = set(df["map"].unique()) - VALID_MAPS
    return df, invalid_maps
```

### V004: 레이블 유효성

```python
def validate_labels(df: pd.DataFrame, fix: bool = True) -> tuple[pd.DataFrame, int]:
    """레이블이 0 또는 1인지 검사"""
    if "label" not in df.columns:
        return df, 0
    
    invalid_mask = ~df["label"].isin([0, 1])
    invalid_count = invalid_mask.sum()
    
    if invalid_count > 0:
        print(f"[V004] 유효하지 않은 레이블: {invalid_count}행")
        print(f"  값 분포: {df.loc[invalid_mask, 'label'].value_counts().to_dict()}")
        if fix:
            df = df[~invalid_mask].reset_index(drop=True)
    
    return df, int(invalid_count)
```

### V005: match_id 중복 제거

```python
def validate_duplicates(df: pd.DataFrame, fix: bool = True) -> tuple[pd.DataFrame, int]:
    """match_id 기반 중복 제거"""
    if "match_id" not in df.columns:
        return df, 0
    
    dup_count = df.duplicated(subset=["match_id"]).sum()
    
    if dup_count > 0:
        print(f"[V005] match_id 중복: {dup_count}행")
        if fix:
            df = df.drop_duplicates(subset=["match_id"]).reset_index(drop=True)
    
    # 조합+맵 기반 2차 중복 제거
    combo_cols = ["team_a_agents", "team_b_agents", "map", "label"]
    available = [c for c in combo_cols if c in df.columns]
    combo_dups = df.duplicated(subset=available).sum() if available else 0
    
    if combo_dups > 0:
        print(f"[V005] 조합+맵 중복: {combo_dups}행 (소스 가중치 기준 유지)")
    
    return df, int(dup_count)
```

---

## 3. 전체 검증 파이프라인

```python
def run_all_validations(df: pd.DataFrame, fix: bool = True) -> pd.DataFrame:
    """모든 검증 규칙 순차 실행"""
    original_len = len(df)
    errors = {}
    
    df, unknown_agents = validate_agent_names(df, fix=fix)
    errors["V002_unknown_agents"] = len(unknown_agents)
    
    df, invalid_maps = validate_map_names(df, fix=fix)
    errors["V003_invalid_maps"] = len(invalid_maps)
    
    df, v004_err = validate_labels(df, fix=fix)
    errors["V004_label_errors"] = v004_err
    
    df, v005_err = validate_duplicates(df, fix=fix)
    errors["V005_duplicates"] = v005_err
    
    # 피처 컬럼이 있을 때만 실행
    if "a_duelist" in df.columns:
        df, v006_err = validate_diff_features(df, fix=fix)
        errors["V006_diff_errors"] = v006_err
        
        df, v001_err = validate_role_sum(df, fix=fix)
        errors["V001_role_sum_errors"] = v001_err
    
    removed = original_len - len(df)
    print(f"\n[검증 완료] {original_len:,} → {len(df):,}행 (제거: {removed:,}행)")
    print(f"[오류 요약] {errors}")
    
    return df
```
