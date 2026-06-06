# 06. ML 파이프라인 아키텍처

마지막 업데이트: 2026-05-27

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
│           ↓ python -m data.dataload                              │
│      data/raw/kaggle/                                       │
└─────────────────────────────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                         파싱 단계                              │
│         [src/features/preprocess.py, src/data/ingest.py] │
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
│                   품질 검사 단계                               │
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
│  출력: data/processed/matches.csv                           │
└─────────────────────────────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                   데이터 분할 단계                             │
│                                                             │
│  match_key 단위 GroupShuffleSplit                           │
│  train 80% / test 20%                                       │
│  (별도 검증셋 없이 train 내부 GroupKFold로 튜닝)             │
│                                                             │
│  출력: data/processed/train.csv (test.csv)                  │
│                                                             │
│  (선택) 시간 기반 분할 검증 실험:                            │
│    train: 2021-01 ~ 2023-12                                 │
│    test:  2024-01 ~ 2025-현재                               │
└─────────────────────────────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│               피처 사전 집계 단계 (데이터 분리 유지)            │
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
│  피처 계약별 생성 수:                                         │
│    baseline  (421피처): 슬롯400=10선수×[PRIOR8+요원27+역할5] │
│                         + 컨텍스트21=맵12+합동3+역할조합6     │
│                         (LR+DT soft voting, 랜덤 80:20)       │
│    advanced  (179피처): 맵 원핫 + 역할군·요원 count +         │
│                         선수 prior/synergy/map×agent + 팀 form│
│                         (RF+XGB+LGBM, 시간순 split)           │
│                                                             │
│  공통 카테고리 (advanced 기준):                               │
│  맵 원핫 + 역할군·요원 count + 선수 prior                    │
│  synergy/map_agent/player_agent + team form                  │
│  composition meta + cold-start flags                         │
│                                                             │
│  데이터 분리: match_key 단위 분할 + GroupKFold + 금지 피처 26개│
│             + 이전 연도만 prior + smoothing                  │
│                                                             │
│  sample_weight = time_weight × source_weight                │
│                                                             │
│  출력: data/processed/advanced/{train,test}.csv              │
└─────────────────────────────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                       모델 학습 단계                          │
│         [src/ml/advanced/ensemble.py]                           │
│                                                             │
│  GroupKFold(n=5, match_key 단위) — Optuna HPO 미사용(향후 계획)        │
│                                                             │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐    │
│  │ Random Forest │ │   XGBoost     │ │   LightGBM    │    │
│  │ train_rf()    │ │ train_xgb()   │ │ train_lgbm()  │    │
│  │ (scikit-learn)│ │ Early Stopping│ │ Early Stopping│    │
│  └───────┬───────┘ └───────┬───────┘ └───────┬───────┘    │
│          └────────────────┬──────────────────┘             │
│                           ↓                                 │
│      final = ensemble.predict_proba (단일 ensemble.joblib, soft voting 가중평균 w=2.0:3.0:0.1)│
│                                                             │
│  성능: Ensemble Test AUC=0.7010 / Acc=0.6454 / F1=0.6478   │
│        (시간순 split: train2020–2025 / test2026)            │
│        맵 단위 승패 샘플 train 75,405 / test 16,053          │
│                                                             │
│  출력: models/advanced/ensemble.joblib  (서빙용, 단일 VotingClassifier)│
│        models/advanced/rf.joblib                            │
│        models/advanced/xgb.joblib                           │
│        models/advanced/lgbm.joblib                          │
│        models/advanced/meta.json                            │
└─────────────────────────────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                         평가 단계                              │
│         [src/ml/advanced/evaluate.py]                           │
│                                                             │
│  kfold_evaluate() — GroupKFold(n=5, baseline) / 시간순(advanced)│
│  feature_importance() — feature_importances_·순열 중요도    │
│  (SHAP 미구현 — shap_analysis.py 향후 계획)                 │
│                                                             │
│  평가 지표 (advanced 시간순 기준):                           │
│  - Accuracy: 0.6454                                         │
│  - ROC-AUC:  0.7010 (Ensemble)                              │
│  - F1-Score: 0.6478                                         │
│  - Confusion Matrix                                         │
│                                                             │
│  출력: reports/advanced/metrics.json                        │
│        reports/advanced/validation.json                     │
│        data/processed/rejects.csv                           │
└─────────────────────────────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                   검증 단계                                    │
│         [src/ml/advanced/validate.py]                           │
│                                                             │
│  baseline_compare()       — 랜덤/다수결 베이스라인 대비 검증  │
│  generalization_check()   — Train-Test 갭 과적합 진단        │
│  shap_analysis()          — SHAP 값 일관성·방향성 검증       │
└─────────────────────────────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                   서빙 단계 (구현 완료)                        │
│   [web (Next.js) → src/api (FastAPI) → src/inference/predict.py] │
│                                                             │
│  모듈 로드 시 모델 1회 로드                                  │
│  → 사용자 입력 → 피처 빌드 → 앙상블 예측 → 승률 출력        │
│  → 피처 중요도 발산형 막대 / 자연어 근거                    │
│  → 경기 다시보기 · 모델 근거 화면                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 모듈 의존성

```
src/data/dataload.py
    ↓ kagglehub → data/raw/kaggle/

src/domain/valorant.py             (공통 참조: AGENT_ROLE_MAP, MAP_ORDER, 정규화 함수)

── Baseline 파이프라인 ──────────────────────────────────────
src/features/preprocess.py
    ↓ src/domain/valorant.py       (정규화)
    ↓ data/processed/      (matches, players, teams, features_*, files, schemas, sources, rejects, train, val, test)

src/ml/baseline/train.py
    ↓ data/processed/train.csv
    ↓ models/baseline/     (model.joblib, meta.json)

src/ml/baseline/evaluate.py + src/ml/baseline/validate.py
    ↓ models/baseline/model.joblib
    ↓ data/processed/test.csv
    ↓ reports/             (출력)

── Advanced 파이프라인 ─────────────────────────────────────
src/data/ingest.py
    ↓ src/domain/valorant.py       (정규화)
    ↓ data/processed/      (동일 출력 구조)

src/ml/advanced/ensemble.py    # RF(w=2.0)+XGB(w=3.0)+LGBM(w=0.1) soft voting
    ↓ data/processed/train.csv
    ↓ models/advanced/     (rf.joblib, xgb.joblib, lgbm.joblib, meta.json)

src/ml/advanced/evaluate.py + src/ml/advanced/validate.py
    ↓ models/advanced/*.joblib
    ↓ data/processed/test.csv
    ↓ reports/             (출력)

── 사용자 차별점 모듈 (미구현 — Phase 5c 계획) ──────────────
ml/differentiators/  ← 현재 미존재 (Phase 5c 구현 예정)
    ├── counter_alert.py        (계획)
    ├── agent_map_fit.py        (계획)
    ├── map_ideal_comp.py       (계획)
    ├── risk_alert.py           (계획)
    ├── ult_balance.py          (계획)
    ├── nl_explain.py           (계획)
    ├── player_agent_pool.py    (계획)
    └── side_panel.py           (계획)

── 서빙 ─────────────────────────────────────────────────────
web/ (Next.js) → src/api/ (FastAPI)
    ↓ src/inference/predict.py            (추론 로직, FastAPI가 import)
    ↓ models/advanced/ensemble.joblib  (모듈 로드 시 1회 로드)
    ↓ src/domain/valorant.py            (피처 빌드)
    ↓ src/insights/build_insights.py    (인사이트 사전 집계)
```

### 2.1 사용자 차별점 통합 흐름 (Phase 5c 계획 — 현재 미구현)

> 아래 흐름은 Phase 5c 계획안이다. `ml/differentiators/`, `app/whatif.py`, `app/components.py`는 현재 존재하지 않는다.

```
사용자 입력 (맵 + 선수 10명 + 요원 10명)
        ↓
┌──────────── 입력 즉시 피드백 (그룹 1, 미구현) ────────────┐
│ I. counter_alert  → st.error/warning/info               │
│ N. agent_map_fit  → st.metric ✓/△/✗                    │
│ K. map_ideal_comp → st.progress + st.info              │
│ G. risk_alert     → st.warning fixed banner            │
└─────────────────────────────────────────────────────────┘
        ↓
src/inference/predict.py — 모델 예측 (ensemble.joblib, 단일 VotingClassifier)
        ↓
┌──────────── 예측 결과 해석 (그룹 2, 미구현) ─────────────┐
│ B. calibration   → reliability + Brier + ECE           │
│ C. nl_explain    → SHAP → 한국어 카드                  │
│ J. ult_balance   → st.progress gauge                   │
│ D. player_pool   → plotly 도넛 + out-of-pool           │
└─────────────────────────────────────────────────────────┘
        ↓
┌──────────── 인터랙티브 시뮬레이션 (그룹 3, 미구현) ───────┐
│ A. whatif        → 슬롯 교체 → 승률 delta              │
│ E. side_panel    → ATK/DEF 게이지 + 권장               │
└─────────────────────────────────────────────────────────┘
```

---

## 3. 관련 문서

| 문서 | 내용 |
|------|------|
| [../02_file_structure/03_ml_pipeline_files.md](../02_file_structure/03_ml_pipeline_files.md) | ml/ 폴더 파일 상세 |
| [02_request_flow.md](02_request_flow.md) | 서빙 시 피처 처리 흐름 |
| [../06_model_test/project_differentiation.md](../06_model_test/project_differentiation.md) | 5개 기술 차별점 + 10개 사용자 차별점 검증 |
| [../08_web/07_styling/02_layout_demo_dashboard.md](../08_web/07_styling/02_layout_demo_dashboard.md) | 시연 대시보드 화면 + 위젯 배치 |
