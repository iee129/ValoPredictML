# 심화 모델 (시간순 holdout)

분할축 **시간순 holdout** × 모델축 **심화**. 2020~2025 맵 단위 승패 샘플로 학습하고 2026 샘플을 평가한 RF+XGB+LGBM soft voting 구성이다. 본 프로젝트의 유일한 심화 모델이며, 앱·웹·발표의 대표 모델이다.

출처: `reports/advanced/metrics.json`, `reports/advanced/validation.json`, `models/advanced/meta.json`.

## 1. 모델 정의

활성 advanced feature contract를 사용한다.

| 항목 | 값 |
|---|---|
| 알고리즘 | RF + XGBoost + LightGBM soft voting (가중치 2.0 : 3.0 : 0.1) |
| 피처 계약 | advanced 179 features |
| 샘플 단위 | 맵 단위 승패 샘플(BO 시리즈 수 아님) |
| 학습 기간 | 2020-2025 |
| 평가 기간 | 2026 |
| 요원 / 맵 | 요원 29종 / 맵 13종 |
| 소스 계열 | allowed source prefixes (`kaggle_*`, `vlrgg_*`) |

## 2. 데이터 분할

연도 블록 시간순 분할 — train은 2020–2025, test는 2026. train 연도가 test 연도보다 모두 앞선 **과거→미래** 구성이다.

이 분할은 랜덤 holdout보다 어려운 질문을 던진다. 같은 기간 분포 안에서 뺀 경기를 맞히는 것이 아니라, 학습 이후 시즌의 경기로 일반화를 점검한다.

## 3. 성능 지표

| 모델 | Test ROC-AUC |
|---|---:|
| RF | 0.6965 |
| XGBoost | 0.7007 |
| LightGBM | 0.7015 |
| **앙상블 (soft voting)** | **0.7010** |

| 지표 | 값 |
|---|---:|
| Test ROC-AUC | **0.7010** |
| Test Accuracy | **0.6454** |
| Test F1 | **0.6478** |

Validation verdict: `신뢰 가능` (`feature_count=179`, `split_overlap_count=0`, `source_prefix_check=정상`, `test AUC ≥ 0.70`).

## 4. 혼동 행렬 (시간순 holdout, test 2026)

> 출처: `reports/advanced/validation.json` / SSOT `final/deliverables/00_수치_단일진실표.md`

| | 예측: 팀A 승 | 예측: 팀B 승 |
|---|---:|---:|
| **실제: 팀B 승** | FP 2,867 | TN 5,124 |
| **실제: 팀A 승** | TP 5,236 | FN 2,826 |

행렬 전체: `[[5124, 2867], [2826, 5236]]`

| 셀 | 값 | 의미 |
|---|---:|---|
| TN (True Negative) | 5,124 | 팀B 실제 승 → 팀B 승 예측 (정답) |
| FP (False Positive) | 2,867 | 팀B 실제 승 → 팀A 승 예측 (오답) |
| FN (False Negative) | 2,826 | 팀A 실제 승 → 팀B 승 예측 (오답) |
| TP (True Positive) | 5,236 | 팀A 실제 승 → 팀A 승 예측 (정답) |
| 합계 | 16,053 | test set 전체 (2026 시즌) |

정밀도(Precision) = 5236 / (5236+2867) ≈ 0.646, 재현율(Recall) = 5236 / (5236+2826) ≈ 0.650. 두 클래스(팀A 승 / 팀B 승)가 대칭적으로 오분류돼 모델이 특정 팀 방향으로 편향되지 않음을 확인한다.

## 5. 모델 구성 메모

- **튜닝**: Optuna는 사용하지 않는다. 각 모델의 하이퍼파라미터는 코드에 고정된 값을 사용한다.
- **피처 중요도**: 진짜 SHAP이 아니라 트리 모델의 `feature_importances_`와 `importance × value` 휴리스틱으로 산출한다(`serializers.py`의 자연어 근거 포함).
- **소스 계약**: `kaggle_*`·`vlrgg_*` 두 프리픽스를 모두 허용한다.

## 6. 의미 해석

- 시간순 holdout은 2020–2024로 학습한 모델이 2025 경기를 맞히는 정도를 본다. test가 train보다 뒤 시기라, 학습 분포와 평가 분포가 같지 않은 과거→미래 일반화를 점검한다.
- 세 트리 모델(RF/XGB/LGBM)의 Test AUC가 0.6965~0.7015로 근접하며, soft voting 앙상블이 0.7010으로 안정적으로 수렴한다.
- 베이스라인(랜덤 holdout, Test AUC 0.5943)과는 분할·모델 축이 모두 달라 직접 우열 비교가 아니라 서로 다른 평가 질문에 대한 값이다. 교차 정리는 [05_cross_model_comparison.md](./05_cross_model_comparison.md)를 본다.
- 최종 발표에서는 시간순 holdout을 대표 평가로 사용한다.

## 7. 산출물 경로

| 종류 | 경로 |
|---|---|
| 지표 | `reports/advanced/metrics.json` |
| 검증 | `reports/advanced/validation.json` |
| 모델 메타 | `models/advanced/meta.json` |
| 모델 파일 | `models/advanced/ensemble.joblib` |
| 데이터 | `data/processed/advanced/` |
