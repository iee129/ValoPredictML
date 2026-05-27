# 08. 전체 작업 Todo List

> 마지막 업데이트: 2026-05-27
> 현재 브랜치: `iee`
> 원본 계획: `.omc/plans/user_facing_differentiators_plan.md`

---

## 완료

- [x] **프로젝트 초기화** — 저장소 생성, `.gitignore`, `requirements.txt`, `CLAUDE.md`
- [x] **데이터 수집 스크립트** — `dataload.py` 작성, Kaggle 다수 데이터셋 다운로드 (`data/raw/kaggle/`, 2.3GB)
- [x] **문서화**
  - [x] `docs/overview.md` — 프로젝트 정의, 아키텍처, 앙상블·K-Fold WHY 설명
  - [x] `docs/preprocessing.md` — 파서 분리, 품질 게이트, 레이블, 분할 전략 + WHY
  - [x] `docs/ui_design.md` — Streamlit 5개 화면 설계 + WHY
  - [x] `docs/datasets.md` — 데이터셋 상세, 관련성 평가, 파이프라인 역할
  - [x] `docs/valorant.md` — 게임 규칙, 역할 가이드, 프로 데이터 한계 + WHY
  - [x] `docs/competitive_analysis.md` — 8개 경쟁 프로젝트 비교 분석
- [x] **1단계: 데이터 전처리 (`ml/`)** — 구현 완료
  - [x] `ml/agent_roles.py` — 27종 요원 × 4개 역할 분류 + 12개 맵 목록
  - [x] `ml/data_pipeline.py` — 파서 5종(ryanluong·qualidea·piyush·ediashtarevin·challengers) + 품질 게이트 + dedup + 피처 + 분할
  - [x] 전처리 결과: clean **66,485행** → train **93,078** / val **9,973** / test **9,973** (seed=42)
  - [x] `reports/preprocess_summary.json`, `reports/rejected_matches.csv` 출력
- [x] **3단계: 모델 학습 (`ml/train_model.py`)** — 구현 완료
  - [x] Random Forest (n_estimators=300)
  - [x] XGBoost (n=500, Optuna HPO)
  - [x] LightGBM (n=500, Optuna HPO)
  - [x] 앙상블 — metadata 기반 RF/XGBoost/LightGBM 가중 평균
  - [x] K-Fold 교차검증 (K=5, GroupKFold, match_key 기준)
  - [x] 모델 파일 저장 (`models/`, git 제외)
- [x] **4단계: 모델 평가 (`ml/evaluate_model.py`, `ml/validate_metrics.py`)** — 완료
  - [x] Ensemble Test AUC=**0.9355**, Acc=**0.8540**, F1=**0.8508**
  - [x] K-Fold Ensemble AUC=**0.9414** (gap=0.0059 — 과적합 없음)
  - [x] Baseline(다수 클래스) 대비 **+29.13%p** 개선
  - [x] SHAP feature importance 분석
  - [x] `reports/eval_summary.json`, `reports/baseline_comparison.json` 출력
- [x] **5단계: Streamlit UI (`app/streamlit_app.py`)**
  - [x] Feature Builder — 선수/요원 입력 → P1-P4 57개 피처 자동 생성
  - [x] 예측 결과 — 승률, 주요 영향 피처 bar chart, 선수 기여도 표
  - [x] 교체 실험 — 요원 교체 전후 승률 delta 계산
  - [x] 기록 화면 — SQLite 예측 기록 조회/필터
  - [x] 가이드 화면 — 역할군, 맵별 강세 요원, 인기 승리 조합

---

## 진행 중 (2026-05-28 ~ 2026-06-08 — 사용자 차별점 강화 2주 스프린트)

### 1주차 (5/29~6/1) — VLR.gg 비의존 차별점 7개 + 심화 모델

- [ ] **5/29 (금)** I (카운터 픽 경고) + G (위험 알림)
  - [ ] `docs/10_valorant/counters.md` 18쌍 → `data/research/valorant_counters.json`
  - [ ] `ml/differentiators/counter_alert.py` + `tests/differentiators/test_counter_alert.py`
  - [ ] `ml/differentiators/risk_alert.py` (룰 5개: no_controller / too_many_sentinels / no_duelist / no_initiator / same_role_overload)
- [ ] **5/30 (토)** N (요원-맵 적합도) + K (맵별 이상 구성) + J (Ult Cycle Balance)
  - [ ] `docs/10_valorant/agents.md` → `data/research/agent_map_fit.json` (29×13)
  - [ ] `docs/10_valorant/maps.md` → `data/research/map_ideal_comp.json` (12 맵)
  - [ ] `docs/10_valorant/economy.md` → `data/research/agent_ult_cost.json` (29 요원)
  - [ ] `ml/differentiators/{agent_map_fit,map_ideal_comp,ult_balance}.py` + 단위 테스트 3건
- [ ] **5/31 (일)** Phase 5a — 심화 모델 학습
  - [ ] `ml/advanced/preprocess.py` + `ml/advanced/train.py` (RF + XGBoost + LightGBM + Optuna)
  - [ ] `models/advanced/{rf,xgb,lgbm}.joblib` 생성, `reports/advanced/metrics.json`
  - [ ] `ml/advanced/validate.py` — 6관문 데이터 누수 게이트 통과
- [ ] **6/01 (월)** B (박빙 검증) + C (자연어 설명 골격)
  - [ ] `ml/baseline/evaluate.py` 보강 — Brier + Reliability + ECE + 박빙 구간 다단계
  - [ ] `reports/baseline/calibration.png`, `reports/advanced/calibration.png`
  - [ ] `ml/differentiators/nl_explain.py` 한국어 템플릿 골격

### 2주차 (6/2~6/8) — VLR.gg 통합 + 차별점 D·E·A·C 완성 + Streamlit 통합

- [ ] **6/02 (화)** VLR.gg 스크래핑 완료 확인 + 통합 데이터 정합성 검증
  - [ ] `data/processed/vlrgg/` 통합 CSV, dedup_key 매칭 리포트
- [ ] **6/03 (수)** D (선수 Agent Pool) + Phase 5b VLR.gg 통합 모델 재학습
  - [ ] `ml/differentiators/player_agent_pool.py` (vlrggapi + CSV fallback)
  - [ ] `models/advanced_vlrgg/{rf,xgb,lgbm}.joblib`, 6관문 통과
- [ ] **6/04 (목)** E (사이드별 ATK/DEF 패널)
  - [ ] `ml/differentiators/side_panel.py` (VLR team stats ATK RWin% / DEF RWin%)
- [ ] **6/05 (금)** A (What-if 시뮬레이션)
  - [ ] `app/whatif.py` — session_state 히스토리 stack, `@st.cache_resource`로 모델 로드
- [ ] **6/06 (토)** C (자연어 설명) SHAP 통합
  - [ ] SHAP TreeExplainer → 상위 5개 피처 → 한국어 카드 (발로란트 도메인 비유 포함)
- [ ] **6/07 (일)** Phase 5c 통합
  - [ ] `app/main.py` — 10개 차별점 단일 화면 통합 (`st.tabs` 3그룹)
  - [ ] `app/predict.py`, `app/components.py`
  - [ ] `tests/integration/test_streamlit_integration.py`
  - [ ] 시연 영상 3개 1차 (정상 / 박빙 / out-of-pool)
- [ ] **6/08 (월)** 최종 리허설
  - [ ] `notice/final/final_presentation.md`, `final_script.md`
  - [ ] 백업 시연 영상

### 검증 게이트 (전 기간)

- [ ] 데이터 누수 6관문 — 베이스라인 / 심화 (Kaggle) / 심화 (Kaggle+VLR.gg) 3개 모델 모두 PASS
- [ ] 차별점 단위 테스트 10개 모두 통과 (`pytest tests/differentiators/`)
- [ ] 통합 테스트 통과 (`pytest tests/integration/`)
- [ ] 박빙 구간 정확도 ≥50% (찍기 초과, B 차별점 학술 기준)

---

## 보류 / 범위 외

- HenrikDev API — 외부 API 미사용 방침으로 제외
- Riot VCT S3 API — 외부 API 미사용 방침으로 제외
- FastAPI / Next.js / 클라우드 배포 — 로컬 Streamlit 도구가 목표
- PostgreSQL — 후보지만 현재 범위 외. 기본 저장소는 SQLite
- 일반 유저 데이터 수집 — 현재 프로/준프로 경기 데이터로 한정
- VLR.gg 직접 scraping — robots 정책 리스크로 기본 비활성화

---

## 참고 링크

| 문서 | 경로 |
|------|------|
| 피처 정의 | `docs/preprocessing.md` (섹션 7) |
| 데이터셋 목록 | `docs/datasets.md` |
| UI 설계 | `docs/ui_design.md` |
| 아키텍처 | `docs/overview.md` |
| 경쟁 분석 | `docs/competitive_analysis.md` |
