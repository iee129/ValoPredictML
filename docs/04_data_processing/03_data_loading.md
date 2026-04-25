# 03. 데이터 로드 및 컬럼 표준화

## 1. 멀티 CSV 로드

```python
import pandas as pd
import glob
import os

def load_kaggle_data(raw_dir: str = "data/raw") -> pd.DataFrame:
    """
    data/raw/ 하위 모든 CSV 파일을 로드하고 병합한다.
    소스별 다른 구조를 하나의 표준 컬럼으로 통일한다.
    """
    all_files = glob.glob(os.path.join(raw_dir, "**", "*.csv"), recursive=True)
    
    if not all_files:
        raise FileNotFoundError(f"CSV 파일 없음: {raw_dir}")
    
    dfs = []
    for f in sorted(all_files):
        df = pd.read_csv(f, low_memory=False)
        df["_source_file"] = os.path.basename(f)  # 소스 추적용
        dfs.append(df)
    
    combined = pd.concat(dfs, ignore_index=True)
    print(f"로드 완료: {len(all_files)}개 파일, {len(combined):,}행")
    return combined
```

---

## 2. 소스별 컬럼 매핑 테이블

각 Kaggle 데이터셋은 서로 다른 컬럼명을 사용한다.

| 표준 컬럼명 | VCT 2021 | VCT 2022 | VCT 2023 | HenrikDev |
|---|---|---|---|---|
| `match_id` | `gameid` | `match_id` | `match_id` | `metadata.match_id` |
| `team_id` | `teamname` | `team` | `team_id` | `team` |
| `agent_name` | `agent` | `character` | `agent` | `agent.name` |
| `team_won` | `result` | `win` | `outcome` | `won` |
| `map_name` | `map` | `map` | `map` | `metadata.map.name` |
| `round_number` | `roundsplayed` | `rounds` | `rounds_played` | — |

```python
COLUMN_MAPPING = {
    # VCT 2021
    "gameid": "match_id",
    "teamname": "team_id",
    "agent": "agent_name",
    "result": "team_won",
    "map": "map_name",
    "roundsplayed": "round_count",
    # VCT 2022
    "character": "agent_name",
    "win": "team_won",
    "rounds": "round_count",
    # VCT 2023
    "team_id": "team_id",   # 이미 표준
    "outcome": "team_won",
    "rounds_played": "round_count",
}

def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {k: v for k, v in COLUMN_MAPPING.items() if k in df.columns}
    df = df.rename(columns=rename_map)
    return df
```

---

## 3. 필수 컬럼 확인

```python
REQUIRED_COLUMNS = ["match_id", "team_id", "agent_name", "team_won", "map_name"]

def validate_columns(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"필수 컬럼 없음: {missing}")
    return df[REQUIRED_COLUMNS]  # 필요 컬럼만 선택
```

---

## 4. 데이터 타입 통일

```python
def normalize_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    # 문자열 정규화
    df["match_id"] = df["match_id"].astype(str).str.strip()
    df["team_id"] = df["team_id"].astype(str).str.strip()
    df["agent_name"] = df["agent_name"].astype(str).str.strip()
    df["map_name"] = df["map_name"].astype(str).str.strip()
    
    # 승패 → bool
    won_mapping = {
        "win": True, "Win": True, "WIN": True, "1": True, "True": True, True: True,
        "loss": False, "Loss": False, "LOSS": False, "0": False, "False": False, False: False,
    }
    df["team_won"] = df["team_won"].map(won_mapping)
    df = df.dropna(subset=["team_won"])
    df["team_won"] = df["team_won"].astype(bool)
    
    return df
```

---

## 5. 맵 이름 정규화

발로란트 맵 이름은 영어 대문자로 시작하는 고유명사이다.

```python
VALID_MAPS = {
    "Ascent", "Bind", "Haven", "Split", "Fracture",
    "Pearl", "Lotus", "Sunset", "Abyss",
}

# 구형 맵 (제거된 맵들)
LEGACY_MAPS = {"Icebox", "Breeze", "District", "Piazza", "Kasbah", "Drift"}

def normalize_map_name(map_name: str) -> str:
    """대소문자 정규화 후 유효 맵 반환, 아니면 'Other'"""
    # 앞뒤 공백 제거, 첫 글자 대문자
    normalized = map_name.strip().title()
    if normalized in VALID_MAPS:
        return normalized
    return "Other"
```

---

## 6. 전체 로드 파이프라인

```python
def load_and_preprocess(raw_dir: str = "data/raw") -> pd.DataFrame:
    df = load_kaggle_data(raw_dir)
    df = standardize_columns(df)
    df = validate_columns(df)
    df = normalize_dtypes(df)
    df["map_name"] = df["map_name"].apply(normalize_map_name)
    
    # "Other" 맵 제외 (학습 데이터 품질 유지)
    before = len(df)
    df = df[df["map_name"] != "Other"]
    print(f"맵 필터 후: {before:,} → {len(df):,}행")
    
    return df
```

---

## 7. 관련 문서

| 문서 | 내용 |
|---|---|
| [04_data_cleaning.md](04_data_cleaning.md) | 중복 제거, 결측값 처리 |
| [05_aggregation.md](05_aggregation.md) | 플레이어 행 → 경기 행 집계 |
