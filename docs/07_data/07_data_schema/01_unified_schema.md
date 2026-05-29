# 01. 통합 데이터 스키마

마지막 업데이트: 2026-05-04

## 1. 파서 공통 출력 스키마

모든 소스(ryanluong·qualidea·ediashtarevin, ~~piyush~~(제거됨), ~~kierru~~(제거됨))의 파서는 아래 공통 스키마의 행 리스트를 반환한다. kierru는 리젝션율 80%로 파이프라인에서 제거됨. piyush는 파이프라인에서 제거됨.

```python
{
    "source":     str,            # 소스 식별자 (dedup 가중치 판단용)
    "match_key":  str,            # 16자 SHA-1 (경기 단위 grouping, train/val/test 분할)
    "dedup_key":  str,            # 24자 SHA-1 (중복 제거 키)
    "date":       str,            # YYYY-MM-DD (시간 가중치용)
    "event":      str,
    "map":        str,
    "team_a":     str,
    "team_b":     str,
    "players_a":  list[dict],     # 5명 × {player, agent, acs, kd, kast, adr, fk, fd, assists}
    "players_b":  list[dict],
    "score_a":    int,
    "score_b":    int,
    "atk_a":      int | None,     # 공격 라운드 승리 수 (ryanluong만 보유)
    "def_a":      int | None,
    "label":      int,            # 1 = team_a 승, 0 = team_b 승
}
```

---

## 2. 전처리 출력 파일

> 모두 로컬 생성, git 제외 (`.gitignore`에 포함)

| 경로 | 내용 |
|------|------|
| `data/processed/matches_clean.csv` | 품질 검사·dedup 통과한 맵 행 전체 |
| `data/processed/features_base.csv` | 피처 테이블 (baseline 178개 / advanced 125개 + 레이블) |
| `data/processed/train.csv` | 학습셋 (baseline) |
| `data/processed/adv_kaggle_only/train.csv` | 학습셋 (advanced) |
| `data/processed/test.csv` | 테스트셋 (최종 평가 전용) |
| `reports/preprocess_summary.json` | 파이프라인 실행 요약 |
| `reports/rejected_matches.csv` | 품질 검사 탈락 행 및 사유 |

---

## 3. dedup_key / match_key 생성

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

---

## 4. 참고 문서

- [02_agent_role_mapping.md](./02_agent_role_mapping.md) — AGENT_ROLE_MAP 29종
- [03_map_database.md](./03_map_database.md) — MAP_ORDER 13개
- [04_column_definitions.md](./04_column_definitions.md) — 소스별 컬럼 매핑

### 1.1 필수 컬럼 (학습 피처)

| 컬럼명 | 타입 | 범위/예시 | 설명 |
|--------|------|---------|------|
| `a_duelist` | int8 | 0~5 | 팀 A 듀얼리스트 수 |
| `a_initiator` | int8 | 0~5 | 팀 A 이니시에이터 수 |
| `a_controller` | int8 | 0~5 | 팀 A 컨트롤러 수 |
| `a_sentinel` | int8 | 0~5 | 팀 A 센티넬 수 |
| `b_duelist` | int8 | 0~5 | 팀 B 듀얼리스트 수 |
| `b_initiator` | int8 | 0~5 | 팀 B 이니시에이터 수 |
| `b_controller` | int8 | 0~5 | 팀 B 컨트롤러 수 |
| `b_sentinel` | int8 | 0~5 | 팀 B 센티넬 수 |
| `duelist_diff` | int8 | -5~5 | a_duelist - b_duelist |
| `initiator_diff` | int8 | -5~5 | a_initiator - b_initiator |
| `controller_diff` | int8 | -5~5 | a_controller - b_controller |
| `sentinel_diff` | int8 | -5~5 | a_sentinel - b_sentinel |
| `map_encoded` | int8 | 0~12 | 맵 LabelEncoded 정수 |
| `has_controller_a` | int8 | 0 or 1 | 팀 A Controller ≥1 여부 |
| `has_controller_b` | int8 | 0 or 1 | 팀 B Controller ≥1 여부 |
| `label` | int8 | 0 or 1 | 1=팀 A 승리, 0=팀 A 패배 |

### 1.2 메타 컬럼 (학습 시 제외, 추적/검증용)

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `match_id` | string | 경기 고유 ID |
| `map` | string | 맵 이름 (원본) |
| `team_a` | string | 팀 A 이름 |
| `team_b` | string | 팀 B 이름 |
| `team_a_agents` | string | 쉼표 구분 팀 A 요원 목록 |
| `team_b_agents` | string | 쉼표 구분 팀 B 요원 목록 |
| `source` | string | 데이터 출처 코드 |
| `data_type` | string | "pro" or "ranked" |
| `sample_weight` | float | 학습 가중치 |
| `game_version` | string | 패치 버전 (가용 시) |

---

## 2. 피처 컬럼 목록 (학습용)

```python
FEATURE_COLUMNS = [
    # 팀 A 역할군
    "a_duelist", "a_initiator", "a_controller", "a_sentinel",
    # 팀 B 역할군
    "b_duelist", "b_initiator", "b_controller", "b_sentinel",
    # Diff 피처
    "duelist_diff", "initiator_diff", "controller_diff", "sentinel_diff",
    # 맵
    "map_encoded",
    # 이진 피처
    "has_controller_a", "has_controller_b",
]
# 기본 역할군 피처 15개 (베이스라인; 확정 설계는 43개)

LABEL_COLUMN = "label"
META_COLUMNS = ["match_id", "map", "team_a", "team_b", "team_a_agents", "team_b_agents",
                "source", "data_type", "sample_weight", "game_version"]
```

---

## 3. 스키마 변환 파이프라인

```python
import pandas as pd
from sklearn.preprocessing import LabelEncoder

VALID_MAPS = [
    "Ascent", "Bind", "Breeze", "Drift", "Fracture", "Haven",
    "Icebox", "Lotus", "Pearl", "Split", "Sunset", "Abyss",
    "Corrode",
]

AGENT_ROLE_MAP = {
    # Duelist
    "Jett": "Duelist", "Reyna": "Duelist", "Raze": "Duelist",
    "Neon": "Duelist", "Yoru": "Duelist", "Phoenix": "Duelist",
    "ISO": "Duelist", "Waylay": "Duelist",
    # Initiator
    "Sova": "Initiator", "Breach": "Initiator", "Fade": "Initiator",
    "KAY/O": "Initiator", "Gekko": "Initiator", "Skye": "Initiator",
    "Tejo": "Initiator",
    # Controller
    "Viper": "Controller", "Omen": "Controller", "Brimstone": "Controller",
    "Astra": "Controller", "Harbor": "Controller", "Clove": "Controller",
    # Sentinel
    "Killjoy": "Sentinel", "Cypher": "Sentinel", "Sage": "Sentinel",
    "Chamber": "Sentinel", "Deadlock": "Sentinel", "Vyse": "Sentinel",
}


def normalize_map_name(map_name: str) -> str | None:
    """맵 이름 표준화"""
    name = map_name.strip().title()
    return name if name in VALID_MAPS else None


def agents_str_to_roles(agents_str: str) -> dict:
    """'Jett,Sova,Viper,Omen,Killjoy' → 역할군 카운트"""
    agents = [a.strip() for a in agents_str.split(",") if a.strip()]
    counts = {"Duelist": 0, "Initiator": 0, "Controller": 0, "Sentinel": 0}
    for agent in agents:
        role = AGENT_ROLE_MAP.get(agent, "Unknown")
        if role in counts:
            counts[role] += 1
    return counts


def convert_to_standard_schema(
    df: pd.DataFrame,
    map_col: str = "map",
    team_a_agents_col: str = "team_a_agents",
    team_b_agents_col: str = "team_b_agents",
    label_col: str = "label",
    source: str = "unknown",
) -> pd.DataFrame:
    """임의 형식 DataFrame → 표준 스키마로 변환"""
    records = []
    
    le = LabelEncoder()
    le.fit(VALID_MAPS)
    
    for _, row in df.iterrows():
        map_name = normalize_map_name(str(row.get(map_col, "")))
        if map_name is None:
            continue  # 유효하지 않은 맵 → 제외
        
        try:
            a_roles = agents_str_to_roles(str(row.get(team_a_agents_col, "")))
            b_roles = agents_str_to_roles(str(row.get(team_b_agents_col, "")))
        except Exception:
            continue
        
        record = {
            "match_id": str(row.get("match_id", "")),
            "map": map_name,
            "map_encoded": int(le.transform([map_name])[0]),
            "team_a": str(row.get("team_a", "")),
            "team_b": str(row.get("team_b", "")),
            "team_a_agents": str(row.get(team_a_agents_col, "")),
            "team_b_agents": str(row.get(team_b_agents_col, "")),
            "a_duelist": a_roles["Duelist"],
            "a_initiator": a_roles["Initiator"],
            "a_controller": a_roles["Controller"],
            "a_sentinel": a_roles["Sentinel"],
            "b_duelist": b_roles["Duelist"],
            "b_initiator": b_roles["Initiator"],
            "b_controller": b_roles["Controller"],
            "b_sentinel": b_roles["Sentinel"],
            "duelist_diff": a_roles["Duelist"] - b_roles["Duelist"],
            "initiator_diff": a_roles["Initiator"] - b_roles["Initiator"],
            "controller_diff": a_roles["Controller"] - b_roles["Controller"],
            "sentinel_diff": a_roles["Sentinel"] - b_roles["Sentinel"],
            "has_controller_a": int(a_roles["Controller"] >= 1),
            "has_controller_b": int(b_roles["Controller"] >= 1),
            "label": int(row.get(label_col, 0)),
            "source": source,
            "data_type": "pro" if source in ("riot_s3", "kaggle_vct", "vlrgg") else "ranked",
            "sample_weight": 1.0,
            "game_version": str(row.get("game_version", "")),
        }
        records.append(record)
    
    return pd.DataFrame(records)
```

---

## 4. 스키마 검증

```python
def validate_schema(df: pd.DataFrame) -> dict:
    """표준 스키마 유효성 검증"""
    issues = {}
    
    # 레이블 분포
    label_dist = df["label"].value_counts(normalize=True)
    if abs(label_dist.get(0, 0) - 0.5) > 0.1:
        issues["label_imbalance"] = f"레이블 불균형: {label_dist.to_dict()}"
    
    # 역할군 합계 (항상 5여야 함)
    a_sum = df[["a_duelist", "a_initiator", "a_controller", "a_sentinel"]].sum(axis=1)
    b_sum = df[["b_duelist", "b_initiator", "b_controller", "b_sentinel"]].sum(axis=1)
    
    invalid_a = (a_sum != 5).sum()
    invalid_b = (b_sum != 5).sum()
    if invalid_a > 0:
        issues["invalid_team_a_composition"] = f"{invalid_a}개 행에서 팀 A 역할군 합계 ≠ 5"
    if invalid_b > 0:
        issues["invalid_team_b_composition"] = f"{invalid_b}개 행에서 팀 B 역할군 합계 ≠ 5"
    
    # NaN 확인
    nan_counts = df[FEATURE_COLUMNS + [LABEL_COLUMN]].isna().sum()
    nan_cols = nan_counts[nan_counts > 0]
    if len(nan_cols) > 0:
        issues["nan_values"] = nan_cols.to_dict()
    
    if not issues:
        print(f"[OK] 스키마 검증 통과 ({len(df)} 행)")
    else:
        print(f"[WARN] {len(issues)}개 이슈 발견")
        for k, v in issues.items():
            print(f"  - {k}: {v}")
    
    return issues
```
