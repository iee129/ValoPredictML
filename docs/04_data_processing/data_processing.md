# 04. 데이터 로드 및 전처리 전략

## 1. 전처리 파이프라인 개요

```
[수집] → [로드] → [정제] → [집계] → [피처 생성] → [분할] → [저장]
```

전처리는 `ml/data_pipeline.py`와 `ml/feature_engineering.py` 두 모듈로 처리합니다.

---

## 2. 데이터 수집

### 2.1 Kaggle VCT 데이터셋 다운로드

```python
# dataload.py (현재 존재)
import kagglehub

path = kagglehub.dataset_download("ryanluong1/valorant-champion-tour-2021-2023-data")
print("Path to dataset files:", path)
```

> **주의:** `.venv` 가상환경에서 실행할 것.  
> 다운로드된 파일 경로를 확인 후 `data/raw/`로 복사합니다.

```bash
# 실행 방법
source .venv/bin/activate
python dataload.py
```

### 2.2 HenrikDev API 수집

```python
# ml/henrik_collector.py
import os
import requests
import pandas as pd
from time import sleep

API_KEY = os.environ["HENRIK_API_KEY"]
BASE_URL = "https://api.henrikdev.xyz/valorant/v4"

def fetch_recent_matches(name: str, tag: str, region: str = "ap", size: int = 20) -> list:
    """특정 플레이어의 최근 경기 목록 수집"""
    url = f"{BASE_URL}/matches/{region}/pc/{name}/{tag}"
    params = {"mode": "competitive", "size": size}
    headers = {"Authorization": API_KEY}
    
    resp = requests.get(url, params=params, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json().get("data", [])

def collect_and_save(player_list: list, output_path: str):
    """여러 플레이어의 경기 데이터 수집 후 CSV 저장"""
    all_rows = []
    for name, tag in player_list:
        try:
            matches = fetch_recent_matches(name, tag)
            for match in matches:
                row = extract_match_features(match)
                if row:
                    all_rows.append(row)
            sleep(0.5)  # API Rate Limit 준수
        except Exception as e:
            print(f"[WARN] {name}#{tag} 수집 실패: {e}")
    
    df = pd.DataFrame(all_rows)
    df.to_csv(output_path, index=False)
    print(f"[INFO] {len(df)} 경기 저장 → {output_path}")
```

---

## 3. 데이터 로드

### 3.1 CSV 멀티파일 로드 및 병합

```python
# ml/data_pipeline.py
import os
import glob
import pandas as pd

def load_raw_data(raw_dir: str = "data/raw") -> pd.DataFrame:
    """data/raw/ 하위 모든 CSV 파일 로드 및 병합"""
    csv_files = glob.glob(os.path.join(raw_dir, "**/*.csv"), recursive=True)
    
    if not csv_files:
        raise FileNotFoundError(f"CSV 파일이 없습니다: {raw_dir}")
    
    dfs = []
    for filepath in csv_files:
        try:
            df = pd.read_csv(filepath, encoding="utf-8")
            df["source_file"] = os.path.basename(filepath)
            dfs.append(df)
        except Exception as e:
            print(f"[WARN] 로드 실패: {filepath} → {e}")
    
    combined = pd.concat(dfs, ignore_index=True)
    print(f"[INFO] 로드 완료: {len(combined)} 행, {len(csv_files)} 파일")
    return combined
```

### 3.2 컬럼 표준화

Kaggle 데이터셋과 HenrikDev API 데이터의 컬럼명이 다를 수 있습니다.  
모든 소스를 **표준 컬럼명**으로 통일합니다.

```python
COLUMN_MAPPING = {
    # Kaggle VCT → 표준
    "match_id": "match_id",
    "map": "map",
    "player": "player_name",
    "team": "team_name",
    "agent": "agent",
    "winner": "winner",
    # HenrikDev → 표준 (extract_match_features에서 처리)
}

def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns=COLUMN_MAPPING)
    required = ["match_id", "map", "player_name", "team_name", "agent", "winner"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"필수 컬럼 누락: {missing}")
    return df
```

---

## 4. 데이터 정제

### 4.1 중복 제거

```python
def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """동일한 match_id + player_name 중복 제거"""
    before = len(df)
    df = df.drop_duplicates(subset=["match_id", "player_name"], keep="first")
    after = len(df)
    print(f"[INFO] 중복 제거: {before} → {after} 행 (-{before - after})")
    return df
```

### 4.2 결측값 처리

```python
def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """결측값 처리 전략"""
    
    # 핵심 컬럼 결측 → 행 제거
    critical_cols = ["match_id", "map", "agent", "team_name", "winner"]
    before = len(df)
    df = df.dropna(subset=critical_cols)
    print(f"[INFO] 핵심 컬럼 결측 제거: -{before - len(df)} 행")
    
    # 수치 컬럼 결측 → 0으로 대체 (역할군 카운트에 영향 없음)
    numeric_cols = ["kills", "deaths", "assists", "acs", "kd", "kast", "adr"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].fillna(0)
    
    return df
```

### 4.3 신규 요원 처리 (방어 로직)

```python
from ml.agent_roles import AGENT_ROLE_MAP

def safe_get_role(agent_name: str) -> str:
    """매핑에 없는 요원을 Unknown으로 처리 (오류 방지)"""
    role = AGENT_ROLE_MAP.get(agent_name)
    if role is None:
        print(f"[WARN] 알 수 없는 요원: '{agent_name}' → Unknown 처리")
        return "Unknown"
    return role
```

### 4.4 맵 유효성 검증

```python
VALID_MAPS = {
    "Bind", "Haven", "Split", "Ascent", "Icebox",
    "Breeze", "Fracture", "Pearl", "Lotus", "Sunset", "Abyss"
}

def validate_maps(df: pd.DataFrame) -> pd.DataFrame:
    unknown_maps = set(df["map"].unique()) - VALID_MAPS
    if unknown_maps:
        print(f"[WARN] 알 수 없는 맵 발견: {unknown_maps} → 해당 행 제거")
        df = df[df["map"].isin(VALID_MAPS)]
    return df
```

---

## 5. 경기 단위 집계

Kaggle 데이터는 **플레이어 행 단위**입니다.  
모델 학습을 위해 **경기(match) 단위**로 집계합니다.

```python
def aggregate_to_match_level(df: pd.DataFrame) -> pd.DataFrame:
    """
    플레이어 행 → 경기 행 변환
    
    입력: match_id, map, team_name, agent, winner 컬럼이 있는 플레이어 단위 DF
    출력: 경기 단위로 집계된 DF (1경기 = 1행)
    """
    
    match_rows = []
    
    for match_id, match_df in df.groupby("match_id"):
        # 팀 분리 (팀 이름 기준으로 team_a / team_b 구분)
        teams = match_df["team_name"].unique()
        if len(teams) != 2:
            continue  # 팀이 정확히 2개가 아니면 스킵
        
        team_a_name, team_b_name = teams[0], teams[1]
        team_a_df = match_df[match_df["team_name"] == team_a_name]
        team_b_df = match_df[match_df["team_name"] == team_b_name]
        
        # 각 팀 5명 확인
        if len(team_a_df) != 5 or len(team_b_df) != 5:
            continue
        
        # 역할군 카운트
        map_name = match_df["map"].iloc[0]
        winner = match_df["winner"].iloc[0]
        
        row = {
            "match_id": match_id,
            "map": map_name,
            "team_a": team_a_name,
            "team_b": team_b_name,
            "winner": winner,
        }
        
        # 팀별 역할군 카운트
        for team_key, team_df in [("team_a", team_a_df), ("team_b", team_b_df)]:
            roles = [safe_get_role(a) for a in team_df["agent"].tolist()]
            row[f"{team_key}_duelist"] = roles.count("Duelist")
            row[f"{team_key}_initiator"] = roles.count("Initiator")
            row[f"{team_key}_controller"] = roles.count("Controller")
            row[f"{team_key}_sentinel"] = roles.count("Sentinel")
        
        match_rows.append(row)
    
    result = pd.DataFrame(match_rows)
    print(f"[INFO] 경기 단위 집계 완료: {len(result)} 경기")
    return result
```

---

## 6. 피처 엔지니어링

### 6.1 전체 피처 생성 로직

```python
# ml/feature_engineering.py
from sklearn.preprocessing import LabelEncoder
import joblib

def create_features(df: pd.DataFrame, fit_encoder: bool = True) -> pd.DataFrame:
    """
    경기 단위 DF에서 모델 입력 피처 생성
    fit_encoder=True: 학습 시 (새로 fit)
    fit_encoder=False: 추론 시 (저장된 encoder 사용)
    """
    
    # 1. 맵 인코딩
    if fit_encoder:
        le_map = LabelEncoder()
        df["map_encoded"] = le_map.fit_transform(df["map"])
        joblib.dump(le_map, "models/label_encoder_map.joblib")
    else:
        le_map = joblib.load("models/label_encoder_map.joblib")
        # 미등록 맵 방어 처리
        df["map"] = df["map"].apply(
            lambda m: m if m in le_map.classes_ else le_map.classes_[0]
        )
        df["map_encoded"] = le_map.transform(df["map"])
    
    # 2. 차이(diff) 피처
    for role in ["duelist", "initiator", "controller", "sentinel"]:
        df[f"{role}_diff"] = df[f"team_a_{role}"] - df[f"team_b_{role}"]
    
    # 3. 전략가 보유 여부 (이진)
    df["team_a_has_controller"] = (df["team_a_controller"] > 0).astype(int)
    df["team_b_has_controller"] = (df["team_b_controller"] > 0).astype(int)
    
    # 4. 레이블 생성
    df["label"] = (df["winner"] == df["team_a"]).astype(int)
    
    return df

# 최종 피처 컬럼 목록
FEATURE_COLUMNS = [
    "team_a_duelist", "team_a_initiator", "team_a_controller", "team_a_sentinel",
    "team_b_duelist", "team_b_initiator", "team_b_controller", "team_b_sentinel",
    "map_encoded",
    "duelist_diff", "initiator_diff", "controller_diff", "sentinel_diff",
    "team_a_has_controller", "team_b_has_controller",
]
TARGET_COLUMN = "label"
```

---

## 7. Train / Validation / Test Split

### 전략: Stratified Split (70 / 15 / 15)

```python
from sklearn.model_selection import train_test_split

def split_data(df: pd.DataFrame):
    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN]
    
    # 1차: Train 70% vs Rest 30%
    X_train, X_rest, y_train, y_rest = train_test_split(
        X, y,
        test_size=0.30,
        random_state=42,
        stratify=y        # 클래스 비율 유지
    )
    
    # 2차: Rest → Val 50% / Test 50% (각 15%)
    X_val, X_test, y_val, y_test = train_test_split(
        X_rest, y_rest,
        test_size=0.50,
        random_state=42,
        stratify=y_rest
    )
    
    # 분할 결과 확인
    print(f"Train: {len(X_train)} | Val: {len(X_val)} | Test: {len(X_test)}")
    print(f"Train 양성 비율: {y_train.mean():.3f}")
    print(f"Val   양성 비율: {y_val.mean():.3f}")
    print(f"Test  양성 비율: {y_test.mean():.3f}")
    
    return X_train, X_val, X_test, y_train, y_val, y_test
```

### 왜 Stratified인가?
- 클래스 불균형 가능성 (특정 팀 조합이 더 많이 등장)
- 분할 후에도 승/패 비율이 균등하게 유지됨
- K-Fold에서도 `StratifiedKFold` 사용

---

## 8. 데이터 저장

```python
def save_processed_data(X_train, X_val, X_test, y_train, y_val, y_test):
    """전처리된 데이터 CSV로 저장"""
    os.makedirs("data/processed", exist_ok=True)
    
    train = pd.concat([X_train, y_train], axis=1)
    val = pd.concat([X_val, y_val], axis=1)
    test = pd.concat([X_test, y_test], axis=1)
    
    train.to_csv("data/processed/train.csv", index=False)
    val.to_csv("data/processed/val.csv", index=False)
    test.to_csv("data/processed/test.csv", index=False)
    
    print("[INFO] 전처리 데이터 저장 완료")
```

---

## 9. 전체 파이프라인 실행

```python
# ml/data_pipeline.py 메인 실행 흐름
if __name__ == "__main__":
    # 1. 데이터 로드
    df = load_raw_data("data/raw")
    
    # 2. 표준화
    df = standardize_columns(df)
    
    # 3. 정제
    df = remove_duplicates(df)
    df = handle_missing_values(df)
    df = validate_maps(df)
    
    # 4. 경기 단위 집계
    df = aggregate_to_match_level(df)
    
    # 5. 피처 생성
    df = create_features(df, fit_encoder=True)
    
    # 6. Split
    X_train, X_val, X_test, y_train, y_val, y_test = split_data(df)
    
    # 7. 저장
    save_processed_data(X_train, X_val, X_test, y_train, y_val, y_test)
```

---

## 10. 데이터 품질 검증 체크리스트

실행 후 아래 항목을 확인합니다.

| 체크 항목 | 확인 방법 | 기준 |
|---|---|---|
| 총 샘플 수 | `len(df)` | ≥ 3,000 경기 |
| 클래스 균형 | `df['label'].mean()` | 0.45 ~ 0.55 |
| 결측값 없음 | `df.isnull().sum()` | 모든 피처 0 |
| 역할군 합계 | `sum of role counts` | 각 팀 항상 합계 = 5 |
| 맵 인코딩 확인 | `df['map_encoded'].nunique()` | ≤ 11 |
| 중복 경기 없음 | `df['match_id'].duplicated().sum()` | 0 |

```python
def validate_processed_data(df: pd.DataFrame):
    """전처리 결과 자동 검증"""
    assert len(df) >= 3000, f"샘플 부족: {len(df)}"
    assert 0.40 <= df["label"].mean() <= 0.60, f"클래스 불균형: {df['label'].mean()}"
    assert df[FEATURE_COLUMNS].isnull().sum().sum() == 0, "결측값 존재"
    
    for team in ["team_a", "team_b"]:
        role_sum = (
            df[f"{team}_duelist"] + df[f"{team}_initiator"] +
            df[f"{team}_controller"] + df[f"{team}_sentinel"]
        )
        # Unknown 역할군 포함 시 5가 안 될 수 있으므로 ≤ 5 체크
        assert (role_sum <= 5).all(), f"{team} 역할군 합계 이상"
    
    print("[INFO] 데이터 검증 통과 ✅")
```
