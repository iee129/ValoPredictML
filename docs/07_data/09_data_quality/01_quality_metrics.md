# 01. 데이터 품질 지표 및 품질 게이트

마지막 업데이트: 2026-05-04

---

## 1. 품질 게이트 (Phase 3)

아래 조건 중 하나라도 실패하면 해당 맵 행 제외 → `reports/rejected_matches.csv`에 기록.

| 조건 | 기준 | 이유 |
|------|------|------|
| 팀당 요원 수 | 팀 A·B 각각 정확히 5명 | 5명 아니면 역할군 카운트 피처 부정확 |
| 요원 유효성 | 5명 모두 AGENT_ROLE_MAP에 존재 | 알 수 없는 요원 → 역할군 집계 불가 |
| 맵 유효성 | MAP_ORDER에 존재 | map_encoded / atk_side_advantage 집계 불가 |
| 레이블 유효성 | winner가 team_a 또는 team_b | 레이블 없으면 지도학습 불가 |
| 핵심 스탯 결측 | ACS·KD 각 선수 모두 비결측 | 핵심 선수 스탯 피처 생성 불가 |
| 소스 비중 | 단일 소스 < 학습셋 전체의 20% | 소스 편향 방지 |
| 승패 동점 | score_a ≠ score_b | 동점(overtime 등)은 레이블 불명확 |

---

## 2. 품질 지표 목표

| 지표 | 최소 기준 | 권장 기준 |
|------|---------|--------|
| 역할군 합계=5 비율 | 95% | 99% |
| 미인식 요원 수 | 0개 | 0개 |
| 미인식 맵 수 | 0개 | 0개 |
| 레이블 균형 (0:1) | 45:55 ~ 55:45 | 48:52 ~ 52:48 |
| 최소 맵 행 수 | 80K | 100K |

---

## 3. 품질 검증 코드

```python
def run_quality_gate(row: dict) -> tuple[bool, str]:
    """단일 맵 행 품질 게이트. (통과, 사유)를 반환."""
    agents_a = [p["agent"] for p in row["players_a"]]
    agents_b = [p["agent"] for p in row["players_b"]]

    if len(agents_a) != 5 or len(agents_b) != 5:
        return False, "팀당 요원 수 != 5"

    for agent in agents_a + agents_b:
        if agent not in AGENT_ROLE_MAP:
            return False, f"미인식 요원: {agent}"

    if row["map"] not in MAP_ORDER:
        return False, f"미인식 맵: {row['map']}"

    if row["label"] not in (0, 1):
        return False, "레이블 유효하지 않음"

    if row["score_a"] == row["score_b"]:
        return False, "동점 — 레이블 불명확"

    for p in row["players_a"] + row["players_b"]:
        if p.get("acs") is None or p.get("kd") is None:
            return False, "ACS 또는 KD 결측"

    return True, ""
```

---

## 4. KAST 결측 처리

| 소스 | KAST 가용성 |
|------|------------|
| vct_2021_2023 | ✅ |
| ryanluong challengers | ✅ |
| qualidea | ✅ |
| ~~piyush 2024/2025~~ | ~~⚠️ 일부 이벤트 결측~~ | (제거됨) |
| ediashtarevin | ✅ |
| kierru | ❌ 제거됨 (리젝션율 80%) |

처리 원칙:
1. 행 레벨 결측 (특정 선수만): 동일 경기 팀 평균으로 imputation.
2. 이벤트 전체 결측 (~~piyush 일부~~ — piyush 소스 제거됨): `a_avg_kast`/`b_avg_kast`를 `-1` 플래그로 채움.
3. KAST 결측 행이 전체 학습셋의 20% 초과 시 해당 피처 제외 후 재실험.
