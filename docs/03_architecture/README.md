# 03_architecture — 시스템 아키텍처

ValoPredictML의 시스템 구조, 데이터 흐름, API 설계를 다루는 문서 모음.

## 파일 목록

| 파일 | 내용 |
|------|------|
| [01_system_overview.md](01_system_overview.md) | 전체 시스템 구성도 |
| [02_request_flow.md](02_request_flow.md) | 요청/응답 흐름 (입력 → 예측 → DB 저장 → 출력) |
| [04_api_design.md](04_api_design.md) | API 설계 (FastAPI `src/api` — HTTP 계약 SSOT는 `docs/08_web`) |
| [06_ml_pipeline_architecture.md](06_ml_pipeline_architecture.md) | ML 파이프라인 상세 아키텍처 |

> DB 스키마(`prediction_history` 테이블, SQLAlchemy Core, docker-compose) 상세: [`docs/08_web/02_backend_fastapi/06_history_and_db.md`](../08_web/02_backend_fastapi/06_history_and_db.md)
