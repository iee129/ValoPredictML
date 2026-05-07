# 01. 디렉토리 전체 구조

마지막 업데이트: 2026-05-04

## 1. 최상위 트리

```
ValoPredictML/
├── .venv/                          # Python 가상환경 (git 제외)
├── .env                            # 환경변수 (git 제외)
├── .gitignore
├── README.md
├── requirements.txt                # Python 의존성
├── dataload.py                     # Kaggle 데이터셋 다운로드 (구현 완료)
│
├── docs/                           # 프로젝트 문서 (이 폴더)
├── data/                           # 데이터 저장소
├── notebooks/                      # Jupyter 실험 노트북
├── models/                         # 학습된 모델
├── ml/                             # ML 파이프라인 (구현 완료)
│   ├── __init__.py
│   ├── agent_roles.py              # AGENT_ROLE_MAP(27개 요원), MAP_ORDER(12개 맵), 정규화 함수
│   ├── data_pipeline.py            # 전처리 파이프라인: 파서 → 품질 게이트 → 피처 → 분할
│   ├── train_model.py              # RF + XGBoost + LightGBM 학습, Optuna HPO, 앙상블
│   ├── evaluate_model.py           # GroupKFold(n=5) 교차 검증, SHAP TreeExplainer
│   └── validate_metrics.py         # baseline 비교, generalization 검증, SHAP 일관성
└── app/                            # Streamlit UI (Phase 5, 미구현)
```

**범위 외 (out of scope)**: `backend/` (FastAPI), `valo_predict_system/` (Next.js) 폴더는 이 프로젝트에 존재하지 않습니다. 본 프로젝트는 Streamlit 로컬 도구입니다.

---

## 2. 폴더별 역할 요약

| 폴더 | 역할 | 주요 작업 단계 |
|------|------|--------------|
| `docs/` | 설계 문서, 가이드, 전략 문서 | 전체 |
| `data/` | 원본/전처리 데이터 저장 | Phase 1-3 |
| `notebooks/` | EDA, 피처 실험, 모델 비교 노트북 | Phase 2-4 |
| `models/` | joblib 모델, 메타데이터 저장 | Phase 4 |
| `ml/` | 파서, 전처리 파이프라인, 학습, 평가 스크립트 (구현 완료) | Phase 2-4 |
| `app/` | Streamlit 앱 | Phase 5 |

---

## 3. `docs/` 폴더 구조

```
docs/
├── 01_overview/              # 프로젝트 개요, 기술 스택, 설계 원칙
│   ├── 01_project_summary.md
│   ├── 02_tech_stack.md
│   ├── 03_design_principles.md
│   └── 04_roadmap_and_team.md
├── 02_file_structure/        # 파일 구조 설명 (이 폴더)
│   ├── 01_directory_overview.md
│   ├── 02_backend_files.md
│   ├── 03_ml_pipeline_files.md
│   ├── 04_frontend_files.md
│   └── 05_config_and_env.md
├── 03_architecture/          # 시스템 아키텍처
│   ├── 01_system_overview.md
│   ├── 02_request_flow.md
│   ├── 03_database_schema.md
│   ├── 04_api_design.md
│   ├── 05_deployment_architecture.md
│   └── 06_ml_pipeline_architecture.md
├── overview.md               # 프로젝트 정전 개요 (iee 정전 문서)
├── preprocessing.md          # 전처리 파이프라인 정전 설계 (iee 정전 문서)
└── datasets.md               # 7개 Kaggle 데이터셋 가이드 (iee 정전 문서)
```

---

## 4. `data/` 폴더 구조

```
data/
├── raw/                    # 절대 수정 금지. 원본 CSV 그대로 보관 (git 제외)
│   └── kaggle/             # Kaggle 7개 데이터셋 (2.3GB)
│       ├── vct_2021_2023/
│       ├── ryanluong1__valorant-challengers-league-data/
│       ├── qualidea1217__valorant-pro-matches-since-april-2021/
│       └── ediashtarevin__vct-champions-2023-stats/
└── processed/              # 전처리 스크립트 실행 결과물 (git 제외)
    ├── matches_clean.csv   # 품질 게이트·dedup 통과한 맵 행 전체
    ├── features_base.csv   # 피처 테이블 (43개 피처 + 레이블)
    ├── train.csv           # 학습용 (70%)
    ├── val.csv             # 검증용 (15%)
    └── test.csv            # 테스트용 (15%)
```

**규칙:**
- `raw/`는 `ml/data_pipeline.py`가 읽기 전용으로 사용
- `processed/`는 학습 파이프라인의 입/출력
- Git에서 `data/raw/`와 `data/processed/`는 `.gitignore` 처리

---

## 5. `models/` 폴더 구조

```
models/
├── rf_model.joblib             # 학습된 Random Forest 모델
├── xgboost_model.joblib        # 학습된 XGBoost 모델
├── lgbm_model.joblib           # 학습된 LightGBM 모델
├── label_encoder_map.joblib    # 맵 이름 LabelEncoder
└── model_metadata.json         # 학습 날짜, 성능 지표, 파라미터
```

- 모든 `.joblib` 파일은 `.gitignore` 처리 (용량)
- `model_metadata.json`은 Git 추적 허용 (텍스트, 경량)

---

## 6. `reports/` 폴더 구조

```
reports/                        # 파이프라인 실행 결과 리포트 (git 제외)
├── preprocess_summary.json     # 소스별 행수·제거율·최종 분포 등 실행 통계
└── rejected_matches.csv        # 품질 게이트 탈락 행 및 탈락 사유
```

---

## 7. `notebooks/` 폴더 구조

```
notebooks/
├── 01_eda.ipynb                # 탐색적 데이터 분석
├── 02_feature_engineering.ipynb# 피처 생성 실험
├── 03_model_comparison.ipynb   # RF vs XGBoost vs LightGBM 비교
└── 04_kfold_validation.ipynb   # K-Fold(K=5) 교차 검증 실험
```

- 실제 운영 코드가 아닌 **실험/탐색용**
- 발견한 인사이트는 `ml/` 폴더 스크립트로 이식

---

## 8. 관련 문서

| 문서 | 내용 |
|------|------|
| [03_ml_pipeline_files.md](03_ml_pipeline_files.md) | `ml/` 폴더 실행 순서 및 의존성 |
| [04_frontend_files.md](04_frontend_files.md) | `app/` Streamlit 구조 |
| [05_config_and_env.md](05_config_and_env.md) | `.env` 변수, gitignore, 명명 규칙 |
