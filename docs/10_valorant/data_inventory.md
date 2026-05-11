# 데이터셋 인벤토리

작성: 2026-05-09  
관련: US-T01 (US-002 데이터 통합, plan v7)

총 **29개** 데이터셋 (Kaggle 24 + GitHub 5). 활성 6개는 현재 파이프라인 사용 중.  
통합 결정: **Y** (파이프라인 통합), **P** (부분/검토 중), **N** (제외)

---

## 활성 데이터셋 (현재 파이프라인 사용 — 6개)

### D-01 · ryanluong1__valorant-challengers-league-data
- **경로**: `data/raw/kaggle/ryanluong1__valorant-challengers-league-data/`
- **파일**: `vcl_2023/`, `vcl_2024/` (하위: agents/, players_stats/, matches/, ids/)
- **주요 행 수**: teams_picked_agents 137,598 · agents_pick_rates 201,578 · maps_stats 7,753
- **주요 컬럼**: map, team, agent, pick_rate, win_rate, side_win_rate 등
- **소스 가중치**: 1.8 (`kaggle_challengers`)
- **통합**: **Y** — Challengers 리그 요원·맵 픽률 핵심 소스

### D-02 · vct_2021_2023
- **경로**: `data/raw/kaggle/vct_2021_2023/`
- **파일**: `vct_2021/`, `vct_2022/`, `vct_2023/`, `vct_2024/`, `vct_2025/`, `vct_2026/`
- **주요 행 수**: 연도별 VCT 매치 결과 (전체 추정 ≥ 10,000 매치)
- **주요 컬럼**: event, match_id, team_a, team_b, map, winner, agent_picks 등
- **소스 가중치**: 1.0 (`kaggle_vct`)
- **통합**: **Y** — VCT 공식 매치 결과 2021–2026 전범위

### D-03 · qualidea1217__valorant-pro-matches-since-april-2021
- **경로**: `data/raw/kaggle/qualidea1217__valorant-pro-matches-since-april-2021/`
- **파일**: `data-since-april-2021.csv` (latin-1 인코딩)
- **행 수**: 249,710
- **주요 컬럼**: match_id, date, team_a, team_b, map, winner, agent_a1..a5, agent_b1..b5
- **소스 가중치**: 1.0 (`kaggle_qualidea`)
- **통합**: **Y** — 2021년 4월 이후 프로 매치 전체, 요원 픽 구조 일치

### D-04 · ediashtarevin__vct-champions-2023-stats
- **경로**: `data/raw/kaggle/ediashtarevin__vct-champions-2023-stats/`
- **파일**: `player_stats.csv`
- **행 수**: 6,230
- **주요 컬럼**: player, team, agent, map, acs, kills, deaths, assists, adr
- **통합**: **Y** — Champions 2023 선수 통계, 요원별 성능 피처 보강

### D-05 · piyush86kumar__valorant-champions-2024
- **경로**: `data/raw/kaggle/piyush86kumar__valorant-champions-2024/`
- **파일**: agents_stats, maps_stats, detailed_matches_overview (34행), detailed_matches_player_stats, economy_data 등 11 CSVs
- **주요 행 수**: agents_stats 일부, maps_stats ~수백
- **통합**: **Y** — Champions 2024 공식 통계, piyush 스키마 호환

### D-06 · piyush86kumar__valorant-vct-2025-all-events
- **경로**: `data/raw/kaggle/piyush86kumar__valorant-vct-2025-all-events/`
- **파일**: 17개 이벤트 디렉토리 (Kickoff × 4 + Stage 1 × 4 + Stage 2 × 4 + Masters Bangkok + Masters Toronto + Champions 2025)
- **주요 행 수**: 이벤트별 dozens ~ 수백 매치
- **통합**: **Y** — VCT 2025 전 이벤트 통합 소스

---

## 통합 예정 데이터셋 (미활성 — 우선순위 높음)

### D-07 · visualize25__valorant-pro-matches-full-data ⭐
- **경로**: `data/raw/kaggle/visualize25__valorant-pro-matches-full-data/`
- **파일**: `valorant.sqlite` (76MB)
- **테이블**:
  - Matches: 7,818행 (MatchID, Date, Patch, EventID, EventName, EventStage, Team1/2)
  - Games: 15,888행 (GameID, MatchID, Map, Winner, Team1/2_TotalRounds)
  - Game_Rounds: 15,531행 (GameID, RoundHistory JSON)
  - Game_Scoreboard: 157,939행 (GameID, PlayerID, Agent, ACS, K/D/A)
- **ETL 상태**: ✅ `ml/data_loaders/sqlite.py` 구현 완료 (US-T03)
- **통합**: **Y** — 라운드 단위 데이터 유일 소스, MoE·Discovery 피처에 필수

### D-08 · hidious__valorant-vlrgg-results-and-stats
- **경로**: `data/raw/kaggle/hidious__valorant-vlrgg-results-and-stats/`
- **파일**: `results.csv` (11,300행), `stats.csv` (315행)
- **주요 컬럼** (results): match_id, team_a, team_b, map, score, date, region
- **통합**: **Y** — VLR.gg 직접 스크래핑 대안 (이미 캐시됨), 지역별 매치 결과

### D-09 · daturasj__valorant-champions-tour-promotion-analysis
- **경로**: `data/raw/kaggle/daturasj__valorant-champions-tour-promotion-analysis/`
- **파일**: `vct_player_stats_2.csv` (64,778행)
- **주요 컬럼**: player, team, tournament, agent, map, acs, k, d, a, kd_ratio
- **통합**: **Y** — 대규모 선수 통계, 요원별 ACS·KDA 피처 보강

### D-10 · kierru__valorant-vct-champions-2025-dataset
- **경로**: `data/raw/kaggle/kierru__valorant-vct-champions-2025-dataset/`
- **파일**: score.csv, stats.csv, economy.csv, 1v1.csv, counter_kill.csv, pick_ban.csv, player_id.csv, team_id.csv, agent_id.csv, match_id.csv (10 CSVs)
- **통합**: **Y** — Champions 2025 이코노미·1v1·카운터킬 데이터, US-007 Causal·추천 피처

### D-11 · grap510__valorant-vct-economy-data
- **경로**: `data/raw/kaggle/grap510__valorant-vct-economy-data/`
- **파일**: `vct_data.csv`, `vctdata/`, `vctguns_training/`, `vctshield_training/`
- **통합**: **P** — 이코노미 특화 데이터 (gun/shield 학습셋), US-007 ult timing 피처 후보

### D-12 · piyush86kumar__valorant-champions-tour-2024-all-events
- **경로**: `data/raw/kaggle/piyush86kumar__valorant-champions-tour-2024-all-events/`
- **파일**: 14 이벤트 × `_csvs/` 디렉토리 (Americas/EMEA/Pacific/China × Kickoff+Stage1+Stage2 + Masters Madrid + Masters Shanghai + Champions 2024)
- **통합**: **Y** — VCT 2024 전 이벤트, D-05 대비 이벤트 세분화

### D-13 · piyush86kumar__valorant-champions-tour-2025-paris
- **경로**: `data/raw/kaggle/piyush86kumar__valorant-champions-tour-2025-paris/`
- **파일**: 11 CSVs (agents_stats, maps_stats, detailed_matches_*)
- **통합**: **Y** — VCT 2025 Paris Champions 이벤트 (D-06 보완)

### D-14 · piyush86kumar__valorant-kickoff-2025-all-regions
- **경로**: `data/raw/kaggle/piyush86kumar__valorant-kickoff-2025-all-regions/`
- **파일**: Americas/EMEA/Pacific/China Kickoff `_csvs/`
- **통합**: **Y** — 2025 Kickoff 지역별 (D-06 포함이나 개별 접근 가능)

### D-15 · piyush86kumar__valorant-masters-bangkok-2025
- **경로**: `data/raw/kaggle/piyush86kumar__valorant-masters-bangkok-2025/`
- **파일**: 11 CSVs
- **통합**: **Y** — Masters Bangkok 2025 (D-06 포함이나 개별 접근 가능)

### D-16 · piyush86kumar__valorant-masters-toronto-2025
- **경로**: `data/raw/kaggle/piyush86kumar__valorant-masters-toronto-2025/`
- **파일**: 11 CSVs
- **통합**: **Y** — Masters Toronto 2025

### D-17 · piyush86kumar__valorant-stage-1-2025-all-regions
- **경로**: `data/raw/kaggle/piyush86kumar__valorant-stage-1-2025-all-regions/`
- **파일**: Americas/EMEA/Pacific/China Stage 1 `_csvs/`
- **통합**: **Y** — 2025 Stage 1 지역별

### D-18 · piyush86kumar__valorant-stage-2-2025-all-regions
- **경로**: `data/raw/kaggle/piyush86kumar__valorant-stage-2-2025-all-regions/`
- **파일**: Americas/EMEA/Pacific/China Stage 2 `_csvs/`
- **통합**: **Y** — 2025 Stage 2 지역별

---

## 검토 중 데이터셋

### D-19 · notnguyen__valorant-dataset-v3
- **경로**: `data/raw/kaggle/notnguyen__valorant-dataset-v3/`
- **파일**: `valorant_dataset_v3.csv` (2,694행)
- **주요 컬럼**: 미확인 (스키마 검토 필요)
- **통합**: **P** — 행 수 적음, 스키마 검토 후 결정

### D-20 · sauurabhkr__valorant-champions-tour-2024
- **경로**: `data/raw/kaggle/sauurabhkr__valorant-champions-tour-2024/`
- **파일**: `vct-challengers.json`, `vct-game-changer.json`, `vct-international.json`
- **통합**: **P** — JSON 포맷, Game Changers 포함 (스코프 검토 필요)

### D-21 · ulisescruzsantos__valorant-champions-tour-2024-regional-stats
- **경로**: `data/raw/kaggle/ulisescruzsantos__valorant-champions-tour-2024-regional-stats/`
- **파일**: `VCT_2024.csv` (775행)
- **통합**: **P** — 지역별 통계, 행 수 적음 (집계 단위 큼)

### D-22 · agarwalvishal00__esports-data-valorant-vct-lockin-player-stats
- **경로**: `data/raw/kaggle/agarwalvishal00__esports-data-valorant-vct-lockin-player-stats/`
- **파일**: `Val.xlsx`
- **통합**: **P** — Lock-In 이벤트 선수 통계, XLSX 파싱 필요 (openpyxl)

### D-23 · kierru__vctpacific-2023
- **경로**: `data/raw/kaggle/kierru__vctpacific-2023/`
- **파일**: `csv/` 디렉토리
- **통합**: **P** — VCT Pacific 2023 상세, kierru 스키마

### D-24 · wsiah6864__vct_paris_2025 *(GitHub)*
- **경로**: `data/raw/github/wsiah6864__vct_paris_2025/`
- **파일**: agents_stats.csv, maps_stats.csv, detailed_matches_overview.csv, detailed_matches_maps.csv, detailed_matches_player_stats.csv
- **통합**: **P** — Paris 2025 (D-13 중복 가능성 확인 필요)

---

## 제외 데이터셋

### D-25 · vkay616__valorant-vct-2023-player-performance
- **경로**: `data/raw/kaggle/vkay616__valorant-vct-2023-player-performance/`
- **파일**: `overall_player_stats.csv` (80행), `player_stats_by_agent.csv`
- **통합**: **N** — 행 수 너무 적음 (80행), 노이즈 대비 정보량 낮음

---

## GitHub 데이터셋

### D-26 · cameronwafer__valorant *(GitHub)*
- **경로**: `data/raw/github/cameronwafer__valorant/`
- **파일**: `valorantStatsAll.xlsx`
- **통합**: **P** — XLSX 파싱 필요, 스키마 검토 후 결정

### D-27 · hennazu__valorant-dataset *(GitHub)*
- **경로**: `data/raw/github/hennazu__valorant-dataset/`
- **파일**: `agents.csv`, `maps.csv`, `players.csv`, `teams.csv`
- **통합**: **P** — 요원·맵 메타 레퍼런스 (통합 후 도메인 피처 검증용)

### D-28 · ironicninja__valorant-stats *(GitHub)*
- **경로**: `data/raw/github/ironicninja__valorant-stats/`
- **파일**: `agents_data/` 디렉토리
- **통합**: **P** — 스키마 검토 후 결정

### D-29 · sushant-jha__valorant-data-sheets *(GitHub)*
- **경로**: `data/raw/github/sushant-jha__valorant-data-sheets/`
- **파일**: `VCT_NA_EMEA.csv`
- **통합**: **P** — NA/EMEA 지역별, 스키마 검토 후 결정

---

## 요약 통계

| 결정 | 수 | 비고 |
|------|----|------|
| **Y** (통합) | 18 | D-01~18 |
| **P** (검토 중) | 10 | D-19~29 (D-25 제외) |
| **N** (제외) | 1 | D-25 (vkay616, 80행) |
| **합계** | **29** | Kaggle 24 + GitHub 5 |

**ETL 구현 완료**: D-07 (visualize25 SQLite) — `ml/data_loaders/sqlite.py`  
**다음 단계**: D-07 통합 후 D-08 (hidious VLR.gg proxy) → D-09 (daturasj 64k) → D-10 (kierru 2025) 순서 권장
