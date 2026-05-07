# ValoPredictML 문서

Valorant 5v5 팀 구성 기반 승률 예측 ML 프로젝트 문서 모음.

## 서브디렉토리

| 디렉토리 | 내용 |
|---------|------|
| [01_overview](01_overview/) | 프로젝트 요약, 기술 스택, 설계 원칙, 로드맵 |
| [02_file_structure](02_file_structure/) | 저장소 디렉토리 구조, 파일별 역할 설명 |
| [03_architecture](03_architecture/) | 시스템 아키텍처, 요청 흐름, DB 스키마, API |
| [04_data_processing](04_data_processing/) | 전처리 파이프라인 — 파서 → 품질 게이트 → 피처 → 분할 |
| [05_data_learning](05_data_learning/) | ML 모델 전략, 학습, 앙상블, Optuna HPO |
| [06_model_test](06_model_test/) | ⚠️ 범위 외 — FastAPI 기반 테스트 문서 (참고용 보존) |
| [07_data](07_data/) | 데이터 소스, 스키마, 피처, 품질 메트릭 |
| [08_todo_list](08_todo_list/) | 프로젝트 작업 목록 및 진행 상태 |
| [09_web](09_web/) | ⚠️ 범위 외 — Next.js 프론트엔드 설계 (참고용 보존) |
| [10_valorant](10_valorant/) | Valorant 게임 규칙, 요원, 맵 |
| [11_ui_design](11_ui_design/) | Streamlit UI 화면 설계 |

## 루트 레벨 파일

| 파일 | 내용 |
|------|------|
| [overview.md](overview.md) | 프로젝트 개요 |
| [preprocessing.md](preprocessing.md) | 전처리 전략 요약 |
| [datasets.md](datasets.md) | Kaggle 데이터셋 카탈로그 |
| [valorant.md](valorant.md) | Valorant 규칙 요약 |
| [competitive_analysis.md](competitive_analysis.md) | 경쟁 프로젝트 차별점 분석 |
| [ui_design.md](ui_design.md) | UI 설계 요약 |
| [TODO.md](TODO.md) | 작업 목록 |

## 현재 상태 (2026-05-05)

- **ML 파이프라인**: 완료 — Ensemble AUC=0.9355, Acc=0.8540, F1=0.8508
- **Streamlit UI**: 미구현 (다음 단계)
- **범위 외**: FastAPI, Next.js, PostgreSQL, 클라우드 배포
