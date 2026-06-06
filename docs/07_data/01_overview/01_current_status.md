# 01. 현재 데이터셋 현황

마지막 업데이트: 2026-06-05

---

## 1. 채택 데이터셋 전체 현황

현행 advanced 모델은 Kaggle 5개 데이터셋과 VLR.gg 수집 데이터를 통합해 사용한다. 행 단위는 BO 시리즈 전체 경기가 아니라 **맵 단위 승패 샘플**이다.

| # | 등급 | Kaggle ID | 용량 | 파서 | 소스 가중치 | 행 수 (추정) |
|---|------|-----------|------|------|------------|------------|
| 1 | 핵심 | `ryanluong1/valorant-champion-tour-2021-2023-data` | 1.2GB | ryanluong | 1.0 | ~600K (선수행) |
| 2 | 핵심 | `ryanluong1/valorant-challengers-league-data` | 1.0GB | ryanluong | **1.8** | ~412K (선수행) |
| 3 | 핵심 | `qualidea1217/valorant-pro-matches-since-april-2021` | ~35MB | qualidea | 1.0 | ~250K (선수행) |
| 4 | ~~piyush~~ ❌ 제거됨 | `piyush86kumar/valorant-champions-tour-2024-all-events` | ~15MB | ~~piyush~~ (제거됨) | — | ~30K (선수행) |
| 5 | ~~piyush~~ ❌ 제거됨 | `piyush86kumar/valorant-vct-2025-all-events` | — | ~~piyush~~ (제거됨) | — | ~15K (선수행) |
| 6 | 보조 | `ediashtarevin/vct-champions-2023-stats` | — | ediashtarevin | 0.9 | ~6K (선수행) |
| 7 | ~~보조~~ | `kierru/vctpacific-2023` | — | kierru | 0.9 (제거됨 — 리젝션율 80%로 제거) | ~5K (선수행) |

**총 용량**: 2.3GB (`data/raw/kaggle/`, git 제외)

---

## 2. 데이터 볼륨 추정

```
선수 행 합계 (7개 소스): ~1,318K 행
경기 단위로 환산 (÷10): ~130K 맵 행
processed 맵 단위 승패 후보: 91,459
advanced 학습/평가 샘플:    91,458 (train 75,405 / test 16,053)
```

소스 가중치 정책: 동일 경기가 두 소스에 존재할 때 가중치가 높은 소스의 행을 보존.
동점이면 컬럼 수가 더 많은 행 보존.

---

## 3. 파이프라인 역할 매핑

| 파이프라인 단계 | 사용 데이터셋 |
|----------------|-------------|
| 파서 — ryanluong | `vct_2021_2023`, `ryanluong1__valorant-challengers-league-data` |
| ~~파서 — piyush~~ | ~~`piyush86kumar__2024-all-events`, `piyush86kumar__2025-all-events`~~ (제거됨) |
| 파서 — qualidea | `qualidea1217__valorant-pro-matches-since-april-2021` |
| 보조 스탯 보강 | `ediashtarevin__vct-champions-2023-stats`, ~~`kierru__vctpacific-2023`~~ (제거됨) |
| atk_side_advantage 집계 | `ryanluong1__challengers` (`maps_scores.csv`) |
| role_agent 직접 추출 | ~~`kierru__vctpacific-2023`~~ (제거됨 — 리젝션율 80%) |
| 공수 분리 스탯 | `qualidea1217__*` (`acs-t`, `acs-ct`, `kd-t`, `kd-ct`) |

---

## 4. 구현 현황

| 항목 | 상태 |
|------|------|
| 데이터 다운로드 (`src/data/dataload.py`) | ✅ 완료 |
| 요원·맵 참조 테이블 (`src/domain/valorant.py`) | ✅ 완료 |
| raw 정제 진입점 (`src/data/raw_preprocess.py`) | ✅ 완료 |
| 전처리 파이프라인 (`src/features/preprocess.py`) | ✅ 완료 |
| 모델 학습 (`src/ml/baseline/train.py` / `src/ml/advanced/ensemble.py`) | ✅ 완료 |
| 웹 스택 (FastAPI `src/api` + Next.js `web`) | ✅ 완료 |

---

## 5. ML 파이프라인 완료 결과

### Baseline (src/ml/baseline/) — 중간발표 기준
| 항목 | 수치 |
|------|------|
| 피처 수 | 421 (슬롯 선수 400 + 매치 컨텍스트 21) |
| 모델 | LR + DT Soft Voting (0.50 / 0.50) |
| 분할 | 랜덤 Train 80% / Test 20% |
| Test AUC | 0.5943 |
| Accuracy | 0.5667 |
| F1 | 0.6072 |
| 레이블 총계 | 21,258 (A승 42.0% / B승 58.0%) |

### Advanced (src/ml/advanced/)
| 항목 | 수치 |
|------|------|
| 피처 수 | 179 |
| 모델 | RF + XGBoost + LightGBM Soft Voting (2.0 : 3.0 : 0.1) |
| 분할 | 시간순(chrono): train 2020–2025 / test 2026 |
| 샘플 단위 | 맵 단위 승패 샘플 91,458개(BO 시리즈 수 아님) |
| Test AUC | 0.7010 |
| Accuracy | 0.6454 |
| F1 | 0.6478 |
| verdict | 신뢰 가능 |

- Ensemble: Random Forest + XGBoost + LightGBM soft voting (가중치 2.0 : 3.0 : 0.1)
- 데이터가 섞이지 않게: 시간순 분할 + 금지 피처 패턴 + 이전 연도만 prior + smoothing(PLAYER_PRIOR_SMOOTHING_GAMES=5.0)

---

## 6. 참고 문서

- [02_data_gap_analysis.md](./02_data_gap_analysis.md)
- [03_collection_strategy.md](./03_collection_strategy.md)
- [../10_data_volume/01_current_volume.md](../10_data_volume/01_current_volume.md)
