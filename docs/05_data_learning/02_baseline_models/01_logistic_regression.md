# 01. 베이스라인 (LR + DT soft voting)

마지막 업데이트: 2026-06-04

## 개요

베이스라인은 **로지스틱 회귀(LR)와 결정 트리(DT)의 soft voting**이다(강의 산출물 PDF 기준). 두 모델의 예측 확률을 0.50/0.50 동일 가중으로 평균한다. 데이터는 랜덤 Train 80% / Test 20%로 분할한다.

입력 계약은 UI와 같다.

```
맵 1개
팀 A 선수 5명 + 요원 5명
팀 B 선수 5명 + 요원 5명
```

팀명 기반 prior나 현재 경기 스코어/스탯은 모델 피처에 넣지 않는다. 선수 성능 피처는 현재 경기 연도보다 이전 연도의 기록만 사용한다.

세부 피처 명세: [../../04_data_processing/06_feature_engineering.md](../../04_data_processing/06_feature_engineering.md)

## 모델

학습기는 LR + DT soft voting이다.

| 구성 | 설정 |
|---|---|
| Logistic Regression | `StandardScaler` + `LogisticRegression` |
| Decision Tree | `DecisionTreeClassifier` |
| 결합 방식 | `VotingClassifier(voting="soft", weights=[0.5, 0.5])` — 동일 가중 |
| 데이터 분할 | 랜덤 Train 80% / Test 20% |
| 최종 평가 | `test` holdout |

## 피처

PDF 기준 베이스라인 피처는 **총 421개**다.

```
421 = 슬롯 400 + 컨텍스트 21
  슬롯 400 = 10슬롯 × (PRIOR 8 + 요원 ONE-HOT 27 + 역할군 ONE-HOT 5)
  컨텍스트 21 = 맵 12 + 합동출전 3 + 역할조합 PRIOR 6
```

## 성능 (PDF 기준, 랜덤 80/20)

| 모델 | AUC | Acc | F1 |
|---|---:|---:|---:|
| Logistic Regression 단독 | 0.6000 | 0.5821 | 0.6216 |
| Decision Tree 단독 | 0.5556 | 0.5483 | 0.5860 |
| **LR+DT soft voting (앙상블)** | **0.5943** | **0.5667** | **0.6072** |
| baseline_random (랜덤 추측) | 0.4864 | — | — |

앙상블은 majority 클래스 분류 대비 +0.0649 향상.

## 해석

이 baseline은 높은 숫자를 만들기 위해 현재 경기의 선수 스탯을 쓰지 않는다. pre-match 피처만 사용한 LR+DT soft voting AUC 0.5943은 이후 심화 모델(RF+XGB+LightGBM, 시간순 split AUC 0.7010)의 개선 기준선 역할을 한다. 베이스라인은 랜덤 분할, 심화는 시간순 분할을 사용하므로 두 AUC를 1:1로 직접 비교하지 않는다.

> 참고: Random Forest는 베이스라인이 아니라 심화 앙상블의 구성원이다. RF 관련 설명은 [02_random_forest.md](02_random_forest.md)와 `03_advanced_models/` 참조.
