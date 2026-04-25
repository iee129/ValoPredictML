# 01. 현재 데이터 볼륨

## 1. 현황 요약

| 소스 | 경기 수 (추정) | 상태 | 가중치 |
|------|------------|------|------|
| Kaggle VCT 2021-2023 | ~2,000 경기 | ✅ 확보 | 2.0 |
| HenrikDev API (수집 중) | ~5,000 경기 | ⚠️ 진행 중 | 1.0 |
| VLR.gg 스크래핑 | ~0 경기 | ❌ 미수집 | 1.5 |
| Riot S3 공식 | ~0 경기 | ❌ 미수집 | 2.5 |
| Kaggle 추가 데이터셋 | ~0 경기 | ❌ 미탐색 | 0.8 |
| **합계** | **~7,000 경기** | **부족** | - |

---

## 2. 현재 볼륨 상세 분석

### 2.1 Kaggle VCT 2021-2023 (주요 확보 소스)

```python
import pandas as pd

def analyze_current_kaggle_volume():
    """현재 Kaggle 데이터셋 볼륨 분석"""
    # 예상 파일 구조 (실제 다운로드 후 확인 필요)
    EXPECTED_FILES = {
        "2021_vct_game_info.csv": 600,   # 추정 경기 수
        "2022_vct_game_info.csv": 700,
        "2023_vct_game_info.csv": 750,
    }
    
    # 실제 볼륨 확인 코드
    import glob
    csv_files = glob.glob("data/kaggle_vct/*.csv")
    
    total = 0
    for f in csv_files:
        df = pd.read_csv(f, nrows=1, header=0)
        row_count = sum(1 for _ in open(f)) - 1
        print(f"{f}: {row_count:,}행")
        total += row_count
    
    print(f"\n총 경기: {total:,}경기 (플레이어 행 기준 ÷5÷2 = {total//10:,}경기)")
```

### 2.2 HenrikDev API 수집 현황

```python
def report_henrikdev_collection_status(output_dir: str = "data/henrikdev") -> dict:
    """HenrikDev API 수집 현황 보고"""
    import os
    
    status = {
        "files_count": 0,
        "match_count": 0,
        "seed_players_processed": 0,
        "collection_rate": "~20 경기/분 (Rate Limit 25 req/min)",
    }
    
    if os.path.exists(output_dir):
        files = [f for f in os.listdir(output_dir) if f.endswith(".json")]
        status["files_count"] = len(files)
        status["match_count"] = len(files)  # 경기당 1파일
    
    print(f"[HenrikDev 수집 현황]")
    print(f"  수집 경기: {status['match_count']:,}경기")
    print(f"  Rate Limit: {status['collection_rate']}")
    print(f"  완료까지: {max(0, 10000 - status['match_count']):,}경기 추가 필요")
    
    return status
```

---

## 3. 현재 데이터 분포 분석

```python
def analyze_data_distribution(df: pd.DataFrame) -> None:
    """현재 데이터 분포 출력"""
    print("=== 현재 데이터 분포 분석 ===\n")
    
    print(f"전체 경기 수: {len(df):,}")
    
    # 맵 분포
    print("\n[맵 분포]")
    map_dist = df["map"].value_counts()
    for map_name, count in map_dist.items():
        bar = "█" * (count // 20)
        print(f"  {map_name:<12}: {count:>5} {bar}")
    
    # 레이블 균형
    print("\n[승/패 균형]")
    label_dist = df["label"].value_counts(normalize=True)
    print(f"  팀A 승 (label=1): {label_dist.get(1, 0):.1%}")
    print(f"  팀B 승 (label=0): {label_dist.get(0, 0):.1%}")
    
    # 역할군 분포
    print("\n[역할군 평균 카운트]")
    for role in ["duelist", "initiator", "controller", "sentinel"]:
        avg_a = df[f"a_{role}"].mean() if f"a_{role}" in df.columns else 0
        avg_b = df[f"b_{role}"].mean() if f"b_{role}" in df.columns else 0
        print(f"  {role:<12}: A={avg_a:.2f}, B={avg_b:.2f}")
```

---

## 4. 현재 볼륨의 한계

| 문제 | 수치 | 영향 |
|------|------|------|
| 총 경기 수 부족 | ~7,000 (목표 50,000) | 일반화 어려움 |
| 맵별 경기 수 불균형 | 맵당 평균 ~700경기 | 특정 맵 편향 |
| 신규 패치 데이터 없음 | EP8~10 거의 없음 | 현재 메타 반영 불가 |
| 요원 조합 커버리지 | 전체 조합 중 <1% | 희소 조합 예측 불가 |

### 예상 정확도 vs 데이터 볼륨

```
경기 수   정확도 추정 (XGB+LGBM, 15 피처)
-------   --------------------------------
 2,000    ~63-67%  ← 현재 Kaggle만
 7,000    ~67-72%  ← 현재 HenrikDev 포함
10,000    ~70-73%
20,000    ~73-76%
50,000    ~76-80%  ← 데이터 목표
50,000+   ~80-84%  ← 피처 확장 시
```
