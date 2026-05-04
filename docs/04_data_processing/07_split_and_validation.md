# 07. 데이터 분할 및 검증

마지막 업데이트: 2026-05-04

## 1. 분할 전략 — match_key 단위 GroupShuffleSplit

단순 행 단위 Stratified Split이 아닌 **match_key 단위** GroupShuffleSplit을 사용한다.

한 경기는 맵 2~3개로 구성된다. 맵 1이 train에, 맵 2가 val에 들어가면 "같은 경기"라는 정보가 모델에 간접 누수된다. match_key 단위로 경기 전체를 한 분할에 몰아야 누수가 없다.

```python
from sklearn.model_selection import GroupShuffleSplit

# 1차 분할: train(70%) / temp(30%)
splitter = GroupShuffleSplit(n_splits=1, test_size=0.30, random_state=42)
train_idx, temp_idx = next(splitter.split(df, groups=df["match_key"]))

# 2차 분할: val(15%) / test(15%)
splitter2 = GroupShuffleSplit(n_splits=1, test_size=0.50, random_state=42)
val_idx, test_idx = next(
    splitter2.split(df.iloc[temp_idx], groups=df.iloc[temp_idx]["match_key"])
)

train = df.iloc[train_idx]
val   = df.iloc[temp_idx].iloc[val_idx]
test  = df.iloc[temp_idx].iloc[test_idx]
```

비율: **train 70% / val 15% / test 15%** — test는 최종 평가에만 한 번 사용.

---

## 2. 분할 결과 예시

| 세트 | 비율 | 예상 맵 행 수 | 비고 |
|------|------|-------------|------|
| Train | 70% | ~56K~70K | A/B swap 증강 후 2x |
| Val | 15% | ~12K~15K | 증강 없음 |
| Test | 15% | ~12K~15K | 최종 평가 전용, 열람 금지 |

---

## 3. A/B swap 증강 (train 전용)

분할 후 train에만 적용한다.

```
원본: team_a=T1, team_b=FNC, label=1
swap: team_a=FNC, team_b=T1, label=0  ← train에만 추가
```

목적: 파일에 먼저 기록된 팀이 항상 team_a가 되는 구조적 편향 제거. 모델이 피처 내용(스탯, 역할군)으로만 승패를 판단하도록 학습.

val/test 미적용 — 평가는 실제 경기 그대로의 행만 사용.
`--no-augment-train` 플래그로 비활성화 가능.

```python
def augment_swap(df: pd.DataFrame) -> pd.DataFrame:
    """train.csv에만 호출"""
    flipped = df.copy()
    # A/B 피처 스왑
    for col_suffix in ["duelist", "initiator", "controller", "sentinel",
                       "avg_acs", "avg_kd", "avg_kast", "avg_adr",
                       "max_clutch", "avg_hs", "fk_fd_ratio", "avg_assists",
                       "kast_std", "avg_agent_map_wr", "avg_agent_pick_rate",
                       "avg_agent_exp"]:
        a_col = f"a_{col_suffix}"
        b_col = f"b_{col_suffix}"
        if a_col in df.columns:
            flipped[a_col], flipped[b_col] = df[b_col].copy(), df[a_col].copy()
    for col in ["has_controller_a", "has_controller_b",
                "is_double_duelist_a", "is_double_duelist_b"]:
        a_col = col.replace("_a", "_TEMP")
        # boolean 피처 스왑
        pass  # 실제 구현에서 상세 처리
    flipped["label"] = 1 - df["label"]
    return pd.concat([df, flipped], ignore_index=True)
```

---

## 4. 피처 사전 집계 누수 방지

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
  matches_clean.csv       # 품질 게이트·dedup 통과 전체 행
  features_base.csv       # 피처 테이블 (레이블 포함)
  train.csv               # 학습셋 (A/B swap 증강 포함)
  val.csv                 # 검증셋
  test.csv                # 테스트셋 (최종 평가 전용)
```

CSV 헤더 (43개 피처 + label):
```
match_key,
a_duelist,a_initiator,a_controller,a_sentinel,
b_duelist,b_initiator,b_controller,b_sentinel,
diff_duelist,diff_initiator,diff_controller,diff_sentinel,
has_controller_a,has_controller_b,
is_double_duelist_a,is_double_duelist_b,
a_avg_acs,b_avg_acs,a_avg_kd,b_avg_kd,
a_avg_kast,b_avg_kast,a_avg_adr,b_avg_adr,
a_max_clutch,b_max_clutch,a_avg_hs,b_avg_hs,
a_fk_fd_ratio,b_fk_fd_ratio,a_avg_assists,b_avg_assists,
a_kast_std,b_kast_std,
a_avg_agent_map_wr,b_avg_agent_map_wr,
a_avg_agent_pick_rate,b_avg_agent_pick_rate,
a_avg_agent_exp,b_avg_agent_exp,
map_encoded,atk_side_advantage,is_attacker_a,
label
```

---

## 6. 품질 검증 체크리스트

```python
def validate_splits(train, val, test):
    # 1. 행 수 합계 (증강 전 기준)
    total = len(train) // 2 + len(val) + len(test)  # swap 증강 후 train은 2x
    print(f"맵 행 총계(증강 전): {total}")

    # 2. match_key 누수 없음 확인
    train_keys = set(train["match_key"])
    val_keys   = set(val["match_key"])
    test_keys  = set(test["match_key"])
    assert train_keys.isdisjoint(val_keys),  "train-val match_key 누수"
    assert train_keys.isdisjoint(test_keys), "train-test match_key 누수"
    assert val_keys.isdisjoint(test_keys),   "val-test match_key 누수"

    # 3. 피처 수 확인
    feature_cols = [c for c in train.columns if c not in ["match_key", "label"]]
    assert len(feature_cols) == 43, f"피처 수 오류: {len(feature_cols)}"

    # 4. 결측값 0 확인
    for name, df in [("Train", train), ("Val", val), ("Test", test)]:
        null_count = df.isnull().sum().sum()
        assert null_count == 0, f"{name} 결측값: {null_count}"

    print("모든 품질 검증 통과")
```

---

## 7. 시간 기반 분할 (선택적 검증 실험)

랜덤 분할 성능이 나온 후 "이 모델이 실제로 미래 경기를 잘 예측하는가?"를 별도 검증할 때 사용한다.

```
train : 2021-01 ~ 2023-12
test  : 2024-01 ~ 2025-현재
```

랜덤 분할보다 Accuracy가 크게 낮으면 메타 시프트 영향이 크다는 신호 → 시간 가중치 강도 조정.

---

## 8. 전체 파이프라인 실행 순서

```bash
# 전체 실행 (분할 포함)
python -m ml.data_pipeline \
  --input data/raw/kaggle \
  --output data/processed \
  --reports reports

# 내부 실행 순서:
# 1. 파싱 (5종 파서)
# 2. 정규화 (요원·맵·팀명)
# 3. 품질 게이트
# 4. dedup_key 중복 제거 → matches_clean.csv
# 5. match_key 단위 GroupShuffleSplit (70/15/15)
# 6. train.csv 기준 피처 사전 집계
# 7. val/test에 집계값 join
# 8. A/B swap 증강 (train 전용)
# 9. sample_weight 계산
# 10. features_base.csv / train.csv / val.csv / test.csv 저장
# 11. validate_splits()
```

---

## 9. 관련 문서

| 문서 | 내용 |
|------|------|
| [06_feature_engineering.md](06_feature_engineering.md) | 43개 피처 생성 상세 |
| [../preprocessing.md](../preprocessing.md) | 전처리 전략 원문 (섹션 5·8·9) |
