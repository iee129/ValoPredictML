# 02. Riot 공식 API (Developer Portal)

## 1. 개요

| 항목 | 값 |
|------|-----|
| 공식 사이트 | https://developer.riotgames.com |
| API 버전 | VALORANT v1 |
| 인증 | Riot API Key (개발자 등록 필요) |
| 개발자 키 Rate Limit | 20 req/s (개인), 100 req/s (프로덕션) |
| 개인 키 유효기간 | 24시간 (매일 재발급 필요) |
| 데이터 커버리지 | 경쟁전 매치 이력 (최근 최대 200경기) |

---

## 2. API Key 발급

```bash
# 1. Riot 개발자 포털 가입
# https://developer.riotgames.com/ → 로그인 → Generate API Key

# 2. 환경 변수 설정
echo "RIOT_API_KEY=RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" >> .env

# 주의: 개발자 키는 24시간마다 만료 → 자동화 수집에는 부적합
# 프로덕션 키 신청 필요 (팀 신청 or 앱 등록)
```

---

## 3. VALORANT API 엔드포인트

### 3.1 계정 API

```python
import httpx
import os

RIOT_KEY = os.getenv("RIOT_API_KEY")
headers = {"X-Riot-Token": RIOT_KEY}

# 게임 이름 + 태그로 PUUID 조회
def get_puuid(game_name: str, tag_line: str) -> str:
    url = f"https://asia.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    resp = httpx.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()["puuid"]
```

### 3.2 매치 이력

```python
def get_match_ids(puuid: str, region: str = "ap", count: int = 20, queue: str = "competitive") -> list[str]:
    """최근 경기 ID 목록"""
    url = f"https://{region}.api.riotgames.com/val/match/v1/matchlists/by-puuid/{puuid}"
    params = {"queue": queue}
    resp = httpx.get(url, headers=headers, params=params)
    resp.raise_for_status()
    return resp.json().get("history", [])
```

### 3.3 경기 상세

```python
def get_match(match_id: str, region: str = "ap") -> dict:
    """경기 상세 정보"""
    url = f"https://{region}.api.riotgames.com/val/match/v1/matches/{match_id}"
    resp = httpx.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()
```

---

## 4. VALORANT API 데이터 구조

### 4.1 매치 응답 구조

```json
{
  "matchInfo": {
    "matchId": "...",
    "mapId": "...",
    "gameVersion": "release-08.02",
    "gameStartMillis": 1704067200000
  },
  "players": [
    {
      "puuid": "...",
      "gameName": "TenZ",
      "tagLine": "TenZ",
      "teamId": "Red",
      "characterId": "...",
      "stats": {
        "kills": 22,
        "deaths": 14,
        "assists": 3,
        "score": 6248
      }
    }
  ],
  "teams": [
    {
      "teamId": "Red",
      "won": true,
      "roundsPlayed": 24,
      "roundsWon": 13
    },
    {
      "teamId": "Blue",
      "won": false,
      "roundsPlayed": 24,
      "roundsWon": 11
    }
  ],
  "roundResults": [...]
}
```

### 4.2 characterId → 요원 이름 변환

```python
# Riot API는 요원 이름 대신 UUID(characterId)를 반환
# valorant-api.com을 통해 UUID → 이름 매핑 필요

import httpx

def fetch_agent_uuid_map() -> dict:
    """valorant-api.com에서 요원 UUID → 이름 매핑 다운로드"""
    url = "https://valorant-api.com/v1/agents?isPlayableCharacter=true"
    resp = httpx.get(url)
    resp.raise_for_status()
    data = resp.json()
    
    return {
        agent["uuid"]: agent["displayName"]
        for agent in data["data"]
    }

# 파싱 시 사용
AGENT_UUID_MAP = fetch_agent_uuid_map()

def get_agent_name(character_id: str) -> str:
    return AGENT_UUID_MAP.get(character_id.lower(), "Unknown")
```

---

## 5. 개발자 키 vs 프로덕션 키

| 구분 | 개발자 키 | 프로덕션 키 |
|------|---------|----------|
| 취득 방법 | 즉시 발급 | 프로젝트 신청 후 심사 |
| 유효기간 | 24시간 | 영구 (갱신 필요) |
| Rate Limit | 20 req/s | 100~500 req/s |
| 대량 수집 가능 여부 | ❌ (비실용적) | ✅ |
| 권장 용도 | 개발/테스트 | 프로덕션 수집 |

> **결론:** 대량 데이터 수집을 위해서는 **프로덕션 키 신청 필요**.  
> 대안으로 **HenrikDev API** (래퍼 서비스)는 무료로 동일한 데이터 접근 가능.

---

## 6. Rate Limit 관리

```python
import time
from functools import wraps

def rate_limited(max_per_second: float):
    """데코레이터: API 함수에 Rate Limit 적용"""
    min_interval = 1.0 / max_per_second
    last_called = [0.0]
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            wait = min_interval - elapsed
            if wait > 0:
                time.sleep(wait)
            result = func(*args, **kwargs)
            last_called[0] = time.time()
            return result
        return wrapper
    return decorator

# 개발자 키: 20 req/s 제한
@rate_limited(max_per_second=18)  # 안전 마진
def safe_get_match(match_id: str, region: str = "ap") -> dict:
    return get_match(match_id, region)
```

---

## 7. 데이터 파싱 → DataFrame

```python
def parse_riot_match(data: dict) -> dict | None:
    """Riot API 매치 JSON → 경기 레코드"""
    try:
        match_info = data.get("matchInfo", {})
        map_id = match_info.get("mapId", "")
        
        # mapId → 맵 이름 변환 (별도 매핑 필요)
        map_name = MAP_UUID_MAP.get(map_id, map_id.split("/")[-1] if "/" in map_id else map_id)
        
        players = data.get("players", [])
        teams = {t["teamId"]: t for t in data.get("teams", [])}
        
        red_players = [p for p in players if p.get("teamId") == "Red"]
        blue_players = [p for p in players if p.get("teamId") == "Blue"]
        
        red_agents = [get_agent_name(p.get("characterId", "")) for p in red_players]
        blue_agents = [get_agent_name(p.get("characterId", "")) for p in blue_players]
        
        red_won = teams.get("Red", {}).get("won", False)
        
        return {
            "match_id": match_info.get("matchId", ""),
            "map": map_name,
            "team_a_agents": ",".join(red_agents),
            "team_b_agents": ",".join(blue_agents),
            "label": 1 if red_won else 0,
            "source": "riot_official",
        }
    except Exception as e:
        return None
```

---

## 8. 사용 권장 사항

| 상황 | 권장 API |
|------|---------|
| 빠른 개발/테스트 | HenrikDev API |
| 소규모 수집 (~1,000경기) | Riot 개발자 키 |
| 대규모 수집 (10,000+경기) | Riot 프로덕션 키 또는 HenrikDev |
| 프로 경기 데이터 | Riot VCT S3 |

> **결론:** ValoPredictML 프로젝트에서 Riot 공식 API는 보조 수단으로 활용.  
> 주 수집은 **Riot S3** (프로) + **HenrikDev** (랭크 매치)로 진행.
