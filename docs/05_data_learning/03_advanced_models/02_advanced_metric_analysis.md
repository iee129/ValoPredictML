# 02. 심화 앙상블 지표 상승 원인 분석

작성일: 2026-05-28  
대상 브랜치: `iee`  
외부 참고 문서: `/Users/iee12/Downloads/valopredict_analysis.md`

## 질문

현재 기존 심화모델 앙상블(`RF + XGB + LGBM`)의 Test ROC-AUC가 `0.7570`으로 베이스라인 `0.6587`보다 높게 나오는 이유가 무엇인지, 그리고 **시간순 holdout에서도 이 우위가 유지되는지**를 실측 결과로 확인한다.

## 결론 요약

80/20 랜덤 holdout 기준 `0.7570`은 `reports/adv_kaggle_only/metrics.json`, `models/advanced/meta.json`, Streamlit 런타임 경로가 같은 값을 가리키는 활성 산출물이다. 다만 이 값은 "시간순 미래 예측 성능"이라기보다 "Kaggle-only 데이터에서 match_key 랜덤 holdout을 맞히는 성능"으로 해석해야 한다.

**시간순 holdout 실측 결과** (train 2021–23 = 53,897 / test 2024–26 = 12,887):

| 분할 방식 | Baseline AUC | Advanced Ensemble AUC | 낙폭 (랜덤→시간순) |
|---|---:|---:|---:|
| 랜덤 holdout (80/20) | 0.6587 | **0.7570** | — |
| 시간순 holdout | 0.6124 | **0.6182** | advanced −0.139, baseline −0.046 |

핵심 관찰: 랜덤 holdout은 복잡한 모델(advanced)을 3배 더 크게 과대평가한다. 시간순 기준에서 advanced의 baseline 대비 우위는 +0.006으로 사실상 소멸한다. 이는 랜덤 split에서 historical prior 신호가 얼마나 강하게 작용하는지를 보여준다.

가장 큰 원인은 아래 세 가지다.

| 순위 | 원인 | 신뢰도 | 해석 |
|---:|---|---|---|
| 1 | train/test가 시간순이 아니라 match_key 단위 랜덤 분할 | 높음 | 같은 연도, 같은 데이터 소스, 같은 팀/이벤트 분포가 test에도 섞여 미래 시즌 일반화보다 쉬운 평가가 된다. 시간순 holdout에서 advanced 낙폭(−0.139)이 baseline 낙폭(−0.046)의 3배에 달한다. |
| 2 | 심화 피처가 이전 연도 선수 prior, synergy, map-agent, player-agent 성과 집계를 강하게 사용 | 높음 | 같은 경기 결과가 직접 섞인 것은 아니지만, KD/KAST/ADR/APR/FKPR/FDPR/clutch 같은 결과 기반 과거 성과 요약이 모델의 핵심 신호다. 시간순 미래 경기에서는 이 prior의 설명력이 급감한다. |
| 3 | XGBoost 중심의 고용량 트리 앙상블이 랜덤 split 환경에서 prior 신호를 잘 학습 | 중간-높음 | 단일 XGB Test AUC가 `0.7641`로 앙상블 `0.7570`보다도 높다. SVM 대체 실험은 성능이 크게 내려가므로 선형 모델 우위가 아니라 트리 모델의 비선형 학습 효과가 크다. |

반대로, 외부 문서의 '같은 연도 데이터가 섞이는 것' 표현은 현재 활성 피처 경로만 놓고 보면 과하게 단정적이다. 로컬 코드의 활성 `advanced` 계약은 같은 해 이력은 제외하고 이전 연도 이력만 집계한다. 문제의 핵심은 같은 연도 피처가 직접 섞이는 것이라기보다, 랜덤 분할 평가와 강한 historical prior가 결합되어 미래 시즌 일반화 성능보다 높은 숫자를 만든다는 점이다.

## 현재 활성 숫자

| 항목 | 값 |
|---|---:|
| Baseline Test ROC-AUC (랜덤 80/20) | 0.6587 |
| Advanced Ensemble Test ROC-AUC (랜덤 80/20) | 0.7570 |
| AUC 차이 (랜덤) | +0.0983 |
| Advanced Test Accuracy (랜덤) | 0.6958 |
| Advanced Test F1 (랜덤) | 0.7649 |
| Advanced train rows (랜덤) | 53,427 |
| Advanced test rows (랜덤) | 13,357 |
| Baseline Test ROC-AUC (시간순) | 0.6124 |
| Advanced Ensemble Test ROC-AUC (시간순) | 0.6182 |
| AUC 차이 (시간순) | +0.0058 |

로컬 산출물 기준 모델별 Test ROC-AUC (랜덤 holdout)는 다음과 같다.

| 모델 | Test ROC-AUC | Test Accuracy | Test F1 |
|---|---:|---:|---:|
| RF | 0.7013 | — | — |
| XGB | 0.7641 | — | — |
| LGBM | 0.7332 | — | — |
| Ensemble | 0.7570 | 0.6958 | 0.7649 |

SVM을 넣은 비승격 실험은 해석을 보강한다.

| 실험 | Test ROC-AUC | 현재 앙상블 대비 |
|---|---:|---:|
| 현재 RF+XGB+LGBM | 0.7570 | 기준 |
| SVM 단독 | 0.6602 | -0.0968 |
| RF+XGB+LGBM+SVM | 0.7594 | +0.0024 |
| RF+LGBM+SVM, XGB 제외 | 0.7279 | -0.0291 |
| RF+LGBM, XGB 제외 | 0.7391 | -0.0179 |

즉 현재 높은 심화 지표는 SVM 같은 선형 경계보다 XGB/LGBM/RF 계열 트리가 historical prior와 조합 피처를 더 잘 활용한 결과로 보는 것이 더 타당하다.

## 외부 분석 문서와의 대조

| 외부 문서 주장 | 로컬 대조 결과 | 판정 |
|---|---|---|
| `verification_summary.md`의 0.9355 AUC는 현재 0.7570와 충돌한다. | 맞다. 현재 README는 0.7570을, 오래된 테스트 문서는 0.9355를 동시에 노출했다 (현재는 정정 완료). | 동의 |
| `advanced/preprocess.py`가 `prior_wr`, `h2h`, `map_wr`, `recent5_wr`를 만든다. | 맞다. 다만 현재 README 실행 순서와 UI 경로는 `ml.baseline.preprocess --feature-contract advanced`의 산출물인 `adv_kaggle_only`를 사용한다. | 부분 동의 |
| `advanced/preprocess.py`가 만든 `prior_wr/h2h/map_wr`가 실제 심화 모델 성능을 직접 올린다. | 현재 활성 `adv_kaggle_only` 헤더에는 해당 컬럼이 없다. 실제 학습은 `FEATURE_COLS_ADVANCED` 125개만 사용한다. | 정정 필요 |
| forbidden 검사는 이름 기반이라 KD/KAST/ADR 등 결과 기반 prior의 의미까지 막지는 못한다. | 맞다. forbidden regex는 `acs/kills/deaths/assists/hs` 등 일부 이름을 막지만 `kd/kast/adr/apr/fkpr/fdpr/clutch`는 활성 prior 통계로 남아 있다. | 동의 |
| 0.7570은 모델 우위라기보다 평가가 관대해서 높다. | 큰 방향은 맞다. 시간순 holdout 실측(0.6182)이 이를 뒷받침한다. 단, 같은 연도 피처가 직접 섞이는 문제보다 랜덤 split과 historical prior 효과로 표현하는 편이 정확하다. | 부분 동의 |
| reports/models/data가 gitignored라 외부 clone만으로 재현이 어렵다. | 맞다. 로컬에는 검증 산출물이 있으나, 저장소 추적 파일만으로는 동일 산출물을 보장하기 어렵다. | 동의 |

## 근거

| 근거 | 파일/라인 | 의미 |
|---|---|---|
| README의 현재 상태가 Baseline `0.6587`, Advanced `0.7570`을 노출 | `README.md:12-13` | 현재 대표 지표는 0.7570 계열이다. |
| 오래된 검증 문서는 Ensemble Test AUC `0.9355`를 노출 | `docs/06_model_test/verification_summary.md:12-26` | 0.93대 문서 수치는 현재 활성 산출물과 충돌한다. |
| 활성 advanced 피처는 125개이고 KD/KAST/ADR/APR/FKPR/FDPR/clutch prior를 포함 | `ml/baseline/preprocess.py:41-42`, `ml/baseline/preprocess.py:180-204` | 모델이 강한 과거 성과 집계를 입력으로 받는다. |
| feature config가 같은 연도 이력 제외를 선언 | `ml/baseline/preprocess.py:84-90`, `ml/baseline/preprocess.py:211-216` | 활성 피처 계약 자체는 같은 해 이력을 쓰지 않는다고 선언한다. |
| forbidden regex는 일부 결과 컬럼명만 차단 | `ml/baseline/preprocess.py:137-148`, `ml/baseline/preprocess.py:315-321` | forbidden count 0은 의미론적으로 결과가 섞이지 않았다는 것을 전체 증명하지는 않는다. |
| 이전 연도만 history로 선택 | `ml/baseline/preprocess.py:757-762` | `year < current_year`만 prior history에 들어간다. |
| 같은 해 feature row 생성 후 history 업데이트 | `ml/baseline/preprocess.py:833-864` | 같은 연도 내부 매치 결과는 해당 연도 feature에 누적되지 않는다. |
| advanced build는 source filter, 125 피처 생성, split membership 부착, forbidden gate 수행 | `ml/baseline/preprocess.py:928-1010` | 현재 `adv_kaggle_only` 산출물의 핵심 생성 경로다. |
| `build_xy(feature_contract="advanced")`가 125개 canonical 피처만 사용 | `ml/baseline/preprocess.py:285-297` | CSV에 다른 컬럼이 있어도 학습 입력은 canonical feature list로 제한된다. |
| `advanced/preprocess.py`는 `prior_wr`, `map_wr`, `recent_wr`, `h2h`를 만들고 랜덤 split을 수행 | `ml/advanced/preprocess.py:152-324`, `ml/advanced/preprocess.py:291-305` | 외부 문서가 지적한 위험한 컬럼 생성 코드는 존재한다. |
| 현재 README 실행 순서는 `ml.baseline.preprocess --feature-contract advanced`를 사용 | `README.md:78-81` | 활성 문서상 심화 모델 전처리 진입점은 `advanced/preprocess.py`가 아니다. |
| 앙상블 학습은 train+val을 합쳐 `build_xy(... advanced)`로 학습 | `ml/advanced/ensemble.py:110-119`, `ml/advanced/ensemble.py:133-161` | val 평가는 독립 검증이 아니라 학습 포함 split에 대한 재평가다. |
| 평가 코드는 train/val/test를 모두 읽고 같은 모델로 metrics를 저장 | `ml/advanced/evaluate.py:101-174` | 최종 독립 평가는 test에 한정된다. |
| validation gate는 125피처, forbidden count, split overlap, Kaggle-only, AUC threshold를 확인 | `ml/advanced/validate.py:110-180` | 시간순 holdout이나 팀/이벤트 그룹 holdout은 검증하지 않는다. |
| Streamlit 런타임은 `models/advanced`와 `reports/adv_kaggle_only`를 읽는다 | `app/predict.py:217-235`, `app/predict.py:536-540`, `app/predict.py:584-595` | 0.7570 산출물이 실제 UI 경로에 연결되어 있다. |

## 로컬 데이터 분할 관찰

`data/processed/adv_kaggle_only/{train,val,test}.csv`를 직접 집계한 결과, 세 split 모두 연도/소스/라벨 분포가 거의 같은 랜덤 holdout 형태다.

| split | rows | label mean | 주요 연도 분포 |
|---|---:|---:|---|
| train (랜덤 80%) | 53,427 | 0.5684 | 2021–2026 혼합 |
| test (랜덤 20%) | 13,357 | 0.5700 | 2021–2026 혼합 |
| train (시간순) | 53,897 | — | 2021–2023 |
| test (시간순) | 12,887 | — | 2024–2026 |

train-test 사이에도 같은 팀/이벤트가 넓게 공유된다.

| 항목 | train-test 공유 수 |
|---|---:|
| `team_a` unique overlap | 2,382 |
| `team_b` unique overlap | 2,880 |
| `event` unique overlap | 357 |
| `map` unique overlap | 12 |

이 구조에서는 모델이 "이전 연도까지의 선수/조합 강도"를 학습하면 같은 데이터 분포 안의 test match를 비교적 잘 맞힐 수 있다. 하지만 이는 미래 시즌을 통째로 holdout한 평가와는 다르다.

## 왜 0.7570이 높게 보이는가 (그리고 시간순에서 왜 소멸하는가)

### 1. 랜덤 split이 시간순 평가보다 쉽다 — 실측으로 확인됨

현재 활성 split은 match_key 단위 중복은 막지만, 연도와 소스 분포를 test에 그대로 섞는다. `ml/baseline/preprocess.py`의 80/20 split도 seed 42 랜덤 방식이다.

**실측 결과**: 시간순 holdout(2024–26 test)에서 advanced AUC는 0.7570 → 0.6182로 −0.139 낙폭, baseline은 0.6587 → 0.6124로 −0.046 낙폭이다. 복잡한 모델일수록 랜덤 split 과대평가가 더 크다는 점이 수치로 확인된다. 따라서 랜덤 holdout AUC는 "다음 연도 혹은 새 시즌 예측"이 아니라 "동일한 historical population에서 holdout된 match_key 예측"으로 해석해야 한다.

### 2. 심화 피처는 prior 성과 신호가 매우 강하다

현재 advanced 125개 피처에는 다음 성과 기반 historical prior가 포함된다.

- 선수 prior: `prior_games`, `prior_kd`, `prior_kast`, `prior_adr`, `prior_apr`, `prior_fkpr`, `prior_fdpr`, `prior_clutch`
- 조합 prior: `a_synergy_mean`, `b_synergy_mean`
- map-agent prior: `a_map_agent_*_mean`, `b_map_agent_*_mean`
- player-agent prior: `a_player_agent_*_mean`, `b_player_agent_*_mean`

Top feature도 이 해석과 일치한다. 로컬 `metrics.json`의 ensemble top features 상위권은 `b_prior_games_mean`, `b_prior_fdpr_mean`, `a_prior_fdpr_mean`, `a_prior_games_mean`, `a_prior_kast_mean`, `a_prior_kd_mean`, `a_synergy_mean`, `b_synergy_mean`이다.

이 피처들은 현재 코드상 이전 연도만 쓰므로 같은 경기 결과가 그대로 섞인다고 단정할 수는 없다. 그러나 결과 기반 경기력 요약이므로 랜덤 split 환경에서는 팀/선수 강도 차이를 매우 직접적으로 전달한다.

### 3. 현재 검증이 보는 범위가 제한적이다

현재 `PASS_TRUSTED_KAGGLE_ONLY_ADVANCED`는 다음을 의미한다.

- feature count가 125개다.
- forbidden feature name이 0개다.
- train/val/test `match_key` overlap이 0개다.
- 모든 source가 `kaggle_`로 시작한다.
- 모델 artifact의 `n_features_in_`가 125다.
- Test AUC가 0.70 이상이다.

이 검증은 필요한 기본 안전장치지만, 다음 질문까지 답하지는 않는다.

- 시간순 future-year holdout에서도 AUC가 유지되는가?
- 같은 팀/이벤트/선수 그룹을 train과 test에 공유하지 않아도 유지되는가?
- KD/KAST/ADR 계열 prior를 제거해도 성능이 유지되는가?
- 소스별 artifact 차이를 모델이 간접 학습하고 있지는 않은가?

### 4. train 내부 GroupKFold가 독립 검증 역할을 한다

80/20 분할에서 val 세트는 없고, 튜닝은 train 내부 GroupKFold(K=5)로 수행된다. 최종 비교에 사용할 수 있는 값은 랜덤 holdout test AUC `0.7570`이며, 시간순 일반화 성능은 별도 chrono holdout 측정값인 `0.6182`다.

## 최종 판정

현재 기존 심화모델 앙상블 지표가 높게 나오는 주된 이유는 단일 원인으로 단정하기보다, 다음 조합으로 보는 것이 가장 근거에 맞다.

1. `match_key` 중복만 막은 랜덤 holdout 평가다.
2. test가 train과 같은 연도/소스/팀/이벤트 분포를 공유한다.
3. historical prior 피처가 선수와 조합의 이전 성과를 강하게 요약한다.
4. XGB/LGBM/RF가 이 prior 신호와 조합 피처의 비선형 패턴을 잘 학습한다.
5. 현재 validation은 name/source/overlap/feature-count 중심이라 시간순 일반화 리스크를 직접 검증하지 않는다.

따라서 `0.7570`은 로컬 활성 아티팩트로는 맞는 숫자지만, "실전 미래 경기 예측 성능"으로 소개하려면 과장될 수 있다. 더 보수적으로는 "Kaggle-only 랜덤 holdout 기준 심화 앙상블 AUC"라고 표기하는 것이 맞다. 시간순 기준 실측치(`0.6182`)가 이를 뒷받침한다.

## 남은 불확실성

year holdout은 실측으로 해소됐다. 아래 항목은 추가 검증 후보다.

1. event/team group holdout: 동일 이벤트 또는 팀이 train/test에 동시에 들어가지 않게 나눈다.
2. prior ablation: `prior_kd/kast/adr/apr/fkpr/fdpr/clutch` 계열을 제거하고 AUC 하락폭을 본다.
3. source holdout: `kaggle_vct`, `kaggle_qualidea`, `kaggle_challengers` 중 한 소스를 완전히 holdout한다.
4. calibration 확인: AUC뿐 아니라 Brier score, calibration curve, close-match subset 성능을 확인한다.

