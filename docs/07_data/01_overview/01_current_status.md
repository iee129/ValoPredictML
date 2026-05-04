# 01. 현재 데이터셋 현황

마지막 업데이트: 2026-05-04

---

## 1. 채택 데이터셋 전체 현황

본 프로젝트는 Kaggle 7개 데이터셋만 사용한다. 외부 API·스크래핑은 방침상 미사용.

| # | 등급 | Kaggle ID | 용량 | 파서 | 소스 가중치 | 행 수 (추정) |
|---|------|-----------|------|------|------------|------------|
| 1 | 핵심 | `ryanluong1/valorant-champion-tour-2021-2023-data` | 1.2GB | ryanluong | 1.0 | ~600K (선수행) |
| 2 | 핵심 | `ryanluong1/valorant-challengers-league-data` | 1.0GB | ryanluong | **1.8** | ~412K (선수행) |
| 3 | 핵심 | `qualidea1217/valorant-pro-matches-since-april-2021` | ~35MB | qualidea | 1.0 | ~250K (선수행) |
| 4 | piyush | `piyush86kumar/valorant-champions-tour-2024-all-events` | ~15MB | piyush | **1.5** | ~30K (선수행) |
| 5 | piyush | `piyush86kumar/valorant-vct-2025-all-events` | — | piyush | **1.5** | ~15K (선수행) |
| 6 | 보조 | `ediashtarevin/vct-champions-2023-stats` | — | ediashtarevin | 0.9 | ~6K (선수행) |
| 7 | 보조 | `kierru/vctpacific-2023` | — | kierru | 0.9 | ~5K (선수행) |

**총 용량**: 2.3GB (`data/raw/kaggle/`, git 제외)

---

## 2. 데이터 볼륨 추정

```
선수 행 합계 (7개 소스): ~1,318K 행
경기 단위로 환산 (÷10): ~130K 맵 행
중복 제거 후 예상:       80~100K 맵 행
train/val/test 분할:    70/15/15
```

소스 가중치 정책: 동일 경기가 두 소스에 존재할 때 가중치가 높은 소스의 행을 보존.
동점이면 컬럼 수가 더 많은 행 보존.

---

## 3. 파이프라인 역할 매핑

| 파이프라인 단계 | 사용 데이터셋 |
|----------------|-------------|
| 파서 — ryanluong | `vct_2021_2023`, `ryanluong1__valorant-challengers-league-data` |
| 파서 — piyush | `piyush86kumar__2024-all-events`, `piyush86kumar__2025-all-events` |
| 파서 — qualidea | `qualidea1217__valorant-pro-matches-since-april-2021` |
| 보조 스탯 보강 | `ediashtarevin__vct-champions-2023-stats`, `kierru__vctpacific-2023` |
| atk_side_advantage 집계 | `ryanluong1__challengers` (`maps_scores.csv`) |
| role_agent 직접 추출 | `kierru__vctpacific-2023` (`role_agent` 컬럼) |
| 공수 분리 스탯 | `qualidea1217__*` (`acs-t`, `acs-ct`, `kd-t`, `kd-ct`) |

---

## 4. 구현 현황

| 항목 | 상태 |
|------|------|
| 데이터 다운로드 (`dataload.py`) | ✅ 완료 |
| 요원·맵 참조 테이블 (`ml/agent_roles.py`) | 미구현 |
| 전처리 파이프라인 (`ml/data_pipeline.py`) | 미구현 |
| 모델 학습 (`ml/train_model.py`) | 미구현 |
| Streamlit UI (`app/streamlit_app.py`) | 미구현 |

전처리 계획 상세: `.omc/plans/preprocessing.md`

---

## 5. 참고 문서

- [02_data_gap_analysis.md](./02_data_gap_analysis.md)
- [03_collection_strategy.md](./03_collection_strategy.md)
- [../10_data_volume/01_current_volume.md](../10_data_volume/01_current_volume.md)
