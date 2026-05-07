# 03. 보조 데이터셋 — ediashtarevin + kierru

마지막 업데이트: 2026-05-04

---

## 1. ediashtarevin — VCT Champions 2023

| 항목 | 내용 |
|------|------|
| Kaggle ID | `ediashtarevin/vct-champions-2023-stats` |
| 핵심 파일 | `player_stats.csv` (~6,231행) |
| 파서 | ediashtarevin |
| 소스 가중치 | 0.9 |

**행 단위**: 선수 1명 × 맵 1개.

| 컬럼 | 설명 |
|------|------|
| `match_id` / `game_id` / `map` / `player` / `agent` / `team` / `opponent` | 식별 정보 |
| `win_lose` | 이 맵의 승패 — 레이블 소스 (`win`→1, `lose`→0) |
| `rating` / `acs` / `k` / `d` / `a` / `kast` / `adr` / `hs` / `fk` / `fd` | 스탯 컬럼 |

KAST 가용성: ✅ (`kast%`)

**파이프라인 역할**: 2023 Champions 선수 스탯 보강, vct_2021_2023 교차 검증.

---

## 2. kierru — VCT Pacific 2023

> ⚠️ **현재 파이프라인에서 제거됨**: 리젝션율 80%, 26행만 통과

| 항목 | 내용 |
|------|------|
| Kaggle ID | `kierru/vctpacific-2023` |
| 핵심 파일 | `csv/stats.csv` (~5,257행) |
| 파서 | kierru |
| 소스 가중치 | 0.9 (제거됨 — 가중치 0.9이었으나 리젝션율 80%로 제거) |

**행 단위**: 선수 1명 × 맵 1개.

| 컬럼 | 설명 |
|------|------|
| `player_name` / `team` / `agent` / `map` / `game_id` / `match_id` | 식별 정보 |
| `win_lose` | 이 맵의 승패 — 레이블 소스 |
| `role_agent` | 요원 역할군 직접 포함 (`Duelist`, `Initiator` 등) |
| `acs` / `kill` / `death` / `assist` / `kast_percent` / `adr` / `hs_percent` / `first_kill` / `first_death` | 스탯 컬럼 |
| `score_team` / `score_opp` | 팀·상대 점수 |

KAST 가용성: ❓ 구현 시 컬럼 확인 필요.

**파이프라인 역할**: Pacific 지역(한국·일본 등) 메타 보강. `role_agent` 컬럼 직접 제공으로 AGENT_ROLE_MAP 조회 없이 역할군 파싱 가능.

---

## 3. qualidea1217 — 2021년 이후 프로 경기

| 항목 | 내용 |
|------|------|
| Kaggle ID | `qualidea1217/valorant-pro-matches-since-april-2021` |
| 용량 | ~35MB |
| 핵심 파일 | `data-since-april-2021.csv` (249,711행) |
| 파서 | qualidea |
| 소스 가중치 | 1.0 |

**행 단위**: 선수 1명 × 맵 1개. 팀 점수와 선수 스탯이 같은 행에 있어 조인 없이 레이블 생성 가능.

| 컬럼 | 설명 |
|------|------|
| `match-datetime` | 경기 일시 |
| `patch` | 게임 패치 버전 |
| `map` | 맵 이름 |
| `team1` / `team2` | 양 팀 이름 |
| `team1-score` / `team2-score` | 라운드 승리 수 — 승패 레이블 소스 |
| `player-name` / `player-team` / `agent` | 선수·팀·요원 |
| `acs` / `k` / `d` / `a` / `kast` / `adr` / `fk` / `fd` / `hs` | 스탯 컬럼 |
| `acs-t` / `acs-ct` | 공격·수비 사이드별 ACS — 다른 소스에 없는 희귀 컬럼 |
| `kd-t` / `kd-ct` / `adr-t` / `adr-ct` | 공격·수비 사이드별 스탯 |

KAST 가용성: ✅

**파이프라인 역할**: qualidea 파서 단일 소스. 공수 분리 스탯(`acs-t`, `acs-ct`)을 보유하는 유일한 소스.
