# TODO 리스트

> 마지막 업데이트: 2026-05-05  
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
- [x] **ML 파이프라인 구현** — `ml/` 전체 (agent_roles, data_pipeline, train_model, evaluate_model, validate_metrics)
  - [x] `ml/agent_roles.py` — 27개 요원 역할 매핑, 맵 목록, 정규화 함수
  - [x] `ml/data_pipeline.py` — ryanluong 파서, 품질 게이트, 피처 엔지니어링, A/B swap 증강, 70/15/15 분할 (piyush 파서 제거됨)
  - [x] `ml/train_model.py` — RF + XGBoost + LightGBM + 앙상블, GroupKFold K=5
  - [x] `ml/evaluate_model.py` — Accuracy/ROC-AUC/F1 평가, SHAP feature importance
  - [x] `ml/validate_metrics.py` — 성과지표 검증
  - [x] `data/processed/train.csv` (93,078행), `test.csv` (9,973행) 생성
  - [x] `reports/` JSON 생성 — eval_summary, baseline_comparison, generalization_check, shap_analysis
  - [x] `models/` 학습된 모델 파일 저장
  - [x] **앙상블 Ensemble AUC = 0.935, baseline 대비 +29.13%p 개선**
- [x] **모델 검증 문서**
  - [x] `docs/06_model_test/ml_concept_validation.md`
  - [x] `docs/06_model_test/project_differentiation.md`
  - [x] `docs/06_model_test/verification_summary.md`

---

## 진행 중 🔜

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
