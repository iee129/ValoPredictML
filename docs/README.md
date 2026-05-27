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

## 현재 상태 (2026-05-27)

- **Baseline ML 파이프라인**: 완료 — Kaggle-only previous-year 184피처, train+val 학습, Test AUC=0.6707, 데이터 누수 6관문 PASS
- **차별점 강화 스프린트 (2026-05-28 ~ 2026-06-08)**: 진행 — 사용자 측면 차별점 10개 (I·N·K·G·B·C·J·D·A·E) Streamlit 단일 도구 통합
  - 원본 계획: `.omc/plans/user_facing_differentiators_plan.md`
  - 시장 빈자리 분석: [competitive_analysis.md](competitive_analysis.md)
  - VLR.gg 데이터원 매핑: [07_data/02_primary_datasets/04_vlrgg.md](07_data/02_primary_datasets/04_vlrgg.md)
  - 일정 상세: [01_overview/04_roadmap_and_team.md](01_overview/04_roadmap_and_team.md) 섹션 1.1
- **심화 모델**: 5/31 (Kaggle 단독) + 6/3 (Kaggle+VLR.gg 통합) 학습 예정
- **Streamlit UI**: 5/29~6/7 차별점 모듈과 함께 점진적 통합 (`app/main.py` 단일 진입점)
- **기말 발표**: 2026-06-09
- **범위 외**: FastAPI, Next.js, 클라우드 배포 (PostgreSQL/SQLite는 현재 범위에서 미사용)
