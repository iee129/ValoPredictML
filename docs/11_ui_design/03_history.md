# 03. 기록 화면 설계

> Streamlit 기반 — FastAPI/Next.js 사용 안 함
> 마지막 업데이트: 2026-05-04

---

## 1. 화면 목적

과거 조합 실험과 예측 결과를 조회하는 화면 설계 (참고용 — 예측 기록 영속화는 현재 미구현, PostgreSQL/SQLite 범위 외).

**왜 예측 기록을 저장하는가?**
같은 조합을 여러 번 실험하거나 "어제 시도한 조합과 오늘 시도한 조합 중 어느 쪽이 더 나은가"를 비교하려면 과거 결과를 다시 불러올 수 있어야 한다. 매번 다시 입력하는 대신 기록에서 불러와 교체 실험을 이어서 할 수 있도록 저장 기능을 제공한다. 현재는 미구현이며 DB 연동은 범위 외다.

---

## 2. 레이아웃

```
[기록 화면]

필터: 모델명 / 선수명 / 요원명 / 날짜 범위

┌────────────────────────────────────────────────────────┐
│ created_at │ model_name │ team_a │ team_b │ win_prob │
├────────────┼────────────┼────────┼────────┼──────────┤
│  ...       │  ...       │  ...   │  ...   │  ...     │
└────────────┴────────────┴────────┴────────┴──────────┘

[상세 보기]  [재실행]
```

---

## 3. 기능 명세

| 기능 | 설명 | Streamlit 컴포넌트 |
|------|------|-------------------|
| 기록 조회 | 입력 조합, 예측 확률, 모델명, 실행 시각 | `st.dataframe` |
| 필터 | 모델명, 선수명, 요원명, 날짜 범위 | `st.selectbox`, `st.date_input` |
| 상세 보기 | 영향 피처 + 교체 변화량 | `st.expander` |
| 재실행 | 과거 조합을 예측 화면으로 불러오기 | `st.button` + `st.session_state` |

---

## 4. 테이블 컬럼

| 컬럼 | 내용 |
|------|------|
| `created_at` | 예측 실행 시각 |
| `model_name` | 사용된 모델 (RF / XGBoost / LightGBM / 앙상블) |
| `team_a_players` | Team A 선수 5명 |
| `team_a_agents` | Team A 요원 5명 |
| `team_b_players` | Team B 선수 5명 |
| `team_b_agents` | Team B 요원 5명 |
| `win_probability` | 팀 A 예측 승률 |
| `top_factors` | 주요 영향 피처 (JSON) |

---

## 5. PostgreSQL 연동 (현재 미구현 — 범위 외)

예측 기록 영속화를 위한 PostgreSQL 후보 설계 (현재 미구현, 범위 외):

```python
# SQLAlchemy 후보 예시 (현재 미사용)
SELECT * FROM predictions
WHERE model_name = :model
  AND :agent = ANY(team_a_agents)
  AND created_at BETWEEN :start AND :end
ORDER BY created_at DESC
LIMIT 50;
```

DB 미연결 시 `st.warning("DB 연결 없음 — 기록 기능 비활성")` 표시 예정.
