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
피처 수:           baseline 178 / advanced 125 (구현 완료)
실측 Accuracy:     baseline 0.6290 / advanced 0.6958 (43피처 초기 추정치 대비 상회)
```

### 2.2 소스별 기여 추정

| 소스 | 선수 행 | 맵 행 환산 (÷10) |
|------|---------|----------------|
| vct_2021_2023 | ~600K | ~60K |
| ryanluong challengers | ~412K | ~41K |
| qualidea | ~250K | ~25K |
| ~~piyush 2024~~ (제거됨) | ~~~30K~~ | ~~~3K~~ |
| ~~piyush 2025~~ (제거됨) | ~~~15K~~ | ~~~1.5K~~ |
| ediashtarevin | ~6K | ~0.6K |
| ~~kierru~~ (제거됨) | ~5K | ~0.5K |
| **합계 (중복 제거 전)** | ~1,318K | ~130K |
| **중복 제거 후 예상** | — | **80~100K** |

---

## 3. 피처 갭

### 3.1 초기 설계 기준선 43개 (참고용 — 실제 구현: baseline 178 / advanced 125)

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
| KAST 결측 | ~~piyush 일부 이벤트에서 결측~~ (piyush 소스 제거됨) — 기타 소스에서 결측 발생 시 -1 플래그로 처리 |
| Clutch% 결측 | 일부 소스 없음 — 0으로 대체 |
| atk_side_advantage | ryanluong challengers `maps_scores.csv`에서만 집계 가능 |
| role_agent | ~~kierru~~(제거됨)만 직접 컬럼 보유했으나 파이프라인에서 제거. 나머지는 AGENT_ROLE_MAP 조회 |
| Team_Shared_Exp | visualize25 데이터셋 보류 — 미구현, 추후 재검토 |

---

## 4. 시간적 갭

| 기간 | 커버 소스 |
|------|---------|
| 2021~2023 | vct_2021_2023, qualidea, ediashtarevin, ~~kierru~~ (제거됨) |
| 2023~2024 | ryanluong challengers, qualidea |
| 2024 | ~~piyush 2024~~ (제거됨) |
| 2025 | ~~piyush 2025~~ (제거됨) |

~~2025년 신규 요원(Waylay, Tejo)·맵(Drift) 데이터는 piyush 2025 소스에만 존재.~~ (piyush 소스 제거됨)
시간 가중치(2024+ → 1.2, 2023 → 0.8, 2022 이하 → 0.6)로 구식 메타 영향 완화.

---

## 5. 갭 해결 결과

외부 소스 추가는 방침 외. 현재 7개 소스 내에서 갭이 해소되었다.

| 항목 | 목표 | 실제 결과 |
|------|------|----------|
| 총 맵 행 수 | 80K 이상 | 충족 (train+val+test 합산) |
| train 샘플 (advanced) | 56K 이상 | 53,427행 ✅ |
| test 샘플 | — | 13,357행 |
| Ensemble Test AUC | — | 0.7570 |

적용된 해결 방법:

1. 중복 제거 후 충분한 맵 행 확보
2. KAST 결측 → -1 플래그 처리
3. 공수 분리 스탯(atk_side_advantage) → ryanluong challengers 집계
4. 데이터가 섞이지 않게: match_key 단위 분할 + GroupKFold + 금지 피처 26개 + 이전 연도만 prior + smoothing

---

## 6. 참고 문서

- [01_current_status.md](./01_current_status.md)
- [../10_data_volume/03_accuracy_requirements.md](../10_data_volume/03_accuracy_requirements.md)
- [../08_feature_engineering/01_current_features.md](../08_feature_engineering/01_current_features.md)
