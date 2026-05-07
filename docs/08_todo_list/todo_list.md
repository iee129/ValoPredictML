# 08. 전체 작업 Todo List

> 마지막 업데이트: 2026-05-05
> 현재 브랜치: `iee`

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
  - [x] 앙상블 — 3모델 확률 단순 평균
  - [x] K-Fold 교차검증 (K=5, GroupKFold, match_key 기준)
  - [x] 모델 파일 저장 (`models/`, git 제외)
- [x] **4단계: 모델 평가 (`ml/evaluate_model.py`, `ml/validate_metrics.py`)** — 완료
  - [x] Ensemble Test AUC=**0.9355**, Acc=**0.8540**, F1=**0.8508**
  - [x] K-Fold Ensemble AUC=**0.9414** (gap=0.0059 — 과적합 없음)
  - [x] Baseline(다수 클래스) 대비 **+29.13%p** 개선
  - [x] SHAP feature importance 분석
  - [x] `reports/eval_summary.json`, `reports/baseline_comparison.json` 출력

---

## 미구현

### 5단계: Streamlit UI (`app/streamlit_app.py`)

- [ ] **Feature Builder** — 선수/요원 입력 → 45개 피처 자동 생성
- [ ] **홈 화면** — Team A / Team B 입력, 예측 실행 버튼
- [ ] **예측 결과** — 승률 게이지, 주요 영향 피처 bar chart, 선수-요원 적합도 표
- [ ] **교체 실험** — 요원/선수 교체 전후 승률 delta 계산
- [ ] **기록 화면** — 예측 기록 조회, 필터, 재실행
- [ ] **분석 화면** — 모델 비교, feature importance, 리포트 출력

---

## 보류 / 범위 외

- HenrikDev API — 외부 API 미사용 방침으로 제외
- Riot VCT S3 API — 외부 API 미사용 방침으로 제외
- FastAPI / Next.js / 클라우드 배포 — 로컬 Streamlit 도구가 목표
- PostgreSQL — 후보지만 현재 범위 외
- 일반 유저 데이터 수집 — 현재 프로/준프로 경기 데이터로 한정
- 선수 스탯 피처 고도화 (`Team_Avg_Rating` 등) — 현재 45개 피처로 충분, 향후 개선 항목

---

## 참고 링크

| 문서 | 경로 |
|------|------|
| 피처 정의 | `docs/preprocessing.md` (섹션 7) |
| 데이터셋 목록 | `docs/datasets.md` |
| UI 설계 | `docs/ui_design.md` |
| 아키텍처 | `docs/overview.md` |
| 경쟁 분석 | `docs/competitive_analysis.md` |
