> ⚠️ **범위 외**: 스크래핑 미사용 방침. 본 프로젝트는 Kaggle 7개 데이터셋만 사용하며 Liquipedia 스크래핑은 적용되지 않는다. 본문은 참고용으로 보존된다.

# 02. Liquipedia 스크래핑 가이드

## 1. Liquipedia VALORANT 소개

| 항목 | 값 |
|------|-----|
| URL | https://liquipedia.net/valorant |
| 용도 | e스포츠 팀/선수/대회 위키 데이터베이스 |
| 커버리지 | VCT + 지역 리그 + 국내 대회 |
| 데이터 종류 | 경기 결과, 팀 구성, 대회 브래킷 |
| 스크래핑 가능 여부 | 조건부 허용 (Rate Limit 엄격) |
| API 여부 | 비공식 API 있음 (`liquipediapy` 라이브러리) |

---

## 2. robots.txt 및 정책

```bash
curl https://liquipedia.net/robots.txt
```

Liquipedia 스크래핑 정책:
- **User-Agent 필수 명시** (연구 목적 명시)
- **요청 간격 최소 30초** (매우 엄격)
- 하루 최대 요청 수 제한 (미공개)
- API 토큰 시스템 있음 (연구자 신청 가능)

---

## 3. liquipediapy 라이브러리 사용

```bash
pip install liquipediapy
```

```python
from liquipediapy import Liquipedia

lp = Liquipedia("valorant")

# 선수 정보
player_info = lp.get_player_info("TenZ")

# 팀 정보
team_info = lp.get_team_info("Sentinels")
```

---

## 4. 직접 스크래핑 (Rate Limit 준수 필수)

```python
import httpx
from bs4 import BeautifulSoup
import time
import re

LIQUIPEDIA_BASE = "https://liquipedia.net/valorant"
HEADERS = {
    "User-Agent": "ValoPredictML-Research/1.0 (Educational/Non-commercial; contact: your@email.com)",
    "Accept-Language": "en-US,en;q=0.9"
}
CRAWL_DELAY = 30  # Liquipedia 요구 최소 30초

def get_tournament_matches(tournament_path: str) -> list[dict]:
    """
    대회 페이지에서 경기 결과 파싱
    
    tournament_path 예시:
    - "/VCT/2023/Champions"
    - "/VCT/2023/Americas/League/Stage_1"
    """
    url = f"{LIQUIPEDIA_BASE}{tournament_path}"
    
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        print(f"[WARN] {url}: {e}")
        return []
    
    soup = BeautifulSoup(resp.text, "html.parser")
    matches = []
    
    # 브래킷 매치 파싱
    for match_el in soup.select(".bracket-cell .bracket-popup-wrapper"):
        team_els = match_el.select(".bracket-popup-header-team")
        score_els = match_el.select(".bracket-popup-header-score")
        
        if len(team_els) < 2:
            continue
        
        team_a = team_els[0].text.strip()
        team_b = team_els[1].text.strip()
        
        scores = [s.text.strip() for s in score_els]
        
        matches.append({
            "team_a": team_a,
            "team_b": team_b,
            "scores": scores,
        })
    
    time.sleep(CRAWL_DELAY)  # 반드시 대기
    return matches
```

---

## 5. API 토큰 신청 (권장)

대량 수집을 위해서는 Liquipedia API 토큰 신청 권장:

```
신청 URL: https://liquipedia.net/commons/Special:ApiKeyRequest
용도: 학술/연구 목적 명시
```

토큰 발급 후:
```python
LIQUIPEDIA_API_URL = "https://liquipedia.net/valorant/api.php"
params = {
    "action": "parse",
    "page": "VCT/2023/Champions",
    "format": "json",
    "token": "your_api_token_here"
}
```

---

## 6. Liquipedia의 VLR.gg 대비 장단점

| 항목 | VLR.gg | Liquipedia |
|------|--------|-----------|
| 경기 데이터 | ✅ 상세 스탯 포함 | ❌ 결과/브래킷 중심 |
| Rate Limit | 2~3초 간격 | 30초 이상 |
| 요원 픽 정보 | ✅ 있음 | ❌ 제한적 |
| 대회 역사 | 최근 중심 | 광범위 |
| 구조화 정도 | 동적 (JS 렌더) | 위키 형식 |

---

## 7. ValoPredictML에서의 활용

Liquipedia는 주 스크래핑 소스로 사용하기에 부적합 (Rate Limit, 데이터 형식).  
대신 다음 용도로 활용:

1. **팀 명단 확인** — 특정 시즌 팀 구성 확인
2. **대회 목록 구축** — VCT 전체 대회 URL 목록 생성
3. **팀 이름 표준화** — 약어/풀네임 매핑 테이블 구축

```python
# 팀 이름 표준화 테이블 (Liquipedia → VLR.gg → Riot 데이터 연결)
TEAM_NAME_ALIASES = {
    "NRG": ["NRG Esports", "NRG"],
    "SEN": ["Sentinels", "SEN"],
    "C9": ["Cloud9", "Cloud 9", "C9"],
    "100T": ["100 Thieves", "100T"],
    "LOUD": ["LOUD", "Loud"],
    "FPX": ["FunPlus Phoenix", "FPX"],
}
```

---

## 8. 결론: 스크래핑 우선순위

| 우선순위 | 소스 | 이유 |
|---------|------|------|
| 1순위 | VLR.gg | 가장 상세한 스탯, Rate Limit 관대 |
| 2순위 | Liquipedia | 대회 구조 파악, 팀 이름 표준화 보조 |

> 스크래핑은 **Riot S3 + HenrikDev API** 확보 후, 추가 볼륨이 필요할 때 시작.
