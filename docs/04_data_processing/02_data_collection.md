# 02. 데이터 수집 가이드

마지막 업데이트: 2026-05-04

## 1. 수집 방침

외부 API 미사용 — Kaggle CSV 5개만 사용한다. HenrikDev API 등 외부 스크래핑은 범위 외.

---

## 2. 사용 데이터셋 (5개)

| 폴더 | Kaggle ID | 용량 | 기간 | 파서 | 소스 가중치 |
|------|-----------|------|------|------|------------|
| `vct_2021_2023` | `ryanluong1/valorant-champion-tour-2021-2023-data` | 1.2GB | 2021~2026 | ryanluong | 1.0 |
| `ryanluong1__valorant-challengers-league-data` | `ryanluong1/valorant-challengers-league-data` | 1.0GB | 2023~2024 | ryanluong | **1.8** |
| `qualidea1217__valorant-pro-matches-since-april-2021` | `qualidea1217/valorant-pro-matches-since-april-2021` | ~35MB | 2021~현재 | qualidea | 1.0 |
| `piyush86kumar__valorant-champions-2024` | `piyush86kumar/valorant-champions-2024` | ~15MB | 2024 | piyush | **1.5** |
| `ediashtarevin__vct-champions-2023-stats` | `ediashtarevin/vct-champions-2023-stats` | ~6K행 | 2023 | ediashtarevin | 0.9 |

**소스 가중치 정책**: 동일 경기가 두 소스에 존재할 때 어느 행을 남길지 결정. ryanluong challengers(1.8)가 공수 분리 스탯 포함으로 신뢰도 최고. 동점 시 컬럼 수가 많은 소스 우선.

---

## 3. `dataload.py` 구현

```python
import kagglehub
import os
import shutil

DATASETS = [
    ("ryanluong1/valorant-champion-tour-2021-2023-data",
     "data/raw/kaggle/vct_2021_2023"),
    ("ryanluong1/valorant-challengers-league-data",
     "data/raw/kaggle/ryanluong1__valorant-challengers-league-data"),
    ("qualidea1217/valorant-pro-matches-since-april-2021",
     "data/raw/kaggle/qualidea1217__valorant-pro-matches-since-april-2021"),
    ("piyush86kumar/valorant-champions-2024",
     "data/raw/kaggle/piyush86kumar__valorant-champions-2024"),
    ("ediashtarevin/vct-champions-2023-stats",
     "data/raw/kaggle/ediashtarevin__vct-champions-2023-stats"),
]

def download_dataset(dataset_id: str, target_dir: str):
    print(f"Downloading: {dataset_id}")
    path = kagglehub.dataset_download(dataset_id)
    os.makedirs(target_dir, exist_ok=True)
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(".csv"):
                rel = os.path.relpath(root, path)
                dest = os.path.join(target_dir, rel)
                os.makedirs(dest, exist_ok=True)
                shutil.copy(os.path.join(root, file), dest)
    print(f"Saved: {target_dir}")

if __name__ == "__main__":
    for dataset_id, target_dir in DATASETS:
        download_dataset(dataset_id, target_dir)
```

---

## 4. Kaggle API 인증 설정

```bash
# 1. Kaggle 계정 → Account → API → "Create New API Token"
# 2. kaggle.json 다운로드
# 3. 배치

# macOS / Linux
mkdir -p ~/.kaggle
mv ~/Downloads/kaggle.json ~/.kaggle/
chmod 600 ~/.kaggle/kaggle.json
```

API 키와 raw CSV는 절대 커밋 금지 — `data/raw/`는 `.gitignore`에 포함.

---

## 5. 소스별 파일 구조 요약

| 소스 | 핵심 파일 | 조인 필요 여부 |
|------|-----------|--------------|
| vct_2021_2023 | `players_stats/*.csv` + `maps_scores.csv` | 필요 (Match Name + Map) |
| ryanluong challengers | `overview.csv` + `maps_scores.csv` | 필요 (Match Name + Map) |
| qualidea1217 | `data-since-april-2021.csv` | 불필요 |
| piyush86kumar/valorant-champions-2024 | `detailed_matches_player_stats.csv` | 불필요 |
| ediashtarevin | `player_stats.csv` | 불필요 |

ryanluong 계열은 선수 스탯(`overview.csv`)과 팀 점수(`maps_scores.csv`)가 파일 2개로 분리되어 있어 `Match Name + Map` 키로 조인이 필수.

---

## 6. 수집 주의사항

- `data/raw/`는 `.gitignore`에 포함 (2.3GB, 커밋 금지)
- 원본 데이터(`raw/`)는 절대 수정하지 않음
- 재다운로드 시 덮어쓰기 허용 (내용 동일)

---

## 7. 관련 문서

| 문서 | 내용 |
|------|------|
| [03_data_loading.md](03_data_loading.md) | 소스별 파서 및 컬럼 매핑 |
| [../datasets.md](../datasets.md) | 5개 데이터셋 컬럼 상세 |
