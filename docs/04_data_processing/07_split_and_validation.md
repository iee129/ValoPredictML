# 07. 데이터 분할 및 검증

## 1. Stratified Split 전략

```python
from sklearn.model_selection import train_test_split

def split_and_save(df: pd.DataFrame, output_dir: str = "data/processed"):
    """
    Stratified Split으로 라벨 분포 유지하며 분할
    비율: 70% 학습 / 15% 검증 / 15% 테스트
    """
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    # 1차 분할: train(70%) / temp(30%)
    train, temp = train_test_split(
        df,
        test_size=0.30,
        stratify=df["label"],
        random_state=42,
    )
    
    # 2차 분할: val(15%) / test(15%)
    val, test = train_test_split(
        temp,
        test_size=0.50,
        stratify=temp["label"],
        random_state=42,
    )
    
    # 저장
    train.to_csv(f"{output_dir}/train.csv", index=False)
    val.to_csv(f"{output_dir}/val.csv", index=False)
    test.to_csv(f"{output_dir}/test.csv", index=False)
    
    # 분할 결과 출력
    for name, split_df in [("Train", train), ("Val", val), ("Test", test)]:
        label_dist = split_df["label"].value_counts(normalize=True)
        print(f"{name}: {len(split_df):,}행 | 라벨 분포: {label_dist.to_dict()}")
    
    return train, val, test
```

---

## 2. 분할 결과 예시

| 세트 | 비율 | 예상 행 수 | 라벨 0 | 라벨 1 |
|---|---|---|---|---|
| Train | 70% | ~4,900 | ~50% | ~50% |
| Val | 15% | ~1,050 | ~50% | ~50% |
| Test | 15% | ~1,050 | ~50% | ~50% |

- Stratified Split으로 각 세트의 라벨 분포가 원본과 동일하게 유지됨
- `random_state=42`로 재현 가능성 보장

---

## 3. 저장 형식

```
data/processed/
├── train.csv       # 피처 15개 + label 컬럼
├── val.csv
└── test.csv
```

**CSV 헤더:**
```
match_id,team_a_duelist_count,team_a_initiator_count,team_a_controller_count,
team_a_sentinel_count,team_b_duelist_count,team_b_initiator_count,
team_b_controller_count,team_b_sentinel_count,duelist_diff,initiator_diff,
controller_diff,sentinel_diff,team_a_has_controller,team_b_has_controller,
map_encoded,label
```

---

## 4. 품질 검증 체크리스트

```python
def validate_splits(train, val, test):
    """분할 결과 품질 검증"""
    
    # 1. 행 수 합계 확인
    total = len(train) + len(val) + len(test)
    print(f"전체 {total}행 = Train {len(train)} + Val {len(val)} + Test {len(test)}")
    
    # 2. 라벨 분포 확인 (0.45~0.55 범위)
    for name, df in [("Train", train), ("Val", val), ("Test", test)]:
        ratio = df["label"].mean()
        assert 0.45 <= ratio <= 0.55, f"{name} 라벨 불균형: {ratio:.3f}"
        print(f"{name} 승률: {ratio:.3f} ✓")
    
    # 3. 피처 누락 확인
    feature_cols = [c for c in train.columns if c not in ["match_id", "label"]]
    assert len(feature_cols) == 15, f"피처 수 오류: {len(feature_cols)}"
    
    # 4. 데이터 타입 확인
    for col in feature_cols:
        assert train[col].dtype in ["int64", "float64"], f"{col} 타입 오류"
    
    # 5. 결측값 0 확인
    for name, df in [("Train", train), ("Val", val), ("Test", test)]:
        null_count = df.isnull().sum().sum()
        assert null_count == 0, f"{name} 결측값: {null_count}"
    
    print("\n✅ 모든 품질 검증 통과")
```

---

## 5. 데이터 분포 시각화 (선택)

```python
import matplotlib.pyplot as plt
import seaborn as sns

def plot_feature_distributions(train: pd.DataFrame):
    feature_cols = [c for c in train.columns if c not in ["match_id", "label"]]
    
    fig, axes = plt.subplots(3, 5, figsize=(20, 12))
    for ax, col in zip(axes.flat, feature_cols):
        train[col].hist(ax=ax, bins=10)
        ax.set_title(col)
    plt.tight_layout()
    plt.savefig("reports/feature_distributions.png")
```

---

## 6. 전체 파이프라인 실행 순서

```bash
# 데이터 준비부터 분할까지 한 번에 실행
python ml/data_pipeline.py

# 내부 실행 순서:
# 1. load_and_preprocess("data/raw")
# 2. clean_data(df)
# 3. aggregate_to_match_level(df)
# 4. augment_symmetric(df)
# 5. create_features_batch(df, le_map)
# 6. split_and_save(df)
# 7. validate_splits(train, val, test)
```

---

## 7. 관련 문서

| 문서 | 내용 |
|---|---|
| [../05_data_learning/07_cross_validation.md](../05_data_learning/07_cross_validation.md) | train.csv로 10-Fold CV 학습 |
| [../05_data_learning/01_model_strategy.md](../05_data_learning/01_model_strategy.md) | 학습 전략 전체 |
