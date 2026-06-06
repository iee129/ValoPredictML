# 01. 데이터 전처리 파이프라인 개요

마지막 업데이트: 2026-05-05

> **구현 완료** — `src/features/preprocess.py` 전처리 파이프라인 구현 완료.
> 현행 advanced 실행 결과: train 75,405개 + test 16,053개 = 총 91,458개 **맵 단위 승패 샘플**. 이 값은 BO 시리즈 전체 경기 수가 아니라 모델 학습·평가 행 수다.

## 1. 파이프라인 전체 흐름

```
[데이터 소스: Kaggle CSV 5개 + VLR.gg 수집 데이터]
  vct_2021_2023 (ryanluong, 소스 가중치 1.0)
  ryanluong1__challengers (소스 가중치 1.8)
  qualidea1217__* (소스 가중치 1.0)
  ediashtarevin__* (소스 가중치 0.9)
  piyush86kumar/valorant-champions-2024 (소스 가중치 1.5)
         |
         v
  [Phase 1: 파싱 — src/data/raw_preprocess.py parser family]
    parse_ryanluong / parse_qualidea
    parse_ediashtarevin / parse_piyush2024
    → 공통 스키마 행 리스트 (match_key 16자, dedup_key 24자 SHA-1)
         |
         v
  [Phase 2: 정규화]
    normalize_agent() / normalize_map() / normalize_team()
    컬럼명 snake_case 통일 (hs%/hs_percent/HS% → hs)
         |
         v
  [Phase 3: 품질 검사]
    팀당 요원 5명 / AGENT_ROLE_MAP 존재 / MAP_ORDER 존재
    유효 레이블 / ACS·KD 비결측 / 소스 비중 <20% / 동점 제외
    탈락 행 → data/processed/rejects.csv
         |
         v
  [Phase 4: dedup_key 중복 제거]
    소스 가중치 높은 행 보존 (동점 시 컬럼 수 우선)
    → data/processed/matches.csv
         |
         v
  [Phase 5: 데이터 분할]
    match_key 단위 GroupShuffleSplit, seed=42
    80% train / 20% test
         |
         v
  [Phase 6: 피처 사전 집계 — train.csv만 사용]
    atk_side_advantage / agent_map_stats / agent_experience
    → val/test에 join (신규 조합: winrate=0.5, experience=0)
         |
         v
  [Phase 7: 피처 엔지니어링]
    baseline 계약: 421개 피처 (슬롯 선수 400 = 10슬롯 × [PRIOR 8 + 요원 one-hot 27 + 역할군 one-hot 5] + 매치 컨텍스트 21 = 맵 one-hot 12 + 팀 합동출전 3 + 역할 조합 prior 6)
    advanced 계약: 179개 피처 (Drift/Miks/저표본 요원·clutch 제거, rare는 other bucket, prior/synergy 계열 diff 포함)
    (구 FEATURE_COLS_P1/P2 43개 설계는 폐기됨)
         |
         v
  [Phase 8: sample_weight 계산]
    time_weight × source_weight
    (≤2022: 0.6 / 2023: 0.8 / 2024+: 1.2)
         |
         v
  [저장]
    data/processed/features_base.csv
    data/processed/train.csv / test.csv
    reports/preprocess_summary.json
```

---

## 2. 각 단계 목적

| 단계 | 스크립트 | 목적 | 주요 출력 |
|------|----------|------|-----------|
| 파싱 | `src/data/raw_preprocess.py` (parser family) | 소스별 CSV → 공통 스키마 | 행 리스트 |
| 정규화 | `src/domain/agent_roles.py` | 요원·맵·팀명 통일 | 정규화된 행 |
| 품질 검사 | `src/features/preprocess.py` | 불완전 행 제거 | 클린 행 리스트 |
| dedup | `src/features/preprocess.py` | 소스 중복 제거 | matches.csv |
| 분할 | `src/features/preprocess.py` | 경기 단위 그룹 분할 | train/val/test |
| 피처 집계 | `src/features/preprocess.py` | train 기준 통계 집계 | 집계 테이블 |
| 피처 생성 | `src/features/preprocess.py` | 피처 생성 (baseline 421 / advanced 179) | features_base.csv |
| sample_weight | `src/features/preprocess.py` | time_weight × source_weight 계산 | train.csv |

---

## 3. 데이터 볼륨 (실측)

| 소스 | 소스 식별자 | 소스 가중치 |
|------|------------|------------|
| vct_2021_2023 | `kaggle_vct` | 1.0 |
| ryanluong challengers | `kaggle_challengers` | 1.8 |
| qualidea1217 | `kaggle_qualidea` | 1.0 |
| ediashtarevin | `kaggle_ediashtarevin` | 0.9 |

품질 검사 + dedup 통과: **91,459개 맵 단위 승패 후보**.
advanced 분할: train **75,405개** / test **16,053개** 맵 단위 승패 샘플.

---

## 4. 품질 기준

| 항목 | 기준 | 실패 시 처리 |
|------|------|-------------|
| 팀당 요원 수 | 정확히 5명 | 해당 맵 행 제외 |
| 요원 유효성 | AGENT_ROLE_MAP에 모두 존재 | 행 제거 |
| 맵 유효성 | MAP_ORDER 13개 중 하나 | 행 제거 |
| 레이블 유효성 | winner가 team_a 또는 team_b | 행 제거 |
| 핵심 스탯 결측 | ACS·KD 비결측 | 행 제거 |
| 소스 비중 | 단일 소스 < 전체의 20% | under-sampling |
| 동점 | score_a ≠ score_b | 행 제거 |

---

## 5. 스크립트 실행 가이드

```bash
# 1. Kaggle 데이터 다운로드 (최초 1회, ~/.kaggle/kaggle.json 필요)
python -m data.dataload

# 2. 전처리 파이프라인 전체 실행 (baseline)
python -m features.preprocess \
  --input data/raw/kaggle \
  --output data/processed \
  --reports reports

# 3. dry-run (원본 무수정)
python -m features.preprocess \
  --input data/raw/kaggle \
  --output /tmp/valo_out \
  --reports /tmp/valo_reports

# 4. dry-run with custom reports path
python -m features.preprocess --input data/raw/kaggle --output /tmp/out --reports /tmp/rep
```

---

## 6. 관련 문서

| 문서 | 내용 |
|------|------|
| [02_data_collection.md](02_data_collection.md) | 5개 Kaggle 데이터셋 수집 방법 |
| [03_data_loading.md](03_data_loading.md) | 소스별 파서 및 컬럼 매핑 |
| [04_data_cleaning.md](04_data_cleaning.md) | 품질 검사 및 dedup |
| [05_aggregation.md](05_aggregation.md) | 선수 행 → 맵 행 집계 |
| [06_feature_engineering.md](06_feature_engineering.md) | baseline 421 / advanced 179 피처 생성 상세 |
| [07_split_and_validation.md](07_split_and_validation.md) | 데이터 분할 및 검증 |
