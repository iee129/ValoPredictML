# 07. 데이터 문서 인덱스

ValoPredictML의 데이터 소스, 스키마, 피처 엔지니어링 전반을 다루는 문서 모음.

데이터 소스: Kaggle 7개 데이터셋 (총 2.3GB, `data/raw/kaggle/`). 외부 API·스크래핑은 본 프로젝트 방침상 미사용.

마지막 업데이트: 2026-05-04

---

## 채택 데이터셋 요약

| 등급 | Kaggle ID | 용량 | 파서 | 소스 가중치 |
|------|-----------|------|------|------------|
| 핵심 | `ryanluong1/valorant-champion-tour-2021-2023-data` | 1.2GB | ryanluong | 1.0 |
| 핵심 | `ryanluong1/valorant-challengers-league-data` | 1.0GB | ryanluong | **1.8** |
| 핵심 | `qualidea1217/valorant-pro-matches-since-april-2021` | 35MB | qualidea | 1.0 |
| piyush | `piyush86kumar/valorant-champions-tour-2024-all-events` | ~15MB | piyush | **1.5** |
| piyush | `piyush86kumar/valorant-vct-2025-all-events` | — | piyush | **1.5** |
| 보조 | `ediashtarevin/vct-champions-2023-stats` | — | ediashtarevin | 0.9 |
| 보조 | `kierru/vctpacific-2023` | — | kierru | 0.9 |

다운로드: `python dataload.py` (`~/.kaggle/kaggle.json` 필요)

---

## 폴더 구조

```
docs/07_data/
├── README.md
├── 01_overview/
│   ├── 01_current_status.md       — 7개 데이터셋 현황 및 볼륨
│   ├── 02_data_gap_analysis.md    — 갭 분석 (범위 외 소스 제거)
│   └── 03_collection_strategy.md — Kaggle 전용 수집 전략
├── 02_primary_datasets/
│   ├── 01_vct_2021_2023.md        — ryanluong vct_2021_2023 상세
│   ├── 02_vct_2024.md             — piyush 2024/2025 상세
│   └── 03_valorant_ranked.md      — 보조 2개 데이터셋
├── 03_riot_official_data/         — 범위 외 (외부 API 미사용 방침)
├── 04_api_sources/                — 범위 외 (외부 API 미사용 방침)
├── 05_scraping_sources/           — 범위 외 (스크래핑 미사용 방침)
├── 06_additional_kaggle/
│   ├── 01_dataset_catalog.md      — 7개 채택 데이터셋 명세
│   └── 02_adoption_criteria.md    — 채택 기준
├── 07_data_schema/
│   ├── 01_unified_schema.md       — 파서 공통 출력 스키마
│   ├── 02_agent_role_mapping.md   — 27종 AGENT_ROLE_MAP
│   ├── 03_map_database.md         — 12개 맵 MAP_ORDER
│   └── 04_column_definitions.md   — 소스별 컬럼 정의
├── 08_feature_engineering/
│   ├── 01_current_features.md     — 43개 피처 전체 목록
│   ├── 02_additional_features.md  — 피처 확장 설계
│   └── 03_feature_selection.md    — 중요도 분석 계획
├── 09_data_quality/
│   ├── 01_quality_metrics.md      — 품질 게이트 기준
│   ├── 02_validation_rules.md     — 검증 규칙
│   └── 03_known_issues.md         — 알려진 리스크 R1~R8
└── 10_data_volume/
    ├── 01_current_volume.md       — 2.3GB / 80~100K 맵 행 예상
    ├── 02_target_volume.md        — 목표 볼륨
    └── 03_accuracy_requirements.md — Accuracy 58~65% 가설
```

---

## 빠른 탐색

| 목적 | 문서 |
|------|------|
| 데이터셋 전체 현황 | [01_current_status](./01_overview/01_current_status.md) |
| 파서별 컬럼 매핑 | [04_column_definitions](./07_data_schema/04_column_definitions.md) |
| 27종 요원 역할군 | [02_agent_role_mapping](./07_data_schema/02_agent_role_mapping.md) |
| 12개 맵 목록 | [03_map_database](./07_data_schema/03_map_database.md) |
| 43개 피처 목록 | [01_current_features](./08_feature_engineering/01_current_features.md) |
| 품질 게이트 기준 | [01_quality_metrics](./09_data_quality/01_quality_metrics.md) |
| 예상 성능 범위 | [03_accuracy_requirements](./10_data_volume/03_accuracy_requirements.md) |
