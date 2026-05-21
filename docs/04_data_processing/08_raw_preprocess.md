# 08. Raw-Only 전처리 산출물

마지막 업데이트: 2026-05-21

> **구현 완료** — `ml/raw_preprocess.py`로 생성.
> 실행 결과: raw 파일 1,608개 inventory → 후보 match-map 68,191행 → accepted 66,931행 → strict-before static 27,268행.

이 문서는 `data/processed/preprocess/`가 어떤 기준으로 생성되었는지 설명한다. 이 경로는 기존 `data/processed/` 파이프라인을 덮어쓴 것이 아니라, 오직 `data/raw/**`만 입력으로 읽어 처음부터 재정제한 별도 산출물 루트다.

현재 Streamlit 앱과 active champion 모델은 이 산출물로 교체되지 않았다. 즉, 이 문서의 대상은 “새 raw-only 전처리 결과”이고, “현재 서비스 예측 모델의 활성 입력 계약”은 아니다.

---

## 1. 실행 명령

```bash
.venv/bin/python -m ml.raw_preprocess \
  --input data/raw \
  --output data/processed/preprocess \
  --reports reports/preprocess
```

검증용 smoke 실행은 다음처럼 별도 출력 루트에 제한해서 돌릴 수 있다.

```bash
.venv/bin/python -m ml.raw_preprocess \
  --input data/raw \
  --output /private/tmp/valopredicml_raw_preprocess_smoke/data \
  --reports /private/tmp/valopredicml_raw_preprocess_smoke/reports \
  --smoke-limit 50 \
  --skip-model-check
```

입력 루트는 반드시 `data/raw` 하위여야 한다. `data/processed`, `reports`, `models`는 전처리 입력으로 거부한다.

---

## 2. 생성 파일

`data/processed/preprocess/` 아래에 다음 파일이 생성된다.

| 파일 | 행 수 | 내용 |
|------|------:|------|
| `files.csv` | 1,608 | raw 파일 inventory, 파일 크기, sha256, 확장자, detected source, source decision |
| `schemas.csv` | 1,234 | CSV 컬럼, JSON key, row count, encoding 상태 |
| `sources.csv` | 26 | source별 accepted/report_only/excluded 판정과 후보/통과/리젝트 수 |
| `matches.csv` | 66,931 | accepted match-map 단위 행 |
| `players.csv` | 669,310 | player-map long 행. match-map 1행당 10명 |
| `teams.csv` | 133,862 | team-map long 행. match-map 1행당 2팀 |
| `rejects.csv` | 1,260 | reject reason과 provenance |
| `features_lineup.csv` | 66,931 | map/agent/role only 피처 테이블 |
| `features_static.csv` | 27,268 | ISO date 확정 row만 strict-before history를 붙인 피처 테이블 |
| `train.csv` | 18,965 | 최종 학습 split. 이번 full run에서는 `features_static.csv` 기반 |
| `val.csv` | 4,129 | 최종 검증 split |
| `test.csv` | 4,174 | 최종 테스트 split |

리포트는 `reports/preprocess/` 아래에 생성된다.

| 파일 | 내용 |
|------|------|
| `summary.json` | 전체 실행 요약 |
| `data_checks.json` | split overlap, 금지 피처, provenance, source/reject count 검증값 |
| `comparison.csv` | `features_lineup`과 `features_static`의 LR/LGB smoke 비교 |
| `decision.md` | 모델 비교 요약과 산출물 사용 판단 메모 |

---

## 3. Source 판정 기준

source decision은 raw 파일 단위 inventory에서 먼저 기록된다.

| decision | 기준 |
|----------|------|
| `accepted` | match-map score, 두 팀, 맵, 10 player-agent slots, winner/label을 복원할 수 있는 원천 |
| `report_only` | event listing, team/player profile, aggregate stats처럼 단독 학습 row를 만들 수 없는 원천 |
| `excluded` | image/log/doc, economy-only, round/kill log, leakage audit 전 post-match-only source |

실행 결과 accepted row의 source 분포는 다음과 같다.

| source | accepted rows |
|--------|--------------:|
| `kaggle_qualidea` | 24,891 |
| `kaggle_vct` | 23,831 |
| `kaggle_challengers` | 15,081 |
| `kaggle_piyush2025` | 2,291 |
| `kaggle_ediashtarevin` | 618 |
| `vlrgg_raw_detail` | 133 |
| `kaggle_piyush2024` | 86 |

`vlrgg_event_detail`, `vlrgg_event_listing`, `vlrgg_player_profile`, `vlrgg_aggregate_stats`는 inventory에는 남기지만 단독 학습 row로 승격하지 않는다.

---

## 4. 처리 단계

### 4.1 Raw 파일 inventory

`data/raw/**` 전체를 순회하면서 다음을 기록한다.

- 상대 경로
- 파일 크기
- SHA-256
- 확장자
- detected source
- accepted/report_only/excluded 판정
- CSV 컬럼 또는 JSON key
- CSV row count와 encoding 상태

이 단계의 산출물이 `files.csv`, `schemas.csv`, `sources.csv`다.

### 4.2 Parser family별 후보 생성

학습 row를 만들 수 있는 source만 parser 후보가 된다.

| Parser family | 입력 raw 형태 | 설명 |
|---------------|---------------|------|
| `kaggle_vct` | `vct_2021_2023/**/matches/overview.csv` + `maps_scores.csv` | player-row와 score-row를 묶어 match-map 후보 생성 |
| `kaggle_challengers` | `ryanluong1__valorant-challengers-league-data/**/matches/overview.csv` + `maps_scores.csv` | VCT parser와 같은 구조 |
| `kaggle_qualidea` | `data-since-april-2021.csv` | 단일 CSV 안에서 match datetime, map, team, player-team 단위 grouping |
| `kaggle_ediashtarevin` | `player_stats.csv` | winner/loser 5명씩 묶어 후보 생성 |
| `kaggle_piyush2024/2025` | `*_csvs/detailed_matches_player_stats.csv` + `detailed_matches_maps.csv` | player stat과 map score를 match_id/map_name 기준으로 결합 |
| `vlrgg_raw_detail` | `_v2_match_details_match_id_*.json` | VLR.gg raw JSON의 `data.segments[0]` match detail payload 파싱 |

이번 full run에서 후보 match-map은 68,191행이었다.

### 4.3 Match row acceptance gate

후보 row는 아래 조건을 모두 통과해야 `matches.csv`에 남는다.

| 조건 | 실패 reject reason |
|------|--------------------|
| one row = one completed match-map | parser 후보 생성 단계에서 보장 |
| `map`이 known map | `unknown_map` |
| `team_a`, `team_b`가 비어 있지 않고 서로 다름 | `missing_team`, `same_team` |
| `score_a`, `score_b`가 정수 | `score_missing` |
| draw가 아님 | `draw_map` |
| `label`이 score/winner와 일치 | `label_mismatch` |
| 각 팀이 정확히 5명 | `player_count_not_5v5` |
| 각 팀의 agent가 known agent | `unknown_or_blank_agent` |
| 팀 내부 agent 중복 없음 | `duplicate_agent_in_team` |

이번 full run의 reject reason은 다음과 같다.

| reason | rows |
|--------|-----:|
| `dedup_lower_priority` | 1,256 |
| `player_count_not_5v5` | 4 |

### 4.4 Date handling

date는 세 등급으로 기록한다.

| `date_quality` | 의미 | 후속 처리 |
|----------------|------|----------|
| `iso` | `YYYY-MM-DD`로 확정 가능 | `features_static.csv` 대상 |
| `partial` | 연도만 있거나 월/일만 추정 가능한 문자열 | `matches.csv`, `features_lineup.csv`에는 보존. static에서는 제외 |
| `missing` | usable date 없음 | `matches.csv`, `features_lineup.csv`에는 보존. static에서는 제외 |

수동 fuzzy 추정은 하지 않는다. 예를 들어 VLR.gg raw date가 `Friday, May 8 11:00 PM EDT`처럼 연도 없는 문자열이면 `partial`로 남긴다.

이번 full run의 date 품질은 다음과 같다.

| date_quality | rows |
|--------------|-----:|
| `iso` | 27,268 |
| `missing` | 39,530 |
| `partial` | 133 |

### 4.5 Dedup

중복 제거는 다음 값의 canonical 조합으로 만든 `dedup_key`를 사용한다.

```text
date/event/map/team_pair/agent_pair/score_pair
```

팀 A/B 순서가 뒤집혀도 같은 경기로 인식되도록 team pair를 canonical sort한다. 같은 `dedup_key`가 여러 source에서 나오면 다음 우선순위로 1행만 남긴다.

1. source priority
2. completeness score
3. match_key 안정 정렬

밀린 row는 `rejects.csv`에 `dedup_lower_priority`로 남긴다.

---

## 5. Output table 구조

### 5.1 `matches.csv`

`matches.csv`는 학습 기본 단위다. 한 행은 completed match-map 하나다.

주요 컬럼:

```text
match_key, dedup_key, source, source_priority,
date, date_raw, date_quality, event, map,
team_a, team_b, score_a, score_b, label,
agents_a, agents_b, provenance
```

`agents_a`, `agents_b`는 `|`로 연결된 5-agent lineup이다.

### 5.2 `players.csv`

`players.csv`는 player-map long table이다. accepted match-map 1행마다 team A 5명 + team B 5명 = 10행이 생긴다.

주요 컬럼:

```text
match_key, dedup_key, side, team, player_slot,
player, agent, role,
acs, kills, deaths, kd, kast, adr, assists, hs, fk, fd, clutch,
source, provenance
```

player stat은 보존하지만 예측 피처에 직접 넣지 않는다. 같은 경기의 ACS/KD/KAST/ADR/score/round/economy/clutch는 leakage 위험 때문에 `features_lineup.csv`, `features_static.csv`에서 제외한다.

### 5.3 `teams.csv`

`teams.csv`는 team-map long table이다. accepted match-map 1행마다 2행이 생긴다.

주요 컬럼:

```text
match_key, dedup_key, side, team, score, won,
agents, duelist, initiator, controller, sentinel,
source, provenance
```

---

## 6. Feature table

### 6.1 `features_lineup.csv`

라인업만으로 만들 수 있는 pre-match 피처다.

포함:

- map one-hot
- team A/B role count
- role count diff
- team A/B agent one-hot
- agent one-hot diff
- label
- provenance와 split 메타데이터

제외:

- ACS
- KD
- KAST
- ADR
- score
- round
- economy
- clutch
- 같은 경기 후행 stat 일체

이번 full run 검증값:

```json
"forbidden_lineup_feature_columns": []
```

### 6.2 `features_static.csv`

`features_lineup.csv` 중 `date_quality=iso`인 row에만 strict-before history를 붙인 테이블이다.

strict-before 규칙:

- 같은 날짜의 경기들은 서로의 history로 사용하지 않는다.
- 해당 경기 날짜보다 과거 row만 집계한다.
- 날짜가 `partial` 또는 `missing`이면 static 대상에서 제외한다.

추가되는 주요 피처:

```text
strict_before_cutoff,
a_team_prior_games, b_team_prior_games,
a_team_prior_wr, b_team_prior_wr, diff_team_prior_wr,
a_team_map_prior_games, b_team_map_prior_games,
a_team_map_prior_wr, b_team_map_prior_wr, diff_team_map_prior_wr,
a_agent_map_prior_games, b_agent_map_prior_games,
a_agent_map_prior_wr, b_agent_map_prior_wr, diff_agent_map_prior_wr
```

이번 full run 검증값:

```json
"forbidden_static_feature_columns": []
```

---

## 7. Split

`dedup_key`를 SHA-256 bucket으로 나눠 deterministic split을 만든다.

| bucket | split |
|--------|-------|
| 0-69 | train |
| 70-84 | val |
| 85-99 | test |

이번 full run에서는 `features_static.csv`가 존재하므로 `train.csv`, `val.csv`, `test.csv`는 `features_static.csv` 기준으로 저장되었다.

| split | rows |
|-------|-----:|
| train | 18,965 |
| val | 4,129 |
| test | 4,174 |

검증 결과:

```json
"split_overlap_count": 0
```

---

## 8. Model smoke 비교

`reports/preprocess/comparison.csv`는 같은 split에서 `features_lineup`과 `features_static`을 LR/LGB로 가볍게 비교한 결과다.

| dataset | model | accuracy | ROC-AUC | feature_count |
|---------|-------|---------:|--------:|--------------:|
| `features_lineup` | `lr` | 0.575836 | 0.547682 | 112 |
| `features_lineup` | `lgb` | 0.577229 | 0.556333 | 112 |
| `features_static` | `lr` | 0.624581 | 0.643706 | 127 |
| `features_static` | `lgb` | 0.636080 | 0.674541 | 127 |

이 값은 “현재 champion 교체” 근거가 아니라 raw-only preprocessing 산출물이 학습 가능한 형태인지 보는 smoke check다.

---

## 9. 검증 명령

구현 파일과 전용 테스트:

```bash
.venv/bin/python -m py_compile ml/raw_preprocess.py tests/test_raw_preprocess.py
.venv/bin/python -m pytest tests/test_raw_preprocess.py -q
```

전용 테스트가 확인하는 항목:

- raw input deny-list
- parser acceptance/reject
- dedup key 안정성
- date-quality gate
- forbidden feature exclusion
- strict-before guard

full run 중 로컬 환경에서 Matplotlib cache와 joblib physical core 감지 warning이 나왔지만, 전처리 산출물 생성 실패는 아니었다.

---

## 10. 현재 산출물의 사용 경계

이 산출물은 다음 목적에 적합하다.

- raw source inventory와 schema audit
- match/player/team 정규화 결과 검토
- leakage-safe lineup/static 피처 비교
- 향후 champion 교체 후보를 만들기 전 데이터 기반 검토

아직 다음을 의미하지 않는다.

- 기존 active v8/v8.6 champion 교체
- Streamlit app input contract 변경
- economy/clutch/round momentum 피처 사용 승인
- partial/missing date row의 static feature 승격

champion 교체나 앱 wiring 변경은 별도 실험, 평가, 회귀 검증 후 진행해야 한다.
