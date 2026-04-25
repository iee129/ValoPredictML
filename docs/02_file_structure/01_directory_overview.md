# 01. 디렉토리 전체 구조

## 1. 최상위 트리

```
ValoPredictML/
├── .venv/                          # Python 가상환경 (git 제외)
├── .env                            # 환경변수 (git 제외)
├── .gitignore
├── README.md
├── requirements.txt                # Python 의존성
├── dataload.py                     # Kaggle 데이터셋 다운로드
├── overview.md                     # 프로젝트 회의록
├── riot.txt                        # HenrikDev API Key (git 제외)
│
├── docs/                           # 📄 프로젝트 문서 (이 폴더)
├── data/                           # 📊 데이터 저장소
├── notebooks/                      # 📓 Jupyter 실험 노트북
├── models/                         # 🤖 학습된 모델
├── backend/                        # 🖥️ FastAPI 백엔드
├── ml/                             # 🔬 ML 파이프라인
└── valo_predict_system/            # 🌐 Next.js 프론트엔드
```

---

## 2. 폴더별 역할 요약

| 폴더 | 역할 | 주요 작업 단계 |
|---|---|---|
| `docs/` | 설계 문서, 가이드, 전략 문서 | 전체 |
| `data/` | 원본/전처리/외부 데이터 저장 | Phase 1-2 |
| `notebooks/` | EDA, 피처 실험, 모델 비교 노트북 | Phase 2-3 |
| `models/` | joblib 모델, 메타데이터 저장 | Phase 3 |
| `backend/` | FastAPI 서버, DB 연결, 라우터 | Phase 4 |
| `ml/` | 데이터 파이프라인, 학습, 평가 스크립트 | Phase 2-3 |
| `valo_predict_system/` | Next.js 프론트엔드 앱 | Phase 5-7 |

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
├── 04_data_processing/       # 데이터 전처리 파이프라인
├── 05_data_learning/         # 모델 학습 전략
├── 06_model_test/            # FastAPI 테스트 및 검증
├── 07_data/                  # 데이터셋 상세 분석 (30개 파일)
├── 08_todo_list/             # 전체 Todo List
├── 09_web/                   # Next.js 웹 설계 (다수 파일)
├── 10_valorant/              # 발로란트 게임 설명
└── 11_ui_design/             # UI 디자인 가이드
```

---

## 4. `data/` 폴더 구조

```
data/
├── raw/                    ← 절대 수정 금지. 원본 CSV 그대로 보관
│   ├── vct_2021/           ← Kaggle VCT 2021 데이터
│   ├── vct_2022/           ← Kaggle VCT 2022 데이터
│   └── vct_2023/           ← Kaggle VCT 2023 데이터
├── processed/              ← 전처리 스크립트 실행 결과물
│   ├── features.csv        ← 피처 엔지니어링 완료 데이터
│   ├── train.csv           ← 학습용 (70%)
│   ├── val.csv             ← 검증용 (15%)
│   └── test.csv            ← 테스트용 (15%)
└── external/               ← HenrikDev API 수집 데이터
    └── henrik_matches.csv
```

**규칙:**
- `raw/`는 `ml/data_pipeline.py`가 읽기 전용으로 사용
- `processed/`는 학습 파이프라인의 입/출력
- Git에서 `data/raw/`와 `data/processed/`는 `.gitignore` 처리

---

## 5. `models/` 폴더 구조

```
models/
├── xgboost_model.joblib        ← 학습된 XGBoost 모델
├── lgbm_model.joblib           ← 학습된 LightGBM 모델
├── label_encoder_map.joblib    ← 맵 이름 LabelEncoder
└── model_metadata.json         ← 학습 날짜, 성능 지표, 파라미터
```

- 모든 `.joblib` 파일은 `.gitignore` 처리 (용량)
- `model_metadata.json`은 Git 추적 허용 (텍스트, 경량)

---

## 6. `notebooks/` 폴더 구조

```
notebooks/
├── 01_eda.ipynb                ← 탐색적 데이터 분석
├── 02_feature_engineering.ipynb← 피처 생성 실험
├── 03_model_comparison.ipynb   ← RF vs XGBoost vs LightGBM 비교
└── 04_hyperparameter_tuning.ipynb ← Optuna 실험
```

- 실제 운영 코드가 아닌 **실험/탐색용**
- 발견한 인사이트는 `ml/` 폴더 스크립트로 이식

---

## 7. 관련 문서

| 문서 | 내용 |
|---|---|
| [02_backend_files.md](02_backend_files.md) | `backend/` 폴더 각 파일 상세 |
| [03_ml_pipeline_files.md](03_ml_pipeline_files.md) | `ml/` 폴더 실행 순서 및 의존성 |
| [04_frontend_files.md](04_frontend_files.md) | `valo_predict_system/` App Router 구조 |
| [05_config_and_env.md](05_config_and_env.md) | `.env` 변수, gitignore, 명명 규칙 |
