# 07. 데이터 문서 인덱스

ValoPredictML의 데이터 전략, 소스, 스키마, 피처 엔지니어링 전반을 다루는 문서 모음.

---

## 빠른 탐색

| 목적 | 문서 |
|------|------|
| 현재 데이터 현황 파악 | [01_current_status](./01_overview/01_current_status.md) |
| 데이터 부족 원인 분석 | [02_data_gap_analysis](./01_overview/02_data_gap_analysis.md) |
| 수집 전략 전체 로드맵 | [03_collection_strategy](./01_overview/03_collection_strategy.md) |
| Kaggle VCT 2021-2023 다운로드 | [01_vct_2021_2023](./02_primary_datasets/01_vct_2021_2023.md) |
| Riot 공식 대용량 데이터 | [01_vct_hackathon_overview](./03_riot_official_data/01_vct_hackathon_overview.md) |
| S3 다운로드 방법 | [02_s3_download_guide](./03_riot_official_data/02_s3_download_guide.md) |
| HenrikDev API 수집 | [01_henrikdev_api](./04_api_sources/01_henrikdev_api.md) |
| 추가 Kaggle 데이터셋 목록 | [01_dataset_catalog](./06_additional_kaggle/01_dataset_catalog.md) |
| 피처 30+ 확장 설계 | [02_additional_features](./08_feature_engineering/02_additional_features.md) |
| 80% 정확도 요구사항 | [03_accuracy_requirements](./10_data_volume/03_accuracy_requirements.md) |

---

## 폴더 구조

```
docs/07_data/
├── README.md                                    ← 이 파일
│
├── 01_overview/                                 # 현황·갭 분석·전략
│   ├── 01_current_status.md
│   ├── 02_data_gap_analysis.md
│   └── 03_collection_strategy.md
│
├── 02_primary_datasets/                         # 핵심 데이터셋
│   ├── 01_vct_2021_2023.md
│   ├── 02_vct_2024.md
│   └── 03_valorant_ranked.md
│
├── 03_riot_official_data/                       # Riot 공식 VCT 데이터
│   ├── 01_vct_hackathon_overview.md
│   ├── 02_s3_download_guide.md
│   └── 03_data_structure.md
│
├── 04_api_sources/                              # API 수집
│   ├── 01_henrikdev_api.md
│   ├── 02_riot_official_api.md
│   └── 03_valorant_api_com.md
│
├── 05_scraping_sources/                         # 웹 스크래핑
│   ├── 01_vlr_gg.md
│   └── 02_liquipedia.md
│
├── 06_additional_kaggle/                        # 추가 Kaggle 데이터셋
│   ├── 01_dataset_catalog.md
│   └── 02_evaluation_criteria.md
│
├── 07_data_schema/                              # 데이터 스키마
│   ├── 01_unified_schema.md
│   ├── 02_agent_role_mapping.md
│   ├── 03_map_database.md
│   └── 04_column_definitions.md
│
├── 08_feature_engineering/                      # 피처 엔지니어링
│   ├── 01_current_features.md
│   ├── 02_additional_features.md
│   └── 03_feature_selection.md
│
├── 09_data_quality/                             # 데이터 품질
│   ├── 01_quality_metrics.md
│   ├── 02_validation_rules.md
│   └── 03_known_issues.md
│
└── 10_data_volume/                              # 데이터 볼륨
    ├── 01_current_volume.md
    ├── 02_target_volume.md
    └── 03_accuracy_requirements.md
```

---

## 전체 문서 목록

### 01_overview — 현황·갭 분석·전략

| 파일 | 내용 |
|------|------|
| [01_current_status.md](./01_overview/01_current_status.md) | 현재 데이터셋 현황, 볼륨, 한계 진단 |
| [02_data_gap_analysis.md](./01_overview/02_data_gap_analysis.md) | 80% 목표 달성에 필요한 데이터 갭 분석 |
| [03_collection_strategy.md](./01_overview/03_collection_strategy.md) | 소스별 우선순위, 단계별 수집 로드맵 |

### 02_primary_datasets — 핵심 데이터셋

| 파일 | 내용 |
|------|------|
| [01_vct_2021_2023.md](./02_primary_datasets/01_vct_2021_2023.md) | Kaggle VCT 2021-2023 완전 상세 |
| [02_vct_2024.md](./02_primary_datasets/02_vct_2024.md) | VCT 2024 추가 데이터셋 |
| [03_valorant_ranked.md](./02_primary_datasets/03_valorant_ranked.md) | 일반 유저 랭크 매치 데이터셋들 |

### 03_riot_official_data — Riot 공식 데이터

| 파일 | 내용 |
|------|------|
| [01_vct_hackathon_overview.md](./03_riot_official_data/01_vct_hackathon_overview.md) | Riot VCT S3 Hackathon 데이터 개요 |
| [02_s3_download_guide.md](./03_riot_official_data/02_s3_download_guide.md) | AWS S3 다운로드 가이드 및 코드 |
| [03_data_structure.md](./03_riot_official_data/03_data_structure.md) | 데이터 구조·JSON 파싱·피처 추출 |

### 04_api_sources — API 수집

| 파일 | 내용 |
|------|------|
| [01_henrikdev_api.md](./04_api_sources/01_henrikdev_api.md) | HenrikDev API v4 완전 상세 |
| [02_riot_official_api.md](./04_api_sources/02_riot_official_api.md) | Riot 공식 API 접근 방법 |
| [03_valorant_api_com.md](./04_api_sources/03_valorant_api_com.md) | valorant-api.com 메타 정보 API |

### 05_scraping_sources — 웹 스크래핑

| 파일 | 내용 |
|------|------|
| [01_vlr_gg.md](./05_scraping_sources/01_vlr_gg.md) | VLR.gg 스크래핑 전략·파서 설계 |
| [02_liquipedia.md](./05_scraping_sources/02_liquipedia.md) | Liquipedia MediaWiki API 활용 |

### 06_additional_kaggle — 추가 Kaggle 데이터셋

| 파일 | 내용 |
|------|------|
| [01_dataset_catalog.md](./06_additional_kaggle/01_dataset_catalog.md) | 발굴된 데이터셋 카탈로그 (10+개) |
| [02_evaluation_criteria.md](./06_additional_kaggle/02_evaluation_criteria.md) | 데이터셋 채택 기준·평가 매트릭스 |

### 07_data_schema — 데이터 스키마

| 파일 | 내용 |
|------|------|
| [01_unified_schema.md](./07_data_schema/01_unified_schema.md) | 전 소스 통합 스키마 |
| [02_agent_role_mapping.md](./07_data_schema/02_agent_role_mapping.md) | 에이전트-역할군 완전 매핑 (48종) |
| [03_map_database.md](./07_data_schema/03_map_database.md) | 맵 목록·특성·픽률 데이터 |
| [04_column_definitions.md](./07_data_schema/04_column_definitions.md) | 전체 컬럼 정의·타입·범위 |

### 08_feature_engineering — 피처 엔지니어링

| 파일 | 내용 |
|------|------|
| [01_current_features.md](./08_feature_engineering/01_current_features.md) | 현재 15개 피처 완전 상세 |
| [02_additional_features.md](./08_feature_engineering/02_additional_features.md) | 추가 30+ 피처 설계 (80% 달성 전략) |
| [03_feature_selection.md](./08_feature_engineering/03_feature_selection.md) | 피처 선택·중요도 분석·SHAP |

### 09_data_quality — 데이터 품질

| 파일 | 내용 |
|------|------|
| [01_quality_metrics.md](./09_data_quality/01_quality_metrics.md) | 품질 지표 정의·기준값 |
| [02_validation_rules.md](./09_data_quality/02_validation_rules.md) | 검증 규칙 및 구현 코드 |
| [03_known_issues.md](./09_data_quality/03_known_issues.md) | 알려진 문제점·처리 방법 |

### 10_data_volume — 데이터 볼륨

| 파일 | 내용 |
|------|------|
| [01_current_volume.md](./10_data_volume/01_current_volume.md) | 현재 볼륨 분석·부족 진단 |
| [02_target_volume.md](./10_data_volume/02_target_volume.md) | 목표 볼륨·단계별 수집 계획 |
| [03_accuracy_requirements.md](./10_data_volume/03_accuracy_requirements.md) | 80% 정확도 달성을 위한 요구사항 |

---

## 데이터 소스 우선순위 요약

| 우선순위 | 소스 | 예상 규모 | 채택 |
|---------|------|-----------|------|
| ⭐⭐⭐ 최우선 | Riot VCT S3 Hackathon | 수십만 경기 | ✅ |
| ⭐⭐⭐ 최우선 | Kaggle VCT 2021-2023 | ~2,000경기 | ✅ 기존 |
| ⭐⭐⭐ 최우선 | Kaggle VCT 2024 | ~1,000경기 | ✅ |
| ⭐⭐ 우선 | HenrikDev API | ~5,000경기 | ✅ 기존 |
| ⭐⭐ 우선 | Kaggle 랭크 매치 | 수만 경기 | ✅ |
| ⭐ 선택적 | VLR.gg 스크래핑 | 수천 경기 | 🔄 |
| ⭐ 선택적 | Liquipedia | 메타 보완 | 🔄 |
