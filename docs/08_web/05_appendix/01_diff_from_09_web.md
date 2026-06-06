# 01. 구 `docs/08_web` 대비 변경 기록

이 파일이 속한 `docs/08_web/`은 기존에 루트에 별도 디렉터리로 존재하던 현행 웹 설계 SSOT를 `docs/` 트리로 통합한 결과다.
통합 전 존재했던 구 `docs/08_web/`은 Streamlit 시대 폐기 설계로, 삭제됐다.

## 구 docs/08_web 대비 바로잡은 점

| 항목 | 구 docs/08_web (폐기) | 현재 docs/08_web (본 경로) |
|---|---|---|
| 프론트 언어 | JavaScript 구상 | TypeScript |
| 예측 입력 | 맵 + 요원 5개씩 | 맵 + 기준연도 + 팀별 `{player, agent}` 5개 |
| 응답 | 임의 승률/feature 필드 | `PredictResponse` 직렬화 |
| 페이지 | `/history`, `/analytics` 중심 | `/predict`, `/replay`, `/model` 중심 |
| 모델 수치 | 문서 예시값 | 모델 산출물과 리포트 값 |
