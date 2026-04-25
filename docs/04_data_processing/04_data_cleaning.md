# 04. 데이터 클리닝

## 1. 중복 제거

### 1.1 중복 유형

| 유형 | 발생 원인 | 기준 컬럼 |
|---|---|---|
| 완전 중복 | 동일 파일 중복 행 | 전체 컬럼 |
| 경기-요원 중복 | 여러 파일에서 같은 경기 | `match_id` + `team_id` + `agent_name` |

```python
def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)
    
    # 1. 완전 중복 제거
    df = df.drop_duplicates()
    
    # 2. 경기-요원 수준 중복 제거
    df = df.drop_duplicates(subset=["match_id", "team_id", "agent_name"])
    
    after = len(df)
    print(f"중복 제거: {before - after:,}행 제거 ({before:,} → {after:,})")
    return df
```

---

## 2. 결측값 처리

```python
def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    print("결측값 현황:")
    print(df[["match_id", "team_id", "agent_name", "team_won", "map_name"]].isnull().sum())
    
    # 핵심 컬럼 결측 → 행 제거
    critical_cols = ["match_id", "agent_name", "team_won", "map_name"]
    before = len(df)
    df = df.dropna(subset=critical_cols)
    print(f"결측값 제거: {before - len(df):,}행")
    
    # team_id 결측 → match_id 기반 유추 시도
    if df["team_id"].isnull().any():
        df["team_id"] = df.groupby("match_id")["team_id"].transform(
            lambda x: x.fillna(method="ffill")
        )
        df = df.dropna(subset=["team_id"])
    
    return df
```

---

## 3. 신규 요원 및 미지원 요원 처리

새 요원이 추가될 경우 `agent_roles.py` 업데이트 전까지 Unknown으로 처리.

```python
from backend.ml.agent_roles import AGENT_ROLE_MAP

def handle_unknown_agents(df: pd.DataFrame) -> pd.DataFrame:
    known_agents = set(AGENT_ROLE_MAP.keys())
    
    # 알 수 없는 요원 확인
    unknown = df[~df["agent_name"].isin(known_agents)]["agent_name"].unique()
    if len(unknown) > 0:
        print(f"미지원 요원 {len(unknown)}개: {unknown}")
        # 미지원 요원이 포함된 경기 제외 (팀 조합이 불완전)
        invalid_matches = df[df["agent_name"].isin(unknown)]["match_id"].unique()
        before = len(df)
        df = df[~df["match_id"].isin(invalid_matches)]
        print(f"미지원 요원 경기 제외: {before - len(df):,}행")
    
    return df
```

---

## 4. 팀당 요원 수 검증

각 팀은 정확히 5명이어야 한다.

```python
def validate_team_size(df: pd.DataFrame) -> pd.DataFrame:
    # match_id + team_id 기준 요원 수 계산
    team_counts = df.groupby(["match_id", "team_id"])["agent_name"].count()
    
    # 5명이 아닌 팀 식별
    invalid_teams = team_counts[team_counts != 5]
    if len(invalid_teams) > 0:
        invalid_match_ids = invalid_teams.index.get_level_values("match_id").unique()
        print(f"비정상 팀 크기: {len(invalid_match_ids)}개 경기 제외")
        df = df[~df["match_id"].isin(invalid_match_ids)]
    
    return df
```

---

## 5. 라벨 일관성 검사

같은 경기에서 두 팀의 결과가 모순되지 않아야 한다.

```python
def validate_label_consistency(df: pd.DataFrame) -> pd.DataFrame:
    """
    한 경기에서 두 팀만 존재해야 하고,
    하나는 team_won=True, 다른 하나는 team_won=False여야 한다.
    """
    match_results = df.groupby(["match_id", "team_id"])["team_won"].first()
    match_won_counts = match_results.groupby("match_id").sum()
    
    # 승리 팀이 정확히 1개인 경기만 유지
    valid_matches = match_won_counts[match_won_counts == 1].index
    before = len(df)
    df = df[df["match_id"].isin(valid_matches)]
    print(f"라벨 검증: {before - len(df):,}행 제거")
    return df
```

---

## 6. 전체 클리닝 파이프라인

```python
def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df = remove_duplicates(df)
    df = handle_missing_values(df)
    df = handle_unknown_agents(df)
    df = validate_team_size(df)
    df = validate_label_consistency(df)
    
    print(f"\n클리닝 완료: {len(df):,}행")
    return df
```

---

## 7. 클리닝 품질 체크리스트

```
□ 중복 행 0개 확인
□ 필수 컬럼 결측값 0개 확인
□ 모든 요원이 AGENT_ROLE_MAP에 존재
□ 모든 팀의 요원 수 = 5
□ 모든 경기의 승리 팀 = 1개
□ 맵 이름이 유효한 9개 맵 중 하나
□ team_won 컬럼이 bool 타입
```

---

## 8. 관련 문서

| 문서 | 내용 |
|---|---|
| [05_aggregation.md](05_aggregation.md) | 클리닝 후 경기 단위 집계 |
| [../07_data/](../07_data/) | 각 데이터셋 품질 분석 |
