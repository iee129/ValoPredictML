# 01. 홈 화면 설계

> Streamlit 기반 — FastAPI/Next.js 사용 안 함
> 마지막 업데이트: 2026-05-04

---

## 1. 화면 목적

앱 진입 시 바로 조합을 입력하고 예측을 실행할 수 있는 화면.

---

## 2. 레이아웃

```
ValoPredictML — 발로란트 라인업 실험실

[모델 상태]  [DB 연결 상태]  [최근 평가 지표]

Team A 입력          Team B 입력
- 선수 5명           - 선수 5명
- 요원 5명           - 요원 5명

[예측 실행]

결과:
- 팀 A 승리 확률
- 주요 영향 피처
- 선수-요원 적합도
- 팀 시너지/충돌 요인
```

---

## 3. 상단 상태 표시

| 항목 | Streamlit 컴포넌트 | 내용 |
|------|-------------------|------|
| 모델 상태 | `st.metric` | 로드된 모델명 (앙상블 ensemble.joblib) |
| DB 연결 상태 | `st.metric` | 예측 기록 영속화는 현재 미구현 (PostgreSQL/SQLite 범위 외) |
| 최근 평가 지표 | `st.metric` × 3 | Accuracy, ROC-AUC, F1 |

---

## 4. 입력 영역

`st.columns(2)` 로 Team A / Team B 나란히 배치.

| 입력 | 컴포넌트 | 검증 |
|------|---------|------|
| Team A/B 선수 | `st.multiselect` | 각 5명 |
| Team A/B 요원 | `st.multiselect` 또는 슬롯별 `st.selectbox` | 각 5명 |
| 선수 정보 | `st.data_editor` | 결측/범위 확인 |

사용자는 피처를 직접 입력하지 않음. Feature Builder가 역할군 카운트, 선수-요원 적합도, 팀 통계를 자동 생성.

---

## 5. 예측 실행

`st.button("예측 실행")` — Team A/B 각 5명 선택 완료 후 활성화.

---

## 6. 결과 표시

| 출력 | 컴포넌트 |
|------|---------|
| 팀 A 승리 확률 | `st.metric` 또는 게이지 |
| 팀 B 승리 확률 | `1 - 팀 A 확률` |
| 주요 영향 피처 | `st.bar_chart` |
| 선수-요원 적합도 | 슬롯별 점수 표 (`st.dataframe`) |
| 팀 시너지/충돌 | `st.text` 요약 |
