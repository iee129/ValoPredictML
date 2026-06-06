# 03. ML 파이프라인 파일 상세 (`src/`)

마지막 업데이트: 2026-06-06

## 1. 폴더 전체 구조 (src-layout, `pip install -e .`)

```
src/
├── domain/                 # 도메인 상수
│   ├── valorant.py         # 요원→역할 매핑, 맵 목록, 정규화 함수 (완료)
│   └── agent_roles.py      # 요원→역할군 매핑, 맵 목록 (완료)
├── data/                   # 원천 수집·인제스트
│   ├── dataload.py         # Kaggle 데이터셋 다운로드 (구 dataload.py)
│   ├── ingest.py           # 통합 인제스트 raw → data/processed/ (구 ml/advanced/preprocess.py)
│   └── raw_preprocess.py   # VLR.gg raw → 검사용 CSV (리포트 전용)
├── features/               # 피처 빌더·EDA·split 생성
│   ├── preprocess.py       # 활성 피처 빌더: baseline 421·advanced 179 두 계약 포함 (구 ml/baseline/preprocess.py)
│   ├── eda.py              # EDA 차트 생성
│   └── chrono_preprocess.py  # 시간순 연도블록 분할 (구 ml/advanced/chrono_preprocess.py)
├── ml/                     # 모델 학습·평가·검증만 (모듈 경로 ml.baseline.* / ml.advanced.* 유지)
│   ├── baseline/           # 베이스라인 (랜덤 Test AUC 0.5943, 421피처, LR+DT)
│   │   ├── train.py        # 베이스라인 모델 학습
│   │   ├── evaluate.py     # GroupKFold CV + feature_importances_
│   │   └── validate.py     # 지표 검증
│   └── advanced/           # RF + XGBoost + LightGBM 앙상블 (시간순 Test AUC 0.7010, 179피처)
│       ├── ensemble.py     # Soft Voting 앙상블 학습
│       ├── evaluate.py     # train/val/test 평가
│       ├── validate.py     # 구조·성능 검증
│       ├── chrono_evaluate.py
│       ├── optimize.py     # HPO (rf/xgb/lgbm best_params)
│       ├── feature_importance.py
│       └── shap_analysis.py  # SHAP TreeExplainer 분석 (현재 feature_importances_/휴리스틱 사용)
├── insights/               # 인사이트 사전 집계
│   └── build_insights.py
├── inference/              # 런타임 예측 로직
│   └── predict.py          # 모델 로드 + 추론 (구 app/predict.py, FastAPI가 import)
└── api/                    # FastAPI 백엔드 (구 web/backend/)
    ├── main.py             # FastAPI 앱 진입점
    ├── schemas.py          # Pydantic v2 입출력 계약 (TS types/api.ts와 동기화)
    ├── serializers.py      # PredictionResult → JSON 직렬화, 자연어 근거 생성
    ├── deps.py             # 예외→HTTP 변환 (ValueError→422, FileNotFoundError→503)
    ├── routers/            # 라우터별 엔드포인트
    │   ├── predict.py      # POST /predict → save_prediction() 자동 저장 포함
    │   ├── replay.py       # GET /replay
    │   ├── options.py      # GET /options (요원·맵 목록)
    │   ├── model.py        # GET /model (모델 근거)
    │   ├── insights.py     # GET /insights
    │   └── history.py      # GET /history (예측 기록 조회)
    └── services/           # 비즈니스 로직
        ├── prediction.py   # src/inference/predict.py import·호출
        ├── insights.py     # 인사이트 사전 집계 로드
        └── history.py      # prediction_history 테이블 CRUD (SQLAlchemy Core)
```

---

## 2. 실행 순서

```bash
# Step 1: 데이터 다운로드 (완료)
python -m data.dataload

# Step 2a: 베이스라인 reference artifact
python -m ml.baseline.reference
python -m ml.baseline.validate

# Step 2b: 앙상블 파이프라인 (활성 진입점: features.chrono_preprocess --include-vlrgg)
python -m features.chrono_preprocess --include-vlrgg
python -m ml.advanced.ensemble   # RF(w=2.0)+XGB(w=3.0)+LGBM(w=0.1) soft voting
python -m ml.advanced.evaluate
# 참고: Optuna HPO는 향후 계획 — 현재 미사용
```

---

## 3. 파일별 역할 및 구조

### 3.1 `src/domain/valorant.py` — 공통 도메인 상수

**책임:** `baseline/`과 `advanced/` 양쪽에서 공통 참조하는 발로란트 도메인 지식.

- `AGENT_ROLE_MAP` — 요원 → 역할(Duelist/Initiator/Controller/Sentinel) 매핑
- `MAP_ORDER` — 공식 맵 목록
- `normalize_agent()`, `normalize_map()`, `normalize_team()` — 정규화 함수

---

### 3.2 `src/features/preprocess.py` — 베이스라인 전처리

**입력:** `data/raw/`  
**출력:** `data/processed/matches.csv`, `players.csv`, `teams.csv`, `features_lineup.csv`, `features_static.csv`, `files.csv`, `schemas.csv`, `sources.csv`, `rejects.csv`, `train.csv`, `test.csv`

파이프라인 단계:
1. **파싱** — Kaggle 소스별 파서 → 공통 스키마 행 생성
2. **품질 검사** — 팀당 요원 5개, 유효 요원/맵/레이블, `dedup_key` 중복 제거
3. **피처 엔지니어링** — 역할 카운트, 역할 차이, `map_encoded`, `has_controller_a/b`
4. **분할** — 80/20 (`match_key` 단위 GroupShuffleSplit, 같은 경기가 train/test에 겹치지 않음, 별도 검증셋 없이 train 내부 GroupKFold로 튜닝)

---

### 3.3 `src/ml/baseline/train.py` — 베이스라인 학습

**입력:** `data/processed/train.csv`  
**출력:** `models/baseline/model.joblib`, `models/baseline/meta.json`

---

### 3.4 `src/data/ingest.py` — 통합 인제스트 (raw → processed)

통합 인제스트(raw → processed). 피처 빌드 활성 경로: `features.chrono_preprocess --include-vlrgg`.

---

### 3.5 `src/ml/advanced/ensemble.py` — 앙상블 학습

**입력:** `data/processed/advanced/train.csv`
**출력:** `models/advanced/rf.joblib`, `models/advanced/xgb.joblib`, `models/advanced/lgbm.joblib`, `models/advanced/ensemble.joblib`, `models/advanced/meta.json`

- `train_rf()` — RandomForestClassifier, GroupKFold(n=5)
- `train_xgb()` — XGBClassifier, Early Stopping (Optuna HPO 향후 계획)
- `train_lgbm()` — LGBMClassifier, Early Stopping (Optuna HPO 향후 계획)
- 앙상블: VotingClassifier soft voting (weights=[2.0, 3.0, 0.1]) → 단일 `ensemble.joblib`으로 저장

**현재 성능:** Ensemble Test AUC 0.7010 / Acc 0.6454 / F1 0.6478 (시간순 split train2020–2025/test2026, 91,458개 맵 단위 승패 샘플, reports/advanced/metrics.json)

---

## 4. 파일 간 의존성 그래프

```
src/data/dataload.py
    ↓ (data/raw/kaggle/ 저장)
src/features/preprocess.py ──→ src/domain/valorant.py (공통 참조)
    └──→ data/processed/
              ↓
         src/ml/baseline/train.py
         └──→ models/baseline/

src/data/ingest.py ──→ src/domain/valorant.py (공통 참조)
    └──→ data/processed/
              ↓
         src/ml/advanced/ensemble.py
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
