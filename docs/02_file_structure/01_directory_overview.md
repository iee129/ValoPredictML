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
├── ml/                             # ML 파이프라인
│   ├── __init__.py
│   ├── valorant.py                 # 요원→역할 매핑, 맵 목록, 정규화 함수 (미구현)
│   ├── baseline/                   # 단순 베이스라인 모델 (미구현)
│   │   ├── preprocess.py
│   │   ├── train.py
│   │   ├── evaluate.py
│   │   └── validate.py
│   ├── advanced/                   # RF + XGBoost + LightGBM 앙상블 (미구현)
│   │   ├── preprocess.py
│   │   ├── ensemble.py
│   │   ├── evaluate.py
│   │   └── validate.py
│   └── vlrgg/                      # VLR.gg 데이터 수집 (부분 구현)
│       ├── client.py
│       ├── collector.py
│       └── worker.py
└── app/                            # Streamlit UI (미구현)
    ├── main.py                     # Streamlit 진입점
    └── predict.py                  # 모델 로드 + 추론
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
    ├── matches.csv         # 품질 게이트·dedup 통과한 맵 행
    ├── players.csv         # 선수 스탯 집계
    ├── teams.csv           # 팀별 집계
    ├── features_lineup.csv # 요원 조합 피처
    ├── features_static.csv # 정적 피처 (맵·역할군 등)
    ├── files.csv           # 소스 파일 레지스트리
    ├── schemas.csv         # 스키마 정의
    ├── sources.csv         # 소스별 메타데이터
    ├── rejects.csv         # 품질 게이트 탈락 행
    ├── train.csv           # 학습용 (70%)
    ├── val.csv             # 검증용 (15%)
    └── test.csv            # 테스트용 (15%)
```

**규칙:**
- `raw/`는 `ml/baseline/preprocess.py`, `ml/advanced/preprocess.py`가 읽기 전용으로 사용
- `processed/`는 학습 파이프라인의 입/출력
- Git에서 `data/raw/`와 `data/processed/`는 `.gitignore` 처리

---

## 5. `models/` 폴더 구조

```
models/
├── baseline/               # 베이스라인 (로지스틱 회귀)
│   ├── model.joblib        # 학습된 모델
│   └── meta.json           # 학습 메타데이터
└── advanced/               # 최종 채택된 advanced 모델만
    ├── rf.joblib            # Random Forest
    ├── xgb.joblib           # XGBoost
    ├── lgbm.joblib          # LightGBM
    └── meta.json            # 학습 날짜, AUC·Acc·F1
```

**규칙**: `models/`에는 **최종 채택된 모델 파일만** 저장한다. 실험 중인 버전은 `notebooks/v{N}_{algorithm}/` 안에만 보관한다.

- 모든 `.joblib` 파일은 `.gitignore` 처리 (용량)
- `meta.json`은 Git 추적 허용 (텍스트, 경량)

---

## 6. `reports/` 폴더 구조

```
reports/                        # 파이프라인 실행 결과 리포트 (git 제외)
├── baseline/                   # 베이스라인 모델 리포트
│   ├── metrics.json            # CV AUC·Acc·F1 + 테스트 지표
│   └── validation.json         # 다수결 비교·과적합 진단·피처 계수
└── v{N}_{algorithm}/           # advanced 버전별 리포트 (예: v1_random_forest/)
    └── metrics.json
```

**규칙**: `reports/`의 버전 폴더명은 `notebooks/`의 실험 폴더명과 동일하게 유지한다.

---

## 7. `notebooks/` 폴더 구조

```
notebooks/
└── v{N}_{algorithm}/           # advanced 후보 실험 폴더 (예: v1_random_forest/)
    └── experiment.ipynb        # 실험 노트북 (폴더 먼저 생성 후 파일 생성)
```

**규칙**:
- `notebooks/`에 파일을 직접 생성하지 않는다 → `v{N}_{algorithm}/` 폴더를 먼저 만든 뒤 그 안에 노트북을 생성한다
- 폴더명 형식: `v{N}_{algorithm}` (N은 1부터 증가, algorithm은 영어 snake_case)
- 베이스라인(로지스틱 회귀)은 버전 번호 없음 — `ml/baseline/`에서 직접 관리
- 발견한 인사이트는 `ml/advanced/`로 최종 이식

---

## 8. 관련 문서

| 문서 | 내용 |
|------|------|
| [03_ml_pipeline_files.md](03_ml_pipeline_files.md) | `ml/` 폴더 실행 순서 및 의존성 |
| [04_frontend_files.md](04_frontend_files.md) | `app/` Streamlit 구조 |
| [05_config_and_env.md](05_config_and_env.md) | `.env` 변수, gitignore, 명명 규칙 |
