# 04. 데이터 로드 및 전처리 전략

마지막 업데이트: 2026-05-05

> **구현 완료** — `ml/data_pipeline.py` 전체 파이프라인 구현 완료.
> 실행 결과: clean 66,485행 → train 93,078행(A/B swap 증강) / val 9,973행 / test 9,973행.

## 1. 전처리 파이프라인 개요

```
[수집] → [파싱] → [정규화] → [품질 게이트] → [dedup] → [분할] → [피처 집계] → [피처 생성] → [증강] → [저장]
```

외부 API 미사용 — Kaggle CSV 7개만 사용한다. 전처리는 `ml/data_pipeline.py`와 `ml/parsers/*.py`로 처리한다.

---

## 2. 데이터 수집

### 2.1 Kaggle 7개 데이터셋 다운로드

```python
# dataload.py
import kagglehub

DATASETS = [
    ("ryanluong1/valorant-champion-tour-2021-2023-data",
     "data/raw/kaggle/vct_2021_2023"),
    ("ryanluong1/valorant-challengers-league-data",
     "data/raw/kaggle/ryanluong1__valorant-challengers-league-data"),
    ("qualidea1217/valorant-pro-matches-since-april-2021",
     "data/raw/kaggle/qualidea1217__valorant-pro-matches-since-april-2021"),
    ("ediashtarevin/vct-champions-2023-stats",
     "data/raw/kaggle/ediashtarevin__vct-champions-2023-stats"),
]
```

실행:
```bash
source .venv/bin/activate
python dataload.py
```

`~/.kaggle/kaggle.json` 필요. API 키나 raw CSV는 절대 커밋 금지.

---

## 3. 소스별 파서

소스마다 파일 구조가 달라 파서를 소스별로 분리한다. 파서 공통 출력 스키마:

```python
{
    "source": str,           # 소스 식별자
    "match_key": str,        # 16자 SHA-1 (경기 단위 grouping)
    "dedup_key": str,        # 24자 SHA-1 (중복 제거 키)
    "date": str,             # YYYY-MM-DD
    "event": str,
    "map": str,
    "team_a": str,
    "team_b": str,
    "players_a": list[dict], # 5명 x {player, agent, acs, kd, kast, adr, fk, fd, assists}
    "players_b": list[dict],
    "score_a": int,
    "score_b": int,
    "atk_a": int | None,
    "def_a": int | None,
    "label": int,            # 1 = team_a 승, 0 = team_b 승
}
```

| 파서 | 소스 | 조인 필요 |
|------|------|----------|
| ryanluong | vct_2021_2023, challengers | 필요 (Match Name + Map) |
| qualidea | qualidea1217 | 불필요 |
| ediashtarevin | ediashtarevin | 불필요 |

---

## 4. 정규화

```python
from ml.agent_roles import normalize_agent, normalize_map, normalize_team

# 파서 내 팀명 확정 직후
team_a = normalize_team(raw_team_a)
team_b = normalize_team(raw_team_b)

# 요원·맵 정규화
agent = normalize_agent(raw_agent)   # None이면 품질 게이트 탈락
map_  = normalize_map(raw_map)       # None이면 품질 게이트 탈락
```

컬럼명 통일: `hs%` / `hs_percent` / `HS%` → `hs`, `kast%` / `Kill Assist Trade Survive %` → `kast`.

---

## 5. 품질 게이트

| 조건 | 기준 |
|------|------|
| 팀당 요원 수 | 팀 A·B 각각 정확히 5명 |
| 요원 유효성 | AGENT_ROLE_MAP에 모두 존재 |
| 맵 유효성 | MAP_ORDER 12개에 존재 |
| 레이블 유효성 | winner가 team_a 또는 team_b |
| 핵심 스탯 결측 | ACS·KD 비결측 |
| 소스 비중 | 단일 소스 < 전체의 20% |
| 동점 | score_a != score_b |

탈락 행 → `reports/rejected_matches.csv`.

---

## 6. dedup_key 중복 제거

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
```

소스 가중치:

| 소스 | 가중치 |
|------|--------|
| ryanluong challengers | 1.8 |
| vct_2021_2023 | 1.0 |
| qualidea | 1.0 |
| ediashtarevin | 0.9 |

동일 dedup_key 중 소스 가중치가 가장 높은 행 보존. 동점 시 컬럼 수 많은 행 보존.

---

## 7. 데이터 분할

match_key 단위 GroupShuffleSplit (seed=42) — 구현 완료:

```python
from sklearn.model_selection import GroupShuffleSplit

splitter = GroupShuffleSplit(n_splits=1, test_size=0.30, random_state=42)
train_idx, temp_idx = next(splitter.split(df, groups=df["match_key"]))

splitter2 = GroupShuffleSplit(n_splits=1, test_size=0.50, random_state=42)
val_idx, test_idx = next(
    splitter2.split(df.iloc[temp_idx], groups=df.iloc[temp_idx]["match_key"])
)
```

비율: train 70% / val 15% / test 15%.

---

## 8. 피처 엔지니어링

### 8.1 피처 카테고리 (43개 + 1 레이블)

| 카테고리 | 피처 수 |
|----------|---------|
| 역할군 카운트 (a/b 각 4 + diff 4) | 12 |
| 역할군 파생 (has_controller, is_double_duelist) | 4 |
| 선수 스탯 (acs/kd/kast/adr/clutch/hs, 팀당) | 12 |
| 시너지 (fk_fd_ratio/assists/kast_std, 팀당) | 6 |
| 요원 조합 (agent_map_wr/pick_rate/exp, 팀당) | 6 |
| 맵 (map_encoded/atk_side_advantage/is_attacker_a) | 3 |
| 레이블 | 1 |

### 8.2 피처 생성 함수 스켈레톤

```python
from ml.agent_roles import AGENT_ROLE_MAP, MAP_TO_INDEX

def build_features(row: dict, agent_map_stats: dict, agent_exp: dict) -> dict:
    agents_a = [p["agent"] for p in row["players_a"]]
    agents_b = [p["agent"] for p in row["players_b"]]

    # 역할군 카운트
    def count_roles(agents):
        counts = {"Duelist": 0, "Initiator": 0, "Controller": 0, "Sentinel": 0}
        for a in agents:
            role = AGENT_ROLE_MAP.get(a)
            if role:
                counts[role] += 1
        return counts

    a_cnt = count_roles(agents_a)
    b_cnt = count_roles(agents_b)

    feats = {}
    for role in ["Duelist", "Initiator", "Controller", "Sentinel"]:
        r = role.lower()
        feats[f"a_{r}"] = a_cnt[role]
        feats[f"b_{r}"] = b_cnt[role]
        feats[f"diff_{r}"] = a_cnt[role] - b_cnt[role]

    feats["has_controller_a"] = int(a_cnt["Controller"] >= 1)
    feats["has_controller_b"] = int(b_cnt["Controller"] >= 1)
    feats["is_double_duelist_a"] = int(a_cnt["Duelist"] >= 2)
    feats["is_double_duelist_b"] = int(b_cnt["Duelist"] >= 2)

    # 선수 스탯 (train split 후 집계 없이 직접 계산)
    def mean_stat(players, key):
        vals = [p[key] for p in players if p.get(key) is not None]
        return sum(vals) / len(vals) if vals else None

    feats["a_avg_acs"]  = mean_stat(row["players_a"], "acs")
    feats["b_avg_acs"]  = mean_stat(row["players_b"], "acs")
    feats["a_avg_kd"]   = mean_stat(row["players_a"], "kd")
    feats["b_avg_kd"]   = mean_stat(row["players_b"], "kd")
    # ... 나머지 스탯 동일 패턴

    # 맵
    feats["map_encoded"] = MAP_TO_INDEX.get(row["map"], 0)
    feats["label"] = row["label"]

    return feats
```

### 8.3 피처 사전 집계 (누수 방지)

```
Step 1. matches_clean.csv → train/val/test 분할
Step 2. train.csv만으로:
          atk_side_advantage, agent_map_stats, agent_experience 집계
Step 3. train/val/test 각각에 join
          신규 조합: winrate=0.5, experience=0
Step 4. A/B swap 증강 (train 전용)
Step 5. sample_weight = time_weight x source_weight
Step 6. features_base.csv 저장
```

### 8.4 sample_weight

```python
def get_time_weight(date_str: str) -> float:
    year = int(date_str[:4])
    if year <= 2022:   return 0.6
    elif year == 2023: return 0.8
    else:              return 1.2  # 2024+

SOURCE_WEIGHT = {
    "ryanluong_challengers": 1.8,
    "vct_2021_2023": 1.0, "qualidea": 1.0,
    "ediashtarevin": 0.9,
}

sample_weight = get_time_weight(row["date"]) * SOURCE_WEIGHT[row["source"]]
```

---

## 9. 전체 파이프라인 실행

```python
# ml/data_pipeline.py 메인 실행 흐름
if __name__ == "__main__":
    # 1. 파싱 (5종 파서)
    rows = []
    rows += parse_ryanluong("data/raw/kaggle/vct_2021_2023")
    rows += parse_ryanluong("data/raw/kaggle/ryanluong1__valorant-challengers-league-data")
    rows += parse_qualidea ("data/raw/kaggle/qualidea1217__valorant-pro-matches-since-april-2021")
    rows += parse_edia     ("data/raw/kaggle/ediashtarevin__vct-champions-2023-stats")

    # 2. 정규화
    rows = [normalize_row(r) for r in rows]

    # 3. 품질 게이트
    rows, rejected = quality_gate_all(rows)
    save_rejected(rejected, "reports/rejected_matches.csv")

    # 4. dedup
    rows = dedup_rows(rows)
    save_clean(rows, "data/processed/matches_clean.csv")

    # 5. 분할 (match_key 단위 GroupShuffleSplit)
    train_rows, val_rows, test_rows = split_rows(rows, seed=42)

    # 6. 피처 사전 집계 (train 기준)
    agent_map_stats = compute_agent_map_stats(train_rows)
    agent_exp       = compute_agent_experience(train_rows)
    atk_advantage   = compute_atk_side_advantage(train_rows)

    # 7. 피처 생성
    train_df = build_features_df(train_rows, agent_map_stats, agent_exp, atk_advantage)
    val_df   = build_features_df(val_rows,   agent_map_stats, agent_exp, atk_advantage)
    test_df  = build_features_df(test_rows,  agent_map_stats, agent_exp, atk_advantage)

    # 8. A/B swap 증강 (train 전용)
    train_df = augment_swap(train_df)

    # 9. 저장
    train_df.to_csv("data/processed/train.csv", index=False)
    val_df.to_csv("data/processed/val.csv",     index=False)
    test_df.to_csv("data/processed/test.csv",   index=False)
```

---

## 10. 데이터 품질 검증 체크리스트

| 체크 항목 | 확인 방법 | 기준 | 실측 결과 |
|----------|----------|------|----------|
| 맵 행 총수 (dedup 후) | `len(matches_clean)` | — | 66,485행 |
| train (A/B swap 증강 후) | `len(train)` | — | 93,078행 |
| val | `len(val)` | — | 9,973행 |
| test | `len(test)` | — | 9,973행 |
| 클래스 균형 (test) | `df["label"].mean()` | 0.45~0.55 | 0.569 (imbalance_ratio 1.32) |
| 결측값 없음 | `df.isnull().sum()` | 모든 피처 0 | 통과 |
| 역할군 합계 | `a_duelist+...+a_sentinel` | 각 팀 = 5 | 통과 |
| match_key 누수 없음 | train/val/test 교집합 | 0 | 통과 |
| 피처 수 | `len(feature_cols)` | 43 | FEATURE_COLS_P1(19) + FEATURE_COLS_P2(24) = 43 |
| 중복 dedup_key | `dedup_key.duplicated().sum()` | 0 | 통과 |

---

## 11. 전처리 출력 파일

| 경로 | 내용 |
|------|------|
| `data/processed/matches_clean.csv` | 품질 게이트·dedup 통과한 맵 행 전체 |
| `data/processed/features_base.csv` | 피처 테이블 (레이블 포함) |
| `data/processed/train.csv` | 학습셋 (A/B swap 증강 포함) |
| `data/processed/val.csv` | 검증셋 |
| `data/processed/test.csv` | 테스트셋 (최종 평가 전용) |
| `reports/preprocess_summary.json` | 소스별 행수·제거율·최종 분포 등 실행 통계 |
| `reports/rejected_matches.csv` | 품질 게이트 탈락 행 및 탈락 사유 |

모두 로컬 생성, git 제외 (`.gitignore`에 포함).
