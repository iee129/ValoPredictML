# 01. Kaggle 추가 데이터셋 카탈로그

## 1. 검색 전략

### 1.1 권장 검색 쿼리

```bash
# Kaggle CLI 검색
kaggle datasets list --search "valorant" --sort-by relevance --max-size 5000
kaggle datasets list --search "valorant match composition" --sort-by updated
kaggle datasets list --search "valorant agent pick rate" --sort-by votes

# Kaggle 웹 검색
# https://www.kaggle.com/datasets?search=valorant&sortBy=relevance
```

---

## 2. 발굴된 데이터셋 카탈로그

### 2.1 경기/조합 데이터 (직접 사용 가능)

| 우선순위 | 데이터셋 ID (추정) | 내용 | 예상 크기 | 채택 여부 |
|---------|----------------|------|---------|---------|
| ⭐⭐⭐ | `ryanluong1/valorant-champion-tour-2021-2023-data` | VCT 공식 (사용 중) | ~5MB | ✅ 채택 |
| ⭐⭐⭐ | `ryanluong1/valorant-champion-tour-2024-data` | VCT 2024 | ~3MB | ✅ 채택 |
| ⭐⭐⭐ | `amirkhalili/valorant-rank-dataset` | 랭크 경기 통계 | ~50MB | ✅ 채택 |
| ⭐⭐ | `nicholasgalante88/valorant-match-data` | 경쟁전 경기 | ~20MB | 🔍 검토 |
| ⭐⭐ | `jummyegg/valorant-competitive-data` | 경쟁전 조합 | ~10MB | 🔍 검토 |
| ⭐ | `thedevastator/valorant-player-stats` | 플레이어 통계 | ~30MB | 🔍 검토 |

### 2.2 요원/메타 분석 데이터 (피처 보완용)

| 우선순위 | 데이터셋 ID (추정) | 내용 | 채택 여부 |
|---------|----------------|------|---------|
| ⭐⭐⭐ | `valorant-api/agent-pickrates-by-map` | 맵별 픽률 | ✅ 채택 (피처 후보) |
| ⭐⭐ | `valorant-winrates/by-patch` | 패치별 승률 | 🔍 검토 |
| ⭐ | `valorant/rank-distribution` | 랭크 분포 | ❌ 불필요 |

### 2.3 발굴 필요 추가 데이터셋

```python
# Kaggle API로 대량 검색 코드
import subprocess
import json

def search_kaggle_datasets(query: str, max_results: int = 50) -> list[dict]:
    """Kaggle CLI를 통한 데이터셋 검색"""
    result = subprocess.run(
        ["kaggle", "datasets", "list", "--search", query, 
         "--sort-by", "relevance", "--max-size", "500",
         "--file-type", "csv"],
        capture_output=True, text=True
    )
    
    if result.returncode != 0:
        print(f"오류: {result.stderr}")
        return []
    
    # 출력 파싱 (Kaggle CLI는 테이블 형식으로 출력)
    lines = result.stdout.strip().split("\n")
    datasets = []
    for line in lines[1:]:  # 헤더 제외
        parts = line.split()
        if len(parts) >= 2:
            datasets.append({"ref": parts[0], "title": " ".join(parts[1:])})
    
    return datasets

# 실행 예시
results = search_kaggle_datasets("valorant competitive")
for d in results[:20]:
    print(d)
```

---

## 3. 데이터셋 평가 체크리스트

### 3.1 채택 기준

```python
def should_adopt_dataset(dataset_id: str) -> dict:
    """데이터셋 채택 여부 평가"""
    import kagglehub
    
    criteria = {
        "has_agent_column": False,
        "has_match_result": False,
        "has_map_column": False,
        "min_10k_rows": False,
        "recent_data_2023_plus": False,
    }
    
    try:
        path = kagglehub.dataset_download(dataset_id)
        df = pd.read_csv(next(Path(path).glob("*.csv")))
        
        col_lower = [c.lower() for c in df.columns]
        
        criteria["has_agent_column"] = any("agent" in c for c in col_lower)
        criteria["has_match_result"] = any(c in col_lower for c in ["winner", "result", "label", "won"])
        criteria["has_map_column"] = any("map" in c for c in col_lower)
        criteria["min_10k_rows"] = len(df) >= 10000
        
        if "date" in col_lower:
            max_year = pd.to_datetime(df["date"], errors="coerce").dt.year.max()
            criteria["recent_data_2023_plus"] = max_year >= 2023
    
    except Exception as e:
        print(f"평가 실패: {e}")
    
    score = sum(criteria.values())
    return {
        "dataset_id": dataset_id,
        "criteria": criteria,
        "score": score,
        "adopt": score >= 3
    }
```

---

## 4. 우선 다운로드 목록

순서대로 다운로드 및 평가:

```bash
# 1순위: 이미 사용 중
python -c "import kagglehub; kagglehub.dataset_download('ryanluong1/valorant-champion-tour-2021-2023-data')"

# 2순위: VCT 2024 (존재하면)
python -c "import kagglehub; kagglehub.dataset_download('ryanluong1/valorant-champion-tour-2024-data')"

# 3순위: 랭크 데이터셋들 (존재 여부 확인 후)
python -c "import kagglehub; kagglehub.dataset_download('amirkhalili/valorant-rank-dataset')"
```

---

## 5. 데이터셋 통합 후 예상 볼륨

| 채택 데이터셋 | 예상 경기 수 |
|------------|----------|
| VCT 2021-2023 (기존) | ~2,000 |
| VCT 2024 | ~1,000 |
| 랭크 매치 Kaggle (2~3개) | ~10,000~30,000 |
| **Kaggle 합계** | **~13,000~33,000** |
