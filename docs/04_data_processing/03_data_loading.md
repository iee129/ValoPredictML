# 03. 데이터 로드 및 소스별 파서

마지막 업데이트: 2026-05-04

## 1. 파서 개요

소스마다 파일 구조가 달라 파서를 소스별로 분리한다. 파서 공통 출력 스키마는 동일하며, 이후 품질 검사·피처 생성 단계는 소스에 무관하게 동일한 인터페이스로 처리된다.

**파서 목록**:

실제 파싱은 `ml/raw_preprocess.py` 내 parser family로 구현되어 있다 (`ml/parsers/` 디렉토리는 존재하지 않음).

| 파서 함수 | 소스 | 구현 위치 |
|-----------|------|----------|
| `parse_ryanluong` | vct_2021_2023, ryanluong challengers | `ml/raw_preprocess.py` |
| `parse_qualidea` | qualidea1217 | `ml/raw_preprocess.py` |
| `parse_ediashtarevin` | ediashtarevin | `ml/raw_preprocess.py` |
| `parse_piyush2024` | piyush86kumar/valorant-champions-2024 | `ml/raw_preprocess.py` |
| `parse_vlrgg_raw_detail` | vlrgg_* (예정) | `ml/raw_preprocess.py` |

---

## 2. 파서 공통 출력 스키마

모든 파서는 아래 딕셔너리 리스트를 반환한다.

```python
{
    "source": str,           # 소스 식별자 (dedup 가중치 판단용)
    "match_key": str,        # 16자 SHA-1 (경기 단위 grouping)
    "dedup_key": str,        # 24자 SHA-1 (중복 제거 키)
    "date": str,             # YYYY-MM-DD (시간 가중치용)
    "event": str,
    "map": str,
    "team_a": str,
    "team_b": str,
    "players_a": list[dict], # 5명 × {player, agent, acs, kd, kast, adr, fk, fd, assists}
    "players_b": list[dict],
    "score_a": int,
    "score_b": int,
    "atk_a": int | None,     # 공격 라운드 승리 수 (ryanluong만 보유)
    "def_a": int | None,
    "label": int,            # 1 = team_a 승, 0 = team_b 승
}
```

---

## 3. 소스별 컬럼 매핑

### 3-1. ryanluong 파서 (vct_2021_2023 + challengers)

**파일 구조**: `overview.csv` (선수 스탯) + `maps_scores.csv` (팀 점수) — **조인 필수**

```
overview.csv 컬럼               → 정규화 컬럼
  Tournament, Stage, Match Name → match_key 재료
  Map                           → map
  Player                        → player
  Team                          → team
  Agents                        → agent
  Average Combat Score          → acs
  Kills - Deaths (KD)           → kd
  Kill Assist Trade Survive %   → kast
  Average Damage Per Round      → adr
  First Kills / First Deaths    → fk / fd

maps_scores.csv 컬럼            → 정규화 컬럼
  Match Name + Map              → 조인 키
  Team A, Team B                → team_a, team_b
  Team A Score, Team B Score    → score_a, score_b → label
  Team A Attacker Score         → atk_a  (atk_side_advantage 집계 소스)
  Team A Defender Score         → def_a
```

조인 키: `Match Name + Map`.
`vct_2021_2023`은 연도별 하위 폴더(`vct_2021/`~`vct_2026/`)에 동일 구조 반복 — 파서가 재귀 탐색.
KAST 가용성: 있음.

---

### 3-2. qualidea 파서

**파일**: `data-since-april-2021.csv` (249,711행) — **조인 불필요**

```
player-team               → team
agent                     → agent  (소문자)
acs, k, d, a              → acs, kills, deaths, assists
kast                      → kast
adr, fk, fd               → adr, fk, fd
team1-score, team2-score  → score_a, score_b → label
```

공수 분리 컬럼 (보강 시 활용 가능): `acs-t`, `acs-ct`, `kd-t`, `kd-ct`, `adr-t`, `adr-ct`.
KAST 가용성: 있음.

---

### 3-3. ediashtarevin 파서

**파일**: `player_stats.csv` — **조인 불필요**

```
match_id, game_id          → match_key 재료
team / opponent            → team_a (win='win' 기준) / team_b
win_lose                   → label  ('win'→1, 'lose'→0)
map, player, agent         → map, player, agent
acs, kill, death, assist   → acs, kills, deaths, assists
kast%, adr, fk, fd         → kast, adr, fk, fd
```

KAST 가용성: 있음 (`kast%`).

---

## 4. dedup_key / match_key 생성

```python
import hashlib

def make_dedup_key(date, event, map_, team_a, team_b, agents_a, agents_b, score_a, score_b):
    canonical = "|".join([
        str(date), event.lower().strip(), map_.lower(),
        team_a.lower(), team_b.lower(),
        ",".join(sorted(agents_a)), ",".join(sorted(agents_b)),
        str(score_a), str(score_b)
    ])
    return hashlib.sha1(canonical.encode()).hexdigest()[:24]  # 24자

def make_match_key(date, event, team_a, team_b):
    canonical = "|".join([str(date), event.lower(), team_a.lower(), team_b.lower()])
    return hashlib.sha1(canonical.encode()).hexdigest()[:16]  # 16자
```

`dedup_key`: 동일 경기 중복 제거 기준 (24자 SHA-1).
`match_key`: train/val/test 분할 그룹 단위 (16자 SHA-1).

팀명은 key 생성 전 반드시 `normalize_team()` 호출.

---

## 5. 컬럼명 정규화

| 항목 | 처리 |
|------|------|
| 요원명 | `normalize_agent(raw)` — AGENT_ROLE_MAP → AGENT_ALIASES 소문자 → `.title()` → None |
| 맵명 | `normalize_map(raw)` — MAP_ORDER → 별칭 → `.title()` → None |
| 컬럼명 | snake_case 통일 (`hs%` / `hs_percent` / `HS%` → `hs`) |
| KD 표기 | `kd_ratio`, `k:d`, `Kills - Deaths (KD)` → `kd` (float) |
| KAST 표기 | `kast%`, `Kill Assist Trade Survive %` → `kast` (float 0~1) |

---

## 6. 파싱 실행 흐름

```python
# ml/raw_preprocess.py parser family 호출
parse_ryanluong("data/raw/kaggle/vct_2021_2023")
parse_ryanluong("data/raw/kaggle/ryanluong1__valorant-challengers-league-data")
parse_qualidea ("data/raw/kaggle/qualidea1217__valorant-pro-matches-since-april-2021")
parse_piyush2024("data/raw/kaggle/piyush86kumar__valorant-champions-2024")
parse_edia     ("data/raw/kaggle/ediashtarevin__vct-champions-2023-stats")
# → 공통 스키마 행 리스트로 병합
```

---

## 7. 관련 문서

| 문서 | 내용 |
|------|------|
| [04_data_cleaning.md](04_data_cleaning.md) | 품질 검사 및 dedup 중복 제거 |
| [05_aggregation.md](05_aggregation.md) | 선수 행 → 맵 행 집계 |
| [../preprocessing.md](../preprocessing.md) | 전처리 전략 원문 (섹션 3) |
