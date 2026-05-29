# ③ 시간순 베이스라인

분할축 **시간순 holdout** × 모델축 **베이스라인**. 과거 연도로 학습해 이후 연도를 평가한, 베이스라인 구성의 모델이다.

출처: `reports/baseline_chrono/metrics.json`, `reports/baseline_chrono/split_metadata.json`, `models/baseline_chrono/meta.json`.

## 1. 모델 정의

①과 같은 LR + DT soft voting 베이스라인(178피처)을, 연도 블록으로 나눈 시간순 holdout으로 평가한 구성이다.
①과 모델 계열은 같고 분할 축만 다른 짝이다.

## 2. 데이터 분할

- **방식**: 연도 블록 분할 — train은 2024년 이전(2021–2023), test는 2024년 이상(2024–2026). train 연도가 test 연도보다 모두 앞선다.
- **행 수**: train 53,897 (2021–2023) / test 12,887 (2024–2026).
- **라벨 평균**: train 0.5802 / test 0.5220 — 두 블록의 라벨 비율이 다르다.
- **소스 구성** (`split_metadata.json`):

  | 블록 | 주요 소스(행 수) |
  |------|------------------|
  | train | qualidea 24,889 · vct 21,556 · challengers 6,834 · ediashtarevin 618 |
  | test | challengers 8,236 · piyush2025 2,291 · vct 2,274 · piyush2024 86 |

  test 블록에는 train에 없던 소스(`piyush2024`, `piyush2025`)가 등장한다.
- **소스 계열**: Kaggle 소스(`kaggle_*`)만 사용하고, 같은 경기·같은 해 통계는 제외한다.

## 3. 모델 구성

- **알고리즘**: LR + DT soft voting (①과 동일 계열, 178피처, `diff_*` 포함).
- **튜닝 결과** (`models/baseline_chrono/meta.json`) — 이 분할에 대해 독립적으로 탐색된 값:
  - LR: `C=1.0`, `l1_ratio=1.0`, CV AUC 0.6628
  - DT: `max_depth=10`, `min_samples_leaf=100`, CV AUC 0.6514

## 4. 성능 지표

| 구분 | ROC-AUC | Accuracy | F1 |
|------|--------:|---------:|---:|
| CV (GroupKFold, train 내부) | 0.6684 ± 0.0103 | 0.6351 | 0.7323 |
| Test (2024–2026 holdout) | 0.6124 | 0.5795 | 0.6226 |

- **혼동행렬** (test, 행=실제 / 열=예측): `[[2999, 3161], [2258, 4469]]`

## 5. 의미 해석

시간순 holdout은 2021–2023으로 학습한 모델이 2024–2026 경기를 맞히는 정도를 본다. test가 train보다
뒤 시기이고, 위 분포 표처럼 라벨 비율(0.5802→0.5220)과 소스 구성이 달라 학습 분포와 평가 분포가 같지 않다.
- **CV 편차**: train 내부 CV AUC의 표준편차가 0.0103으로, 랜덤 분할 베이스라인(①, 0.0016)보다 크다.
  연도 순서로 폴드를 나눌 때 폴드 간 분포 차이가 더 크게 나타난다.
- **CV–Test 관계**: CV AUC(0.6684)는 train 기간(2021–2023) 내부에서 측정한 값이고, test AUC(0.6124)는 이후
  기간(2024–2026)에서 측정한 값이다. 두 값은 서로 다른 시기 분포에 대한 측정이다.
- 같은 베이스라인 모델을 랜덤 분할로 본 ①과는 [05_cross_model_comparison.md](./05_cross_model_comparison.md)에서 직접 비교한다.

## 6. 산출물 경로

| 종류 | 경로 |
|------|------|
| 지표 | `reports/baseline_chrono/metrics.json` |
| 분할 메타(연도·소스·라벨 분포) | `reports/baseline_chrono/split_metadata.json` |
| 모델 메타·튜닝 결과 | `models/baseline_chrono/meta.json` |
| 모델 파일 | `models/baseline_chrono/model.joblib` |
