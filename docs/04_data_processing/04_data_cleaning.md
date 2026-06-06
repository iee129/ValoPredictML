# 04. 데이터 클리닝 — 품질 검사 및 dedup

마지막 업데이트: 2026-05-04

## 1. 개요

파싱·정규화 이후 두 단계 클리닝이 진행된다.

1. **품질 검사** (Phase 3): 개별 행이 학습에 적합한지 7개 조건 검사
2. **dedup_key 중복 제거** (Phase 4): 여러 소스에 걸친 동일 경기 중복 제거

---

## 2. 품질 검사 (Phase 3)

아래 조건 중 하나라도 해당하면 해당 맵 행 제외 → `data/processed/rejects.csv`에 기록.

| 조건 | 기준 | 왜 |
|------|------|----|
| 팀당 요원 수 | 팀 A·B 각각 정확히 5명 | 5명 아니면 역할군 카운트 피처 부정확 |
| 요원 유효성 | 5명 모두 AGENT_ROLE_MAP에 존재 | 알 수 없는 요원 → 역할군 집계 불가 |
| 맵 유효성 | MAP_ORDER 13개에 존재 | map_encoded / atk_side_advantage 집계 불가 |
| 레이블 유효성 | winner가 team_a 또는 team_b | 레이블 없으면 지도학습 불가 |
| 핵심 스탯 결측 | ACS·KD 각 선수 모두 비결측 | 핵심 선수 스탯 피처 생성 불가 |
| 소스 비중 | 단일 소스 < 학습셋 전체의 20% | 소스 편향 방지 |
| 동점 | score_a ≠ score_b | 동점(overtime 등)은 레이블 불명확 |

```python
def quality_gate(row: dict) -> tuple[bool, str]:
    """
    반환: (검사 통과 여부, 탈락 사유)
    """
    agents_a = [p["agent"] for p in row["players_a"]]
    agents_b = [p["agent"] for p in row["players_b"]]

    if len(agents_a) != 5 or len(agents_b) != 5:
        return False, "team_size_not_5"
    if not all(a in AGENT_ROLE_MAP for a in agents_a + agents_b):
        return False, "unknown_agent"
    if row["map"] not in MAP_ORDER:
        return False, "unknown_map"
    if row["label"] not in (0, 1):
        return False, "invalid_label"
    if row["score_a"] == row["score_b"]:
        return False, "draw"
    # ACS·KD 결측 검사
    for players in (row["players_a"], row["players_b"]):
        for p in players:
            if p.get("acs") is None or p.get("kd") is None:
                return False, "missing_core_stat"
    return True, ""
```

`MAP_ORDER` 기준 맵 13개: Ascent, Bind, Haven, Split, Icebox, Breeze, Fracture, Pearl, Lotus, Sunset, Abyss, Drift, Corrode.

---

## 3. 신규 요원 처리

새 요원(`AGENT_ROLE_MAP`에 없는)이 포함된 행은 품질 검사에서 제외된다. `src/domain/agent_roles.py`의 `AGENT_ROLE_MAP`을 업데이트하면 자동으로 통과한다.

---

## 4. dedup_key 중복 제거 (Phase 4)

### 왜 중복이 발생하는가

qualidea와 vct_2021_2023이 같은 VCT 경기를 각자 수록하면 동일 경기가 두 번 학습되어 모델이 해당 경기 패턴에 과적합된다.

### 중복 제거 전략

```python
def dedup_rows(rows: list[dict]) -> list[dict]:
    """
    동일 dedup_key 중 소스 가중치가 가장 높은 행만 보존.
    가중치 동점 시 컬럼 수(스탯 완성도)가 더 많은 행 보존.
    """
    SOURCE_WEIGHT = {
        "ryanluong_challengers": 1.8,
        "vct_2021_2023": 1.0,
        "qualidea": 1.0,
        "ediashtarevin": 0.9,
    }

    best: dict[str, dict] = {}
    for row in rows:
        key = row["dedup_key"]
        if key not in best:
            best[key] = row
        else:
            existing = best[key]
            ew = SOURCE_WEIGHT.get(existing["source"], 1.0)
            rw = SOURCE_WEIGHT.get(row["source"], 1.0)
            if rw > ew:
                best[key] = row
            elif rw == ew:
                # 컬럼 수(스탯 완성도) 비교
                if _col_count(row) > _col_count(existing):
                    best[key] = row
    return list(best.values())
```

---

## 5. 팀명 정규화 (dedup 누락 방지)

같은 팀이 소스마다 `"T1"` / `"T1 Korea"` / `"Team One Korea"`로 다르게 표기되면 dedup_key가 달라져 동일 경기가 중복 제거되지 않는다.

파서 A~E 모두에서 팀명 확정 직후 `normalize_team()` 호출.

```python
from ml.agent_roles import normalize_team

team_a = normalize_team(raw_team_a)
team_b = normalize_team(raw_team_b)
dedup_key = make_dedup_key(date, event, map_, team_a, team_b, ...)
```

`TEAM_NAME_ALIASES` 딕셔너리는 파싱 실행 중 불일치 발견 시 지속 보완.

---

## 6. 클리닝 출력

| 파일 | 내용 |
|------|------|
| `data/processed/matches.csv` | 품질 검사·dedup 통과한 맵 행 전체 |
| `data/processed/rejects.csv` | 품질 검사에서 제외된 행 및 탈락 사유 |

---

## 7. 클리닝 품질 체크리스트

```
[ ] 팀당 요원 수 = 5 (양 팀 모두)
[ ] 모든 요원이 AGENT_ROLE_MAP에 존재
[ ] 모든 맵이 MAP_ORDER 13개 중 하나
[ ] score_a != score_b (동점 없음)
[ ] ACS·KD 결측 없음
[ ] dedup 후 동일 dedup_key 중복 0개
[ ] 단일 소스 비중 < 20%
```

---

## 8. 관련 문서

| 문서 | 내용 |
|------|------|
| [05_aggregation.md](05_aggregation.md) | 클리닝 후 선수 행 → 맵 행 집계 |
| [01_pipeline_overview.md](01_pipeline_overview.md) | 전처리 파이프라인 전체 흐름 개요 |
