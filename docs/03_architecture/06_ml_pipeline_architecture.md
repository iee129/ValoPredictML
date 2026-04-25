# 06. ML 파이프라인 아키텍처

## 1. 전체 파이프라인 다이어그램

```
┌─────────────────────────────────────────────────────────────┐
│                       데이터 수집 단계                        │
│                                                             │
│  ┌──────────────────┐    ┌─────────────────────────────┐   │
│  │  Kaggle Datasets │    │   HenrikDev API (선택)      │   │
│  │  (kagglehub)     │    │   henrik_api_key 필요       │   │
│  │  - VCT 2021~2023 │    │   match_cache 테이블 저장   │   │
│  └────────┬─────────┘    └──────────────┬──────────────┘   │
│           │                             │                    │
│           ↓                             ↓                    │
│      data/raw/*.csv            data/external/                │
└─────────────────────────────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                       전처리 단계                             │
│          [ml/data_pipeline.py]                              │
│                                                             │
│  1. 멀티 CSV 로드 (glob 패턴)                               │
│  2. 컬럼 표준화 (소스별 다른 컬럼명 통일)                   │
│  3. 중복 제거 (match_id + team_id + agent)                  │
│  4. 결측값 처리 (신규 요원 → Unknown, 맵 → Other)           │
│  5. 플레이어 → 경기 단위 집계                               │
│  6. Stratified Split 70/15/15                              │
│                                                             │
│       data/processed/train.csv (70%)                        │
│       data/processed/val.csv   (15%)                        │
│       data/processed/test.csv  (15%)                        │
└─────────────────────────────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                    피처 엔지니어링 단계                        │
│         [ml/feature_engineering.py]                         │
│                                                             │
│  입력: 요원 리스트 (팀 A 5명, 팀 B 5명) + 맵                │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              15개 피처 생성                          │   │
│  │                                                     │   │
│  │  역할군 카운트 (8개)                                 │   │
│  │  team_a_duelist_count  team_b_duelist_count         │   │
│  │  team_a_initiator_count team_b_initiator_count      │   │
│  │  team_a_controller_count team_b_controller_count    │   │
│  │  team_a_sentinel_count  team_b_sentinel_count       │   │
│  │                                                     │   │
│  │  diff 피처 (4개)                                    │   │
│  │  duelist_diff = a_count - b_count                   │   │
│  │  initiator_diff, controller_diff, sentinel_diff     │   │
│  │                                                     │   │
│  │  has_controller (2개)                               │   │
│  │  team_a_has_controller  team_b_has_controller       │   │
│  │                                                     │   │
│  │  맵 인코딩 (1개)                                    │   │
│  │  map_encoded (LabelEncoder: Ascent=0, Bind=1, ...)  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                    하이퍼파라미터 최적화 단계                  │
│         [ml/optimize.py] — Optuna TPE Sampler               │
│                                                             │
│  XGBoost 탐색 공간:                                         │
│  - max_depth: [3, 8]                                        │
│  - n_estimators: [100, 800]                                 │
│  - learning_rate: [0.01, 0.3] (log scale)                   │
│  - subsample: [0.5, 1.0]                                    │
│  - colsample_bytree: [0.5, 1.0]                             │
│  - min_child_weight: [1, 10]                                │
│                                                             │
│  LightGBM 탐색 공간:                                        │
│  - num_leaves: [20, 150]                                    │
│  - max_depth: [3, 8]                                        │
│  - n_estimators: [100, 800]                                 │
│  - learning_rate: [0.01, 0.3] (log scale)                   │
│  - min_child_samples: [5, 50]                               │
│                                                             │
│  평가: StratifiedKFold 10겹, ROC-AUC 최대화                  │
│  n_trials=100, timeout=3600초                               │
│                                                             │
│  출력: reports/best_params_xgb.json                         │
│        reports/best_params_lgbm.json                        │
└─────────────────────────────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                       학습 단계                               │
│         [ml/train.py]                                       │
│                                                             │
│  ┌────────────────────┐    ┌──────────────────────────┐    │
│  │  XGBoost 모델      │    │  LightGBM 모델           │    │
│  │  (60% 가중치)      │    │  (40% 가중치)            │    │
│  │  Early Stopping    │    │  Early Stopping          │    │
│  │  eval_metric=      │    │  callbacks=              │    │
│  │  ['logloss','auc'] │    │  [early_stopping(50)]    │    │
│  └────────┬───────────┘    └──────────────┬───────────┘    │
│           │                               │                  │
│           └────────────┬──────────────────┘                 │
│                        ↓                                     │
│               Soft Voting 앙상블                             │
│      final = 0.6 * xgb_prob + 0.4 * lgbm_prob              │
│                                                             │
│  출력: models/xgboost_model.joblib                          │
│        models/lgbm_model.joblib                             │
│        models/label_encoder_map.joblib                      │
│        models/model_metadata.json                           │
└─────────────────────────────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                       평가 단계                               │
│         [ml/evaluate.py]                                    │
│                                                             │
│  평가 지표:                                                  │
│  - Accuracy (목표: ≥ 80%)                                   │
│  - F1-Score Macro                                           │
│  - ROC-AUC                                                  │
│  - PR-AUC                                                   │
│  - Confusion Matrix                                         │
│                                                             │
│  과적합 검사:                                                │
│  - Train Accuracy - Val Accuracy 갭 < 3% 목표               │
│  - Train Loss vs Val Loss 비교                              │
│                                                             │
│  출력: reports/training_report.json                         │
│        reports/confusion_matrix.png (선택)                   │
└─────────────────────────────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                      서빙 단계 (런타임)                        │
│         [backend/ml/predictor.py]                           │
│                                                             │
│  FastAPI 시작 시 모델 싱글톤 로드                           │
│  → 요청마다 joblib 로드 없이 메모리에서 즉시 추론           │
│  → 평균 응답 시간 < 50ms                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 모듈 의존성

```
dataload.py
    ↓ 사용: kagglehub
    ↓ 출력: data/raw/

ml/data_pipeline.py
    ↓ 사용: ml/feature_engineering.py
    ↓ 입력: data/raw/
    ↓ 출력: data/processed/

ml/optimize.py
    ↓ 사용: ml/feature_engineering.py, xgboost, lightgbm, optuna
    ↓ 입력: data/processed/train.csv, val.csv
    ↓ 출력: reports/best_params_*.json

ml/train.py
    ↓ 사용: ml/feature_engineering.py, xgboost, lightgbm, joblib
    ↓ 입력: data/processed/train.csv, val.csv, reports/best_params_*.json
    ↓ 출력: models/*.joblib

ml/evaluate.py
    ↓ 사용: ml/feature_engineering.py, sklearn
    ↓ 입력: models/*.joblib, data/processed/test.csv
    ↓ 출력: reports/training_report.json

backend/ml/predictor.py
    ↓ 사용: models/*.joblib (서빙 시 로드)
    ↓ 의존: backend/ml/agent_roles.py
              backend/ml/feature_engineer.py (피처 엔지니어링 서빙 버전)
```

---

## 3. 관련 문서

| 문서 | 내용 |
|---|---|
| [../04_data_processing/](../04_data_processing/) | 전처리 단계 상세 |
| [../05_data_learning/](../05_data_learning/) | 학습 전략 상세 |
| [../03_architecture/02_request_flow.md](02_request_flow.md) | 서빙 시 피처 처리 흐름 |
