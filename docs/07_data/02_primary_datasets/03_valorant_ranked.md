# 03. Valorant 랭크 매치 데이터셋

## 1. 왜 랭크 매치 데이터가 필요한가?

| 구분 | 프로 경기 (VCT) | 랭크 매치 |
|------|--------------|---------|
| 볼륨 | ~3,000경기 | 수십만~수백만 경기 |
| 메타 다양성 | 프로 픽 편중 | 일반 유저 다양한 조합 |
| 실력 분포 | 극소수 최정상 | 다양한 레벨 |
| 데이터 수집 난이도 | 낮음 (Kaggle, Riot S3) | 높음 (API, 스크래핑) |

> 80% 정확도 달성을 위해서는 **일반 유저 수준**에서도 예측이 작동해야 함.  
> 프로 데이터만 학습하면 일반 유저 예측 시 성능 저하 발생.

---

## 2. 주요 랭크 매치 데이터셋 목록

### 2.1 Kaggle에서 발굴된 데이터셋

| 데이터셋 ID | 내용 | 예상 규모 | 우선순위 |
|------------|------|---------|---------|
| `amirkhalili/valorant-rank-dataset` | 랭크별 플레이어 통계 | ~100K 행 | ⭐⭐⭐ |
| `visualize/valorant-ranked-game-data` | 경기별 데이터 | ~50K 행 | ⭐⭐⭐ |
| `nicholasgalante88/valorant-match-data` | 경기 상세 데이터 | ~30K 행 | ⭐⭐ |
| `jummyegg/valorant-competitive-data` | 경쟁전 데이터 | ~20K 행 | ⭐⭐ |
| `torcordobes/valorant-ranked-matches` | 랭크 매치 | 미확인 | ⭐ |

> **주의:** 위 데이터셋 ID는 검색 추정 ID이며, 실제 존재 여부를 Kaggle에서 확인 필요.

### 2.2 확인된 검색 쿼리

```bash
# Kaggle CLI 검색
kaggle datasets list --search "valorant ranked" --sort-by relevance --max-size 1000
kaggle datasets list --search "valorant competitive match" --sort-by updated
kaggle datasets list --search "valorant agent composition" --sort-by relevance
```

---

## 3. 랭크 매치 데이터셋 평가 기준

### 3.1 필수 컬럼 (최소 요건)

```python
REQUIRED_COLUMNS = [
    "match_id",      # 경기 고유 ID
    "map",           # 맵 이름
    "agent",         # 사용 요원 (또는 team_agents 리스트)
    "team",          # 팀 구분
    "result",        # 경기 결과 (win/loss 또는 0/1)
]
```

### 3.2 우선 선택 기준

```python
def evaluate_dataset(df: pd.DataFrame) -> dict:
    """데이터셋 평가 점수 계산"""
    scores = {}
    
    # 볼륨 점수 (10,000경기 = 만점)
    match_count = df["match_id"].nunique()
    scores["volume"] = min(match_count / 10000 * 100, 100)
    
    # 필수 컬럼 충족도
    has_required = sum(1 for c in REQUIRED_COLUMNS if c in df.columns)
    scores["columns"] = (has_required / len(REQUIRED_COLUMNS)) * 100
    
    # 요원 다양성 (27종 중)
    agent_count = df["agent"].nunique() if "agent" in df.columns else 0
    scores["agent_diversity"] = (agent_count / 27) * 100
    
    # 맵 다양성 (12개 맵 기준)
    map_count = df["map"].nunique() if "map" in df.columns else 0
    scores["map_diversity"] = (map_count / 12) * 100
    
    scores["total"] = sum(scores.values()) / len(scores)
    return scores
```

---

## 4. 데이터 로드 및 전처리

### 4.1 표준 로더

```python
import pandas as pd
import kagglehub
import os

RANKED_DATASETS = [
    "amirkhalili/valorant-rank-dataset",
    "visualize/valorant-ranked-game-data",
    "nicholasgalante88/valorant-match-data",
]

def load_ranked_dataset(dataset_id: str, dest_dir: str = "data/raw/kaggle") -> pd.DataFrame | None:
    """랭크 매치 데이터셋 로드 시도"""
    try:
        path = kagglehub.dataset_download(dataset_id)
        df = pd.read_csv(path + "/data.csv")  # 파일명은 데이터셋마다 다를 수 있음
        df["source_dataset"] = dataset_id
        print(f"[INFO] {dataset_id}: {len(df)} 행 로드 완료")
        return df
    except FileNotFoundError:
        # 폴더 내 첫 번째 CSV 사용 시도
        for f in os.listdir(path):
            if f.endswith(".csv"):
                df = pd.read_csv(os.path.join(path, f))
                df["source_dataset"] = dataset_id
                return df
    except Exception as e:
        print(f"[WARN] {dataset_id} 실패: {e}")
        return None


def load_all_ranked(dest_dir: str = "data/raw/kaggle") -> pd.DataFrame:
    """모든 랭크 데이터셋 시도 후 병합"""
    dfs = []
    for dataset_id in RANKED_DATASETS:
        df = load_ranked_dataset(dataset_id, dest_dir)
        if df is not None:
            dfs.append(df)
    
    if not dfs:
        raise RuntimeError("랭크 데이터셋을 하나도 로드하지 못함")
    
    return pd.concat(dfs, ignore_index=True)
```

---

## 5. 랭크 매치 특유의 전처리 이슈

### 5.1 학습 불균형 문제

```python
# 랭크 분포 편향 (골드 이하가 다수)
# → 레이블(승/패) 자체는 50:50으로 균형이지만,
# → 실력 분포 편향으로 인해 피처 분포가 왜곡될 수 있음

# 해결: 랭크 계층별 샘플링 (선택적)
from sklearn.utils import resample

def stratified_by_rank(df: pd.DataFrame, target_per_rank: int = 5000) -> pd.DataFrame:
    """랭크별 균등 샘플링"""
    if "rank_tier" not in df.columns:
        return df  # 랭크 정보 없으면 그대로 사용
    
    sampled = []
    for rank in df["rank_tier"].unique():
        subset = df[df["rank_tier"] == rank]
        n = min(len(subset), target_per_rank)
        sampled.append(subset.sample(n, random_state=42))
    
    return pd.concat(sampled, ignore_index=True)
```

### 5.2 요원 이름 표준화

```python
# 데이터셋마다 요원 이름이 다르게 표기될 수 있음
AGENT_NAME_MAP = {
    "kay/o": "KAYO",
    "kayo": "KAYO",
    "kay-o": "KAYO",
    "k/o": "KAYO",
    "neon": "Neon",
    "neon ": "Neon",  # 공백 포함
}

def normalize_agent(name: str) -> str:
    return AGENT_NAME_MAP.get(name.lower().strip(), name.strip().title())
```

---

## 6. 병합 전략

랭크 매치 데이터는 프로 경기 데이터와 **별도로 관리**하다가 최종 병합:

```python
# 병합 시 데이터 출처 레이블 추가 (소스별 가중치 적용 가능)
df_ranked["data_type"] = "ranked"
df_vct["data_type"] = "pro"

df_all = pd.concat([df_vct, df_ranked], ignore_index=True)

# 소스별 클래스 가중치 (프로 데이터에 높은 가중치)
SAMPLE_WEIGHTS = {"pro": 2.0, "ranked": 1.0}
df_all["sample_weight"] = df_all["data_type"].map(SAMPLE_WEIGHTS)
```

---

## 7. 예상 최종 볼륨

| 소스 | 예상 경기 수 |
|------|------------|
| VCT 2021-2023 (Kaggle) | ~2,000 |
| VCT 2024 (Kaggle) | ~1,000 |
| 랭크 매치 Kaggle 데이터셋 합산 | ~10,000~50,000 |
| Riot VCT S3 | ~100,000+ |
| HenrikDev API 수집 | ~5,000 |
| **총합 목표** | **>50,000** |

> 50,000+ 경기 확보 시 80% 정확도 달성 가능 (기존 ~67-72%에서 향상 예상)
