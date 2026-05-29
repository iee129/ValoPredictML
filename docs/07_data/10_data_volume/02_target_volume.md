# 02. 목표 데이터 볼륨

마지막 업데이트: 2026-05-04

> 데이터 소스는 Kaggle 7개 데이터셋으로 확정. 외부 소스 추가는 방침 외.
> 목표: 중복 제거 후 80~100K 맵 행 확보.

## 1. 목표 설정

| 단계 | 목표 맵 행 수 | 달성 방법 | 예상 Accuracy |
|------|-----------|---------|----------|
| Phase 1 (단기) | 20,000 경기 | Kaggle + HenrikDev API | ~73-76% |
| Phase 2 (중기) | 50,000 경기 | + Riot S3 + VLR.gg | ~78-80% |
| **Phase 3 (목표)** | **100,000+ 경기** | **+ 피처 확장** | **80-84% (미달성 추정 — 현재 Acc 0.6958; Kaggle 단독 데이터 한계 존재)** |

---

## 2. 소스별 수집 목표

> ⚠️ **본 문서는 방침 변경 전 초기 계획** — 현재 방침: Kaggle 7개 데이터셋 전용, Riot S3·HenrikDev·VLR.gg 미사용.

| 소스 | 현재 | 수집 목표 | 가중치 | 가중 경기 수 |
|------|------|---------|------|-----------|
| Riot S3 공식 | 0 | 30,000 | 2.5 | 75,000 |
| Kaggle VCT | 2,000 | 5,000 | 2.0 | 10,000 |
| VLR.gg | 0 | 15,000 | 1.5 | 22,500 |
| HenrikDev API | 5,000 | 20,000 | 1.0 | 20,000 |
| Kaggle 추가 | 0 | 10,000 | 0.8 | 8,000 |
| **합계** | **7,000** | **80,000** | - | **135,500** |

가중 경기 수 기준 **135,500** → 80%+ 달성 가능 (초기 추정 — 현재 미달성)

---

## 3. 수집 로드맵

### Phase 1: 단기 (2주)

```python
PHASE1_TARGETS = {
    "riot_s3": {
        "target": 30000,
        "method": "boto3 익명 접근",
        "estimated_time": "3-5일 (병렬 다운로드)",
        "priority": 1,
    },
    "vlrgg_scraping": {
        "target": 5000,
        "method": "2-3초 딜레이 스크래핑",
        "estimated_time": "2-3일",
        "priority": 2,
    },
    "henrikdev_continue": {
        "target": 5000,  # 추가 수집
        "method": "API 지속 수집",
        "estimated_time": "진행 중",
        "priority": 3,
    },
}
```

### Phase 2: 중기 (1개월)

```python
PHASE2_TARGETS = {
    "kaggle_additional": {
        "target": 10000,
        "method": "Kaggle API 탐색 후 채택",
        "datasets": [
            "valorant-matches-2024",
            "valorant-ranked-matches",
        ],
    },
    "vlrgg_full": {
        "target": 15000,
        "method": "전체 토너먼트 스크래핑",
    },
}
```

---

## 4. 진행률 추적

```python
def track_collection_progress(
    current_counts: dict[str, int],
    targets: dict[str, int],
) -> None:
    """수집 진행률 대시보드"""
    print("\n=== 데이터 수집 진행률 ===\n")
    
    total_current = sum(current_counts.values())
    total_target = sum(targets.values())
    
    for source, target in targets.items():
        current = current_counts.get(source, 0)
        pct = min(current / target * 100, 100)
        bar_len = int(pct / 5)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        print(f"  {source:<20}: [{bar}] {pct:>5.1f}% ({current:>6,}/{target:>6,})")
    
    total_pct = min(total_current / total_target * 100, 100)
    print(f"\n  {'전체':>20}: {total_pct:.1f}% ({total_current:,}/{total_target:,})")
    
    # 남은 시간 추정 (HenrikDev 기준 20 경기/분)
    remaining = total_target - total_current
    if remaining > 0:
        print(f"\n  예상 남은 시간: {remaining / 20 / 60:.1f}시간 (HenrikDev 속도 기준)")

# 사용 예시
# track_collection_progress(
#     current_counts={"riot_s3": 0, "kaggle_vct": 2000, "vlrgg": 0, "henrikdev": 5000},
#     targets={"riot_s3": 30000, "kaggle_vct": 5000, "vlrgg": 15000, "henrikdev": 20000}
# )
```

---

## 5. 맵별 균형 목표

현재 맵별 데이터가 불균형. 50,000 경기 기준 맵별 목표:

| 맵 | 최소 경기 | 권장 경기 |
|----|---------|--------|
| Ascent | 4,000 | 6,000 |
| Bind | 4,000 | 5,500 |
| Haven | 4,000 | 5,500 |
| Split | 3,500 | 5,000 |
| Icebox | 3,500 | 5,000 |
| Pearl | 3,000 | 4,500 |
| Lotus | 3,000 | 4,500 |
| Sunset | 2,500 | 4,000 |
| Abyss | 2,000 | 3,500 |
| Drift | 1,000 | 2,500 |
| Breeze* | 500 | 1,000 |
| Fracture* | 500 | 1,000 |

*비활성 맵 — 학습 옵션에서 제외 가능

```python
def check_map_balance(df: pd.DataFrame, min_per_map: int = 1000) -> dict:
    """맵별 균형 확인"""
    if "map" not in df.columns:
        return {}
    
    map_counts = df["map"].value_counts().to_dict()
    
    insufficient = {
        map_name: count
        for map_name, count in map_counts.items()
        if count < min_per_map
    }
    
    if insufficient:
        print(f"[경고] 데이터 부족 맵 ({min_per_map}경기 미만): {insufficient}")
    
    return map_counts
```

---

## 6. 데이터 수집 우선순위 요약

```
[즉시 실행] Riot S3 버킷 다운로드 (boto3, 무료)
  → 예상 30,000+ 경기, 가중치 2.5 (가장 신뢰도 높음)

[병행 실행] VLR.gg 스크래핑 (프로 경기)
  → 예상 15,000 경기, 가중치 1.5

[지속 수집] HenrikDev API (랭크 매치)
  → 예상 20,000 경기, 가중치 1.0

[탐색 후 결정] Kaggle 추가 데이터셋
  → 평가 기준(06_additional_kaggle/02_adoption_criteria.md) 통과 시만 채택
```
