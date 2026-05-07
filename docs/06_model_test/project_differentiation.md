# 프로젝트 차별점 검증 — ValoPredictML

기반 코드: `ml/data_pipeline.py`, `ml/evaluate_model.py`, `ml/train_model.py`

---

## 단순 통계 사이트와 다른 점

| 구분 | 단순 통계 사이트 (tracker.gg 등) | ValoPredictML |
|------|----------------------------------|---------------|
| 예측 단위 | 개별 선수 통계 나열 | 팀 A vs 팀 B **역할 조합 차이** |
| 편향 문제 | 팀 포지션 편향 존재 | A/B Swap 증강으로 제거 |
| 검증 방법 | 없음 (단순 표시) | GroupKFold + 누수 방지 검증 |
| 설명 가능성 | 없음 | SHAP 기반 피처 기여도 |
| 하이퍼파라미터 | 없음 | Optuna 자동 최적화 |

---

## 5개 핵심 차별점

### 1. 역할 조합 단위 예측

개별 선수 KDA가 아닌 **팀 A vs 팀 B 역할 카운트·차이·조합**을 피처로 사용한다.

```python
# ml/data_pipeline.py:36-43
FEATURE_COLS_P1 = [
    "a_duelist", "a_initiator", "a_controller", "a_sentinel",
    "b_duelist", "b_initiator", "b_controller", "b_sentinel",
    "diff_duelist", "diff_initiator", "diff_controller", "diff_sentinel",
    "has_controller_a", "has_controller_b",
    "a_avg_kills", "a_avg_assists", "a_avg_deaths",
    "b_avg_kills", "b_avg_assists", "b_avg_deaths",
]
```

### 2. A/B Swap 대칭 증강

어떤 팀이 "A"로 기록되느냐는 임의적이다. Swap 증강은 이 포지션 편향을 제거하고 클래스 균형을 맞춘다.

```python
# ml/data_pipeline.py:919-966
def augment_swap(df: pd.DataFrame) -> pd.DataFrame:
    swap = df.copy()
    # 팀 A ↔ 팀 B 피처 교환 (a_* ↔ b_*, diff_* 부호 반전)
    swap["label"] = 1 - df["label"].values
    swap["match_key"] = df["match_key"].astype(str) + "_swap"
    ...
```

결과: train 66,485행 → 93,078행, label 50:50 균형.

### 3. Leakage-free 교차검증 (GroupKFold)

같은 경기(match_key)의 원본·swap twin이 다른 fold에 들어가면 낙관적 검증이 된다.

```python
# ml/evaluate_model.py:49-51
gkf = GroupKFold(n_splits=n_splits)
groups = df_train["match_key"].str.replace(r"_swap$", "", regex=True)
```

`_swap` suffix 제거로 원본과 twin을 항상 같은 그룹으로 묶는다. test.csv는 K-Fold 중 절대 사용하지 않는다.

### 4. SHAP 기반 설명 가능성

왜 이 팀 조합이 이기는지 피처 기여도로 설명한다.

```python
# ml/evaluate_model.py:137-154
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_sample)
```

세 모델 간 SHAP Spearman r=0.899 → 피처 중요도 일관성 검증 완료.  
Top5: `a_avg_assists`, `b_avg_assists`, `b_fk_fd_ratio`, `a_fk_fd_ratio`, `b_avg_agent_exp`.

### 5. Optuna 하이퍼파라미터 자동 최적화

수동 튜닝 없이 TPESampler + MedianPruner로 자동 최적화한다.

```python
# ml/train_model.py:219-242
study = optuna.create_study(
    direction="maximize",
    sampler=optuna.samplers.TPESampler(seed=42),
    pruner=optuna.pruners.MedianPruner(n_warmup_steps=5),
)
study.optimize(objective, n_trials=50)
```

`--optimize` 플래그로 활성화. 최적 파라미터는 `models/best_params.json`에 저장된다.

---

## 기술 스택 적정성

| 기술 | 사용 여부 | 판정 | 이유 |
|------|-----------|------|------|
| 딥러닝 (Neural Network) | 미사용 | **적절** | 93k행 표 형태 데이터 → 트리 기반이 표준 선택 |
| 스택킹 (Stacking Ensemble) | 미사용 (단순 평균) | **적절** | 단순 평균이 과적합 위험 낮고 해석 용이 |
| SMOTE (클래스 불균형) | 미사용 | **적절** | 도메인 기반 A/B Swap 증강이 더 의미 있음 |
| AutoML | Optuna HPO만 사용 | **적절** | HPO는 표준 관행; Full AutoML은 오버킬 |
| 임베딩 (Embedding) | 미사용 | **적절** | 역할 카운트/비율 피처로 충분 |
| 외부 API / 실시간 데이터 | 미사용 | **적절** | 배치 예측 목표; 실시간 필요 없음 |

### 고급기술이 없어도 충분한 이유

이 프로젝트의 문제는 **93k행 표 형태 이진 분류**다. 이 규모에서:

- 딥러닝은 표 데이터에서 트리 기반 모델 대비 이점이 없고 해석이 어렵다.
- 스택킹은 추가 메타 모델 학습으로 복잡도가 높아지며 단순 평균보다 일관되게 우수하다는 보장이 없다.
- SMOTE는 합성 데이터를 생성하지만, A/B Swap은 **실제 경기 물리 구조**를 활용한 증강이다.

결론: **문제 규모와 목표에 맞는 적정 복잡도**가 적용됐다. 고급 기술의 부재는 부족함이 아니라 설계 선택이다.
