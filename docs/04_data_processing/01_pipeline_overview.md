# 01. 데이터 전처리 파이프라인 개요

마지막 업데이트: 2026-05-05

> **구현 완료** — `ml/data_pipeline.py` 전체 파이프라인 구현 완료.
> 실행 결과: clean 66,485행 → train 93,078행 / val 9,973행 / test 9,973행.

## 1. 파이프라인 전체 흐름

```
[데이터 소스: Kaggle CSV 7개 — 외부 API 미사용]
  vct_2021_2023 (ryanluong, 소스 가중치 1.0)
  ryanluong1__challengers (소스 가중치 1.8)
  qualidea1217__* (소스 가중치 1.0)
  ediashtarevin__* (소스 가중치 0.9)
         |
         v
  [Phase 1: 파싱 — 소스별 파서 3종]
    parse_ryanluong / parse_qualidea
    parse_ediashtarevin
    → 공통 스키마 행 리스트 (match_key 16자, dedup_key 24자 SHA-1)
         |
         v
  [Phase 2: 정규화]
    normalize_agent() / normalize_map() / normalize_team()
    컬럼명 snake_case 통일 (hs%/hs_percent/HS% → hs)
         |
         v
  [Phase 3: 품질 게이트]
    팀당 요원 5명 / AGENT_ROLE_MAP 존재 / MAP_ORDER 존재
    유효 레이블 / ACS·KD 비결측 / 소스 비중 <20% / 동점 제외
    탈락 행 → reports/rejected_matches.csv
         |
         v
  [Phase 4: dedup_key 중복 제거]
    소스 가중치 높은 행 보존 (동점 시 컬럼 수 우선)
    → data/processed/matches_clean.csv
         |
         v
  [Phase 5: 데이터 분할]
    match_key 단위 GroupShuffleSplit, seed=42
    70% train / 15% val / 15% test
         |
         v
  [Phase 6: 피처 사전 집계 — train.csv만 사용]
    atk_side_advantage / agent_map_stats / agent_experience
    → val/test에 join (신규 조합: winrate=0.5, experience=0)
         |
         v
  [Phase 7: 피처 엔지니어링]
    FEATURE_COLS_P1(19): 역할군 카운트 8 + diff 4 + 파생 4 + 맵 3
    FEATURE_COLS_P2(24): 선수 스탯 10 + 시너지 6 + 요원 조합 6 + kast_std 2
    = 43개 피처 + 1 레이블
         |
         v
  [Phase 8: A/B swap 증강 — train 한정]
    --no-augment-train 플래그로 비활성화 가능
         |
         v
  [Phase 9: sample_weight 계산]
    time_weight × source_weight
    (≤2022: 0.6 / 2023: 0.8 / 2024+: 1.2)
         |
         v
  [저장]
    data/processed/features_base.csv
    data/processed/train.csv / val.csv / test.csv
    reports/preprocess_summary.json
```

---

## 2. 각 단계 목적

| 단계 | 스크립트 | 목적 | 주요 출력 |
|------|----------|------|-----------|
| 파싱 | `ml/parsers/*.py` | 소스별 CSV → 공통 스키마 | 행 리스트 |
| 정규화 | `ml/agent_roles.py` | 요원·맵·팀명 통일 | 정규화된 행 |
| 품질 게이트 | `ml/data_pipeline.py` | 불완전 행 제거 | 클린 행 리스트 |
| dedup | `ml/data_pipeline.py` | 소스 중복 제거 | matches_clean.csv |
| 분할 | `ml/data_pipeline.py` | 경기 단위 그룹 분할 | train/val/test |
| 피처 집계 | `ml/data_pipeline.py` | train 기준 통계 집계 | 집계 테이블 |
| 피처 생성 | `ml/data_pipeline.py` | P1(19) + P2(24) = 43개 피처 생성 | features_base.csv |
| 증강 | `ml/data_pipeline.py` | A/B swap (train 전용) | 66,485 → 93,078행 |

---

## 3. 데이터 볼륨 (실측)

| 소스 | 소스 식별자 | 소스 가중치 |
|------|------------|------------|
| vct_2021_2023 | `kaggle_vct` | 1.0 |
| ryanluong challengers | `kaggle_challengers` | 1.8 |
| qualidea1217 | `kaggle_qualidea` | 1.0 |
| ediashtarevin | `kaggle_ediashtarevin` | 0.9 |

품질 게이트 + dedup 통과: **66,485 맵 행**.
A/B swap 증강 후 train: **93,078행** / val: **9,973행** / test: **9,973행**.

---

## 4. 품질 기준

| 항목 | 기준 | 실패 시 처리 |
|------|------|-------------|
| 팀당 요원 수 | 정확히 5명 | 해당 맵 행 제외 |
| 요원 유효성 | AGENT_ROLE_MAP에 모두 존재 | 행 제거 |
| 맵 유효성 | MAP_ORDER 12개 중 하나 | 행 제거 |
| 레이블 유효성 | winner가 team_a 또는 team_b | 행 제거 |
| 핵심 스탯 결측 | ACS·KD 비결측 | 행 제거 |
| 소스 비중 | 단일 소스 < 전체의 20% | under-sampling |
| 동점 | score_a ≠ score_b | 행 제거 |

---

## 5. 스크립트 실행 가이드

```bash
# 1. Kaggle 데이터 다운로드 (최초 1회, ~/.kaggle/kaggle.json 필요)
python dataload.py

# 2. 전처리 파이프라인 전체 실행
python -m ml.data_pipeline \
  --input data/raw/kaggle \
  --output data/processed \
  --reports reports

# 3. dry-run (원본 무수정)
python -m ml.data_pipeline \
  --input data/raw/kaggle \
  --output /tmp/valo_out \
  --reports /tmp/valo_reports

# 4. A/B swap 증강 비활성화
python -m ml.data_pipeline ... --no-augment-train
```

---

## 6. 관련 문서

| 문서 | 내용 |
|------|------|
| [02_data_collection.md](02_data_collection.md) | 7개 Kaggle 데이터셋 수집 방법 |
| [03_data_loading.md](03_data_loading.md) | 소스별 파서 및 컬럼 매핑 |
| [04_data_cleaning.md](04_data_cleaning.md) | 품질 게이트 및 dedup |
| [05_aggregation.md](05_aggregation.md) | 선수 행 → 맵 행 집계 |
| [06_feature_engineering.md](06_feature_engineering.md) | 43개 피처 생성 상세 |
| [07_split_and_validation.md](07_split_and_validation.md) | 데이터 분할 및 검증 |
