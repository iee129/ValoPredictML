# 05. 경기 단위 집계

## 1. 집계 필요성

원본 데이터는 **플레이어 단위** (1행 = 1명의 플레이어 통계)이다.  
모델 학습을 위해 **경기 단위** (1행 = 1경기, 양 팀 요원 포함)로 변환해야 한다.

```
원본 데이터 (플레이어 단위):
match_id | team_id | agent_name | team_won | map_name
---------|---------|------------|----------|----------
G001     | TeamA   | Jett       | True     | Ascent
G001     | TeamA   | Viper      | True     | Ascent
G001     | TeamA   | Sova       | True     | Ascent
G001     | TeamA   | Killjoy    | True     | Ascent
G001     | TeamA   | Omen       | True     | Ascent
G001     | TeamB   | Reyna      | False    | Ascent
G001     | TeamB   | Brimstone  | False    | Ascent
G001     | TeamB   | Fade       | False    | Ascent
G001     | TeamB   | Cypher     | False    | Ascent
G001     | TeamB   | Skye       | False    | Ascent
             ↓ 집계
집계 데이터 (경기 단위):
match_id | map_name | team_a                         | team_b                           | label
---------|----------|--------------------------------|----------------------------------|------
G001     | Ascent   | [Jett,Viper,Sova,Killjoy,Omen] | [Reyna,Brimstone,Fade,Cypher,Skye] | 1
```

---

## 2. 집계 구현

```python
def aggregate_to_match_level(df: pd.DataFrame) -> pd.DataFrame:
    """
    플레이어 단위 DataFrame → 경기 단위 DataFrame
    
    반환 컬럼:
    - match_id: str
    - map_name: str
    - team_a: list[str]  (team_won=True 팀의 요원 리스트)
    - team_b: list[str]  (team_won=False 팀의 요원 리스트)
    - label: int          (1 = team_a 승리)
    """
    results = []
    
    for match_id, match_df in df.groupby("match_id"):
        map_name = match_df["map_name"].iloc[0]
        
        winning_team_df = match_df[match_df["team_won"] == True]
        losing_team_df = match_df[match_df["team_won"] == False]
        
        # 중복 제거 후 팀 구분
        winning_teams = winning_team_df["team_id"].unique()
        losing_teams = losing_team_df["team_id"].unique()
        
        if len(winning_teams) != 1 or len(losing_teams) != 1:
            continue  # 팀 구성이 불명확한 경기 건너뜀
        
        team_a_agents = winning_team_df["agent_name"].tolist()
        team_b_agents = losing_team_df["agent_name"].tolist()
        
        if len(team_a_agents) != 5 or len(team_b_agents) != 5:
            continue  # 5명이 아닌 팀 건너뜀
        
        results.append({
            "match_id": match_id,
            "map_name": map_name,
            "team_a": team_a_agents,
            "team_b": team_b_agents,
            "label": 1,  # team_a가 항상 승리 팀
        })
    
    match_df = pd.DataFrame(results)
    print(f"집계 완료: {len(match_df):,}경기")
    return match_df
```

---

## 3. 데이터 증강 (대칭 쌍 생성)

팀 A와 팀 B를 뒤집어 반대 케이스를 생성한다.  
이를 통해 데이터를 2배로 늘리고 모델의 대칭성을 확보한다.

```python
def augment_symmetric(df: pd.DataFrame) -> pd.DataFrame:
    """
    각 경기에 대해 팀 A/B를 뒤집은 대칭 샘플 추가
    원본: team_a 승리(label=1)
    추가: team_b 승리(label=0)
    """
    flipped = df.copy()
    flipped["team_a"], flipped["team_b"] = df["team_b"].copy(), df["team_a"].copy()
    flipped["label"] = 0
    flipped["match_id"] = df["match_id"] + "_flip"
    
    augmented = pd.concat([df, flipped], ignore_index=True)
    print(f"대칭 증강: {len(df):,} → {len(augmented):,}행")
    return augmented
```

**증강 후 예시:**
```
G001     | Ascent | [Jett,...] | [Reyna,...] | 1   ← 원본
G001_flip| Ascent | [Reyna,...] | [Jett,...] | 0   ← 증강
```

> **주의**: 증강 후 라벨 분포는 항상 50:50으로 균형잡힘

---

## 4. 팀 할당 전략

승리 팀 = team_a, 패배 팀 = team_b로 고정하는 이유:
- 모델이 "누가 더 강한 조합인가"를 학습
- 대칭 증강으로 편향 방지

만약 원본 데이터에 승패 정보 없이 side 정보(공격/수비)만 있는 경우:
```python
# side 기반 팀 구분 대안
attacker_df = match_df[match_df["side"] == "attack"]
defender_df = match_df[match_df["side"] == "defense"]
# 라운드 승수로 label 결정
```

---

## 5. 예외 케이스 처리

| 예외 | 처리 방법 |
|---|---|
| 팀이 3개 이상인 경기 | 해당 경기 전체 제외 |
| 무승부 경기 | 해당 경기 제외 (라벨 불명확) |
| 요원이 5명 미만인 팀 | 해당 경기 제외 |
| 같은 경기에서 같은 요원 2명 이상 선택 | 경고 로그 후 제외 |

---

## 6. 관련 문서

| 문서 | 내용 |
|---|---|
| [06_feature_engineering.md](06_feature_engineering.md) | 집계 후 피처 생성 |
| [07_split_and_validation.md](07_split_and_validation.md) | 증강 데이터 분할 |
