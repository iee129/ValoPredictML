# 06. 피처 엔지니어링

마지막 업데이트: 2026-05-05

> **구현 완료** — `ml/data_pipeline.py`의 `build_features_phase1()` + `_add_phase2_features()`로 구현.

## 1. 피처 설계 철학

- **도메인 지식 기반**: 역할군 메타(Controller 필수 등)를 반영
- **역할군으로 묶음**: 요원 27종 원핫인코딩 대신 역할군 카운트 사용 — 데이터 희소성 해결, 신규 요원 추가 시 재학습 불필요, 메타 변화에 강인
- **대칭성**: 팀 A/B 각각 동일한 피처 구조로 비교 가능하게 설계
- **피처 사전 집계**: train.csv만 사용 (val/test 누수 방지)

---

## 2. 피처 카테고리 개요

피처는 두 단계로 생성된다. Phase 1(`build_features_phase1`)은 파싱 직후 역할군·맵 피처를 생성하고, Phase 2(`_add_phase2_features`)는 train 기준 집계값을 join해 선수 스탯·시너지·요원 조합 피처를 추가한다.

**FEATURE_COLS_P1 (19개)**:

| 카테고리 | 피처 수 | 컬럼 |
|----------|---------|------|
| 역할군 카운트 (a/b 각 4) | 8 | `a_duelist`, `a_initiator`, `a_controller`, `a_sentinel`, `b_duelist`, `b_initiator`, `b_controller`, `b_sentinel` |
| 역할군 차이 (diff) | 4 | `diff_duelist`, `diff_initiator`, `diff_controller`, `diff_sentinel` |
| 역할군 파생 | 4 | `has_controller_a`, `has_controller_b`, `is_double_duelist_a`, `is_double_duelist_b` |
| 맵 | 3 | `map_encoded`, `atk_side_advantage`, `is_attacker_a` |

**FEATURE_COLS_P2 (24개)**:

| 카테고리 | 피처 수 | 컬럼 |
|----------|---------|------|
| 선수 스탯 | 10 | `a_avg_acs`, `b_avg_acs`, `a_avg_kd`, `b_avg_kd`, `a_avg_kast`, `b_avg_kast`, `a_avg_adr`, `b_avg_adr`, `a_avg_hs`, `b_avg_hs` |
| 클러치 | 2 | `a_max_clutch`, `b_max_clutch` |
| 시너지 | 6 | `a_fk_fd_ratio`, `b_fk_fd_ratio`, `a_avg_assists`, `b_avg_assists`, `a_kast_std`, `b_kast_std` |
| 요원 조합 | 6 | `a_avg_agent_map_wr`, `b_avg_agent_map_wr`, `a_avg_agent_pick_rate`, `b_avg_agent_pick_rate`, `a_avg_agent_exp`, `b_avg_agent_exp` |

**합계: FEATURE_COLS_P1(19) + FEATURE_COLS_P2(24) = 43개 피처 + 1 레이블**

---

## 3. 역할군 카운트 피처 (12개)

요원 27종을 그대로 쓰지 않고 역할군으로 묶는 이유: 모델이 "Jett가 있으면 이긴다"처럼 특정 요원에 과도하게 의존하는 패턴을 학습하지 않도록. 역할군으로 묶으면 "Duelist 2명"이라는 구조적 의미만 남아 메타 변화에도 안정적.

차이(diff) 피처도 함께 쓰는 이유: 팀 A Controller 1명 / 팀 B Controller 0명이면 팀 A가 유리. 절대적인 수보다 두 팀의 상대적 차이가 승패에 영향.

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
| `diff_duelist` | int | a_duelist - b_duelist | -5~5 |
| `diff_initiator` | int | a_initiator - b_initiator | -5~5 |
| `diff_controller` | int | a_controller - b_controller | -5~5 |
| `diff_sentinel` | int | a_sentinel - b_sentinel | -5~5 |

```python
from ml.agent_roles import AGENT_ROLE_MAP

def count_roles(agents: list[str]) -> dict:
    counts = {"Duelist": 0, "Initiator": 0, "Controller": 0, "Sentinel": 0}
    for agent in agents:
        role = AGENT_ROLE_MAP.get(agent)
        if role:
            counts[role] += 1
    return counts
```

---

## 4. 역할군 파생 피처 (4개)

Controller가 0명이면 스모크 없이 사이트 진입 — 수비팀이 모든 각도에서 쏠 수 있어 진입이 거의 불가능. "있음/없음" 자체가 카운트 피처와 별개로 결정적 차이.

Duelist 2명 이상 조합은 교전력 극대화 vs 유틸 부족이라는 특정 패턴. 2명과 3명의 차이보다 2명 이상인지 아닌지의 전략적 의미가 더 뚜렷.

| 피처명 | 타입 | 조건 |
|--------|------|------|
| `has_controller_a` | 0/1 | 팀 A Controller >= 1 |
| `has_controller_b` | 0/1 | 팀 B Controller >= 1 |
| `is_double_duelist_a` | 0/1 | 팀 A Duelist >= 2 |
| `is_double_duelist_b` | 0/1 | 팀 B Duelist >= 2 |

---

## 5. 선수 스탯 피처 (12개)

팀 5명의 개인 스탯을 집계한 팀 단위 피처.

- **ACS**: 킬의 질·피해량·클러치까지 반영한 종합 전투 기여도.
- **K/D**: 교환 효율. 1보다 크면 죽는 것보다 많이 잡아 수적 우위를 자주 만든다.
- **KAST%**: 킬 못 해도 어시스트·생존·트레이드로 팀에 기여한 라운드 비율. K/D가 보지 못하는 팀 기여를 보완.
- **ADR**: 킬 못 한 라운드에서도 피해를 줘 다음 플레이어의 킬 기회를 만드는 지표.
- **클러치율 max**: 1대多 상황에서 라운드를 이긴 비율. 팀 평균이 아닌 최고값 — "가장 믿을 수 있는 1명이 있느냐"가 중요.
- **HS% (헤드샷률)**: TTK를 대폭 줄여 교환 효율 향상. 소스별 컬럼명이 `hs%` / `hs_percent` / `HS%`로 달라 파서 내 정규화 필수.

| 피처명 | 집계 | 원본 컬럼 |
|--------|------|----------|
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

## 6. 시너지 피처 (6개)

개인 스탯이 높아도 팀으로서 맞물리지 않으면 지는 경기가 많다. 시너지 피처는 "팀이 함께 얼마나 잘 작동하는가"를 수치화한다.

- **fk_fd_ratio**: 먼저 잡은 팀이 5v4 수적 우위를 만든다. 이 비율이 높으면 진입 전략과 스킬 연계가 잘 작동하는 신호.
- **avg_assists**: 어시스트가 많을수록 선수들이 스킬을 팀에 맞춰 사용 — 역할군 조합이 실제로 맞물리는지의 지표.
- **KAST 표준편차**: 평균 KAST가 같아도 팀원 한 명의 KAST가 현저히 낮으면 상대가 집중 공략. 표준편차가 낮을수록 균형 잡힌 팀. "약한 고리" 유무를 포착.
- **Team_Shared_Exp**: `visualize25` 데이터셋 보류로 현재 미구현 — 이후 재검토.

| 피처명 | 계산식 | 소스 |
|--------|--------|------|
| `a_fk_fd_ratio` | sum(fk_a) / sum(fd_a) | overview.csv |
| `b_fk_fd_ratio` | sum(fk_b) / sum(fd_b) | overview.csv |
| `a_avg_assists` | mean(assists_a) | overview.csv |
| `b_avg_assists` | mean(assists_b) | overview.csv |
| `a_kast_std` | std(kast_a) | 전 소스 |
| `b_kast_std` | std(kast_b) | 전 소스 |

---

## 7. 요원 조합 피처 (6개)

역할군 카운트만으로는 "Jett가 Ascent에서 특히 강하다"는 맵별 특성을 반영하지 못한다. 요원x맵 승률을 쓰면 "이 맵에서 이 요원들이 역사적으로 얼마나 이겼는가"라는 실적 기반 정보를 피처에 담을 수 있다.

픽률이 높을수록 프로들이 해당 맵에서 검증한 요원 — 메타 적합성 신호. 아무리 강한 요원도 처음 쓰는 선수가 들면 기대 성능이 안 나온다.

**피처 사전 집계**: train.csv만 사용. val/test 기준 집계는 데이터 누수.

```python
# train.csv 기준 집계
agent_map_stats[agent][map] = {
    "wins":     count(label == 1),
    "total":    count(*),
    "winrate":  wins / total,
    "pickrate": total / total_matches_on_map,
}
# (player, agent) 등장 횟수
agent_experience[player][agent] = count(*)
```

신규 조합 처리: winrate=0.5(중립), experience=0.

| 피처명 | 계산식 | 설명 |
|--------|--------|------|
| `a_avg_agent_map_wr` | mean(각 요원의 해당 맵 승률) | 팀 A 5요원의 해당 맵 평균 승률 |
| `b_avg_agent_map_wr` | 동일 | 팀 B |
| `a_avg_agent_pick_rate` | mean(각 요원의 해당 맵 픽률) | 팀 A 메타 적합성 |
| `b_avg_agent_pick_rate` | 동일 | 팀 B |
| `a_avg_agent_exp` | mean(각 선수의 해당 요원 과거 플레이 횟수) | 팀 A 선수-요원 숙련도 |
| `b_avg_agent_exp` | 동일 | 팀 B |

---

## 8. 맵 피처 (3개)

맵이 달라지면 강한 요원도, 유리한 공수 사이드도 완전히 바뀐다. 맵 정보 없이 학습하면 모든 맵을 동일한 조건으로 처리.

- **map_encoded**: 문자열을 숫자 인덱스로 변환해야 트리 모델이 분기 조건으로 사용 가능. `MAP_TO_INDEX[map]` (0~11).
- **atk_side_advantage**: 맵마다 공격·수비 중 어느 쪽이 구조적으로 유리한지를 전체 데이터 집계로 수치화. 집계 소스: ryanluong challengers `maps_scores.csv`의 `Attacker Score`/`Defender Score`. train 기준 집계.
- **is_attacker_a**: `atk_side_advantage`가 맵 수준 정보라면 이건 경기 수준 정보. 두 피처를 함께 쓰면 "공격이 유리한 맵에서 팀 A가 공격으로 시작했을 때"라는 조합 패턴을 모델이 학습 가능.

| 피처명 | 타입 | 계산식 |
|--------|------|--------|
| `map_encoded` | int | `MAP_TO_INDEX[map]` (0~11) |
| `atk_side_advantage` | float | global_atk_wins / global_total (train 기준 집계) |
| `is_attacker_a` | 0/1 | 사용자 입력 (선공/후공) |

---

## 9. 레이블

| 피처명 | 타입 | 값 |
|--------|------|-----|
| `label` | int | 1 = 팀 A 승, 0 = 팀 B 승 |

---

## 10. 최종 피처 목록 (43개 + 1 레이블)

```
# FEATURE_COLS_P1 (19개) — build_features_phase1() 생성
역할군 카운트 (8):
  a_duelist, a_initiator, a_controller, a_sentinel
  b_duelist, b_initiator, b_controller, b_sentinel

역할군 diff (4):
  diff_duelist, diff_initiator, diff_controller, diff_sentinel

역할군 파생 (4):
  has_controller_a, has_controller_b
  is_double_duelist_a, is_double_duelist_b

맵 (3):
  map_encoded, atk_side_advantage, is_attacker_a

# FEATURE_COLS_P2 (24개) — _add_phase2_features() 생성 (train 집계 기반)
선수 스탯 (10):
  a_avg_acs, b_avg_acs
  a_avg_kd,  b_avg_kd
  a_avg_kast, b_avg_kast
  a_avg_adr,  b_avg_adr
  a_avg_hs,  b_avg_hs

클러치 (2):
  a_max_clutch, b_max_clutch

시너지 (6):
  a_fk_fd_ratio, b_fk_fd_ratio
  a_avg_assists, b_avg_assists
  a_kast_std, b_kast_std

요원 조합 (6):
  a_avg_agent_map_wr, b_avg_agent_map_wr
  a_avg_agent_pick_rate, b_avg_agent_pick_rate
  a_avg_agent_exp, b_avg_agent_exp

레이블 (1): label
```

---

## 11. 피처 사전 집계 순서 (누수 방지)

```
Step 1. 파싱 → 정규화 → 품질 게이트 → dedup → matches_clean.csv
Step 2. matches_clean.csv에서 train/val/test 분할
Step 3. train.csv만 사용해서:
          - atk_side_advantage (맵별 공격 측 전역 승률)
          - agent_map_stats    (요원x맵 승률·픽률)
          - agent_experience   (선수x요원 등장 횟수)
Step 4. train/val/test 각각에 집계값 join
          신규 조합: winrate=0.5(중립), experience=0
Step 5. A/B swap으로 train 행 수 2x 증강
Step 6. sample_weight = time_weight x source_weight 계산
Step 7. features_base.csv 저장
```

---

## 12. 결측치 처리

| 피처 | 처리 | 이유 |
|------|------|------|
| `kast` 결측 | 팀 평균 imputation 또는 -1 플래그 | -1 플래그는 결측 여부 자체를 모델이 학습 가능하게 함 |
| `clutch_%` 결측 | 0으로 대체 | 클러치 기록 없음 = 실제 기여 없음. 팀 평균 대체 시 과대평가 |
| `agent_map_wr` 집계 불가 | 0.5(중립) 대체 | 0이면 "무조건 진다", 1이면 반대. 0.5 = "데이터 없음 = 유불리 불명" |
| `fk_fd_ratio` FD=0 | 1.0 대체 | FD=0 팀은 한 번도 먼저 죽지 않음 — 극단값 대신 균형값(1.0) |
| `agent_experience` 신규 | 0으로 대체 | 경험 없음 = 0회 플레이와 동일 |

---

## 13. sample_weight 계산

```python
def get_time_weight(date_str: str) -> float:
    year = int(date_str[:4])
    if year <= 2022:  return 0.6   # 구식 메타
    elif year == 2023: return 0.8  # 전환기
    else:              return 1.2  # 현재 메타 (2024~)

SOURCE_WEIGHT = {
    "ryanluong_challengers": 1.8,
    # 제거됨: "piyush_2024": 1.5,
    # 제거됨: "piyush_2025": 1.5,
    "vct_2021_2023": 1.0,
    "qualidea": 1.0,
    "ediashtarevin": 0.9,
}

sample_weight = get_time_weight(row["date"]) * SOURCE_WEIGHT[row["source"]]
# model.fit(..., sample_weight=weights) 에 적용
```

---

## 14. 피처 중요도 검증 계획

1. **RF feature_importances_** — 훈련 직후 무료. 빠른 전체 윤곽.
2. **XGBoost gain/cover** — RF와 비교해 일관성 확인.
3. **Permutation importance** — 피처를 섞었을 때 성능 하락량. 실제 예측 기여 직접 측정.
4. **Ablation study** — 카테고리 단위(역할군만 / 스탯만 / 시너지만) 제거 실험.

---

## 15. 관련 문서

| 문서 | 내용 |
|------|------|
| [07_split_and_validation.md](07_split_and_validation.md) | 피처 완성 후 데이터 분할 |
| [../preprocessing.md](../preprocessing.md) | 전처리 전략 원문 (섹션 7~9) |
