> ⚠️ **범위 외**: 외부 API 미사용 방침. 본 프로젝트는 Kaggle 7개 데이터셋만 사용하며 valorant-api.com은 적용되지 않는다. 본문은 참고용으로 보존된다.

# 03. valorant-api.com — 게임 메타 데이터 API

## 1. 개요

| 항목 | 값 |
|------|-----|
| 사이트 | https://valorant-api.com |
| 용도 | 요원/맵/스킨/패치 정보 (게임 에셋 API) |
| 인증 | 불필요 (완전 무료) |
| Rate Limit | 없음 (비공식이지만 관대함) |
| 데이터 종류 | 요원 정보, 맵 목록, 패치 노트, 무기 등 |

> **주의:** 이 API는 **경기 결과 데이터**를 제공하지 않음.  
> 요원 UUID → 이름/역할군 매핑, 맵 UUID → 이름 변환에 사용.

---

## 2. 주요 엔드포인트

### 2.1 요원 정보

```python
import httpx
import json
import os

BASE = "https://valorant-api.com/v1"

def fetch_agents(language: str = "en-US") -> list[dict]:
    """플레이 가능한 모든 요원 정보"""
    url = f"{BASE}/agents"
    resp = httpx.get(url, params={"language": language, "isPlayableCharacter": "true"})
    resp.raise_for_status()
    return resp.json()["data"]

def build_agent_maps() -> tuple[dict, dict]:
    """UUID → 이름, UUID → 역할군 매핑 딕셔너리 생성"""
    agents = fetch_agents()
    
    uuid_to_name = {}
    uuid_to_role = {}
    name_to_role = {}
    
    for agent in agents:
        uuid = agent["uuid"]
        name = agent["displayName"]
        role = agent.get("role", {}).get("displayName", "Unknown") if agent.get("role") else "Unknown"
        
        uuid_to_name[uuid] = name
        uuid_to_role[uuid] = role
        name_to_role[name] = role
    
    return uuid_to_name, uuid_to_role, name_to_role
```

### 2.2 맵 정보

```python
def fetch_maps() -> list[dict]:
    """모든 맵 정보"""
    url = f"{BASE}/maps"
    resp = httpx.get(url)
    resp.raise_for_status()
    return resp.json()["data"]

def build_map_uuid_map() -> dict:
    """mapUrl (UUID 경로) → 맵 이름 매핑"""
    maps = fetch_maps()
    
    return {
        m["mapUrl"]: m["displayName"]
        for m in maps
    }

# 예시:
# "/Game/Maps/Ascent/Ascent" → "Ascent"
# "/Game/Maps/Bind/Duality" → "Bind"
```

### 2.3 패치/버전 정보

```python
def fetch_latest_version() -> dict:
    """현재 패치 버전 정보"""
    url = f"{BASE}/version"
    resp = httpx.get(url)
    resp.raise_for_status()
    return resp.json()["data"]

# 반환 예시:
# {
#   "manifestId": "...",
#   "branch": "release-09.03",
#   "version": "09.03.00.1234567",
#   "buildVersion": "1234567",
#   "engineVersion": "...",
#   "riotClientVersion": "release-09.03-shipping-...",
#   "riotClientBuild": "...",
#   "buildDate": "2025-01-15"
# }
```

---

## 3. 역할군 매핑 생성 및 저장

```python
def save_agent_role_mapping(output_path: str = "data/meta/agent_roles.json"):
    """요원 역할군 매핑을 JSON 파일로 저장"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    _, _, name_to_role = build_agent_maps()
    
    # 역할군 영어 → 한국어 변환
    ROLE_KO = {
        "Duelist": "듀얼리스트",
        "Initiator": "이니시에이터",
        "Controller": "컨트롤러",
        "Sentinel": "센티넬",
    }
    
    mapping = {
        name: {
            "role_en": role,
            "role_ko": ROLE_KO.get(role, role)
        }
        for name, role in name_to_role.items()
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    
    print(f"[INFO] 저장: {output_path} ({len(mapping)} 요원)")
    return mapping
```

---

## 4. 패치 버전과 데이터 연계

데이터셋에 패치 버전 정보가 있으면 피처로 활용 가능:

```python
# 주요 패치 → 메타 변화 매핑
MAJOR_META_PATCHES = {
    "release-07.0": "에피소드 7 시작, Deadlock 추가",
    "release-08.0": "에피소드 8 시작, ISO 너프",
    "release-08.02": "Clove 추가",
    "release-09.0": "에피소드 9 시작",
}

def categorize_patch(game_version: str) -> str:
    """게임 버전 문자열 → 주요 패치 에포크 분류"""
    # "release-08.02.00.1234567" → "08.02"
    parts = game_version.split("-")
    if len(parts) >= 2:
        ep_act = ".".join(parts[1].split(".")[:2])
        return ep_act
    return "unknown"

# 피처 추가 예시
df["patch_epoch"] = df["game_version"].apply(categorize_patch)
```

---

## 5. ValoPredictML에서의 활용

### 5.1 현재 사용 (필수)

- Riot 공식 API의 `characterId` (UUID) → 요원 이름 변환
- Riot 공식 API의 `mapId` → 맵 이름 변환

### 5.2 추가 피처 (선택)

| 피처 | 엔드포인트 | 기대 효과 |
|------|-----------|--------|
| 패치 버전 그룹 | `/version` | +1~2%p 정확도 향상 |
| 요원 역할군 (29종 전체) | `/agents` | 기존 역할군 피처 보완 |
| 맵 좌표 (공격/수비 구조) | `/maps` (minimap) | 고급 피처 후보 |

---

## 6. 데이터 캐싱 (권장)

valorant-api.com은 게임 업데이트 시에만 변경되므로 로컬 캐싱 필수:

```python
def load_or_fetch_agents(cache_path: str = "data/meta/agents.json") -> list[dict]:
    """캐시가 있으면 로드, 없으면 API 호출"""
    if os.path.exists(cache_path):
        with open(cache_path) as f:
            return json.load(f)
    
    agents = fetch_agents()
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(agents, f, ensure_ascii=False, indent=2)
    
    return agents
```

---

## 7. 전체 요원 목록 (2025년 기준)

```python
# 현재 플레이 가능한 29종 요원 (fetch_agents()로 최신 정보 확인)
CURRENT_AGENTS = {
    "Duelist": ["Jett", "Reyna", "Raze", "Neon", "Yoru", "Phoenix", "ISO", "Waylay"],
    "Initiator": ["Sova", "Breach", "Fade", "KAY/O", "Gekko", "Skye", "Tejo"],
    "Controller": ["Viper", "Omen", "Brimstone", "Astra", "Harbor", "Clove", "Miks"],
    "Sentinel": ["Killjoy", "Cypher", "Sage", "Chamber", "Deadlock", "Vyse", "Veto"],
}
# 총 29종: Duelist 8, Initiator 7, Controller 7, Sentinel 7
```
