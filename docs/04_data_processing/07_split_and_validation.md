# 07. 데이터 분할 및 검증

마지막 업데이트: 2026-06-05

> **구현 완료** — `src/features/preprocess.py`의 `save_splits()`로 구현.
> 현행 advanced 실행 결과: train 75,405개 + test 16,053개 = 총 91,458개 **맵 단위 승패 샘플**. 이 값은 BO 시리즈 전체 경기 수가 아니라 모델 학습·평가 행 수다.

## 1. 분할 전략 — match_key 단위 GroupShuffleSplit

단순 행 단위 Stratified Split이 아닌 **match_key 단위** GroupShuffleSplit을 사용한다.

BO3·BO5 시리즈 한 경기는 여러 맵으로 구성될 수 있다. 맵 1이 train에, 맵 2가 val에 들어가면 "같은 시리즈"라는 정보가 모델에 간접적으로 전달될 수 있다. `match_key` 단위로 동일 맵 승패 샘플을 한 분할에 몰아야 train과 test가 깔끔하게 분리된다.

```python
from sklearn.model_selection import GroupShuffleSplit

# 단일 분할: train(80%) / test(20%)
splitter = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=42)
train_idx, test_idx = next(splitter.split(df, groups=df["match_key"]))

train = df.iloc[train_idx]
test  = df.iloc[test_idx]
```

비율: **train 80% / test 20%** — 별도 검증셋 없이 train 내부 GroupKFold로 튜닝. test는 최종 평가에만 한 번 사용.

`save_splits()`는 기존 train/test.csv의 match_key 멤버십을 `_load_split_membership()`으로 재사용하고, 없으면 seed=42로 shuffle 후 80/20 fallback 분할한다.

---

## 2. 분할 결과 (실측, seed=42)

| 세트 | 비율 | 행 수 | 비고 |
|------|------|-------|------|
| Train (baseline) | 80% | **53,427** | match_key 단위 80% (랜덤 분할) |
| Test (baseline) | 20% | **13,357** | 최종 평가 전용, 열람 금지 |

baseline은 랜덤 Train 80% / Test 20% 분할을 사용한다. **advanced 모델은 시간순(chrono) 분할**을 사용한다(train 2020–2025 / test 2026, 맵 단위 승패 샘플) — 3절 참조.

test 세트 label 분포: mean ≈ 0.568 (label=1이 약 56.8%). 클래스 불균형은 자연 분포 그대로 유지한다.

---

## 3. 데이터 분리 장치

증강 없이 다음 장치로 train과 test가 섞이지 않게 한다.

| 장치 | 설명 |
|------|------|
| match_key 단위 분할 | 같은 경기의 모든 맵 행이 단일 split에 배정 |
| GroupKFold(match_key) | baseline CV에서 경기 단위 fold 분리 |
| 금지 피처 26개 정규식 차단 | `find_forbidden_feature_names()`로 미래 정보 피처 학습 전 제외 |
| 이전 연도만 prior | `agent_map_stats` 집계 시 `year < current_year` 조건 적용 |
| 리그평균 smoothing | `RunningStats.smoothed_avg()`로 소표본 노이즈 억제 |

---

## 4. 피처 사전 집계 — 분할 기준 유지

분할 이후 train.csv만으로 집계한 통계를 val/test에 join한다.

| 집계 항목 | 집계 소스 | val/test 처리 |
|-----------|-----------|--------------|
| `atk_side_advantage` | train 맵별 공격 측 승률 | join |
| `agent_map_stats` (winrate, pickrate) | train 요원x맵 통계 | join (미등록: winrate=0.5) |
| `agent_experience` | train 선수x요원 등장 횟수 | join (미등록: 0) |

---

## 5. 저장 형식

```
data/processed/
  matches_clean.csv       # 품질 검사·dedup를 통과한 전체 행
  features_base.csv       # 피처 테이블 (레이블 포함)
  train.csv               # 학습셋
  test.csv                # 테스트셋 (최종 평가 전용)

data/processed/advanced/
  train.csv               # advanced 학습셋 (시간순 분할: 2020–2025)
  test.csv                # advanced 테스트셋 (시간순 분할: 2026)
```

---

## 6. 품질 검증 체크리스트

```python
def validate_splits(train, val, test):
    # 1. match_key 겹침 없음 확인
    train_keys = set(train["match_key"])
    test_keys  = set(test["match_key"])
    assert train_keys.isdisjoint(test_keys), "train-test match_key 겹침"

    # 2. 피처 수 확인 (파이프라인별 feature contract)
    feature_cols = [c for c in train.columns if c not in ["match_key", "label"]]
    print(f"피처 수: {len(feature_cols)}")  # baseline 421 / advanced 179

    # 3. 결측값 0 확인
    for name, df in [("Train", train), ("Test", test)]:
        null_count = df.isnull().sum().sum()
        assert null_count == 0, f"{name} 결측값: {null_count}"

    print("모든 품질 검증 통과")
```

---

## 7. 시간 기반 분할 (advanced 모델 기본 분할)

baseline은 랜덤 분할을 쓰지만, **advanced 모델은 시간순(chrono) 분할을 기본으로 사용**해 "미래 경기를 실제로 잘 예측하는가"를 평가한다.

```
train : 2020 ~ 2024
test  : 2025
```

랜덤 분할보다 Accuracy가 크게 낮으면 메타 시프트 영향이 크다는 신호 → 시간 가중치 강도 조정.

---

## 8. 전체 파이프라인 실행 순서

```bash
# 전체 실행 (분할 포함)
python -m features.preprocess \
  --input data/raw/kaggle \
  --output data/processed \
  --reports reports

# 내부 실행 순서:
# 1. 파싱 (소스별 파서)
# 2. 정규화 (요원·맵·팀명)
# 3. 품질 검사
# 4. dedup_key 중복 제거 → matches_clean.csv
# 5. match_key 단위 GroupShuffleSplit (80/20)
# 6. train.csv 기준 피처 사전 집계
# 7. test에 집계값 join
# 8. sample_weight 계산
# 9. features_base.csv / train.csv / test.csv 저장
# 10. validate_splits()
```

---

## 9. 관련 문서

| 문서 | 내용 |
|------|------|
| [06_feature_engineering.md](06_feature_engineering.md) | 피처 생성 상세 (baseline 421 / advanced 179) |
| [01_pipeline_overview.md](01_pipeline_overview.md) | 전처리 파이프라인 전체 흐름 개요 |
