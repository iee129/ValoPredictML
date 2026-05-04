# TODO 리스트

> 마지막 업데이트: 2026-05-03  
> 현재 브랜치: `iee`

---

## 완료 ✅

- [x] **프로젝트 초기화** — 저장소 생성, `.gitignore`, `requirements.txt`, `CLAUDE.md`
- [x] **데이터 수집 스크립트** — `dataload.py` 작성, Kaggle 7개 데이터셋 일괄 다운로드 (`data/raw/kaggle/`, 2.3GB)
- [x] **문서화 완료**
  - [x] `docs/overview.md` — 프로젝트 정의, 아키텍처, 앙상블·K-Fold WHY 설명
  - [x] `docs/preprocessing.md` — 파서 분리, 품질 게이트, 레이블, 분할 전략 + WHY
  - [x] `docs/preprocessing.md` (피처 엔지니어링 통합) — 43개 피처 정의 및 생성 로직 + WHY
  - [x] `docs/ui_design.md` — Streamlit 5개 화면 설계 + WHY
  - [x] `docs/datasets.md` — 7개 데이터셋 상세, 관련성 평가, 파이프라인 역할
  - [x] `docs/valorant.md` — 게임 규칙, 역할 가이드, 프로 데이터 한계 + WHY

---

## 진행 중 🔜

### 1단계: 데이터 전처리 (`ml/`)

> 계획 문서: `.omc/plans/preprocessing.md`

- [ ] **`ml/agent_roles.py`** 구현
  - [ ] `AGENT_ROLE_MAP` (27종 요원 → 역할군) 딕셔너리
  - [ ] `MAP_ORDER` / `MAP_TO_INDEX` (12개 맵)
  - [ ] `normalize_agent(raw)` — 별칭·소문자·`.title()` 폴백
  - [ ] `normalize_map(raw)` — 동일 패턴
- [ ] **`ml/data_pipeline.py`** 구현
  - [ ] ryanluong 파서 — `overview.csv` + `maps_scores.csv` 통합 row 생성
  - [ ] piyush 파서 — `player_stats.csv` + `maps.csv` 통합 row 생성
  - [ ] qualidea 파서 — `matches.csv` 파싱
  - [ ] 품질 게이트 — 팀당 요원 5개, 알려진 요원/맵, 유효 레이블, `dedup_key` 중복 제거
  - [ ] 피처 엔지니어링 — 역할 카운트, diff, `map_encoded`, `has_controller_a/b`, `label`
  - [ ] 70/15/15 train/val/test 분할 (`match_key` 단위, seed=42)
  - [ ] `reports/preprocess_summary.json` 출력
  - [ ] `reports/rejected_matches.csv` 출력
- [ ] 전처리 dry-run 실행 및 검증
  ```bash
  python -m ml.data_pipeline --input data/raw/kaggle --output /tmp/valo_out --reports /tmp/valo_reports
  ```

---

## 미구현 ⬜

### 2단계: 피처 엔지니어링 고도화

- [ ] **선수 스탯 피처** — `Team_Avg_Rating`, `Team_Avg_KD`, `Team_Max_Clutch_Rate`, `Team_Avg_KAST`, `Team_Avg_Assists`, `Team_ADR`
- [ ] **시너지 피처** — `First_Kill_Death_Ratio`, `Team_Shared_Exp` (visualize25 데이터셋 가공 필요)
- [ ] **요원×맵 피처** — `agent_map_wr` (train.csv 기반 집계, 데이터 누수 방지), `Avg_Agent_Pick_Rate`, `Team_Agent_Experience`
- [ ] **맵 피처** — `atk_side_advantage`, `is_attacker_a`
- [ ] `visualize25__*` 데이터셋 수집 — `Team_Shared_Exp` 피처용

### 3단계: 모델 학습 (`ml/train_model.py`)

- [ ] **Random Forest** 기본 학습
- [ ] **XGBoost** 학습
- [ ] **LightGBM** 학습
- [ ] **앙상블** — 3모델 확률 평균 → 최종 승률
- [ ] **K-Fold 교차검증** (K=5) — Accuracy, ROC-AUC, F1 평균 산출
- [ ] 모델 파일 저장 (`models/`, git 제외)

### 4단계: 모델 평가 (`ml/evaluate_model.py`)

- [ ] Accuracy, ROC-AUC, F1 평가 출력
- [ ] SHAP feature importance 시각화
- [ ] `reports/eval_summary.json` 출력

### 5단계: Streamlit UI (`app/streamlit_app.py`)

- [ ] **Feature Builder** — 선수/요원 입력 → 31개 피처 자동 생성
- [ ] **홈 화면** — Team A / Team B 입력, 예측 실행 버튼
- [ ] **예측 결과** — 승률 게이지, 주요 영향 피처 bar chart, 선수-요원 적합도 표
- [ ] **교체 실험** — 요원/선수 교체 전후 승률 delta 계산
- [ ] **기록 화면** — 예측 기록 조회, 필터, 재실행
- [ ] **분석 화면** — 모델 비교, feature importance, 리포트 출력

### 6단계: PostgreSQL (후보)

- [ ] `predictions` 테이블 스키마 설계
- [ ] SQLAlchemy 연결 설정
- [ ] 예측 결과 저장/조회 구현

---

## 보류 / 범위 외 🚫

- HenrikDev API — 외부 API 미사용 방침으로 제외
- Riot VCT S3 API — 외부 API 미사용 방침으로 제외
- FastAPI / Next.js / 클라우드 배포 — 로컬 Streamlit 도구가 목표
- 일반 유저 데이터 수집 — 현재 프로/준프로 경기 데이터로 한정

---

## 참고 링크

| 문서 | 경로 |
|------|------|
| 전처리 계획 | `.omc/plans/preprocessing.md` |
| 피처 정의 | `docs/preprocessing.md` (섹션 7) |
| 데이터셋 목록 | `docs/datasets.md` |
| UI 설계 | `docs/ui_design.md` |
| 아키텍처 | `docs/overview.md` |
