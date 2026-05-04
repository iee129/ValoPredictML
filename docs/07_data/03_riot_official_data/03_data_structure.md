> ⚠️ **범위 외**: 외부 API 미사용 방침. 본 프로젝트는 Kaggle 7개 데이터셋만 사용하며 Riot S3 데이터 구조는 적용되지 않는다. 본문은 참고용으로 보존된다.

# 03. Riot VCT S3 데이터 구조 및 파싱

## 1. 파일 타입별 상세 구조

### 1.1 mapping.json — 핵심 피처 파일

```json
{
  "platformGameId": "val:gvp-abc123",
  "matchId": "match_uuid_001",
  "gameId": "game_uuid_001",
  "map": {
    "id": "map_uuid",
    "name": "Ascent"
  },
  "gameVersion": "08.02.00.2341534",
  "participants": [
    {
      "participantId": 1,
      "displayName": "TenZ",
      "playerId": "player_uuid_001",
      "teamId": "team_a_id"
    }
  ],
  "teams": [
    {
      "teamId": "team_a_id",
      "teamName": "Sentinels",
      "won": true
    },
    {
      "teamId": "team_b_id", 
      "teamName": "Cloud9",
      "won": false
    }
  ],
  "agents": [
    {
      "participantId": 1,
      "agentId": "agent_uuid",
      "agentName": "Jett"
    }
  ]
}
```

### 1.2 scoreboard.json — 통계 파일

```json
{
  "platformGameId": "val:gvp-abc123",
  "players": [
    {
      "participantId": 1,
      "kills": 22,
      "deaths": 14,
      "assists": 3,
      "acs": 312,
      "kast": 78.3,
      "adr": 185.0,
      "headshots": 7,
      "bodyshots": 15,
      "legshots": 2,
      "firstKills": 5,
      "firstDeaths": 2
    }
  ]
}
```

---

## 2. 파싱 코드

### 2.1 단일 경기 파싱

```python
import json
import os
from dataclasses import dataclass, field

@dataclass
class MatchRecord:
    game_id: str
    map_name: str
    team_a_name: str
    team_b_name: str
    team_a_agents: list[str]
    team_b_agents: list[str]
    winner: str  # 'team_a' or 'team_b'
    game_version: str = ""
    source: str = "riot_s3"


def parse_mapping_file(filepath: str) -> MatchRecord | None:
    """mapping.json 파일 → MatchRecord 파싱"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[ERROR] 파싱 실패 {filepath}: {e}")
        return None

    # 팀 정보 추출
    teams = {t["teamId"]: t for t in data.get("teams", [])}
    if len(teams) != 2:
        return None  # 비정상 데이터

    team_ids = list(teams.keys())
    team_a_id, team_b_id = team_ids[0], team_ids[1]
    team_a = teams[team_a_id]
    team_b = teams[team_b_id]

    # 참가자 → 팀 매핑
    participant_team = {
        p["participantId"]: p["teamId"]
        for p in data.get("participants", [])
    }

    # 요원 → 팀 분류
    team_a_agents, team_b_agents = [], []
    for agent_info in data.get("agents", []):
        pid = agent_info["participantId"]
        agent_name = agent_info.get("agentName", "Unknown")
        team_id = participant_team.get(pid)
        if team_id == team_a_id:
            team_a_agents.append(agent_name)
        elif team_id == team_b_id:
            team_b_agents.append(agent_name)

    # 승리 팀 결정
    winner = "team_a" if team_a.get("won") else "team_b"

    return MatchRecord(
        game_id=data.get("gameId", ""),
        map_name=data.get("map", {}).get("name", "Unknown"),
        team_a_name=team_a.get("teamName", "TeamA"),
        team_b_name=team_b.get("teamName", "TeamB"),
        team_a_agents=team_a_agents,
        team_b_agents=team_b_agents,
        winner=winner,
        game_version=data.get("gameVersion", ""),
        source="riot_s3"
    )
```

### 2.2 대량 파싱 → DataFrame

```python
import glob
import pandas as pd
from tqdm import tqdm

AGENT_ROLE_MAP = {
    "Jett": "Duelist", "Reyna": "Duelist", "Raze": "Duelist",
    "Neon": "Duelist", "Yoru": "Duelist", "Phoenix": "Duelist",
    "ISO": "Duelist", "Waylay": "Duelist",
    "Sova": "Initiator", "Breach": "Initiator", "Fade": "Initiator",
    "KAY/O": "Initiator", "Gekko": "Initiator", "Skye": "Initiator",
    "Tejo": "Initiator",
    "Viper": "Controller", "Omen": "Controller", "Brimstone": "Controller",
    "Astra": "Controller", "Harbor": "Controller", "Clove": "Controller",
    "Killjoy": "Sentinel", "Cypher": "Sentinel", "Sage": "Sentinel",
    "Chamber": "Sentinel", "Deadlock": "Sentinel", "Vyse": "Sentinel",
}

def count_roles(agents: list[str]) -> dict:
    """요원 목록 → 역할군 카운트"""
    counts = {"Duelist": 0, "Initiator": 0, "Controller": 0, "Sentinel": 0}
    for agent in agents:
        role = AGENT_ROLE_MAP.get(agent, "Unknown")
        if role in counts:
            counts[role] += 1
    return counts


def parse_all_mapping_files(riot_s3_dir: str = "data/raw/riot_s3") -> pd.DataFrame:
    """모든 mapping.json 파일을 읽어 DataFrame 생성"""
    mapping_files = glob.glob(
        os.path.join(riot_s3_dir, "**/*/mapping.json"),
        recursive=True
    )
    
    records = []
    for filepath in tqdm(mapping_files, desc="Parsing mapping files"):
        match = parse_mapping_file(filepath)
        if match is None:
            continue
        
        # 팀 A 역할군 카운트
        a_roles = count_roles(match.team_a_agents)
        b_roles = count_roles(match.team_b_agents)
        
        row = {
            "game_id": match.game_id,
            "map": match.map_name,
            "team_a": match.team_a_name,
            "team_b": match.team_b_name,
            "team_a_agents": ",".join(match.team_a_agents),
            "team_b_agents": ",".join(match.team_b_agents),
            "a_duelist": a_roles["Duelist"],
            "a_initiator": a_roles["Initiator"],
            "a_controller": a_roles["Controller"],
            "a_sentinel": a_roles["Sentinel"],
            "b_duelist": b_roles["Duelist"],
            "b_initiator": b_roles["Initiator"],
            "b_controller": b_roles["Controller"],
            "b_sentinel": b_roles["Sentinel"],
            "winner": match.winner,
            "label": 1 if match.winner == "team_a" else 0,
            "game_version": match.game_version,
            "source": match.source,
        }
        records.append(row)
    
    df = pd.DataFrame(records)
    print(f"[INFO] 파싱 완료: {len(df)} 경기")
    return df
```

---

## 3. 파싱 후 피처 추가

### 3.1 diff 피처 (기존 설계와 호환)

```python
def add_diff_features(df: pd.DataFrame) -> pd.DataFrame:
    """역할군 diff 피처 추가 (기존 15개 피처와 호환)"""
    for role in ["duelist", "initiator", "controller", "sentinel"]:
        df[f"{role}_diff"] = df[f"a_{role}"] - df[f"b_{role}"]
    return df
```

### 3.2 맵 인코딩

```python
from sklearn.preprocessing import LabelEncoder

def encode_map(df: pd.DataFrame) -> pd.DataFrame:
    """맵 이름 → 정수 인코딩"""
    le = LabelEncoder()
    df["map_encoded"] = le.fit_transform(df["map"])
    return df, le
```

---

## 4. 저장 및 캐싱

```python
def save_parsed_data(df: pd.DataFrame, output_path: str = "data/processed/riot_s3_parsed.csv"):
    """파싱 결과를 CSV로 저장"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8")
    print(f"[INFO] 저장 완료: {output_path} ({len(df)} 행)")

def load_or_parse(riot_s3_dir: str, cache_path: str) -> pd.DataFrame:
    """캐시가 있으면 로드, 없으면 파싱 후 저장"""
    if os.path.exists(cache_path):
        print(f"[INFO] 캐시 로드: {cache_path}")
        return pd.read_csv(cache_path)
    
    df = parse_all_mapping_files(riot_s3_dir)
    df = add_diff_features(df)
    save_parsed_data(df, cache_path)
    return df
```

---

## 5. 예상 출력 컬럼

```
game_id, map, team_a, team_b,
team_a_agents, team_b_agents,
a_duelist, a_initiator, a_controller, a_sentinel,
b_duelist, b_initiator, b_controller, b_sentinel,
duelist_diff, initiator_diff, controller_diff, sentinel_diff,
winner, label,
game_version, source
```

총 **23개 컬럼** (기존 15개 피처와 완전 호환 + 메타 컬럼)
