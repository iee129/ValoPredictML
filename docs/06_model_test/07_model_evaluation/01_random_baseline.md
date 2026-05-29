# ① 랜덤순 베이스라인

분할축 **랜덤 holdout** × 모델축 **베이스라인**. 전체 기간의 경기를 무작위로 나눠 평가한, 가장 단순한 구성의 모델이다.

출처: `reports/baseline/metrics.json`, `reports/baseline/validation.json`, `models/baseline/meta.json`.

## 1. 모델 정의

로지스틱 회귀(LR)와 결정트리(DT)를 soft voting으로 묶은 베이스라인을, `match_key` 단위 무작위 80/20
holdout으로 평가한 구성이다. 178개 피처를 사용하며, 이후 세 모델(②③④)의 비교 기준점 역할을 한다.

## 2. 데이터 분할

- **방식**: `match_key`(경기) 단위 무작위 80/20 분할. 같은 경기에서 나온 여러 맵 행은 train·test 중 한쪽에만 들어간다.
- **튜닝**: train 내부에서 GroupKFold(K=5, group=`match_key`)로 하이퍼파라미터를 탐색한 뒤, train 전체로 최종 적합하고 test로 1회 평가한다.
- **행 수**: train 53,427 / test 13,357.
- **소스**: Kaggle 소스(`kaggle_*`)만 사용한다. 같은 경기·같은 해 통계는 입력에서 제외하고, 선수 prior는 이전 연도까지만 집계한다.

## 3. 모델 구성

- **알고리즘**: LR + DT soft voting (가중 평균 확률).
- **피처**: 178개 — 맵 원-핫, 역할군 카운트, 28요원 카운트, 선수 prior(이전 연도 KD/KAST/ADR/APR/FKPR/FDPR/clutch 등),
  synergy, map×agent·player×agent 집계. 베이스라인 계약은 `a_*`·`b_*`와 함께 양 팀 차이 `diff_*`를 포함한다.
- **튜닝 결과** (`models/baseline/meta.json`):
  - LR: `C=0.01`, `l1_ratio=1.0`, CV AUC 0.6583
  - DT: `max_depth=6`, `min_samples_leaf=100`, CV AUC 0.6455

## 4. 성능 지표

| 구분 | ROC-AUC | Accuracy | F1 |
|------|--------:|---------:|---:|
| CV (GroupKFold) | 0.6599 ± 0.0016 | 0.6260 | 0.7197 |
| Test (holdout) | 0.6587 | 0.6290 | 0.7231 |

- **혼동행렬** (test, 행=실제 / 열=예측): `[[1930, 3827], [1129, 6471]]`
- 다수 클래스(label=1) 기준 정확도 0.5690 대비 test 정확도 0.6290.
- train·test AUC 차이는 0.0034로 작다(`reports/baseline/validation.json`).

## 5. 의미 해석

랜덤 holdout은 전 기간에서 무작위로 떼어낸 경기를 맞히는 정도를 본다. train과 test가 같은 시기·소스를
공유하므로, 이전 시즌까지 쌓인 선수·조합 강도가 같은 분포의 test 경기에 비교적 직접 작용한다.
- **피처 영향도** (permutation, AUC 감소량 기준): `diff_prior_kd_mean`(0.025),
  `diff_prior_games_mean`(0.0176), `diff_prior_fkpr_mean`(0.0126)이 상위다. 양 팀의 이전 성과 차이(`diff_*`)가
  예측을 주로 움직인다.
- **CV–Test 일관성**: CV AUC(0.6599)와 test AUC(0.6587)가 거의 같고 표준편차가 0.0016으로 작아, 폴드 간 편차가 작은 구성이다.
- 선형(LR)과 얕은 트리(DT) 조합이라 표현력이 제한적이며, 비선형 상호작용 학습은 ②④의 트리 앙상블이 담당한다.

## 6. 산출물 경로

| 종류 | 경로 |
|------|------|
| 지표 | `reports/baseline/metrics.json` |
| 추가 분석(혼동행렬·피처 영향도) | `reports/baseline/validation.json` |
| 모델 메타·튜닝 결과 | `models/baseline/meta.json` |
| 모델 파일 | `models/baseline/model.joblib` |
| EDA 그림 | `reports/baseline/eda/` |
