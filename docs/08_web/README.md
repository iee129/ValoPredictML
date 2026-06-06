# docs/08_web — 현행 웹 설계 SSOT

FastAPI + Next.js 웹 스택(`src/api/`, `web/`)의 설계 문서.
모델 feature 수, 성능, 검증 verdict는 이 경로의 예시가 아니라 다음 원천을 따른다.

- `models/advanced/meta.json`
- `reports/advanced/metrics.json`
- `reports/advanced/validation.json`
- `docs/05_data_learning/`

새 웹 문서나 링크는 이 경로(`docs/08_web/`)에 추가한다.

---

## 색인

| 폴더 | 내용 |
|------|------|
| `01_overview/` | 목적·범위, 아키텍처, 기술 스택 |
| `02_backend_fastapi/` | 앱 구조, 모델 서빙, 엔드포인트, 스키마, 실행·CORS, **[히스토리·DB](02_backend_fastapi/06_history_and_db.md)** |
| `03_frontend_nextjs/` | 라우팅, 타입·API 클라이언트, 예측 페이지, 기타 페이지·컴포넌트 |
| `04_integration/` | 데이터 계약(SSOT), 시연 런북 |
| `06_insights/` | 인사이트 시스템(요원-맵 적합도·메타 조합·구성 결함·자연어 근거) |
| `07_styling/` | 비주얼 토큰, 레이아웃·시연 대시보드 |
| `08_testing/` | 테스트 전략 |
