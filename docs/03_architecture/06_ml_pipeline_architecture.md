# 06. ML 파이프라인 아키텍처

마지막 업데이트: 2026-05-04

## 1. 전체 파이프라인 다이어그램

```
┌─────────────────────────────────────────────────────────────┐
│                       데이터 수집 단계 (완료)                  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Kaggle 데이터셋 (kagglehub)                          │  │
│  │  - vct_2021_2023          (1.2GB, ryanluong)         │  │
│  │  - ryanluong challengers  (1.0GB, ryanluong, w=1.8)  │  │
│  │  - qualidea1217           (~35MB, qualidea)          │  │
│  │  - ediashtarevin          (~6K행, 보조)               │  │
│  └──────────────────────────────────────────────────────┘  │
│           ↓ python dataload.py                              │
│      data/raw/kaggle/                                       │
└─────────────────────────────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                         파싱 단계                              │
│         [ml/parsers/*.py]                                   │
│                                                             │
│  parse_ryanluong("vct_2021_2023")        → 공통 스키마 행    │
│  parse_ryanluong("ryanluong challengers") → 공통 스키마 행   │
│  parse_qualidea ("qualidea1217__*")       → 공통 스키마 행   │
│  parse_edia     ("ediashtarevin__*")      → 공통 스키마 행   │
│                                                             │
│  공통 스키마: source, match_key, dedup_key, date, event,    │
│              map, team_a, team_b, players_a, players_b,     │
│              score_a, score_b, atk_a, def_a, label          │
└─────────────────────────────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                   정규화 단계                                  │
│                                                             │
│  normalize_agent(raw)  → AGENT_ROLE_MAP → 별칭 → .title()   │
│  normalize_map(raw)    → MAP_ORDER → 별칭 → .title()         │
│  normalize_team(raw)   → TEAM_NAME_ALIASES                  │
│  컬럼명 통일           → snake_case (hs%/hs_percent → hs)    │
│  KD 표기 통일          → kd (float)                         │
│  KAST 표기 통일        → kast (float 0~1)                   │
└─────────────────────────────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                   품질 게이트 단계                             │
│                                                             │
│  팀당 요원 수 = 5       (미충족 → rejected_matches.csv)      │
│  요원 유효성            (AGENT_ROLE_MAP에 없으면 탈락)        │
│  맵 유효성              (MAP_ORDER에 없으면 탈락)             │
│  레이블 유효성          (승팀 특정 불가 → 탈락)              │
│  핵심 스탯 결측         (ACS·KD 결측 → 탈락)                │
│  승패 동점              (score_a = score_b → 탈락)           │
│  소스 비중              (단일 소스 > 20% → under-sampling)   │
└─────────────────────────────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                   dedup 단계                                  │
│                                                             │
│  dedup_key = SHA-1[:24](date|event|map|team_a|team_b|       │
│                          agents_a|agents_b|score_a|score_b) │
│                                                             │
│  동일 dedup_key → 소스 가중치 높은 행 보존                   │
│  동점 → 컬럼 수 더 많은 행 보존                             │
│                                                             │
│  출력: data/processed/matches_clean.csv                     │
└─────────────────────────────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                   데이터 분할 단계                             │
│                                                             │
│  match_key 단위 GroupShuffleSplit                           │
│  train 70% / val 15% / test 15%                             │
│                                                             │
│  출력: data/processed/train.csv                             │
│        data/processed/val.csv                               │
│        data/processed/test.csv                              │
│                                                             │
│  (선택) 시간 기반 분할 검증 실험:                            │
│    train: 2021-01 ~ 2023-12                                 │
│    test:  2024-01 ~ 2025-현재                               │
└─────────────────────────────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│               피처 사전 집계 단계 (누수 방지)                  │
│         train.csv 기준으로만 집계                            │
│                                                             │
│  atk_side_advantage[map]        ← ryanluong challengers    │
│  agent_map_stats[agent][map]    ← train 경기 전체           │
│    .winrate = wins / total                                  │
│    .pickrate = total / total_matches_on_map                 │
│  agent_experience[player][agent] ← train 등장 횟수          │
│                                                             │
│  val/test에 join (신규 조합: winrate=0.5, experience=0)      │
└─────────────────────────────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│               피처 엔지니어링 단계                             │
│                                                             │
│  43개 피처 생성:                                             │
│  역할군 카운트 (12): a_duelist ~ diff_sentinel               │
│  역할군 파생   (4):  has_controller_a/b, is_double_duelist_a/b│
│  선수 스탯    (12): a_avg_acs ~ b_avg_hs                    │
│  시너지       (6):  a_fk_fd_ratio ~ b_kast_std              │
│  요원 조합    (6):  a_avg_agent_map_wr ~ b_avg_agent_exp    │
│  맵           (3):  map_encoded, atk_side_advantage, is_attacker_a│
│                                                             │
│  A/B Swap 증강 (train 한정):                                │
│    원본: team_a=T1, label=1                                 │
│    swap: team_a=FNC, label=0  (--no-augment-train 으로 비활성)│
│                                                             │
│  sample_weight = time_weight × source_weight                │
│                                                             │
│  출력: data/processed/features_base.csv                     │
└─────────────────────────────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                       모델 학습 단계                          │
│         [ml/train_model.py]                                 │
│                                                             │
│  GroupKFold(n=5, match_key 단위), Optuna HPO                │
│                                                             │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐    │
│  │ Random Forest │ │   XGBoost     │ │   LightGBM    │    │
│  │ train_rf()    │ │ train_xgb()   │ │ train_lgbm()  │    │
│  │ (scikit-learn)│ │ Early Stopping│ │ Early Stopping│    │
│  └───────┬───────┘ └───────┬───────┘ └───────┬───────┘    │
│          └────────────────┬──────────────────┘             │
│                           ↓                                 │
│        ensemble_predict_proba() — 확률 단순 평균             │
│      final = (p_rf + p_xgb + p_lgb) / 3                    │
│                                                             │
│  성능: AUC=0.935, Acc=0.854, 베이스라인 대비 +29.13%p       │
│                                                             │
│  출력: models/rf_model.joblib                               │
│        models/xgboost_model.joblib                          │
│        models/lgbm_model.joblib                             │
│        models/label_encoder_map.joblib                      │
│        models/model_metadata.json                           │
└─────────────────────────────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                         평가 단계                              │
│         [ml/evaluate_model.py]                              │
│                                                             │
│  kfold_evaluate() — GroupKFold(n=5)                         │
│  shap_analyze()  — SHAP TreeExplainer                       │
│                                                             │
│  평가 지표:                                                  │
│  - Accuracy: 0.854                                          │
│  - ROC-AUC:  0.935                                          │
│  - F1-Score                                                 │
│  - Confusion Matrix                                         │
│                                                             │
│  출력: reports/training_report.json                         │
│        reports/rejected_matches.csv                         │
└─────────────────────────────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                   검증 단계                                    │
│         [ml/validate_metrics.py]                            │
│                                                             │
│  baseline_compare()       — 랜덤/다수결 베이스라인 대비 검증  │
│  generalization_check()   — Train-Test 갭 과적합 진단        │
│  shap_analysis()          — SHAP 값 일관성·방향성 검증       │
└─────────────────────────────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                   서빙 단계 (Phase 5, 미구현)                  │
│         [app/streamlit_app.py]                              │
│                                                             │
│  @st.cache_resource 로 모델 1회 로드                        │
│  → 사용자 입력 → 피처 빌드 → 앙상블 예측 → 승률 출력        │
│  → 피처 중요도 / SHAP 시각화 (Plotly)                       │
│  → 교체 시뮬레이션 delta 표시                               │
│  → 맵별 최적 요원 조합 탐색 (80,730가지)                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 모듈 의존성

```
dataload.py
    ↓ kagglehub → data/raw/kaggle/

ml/agent_roles.py          (공통 참조: AGENT_ROLE_MAP, MAP_ORDER, 정규화 함수)

ml/data_pipeline.py
    ↓ ml/parsers/*.py      (파싱)
    ↓ ml/agent_roles.py    (정규화)
    ↓ data/processed/      (출력)

ml/train_model.py
    ↓ data/processed/train.csv, val.csv
    ↓ models/*.joblib      (출력)

ml/evaluate_model.py
    ↓ models/*.joblib
    ↓ data/processed/test.csv
    ↓ reports/             (출력)

app/streamlit_app.py
    ↓ models/*.joblib      (서빙 시 로드)
    ↓ ml/agent_roles.py    (피처 빌드)
```

---

## 3. 관련 문서

| 문서 | 내용 |
|------|------|
| [../docs/preprocessing.md](../preprocessing.md) | 전처리 파이프라인 정전 설계 (43개 피처 상세) |
| [../02_file_structure/03_ml_pipeline_files.md](../02_file_structure/03_ml_pipeline_files.md) | ml/ 폴더 파일 상세 |
| [02_request_flow.md](02_request_flow.md) | 서빙 시 피처 처리 흐름 |
