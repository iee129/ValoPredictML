# 07. 데이터 문서 인덱스

ValoPredictML의 데이터 소스, 스키마, 피처 엔지니어링 전반을 다루는 문서 모음.

데이터 소스: Kaggle 활성 4개 소스 (총 7개 중 3개 제거됨, 총 2.3GB, `data/raw/kaggle/`). 외부 API·스크래핑은 본 프로젝트 방침상 미사용.

마지막 업데이트: 2026-05-06

---

## 채택 데이터셋 요약

| 등급 | Kaggle ID | 용량 | 파서 | 소스 가중치 |
|------|-----------|------|------|------------|
| 핵심 | `ryanluong1/valorant-champion-tour-2021-2023-data` | 1.2GB | ryanluong | 1.0 |
| 핵심 | `ryanluong1/valorant-challengers-league-data` | 1.0GB | ryanluong | **1.8** |
| 핵심 | `qualidea1217/valorant-pro-matches-since-april-2021` | 35MB | qualidea | 1.0 |
| 보조 | `ediashtarevin/vct-champions-2023-stats` | — | ediashtarevin | 0.9 |
| ~~보조~~ | ~~`kierru/vctpacific-2023`~~ | — | ~~kierru~~ | ~~0.9~~ (제거됨) |
| 보조 | `piyush86kumar/valorant-champions-2024` | — | piyush | 1.0 (dataload.py 포함, 중복 시 dedup 처리) |

다운로드: `python dataload.py` (`~/.kaggle/kaggle.json` 필요)

---

## 폴더 구조

```
docs/07_data/
├── README.md
├── 01_overview/
│   ├── 01_current_status.md       — 5개 데이터셋 현황 및 볼륨
│   ├── 02_data_gap_analysis.md    — 갭 분석 (범위 외 소스 제거)
│   └── 03_collection_strategy.md — Kaggle 전용 수집 전략
├── 02_primary_datasets/
│   ├── 01_vct_2021_2023.md        — ryanluong vct_2021_2023 상세
│   ├── 02_vct_2024.md             — ryanluong vct_2024/vct_2025 상세 (구 piyush 문서, 내용 갱신 필요)
│   └── 03_valorant_ranked.md      — 보조 2개 데이터셋
├── 03_riot_official_data/         — 범위 외 (외부 API 미사용 방침)
├── 04_api_sources/                — 범위 외 (외부 API 미사용 방침)
├── 05_scraping_sources/           — 범위 외 (스크래핑 미사용 방침)
├── 06_additional_kaggle/
│   ├── 01_dataset_catalog.md      — 채택 데이터셋 명세 (kierru 제거됨)
│   └── 02_adoption_criteria.md    — 채택 기준
├── 07_data_schema/
│   ├── 01_unified_schema.md       — 파서 공통 출력 스키마
│   ├── 02_agent_role_mapping.md   — 29종 AGENT_ROLE_MAP
│   ├── 03_map_database.md         — 13개 맵 MAP_ORDER
│   └── 04_column_definitions.md   — 소스별 컬럼 정의
├── 08_feature_engineering/
│   ├── 01_current_features.md     — 43개 피처 전체 목록
│   ├── 02_additional_features.md  — 피처 확장 설계
│   └── 03_feature_selection.md    — 중요도 분석 계획
├── 09_data_quality/
│   ├── 01_quality_metrics.md      — 품질 지표 및 품질 검사
│   ├── 02_validation_rules.md     — 검증 규칙
│   └── 03_known_issues.md         — 알려진 리스크 R1~R8
└── 10_data_volume/
    ├── 01_current_volume.md       — 2.3GB / 80~100K 맵 행 예상
    ├── 02_target_volume.md        — 목표 볼륨
    └── 03_accuracy_requirements.md — 초기 추정 58~65% vs 실측 Acc 0.6958·AUC 0.7570
```

---

## 데이터셋 관련성 종합 평가

| 데이터셋 | 관련성 | 이유 |
|----------|--------|------|
| `vct_2021_2023` | ★★★★★ | 6년치 T1 프로 경기 1.2GB, 핵심 학습 소스 |
| `ryanluong1__challengers` | ★★★★★ | T2 대용량 1.0GB, 공수 점수 분리, 소스 가중치 최고(1.8) |
| `qualidea1217__*` | ★★★★★ | 249K행, 공수 분리 스탯 유일 소스, 조인 불필요 |
| ~~`piyush86kumar__2024`~~ | ❌ 제거 | ryanluong vct_2024와 동일 대회 중복 |
| ~~`piyush86kumar__2025`~~ | ❌ 제거 | ryanluong vct_2025와 동일 대회 중복 |
| `ediashtarevin__*` | ★★★☆☆ | 2023 Champions 특화, 교차 검증용 |
| `kierru__vctpacific-2023` | ❌ 제거 | 리젝션율 80%, 26행만 통과 — 파이프라인에서 제거됨 |

---

## 빠른 탐색

| 목적 | 문서 |
|------|------|
| 데이터셋 전체 현황 | [01_current_status](./01_overview/01_current_status.md) |
| 파서별 컬럼 매핑 | [04_column_definitions](./07_data_schema/04_column_definitions.md) |
| 29종 요원 역할군 | [02_agent_role_mapping](./07_data_schema/02_agent_role_mapping.md) |
| 13개 맵 목록 | [03_map_database](./07_data_schema/03_map_database.md) |
| 피처 목록 (초기 설계 43개 / 실제 178·125개) | [01_current_features](./08_feature_engineering/01_current_features.md) |
| 품질 지표 및 검사 기준 | [01_quality_metrics](./09_data_quality/01_quality_metrics.md) |
| 예상 성능 범위 | [03_accuracy_requirements](./10_data_volume/03_accuracy_requirements.md) |
