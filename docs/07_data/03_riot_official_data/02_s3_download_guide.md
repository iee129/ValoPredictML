# 02. Riot VCT S3 다운로드 가이드

## 1. 사전 준비

### 1.1 의존성 설치

```bash
# 가상환경 활성화
source .venv/bin/activate

# AWS S3 접근을 위한 boto3 (익명 접근용)
pip install boto3 tqdm requests

# 또는 requirements.txt에 추가:
# boto3>=1.28.0
# tqdm>=4.65.0
```

### 1.2 AWS CLI (선택적)

```bash
# macOS
brew install awscli

# pip
pip install awscli

# 익명 접근이므로 자격증명 불필요
aws configure set default.s3.signature_version s3
```

---

## 2. 버킷 구조 탐색

### 2.1 Python으로 버킷 인덱스 확인

```python
import boto3
from botocore import UNSIGNED
from botocore.client import Config
import json

BUCKET_NAME = "vcthackathon-data"

def list_bucket_structure(prefix: str = "", max_keys: int = 100) -> list:
    """S3 버킷 구조 탐색"""
    s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED), region_name="us-east-1")
    
    response = s3.list_objects_v2(
        Bucket=BUCKET_NAME,
        Prefix=prefix,
        Delimiter="/",
        MaxKeys=max_keys
    )
    
    prefixes = [p["Prefix"] for p in response.get("CommonPrefixes", [])]
    files = [obj["Key"] for obj in response.get("Contents", [])]
    
    return {"prefixes": prefixes, "files": files}

# 최상위 구조 확인
structure = list_bucket_structure()
print("최상위 폴더:", structure["prefixes"])
# 예상: ['international/', 'americas/', 'emea/', 'pacific/', 'game_changers/']
```

### 2.2 게임 ID 목록 추출

```python
def get_all_game_ids(league: str, year: str) -> list[str]:
    """특정 리그/연도의 모든 game_id 추출"""
    s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED), region_name="us-east-1")
    
    prefix = f"{league}/{year}/games/"
    game_ids = []
    paginator = s3.get_paginator("list_objects_v2")
    
    for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            # key 형식: league/year/games/{game_id}/{file_type}.json
            parts = key.split("/")
            if len(parts) >= 5:
                game_id = parts[3]
                if game_id not in game_ids:
                    game_ids.append(game_id)
    
    print(f"[INFO] {league}/{year}: {len(game_ids)} 게임 발견")
    return game_ids
```

---

## 3. 다운로드 코드

### 3.1 단일 파일 다운로드

```python
import os
import json
import boto3
from botocore import UNSIGNED
from botocore.client import Config

BUCKET_NAME = "vcthackathon-data"
LOCAL_DIR = "data/raw/riot_s3"

def download_file(s3_key: str, dest_dir: str = LOCAL_DIR) -> str | None:
    """S3에서 단일 파일 다운로드"""
    s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED), region_name="us-east-1")
    
    local_path = os.path.join(dest_dir, s3_key)
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    
    if os.path.exists(local_path):
        return local_path  # 이미 다운로드됨
    
    try:
        s3.download_file(BUCKET_NAME, s3_key, local_path)
        return local_path
    except Exception as e:
        print(f"[ERROR] {s3_key}: {e}")
        return None
```

### 3.2 대량 병렬 다운로드

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import time

def download_league_data(
    league: str, 
    year: str, 
    file_types: list[str] = ["mapping", "scoreboard"],
    max_workers: int = 8,
    delay_between_requests: float = 0.1
) -> dict:
    """특정 리그/연도의 모든 데이터 병렬 다운로드"""
    
    game_ids = get_all_game_ids(league, year)
    
    # 다운로드할 파일 키 목록 생성
    keys_to_download = []
    for game_id in game_ids:
        for file_type in file_types:
            key = f"{league}/{year}/games/{game_id}/{file_type}.json"
            keys_to_download.append(key)
    
    print(f"[INFO] 다운로드 대상: {len(keys_to_download)} 파일")
    
    results = {"success": [], "failed": []}
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(download_file, key): key for key in keys_to_download}
        
        with tqdm(total=len(futures), desc=f"{league}/{year}") as pbar:
            for future in as_completed(futures):
                key = futures[future]
                result = future.result()
                if result:
                    results["success"].append(key)
                else:
                    results["failed"].append(key)
                pbar.update(1)
                time.sleep(delay_between_requests)
    
    print(f"[INFO] 완료: {len(results['success'])} 성공, {len(results['failed'])} 실패")
    return results


# 실행 예시
if __name__ == "__main__":
    # 우선순위 순서로 다운로드
    DOWNLOAD_PLAN = [
        ("international", "2023"),
        ("americas", "2023"),
        ("emea", "2023"),
        ("pacific", "2023"),
        ("international", "2022"),
        ("game_changers", "2023"),
        ("game_changers", "2022"),
    ]
    
    for league, year in DOWNLOAD_PLAN:
        download_league_data(
            league=league,
            year=year,
            file_types=["mapping", "scoreboard"],
            max_workers=8
        )
```

---

## 4. 디스크 공간 추정

| 파일 타입 | 파일당 크기 | 파일 수 | 총 크기 |
|---------|---------|--------|--------|
| `mapping.json` | ~5KB | ~4,300 | ~21MB |
| `scoreboard.json` | ~50KB | ~4,300 | ~215MB |
| `game_timeline.json` | ~5MB | ~4,300 | ~21GB |

> **권장:** 처음에는 `mapping` + `scoreboard`만 다운로드 (약 240MB)  
> `game_timeline`은 더 풍부한 피처 추출이 필요할 때 선택적으로 다운로드

---

## 5. 다운로드 후 검증

```python
import os, json, glob

def verify_downloads(local_dir: str = "data/raw/riot_s3") -> dict:
    """다운로드된 파일 무결성 검증"""
    json_files = glob.glob(os.path.join(local_dir, "**/*.json"), recursive=True)
    
    stats = {"total": len(json_files), "valid": 0, "invalid": []}
    
    for f in json_files:
        try:
            with open(f) as fp:
                data = json.load(fp)
            if data:  # 빈 JSON 체크
                stats["valid"] += 1
        except json.JSONDecodeError:
            stats["invalid"].append(f)
        except Exception as e:
            stats["invalid"].append(f)
    
    print(f"[INFO] 전체: {stats['total']}, 유효: {stats['valid']}, 오류: {len(stats['invalid'])}")
    return stats
```

---

## 6. 다음 단계

- [03_data_structure.md](03_data_structure.md) — 다운로드된 JSON 파싱 및 피처 추출
- [../../08_feature_engineering/](../08_feature_engineering/) — 피처 엔지니어링 전략
