# 06. 피처 엔지니어링

마지막 업데이트: 2026-05-26

## 1. 입력 계약

baseline은 기존 `ml/baseline/` 경로와 `models/baseline/`, `reports/baseline/` 산출물을 그대로 사용한다. 새 버전명은 만들지 않는다.

모델 입력은 UI 입력과 같은 구조다.

| 입력 | 설명 |
|---|---|
| 맵 | 경기 맵 1개 |
| 팀 A | 선수 5명 + 각 선수의 요원 5명 |
| 팀 B | 선수 5명 + 각 선수의 요원 5명 |

팀명은 입력 계약에 없다. `team_a`, `team_b`는 CSV 메타데이터로만 남고 모델 피처에는 들어가지 않는다.

활성 baseline의 학습 source는 Kaggle 계열로만 제한한다. `source`가 `kaggle_`로 시작하지 않는 행, 특히 `vlrgg_*` 행은 feature construction 전에 제외한다.

## 2. 누설 방지 원칙

현재 데이터에서는 날짜 순서를 신뢰하지 않고 **연도만 사용**한다. 2024년 경기의 선수 history 피처는 2021~2023년 기록만 사용하고, 2024년 기록 전체는 제외한다.

금지 입력:

- 현재 경기의 `score`, `round`, `winner`, `result`, `label`
- 현재 경기의 선수 스탯 `acs`, `kills`, `deaths`, `assists`, `hs`, `kd`, `kast`, `adr`, `fk`, `fd`, `clutch`
- 같은 연도의 선수 history
- 팀명 기반 이력 `h2h`, `prior_wr`, `map_wr`, `recent5_wr`
- 입력 순서 슬롯 피처 `a_p1_*`, `b_p1_*` 등

## 3. 피처 개요

현재 baseline 피처 수는 178개다.

| 카테고리 | 수 | 예시 |
|---|---:|---|
| 맵 원핫 | 13 | `map_ascent` |
| 역할군 count | 12 | `a_role_duelist_count`, `diff_role_controller_count` |
| 28명 요원 count/one-hot | 84 | `a_agent_jett_count`, `diff_agent_sova_count` |
| 이전 연도 선수 prior smoothed 평균 | 24 | `a_prior_kd_mean`, `diff_prior_games_mean` |
| 이전 연도 Synergy | 3 | `a_synergy_mean`, `diff_synergy_mean` |
| 맵×요원 smoothed 평균 | 21 | `a_map_agent_kd_mean`, `diff_map_agent_adr_mean` |
| 선수×요원 smoothed 평균 | 21 | `a_player_agent_kd_mean`, `diff_player_agent_fkpr_mean` |
| **합계** | **178** | |

`miks`는 현재 로컬 요원 registry에는 있지만 승인된 28명 one-hot baseline에는 포함하지 않는다. 별도 agent 컬럼을 추가하려면 피처 변경 승인이 필요하다.

## 4. 선수 피처

선수명 자체를 원핫 피처로 넣지 않는다. 선수명은 이전 연도 기록을 조회하는 key로만 사용하고, 모델에는 팀 단위 평균값만 들어간다.

선수별 prior base:

```
prior_games
prior_kd, prior_kast, prior_adr
prior_apr, prior_fkpr, prior_fdpr, prior_clutch
```

metric prior는 전체 선수 평균 쪽으로 5게임 기준 smoothing한다. `prior_games`는 실제 이전 경기 수 그대로이며, history가 없는 선수는 count 0, metric 0을 유지한다.

팀별 평균과 A-B 차이:

```
a_prior_kd_mean
b_prior_kd_mean
diff_prior_kd_mean
```

선수 5명의 입력 순서는 모델 의미가 아니므로 `mean`만 사용한다. `min`, `max`, `std`, `recent5`, `player-map`은 baseline에서 제외한다.

## 5. 맵×요원 피처

각 팀의 요원 5명이 **현재 맵**에서 이전 연도에 기록한 스탯(kd, kast, adr, apr, fkpr, fdpr, clutch)을 팀 평균으로 집계한다. smoothing은 선수 prior와 동일하게 5게임 기준 리그 평균으로 수축한다.

컬럼 구조:
```
a_map_agent_kd_mean    # A팀 요원들의 현재 맵 KD 평균 (이전 연도)
b_map_agent_kd_mean
diff_map_agent_kd_mean
... (kast, adr, apr, fkpr, fdpr, clutch 동일)
```

맵 정보가 없는 경기 또는 해당 맵 이력이 없는 요원의 경우 0.0.

## 6. 선수×요원 피처

각 팀의 선수 5명이 **현재 경기에서 플레이하는 요원**으로 이전 연도에 기록한 스탯을 팀 평균으로 집계한다. 선수-요원 조합 이력이 없으면 0.0.

컬럼 구조:
```
a_player_agent_kd_mean    # A팀 선수들의 담당 요원별 KD 평균 (이전 연도)
b_player_agent_kd_mean
diff_player_agent_kd_mean
... (kast, adr, apr, fkpr, fdpr, clutch 동일)
```

## 7. Synergy

`a_synergy_mean`, `b_synergy_mean`은 팀 5명 내부의 10개 선수 페어가 현재 경기 연도보다 이전 연도에 함께 출전한 횟수의 평균이다. `diff_synergy_mean`은 팀 A 값에서 팀 B 값을 뺀다.

## 8. 결측 처리

| 상황 | 처리 |
|---|---|
| history가 없는 선수 | count 0, metric 0 |
| 같은 연도 경기 | prior에서 제외 |
| 연도 없는 경기 | history-derived 피처 0 |
| 팀당 선수 5명이 안 되는 경기 | baseline 학습 행에서 제외 |
| 28명 one-hot 밖 요원 | agent count 0, role count는 가능한 경우 반영 |

## 9. 검증 결과

현재 산출물 기준 (재학습 예정):

| 항목 | 값 |
|---|---:|
| 피처 수 | 178 |
| 모델링 split | `train + val` |
| 최종 평가 split | `test` |
| source contract | `kaggle_*` only, `vlrgg_*` excluded |
| Modeling rows | 56,767 |
| Test rows | 10,017 |
| CV ROC-AUC | 0.6608 |
| Test ROC-AUC | 0.6562 |
| Test Accuracy | 0.6290 |
| Test F1 | 0.7243 |
| forbidden feature count | 0 |
| split overlap | 0 |
| final verdict | `PASS_TRUSTED_PREMATCH_BASELINE` |
| permutation top feature | `diff_prior_kd_mean` (Δauc=+0.0259) |

근거 파일:

- `reports/baseline/metrics.json`
- `reports/baseline/validation.json`
- `models/baseline/meta.json`

## 10. 데이터 소스별 성능 비교 계획

baseline 파이프라인은 현재 `kaggle_*` source만 사용한다. VLR.gg 스크래핑이 완료되면 두 조건의 성능을 비교한다.

| 실험 | source contract | 목적 |
|------|----------------|------|
| **Kaggle-only** (현재) | `kaggle_*` only | 기준선 확보 |
| **Kaggle + VLR.gg** (예정) | `kaggle_*` + `vlrgg_*` | 데이터 추가 효과 측정 |

비교 지표: CV ROC-AUC, Test ROC-AUC, Test Accuracy, Test F1

성능 수치는 각 실험 완료 후 `## 9. 검증 결과` 섹션에 추가한다.

---

## 11. Advanced Contract (125피처)

`feature_contract="advanced"`는 심화 모델(adv_kaggle_only 등)에서 사용한다. diff 컬럼을 모두 제거하고 `miks`를 29번째 요원으로 포함한다.

| 카테고리 | baseline (178) | advanced (125) | 변경 |
|---|---:|---:|---|
| 맵 원핫 | 13 | 13 | 동일 |
| 역할군 count | 12 (a/b/diff) | 8 (a/b만) | diff 4개 제거 |
| 요원 count | 84 (28명×3) | 58 (29명×2) | diff 제거, miks 추가 |
| 선수 prior | 24 (8base×3) | 16 (8base×2) | diff 8개 제거 |
| Synergy | 3 (a/b/diff) | 2 (a/b만) | diff 1개 제거 |
| 맵×요원 | 21 (7stat×3) | 14 (7stat×2) | diff 7개 제거 |
| 선수×요원 | 21 (7stat×3) | 14 (7stat×2) | diff 7개 제거 |

코드:

```python
from ml.baseline.preprocess import build_xy, FEATURE_COLS_ADVANCED

# advanced contract: 125피처, miks 포함, diff 없음
X, y, groups = build_xy(df, feature_contract="advanced")
```

전처리 출력 위치: `data/processed/adv_kaggle_only/`

세부 명세: [../05_data_learning/03_advanced_models/01_adv_kaggle_only.md](../05_data_learning/03_advanced_models/01_adv_kaggle_only.md)
