# 02. 예측 요청 흐름

마지막 업데이트: 2026-05-04

> **범위 외 (out of scope)**: 이 프로젝트는 FastAPI REST API를 사용하지 않습니다. Streamlit이 Python 함수를 직접 호출합니다.

## 1. 전체 흐름 다이어그램

```
사용자 (Streamlit UI)
    │
    │  1. 맵 선택, 팀 A/B 선수 5명 + 요원 5명 선택 후 "예측 실행" 클릭
    ↓
[app/main.py]
    │
    │  2. 입력값 검증
    │     - 팀당 요원 정확히 5명
    │     - 요원 이름 유효성 (normalize_agent → None 이면 오류 표시)
    ↓
[피처 빌더 (인라인 또는 ml/ 함수 호출)]
    │
    │  3. normalize_agent() → 역할군 매핑 (ml/agent_roles.py)
    │
    │  4. 역할군 카운트 계산 (12개 피처)
    │     a_duelist, a_initiator, a_controller, a_sentinel
    │     b_duelist, b_initiator, b_controller, b_sentinel
    │     diff_duelist, diff_initiator, diff_controller, diff_sentinel
    │
    │  5. 역할군 파생 피처 (4개)
    │     has_controller_a, has_controller_b
    │     is_double_duelist_a, is_double_duelist_b
    │
    │  6. 선수 스탯 피처 (12개)
    │     a_avg_acs, b_avg_acs, a_avg_kd, b_avg_kd
    │     a_avg_kast, b_avg_kast, a_avg_adr, b_avg_adr
    │     a_max_clutch, b_max_clutch, a_avg_hs, b_avg_hs
    │
    │  7. 시너지 피처 (6개)
    │     a_fk_fd_ratio, b_fk_fd_ratio
    │     a_avg_assists, b_avg_assists
    │     a_kast_std, b_kast_std
    │
    │  8. 요원 조합 피처 (6개) — 사전 집계값 join
    │     a_avg_agent_map_wr, b_avg_agent_map_wr
    │     a_avg_agent_pick_rate, b_avg_agent_pick_rate
    │     a_avg_agent_exp, b_avg_agent_exp
    │
    │  9. 맵 피처 (3개)
    │     map_encoded, atk_side_advantage, is_attacker_a
    │
    │  반환: shape (1, 125) NumPy 배열 (advanced 계약, FEATURE_COLS_ADVANCED)
    ↓
[앙상블 예측]
    │
    │  10. ensemble_model.predict_proba(X)
    │      — models/advanced/ensemble.joblib (VotingClassifier soft voting)
    │      — 내부적으로 RF + XGBoost + LightGBM 가중평균 (weights=[1,1,1])
    │
    │  11. 최종 승률 반환
    │      final_prob = ensemble_model.predict_proba(X)[0][1]
    ↓
[Streamlit UI 출력]
    │
    │  14. 승률 표시 (팀 A: X%, 팀 B: Y%)
    │  15. 피처 중요도 바 차트 (Plotly)
    │  16. 역할군 분포 레이더 차트 (Plotly)
    │  17. SHAP 분석 (구현 시)
    │  18. 교체 시뮬레이션 — 선수/요원 교체 전후 delta 표시
    ↓
[PostgreSQL 저장 (후보, 미구현)]
    │
    │  19. predictions 테이블 INSERT
    ↓
사용자 화면
```

---

## 2. 단계별 피처 목록 (125개, advanced 계약)

> 아래는 advanced 계약(FEATURE_COLS_ADVANCED, 125피처)의 주요 카테고리 요약이다. 전체 목록은 `models/advanced/meta.json` `feature_names` 참조.

| 번호 | 카테고리 | 피처명 예시 | 설명 |
|------|----------|--------|------|
| 1~4 | 역할군 카운트 (A) | `a_duelist` ~ `a_sentinel` | 팀 A 4역할군 수 |
| 5~8 | 역할군 카운트 (B) | `b_duelist` ~ `b_sentinel` | 팀 B 4역할군 수 |
| 9~12 | 역할군 diff | `diff_duelist` ~ `diff_sentinel` | A − B 차이 (−5~5) |
| 13~14 | 역할군 파생 | `has_controller_a`, `has_controller_b` | Controller ≥ 1 (0/1) |
| 15~16 | 역할군 파생 | `is_double_duelist_a`, `is_double_duelist_b` | Duelist ≥ 2 (0/1) |
| 17~18 | 선수 스탯 | `a_avg_acs`, `b_avg_acs` | 팀 평균 ACS |
| 19~20 | 선수 스탯 | `a_avg_kd`, `b_avg_kd` | 팀 평균 KD |
| 21~22 | 선수 스탯 | `a_avg_kast`, `b_avg_kast` | 팀 평균 KAST |
| 23~24 | 선수 스탯 | `a_avg_adr`, `b_avg_adr` | 팀 평균 ADR |
| 25~26 | 선수 스탯 | `a_max_clutch`, `b_max_clutch` | 팀 최고 클러치율 |
| 27~28 | 선수 스탯 | `a_avg_hs`, `b_avg_hs` | 팀 평균 헤드샷율 |
| 29~30 | 시너지 | `a_fk_fd_ratio`, `b_fk_fd_ratio` | FK/FD 비율 |
| 31~32 | 시너지 | `a_avg_assists`, `b_avg_assists` | 팀 평균 어시스트 |
| 33~34 | 시너지 | `a_kast_std`, `b_kast_std` | KAST 표준편차 |
| 35~36 | 요원 조합 | `a_avg_agent_map_wr`, `b_avg_agent_map_wr` | 요원×맵 평균 승률 |
| 37~38 | 요원 조합 | `a_avg_agent_pick_rate`, `b_avg_agent_pick_rate` | 요원×맵 평균 픽률 |
| 39~40 | 요원 조합 | `a_avg_agent_exp`, `b_avg_agent_exp` | 선수-요원 경험치 |
| 41 | 맵 | `map_encoded` | 맵 Label Encoding (0~12, 13개 맵) |
| 42 | 맵 | `atk_side_advantage` | 맵별 공격 사이드 승률 |
| 43 | 맵 | `is_attacker_a` | 팀 A 선공 여부 (0/1) |
| 44~125 | 요원 one-hot 등 | `a_agent_*_count`, `b_agent_*_count` 등 | 29종 요원 카운트·one-hot 등 advanced 전용 피처 |

---

## 3. 앙상블 계산

```python
# 단일 ensemble.joblib 로드 (VotingClassifier soft voting, weights=[1,1,1])
model = joblib.load("models/advanced/ensemble.joblib")

# 단일 predict_proba 호출 — 내부적으로 RF + XGBoost + LightGBM 가중평균
final_prob = model.predict_proba(X)[0][1]   # 팀 A 승률
p_b = 1 - final_prob
```

---

## 4. 에러 처리

| 상황 | 처리 방법 |
|------|-----------|
| 팀당 5명 미만/초과 | Streamlit 경고 메시지 표시, 예측 버튼 비활성화 |
| 알 수 없는 요원 | normalize_agent() → None → 경고 메시지 |
| 모델 파일 없음 | `FileNotFoundError` 안내 메시지 (Phase 4 미완료 안내) |
| KAST 결측 | -1 플래그 또는 팀 평균 imputation |

---

## 5. 관련 문서

| 문서 | 내용 |
|------|------|
| [../04_data_processing/06_feature_engineering.md](../04_data_processing/06_feature_engineering.md) | baseline 178 / advanced 125 피처 생성 상세 |
| [06_ml_pipeline_architecture.md](06_ml_pipeline_architecture.md) | ML 파이프라인 전체 |
| [03_database_schema.md](03_database_schema.md) | predictions 테이블 스키마 |
