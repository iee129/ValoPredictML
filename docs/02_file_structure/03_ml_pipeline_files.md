# 03. ML 파이프라인 파일 상세 (`ml/`)

## 1. 폴더 전체 구조

```
ml/
├── data_pipeline.py            # 데이터 로드 및 전처리
├── feature_engineering.py      # 피처 생성
├── train.py                    # 모델 학습 스크립트
├── evaluate.py                 # 모델 평가
├── optimize.py                 # Optuna 하이퍼파라미터 최적화
├── utils.py                    # 공통 유틸리티
└── collect_matches.py          # HenrikDev API 데이터 수집 (선택)
```

---

## 2. 실행 순서

```bash
# Step 1: 데이터 전처리 (raw/ → processed/)
python ml/data_pipeline.py

# Step 2: 하이퍼파라미터 최적화 (약 30~60분)
python ml/optimize.py

# Step 3: 최적 파라미터로 최종 모델 학습
python ml/train.py

# Step 4: 성능 평가 및 리포트 출력
python ml/evaluate.py
```

---

## 3. 파일별 역할 및 구조

### 3.1 `data_pipeline.py` — 데이터 로드 및 전처리

**입력:** `data/raw/**/*.csv`  
**출력:** `data/processed/train.csv`, `val.csv`, `test.csv`

```python
import pandas as pd
import glob
from ml.feature_engineering import create_features
from sklearn.model_selection import train_test_split

def load_kaggle_data(raw_dir: str = "data/raw") -> pd.DataFrame:
    """멀티 CSV 로드 및 concat"""
    all_files = glob.glob(f"{raw_dir}/**/*.csv", recursive=True)
    dfs = [pd.read_csv(f) for f in all_files]
    return pd.concat(dfs, ignore_index=True)

def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """소스별 컬럼명 통일"""
    column_mapping = {
        "agent": "agent_name",
        "character": "agent_name",
        "result": "team_won",
        "outcome": "team_won",
        "gameid": "match_id",
        # ... 소스별 매핑
    }
    return df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """match_id + team_id 기준 중복 제거"""
    return df.drop_duplicates(subset=["match_id", "team_id", "agent_name"])

def aggregate_to_match_level(df: pd.DataFrame) -> pd.DataFrame:
    """플레이어 단위 데이터 → 경기 단위 집계"""
    # 같은 match_id의 5명을 1행으로 묶음
    ...

def split_and_save(df: pd.DataFrame):
    """Stratified Split: 70/15/15"""
    train, temp = train_test_split(df, test_size=0.30, stratify=df["label"], random_state=42)
    val, test = train_test_split(temp, test_size=0.50, stratify=temp["label"], random_state=42)
    train.to_csv("data/processed/train.csv", index=False)
    val.to_csv("data/processed/val.csv", index=False)
    test.to_csv("data/processed/test.csv", index=False)
```

---

### 3.2 `feature_engineering.py` — 피처 생성

**입력:** 경기 단위 DataFrame (요원 리스트 포함)  
**출력:** 15개 피처 + `label` 컬럼

```python
from ml.agent_roles import get_role  # backend/ml/agent_roles.py와 공유

ROLES = ["Duelist", "Initiator", "Controller", "Sentinel"]

def get_role_counts(agents: list) -> dict:
    counts = {role: 0 for role in ROLES}
    for agent in agents:
        role = get_role(agent)
        if role in counts:
            counts[role] += 1
    return counts

def create_features(team_a: list, team_b: list, map_name: str, le_map) -> pd.Series:
    a_counts = get_role_counts(team_a)
    b_counts = get_role_counts(team_b)

    features = {}
    for role in ROLES:
        features[f"team_a_{role.lower()}_count"] = a_counts[role]
        features[f"team_b_{role.lower()}_count"] = b_counts[role]
        features[f"{role.lower()}_diff"] = a_counts[role] - b_counts[role]

    features["team_a_has_controller"] = int(a_counts["Controller"] >= 1)
    features["team_b_has_controller"] = int(b_counts["Controller"] >= 1)
    features["map_encoded"] = le_map.transform([map_name])[0]

    return pd.Series(features)
```

---

### 3.3 `train.py` — 모델 학습

**입력:** `data/processed/train.csv`, `val.csv`  
**출력:** `models/xgboost_model.joblib`, `models/lgbm_model.joblib`, `models/model_metadata.json`

```python
import xgboost as xgb
import lightgbm as lgb
import joblib
import json

FEATURE_COLS = [
    "team_a_duelist_count", "team_a_initiator_count",
    "team_a_controller_count", "team_a_sentinel_count",
    "team_b_duelist_count", "team_b_initiator_count",
    "team_b_controller_count", "team_b_sentinel_count",
    "duelist_diff", "initiator_diff", "controller_diff", "sentinel_diff",
    "team_a_has_controller", "team_b_has_controller",
    "map_encoded"
]

def train_xgboost(X_train, y_train, X_val, y_val, params: dict):
    model = xgb.XGBClassifier(**params, early_stopping_rounds=50, eval_metric="logloss")
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=100)
    joblib.dump(model, "models/xgboost_model.joblib")
    return model

def train_lightgbm(X_train, y_train, X_val, y_val, params: dict):
    model = lgb.LGBMClassifier(**params)
    model.fit(X_train, y_train,
              eval_set=[(X_val, y_val)],
              callbacks=[lgb.early_stopping(50), lgb.log_evaluation(100)])
    joblib.dump(model, "models/lgbm_model.joblib")
    return model
```

---

### 3.4 `optimize.py` — Optuna 하이퍼파라미터 최적화

**입력:** `data/processed/train.csv`, `val.csv`  
**출력:** 최적 파라미터 (터미널 출력 + JSON 저장)

```python
import optuna

def objective_xgb(trial):
    params = {
        "max_depth": trial.suggest_int("max_depth", 3, 8),
        "n_estimators": trial.suggest_int("n_estimators", 100, 800),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "subsample": trial.suggest_float("subsample", 0.5, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
        "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
    }
    # 5-Fold CV로 평가
    ...
    return cv_score

study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler())
study.optimize(objective_xgb, n_trials=100, timeout=3600)
```

---

### 3.5 `evaluate.py` — 모델 평가

**입력:** `models/*.joblib`, `data/processed/test.csv`  
**출력:** 터미널 리포트 + `reports/training_report.json`

**출력 내용:**
- Accuracy, F1-Score (Macro), ROC-AUC
- Confusion Matrix
- Train-Val 갭 (과적합 여부)
- 피처 중요도 상위 10개

---

### 3.6 `utils.py` — 공통 유틸리티

```python
import logging
import os

def setup_logger(name: str, level=logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(handler)
    return logger

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)
```

---

## 4. 파일 간 의존성 그래프

```
dataload.py
    ↓ (data/raw/ 저장)
data_pipeline.py
    ├──→ feature_engineering.py
    └──→ data/processed/ 저장
         ↓
    optimize.py
         ↓ (최적 파라미터)
    train.py
    ├──→ feature_engineering.py
    └──→ models/ 저장
         ↓
    evaluate.py
    └──→ reports/ 저장
```

---

## 5. 관련 문서

| 문서 | 내용 |
|---|---|
| [../04_data_processing/](../04_data_processing/) | 데이터 전처리 전략 상세 |
| [../05_data_learning/](../05_data_learning/) | 모델 학습 전략 상세 |
| [../03_architecture/06_ml_pipeline_architecture.md](../03_architecture/06_ml_pipeline_architecture.md) | ML 파이프라인 아키텍처 다이어그램 |
