# 01. VLR.gg 스크래핑 가이드

## 1. VLR.gg 소개

| 항목 | 값 |
|------|-----|
| URL | https://www.vlr.gg |
| 용도 | 발로란트 e스포츠 공식 통계 사이트 |
| 커버리지 | VCT + Challengers + Game Changers + 국내 리그 |
| 데이터 종류 | 경기 결과, 팀 조합, 맵별 통계, 선수 스탯 |
| 스크래핑 가능 여부 | 기술적으로 가능, robots.txt 확인 필요 |
| 예상 경기 수 | 10,000+ (VCT 전 기간 + 지역 리그) |

---

## 2. 법적 고려사항

```bash
# robots.txt 확인 (항상 먼저 확인)
curl https://www.vlr.gg/robots.txt
```

VLR.gg는 일반적으로 비상업적 연구 목적 스크래핑을 허용하지만:
- 서버에 과도한 부하를 주지 않을 것 (delay 필수)
- 재배포 금지
- 상업적 이용 금지
- 크롤링 간격: 최소 2~3초 이상

---

## 3. 페이지 구조 분석

### 3.1 주요 URL 패턴

```
# 경기 목록
https://www.vlr.gg/matches/results

# 특정 경기 상세
https://www.vlr.gg/{match_id}/{team_a}-vs-{team_b}

# 팀 통계
https://www.vlr.gg/team/{team_id}/{team_name}

# 이벤트(대회) 목록
https://www.vlr.gg/events
```

### 3.2 경기 목록 페이지 구조

```html
<!-- 경기 카드 -->
<a class="m-item" href="/12345/sentinels-vs-cloud9">
  <div class="m-item-result">
    <span>S</span>  <!-- 팀 A 첫 글자 -->
    <span>13 : 11</span>
    <span>C9</span>
  </div>
  <div class="m-item-games">
    <span class="m-item-map">Ascent</span>
  </div>
</a>
```

---

## 4. 스크래핑 코드

### 4.1 경기 ID 목록 수집

```python
import httpx
from bs4 import BeautifulSoup
import time
import re

BASE_URL = "https://www.vlr.gg"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ValoPredictML-Research/1.0; educational purpose)"
}

def get_match_ids_from_results(page: int = 1) -> list[str]:
    """결과 목록 페이지에서 경기 ID 추출"""
    url = f"{BASE_URL}/matches/results?page={page}"
    
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"[WARN] 페이지 {page} 로드 실패: {e}")
        return []
    
    soup = BeautifulSoup(resp.text, "html.parser")
    
    match_ids = []
    for link in soup.select("a.m-item"):
        href = link.get("href", "")
        # 형식: /12345/team-a-vs-team-b
        match = re.match(r"/(\d+)/", href)
        if match:
            match_ids.append(match.group(1))
    
    return match_ids


def scrape_all_match_ids(max_pages: int = 100, delay: float = 2.5) -> list[str]:
    """전체 결과 목록에서 경기 ID 수집"""
    all_ids = []
    
    for page in range(1, max_pages + 1):
        ids = get_match_ids_from_results(page)
        if not ids:
            print(f"[INFO] 페이지 {page}: 경기 없음, 중단")
            break
        
        all_ids.extend(ids)
        print(f"[INFO] 페이지 {page}: {len(ids)}개 ({len(all_ids)}개 누적)")
        time.sleep(delay)  # 서버 부하 방지
    
    return list(set(all_ids))  # 중복 제거
```

### 4.2 경기 상세 파싱

```python
def scrape_match_detail(match_id: str, delay: float = 3.0) -> dict | None:
    """경기 상세 페이지 파싱"""
    
    # 먼저 경기 URL 결정 (slug 포함 URL 필요)
    url = f"{BASE_URL}/{match_id}"  # 리다이렉트 됨
    
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=15, follow_redirects=True)
        resp.raise_for_status()
    except Exception as e:
        print(f"[WARN] 경기 {match_id}: {e}")
        return None
    
    soup = BeautifulSoup(resp.text, "html.parser")
    
    # 팀 이름
    team_names = [el.text.strip() for el in soup.select(".match-header-link-name .wf-title-med")]
    if len(team_names) < 2:
        return None
    
    # 각 맵별 결과
    maps_data = []
    for map_section in soup.select(".vm-stats-game"):
        map_name_el = map_section.select_one(".map-name")
        if not map_name_el:
            continue
        map_name = map_name_el.text.strip()
        
        # 요원 픽
        agents_by_team = [[], []]
        player_rows = map_section.select(".wf-table-inset tr")
        
        current_team = 0
        for row in player_rows:
            agent_el = row.select_one(".gt-lg img")  # 요원 이미지
            if agent_el:
                agent_name = agent_el.get("alt", "").replace(" Icon", "")
                agents_by_team[current_team].append(agent_name)
                if len(agents_by_team[current_team]) >= 5:
                    current_team = 1
        
        # 스코어
        score_els = map_section.select(".score")
        scores = [int(el.text.strip()) for el in score_els if el.text.strip().isdigit()]
        
        if len(scores) >= 2:
            winner = "team_a" if scores[0] > scores[1] else "team_b"
            maps_data.append({
                "map": map_name,
                "team_a_score": scores[0],
                "team_b_score": scores[1],
                "team_a_agents": agents_by_team[0],
                "team_b_agents": agents_by_team[1],
                "winner": winner,
            })
    
    time.sleep(delay)
    
    return {
        "match_id": match_id,
        "team_a": team_names[0],
        "team_b": team_names[1],
        "maps": maps_data,
    }
```

### 4.3 전체 파이프라인

```python
import json
import os

def run_vlrgg_scraper(
    output_dir: str = "data/raw/vlrgg",
    max_pages: int = 50,
    target_matches: int = 3000
):
    """VLR.gg 전체 스크래핑 파이프라인"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Step 1: 경기 ID 수집
    print("[STEP 1] 경기 ID 수집...")
    match_ids = scrape_all_match_ids(max_pages=max_pages)
    print(f"[INFO] 총 {len(match_ids)}개 경기 ID 수집")
    
    # Step 2: 상세 정보 수집
    print("[STEP 2] 경기 상세 수집...")
    collected = 0
    
    for match_id in match_ids:
        if collected >= target_matches:
            break
        
        output_path = os.path.join(output_dir, f"{match_id}.json")
        if os.path.exists(output_path):
            collected += 1
            continue  # 이미 수집됨
        
        match_data = scrape_match_detail(match_id)
        if match_data and match_data.get("maps"):
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(match_data, f, ensure_ascii=False)
            collected += 1
            if collected % 100 == 0:
                print(f"[INFO] 수집: {collected}개")
    
    print(f"[INFO] 완료: {collected}개 경기")
```

---

## 5. 예상 수집 볼륨

| 수집 범위 | 예상 경기 수 | 소요 시간 |
|---------|-----------|---------|
| 최근 50페이지 | ~1,500 | ~2시간 |
| 최근 200페이지 | ~6,000 | ~8시간 |
| 전체 (모든 기간) | 10,000+ | ~2일+ |

> **권장:** 처음에는 최근 50페이지로 시작 후, 볼륨 확인 후 확장

---

## 6. 의존성

```bash
pip install httpx beautifulsoup4 lxml
```
