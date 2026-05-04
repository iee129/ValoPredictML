# 데이터 전처리 전략

`data/raw/kaggle/` 7개 데이터셋 기반 전처리 파이프라인 및 피처 엔지니어링 설계 문서.  
마지막 업데이트: 2026-05-04

---

## 1. 데이터 소스 현황

| 소스 폴더 | 행 수 (추정) | 기간 | 파서 | 소스 가중치 |
|----------|------------|------|------|------------|
| `vct_2021_2023` | ~600K | 2021~2026 | ryanluong | 1.0 |
| `ryanluong1__valorant-challengers-league-data` | ~412K | 2023~2024 | ryanluong | **1.8** |
| `qualidea1217__valorant-pro-matches-since-april-2021` | ~250K | 2021~현재 | qualidea | 1.0 |
| `piyush86kumar__valorant-champions-tour-2024-all-events` | ~30K | 2024 | piyush | **1.5** |
| `piyush86kumar__valorant-vct-2025-all-events` | ~15K | 2025 | piyush | **1.5** |
| `ediashtarevin__vct-champions-2023-stats` | ~6K | 2023 | ediashtarevin | 0.9 |
| `kierru__vctpacific-2023` | ~5K | 2023 | kierru | 0.9 |

**소스 가중치 정책**: 중복 경기가 두 소스에 존재할 때 남길 행을 결정. ryanluong challengers(1.8)가 컬럼 수가 많고 공수 분리 스탯이 있어 신뢰도 최고. piyush(1.5)는 최신 메타를 담아 두 번째. 동점 시 컬럼 수가 더 많은 소스 우선.

**전처리 후 예상 맵 행수**: 선수행 ÷ 10 → 약 130K → 중복 제거 후 **80~100K 맵** 예상.

---

## 2. 공통 참조 데이터 (`ml/agent_roles.py`)

파서·정규화·품질 게이트 전 단계에서 공통으로 참조하는 매핑 테이블.

### 2-1. 요원 역할군 매핑 (27종)

| 요원 | 역할군 | 출시 |
|------|--------|------|
| Jett, Reyna, Phoenix, Raze | Duelist | EP 1 |
| Yoru | Duelist | EP 2 |
| Neon | Duelist | EP 4 |
| ISO | Duelist | EP 7 |
| Waylay | Duelist | EP 10 Act 2 |
| Sova, Breach | Initiator | EP 1 |
| Skye | Initiator | EP 1 Act 3 |
| KAY/O | Initiator | EP 3 |
| Fade | Initiator | EP 4 |
| Gekko | Initiator | EP 6 |
| Tejo | Initiator | EP 10 Act 1 |
| Viper, Omen, Brimstone | Controller | EP 1 |
| Astra | Controller | EP 2 |
| Harbor | Controller | EP 5 |
| Clove | Controller | EP 8 |
| Killjoy, Cypher, Sage | Sentinel | EP 1 |
| Chamber | Sentinel | EP 3 |
| Deadlock | Sentinel | EP 7 |
| Vyse | Sentinel | EP 9 |

```python
AGENT_ROLE_MAP: dict[str, str] = {
    # Duelist (8종)
    "Jett": "Duelist", "Reyna": "Duelist", "Phoenix": "Duelist",
    "Raze": "Duelist", "Yoru": "Duelist", "Neon": "Duelist",
    "ISO": "Duelist", "Waylay": "Duelist",
    # Initiator (7종)
    "Sova": "Initiator", "Breach": "Initiator", "Skye": "Initiator",
    "KAY/O": "Initiator", "Fade": "Initiator", "Gekko": "Initiator",
    "Tejo": "Initiator",
    # Controller (6종)
    "Viper": "Controller", "Omen": "Controller", "Brimstone": "Controller",
    "Astra": "Controller", "Harbor": "Controller", "Clove": "Controller",
    # Sentinel (6종)
    "Killjoy": "Sentinel", "Cypher": "Sentinel", "Sage": "Sentinel",
    "Chamber": "Sentinel", "Deadlock": "Sentinel", "Vyse": "Sentinel",
}
```

**`normalize_agent(raw)` 처리 순서**:
1. `AGENT_ROLE_MAP`에 그대로 있으면 반환
2. 소문자 → `AGENT_ALIASES` 조회 (`"kayo"` → `"KAY/O"`, `"iso"` → `"ISO"`)
3. `.title()` 시도 후 재확인
4. 없으면 `None` → 품질 게이트 탈락

---

### 2-2. 맵 목록 (12개)

| 맵 | 인코딩 | 특성 |
|----|--------|------|
| Ascent | 0 | 개방형 미드, 균형 |
| Bind | 1 | 텔레포터, 공격자 불리 |
| Haven | 2 | 사이트 3개, 수비자 불리 |
| Split | 3 | 수직 구조, Sentinel 유리 |
| Icebox | 4 | 좁은 통로, Sentinel 유리 |
| Breeze | 5 | 장거리 교전, Controller 유리 |
| Fracture | 6 | H자 구조, 공격자 양방향 진입 |
| Pearl | 7 | 해저 도시, 균형 |
| Lotus | 8 | 사이트 3개, Controller 유리 |
| Sunset | 9 | 좁은 골목, 균형 |
| Abyss | 10 | 절벽 추락 지형 |
| Drift | 11 | 2025년 신규 |

```python
MAP_ORDER: list[str] = [
    "Ascent", "Bind", "Haven", "Split", "Icebox", "Breeze",
    "Fracture", "Pearl", "Lotus", "Sunset", "Abyss", "Drift",
]
MAP_TO_INDEX: dict[str, int] = {m: i for i, m in enumerate(MAP_ORDER)}
```

**`normalize_map(raw)` 처리**: 정확한 이름 → 소문자 별칭 → `.title()` → `None`

---

### 2-3. 팀명 정규화 (`TEAM_NAME_ALIASES`)

**왜 팀명 정규화가 필요한가?**  
같은 팀이 소스마다 다르게 표기된다. `"T1"` / `"T1 Korea"` / `"Team One Korea"`가 모두 동일 팀이지만 dedup_key 생성 시 다른 팀으로 처리되면 동일 경기가 중복 제거되지 않고 학습에 두 번 들어간다. 파서가 팀명을 읽는 즉시 정규화한 뒤 dedup_key를 생성해야 한다.

```python
TEAM_NAME_ALIASES: dict[str, str] = {
    # key는 소문자 strip 후 조회
    "t1 korea":       "T1",
    "team one korea": "T1",
    "natus vincere":  "NAVI",
    "navi":           "NAVI",
    "fnatic":         "FNC",
    "cloud9":         "C9",
    # 파싱 실행 중 불일치 발견 시 추가
}

def normalize_team(raw: str) -> str:
    return TEAM_NAME_ALIASES.get(raw.strip().lower(), raw.strip())
```

`normalize_team()`은 파서 A~D 모두에서 `team_a`, `team_b` 값 확정 직후 호출.

---

## 3. 파서 구조

### 왜 소스마다 파서를 따로 만드는가?
ryanluong은 선수 스탯(`overview.csv`)과 팀 점수(`maps_scores.csv`)를 파일 2개로 분리했고, qualidea는 단일 파일에 모든 정보가 있으며, piyush는 이벤트 폴더 단위 구조다. 파서를 소스별로 분리하면 각 파일 구조에 최적화된 로직을 쓸 수 있고, 이후 품질 게이트·피처 생성 단계는 소스에 무관하게 동일한 인터페이스로 처리할 수 있다.

**파서 공통 출력 스키마**:

```python
{
    "source": str,          # 소스 식별자 (dedup 가중치 판단용)
    "match_key": str,       # 16자 SHA-1 (경기 단위 grouping)
    "dedup_key": str,       # 24자 SHA-1 (중복 제거 키)
    "date": str,            # YYYY-MM-DD (시간 가중치용)
    "event": str,
    "map": str,
    "team_a": str,
    "team_b": str,
    "players_a": list[dict],  # 5명 × {player, agent, acs, kd, kast, adr, fk, fd, assists}
    "players_b": list[dict],
    "score_a": int,
    "score_b": int,
    "atk_a": int | None,    # 공격 라운드 승리 수 (ryanluong만 보유)
    "def_a": int | None,
    "label": int,           # 1 = team_a 승, 0 = team_b 승
}
```

---

## 3. 소스별 컬럼 매핑

### 3-1. ryanluong 파서 (vct_2021_2023 + challengers)

**파일 구조**: `overview.csv` (선수 스탯) + `maps_scores.csv` (팀 점수) 분리 — **조인 필수**

```
overview.csv 컬럼             → 정규화 컬럼
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

maps_scores.csv 컬럼          → 정규화 컬럼
  Match Name + Map              → 조인 키
  Team A, Team B                → team_a, team_b
  Team A Score, Team B Score    → score_a, score_b → label
  Team A Attacker Score         → atk_a  (atk_side_advantage 집계 소스)
  Team A Defender Score         → def_a
```

**조인 키**: `Match Name` + `Map`.  
`vct_2021_2023`은 연도별 하위 폴더(`vct_2021/`~`vct_2026/`)에 동일 구조 반복 — 파서가 재귀 탐색.  
**KAST 가용성**: ✅

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

공수 분리 컬럼 (보강 시 활용 가능): `acs-t`, `acs-ct`, `kd-t`, `kd-ct`, `adr-t`, `adr-ct`  
**KAST 가용성**: ✅

---

### 3-3. piyush 파서

**파일**: 이벤트 폴더 내 `detailed_matches_player_stats.csv` — **조인 불필요**

```
player_name     → player
team, agent     → team, agent
acs, k, d, a    → acs, kills, deaths, assists
kast, adr       → kast, adr
hs_percent      → hs  (다른 소스의 hs%, HS%와 정규화 필요)
fk, fd          → fk, fd
map_winner      → 승팀 이름 → label
```

2024/2025 모두 `*_csvs` 하위 폴더 반복 — 파서가 재귀 탐색.  
**KAST 가용성**: ⚠️ 일부 이벤트 결측

---

### 3-4. ediashtarevin 파서

**파일**: `player_stats.csv` — **조인 불필요**

```
match_id, game_id          → match_key 재료
team / opponent            → team_a (win='win' 기준) / team_b
win_lose                   → label  ('win'→1, 'lose'→0)
map, player, agent         → map, player, agent
acs, kill, death, assist   → acs, kills, deaths, assists
kast%, adr, fk, fd         → kast, adr, fk, fd
```

**KAST 가용성**: ✅ (`kast%`)

---

### 3-5. kierru 파서

**파일**: `csv/stats.csv` — **조인 불필요**

`role_agent` 컬럼 직접 포함 → `AGENT_ROLE_MAP` 조회 없이 역할군 파싱 가능.  
**KAST 가용성**: ❓ 구현 시 컬럼 확인 필요.

---

## 4. 파이프라인 단계

### Phase 1 — 파싱

```
parse_ryanluong("data/raw/kaggle/vct_2021_2023")
parse_ryanluong("data/raw/kaggle/ryanluong1__*")
parse_qualidea ("data/raw/kaggle/qualidea1217__*")
parse_piyush   ("data/raw/kaggle/piyush86kumar__*2024*")
parse_piyush   ("data/raw/kaggle/piyush86kumar__*2025*")
parse_edia     ("data/raw/kaggle/ediashtarevin__*")
parse_kierru   ("data/raw/kaggle/kierru__*")
→ 공통 스키마 행 리스트로 병합
```

---

### Phase 2 — 정규화

**왜 정규화가 필요한가?**  
`KAY/O`를 `kayo`, `kay-o`, `KAY/O`로 각기 다르게 표기하면 역할군 매핑에서 `None`이 반환되어 품질 게이트에서 탈락한다. 컬럼명도 소스마다 달라 통일하지 않으면 하위 단계에서 참조 오류가 발생한다.

| 항목 | 처리 |
|------|------|
| 요원명 | `normalize_agent(raw)` — AGENT_ROLE_MAP → 소문자 별칭(AGENT_ALIASES) → `.title()` → None |
| 맵명 | `normalize_map(raw)` — MAP_ORDER → 별칭 → `.title()` → None |
| 컬럼명 | snake_case 통일 (`hs%`/`hs_percent`/`HS%` → `hs`) |
| KD 표기 | `kd_ratio`, `k:d`, `Kills - Deaths (KD)` → `kd` (float) |
| KAST 표기 | `kast%`, `Kill Assist Trade Survive %` → `kast` (float 0~1) |

---

### Phase 3 — 품질 게이트

아래 조건 중 하나라도 실패하면 해당 맵 행 **제외** → `reports/rejected_matches.csv`에 기록.

| 조건 | 기준 | 왜 |
|------|------|---|
| 팀당 요원 수 | 팀 A·B 각각 정확히 5명 | 5명 아니면 역할군 카운트 피처 부정확 |
| 요원 유효성 | 5명 모두 AGENT_ROLE_MAP에 존재 | 알 수 없는 요원 → 역할군 집계 불가 |
| 맵 유효성 | MAP_ORDER에 존재 | map_encoded / atk_side_advantage 집계 불가 |
| 레이블 유효성 | winner가 team_a 또는 team_b | 레이블 없으면 지도학습 불가 |
| 핵심 스탯 결측 | ACS·KD 각 선수 모두 비결측 | 핵심 선수 스탯 피처 생성 불가 |
| 소스 비중 | 단일 소스 < 학습셋 전체의 20% | 소스 편향 방지 |
| 승패 동점 | score_a ≠ score_b | 동점(overtime 등)은 레이블 불명확 |

---

### Phase 4 — dedup_key 중복 제거

**왜 중복이 발생하는가?**  
qualidea와 vct_2021_2023이 같은 VCT 경기를 각자 수록하면 동일 경기가 두 번 학습되어 모델이 그 경기에 과적합된다.

```python
import hashlib

def make_dedup_key(date, event, map_, team_a, team_b, agents_a, agents_b, score_a, score_b):
    canonical = "|".join([
        str(date), event.lower().strip(), map_.lower(),
        team_a.lower(), team_b.lower(),
        ",".join(sorted(agents_a)), ",".join(sorted(agents_b)),
        str(score_a), str(score_b)
    ])
    return hashlib.sha1(canonical.encode()).hexdigest()[:24]

def make_match_key(date, event, team_a, team_b):
    canonical = "|".join([str(date), event.lower(), team_a.lower(), team_b.lower()])
    return hashlib.sha1(canonical.encode()).hexdigest()[:16]
```

동일 dedup_key 중 소스 가중치가 가장 높은 행만 보존. 동점이면 컬럼 수가 더 많은 행 보존.

---

### Phase 5 — 데이터 분할

#### 기본 분할: match_key 단위 랜덤 70/15/15

**왜 match_key 단위인가?**  
한 경기는 맵 2~3개로 구성된다. 맵 1이 train에, 맵 2가 val에 들어가면 "같은 경기"라는 정보가 모델에 간접 누수된다. match_key 단위로 경기 전체를 한 분할에 몰아야 누수가 없다.

```python
from sklearn.model_selection import GroupShuffleSplit

splitter = GroupShuffleSplit(n_splits=1, test_size=0.30, random_state=42)
train_idx, temp_idx = next(splitter.split(df, groups=df["match_key"]))

splitter2 = GroupShuffleSplit(n_splits=1, test_size=0.50, random_state=42)
val_idx, test_idx = next(splitter2.split(df.iloc[temp_idx], groups=df.iloc[temp_idx]["match_key"]))
```

비율: **train 70% / val 15% / test 15%** — test는 최종 평가에만 한 번 사용.

#### 시간 기반 분할 (선택적 검증 실험)

**언제 사용하는가?**  
랜덤 분할 성능이 나온 후, "이 모델이 실제로 미래 경기를 잘 예측하는가?"를 별도로 검증할 때 사용한다.

```
train : 2021-01 ~ 2023-12
test  : 2024-01 ~ 2025-현재
```

랜덤 분할보다 Accuracy가 크게 낮으면 메타 시프트 영향이 크다는 신호 → 시간 가중치 강도 조정.

---

## 5. 과적합 리스크 및 완화 전략

### 5-1. 데이터 누수 (가장 위험)

| 리스크 | 원인 | 완화 |
|--------|------|------|
| 경기 누수 | 같은 경기 맵이 train/val에 분산 | match_key 단위 GroupShuffleSplit |
| 피처 누수 | agent_map_wr 집계 시 val/test 포함 | **train.csv만으로 사전 집계** |
| 선수 경험 누수 | Team_Agent_Experience 집계 시 미래 경기 포함 | train 기준 집계 후 val/test에 join |

---

### 5-2. 메타 시프트 처리 (시간 가중치)

**왜 시간 가중치인가?**  
2021년 초기 메타와 2025년 메타(Tejo·Waylay 추가, 경제 패치)는 완전히 다르다. 구식 데이터를 버리면 학습량이 줄고, 동등 가중치로 두면 구식 패턴에 과도하게 의존한다. 시간 가중치는 데이터를 유지하면서 영향도만 낮추는 절충안이다.

```python
def get_time_weight(date_str: str) -> float:
    year = int(date_str[:4])
    if year <= 2022:  return 0.6   # 구식 메타
    elif year == 2023: return 0.8  # 전환기
    else:              return 1.2  # 현재 메타 (2024~)
```

최종 `sample_weight = time_weight × source_weight` — `model.fit(..., sample_weight=weights)`에 적용.

---

### 5-3. 소스 편향 (vct_2021_2023 과다)

vct_2021_2023이 학습셋의 ~60%를 차지하면 북미/유럽 초기 메타를 과학습할 수 있다.  
Phase 3 Gate "소스 비중 < 20%" → 초과 시 해당 소스 under-sampling.

---

### 5-4. 팀명 표기 불일치 (dedup 누락 위험)

**문제**: 같은 팀이 소스마다 `"T1"` / `"T1 Korea"` / `"Team One Korea"`로 달리 표기되면 dedup_key가 달라져 동일 경기가 중복 제거되지 않는다. 이 경우 같은 경기가 두 소스에서 각각 학습에 투입되어 해당 경기 패턴에 과적합된다.

**완화**: 파서 A~D 모두에서 팀명 확정 직후 `normalize_team()` 호출 (`TEAM_NAME_ALIASES`, 섹션 2-3). 파싱 실행 중 불일치 발견 시 aliases 딕셔너리 보완.

---

## 6. KAST 결측 처리

소스별 가용성:

| 소스 | KAST |
|------|------|
| vct_2021_2023 | ✅ |
| ryanluong challengers | ✅ |
| qualidea | ✅ |
| piyush 2024/2025 | ⚠️ 일부 이벤트 결측 |
| ediashtarevin | ✅ |
| kierru | ❓ 확인 필요 |

**처리 원칙**:
1. **행 레벨 결측** (특정 선수만): 동일 경기 팀 평균으로 imputation.
2. **이벤트 전체 결측** (piyush 일부): `a_avg_kast`/`b_avg_kast`를 `-1` 플래그로 채워 모델이 "KAST 없음" 패턴 학습 가능하게 함.
3. **피처 제외 기준**: KAST 결측 행이 전체 학습셋의 20% 초과 시 해당 피처 제외 후 재실험.

---

## 7. 피처 엔지니어링

### 7-0. 피처 카테고리 개요

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

### 7-1. 역할군 카운트 피처 (12개)

**왜 27개 요원을 그대로 쓰지 않고 역할군으로 묶는가?**  
요원 27종을 각각 피처로 만들면 모델이 "Jett가 있으면 이긴다"처럼 특정 요원에 과도하게 의존하는 패턴을 학습한다. 역할군으로 묶으면 "Duelist 2명"이라는 구조적 의미만 남아서 메타가 바뀌어도 모델이 더 안정적으로 작동한다.

**왜 차이(diff) 피처도 함께 쓰는가?**  
팀 A Controller 1명 / 팀 B Controller 0명이면 팀 A가 유리하다. 절대적인 수보다 두 팀의 상대적 차이가 승패에 영향을 준다.

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

### 7-2. 역할군 파생 피처 (4개)

**왜 Controller 보유 여부를 별도 피처로 만드는가?**  
Controller가 0명이면 스모크 없이 사이트 진입 — 수비팀이 모든 각도에서 쏠 수 있어 진입이 거의 불가능하다. "있음/없음" 자체가 전략적으로 결정적 차이이므로 카운트 피처와 별개로 이진 피처를 추가한다.

**왜 더블 Duelist 여부를 별도 피처로 만드는가?**  
Duelist 2명 이상 조합은 교전력 극대화 vs 유틸 부족이라는 특정 패턴이다. 2명과 3명의 차이보다 2명 이상인지 아닌지의 전략적 의미가 더 뚜렷하다.

| 피처명 | 타입 | 조건 |
|--------|------|------|
| `has_controller_a` | 0/1 | 팀 A Controller ≥ 1 |
| `has_controller_b` | 0/1 | 팀 B Controller ≥ 1 |
| `is_double_duelist_a` | 0/1 | 팀 A Duelist ≥ 2 |
| `is_double_duelist_b` | 0/1 | 팀 B Duelist ≥ 2 |

---

### 7-3. 선수 스탯 피처 (12개)

팀 5명의 개인 스탯을 집계한 팀 단위 피처.

- **ACS**: 킬의 질·피해량·클러치까지 반영한 종합 전투 기여도. 킬만 보면 구별 안 되는 "잘 잡는 선수"와 "팀에 기여하는 선수"를 구분할 수 있다.
- **K/D**: 교환 효율. 1보다 크면 죽는 것보다 많이 잡아 수적 우위를 자주 만든다.
- **KAST%**: 킬 못 해도 어시스트·생존·트레이드로 팀에 기여한 라운드 비율. K/D가 보지 못하는 팀 기여를 보완한다.
- **ADR**: 킬 못 한 라운드에서도 피해를 줘 다음 플레이어의 킬 기회를 만드는 지표.
- **클러치율 max**: 1대多 상황에서 라운드를 이긴 비율. 팀 평균이 아닌 최고값을 쓰는 이유는, "가장 믿을 수 있는 1명이 있느냐"가 중요하기 때문이다.
- **HS% (헤드샷률)**: 헤드샷은 TTK(Time to Kill)를 대폭 줄여 교환 효율을 높인다. KD가 같아도 헤드샷 비율이 높은 팀은 더 적은 리소스로 처치한다는 의미다. ACS·KD와 함께 팀 전투력을 다각도로 수치화하는 교전 "정확도" 지표. 소스별 컬럼명은 `hs%`/`hs_percent`/`HS%`로 달라 정규화 필요.

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

### 7-4. 시너지 피처 (6개)

**왜 개인 스탯 외에 시너지 피처가 필요한가?**  
개인 스탯이 높아도 팀으로서 맞물리지 않으면 지는 경기가 많다. 시너지 피처는 "팀이 함께 얼마나 잘 작동하는가"를 수치로 나타낸다.

- **fk_fd_ratio**: 먼저 잡은 팀이 5v4 수적 우위를 만든다. 이 비율이 높으면 진입 전략과 스킬 연계가 잘 작동한다는 신호.
- **avg_assists**: 어시스트가 많을수록 선수들이 스킬을 팀에 맞춰 쓴다는 뜻 — 역할군 조합이 실제로 "맞물리고 있는가"의 지표.
- **KAST 표준편차**: 평균 KAST가 같아도 팀원 한 명의 KAST가 현저히 낮으면 상대가 그 선수를 집중 공략한다. 표준편차가 낮을수록 균형 잡힌 팀, 높을수록 특정 선수에 의존하는 팀. "약한 고리" 유무를 포착하는 지표다.
- **Team_Shared_Exp**: 같은 팀으로 오래 뛴 선수들은 서로 움직임을 예측하고 더 잘 협력한다. **`visualize25` 데이터셋 보류로 현재 미구현 — 이후 재검토.**

| 피처명 | 계산식 | 소스 |
|--------|--------|------|
| `a_fk_fd_ratio` | sum(fk_a) / sum(fd_a) | overview.csv |
| `b_fk_fd_ratio` | sum(fk_b) / sum(fd_b) | overview.csv |
| `a_avg_assists` | mean(assists_a) | overview.csv |
| `b_avg_assists` | mean(assists_b) | overview.csv |
| `a_kast_std` | std(kast_a) | 전 소스 |
| `b_kast_std` | std(kast_b) | 전 소스 |

---

### 7-5. 요원 조합 피처 (6개)

**왜 요원×맵 승률이 필요한가?**  
역할군 카운트만으로는 "Jett가 Ascent에서 특히 강하다"는 맵별 특성을 반영하지 못한다. 요원×맵 승률을 쓰면 "이 맵에서 이 요원들이 역사적으로 얼마나 이겼는가"라는 실적 기반 정보를 피처에 담을 수 있다.

**왜 픽률도 함께 쓰는가?**  
픽률이 높을수록 프로들이 해당 맵에서 검증한 요원이라는 의미다 — 메타 적합성 신호.

**왜 선수-요원 경험치가 필요한가?**  
아무리 강한 요원도 처음 쓰는 선수가 들면 기대 성능이 안 나온다. 경험치는 "좋은 요원을 숙련된 선수가 드는가"를 수치화한다.

| 피처명 | 계산식 | 설명 |
|--------|--------|------|
| `a_avg_agent_map_wr` | mean(각 요원의 해당 맵 승률) | 팀 A 5요원의 해당 맵 평균 승률 |
| `b_avg_agent_map_wr` | 동일 | 팀 B |
| `a_avg_agent_pick_rate` | mean(각 요원의 해당 맵 픽률) | 팀 A 메타 적합성 |
| `b_avg_agent_pick_rate` | 동일 | 팀 B |
| `a_avg_agent_exp` | mean(각 선수의 해당 요원 과거 플레이 횟수) | 팀 A 선수-요원 숙련도 |
| `b_avg_agent_exp` | 동일 | 팀 B |

**사전 집계 방법** (train.csv 기준, val/test 누수 방지):
```python
agent_map_stats[agent][map] = {
    "wins":     count(label == 1),
    "total":    count(*),
    "winrate":  wins / total,
    "pickrate": total / total_matches_on_map,
}
# (player, agent) 등장 횟수 → agent_experience[player][agent]
```

---

### 7-6. 맵 피처 (3개)

**왜 맵 피처가 세 개인가?**  
맵이 달라지면 강한 요원도, 유리한 공수 사이드도 완전히 바뀐다. 맵 정보 없이 학습하면 모든 맵을 동일한 조건으로 처리한다.

- **map_encoded**: 문자열을 숫자 인덱스로 변환해야 트리 모델이 분기 조건으로 사용할 수 있다.
- **atk_side_advantage**: 맵마다 공격·수비 중 어느 쪽이 구조적으로 유리한지를 전체 데이터 집계로 수치화. 집계 소스: ryanluong challengers `maps_scores.csv`의 `Attacker Score`/`Defender Score`.
- **is_attacker_a**: `atk_side_advantage`가 맵 수준 정보라면 이건 경기 수준 정보. 두 피처를 함께 쓰면 "공격이 유리한 맵에서 팀 A가 공격으로 시작했을 때"라는 조합 패턴을 모델이 학습할 수 있다.

| 피처명 | 타입 | 계산식 |
|--------|------|--------|
| `map_encoded` | int | `MAP_TO_INDEX[map]` (0~11) |
| `atk_side_advantage` | float | global_atk_wins / global_total (train 기준 집계) |
| `is_attacker_a` | 0/1 | 사용자 입력 (선공/후공) |

---

### 7-7. 레이블

| 피처명 | 타입 | 값 |
|--------|------|-----|
| `label` | int | 1 = 팀 A 승, 0 = 팀 B 승 |

---

### 7-8. 최종 피처 목록 (학습 입력)

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

레이블 (1):  label
```

**총 43개 피처 + 1개 레이블**  
Team_Shared_Exp(시너지, 동반 출전 횟수)는 visualize25 데이터셋 보류로 미구현 — 추가 시 44개.

---

## 8. A/B Swap 증강 (train 한정)

**왜 swap이 필요한가?**  
파일에 먼저 기록된 팀이 항상 "team_a"가 되므로, swap 없이 학습하면 모델이 "team_a 위치에 있는 팀이 더 자주 이긴다"는 허위 패턴을 학습할 수 있다. 동일 경기를 팀 B 시점으로 뒤집은 행을 추가하면 모델은 피처 내용(스탯, 역할군)으로만 승패를 판단하도록 학습된다.

```
원본: team_a=T1, team_b=FNC, label=1
swap: team_a=FNC, team_b=T1, label=0  ← train에만 추가
```

val/test 미적용 — 평가는 실제 경기 그대로의 행만 사용.  
`--no-augment-train` 플래그로 비활성화 가능.

---

## 9. 피처 사전 집계 순서 (누수 방지)

```
Step 1. 파싱 → 정규화 → 품질 게이트 → dedup → matches_clean.csv
Step 2. matches_clean.csv에서 train/val/test 분할
Step 3. train.csv만 사용해서:
          - atk_side_advantage (맵별 공격 측 전역 승률)
          - agent_map_stats    (요원×맵 승률·픽률)
          - agent_experience   (선수×요원 등장 횟수)
Step 4. train/val/test 각각에 집계값 join
          신규 조합 → winrate: 0.5(중립), experience: 0
Step 5. A/B swap으로 train 행 수 2× 증강
Step 6. sample_weight = time_weight × source_weight 계산
Step 7. features_base.csv 저장
```

---

## 10. 결측치 처리

**왜 결측치마다 처리 방식이 다른가?**  
"데이터가 없어서" 결측인 경우와 "해당 상황이 0번 발생해서" 결측인 경우는 의미가 다르다. 원인에 맞는 방식으로 처리해야 모델에 잘못된 신호를 주지 않는다.

| 피처 | 처리 | 이유 |
|------|------|------|
| `kast` 결측 | 팀 평균 imputation 또는 -1 플래그 | 팀 평균 대체 = "팀과 비슷한 기여" 중립 가정. -1 플래그는 결측 여부 자체를 모델이 학습 가능하게 함 |
| `clutch_%` 결측 | 0으로 대체 | 클러치 기록 없음 = 실제 기여 없음. 팀 평균으로 대체하면 과대평가 |
| `agent_map_wr` 집계 불가 | 0.5(중립) 대체 | 0이면 "무조건 진다", 1이면 반대. 0.5 = "데이터 없음 = 유불리 불명" |
| `fk_fd_ratio` FD=0 | 1.0 대체 | FD=0 팀은 한 번도 먼저 죽지 않음 — 사실상 매우 유리한 팀이므로 극단값 대신 균형값(1.0) 사용 |
| `agent_experience` 신규 | 0으로 대체 | 경험 없음 = 0회 플레이와 동일 |

---

## 11. 스케일링 전략

**왜 트리 기반 모델은 스케일링이 필요 없는가?**  
RF/XGBoost/LightGBM은 "이 값이 X보다 크냐/작냐"로 데이터를 나눈다. 이 분기 방식은 절대적인 숫자 크기가 아닌 상대적 순서(rank)에만 의존하므로, ACS(0~400)와 K/D(0~5)를 그대로 넣어도 분기 결과가 동일하다.

| 모델 | 스케일링 |
|------|----------|
| Random Forest | 불필요 |
| XGBoost | 불필요 |
| LightGBM | 불필요 |
| Logistic Regression (baseline 비교용) | StandardScaler 필수 |

---

## 12. 피처 중요도 검증 계획

**왜 이 순서인가?**  
비용이 낮은 방법으로 먼저 스크리닝하고, 신뢰도가 높은 방법으로 마지막에 확인하는 순서다.

1. **RF feature_importances_** — 훈련 직후 무료. 불순도 기반이라 편향이 있지만 빠른 전체 윤곽에 적합.
2. **XGBoost gain/cover** — gain은 분기 시 오류 감소량, cover는 영향 샘플 수. RF와 비교해 일관성 확인.
3. **Permutation importance** — 피처를 섞었을 때 성능 하락량. 실제 예측 기여를 직접 측정하므로 1~2보다 신뢰도 높음.
4. **Ablation study** — 카테고리 단위(역할군만 / 스탯만 / 시너지만) 제거 실험. 재훈련 필요 → 앞 단계에서 중요하다고 확인된 카테고리만 대상.

---

## 13. 최적 조합 탐색 방법

**왜 후처리 탐색인가?**  
모델은 "주어진 조합이 이길 확률"을 출력하도록 학습되어 있다. 강화학습·유전 알고리즘 같은 생성형 접근은 별도 시스템이 필요해 구현 비용이 크다. 후처리 탐색은 학습된 모델을 그대로 사용해 가능한 조합들을 스코어링하므로 즉시 구현 가능하다. 요원 27종에서 5종 선택 = 80,730가지 — 수 초 내 완료 가능한 범위.

### 맵별 최적 요원 조합

```python
for agents in combinations(AGENT_POOL, 5):
    features = build_features(agents, map_name, player_stats)
    score = model.predict_proba(features)[0][1]  # 팀 A 승률
    results.append((agents, score))

top_N = sorted(results, key=lambda x: x[1], reverse=True)[:N]
```

### 최정예 로스터

```python
for players in combinations(player_pool, 5):
    avg_stats = compute_team_stats(players)
    features = build_features(avg_stats)
    score = model.predict_proba(features)[0][1]

best_roster = max(results, key=lambda x: x[1])
```

### 키 플레이어 식별

```python
base_score = model.predict_proba(team_features)[0][1]
for player in team:
    drop_features = build_features(team - {player})
    drop_score = model.predict_proba(drop_features)[0][1]
    contribution[player] = base_score - drop_score

key_player = max(contribution, key=contribution.get)
```

---

## 14. 출력 파일

> 모두 로컬 생성, git 제외 (`.gitignore`에 포함)

| 경로 | 내용 |
|------|------|
| `data/processed/matches_clean.csv` | 품질 게이트·dedup 통과한 맵 행 전체 |
| `data/processed/features_base.csv` | 피처 테이블 (레이블 포함) |
| `data/processed/train.csv` | 학습셋 (A/B swap 증강 포함) |
| `data/processed/val.csv` | 검증셋 |
| `data/processed/test.csv` | 테스트셋 (최종 평가 전용) |
| `reports/preprocess_summary.json` | 소스별 행수·제거율·최종 분포 등 실행 통계 |
| `reports/rejected_matches.csv` | 품질 게이트 탈락 행 및 탈락 사유 |

---

## 15. 구현 진입점

```bash
# 전체 실행
python -m ml.data_pipeline \
  --input data/raw/kaggle \
  --output data/processed \
  --reports reports

# dry-run (원본 무수정)
python -m ml.data_pipeline \
  --input data/raw/kaggle \
  --output /tmp/valo_out \
  --reports /tmp/valo_reports

# A/B swap 증강 비활성화
python -m ml.data_pipeline ... --no-augment-train
```

모듈 구조:
```
ml/
  agent_roles.py       # AGENT_ROLE_MAP, MAP_ORDER, normalize_agent(), normalize_map()
  data_pipeline.py     # 전처리 파이프라인 진입점
  parsers/
    ryanluong.py       # vct_2021_2023 + challengers
    qualidea.py
    piyush.py          # 2024/2025
    ediashtarevin.py
    kierru.py
```

---

## 16. 예상 성능 및 한계

| 지표 | 범위 | 조건 |
|------|------|------|
| Accuracy (랜덤 분할) | 58~65% | 43개 피처, 80K 맵 행 |
| Accuracy (시간 분할) | 55~62% | 메타 시프트 반영 |
| ROC-AUC | 0.62~0.68 | RF/XGB/LGB 앙상블 |

**구조적 한계**:
- 프리매치 예측이므로 인게임 실력 발현(컨디션, 순간 판단)을 피처로 잡을 수 없음
- **선수 이적 후 스탯 구식화**: 이적 이전 팀 소속 스탯이 이적 후에도 같은 선수 이름으로 연결됨 → 시간 가중치(2024+ 1.2)로 구식 스탯 영향을 줄이고, Streamlit UI에서 사용자가 최신 스탯 직접 입력 가능. 이적 날짜를 데이터에서 추적하는 것은 불가능하므로 이 한계는 명시적으로 고지한다.
- Team_Shared_Exp 미구현 (visualize25 보류) → 팀 시너지 일부 손실
- KAST 결측 행이 많으면 KAST 피처 제외 필요

---

## 17. 주의사항

| 항목 | 내용 |
|------|------|
| vct_2021_2023 하위 폴더 | `vct_2021/`~`vct_2026/` 재귀 탐색, `all_ids/` 건너뜀 |
| piyush 이벤트 폴더 | `*_csvs` 패턴 재귀, 중복 이벤트는 dedup_key로 자동 처리 |
| kierru role_agent | AGENT_ROLE_MAP 없이 역할군 파싱 가능 — 이름 정규화 확인 필요 |
| 팀명 정규화 | `normalize_team()` 미적용 시 동일 팀이 다른 팀으로 처리돼 dedup 누락 — `TEAM_NAME_ALIASES` 지속 보완 필요 (섹션 2-3) |
| HS% 컬럼명 | 소스마다 `hs` / `hs_percent` / `HS%`로 달라 파서 내 정규화 필수 |
| 데이터 불균형 | 승/패 비율 집계 후 불균형 시 `class_weight='balanced'` 적용 |
| test.csv | K-Fold 전 과정에서 **열람 금지** — 최종 보고 단계에만 1회 사용 |
