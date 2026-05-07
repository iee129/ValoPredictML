# 04_data_processing — 데이터 전처리

전처리 파이프라인 전 단계를 다루는 문서 모음. 상세 색인은 [data_processing.md](data_processing.md) 참조.

## 파이프라인 개요 (완료)

```
파서 → 품질 게이트 + dedup → 피처 엔지니어링 → 70/15/15 분할
결과: clean 66,485행 → train 93,078 / val 9,973 / test 9,973
```

## 파일 목록

| 파일 | 내용 |
|------|------|
| [data_processing.md](data_processing.md) | 전체 색인 및 파이프라인 요약 |
| [01_pipeline_overview.md](01_pipeline_overview.md) | 파이프라인 단계별 개요 |
| [02_data_collection.md](02_data_collection.md) | Kaggle 데이터 수집 전략 |
| [03_data_loading.md](03_data_loading.md) | CSV 파싱 및 로딩 |
| [04_data_cleaning.md](04_data_cleaning.md) | 품질 게이트 + SHA-1 dedup |
| [05_aggregation.md](05_aggregation.md) | 집계 피처 (Phase 2) |
| [06_feature_engineering.md](06_feature_engineering.md) | 역할 피처, 맵 인코딩 등 |
| [07_split_and_validation.md](07_split_and_validation.md) | match_key 기반 train/val/test 분할 |
