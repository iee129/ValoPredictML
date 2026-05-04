# 02. 데이터 갭 분석

마지막 업데이트: 2026-05-04

---

## 1. 개요

본 프로젝트의 데이터 소스는 Kaggle 7개 데이터셋으로 확정되어 있다.
외부 API(HenrikDev, Riot 공식)·스크래핑(VLR.gg, Liquipedia)은 방침상 미사용.

이 문서는 채택된 7개 소스 내에서 존재하는 갭을 분석한다.

---

## 2. 볼륨 갭

### 2.1 현재 vs 목표

```
                  현재 (7개 소스)   목표
총 맵 행 수:       80~100K (예상)   80K 이상이면 충분
train 샘플:        56~70K          56K 이상
피처 수:           43              43 (확정)
예상 Accuracy:     58~65%          58~65% (구조적 상한)
```

### 2.2 소스별 기여 추정

| 소스 | 선수 행 | 맵 행 환산 (÷10) |
|------|---------|----------------|
| vct_2021_2023 | ~600K | ~60K |
| ryanluong challengers | ~412K | ~41K |
| qualidea | ~250K | ~25K |
| piyush 2024 | ~30K | ~3K |
| piyush 2025 | ~15K | ~1.5K |
| ediashtarevin | ~6K | ~0.6K |
| kierru | ~5K | ~0.5K |
| **합계 (중복 제거 전)** | ~1,318K | ~130K |
| **중복 제거 후 예상** | — | **80~100K** |

---

## 3. 피처 갭

### 3.1 현재 피처 43개 카테고리

| 카테고리 | 피처 수 |
|---------|---------|
| 역할군 카운트 | 12 |
| 역할군 파생 (이진) | 4 |
| 선수 스탯 | 12 |
| 시너지 | 6 |
| 요원 조합 | 6 |
| 맵 | 3 |
| **합계** | **43** |

### 3.2 알려진 데이터 한계

| 항목 | 내용 |
|------|------|
| KAST 결측 | piyush 일부 이벤트에서 결측 — -1 플래그로 처리 |
| Clutch% 결측 | 일부 소스 없음 — 0으로 대체 |
| atk_side_advantage | ryanluong challengers `maps_scores.csv`에서만 집계 가능 |
| role_agent | kierru만 직접 컬럼 보유, 나머지는 AGENT_ROLE_MAP 조회 |
| Team_Shared_Exp | visualize25 데이터셋 보류 — 미구현, 추후 재검토 |

---

## 4. 시간적 갭

| 기간 | 커버 소스 |
|------|---------|
| 2021~2023 | vct_2021_2023, qualidea, ediashtarevin, kierru |
| 2023~2024 | ryanluong challengers, qualidea |
| 2024 | piyush 2024 |
| 2025 | piyush 2025 |

2025년 신규 요원(Waylay, Tejo)·맵(Drift) 데이터는 piyush 2025 소스에만 존재.
시간 가중치(2024+ → 1.2, 2023 → 0.8, 2022 이하 → 0.6)로 구식 메타 영향 완화.

---

## 5. 갭 해결 방침

외부 소스 추가는 방침 외. 현재 7개 소스 내에서:

1. 중복 제거 후 80~100K 맵 행 확보
2. KAST 결측은 -1 플래그 또는 팀 평균 imputation
3. 공수 분리 스탯(atk_side_advantage)은 ryanluong challengers 집계
4. A/B swap 증강으로 train 행 수 2배 확보

---

## 6. 참고 문서

- [01_current_status.md](./01_current_status.md)
- [../10_data_volume/03_accuracy_requirements.md](../10_data_volume/03_accuracy_requirements.md)
- [../08_feature_engineering/01_current_features.md](../08_feature_engineering/01_current_features.md)
