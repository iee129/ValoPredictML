# 02. 데이터 수집 가이드

## 1. Kaggle 데이터셋 수집

### 1.1 사용 데이터셋

| 데이터셋 | URL | 용량 | 경기 수 |
|---|---|---|---|
| VCT 2021 | `ryncruz/valorant-championship-tour-2021` | ~15MB | ~800경기 |
| VCT 2022 | `visualize23/valorant-championship-tour-2022` | ~20MB | ~1,000경기 |
| VCT 2023 | `ryncruz/valorant-e-sports-stats` | ~25MB | ~1,200경기 |

### 1.2 `dataload.py` 구현

```python
import kagglehub
import os
import shutil

DATASETS = [
    ("ryncruz/valorant-championship-tour-2021", "data/raw/vct_2021"),
    ("visualize23/valorant-championship-tour-2022", "data/raw/vct_2022"),
    ("ryncruz/valorant-e-sports-stats", "data/raw/vct_2023"),
]

def download_dataset(dataset_id: str, target_dir: str):
    print(f"다운로드 중: {dataset_id}")
    path = kagglehub.dataset_download(dataset_id)
    os.makedirs(target_dir, exist_ok=True)
    for file in os.listdir(path):
        if file.endswith(".csv"):
            shutil.copy(os.path.join(path, file), target_dir)
    print(f"저장 완료: {target_dir}")

if __name__ == "__main__":
    for dataset_id, target_dir in DATASETS:
        download_dataset(dataset_id, target_dir)
```

### 1.3 Kaggle API 인증 설정

```bash
# 1. Kaggle 계정 → Account → API → "Create New API Token"
# 2. kaggle.json 파일 다운로드
# 3. 배치

# macOS / Linux
mkdir -p ~/.kaggle
mv ~/Downloads/kaggle.json ~/.kaggle/
chmod 600 ~/.kaggle/kaggle.json

# Windows
# %USERPROFILE%\.kaggle\kaggle.json
```

---

## 2. HenrikDev API 수집 (보조)

### 2.1 API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | HenrikDev Unofficial Valorant API |
| URL | https://api.henrikdev.xyz |
| 인증 | API Key (https://app.henrikdev.xyz에서 발급) |
| Rate Limit | 무료: 30req/min, 유료: 250req/min |
| 데이터 | 매치 히스토리, 요원, 맵, 결과 |

### 2.2 `ml/collect_matches.py` 구현

```python
import requests
import time
import json
import os
from backend.database import SessionLocal
from backend.db.models import MatchCache

HENRIK_API_URL = "https://api.henrikdev.xyz/valorant/v4"
API_KEY = os.getenv("HENRIK_API_KEY")

HEADERS = {
    "Authorization": API_KEY,
    "Content-Type": "application/json",
}

# 수집 대상 프로 플레이어 목록 (일부)
PRO_PLAYERS = [
    ("TenZ", "NA1"),
    ("yay", "NA1"),
    ("aspas", "BR1"),
    ("Derke", "EU1"),
]

def get_match_history(name: str, tag: str, mode="competitive", size=20) -> list:
    url = f"{HENRIK_API_URL}/matches/{name}/{tag}?mode={mode}&size={size}"
    resp = requests.get(url, headers=HEADERS, timeout=10)
    if resp.status_code == 200:
        return resp.json().get("data", [])
    return []

def save_match_to_db(match: dict):
    db = SessionLocal()
    try:
        existing = db.query(MatchCache).filter(
            MatchCache.match_id == match["metadata"]["match_id"]
        ).first()
        if not existing:
            cache = MatchCache(
                match_id=match["metadata"]["match_id"],
                raw_data=match,
                match_status="pending",
            )
            db.add(cache)
            db.commit()
    finally:
        db.close()

def collect_all():
    total = 0
    for name, tag in PRO_PLAYERS:
        matches = get_match_history(name, tag)
        for match in matches:
            save_match_to_db(match)
            total += 1
        time.sleep(2)  # Rate limit 준수
    print(f"수집 완료: {total}개 경기")

if __name__ == "__main__":
    collect_all()
```

### 2.3 HenrikDev 응답 구조

```json
{
  "metadata": {
    "match_id": "a1b2c3d4",
    "map": { "name": "Ascent" },
    "started_at": "2025-01-10T12:00:00Z"
  },
  "teams": {
    "red": { "won": true, "rounds_won": 13 },
    "blue": { "won": false, "rounds_won": 10 }
  },
  "players": {
    "red": [
      { "name": "TenZ", "tag": "NA1", "agent": { "name": "Jett" } }
    ],
    "blue": [...]
  }
}
```

---

## 3. 데이터 소스별 특성 비교

| 소스 | 장점 | 단점 | 수집 난이도 |
|---|---|---|---|
| Kaggle VCT | 대용량, 공개, 안정적 | 최신 요원 없음 | 쉬움 |
| HenrikDev API | 최신 데이터, 상세 | Rate Limit, 비공식 | 중간 |

---

## 4. 수집 주의사항

- **Kaggle**: `data/raw/`는 `.gitignore`에 포함 (용량)
- **HenrikDev**: API Key는 `.env` 파일에 보관, 하드코딩 금지
- 수집된 데이터는 `data/raw/` 또는 PostgreSQL `match_cache`에 보관
- 원본 데이터(`raw/`)는 절대 수정하지 않음

---

## 5. 관련 문서

| 문서 | 내용 |
|---|---|
| [../07_data/](../07_data/) | 데이터셋 상세 분석 |
| [03_data_loading.md](03_data_loading.md) | 수집된 데이터 로드 방법 |
