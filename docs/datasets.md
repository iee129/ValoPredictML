# 데이터셋 가이드

ValoPredictML에서 사용하는 7개 Kaggle 데이터셋의 내용, 프로젝트 관련성, 파이프라인 역할을 정리한 문서.

> 로컬 위치: `data/raw/kaggle/` (2.3GB, git 제외)  
> 다운로드: `python dataload.py` (`~/.kaggle/kaggle.json` 필요)

---

## 1. 데이터셋 분류 체계

수집 기준: `agent + map + winner` 3개 필수 컬럼 / K·D·A 개별 분리 / 선수-경기-맵 1행 단위 / 핵심 스탯 결측률 < 30% / 프로·준프로 경기만

| 등급 | 설명 | 수 |
|------|------|----|
| **핵심** | 대용량 다년도 학습 소스 — 선수 스탯 + 팀 점수 + 승패 레이블 보유 | 3개 |
| **보조** | 특정 대회·지역 보강, 교차 검증용 | 2개 |

---

## 2. 핵심 데이터셋 (Core)

학습 파이프라인에 직접 투입되는 대용량 다년도 소스.

---

### 2.1 `vct_2021_2023` — VCT 프로 경기 2021~2026

| 항목 | 내용 |
|------|------|
| Kaggle ID | `ryanluong1/valorant-champion-tour-2021-2023-data` |
| 용량 | 1.2GB |
| 구조 | `vct_2021~2026/matches/`, `players_stats/`, `agents/`, `all_ids/` |
| 핵심 파일 | `players_stats/*.csv` — 선수별 경기 스탯 |

**행 단위**: 선수 1명 × 맵 1개 — 특정 경기의 특정 맵에서 선수 한 명이 어떤 요원으로 뛴 결과가 1행. bo3 경기라면 선수당 최대 3행, 5명 × 2팀 × 3맵 = 최대 150행.

| 컬럼 | 설명 |
|------|------|
| `Tournament` | 대회명 |
| `Stage` | 대회 단계 (`Group Stage`, `Playoffs`, `Grand Final`) |
| `Match Type` | 경기 포맷 (`BO1` / `BO3` / `BO5`) |
| `Player` | 선수 이름 |
| `Teams` | 선수 소속 팀 |
| `Agents` | **이 맵에서 선택한 요원** |
| `Rounds Played` | 총 라운드 수 |
| `Rating` | VLR.gg 종합 기여도 점수 |
| `ACS` | Average Combat Score — 라운드당 평균 전투 점수 |
| `KD` | Kill / Death 비율 |
| `KAST` | Kill/Assist/Survived/Traded 라운드 비율(%) |
| `ADR` | Average Damage per Round |
| `FK` / `FD` | First Kill / First Death 횟수 |
| `HS%` | 헤드샷 비율(%) |
| `Clutch%` | 클러치 성공률(%) |

**승패 레이블**: `maps_scores.csv`의 `Score A / B`로 조인하여 생성. `Match Name + Map` 조인 키.

**파이프라인 역할**: ryanluong 파서 메인 소스 → 품질 게이트 → 학습 데이터

---

### 2.2 `ryanluong1__valorant-challengers-league-data` — Challengers League (T2)

| 항목 | 내용 |
|------|------|
| Kaggle ID | `ryanluong1/valorant-challengers-league-data` |
| 용량 | 1.0GB |
| 구조 | `vcl_2023/`, `vcl_2024/` — 각 폴더에 `overview.csv`, `maps_scores.csv` |
| 핵심 파일 | `overview.csv` (선수-맵 단위), `maps_scores.csv` (팀 점수 + 공수 기록) |

**`overview.csv` — 행 단위**: 선수 1명 × 맵 1개.

| 컬럼 | 설명 |
|------|------|
| `Match Name` | 경기 식별명 — `maps_scores.csv`와의 조인 키 |
| `Map` | 맵 이름 |
| `Player` / `Team` | 선수·소속 팀 |
| `Agents` | **이 맵에서 선택한 요원** |
| `ACS` / `KD` / `KAST` / `ADR` / `FK` / `FD` / `Rating` | 스탯 컬럼 |

**`maps_scores.csv` — 행 단위**: 팀 1개 × 맵 1개.

| 컬럼 | 설명 |
|------|------|
| `Match Name` / `Map` | 조인 키 |
| `Score A / B` | 각 팀의 최종 라운드 승리 수 — **승패 레이블 소스** |
| `Attacker Score` | **공격(T) 사이드 라운드 승리 수** — `atk_side_advantage` 집계 핵심 소스 |
| `Defender Score` | **수비(CT) 사이드 라운드 승리 수** |

**왜 필요한가?** VCT 바로 아래 2부 리그. VCT보다 경기 수가 많아 학습 데이터를 크게 늘린다. 지역별 다양한 팀 스타일이 담겨 모델의 과적합을 방지한다. 공격/수비 라운드 점수 분리 제공으로 `atk_side_advantage` 피처 집계의 핵심 소스다.

**파이프라인 역할**: ryanluong 파서 메인 소스, 소스 가중치 1.8(최고)

---

### 2.3 `qualidea1217__valorant-pro-matches-since-april-2021` — 2021년 이후 프로 경기

| 항목 | 내용 |
|------|------|
| Kaggle ID | `qualidea1217/valorant-pro-matches-since-april-2021` |
| 용량 | ~35MB |
| 핵심 파일 | `data-since-april-2021.csv` (249,711행) |

**행 단위**: 선수 1명 × 맵 1개. 팀 점수와 선수 스탯이 같은 행에 있어 **조인 없이 레이블 생성 가능**.

| 컬럼 | 설명 |
|------|------|
| `match-datetime` | 경기 일시 |
| `patch` | 게임 패치 버전 — 메타 변화 시점 추적 |
| `map` | 맵 이름 |
| `team1` / `team2` | 양 팀 이름 |
| `team1-score` / `team2-score` | 라운드 승리 수 — **승패 레이블 소스** |
| `player-name` / `player-team` / `agent` | 선수·팀·요원 |
| `acs` / `k` / `d` / `a` / `kast` / `adr` / `fk` / `fd` / `hs` | 스탯 컬럼 |
| `acs-t` / `acs-ct` | **공격·수비 사이드별 ACS** — 다른 소스에 없는 희귀 컬럼 |
| `kd-t` / `kd-ct` / `adr-t` / `adr-ct` | 공격·수비 사이드별 스탯 |

**왜 필요한가?** 249,711행 대규모 데이터셋. 공격/수비 분리 스탯(`acs-t`, `acs-ct` 등)이 포함된 유일한 소스로 선공/후공 성능 차이 분석에 활용 가능하다. 2021년부터 현재까지 메타 변화 추이 포함.

**파이프라인 역할**: qualidea 파서 단일 소스, 공수 분리 스탯 검증

---

## 3. ~~piyush86kumar 계열~~ (제거됨)

> ❌ **파이프라인에서 제거됨**: `piyush86kumar__valorant-champions-tour-2024-all-events` 및 `piyush86kumar__valorant-vct-2025-all-events` 데이터셋 폴더와 `ml/parsers/piyush.py` 파서가 삭제됨.

---

## 4. 보조 데이터셋 (Supplementary)

특정 대회·지역 보강 및 교차 검증용.

---

### 4.1 `ediashtarevin__vct-champions-2023-stats` — VCT Champions 2023 선수 스탯

| 항목 | 내용 |
|------|------|
| Kaggle ID | `ediashtarevin/vct-champions-2023-stats` |
| 핵심 파일 | `player_stats.csv` (~6,231행) |

**행 단위**: 선수 1명 × 맵 1개. `match_id, game_id` 포함으로 경기 단위 조인 가능.

| 컬럼 | 설명 |
|------|------|
| `match_id` / `game_id` / `map` / `player` / `agent` / `team` / `opponent` | 식별 정보 |
| `win_lose` | **이 맵의 승패** — 레이블 소스 |
| `rating` / `acs` / `k` / `d` / `a` / `kast` / `adr` / `hs` / `fk` / `fd` | 스탯 컬럼 |

**파이프라인 역할**: 2023 Champions 선수 스탯 보강, vct_2021_2023 교차 검증

---

### 4.2 `kierru__vctpacific-2023` — VCT Pacific 2023

> ❌ **현재 파이프라인에서 제거됨**: 리젝션율 80%, 26행만 통과

| 항목 | 내용 |
|------|------|
| Kaggle ID | `kierru/vctpacific-2023` |
| 핵심 파일 | `csv/stats.csv` (~5,257행) |

**행 단위**: 선수 1명 × 맵 1개.

| 컬럼 | 설명 |
|------|------|
| `player_name` / `team` / `agent` / `map` / `game_id` / `match_id` | 식별 정보 |
| `win_lose` | **이 맵의 승패** — 레이블 소스 |
| `acs` / `kill` / `death` / `assist` / `kast_percent` / `adr` / `hs_percent` / `first_kill` / `first_death` | 스탯 컬럼 |
| `role_agent` | **요원 역할군 직접 포함** (`Duelist`, `Initiator` 등) — 역할군 피처 추출 간소화 |
| `score_team` / `score_opp` | 팀·상대 점수 — 추가 레이블 검증 가능 |

**왜 필요한가?** 한국·일본 등 Pacific 지역 특유의 빠른 템포와 Initiator 중심 조합을 포함. `role_agent` 컬럼이 직접 있어 역할군 파싱 로직 간소화 가능.

**파이프라인 역할**: ~~Pacific 지역 메타 보강, role_agent 직접 활용~~ → 제거됨 (리젝션율 80%, 26행만 통과)

---

## 5. 파이프라인 역할 매핑

| 파이프라인 단계 | 사용 데이터셋 |
|----------------|-------------|
| **파서 — ryanluong** | `vct_2021_2023`, `ryanluong1__valorant-challengers-league-data` |
| **~~파서 — piyush~~** | ~~`piyush86kumar__valorant-champions-tour-2024-all-events`, `piyush86kumar__valorant-vct-2025-all-events`~~ (제거됨) |
| **파서 — qualidea** | `qualidea1217__valorant-pro-matches-since-april-2021` |
| **보조 스탯 보강** | `ediashtarevin__vct-champions-2023-stats`, ~~`kierru__vctpacific-2023`~~ (제거됨) |
| **atk_side_advantage 집계** | `ryanluong1__challengers` (`maps_scores.csv`) |
| **role_agent 직접 추출** | ~~`kierru__vctpacific-2023`~~ (제거됨 — 리젝션율 80%로 파이프라인에서 제외) |
| **공수 분리 스탯** | `qualidea1217__*` (`acs-t`, `acs-ct`, `kd-t`, `kd-ct`) |

---

## 6. 관련성 종합 평가

| 데이터셋 | 관련성 | 이유 |
|----------|--------|------|
| `vct_2021_2023` | ★★★★★ | 6년치 T1 프로 경기 1.2GB, 핵심 학습 소스 |
| `ryanluong1__challengers` | ★★★★★ | T2 대용량 1.0GB, 공수 점수 분리, 소스 가중치 최고 |
| `qualidea1217__*` | ★★★★★ | 249K행, 공수 분리 스탯 유일 소스, 조인 불필요 |
| `piyush86kumar__2024` | ❌ 제거됨 | 데이터셋 폴더 및 파서 제거됨 |
| `piyush86kumar__2025` | ❌ 제거됨 | 데이터셋 폴더 및 파서 제거됨 |
| `ediashtarevin__*` | ★★★☆☆ | 2023 Champions 특화, 교차 검증용 |
| `kierru__vctpacific-2023` | ❌ 제거됨 | Pacific 지역 보강 목적이었으나 리젝션율 80%, 26행만 통과 — 파이프라인에서 제거됨 |
