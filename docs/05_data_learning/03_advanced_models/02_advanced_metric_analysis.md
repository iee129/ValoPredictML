# 02. 심화 앙상블 지표 해석 및 일반화 한계 분석

작성일: 2026-05-28 (현행값 정합: 2026-06-04)
대상 브랜치: `iee`

## 질문

현재 심화 앙상블(`RF + XGB + LGBM` 가중 soft voting)이 어떤 신호로 예측하며, 시간순 holdout에서 일반화가 어디까지 유지되는지를 실측으로 정리한다.

## 결론 요약

현행 활성 산출물은 **시간순 year-block split**(train 2020–2025 / test 2026) 기준이다. 행 단위는 BO 시리즈 전체 경기가 아니라 **맵 단위 승패 샘플**이다. 출처가 일치하는 산출물은 `reports/advanced/metrics.json`, `reports/advanced/validation.json`, `models/advanced/meta.json`, 앱 런타임 경로다.

| 항목 | 값 |
|---|---:|
| Advanced Ensemble Test ROC-AUC (시간순) | 0.7010 |
| Advanced Test Accuracy (시간순) | 0.6454 |
| Advanced Test F1 (시간순) | 0.6478 |
| 개별 Test AUC | RF 0.6965 / XGB 0.7007 / LGBM 0.7015 |
| soft voting 가중치 | RF 2.0 : XGB 3.0 : LGBM 0.1 |
| 가중치 선택 val AUC | 0.6682 |
| Advanced sample unit | 맵 단위 승패 샘플 |
| Advanced train rows | 75,405 (2020–2025) |
| Advanced test rows | 16,053 (2026) |

> 과거 문서가 노출하던 랜덤 holdout 기반 심화 AUC 수치는 현행 정본에서 폐기됐다. 현행 대표 지표는 시간순 split AUC `0.7010` 하나뿐이며, 미래 시즌(2026) holdout 평가다.

## 지표가 이 수준인 이유

### 1. 시간순 평가는 랜덤 평가보다 보수적이다

현행 split은 match_key 단위 중복을 막을 뿐 아니라, **미래 연도(2026)를 test로 분리**한다. 따라서 같은 연도/이벤트/팀 분포를 학습에 섞어 쉽게 맞히는 랜덤 holdout과 달리, 새 시즌에 대한 일반화 성능을 직접 측정한다. 랜덤 holdout 방식은 복잡한 모델을 과대평가하는 경향이 있어 현행 정본에서는 사용하지 않는다.

### 2. 심화 피처는 prior 성과 신호가 매우 강하다

현재 advanced 179개 피처에는 다음 성과 기반 historical prior가 포함된다.

- 선수 prior: `prior_games`, `prior_kd`, `prior_kast`, `prior_adr`, `prior_apr`, `prior_fkpr`, `prior_fdpr`
- 조합 prior: `a_synergy_mean`, `b_synergy_mean`
- map-agent prior: `a_map_agent_*_mean`, `b_map_agent_*_mean`
- player-agent prior: `a_player_agent_*_mean`, `b_player_agent_*_mean`

`reports/advanced/metrics.json`의 ensemble top features 상위권도 이 해석과 일치한다(`b_prior_games_mean`, `b_prior_fdpr_mean`, `a_prior_fdpr_mean`, `a_prior_games_mean`, `a_prior_kast_mean`, `a_prior_kd_mean`, `a_synergy_mean`, `b_synergy_mean` 등). 이 피처들은 코드상 **이전 연도만** 집계하므로 같은 경기 결과가 직접 섞이지는 않지만, 결과 기반 경기력 요약이므로 팀/선수 강도 차이를 강하게 전달한다.

### 3. 트리 앙상블이 prior·조합 피처의 비선형 패턴을 학습한다

개별 Test AUC(RF 0.6965 / XGB 0.7007 / LGBM 0.7015)가 서로 근접하며, 가중 soft voting(2.0:3.0:0.1)으로 결합해 앙상블 AUC 0.7010을 얻는다. 선형 경계(예: SVM 단독)는 이보다 크게 낮으므로, 높은 지표는 선형 우위가 아니라 트리 계열의 비선형 학습 효과에 가깝다.

## 현재 검증이 보는 범위

`신뢰 가능`(`final_verdict`)는 다음을 의미한다.

- feature count가 179개다.
- forbidden feature name이 0개다.
- train/test `match_key` overlap이 0개다.
- 모든 source가 `kaggle_` 또는 `vlrgg_` 프리픽스다.
- 모델 artifact의 `n_features_in_`이 179다.
- 시간순 Test AUC가 임계값(threshold)을 통과한다.

이 검증은 필요한 기본 안전장치다. 시간순 future-year holdout(2026)이 기본 평가에 포함된 것이 이전 랜덤 holdout 대비 핵심 개선이다.

## 피처 중요도 — 실측 상위 11위 (앙상블 feature_importances_ 기준)

> 출처: `reports/advanced/metrics.json` → `top_features.ensemble` / SSOT `final/deliverables/00_수치_단일진실표.md`
> **진짜 SHAP 아님.** 트리 모델의 `feature_importances_`(gain 기반) 기준이며, 예측에 기여한 정도를 나타낸다.

| 순위 | 피처명 | 중요도 | 설명 |
|---|---|---:|---|
| 1 | `diff_prior_kd_mean` | 0.1559 | 이전 연도 평균 K/D 비율 팀 간 차이 — **주 신호** |
| 2 | `diff_prior_kd_x_history_coverage` | 0.0804 | K/D × 히스토리 신뢰도 가중 차이 |
| 3 | `diff_prior_games_mean` | 0.0690 | 이전 연도 평균 출전 경기 수 팀 간 차이 |
| 4 | `diff_max_prior_kd` | 0.0295 | 팀 내 최고 K/D 선수 팀 간 차이 |
| 5 | `diff_player_agent_games_mean` | 0.0211 | 선수×요원 조합 히스토리 경험 팀 간 차이 |
| 6 | `diff_low_sample_player_ratio` | 0.0200 | 저표본 선수 비율 팀 간 차이 |
| 7 | `diff_prior_fkpr_mean` | 0.0192 | 이전 연도 평균 FKPR 팀 간 차이 |
| 8 | `diff_prior_adr_mean` | 0.0172 | 이전 연도 평균 ADR 팀 간 차이 |
| 9 | `diff_history_coverage_mean` | 0.0116 | 히스토리 커버리지 평균 팀 간 차이 |
| 10 | `diff_player_agent_kd_mean` | 0.0113 | 선수×요원 조합 K/D 팀 간 차이 |
| **11** | **`diff_agent_map_fit`** | **0.0095** | **요원-맵 적합도 팀 간 차이 — 보조 신호** |

**핵심 인사이트**:
- **1위 신호는 선수 누적 K/D 역량 격차**(`diff_prior_kd_mean`, 중요도 0.1559)다. 팀 간 누적 역량 차이가 승패의 가장 강력한 예측 변수임을 의미한다.
- 2~3위(`diff_prior_kd_x_history_coverage`, `diff_prior_games_mean`)는 선수 히스토리 신뢰도와 경험량이다. 데이터가 충분한 선수가 많은 팀이 예측 신호가 뚜렷하다.
- **요원-맵 적합도(`diff_agent_map_fit`)는 11위(중요도 0.0095), 보조 신호**에 해당한다. 전략적 구성보다 선수 개인 역량이 더 큰 예측력을 가진다는 실측 근거다.

## 남은 불확실성 (추가 검증 후보)

1. event/team group holdout: 동일 이벤트 또는 팀이 train/test에 동시에 들어가지 않게 나눈다.
2. prior ablation: `prior_kd/kast/adr/apr/fkpr/fdpr` 계열을 제거하고 AUC 하락폭을 본다.
3. source holdout: 특정 Kaggle/VLR.gg 소스를 완전히 holdout한다.
4. calibration 확인: AUC뿐 아니라 Brier score, calibration curve, close-match subset 성능을 확인한다.

## 근거

| 근거 | 파일/라인 | 의미 |
|---|---|---|
| 현행 대표 지표가 시간순 Test AUC 0.7010 | `reports/advanced/metrics.json` | 정본 지표는 시간순 0.7010 하나다. |
| 활성 advanced 피처는 179개이고 KD/KAST/ADR/APR/FKPR/FDPR prior를 포함 | `src/features/preprocess.py` | 모델이 강한 과거 성과 집계를 입력으로 받는다. |
| feature config가 같은 연도 이력 제외를 선언 | `src/features/preprocess.py` | 활성 피처 계약 자체는 같은 해 이력을 쓰지 않는다고 선언한다. |
| 이전 연도만 history로 선택 | `src/features/preprocess.py` | `year < current_year`만 prior history에 들어간다. |
| 앙상블 학습은 가중 soft voting(2.0:3.0:0.1) | `src/ml/advanced/ensemble.py` | 가중치는 2025 검증 split grid search로 선택. |
| validation gate는 179피처, forbidden count, split overlap, source prefix, 시간순 AUC threshold 확인 | `src/ml/advanced/validate.py` | 시간순 holdout이 기본 검증에 포함된다. |
| 앱 런타임은 `models/advanced`, `reports/advanced`를 읽는다 | `src/inference/predict.py` | 0.7010 산출물이 실제 UI 경로에 연결돼 있다. |
