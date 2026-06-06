# 02. 예측 요청 흐름

마지막 업데이트: 2026-05-31

> **현행 요청 경로**: 브라우저(`web`) → Next Route Handler(`/api`) → FastAPI(`src/api`) → `src/inference/predict.py`. (구 Streamlit 직접 호출 경로는 폐기됨.)

## 1. 전체 흐름 다이어그램

```
사용자 (브라우저, Next.js web)
    │
    │  1. 맵 선택, 팀 A/B 선수 5명 + 요원 5명 선택 후 "예측 실행" 클릭
    ↓
[web → Next Route Handler /api → FastAPI src/api (POST /predict)]
    │
    │  2. 입력값 검증 (Pydantic schemas.py)
    │     - 팀당 요원 정확히 5명
    │     - 요원 이름 유효성 (normalize_agent → None 이면 오류 표시)
    ↓
[피처 빌더 (`src/inference/predict.py` → `features.preprocess` 재사용)]
    │
    │  3. 맵 원핫 생성 (Drift 제외 12개)
    │  4. normalize_agent() → 역할군·요원 count 생성
    │  5. 선수 prior, synergy, map-agent, player-agent 이전 연도 집계 조회
    │  6. cold-start flag, team prior form, map attack advantage 추가
    │  반환: shape (1, 179) DataFrame (advanced 계약, FEATURE_COLS_ADVANCED)
    ↓
[앙상블 예측]
    │
    │  10. ensemble_model.predict_proba(X)
    │      — models/advanced/ensemble.joblib (VotingClassifier soft voting)
    │      — 내부적으로 RF + XGBoost + LightGBM 가중평균 (weights=[2.0, 3.0, 0.1])
    │
    │  11. 최종 승률 반환
    │      final_prob = ensemble_model.predict_proba(X)[0][1]
    ↓
[FastAPI 직렬화 → web 출력 (React/Tailwind)]
    │
    │  12. save_prediction(req, response) — prediction_history 테이블에 자동 저장
    │      (선택적: VALO_DATABASE_URL 미설정 시 경고 로그 후 skip, 예측 응답에는 영향 없음)
    │  13. 승률 표시 (팀 A: X%, 팀 B: Y%)
    │  14. 피처 중요도 발산형 막대 차트
    │  15. 역할군 분포 레이더 차트
    │  16. 자연어 승부 근거
    ↓
사용자 화면
```

---

## 2. 단계별 피처 목록 (179개, advanced 계약)

> 아래는 advanced 계약(FEATURE_COLS_ADVANCED, 179피처)의 주요 카테고리 요약이다. 전체 목록은 `models/advanced/meta.json` `feature_names` 참조.

| 카테고리 | 피처명 예시 | 설명 |
|----------|--------|------|
| 맵/역할/요원 | `map_ascent`, `a_role_duelist_count`, `b_agent_jett_count` | 맵과 양 팀 조합 구성 |
| 선수 prior | `a_prior_kd_mean`, `diff_prior_adr_mean` | 이전 연도 선수 평균 |
| Synergy | `a_synergy_mean`, `diff_synergy_mean` | 이전 연도 동반 출전 경험 |
| 맵×요원 / 선수×요원 | `a_map_agent_kd_mean`, `a_player_agent_adr_mean` | 이전 연도 조건부 성과 |
| 팀 form / meta / cold-start | `diff_team_form5_success`, `comp_meta_wr`, `map_agent_history_missing` | 팀 최근 흐름, 조합 메타, 기록 없음 여부 |

---

## 3. 앙상블 계산

```python
# 단일 ensemble.joblib 로드 (VotingClassifier soft voting, weights=[2.0, 3.0, 0.1])
model = joblib.load("models/advanced/ensemble.joblib")

# 단일 predict_proba 호출 — 내부적으로 RF + XGBoost + LightGBM 가중평균
final_prob = model.predict_proba(X)[0][1]   # 팀 A 승률
p_b = 1 - final_prob
```

---

## 4. 에러 처리

| 상황 | 처리 방법 |
|------|-----------|
| 팀당 5명 미만/초과 | 프런트 폼 검증 + 백엔드 422 응답, 예측 버튼 비활성화 |
| 알 수 없는 요원 | normalize_agent() → None → 경고 메시지 |
| 모델 파일 없음 | `FileNotFoundError` 안내 메시지 (Phase 4 미완료 안내) |
| KAST 결측 | -1 플래그 또는 팀 평균 imputation |

---

## 5. 관련 문서

| 문서 | 내용 |
|------|------|
| [../04_data_processing/06_feature_engineering.md](../04_data_processing/06_feature_engineering.md) | baseline 421 / advanced 179 피처 생성 상세 |
| [06_ml_pipeline_architecture.md](06_ml_pipeline_architecture.md) | ML 파이프라인 전체 |
