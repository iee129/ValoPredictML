# 01. 현재 피처 엔지니어링 (초기 설계 스펙 43개 — 실제 구현: baseline 178개 / advanced 125개)

마지막 업데이트: 2026-05-04

---

## 1. 피처 카테고리 개요

| 카테고리 | 피처 수 | 소스 |
|----------|---------|------|
| 역할군 카운트 | 12 | 요원 → AGENT_ROLE_MAP |
| 역할군 파생 | 4 | 역할군 카운트 → boolean |
| 선수 스탯 | 12 | overview.csv / player_stats.csv |
| 시너지 | 6 | 선수 스탯 집계 |
| 요원 조합 | 6 | 요원+맵 통계, 경기 이력 집계 |
| 맵 | 3 | MAP_TO_INDEX, 공수 기록 |
| **합계** | **43 + 1 레이블** | |

---

## 2. 역할군 카운트 피처 (12개)

| 피처명 | 타입 | 설명 | 범위 |
|--------|------|------|------|
| `a_duelist` | int | 팀 A Duelist 수 | 0~5 |
| `a_initiator` | int | 팀 A Initiator 수 | 0~5 |
| `a_controller` | int | 팀 A Controller 수 | 0~5 |
| `a_sentinel` | int | 팀 A Sentinel 수 | 0~5 |
| `b_duelist` | int | 팀 B Duelist 수 | 0~5 |
| `b_initiator` | int | 팀 B Initiator 수 | 0~5 |
| `b_controller` | int | 팀 B Controller 수 | 0~5 |
| `b_sentinel` | int | 팀 B Sentinel 수 | 0~5 |
| `diff_duelist` | int | a_duelist − b_duelist | −5~5 |
| `diff_initiator` | int | a_initiator − b_initiator | −5~5 |
| `diff_controller` | int | a_controller − b_controller | −5~5 |
| `diff_sentinel` | int | a_sentinel − b_sentinel | −5~5 |

---

## 3. 역할군 파생 피처 (4개)

| 피처명 | 타입 | 조건 |
|--------|------|------|
| `has_controller_a` | 0/1 | 팀 A Controller >= 1 |
| `has_controller_b` | 0/1 | 팀 B Controller >= 1 |
| `is_double_duelist_a` | 0/1 | 팀 A Duelist >= 2 |
| `is_double_duelist_b` | 0/1 | 팀 B Duelist >= 2 |

---

## 4. 선수 스탯 피처 (12개)

> ⚠️ **주의**: 이 피처들은 현행 매치 스탯(사후 정보)이므로 prematch 예측 파이프라인에서 사용 금지. 실제 baseline/advanced 파이프라인에서는 이 카테고리를 사용하지 않음.

팀 5명의 개인 스탯을 집계한 팀 단위 피처 (초기 설계 스펙 — 미채택).

| 피처명 | 집계 | 원본 컬럼 |
|--------|------|---------|
| `a_avg_acs` | mean(5명) | `acs` |
| `b_avg_acs` | mean(5명) | `acs` |
| `a_avg_kd` | mean(5명) | `kd` |
| `b_avg_kd` | mean(5명) | `kd` |
| `a_avg_kast` | mean(5명) | `kast` |
| `b_avg_kast` | mean(5명) | `kast` |
| `a_avg_adr` | mean(5명) | `adr` |
| `b_avg_adr` | mean(5명) | `adr` |
| `a_max_clutch` | max(5명) | `clutch_%` |
| `b_max_clutch` | max(5명) | `clutch_%` |
| `a_avg_hs` | mean(5명) | `hs` / `hs_percent` / `HS%` |
| `b_avg_hs` | mean(5명) | `hs` / `hs_percent` / `HS%` |

---

## 5. 시너지 피처 (6개)

> ⚠️ **주의**: 이 피처들도 현행 매치 스탯 기반으로, prematch 예측 파이프라인에서 사용 금지. 실제 파이프라인에서는 미채택.

| 피처명 | 계산식 | 소스 |
|--------|--------|------|
| `a_fk_fd_ratio` | sum(fk_a) / sum(fd_a) | overview.csv |
| `b_fk_fd_ratio` | sum(fk_b) / sum(fd_b) | overview.csv |
| `a_avg_assists` | mean(assists_a) | overview.csv |
| `b_avg_assists` | mean(assists_b) | overview.csv |
| `a_kast_std` | std(kast_a) | 전 소스 |
| `b_kast_std` | std(kast_b) | 전 소스 |

---

## 6. 요원 조합 피처 (6개)

사전 집계는 train.csv 기준 (val/test가 섞이지 않게).

| 피처명 | 계산식 | 설명 |
|--------|--------|------|
| `a_avg_agent_map_wr` | mean(각 요원의 해당 맵 승률) | 팀 A 5요원의 해당 맵 평균 승률 |
| `b_avg_agent_map_wr` | 동일 | 팀 B |
| `a_avg_agent_pick_rate` | mean(각 요원의 해당 맵 픽률) | 팀 A 메타 적합성 |
| `b_avg_agent_pick_rate` | 동일 | 팀 B |
| `a_avg_agent_exp` | mean(각 선수의 해당 요원 과거 플레이 횟수) | 팀 A 선수-요원 숙련도 |
| `b_avg_agent_exp` | 동일 | 팀 B |

신규 조합: winrate → 0.5(중립), experience → 0.

---

## 7. 맵 피처 (3개)

| 피처명 | 타입 | 계산식 |
|--------|------|--------|
| `map_encoded` | int | `MAP_TO_INDEX[map]` (0~12) |
| `atk_side_advantage` | float | global_atk_wins / global_total (train 기준 집계) |
| `is_attacker_a` | 0/1 | 사용자 입력 (선공/후공) |

`atk_side_advantage` 집계 소스: ryanluong challengers `maps_scores.csv`의 `Attacker Score`/`Defender Score`.

---

## 8. 레이블

| 피처명 | 타입 | 값 |
|--------|------|-----|
| `label` | int | 1 = 팀 A 승, 0 = 팀 B 승 |

---

## 9. 최종 피처 목록

```
역할군 카운트 (12):
  a_duelist, a_initiator, a_controller, a_sentinel
  b_duelist, b_initiator, b_controller, b_sentinel
  diff_duelist, diff_initiator, diff_controller, diff_sentinel

역할군 파생 (4):
  has_controller_a, has_controller_b
  is_double_duelist_a, is_double_duelist_b

선수 스탯 (12):
  a_avg_acs, b_avg_acs
  a_avg_kd,  b_avg_kd
  a_avg_kast, b_avg_kast
  a_avg_adr,  b_avg_adr
  a_max_clutch, b_max_clutch
  a_avg_hs,  b_avg_hs

시너지 (6):
  a_fk_fd_ratio, b_fk_fd_ratio
  a_avg_assists, b_avg_assists
  a_kast_std, b_kast_std

요원 조합 (6):
  a_avg_agent_map_wr, b_avg_agent_map_wr
  a_avg_agent_pick_rate, b_avg_agent_pick_rate
  a_avg_agent_exp, b_avg_agent_exp

맵 (3):
  map_encoded, atk_side_advantage, is_attacker_a

레이블 (1): label
```

**총 43개 피처 + 1개 레이블 (초기 설계 스펙 — 실제 구현: baseline 178피처 / advanced 125피처)**

> 참고: 실제 파이프라인 피처 수는 `reports/baseline/metrics.json`(178) 및 `reports/adv_kaggle_only/metrics.json`(125) 참조.

Team_Shared_Exp(시너지, 동반 출전 횟수)는 visualize25 데이터셋 보류로 미구현 — 추가 시 44개.
