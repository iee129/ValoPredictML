# 04. 소스별 컬럼 정의 및 파서 매핑

마지막 업데이트: 2026-05-04

---

## 1. ryanluong 파서 (vct_2021_2023 + challengers)

**파일 구조**: `overview.csv` (선수 스탯) + `maps_scores.csv` (팀 점수) — 조인 필수  
**조인 키**: `Match Name` + `Map`

### overview.csv

| 원본 컬럼 | 정규화 컬럼 | 비고 |
|---------|-----------|------|
| `Tournament`, `Stage`, `Match Name` | `match_key` 재료 | — |
| `Map` | `map` | normalize_map() |
| `Player` | `player` | — |
| `Teams` | `team` | normalize_team() |
| `Agents` | `agent` | normalize_agent() |
| `Average Combat Score` | `acs` | — |
| `Kills - Deaths (KD)` | `kd` | float |
| `Kill Assist Trade Survive %` | `kast` | float 0~1 |
| `Average Damage Per Round` | `adr` | — |
| `First Kills` / `First Deaths` | `fk` / `fd` | — |
| `HS%` | `hs` | 소문자 정규화 |
| `Clutch%` | `clutch` | 결측 시 0 |

KAST 가용성: ✅

### maps_scores.csv

| 원본 컬럼 | 정규화 컬럼 | 비고 |
|---------|-----------|------|
| `Match Name` + `Map` | 조인 키 | — |
| `Team A`, `Team B` | `team_a`, `team_b` | normalize_team() |
| `Team A Score`, `Team B Score` | `score_a`, `score_b` → `label` | — |
| `Team A Attacker Score` | `atk_a` | atk_side_advantage 집계 소스 |
| `Team A Defender Score` | `def_a` | — |

---

## 2. qualidea 파서

**파일**: `data-since-april-2021.csv` (249,711행) — 조인 불필요

| 원본 컬럼 | 정규화 컬럼 | 비고 |
|---------|-----------|------|
| `player-team` | `team` | normalize_team() |
| `agent` | `agent` | 소문자 → normalize_agent() |
| `acs`, `k`, `d`, `a` | `acs`, `kills`, `deaths`, `assists` | — |
| `kast` | `kast` | float |
| `adr`, `fk`, `fd` | `adr`, `fk`, `fd` | — |
| `hs` | `hs` | — |
| `team1-score`, `team2-score` | `score_a`, `score_b` → `label` | — |
| `acs-t`, `acs-ct` | 공수 분리 (보강용) | 유일 소스 |
| `kd-t`, `kd-ct`, `adr-t`, `adr-ct` | 공수 분리 (보강용) | — |

KAST 가용성: ✅

---

## 3. piyush 파서 (2024/2025)

**파일**: 이벤트 폴더 내 `detailed_matches_player_stats.csv` — 조인 불필요  
**폴더 탐색**: `*_csvs` 패턴 재귀

| 원본 컬럼 | 정규화 컬럼 | 비고 |
|---------|-----------|------|
| `player_name` | `player` | — |
| `team`, `agent` | `team`, `agent` | normalize_team/agent() |
| `acs`, `k`, `d`, `a` | `acs`, `kills`, `deaths`, `assists` | — |
| `kast` | `kast` | ⚠️ 일부 이벤트 결측 |
| `adr` | `adr` | — |
| `hs_percent` | `hs` | 다른 소스의 `HS%`와 정규화 필요 |
| `fk`, `fd` | `fk`, `fd` | — |
| `map_winner` | 승팀 이름 → `label` | 조인 불필요 |

KAST 가용성: ⚠️ 일부 이벤트 결측 — `-1` 플래그 처리

---

## 4. ediashtarevin 파서

**파일**: `player_stats.csv` — 조인 불필요

| 원본 컬럼 | 정규화 컬럼 | 비고 |
|---------|-----------|------|
| `match_id`, `game_id` | `match_key` 재료 | — |
| `team` / `opponent` | `team_a` / `team_b` | win='win' 기준 |
| `win_lose` | `label` | `win`→1, `lose`→0 |
| `map`, `player`, `agent` | `map`, `player`, `agent` | normalize_*() |
| `acs`, `kill`, `death`, `assist` | `acs`, `kills`, `deaths`, `assists` | — |
| `kast%`, `adr`, `fk`, `fd` | `kast`, `adr`, `fk`, `fd` | — |

KAST 가용성: ✅ (`kast%`)

---

## 5. kierru 파서

**파일**: `csv/stats.csv` — 조인 불필요

| 원본 컬럼 | 정규화 컬럼 | 비고 |
|---------|-----------|------|
| `player_name`, `team`, `agent` | `player`, `team`, `agent` | normalize_*() |
| `map`, `game_id`, `match_id` | `map`, `match_key` 재료 | — |
| `win_lose` | `label` | — |
| `role_agent` | 역할군 직접 추출 | AGENT_ROLE_MAP 없이 가능 |
| `acs`, `kill`, `death`, `assist` | `acs`, `kills`, `deaths`, `assists` | — |
| `kast_percent`, `adr`, `hs_percent` | `kast`, `adr`, `hs` | — |
| `first_kill`, `first_death` | `fk`, `fd` | — |
| `score_team`, `score_opp` | 추가 레이블 검증용 | — |

KAST 가용성: ❓ 구현 시 컬럼 확인 필요

---

## 6. 컬럼명 정규화 규칙

| 항목 | 처리 |
|------|------|
| HS% 컬럼명 | `HS%` / `hs_percent` / `hs` → `hs` |
| KD 표기 | `KD`, `Kills - Deaths (KD)`, `kd_ratio` → `kd` (float) |
| KAST 표기 | `KAST`, `kast%`, `Kill Assist Trade Survive %` → `kast` (float 0~1) |
| 컬럼명 | snake_case 통일 |
