# 03. ML 파이프라인 파일 상세 (`ml/`)

마지막 업데이트: 2026-05-22

## 1. 폴더 전체 구조

```
ml/
├── __init__.py
├── valorant.py             # 요원→역할 매핑, 맵 목록, 정규화 함수 (미구현)
├── baseline/               # 단순 베이스라인 모델 파이프라인 (미구현)
│   ├── __init__.py
│   ├── preprocess.py       # 전처리: 파서 → 품질 게이트 → 피처 → 분할
│   ├── train.py            # 베이스라인 모델 학습
│   ├── evaluate.py         # GroupKFold CV + SHAP
│   └── validate.py         # 지표 검증
├── advanced/               # RF + XGBoost + LightGBM 앙상블 (미구현)
│   ├── __init__.py
│   ├── preprocess.py       # 전처리 (baseline 확장 또는 독립)
│   ├── ensemble.py         # 앙상블 학습
│   ├── evaluate.py         # GroupKFold CV + SHAP
│   └── validate.py         # 지표 검증
└── vlrgg/                  # VLR.gg 데이터 수집 (부분 구현)
    ├── __init__.py
    ├── client.py           # HTTP 클라이언트 (vlrggapi)
    ├── collector.py        # 데이터 수집 오케스트레이터
    └── worker.py           # 자동 수집 워커
```

---

## 2. 실행 순서 (구현 예정)

```bash
# Step 1: 데이터 다운로드 (완료)
python dataload.py

# Step 2a: 베이스라인 파이프라인
python -m ml.baseline.preprocess --input data/raw --output data/processed
python -m ml.baseline.train --input data/processed --output models/baseline
python -m ml.baseline.evaluate --input data/processed --models models/baseline

# Step 2b: 앙상블 파이프라인
python -m ml.advanced.preprocess --input data/raw --output data/processed
python -m ml.advanced.ensemble --input data/processed --output models/advanced
python -m ml.advanced.evaluate --input data/processed --models models/advanced
```

---

## 3. 파일별 역할 및 구조

### 3.1 `ml/valorant.py` — 공통 도메인 상수

**책임:** `baseline/`과 `advanced/` 양쪽에서 공통 참조하는 발로란트 도메인 지식.

- `AGENT_ROLE_MAP` — 요원 → 역할(Duelist/Initiator/Controller/Sentinel) 매핑
- `MAP_ORDER` — 공식 맵 목록
- `normalize_agent()`, `normalize_map()`, `normalize_team()` — 정규화 함수

---

### 3.2 `ml/baseline/preprocess.py` — 베이스라인 전처리

**입력:** `data/raw/`  
**출력:** `data/processed/matches.csv`, `players.csv`, `teams.csv`, `features_lineup.csv`, `features_static.csv`, `files.csv`, `schemas.csv`, `sources.csv`, `rejects.csv`, `train.csv`, `val.csv`, `test.csv`

파이프라인 단계:
1. **파싱** — Kaggle 소스별 파서 → 공통 스키마 행 생성
2. **품질 게이트** — 팀당 요원 5개, 유효 요원/맵/레이블, `dedup_key` 중복 제거
3. **피처 엔지니어링** — 역할 카운트, 역할 차이, `map_encoded`, `has_controller_a/b`
4. **분할** — 70/15/15 (`match_key` 단위 GroupShuffleSplit, 경기 누수 없음)

---

### 3.3 `ml/baseline/train.py` — 베이스라인 학습

**입력:** `data/processed/train.csv`  
**출력:** `models/baseline/model.joblib`, `models/baseline/meta.json`

---

### 3.4 `ml/advanced/preprocess.py` — 앙상블 전처리

baseline과 동일하거나 확장된 전처리. advanced 전용 피처(선수 통계 등) 추가 가능.

---

### 3.5 `ml/advanced/ensemble.py` — 앙상블 학습

**입력:** `data/processed/train.csv`  
**출력:** `models/advanced/rf.joblib`, `models/advanced/xgb.joblib`, `models/advanced/lgbm.joblib`, `models/advanced/meta.json`

- `train_rf()` — RandomForestClassifier, GroupKFold(n=5)
- `train_xgb()` — XGBClassifier, Early Stopping, Optuna HPO
- `train_lgbm()` — LGBMClassifier, Early Stopping, Optuna HPO
- 앙상블: 세 모델 예측 확률 평균

**성능 목표:** Ensemble AUC ≥ 0.933 (구 파이프라인 달성 기준)

---

## 4. 파일 간 의존성 그래프

```
dataload.py
    ↓ (data/raw/kaggle/ 저장)
ml/baseline/preprocess.py ──→ ml/valorant.py (공통 참조)
    └──→ data/processed/
              ↓
         ml/baseline/train.py
         └──→ models/baseline/

ml/advanced/preprocess.py ──→ ml/valorant.py (공통 참조)
    └──→ data/processed/
              ↓
         ml/advanced/ensemble.py
         └──→ models/advanced/
```

---

## 5. 출력 파일

| 경로 | 내용 |
|------|------|
| `data/processed/matches.csv` | 품질 게이트·dedup 통과한 맵 행 |
| `data/processed/players.csv` | 선수 스탯 집계 |
| `data/processed/teams.csv` | 팀별 집계 |
| `data/processed/features_lineup.csv` | 요원 조합 피처 |
| `data/processed/features_static.csv` | 정적 피처 (맵·역할군 등) |
| `data/processed/files.csv` | 소스 파일 레지스트리 |
| `data/processed/schemas.csv` | 스키마 정의 |
| `data/processed/sources.csv` | 소스별 메타데이터 |
| `data/processed/rejects.csv` | 품질 게이트 탈락 행 |
| `data/processed/train.csv` | 학습셋 (70%) |
| `data/processed/val.csv` | 검증셋 (15%) |
| `data/processed/test.csv` | 테스트셋 (15%) |
| `models/baseline/model.joblib` | 베이스라인 학습 모델 |
| `models/advanced/{rf,xgb,lgbm}.joblib` | 앙상블 개별 모델 |
| `models/baseline/meta.json` | 학습 날짜·지표 |
| `models/advanced/meta.json` | 학습 날짜·AUC·Acc·F1 |

---

## 6. 관련 문서

| 문서 | 내용 |
|------|------|
| [../03_architecture/06_ml_pipeline_architecture.md](../03_architecture/06_ml_pipeline_architecture.md) | ML 파이프라인 아키텍처 다이어그램 |
