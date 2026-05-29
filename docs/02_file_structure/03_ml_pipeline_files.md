# 03. ML 파이프라인 파일 상세 (`ml/`)

마지막 업데이트: 2026-05-22

## 1. 폴더 전체 구조

```
ml/
├── __init__.py
├── valorant.py             # 요원→역할 매핑, 맵 목록, 정규화 함수 (완료)
├── agent_roles.py          # 요원→역할군 매핑, 맵 목록 (완료)
├── raw_preprocess.py       # Kaggle raw → data/processed/ 정제 (완료)
├── baseline/               # 베이스라인 모델 파이프라인 (완료, Test AUC 0.6587)
│   ├── __init__.py
│   ├── preprocess.py       # 전처리: 파서 → 품질 검사 → 피처 → 분할
│   ├── eda.py              # EDA 차트 생성
│   ├── train.py            # 베이스라인 모델 학습
│   ├── evaluate.py         # GroupKFold CV + SHAP
│   └── validate.py         # 지표 검증
├── advanced/               # RF + XGBoost + LightGBM 앙상블 (완료, Test AUC 0.7570)
│   ├── __init__.py
│   ├── preprocess.py       # (비활성) 구 advanced 전처리; 활성 경로: ml.baseline.preprocess --feature-contract advanced
│   ├── optimize.py         # Optuna HPO (rf/xgb/lgbm best_params, --n-trials 50)
│   ├── ensemble.py         # Soft Voting 앙상블 학습
│   ├── evaluate.py         # train/val/test 평가
│   ├── shap_analysis.py    # SHAP TreeExplainer 분석 (summary + importance)
│   ├── validate.py         # 구조·성능 검증
│   ├── chrono_preprocess.py  # 시간순 연도블록 분할 (비활성 실험)
│   └── svm_experiment.py   # SVM 사이드카 비교 (비승격 실험)
└── vlrgg/                  # VLR.gg 데이터 수집 (부분 구현)
    ├── __init__.py
    ├── client.py           # HTTP 클라이언트 (vlrggapi)
    ├── collector.py        # 데이터 수집 오케스트레이터
    ├── preprocess.py       # VLR.gg 수집 데이터 → matches.csv 포맷 변환
    └── worker.py           # 자동 수집 워커
```

---

## 2. 실행 순서

```bash
# Step 1: 데이터 다운로드 (완료)
python dataload.py

# Step 2a: 베이스라인 파이프라인
python -m ml.baseline.preprocess --input data/raw --output data/processed
python -m ml.baseline.train --input data/processed --output models/baseline
python -m ml.baseline.evaluate --input data/processed --models models/baseline

# Step 2b: 앙상블 파이프라인 (활성 진입점: ml.baseline.preprocess --feature-contract advanced)
python -m ml.baseline.preprocess --feature-contract advanced
python -m ml.advanced.optimize --models rf xgb lgbm --n-trials 50
python -m ml.advanced.ensemble --input data/processed/adv_kaggle_only --output models/advanced --reports reports/adv_kaggle_only
python -m ml.advanced.evaluate --input data/processed/adv_kaggle_only --models models/advanced --reports reports/adv_kaggle_only
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
**출력:** `data/processed/matches.csv`, `players.csv`, `teams.csv`, `features_lineup.csv`, `features_static.csv`, `files.csv`, `schemas.csv`, `sources.csv`, `rejects.csv`, `train.csv`, `test.csv`

파이프라인 단계:
1. **파싱** — Kaggle 소스별 파서 → 공통 스키마 행 생성
2. **품질 검사** — 팀당 요원 5개, 유효 요원/맵/레이블, `dedup_key` 중복 제거
3. **피처 엔지니어링** — 역할 카운트, 역할 차이, `map_encoded`, `has_controller_a/b`
4. **분할** — 80/20 (`match_key` 단위 GroupShuffleSplit, 같은 경기가 train/test에 겹치지 않음, 별도 검증셋 없이 train 내부 GroupKFold로 튜닝)

---

### 3.3 `ml/baseline/train.py` — 베이스라인 학습

**입력:** `data/processed/train.csv`  
**출력:** `models/baseline/model.joblib`, `models/baseline/meta.json`

---

### 3.4 `ml/advanced/preprocess.py` — 앙상블 전처리 (비활성)

**(비활성) 구 advanced 전처리 — 활성 경로: `ml.baseline.preprocess --feature-contract advanced`**

---

### 3.5 `ml/advanced/ensemble.py` — 앙상블 학습

**입력:** `data/processed/adv_kaggle_only/train.csv`  
**출력:** `models/advanced/rf.joblib`, `models/advanced/xgb.joblib`, `models/advanced/lgbm.joblib`, `models/advanced/ensemble.joblib`, `models/advanced/meta.json`

- `train_rf()` — RandomForestClassifier, GroupKFold(n=5)
- `train_xgb()` — XGBClassifier, Early Stopping, Optuna HPO
- `train_lgbm()` — LGBMClassifier, Early Stopping, Optuna HPO
- 앙상블: VotingClassifier soft voting (weights=[1,1,1]) → 단일 `ensemble.joblib`으로 저장

**현재 성능:** Ensemble Test AUC 0.7570 (adv_kaggle_only 실측, reports/adv_kaggle_only/metrics.json)

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
| `data/processed/matches.csv` | 품질 검사·dedup 통과한 맵 행 |
| `data/processed/players.csv` | 선수 스탯 집계 |
| `data/processed/teams.csv` | 팀별 집계 |
| `data/processed/features_lineup.csv` | 요원 조합 피처 |
| `data/processed/features_static.csv` | 정적 피처 (맵·역할군 등) |
| `data/processed/files.csv` | 소스 파일 레지스트리 |
| `data/processed/schemas.csv` | 스키마 정의 |
| `data/processed/sources.csv` | 소스별 메타데이터 |
| `data/processed/rejects.csv` | 품질 검사에서 제외된 행 |
| `data/processed/train.csv` | 학습셋 (80%) |
| `data/processed/test.csv` | 테스트셋 (20%) |
| `models/baseline/model.joblib` | 베이스라인 학습 모델 |
| `models/advanced/{rf,xgb,lgbm}.joblib` | 앙상블 개별 모델 |
| `models/advanced/ensemble.joblib` | Soft Voting 앙상블 (서빙용) |
| `models/baseline/meta.json` | 학습 날짜·지표 |
| `models/advanced/meta.json` | 학습 날짜·AUC·Acc·F1 |

---

## 6. 관련 문서

| 문서 | 내용 |
|------|------|
| [../03_architecture/06_ml_pipeline_architecture.md](../03_architecture/06_ml_pipeline_architecture.md) | ML 파이프라인 아키텍처 다이어그램 |
