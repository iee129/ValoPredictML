> ⚠️ **범위 외**: 외부 API 미사용 방침. 본 프로젝트는 Kaggle 7개 데이터셋만 사용하며 HenrikDev API는 적용되지 않는다. 본문은 참고용으로 보존된다.

# 01. HenrikDev API 상세 가이드

## 1. 개요

| 항목 | 값 |
|------|-----|
| 공식 사이트 | https://henrikdev.xyz |
| API 베이스 URL | `https://api.henrikdev.xyz/valorant` |
| API 버전 | v4 (최신), v3 (구버전도 지원) |
| 인증 | API Key (무료/유료 플랜) |
| 무료 Rate Limit | 25 req/min (약 1,500 req/hour) |
| 데이터 범위 | 전 세계 모든 서버, 랭크 + 비랭크 + 커스텀 |
| 역사적 데이터 | 제한적 (최근 N경기까지, 서버별 차이) |

---

## 2. API Key 발급

```bash
# 1. HenrikDev 웹사이트에서 가입
# https://henrikdev.xyz → 로그인 → API Key 발급

# 2. 환경 변수로 저장 (절대 코드에 하드코딩 금지)
# .env 파일 (절대 git에 커밋하지 말 것)
echo "HENRIK_API_KEY=HDEV-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" >> .env

# 3. .gitignore에 추가
echo ".env" >> .gitignore
```

---

## 3. 주요 엔드포인트

### 3.1 선수 정보

```python
import httpx
import os

BASE_URL = "https://api.henrikdev.xyz/valorant"
API_KEY = os.getenv("HENRIK_API_KEY")

headers = {"Authorization": API_KEY}

# 선수 기본 정보
def get_account(name: str, tag: str, region: str = "ap") -> dict:
    url = f"{BASE_URL}/v2/account/{name}/{tag}"
    response = httpx.get(url, headers=headers)
    response.raise_for_status()
    return response.json()
```

### 3.2 매치 목록 (핵심 엔드포인트)

```python
def get_match_history(
    name: str, 
    tag: str, 
    region: str = "ap",
    mode: str = "competitive",  # competitive, deathmatch, spikerush 등
    size: int = 25  # 최대 25
) -> dict:
    """플레이어의 최근 경기 목록"""
    url = f"{BASE_URL}/v4/matches/{region}/{name}/{tag}"
    params = {"mode": mode, "size": size}
    response = httpx.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()
```

### 3.3 경기 상세 정보

```python
def get_match_detail(match_id: str, region: str = "ap") -> dict:
    """특정 경기의 상세 정보"""
    url = f"{BASE_URL}/v4/match/{region}/{match_id}"
    response = httpx.get(url, headers=headers)
    response.raise_for_status()
    return response.json()
```

---

## 4. 대량 수집 파이프라인

### 4.1 Rate Limit 관리

```python
import time
import asyncio
import httpx
from collections import deque

class RateLimiter:
    """슬라이딩 윈도우 방식 Rate Limiter (25 req/min)"""
    
    def __init__(self, max_requests: int = 25, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.request_times = deque()
    
    def wait_if_needed(self):
        now = time.time()
        
        # 윈도우 밖의 요청 제거
        while self.request_times and self.request_times[0] < now - self.window_seconds:
            self.request_times.popleft()
        
        if len(self.request_times) >= self.max_requests:
            wait_time = self.request_times[0] + self.window_seconds - now + 0.1
            print(f"[RATE LIMIT] {wait_time:.1f}초 대기...")
            time.sleep(wait_time)
        
        self.request_times.append(now)


rate_limiter = RateLimiter(max_requests=24, window_seconds=60)  # 24/min으로 보수적 설정
```

### 4.2 시드 플레이어 기반 수집

```python
import json
from pathlib import Path

# 시드 플레이어 목록 (이머탈+ 티어를 목표로 수집)
SEED_PLAYERS = [
    # 한국 서버 (KR)
    {"name": "TenZ", "tag": "TenZ", "region": "na"},
    {"name": "Boaster", "tag": "123", "region": "eu"},
    # 필요시 추가
]

class HenrikCollector:
    def __init__(self, api_key: str, output_dir: str = "data/raw/henrikdev"):
        self.api_key = api_key
        self.output_dir = output_dir
        self.headers = {"Authorization": api_key}
        os.makedirs(output_dir, exist_ok=True)
        self.collected_match_ids = set()
        self._load_existing_ids()
    
    def _load_existing_ids(self):
        """이미 수집된 경기 ID 로드 (중복 방지)"""
        for f in Path(self.output_dir).glob("*.json"):
            try:
                with open(f) as fp:
                    data = json.load(fp)
                if "metadata" in data:
                    self.collected_match_ids.add(data["metadata"].get("matchid", ""))
            except:
                pass
        print(f"[INFO] 기존 수집 경기: {len(self.collected_match_ids)}개")
    
    def collect_player_matches(self, name: str, tag: str, region: str, size: int = 25) -> list[str]:
        """선수의 최근 경기 목록 수집 → 새 match_id 반환"""
        rate_limiter.wait_if_needed()
        
        url = f"{BASE_URL}/v4/matches/{region}/{name}/{tag}"
        params = {"mode": "competitive", "size": size}
        
        try:
            resp = httpx.get(url, headers=self.headers, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[WARN] {name}#{tag}: {e}")
            return []
        
        new_ids = []
        for match in data.get("data", []):
            mid = match.get("metadata", {}).get("matchid", "")
            if mid and mid not in self.collected_match_ids:
                new_ids.append(mid)
        
        return new_ids
    
    def collect_match_detail(self, match_id: str, region: str) -> bool:
        """경기 상세 정보 수집 및 저장"""
        if match_id in self.collected_match_ids:
            return False  # 이미 수집
        
        rate_limiter.wait_if_needed()
        
        url = f"{BASE_URL}/v4/match/{region}/{match_id}"
        try:
            resp = httpx.get(url, headers=self.headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[WARN] match {match_id}: {e}")
            return False
        
        # 저장
        output_path = os.path.join(self.output_dir, f"{match_id}.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        
        self.collected_match_ids.add(match_id)
        return True
    
    def run_collection(self, target_count: int = 5000):
        """목표 경기 수까지 수집"""
        collected = 0
        
        for seed in SEED_PLAYERS:
            if collected >= target_count:
                break
            
            print(f"\n[INFO] 시드: {seed['name']}#{seed['tag']}")
            new_ids = self.collect_player_matches(
                seed["name"], seed["tag"], seed["region"]
            )
            
            for match_id in new_ids:
                if collected >= target_count:
                    break
                success = self.collect_match_detail(match_id, seed["region"])
                if success:
                    collected += 1
                    if collected % 100 == 0:
                        print(f"[INFO] 수집 완료: {collected}개")
        
        print(f"\n[INFO] 최종 수집: {collected}개 경기")
```

---

## 5. 수집된 JSON → DataFrame 변환

```python
def parse_henrikdev_match(data: dict) -> dict | None:
    """HenrikDev v4 match JSON → 경기 레코드 변환"""
    try:
        metadata = data.get("metadata", {})
        map_name = metadata.get("map", "Unknown")
        
        teams = data.get("teams", {})
        players = data.get("players", [])
        
        team_a_players = [p for p in players if p.get("team_id") == "Red"]
        team_b_players = [p for p in players if p.get("team_id") == "Blue"]
        
        team_a_agents = [p.get("agent", {}).get("name", "") for p in team_a_players]
        team_b_agents = [p.get("agent", {}).get("name", "") for p in team_b_players]
        
        # 승패 결정
        team_a_won = teams.get("red", {}).get("has_won", False)
        
        return {
            "match_id": metadata.get("matchid", ""),
            "map": map_name,
            "team_a_agents": ",".join(team_a_agents),
            "team_b_agents": ",".join(team_b_agents),
            "label": 1 if team_a_won else 0,
            "source": "henrikdev",
        }
    except Exception as e:
        return None
```

---

## 6. 무료 플랜 한계 및 대응

| 한계 | 값 | 대응 |
|------|-----|------|
| Rate Limit | 25 req/min | Rate Limiter 구현 |
| 역사적 데이터 | 최근 25경기 | 많은 시드 플레이어 |
| 서버 지원 | 전 서버 | 다양한 region 사용 |
| 비용 | 무료 | 5,000경기 목표 달성 가능 |

> **예상 수집 시간:** 5,000경기 × 2 API 호출 = 10,000 req ÷ 24 req/min = **약 7시간**
