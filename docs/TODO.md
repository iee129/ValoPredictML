# TODO 리스트

> 마지막 업데이트: 2026-05-10  
> 현재 브랜치: `iee`

---

## 완료 ✅

- [x] **프로젝트 초기화** — 저장소 생성, `.gitignore`, `requirements.txt`, `CLAUDE.md`
- [x] **데이터 수집 스크립트** — `dataload.py` 작성, Kaggle 7개 데이터셋 일괄 다운로드 (`data/raw/kaggle/`, 2.3GB)
- [x] **문서화 완료**
  - [x] `docs/overview.md` — 프로젝트 정의, 아키텍처, 앙상블·K-Fold WHY 설명
  - [x] `docs/preprocessing.md` — 파서 분리, 품질 게이트, 레이블, 분할 전략 + WHY
  - [x] `docs/preprocessing.md` (피처 엔지니어링 통합) — P1-P4 57개 활성 피처 정의 및 생성 로직 + WHY
  - [x] `docs/ui_design.md` — Streamlit 5개 화면 설계 + WHY
  - [x] `docs/datasets.md` — 7개 데이터셋 상세, 관련성 평가, 파이프라인 역할
  - [x] `docs/valorant.md` — 게임 규칙, 역할 가이드, 프로 데이터 한계 + WHY
- [x] **ML 파이프라인 구현** — `ml/` 전체 (agent_roles, data_pipeline, train_model, evaluate_model, validate_metrics)
  - [x] `ml/agent_roles.py` — 27개 요원 역할 매핑, 맵 목록, 정규화 함수
  - [x] `ml/data_pipeline.py` — 파서, 품질 게이트, P1-P4 57개 활성 피처, A/B swap 증강, 70/15/15 분할
  - [x] `ml/train_model.py` — RF + XGBoost + LightGBM + metadata 기반 가중 앙상블, GroupKFold K=5
  - [x] `ml/evaluate_model.py` — Accuracy/ROC-AUC/F1 평가, SHAP feature importance
  - [x] `ml/validate_metrics.py` — 성과지표 검증
  - [x] `data/processed/train.csv` (93,078행), `test.csv` (9,973행) 생성
  - [x] `reports/` JSON 생성 — eval_summary, baseline_comparison, generalization_check, shap_analysis
  - [x] `models/` 학습된 모델 파일 저장
  - [x] **앙상블 지표는 `reports/eval_summary.json` / `reports/validation_report.json` 재생성 결과를 기준으로 확인**
- [x] **모델 검증 문서**
  - [x] `docs/06_model_test/ml_concept_validation.md`
  - [x] `docs/06_model_test/project_differentiation.md`
  - [x] `docs/06_model_test/verification_summary.md`

- [x] **Streamlit 로컬 UI 구현** — `app/streamlit_app.py`, `app/views/*`
  - [x] Feature Builder — 선수/요원 입력 → P1-P4 57개 피처 생성
  - [x] 예측 결과 — 승률, SHAP 기여도, 슬롯별 요원 교체 실험
  - [x] 기록 화면 — 기본 SQLite 예측 기록 저장/조회
  - [x] 가이드 화면 — 역할군, 맵별 강세 요원, 인기 승리 조합

---

## 진행 중 🔜

- [ ] **산출물 재생성 검증** — `data_pipeline -> train_model -> evaluate_model -> validate_metrics`를 같은 P1-P4 계약으로 재실행
- [ ] **v7 데이터 확장** — `visualize25` SQLite 로더를 provenance와 leakage guard 포함해 파이프라인에 통합
- [ ] **가설 검증 확장** — `ml/hypothesis_test.py`를 v7 100+ hypothesis cross-validation 체계로 확장
- [ ] **차별화 산출물** — 경쟁 제품 비교표, Insight Pack, counterfactual recommendation, Discovery dashboard

---

## 보류 / 범위 외 🚫

- HenrikDev API — 외부 API 미사용 방침으로 제외
- Riot VCT S3 API — 외부 API 미사용 방침으로 제외
- FastAPI / Next.js / 클라우드 배포 — 로컬 Streamlit 도구가 목표
- 일반 유저 데이터 수집 — 현재 프로/준프로 경기 데이터로 한정
- VLR.gg 직접 scraping — robots 정책 리스크로 기본 비활성화; 필요 시 cache/rate-limit 있는 unofficial API 경로만 명시적으로 사용
- PostgreSQL — 기본 범위 아님. 로컬 SQLite가 기본 저장소

---

## 참고 링크

| 문서 | 경로 |
|------|------|
| 전처리 계획 | `.omc/plans/preprocessing.md` |
| 피처 정의 | `docs/preprocessing.md` (섹션 7) |
| 데이터셋 목록 | `docs/datasets.md` |
| UI 설계 | `docs/ui_design.md` |
| 아키텍처 | `docs/overview.md` |
