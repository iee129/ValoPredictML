# 02. Kaggle 데이터셋 채택 기준 및 통합 전략

## 1. 채택 기준 (5-point 스코어링)

| 기준 | 점수 | 설명 |
|------|------|------|
| 요원 정보 포함 | 2점 | `agent` 또는 `composition` 컬럼 필수 |
| 경기 결과 포함 | 2점 | `winner`, `result`, `label` 컬럼 필수 |
| 맵 정보 포함 | 1점 | `map` 컬럼 (없어도 채택 가능) |
| 최소 5,000 행 이상 | 1점 | 통계적 유의미성 |
| 2022년 이후 데이터 | 1점 | 현재 메타 반영 |
| 중복 없음 | 1점 | 이미 채택된 데이터셋과 중복 최소화 |
| **최소 채택 점수** | **4점 이상** | |

---

## 2. 통합 전략

### 2.1 소스 우선순위

```
1. Riot VCT S3 (공식, 무결점)
2. Kaggle VCT 시리즈 (ryanluong1)
3. HenrikDev API 수집
4. 기타 Kaggle 랭크 매치 데이터셋
5. VLR.gg 스크래핑 (최후 수단)
```

### 2.2 데이터 흐름

```
각 소스 → 원본 저장 (data/raw/) → 파싱 → 표준 스키마 → data/processed/ → 학습
```

### 2.3 표준 스키마 (모든 소스 공통)

```python
STANDARD_SCHEMA = {
    "match_id": str,       # 경기 고유 ID
    "map": str,            # 맵 이름 (표준화)
    "team_a_agents": str,  # 쉼표 구분 요원 목록 (예: "Jett,Sova,Viper,Omen,Killjoy")
    "team_b_agents": str,  # 동일
    "a_duelist": int,      # 팀 A 역할군 카운트
    "a_initiator": int,
    "a_controller": int,
    "a_sentinel": int,
    "b_duelist": int,
    "b_initiator": int,
    "b_controller": int,
    "b_sentinel": int,
    "duelist_diff": int,   # diff 피처
    "initiator_diff": int,
    "controller_diff": int,
    "sentinel_diff": int,
    "map_encoded": int,    # 맵 정수 인코딩
    "label": int,          # 0 or 1
    "source": str,         # 데이터 출처
    "data_type": str,      # "pro" or "ranked"
}
```

---

## 3. 중복 경기 제거

```python
import pandas as pd

def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """다중 소스 병합 후 중복 경기 제거"""
    
    # match_id 기반 1차 제거
    df_dedup = df.drop_duplicates(subset=["match_id"], keep="first")
    
    # match_id가 없는 경우: 팀 조합 + 맵 + 결과 기반 2차 제거
    mask_no_id = df_dedup["match_id"].isna() | (df_dedup["match_id"] == "")
    
    if mask_no_id.sum() > 0:
        df_no_id = df_dedup[mask_no_id].copy()
        df_no_id["_dedup_key"] = (
            df_no_id["team_a_agents"].str.lower() + "|" +
            df_no_id["team_b_agents"].str.lower() + "|" +
            df_no_id["map"].str.lower() + "|" +
            df_no_id["label"].astype(str)
        )
        df_no_id = df_no_id.drop_duplicates(subset=["_dedup_key"]).drop(columns=["_dedup_key"])
        
        df_dedup = pd.concat([df_dedup[~mask_no_id], df_no_id], ignore_index=True)
    
    removed = len(df) - len(df_dedup)
    print(f"[INFO] 중복 제거: {removed}개 → 최종 {len(df_dedup)}개")
    return df_dedup
```

---

## 4. 소스별 가중치 (학습 시)

```python
# 프로 경기 데이터에 더 높은 신뢰도 부여
SOURCE_WEIGHTS = {
    "riot_s3": 2.5,       # 공식 프로 경기 (가장 신뢰)
    "kaggle_vct": 2.0,    # Kaggle VCT (신뢰)
    "vlrgg": 1.5,         # VLR.gg 스크래핑 (신뢰)
    "henrikdev": 1.0,     # 랭크 매치 (일반)
    "kaggle_ranked": 0.8, # 기타 Kaggle (검증 필요)
}

df["sample_weight"] = df["source"].map(SOURCE_WEIGHTS).fillna(1.0)
```

---

## 5. 최종 데이터셋 구성 목표

| 데이터 타입 | 비율 | 목표 경기 수 |
|-----------|------|-----------|
| 프로 경기 (VCT) | 20% | 10,000 |
| 이머탈+ 랭크 | 30% | 15,000 |
| 플레~다이아 랭크 | 35% | 17,500 |
| 골드 이하 랭크 | 15% | 7,500 |
| **총계** | **100%** | **50,000** |

> 50,000 경기 달성 시 XGBoost+LightGBM 앙상블 기대 정확도: **80~84%**
