# 06. 피처 엔지니어링

마지막 업데이트: 2026-05-26

## 1. 입력 계약

baseline은 기존 `src/ml/baseline/` 경로와 `models/baseline/`, `reports/baseline/` 산출물을 그대로 사용한다. 새 버전명은 만들지 않는다.

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

PRIOR 통계는 시간순(LEAK-SAFE) prior로 구성하며 선수별 **최근 20경기 평균**으로 폼을 반영한다.

## 3. 피처 개요

baseline 피처 수는 총 **421개**다. 슬롯(선수 슬롯) 단위 피처 400개와 매치 컨텍스트 피처 21개로 구성된다.

| 카테고리 | 수 | 구성 |
|---|---:|---|
| **슬롯 선수 피처** | **400** | 10슬롯 × (PRIOR 통계 8 + 요원 ONE-HOT 27 + 역할군 ONE-HOT 5) |
| 매치 컨텍스트 — 맵 ONE-HOT | 12 | `map_ascent` 등 |
| 매치 컨텍스트 — 팀 합동출전 | 3 | 팀 내 동반 출전 이력 |
| 매치 컨텍스트 — 역할 조합 PRIOR | 6 | 역할군 조합 prior |
| **합계** | **421** | |

슬롯 피처는 양 팀 10명을 각 선수 슬롯으로 펼쳐 슬롯마다 PRIOR 통계 8개, 요원 ONE-HOT 27개, 역할군 ONE-HOT 5개를 부여한 구조다(10 × 40 = 400).

## 4. 슬롯 선수 피처 (400)

선수명 자체는 원핫 피처로 넣지 않는다. 선수명은 이전 연도 기록을 조회하는 key로만 사용한다. 양 팀 10명을 각 선수 슬롯으로 펼쳐 슬롯마다 다음 40개 피처를 부여한다(10 × 40 = 400).

슬롯당 PRIOR 통계 8개:

```
prior_games
prior_kd, prior_kast, prior_adr
prior_apr, prior_fkpr, prior_fdpr, prior_clutch
```

PRIOR 통계는 선수별 **최근 20경기 평균**으로 폼을 반영하며, 시간순(LEAK-SAFE) prior로 같은 연도·같은 경기 스탯은 제외한다.

슬롯당 ONE-HOT:

```
요원 ONE-HOT 27개   # 해당 슬롯 선수가 사용하는 요원
역할군 ONE-HOT 5개  # 해당 슬롯 선수의 역할군 (duelist/controller/initiator/sentinel/flex 등)
```

## 5. 매치 컨텍스트 피처 (21)

매치 컨텍스트는 슬롯 외 매치 단위 피처 21개로 구성된다.

| 피처 | 수 | 설명 |
|---|---:|---|
| 맵 ONE-HOT | 12 | 경기 맵 식별 |
| 팀 합동출전 | 3 | 팀 내부 선수들이 이전 연도에 함께 출전한 이력 기반 합동출전 지표 |
| 역할 조합 PRIOR | 6 | 팀의 역할군 조합 prior |

## 6. 결측 처리 (baseline)

| 상황 | 처리 |
|---|---|
| history가 없는 신인 선수 | 전체 선수 PRIOR 통계의 **중앙값(median)**으로 대체 |
| 특정 stat이 누락된 경우 | 해당 stat의 **누락 제외 평균**으로 대체 |
| 클러치(clutch) 통계 누락 | 0으로 대체 |
| 같은 연도 경기 | prior에서 제외 (LEAK-SAFE) |
| 팀당 선수 5명이 안 되는 경기 | baseline 학습 행에서 제외 |

선수 표기는 대소문자 정규화 후 매칭한다. (advanced 계약의 결측 처리는 주요 요원 + other bucket / smoothed prior를 적용하며 9절을 참조한다.)

## 7. 검증 결과 (중간발표 기준)

| 항목 | 값 |
|---|---:|
| 피처 수 | 421 |
| 모델 | LR + DT soft voting (0.50 / 0.50) |
| 분할 | 랜덤 Train 80% / Test 20% |
| 레이블 총계 | 21,258 (A승 42.0% / B승 58.0%) |
| Test ROC-AUC | 0.5943 |
| Test Accuracy | 0.5667 |
| Test F1 | 0.6072 |
| forbidden feature count | 0 |
| split overlap | 0 |

근거 파일:

- `reports/baseline/metrics.json`
- `reports/baseline/validation.json`
- `models/baseline/meta.json`

## 8. 데이터 소스별 성능 비교 계획

baseline 파이프라인은 현재 `kaggle_*` source만 사용한다. VLR.gg 스크래핑이 완료되면 두 조건의 성능을 비교한다.

| 실험 | source contract | 목적 |
|------|----------------|------|
| **Kaggle-only** (현재) | `kaggle_*` only | 기준선 확보 |
| **Kaggle + VLR.gg** (예정) | `kaggle_*` + `vlrgg_*` | 데이터 추가 효과 측정 |

비교 지표: Test ROC-AUC, Test Accuracy, Test F1

성능 수치는 각 실험 완료 후 `## 7. 검증 결과` 섹션에 추가한다.

---

## 9. Advanced Contract (179피처)

`feature_contract="advanced"`는 시간순 active 심화 모델에서 사용한다.
현재 계약은 179개이며, 정본은 `ml.baseline.preprocess.FEATURE_COLS_ADVANCED`와 `models/advanced/meta.json`의 `feature_names`다.

주요 카테고리는 맵 원핫, 역할군·요원 count, 선수 prior, synergy, 맵×요원, 선수×요원, 팀 form, composition meta, cold-start flag다.

코드:

```python
from ml.baseline.preprocess import build_xy, FEATURE_COLS_ADVANCED

# advanced contract: 179피처
X, y, groups = build_xy(df, feature_contract="advanced", processed_dir="data/processed")
```

전처리 출력 위치: `data/processed/advanced/`

세부 명세: [../05_data_learning/03_advanced_models/01_advanced_chrono.md](../05_data_learning/03_advanced_models/01_advanced_chrono.md)
