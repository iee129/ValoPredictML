# 04_data_processing — 데이터 전처리

전처리 파이프라인 전 단계를 다루는 문서 모음. 최종 보고서에서는 데이터 확보 이후 **정제 → 피처 생성 → 분할/검증** 근거를 이 장에서 설명한다. 상세 색인은 [data_processing.md](data_processing.md) 참조.

## 정본 파이프라인 (완료)

```
Kaggle CSV 파서
→ 품질 검사 + dedup
→ previous-year 피처 엔지니어링
→ match_key 단위 80/20 random holdout
→ 별도 year-block chrono holdout
```

| 산출 | 기준 |
|---|---|
| Baseline feature contract | 421 features (슬롯 선수 400 + 매치 컨텍스트 21) |
| Advanced feature contract | 179 features |
| Baseline random split | 랜덤 80/20, baseline 계약 421피처 |
| Advanced split | 시간순(chrono): train 75,405 / test 16,053 맵 단위 승패 샘플 |
| Advanced sample unit | 총 91,458개 맵 단위 승패 샘플(BO 시리즈 수 아님) |
| Advanced validation | split overlap 0, forbidden feature 0, Kaggle/VLR.gg source 정상 |

## 파일 목록

| 파일 | 내용 |
|------|------|
| [data_processing.md](data_processing.md) | 전체 색인 및 파이프라인 요약 |
| [01_pipeline_overview.md](01_pipeline_overview.md) | 파이프라인 단계별 개요 |
| [02_data_collection.md](02_data_collection.md) | Kaggle 데이터 수집 전략 |
| [03_data_loading.md](03_data_loading.md) | CSV 파싱 및 로딩 |
| [04_data_cleaning.md](04_data_cleaning.md) | 품질 검사 + SHA-1 dedup |
| [05_aggregation.md](05_aggregation.md) | 집계 피처 (Phase 2) |
| [06_feature_engineering.md](06_feature_engineering.md) | 역할 피처, 맵 인코딩 등 |
| [07_split_and_validation.md](07_split_and_validation.md) | match_key 기반 train/val/test 분할 |
| [08_raw_preprocess.md](08_raw_preprocess.md) | `data/raw/**` 전용 재전처리 산출물 설명 |
