# 07. 데이터 문서 인덱스

ValoPredictML의 데이터 소스, 스키마, 피처 엔지니어링, 품질 점검을 다루는 장이다. 최종 보고서에서는 **Kaggle 5개 데이터셋과 VLR.gg 수집 데이터를 어떻게 통합했고, 어떤 품질 검사를 거쳐 맵 단위 승패 샘플로 만들었는지**를 이 장에서 설명한다.

마지막 업데이트: 2026-06-05

## 데이터 계약

| 항목 | 정본 |
|---|---|
| 활성 소스 | Kaggle 계열 CSV + VLR.gg 수집 데이터 (`source` prefix `kaggle_`/`vlrgg_`) |
| 제외 소스 | Riot 공식 API, HenrikDev API, Liquipedia scraping |
| 학습 단위 | 맵 단위 승패 샘플(BO 시리즈 수 아님) |
| 런타임 재현 입력 | 맵 + 팀A 선수/요원 5명 + 팀B 선수/요원 5명 |
| 모델 피처 | baseline 421 / advanced 179 |

## 채택 데이터셋 요약

| 등급 | Kaggle ID | 역할 |
|---|---|---|
| 핵심 | `ryanluong1/valorant-champion-tour-2021-2023-data` | VCT 2021~2023 중심 소스 |
| 핵심 | `ryanluong1/valorant-challengers-league-data` | Challengers 대용량 보강 |
| 핵심 | `qualidea1217/valorant-pro-matches-since-april-2021` | 프로 경기 보강 및 공수 분리 스탯 |
| 보조 | `ediashtarevin/vct-champions-2023-stats` | 2023 Champions 보조 검증 |
| 보조 | `piyush86kumar/valorant-champions-2024` | 중복 제거 후 일부 보강 |

현재 active 모델은 VLR.gg 수집 스냅샷을 포함한다. Riot 공식 API·HenrikDev API·Liquipedia 스크래핑은 재현성·수집 안정성 리스크 때문에 최종 평가 범위에서 제외한다.

## 보고서 흐름

| 순서 | 문서 | 설명 |
|---:|---|---|
| 1 | [01_overview/01_current_status.md](./01_overview/01_current_status.md) | 현재 데이터 볼륨과 모델 산출물 연결 |
| 2 | [01_overview/02_data_gap_analysis.md](./01_overview/02_data_gap_analysis.md) | Kaggle+VLR.gg 통합 데이터로 해소된 갭과 남은 한계 |
| 3 | [06_additional_kaggle/01_dataset_catalog.md](./06_additional_kaggle/01_dataset_catalog.md) | 데이터셋 카탈로그 |
| 4 | [07_data_schema/01_unified_schema.md](./07_data_schema/01_unified_schema.md) | 파서 공통 스키마 |
| 5 | [08_feature_engineering/01_current_features.md](./08_feature_engineering/01_current_features.md) | 초기 설계와 실제 421/179 피처 차이 |
| 6 | [09_data_quality/01_quality_metrics.md](./09_data_quality/01_quality_metrics.md) | 품질 검사, dedup, 결측 처리 |
| 7 | [10_data_volume/03_accuracy_requirements.md](./10_data_volume/03_accuracy_requirements.md) | 초기 성능 기대치와 실측 성능 비교 |

## 근거 산출물

| 산출물 | 의미 |
|---|---|
| `reports/preprocess/` | 전처리 요약과 reject 기록 |
| `reports/baseline/metrics.json` | baseline 421 features 학습/평가 결과 |
| `models/advanced/meta.json` | advanced 179 features feature names와 source contract |
| `reports/advanced/validation.json` | source prefix, feature count, split overlap, forbidden feature 검증 |

## 빠른 탐색

| 목적 | 문서 |
|---|---|
| 데이터셋 전체 현황 | [01_current_status](./01_overview/01_current_status.md) |
| 파서별 컬럼 매핑 | [04_column_definitions](./07_data_schema/04_column_definitions.md) |
| 29종 요원 역할군 | [02_agent_role_mapping](./07_data_schema/02_agent_role_mapping.md) |
| 13개 맵 목록 | [03_map_database](./07_data_schema/03_map_database.md) |
| 피처 목록 | [01_current_features](./08_feature_engineering/01_current_features.md) |
| 품질 지표 및 검사 기준 | [01_quality_metrics](./09_data_quality/01_quality_metrics.md) |
