# 05. 경기 단위 집계

마지막 업데이트: 2026-05-04

## 1. 집계 필요성

원본 데이터는 **선수 단위** (1행 = 선수 1명 × 맵 1개)다. 품질 게이트·dedup 이후 `matches_clean.csv`도 선수 행 단위. 피처 엔지니어링을 위해 팀별 5명 스탯을 집계한 **맵 행 단위** (1행 = 맵 1개, 양 팀 포함)로 변환한다.

```
선수 행 단위 (matches_clean.csv 일부):
match_key | map    | team  | player | agent   | acs | kd  | ...
----------|--------|-------|--------|---------|-----|-----|
abc123    | Ascent | T1    | TenZ   | Jett    | 280 | 1.8 | ...
abc123    | Ascent | T1    | Guma   | Raze    | 240 | 1.5 | ...
...
abc123    | Ascent | FNC   | Derke  | Neon    | 200 | 1.2 | ...
...
          ↓ 집계
맵 행 단위:
match_key | map    | team_a | team_b | players_a            | players_b | label
----------|--------|--------|--------|----------------------|-----------|------
abc123    | Ascent | T1     | FNC    | [{TenZ,Jett,...}, ...] | [...]   | 1
```

---

## 2. 집계 구현

```python
def aggregate_to_map_level(rows: list[dict]) -> list[dict]:
    """
    공통 스키마 행 리스트 → 맵 단위 행 리스트.
    각 행은 이미 파서에서 players_a / players_b 리스트를 포함하므로
    별도 groupby 없이 직접 사용.
    """
    result = []
    for row in rows:
        if len(row["players_a"]) != 5 or len(row["players_b"]) != 5:
            continue  # 품질 게이트 통과 후에도 방어 체크
        result.append(row)
    return result
```

ryanluong 파서는 `overview.csv`와 `maps_scores.csv` 조인 시 이미 팀 단위로 집계. qualidea / piyush / ediashtarevin는 선수 행을 파서 내부에서 5명씩 그룹핑.

---

## 3. 선수 스탯 집계 (팀 단위)

맵 행에는 5명 스탯이 배열로 저장된다. 피처 생성 단계에서 팀 단위 집계값을 계산한다.

| 집계 방식 | 적용 피처 |
|-----------|-----------|
| `mean(5명)` | acs, kd, kast, adr, hs |
| `max(5명)` | clutch_% |
| `sum(5명) / sum(5명)` | fk_fd_ratio |
| `mean(5명)` | assists |
| `std(5명)` | kast_std |

---

## 4. A/B swap 증강 (train 한정)

파이프라인에서 분할 후 train에만 적용. 집계 단계에서는 적용하지 않는다.

```
원본: team_a=T1, team_b=FNC, label=1
swap: team_a=FNC, team_b=T1, label=0  ← train에만 추가
```

`--no-augment-train` 플래그로 비활성화 가능.
val/test에는 미적용 — 평가는 실제 경기 그대로의 행만 사용.

---

## 5. 예외 케이스 처리

| 예외 | 처리 |
|------|------|
| 팀이 3개 이상 | 해당 맵 행 제외 (품질 게이트에서 선차단) |
| 동점 경기 | 해당 맵 행 제외 (품질 게이트에서 선차단) |
| 요원이 5명 미만인 팀 | 해당 맵 행 제외 |
| 같은 경기의 같은 요원 2명 이상 | 경고 로그 후 제외 |

---

## 6. 출력

| 파일 | 내용 |
|------|------|
| `data/processed/matches_clean.csv` | 집계 완료된 맵 행 전체 (~80~100K 예상) |

---

## 7. 관련 문서

| 문서 | 내용 |
|------|------|
| [06_feature_engineering.md](06_feature_engineering.md) | 집계 후 43개 피처 생성 |
| [07_split_and_validation.md](07_split_and_validation.md) | 분할 및 A/B swap 증강 |
