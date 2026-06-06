# 03. 데이터 수집 전략

마지막 업데이트: 2026-05-04

---

## 1. 전략 개요

현행 active 데이터 소스는 Kaggle 5개 데이터셋 + VLR.gg 수집 스냅샷이다. Riot 공식 API·HenrikDev API·Liquipedia 스크래핑은 범위 밖이다.
수집은 `src/data/dataload.py`로 이미 완료(2.3GB). 전처리 파이프라인(`src/data/raw_preprocess.py` → `src/features/preprocess.py`) 및 ML 모델 학습 완료.

---

## 2. 데이터 소스 구성

| 소스 | Kaggle ID | 다운로드 상태 |
|------|-----------|-------------|
| vct_2021_2023 | `ryanluong1/valorant-champion-tour-2021-2023-data` | ✅ 완료 |
| challengers | `ryanluong1/valorant-challengers-league-data` | ✅ 완료 |
| qualidea | `qualidea1217/valorant-pro-matches-since-april-2021` | ✅ 완료 |
| ~~piyush 2024~~ | `piyush86kumar/valorant-champions-tour-2024-all-events` | ❌ 제거됨 (데이터셋 폴더 및 파서 삭제) |
| ~~piyush 2025~~ | `piyush86kumar/valorant-vct-2025-all-events` | ❌ 제거됨 (데이터셋 폴더 및 파서 삭제) |
| ediashtarevin | `ediashtarevin/vct-champions-2023-stats` | ✅ 완료 |
| kierru | `kierru/vctpacific-2023` | ❌ 제거됨 (다운로드는 완료되었으나 파이프라인에서 제거 — 리젝션율 80%, 26행만 통과) |

---

## 3. 전처리 파이프라인 진행 순서

### Phase 1 — 파싱 (src/data/raw_preprocess.py → src/features/preprocess.py)

```
parse_ryanluong("data/raw/kaggle/vct_2021_2023")
parse_ryanluong("data/raw/kaggle/ryanluong1__valorant-challengers-league-data")
parse_qualidea ("data/raw/kaggle/qualidea1217__*")
parse_edia     ("data/raw/kaggle/ediashtarevin__*")
# parse_piyush("data/raw/kaggle/piyush86kumar__*")  # 제거됨 — 데이터셋 폴더 및 파서 삭제
# parse_kierru("data/raw/kaggle/kierru__*")  # 제거됨 — 리젝션율 80%, 26행만 통과
→ 공통 스키마 행 리스트로 병합
```

### Phase 2 — 품질 검사 + dedup

- 팀당 요원 5명, AGENT_ROLE_MAP 존재, 유효 맵, 유효 레이블 확인
- `dedup_key` (24자 SHA-1) 기준 중복 제거 — 가중치 높은 소스 우선

### Phase 3 — 피처 엔지니어링

- baseline 계약: 421개 / advanced 계약: 179개 피처 생성 (--feature-contract 인자로 분기)
- 사전 집계(atk_side_advantage, agent_map_stats, agent_experience)는 train.csv 기준

### Phase 4 — 분할

- match_key 단위 GroupShuffleSplit → train 80% / test 20% (별도 검증셋 없이 train 내부 GroupKFold로 튜닝)
- 데이터가 섞이지 않게: match_key 단위 분할 + GroupKFold + 금지 피처 26개 + 이전 연도만 prior + smoothing

---

## 4. 실행 명령

```bash
# raw 정제 (진입점)
python -m ml.raw_preprocess

# baseline reference artifact
python -m ml.baseline.reference

# advanced 시간순 전처리
python -m features.chrono_preprocess --include-vlrgg
```

---

## 5. 참고 문서

- [../06_additional_kaggle/01_dataset_catalog.md](../06_additional_kaggle/01_dataset_catalog.md)
- [../07_data_schema/04_column_definitions.md](../07_data_schema/04_column_definitions.md)
- [../09_data_quality/01_quality_metrics.md](../09_data_quality/01_quality_metrics.md)
